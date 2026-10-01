from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
from threading import Event
import time
import unittest
from unittest.mock import patch

from pcbuilder import recommendation, runtime


class RecommendationPerformanceTests(unittest.TestCase):
    def setUp(self):
        runtime.RECOMMENDATION_CACHE.clear()
        self.addCleanup(runtime.RECOMMENDATION_CACHE.clear)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.db = patch.object(runtime, 'DB_PATH', Path(self.folder.name) / 'pc.db')
        self.db.start()
        self.addCleanup(self.db.stop)

    def inventory(self):
        return {kind: [] for kind in ('cpu', 'gpu', 'ram', 'mb', 'storage', 'psu')}

    def test_same_request_is_coalesced_and_cached_output_is_independent(self):
        started, release = Event(), Event()
        def inventory():
            started.set()
            self.assertTrue(release.wait(2))
            return self.inventory()
        with patch.object(recommendation, 'verified_recommendation_inventory', side_effect=inventory) as fetch, \
             ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(recommendation.recommend, {'budget': 2000000})
            self.assertTrue(started.wait(1))
            second = pool.submit(recommendation.recommend, {'budget': 2000000})
            time.sleep(.02)
            release.set()
            response = first.result(timeout=1)
            second.result(timeout=1)
            response['warning'] = 'changed caller copy'
            cached = recommendation.recommend({'budget': 2000000})
        self.assertNotEqual('changed caller copy', cached['warning'])
        self.assertTrue(cached['engine']['cached'])
        self.assertEqual(1, fetch.call_count)

    def test_config_revision_invalidates_complete_result(self):
        config = Path(self.folder.name) / 'config.json'
        config.write_text('{}')
        with patch.object(runtime, 'CONFIG_PATH', config), \
             patch.object(recommendation, 'verified_recommendation_inventory', side_effect=self.inventory) as fetch:
            recommendation.recommend({'budget': 2100000})
            recommendation.recommend({'budget': 2100000})
            config.write_text('{"revision": 2}')
            recommendation.recommend({'budget': 2100000})
        self.assertEqual(2, fetch.call_count)

    def test_revision_change_during_compute_is_not_cached_as_new_revision(self):
        config = Path(self.folder.name) / 'concurrent-config.json'
        config.write_text('{}')
        calls = []
        def inventory():
            calls.append(True)
            if len(calls) == 1:
                config.write_text('{"revision": 2}')
            return self.inventory()
        with patch.object(runtime, 'CONFIG_PATH', config), \
             patch.object(recommendation, 'verified_recommendation_inventory', side_effect=inventory):
            recommendation.recommend({'budget': 2300000})
            recommendation.recommend({'budget': 2300000})
            recommendation.recommend({'budget': 2300000})
        self.assertEqual(2, len(calls))


if __name__ == '__main__':
    unittest.main()
