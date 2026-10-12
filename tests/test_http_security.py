"""Exercise untrusted HTTP input before it reaches application services."""
import io
import json
import unittest
from email.message import Message
from unittest.mock import Mock, patch

from pcbuilder import http
from product_images import retailer_image_url
from product_import import ProductRedirect


class HttpSecurityTests(unittest.TestCase):
    def request(self, method='POST', path='/api/recommend', body=b'{}', headers=None):
        handler = http.Handler.__new__(http.Handler)
        handler.path = path
        handler.headers = Message()
        for key, value in (headers if headers is not None else {
            'Content-Length': str(len(body)), 'Content-Type': 'application/json',
        }).items():
            handler.headers[key] = value
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        getattr(handler, 'do_' + method)()
        return (handler.send_response.call_args.args[0],
                dict(call.args for call in handler.send_header.call_args_list),
                handler.wfile.getvalue())

    def test_json_must_be_an_object_with_finite_numbers(self):
        for raw in (b'null', b'[]', b'"text"', b'1', b'{"budget":NaN}',
                    b'{"budget":Infinity}', b'{"budget":1e999}'):
            with self.subTest(raw=raw), patch.object(http.recommendation, 'recommend', return_value={'ok': True}):
                status, _, _ = self.request(body=raw)
                self.assertEqual(400, status)

    def test_oversized_body_is_rejected_before_reading(self):
        with patch.object(http.recommendation, 'recommend', return_value={'ok': True}):
            status, _, _ = self.request(headers={
                'Content-Length': '1000000', 'Content-Type': 'application/json',
            })
        self.assertEqual(413, status)

    def test_invalid_framing_is_rejected(self):
        for extra in ({'Content-Length': '-1'}, {'Content-Length': 'abc'},
                      {'Transfer-Encoding': 'chunked', 'Content-Length': '2'}):
            with self.subTest(extra=extra), patch.object(http.recommendation, 'recommend', return_value={}):
                status, _, _ = self.request(headers={'Content-Type': 'application/json', **extra})
                self.assertEqual(400, status)

    def test_content_length_is_required(self):
        with patch.object(http.recommendation, 'recommend', return_value={}):
            status, _, _ = self.request(headers={'Content-Type': 'application/json'})
        self.assertEqual(411, status)

    def test_non_json_content_type_is_rejected(self):
        with patch.object(http.recommendation, 'recommend', return_value={}):
            status, _, _ = self.request(headers={'Content-Length': '2', 'Content-Type': 'text/plain'})
        self.assertEqual(415, status)

    def test_deeply_nested_json_is_rejected(self):
        raw = b'{"items":' + b'[' * 80 + b'0' + b']' * 80 + b'}'
        with patch.object(http.recommendation, 'recommend', return_value={}):
            status, _, _ = self.request(body=raw)
        self.assertEqual(400, status)

    def test_valid_json_reaches_the_service_and_preserves_response(self):
        def recommend(body):
            return {'input': body, 'results': {}}
        raw = b'{"budget":1500000}'
        with patch.object(http.recommendation, 'recommend', side_effect=recommend):
            status, headers, body = self.request(body=raw)
        self.assertEqual(200, status)
        self.assertEqual({'input': {'budget': 1500000}, 'results': {}}, json.loads(body))
        self.assertNotIn('Access-Control-Allow-Origin', headers)

    def test_internal_exception_details_are_not_exposed(self):
        with self.assertLogs(http.logger, level='ERROR'), \
                patch.object(http.recommendation, 'recommend', side_effect=RuntimeError('secret database /private/db')):
            status, _, body = self.request()
        self.assertEqual(500, status)
        self.assertNotIn(b'secret', body)
        self.assertNotIn(b'/private', body)

    def test_invalid_fps_selection_returns_a_client_error(self):
        status, _, _ = self.request(path='/api/estimate-fps', body=b'{"gpu":"unknown"}')
        self.assertEqual(400, status)

    def test_cross_origin_browser_requests_are_rejected(self):
        for method, path in (('GET', '/health'), ('POST', '/api/recommend'), ('OPTIONS', '/api/recommend')):
            with self.subTest(method=method), patch.object(http.recommendation, 'recommend', return_value={}):
                status, _, _ = self.request(method, path, headers={
                    'Host': '127.0.0.1:4000', 'Origin': 'https://untrusted.example',
                    'Content-Length': '2', 'Content-Type': 'application/json',
                })
                self.assertEqual(403, status)

    def test_same_origin_and_development_proxy_requests_work(self):
        for authority in ('127.0.0.1:4000', 'localhost:5173'):
            with self.subTest(authority=authority), patch.object(http.recommendation, 'recommend', return_value={}):
                status, _, _ = self.request(headers={
                    'Host': authority, 'Origin': 'http://' + authority,
                    'Content-Length': '2', 'Content-Type': 'application/json',
                })
                self.assertEqual(200, status)

    def test_another_localhost_port_cannot_embed_api_requests(self):
        status, _, _ = self.request('GET', '/health', headers={
            'Host': 'localhost:4000', 'Sec-Fetch-Site': 'same-site',
        })
        self.assertEqual(403, status)

    def test_responses_have_security_headers(self):
        status, headers, _ = self.request('GET', '/health')
        self.assertEqual(200, status)
        self.assertEqual('nosniff', headers.get('X-Content-Type-Options'))
        self.assertIn("object-src 'none'", headers.get('Content-Security-Policy', ''))
        self.assertEqual('strict-origin-when-cross-origin', headers.get('Referrer-Policy'))

    def test_malformed_query_returns_a_client_error(self):
        status, _, _ = self.request('GET', '/api/products?' + '&'.join('x=1' for _ in range(150)))
        self.assertEqual(400, status)


class PreviewSecurityTests(unittest.TestCase):
    def test_non_product_urls_do_not_trigger_server_requests(self):
        for url in ('http://127.0.0.1/admin', 'http://169.254.169.254/latest/meta-data/',
                    'https://untrusted.example/', 'https://prod.danawa.com/bridge/go_link_goods.php?pcode=123'):
            with self.subTest(url=url), patch.object(http, 'fetch_product_page') as fetch, \
                    patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('Unexpected network request')) as network:
                result = http.page_preview_meta(url, 'Fallback')
                fetch.assert_not_called()
                network.assert_not_called()
                self.assertEqual('Fallback', result['title'])

    def test_supported_product_metadata_is_reused_without_caching_fallbacks(self):
        url = 'https://prod.danawa.com/info/?pcode=123456789123'
        with patch.object(http, 'fetch_product_page', return_value={
            'name': '', 'spec_text': 'Product details', 'image_url': '',
        }):
            first = http.page_preview_meta(url, 'First')
            second = http.page_preview_meta(url, 'Second')
        self.assertEqual('First', first['title'])
        self.assertEqual('Second', second['title'])
        self.assertEqual('Product details', second['description'])

    def test_safe_external_url_rejects_invalid_authority_and_control_characters(self):
        for url in ('https://', 'https://[broken', 'https://user:pass@example.com/',
                    'https://example.com:invalid/', 'https://example.com/\r\nInjected:1',
                    'javascript:alert(1)', 'https://example.com\\@127.0.0.1/'):
            with self.subTest(url=url):
                self.assertEqual('', http.safe_external_url(url))

    def test_retail_image_validation_does_not_silently_strip_control_characters(self):
        self.assertEqual('', retailer_image_url('https://img.danuri.io/photo.jpg\r\nX-Header:1'))

    def test_product_redirect_cannot_escape_retailer_or_change_sku(self):
        redirect = ProductRedirect(('danawa', '123'))
        for target in ('http://127.0.0.1/admin', 'https://prod.danawa.com/info/?pcode=999'):
            with self.subTest(target=target), self.assertRaises(ValueError):
                redirect.redirect_request(None, None, 302, '', {}, target)


if __name__ == '__main__':
    unittest.main()
