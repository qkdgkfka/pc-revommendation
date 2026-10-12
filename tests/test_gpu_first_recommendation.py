"""GPU-first gaming budgets and the user's preferred memory manufacturers."""
import copy
import random
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from pcbuilder import database, fps, recommendation as rec
from recommendation_policy import gaming_objective
from server_catalogs import CATALOGS


class GpuFirstPolicyTests(unittest.TestCase):
    def score(self, cpu_price, gpu_price, gpu_perf=70, coverage=1, cpu_loss=0):
        return gaming_objective(
            gpu_perf=gpu_perf, gpu_target=55, fps_ratio=coverage, low1_ratio=coverage,
            budget_fit=1, unlimited=False, ram_gb=32, cpu_loss=cpu_loss,
            parts={'cpu': {'price': cpu_price}, 'gpu': {'price': gpu_price}, 'storage': {}})

    def test_same_budget_prefers_gpu_over_excess_cpu_when_both_meet_fps_target(self):
        gpu_first = self.score(250000, 850000, gpu_perf=80, cpu_loss=.15)
        cpu_first = self.score(550000, 550000, gpu_perf=60, cpu_loss=0)
        self.assertGreater(gpu_first, cpu_first)

    def test_no_cpu_penalty_after_average_and_low_targets_are_met(self):
        self.assertEqual(self.score(250000, 850000, cpu_loss=0),
                         self.score(250000, 850000, cpu_loss=.3))

    def test_overpriced_cpu_needs_a_real_fps_benefit(self):
        self.assertGreater(self.score(250000, 850000), self.score(600000, 850000))

    def test_cpu_bound_game_still_prefers_meaningful_fps_improvement(self):
        self.assertGreater(self.score(550000, 550000, coverage=.95),
                           self.score(250000, 850000, coverage=.5, cpu_loss=.6))

    def test_cpu_preselection_does_not_target_flagship_for_high_tier(self):
        modest = next(p for p in CATALOGS['cpu'] if p['id'] == 'cpu_r5_7600')
        flagship = next(p for p in CATALOGS['cpu'] if p['id'] == 'cpu_r7_9800x3d')
        with patch.object(database, 'db_lookup_price', return_value=None):
            for budget in (0, 3000000):
                with self.subTest(budget=budget):
                    scores = [rec.score_cpu(p, budget, '1440', 144, 'high', 'cyberpunk2077', random.Random(0))
                              for p in (modest, flagship)]
                    self.assertGreater(scores[0], scores[1])


class PreferredMemoryTests(unittest.TestCase):
    def setUp(self):
        ids = {'cpu': 'cpu_r5_7600', 'gpu': 'gpu_rtx5070', 'ram': 'ram_32_ddr5',
               'mb': 'mb_b650', 'psu': 'psu_850', 'storage': 'ssd_1tb_gen3'}
        self.inventory = {kind: [copy.deepcopy(next(p for p in CATALOGS[kind] if p['id'] == identifier))]
                          for kind, identifier in ids.items()}
        for module, name in ((database, 'db_lookup_price'), (database, 'db_lookup_price_info'),
                             (fps, 'db_lookup_benchmarks')):
            guard = patch.object(module, name, return_value=None)
            guard.start()
            self.addCleanup(guard.stop)

    def select(self, preferred, **extra):
        base = self.inventory['ram'][0]
        self.inventory['ram'] = [dict(base, id='cheap', name='Other DDR5 32GB', brand='Other', price=120000),
                                 {**base, 'id': 'preferred', 'name': preferred, 'brand': '', 'price': 150000, **extra}]
        return rec.build_tier_candidates({'budget_max': 3000000}, 'mid', random.Random(0),
                                         inventory=self.inventory)[0]

    def test_samsung_and_klevv_win_over_cheaper_equivalent_ram(self):
        for name in ('Samsung DDR5 32GB', '삼성전자 DDR5 32GB',
                     'ESSENCORE KLEVV DDR5 32GB', '에센코어 클레브 DDR5 32GB'):
            with self.subTest(name=name):
                self.assertEqual('preferred', self.select(name)['parts']['ram']['id'])

    def test_incompatible_preferred_ram_does_not_displace_compatible_ram(self):
        self.assertEqual('cheap', self.select('Samsung DDR4 32GB', type='DDR4')['parts']['ram']['id'])

    def test_samsung_ic_in_another_brands_product_is_not_samsung_ram(self):
        self.assertEqual('cheap', self.select('Other DDR5 Samsung IC 32GB')['parts']['ram']['id'])

    def test_retail_name_overrides_stale_reference_brand(self):
        self.assertEqual('cheap', self.select('Samsung DDR5 32GB', brand='Samsung',
                                             product_name='Other Samsung IC DDR5 32GB')['parts']['ram']['id'])

    def test_required_capacity_is_not_lost_to_a_smaller_preferred_module(self):
        base = self.inventory['ram'][0]
        self.inventory['ram'] = [dict(base, id='capacity', name='Other DDR5 32GB', price=120000),
                                 dict(base, id='small', name='Samsung DDR5 8GB', gb=8, price=10000)]
        plans = rec.build_tier_candidates({'budget_max': 3000000}, 'high', random.Random(0), inventory=self.inventory)
        self.assertEqual('capacity', plans[0]['parts']['ram']['id'])

    def test_cheap_duplicate_skus_cannot_evict_preferred_ram_before_selection(self):
        base = self.inventory['ram'][0]
        observed = datetime.now(timezone.utc).isoformat()
        rows = []
        for index, name in enumerate(['Other DDR5 32GB'] * 4 + ['Samsung DDR5 32GB', 'ESSENCORE KLEVV DDR5 32GB']):
            rows.append(dict(base, id=f'ram-{index}', name=name, product_name=name,
                             brand='', price=110000 + index * 10000,
                             url=f'https://prod.danawa.com/info/?pcode={10000 + index}',
                             image_url=f'https://img.danuri.io/ram-{index}.jpg',
                             price_source='danawa_live', price_status='verified', price_checked_at=observed))
        with patch.object(rec.retail, 'market_products_response',
                          side_effect=lambda kind, **kw: {'items': rows if kind == 'ram' else []}), \
             patch.object(rec, 'saved_products', return_value=[]), \
             patch.object(rec, 'fetch_product_image', return_value=(b'photo', 'image/jpeg')):
            found = rec.verified_recommendation_inventory()['ram']
        self.assertTrue({'ram-4', 'ram-5'}.issubset({row['id'] for row in found}))

    def test_unverified_preferred_ram_never_enters_recommendation_inventory(self):
        row = dict(self.inventory['ram'][0], id='unverified', name='Samsung DDR5 32GB',
                   product_name='Samsung DDR5 32GB', price=150000, price_source='catalog',
                   price_status='estimated', url='https://prod.danawa.com/info/?pcode=12345',
                   image_url='https://img.danuri.io/ram.jpg')
        with patch.object(rec.retail, 'market_products_response',
                          side_effect=lambda kind, **kw: {'items': [row] if kind == 'ram' else []}), \
             patch.object(rec, 'saved_products', return_value=[]), \
             patch.object(rec, 'fetch_product_image', return_value=(b'photo', 'image/jpeg')):
            self.assertEqual([], rec.verified_recommendation_inventory()['ram'])


if __name__ == '__main__':
    unittest.main()
