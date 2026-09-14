import io
import unittest
from unittest.mock import Mock, patch

import product_images as images
import server_fixed as server


class ProductImageTests(unittest.TestCase):
    def setUp(self):
        images._cache.clear()
        server.IMAGE_URL_CACHE.clear()

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

    def test_html_error_is_not_treated_as_product_image(self):
        self.assertEqual('', images.image_content_type(b'<html>Access denied</html>'))
        self.assertEqual('image/jpeg', images.image_content_type(b'\xff\xd8\xffphoto'))


if __name__ == '__main__':
    unittest.main()
