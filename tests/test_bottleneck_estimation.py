"""Bottleneck estimates must respect controlled tests and pipeline semantics."""
import math
import unittest
from unittest.mock import patch

from bottleneck_estimation import estimate_bottleneck, frame_time_balance


def observation(cpu, gpu, average, **changes):
    return dict(game='fixture', cpu_id=cpu, gpu_id=gpu, avg_fps=average,
                resolution='1080', preset='high', preset_label='High',
                source_url='https://review.example/test', published_at='2026-01-01',
                game_version='1', workload_note='same scene', reference_ram='32GB',
                ray_tracing=False, frame_generation=False, upscaling='native', **changes)


class BottleneckEstimationTests(unittest.TestCase):
    def setUp(self):
        self.gpu = {'id': 'small', 'vendor': 'NVIDIA'}
        self.cpu = {'id': 'slow'}
        self.catalogs = {'gpu': [self.gpu, {'id': 'large', 'vendor': 'NVIDIA'},
                                 {'id': 'other', 'vendor': 'AMD'}]}
        self.evidence = {'method': 'measured_benchmark',
                         'source_url': 'https://review.example/test',
                         'published_at': '2026-01-01', 'reference_preset': 'High',
                         'reference_ram': '32GB', 'game_version': '1',
                         'workload_note': 'same scene',
                         'bottleneck': {'cpu_fps_ceiling': 120, 'gpu_fps_ceiling': 120}}
        self.rows = (observation('slow', 'small', 60), observation('fast', 'small', 100),
                     observation('slow', 'large', 75), observation('fast', 'large', 150))

    def estimate(self, rows=None, **kwargs):
        return estimate_bottleneck(self.gpu, self.cpu, 'fixture', '1080', 'high',
                                   60, self.evidence, self.rows if rows is None else rows,
                                   self.catalogs, **kwargs)

    def test_equal_capacities_do_not_create_synthetic_sixteen_percent_losses(self):
        result = frame_time_balance(100, 100)
        self.assertEqual('balanced', result['limiting_component'])
        self.assertEqual((0, 0), (result['cpu_percent'], result['gpu_percent']))

    def test_model_limits_follow_overlapping_frame_times(self):
        cpu = frame_time_balance(50, 100)
        gpu = frame_time_balance(100, 50)
        self.assertEqual((50, 0, 'cpu'), (cpu['cpu_percent'], cpu['gpu_percent'], cpu['limiting_component']))
        self.assertEqual((0, 50, 'gpu'), (gpu['cpu_percent'], gpu['gpu_percent'], gpu['limiting_component']))

    def test_missing_or_invalid_capacities_are_unknown_not_zero(self):
        for value in (None, 0, -1, True, math.inf, math.nan):
            result = frame_time_balance(value, 100)
            self.assertIsNone(result['percent'])
            self.assertEqual('unknown', result['limiting_component'])

    def test_measured_pairs_override_generic_hardware_scores(self):
        result = self.estimate()
        self.assertEqual('matched_hardware_comparison', result['method'])
        self.assertEqual((40, 20), (result['cpu_percent'], result['gpu_percent']))
        self.assertEqual((100, 75), (result['cpu_reference_fps'], result['gpu_reference_fps']))
        self.assertIsNone(result['cpu_fps_ceiling'], 'Observed FPS is not an isolated CPU ceiling')
        self.assertEqual('fast', result['comparisons']['cpu']['reference_id'])

    def test_cross_vendor_gpu_driver_effect_is_not_attributed_to_gpu_capacity(self):
        rows = self.rows + (observation('slow', 'other', 200),)
        self.assertEqual(20, self.estimate(rows)['gpu_percent'])

    def test_different_scenes_versions_memory_and_settings_are_not_pooled(self):
        for field, changed in [('workload_note', 'other scene'), ('game_version', '2'),
                               ('reference_ram', '16GB'), ('preset_label', 'Custom'),
                               ('resolution', '2160'), ('preset', 'ultra'),
                               ('source_url', 'https://other.example/test'),
                               ('ray_tracing', True), ('upscaling', 'quality'),
                               ('frame_generation', True)]:
            rows = tuple(dict(row, **{field: changed}) for row in self.rows)
            with self.subTest(field=field):
                self.assertEqual('frame_time_model', self.estimate(rows)['method'])

    def test_single_cpu_review_cannot_claim_an_observed_cpu_comparison(self):
        result = self.estimate(self.rows[:1] + self.rows[2:3])
        self.assertEqual('frame_time_model', result['method'])
        self.assertEqual('low', result['confidence'])

    def test_frame_cap_is_its_own_limiter(self):
        result = self.estimate(frame_cap=60)
        self.assertEqual('frame_cap', result['limiting_component'])
        self.assertEqual((0, 0), (result['cpu_percent'], result['gpu_percent']))
        self.assertEqual((40, 20), (result['uncapped']['cpu_percent'], result['uncapped']['gpu_percent']))

    def test_retail_skus_use_reference_ids_and_source_inputs_are_not_mutated(self):
        self.gpu = {'id': 'retail', 'performance_ref_id': 'small', 'vendor': 'NVIDIA'}
        result = self.estimate()
        self.assertEqual(40, result['cpu_percent'])
        self.assertEqual({'cpu_fps_ceiling': 120, 'gpu_fps_ceiling': 120}, self.evidence['bottleneck'])

    def test_upscaling_does_not_treat_a_capacity_gap_as_cpu_busy_time(self):
        from rendering_calibration import upscale_prediction
        with patch('rendering_calibration.selected_pairs', return_value=[{'native_fps': 50, 'upscale_fps': 100}]):
            prediction, _ = upscale_prediction(50, {}, 'fixture', '1080', 'DLSS',
                                               {'cpu_fps_ceiling': 60, 'cpu_penalty_pct': 70})
        self.assertEqual(60, prediction)

    def test_upscaling_uses_observed_gpu_upgrade_limit_conservatively(self):
        from rendering_calibration import upscale_prediction
        with patch('rendering_calibration.selected_pairs', return_value=[{'native_fps': 50, 'upscale_fps': 100}]):
            prediction, _ = upscale_prediction(50, {}, 'fixture', '1080', 'DLSS',
                                               {'method': 'matched_hardware_comparison', 'gpu_reference_fps': 65})
        self.assertEqual(65, prediction)


if __name__ == '__main__':
    unittest.main()
