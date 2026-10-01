from contextlib import ExitStack
import copy
import unittest
from unittest.mock import patch

from pcbuilder import http, pricing


class CatalogPerformanceTests(unittest.TestCase):
    def test_identical_catalog_calls_reuse_normalized_parts_and_facets(self):
        names = {'gpu': 'GPU', 'cpu': 'CPU', 'ram': 'RAM', 'storage': 'STORAGE',
                 'hdd': 'HDD', 'mb': 'MB', 'psu': 'PSU', 'case': 'CASE', 'software': 'SOFTWARE'}
        catalogs = {kind: [{'id': 'performance_' + kind, 'name': kind}] for kind in names}
        with ExitStack() as stack:
            for kind, name in names.items():
                stack.enter_context(patch.object(http, name + '_CATALOG', catalogs[kind]))
            stack.enter_context(patch.object(http, 'CATALOGS', catalogs))
            stack.enter_context(patch.object(http, 'saved_products', return_value=[]))
            stack.enter_context(patch.object(http, 'imported_products', return_value=[]))
            stack.enter_context(patch.object(http, 'enrich_product', side_effect=lambda part, kind: part))
            summaries = stack.enter_context(patch.object(pricing, 'summarize_part', side_effect=lambda part, kind: {'price': 1}))
            facets = stack.enter_context(patch.object(http, 'product_facets', side_effect=lambda kind, rows: {'size': len(rows)}))
            first = http.catalog_response()
            expected = copy.deepcopy(first)
            first['gpus'][0]['name'] = 'modified caller copy'
            second = http.catalog_response()
        self.assertEqual(expected, second)
        self.assertEqual(9, summaries.call_count)
        self.assertEqual(9, facets.call_count)


if __name__ == '__main__':
    unittest.main()
