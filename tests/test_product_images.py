import io
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import product_images as images
import server_fixed as server


class ProductImageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        disk = patch.object(images, "DISK_CACHE_DIR", Path(self.directory.name))
        disk.start()
        self.addCleanup(disk.stop)
        images._cache.clear()
        server.IMAGE_URL_CACHE.clear()

    def test_disk_photo_survives_memory_cache_reset_without_network(self):
        url = "https://img.danuri.io/persist.jpg"
        data = b"\xff\xd8\xffreal-photo"
        images.persist_product_image(url, data)
        images._cache.clear()
        with patch.object(images, "build_opener", side_effect=AssertionError("network")):
            self.assertEqual((data, "image/jpeg"), images.fetch_product_image(url))

    def test_lazy_photo_wins_over_placeholder_src(self):
        html = '<img src="/images/noimg.gif" data-original="//img.danuri.io/ram.jpg">'
        self.assertEqual('https://img.danuri.io/ram.jpg', server.image_from_danawa_block(html, 'https://prod.danawa.com/'))

    def test_failed_lookup_can_be_retried(self):
        with patch.object(server, 'saved_products', return_value=[]), patch.object(server, 'fetch_market_top_product', side_effect=[None, {'image_url': 'https://img.danuri.io/psu.jpg'}]) as lookup:
            self.assertEqual('', server.resolve_part_image_url('Example PSU', 'psu'))
            self.assertEqual('https://img.danuri.io/psu.jpg', server.resolve_part_image_url('Example PSU', 'psu'))
            self.assertEqual(2, lookup.call_count)

    def test_saved_photo_does_not_require_fresh_price_search(self):
        photo = 'https://img.danuri.io/ssd.jpg'
        with patch.object(server, 'saved_products', return_value=[{'name': 'Samsung 990 PRO 1TB', 'image_url': photo, 'stale': True}]), patch.object(server, 'fetch_market_top_product') as lookup:
            self.assertEqual(photo, server.resolve_part_image_url('Samsung 990 PRO 1TB', 'storage'))
            lookup.assert_not_called()

    def test_untrusted_urls_and_redirects_are_rejected(self):
        for url in ('http://127.0.0.1/a', 'https://img.danuri.io.evil.test/a', 'https://user@img.danuri.io/a', 'https://img.danuri.io:8888/a', 'file:///test'):
            self.assertEqual('', images.retailer_image_url(url))
        with self.assertRaises(ValueError):
            images.RetailImageRedirect().redirect_request(None, None, 302, '', {}, 'http://127.0.0.1/a')

    def test_proxy_delivers_image_bytes_instead_of_redirect(self):
        handler = Mock()
        handler.wfile = io.BytesIO()
        data = b'\xff\xd8\xffphoto'
        with patch.object(server, 'fetch_product_image', return_value=(data, 'image/jpeg')):
            server.send_part_image(handler, {'name': 'RAM', 'type': 'ram', 'image_url': 'https://img.danuri.io/ram.jpg'})
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_any_call('Content-Type', 'image/jpeg')
        self.assertEqual(data, handler.wfile.getvalue())
        self.assertFalse(any(args[0] == 'Location' for args, kwargs in handler.send_header.call_args_list))

    def test_failure_placeholder_is_not_cached(self):
        handler = Mock()
        handler.wfile = io.BytesIO()
        with patch.object(server, 'resolve_part_image_url', return_value=''):
            server.send_part_image(handler, {'name': 'SSD', 'type': 'storage'})
        handler.send_header.assert_any_call('Cache-Control', 'no-store')

    def test_failed_server_fetch_offers_valid_photo_to_browser(self):
        handler = Mock(wfile=io.BytesIO())
        photo = 'https://img.danuri.io/ram.jpg'
        with patch.object(server, 'saved_products', return_value=[]), \
             patch.object(server, 'fetch_product_image', return_value=None), \
             patch.object(server, 'resolve_part_image_url', return_value=''):
            server.send_part_image(handler, {'name': 'Example RAM', 'type': 'ram', 'image_url': photo})
        handler.send_response.assert_called_once_with(302)
        handler.send_header.assert_any_call('Location', photo)
        handler.send_header.assert_any_call('Cache-Control', 'no-store')
        self.assertEqual(b'', handler.wfile.getvalue())

    def test_product_page_is_never_used_as_image_redirect(self):
        handler = Mock(wfile=io.BytesIO())
        page = 'https://prod.danawa.com/info/?pcode=123'
        with patch.object(server, 'saved_products', return_value=[]), \
             patch.object(server, 'fetch_product_image', return_value=None), \
             patch.object(server, 'resolve_part_image_url', return_value=''), \
             patch.object(server, 'fetch_product_page_image', return_value=''):
            server.send_part_image(handler, {'name': 'Example RAM', 'type': 'ram',
                                             'image_url': page, 'product_url': page})
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_any_call('Content-Type', 'image/svg+xml; charset=utf-8')

    def test_other_retail_page_is_not_used_as_image_redirect(self):
        handler = Mock(wfile=io.BytesIO())
        page = 'https://www.corsair.com/us/en/p/psu/example'
        with patch.object(server, 'saved_products', return_value=[]), \
             patch.object(server, 'fetch_product_image', return_value=None), \
             patch.object(server, 'resolve_part_image_url', return_value=''):
            server.send_part_image(handler, {'name': 'Example PSU', 'type': 'psu', 'image_url': page})
        handler.send_response.assert_called_once_with(200)

    def test_html_error_is_not_treated_as_product_image(self):
        self.assertEqual('', images.image_content_type(b'<html>Access denied</html>'))
        self.assertEqual('image/jpeg', images.image_content_type(b'\xff\xd8\xffphoto'))

    def test_saved_sku_url_ignores_search_parameters_and_translated_name(self):
        row = {'name': '삼성전자 SSD', 'url': 'https://prod.danawa.com/info/?pcode=123&keyword=SSD',
               'image_url': 'https://img.danuri.io/ssd.jpg'}
        with patch.object(server, 'saved_products', return_value=[row]):
            self.assertEqual(row['image_url'], server.resolve_part_image_url(
                'Samsung SSD', 'storage', 'https://prod.danawa.com/info/?pcode=123'))

    def test_reference_photo_matches_brand_model_and_capacity_without_price_lookup(self):
        rows = [
            {'name': '삼성전자 990 EVO Plus M.2 NVMe (2TB)', 'image_url': 'https://img.danuri.io/wrong.jpg'},
            {'name': '삼성전자 990 PRO M.2 NVMe (1TB)', 'image_url': 'https://img.danuri.io/pro.jpg'},
            {'name': '삼성전자 990 EVO Plus M.2 NVMe (1TB)', 'image_url': 'https://img.danuri.io/right.jpg'},
        ]
        with patch.object(server, 'saved_products', return_value=rows), patch.object(server, 'fetch_market_top_product', return_value=None):
            self.assertEqual(rows[2]['image_url'], server.resolve_part_image_url('Samsung 990 EVO Plus NVMe SSD 1TB', 'storage'))

    def test_compuzone_photo_is_preferred_and_failure_tries_next_source(self):
        rows = [
            {'name': 'Example SSD 1TB', 'image_url': 'https://img.danuri.io/ssd.jpg'},
            {'name': 'Example SSD 1TB', 'image_url': 'https://image3.compuzone.co.kr/ssd.jpg'},
        ]
        handler = Mock(wfile=io.BytesIO())
        data = b'\xff\xd8\xffreal-photo'
        def fetch(url):
            return (data, 'image/jpeg') if url == rows[0]['image_url'] else None
        with patch.object(server, 'saved_products', return_value=rows), patch.object(server, 'fetch_product_image', side_effect=fetch):
            self.assertEqual(rows[1]['image_url'], server.resolve_part_image_url('Example SSD 1TB', 'storage'))
            server.send_part_image(handler, {'name': 'Example SSD 1TB', 'type': 'storage'})
        self.assertEqual(data, handler.wfile.getvalue())

    def test_real_sku_does_not_borrow_photo_from_similar_product(self):
        row = {'name': 'Samsung 990 PRO 1TB', 'url': 'https://prod.danawa.com/info/?pcode=999',
               'image_url': 'https://img.danuri.io/wrong.jpg'}
        with patch.object(server, 'saved_products', return_value=[row]), patch.object(server, 'fetch_market_top_product', return_value=None):
            self.assertEqual('', server.resolve_part_image_url('Samsung 990 PRO 1TB', 'storage',
                             'https://prod.danawa.com/info/?pcode=123'))

    def test_compuzone_lazy_image_is_saved(self):
        from test_market_sources import compuzone_row
        html = compuzone_row().replace('src="https://image3.compuzone.co.kr/product.jpg"',
                                      'src="/noimg.gif" data-original="//image3.compuzone.co.kr/product.jpg"')
        items = server.parse_compuzone_browse_products(html, 'https://www.compuzone.co.kr/', 'gpu')
        self.assertEqual('https://image3.compuzone.co.kr/product.jpg', items[0]['image_url'])

    def test_official_image_is_accepted_without_opening_proxy_to_arbitrary_hosts(self):
        self.assertEqual('https://www.corsair.com/psu.png', images.retailer_image_url('https://www.corsair.com/psu.png'))
        self.assertEqual('', images.retailer_image_url('https://corsair.com.evil.test/psu.png'))


if __name__ == '__main__':
    unittest.main()
