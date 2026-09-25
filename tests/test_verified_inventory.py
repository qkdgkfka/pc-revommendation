import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import server_fixed as s

class VerifiedInventoryTests(unittest.TestCase):
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
        with patch.object(s, "market_products_response", side_effect=lambda kind, **kw: {"items": rows if kind == "cpu" else []}), \
             patch.object(s, "saved_products", return_value=[]), \
             patch.object(s, "fetch_product_image", return_value=photo):
            return s.verified_recommendation_inventory()

    def test_valid_quote_and_decodable_photo_are_required(self):
        self.assertEqual(1, len(self.inventory([self.row()], (b"photo", "image/jpeg"))["cpu"]))
        self.assertEqual([], self.inventory([self.row()], None)["cpu"])
        self.assertEqual([], self.inventory([self.row(price_source="catalog", price_status="estimated")], (b"photo", "image/jpeg"))["cpu"])
        self.assertEqual([], self.inventory([self.row(price_checked_at="2020-01-01T00:00:00Z")], (b"photo", "image/jpeg"))["cpu"])
        self.assertEqual([], self.inventory([self.row()], (b"<svg/>", "image/svg+xml"))["cpu"])

    def test_missing_category_never_falls_back_to_reference_parts(self):
        s.RECOMMENDATION_CACHE.clear()
        with patch.object(s, "verified_recommendation_inventory", return_value={k: [] for k in ("cpu","gpu","ram","mb","storage","psu")}):
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
