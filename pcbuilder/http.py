"""HTTP routes, catalog, images and preview responses."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse
from urllib.request import Request, urlopen
import argparse
from datetime import datetime
from html import escape
import json
import re
import traceback
import copy
import gzip
from product_filters import (
    enrich as enrich_product,
    facets as product_facets,
    FIELDS as PRODUCT_FILTER_FIELDS,
)
from market_catalog import saved_products
from product_metadata import (
    GPU_MAKER_LABELS,
    canonical_name,
    clean_visible_text,
    compatible_price_name,
    gpu_maker_label,
    image_name_tokens,
    normalize_browse_part_type,
    normalize_text,
)
from product_images import (
    fetch_product_image,
    retailer_image_url,
    image_source_priority,
    product_page_key,
    fetch_product_page_image,
)
from product_import import fetch_product_page, imported_products, supported_product_url
from typing import Any, Dict, Iterable, List
from server_catalogs import (
    CPU_CATALOG,
    GPU_CATALOG,
    RAM_CATALOG,
    MB_CATALOG,
    PSU_CATALOG,
    STORAGE_CATALOG,
    HDD_CATALOG,
    CASE_CATALOG,
    SOFTWARE_CATALOG,
    CATALOGS,
    GAME_OPTIONS,
    WORK_PROFILES,
)
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
from . import runtime as state
from . import database
from . import fps as fps_service
from . import pricing
from . import recommendation
from . import retail
from .transport import send_json, send_static, weak_etag
from .cache import MemoryCache
from .revisions import data_revision, fingerprint, freshness_ttl

_catalog_cache = MemoryCache(max_entries=8, max_bytes=16 * 1024 * 1024)


def _catalog_document(compact=False):
    database.ensure_db_cache_loaded()
    key = (bool(compact), data_revision(), fingerprint(CATALOGS),
           id(saved_products), id(imported_products), id(pricing.summarize_part),
           id(enrich_product), id(product_facets))

    def prepare():
        payload = _catalog_response_uncached(compact)
        raw = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        return payload, raw, gzip.compress(raw, compresslevel=6, mtime=0), weak_etag(raw)

    return _catalog_cache.get_or_compute(
        key, prepare, ttl=lambda entry: freshness_ttl(entry[0]),
        size=lambda entry: len(entry[1]) + len(entry[2]))


def catalog_response(compact: bool = False) -> Dict[str, Any]:
    return copy.deepcopy(_catalog_document(compact)[0])


def _catalog_response_uncached(compact: bool = False) -> Dict[str, Any]:
    def catalog_part(part: Dict[str, Any], part_type: str) -> Dict[str, Any]:
        return enrich_product({**part, **pricing.summarize_part(part, part_type)}, part_type)

    response = {
        "gpus": [catalog_part(p, "gpu") for p in GPU_CATALOG],
        "cpus": [catalog_part(p, "cpu") for p in CPU_CATALOG],
        "rams": [catalog_part(p, "ram") for p in RAM_CATALOG],
        "storages": [catalog_part(p, "storage") for p in STORAGE_CATALOG],
        "hdds": [catalog_part(p, "hdd") for p in HDD_CATALOG],
        "mbs": [catalog_part(p, "mb") for p in MB_CATALOG],
        "psus": [catalog_part(p, "psu") for p in PSU_CATALOG],
        "cases": [catalog_part(p, "case") for p in CASE_CATALOG],
        "software": [catalog_part(p, "software") for p in SOFTWARE_CATALOG],
        "gpu_makers": [{"id": key, "label": gpu_maker_label(key)} for key in GPU_MAKER_LABELS],
        "games": GAME_OPTIONS,
        "work_profiles": [
            {"id": key, "label": value["label"], "group": value["group"]}
            for key, value in WORK_PROFILES.items()
        ],
        "db_loaded": state.DB_CACHE.get("loaded", False),
        "db_summary": state.DB_CACHE.get("summary", {}),
    }
    # Retail SKUs extend the browser while the curated reference models keep
    # recommendation/FPS calibration stable. Saved prices retain their age.
    catalog_keys = {
        "gpu": "gpus", "cpu": "cpus", "ram": "rams", "storage": "storages",
        "hdd": "hdds", "mb": "mbs", "psu": "psus", "case": "cases",
        "software": "software",
    }
    response["filter_facets"] = {}
    for part_type, key in catalog_keys.items():
        retail = saved_products(part_type)
        response["filter_facets"][part_type] = product_facets(part_type, retail + response[key])
        if compact:
            continue
        known = {part["id"] for part in response[key]}
        response[key].extend(part for part in retail if part["id"] not in known)
        known.update(part["id"] for part in retail)
        response[key].extend(part for part in imported_products(part_type) if part.get("id") not in known)
    response["catalog_sizes"] = {kind: len(response[key]) for kind, key in catalog_keys.items()}
    response["reference_catalog_sizes"] = {kind: len(items) for kind, items in CATALOGS.items()}
    return response


def safe_external_url(url: Any) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        return ""
    return raw

def saved_part_image_urls(name: Any, part_type: Any, product_url: str = "") -> List[str]:
    ctype = normalize_browse_part_type(part_type)
    sku = product_page_key(product_url)
    requested = image_name_tokens(name, ctype)
    exact, matched = [], []
    for item in saved_products(ctype):
        url = retailer_image_url(item.get("image_url"))
        if not url:
            continue
        listed_name = item.get("product_name") or item.get("name")
        if ctype == "ram" and not retail.market_component_name_valid(ctype, listed_name or ""):
            continue
        if sku:
            if product_page_key(item.get("url")) == sku:
                exact.append(url)
        elif canonical_name(listed_name) == canonical_name(name):
            exact.append(url)
        elif requested and any(re.search(r"\d", token) for token in requested):
            listed = image_name_tokens(listed_name, ctype)
            if requested.issubset(listed):
                if ctype in {"gpu", "ram"} and not compatible_price_name(name, listed_name):
                    continue
                if ctype == "storage" and (requested & {"pro", "evo", "plus"}) != (listed & {"pro", "evo", "plus"}):
                    continue
                # Capacity/model suffix tokens must agree, even when the
                # retailer appends distributor or package descriptions.
                capacities = lambda tokens: {t for t in tokens if re.fullmatch(r"\d+(?:gb|tb|w)|kit\d+x\d+", t)}
                if capacities(requested) == capacities(listed):
                    matched.append(url)
    return sorted(set(exact or matched), key=lambda url: (image_source_priority(url), url))

def resolve_part_image_url(name: Any, part_type: Any = "", product_url: str = "", excluded=()) -> str:
    clean_name = clean_visible_text(name)
    if not clean_name:
        return ""
    key = (normalize_text(part_type), canonical_name(clean_name), product_page_key(product_url))
    cached = state.IMAGE_URL_CACHE.get(key)
    candidates = saved_part_image_urls(clean_name, part_type, product_url)
    if cached:
        candidates.append(cached)
    for url in sorted(set(candidates), key=lambda value: (image_source_priority(value), value)):
        if url not in excluded:
            state.IMAGE_URL_CACHE[key] = url
            return url
    # A known SKU is recovered from its own sales page in send_part_image.
    # Do not replace it with another product returned by a price search.
    if product_page_key(product_url) or excluded:
        return ""
    try:
        live = retail.fetch_market_top_product(clean_name, part_type, timeout=3.0)
        image_url = retailer_image_url((live or {}).get("image_url"))
    except Exception:
        image_url = ""
    if image_url:
        if len(state.IMAGE_URL_CACHE) >= 2048:
            state.IMAGE_URL_CACHE.pop(next(iter(state.IMAGE_URL_CACHE)))
        state.IMAGE_URL_CACHE[key] = image_url
    return image_url

def placeholder_svg(name: Any) -> bytes:
    label = escape(clean_visible_text(name)[:28] or "PC Part")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="320" height="240" viewBox="0 0 320 240">
<rect width="320" height="240" rx="24" fill="#eef4ff"/>
<rect x="68" y="50" width="184" height="112" rx="18" fill="#d9e6ff"/>
<rect x="92" y="78" width="136" height="18" rx="9" fill="#0052cc" opacity=".36"/>
<rect x="104" y="110" width="112" height="14" rx="7" fill="#0052cc" opacity=".24"/>
<text x="160" y="191" text-anchor="middle" font-family="system-ui, sans-serif" font-size="14" font-weight="700" fill="#0052cc">{label}</text>
<text x="160" y="218" text-anchor="middle" font-family="system-ui, sans-serif" font-size="13" fill="#526580">대표 이미지 없음</text>
</svg>"""
    return svg.encode("utf-8")

def send_part_image(handler: BaseHTTPRequestHandler, params: Dict[str, str]) -> None:
    name = params.get("name") or ""
    part_type = params.get("type") or ""
    product_url = params.get("product_url") or ""
    supplied_url = retailer_image_url(params.get("image_url"))
    if supplied_url and (product_page_key(supplied_url) or supplied_url == retailer_image_url(product_url)):
        supplied_url = ""
    candidates = saved_part_image_urls(name, part_type, product_url)
    if supplied_url:
        candidates.append(supplied_url)
    result = None
    browser_fallback_url = ""
    tried = set()
    for url in sorted(set(candidates), key=lambda value: (image_source_priority(value), value))[:3]:
        tried.add(url)
        result = fetch_product_image(url)
        if result:
            break
        if not browser_fallback_url:
            browser_fallback_url = url
    if result is None:
        resolved_url = resolve_part_image_url(name, part_type, product_url, tried)
        if resolved_url and resolved_url not in tried:
            tried.add(resolved_url)
            result = fetch_product_image(resolved_url)
            if not result and not browser_fallback_url:
                browser_fallback_url = resolved_url
    if result is None and product_page_key(product_url):
        recovered_url = fetch_product_page_image(product_url)
        if recovered_url and recovered_url not in tried:
            result = fetch_product_image(recovered_url)
            if result:
                state.IMAGE_URL_CACHE[(normalize_text(part_type), canonical_name(name), product_page_key(product_url))] = recovered_url
            elif not browser_fallback_url:
                browser_fallback_url = recovered_url
    if result is None and browser_fallback_url and re.search(r"\.(?:jpe?g|png|gif|webp|avif)$", urlparse(browser_fallback_url).path, re.I):
        handler.send_response(302)
        handler.send_header("Location", browser_fallback_url)
        handler.send_header("Cache-Control", "no-store")
        handler.send_header("Content-Length", "0")
        handler.end_headers()
        return
    data, content_type = result if result else (placeholder_svg(name), "image/svg+xml; charset=utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Cache-Control", "public, max-age=21600" if result else "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)

def meta_content_from_soup(soup: Any, names: Iterable[str]) -> str:
    if soup is None:
        return ""
    for name in names:
        node = soup.select_one(f"meta[property='{name}'], meta[name='{name}']")
        if node and node.get("content"):
            return clean_visible_text(node.get("content"))
    return ""

def page_preview_meta(url: str, fallback_name: str = "", fallback_image: str = "") -> Dict[str, str]:
    target = safe_external_url(url)
    if not target:
        return {"url": "", "title": clean_visible_text(fallback_name) or "미리보기", "description": "", "image_url": safe_external_url(fallback_image), "domain": ""}
    if target in state.PREVIEW_CACHE:
        cached = state.PREVIEW_CACHE[target]
        return {**cached, "image_url": cached.get("image_url") or safe_external_url(fallback_image)}

    title = clean_visible_text(fallback_name)
    description = ""
    image_url = safe_external_url(fallback_image)
    try:
        req = Request(target, headers=state.DANAWA_HEADERS)
        with urlopen(req, timeout=3.0) as resp:
            raw = resp.read(250000)
            charset = resp.headers.get_content_charset() or "utf-8"
        html = raw.decode(charset, errors="ignore")
        if BeautifulSoup is not None:
            soup = BeautifulSoup(html, "html.parser")
            og_title = meta_content_from_soup(soup, ["og:title", "twitter:title"])
            if og_title:
                title = og_title
            elif soup.title and soup.title.string:
                title = clean_visible_text(soup.title.string)
            description = meta_content_from_soup(soup, ["og:description", "description", "twitter:description"])
            image_url = image_url or retail.absolute_image_url(meta_content_from_soup(soup, ["og:image", "twitter:image"]), target)
        else:
            m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
            if m:
                title = clean_visible_text(re.sub(r"<[^>]+>", " ", m.group(1)))
            m = re.search(r"<meta[^>]+(?:property|name)=[\"'](?:og:image|twitter:image)[\"'][^>]+content=[\"']([^\"']+)[\"']", html, re.I)
            if m:
                image_url = image_url or retail.absolute_image_url(m.group(1), target)
    except Exception:
        pass

    parsed = urlparse(target)
    out = {
        "url": target,
        "title": title or clean_visible_text(fallback_name) or parsed.netloc,
        "description": description,
        "image_url": image_url,
        "domain": parsed.netloc.replace("www.", ""),
    }
    state.PREVIEW_CACHE[target] = out
    return out

def send_page_preview(handler: BaseHTTPRequestHandler, params: Dict[str, str]) -> None:
    meta = page_preview_meta(params.get("url") or "", params.get("name") or "", params.get("image") or "")
    price = clean_visible_text(params.get("price") or "")
    img_html = f'<img src="{escape(meta["image_url"])}" alt=""/>' if meta.get("image_url") else f'<img src="/api/part-image?{urlencode({"name": meta.get("title", "")})}" alt=""/>'
    link = escape(meta.get("url") or "#")
    html = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>
*{{box-sizing:border-box}}body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#fff;color:#10203f}}
.wrap{{width:100%;height:100%;padding:10px}}
.card{{border:1px solid #dbe5f5;border-radius:14px;overflow:hidden;box-shadow:0 10px 30px rgba(0,30,80,.14);background:#fff}}
.img{{height:132px;background:#eef4ff;display:flex;align-items:center;justify-content:center}}
.img img{{max-width:100%;max-height:132px;object-fit:contain;display:block}}
.body{{padding:10px 12px}}
.domain{{font-size:10px;font-weight:800;color:#0052cc;margin-bottom:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.title{{font-size:13px;font-weight:900;line-height:1.35;max-height:38px;overflow:hidden}}
.desc{{font-size:11px;color:#667799;line-height:1.35;max-height:30px;overflow:hidden;margin-top:5px}}
.price{{font-size:12px;font-weight:900;color:#0052cc;margin-top:7px}}
.open{{display:block;margin-top:8px;font-size:11px;font-weight:800;color:#0052cc;text-decoration:none}}
</style></head><body><div class="wrap"><div class="card">
<div class="img">{img_html}</div><div class="body">
<div class="domain">{escape(meta.get("domain") or "preview")}</div>
<div class="title">{escape(meta.get("title") or "미리보기")}</div>
{f'<div class="desc">{escape(meta.get("description") or "")}</div>' if meta.get("description") else ""}
{f'<div class="price">{escape(price)}</div>' if price else ""}
<a class="open" href="{link}" target="_blank" rel="noopener noreferrer">상품 페이지 열기</a>
</div></div></div></body></html>"""
    data = html.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "public, max-age=900")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A003
        return

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        params = {k: v for k, v in parse_qsl(parsed.query, keep_blank_values=True)}

        if path == "/health":
            payload = {
                "model_loaded": state.MODEL_LOADED,
                "engine": "sqlite_hybrid_v1",
                "db_loaded": state.DB_CACHE.get("loaded", False),
                "catalog_sizes": {k: len(v) for k, v in CATALOGS.items()},
                "db_summary": state.DB_CACHE.get("summary", {}),
            }
            send_json(self, 200, payload)
            return

        if path == "/api/catalog":
            document = _catalog_document(compact=params.get("compact") == "1")
            send_json(self, 200, document[0], document=document)
            return

        if path in {"/api/products", "/api/danawa-products"}:
            try:
                spec_filters = json.loads(params.get("filters") or "{}")
                if not isinstance(spec_filters, dict): raise ValueError()
            except (ValueError, TypeError):
                send_json(self, 400, {"ok":False,"error":"필터 형식이 올바르지 않습니다.","items":[]})
                return
            kind = normalize_browse_part_type(params.get("type") or params.get("part_type") or "")
            spec_filters.update({key:params[key].split(',') for key,_ in PRODUCT_FILTER_FIELDS.get(kind,[]) if params.get(key)})
            payload = retail.market_products_response(
                params.get("type") or params.get("part_type") or "",
                params.get("query") or "",
                params.get("page") or 1,
                params.get("limit") or 50,
                params.get("refresh") or "",
                params.get("source") or ("danawa" if path == "/api/danawa-products" else "all"),
                series=params.get("series", ""), model=params.get("model", ""), maker=params.get("maker", ""),
                sort=params.get("sort", "popular"), vendor=params.get("vendor", ""), vram=params.get("vram", ""), cursor=params.get("cursor", ""), filters=spec_filters,
            )
            send_json(self, 200 if payload.get("ok") else 502, payload)
            return

        if path == "/api/part-image":
            send_part_image(self, params)
            return

        if path == "/api/page-preview":
            send_page_preview(self, params)
            return

        send_static(self, path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in {"/api/recommend", "/api/debug_raw", "/api/price-lookup", "/api/product-search", "/api/estimate-fps"}:
            send_json(self, 404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            send_json(self, 400, {"error": "invalid json"})
            return

        try:
            if path == "/api/estimate-fps":
                send_json(self, 200, fps_service.fps_estimate_response(body))
                return
            if path == "/api/price-lookup":
                send_json(self, 200, pricing.price_lookup_response(body))
                return
            if path == "/api/product-search":
                send_json(self, 200, pricing.product_search_response(body))
                return
            send_json(self, 200, recommendation.recommend(body))
        except Exception as e:
            traceback.print_exc()
            send_json(self, 500, {"error": f"server error: {e}"})

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--static-dir", type=str, default=str(state.APP_DIR / 'dist'))
    p.add_argument("--host", type=str, default="127.0.0.1")
    p.add_argument("--port", type=int, default=4000)
    return p.parse_args()

def main() -> None:
    args = parse_args()
    state.STATIC_DIR = Path(args.static_dir).resolve()
    database.load_config()
    database.load_db_cache()

    print("Server ready.")
    print(f"  DB loaded: {state.DB_CACHE.get('loaded', False)}")
    print(f"  Catalog sizes: " + ", ".join(f"{k}={len(v)}" for k, v in CATALOGS.items()))
    if state.DB_CACHE.get("loaded"):
        print(f"  DB summary: {state.DB_CACHE.get('summary', {})}")
    print(f"Serving at http://{args.host}:{args.port}")

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    httpd.serve_forever()
