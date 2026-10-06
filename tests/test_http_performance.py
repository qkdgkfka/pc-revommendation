import gzip
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from pcbuilder import http, runtime, transport


class HttpPerformanceTests(unittest.TestCase):
    def test_warm_static_responses_reuse_validator_and_refresh_on_file_change(self):
        with patch.object(transport.hashlib, 'sha256', wraps=hashlib.sha256) as digest:
            first = self.request('/assets/app-B1234567.js')
            second = self.request('/assets/app-B1234567.js', {'If-None-Match': first[1]['ETag']})
            self.assertEqual(304, second[0])
            self.assertEqual(b'', second[2])
            self.assertEqual(1, digest.call_count)
            self.asset.write_bytes(b'const changed=true;')
            third = self.request('/assets/app-B1234567.js', {'If-None-Match': first[1]['ETag']})
            self.assertEqual(200, third[0])
            self.assertNotEqual(first[1]['ETag'], third[1]['ETag'])
            self.assertEqual(b'const changed=true;', third[2])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / 'dist'
        self.root.mkdir()
        (self.root / 'index.html').write_text('<html>' + 'test ' * 300 + '</html>')
        (self.root / 'assets').mkdir()
        self.asset = self.root / 'assets' / 'app-B1234567.js'
        self.asset.write_bytes(b'const app="' + b'a' * 2000 + b'";')
        self.asset.with_name(self.asset.name + '.gz').write_bytes(gzip.compress(self.asset.read_bytes(), mtime=0))
        (self.root.parent / 'secret.txt').write_text('private')
        (self.root / 'escape.txt').symlink_to(self.root.parent / 'secret.txt')
        self.static_patch = patch.object(runtime, 'STATIC_DIR', self.root)
        self.static_patch.start()
        self.addCleanup(self.static_patch.stop)

    def request(self, path, headers=None):
        handler = http.Handler.__new__(http.Handler)
        handler.path = path
        handler.headers = headers or {}
        handler.wfile = io.BytesIO()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.do_GET()
        return (handler.send_response.call_args.args[0],
                dict(call.args for call in handler.send_header.call_args_list),
                handler.wfile.getvalue())

    def test_static_traversal_and_symlink_cannot_escape_root(self):
        for path in ('/../secret.txt', '/%2e%2e/secret.txt', '/escape.txt'):
            with self.subTest(path=path):
                status, _, body = self.request(path)
                self.assertEqual(404, status)
                self.assertNotIn(b'private', body)

    def test_hashed_static_gzip_etag_and_conditional_response(self):
        status, headers, data = self.request('/assets/app-B1234567.js', {'Accept-Encoding': 'gzip'})
        self.assertEqual(200, status)
        self.assertEqual('gzip', headers.get('Content-Encoding'))
        self.assertEqual(self.asset.read_bytes(), gzip.decompress(data))
        self.assertEqual(str(len(data)), headers.get('Content-Length'))
        self.assertIn('immutable', headers.get('Cache-Control', ''))
        self.assertEqual('Accept-Encoding', headers.get('Vary'))
        status, _, data = self.request('/assets/app-B1234567.js', {'Accept-Encoding': 'gzip', 'If-None-Match': headers.get('ETag', '')})
        self.assertEqual(304, status)
        self.assertEqual(b'', data)

    def test_gzip_q_zero_is_respected_and_html_revalidates(self):
        status, headers, data = self.request('/', {'Accept-Encoding': 'gzip;q=0, *;q=1'})
        self.assertEqual(200, status)
        self.assertNotIn('Content-Encoding', headers)
        self.assertEqual((self.root / 'index.html').read_bytes(), data)
        self.assertIn('no-cache', headers.get('Cache-Control', ''))

    def test_json_gzip_and_no_store_preserve_payload(self):
        payload = {'ok': True, 'items': [{'name': '제품' * 50}] * 20}
        with patch.object(http.retail, 'market_products_response', return_value=payload):
            status, headers, data = self.request('/api/products?type=gpu', {'Accept-Encoding': 'gzip'})
        self.assertEqual(200, status)
        self.assertEqual('gzip', headers.get('Content-Encoding'))
        self.assertEqual(payload, json.loads(gzip.decompress(data)))
        self.assertEqual('no-store', headers.get('Cache-Control'))
        self.assertEqual(str(len(data)), headers.get('Content-Length'))

    def test_missing_dist_explains_build_and_health_still_works(self):
        with patch.object(runtime, 'STATIC_DIR', self.root / 'missing'):
            status, _, body = self.request('/')
            api_status, _, _ = self.request('/health')
        self.assertEqual(503, status)
        self.assertIn(b'npm ci', body)
        self.assertIn(b'npm run build', body)
        self.assertEqual(200, api_status)

    def test_empty_dist_also_explains_how_to_build(self):
        (self.root / 'index.html').unlink()
        status, _, body = self.request('/')
        self.assertEqual(503, status)
        self.assertIn(b'npm run build', body)


if __name__ == '__main__':
    unittest.main()
