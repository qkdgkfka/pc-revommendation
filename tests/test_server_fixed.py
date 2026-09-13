import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "server_fixed.py"
SPEC = importlib.util.spec_from_file_location("pc_builder_server", MODULE_PATH)
server = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = server
SPEC.loader.exec_module(server)


def catalog_part(part_type, part_id):
    return next(part for part in server.CATALOGS[part_type] if part["id"] == part_id)


class FpsEstimatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.load_db_cache()
        cls.gpu = catalog_part("gpu", "gpu_rtx5070")
        cls.cpu = catalog_part("cpu", "cpu_r5_7600")
        cls.ram = catalog_part("ram", "ram_32_ddr5")

    def test_reference_game_benchmark_is_used_for_rtx_5070(self):
        fps = server.estimate_fps_bundle(
            self.gpu, self.cpu, self.ram,
            "cyberpunk2077", "1440", 60, "mid", ["rpg"],
        )
        self.assertEqual("tpu_reference_calibrated", fps["fps_source"])
        self.assertAlmostEqual(104.4, fps["fps_by_option"]["high"], places=1)
        self.assertIn("techpowerup.com", fps["benchmark_source_url"])

    def test_frame_capped_game_uses_effective_target(self):
        fps = server.estimate_fps_bundle(
            self.gpu, self.cpu, self.ram,
            "elden_ring", "1440", 144, "mid", ["rpg"],
        )
        self.assertEqual(60.0, fps["frame_cap"])
        self.assertEqual(60.0, fps["fps_by_option"]["high"])
        self.assertEqual(60.0, fps["target_fps"])
        self.assertEqual("목표 성능 충족", fps["capacity_label"])

    def test_target_coverage_is_not_marked_insufficient_for_expensive_build(self):
        metrics = server.value_metrics(104.4, 2_500_000, 60, 79.3, 48)
        self.assertLess(metrics["score"], 5.0)
        self.assertEqual("목표 성능 여유", metrics["capacity_label"])
        self.assertGreater(metrics["target_coverage"], 1.0)

    def test_direct_spec_fps_api_uses_same_engine(self):
        response = server.fps_estimate_response({
            "gpu": "gpu_rtx5070",
            "cpu": "cpu_r5_7600",
            "ram": "ram_32_ddr5",
            "game": "cyberpunk2077",
            "resolution": "1440",
            "refresh": 60,
            "tier": "mid",
        })
        self.assertEqual("gpu_rtx5070", response["input"]["gpu"])
        self.assertEqual("tpu_reference_calibrated", response["fps"]["fps_source"])
        self.assertAlmostEqual(104.4, response["fps"]["fps_by_option"]["high"], places=1)


class PlanTotalTests(unittest.TestCase):
    def test_total_is_derived_from_part_prices_and_keeps_capacity_context(self):
        plan = {
            "parts": {
                "cpu": {"price": 200_000},
                "gpu": {"price": 900_000},
                "ram": {"price": 130_000},
                "mb": {"price": 150_000},
                "storage": {"price": 120_000},
                "psu": {"price": 100_000},
            },
            "fps": {
                "fps_by_option": {"high": 90},
                "low1_by_option": {"high": 70},
                "target_fps": 60,
                "target_low1_fps": 48,
            },
        }
        server.recompute_plan_total(plan)
        self.assertEqual(1_600_000, plan["totalPrice"])
        self.assertEqual("목표 성능 여유", plan["fps"]["capacity_label"])

    def test_case_can_be_left_unselected_when_importing_recommendation(self):
        self.assertTrue(any(part["id"] == "case_none" and part["price"] == 0 for part in server.CASE_CATALOG))


if __name__ == "__main__":
    unittest.main()
