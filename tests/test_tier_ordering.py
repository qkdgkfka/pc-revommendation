import unittest

import server_fixed as server
from steam_hardware import gpu_key, steam_gpu_share


def plan(name, perf, score=1, price=1_000_000, fps=60, budget=1_000_000):
    return {
        "parts": {"gpu": {"id": name, "name": name, "price": price, "perf_1080": perf, "perf_1440": perf}},
        "totalPrice": price, "budget_max": budget,
        "fps": {"fps_by_option": {"high": fps}},
        "debug": {"candidate_score": score, "power_score": perf},
    }


class TierOrderingTests(unittest.TestCase):
    def test_rejects_higher_scoring_duplicate_or_reversed_gpu(self):
        low = plan("RTX 3060", 45)
        reversed_low = plan("RTX 4080", 95, score=100)
        mid = plan("RTX 4060", 55)
        high = plan("RTX 4070", 75)
        selected = server.select_ordered_tier_plans({
            "low": [reversed_low, low], "mid": [low, mid], "high": [mid, high],
        })
        self.assertEqual([45, 55, 75], [selected[t]["parts"]["gpu"]["perf_1080"] for t in ("low", "mid", "high")])

    def test_same_gpu_different_board_partner_is_not_an_upgrade(self):
        selected = server.select_ordered_tier_plans({
            "low": [plan("MSI RTX 4060", 50)],
            "mid": [plan("ASUS RTX 4060", 51)],
            "high": [plan("RTX 4070", 70)],
        })
        self.assertEqual(2, sum(bool(row) for row in selected.values()))

    def test_budget_is_a_soft_target_and_keeps_higher_tier_visible(self):
        selected = server.select_ordered_tier_plans({
            "low": [plan("RTX 3060", 45, price=900000)],
            "mid": [plan("RTX 4060", 55, price=1000000)],
            "high": [plan("RTX 4080", 90, score=100, price=1100001), plan("RTX 4070", 75, price=1100000)],
        })
        self.assertEqual(1100001, selected["high"]["totalPrice"])

    def test_cpu_bottleneck_cannot_invert_displayed_fps(self):
        selected = server.select_ordered_tier_plans({
            "low": [plan("RTX 3060", 45, fps=100)],
            "mid": [plan("RTX 4060", 55, fps=80)],
            "high": [plan("RTX 4070", 75, fps=110)],
        })
        self.assertLess(sum(bool(row) for row in selected.values()), 3)

    def test_cost_per_frame_recalculates_after_price_update(self):
        row = plan("RTX 4060", 55, price=1000000, fps=100)
        server.recompute_plan_total(row)
        self.assertEqual(10000, row["cost_per_frame"])
        row["parts"]["gpu"]["price"] = 1100000
        server.recompute_plan_total(row)
        self.assertEqual(11000, row["cost_per_frame"])
        self.assertEqual("over_budget", row["budget_status"])
        self.assertEqual(100000, row["budget_overrun"])
        row["fps"]["fps_by_option"]["high"] = 0
        server.recompute_plan_total(row)
        self.assertIsNone(row["cost_per_frame"])

    def test_tier_targets_remain_monotonic_soft_targets(self):
        targets = [server.tier_budget_for_user(1000000, tier) for tier in ("low", "mid", "high")]
        self.assertEqual(sorted(targets), targets)
        self.assertLess(targets[0], targets[1])
        self.assertLessEqual(targets[1], targets[2])
        self.assertEqual(1000000, targets[2])

    def test_steam_laptop_rows_do_not_count_as_desktop_gpu_popularity(self):
        self.assertEqual("", gpu_key("NVIDIA GeForce RTX 4060 Laptop GPU"))
        self.assertGreater(steam_gpu_share("RTX 3060"), 0)
        self.assertGreater(steam_gpu_share("RTX 4060"), 0)


if __name__ == "__main__":
    unittest.main()
