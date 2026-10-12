"""Bounded JSON decoding and browser-origin checks at the HTTP boundary."""
import json
import math
import re
from urllib.parse import urlsplit

from url_safety import safe_external_url

MAX_BODY_BYTES = 64 * 1024
MAX_JSON_DEPTH = 32
MAX_QUERY_FIELDS = 100
MAX_REQUEST_TARGET_LENGTH = 8192


class InvalidRequest(ValueError):
    def __init__(self, status=400, message='invalid request'):
        super().__init__(message)
        self.status = status


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise InvalidRequest()
    return number


def _bounded_int(value):
    if len(value) > 128:
        raise InvalidRequest()
    return int(value)


def _reject_constant(value):
    raise InvalidRequest()


def decode_json_object(raw):
    try:
        payload = json.loads(raw, parse_float=_finite_float,
                             parse_int=_bounded_int, parse_constant=_reject_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise InvalidRequest(message='invalid json') from None
    if not isinstance(payload, dict):
        raise InvalidRequest(message='JSON object required')
    pending = [(payload, 0)]
    while pending:
        value, depth = pending.pop()
        if depth > MAX_JSON_DEPTH:
            raise InvalidRequest(message='JSON nesting limit exceeded')
        if isinstance(value, dict):
            children = value.values()
        elif isinstance(value, list):
            children = value
        else:
            continue
        pending.extend((child, depth + 1) for child in children)
    return payload


def read_json_object(handler):
    headers = handler.headers
    if headers.get('Transfer-Encoding') is not None:
        raise InvalidRequest(message='unsupported transfer encoding')
    lengths = (headers.get_all('Content-Length', []) if hasattr(headers, 'get_all')
               else [headers.get('Content-Length')])
    if not lengths or lengths == [None]:
        raise InvalidRequest(411, 'content length required')
    if len(lengths) != 1 or not re.fullmatch(r'[0-9]{1,10}', lengths[0]):
        raise InvalidRequest(message='invalid content length')
    length = int(lengths[0])
    if length > MAX_BODY_BYTES:
        raise InvalidRequest(413, 'request body too large')
    if headers.get('Content-Type', '').split(';', 1)[0].strip().lower() != 'application/json':
        raise InvalidRequest(415, 'application/json required')
    raw = handler.rfile.read(length)
    if len(raw) != length:
        raise InvalidRequest(message='incomplete request body')
    return decode_json_object(raw)


def require_same_origin(headers):
    """Allow ordinary API clients and the same-origin Vite proxy, deny foreign pages."""
    if headers.get('Sec-Fetch-Site') in {'cross-site', 'same-site'}:
        raise InvalidRequest(403, 'cross-origin request denied')
    origin = headers.get('Origin')
    if origin is None:
        return
    if not safe_external_url(origin):
        raise InvalidRequest(403, 'cross-origin request denied')
    parsed = urlsplit(origin)
    authority = f'{parsed.scheme}://{headers.get("Host", "")}'
    if not safe_external_url(authority):
        raise InvalidRequest(403, 'cross-origin request denied')
    expected = urlsplit(authority)
    default_port = 443 if parsed.scheme == 'https' else 80
    origin_address = (parsed.hostname, parsed.port or default_port)
    expected_address = (expected.hostname, expected.port or default_port)
    if (parsed.path not in {'', '/'} or parsed.query or parsed.fragment
            or expected.path or expected.query or expected.fragment
            or origin_address != expected_address):
        raise InvalidRequest(403, 'cross-origin request denied')
