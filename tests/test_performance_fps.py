from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import game_benchmarks
from pcbuilder import fps
from server_catalogs import CATALOGS


class FpsPerformanceTests(unittest.TestCase):
    def test_candidate_preview_only_measures_high_and_matches_full_estimate(self):
        for game in ('cyberpunk2077', 'genshin_impact', 'unknown_game'):
            with self.subTest(game=game):
                args = list(self.conditions())
                args[3] = game
                with patch.object(fps, 'estimate_from_measurements', wraps=fps.estimate_from_measurements) as measurements:
                    preview = fps.estimate_fps_bundle(*args, high_only=True)
                    self.assertEqual(1, measurements.call_count)
                    full = fps.estimate_fps_bundle(*args)
                self.assertEqual({'high'}, set(preview['fps_by_option']))
                for field in ('fps_by_option', 'low1_by_option', 'option_evidence', 'fps_range_by_option', 'bottleneck_by_option'):
                    self.assertEqual(full[field]['high'], preview[field]['high'])
                for field in ('target_fps', 'target_low1_fps', 'bottleneck', 'value_score', 'avg_fps', 'low1_fps'):
                    self.assertEqual(full[field], preview[field])
                self.assertEqual({'low', 'medium', 'high', 'ultra'}, set(full['fps_by_option']))

    def conditions(self):
        return (dict(CATALOGS['gpu'][0]), dict(CATALOGS['cpu'][0]),
                dict(CATALOGS['ram'][-1]), 'cyberpunk2077', '1440', 144, 'mid', ['rpg'])

    def test_identical_conditions_reuse_compute_and_return_independent_copies(self):
        args = self.conditions()
        with patch.object(fps, 'estimate_from_measurements', return_value=None) as measurements:
            first = fps.estimate_fps_bundle(*args)
            first['fps_by_option']['high'] = -1
            second = fps.estimate_fps_bundle(*args)
        self.assertGreater(second['fps_by_option']['high'], 0)
        self.assertEqual(4, measurements.call_count)

    def test_ram_spec_change_and_snapshot_replacement_invalidate_compute(self):
        args = list(self.conditions())
        with tempfile.TemporaryDirectory() as folder:
            snapshot = Path(folder) / 'benchmarks.json'
            snapshot.write_text('{"measurements": []}')
            with patch.object(game_benchmarks, 'SNAPSHOT_PATH', snapshot), \
                 patch.object(fps, 'estimate_from_measurements', return_value=None) as measurements:
                first = fps.estimate_fps_bundle(*args)
                args[2]['gb'] = 8
                args[2]['speed'] = 2133
                second = fps.estimate_fps_bundle(*args)
                self.assertNotEqual(first['fps_by_option'], second['fps_by_option'])
                snapshot.write_text('{"measurements": [], "revision": 2}')
                fps.estimate_fps_bundle(*args)
                self.assertEqual(12, measurements.call_count)


if __name__ == '__main__':
    unittest.main()
