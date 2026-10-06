import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from pcbuilder import database, retail, runtime
from product_metadata import canonical_name


class PriceLookupPerformanceTests(unittest.TestCase):
    def test_exact_name_does_not_validate_every_unrelated_quote(self):
        name = 'AMD Ryzen 5 7500F'
        row = {'name': name, 'type': 'cpu', 'price': 200000, 'currency': 'KRW',
               'url': 'https://prod.danawa.com/info/?pcode=123',
               'scraped_at': datetime.now(timezone.utc).isoformat()}
        rows = {f'unrelated {i}': dict(row, name='AMD Ryzen 7 7800X3D') for i in range(200)}
        rows[canonical_name(name)] = row
        with patch.object(database, 'ensure_db_cache_loaded'), \
             patch.object(runtime, 'DB_CACHE', {'prices_by_name': rows}), \
             patch.object(retail, 'retail_quote_valid', wraps=retail.retail_quote_valid) as validate:
            result = database.db_lookup_price_info({'name': name}, 'cpu')
        self.assertEqual(200000, result['price'])
        self.assertEqual('db_name_exact', result['price_source'])
        self.assertFalse(result['stale'])
        self.assertLessEqual(validate.call_count, 2)

    def test_wrong_type_exact_name_does_not_mask_valid_fallback(self):
        name = 'AMD Ryzen 5 7500F'
        row = {'name': name, 'type': 'cpu', 'price': 200000,
               'url': 'https://prod.danawa.com/info/?pcode=123', 'scraped_at': '2020-01-01'}
        rows = {canonical_name(name): dict(row, type='gpu'), canonical_name(name) + ' 정품': row}
        with patch.object(database, 'ensure_db_cache_loaded'), \
             patch.object(runtime, 'DB_CACHE', {'prices_by_name': rows}):
            result = database.db_lookup_price_info({'name': name}, 'cpu')
        self.assertEqual(200000, result['price'])
        self.assertTrue(result['stale'])


if __name__ == '__main__':
    unittest.main()
