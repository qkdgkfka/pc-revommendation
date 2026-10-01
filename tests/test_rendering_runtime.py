"""Regression cases for rendering evidence used by the production API."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import crawl_game_benchmarks as crawler
import rendering_calibration as calibration
from graphics_estimates import graphics_scenarios
from pcbuilder import fps as fps_service
from scripts import refresh_rendering_calibration as refresh


def paired_row(**changes):
    return dict(game='starfield', gpu_id='gpu_rx7800xt', resolution='2160',
                technology='FSR', native_fps=39.7, upscale_fps=53.8,
                factor=2, base_fps=53.8, display_fps=96.2,
                source_url='https://review.example/paired', evidence_sha256='a' * 64,
                conditions='Quality, same scene', **changes)


class RenderingRuntimeTests(unittest.TestCase):
    def tearDown(self):
        calibration.calibration_data.cache_clear()

    def test_missing_snapshot_calibration_uses_reviewed_runtime_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'rendering.json'
            path.write_text(json.dumps({'fg_calibration': [paired_row()],
                'upscale_calibration': [paired_row()],
                'fsr_support': {'starfield': {'fsr': True, 'fg': True, 'version': 'FSR 3'}}}))
            with patch.object(calibration, 'CALIBRATION_PATH', path, create=True), \
                 patch('game_database.load_snapshot', return_value={'measurements': []}):
                calibration.calibration_data.cache_clear()
                data = calibration.calibration_data()
                self.assertEqual(data['fg_calibration'][0]['display_fps'], 96.2)
                self.assertTrue(data['fsr_support']['starfield']['fg'])

    def test_native_quality_pairs_are_derived_from_reviewed_measurements(self):
        common = dict(game='expedition33', gpu_id='gpu_rtx5070', cpu_id='cpu_r7_9800x3d',
                      resolution='1440', preset='high', source_url='https://review.example/chart',
                      evidence_sha256='b' * 64, ray_tracing=False)
        snapshot = {'measurements': [dict(common, avg_fps=47.6, upscaling='native', frame_generation=False)],
                    'graphics_measurements': [dict(common, avg_fps=74, mode='upscale',
                                                  generated=False, upscaling='DLSS Quality')]}
        with patch.object(calibration, 'CALIBRATION_PATH', Path('/missing-rendering.json'), create=True), \
             patch('game_database.load_snapshot', return_value=snapshot):
            calibration.calibration_data.cache_clear()
            result = calibration.upscale_prediction(47.6, {'id': 'gpu_rtx5070'},
                                                     'expedition33', '1440', 'DLSS', {})
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result[0], 74)

    def test_derived_fsr2_pair_retains_version_and_cannot_enter_fsr3(self):
        common = dict(game='test_game', gpu_id='gpu_rx7800xt', cpu_id='cpu_r7_9800x3d',
                      resolution='2160', preset='high', source_url='https://review.example/chart',
                      evidence_sha256='b' * 64, ray_tracing=False)
        snapshot = {'measurements': [dict(common, avg_fps=50, upscaling='native', frame_generation=False)],
                    'graphics_measurements': [dict(common, avg_fps=75, mode='upscale',
                                                  generated=False, upscaling='FSR 2 Quality')]}
        pairs = calibration.snapshot_quality_pairs(snapshot)
        with patch.object(calibration, 'calibration_data', return_value={'upscale_calibration': pairs}):
            fsr2 = calibration.upscale_prediction(50, {'id': 'gpu_rx7800xt'}, 'test_game', '2160', 'FSR', {}, version='FSR 2')
            fsr3 = calibration.upscale_prediction(50, {'id': 'gpu_rx7800xt'}, 'test_game', '2160', 'FSR', {}, version='FSR 3')
        self.assertIsNotNone(fsr2)
        self.assertAlmostEqual(fsr2[0], 75)
        self.assertIsNone(fsr3)

    def test_same_review_keeps_fsr2_and_fsr3_quality_pairs_separate(self):
        second = dict(paired_row(), technology_version='FSR 2', native_fps=50, upscale_fps=75)
        third = dict(paired_row(), technology_version='FSR 3', native_fps=50, upscale_fps=80)
        with patch.object(calibration, 'CALIBRATION_PATH', Path('/missing-rendering.json')), \
             patch('game_database.load_snapshot', return_value={'upscale_calibration': [second, third]}):
            calibration.calibration_data.cache_clear()
            result = calibration.upscale_prediction(50, {'id': 'gpu_rx7800xt'}, 'starfield', '2160', 'FSR', {}, version='FSR 2')
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result[0], 75)

    def test_fsr3_fg_does_not_borrow_ml_frame_generation_cost(self):
        native = {'fps_by_option': {'high': 40}, 'fps_range_by_option': {'high': {'min': 30, 'max': 50}},
                  'fps_source': 'benchmark_calibrated', 'bottleneck': {}}
        data = {'upscale_calibration': [dict(paired_row(), technology_version='FSR 3')],
                'fg_calibration': [dict(paired_row(), technology_version='FSR 4')],
                'fsr_support': {'starfield': {'fsr': True, 'fg': True, 'version': 'FSR 3'}}}
        with patch('rendering_calibration.calibration_data', return_value=data), \
             patch('graphics_estimates.calibration_data', return_value=data):
            rows = {r['id']: r for r in graphics_scenarios({'id': 'gpu_rx7800xt'}, {}, 'starfield', '2160', native, lambda _: 40)}
        self.assertNotIn('fg2', rows)
        self.assertEqual(rows['fg2_unavailable']['unavailable_reason'], 'missing_evidence')

    def test_native_crawl_preserves_rendering_calibration_metadata(self):
        previous = {'measurements': [], 'sources': [], 'graphics_measurements': [],
                    'fg_calibration': [paired_row()], 'upscale_calibration': [paired_row()],
                    'fsr_support': {'starfield': {'fsr': True}}}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'snapshot.json'
            path.write_text(json.dumps(previous))
            with patch.object(crawler, 'urlopen', side_effect=[io.BytesIO(b'one'), io.BytesIO(b'two')]), \
                 patch.object(crawler, 'parse_gn', return_value=[]), \
                 patch.object(crawler, 'parse_geek', return_value=[]), \
                 patch.object(crawler, 'parse_graphics_modes', return_value=[]):
                result = crawler.crawl(path)
        self.assertEqual(result.get('fg_calibration'), previous['fg_calibration'])
        self.assertEqual(result.get('fsr_support'), previous['fsr_support'])

    def test_upscaling_prefers_matching_resolution_before_other_game_gpu(self):
        a = paired_row(); a.update(game='other', gpu_id='gpu_rtx5070', technology='DLSS',
                                   resolution='1440', native_fps=40, upscale_fps=80)
        b = paired_row(); b.update(game='other', gpu_id='gpu_rtx4070', technology='DLSS',
                                   native_fps=40, upscale_fps=60)
        with patch.object(calibration, 'calibration_data', return_value={'upscale_calibration': [a, b]}):
            result = calibration.upscale_prediction(40, {'id': 'gpu_rtx5070'}, 'unknown', '2160', 'DLSS', {})
        self.assertAlmostEqual(result[0], 60)

    def test_missing_evidence_is_explicitly_unavailable_not_unsupported(self):
        native = {'fps_by_option': {'high': 60}, 'fps_range_by_option': {'high': {'min': 50, 'max': 70}},
                  'fps_source': 'benchmark_calibrated', 'bottleneck': {}}
        empty = {'upscale_calibration': [], 'fg_calibration': [], 'fsr_support': {}}
        with patch('rendering_calibration.calibration_data', return_value=empty), \
             patch('graphics_estimates.calibration_data', return_value=empty), \
             patch('graphics_estimates.graphics_measurements', return_value=()), \
             patch('graphics_estimates.feature_support', return_value={'starfield': {'dlss': True, 'fg': True, 'mfg': True}}):
            rows = {r['id']: r for r in graphics_scenarios({'id': 'gpu_rtx5070'}, {}, 'starfield', '1440', native, lambda _: 60)}
        self.assertEqual(rows['upscale_unavailable']['unavailable_reason'], 'missing_evidence')

    def test_fsr1_does_not_borrow_fsr3_temporal_upscaling_samples(self):
        native = {'fps_by_option': {'high': 60}, 'fps_range_by_option': {'high': {'min': 50, 'max': 70}},
                  'fps_source': 'benchmark_calibrated', 'bottleneck': {}}
        data = {'upscale_calibration': [paired_row()], 'fg_calibration': [],
                'fsr_support': {'dota2': {'fsr': True, 'fg': False, 'version': 'FSR 1'}}}
        with patch('rendering_calibration.calibration_data', return_value=data), \
             patch('graphics_estimates.calibration_data', return_value=data):
            rows = {r['id']: r for r in graphics_scenarios({'id': 'gpu_rx7800xt'}, {}, 'dota2', '2160', native, lambda _: 60)}
        self.assertNotIn('upscale', rows)
        self.assertEqual(rows['upscale_unavailable']['unavailable_reason'], 'missing_evidence')

    def test_fps_revision_changes_when_rendering_file_is_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'rendering.json'; path.write_text('{}')
            with patch.object(calibration, 'CALIBRATION_PATH', path, create=True):
                first = fps_service._fps_revision()
                path.write_text('{"revision": 2}')
                self.assertNotEqual(first, fps_service._fps_revision())

    def test_live_api_has_dlss_fg_and_vendor_specific_fsr_evidence(self):
        for gpu, technology in [('gpu_rtx5070', 'DLSS'), ('gpu_rx7800xt', 'FSR')]:
            with self.subTest(gpu=gpu):
                result = fps_service.fps_estimate_response({'gpu': gpu, 'cpu': 'cpu_r7_9800x3d',
                    'ram': 'ram_32_ddr5', 'game': 'starfield', 'resolution': '1440'})['fps']
                rows = {r['id']: r for r in result['graphics_modes']}
                self.assertGreater(rows['upscale']['avg_fps'], rows['native']['avg_fps'])
                self.assertTrue(rows['fg2']['calibration_sources'])
                self.assertEqual(rows['fg2']['technology'], technology)
                self.assertTrue(all(r['game'] == 'starfield' for r in rows['fg2']['calibration_references']))

    def test_every_runtime_pair_reconstructs_the_recorded_average(self):
        archive = json.loads(calibration.CALIBRATION_PATH.read_text())
        self.assertTrue(archive['fg_calibration'])
        for row in archive['fg_calibration']:
            with self.subTest(game=row['game'], factor=row['factor']), \
                 patch.object(calibration, 'calibration_data', return_value={'fg_calibration': [row]}):
                result = calibration.fg_prediction(row['base_fps'], {'id': row['gpu_id']},
                    row['game'], row['resolution'], row['technology'], row['factor'])
                self.assertEqual(result['avg_fps'], row['display_fps'])
        for row in archive['upscale_calibration']:
            with self.subTest(game=row['game'], technology=row['technology']), \
                 patch.object(calibration, 'calibration_data', return_value={'upscale_calibration': [row]}):
                result = calibration.upscale_prediction(row['native_fps'], {'id': row['gpu_id']},
                    row['game'], row['resolution'], row['technology'], {})
                self.assertAlmostEqual(result[0], row['upscale_fps'])


class CalibrationRefreshTests(unittest.TestCase):
    def test_dlss4_chart_uses_average_and_explicit_generation_factors(self):
        html = '''<div class="chart" data-title="Cyberpunk 2077, Full Raytracing, DLSS 4 MFG – 3.840 × 2.160">
        <div class="chart__group"><h3 class="chart__group-header">FPS, Durchschnitt</h3>
        <div class="chart__row"><span class="chart__item">5090 @ DLSS 4 SR + RR</span><span data-value="56.7"></span></div>
        <div class="chart__row"><span class="chart__item">5090 @ DLSS 4 SR + RR + FG</span><span data-value="103.5"></span></div>
        <div class="chart__row"><span class="chart__item">5090 @ DLSS 4 SR + RR + MFG 4×</span><span data-value="190.9"></span></div>
        <div class="chart__row"><span class="chart__item">5090 @ DLSS 3 SR + RR + FG</span><span data-value="999"></span></div>
        </div><div class="chart__group"><h3 class="chart__group-header">FPS, 1% Perzentil</h3></div></div>'''
        rows = refresh.dlss4_pairs(html, refresh.CB5090)
        self.assertEqual([(r['factor'], r['base_fps'], r['display_fps']) for r in rows],
                         [(2, 56.7, 103.5), (4, 56.7, 190.9)])
        self.assertTrue(all(r['ray_tracing'] for r in rows))
        self.assertTrue(all(r['quality'] == 'unspecified' for r in rows))

    def test_ml_only_support_does_not_masquerade_as_measured_fsr3(self):
        html = '''<h2>AMD FSR™ “Redstone”</h2><table><td>Cyberpunk 2077</td></table>
        <h2>AMD FSR™ Frame Generation</h2><table><td>Cyberpunk 2077</td></table>
        <h2>AMD FSR™ 3</h2><table><td>Starfield</td></table>'''
        data = refresh.amd_support(html)
        self.assertFalse(data['cyberpunk2077']['fsr'])
        self.assertFalse(data['cyberpunk2077']['fg'])
        self.assertTrue(data['starfield']['fg'])


if __name__ == '__main__':
    unittest.main()
