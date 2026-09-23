"""The runtime and offline crawler must retain the same HTML price extraction."""
import unittest
from unittest.mock import patch

import crawl_data as crawler
import server_fixed as server


class RetailerParserRegressionTests(unittest.TestCase):
    def test_both_adapters_choose_the_cheapest_valid_product(self):
        html = """
        <li class="prod_item"><p class="prod_name"><a href="/info/?pcode=101">FSP Hydro 750W</a></p>
          <input id="productItem_categoryInfo_101" value="파워">
          <input id="min_price_101" value="120000"></li>
        <li class="prod_item"><p class="prod_name"><a href="/info/?pcode=102">FSP Hydro 750W</a></p>
          <input id="productItem_categoryInfo_102" value="파워">
          <p class="price_sect"><strong>100,000</strong>원</p></li>
        """
        for adapter in (server, crawler):
            for soup in (adapter.BeautifulSoup, None):
                with self.subTest(adapter=adapter.__name__, regex=soup is None):
                    with patch.object(adapter, "BeautifulSoup", soup):
                        row = adapter.parse_danawa_top_product(
                            html, "https://prod.danawa.com/", "FSP Hydro 750W", "psu",
                        )
                    self.assertEqual("FSP Hydro 750W", row["name"])
                    self.assertEqual(100000, row["price"])
                    self.assertEqual("https://prod.danawa.com/info/?pcode=102", row["url"])

    def test_missing_price_does_not_borrow_from_the_next_product(self):
        html = """
        <li id="productItem_101"><p class="prod_name"><a href="/info/?pcode=101">FSP Hydro 750W</a></p></li>
        <li id="productItem_102"><p class="prod_name"><a href="/info/?pcode=102">FSP Hydro 750W</a></p>
          <input id="min_price_102" value="100000"></li>
        """
        for adapter in (server, crawler):
            with self.subTest(adapter=adapter.__name__):
                row = adapter.parse_danawa_top_product_regex(
                    html, "https://prod.danawa.com/", "FSP Hydro 750W", "psu",
                )
                self.assertEqual("https://prod.danawa.com/info/?pcode=102", row["url"])


if __name__ == "__main__":
    unittest.main()
