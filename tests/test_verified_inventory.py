from backend_patch import patch_backend
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import server_fixed as s

class VerifiedInventoryTests(unittest.TestCase):
    def test_early_gpu_photos_cannot_block_a_later_required_cpu_photo(self):
        gpu_started, cpu_started = Event(), Event()
        cpu = self.row()
        gpu = next(p for p in s.GPU_CATALOG if p['id'] == 'gpu_rtx5070')
        gpus = [dict(cpu, **{k: v for k, v in gpu.items() if k not in {'id'}},
                     id=f'gpu-{i}', performance_ref_id=f'gpu-model-{i}', product_name='ASUS DUAL RTX 5070 12GB',
                     url=f'https://prod.danawa.com/info/?pcode={1000+i}&cate=112753',
                     image_url=f'https://img.danuri.io/gpu-{i}.jpg') for i in range(32)]
        blocked = []

        def seller(kind, **kwargs):
            if kind == 'cpu':
                self.assertTrue(gpu_started.wait(1))
                return {'items': [cpu]}
            return {'items': gpus if kind == 'gpu' else []}

        def photo(url):
            if 'gpu-' in url:
                gpu_started.set()
                if not cpu_started.wait(1):
                    blocked.append(url)
            else:
                cpu_started.set()
            return b'photo', 'image/jpeg'

        with patch_backend(s, 'market_products_response', side_effect=seller), \
             patch_backend(s, 'saved_products', return_value=[]), \
             patch_backend(s, 'fetch_product_image', side_effect=photo):
            result = s.verified_recommendation_inventory()
        self.assertFalse(blocked, 'A GPU batch starved the CPU photo')
        self.assertEqual(1, len(result['cpu']))
        self.assertEqual(32, len(result['gpu']))

    def test_ready_category_photos_do_not_wait_for_slow_retail_category(self):
        photo_started, release_seller = Event(), Event()
        row = self.row()

        def seller(kind, **kwargs):
            if kind == 'gpu':
                release_seller.wait(2)
            return {'items': [row] if kind == 'cpu' else []}

        def photo(url):
            photo_started.set()
            return b'photo', 'image/jpeg'

        with patch_backend(s, 'market_products_response', side_effect=seller), \
             patch_backend(s, 'saved_products', return_value=[]), \
             patch_backend(s, 'fetch_product_image', side_effect=photo), \
             ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(s.verified_recommendation_inventory)
            try:
                self.assertTrue(photo_started.wait(1), 'A ready photo was blocked by another category')
            finally:
                release_seller.set()
            result = pending.result(timeout=2)
        self.assertEqual([row['id']], [part['id'] for part in result['cpu']])

    def row(self, **changes):
        row = dict(s.CPU_CATALOG[0])
        row.update(id="danawa_cpu_123", product_name=row["name"], price=300000,
                   url="https://prod.danawa.com/info/?pcode=123&cate=113973",
                   price_source="danawa_live", price_status="verified",
                   price_checked_at=datetime.now(timezone.utc).isoformat(),
                   image_url="https://img.danuri.io/exact.jpg")
        row.update(changes)
        return row

    def inventory(self, rows, photo):
        with patch_backend(s, "market_products_response", side_effect=lambda kind, **kw: {"items": rows if kind == "cpu" else []}), \
             patch_backend(s, "saved_products", return_value=[]), \
             patch_backend(s, "fetch_product_image", return_value=photo):
            return s.verified_recommendation_inventory()

    def test_valid_quote_and_decodable_photo_are_required(self):
        self.assertEqual(1, len(self.inventory([self.row()], (b"photo", "image/jpeg"))["cpu"]))
        self.assertEqual([], self.inventory([self.row()], None)["cpu"])
        self.assertEqual([], self.inventory([self.row(price_source="catalog", price_status="estimated")], (b"photo", "image/jpeg"))["cpu"])
        self.assertEqual([], self.inventory([self.row(price_checked_at="2020-01-01T00:00:00Z")], (b"photo", "image/jpeg"))["cpu"])
        self.assertEqual([], self.inventory([self.row()], (b"<svg/>", "image/svg+xml"))["cpu"])

    def test_missing_category_never_falls_back_to_reference_parts(self):
        s.RECOMMENDATION_CACHE.clear()
        with patch_backend(s, "verified_recommendation_inventory", return_value={k: [] for k in ("cpu","gpu","ram","mb","storage","psu")}):
            result=s.recommend({"budget":2000000})
        self.assertFalse(any(p and p.get("parts") for p in result["results"].values()))
        self.assertIn("사진", result["warning"])
        s.RECOMMENDATION_CACHE.clear()

    def test_inventory_is_request_local_and_empty_pools_stay_empty(self):
        import random
        original=list(s.CPU_CATALOG)
        inventory={k:[] for k in ("cpu","gpu","ram","mb","storage","psu")}
        result=s.build_tier_candidates({"budget":2000000}, "low", random.Random(1), inventory=inventory)
        self.assertEqual([], result)
        self.assertEqual(original,s.CPU_CATALOG)

if __name__ == "__main__":
    unittest.main()
