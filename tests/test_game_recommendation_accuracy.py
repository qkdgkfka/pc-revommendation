"""Game performance must drive selection before generic catalog targets."""
import unittest
import math
import random
from unittest.mock import patch
from pcbuilder import recommendation as rec
from pcbuilder import database, fps
from server_catalogs import CATALOGS, GAME_OPTIONS

from recommendation_policy import gaming_objective


class GameRecommendationAccuracyTests(unittest.TestCase):
    def score(self, gpu_perf=100, fps_ratio=1, low1_ratio=1, **overrides):
        arguments = dict(gpu_perf=gpu_perf, gpu_target=100, fps_ratio=fps_ratio,
                         low1_ratio=low1_ratio, budget_fit=1, unlimited=False,
                         ram_gb=32, cpu_loss=0, parts={'cpu': {}, 'gpu': {}, 'storage': {}})
        arguments.update(overrides)
        return gaming_objective(**arguments)

    def test_meeting_game_target_beats_matching_generic_gpu_index(self):
        # A game's performance order need not match the all-game GPU index.
        self.assertGreater(self.score(gpu_perf=140), self.score(fps_ratio=.8, low1_ratio=.8))

    def test_frame_time_stability_beats_generic_index_when_average_ties(self):
        self.assertGreater(self.score(gpu_perf=140), self.score(low1_ratio=.6))

    def test_more_fps_never_lowers_game_score(self):
        scores = [self.score(fps_ratio=value, low1_ratio=value) for value in (.4, .8, 1, 2)]
        self.assertEqual(sorted(scores), scores)
        self.assertEqual(scores[-2], scores[-1], 'FPS above the target has diminishing utility')

    def test_capped_games_retain_hardware_tier_and_budget_preferences(self):
        self.assertGreater(self.score(), self.score(gpu_perf=60))
        self.assertGreater(self.score(), self.score(budget_fit=.7))

    def test_shortlist_retains_game_specialists_and_affordable_value(self):
        parts = [dict(id=name, name=name, price=price) for name, price in
                 [('generic', 400000), ('specialist', 600000), ('value', 200000), ('unaffordable', 2000000)]]
        rates = dict(generic=70, specialist=120, value=65, unaffordable=300)
        calls = []
        def evaluate(part):
            calls.append(part['id'])
            return {'high_setting_avg_fps': rates[part['id']],
                    'high_setting_low1_fps': rates[part['id']] * .8}
        prices = {('gpu', part['id']): part['price'] for part in parts}
        result = rec.retain_game_candidates(parts[:1], parts, 'gpu', evaluate,
                                            144, 100, prices, 700000)
        self.assertEqual({'generic', 'specialist', 'value'}, {p['id'] for p in result})
        self.assertNotIn('unaffordable', calls)

    def test_shortlist_does_not_repeat_scoring_if_all_models_are_retained(self):
        parts = [dict(id='gpu', name='gpu', price=200000)]
        def unexpected(_):
            self.fail('No need to evaluate a complete shortlist')
        self.assertEqual(parts, rec.retain_game_candidates(
            parts, parts, 'gpu', unexpected, 144, 100, {('gpu', 'gpu'): 200000}, 300000))


class AllGameRecommendationTests(unittest.TestCase):
    def test_all_games_and_resolutions_use_valid_fps_and_compatible_ordered_recommendations(self):
        identifiers = {
            'gpu': {'gpu_rtx4060', 'gpu_rtx5070', 'gpu_rtx5080', 'gpu_rx9070xt'},
            'cpu': {'cpu_r5_7600', 'cpu_r7_7800x3d', 'cpu_r7_9800x3d'},
            'ram': {'ram_32_ddr5'}, 'mb': {'mb_b650'},
            'psu': {'psu_850'}, 'storage': {'ssd_1tb_gen3', 'ssd_2tb_gen4'},
        }
        inventory = {kind: [row for row in CATALOGS[kind] if row['id'] in ids]
                     for kind, ids in identifiers.items()}
        with patch.object(database, 'db_lookup_price', return_value=None), \
             patch.object(database, 'db_lookup_price_info', return_value=None), \
             patch.object(fps, 'db_lookup_benchmarks', return_value=[]):
            for game in GAME_OPTIONS:
                for resolution in ('1080', '1440', '2160'):
                    with self.subTest(game=game['id'], resolution=resolution):
                        query = dict(game=game['id'], resolution=resolution, refresh=144,
                                     budget_mode='unlimited')
                        shared = {}
                        candidates = {tier: rec.build_tier_candidates(
                            query, tier, random.Random(0), inventory=inventory, shared_fps=shared)
                            for tier in ('low', 'mid', 'high')}
                        selected = rec.select_ordered_tier_plans(candidates)
                        plans = [plan for plan in selected.values() if plan]
                        self.assertTrue(plans)
                        for previous, current in zip(plans, plans[1:]):
                            self.assertGreater(rec.tier_upgrade_quality(previous, current), 0)
                        for plan in plans:
                            self.assertTrue(plan['compatibility']['compatible'])
                            self.assertGreaterEqual(plan['parts']['psu']['watt'], plan['debug']['recommended_psu_watt'])
                            for preset, average in plan['fps']['fps_by_option'].items():
                                self.assertTrue(math.isfinite(average) and average > 0)
                                low = plan['fps']['low1_by_option'][preset]
                                self.assertTrue(0 < low <= average) if low is not None else self.assertEqual('unavailable', plan['fps']['option_evidence'][preset]['low1_method'])
                                cap = fps.game_frame_cap(game['id'])
                                if cap:
                                    self.assertLessEqual(average, cap)


if __name__ == '__main__':
    unittest.main()
