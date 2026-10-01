from rendering_fixture import install_rendering_fixture
import unittest
from unittest.mock import patch
import math
from rendering_calibration import fg_prediction,calibration_data
import game_benchmarks as bench

class CalibrationTests(unittest.TestCase):
    def setUp(self):
        install_rendering_fixture(self)

    def test_each_fg_pair_reconstructs_its_observation(self):
        data=calibration_data()
        for row in data["fg_calibration"]:
            with self.subTest(game=row["game"],gpu=row["gpu_id"],factor=row["factor"]):
                only=dict(data,fg_calibration=[row])
                with patch("rendering_calibration.calibration_data",return_value=only):
                    result=fg_prediction(row["base_fps"],{"id":row["gpu_id"]},row["game"],
                                         row["resolution"],row["technology"],row["factor"])
                self.assertAlmostEqual(result["avg_fps"],row["display_fps"],places=1)
                self.assertGreater(result["overhead_ms"],0)

    def test_absent_technology_never_borrows_other_vendor_measurements(self):
        data=dict(calibration_data(),fg_calibration=[r for r in calibration_data()["fg_calibration"] if r["technology"]=="DLSS"])
        with patch("rendering_calibration.calibration_data",return_value=data):
            self.assertIsNone(fg_prediction(60,{"id":"gpu_rx7800xt"},"starfield","2160","FSR",2))

    def test_game_curve_uses_measured_neighbors(self):
        self.assertTrue(hasattr(bench,"interpolated_gpu_observation"))
        rows=bench.load_measurements()
        anchor=dict(rows[0],gpu_id="a",resolution="1440",avg_fps=40)
        other=dict(anchor,gpu_id="b",avg_fps=60)
        catalogs={"a":{"perf_1440":40},"b":{"perf_1440":80}}
        value,used=bench.interpolated_gpu_observation(anchor,math.sqrt(40*80),[anchor,other],catalogs)
        self.assertAlmostEqual(value,math.sqrt(40*60))
        self.assertEqual(len(used),2)
        unrelated=dict(other,source_url="https://different-review.test/")
        self.assertIsNone(bench.interpolated_gpu_observation(anchor,60,[anchor,unrelated],catalogs))
        self.assertIsNone(bench.interpolated_gpu_observation(anchor,100,[anchor,other],catalogs))

    def test_heldout_game_fg_error_improves_on_fixed_multiplier(self):
        data=calibration_data()
        old_errors=[];new_errors=[]
        for row in data["fg_calibration"]:
            if row["factor"] not in (2,4):continue
            reduced=dict(data,fg_calibration=[r for r in data["fg_calibration"] if r["game"]!=row["game"]])
            with patch("rendering_calibration.calibration_data",return_value=reduced):
                result=fg_prediction(row["base_fps"],{"id":row["gpu_id"]},row["game"],
                                     row["resolution"],row["technology"],row["factor"])
            if result:
                old_errors.append(abs(row["base_fps"]*.9*row["factor"]/row["display_fps"]-1))
                new_errors.append(abs(result["avg_fps"]/row["display_fps"]-1))
        self.assertGreaterEqual(len(new_errors),18)
        self.assertLess(sum(new_errors),sum(old_errors))

    def test_rtx50_factors_keep_consistent_rendering_costs(self):
        from server_catalogs import GAME_OPTIONS
        for game in GAME_OPTIONS:
            for base in (30,60,144):
                two=fg_prediction(base,{"id":"gpu_rtx5070"},game["id"],"1440","DLSS",2)
                four=fg_prediction(base,{"id":"gpu_rtx5070"},game["id"],"1440","DLSS",4)
                self.assertLess(four["render_fps"],two["render_fps"],game["id"])
                self.assertLess(four["avg_fps"],2*two["avg_fps"],game["id"])
