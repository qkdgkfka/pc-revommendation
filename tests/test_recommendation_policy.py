from backend_patch import patch_backend
import unittest
from recommendation_policy import cpu_allowed, cpu_preference, gpu_product_band, storage_preference

class PolicyTests(unittest.TestCase):
    def test_intel_generation_gate_and_unknown_models(self):
        for name in ("Intel i5-12400F","Intel i7-10700","Intel 7600","Intel Xeon E5-2690"):
            self.assertFalse(cpu_allowed({"name":name,"vendor":"Intel"}),name)
        for name in ("Intel i5-13400F","Intel i7-14700K","Intel Core Ultra 5 245K"):
            self.assertTrue(cpu_allowed({"name":name,"vendor":"Intel"}),name)
        self.assertTrue(cpu_allowed({"name":"AMD Ryzen 5 5600","vendor":"AMD"}))
        self.assertFalse(cpu_allowed({"name":"Intel 7600","vendor":"AMD","performance_ref_id":"cpu_r5_7600"}))

    def test_preference_is_mode_specific_and_modern_intel(self):
        amd={"name":"AMD Ryzen 7 7800X3D","vendor":"AMD"}
        old={"name":"Intel i5-13400F","vendor":"Intel"}
        new={"name":"Intel Core Ultra 5 245K","vendor":"Intel"}
        self.assertGreater(cpu_preference(amd,"game"),cpu_preference(new,"game"))
        self.assertGreater(cpu_preference(new,"game"),cpu_preference(old,"game"))
        self.assertEqual(cpu_preference(amd,"work"),0)

    def test_gpu_board_series_not_chip_tier_or_price(self):
        self.assertEqual(gpu_product_band({"name":"MSI RTX 5060 VENTUS 2X"}),"preferred")
        self.assertEqual(gpu_product_band({"name":"ASUS RTX 5090 ROG STRIX"}),"premium")
        self.assertEqual(gpu_product_band({"name":"ASUS RTX 4060 PHOENIX"}),"entry")
        self.assertEqual(gpu_product_band({"name":"Unknown RTX 5070","price":999999}),"unknown")

    def test_storage_form_factor_and_interface(self):
        self.assertGreater(storage_preference({"name":"Samsung 990 PRO M.2 NVMe"}),storage_preference({"name":"WD SA510 SATA"}))
        self.assertLess(storage_preference({"name":"M.2 SATA SSD"}),storage_preference({"name":"M.2 NVMe SSD"}))

    def test_actual_target_is_shared_and_game_cap_respected(self):
        import server_fixed as s
        self.assertEqual([144.0]*3,[s.target_fps_for_game(t,144,"cyberpunk2077") for t in ("low","mid","high")])
        self.assertEqual([60.0]*3,[s.target_fps_for_game(t,144,"genshin_impact") for t in ("low","mid","high")])

    def test_explicit_budget_ceiling_is_not_overridden_by_old_budget(self):
        from server_fixed import RecommendationRequest
        r=RecommendationRequest.from_payload({"budget":3000000,"budget_max":1500000})
        self.assertEqual(r.budget_max,1500000)

    def test_all_tiers_filter_old_intel_without_mutating_catalog(self):
        import server_fixed as s
        original=list(s.CPU_CATALOG)
        for tier in ("low","mid","high"):
            cpus=s.tier_component_pools(tier,"1440",144,"ANY")[0]
            self.assertTrue(all(cpu_allowed(p) for p in cpus))
            self.assertTrue(any("ultra" in p["name"].lower() for p in cpus))
        self.assertEqual(original,s.CPU_CATALOG)

    def test_retail_cpu_vendor_is_not_inferred_from_model_number_alone(self):
        import server_fixed as s
        self.assertIsNone(s.performance_reference_for_danawa_product("cpu","Intel 7600"))

    def test_target_satisfaction_beats_brand_preference(self):
        from recommendation_policy import objective_score
        parts={"cpu":{"name":"AMD Ryzen 7 7800X3D"},"gpu":{"name":"RTX 5070 VENTUS"},"storage":{"name":"M.2 NVMe"}}
        intel={**parts,"cpu":{"name":"Intel i5-13400F"}}
        self.assertGreater(objective_score(.8,1.0,intel,"game"),objective_score(.8,59/60,parts,"game"))
        self.assertGreater(objective_score(.8,1.0,parts,"game"),objective_score(.8,1.0,intel,"game"))

    def test_impossible_budget_skips_expensive_fps_search(self):
        import random
        from unittest.mock import patch
        import server_fixed as s
        with patch_backend(s,"cached_part_price",return_value=100000), patch_backend(s,"estimate_fps_bundle",side_effect=AssertionError("must not evaluate")):
            self.assertEqual(s.build_tier_candidates({"budget":300000},"low",random.Random(1)),[])
