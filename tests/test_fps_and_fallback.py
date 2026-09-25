import copy
import random
import unittest
from unittest.mock import patch

import game_benchmarks as benchmarks
import server_fixed as server


def part(kind, identifier):
    return next(p for p in server.CATALOGS[kind] if p["id"] == identifier)


class GameFpsCoverageTests(unittest.TestCase):
    def test_every_selectable_game_returns_finite_ordered_fps_at_all_resolutions(self):
        with patch.object(server, "db_lookup_benchmarks", return_value=[]):
            values = set()
            for game in server.GAME_OPTIONS:
                for resolution in ("1080", "1440", "2160"):
                    response = server.fps_estimate_response({"gpu":"gpu_rtx5070", "cpu":"cpu_r5_7600", "ram":"ram_32_ddr5", "game":game["id"], "resolution":resolution})
                    fps = response["fps"]
                    options = fps["fps_by_option"]
                    with self.subTest(game=game["id"], resolution=resolution):
                        self.assertGreater(options["ultra"], 0)
                        self.assertGreaterEqual(options["low"], options["medium"])
                        self.assertGreaterEqual(options["medium"], options["high"])
                        self.assertGreaterEqual(options["high"], options["ultra"])
                        self.assertLessEqual(fps["bottleneck"]["percent"], 100)
                        self.assertGreaterEqual(fps["bottleneck"]["percent"], 0)
                        self.assertTrue(fps["graphics_modes"])
                        values.add(options["high"])
            self.assertGreater(len(values), len(server.GAME_OPTIONS))

    def test_measurement_is_not_modified_for_exact_reference_conditions(self):
        row = next(r for r in benchmarks.load_measurements() if r["game"] == "black_myth_wukong" and r["resolution"] == "1440" and r["gpu_id"] == "gpu_rtx5070")
        fps = server.estimate_fps_bundle(part("gpu",row["gpu_id"]), part("cpu",row["cpu_id"]), {"gb":32}, row["game"], row["resolution"], 144,"mid", ["rpg"])
        self.assertEqual(row["avg_fps"], fps["fps_by_option"][row["preset"]])
        self.assertEqual("measured_benchmark", fps["option_evidence"][row["preset"]]["method"])

    def test_weaker_cpu_reduces_fps_and_increases_cpu_penalty(self):
        gpu = part("gpu", "gpu_rtx5090")
        bundles = [server.estimate_fps_bundle(gpu, part("cpu",identifier), {"gb":32},"starfield","1080",144,"mid",["rpg"])
                   for identifier in ("cpu_r5_5500", "cpu_r7_9800x3d")]
        self.assertLess(bundles[0]["avg_fps"], bundles[1]["avg_fps"])
        self.assertGreater(bundles[0]["bottleneck"]["cpu_percent"], bundles[1]["bottleneck"]["cpu_percent"])

    def test_4k_only_evidence_does_not_become_a_false_cpu_limit_at_1080p(self):
        gpu, cpu = part("gpu", "gpu_rtx5070"), part("cpu", "cpu_r7_9800x3d")
        bundles = [server.estimate_fps_bundle(gpu, cpu, {"gb":32}, "alan_wake2", resolution, 144, "mid", ["rpg"])
                   for resolution in ("1080", "1440", "2160")]
        self.assertGreater(bundles[0]["fps_by_option"]["high"], bundles[1]["fps_by_option"]["high"])
        self.assertGreater(bundles[1]["fps_by_option"]["high"], bundles[2]["fps_by_option"]["high"])
        self.assertEqual(33.0, bundles[2]["fps_by_option"]["high"])
        self.assertLess(bundles[0]["bottleneck"]["cpu_percent"], 10)

    def test_korean_names_and_aliases_resolve_to_correct_game(self):
        for value, expected in [("에이펙스 레전드","apex"),("CS2","csgo2"),("Cyberpunk 2077","cyberpunk2077")]:
            self.assertEqual(expected, server.normalized_game_key(value))

    def test_graphics_modes_respect_gpu_and_game_support(self):
        def modes(gpu, game):
            result = server.fps_estimate_response({"gpu":gpu,"cpu":"cpu_r7_9800x3d","ram":"ram_32_ddr5","game":game,"resolution":"1440"})
            return {r["id"]:r for r in result["fps"]["graphics_modes"]}
        old = modes("gpu_rtx3060", "hogwarts_legacy")
        current = modes("gpu_rtx4060", "hogwarts_legacy")
        new = modes("gpu_rtx5070", "hogwarts_legacy")
        self.assertNotIn("fg2", old)
        self.assertIn("fg2", current)
        self.assertNotIn("mfg4", current)
        self.assertIn("mfg4", new)
        self.assertEqual(235.0, new["upscale_fg_measured"]["avg_fps"])
        self.assertEqual("mode_measurement", new["upscale_fg_measured"]["method"])
        self.assertGreater(new["fg2"]["avg_fps"],new["fg2"]["render_fps"])
        self.assertNotIn("upscale", modes("gpu_rtx5070","valorant"))


class VerifiedInventoryRecommendationTests(unittest.TestCase):
    def setUp(self):
        server.RECOMMENDATION_CACHE.clear()
        from datetime import datetime, timezone
        inventory = {}
        for kind in ("cpu","gpu","ram","mb","psu","storage"):
            inventory[kind] = [
                {**part, "price_source":"danawa_live", "price_status":"verified",
                 "scraped_at":datetime.now(timezone.utc).isoformat(),
                 "url":"https://prod.danawa.com/info/?pcode=123",
                 "image_url":"https://img.danuri.io/verified-test-photo.jpg"}
                for part in server.CATALOGS[kind]
            ]
        verified = patch.object(server, "verified_recommendation_inventory", return_value=inventory)
        verified.start()
        self.addCleanup(verified.stop)
        self.addCleanup(server.RECOMMENDATION_CACHE.clear)
        for name,value in [("db_lookup_price",None),("db_lookup_benchmarks",[]),("resolve_verified_gpu_market_prices",{}),("refresh_recommendation_prices",None)]:
            patcher=patch.object(server,name,return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_low_and_all_tiers_remain_visible_under_small_budgets(self):
        for vendor in ("NVIDIA","AMD","ANY"):
            for game in ("valorant","apex","marvel_rivals"):
                with self.subTest(vendor=vendor,game=game):
                    payload=server.recommend({"budget":300000,"game":game,"gpu_pref":vendor})
                    previous=None
                    for tier in ("low","mid","high"):
                        row=payload["results"][tier]
                        self.assertEqual(6,len(row["parts"]))
                        self.assertTrue(row["compatibility"]["compatible"])
                        self.assertTrue(server.is_recommendable_gpu(row["parts"]["gpu"]))
                        if previous:
                            self.assertGreaterEqual(row["totalPrice"],previous["totalPrice"])
                            self.assertGreaterEqual(row["fps"]["avg_fps"],previous["fps"]["avg_fps"])
                        previous=row

    def test_verified_prices_are_not_replaced_after_selection(self):
        with patch.object(server,"refresh_recommendation_prices") as refresh:
            p=server.recommend({"budget":2000000,"game":"apex"})
        refresh.assert_not_called()
        for row in p["results"].values():
            self.assertEqual(6, len(row["parts"]))
            self.assertEqual(sum(part["price"] for part in row["parts"].values()), row["totalPrice"])
            self.assertTrue(all(part["verified"] for part in row["parts"].values()))
        prices=[r["totalPrice"] for r in p["results"].values()]
        self.assertEqual(sorted(prices),prices)

    def test_repeat_request_uses_cache_without_sharing_mutable_response(self):
        query={"budget":900000,"game":"apex"}
        a=server.recommend(query)
        a["results"]["low"]["parts"].clear()
        with patch.object(server,"build_tier_candidates",side_effect=AssertionError("cache miss")):
            b=server.recommend(query)
        self.assertTrue(b["engine"]["cached"])
        self.assertTrue(b["results"]["low"]["parts"])


if __name__ == "__main__":
    unittest.main()
