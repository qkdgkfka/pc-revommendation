"""Shared extraction and intentionally different crawler/runtime contracts."""
import unittest

import crawl_data as crawler
import product_metadata as metadata
import retailer_parsing
import server_fixed as server


SEARCH_URL = "https://prod.danawa.com/"
PRODUCTS = """
<li id="productItem_1" class="prod_item">
  <p class="prod_name"><a href="/info/?pcode=1">FSP Hydro 750W</a></p>
  <input id="productItem_categoryInfo_1" value="파워">
</li>
<li id="productItem_2" class="prod_item">
  <p class="prod_name"><a href="/info/?pcode=2"><b>FSP</b> Hydro 750W &amp; Gold</a></p>
  <input id="productItem_categoryInfo_2" value="파워">
  <input id="min_price_2" value="120000">
  <p class="price_sect"><strong>100,000</strong>원</p>
</li>
"""


class SharedExtractionTests(unittest.TestCase):
    def test_regex_rows_keep_each_products_own_price_and_prefer_hidden_price(self):
        # A missing-price row must never borrow the next row's cheaper display price.
        parse_rows = retailer_parsing.danawa_regex_products
        rows = list(parse_rows(PRODUCTS, SEARCH_URL))
        self.assertEqual(1, len(rows))
        self.assertEqual("FSP Hydro 750W & Gold", rows[0]["name"])
        self.assertEqual(120000, rows[0]["price"])
        self.assertEqual("https://prod.danawa.com/info/?pcode=2", rows[0]["url"])
        self.assertEqual("파워", rows[0]["category"])

    def test_regex_rows_allow_the_crawler_to_preserve_encoded_visible_text(self):
        parse_rows = retailer_parsing.danawa_regex_products
        rows = list(parse_rows(PRODUCTS, SEARCH_URL, clean_text=crawler.clean_text))
        self.assertEqual(["FSP Hydro 750W &amp; Gold"], [row["name"] for row in rows])

    def test_soup_rows_keep_hidden_price_and_the_source_node_for_runtime_images(self):
        if crawler.BeautifulSoup is None:
            self.skipTest("BeautifulSoup is optional")
        parse_rows = retailer_parsing.danawa_soup_products
        soup = crawler.BeautifulSoup(PRODUCTS, "html.parser")
        rows = list(parse_rows(soup, SEARCH_URL))
        self.assertEqual(1, len(rows))
        self.assertEqual("FSP Hydro 750W & Gold", rows[0]["name"])
        self.assertEqual(120000, rows[0]["price"])
        self.assertEqual("productItem_2", rows[0]["node"].get("id"))

    def test_sub_thousand_hidden_price_falls_back_to_the_display_price(self):
        html = PRODUCTS.replace('value="120000"', 'value="999"')
        rows = list(retailer_parsing.danawa_regex_products(html, SEARCH_URL))
        self.assertEqual(100000, rows[0]["price"])

    def test_soup_retains_image_alt_fallback_for_an_empty_anchor(self):
        if crawler.BeautifulSoup is None:
            self.skipTest("BeautifulSoup is optional")
        html = PRODUCTS.replace("<b>FSP</b> Hydro 750W &amp; Gold", '<img alt="FSP Hydro 750W">')
        regex_rows = list(retailer_parsing.danawa_regex_products(html, SEARCH_URL))
        soup_rows = list(retailer_parsing.danawa_soup_products(crawler.BeautifulSoup(html, "html.parser"), SEARCH_URL))
        self.assertEqual("", regex_rows[0]["name"])
        self.assertEqual("FSP Hydro 750W", soup_rows[0]["name"])


class AdapterContractTests(unittest.TestCase):
    def test_regex_adapters_keep_their_existing_entity_cleanup(self):
        crawler_row = crawler.parse_danawa_top_product_regex(PRODUCTS, SEARCH_URL, "", "psu")
        server_row = server.parse_danawa_top_product_regex(PRODUCTS, SEARCH_URL, "", "psu")
        self.assertEqual("FSP Hydro 750W &amp; Gold", crawler_row["name"])
        self.assertEqual("FSP Hydro 750W & Gold", server_row["name"])
        self.assertEqual(120000, crawler_row["price"])
        self.assertEqual(120000, server_row["price"])

    def test_runtime_capacity_and_variant_matching_remains_stricter(self):
        for query, product in [
            ("DDR5 32GB 6000", "DDR5 16GB 6000"),
            ("RTX 4060 Ti 16GB", "RTX 4060 Ti 8GB"),
            ("Samsung 990 PRO 2TB", "Samsung 990 EVO 2TB"),
        ]:
            with self.subTest(query=query):
                self.assertTrue(crawler.compatible_product_name(query, product))
                self.assertFalse(metadata.compatible_price_name(query, product))
        self.assertFalse(crawler.compatible_product_name("RTX 4070", "RTX 4070 Ti"))
        self.assertFalse(metadata.compatible_price_name("RTX 4070", "RTX 4070 Ti"))

    def test_runtime_selects_the_requested_vram_while_crawler_keeps_token_overlap(self):
        html = """
        <li class="prod_item"><p class="prod_name"><a href="/info/?pcode=8">MSI RTX 4060 Ti 8GB</a></p>
          <input id="productItem_categoryInfo_8" value="그래픽카드"><input id="min_price_8" value="350000"></li>
        <li class="prod_item"><p class="prod_name"><a href="/info/?pcode=16">MSI RTX 4060 Ti 16GB</a></p>
          <input id="productItem_categoryInfo_16" value="그래픽카드"><input id="min_price_16" value="450000"></li>
        """
        for parse_name in ("parse_danawa_top_product_regex", "parse_danawa_top_product"):
            with self.subTest(parser=parse_name):
                crawler_row = getattr(crawler, parse_name)(html, SEARCH_URL, "RTX 4060 Ti 16GB", "gpu")
                server_row = getattr(server, parse_name)(html, SEARCH_URL, "RTX 4060 Ti 16GB", "gpu")
                self.assertEqual("MSI RTX 4060 Ti 8GB", crawler_row["name"])
                self.assertEqual(350000, crawler_row["price"])
                self.assertEqual("MSI RTX 4060 Ti 16GB", server_row["name"])
                self.assertEqual(450000, server_row["price"])
                self.assertNotIn("block", crawler_row)
                self.assertNotIn("node", crawler_row)

    def test_untyped_soup_fallback_keeps_runtime_link_and_crawler_page_price(self):
        if crawler.BeautifulSoup is None or server.BeautifulSoup is None:
            self.skipTest("BeautifulSoup is optional")
        html = '<a href="/info/?pcode=1">FSP Hydro 750W</a> 100,000원'
        crawler_row = crawler.parse_danawa_top_product(html, SEARCH_URL)
        server_row = server.parse_danawa_top_product(html, SEARCH_URL)
        self.assertEqual(("", SEARCH_URL), (crawler_row["name"], crawler_row["url"]))
        self.assertEqual(("FSP Hydro 750W", "https://prod.danawa.com/info/?pcode=1"), (server_row["name"], server_row["url"]))
        self.assertEqual(100000, crawler_row["price"])
        self.assertEqual(100000, server_row["price"])

    def test_query_building_keeps_runtime_gpu_normalization_and_extra_categories(self):
        self.assertEqual("NVIDIA GeForce RTX 4070 그래픽카드", crawler.danawa_query_for_part("NVIDIA GeForce RTX 4070", "gpu"))
        self.assertEqual("RTX 4070 그래픽카드", server.danawa_query_for_part("NVIDIA GeForce RTX 4070", "gpu"))
        self.assertEqual("Seagate 4TB", crawler.danawa_query_for_part("Seagate 4TB", "hdd"))
        self.assertEqual("Seagate 4TB HDD", server.danawa_query_for_part("Seagate 4TB", "hdd"))

    def test_runtime_extended_categories_and_gpu_rejections_remain_runtime_only(self):
        self.assertTrue(crawler.danawa_category_matches("hdd", "SSD"))
        self.assertFalse(server.danawa_category_matches("hdd", "SSD"))
        self.assertFalse(crawler.danawa_name_rejected("gpu", "ASUS RTX 4070 냉각"))
        self.assertTrue(server.danawa_name_rejected("gpu", "ASUS RTX 4070 냉각"))

    def test_both_price_parsers_reject_sub_thousand_and_keep_won_digits(self):
        for raw, expected in [("999원", None), ("1,000원", 1000), ("₩ 123,456", 123456), ("", None)]:
            with self.subTest(raw=raw):
                self.assertEqual(expected, crawler.parse_price_value(raw))
                self.assertEqual(expected, metadata.parse_price_value(raw))

    def test_model_tokens_keep_the_adapters_distinct_preprocessing(self):
        self.assertEqual({"i512400fprocessor"}, crawler.product_model_tokens("i5-12400Fprocessor"))
        self.assertEqual({"i512400f", "12400f"}, metadata.model_tokens("i5-12400Fprocessor"))


if __name__ == "__main__":
    unittest.main()
