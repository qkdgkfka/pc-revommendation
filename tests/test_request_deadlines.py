from concurrent.futures import ThreadPoolExecutor
import time
import unittest
from unittest.mock import patch

from market_search import ProductPager
from pcbuilder import retail, runtime


class RequestDeadlineTests(unittest.TestCase):
    def test_provider_timeout_is_distinguished_from_connection_failure(self):
        runtime.MARKET_BROWSE_CACHE.clear()
        self.addCleanup(runtime.MARKET_BROWSE_CACHE.clear)
        with patch.object(retail, '_market_fetch_html', side_effect=TimeoutError), \
             patch.object(retail, 'saved_market_page', return_value={'items': []}):
            result = retail._market_source_page('ram', 'deadline-test', 1, 40, 'danawa', True, .1, False)
        self.assertEqual('timeout', result['error_kind'])
        self.assertEqual('unavailable', result['status'])

    def test_waiting_for_busy_search_reports_timeout_instead_of_empty_results(self):
        pager = ProductPager(['danawa'], lambda *args: None, lambda: [], lambda row: True, lambda row: row['id'])
        with pager.lock, ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(pager.page, 1, 50, time.monotonic() + .01).result(timeout=1)
        self.assertEqual('timeout', result['results']['danawa']['error_kind'])
        self.assertEqual('unavailable', result['results']['danawa']['status'])

    def test_timeout_reason_reaches_product_response(self):
        runtime.MARKET_SEARCH_CACHE.clear()
        self.addCleanup(runtime.MARKET_SEARCH_CACHE.clear)
        with patch.object(retail, '_market_source_page', return_value={
            'items': [], 'status': 'unavailable', 'has_more': False, 'source_url': '',
            'cached': False, 'error_kind': 'timeout', 'error': '판매처 조회 제한 시간을 초과했습니다.',
        }), patch.object(retail, 'saved_products', return_value=[]):
            result = retail.market_products_response('ram', 'deadline-test', source='danawa', persist=False)
        self.assertFalse(result['ok'])
        self.assertEqual('timeout', result['error_kind'])


if __name__ == '__main__':
    unittest.main()
