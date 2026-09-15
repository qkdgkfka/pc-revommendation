import random
import unittest
from unittest.mock import patch

import server_fixed as server
from component_compatibility import platform_compatibility


def component(kind, identifier):
    return next(p for p in server.CATALOGS[kind] if p["id"] == identifier)


class PlatformTests(unittest.TestCase):
    def setUp(self):
        self.cpu = component("cpu", "cpu_r7_9800x3d")
        self.board = component("mb", "mb_b650")
        self.ram = component("ram", "ram_32_ddr5")

    def test_matching_platform_requires_bios_verification(self):
        result = platform_compatibility(self.cpu, self.board, self.ram)
        self.assertTrue(result["compatible"])
        self.assertEqual("bios_check_required", result["status"])
        self.assertTrue(result["warnings"])

    def test_socket_match_does_not_override_wrong_chipset(self):
        board = {**self.board, "name": "Intel B760", "socket": "AM5"}
        self.assertFalse(platform_compatibility(self.cpu, board, self.ram)["compatible"])

    def test_wrong_socket_ram_and_unidentified_chipset_are_rejected(self):
        for board, ram in [
            ({**self.board, "socket": "AM4"}, self.ram),
            (self.board, {**self.ram, "type": "DDR4"}),
            ({**self.board, "name": "Unspecified motherboard"}, self.ram),
            ({**self.board, "supported_cpu_ids": ["cpu_r5_7600"]}, self.ram),
        ]:
            with self.subTest(board=board, ram=ram):
                self.assertFalse(platform_compatibility(self.cpu, board, ram)["compatible"])

    def test_cpu_generation_and_intel_memory_variants(self):
        cpu = component("cpu", "cpu_i5_14400f")
        board = component("mb", "mb_b760_ddr4")
        ram = {"type": "DDR4", "gb": 32}
        self.assertTrue(platform_compatibility(cpu, board, ram)["compatible"])
        self.assertFalse(platform_compatibility({**cpu, "name": "Intel Core i7-11700", "id": "cpu_i7_11700"}, board, ram)["compatible"])

    def test_empty_compatibility_pool_never_relaxes_to_bad_parts(self):
        self.assertEqual([], server.filter_compatible_mb([self.cpu], [component("mb", "mb_b550")]))
        self.assertEqual([], server.filter_compatible_ram([self.board], [{"type": "DDR4"}]))

    def test_all_catalog_desktop_cpus_have_a_compatible_board(self):
        for cpu in server.CPU_CATALOG:
            if server.is_desktop_cpu(cpu):
                with self.subTest(cpu=cpu["id"]):
                    self.assertTrue(any(platform_compatibility(cpu, board)["compatible"] for board in server.MB_CATALOG))


class RecommendationExclusionsTests(unittest.TestCase):
    def test_all_rtx30_spellings_are_excluded_only_from_recommendations(self):
        for field, value in [("name", "MSI RTX 3060 Ti"), ("id", "gpu_rtx3090"),
                             ("performance_ref_id", "gpu_rtx3080ti"), ("product_name", "ASUS RTX-3070")]:
            self.assertFalse(server.is_recommendable_gpu({field: value}))
        for name in ("RTX 4060", "RTX 5070", "AMD RX 7900 XT"):
            self.assertTrue(server.is_recommendable_gpu({"name": name}))
        for tier in ("low", "mid", "high"):
            self.assertTrue(all(server.is_recommendable_gpu(p) for p in server.tier_component_pools(tier, "1440", 144, "ANY")[1]))

    def test_retail_only_rtx30_inventory_never_reenters_fallback(self):
        gpu = component("gpu", "gpu_rtx3060")
        with patch.object(server, "db_lookup_price", return_value=None):
            for tier in ("low", "mid", "high"):
                result = server.build_tier_candidates({"budget": 1500000, "gpu_market_prices": {gpu["id"]: gpu}}, tier, random.Random(1))
                self.assertTrue(result)
                self.assertTrue(all(server.is_recommendable_gpu(plan["parts"]["gpu"]) for plan in result))
                self.assertTrue(all(plan["compatibility"]["compatible"] for plan in result))

    def test_shared_fps_evaluation_reuses_measurements_across_tiers(self):
        request = server.RecommendationRequest.from_payload({"budget": 1500000, "game": "cyberpunk2077"})
        shared = {}
        gpu = component("gpu", "gpu_rtx5070")
        cpu = component("cpu", "cpu_r5_7600")
        ram = component("ram", "ram_32_ddr5")
        with patch.object(server, "estimate_fps_bundle", wraps=server.estimate_fps_bundle) as estimate:
            results = [server.CandidateEvaluationCache(request, tier, 1500000, {}, [], [], shared).fps_for(gpu, cpu, ram)
                       for tier in ("low", "mid", "high")]
        self.assertEqual(1, estimate.call_count)
        self.assertEqual(results[0]["fps_by_option"], results[2]["fps_by_option"])
        self.assertLess(results[0]["target_fps"], results[2]["target_fps"])


if __name__ == "__main__":
    unittest.main()
