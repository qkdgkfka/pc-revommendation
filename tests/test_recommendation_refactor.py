"""Specification-first recommendations, using a fixed catalog without retail I/O."""
import copy
import random
import unittest
from unittest.mock import patch

from pcbuilder import recommendation as rec, database, pricing, fps
from server_catalogs import CATALOGS


class RecommendationRefactorTests(unittest.TestCase):
    def setUp(self):
        for module, name in ((database, "db_lookup_price"), (database, "db_lookup_price_info"), (fps, "db_lookup_benchmarks")):
            guard = patch.object(module, name, return_value=None)
            guard.start()
            self.addCleanup(guard.stop)
        self.inventory = copy.deepcopy({k: CATALOGS[k] for k in ("cpu", "gpu", "ram", "mb", "psu", "storage")})

    def select(self, payload, inventory=None):
        shared = {}
        candidates = {
            tier: rec.build_tier_candidates(payload, tier, random.Random(1),
                                             shared_fps=shared, inventory=inventory or self.inventory)
            for tier in ("low", "mid", "high")
        }
        return rec.complete_recommendation_tiers(
            rec.select_ordered_tier_plans(candidates), candidates,
            rec.RecommendationRequest.from_payload(payload))

    def test_unlimited_4k_high_refresh_has_three_distinct_high_end_gpu_levels(self):
        inventory = copy.deepcopy(self.inventory)
        inventory["gpu"] = [p for p in inventory["gpu"] if p["id"] in
                            {"gpu_rtx5060", "gpu_rtx5070", "gpu_rtx5070ti", "gpu_rtx5080", "gpu_rtx5090"}]
        result = self.select({"budget_mode": "unlimited", "budget": 300000,
                              "resolution": "2160", "refresh": 144, "game": "cyberpunk2077"}, inventory)
        self.assertEqual(["gpu_rtx5070ti", "gpu_rtx5080", "gpu_rtx5090"],
                         [result[t].get("parts", {}).get("gpu", {}).get("id") for t in result])
        for plan in result.values():
            self.assertEqual("unlimited", plan["budget_status"])
            self.assertEqual(0, plan["budget_overrun"])
            self.assertEqual(144, plan["fps"]["target_fps"])
            self.assertTrue(plan["compatibility"]["compatible"])
            self.assertGreaterEqual(plan["parts"]["psu"]["watt"], plan["debug"]["recommended_psu_watt"])

    def test_unlimited_ignores_stale_budget_fields_and_serializes_no_cap(self):
        request = rec.RecommendationRequest.from_payload({"budget_mode": "unlimited", "budget_max": 300000, "budget_min": 200000})
        self.assertIsNone(request.as_payload()["budget_max"])
        self.assertEqual("unlimited", request.as_payload().get("budget_mode"))
        self.assertEqual(request, rec.RecommendationRequest.from_payload(request.as_payload()))

    def test_soft_budget_can_return_a_compatible_build_just_above_target(self):
        inventory = {k: [rows[0]] for k, rows in self.inventory.items()}
        inventory["gpu"] = [next(p for p in self.inventory["gpu"] if p["id"] == "gpu_rtx4060")]
        inventory["ram"] = [next(p for p in self.inventory["ram"] if p["id"] == "ram_32_ddr4")]
        total = sum(rows[0]["price"] for rows in inventory.values())
        candidates = rec.build_tier_candidates({"budget_max": total - 10000}, "low", random.Random(1), inventory=inventory)
        self.assertTrue(candidates)
        self.assertEqual(10000, candidates[0]["budget_overrun"])
        self.assertEqual("over_budget", candidates[0]["budget_status"])

    def test_budget_minimum_does_not_force_unnecessary_spending(self):
        inventory = {k: [rows[0]] for k, rows in self.inventory.items()}
        inventory["gpu"] = [next(p for p in self.inventory["gpu"] if p["id"] == "gpu_rtx4060")]
        candidates = rec.build_tier_candidates({"budget_min": 2000000, "budget_max": 3000000}, "low", random.Random(1), inventory=inventory)
        self.assertTrue(candidates)
        self.assertLess(candidates[0]["totalPrice"], 2000000)

    def test_no_duplicate_cards_when_only_one_gpu_model_is_available(self):
        inventory = copy.deepcopy(self.inventory)
        inventory["gpu"] = [next(p for p in inventory["gpu"] if p["id"] == "gpu_rtx5070ti")]
        result = self.select({"budget_mode": "unlimited", "resolution": "2160", "refresh": 144}, inventory)
        populated = [p for p in result.values() if p.get("parts")]
        self.assertEqual(1, len(populated))
        self.assertFalse(any(p.get("same_configuration") for p in result.values()))

    def test_retail_variants_cannot_crowd_other_gpu_models_out_of_shortlist(self):
        inventory = copy.deepcopy(self.inventory)
        gpu = next(p for p in inventory["gpu"] if p["id"] == "gpu_rtx5070ti")
        inventory["gpu"] = [dict(gpu, id=f"retail_{i}", name=f"MSI RTX 5070 Ti VENTUS {i}", performance_ref_id=gpu["id"]) for i in range(30)] + [
            p for p in inventory["gpu"] if p["id"] in {"gpu_rtx5080", "gpu_rtx5090"}]
        candidates = rec.build_tier_candidates({"budget_mode": "unlimited", "resolution": "2160", "refresh": 144},
                                                "low", random.Random(1), inventory=inventory)
        ids = {p["parts"]["gpu"].get("performance_ref_id") or p["parts"]["gpu"]["id"] for p in candidates}
        self.assertTrue({"gpu_rtx5070ti", "gpu_rtx5080", "gpu_rtx5090"}.issubset(ids))

    def test_game_power_score_favors_gpu_upgrade_over_equal_cpu_upgrade(self):
        base = {"gpu": {"perf_2160": 50}, "cpu": {"perf": 70}, "ram": {"gb": 32}, "storage": {"capacity": 1000}}
        gpu = copy.deepcopy(base)
        gpu["gpu"]["perf_2160"] += 10
        cpu = copy.deepcopy(base)
        cpu["cpu"]["perf"] += 10
        start = rec.build_power_score(base, "2160")
        self.assertGreater(rec.build_power_score(gpu, "2160") - start,
                           3 * (rec.build_power_score(cpu, "2160") - start))

    def test_unlimited_price_refresh_never_marks_build_over_budget(self):
        plan = {"budget_mode": "unlimited", "tierBudget": 1500000, "budget_max": None,
                "parts": {"gpu": {"price": 5000000}}}
        pricing.recompute_plan_total(plan)
        self.assertEqual("unlimited", plan["budget_status"])
        self.assertEqual(0, plan["budget_overrun"])

    def test_unlimited_8k_editing_respects_memory_and_storage_requirements(self):
        result = self.select({"budget_mode": "unlimited", "mode": "work", "work_profile": "video_8k"})
        for plan in result.values():
            if plan.get("parts"):
                self.assertGreaterEqual(plan["parts"]["ram"]["gb"], 64)
                self.assertGreaterEqual(plan["parts"]["storage"]["capacity"], 2000)
                self.assertGreaterEqual(plan["debug"]["ordering_metrics"]["cpu"], 82)
                norms = rec.work_component_norms(plan["parts"]["gpu"], plan["parts"]["cpu"], plan["parts"]["ram"])
                self.assertGreaterEqual(norms["gpu"] * 100, 78)

    def test_cheaper_sku_of_same_gpu_remains_available_for_soft_budget(self):
        inventory = {k: [copy.deepcopy(rows[0])] for k, rows in self.inventory.items()}
        gpu = next(p for p in self.inventory["gpu"] if p["id"] == "gpu_rtx4060")
        inventory["gpu"] = [dict(gpu, id="cheap", price=150000), dict(gpu, id="expensive", price=450000)]
        for kind, rows in inventory.items():
            if kind != "gpu":
                rows[0]["price"] = 198000
        candidates = rec.build_tier_candidates({"budget_max": 1000000, "resolution": "2160", "refresh": 144},
                                                "low", random.Random(1), inventory=inventory)
        self.assertTrue(candidates)
        self.assertEqual(1140000, candidates[0]["totalPrice"])
        self.assertEqual("cheap", candidates[0]["parts"]["gpu"]["id"])

    def test_unlimited_capped_game_preserves_real_target_and_vendor_preference(self):
        result = self.select({"budget_mode": "unlimited", "resolution": "1440", "refresh": 144,
                              "game": "genshin_impact", "gpu_pref": "AMD"})
        self.assertTrue(any(p.get("parts") for p in result.values()))
        for plan in result.values():
            if plan.get("parts"):
                self.assertEqual("AMD", plan["parts"]["gpu"]["vendor"])
                self.assertEqual(60, plan["fps"]["target_fps"])

    def test_no_matching_maker_stays_unavailable_in_unlimited_mode(self):
        result = self.select({"budget_mode": "unlimited", "gpu_brands": ["zotac"]})
        self.assertFalse(any(p.get("parts") for p in result.values()))


if __name__ == "__main__":
    unittest.main()
