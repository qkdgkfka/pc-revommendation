"""Bounded, same-origin delivery of actual retailer product photographs."""
from collections import OrderedDict
from html.parser import HTMLParser
from threading import RLock
from time import monotonic
from urllib.parse import parse_qs, urljoin, urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


MAX_BYTES = 5 * 1024 * 1024
CACHE_BYTES = 24 * 1024 * 1024
CACHE_SECONDS = 6 * 60 * 60
_cache = OrderedDict()
_lock = RLock()
IMAGE_DOMAINS = (
    'danuri.io', 'danawa.com', 'compuzone.co.kr',
    'amd.com', 'nvidia.com', 'asus.com', 'msi.com', 'gigabyte.com', 'asrock.com',
    'samsung.com', 'skhynix.com', 'crucial.com', 'corsair.com', 'seasonic.com',
    'fsplifestyle.com', 'westerndigital.com', 'wd.com', 'kingston.com', 'teamgroupinc.com',
)


def retailer_image_url(value):
    """The public image endpoint must not become a general URL proxy."""
    try:
        parsed = urlparse(str(value or '').strip())
        host = (parsed.hostname or '').lower()
        allowed = any(host == domain or host.endswith('.' + domain)
                      for domain in IMAGE_DOMAINS)
        if (parsed.scheme not in ('http', 'https') or not allowed
                or parsed.username or parsed.password or parsed.port not in (None, 80, 443)):
            return ''
        return urlunparse(parsed._replace(scheme='https', netloc=host, fragment=''))
    except (ValueError, TypeError):
        return ''


def image_source_priority(url):
    host = urlparse(retailer_image_url(url)).hostname or ''
    if host == 'compuzone.co.kr' or host.endswith('.compuzone.co.kr'):
        return 0
    if any(host == domain or host.endswith('.' + domain) for domain in ('danawa.com', 'danuri.io')):
        return 1
    return 2


def product_page_key(value):
    """Identify the actual retailer SKU, independent of search/tracking parameters."""
    url = retailer_image_url(value)
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if parsed.hostname == 'prod.danawa.com' and parsed.path.rstrip('/') == '/info':
        code = params.get('pcode', [''])[0]
        return ('danawa', code) if code.isdigit() else None
    if parsed.hostname in ('www.compuzone.co.kr', 'compuzone.co.kr') and parsed.path == '/product/product_detail.htm':
        code = params.get('ProductNo', [''])[0]
        return ('compuzone', code) if code.isdigit() else None
    return None


class ProductPhotoParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.photos = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and (attrs.get('property') or attrs.get('name')) in ('og:image', 'twitter:image'):
            self.photos.append(attrs.get('content', ''))


def fetch_product_page_image(value):
    """Recover a changed/missing photo from a known sales page, even if sold out."""
    if not product_page_key(value):
        return ''
    url = retailer_image_url(value)
    try:
        with build_opener(RetailImageRedirect()).open(Request(url, headers={
            'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'ko-KR,ko;q=0.9',
        }), timeout=4) as response:
            if product_page_key(response.geturl()) != product_page_key(url):
                return ''
            raw = response.read(2 * 1024 * 1024)
            encoding = response.headers.get_content_charset() or ('euc-kr' if 'compuzone' in url else 'utf-8')
        parser = ProductPhotoParser()
        parser.feed(raw.decode(encoding, errors='replace'))
        for photo in parser.photos:
            image_url = retailer_image_url(urljoin(url, photo))
            if image_url and not any(token in image_url.lower() for token in ('noimg', 'noimage', 'no_img')):
                return image_url
    except (OSError, ValueError, LookupError):
        pass
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
    priority = image_source_priority(url)
    referer = ('https://www.compuzone.co.kr/' if priority == 0 else
               'https://prod.danawa.com/' if priority == 1 else f'https://{host}/')
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
