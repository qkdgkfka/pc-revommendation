from concurrent.futures import ThreadPoolExecutor
from threading import Event
import time
import unittest
from unittest.mock import patch

from market_search import ProductPager
from pcbuilder import retail, runtime


class RetailPerformanceTests(unittest.TestCase):
    def test_logical_page_passes_remaining_deadline_to_every_fetch(self):
        deadlines = []
        def fetch(provider, number, deadline=None):
            deadlines.append(deadline)
            time.sleep(.02)
            return {'items': [], 'has_more': True, 'status': 'live', 'source_url': '', 'cached': False}
        pager = ProductPager(['danawa'], fetch, lambda: [], lambda row: True, lambda row: row['id'])
        # Explicitly opting into the provider deadline protocol keeps legacy callbacks valid.
        pager.deadline_aware = True
        deadline = time.monotonic() + .05
        result = pager.page(1, 50, deadline=deadline)
        self.assertTrue(result['partial'])
        self.assertTrue(deadlines)
        self.assertTrue(all(value == deadline for value in deadlines))
        self.assertLess(time.monotonic() - deadline, .08)

    def test_identical_retail_fetches_are_coalesced(self):
        runtime.MARKET_BROWSE_CACHE.clear()
        started, release = Event(), Event()
        calls = []
        def fetch(url, provider, timeout):
            calls.append(url)
            started.set()
            self.assertTrue(release.wait(2))
            return '<html>Service unavailable</html>'
        with patch.object(retail, '_market_fetch_html', side_effect=fetch), \
             patch.object(retail, 'saved_market_page', return_value={'items': []}), \
             ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(retail._market_source_page, 'ram', '', 1, 40, 'danawa', False, 1, False)
            self.assertTrue(started.wait(1))
            second = pool.submit(retail._market_source_page, 'ram', '', 1, 40, 'danawa', False, 1, False)
            time.sleep(.02)
            release.set()
            self.assertEqual('unavailable', first.result(timeout=1)['status'])
            self.assertEqual('unavailable', second.result(timeout=1)['status'])
        self.assertEqual(1, len(calls))
        runtime.MARKET_BROWSE_CACHE.clear()


if __name__ == '__main__':
    unittest.main()
