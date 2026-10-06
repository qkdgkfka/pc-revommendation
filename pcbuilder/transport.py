"""Prepared HTTP responses, content negotiation and confined static assets."""
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlparse
from typing import Any, Dict
import gzip
import hashlib
import json
import re

from . import runtime as state
from . import utils
from .cache import MemoryCache
from .revisions import file_stamp

_static_cache = MemoryCache(max_entries=128, max_bytes=32 * 1024 * 1024)


def weak_etag(raw):
    return 'W/"' + hashlib.sha256(raw).hexdigest() + '"'


def accepts_gzip(handler):
    header = str(getattr(handler, 'headers', {}).get('Accept-Encoding', '') or '')
    qualities = {}
    for item in header.lower().split(','):
        parts = [piece.strip() for piece in item.split(';')]
        quality = 1.0
        for parameter in parts[1:]:
            if parameter.startswith('q='):
                try:
                    quality = float(parameter[2:])
                except ValueError:
                    quality = 0
        qualities[parts[0]] = quality
    return qualities.get('gzip', qualities.get('*', 0)) > 0


def _send_bytes(handler, status, raw, content_type, cache_control='no-store', compressed=None, conditional=False, etag=None):
    zipped = compressed is not None and accepts_gzip(handler)
    data = compressed if zipped else raw
    # Weak validators represent the same document with either content encoding.
    etag = (etag or weak_etag(raw)) if conditional else None
    matched = False
    if etag:
        candidates = str(getattr(handler, 'headers', {}).get('If-None-Match', '') or '').split(',')
        matched = any(value.strip() == '*' or value.strip().removeprefix('W/') == etag[2:] for value in candidates)
    handler.send_response(304 if matched and status == 200 else status)
    handler.send_header('Content-Type', content_type)
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Cache-Control', cache_control)
    handler.send_header('X-Content-Type-Options', 'nosniff')
    handler.send_header('Vary', 'Accept-Encoding')
    handler.send_header('Content-Length', str(len(data)))
    if zipped:
        handler.send_header('Content-Encoding', 'gzip')
    if etag:
        handler.send_header('ETag', etag)
    handler.end_headers()
    if not matched or status != 200:
        handler.wfile.write(data)


def send_json(handler: BaseHTTPRequestHandler, status: int, payload: Dict[str, Any], *, document=None) -> None:
    if document is not None:
        _, raw, zipped, etag = document
    else:
        etag = None
        raw = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        zipped = gzip.compress(raw, compresslevel=6, mtime=0) if len(raw) >= 512 else None
    catalog = urlparse(str(getattr(handler, 'path', '') or '')).path == '/api/catalog'
    _send_bytes(handler, status, raw, 'application/json; charset=utf-8',
                'private, no-cache' if catalog else 'no-store', zipped, conditional=catalog, etag=etag)


def send_static(handler, request_path):
    root = Path(state.STATIC_DIR).resolve()
    requested = unquote(request_path)
    if '\x00' in requested or '\\' in requested or '..' in requested.split('/'):
        _send_bytes(handler, 404, b'404 Not Found', 'text/plain; charset=utf-8')
        return
    if not root.is_dir() or (requested in {'', '/', '/index.html'} and not (root / 'index.html').is_file()):
        guidance = b'Frontend build missing. Run npm ci and npm run build, then start the server again.'
        _send_bytes(handler, 503, guidance, 'text/plain; charset=utf-8')
        return
    try:
        fp = (root / ('index.html' if requested in {'', '/'} else requested.lstrip('/'))).resolve(strict=True)
        fp.relative_to(root)
        if not fp.is_file():
            raise ValueError('Not a file')
    except (OSError, ValueError):
        _send_bytes(handler, 404, b'404 Not Found', 'text/plain; charset=utf-8')
        return
    content_type = utils.guess_mime(fp)
    text = content_type.startswith(('text/', 'application/javascript', 'application/json', 'image/svg+xml'))
    sidecar = fp.with_name(fp.name + '.gz')
    key = (file_stamp(fp), file_stamp(sidecar), content_type)

    def read():
        raw = fp.read_bytes()
        zipped = None
        if text:
            try:
                confined = sidecar.resolve(strict=True)
                confined.relative_to(root)
                candidate = confined.read_bytes()
                if gzip.decompress(candidate) == raw:
                    zipped = candidate
            except (OSError, ValueError, EOFError):
                pass
            if zipped is None and len(raw) >= 512:
                zipped = gzip.compress(raw, compresslevel=6, mtime=0)
        return raw, zipped, weak_etag(raw)

    try:
        raw, zipped, etag = _static_cache.get_or_compute(key, read, ttl=300,
                                                   size=lambda data: len(data[0]) + len(data[1] or b''))
    except OSError:
        _send_bytes(handler, 404, b'404 Not Found', 'text/plain; charset=utf-8')
        return
    hashed = requested.startswith('/assets/') and re.search(r'-[A-Za-z0-9_-]{8,}\.[A-Za-z0-9.]+$', fp.name)
    cache_control = 'public, max-age=31536000, immutable' if hashed else 'no-cache'
    _send_bytes(handler, 200, raw, content_type, cache_control, zipped, conditional=True, etag=etag)

