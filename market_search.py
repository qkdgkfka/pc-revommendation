"""Logical retail pages assembled from fixed-size provider batches.

A short-lived search snapshot records emitted SKUs, so grouped variants, saved
quotes and repeated provider rows cannot shift/duplicate already delivered pages.
"""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import RLock
import time


class ProductPager:
    def __init__(self, providers, fetch, saved, matches, identity, sort='popular', deadline_aware=False):
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
        self.deadline_aware = deadline_aware

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

    def fetch_round(self, deadline=None):
        providers = [p for p in self.providers if self.more[p]]
        if not providers:
            return
        pool = ThreadPoolExecutor(max_workers=len(providers))
        pending = {p: pool.submit(self.fetch, p, self.next_provider_page[p], deadline)
                   if self.deadline_aware else pool.submit(self.fetch, p, self.next_provider_page[p])
                   for p in providers}
        results, timed_out = [], set()
        try:
            for p in providers:
                try:
                    result = pending[p].result(timeout=max(0, deadline - time.monotonic()) if deadline else None)
                except TimeoutError:
                    pending[p].cancel()
                    timed_out.add(p)
                    result = {'items': [], 'has_more': True, 'status': 'unavailable',
                              'source_url': self.results.get(p, {}).get('source_url', ''),
                              'cached': False, 'error_kind': 'timeout',
                              'error': '판매처 조회 제한 시간을 초과했습니다.'}
                results.append(result)
        finally:
            # A slow provider cannot hold the response past the total request budget.
            pool.shutdown(wait=False, cancel_futures=True)
        for p, result in zip(providers, results):
            self.results[p] = result
            if p in timed_out:
                continue
            self.next_provider_page[p] += 1
            keys = {self.identity(row) for row in result['items']}
            new = keys - self.provider_seen[p]
            self.provider_seen[p].update(keys)
            # Empty filtered pages may still have a next upstream page. Repeated
            # nonempty batches signal a provider ignoring its offset.
            self.more[p] = bool(result.get('has_more')) and (result.get('query_stream') or not keys or bool(new)) and (result.get('continue_search') or result['status'] not in {'unavailable', 'stale'})
        for i in range(max((len(r['items']) for r in results), default=0)):
            self.add([r['items'][i] for r in results if i < len(r['items'])])

    def page(self, number, limit, deadline=None):
        deadline = deadline if deadline is not None else time.monotonic() + 12
        acquired = self.lock.acquire(timeout=max(0, deadline - time.monotonic()))
        if not acquired:
            return {'items': [], 'has_more': True, 'results': {
                p: {'items': [], 'status': 'unavailable', 'source_url': '', 'cached': False,
                    'error_kind': 'timeout', 'error': '판매처 조회 제한 시간을 초과했습니다.'}
                for p in self.providers}, 'partial': True}
        try:
            reused = len(self.pages) >= number
            while len(self.pages) < number:
                # Request one batch from each active provider per user page, then
                # continue only if it is needed to fill the logical page.
                rounds = 0
                if time.monotonic() < deadline:
                    self.fetch_round(deadline); rounds += 1
                if not self.seeded:
                    self.add(self.saved())
                    self.seeded = True
                while len(self.available()) < limit and any(self.more.values()) and rounds < 6 and time.monotonic() < deadline:
                    self.fetch_round(deadline); rounds += 1
                keys = self.available()[:limit]
                self.delivered.update(keys)
                rows = [self.rows[key] for key in keys]
                pending = bool(self.available() or any(self.more.values()))
                self.pages.append({'items': rows, 'has_more': pending, 'results': dict(self.results),
                                   'partial': len(rows) < limit and pending})
            return {**self.pages[number - 1], 'reused': reused}
        finally:
            self.lock.release()


class RetailQueryStream:
    """Round-robin chipset searches when a retailer's generation query is fuzzy."""
    def __init__(self, providers, queries, fetch):
        self.fetch = fetch
        self.queues = {p:[{'query':q, 'page':1, 'seen':set()} for q in queries] for p in providers}
        self.locks = {p: RLock() for p in providers}

    def next(self, provider, _logical_page, deadline=None):
        lock = self.locks[provider]
        acquired = lock.acquire(timeout=max(0, deadline - time.monotonic())) if deadline else lock.acquire()
        if not acquired:
            raise TimeoutError('Retail request deadline exceeded')
        try:
            queue = self.queues[provider]
            state = queue.pop(0)
            try:
                result = (self.fetch(provider, state['query'], state['page'], deadline)
                          if deadline is not None else self.fetch(provider, state['query'], state['page']))
                if deadline is not None and time.monotonic() >= deadline:
                    raise TimeoutError('Retail request deadline exceeded')
            except BaseException:
                queue.insert(0, state)
                raise
            state['page'] += 1
            keys = {str(row.get('id')) for row in result['items']}
            fresh = keys - state['seen']
            state['seen'].update(keys)
            if result.get('has_more') and result['status'] not in {'unavailable','stale'} and (not keys or fresh):
                queue.append(state)
            return {**result, 'has_more':bool(queue), 'query_stream':True,
                    'continue_search':bool(queue) and bool(result.get('query_failed'))}
        finally:
            lock.release()
