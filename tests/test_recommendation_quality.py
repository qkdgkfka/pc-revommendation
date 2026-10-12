"""Observable quality, budget and performance steps; no retailer/network IO."""
import copy
import random
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

from pcbuilder import database, fps, recommendation as rec
from server_catalogs import CATALOGS
from test_recommendation_ordering import plan


class ComponentQualityTests(unittest.TestCase):
    def setUp(self):
        ids = {'cpu': 'cpu_r5_7600', 'gpu': 'gpu_rtx5070', 'ram': 'ram_32_ddr5',
               'mb': 'mb_b650', 'psu': 'psu_850', 'storage': 'ssd_1tb_gen3'}
        self.inventory = {kind: [copy.deepcopy(next(p for p in CATALOGS[kind] if p['id'] == key))]
                          for kind, key in ids.items()}
        for module, name in ((database, 'db_lookup_price'), (database, 'db_lookup_price_info'),
                             (fps, 'db_lookup_benchmarks')):
            guard = patch.object(module, name, return_value=None)
            guard.start()
            self.addCleanup(guard.stop)

    def choose(self, kind, products, budget=3000000):
        base = self.inventory[kind][0]
        self.inventory[kind] = [dict(base, **item) for item in products]
        candidates = rec.build_tier_candidates({'budget_max': budget}, 'mid', random.Random(0),
                                              inventory=self.inventory)
        self.assertTrue(candidates)
        return candidates[0]['parts'][kind]['id']

    def test_reputable_memory_with_modest_premium_beats_unknown_brand(self):
        for name in ('Kingston DDR5 32GB', 'G.SKILL DDR5 32GB', '마이크론 Crucial DDR5 32GB',
                     '[에센코어] KLEVV DDR5 32GB'):
            with self.subTest(name=name):
                self.assertEqual('known', self.choose('ram', [
                    dict(id='cheap', name='Other DDR5 32GB', price=100000),
                    dict(id='known', name=name, price=125000)]))

    def test_reputable_ssd_with_modest_premium_beats_unknown_brand(self):
        for name in ('SK hynix Platinum NVMe 1TB', 'ESSENCORE KLEVV CRAS NVMe 1TB'):
            with self.subTest(name=name):
                self.assertEqual('known', self.choose('storage', [
                    dict(id='cheap', name='Other NVMe 1TB', price=100000),
                    dict(id='known', name=name, price=125000)]))

    def test_memory_speed_and_latency_justify_modest_premium(self):
        self.assertEqual('fast', self.choose('ram', [
            dict(id='slow', name='Samsung DDR5 32GB 4800 CL40', speed=4800, price=100000),
            dict(id='fast', name='G.SKILL DDR5 32GB 6000 CL30', speed=6000, price=120000)]))

    def test_ssd_actual_specs_break_same_brand_capacity_tie(self):
        self.assertEqual('fast', self.choose('storage', [
            dict(id='slow', name='Kingston NVMe 1TB', price=100000,
                 spec_text='QLC / 읽기: 3000MB/s / 쓰기: 1500MB/s / DRAM-less'),
            dict(id='fast', name='Kingston NVMe 1TB TLC', price=125000,
                 spec_text='TLC / 읽기: 7000MB/s / 쓰기: 6500MB/s / DRAM 탑재')]))

    def test_brand_does_not_justify_unbounded_price_premium(self):
        self.assertEqual('value', self.choose('ram', [
            dict(id='value', name='Other DDR5 32GB', price=100000),
            dict(id='expensive', name='Samsung DDR5 32GB', price=500000)]))

    def test_premium_memory_does_not_remove_only_budget_feasible_build(self):
        # Same compatible capacity; the preferred product exceeds the ceiling.
        self.assertEqual('value', self.choose('ram', [
            dict(id='value', name='Other DDR5 32GB', price=100000),
            dict(id='expensive', name='Samsung DDR5 32GB', price=3000000)], budget=1500000))

    def test_inventory_keeps_affordable_ram_before_quality_premium_scoring(self):
        base = self.inventory['ram'][0]
        rows = []
        for index, (key, cl, price) in enumerate([('value', 40, 100000), ('fast', 30, 500000), ('premium', 32, 510000)]):
            name = f'Kingston DDR5 32GB 6000 CL{cl}'
            rows.append(dict(base, id=key, name=name, product_name=name, price=price,
                             url=f'https://prod.danawa.com/info/?pcode={20000 + index}',
                             image_url=f'https://img.danuri.io/ram-{index}.jpg',
                             price_source='danawa_live', price_status='verified',
                             price_checked_at=datetime.now(timezone.utc).isoformat()))
        with patch.object(rec.retail, 'market_products_response',
                          side_effect=lambda kind, **kw: {'items': rows if kind == 'ram' else []}), \
             patch.object(rec, 'saved_products', return_value=[]), \
             patch.object(rec, 'fetch_product_image', return_value=(b'photo', 'image/jpeg')):
            found = rec.verified_recommendation_inventory()['ram']
        self.assertTrue({'value', 'fast'}.issubset({p['id'] for p in found}))


class MeaningfulTierTests(unittest.TestCase):
    def test_small_gpu_step_is_not_a_new_tier_even_with_a_huge_score(self):
        low = plan('low', gpu=50)
        small = plan('small', gpu=53, score=10000)
        clear = plan('clear', gpu=60)
        selected = rec.select_ordered_tier_plans({'low': [low], 'mid': [small, clear]})
        self.assertEqual('clear', selected['mid']['name'])

    def test_cpu_limited_game_can_upgrade_with_same_gpu_and_real_fps_gain(self):
        low = plan('low', gpu=60, cpu=50, fps=100, low1=70)
        high = plan('high', gpu=60, cpu=70, fps=140, low1=100)
        high['parts']['gpu'] = dict(low['parts']['gpu'])
        low['fps'] = {'bottleneck': {'limiting_component': 'cpu'}}
        self.assertGreater(rec.tier_upgrade_quality(low, high), 0)

    def test_extra_cpu_cost_without_game_gain_is_not_a_tier(self):
        low = plan('low', gpu=60, cpu=50, fps=100)
        high = plan('high', gpu=60, cpu=80, fps=100)
        self.assertLess(rec.tier_upgrade_quality(low, high), 0)

    def test_work_tiers_need_more_than_two_score_points(self):
        low, high = plan('low'), plan('high')
        low['mode'] = high['mode'] = 'work'
        low['debug']['ordering_metrics']['work'] = 70
        high['debug']['ordering_metrics']['work'] = 72
        self.assertLess(rec.tier_upgrade_quality(low, high), 0)
