"""Restricted retailer page lookup and confirmed local product storage."""
from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from threading import RLock
from urllib.parse import urljoin
from urllib.request import HTTPRedirectHandler, Request, build_opener
import json
import re

from product_images import product_page_key, retailer_image_url


IMPORT_PATH = Path(__file__).resolve().parent / "data" / "imported_products.json"
_lock = RLock()


def supported_product_url(value):
    """Only exact Compuzone/Danawa product detail URLs can trigger a fetch."""
    raw = str(value or "").strip()
    if len(raw) > 2048 or not raw.startswith("https://"):
        return ""
    url = retailer_image_url(raw)
    return url if product_page_key(url) else ""


class ProductRedirect(HTTPRedirectHandler):
    def __init__(self, key):
        self.key = key

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = supported_product_url(newurl)
        if not target or product_page_key(target) != self.key:
            raise ValueError("Product page redirected to another destination")
        return super().redirect_request(req, fp, code, msg, headers, target)


class ProductPageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.title = ""
        self.text = []
        self.jsonld = []
        self._capture = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or "").lower()
            if key and attrs.get("content"):
                self.meta[key] = unescape(attrs["content"]).strip()
        if tag == "title":
            self._capture = "title"
        elif tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self._capture = "jsonld"
        elif tag in ("script", "style"):
            self._capture = "skip"

    def handle_endtag(self, tag):
        if tag in ("title", "script", "style"):
            self._capture = ""

    def handle_data(self, data):
        if self._capture == "title":
            self.title += data
        elif self._capture == "jsonld":
            self.jsonld.append(data)
        elif not self._capture:
            value = " ".join(data.split())
            if value and len(value) < 300:
                self.text.append(value)


def _jsonld_product(chunks):
    def walk(value):
        if isinstance(value, list):
            for item in value:
                yield from walk(item)
        elif isinstance(value, dict):
            if str(value.get("@type", "")).lower() == "product":
                yield value
            for child in value.values():
                if isinstance(child, (list, dict)):
                    yield from walk(child)
    for chunk in chunks:
        try:
            return next(walk(json.loads(chunk)))
        except (ValueError, StopIteration, TypeError):
            continue
    return {}


def parse_product_page(html, url):
    parser = ProductPageParser()
    parser.feed(html)
    structured = _jsonld_product(parser.jsonld)
    offers = structured.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        offers = {}
    image = structured.get("image") or parser.meta.get("og:image") or parser.meta.get("twitter:image") or ""
    if isinstance(image, list):
        image = image[0] if image else ""
    if isinstance(image, dict):
        image = image.get("url", "")
    image = retailer_image_url(urljoin(url, str(image))) if image else ""
    brand = structured.get("brand") or ""
    if isinstance(brand, dict):
        brand = brand.get("name", "")
    title = structured.get("name") or parser.meta.get("og:title") or parser.title
    title = re.sub(r"\s+", " ", unescape(str(title))).strip()
    price = offers.get("price") or parser.meta.get("product:price:amount") or parser.meta.get("og:price:amount")
    try:
        price = int(float(str(price).replace(",", "")))
    except (ValueError, TypeError):
        price = 0
    description = structured.get("description") or parser.meta.get("og:description") or ""
    spec = re.sub(r"\s+", " ", unescape(str(description) + " " + " ".join(parser.text[:180])))[:2500]
    return {"name": title, "brand": str(brand).strip(), "price": price if 1000 <= price <= 20_000_000 else 0,
            "image_url": image, "spec_text": spec, "url": url}


def fetch_product_page(value, timeout=6):
    url = supported_product_url(value)
    if not url:
        raise ValueError("Unsupported product URL")
    key = product_page_key(url)
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "ko-KR,ko;q=0.9", "Accept": "text/html"}
    with build_opener(ProductRedirect(key)).open(Request(url, headers=headers), timeout=timeout) as response:
        if product_page_key(response.geturl()) != key:
            raise ValueError("Product page changed identity")
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type:
            raise ValueError("Product URL did not return HTML")
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("Product page is too large")
        charset = response.headers.get_content_charset() or ("euc-kr" if key[0] == "compuzone" else "utf-8")
    return parse_product_page(raw.decode(charset, errors="replace"), url)


def imported_products(part_type=None):
    with _lock:
        try:
            payload = json.loads(IMPORT_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {} if part_type is None else []
    products = payload.get("products", {})
    if not isinstance(products, dict):
        return {} if part_type is None else []
    return products if part_type is None else list(products.get(part_type, []))


def save_imported_product(part, duplicate):
    """Atomic, idempotent insertion; duplicate is checked again under the lock."""
    with _lock:
        products = imported_products()
        for old in products.get(part["component_type"], []):
            if duplicate(old, part):
                return old, False
        products.setdefault(part["component_type"], []).append(part)
        IMPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = IMPORT_PATH.with_suffix(".tmp")
        temporary.write_text(json.dumps({"schema_version": 1, "products": products}, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(IMPORT_PATH)
        return part, True
