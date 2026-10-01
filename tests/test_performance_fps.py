from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import game_benchmarks
from pcbuilder import fps
from server_catalogs import CATALOGS


class FpsPerformanceTests(unittest.TestCase):
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
