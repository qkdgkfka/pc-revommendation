from rendering_fixture import install_rendering_fixture
import unittest
from unittest.mock import patch
from graphics_estimates import graphics_scenarios
from game_benchmarks import load_measurements
from server_fixed import estimate_fps_bundle
from server_catalogs import GPU_CATALOG,CPU_CATALOG

class GraphicsDetailsTests(unittest.TestCase):
    def setUp(self):
        install_rendering_fixture(self)
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
        with patch("pcbuilder.database.db_lookup_price_info",return_value=None):
            response=summarize_part(retail,"gpu")
        resolved,identifier=resolve_fps_part("gpu",response)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["id"],self.gpu["id"])
        self.assertEqual(identifier,"compuzone_gpu_example")

    def test_mfg_has_more_processing_cost_than_fg(self):
        rows=self.modes()
        self.assertLess(rows["mfg4"]["render_fps"],rows["fg2"]["render_fps"])
        self.assertLess(rows["mfg4"]["avg_fps"],2*rows["fg2"]["avg_fps"])

    def test_fg_gain_changes_with_base_frame_time(self):
        with patch("graphics_estimates.graphics_measurements",return_value=()):
            slow_modes=self.modes()
            slow=slow_modes["fg2"]
            self.fps["fps_by_option"]["high"] *= 3
            fast_modes=self.modes()
            fast=fast_modes["fg2"]
        self.assertNotAlmostEqual(slow["avg_fps"]/slow_modes["upscale"]["avg_fps"],
                                  fast["avg_fps"]/fast_modes["upscale"]["avg_fps"],places=2)

    def test_removed_fg_explanation_is_not_rendered(self):
        from pathlib import Path
        self.assertNotIn("FG는 생성 프레임을 포함한 화면 표시 FPS입니다.",
                         (Path(__file__).resolve().parents[1] / "src/components/GraphicsDetails.jsx").read_text(encoding="utf8"))

    def test_amd_uses_own_fsr_calibration(self):
        fps=dict(self.fps,fps_by_option=dict(self.fps["fps_by_option"],high=40))
        gpu={"id":"gpu_rx7800xt","name":"AMD Radeon RX 7800 XT","perf_2160":41}
        rows={r["id"]:r for r in graphics_scenarios(gpu,self.cpu,"starfield","2160",fps,lambda r:40)}
        self.assertIn("FSR",rows["upscale"]["label"])
        self.assertIn("FSR",rows["fg2"]["label"])
        self.assertNotIn("mfg4",rows)
        self.assertTrue(rows["fg2"]["calibration_sources"])
        self.assertFalse(any("DLSS" in r["label"] for r in rows.values()))

    def test_unknown_fg_factor_does_not_become_an_estimate(self):
        base={"game":"expedition33","cpu_id":self.cpu["id"],"gpu_id":self.gpu["id"],
              "preset":"high","resolution":"1440","mode":"upscale_fg_measured","label":"unknown FG",
              "generated":True,"avg_fps":900,"source_url":"https://example.com","note":""}
        with patch("graphics_estimates.graphics_measurements",return_value=(base,)):
            rows=self.modes()
        self.assertNotIn("upscale_fg_measured",rows)

    def test_upscaling_respects_cpu_limit(self):
        self.fps["bottleneck"]={"cpu_fps_ceiling":50,"cpu_penalty_pct":70}
        with patch("graphics_estimates.graphics_measurements",return_value=()):
            rows=self.modes()
        self.assertLessEqual(rows["upscale"]["avg_fps"],50)
