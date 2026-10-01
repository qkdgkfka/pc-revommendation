"""Retailer HTML parsing, live product browsing and search."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qsl, quote_plus, urlencode, urljoin, urlparse, urlsplit
from urllib.request import Request, urlopen
from datetime import datetime
from html import unescape
import logging
from http.client import HTTPException
from threading import RLock
import re
from retailer_parsing import (
    DANAWA_RUNTIME_GPU_REJECT_TOKENS, append_danawa_query_suffix,
    category_from_danawa_block, danawa_candidate_blocks, danawa_category_label_matches,
    danawa_gpu_name_rejected, danawa_regex_products, danawa_soup_products,
    danawa_url_category_id, first_anchor_from_block, price_from_danawa_block,
)
import secrets
import time
from product_filters import (
    enrich as enrich_product,
    normalize_specs,
    clean_filters,
    matches_specs,
    facets as product_facets,
)
from market_catalog import remember_products, saved_products
from market_search import ProductPager, RetailQueryStream
from product_metadata import (
    DANAWA_BROWSE_DEFAULT_QUERIES,
    canonical_name,
    capacity_mb_from_text,
    clean_visible_text,
    compatible_price_name,
    gpu_exact_model_key,
    gpu_maker_label,
    gpu_maker_normalize,
    gpu_search_metadata,
    gpu_series_key,
    infer_brand,
    infer_cpu_metadata,
    infer_gpu_vram,
    infer_hdd_rpm,
    infer_mb_metadata,
    infer_psu_watt,
    model_tokens,
    normalize_browse_part_type,
    normalize_gpu_maker_prefs,
    normalize_text,
    parse_price_value,
    parse_ram_metadata,
    query_model_name,
    safe_int,
    strip_html,
)
from product_images import product_page_key
from typing import Any, Dict, List, Optional, Tuple
from recommendation_policy import cpu_vendor
from server_catalogs import CATALOGS
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
from . import runtime as state
from . import database
from . import http
from . import pricing
from .cache import SingleFlight

_retail_flight = SingleFlight(max_pending=128)
_retail_cache_lock = RLock()


def _current_market_rows(rows, cached=False):
    result = []
    for source in rows:
        row = dict(source)
        fresh = database.price_is_fresh(row.get('price_checked_at') or row.get('scraped_at') or row.get('checked_at'))
        if not fresh:
            row.update(price_status='stale', price_stale=True, price_verified=False, stale=True)
        elif cached and row.get('price_status') == 'verified':
            row['price_status'] = 'cached'
        result.append(row)
    return result


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))

def danawa_search_url(name: Any) -> str:
    q = quote_plus(str(name or "").strip())
    return f"https://search.danawa.com/dsearch.php?query={q}" if q else ""

def danawa_category_matches(part_type: Any, category: Any) -> bool:
    return danawa_category_label_matches(normalize_text(part_type), clean_visible_text(category).lower())

def danawa_query_for_part(query: Any, part_type: Any, gpu_maker: Any = "") -> str:
    q = query_model_name(query) if normalize_text(part_type) == "gpu" else clean_visible_text(query)
    ctype = normalize_text(part_type)
    if ctype == "gpu" and gpu_maker:
        maker = gpu_maker_label(gpu_maker_normalize(gpu_maker) or normalize_text(gpu_maker))
        if maker and maker.lower() not in q.lower():
            q = f"{maker} {q}"
    return append_danawa_query_suffix(q, ctype)

def danawa_name_rejected(part_type: Any, product_name: Any, category: Any = "") -> bool:
    ctype = normalize_text(part_type)
    name = clean_visible_text(product_name).lower()
    label = clean_visible_text(category).lower()
    if ctype == "gpu":
        return danawa_gpu_name_rejected(name, DANAWA_RUNTIME_GPU_REJECT_TOKENS)
    if label and danawa_category_matches(part_type, label):
        return False
    if ctype in {"ram", "memory"}:
        return any(token in name for token in ["메인보드", "메인 보드", " cpu ", "키트", "kit", "h610m", "b550", "b650", "b760"])
    if ctype in {"storage", "ssd", "hdd"}:
        reject_tokens = [
            "노트북", "게이밍 pc", "데스크탑", "컴퓨터 본체", "외장", "portable",
            "케이스", "enclosure", "도킹", "dock", "허브", "hub", "usb", "sd카드", "메모리카드",
        ]
        if ctype == "hdd" and any(token in name for token in ["ssd", "nvme", "m.2", "m2"]):
            return True
        if any(token in name for token in reject_tokens):
            return True
        return False
    if ctype == "psu":
        return any(token in name for token in ["케이블", "연장", "변환"])
    if ctype == "case":
        return any(token in name for token in ["파우치", "가방", "보호필름", "케이블", "쿨러", "팬", "스마트폰", "태블릿"])
    if ctype == "software":
        return any(token in name for token in ["강의", "책", "도서", "스티커", "키보드", "마우스"])
    return False


def danawa_url_category_matches(part_type: Any, url: Any) -> bool:
    ctype = normalize_text(part_type)
    cate = danawa_url_category_id(url)
    if ctype == "gpu":
        return cate in state.GPU_DANAWA_CATEGORY_IDS if cate else False
    if ctype in {"mb", "motherboard", "mainboard"}:
        return cate in state.MB_DANAWA_CATEGORY_IDS if cate else True
    if ctype in {"storage", "ssd", "hdd"}:
        return cate in state.STORAGE_DANAWA_CATEGORY_IDS if cate else True
    return True

def danawa_url_rejected(part_type: Any, url: Any) -> bool:
    ctype = normalize_text(part_type)
    raw = str(url or "").lower()
    if ctype == "gpu":
        return "/bridge/" in raw or "go_link_goods" in raw
    return False

def catalog_reference_price(part_type: Any, query: Any) -> int:
    ctype = normalize_text(part_type)
    parts = CATALOGS.get(ctype) or []
    key = canonical_name(query_model_name(query) if ctype == "gpu" else query)
    if not key:
        return 0
    match = database._best_match_key(key, [canonical_name(p.get("name")) for p in parts])
    if not match:
        return 0
    for part in parts:
        if canonical_name(part.get("name")) == match:
            return safe_int(part.get("price"), 0)
    return 0

def price_sane_for_part(part_type: Any, price: Any, query: Any = "", catalog_price: Any = 0) -> bool:
    value = safe_int(price, 0)
    if value <= 0:
        return False
    ctype = normalize_text(part_type)
    reference = safe_int(catalog_price, 0) or catalog_reference_price(part_type, query)
    if ctype == "gpu":
        # Static GPU prices are only a loose anomaly check. Exact chip model,
        # GPU category, and product URL are validated separately against Danawa.
        if reference <= 0:
            return 80000 <= value <= 8000000
        lower = max(80000, int(reference * 0.35))
        upper = max(750000, int(reference * 3.50))
        return lower <= value <= upper
    if reference <= 0:
        return value >= 1000
    if ctype in {"cpu", "storage", "ssd", "hdd", "ram", "memory", "psu", "case", "software"}:
        lower = max(1000, int(reference * 0.40))
        upper = int(reference * 2.50)
    else:
        lower = max(1000, int(reference * 0.35))
        upper = int(reference * 3.00)
    return lower <= value <= upper

def danawa_candidate_valid(
    part_type: Any,
    query: Any,
    product_name: Any,
    category: Any,
    url: Any,
    price: Any,
    catalog_price: Any = 0,
    gpu_maker_prefs: Optional[List[str]] = None,
) -> bool:
    ctype = normalize_text(part_type)
    product = clean_visible_text(product_name)
    if ctype == "gpu":
        if danawa_url_rejected(part_type, url):
            return False
        if not (danawa_category_matches(part_type, category) or danawa_url_category_matches(part_type, url)):
            return False
        if danawa_name_rejected(part_type, product, category):
            return False
        if query and product and not compatible_price_name(query_model_name(query), product):
            return False
        prefs = normalize_gpu_maker_prefs(gpu_maker_prefs)
        if prefs and gpu_maker_normalize(product) not in prefs:
            return False
        return price_sane_for_part(part_type, price, query, catalog_price)

    if category and not danawa_category_matches(part_type, category):
        return False
    if ctype in {"storage", "ssd", "hdd"} and not danawa_url_category_matches(part_type, url):
        return False
    if danawa_name_rejected(part_type, product, category):
        return False
    if ctype in {"storage", "ssd"} and "nvme" in normalize_text(query):
        if not any(token in normalize_text(product) for token in ["nvme", "m.2", "m2"]):
            return False
    if query and product and not compatible_price_name(query, product):
        return False
    return price_sane_for_part(part_type, price, query, catalog_price)


def absolute_image_url(src: Any, base_url: Any = "") -> str:
    raw = str(src or "").strip()
    if not raw or raw.startswith("data:"):
        return ""
    lowered = raw.lower()
    if any(token in lowered for token in ["noimg", "no_img", "nodata", "noimage"]):
        return ""
    if raw.startswith("//"):
        raw = "https:" + raw
    if base_url:
        raw = urljoin(str(base_url), raw)
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        return ""
    return raw

def image_from_danawa_block(block: str, base_url: str) -> str:
    # Lazy-loading attributes take precedence regardless of HTML attribute order.
    images = re.findall(r"<img\b[^>]*>", block, re.I | re.S)
    for attribute in ("data-original", "data-src", "src"):
        for tag in images:
            url = absolute_image_url(html_attribute(tag, attribute), base_url)
            if url:
                return url
    return ""

def parse_danawa_top_product_regex(
    html: str,
    search_url: str,
    query: Any = "",
    part_type: Any = "",
    catalog_price: Any = 0,
    gpu_maker_prefs: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for row in danawa_regex_products(html, search_url):
        product_name, category, url, price = row["name"], row["category"], row["url"], row["price"]
        if not danawa_candidate_valid(part_type, query, product_name, category, url, price, catalog_price, gpu_maker_prefs):
            continue
        candidates.append({
            "name": product_name,
            "price": price,
            "url": url,
            "search_url": search_url,
            "image_url": image_from_danawa_block(row["block"], search_url),
            "category": category,
            "maker": gpu_maker_normalize(product_name),
        })

    if candidates:
        candidates.sort(key=lambda item: (safe_int(item.get("price"), 0), len(clean_visible_text(item.get("name")))))
        return candidates[0]

    if not part_type:
        text = strip_html(html)
        m = re.search(r"(\d[\d,]{4,})\s*원", text)
        if m:
            return {"name": "", "price": parse_price_value(m.group(1)), "url": search_url, "search_url": search_url}
    return None

def parse_danawa_top_product(
    html: str,
    search_url: str,
    query: Any = "",
    part_type: Any = "",
    catalog_price: Any = 0,
    gpu_maker_prefs: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    if BeautifulSoup is None:
        return parse_danawa_top_product_regex(html, search_url, query, part_type, catalog_price, gpu_maker_prefs)

    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        candidates: List[Dict[str, Any]] = []
        for row in danawa_soup_products(soup, search_url):
            node = row["node"]
            product_name, category, url, price = row["name"], row["category"], row["url"], row["price"]
            image_el = node.select_one("img[data-original], img[data-src], img[src]")
            image_url = ""
            if image_el:
                image_url = absolute_image_url(
                    image_el.get("data-original") or image_el.get("data-src") or image_el.get("src"),
                    search_url,
                )
            if not danawa_candidate_valid(part_type, query, product_name, category, url, price, catalog_price, gpu_maker_prefs):
                continue
            maker_el = node.select_one("[data-maker-name]")
            maker_name = clean_visible_text(maker_el.get("data-maker-name")) if maker_el else product_name
            candidates.append({
                "name": product_name,
                "price": price,
                "url": url,
                "search_url": search_url,
                "image_url": image_url,
                "category": clean_visible_text(category),
                "maker": gpu_maker_normalize(maker_name),
            })

        if candidates:
            candidates.sort(key=lambda item: (safe_int(item.get("price"), 0), len(clean_visible_text(item.get("name")))))
            return candidates[0]

        price_el = soup.select_one(".price_sect strong, .prod_pricelist strong, .prod_price strong")
        price = parse_price_value(price_el.get_text(" ")) if price_el else None
        if price:
            link_el = soup.select_one(".prod_name a, a[name='productName'], a")
            href = link_el.get("href") if link_el else ""
            product_name = clean_visible_text(link_el.get_text(" ")) if link_el else ""
            url = urljoin(search_url, href) if href else search_url
            if (not part_type and (not query or not product_name or compatible_price_name(query, product_name))) or danawa_candidate_valid(part_type, query, product_name, "", url, price, catalog_price, gpu_maker_prefs):
                return {
                    "name": product_name,
                    "price": price,
                    "url": url,
                    "search_url": search_url,
                }

    if not part_type:
        text = re.sub(r"\s+", " ", html)
        m = re.search(r"href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>.*?(\d[\d,]{4,})\s*원", text, re.I | re.S)
        if m:
            return {
                "name": clean_visible_text(re.sub(r"<[^>]+>", " ", m.group(2))),
                "price": parse_price_value(m.group(3)),
                "url": urljoin(search_url, m.group(1)),
                "search_url": search_url,
            }

        m = re.search(r"(\d[\d,]{4,})\s*원", text)
        if m:
            return {"name": "", "price": parse_price_value(m.group(1)), "url": search_url, "search_url": search_url}
    return parse_danawa_top_product_regex(html, search_url, query, part_type, catalog_price, gpu_maker_prefs)


def danawa_browse_url(query: str, page: int = 1, limit: int = 40) -> str:
    """Build a standard-product results URL in Danawa's popular/recommended order."""
    params = [
        ("query", query),
        ("tab", "goods"),
        ("adult", "0"),
        ("page", str(max(1, page))),
        ("volumeType", "allvs"),
        ("limit", str(max(1, min(40, limit)))),
        # Danawa labels saveDESC as "인기상품순".  It is the site's default
        # recommendation/popularity ordering, not a price ordering.
        ("sort", "saveDESC"),
        ("list", "list"),
        ("boost", "Y"),
    ]
    return "https://search.danawa.com/dsearch.php?" + urlencode(params)

def danawa_browse_category_matches(part_type: Any, category: Any, url: Any) -> bool:
    ctype = normalize_browse_part_type(part_type)
    allowed = state.DANAWA_BROWSE_CATEGORY_IDS.get(ctype, set())
    category_id = danawa_url_category_id(url)
    if allowed and category_id:
        return category_id in allowed
    return danawa_category_matches(ctype, category)

def danawa_browse_candidate_valid(part_type: Any, product_name: Any, category: Any, url: Any, price: Any) -> bool:
    ctype = normalize_browse_part_type(part_type)
    product = clean_visible_text(product_name)
    target_url = http.safe_external_url(url)
    value = safe_int(price, 0)
    if not ctype or not product or not target_url or value < 1000:
        return False
    # Direct product pages provide a stable SKU and product code.  Ad/bridge
    # links can change destination and are not suitable as selectable parts.
    parsed = urlparse(target_url)
    if parsed.hostname != "prod.danawa.com" or "/info/" not in parsed.path.lower():
        return False
    if not danawa_browse_category_matches(ctype, category, target_url):
        return False
    if danawa_name_rejected(ctype, product, category):
        return False
    # A deliberately wide guard removes malformed numbers without excluding
    # expensive workstation GPUs or large storage products.
    return value <= 20_000_000

def danawa_product_code(value: Any) -> str:
    match = re.search(r"productItem(\d+)", str(value or ""), re.I)
    return match.group(1) if match else ""

def performance_reference_for_danawa_product(part_type: Any, product_name: Any) -> Optional[Dict[str, Any]]:
    """Use a known exact model/spec profile; unrelated model numbers are not benchmarks."""
    ctype = normalize_browse_part_type(part_type)
    pool = CATALOGS.get(ctype, [])
    name = clean_visible_text(product_name)
    if ctype == "gpu":
        key = gpu_exact_model_key(name)
        vram = infer_gpu_vram(name)
        candidates = [part for part in pool if key and gpu_exact_model_key(part.get("name")) == key]
        if vram:
            candidates = [part for part in candidates if safe_int(part.get("vram"), 0) == vram]
        elif len({part.get("vram") for part in candidates}) > 1:
            return None
        return candidates[0] if candidates else None
    if ctype == "cpu":
        # Preserve K/KF/F/X/X3D suffixes, including Core Ultra's three-digit models.
        def cpu_models(value: Any) -> set:
            return set(re.findall(r"(?<![0-9a-z])(?:[0-9]{3,5}(?:x3d|kf|k|f|x|g|u)?)(?![0-9a-z])", normalize_text(value)))
        models = cpu_models(name)
        vendor = cpu_vendor({"name":name})
        candidates = [part for part in pool
                      if models & cpu_models(part.get("name"))
                      and (not vendor or normalize_text(part.get("vendor")) == normalize_text(vendor))]
        return candidates[0] if len(candidates) == 1 else None
    if ctype == "ram":
        specs = parse_ram_metadata(name)
        # RAM performance is based on its capacity and speed, not the brand.
        if not all(specs.get(key) for key in ("type", "gb", "speed")):
            return None
        return next((part for part in pool if all(part.get(key) == specs[key]
                     for key in ("type", "gb", "speed"))), None)
    # Other categories are described from the retailer's own specification;
    # copying metadata from a loosely similar motherboard/SSD is unsafe.
    return None

def danawa_browse_tier(reference: Optional[Dict[str, Any]], price: int) -> str:
    if reference and normalize_text(reference.get("tier")) in {"low", "mid", "high"}:
        return normalize_text(reference.get("tier"))
    if price >= 600_000:
        return "high"
    if price >= 180_000:
        return "mid"
    return "low"

def enrich_danawa_browse_product(
    part_type: str,
    product_code: str,
    product_name: str,
    price: int,
    url: str,
    image_url: str,
    category: str,
    source_rank: int,
    spec_text: str = "",
) -> Dict[str, Any]:
    """Return a selectable retail SKU plus safe metadata needed by the UI."""
    ctype = normalize_browse_part_type(part_type)
    reference = performance_reference_for_danawa_product(ctype, product_name)
    item: Dict[str, Any] = {
        "id": f"danawa_{ctype}_{product_code}",
        "name": product_name,
        "product_name": product_name,
        "price": price,
        "base_price": price,
        "tier": danawa_browse_tier(reference, price),
        "shop": "Danawa",
        "url": url,
        "image_url": image_url,
        "currency": "KRW",
        "price_source": "danawa_live",
        "price_status": "verified",
        "component_type": ctype,
        "price_checked_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "source_url": url,
        "price_source_label": "다나와",
        "danawa_rank": source_rank,
        "source_rank": source_rank,
        "category": clean_visible_text(category),
        "performance_ref_id": reference.get("id") if reference else "",
        "tags": ["danawa_live", "recommended_order"],
    }

    if reference:
        metadata_fields = {
            "cpu": ("perf", "socket", "vendor", "tdp", "cores", "threads"),
            "gpu": ("perf_1080", "perf_1440", "perf_2160", "vram", "tdp", "vendor"),
            "ram": ("brand", "type", "gb", "speed"),
            "mb": ("brand", "socket", "ram_type"),
            "psu": ("brand", "watt"),
            "storage": ("brand", "capacity"),
            "hdd": ("brand", "capacity", "rpm"),
            "case": ("brand", "form_factor", "color"),
            "software": ("brand", "license"),
        }.get(ctype, ())
        for field in metadata_fields:
            if reference.get(field) not in (None, ""):
                item[field] = reference.get(field)

    combined_text = f"{product_name} {spec_text}"
    # Capacity is SKU-specific; a grouped specification may list every option.
    capacity_text = product_name
    if ctype == "cpu":
        item.update({key: value for key, value in infer_cpu_metadata(combined_text).items() if value})
    elif ctype == "gpu":
        vram = infer_gpu_vram(combined_text)
        if vram:
            item["vram"] = vram
        item.setdefault("vendor", "AMD" if "radeon" in normalize_text(combined_text) or "amd" in normalize_text(combined_text) else "NVIDIA")
    elif ctype == "ram":
        item.update(parse_ram_metadata(capacity_text))
        item["brand"] = infer_brand(product_name, str(item.get("brand") or ""))
    elif ctype == "mb":
        item.update(infer_mb_metadata(combined_text))
        item["brand"] = infer_brand(product_name, str(item.get("brand") or ""))
    elif ctype == "psu":
        watt = infer_psu_watt(combined_text)
        if watt:
            item["watt"] = watt
        item["brand"] = infer_brand(product_name, str(item.get("brand") or ""))
    elif ctype in {"storage", "hdd"}:
        capacity = capacity_mb_from_text(capacity_text)
        if capacity:
            item["capacity"] = capacity
        item["brand"] = infer_brand(product_name, str(item.get("brand") or ""))
        if ctype == "hdd":
            rpm = infer_hdd_rpm(combined_text)
            if rpm:
                item["rpm"] = rpm
    elif ctype == "case":
        item["brand"] = infer_brand(product_name, str(item.get("brand") or ""))
        lower = normalize_text(combined_text)
        if "matx" in lower or "m-atx" in lower:
            item["form_factor"] = "mATX"
        elif "atx" in lower:
            item["form_factor"] = "ATX"
        if "white" in lower or "화이트" in lower:
            item["color"] = "White"
        elif "black" in lower or "블랙" in lower:
            item["color"] = "Black"
    elif ctype == "software":
        item["brand"] = infer_brand(product_name, str(item.get("brand") or ""))

    performance_index, metric = pricing.component_performance_index(item, ctype)
    item["performance_index"] = round(performance_index, 1)
    item["performance_metric"] = metric
    item["value_per_10000krw"] = round(performance_index / max(1.0, price / 10_000.0), 3)
    return item

def html_attribute(tag: str, attribute: str) -> str:
    match = re.search(r"\b" + re.escape(attribute) + r"\s*=\s*([\"'])(.*?)\1", tag, re.I | re.S)
    return unescape(match.group(2)) if match else ""

def parse_danawa_browse_products(
    html: str, search_url: str, part_type: str, limit: int = 40,
) -> List[Dict[str, Any]]:
    """Keep each option's own SKU, price and capacity (stdlib-only parser).

    Danawa groups RAM/SSD capacities and CPU packaging under one product name.
    Mixing the group minimum with arbitrary spec capacities misprices a build.
    Here every displayed option is a separate selectable retail product.
    """
    ctype = normalize_browse_part_type(part_type)
    items: List[Dict[str, Any]] = []
    seen = set()
    for block in danawa_candidate_blocks(html):
        category = category_from_danawa_block(block)
        base_url, base_name = first_anchor_from_block(block)
        image_url = image_from_danawa_block(block, search_url)
        spec_match = re.search(r'<div\b[^>]+class=["\'][^"\']*spec_list[^"\']*["\'][^>]*>(.*?)</div>', block, re.I | re.S)
        spec = strip_html(spec_match.group(1)) if spec_match else ""
        rank_match = re.search(r'data-product-order=["\'](\d+)', block, re.I)
        rank = safe_int(rank_match.group(1), 0) if rank_match else len(items) + 1
        options = list(re.finditer(r'<li\b[^>]+id=["\']productInfoDetail_(\d+)["\'][^>]*>(.*?)</li>', block, re.I | re.S))
        candidates = []
        for option in options:
            body = option.group(2)
            price_area = re.search(r'<p\b[^>]+class=["\'][^"\']*price_sect[^"\']*["\'][^>]*>(.*?)</p>', body, re.I | re.S)
            memory_area = re.search(r'<p\b[^>]+class=["\'][^"\']*memory_sect[^"\']*["\'][^>]*>(.*?)</p>', body, re.I | re.S)
            if not price_area:
                continue
            link = re.search(r'<a\b[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', price_area.group(1), re.I | re.S)
            if not link:
                continue
            price_text = strip_html(link.group(2))
            price_match = re.search(r'([\d,]+)\s*원', price_text)
            price = parse_price_value(price_match.group(1)) if price_match else None
            label_match = re.search(r'<span\b[^>]+class=["\']text["\'][^>]*>(.*?)</span>', memory_area.group(1), re.I | re.S) if memory_area else None
            label = strip_html(label_match.group(1)) if label_match else ""
            label = re.sub(r'\d[\d,]*원/.*$', '', label).strip()
            name = f"{base_name} ({label})" if label and label not in base_name else base_name
            candidates.append((option.group(1), name, price, unescape(link.group(1))))
        # Legacy/simple rows have no grouped option list.
        if not options:
            candidates.append((danawa_product_code(block), base_name, price_from_danawa_block(block), base_url))
        for code, name, price, url in candidates:
            target = urljoin(search_url, unescape(url))
            if code in seen or not code or not danawa_browse_candidate_valid(ctype, name, category, target, price):
                continue
            seen.add(code)
            item = enrich_danawa_browse_product(ctype, code, name, safe_int(price, 0), target, image_url, category, rank, spec)
            item["scraped_at"] = item["price_checked_at"]
            item["spec_text"] = spec[:2000]
            items.append(item)
            if len(items) >= limit:
                return items
    return items

def compuzone_browse_url(part_type: str, query: str = "", page: int = 1, limit: int = 40) -> str:
    # This public endpoint renders the same product rows as the category UI.
    # Each scroll page is 20 rows; StartNum advances the requested outer page.
    return "https://www.compuzone.co.kr/product/product_list.php?" + urlencode({
        "actype": "getList", "BigDivNo": "9" if part_type == "software" else "4",
        "MediumDivNo": state.COMPUZONE_CATEGORY_IDS.get(part_type, ""), "DivNo": "0",
        "PageCount": limit, "StartNum": (page - 1) * limit, "PageNum": page,
        "ScrollPage": 1, "PreOrder": "recommand", "lvm": "L",
        "ProductType": "list", "splist_kw": query,
    })

def parse_compuzone_browse_products(html: str, search_url: str, part_type: str, limit: int = 40) -> List[Dict[str, Any]]:
    ctype = normalize_browse_part_type(part_type)
    starts = [m.start() for m in re.finditer(r'<li\b[^>]*id=["\']li-pno-\d+["\']', html, re.I)]
    items = []
    seen = set()
    for pos, start in enumerate(starts):
        block = html[start:starts[pos + 1] if pos + 1 < len(starts) else len(html)]
        anchor = re.search(r'<a\b(?=[^>]*class=["\'][^"\']*prdTxt)[^>]*>(.*?)</a>', block, re.I | re.S)
        price_tag = re.search(r'<div\b(?=[^>]*class=["\']prd_price["\'])[^>]*>', block, re.I | re.S)
        if not anchor or not price_tag:
            continue
        name = strip_html(anchor.group(1))
        url = urljoin("https://www.compuzone.co.kr/product/", html_attribute(anchor.group(0).split(">", 1)[0], "href"))
        params = dict(parse_qsl(urlparse(url).query))
        code = params.get("ProductNo")
        if not code or code in seen or params.get("MediumDivNo") != state.COMPUZONE_CATEGORY_IDS.get(ctype):
            continue
        if (urlparse(url).hostname or "") not in {"www.compuzone.co.kr", "compuzone.co.kr"}:
            continue
        # The public normal selling price excludes card/member-only discounts.
        price = parse_price_value(html_attribute(price_tag.group(0), "data-price"))
        if not price or not 1000 <= price <= 20_000_000:
            continue
        if re.search(r'class=["\'][^"\']*(?:soldout|sold_out|stock_none)', block, re.I):
            continue
        if not market_component_name_valid(ctype, name):
            continue
        image_area = re.search(r'<a\b[^>]*class=["\']prd_info_main_img["\'][^>]*>(.*?)</a>', block, re.I | re.S)
        image = image_from_danawa_block(image_area.group(1), url) if image_area else ""
        spec_area = re.search(r'<div\b[^>]*class=["\']prd_subTxt["\'][^>]*>(.*?)</div>', block, re.I | re.S)
        spec = strip_html(spec_area.group(1)) if spec_area else ""
        item = enrich_danawa_browse_product(ctype, code, name, price, url, image, DANAWA_BROWSE_DEFAULT_QUERIES[ctype], pos + 1, spec)
        item.update(id=f"compuzone_{ctype}_{code}", shop="Compuzone", price_source="compuzone_live",
                    price_source_label="컴퓨존", source_url=url, tags=["compuzone_live"],
                    spec_text=spec[:2000], scraped_at=item["price_checked_at"])
        item.pop("danawa_rank", None)
        items.append(item)
        seen.add(code)
        if len(items) >= limit:
            break
    return items

def market_component_name_valid(part_type: str, name: str) -> bool:
    lower = normalize_text(name)
    if any(token in lower for token in ("중고", "리퍼", "refurb", "노트북", "sodimm", "so-dimm")):
        return False
    if part_type == "cpu":
        return not any(token in lower for token in ("조립pc", "본체", "데스크탑", "노트북", "브라켓"))
    if part_type in {"ram", "storage", "hdd", "psu", "case"}:
        accessory = ("장착가이드", "브라켓", "변환", "연장", "외장", "도킹", "하드랙", "보관함", "액세서리", "악세서리")
        if any(token in lower for token in accessory):
            return False
        if part_type in {"storage", "hdd"} and any(token in lower for token in ("케이스", "enclosure", "usb")):
            return False
    return not danawa_name_rejected(part_type, name, DANAWA_BROWSE_DEFAULT_QUERIES.get(part_type, ""))

def retail_quote_valid(part_type: str, query: str, item: Dict[str, Any]) -> bool:
    """Validate an observed retail SKU without comparing it to an old estimate."""
    name = item.get("product_name") or item.get("name") or ""
    url = item.get("url") or ""
    if not (1000 <= safe_int(item.get("price"), 0) <= 20_000_000
            and database.market_product_url(url)
            and market_component_name_valid(part_type, name)
            and compatible_price_name(query, name)):
        return False
    params = dict(parse_qsl(urlsplit(url).query))
    if "compuzone" in (urlparse(url).hostname or ""):
        category = params.get("MediumDivNo")
        return not category or category == state.COMPUZONE_CATEGORY_IDS.get(part_type)
    return danawa_url_category_matches(part_type, url) and not danawa_url_rejected(part_type, url)

def saved_market_page(part_type: str, query: str, page: int, limit: int, provider: str, verified_only: bool = False) -> Dict[str, Any]:
    """A retailer outage may reuse observed prices, keeping their original age."""
    rows = []
    for item in saved_products(part_type):
        if verified_only and (not item.get("image_checked_at") or not item.get("price_verified")):
            continue
        item_provider = "compuzone" if "compuzone" in (urlparse(item.get("url", "")).hostname or "") else "danawa"
        if item_provider != provider or not market_component_name_valid(part_type, item["name"]):
            continue
        if query:
            if part_type == 'gpu' and gpu_series_key(query):
                if gpu_search_metadata(item).get('series') != gpu_series_key(query):
                    continue
            elif model_tokens(query) or re.search(r"\d\s*(?:GB|TB)\b", query, re.I):
                if not compatible_price_name(query, item["name"]):
                    continue
            elif not all(token in canonical_name(item["name"]) for token in canonical_name(query).split()):
                continue
        rows.append(item)
    start = (page - 1) * limit
    items = rows[start:start + limit]
    status = "stale" if any(item.get("price_stale") for item in items) else "cached"
    return {"items": items, "status": status if items else "unavailable",
            "total": len(rows), "has_more": start + limit < len(rows), "cached": True}

def _market_fetch_html(url: str, provider: str, timeout: float = 8.0) -> str:
    if timeout <= 0:
        raise TimeoutError('Retail request deadline exceeded')
    deadline = time.monotonic() + timeout
    headers = {**state.DANAWA_HEADERS, "Referer": "https://www.compuzone.co.kr/" if provider == "compuzone" else "https://search.danawa.com/"}
    with urlopen(Request(url, headers=headers), timeout=timeout) as response:
        chunks, remaining_bytes = [], 8_000_000
        while remaining_bytes:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Retail request deadline exceeded')
            socket = getattr(getattr(getattr(response, 'fp', None), 'raw', None), '_sock', None)
            if socket is not None:
                socket.settimeout(remaining)
            chunk = response.read1(min(65536, remaining_bytes))
            if not chunk:
                break
            chunks.append(chunk)
            remaining_bytes -= len(chunk)
        raw = b''.join(chunks)
        charset = response.headers.get_content_charset() or ("cp949" if provider == "compuzone" else "utf-8")
    return raw.decode(charset, errors="replace")

def _market_source_page(part_type: str, query: str, page: int, limit: int, provider: str, refresh: bool = False, timeout: float = 8.0, persist: bool = True) -> Dict[str, Any]:
    key = (part_type, normalize_text(query), page, limit, provider, bool(refresh), bool(persist))
    return _retail_flight.run(key, lambda: _market_source_page_uncached(
        part_type, query, page, limit, provider, refresh, timeout, persist), timeout=max(.001, timeout))


def _market_source_page_uncached(part_type: str, query: str, page: int, limit: int, provider: str, refresh: bool = False, timeout: float = 8.0, persist: bool = True) -> Dict[str, Any]:
    key = (part_type, normalize_text(query), page, limit, provider)
    now = datetime.utcnow()
    with _retail_cache_lock:
        cached = state.MARKET_BROWSE_CACHE.get(key)
    if cached and not refresh and (now - cached["fetched_at"]).total_seconds() < state.DANAWA_BROWSE_CACHE_TTL_SECONDS:
        payload = cached['payload']
        items = _current_market_rows(payload['items'], cached=True)
        status = 'stale' if any(row.get('price_stale') for row in items) else 'cached' if items else payload['status']
        return {**payload, 'items': items, 'status': status, 'cached': True}
    query_used = query or DANAWA_BROWSE_DEFAULT_QUERIES[part_type]
    series = gpu_series_key(query) if part_type == 'gpu' else ''
    # AMD generation labels aren't literal chipsets. Search the retailer's
    # Radeon family and apply the normalized generation after parsing.
    if series.startswith('RX '):
        query_used = "라데온"
    provider_query = query_used if query else ''
    url = danawa_browse_url(query_used, page, limit) if provider == "danawa" else compuzone_browse_url(part_type, provider_query, page, limit)
    base = {"provider": provider, "page": page, "source_url": url, "items": [], "total": None, "has_more": False, "cached": False}
    try:
        html = _market_fetch_html(url, provider, timeout)
        if provider == "danawa":
            all_items = parse_danawa_browse_products(html, url, part_type, 600)
            raw_count = len(re.findall(r'<li\b[^>]*id=["\']productItem\d+', html, re.I))
            later_pages = [int(n) for n in re.findall(r'onclick=["\']paging\((\d+)\)', html, re.I)]
            has_more = any(n > page for n in later_pages) or raw_count >= limit
            recognized = bool(raw_count or 'productListArea' in html or '검색결과가 없습니다' in html)
        else:
            all_items = parse_compuzone_browse_products(html, url, part_type, 100)
            raw_count = len(re.findall(r'id=["\']li-pno-\d+', html, re.I))
            has_more = raw_count >= min(20, limit)
            recognized = bool(raw_count or '검색된 상품이 없습니다' in html or '상품이 없습니다' in html or 'IsMaxPageing' in html)
        if not recognized:
            raise ValueError("upstream returned an unrecognized page")
        items = [item for item in all_items if market_component_name_valid(part_type, item["name"])]
        # Broad category search remains broad; explicit model/capacity constraints
        # must not silently return a different variant from a grouped result.
        if part_type == 'gpu':
            items = [{**item, **gpu_search_metadata(item)} for item in items]
        if series:
            items = [item for item in items if item.get('series') == series]
        elif query and (model_tokens(query) or re.search(r'\d\s*(?:GB|TB)\b', query, re.I)):
            items = [item for item in items if compatible_price_name(query, item["name"])]
        payload = {**base, "status": "live" if items else "empty", "items": items, "has_more": has_more,
                   "checked_at": now.isoformat(timespec="seconds") + "Z", "raw_count": raw_count}
        with _retail_cache_lock:
            state.MARKET_BROWSE_CACHE[key] = {"fetched_at": now, "payload": payload}
            if len(state.MARKET_BROWSE_CACHE) > 240:
                oldest = min(state.MARKET_BROWSE_CACHE, key=lambda k: state.MARKET_BROWSE_CACHE[k]["fetched_at"])
                state.MARKET_BROWSE_CACHE.pop(oldest, None)
        if persist:
            remember_products(part_type, items)
        return payload
    except (OSError, ValueError, HTTPException) as error:
        logging.getLogger(__name__).warning("Retailer %s request failed (%s): %s", provider, type(error).__name__, error)
        if cached and cached["payload"].get("items"):
            old = cached["payload"]
            items = [{**item, "price_status": "stale", "price_stale": True, "price_verified": False,
                      "price_source": provider + "_stale"} for item in old["items"]]
            return {**old, "status": "stale", "items": items, "cached": True, "error": "판매처 응답 지연으로 이전 확인 가격을 표시합니다."}
        saved = saved_market_page(part_type, query, page, limit, provider)
        if saved["items"]:
            return {**base, **saved, "error": "판매처 연결 지연으로 저장된 확인 가격을 표시합니다."}
        timed_out = isinstance(error, TimeoutError) or isinstance(getattr(error, 'reason', None), TimeoutError)
        return {**base, "status": "unavailable", "query_failed": isinstance(error, ValueError),
                "error_kind": "timeout" if timed_out else "upstream",
                "error": "판매처 조회 제한 시간을 초과했습니다." if timed_out else
                         ("다나와" if provider == "danawa" else "컴퓨존") + " 상품 목록을 불러오지 못했습니다."}

def market_products_response(part_type: Any, query: Any = "", page: Any = 1, limit: Any = 50, refresh: Any = False, source: Any = "all", persist: bool = True,
                             series: Any = "", model: Any = "", maker: Any = "", sort: Any = "popular", vendor: Any = "", vram: Any = "", cursor: Any = "", filters: Any = None) -> Dict[str, Any]:
    ctype = normalize_browse_part_type(part_type)
    provider = normalize_text(source) or "all"
    if not ctype or provider not in {"all", "danawa", "compuzone"}:
        return {"ok": False, "status": "invalid", "error": "지원하지 않는 부품 종류 또는 판매처입니다.", "items": []}
    query = clean_visible_text(query)[:120]
    page = max(1, min(100, safe_int(page, 1)))
    limit = max(1, min(100, safe_int(limit, 50)))
    sort = sort if sort in {"popular", "price_asc", "price_desc", "name"} else "popular"
    series = gpu_series_key(series) or (gpu_series_key(query) if ctype == "gpu" else "")
    model_key = gpu_exact_model_key(model)
    makers = normalize_gpu_maker_prefs(maker)
    vendors = [v.lower() for v in str(vendor or '').split(',') if v]
    vrams = [safe_int(v) for v in str(vram or '').split(',') if v]
    filters = clean_filters(ctype, filters)
    source_query = query or (query_model_name(model) if model_key else series)
    force = refresh is True or normalize_text(refresh) in {"1", "true", "yes"}
    providers = ["danawa", "compuzone"] if provider == "all" else [provider]

    def matches(item):
        if not matches_specs(normalize_specs(item, ctype), filters):
            return False
        name = item.get("product_name") or item.get("name") or ""
        if not market_component_name_valid(ctype, name):
            return False
        if ctype == 'gpu':
            metadata = gpu_search_metadata(item)
            if series and metadata.get('series') != series:
                return False
            if model_key and gpu_exact_model_key(metadata.get('chipset')) != model_key:
                return False
            if makers and metadata.get('manufacturer') not in makers:
                return False
            if vendors and metadata.get('vendor', '').lower() not in vendors:
                return False
            if vrams and safe_int(item.get('vram')) not in vrams:
                return False
        if query and not gpu_series_key(query):
            if model_tokens(query) or re.search(r'\d\s*(?:GB|TB)\b', query, re.I):
                return compatible_price_name(query, name)
            return item.get('_query_applied') or all(token in canonical_name(name) for token in canonical_name(query).split())
        return True

    def saved():
        rows = []
        for row in saved_products(ctype):
            host = urlparse(row.get('url', '')).hostname or ''
            retail = 'compuzone' if 'compuzone' in host else 'danawa'
            if retail in providers:
                rows.append({**row, **gpu_search_metadata(row)} if ctype == 'gpu' else row)
        return rows

    deadline = time.monotonic() + 12

    def source_fetch(p, q, n, request_deadline=None):
        remaining = max(.001, (request_deadline or deadline) - time.monotonic())
        result = _market_source_page(ctype, q, n, 20 if p == 'compuzone' else 40, p, force, min(4.0, remaining), persist)
        return {**result, 'items':[{**row, '_query_applied':not query or normalize_text(query) in normalize_text(q)} for row in result['items']]}

    queries = [source_query]
    if ctype == 'gpu' and series and not model_key:
        # Search models that actually exist in structured reference/saved data.
        # This queries real listings; it never manufactures retail products.
        chipsets = {metadata['chipset'] for row in CATALOGS.get('gpu', []) + saved_products('gpu')
                    for metadata in [gpu_search_metadata(row)] if metadata.get('series') == series}
        prefix = query if query and not gpu_series_key(query) else ''
        queries += [f'{prefix} {chipset}'.strip() for chipset in sorted(chipsets)]
        queries = list(dict.fromkeys(queries))
        if len(makers) == 1:
            queries = [f"{gpu_maker_label(makers[0])} {q}" for q in queries]

    key = (ctype, normalize_text(query), provider, limit, series, model_key, tuple(sorted(makers)), sort, tuple(sorted(vendors)), tuple(sorted(vrams)), tuple((k,tuple(v)) for k,v in sorted(filters.items())), persist)
    reset = False
    cursor = str(cursor or "")[:80]
    with state.MARKET_SEARCH_LOCK:
        pager = state.MARKET_SEARCH_CACHE.get((key, cursor) if cursor else key)
        if not pager or (force and page == 1) or time.monotonic() - pager.created_at > 300:
            stream = RetailQueryStream(providers, queries, source_fetch) if len(queries) > 1 else None
            pager = ProductPager(providers,
                stream.next if stream else lambda p,n,d=None: source_fetch(p, source_query, n, d),
                saved, matches, lambda item: product_page_key(item.get('url')) or item.get('id'), sort, deadline_aware=True)
            pager.cursor = secrets.token_urlsafe(12)
            state.MARKET_SEARCH_CACHE[key] = pager
            state.MARKET_SEARCH_CACHE[(key, pager.cursor)] = pager
            if cursor:
                page, reset = 1, True
            while len(state.MARKET_SEARCH_CACHE) > 128:
                oldest = min(state.MARKET_SEARCH_CACHE.values(), key=lambda p:p.created_at)
                for old_key in [k for k,p in state.MARKET_SEARCH_CACHE.items() if p is oldest]:
                    state.MARKET_SEARCH_CACHE.pop(old_key, None)
    result = pager.page(page, limit, deadline=deadline)
    items = [enrich_product({k:v for k,v in row.items() if k != '_query_applied'}, ctype)
             for row in _current_market_rows(result['items'], cached=result.get('reused', False))]
    sources = {provider: {**response, 'cached': True,
                         'status': 'cached' if response['status'] == 'live' else response['status']}
               if result.get('reused') else response for provider, response in result['results'].items()}
    if any(row.get('price_stale') for row in items):
        sources = {p: {**response, 'status': 'stale'} if any(
            row.get('price_stale') and ('compuzone' in row.get('url', '')) == (p == 'compuzone')
            for row in items) else response for p, response in sources.items()}
    statuses = [row.get('price_status') for row in items]
    status = "live" if 'verified' in statuses else "cached" if 'cached' in statuses else "stale" if 'stale' in statuses else "empty" if sources and any(r['status'] != 'unavailable' for r in sources.values()) else "unavailable"
    return {
        "ok": status != "unavailable", "status": status, "type": ctype,
        "query": query, "query_used": source_query or DANAWA_BROWSE_DEFAULT_QUERIES[ctype],
        "page": page, "limit": limit, "items": items, "cursor": pager.cursor, "reset": reset,
        "total": len(pager.rows) if not any(pager.more.values()) else None,
        "has_more": result['has_more'], "partial": result['partial'],
        "source": provider, "source_status": {p:r['status'] for p,r in sources.items()},
        "source_urls": {p:r['source_url'] for p,r in sources.items()},
        "cached": bool(sources) and all(r['cached'] for r in sources.values()),
        "facets": product_facets(ctype, saved_products(ctype) + list(pager.rows.values()), filters),
        "spec_filters": filters,
        "sort": sort, "sort_label": {"popular":"검색처 기본순", "price_asc":"낮은 가격순", "price_desc":"높은 가격순", "name":"제품명순"}[sort],
        "filters": {"series":series, "model":str(model or ''), "maker":makers, "vendor":vendors, "vram":vrams},
        "error": next((r.get("error", "") for r in sources.values() if r.get("error")), ""),
        "error_kind": next((r.get("error_kind", "") for r in sources.values() if r.get("error_kind")), ""),
    }


def fetch_market_top_product(query: Any, part_type: Any = "", timeout: float = 2.5, catalog_price: Any = 0,
                             gpu_maker_prefs: Optional[List[str]] = None, include_image_preview: bool = True,
                             allow_relaxed_retry: bool = False, source: Any = "all") -> Optional[Dict[str, Any]]:
    ctype = normalize_browse_part_type(part_type)
    if not ctype:
        return None
    provider = normalize_text(source) or "all"
    providers = [provider] if provider in {"danawa", "compuzone"} else ["danawa", "compuzone"]
    prefs = normalize_gpu_maker_prefs(gpu_maker_prefs)
    search_query = query_model_name(query) if ctype == "gpu" else clean_visible_text(query)
    # Korean retailers index CPU model numbers more consistently than English
    # marketing prefixes. The full original query still validates every result.
    if ctype == "cpu":
        search_query = re.sub(r'\b(?:AMD|Intel|Core|Ryzen)\b', ' ', search_query, flags=re.I)
        search_query = re.sub(r'\b[3579]\s+(?=\d{4,5})', '', search_query)
        search_query = clean_visible_text(search_query)
    with ThreadPoolExecutor(max_workers=len(providers)) as executor:
        results = list(executor.map(lambda p: _market_source_page(ctype, search_query, 1, 20, p, False, timeout), providers))
    matches = []
    for response in results:
        if response.get("status") not in {"live", "cached"}:
            continue
        for item in response["items"]:
            if not compatible_price_name(query, item["name"]):
                continue
            if prefs and gpu_maker_normalize(item["name"]) not in prefs:
                continue
            if not retail_quote_valid(ctype, query, item):
                continue
            matches.append(item)
    if not matches:
        return None
    best = dict(min(matches, key=lambda item: item["price"]))
    best.update(matched_by="market_exact_model", search_url=next((r["source_url"] for r in results if r["provider"] in best["price_source"]), ""))
    return best
