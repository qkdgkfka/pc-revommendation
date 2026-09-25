import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import crawl_game_benchmarks as crawler


class BenchmarkCrawlerTests(unittest.TestCase):
    def test_native_sentence_is_not_replaced_with_generated_fps(self):
        html = """
        <p>AMD Ryzen 7 9800X3D</p><h3>Alan Wake 2</h3>
        <p>Settings: 4K High</p>
        <img src="native.jpg" alt="Alan Wake 2 @ 4K High, Rasterisation Only">
        <p>The RTX 5070 offered an average framerate of 33FPS.</p>
        <p>After switching on ray tracing, DLSS and Frame Gen: 54FPS.</p>
        <img src="generated.jpg" alt="Alan Wake 2 @ 4K High, DLSS Frame Gen">
        """
        rule = next(rule for rule in crawler.GEEK_RULES if rule[1] == "alan_wake2")
        with patch.object(crawler, "GEEK_RULES", [rule]):
            row, = crawler.parse_geek(html)
            self.assertEqual(row["avg_fps"], 33)
            self.assertFalse(row["frame_generation"])
            self.assertEqual(row["upscaling"], "native")
            self.assertTrue(row["chart_url"].endswith("native.jpg"))
            with self.assertRaises(ValueError):
                crawler.parse_geek(html.replace("Rasterisation Only", "DLSS Frame Gen"))

    def test_gn_rejects_chart_moved_into_ray_tracing_section(self):
        html = """
        <p>9800X3D</p><h3>RTX 5070 Benchmarks</h3>
        <h4>Dragon’s Dogma 2 - 4K</h4>
        <img src="Dragon%20(4K_Max).png">
        <p>The RTX 5070 ran at 56 FPS AVG.</p>
        """
        rule = next(rule for rule in crawler.GN_RULES if rule[1] == "dragons_dogma2")
        with patch.object(crawler, "GN_RULES", [rule]):
            self.assertEqual(crawler.parse_gn(html)[0]["avg_fps"], 56)
            with self.assertRaises(ValueError):
                crawler.parse_gn(html.replace("RTX 5070 Benchmarks", "RTX 5070 Ray Tracing Benchmarks"))
            with self.assertRaises(ValueError):
                crawler.parse_gn(html.replace("4K_Max", "4K_Low"))
            with self.assertRaises(ValueError):
                crawler.parse_gn(html.replace("9800X3D", "Unknown CPU"))

    def test_ambiguous_or_missing_measurements_fail_closed(self):
        pattern = r"RTX 5070 ran at (\d+) FPS AVG"
        for text in ("No reported FPS", "RTX 5070 ran at 56 FPS AVG. RTX 5070 ran at 58 FPS AVG."):
            with self.assertRaises(ValueError):
                crawler.measurement(text, pattern)

    def test_failed_source_preserves_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "benchmarks.json"
            output.write_text("previous snapshot", encoding="utf-8")
            with patch.object(crawler, "urlopen", side_effect=[io.BytesIO(b"page one"), io.BytesIO(b"page two")]), \
                    patch.object(crawler, "parse_gn", return_value=[]), \
                    patch.object(crawler, "parse_geek", side_effect=ValueError("changed source")):
                with self.assertRaises(ValueError):
                    crawler.crawl(output)
            self.assertEqual(output.read_text(encoding="utf-8"), "previous snapshot")

    def test_snapshot_covers_added_games_with_traceable_native_results(self):
        snapshot = json.loads(crawler.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        rows = snapshot["measurements"]
        expected = {"dragons_dogma2", "dying_light2", "resident_evil4", "alan_wake2",
                    "marvel_rivals", "cod_black_ops6", "fortnite"}
        self.assertTrue(expected.issubset({row["game"] for row in rows}))
        keys = set()
        for row in rows:
            self.assertTrue(row["source_url"].startswith("https://"))
            self.assertTrue(row["chart_url"])
            self.assertEqual(len(row["evidence_sha256"]), 64)
            from server_catalogs import CPU_CATALOG
            self.assertIn(row["cpu_id"], {cpu["id"] for cpu in CPU_CATALOG})
            self.assertFalse(row["ray_tracing"])
            self.assertFalse(row["frame_generation"])
            self.assertEqual(row["upscaling"], "native")
            self.assertGreater(row["avg_fps"], 0)
            key = tuple(row[field] for field in ("source_url", "game", "gpu_id", "cpu_id", "resolution", "preset"))
            self.assertNotIn(key, keys)
            keys.add(key)


if __name__ == "__main__":
    unittest.main()
