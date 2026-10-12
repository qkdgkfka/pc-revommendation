import unittest
from unittest.mock import patch

import product_filters as filters


class FilterPerformanceTests(unittest.TestCase):
    def test_categories_without_facets_do_not_parse_product_specs(self):
        with patch.object(filters, 'normalize_specs', wraps=filters.normalize_specs) as normalize:
            for kind in ('case', 'software'):
                self.assertEqual([], filters.facets(kind, [{'name': 'ASUS product'}]))
        normalize.assert_not_called()

    def test_facet_counts_keep_unique_values_and_selected_missing_options(self):
        rows = [
            {'specs': {'memory_type': ('DDR5', 'DDR5'), 'socket': 'AM5'}},
            {'specs': {'memory_type': 'DDR5', 'socket': 'LGA1700'}},
        ]
        facets = {item['key']: item for item in filters.facets(
            'mb', rows, {'memory_type': ['DDR4']})}
        self.assertEqual({'DDR5': 2, 'DDR4': 0}, facets['memory_type']['counts'])
        self.assertEqual([['DDR5', 'DDR5'], ['DDR4', 'DDR4']],
                         facets['memory_type']['options'])


if __name__ == '__main__':
    unittest.main()
