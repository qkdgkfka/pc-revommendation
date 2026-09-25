import importlib.util
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("refresh_games",ROOT/"scripts/refresh_game_data.py")
refresh=importlib.util.module_from_spec(spec);spec.loader.exec_module(refresh)

class GameRefreshTests(unittest.TestCase):
    def test_merge_preserves_other_sources_and_pending(self):
        snapshot={"measurements":[{"source_url":"a"},{"source_url":"b"}],"pending_measurements":[{"source_url":"b"}]}
        refresh.merge_source(snapshot,"a",[{"source_url":"a","avg_fps":42}],[])
        self.assertEqual(len(snapshot["measurements"]),2)
        self.assertEqual(snapshot["pending_measurements"],[{"source_url":"b"}])

    def test_invalid_numeric_cells_are_never_guessed(self):
        for value in ("13 7","-","NaN","inf","120fps","0","1501"):
            self.assertIsNone(refresh.number(value))
        self.assertEqual(refresh.number("58.5"),58.5)
        self.assertNotIn("rx7080xt",refresh.GPU_MAP)

    def test_csv_requires_reference_cpu_and_native_methodology(self):
        html='<h1>Review</h1><script type="application/ld+json">{"@type":"Article","datePublished":"2025-03-05"}</script>'
        with self.assertRaises(ValueError):refresh.parse_b2g(html,"invalid csv")

    def test_saved_rows_validate_and_pending_are_excluded(self):
        from game_benchmarks import load_measurements
        loaded=load_measurements()
        snapshot=json.loads((ROOT/"data/game_benchmarks.json").read_text(encoding="utf8"))
        self.assertEqual(len(loaded),len(snapshot["measurements"]))
        self.assertGreater(len(snapshot["pending_measurements"]),0)
        for row in loaded:
            self.assertIs(row["ray_tracing"],False)
            self.assertEqual(row["upscaling"],"native")
            self.assertIs(row["frame_generation"],False)
        for game in ["csgo2","pubg","baldurs_gate3","zenless_zone_zero"]:
            self.assertTrue(any(r["game"]==game for r in loaded),game)

    def test_cap_remains_game_rule_not_fabricated_measurement(self):
        from server_fixed import game_frame_cap
        self.assertEqual(game_frame_cap("genshin_impact"),60)
        self.assertEqual(game_frame_cap("elden_ring"),60)
        self.assertIsNone(game_frame_cap("zenless_zone_zero"))

if __name__=="__main__":unittest.main()
