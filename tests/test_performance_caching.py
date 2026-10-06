from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import tempfile
from threading import Event, Lock
import time
import unittest
from unittest.mock import patch

from pcbuilder.cache import MemoryCache, SingleFlight
from pcbuilder import database, runtime
from pcbuilder.revisions import freshness_ttl


class CachePerformanceTests(unittest.TestCase):
    def test_clear_during_compute_does_not_restore_invalidated_value(self):
        cache = MemoryCache()
        started, release = Event(), Event()

        def slow():
            started.set()
            self.assertTrue(release.wait(2))
            return 'old'

        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(cache.get_or_compute, 'key', slow)
            self.assertTrue(started.wait(1))
            cache.clear()
            release.set()
            self.assertEqual('old', pending.result(timeout=1))
        self.assertIsNone(cache.get('key'))
        self.assertEqual('new', cache.get_or_compute('key', lambda: 'new'))

    def test_request_after_clear_does_not_join_invalidated_work(self):
        cache = MemoryCache()
        started, release = Event(), Event()

        def slow():
            started.set()
            self.assertTrue(release.wait(2))
            return 'old'

        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = pool.submit(cache.get_or_compute, 'key', slow)
            self.assertTrue(started.wait(1))
            cache.clear()
            try:
                fresh = pool.submit(cache.get_or_compute, 'key', lambda: 'new')
                self.assertEqual('new', fresh.result(timeout=.5))
            finally:
                release.set()
            self.assertEqual('old', pending.result(timeout=1))
        self.assertEqual('new', cache.get('key'))

    def test_same_key_computes_once_while_other_key_progresses(self):
        flight = SingleFlight()
        started, release = Event(), Event()
        calls = []

        def slow():
            calls.append('slow')
            started.set()
            self.assertTrue(release.wait(2))
            return 'shared'

        with ThreadPoolExecutor(max_workers=3) as pool:
            first = pool.submit(flight.run, 'same', slow)
            self.assertTrue(started.wait(1))
            second = pool.submit(flight.run, 'same', slow)
            other = pool.submit(flight.run, 'other', lambda: 'independent')
            self.assertEqual('independent', other.result(timeout=1))
            release.set()
            self.assertEqual('shared', first.result(timeout=1))
            self.assertEqual('shared', second.result(timeout=1))
        self.assertEqual(['slow'], calls)

    def test_failed_compute_does_not_poison_key(self):
        cache = MemoryCache(2)
        def fail():
            raise ValueError('retry')
        with self.assertRaisesRegex(ValueError, 'retry'):
            cache.get_or_compute('same', fail)
        self.assertEqual('recovered', cache.get_or_compute('same', lambda: 'recovered'))

    def test_cache_bounds_and_expiry(self):
        cache = MemoryCache(max_entries=2, max_bytes=6)
        for key in ('first', 'second', 'third'):
            cache.get_or_compute(key, lambda: b'123', ttl=.03, size=len)
        self.assertIsNone(cache.get('first'))
        self.assertEqual(b'123', cache.get('third'))
        time.sleep(.04)
        self.assertIsNone(cache.get('third'))

    def test_freshness_expiry_uses_timestamp_boundary(self):
        observed = datetime.fromtimestamp(1000, timezone.utc).isoformat()
        with patch('pcbuilder.revisions.time.time', return_value=1000 + 24 * 3600 - 2):
            ttl = freshness_ttl({'parts': [{'price_checked_at': observed}]}, maximum=300)
        self.assertGreater(ttl, 1.9)
        self.assertLess(ttl, 2)

    def test_snapshot_connection_is_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'pc.db'
            with sqlite3.connect(path) as conn:
                conn.execute('CREATE TABLE sample(value TEXT)')
            with patch.object(runtime, 'DB_PATH', path):
                conn = database._ensure_db_connection()
                try:
                    with self.assertRaises(sqlite3.OperationalError):
                        conn.execute("INSERT INTO sample VALUES ('should fail')")
                finally:
                    conn.close()

    def test_changed_database_refreshes_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'pc.db'
            with sqlite3.connect(path) as conn:
                conn.execute('CREATE TABLE components(id INTEGER, type TEXT, name TEXT)')
                conn.execute("INSERT INTO components VALUES (1,'GPU','first')")
            with patch.object(runtime, 'DB_PATH', path), patch.object(runtime, 'DB_CACHE', {}):
                database.ensure_db_cache_loaded()
                self.assertEqual(1, len(runtime.DB_CACHE['components']))
                with sqlite3.connect(path) as conn:
                    conn.execute("INSERT INTO components VALUES (2,'GPU','second')")
                database.ensure_db_cache_loaded()
                self.assertEqual(2, len(runtime.DB_CACHE['components']))


if __name__ == '__main__':
    unittest.main()
