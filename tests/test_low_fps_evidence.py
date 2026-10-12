import unittest
from unittest.mock import patch

import game_benchmarks as benchmarks
from test_empirical_fps import observation


class LowFpsEvidenceTests(unittest.TestCase):
    def test_missing_low_is_not_zero_performance_in_recommendation_metrics(self):
        from pcbuilder.pricing import value_metrics
        metrics = value_metrics(180, 1000000, 144, None, 100)
        self.assertIsNone(metrics['low1_target_coverage'])
        self.assertIn('1% Low 자료 없음', metrics['capacity_label'])
        self.assertIn('충족', metrics['capacity_label'])

    def setUp(self):
        self.catalogs = {
            'gpu': [dict(id=key, name=key, perf_1080=perf, perf_1440=perf*.7, perf_2160=perf*.4)
                    for key, perf in [('small', 50), ('medium', 100), ('large', 200)]],
            'cpu': [dict(id='fast', perf=100), dict(id='slow', perf=50)],
        }
        self.addCleanup(benchmarks.clear_caches)

    def estimate(self, rows, preset='high', gpu='small', cpu='fast'):
        with patch.object(benchmarks, 'load_measurements', return_value=tuple(rows)):
            return benchmarks.estimate_from_measurements(
                next(p for p in self.catalogs['gpu'] if p['id'] == gpu),
                next(p for p in self.catalogs['cpu'] if p['id'] == cpu),
                {'gb': 32}, 'fixture', '1080', preset,
                {'cpu_weight': .25, 'low1': .9}, self.catalogs)

    def test_average_only_source_never_creates_low_from_profile_ratio(self):
        average, low, evidence = self.estimate([observation('small', 100)])
        self.assertEqual(100, average)
        self.assertIsNone(low)
        self.assertEqual('unavailable', evidence['low1_method'])

    def test_low_has_own_measured_source_even_if_average_source_has_none(self):
        average_row = observation('small', 110)
        low_row = dict(observation('small', 100, low=40),
                       source_url='https://other.example/low-benchmark')
        average, low, evidence = self.estimate([average_row, low_row])
        self.assertEqual(110, average)
        self.assertEqual(40, low)
        self.assertEqual(low_row['source_url'], evidence['low1_source_url'])
        self.assertEqual('measured', evidence['low1_method'])

    def test_lower_preset_keeps_measured_tail_time_instead_of_scaling_low(self):
        average, low, evidence = self.estimate([observation('small', 100, low=40)], preset='low')
        # Source excess frame time = 25ms - 10ms = 15ms.
        self.assertAlmostEqual(1000 / (1000 / average + 15), low, delta=.1)
        self.assertLess(low, average * .4)
        self.assertEqual('interpolated', evidence['low1_method'])
        self.assertEqual('low', evidence['low1_confidence'])

    def test_exact_low_is_preserved_without_blanket_discount(self):
        _, low, evidence = self.estimate([observation('small', 100, low=91)])
        self.assertEqual(91, low)
        self.assertEqual('measured', evidence['low1_method'])

    def test_gpu_curve_uses_actual_low_values_not_average_ratio(self):
        _, low, evidence = self.estimate([
            observation('small', 100, low=30), observation('large', 400, low=320)
        ], gpu='medium')
        self.assertAlmostEqual((30*320)**.5, low, delta=.1)
        self.assertEqual('interpolated', evidence['low1_method'])


if __name__ == '__main__':
    unittest.main()
