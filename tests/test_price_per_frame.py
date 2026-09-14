import unittest

import server_fixed as server


class PricePerFrameTests(unittest.TestCase):
    def test_cost_is_total_price_divided_by_fps(self):
        self.assertEqual(20000, server.value_metrics(100, 2000000)['price_per_frame_krw'])

    def test_missing_and_nonfinite_inputs_have_no_cost(self):
        for fps, price in ((0, 100), (None, 100), (100, 0), (float('inf'), 100), (100, float('nan')), (-1, 100)):
            self.assertIsNone(server.value_metrics(fps, price)['price_per_frame_krw'])

    def test_price_refresh_recomputes_all_presets_and_clears_stale_cost(self):
        plan = {'parts': {'gpu': {'price': 600000}, 'cpu': {'price': 200000}},
                'fps': {'fps_by_option': {'low': 200, 'medium': 160, 'high': 100}}}
        server.recompute_plan_total(plan)
        self.assertEqual(8000, plan['fps']['price_per_frame_krw'])
        self.assertEqual(4000, plan['fps']['price_per_frame_by_option']['low'])
        plan['parts']['gpu']['price'] = 800000
        server.recompute_plan_total(plan)
        self.assertEqual(10000, plan['fps']['price_per_frame_krw'])
        plan['fps']['fps_by_option']['high'] = None
        server.recompute_plan_total(plan)
        self.assertIsNone(plan['fps']['price_per_frame_krw'])


if __name__ == '__main__':
    unittest.main()
