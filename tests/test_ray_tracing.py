import unittest
from unittest.mock import patch

from graphics_estimates import graphics_scenarios


class RayTracingTests(unittest.TestCase):
    def setUp(self):
        self.gpu = {'id': 'gpu_rtx5070', 'name': 'RTX 5070'}
        self.cpu = {'id': 'cpu_r7_9800x3d'}
        self.fps = {'fps_by_option': {'high': 120, 'ultra': 100},
                    'fps_range_by_option': {'high': {}}, 'fps_source': 'model_estimate'}

    def scenario(self, gpu=None, cpu=None, game='cyberpunk2077', fps=None):
        rows = graphics_scenarios(gpu or self.gpu, cpu or self.cpu, game, '1440',
                                  fps or self.fps, lambda _: 100)
        return next((row for row in rows if row['id'] in ('rt', 'rt_unavailable')), None)

    def test_reviewed_native_rt_pair_is_available(self):
        row = self.scenario()
        self.assertEqual(row['id'], 'rt')
        self.assertTrue(row['supported'])
        self.assertGreater(row['rt_off_fps'], row['avg_fps'])
        self.assertFalse(row['generated'])
        self.assertEqual(row['upscaling'], 'native')
        self.assertEqual(row['method'], 'mode_measurement')

    def test_different_cpu_is_estimated_without_fabricated_low(self):
        row = self.scenario(cpu={'id': 'cpu_i5_14400f'}, fps={**self.fps,
            'fps_by_option': {'high': 45, 'ultra': 30}})
        self.assertEqual(row['id'], 'rt')
        self.assertEqual(row['method'], 'mode_calibrated_estimate')
        self.assertLessEqual(row['avg_fps'], 30)
        self.assertIsNone(row['low1_fps'])

    def test_retail_alias_uses_same_evidence(self):
        row = self.scenario(gpu={'id': 'retail', 'performance_ref_id': 'gpu_rtx5070'})
        self.assertEqual(row['avg_fps'], self.scenario()['avg_fps'])

    def test_unmeasured_gpu_does_not_borrow_other_gpu_rt_ratio(self):
        row = self.scenario(gpu={'id': 'gpu_rx7800xt', 'name': 'RX 7800 XT'})
        self.assertFalse(row['supported'])
        self.assertTrue(row['game_supported'])
        self.assertIsNone(row['avg_fps'])

    def test_non_rt_game_has_no_rt_section(self):
        self.assertIsNone(self.scenario(game='csgo2'))

    def test_frame_cap_applies_to_both_values(self):
        row = self.scenario(fps={**self.fps, 'frame_cap': 20})
        self.assertEqual(row['avg_fps'], 20)
        self.assertEqual(row['rt_off_fps'], 20)
        self.assertLessEqual(row['low1_fps'], 20)

    def test_invalid_or_mixed_mode_evidence_is_rejected(self):
        from ray_tracing_estimates import rt_data
        original = next(r for r in rt_data()['pairs'] if r['game'] == 'cyberpunk2077'
                        and r['gpu_id'] == 'gpu_rtx5070' and r['resolution'] == '1440')
        for change in ({'rt_fps': float('nan')}, {'rt_fps': True}, {'rt_fps': -1},
                       {'frame_generation': True}, {'upscaling': 'DLSS Quality'},
                       {'resolution': '2160'}, {'ray_tracing': False}):
            with self.subTest(change=change), patch('ray_tracing_estimates.rt_data',
                return_value={'support': {'cyberpunk2077': 'Cyberpunk 2077'},
                              'pairs': [{**original, **change}]}):
                self.assertFalse(self.scenario()['supported'])

    def test_csv_pairing_does_not_mix_board_models_or_resolutions(self):
        from scripts.import_rt_evidence import parse_pairs
        header = 'Game Name,GPU Name,Average FPS,1% low average FPS,Model,Resolution,Mode\n'
        off = 'Cyberpunk 2077,NVIDIA GeForce RTX 5070,100,80,Board A,2560x1440,Raster\n'
        on = 'Cyberpunk 2077,NVIDIA GeForce RTX 5070,50,40,Board A,2560x1440,Ray Tracing\n'
        self.assertEqual(len(parse_pairs(header + off + on)), 1)
        self.assertEqual(parse_pairs(header + off + on.replace('Board A', 'Board B')), [])
        self.assertEqual(parse_pairs(header + off + on.replace('2560x1440', '3840x2160')), [])
        self.assertEqual(parse_pairs(header + off + on.replace(',50,', ',150,')), [])
