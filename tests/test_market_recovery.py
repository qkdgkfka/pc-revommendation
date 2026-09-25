"""Regression cases for observed retail quotes and outage recovery."""
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import market_catalog
import server_fixed as server
from test_market_sources import danawa_group, compuzone_row
from urllib.error import HTTPError, URLError


class MarketRecoveryTests(unittest.TestCase):
    def setUp(self):
        server.MARKET_BROWSE_CACHE.clear()
        server.IMAGE_URL_CACHE.clear()
        self.directory = tempfile.TemporaryDirectory()
        folder = Path(self.directory.name)
        self.addCleanup(self.directory.cleanup)
        for name, value in (("DATA_DIR", folder), ("SNAPSHOT_PATH", folder / "snapshot.json"),
                            ("CACHE_PATH", folder / "cache.json")):
            replacement = patch.object(market_catalog, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        self.addCleanup(server.MARKET_BROWSE_CACHE.clear)
        self.addCleanup(server.IMAGE_URL_CACHE.clear)

    def quote(self, **updates):
        row = dict(id="danawa_cpu_123", name="Intel Core i5-14600KF", price=296980,
                   url="https://prod.danawa.com/info/?pcode=123&cate=113973",
                   price_checked_at=datetime.now(timezone.utc).isoformat(),
                   price_source="danawa_live", image_url="https://img.danuri.io/cpu.jpg")
        row.update(updates)
        return row

    def test_outage_after_restart_returns_saved_quotes_with_original_date(self):
        row = self.quote()
        market_catalog.remember_products("cpu", [row])
        with patch.object(server, "_market_fetch_html", side_effect=TimeoutError):
            result = server.market_products_response("cpu", "14600KF", source="danawa")
        self.assertTrue(result["ok"])
        self.assertEqual("cached", result["status"])
        self.assertEqual(296980, result["items"][0]["price"])
        self.assertEqual(row["price_checked_at"], result["items"][0]["price_checked_at"])

    def test_outage_preserves_stale_status_and_source_and_query_filters(self):
        old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        market_catalog.remember_products("cpu", [
            self.quote(price_checked_at=old),
            self.quote(id="compuzone_cpu_456", url="https://www.compuzone.co.kr/product/product_detail.htm?ProductNo=456"),
            self.quote(id="danawa_cpu_789", name="Intel Core i5-14600K"),
        ])
        with patch.object(server, "_market_fetch_html", side_effect=TimeoutError):
            result = server.market_products_response("cpu", "14600KF", source="danawa")
        self.assertEqual("stale", result["status"])
        self.assertEqual(["danawa_cpu_123"], [item["id"] for item in result["items"]])
        self.assertFalse(result["items"][0]["price_verified"])

    def test_current_exact_ssd_price_is_not_replaced_by_old_catalog_estimate(self):
        html = danawa_group("storage", [("101", "1TB", 331560)]).replace(
            "Samsung 990 PRO M.2 NVMe", "Samsung 990 EVO Plus M.2 NVMe")
        with patch.object(server, "_market_fetch_html", return_value=html):
            result = server.fetch_market_top_product(
                "Samsung 990 EVO Plus NVMe SSD 1TB", "storage",
                catalog_price=105000, source="danawa")
        self.assertIsNotNone(result)
        self.assertEqual(331560, result["price"])
        self.assertEqual("https://img.danuri.io/product.jpg", result["image_url"])

    def test_price_observation_time_is_not_replaced_when_quote_is_stored(self):
        row = self.quote(price_checked_at="2026-09-20T11:00:00Z")
        with patch.object(server, "_ensure_db_connection", return_value=None):
            result = server.store_danawa_price({"name":row["name"]}, "cpu", row)
        self.assertEqual("2026-09-20T11:00:00Z", result["scraped_at"])

    def test_saved_quote_remains_cached_in_recommendation_and_lookup(self):
        row = self.quote(price_status="cached", price_source="danawa_snapshot")
        with patch.object(server, "_ensure_db_connection", return_value=None):
            info = server.store_danawa_price({"name": row["name"]}, "cpu", row)
        part = {"name": row["name"], "price_checked_at": "2020-01-01T00:00:00Z"}
        server.apply_price_info_to_part(part, info)
        self.assertEqual("cached", part["price_status"])
        self.assertEqual(row["price_checked_at"], part["scraped_at"])
        self.assertEqual(row["price_checked_at"], part["price_checked_at"])
        with patch.object(server, "resolve_recommendation_price_cache",
                          return_value={("cpu", server.canonical_name(row["name"])): info}):
            result = server.price_lookup_response({"items":[{"type":"cpu", "name":row["name"]}]})
        self.assertEqual("cached", result["results"][0]["price_status"])

    def test_queued_parts_can_finish_their_price_request(self):
        def lookup(name, *args):
            time.sleep(1.6)
            return self.quote(name=name)
        wanted = {("cpu", str(i)): ({"name":f"Test CPU {i}", "price":300000}, "cpu") for i in range(7)}
        with patch.object(server, "db_lookup_price_info", return_value=None), \
             patch.object(server, "fetch_market_top_product", side_effect=lookup), \
             patch.object(server, "_ensure_db_connection", return_value=None):
            result = server.resolve_recommendation_price_cache(wanted)
        self.assertEqual(7, sum(value is not None for value in result.values()))

    def test_one_provider_failure_keeps_other_live_results(self):
        failures = [TimeoutError(), URLError("DNS failed"), ConnectionError(),
                    ValueError("invalid HTML")]
        failures.extend(HTTPError("https://search.danawa.com", code, "error", {}, None)
                        for code in (403, 404, 429, 500))
        for failure in failures:
            with self.subTest(failure=repr(failure)):
                server.MARKET_BROWSE_CACHE.clear()
                def fetch(url, provider, timeout):
                    if provider == "danawa":
                        raise failure
                    return compuzone_row()
                with patch.object(server, "_market_fetch_html", side_effect=fetch):
                    result = server.market_products_response("gpu", source="all")
                self.assertTrue(result["ok"])
                self.assertEqual("live", result["status"])
                self.assertTrue(any(item["shop"] == "Compuzone" for item in result["items"]))

    def test_programming_errors_are_not_reported_as_retailer_outages(self):
        with patch.object(server, "_market_fetch_html", side_effect=RuntimeError("bug")):
            with self.assertRaises(RuntimeError):
                server.market_products_response("cpu", source="danawa")

    def test_collected_verified_products_extend_live_browse_pages(self):
        row = self.quote(image_checked_at="2026-09-25T00:00:00Z")
        market_catalog.remember_products("cpu", [row])
        with patch.object(server, "_market_fetch_html", return_value=danawa_group("cpu")):
            result = server.market_products_response("cpu", source="danawa")
        self.assertIn(row["id"], [part["id"] for part in result["items"]])

    def test_desktop_memory_does_not_use_notebook_quote(self):
        self.assertFalse(server.market_component_name_valid("ram", "삼성전자 노트북 DDR4-3200 (8GB)"))

    def test_saved_photos_reject_mobile_gpu_and_notebook_memory(self):
        for part_type, requested, listed in (
            ("gpu", "AMD Radeon RX 6600 8GB", "AMD Radeon RX 6600 M 8GB"),
            ("ram", "Samsung DDR4 8GB 3200", "삼성전자 노트북 DDR4-3200 8GB"),
        ):
            with self.subTest(part_type=part_type):
                row = {"name":listed, "image_url":"https://img.danuri.io/wrong.jpg"}
                with patch.object(server, "saved_products", return_value=[row]):
                    self.assertEqual([], server.saved_part_image_urls(requested, part_type))

    def test_gpu_price_match_rejects_mobile_and_other_suffixes(self):
        for name in ("FORSA 라데온 RX 6600 M D6 8GB", "AMD RX 6600 XT 8GB"):
            self.assertFalse(server.compatible_price_name("AMD Radeon RX 6600 8GB", name))

    def test_memory_kit_price_does_not_match_single_module(self):
        self.assertFalse(server.compatible_price_name(
            "Kingston DDR5 32GB (16x2) 5600", "Kingston DDR5-5600 32GB"))
        self.assertTrue(server.compatible_price_name(
            "Kingston DDR5 32GB (16x2) 5600", "Kingston DDR5-5600 32GB (16GBx2)"))


if __name__ == "__main__":
    unittest.main()
