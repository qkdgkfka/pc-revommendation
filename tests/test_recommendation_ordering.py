"""Regression coverage for ordered, compatible recommendations without network IO."""
import random
import unittest
from unittest.mock import patch

import server_fixed as server


def plan(name, gpu=50, cpu=50, fps=80, low1=60, power=50, score=1, ram=32):
    return {
        "name": name,
        "parts": {"cpu": {"id": name + "cpu"}, "gpu": {"id": name + "gpu"}},
        "totalPrice": 1_000_000,
        "debug": {
            "candidate_score": score,
            "ordering_metrics": {"gpu": gpu, "cpu": cpu, "fps": fps, "low1": low1,
                                 "gpu_1080": gpu, "gpu_1440": gpu, "gpu_2160": gpu,
                                 "power": power, "ram": ram, "storage": 1000, "work": 0},
        },
    }


class OrderedSelectionTests(unittest.TestCase):
    def test_large_score_cannot_override_cpu_gpu_or_fps_regression(self):
        low = plan("low")
        valid = plan("valid", gpu=60, cpu=60, fps=100, low1=70, power=60)
        high = plan("high", gpu=80, cpu=80, fps=120, low1=80, power=80)
        for change in ({"cpu": 49}, {"gpu": 49}, {"gpu_2160": 49}, {"fps": 79}, {"low1": 59}, {"ram": 16}):
            with self.subTest(change=change):
                bad = plan("bad", gpu=60, cpu=60, fps=100, low1=70, power=70, score=1_000_000)
                bad["debug"]["ordering_metrics"].update(change)
                selected = server.select_ordered_tier_plans({"low": [low], "mid": [bad, valid], "high": [high]})
                self.assertEqual("valid", selected["mid"]["name"])

    def test_global_selection_keeps_a_lower_score_candidate_to_enable_all_tiers(self):
        low = plan("low")
        locally_best = plan("locally_best", cpu=95, score=1000)
        mid = plan("mid", gpu=60, cpu=60, fps=100, power=60)
        high = plan("high", gpu=80, cpu=80, fps=120, power=80)
        selected = server.select_ordered_tier_plans({"low": [locally_best, low], "mid": [mid], "high": [high]})
        self.assertTrue(all(selected.values()))
        self.assertEqual("low", selected["low"]["name"])

    def test_strict_upgrade_is_preferred_to_identical_performance(self):
        low = plan("low")
        equal = plan("equal", score=100)
        mid = plan("upgrade", gpu=60, cpu=60, fps=100, power=60)
        high = plan("high", gpu=80, cpu=80, fps=120, power=80)
        selected = server.select_ordered_tier_plans({"low": [low], "mid": [equal, mid], "high": [high]})
        self.assertEqual("upgrade", selected["mid"]["name"])

    def test_frame_cap_does_not_prevent_real_hardware_upgrade(self):
        low = plan("low", fps=60, low1=50)
        mid = plan("mid", gpu=60, cpu=60, fps=60, low1=50, power=60)
        high = plan("high", gpu=80, cpu=80, fps=60, low1=50, power=80)
        selected = server.select_ordered_tier_plans({"low": [low], "mid": [mid], "high": [high]})
        self.assertTrue(all(selected.values()))
        self.assertEqual(2, server.tier_upgrade_quality(low, mid))

    def test_no_valid_triple_does_not_return_a_regressing_fallback(self):
        selected = server.select_ordered_tier_plans({
            "low": [plan("low", cpu=80)], "mid": [plan("mid", cpu=50)],
            "high": [plan("high", cpu=90, gpu=90, fps=120, power=90)],
        })
        populated = [p for p in selected.values() if p]
        self.assertEqual(2, len(populated))
        self.assertGreaterEqual(server.tier_upgrade_quality(*populated), 0)

    def test_missing_middle_tier_still_checks_low_against_high(self):
        selected = server.select_ordered_tier_plans({
            "low": [plan("low", cpu=80)], "high": [plan("high", cpu=40, score=100)],
        })
        self.assertEqual(1, sum(bool(p) for p in selected.values()))

    def test_equal_performance_is_allowed_when_inventory_is_limited(self):
        selected = server.select_ordered_tier_plans({tier: [plan(tier)] for tier in ("low", "mid", "high")})
        self.assertTrue(all(selected.values()))
        self.assertEqual(0, server.tier_upgrade_quality(selected["low"], selected["mid"]))


class CatalogRecommendationTests(unittest.TestCase):
    def setUp(self):
        # Never crawl, refresh prices, or alter the user's SQLite database.
        for target in ("db_lookup_price", "db_lookup_price_info", "db_lookup_benchmarks"):
            patcher = patch.object(server, target, return_value=None)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_component_ranking_has_no_random_jitter(self):
        gpu = server.GPU_CATALOG[0]
        cpu = server.CPU_CATALOG[0]
        self.assertEqual(
            server.score_gpu(gpu, 1_500_000, "1440", "mid", "cyberpunk2077", 144, ["rpg"], random.Random(1)),
            server.score_gpu(gpu, 1_500_000, "1440", "mid", "cyberpunk2077", 144, ["rpg"], random.Random(999)),
        )
        self.assertEqual(
            server.score_cpu(cpu, 1_500_000, "1440", 144, "mid", "cyberpunk2077", random.Random(1)),
            server.score_cpu(cpu, 1_500_000, "1440", 144, "mid", "cyberpunk2077", random.Random(999)),
        )

    def test_unavailable_gpu_vendor_never_falls_back_to_another_vendor(self):
        with patch.object(server, "GPU_CATALOG", [p for p in server.GPU_CATALOG if p["vendor"] == "AMD"]):
            pools = server.tier_component_pools("mid", "1440", 144, "NVIDIA")
            self.assertEqual([], pools[1])

    def test_budget_resolution_vendor_and_work_matrix(self):
        cases = (
            (900_000, "1080", "ANY", "cyberpunk2077", "game", 0),
            (1_500_000, "1440", "NVIDIA", "cyberpunk2077", "game", 0),
            (2_500_000, "2160", "AMD", "cyberpunk2077", "game", 0),
            (2_500_000, "1440", "ANY", "elden_ring", "game", 0),
            (3_000_000, "1440", "NVIDIA", "cyberpunk2077", "work", 0),
            (2_000_000, "1440", "ANY", "cyberpunk2077", "game", 1_300_000),
        )
        for budget, resolution, vendor, game, mode, minimum in cases:
            with self.subTest(budget=budget, resolution=resolution, vendor=vendor, mode=mode, minimum=minimum):
                request = {"budget": budget, "budget_min": minimum, "resolution": resolution,
                           "gpu_pref": vendor, "game": game, "mode": mode, "refresh": 144,
                           "work_profile": "video_4k"}
                candidates = {tier: server.build_tier_candidates(request, tier, random.Random(42))
                              for tier in ("low", "mid", "high")}
                selected = server.select_ordered_tier_plans(candidates)
                self.assertTrue(all(selected.values()), "Expected three feasible tiers for this catalog fixture")
                values = list(selected.values())
                for lower, upper in zip(values, values[1:]):
                    self.assertGreater(server.tier_upgrade_quality(lower, upper), 0)
                for result in values:
                    parts = result["parts"]
                    self.assertGreaterEqual(result["totalPrice"], minimum)
                    self.assertLessEqual(result["totalPrice"], budget)
                    self.assertEqual(parts["cpu"]["socket"], parts["mb"]["socket"])
                    self.assertEqual(parts["ram"]["type"], parts["mb"]["ram_type"])
                    self.assertGreaterEqual(parts["psu"]["watt"], server.recommended_psu_watt(parts["cpu"], parts["gpu"]))
                    if vendor != "ANY":
                        self.assertEqual(vendor, parts["gpu"]["vendor"])
                # Candidate lists must preserve genuinely different CPUs/GPUs.
                self.assertGreater(len({(p["parts"]["cpu"]["id"], p["parts"]["gpu"]["id"])
                                        for p in candidates["mid"]}), 3)


if __name__ == "__main__":
    unittest.main()
