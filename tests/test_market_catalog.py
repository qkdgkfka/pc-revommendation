from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import market_catalog as catalog


class SavedRetailCatalogTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        folder = Path(self.directory.name)
        self.patches = [
            patch.object(catalog, "DATA_DIR", folder),
            patch.object(catalog, "SNAPSHOT_PATH", folder / "snapshot.json"),
            patch.object(catalog, "CACHE_PATH", folder / "cache.json"),
        ]
        for replacement in self.patches:
            replacement.start()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(patch.stopall)
        self.now = datetime(2026, 9, 14, 8, tzinfo=timezone.utc)

    def item(self, **changes):
        row = {
            "id": "danawa_cpu_123", "name": "AMD Ryzen 5 7500F",
            "price": 200000, "url": "https://prod.danawa.com/info/?pcode=123",
            "price_checked_at": self.now.isoformat(), "price_source": "danawa_top_live",
        }
        row.update(changes)
        return row

    def test_recent_saved_quote_is_cached_and_expires(self):
        catalog.remember_products("cpu", [self.item()])
        recent = catalog.saved_products("cpu", self.now + timedelta(hours=1))[0]
        self.assertEqual("cached", recent["price_status"])
        self.assertTrue(recent["price_verified"])
        self.assertEqual("danawa_snapshot", recent["price_source"])
        stale = catalog.saved_products("cpu", self.now + timedelta(hours=25))[0]
        self.assertEqual("stale", stale["price_status"])
        self.assertFalse(stale["price_verified"])
        self.assertEqual(200000, stale["price"])

    def test_missing_date_and_non_retailer_quotes_are_not_saved(self):
        catalog.remember_products("cpu", [
            self.item(price_checked_at=""), self.item(url="https://example.com/product"),
            self.item(url="https://prod.danawa.com.evil.test/info/?pcode=123"),
        ])
        self.assertEqual([], catalog.saved_products("cpu", self.now))

    def test_refresh_updates_same_sku_without_losing_other_options(self):
        catalog.SNAPSHOT_PATH.write_text(json.dumps({"products": {"cpu": [
            self.item(), self.item(id="danawa_cpu_456"),
        ]}}))
        catalog.remember_products("cpu", [self.item(price=210000)])
        catalog.remember_products("cpu", [])
        rows = {row["id"]: row for row in catalog.saved_products("cpu", self.now)}
        self.assertEqual(2, len(rows))
        self.assertEqual(210000, rows["danawa_cpu_123"]["price"])

    def test_corrupt_runtime_cache_preserves_bundled_snapshot(self):
        catalog.SNAPSHOT_PATH.write_text(json.dumps({"products": {"cpu": [self.item()]}}))
        catalog.CACHE_PATH.write_text("{broken")
        self.assertEqual(1, len(catalog.saved_products("cpu", self.now)))

    def test_unchanged_catalog_reuses_validation_but_returns_independent_rows(self):
        catalog.remember_products("cpu", [self.item()])
        with patch.object(catalog, "_verified_retail_row", wraps=catalog._verified_retail_row) as verify:
            first = catalog.saved_products("cpu", self.now)
            count = verify.call_count
            self.assertGreater(count, 0)
            first[0]["price"] = 1
            later = catalog.saved_products("cpu", self.now + timedelta(hours=25))
            self.assertEqual(count, verify.call_count)
        self.assertEqual(200000, later[0]["price"])
        self.assertEqual("stale", later[0]["price_status"])

    def test_cached_rows_follow_replacement_and_removal_of_source_files(self):
        catalog.remember_products("cpu", [self.item()])
        self.assertEqual(200000, catalog.saved_products("cpu", self.now)[0]["price"])
        replacement = catalog.CACHE_PATH.with_suffix(".replacement")
        replacement.write_text(json.dumps({"products": {"cpu": [self.item(price=250000)]}}))
        replacement.replace(catalog.CACHE_PATH)
        self.assertEqual(250000, catalog.saved_products("cpu", self.now)[0]["price"])
        catalog.CACHE_PATH.unlink()
        self.assertEqual([], catalog.saved_products("cpu", self.now))


if __name__ == "__main__":
    unittest.main()
