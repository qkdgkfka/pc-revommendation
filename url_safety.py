"""Validate browser-facing URLs without treating them as safe fetch targets."""
import re
from urllib.parse import urlsplit

MAX_URL_LENGTH = 2048
_UNSAFE_CHARACTERS = re.compile(r'[\x00-\x20\x7f\\]')


def safe_external_url(value):
    """Return an absolute HTTP(S) link; outbound fetches need an allowlist too."""
    if not isinstance(value, str) or len(value) > MAX_URL_LENGTH:
        return ''
    raw = value.strip(' ')
    if not raw or _UNSAFE_CHARACTERS.search(raw):
        return ''
    try:
        parsed = urlsplit(raw)
        if (parsed.scheme not in {'http', 'https'} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None):
            return ''
        # Accessing port validates malformed and out-of-range authorities.
        if parsed.port == 0:
            return ''
    except ValueError:
        return ''
    return raw
