import argparse
import errno
import io
import unittest
from contextlib import redirect_stdout
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from pcbuilder import http, runtime


class ServerStartupTests(unittest.TestCase):
    def run_server_until_interrupt(self, port):
        servers = []

        def create_server(address, handler):
            server = ThreadingHTTPServer(address, handler)
            servers.append(server)
            self.addCleanup(server.server_close)
            return server

        args = argparse.Namespace(host='127.0.0.1', port=port, static_dir='dist')
        output = io.StringIO()
        with patch.object(http, 'parse_args', return_value=args), \
                patch.object(http.database, 'load_config'), \
                patch.object(http.database, 'load_db_cache'), \
                patch.object(runtime, 'STATIC_DIR', runtime.STATIC_DIR), \
                patch.object(http, 'ThreadingHTTPServer', side_effect=create_server), \
                patch.object(ThreadingHTTPServer, 'serve_forever', side_effect=KeyboardInterrupt), \
                redirect_stdout(output):
            try:
                http.main()
            except (OSError, KeyboardInterrupt) as error:
                self.fail('Server startup/stop must handle this: {!r}'.format(error))
        return servers, output.getvalue()

    def test_busy_port_starts_on_another_port_and_preserves_existing_listener(self):
        with ThreadingHTTPServer(('127.0.0.1', 0), http.Handler) as existing:
            port = existing.server_port
            servers, output = self.run_server_until_interrupt(port)
            self.assertEqual(1, len(servers))
            self.assertNotEqual(port, servers[0].server_port)
            self.assertGreater(servers[0].server_port, 0)
            self.assertIn('http://127.0.0.1:{}'.format(servers[0].server_port), output)
            self.assertGreaterEqual(existing.socket.fileno(), 0)
            self.assertEqual(-1, servers[0].socket.fileno())

    def test_port_zero_reports_actual_port_and_interrupt_releases_socket(self):
        servers, output = self.run_server_until_interrupt(0)
        self.assertGreater(servers[0].server_port, 0)
        self.assertIn('http://127.0.0.1:{}'.format(servers[0].server_port), output)
        self.assertNotIn('http://127.0.0.1:0', output)
        self.assertEqual(-1, servers[0].socket.fileno())

    def test_unrelated_bind_error_does_not_report_ready(self):
        output = io.StringIO()
        args = argparse.Namespace(host='127.0.0.1', port=4000, static_dir='dist')
        with patch.object(http, 'parse_args', return_value=args), \
                patch.object(http.database, 'load_config'), \
                patch.object(http.database, 'load_db_cache'), \
                patch.object(runtime, 'STATIC_DIR', runtime.STATIC_DIR), \
                patch.object(http, 'ThreadingHTTPServer', side_effect=OSError(errno.EACCES, 'denied')), \
                redirect_stdout(output):
            with self.assertRaises(OSError) as raised:
                http.main()
        self.assertEqual(errno.EACCES, raised.exception.errno)
        self.assertNotIn('Server ready.', output.getvalue())
        self.assertNotIn('Serving at', output.getvalue())
