from backend_patch import patch_backend
"""Regression coverage for retailer SKU/price identity and honest availability."""
import importlib.util
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location('market_source_test_server', ROOT / 'server_fixed.py')
server = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = server
SPEC.loader.exec_module(server)


def danawa_group(category='storage', rows=None):
    category_id, label, name = {
        'storage': ('112760', 'PC 주요 부품_SSD', 'Samsung 990 PRO M.2 NVMe'),
        'cpu': ('113973', 'PC 주요 부품_CPU', '인텔 코어i5-14세대 14400F'),
    }[category]
    rows = rows or [('101', '1TB', 120000), ('102', '2TB', 210000)]
    options = ''.join(f'''<li id="productInfoDetail_{code}"><p class="price_sect">
       <a href="https://prod.danawa.com/info/?pcode={code}&amp;cate={category_id}"><strong>{price:,}</strong>원</a>
       </p><p class="memory_sect"><span class="rank">1위</span><span class="text">{label}</span></p></li>'''
       for code, label, price in rows)
    return f'''<div id="productListArea"><ul><li id="productItem101" data-product-order="1">
       <input id="productItem_categoryInfo_101" value="{label}">
       <input id="min_price_101" value="10000">
       <p class="prod_name"><a href="https://prod.danawa.com/info/?pcode=101&cate={category_id}">{name}</a></p>
       <img src="https://img.danuri.io/product.jpg"><div class="spec_list">1TB / 2TB / 최대 4TB</div>
       <div class="prod_pricelist"><ul>{options}</ul></div></li></ul>
       <a onclick="paging(2); return false;">2</a></div>'''


def compuzone_row(category='1016', name='[MSI] 지포스 RTX 5060 Ti D7 16GB'):
    return f'''<ul class="product_list"><li id="li-pno-123" idx="0">
       <a class="prd_info_main_img" href="../product/product_detail.htm?ProductNo=123&MediumDivNo={category}">
       <img src="https://image3.compuzone.co.kr/product.jpg"></a>
       <a href="../product/product_detail.htm?ProductNo=123&MediumDivNo={category}" class="prd_info_name prdTxt">{name}</a>
       <div class="prd_subTxt">16GB GDDR7</div>
       <div class="prd_price" data-price="620,000" data-discountprice="550,000">
       <strong>&#54;20,000</strong></div></li></ul>'''


class MarketplaceParserTests(unittest.TestCase):
    def test_modern_danawa_cards_keep_each_package_price_and_product_code(self):
        html = (ROOT / 'tests/fixtures/danawa_modern_search.html').read_text(encoding='utf-8')
        products = server.parse_danawa_browse_products(html, 'https://search.danawa.com/?query=CPU', 'cpu')
        self.assertEqual(['danawa_cpu_70531547', 'danawa_cpu_70679912'], [row['id'] for row in products])
        self.assertEqual([633970, 720000], [row['price'] for row in products])
        self.assertTrue(products[0]['name'].endswith('(멀티팩 정품)'))
        self.assertTrue(products[1]['name'].endswith('(정품)'))
        self.assertEqual('AM5', products[0]['socket'])
        self.assertEqual('https://img.danuri.io/catalog-image/cpu.jpeg', products[0]['image_url'])

    def test_modern_danawa_capacity_and_unpriced_options_cannot_borrow_other_prices(self):
        html = (ROOT / 'tests/fixtures/danawa_modern_search.html').read_text(encoding='utf-8')
        products = server.parse_danawa_browse_products(html, 'https://search.danawa.com/', 'storage')
        self.assertEqual([(120000, 1000), (210000, 2000)], [(row['price'], row['capacity']) for row in products])
        self.assertEqual(['danawa_storage_101', 'danawa_storage_102'], [row['id'] for row in products])

    def test_modern_option_without_its_own_label_does_not_take_a_siblings_label(self):
        html = '''<li data-product-seq="101"><p><a href="https://prod.danawa.com/info/?pcode=101&amp;cate=112760">Samsung 990 PRO</a></p><ul>
        <div><div><span class="truncate">1TB</span></div><div><a href="https://prod.danawa.com/info/?pcode=101&amp;cate=112760">120,000원</a></div></div>
        <div><div></div><div><a href="https://prod.danawa.com/info/?pcode=102&amp;cate=112760">210,000원</a></div></div>
        </ul></li>'''
        products = server.parse_danawa_browse_products(html, 'https://search.danawa.com/', 'storage')
        self.assertEqual(['danawa_storage_101'], [row['id'] for row in products])

    def test_danawa_variants_keep_their_own_price_capacity_and_sku(self):
        products = server.parse_danawa_browse_products(danawa_group(), 'https://search.danawa.com/', 'storage', 40)
        self.assertEqual([(120000, 1000), (210000, 2000)], [(p['price'], p['capacity']) for p in products])
        self.assertEqual(['danawa_storage_101', 'danawa_storage_102'], [p['id'] for p in products])
        self.assertTrue(products[1]['name'].endswith('(2TB)'))
        self.assertIn('pcode=102', products[1]['url'])
        self.assertEqual('verified', products[1]['price_status'])
        self.assertTrue(products[1]['price_checked_at'].endswith('Z'))

    def test_intel_cpu_category_and_package_are_selectable(self):
        products = server.parse_danawa_browse_products(danawa_group('cpu', [('101', '정품', 200000)]), 'https://search.danawa.com/', 'cpu')
        self.assertEqual(1, len(products))
        self.assertTrue(products[0]['name'].endswith('(정품)'))

    def test_danawa_rejects_other_category_and_spoofed_host(self):
        self.assertEqual([], server.parse_danawa_browse_products(danawa_group(), 'https://search.danawa.com/', 'ram'))
        forged = danawa_group().replace('prod.danawa.com', 'prod.danawa.com.example.org')
        self.assertEqual([], server.parse_danawa_browse_products(forged, 'https://search.danawa.com/', 'storage'))

    def test_compuzone_reads_public_price_and_thumbnail(self):
        items = server.parse_compuzone_browse_products(compuzone_row(), 'https://www.compuzone.co.kr/', 'gpu')
        self.assertEqual(1, len(items))
        self.assertEqual(620000, items[0]['price'])
        self.assertEqual(16, items[0]['vram'])
        self.assertEqual('Compuzone', items[0]['shop'])
        self.assertTrue(items[0]['image_url'].endswith('product.jpg'))

    def test_compuzone_rejects_wrong_category_and_accessories(self):
        self.assertEqual([], server.parse_compuzone_browse_products(compuzone_row('1013'), 'https://www.compuzone.co.kr/', 'gpu'))
        self.assertEqual([], server.parse_compuzone_browse_products(compuzone_row(name='RTX 5060 그래픽카드 지지대'), 'https://www.compuzone.co.kr/', 'gpu'))


class MarketplaceAvailabilityTests(unittest.TestCase):
    def setUp(self):
        server.MARKET_BROWSE_CACHE.clear()
        server.MARKET_SEARCH_CACHE.clear()
        self.persist = patch_backend(server, 'remember_products')
        self.persist.start()
        empty_saved = patch_backend(server, 'saved_products', return_value=[])
        empty_saved.start()
        self.addCleanup(empty_saved.stop)

    def tearDown(self):
        self.persist.stop()
        server.MARKET_BROWSE_CACHE.clear()
        server.MARKET_SEARCH_CACHE.clear()

    def test_filtering_rows_does_not_hide_upstream_next_page(self):
        with patch_backend(server, '_market_fetch_html', return_value=danawa_group()):
            result = server._market_source_page('storage', 'Samsung 990 PRO 2TB', 1, 40, 'danawa')
        self.assertTrue(result['has_more'])
        self.assertEqual('live', result['status'])
        self.assertEqual(1, len(result['items']))
        self.assertEqual(210000, result['items'][0]['price'])

    def test_modern_danawa_search_is_live_and_keeps_its_next_page(self):
        html = (ROOT / 'tests/fixtures/danawa_modern_search.html').read_text(encoding='utf-8')
        with patch_backend(server, '_market_fetch_html', return_value=html):
            result = server._market_source_page('cpu', '', 1, 40, 'danawa')
        self.assertEqual('live', result['status'])
        self.assertTrue(result['has_more'])
        self.assertEqual(2, len(result['items']))

    def test_modern_search_taking_five_seconds_can_finish_within_the_product_deadline(self):
        html = (ROOT / 'tests/fixtures/danawa_modern_search.html').read_text(encoding='utf-8')
        def fetch(url, provider, timeout=8):
            # The external service needs five seconds to transfer its larger
            # rendered page; no real network or delay is needed in this test.
            if timeout < 5:
                raise TimeoutError('The read operation timed out')
            return html
        with patch_backend(server, '_market_fetch_html', side_effect=fetch):
            result = server.market_products_response('cpu', source='danawa', persist=False)
        self.assertTrue(result['ok'])
        self.assertEqual('live', result['status'])
        self.assertEqual(2, len(result['items']))

    def test_modern_merchant_only_page_is_recognized_without_inventing_catalog_skus(self):
        html = '''<div id="searchProductArea"></div><ul><li class="border-b">
        <p><a href="https://prod.danawa.com/bridge/go_link_goods.php?cmpny_c=EE128&amp;link_prod_c=3509600922&amp;cate=112753">MSI Gaming GeForce RTX 4070 Ti</a></p>
        <span>1,793,000원</span></li></ul><nav aria-label="페이지 네비게이션">
        <button aria-label="페이지 4">4</button></nav>'''
        with patch_backend(server, '_market_fetch_html', return_value=html):
            result = server._market_source_page('gpu', '4070', 3, 40, 'danawa')
        self.assertEqual('empty', result['status'])
        self.assertEqual([], result['items'])
        self.assertTrue(result['has_more'])
        self.assertNotIn('error_kind', result)

    def test_modern_page_group_boundary_uses_only_an_enabled_next_group(self):
        for disabled, expected in [('', True), (' disabled=""', False)]:
            with self.subTest(disabled=bool(disabled)):
                html = f'''<div id="searchProductArea"></div><ul><li>
                <a href="https://prod.danawa.com/bridge/go_link_goods.php?link_prod_c=3509600922">MSI RTX 4070 Ti</a>
                </li></ul><nav aria-label="페이지 네비게이션">
                <button aria-label="페이지 10">10</button>
                <button{disabled} aria-label="다음 페이지 그룹">다음</button></nav>'''
                with patch_backend(server, '_market_fetch_html', return_value=html):
                    result = server._market_source_page('gpu', '4070', 10, 40, 'danawa', refresh=True)
                self.assertEqual(expected, result['has_more'])

    def test_block_or_timeout_is_unavailable_and_never_a_verified_price(self):
        with patch_backend(server, '_market_fetch_html', return_value='<html>Service unavailable</html>'):
            result = server.market_products_response('gpu', '', 1, 40, False, 'danawa')
        self.assertFalse(result['ok'])
        self.assertEqual('unavailable', result['status'])
        self.assertEqual([], result['items'])

    def test_old_cache_on_network_failure_is_explicitly_stale(self):
        with patch_backend(server, '_market_fetch_html', return_value=danawa_group()):
            server.market_products_response('storage', '', 1, 40, False, 'danawa')
        for cached in server.MARKET_BROWSE_CACHE.values():
            cached['fetched_at'] = datetime.utcnow() - timedelta(minutes=10)
        server.MARKET_SEARCH_CACHE.clear()
        with patch_backend(server, '_market_fetch_html', side_effect=TimeoutError):
            result = server.market_products_response('storage', '', 1, 40, False, 'danawa')
        self.assertEqual('stale', result['status'])
        self.assertEqual('stale', result['items'][0]['price_status'])
        self.assertFalse(result['items'][0]['price_verified'])

    def test_compuzone_page_offset_does_not_skip_fixed_twenty_row_batch(self):
        with patch_backend(server, '_market_fetch_html', return_value=compuzone_row()) as fetch:
            server._market_source_page('gpu', '', 2, 20, 'compuzone')
        self.assertIn('StartNum=20', fetch.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
