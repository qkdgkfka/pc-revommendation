import unittest
from unittest.mock import patch
import game_benchmarks as benchmarks
import game_database
from collections import defaultdict
from server_catalogs import CATALOGS, GAME_FPS_PROFILES


def observation(gpu, fps, *, cpu='fast', resolution='1080', low=None):
    return dict(game='fixture', gpu_id=gpu, cpu_id=cpu, resolution=resolution,
                preset='high', preset_label='High', avg_fps=fps, low1_fps=low,
                source_url='https://review.example/benchmark', source_title='Review',
                published_at='2026-01-01', collected_at='2026-01-02',
                reference_cpu=cpu, reference_ram='32 GB DDR5', game_version='1.0')


class EmpiricalFpsTests(unittest.TestCase):
    def test_validation_profiles_match_server_without_import_side_effects(self):
        import subprocess
        import sys
        result = subprocess.run([sys.executable, '-c', '''
import copy
from server_catalogs import GAME_FPS_PROFILES
before = copy.deepcopy(GAME_FPS_PROFILES)
import pcbuilder.runtime
assert before == GAME_FPS_PROFILES, 'Server import changed validation profiles'
'''], capture_output=True, text=True, cwd=benchmarks.SNAPSHOT_PATH.parent.parent)
        self.assertEqual(0, result.returncode, result.stderr)

    def setUp(self):
        self.catalogs = {
            'gpu': [dict(id=key, name=key, perf_1080=perf, perf_1440=perf * .9, perf_2160=perf * .6)
                    for key, perf in [('small', 50), ('medium', 100), ('large', 200)]],
            'cpu': [dict(id='fast', perf=100), dict(id='slow', perf=50)],
        }
        self.profile = dict(cpu_weight=.25, low1=.8)

    def estimate(self, rows, gpu='small', cpu='fast', resolution='1080', preset='high', ram_gb=32):
        with patch.object(benchmarks, 'load_measurements', return_value=tuple(rows)):
            return benchmarks.estimate_from_measurements(
                next(p for p in self.catalogs['gpu'] if p['id']==gpu),
                next(p for p in self.catalogs['cpu'] if p['id']==cpu),
                {'gb':ram_gb}, 'fixture', resolution, preset, self.profile, self.catalogs)

    def test_missing_preset_uses_closest_reported_setting_before_resolution(self):
        rows = [dict(observation('small', 100, resolution='1440'), preset='high'),
                dict(observation('small', 50), preset='ultra', preset_label='Ultra')]
        _, _, evidence = self.estimate(rows, preset='medium')
        self.assertEqual('High', evidence['reference_preset'])

    def test_low_interpolation_tolerates_missing_source_resolution_profile(self):
        self.catalogs['gpu'][1].pop('perf_1080')
        average, low, evidence = self.estimate(
            [observation('small', 100, low=50)], gpu='medium', resolution='1440')
        self.assertGreater(average, 0)
        self.assertTrue(low is None or 0 < low <= average)

    def test_exact_small_ram_measurement_is_not_penalized_twice(self):
        row = dict(observation('small', 100, low=73), reference_ram='8 GB DDR5')
        avg, low, evidence = self.estimate([row], ram_gb=8)
        self.assertEqual((100, 73), (avg, low))
        self.assertEqual('measured_benchmark', evidence['method'])

    def test_both_memory_kit_notations_resolve_total_capacity(self):
        for label in ('2 x 16 GB DDR5', '16GB x 2 DDR5'):
            with self.subTest(label=label):
                _, _, evidence = self.estimate([dict(observation('small', 100), reference_ram=label)])
                self.assertIs(True, evidence['ram_capacity_match'])

    def test_resolution_uses_paired_game_observations(self):
        rows = [observation('small',100), observation('large',200),
                observation('large',100,resolution='1440')]
        average, _, evidence = self.estimate(rows,resolution='1440')
        self.assertAlmostEqual(50, average, delta=.2)
        self.assertEqual('benchmark_calibrated', evidence['method'])

    def test_middle_resolution_uses_same_gpu_frame_time_curve(self):
        # Linear pixel cost: 1080p takes 10 ms; 2160p takes 40 ms.
        rows = [observation('small', 100, low=50),
                observation('small', 25, resolution='2160', low=12.5),
                observation('large', 200),
                observation('large', 180, resolution='1440')]
        average, low, evidence = self.estimate(rows, resolution='1440')
        self.assertAlmostEqual(56.25, average, delta=.1)
        self.assertAlmostEqual(28.125, low, delta=.1)
        self.assertEqual('resolution_frame_time_interpolation',
                         evidence['paired_transfers'][0]['method'])
        self.assertEqual('benchmark_calibrated', evidence['method'])

    def test_resolution_curve_does_not_cross_context_or_extrapolate(self):
        from benchmark_interpolation import paired_transfer
        gpu = self.catalogs['gpu'][0]
        index = {row['id']: row for row in self.catalogs['gpu']}
        start = observation('small', 100)
        end = observation('small', 25, resolution='2160')
        for change in ({'source_url': 'https://other.example/review'},
                       {'cpu_id': 'slow'}, {'reference_ram_gb': 64},
                       {'workload_note': 'different scene'}, {'game_version': '2.0'},
                       {'preset_label': 'Custom'}, {'avg_fps': 150}):
            with self.subTest(change=change):
                self.assertIsNone(paired_transfer(start, 'resolution', '1440',
                    [start, dict(end, **change)], index, gpu))
        middle = observation('small', 60, resolution='1440')
        self.assertIsNone(paired_transfer(middle, 'resolution', '1080',
                                          [middle, end], index, gpu))

    def test_missing_low_does_not_invent_measured_low_curve(self):
        rows = [observation('small', 100, low=50),
                observation('small', 25, resolution='2160')]
        average, low, evidence = self.estimate(rows, resolution='1440')
        self.assertAlmostEqual(56.25, average, delta=.1)
        self.assertLessEqual(low, average)
        self.assertIsNone(evidence['paired_transfers'][0]['low_ratio'])
        self.assertTrue(evidence['low1_estimated'])

    def test_inverted_lows_do_not_establish_resolution_low_curve(self):
        rows = [observation('small', 100, low=20),
                observation('small', 25, resolution='2160', low=24)]
        average, low, evidence = self.estimate(rows, resolution='1440')
        self.assertAlmostEqual(56.25, average, delta=.1)
        # No valid low curve: carry the measured 40ms tail overhead forward.
        self.assertAlmostEqual(1000 / (1000 / average + 40), low, delta=.1)
        self.assertIsNone(evidence['paired_transfers'][0]['low_ratio'])

    def test_cpu_uses_same_review_paired_observations(self):
        rows = [observation('small',100), observation('large',200),
                observation('large',100,cpu='slow')]
        average, _, _ = self.estimate(rows,cpu='slow')
        self.assertAlmostEqual(50, average, delta=.2)

    def test_one_percent_low_interpolates_measured_lows_independently(self):
        rows = [observation('small',100,low=30), observation('large',400,low=320)]
        average, low, evidence = self.estimate(rows,gpu='medium')
        self.assertAlmostEqual(200,average,delta=.2)
        self.assertAlmostEqual((30*320)**.5,low,delta=.2)
        self.assertTrue(evidence['low1_estimated'])

    def test_paired_correction_never_crosses_review_or_game_version(self):
        base = [observation('small',100), observation('large',200)]
        cross_source = dict(observation('large',100,resolution='1440'), source_url='https://other.example/review')
        cross_version = dict(observation('large',100,resolution='1440'), game_version='2.0')
        expected = self.estimate(base,resolution='1440')[0]
        self.assertEqual(expected,self.estimate(base+[cross_source],resolution='1440')[0])
        self.assertEqual(expected,self.estimate(base+[cross_version],resolution='1440')[0])

    def test_exact_measurement_preserves_average_and_low(self):
        row=observation('small',100,low=73)
        average,low,evidence=self.estimate([row])
        self.assertEqual((100,73),(average,low))
        self.assertEqual('measured_benchmark',evidence['method'])

    def test_requested_preset_curve_wins_over_same_gpu_at_other_settings(self):
        # The requested high setting has measured endpoints around this GPU.
        # A 1000 FPS low-setting run must not override that measured curve.
        rows = [observation('small', 100), observation('large', 400),
                dict(observation('medium', 1000), preset='low', preset_label='Low')]
        average, _, evidence = self.estimate(rows, gpu='medium')
        self.assertAlmostEqual(200, average, delta=.2)
        self.assertEqual('High', evidence['reference_preset'])

    def test_unknown_reference_ram_does_not_claim_full_memory_match(self):
        row = dict(observation('small', 100, low=73), reference_ram='not reported')
        average, low, evidence = self.estimate([row])
        self.assertEqual((100, 73), (average, low))
        self.assertIsNone(evidence.get('ram_capacity_match'))
        self.assertNotEqual('high', evidence['confidence'])

    def test_different_reference_ram_keeps_measurement_with_lower_confidence(self):
        row = dict(observation('small', 100, low=73), reference_ram='64 GB DDR5', reference_ram_gb=64)
        average, low, evidence = self.estimate([row])
        self.assertEqual((100, 73), (average, low))
        self.assertEqual(64, evidence.get('reference_ram_gb'))
        self.assertIs(False, evidence.get('ram_capacity_match'))
        self.assertNotEqual('high', evidence['confidence'])

    def test_reported_reference_ram_capacity_can_match(self):
        _, _, evidence = self.estimate([observation('small', 100)])
        self.assertIs(True, evidence.get('ram_capacity_match'))
        self.assertEqual(32, evidence.get('reference_ram_gb'))

    def test_memory_and_workload_changes_do_not_form_measured_pairs(self):
        base = [observation('small', 100), observation('large', 200)]
        expected = self.estimate(base, resolution='1440')[0]
        for change in ({'reference_ram': '16 GB DDR4'}, {'reference_ram_gb': 64}, {'workload_note': 'different scene'},
                       {'preset_label': 'Custom settings'}):
            other = dict(observation('large', 50, resolution='1440'), **change)
            self.assertEqual(expected, self.estimate(base + [other], resolution='1440')[0])

    def test_missing_resolution_index_does_not_crash_paired_prediction(self):
        rows = [observation('small', 100), observation('large', 200),
                observation('large', 100, resolution='1440')]
        self.catalogs['gpu'][0].pop('perf_1440')
        result = self.estimate(rows, gpu='medium', resolution='1440')
        self.assertTrue(result is None or result[0] > 0)

    def test_all_exact_snapshot_conditions_preserve_source_values(self):
        with patch.object(game_database, 'load_snapshot', return_value=None):
            benchmarks.clear_caches()
            rows = benchmarks.load_measurements()
        self.addCleanup(benchmarks.clear_caches)
        groups = defaultdict(list)
        for row in rows:
            groups[tuple(row[key] for key in ('game', 'gpu_id', 'cpu_id', 'resolution', 'preset'))].append(row)
        gpu = {row['id']: row for row in CATALOGS['gpu']}
        cpu = {row['id']: row for row in CATALOGS['cpu']}
        self.assertGreater(len(groups), 0)
        with patch.object(benchmarks, 'load_measurements', return_value=rows):
            for (game, gpu_id, cpu_id, resolution, preset), observations in groups.items():
                with self.subTest(game=game, gpu=gpu_id, cpu=cpu_id, resolution=resolution, preset=preset):
                    average, low, evidence = benchmarks.estimate_from_measurements(
                        gpu[gpu_id], cpu[cpu_id], {'gb': 32}, game, resolution, preset,
                        GAME_FPS_PROFILES.get(game, GAME_FPS_PROFILES['default']), CATALOGS)
                    self.assertEqual('measured_benchmark', evidence['method'])
                    selected = [row for row in observations if row['source_url'] == evidence['source_url']]
                    self.assertIn(average, [round(row['avg_fps'], 1) for row in selected])
                    if not evidence['low1_estimated']:
                        selected_lows = [row for row in observations if row['source_url'] == evidence['low1_source_url']]
                        self.assertIn(low, [round(row['low1_fps'], 1) for row in selected_lows if row.get('low1_fps')])


if __name__=='__main__': unittest.main()
