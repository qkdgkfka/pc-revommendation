"""Bounded, same-origin delivery of actual retailer product photographs."""
from collections import OrderedDict
from threading import RLock
from time import monotonic
from urllib.parse import urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


MAX_BYTES = 5 * 1024 * 1024
CACHE_BYTES = 24 * 1024 * 1024
CACHE_SECONDS = 6 * 60 * 60
_cache = OrderedDict()
_lock = RLock()


def retailer_image_url(value):
    """The public image endpoint must not become a general URL proxy."""
    try:
        parsed = urlparse(str(value or '').strip())
        host = (parsed.hostname or '').lower()
        allowed = any(host == domain or host.endswith('.' + domain)
                      for domain in ('danuri.io', 'danawa.com', 'compuzone.co.kr'))
        if (parsed.scheme not in ('http', 'https') or not allowed
                or parsed.username or parsed.password or parsed.port not in (None, 80, 443)):
            return ''
        return urlunparse(parsed._replace(scheme='https', netloc=host, fragment=''))
    except (ValueError, TypeError):
        return ''


class RetailImageRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = retailer_image_url(newurl)
        if not target:
            raise ValueError('Non-retailer image redirect')
        return super().redirect_request(req, fp, code, msg, headers, target)


def image_content_type(data):
    if data.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if data.startswith((b'GIF87a', b'GIF89a')):
        return 'image/gif'
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return 'image/webp'
    if data[4:8] == b'ftyp' and data[8:12] in (b'avif', b'avis'):
        return 'image/avif'
    return ''


def fetch_product_image(value):
    url = retailer_image_url(value)
    if not url:
        return None
    with _lock:
        cached = _cache.get(url)
        if cached and monotonic() - cached[0] < CACHE_SECONDS:
            _cache.move_to_end(url)
            return cached[1], cached[2]
        _cache.pop(url, None)
    host = urlparse(url).hostname or ''
    referer = 'https://www.compuzone.co.kr/' if host.endswith('compuzone.co.kr') else 'https://prod.danawa.com/'
    request = Request(url, headers={
        'User-Agent': 'Mozilla/5.0', 'Referer': referer,
        'Accept': 'image/avif,image/webp,image/png,image/jpeg,image/*;q=0.8',
    })
    try:
        with build_opener(RetailImageRedirect()).open(request, timeout=5) as response:
            if not retailer_image_url(response.geturl()):
                return None
            data = response.read(MAX_BYTES + 1)
        content_type = image_content_type(data)
        if not content_type or len(data) > MAX_BYTES:
            return None
    except (OSError, ValueError):
        # A transient failure never replaces an image with a cached placeholder.
        return None
    with _lock:
        _cache[url] = (monotonic(), data, content_type)
        while len(_cache) > 256 or sum(len(item[1]) for item in _cache.values()) > CACHE_BYTES:
            _cache.popitem(last=False)
    return data, content_type
