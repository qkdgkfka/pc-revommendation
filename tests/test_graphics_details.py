import unittest
from unittest.mock import patch
from graphics_estimates import graphics_scenarios
from game_benchmarks import load_measurements
from server_fixed import estimate_fps_bundle
from server_catalogs import GPU_CATALOG,CPU_CATALOG

class GraphicsDetailsTests(unittest.TestCase):
    def setUp(self):
        self.gpu=next(g for g in GPU_CATALOG if g["id"]=="gpu_rtx5070")
        self.cpu=next(c for c in CPU_CATALOG if c["id"]=="cpu_r7_9800x3d")
        self.fps=estimate_fps_bundle(self.gpu,self.cpu,{"gb":32},"expedition33","1440",144,"mid",["rpg"])

    def modes(self,gpu=None):
        return {r["id"]:r for r in graphics_scenarios(gpu or self.gpu,self.cpu,
            "expedition33","1440",self.fps,lambda row:47.6)}

    def test_reviewed_native_and_dlss_remain_distinct(self):
        rows=self.modes()
        self.assertEqual(self.fps["fps_by_option"]["high"],47.6)
        self.assertEqual(rows["upscale"]["avg_fps"],74.0)
        self.assertEqual(rows["upscale"]["method"],"mode_measurement")
        self.assertEqual(rows["mfg4"]["method"],"workload_estimate")
        self.assertLess(rows["fg2"]["render_fps"],rows["fg2"]["avg_fps"])
        self.assertEqual(len([r for r in rows if r=="upscale"]),1)

    def test_unsupported_hardware_does_not_get_frame_generation(self):
        rows=self.modes({"id":"gpu_rtx3060","name":"RTX 3060"})
        self.assertNotIn("fg2",rows)
        self.assertNotIn("mfg4",rows)
        self.assertEqual(rows["upscale"]["method"],"mode_calibrated_estimate")

    def test_unknown_game_support_fails_closed(self):
        with patch("graphics_estimates.feature_support",return_value={"expedition33":{"dlss":False,"fg":False,"mfg":False}}):
            rows=self.modes()
        self.assertNotIn("upscale",rows)
        self.assertNotIn("fg2",rows)

    def test_closest_measured_configuration_wins(self):
        base={"game":"expedition33","cpu_id":self.cpu["id"],"gpu_id":self.gpu["id"],"preset":"high",
              "mode":"upscale","label":"DLSS Quality","generated":False,"source_url":"https://example.com/review","note":""}
        rows=[dict(base,resolution="2160",avg_fps=35),dict(base,resolution="1440",avg_fps=74)]
        with patch("graphics_estimates.graphics_measurements",return_value=tuple(rows)):
            self.assertEqual(self.modes()["upscale"]["avg_fps"],74)

    def test_recommended_retail_sku_keeps_fps_reference_on_import(self):
        from server_fixed import summarize_part,resolve_fps_part
        from unittest.mock import patch
        retail={**self.gpu,"id":"compuzone_gpu_example","performance_ref_id":self.gpu["id"]}
        with patch("server_fixed.db_lookup_price_info",return_value=None):
            response=summarize_part(retail,"gpu")
        resolved,identifier=resolve_fps_part("gpu",response)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["id"],self.gpu["id"])
        self.assertEqual(identifier,"compuzone_gpu_example")
