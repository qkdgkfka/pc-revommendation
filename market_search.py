"""Logical retail pages assembled from fixed-size provider batches.

A short-lived search snapshot records emitted SKUs, so grouped variants, saved
quotes and repeated provider rows cannot shift/duplicate already delivered pages.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import RLock
import time


class ProductPager:
    def __init__(self, providers, fetch, saved, matches, identity, sort='popular'):
        self.providers = providers
        self.fetch = fetch
        self.matches = matches
        self.identity = identity
        self.sort = sort
        self.saved = saved
        self.rows = {}
        self.order = []
        self.delivered = set()
        self.provider_seen = {p:set() for p in providers}
        self.next_provider_page = {p:1 for p in providers}
        self.more = {p:True for p in providers}
        self.results = {}
        self.pages = []
        self.created_at = time.monotonic()
        self.lock = RLock()
        self.seeded = False

    def add(self, items):
        for item in items:
            if not self.matches(item):
                continue
            key = self.identity(item)
            if not key:
                continue
            if key not in self.rows:
                self.order.append(key)
            old = self.rows.get(key)
            # A saved quote must not overwrite a freshly fetched one.
            if not old or item.get('price_status') == 'verified' or old.get('price_status') != 'verified':
                self.rows[key] = item

    def available(self):
        keys = [key for key in self.order if key not in self.delivered]
        if self.sort in {'price_asc', 'price_desc'}:
            keys.sort(key=lambda key: (self.rows[key].get('price') is None,
                       (self.rows[key].get('price') or 0) * (-1 if self.sort == 'price_desc' else 1), str(key)))
        elif self.sort == 'name':
            keys.sort(key=lambda key: (self.rows[key].get('product_name') or self.rows[key].get('name') or '', str(key)))
        return keys

    def fetch_round(self):
        providers = [p for p in self.providers if self.more[p]]
        if not providers:
            return
        with ThreadPoolExecutor(max_workers=len(providers)) as pool:
            results = list(pool.map(lambda p:self.fetch(p, self.next_provider_page[p]), providers))
        for p, result in zip(providers, results):
            self.next_provider_page[p] += 1
            self.results[p] = result
            keys = {self.identity(row) for row in result['items']}
            new = keys - self.provider_seen[p]
            self.provider_seen[p].update(keys)
            # Empty filtered pages may still have a next upstream page. Repeated
            # nonempty batches signal a provider ignoring its offset.
            self.more[p] = bool(result.get('has_more')) and (result.get('query_stream') or not keys or bool(new)) and (result.get('continue_search') or result['status'] not in {'unavailable', 'stale'})
        for i in range(max((len(r['items']) for r in results), default=0)):
            self.add([r['items'][i] for r in results if i < len(r['items'])])

    def page(self, number, limit):
        with self.lock:
            while len(self.pages) < number:
                # Request one batch from each active provider per user page, then
                # continue only if it is needed to fill the logical page.
                started = time.monotonic()
                rounds = 0
                self.fetch_round(); rounds += 1
                if not self.seeded:
                    self.add(self.saved())
                    self.seeded = True
                while len(self.available()) < limit and any(self.more.values()) and rounds < 6 and time.monotonic() - started < 12:
                    self.fetch_round(); rounds += 1
                keys = self.available()[:limit]
                self.delivered.update(keys)
                rows = [self.rows[key] for key in keys]
                pending = bool(self.available() or any(self.more.values()))
                self.pages.append({'items': rows, 'has_more': pending, 'results': dict(self.results),
                                   'partial': len(rows) < limit and pending})
            return self.pages[number - 1]


class RetailQueryStream:
    """Round-robin chipset searches when a retailer's generation query is fuzzy."""
    def __init__(self, providers, queries, fetch):
        self.fetch = fetch
        self.queues = {p:[{'query':q, 'page':1, 'seen':set()} for q in queries] for p in providers}

    def next(self, provider, _logical_page):
        queue = self.queues[provider]
        state = queue.pop(0)
        result = self.fetch(provider, state['query'], state['page'])
        state['page'] += 1
        keys = {str(row.get('id')) for row in result['items']}
        fresh = keys - state['seen']
        state['seen'].update(keys)
        if result.get('has_more') and result['status'] not in {'unavailable','stale'} and (not keys or fresh):
            queue.append(state)
        return {**result, 'has_more':bool(queue), 'query_stream':True,
                'continue_search':bool(queue) and bool(result.get('query_failed'))}
