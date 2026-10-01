import unittest
from unittest.mock import patch
import server_fixed as server


class RequestPersistenceTests(unittest.TestCase):
    def test_fps_http_response_does_not_write_prediction_database(self):
        with patch('game_database.save_prediction') as save:
            response = server.fps_estimate_response({
                'gpu': 'gpu_rtx5070', 'cpu': 'cpu_r5_7600', 'ram': 'ram_32_ddr5',
                'game': 'cyberpunk2077', 'resolution': '1440',
            })
        self.assertTrue(response['fps']['graphics_modes'])
        save.assert_not_called()

    def test_offline_precomputation_can_explicitly_save_scenarios(self):
        response = server.fps_estimate_response({
            'gpu': 'gpu_rtx5070', 'cpu': 'cpu_r5_7600', 'ram': 'ram_32_ddr5',
            'game': 'cyberpunk2077', 'resolution': '1440',
        })
        gpu = next(p for p in server.GPU_CATALOG if p['id'] == 'gpu_rtx5070')
        cpu = next(p for p in server.CPU_CATALOG if p['id'] == 'cpu_r5_7600')
        with patch('game_database.save_prediction') as save:
            server.attach_graphics_modes(response['fps'], gpu, cpu, 'cyberpunk2077', '1440', persist=True)
        save.assert_called_once()

    def test_missing_rendering_evidence_never_invents_fg_or_upscale(self):
        empty = {'fg_calibration': [], 'upscale_calibration': [], 'fsr_support': {}}
        with patch('graphics_estimates.calibration_data', return_value=empty), \
             patch('rendering_calibration.calibration_data', return_value=empty), \
             patch('graphics_estimates.graphics_measurements', return_value=()), \
             patch('graphics_estimates.feature_support', return_value={'cyberpunk2077': {'dlss': True, 'fg': True, 'mfg': True}}):
            response = server.fps_estimate_response({
                'gpu': 'gpu_rtx5070', 'cpu': 'cpu_r5_7600', 'ram': 'ram_32_ddr5',
                'game': 'cyberpunk2077', 'resolution': '1440',
            })
        modes = {row['id'] for row in response['fps']['graphics_modes'] if row['supported']}
        self.assertEqual({'native'}, modes)
