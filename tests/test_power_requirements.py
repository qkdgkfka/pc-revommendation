"""PSU recommendations must retain quality and electrical headroom at every budget."""
import copy
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from pcbuilder import recommendation as rec
from server_catalogs import CATALOGS


def part(kind, key):
    return copy.deepcopy(next(p for p in CATALOGS[kind] if p['id'] == key))


class PowerRequirementsTests(unittest.TestCase):
    def setUp(self):
        self.cpu = part('cpu', 'cpu_r5_7600')
        self.gpu = part('gpu', 'gpu_rtx5070')

    def candidates(self, rows, budget=1500000):
        with patch.object(rec, 'cached_part_price', side_effect=lambda p, *_: p['price']):
            return rec.psu_candidates_for(self.cpu, self.gpu, rows, 'low', budget, {})

    def test_gold_is_required_even_if_bronze_is_cheaper_or_budget_is_unspecified(self):
        rows = [dict(id='bronze', name='PSU 850W 80 PLUS Bronze', watt=850, price=30000),
                dict(id='gold', name='PSU 850W 80 PLUS Gold', watt=850, price=110000)]
        for budget in (0, 1000000, 3000000):
            self.assertEqual(['gold'], [p['id'] for p in self.candidates(rows, budget)])

    def test_unknown_and_unrelated_gold_labels_do_not_qualify(self):
        for name in ('PSU 850W', 'Gold edition 850W', '850W Cybenetics Gold',
                     '850W 80 PLUS Bronze Cybenetics Gold'):
            with self.subTest(name=name):
                self.assertEqual([], self.candidates([dict(name=name, watt=850, price=30000)]))

    def test_gold_platinum_and_titanium_qualify(self):
        for grade in ('Gold', 'Platinum', 'Titanium', '골드', '플래티넘', '티타늄'):
            with self.subTest(grade=grade):
                self.assertTrue(self.candidates([dict(name=f'PSU 850W 80 PLUS {grade}', watt=850, price=100000)]))

    def test_insufficient_gold_does_not_fall_back_to_bronze(self):
        self.assertEqual([], self.candidates([
            dict(id='small', name='PSU 500W 80 PLUS Gold', watt=500, price=100000),
            dict(id='bronze', name='PSU 1200W 80 PLUS Bronze', watt=1200, price=90000)]))

    def test_gpu_manufacturer_floor_is_applied(self):
        for key, floor in [('gpu_rtx5070', 650), ('gpu_rtx5060ti16', 600),
                           ('gpu_rtx5080', 850), ('gpu_rtx5090', 1000),
                           ('gpu_rx7700xt', 700), ('gpu_rx9070xt', 750)]:
            with self.subTest(gpu=key):
                self.assertGreaterEqual(rec.recommended_psu_watt(self.cpu, part('gpu', key)), floor)

    def test_high_power_cpu_and_gpu_need_more_than_gpu_minimum(self):
        cpu = part('cpu', 'cpu_i9_14900k')
        self.assertEqual(1200, rec.recommended_psu_watt(cpu, part('gpu', 'gpu_rtx5090')))
        self.assertGreaterEqual(rec.recommended_psu_watt(cpu, part('gpu', 'gpu_rtx5080')), 900)

    def test_retail_reference_preserves_power_requirements(self):
        cpu = dict(id='retail-cpu', performance_ref_id='cpu_i9_14900k', tdp=125)
        gpu = dict(id='retail-gpu', performance_ref_id='gpu_rtx5090', tdp=575)
        self.assertEqual(1200, rec.recommended_psu_watt(cpu, gpu))

    def test_explicit_higher_board_power_and_psu_requirement_are_preserved(self):
        gpu = dict(self.gpu, board_power_watt=350, recommended_psu_watt=1000)
        self.assertGreaterEqual(rec.recommended_psu_watt(self.cpu, gpu), 1000)
        cpu = dict(self.cpu, max_power_watt=300)
        self.assertGreaterEqual(rec.recommended_psu_watt(cpu, gpu), 1000)

    def test_product_specific_requirement_in_retail_specs_is_applied(self):
        gpu = dict(self.gpu, spec_text='소비전력: 320W / 권장파워: 850W 이상 / 전원 포트: 16핀')
        self.assertGreaterEqual(rec.recommended_psu_watt(self.cpu, gpu), 850)

    def test_inventory_filters_quality_before_cheapest_per_watt_bucketing(self):
        rows = []
        for index, grade in enumerate(('Bronze', 'Silver', 'Gold')):
            name = f'FSP 850W 80 PLUS {grade}'
            rows.append(dict(id=grade, name=name, product_name=name, watt=850,
                             price=50000 + index * 20000,
                             url=f'https://prod.danawa.com/info/?pcode={90000 + index}',
                             image_url=f'https://img.danuri.io/psu-{index}.jpg',
                             price_source='danawa_live', price_status='verified',
                             price_checked_at=datetime.now(timezone.utc).isoformat()))
        with patch.object(rec.retail, 'market_products_response',
                          side_effect=lambda kind, **kw: {'items': rows if kind == 'psu' else []}), \
             patch.object(rec, 'saved_products', return_value=[]), \
             patch.object(rec, 'fetch_product_image', return_value=(b'photo', 'image/jpeg')):
            found = rec.verified_recommendation_inventory()['psu']
        self.assertEqual(['Gold'], [p['id'] for p in found])
