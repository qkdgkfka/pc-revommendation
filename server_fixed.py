#!/usr/bin/env python3
from __future__ import annotations

"""
server_fixed.py

A small HTTP server that:
- serves the frontend files in this folder
- exposes /health and /api/recommend
- reads prices / benchmarks from a local SQLite DB when available
- falls back to embedded catalogs when the DB is empty or missing

DB schema expected by the crawler:
- components(id, type, name, brand, model, socket, vram, tdp, created_at)
- prices(id, component_id, shop, currency, price, url, scraped_at)
- benchmarks(id, component_id, game, resolution, setting, avg_fps, low1_fps, source_url, scraped_at)
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from dataclasses import dataclass, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, quote_plus, urlencode, urljoin, urlparse, urlsplit
from urllib.request import Request, urlopen
import argparse
from datetime import datetime, timedelta
from html import escape, unescape
import json
import math
import random
import re
from retailer_parsing import danawa_candidate_blocks, price_from_danawa_block
import secrets
import sqlite3
import traceback
import copy
import time
from market_catalog import remember_products, saved_products
# Preserve existing helper imports for scripts/tests while implementation lives
# in the shared metadata module.
from product_metadata import (
    DANAWA_BROWSE_DEFAULT_QUERIES, GPU_MAKER_ALIASES, GPU_MAKER_LABELS, canonical_name,
    capacity_mb_from_text, clean_visible_text, compatible_gpu_price_name, compatible_price_name,
    gpu_exact_model_key, gpu_maker_label, gpu_maker_normalize, gpu_model_number_from_key,
    gpu_model_number_mentions, image_name_tokens, infer_brand, infer_cpu_metadata,
    infer_gpu_vram, infer_hdd_rpm, infer_mb_metadata, infer_psu_watt,
    model_tokens, normalize_browse_part_type, normalize_gpu_maker_prefs, normalize_product_url,
    normalize_text, parse_price_value, parse_ram_metadata, query_model_name,
    safe_float, safe_int, strip_html, variant_tokens,
)
from game_benchmarks import estimate_from_measurements, load_measurements
from graphics_estimates import graphics_scenarios
from product_images import (fetch_product_image, retailer_image_url, image_source_priority,
                            product_page_key, fetch_product_page_image)
from product_import import fetch_product_page, imported_products, save_imported_product, supported_product_url
from component_compatibility import platform_compatibility
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - BeautifulSoup is optional at runtime.
    BeautifulSoup = None

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
ARTIFACT_DIR = APP_DIR / "artifacts"
DB_PATH = DATA_DIR / "pc.db"
CONFIG_PATH = ARTIFACT_DIR / "hybrid_config.json"
STATIC_DIR = APP_DIR

MODEL_LOADED = True
HYBRID_CONFIG: Dict[str, Any] = {}
DANAWA_PRICE_MAX_AGE_HOURS = 24
DANAWA_BROWSE_CACHE_TTL_SECONDS = 300
DANAWA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.6",
}
IMAGE_URL_CACHE: Dict[Tuple[str, str], str] = {}
PREVIEW_CACHE: Dict[str, Dict[str, str]] = {}
# Per-process cache for GPU models that have already been checked against Danawa.
# A None entry means Danawa did not return a valid graphics-card listing for that model.
GPU_MARKET_PRICE_CACHE: Dict[str, Optional[Dict[str, Any]]] = {}
# The direct-spec browser deliberately fetches fresh Danawa result pages rather
# than presenting a pre-composed component list.  Cache short-lived pages so a
# user changing local filters does not repeatedly hit Danawa for the same page.
DANAWA_BROWSE_CACHE: Dict[Tuple[str, str, int, int], Dict[str, Any]] = {}

# ─────────────────────────────────────────────────────────────
# Embedded fallback catalogs
# ─────────────────────────────────────────────────────────────

from server_catalogs import CPU_CATALOG, GPU_CATALOG, RAM_CATALOG, MB_CATALOG, PSU_CATALOG, STORAGE_CATALOG, HDD_CATALOG, CASE_CATALOG, SOFTWARE_CATALOG, CATALOGS, GAME_OPTIONS, BENCHMARK_FPS_BY_GPU, GAME_FPS_PROFILES, WORK_PROFILES, WORK_ALIASES, COMMON_GPU_MODEL_NUMBERS

# ─────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────

def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def danawa_search_url(name: Any) -> str:
    q = quote_plus(str(name or "").strip())
    return f"https://search.danawa.com/dsearch.php?query={q}" if q else ""


GPU_DANAWA_CATEGORY_IDS = {"112753"}
STORAGE_DANAWA_CATEGORY_IDS = {"112760"}
MB_DANAWA_CATEGORY_IDS = {"112751"}
# Exact category IDs keep broad queries such as "CPU" or "RAM" from leaking
# accessories and finished PCs into the direct-spec browser.  We still fall
# back to the visible category label when Danawa omits a category parameter.
DANAWA_BROWSE_CATEGORY_IDS = {
    "cpu": {"113990", "113973"},
    "gpu": GPU_DANAWA_CATEGORY_IDS,
    "ram": {"112752"},
    "mb": MB_DANAWA_CATEGORY_IDS,
    "storage": STORAGE_DANAWA_CATEGORY_IDS,
    "hdd": {"1131401"},
    "psu": {"112777"},
    "case": {"112775"},
}


def danawa_category_matches(part_type: Any, category: Any) -> bool:
    ctype = normalize_text(part_type)
    label = clean_visible_text(category).lower()
    if not ctype or not label:
        return False if ctype == "gpu" else True
    expected = {
        "gpu": ("그래픽", "vga"),
        "cpu": ("cpu", "프로세서"),
        "ram": ("ram", "메모리"),
        "memory": ("ram", "메모리"),
        "storage": ("ssd", "hdd", "저장", "스토리지"),
        "ssd": ("ssd", "저장", "스토리지"),
        "hdd": ("hdd", "하드", "저장", "스토리지"),
        "psu": ("파워", "power"),
        "mb": ("메인보드", "mainboard", "motherboard"),
        "motherboard": ("메인보드", "mainboard", "motherboard"),
        "case": ("케이스", "case", "chassis"),
        "software": ("소프트웨어", "운영체제", "os", "windows", "office"),
    }.get(ctype)
    return True if not expected else any(token in label for token in expected)

def danawa_query_for_part(query: Any, part_type: Any, gpu_maker: Any = "") -> str:
    q = query_model_name(query) if normalize_text(part_type) == "gpu" else clean_visible_text(query)
    ctype = normalize_text(part_type)
    suffix = {
        "gpu": "그래픽카드",
        "ram": "메모리",
        "memory": "메모리",
        "storage": "SSD",
        "ssd": "SSD",
        "hdd": "HDD",
        "psu": "파워",
        "mb": "메인보드",
        "motherboard": "메인보드",
        "case": "PC 케이스",
        "software": "소프트웨어",
    }.get(ctype, "")
    if ctype == "gpu" and gpu_maker:
        maker = gpu_maker_label(gpu_maker_normalize(gpu_maker) or normalize_text(gpu_maker))
        if maker and maker.lower() not in q.lower():
            q = f"{maker} {q}"
    if suffix and suffix.lower() not in q.lower():
        return f"{q} {suffix}"
    return q

def danawa_name_rejected(part_type: Any, product_name: Any, category: Any = "") -> bool:
    ctype = normalize_text(part_type)
    name = clean_visible_text(product_name).lower()
    label = clean_visible_text(category).lower()
    if ctype == "gpu":
        if not name:
            return True
        reject_tokens = [
            "조립pc", "조립 pc", "완본체", "본체", "데스크탑", "데스크톱", "컴퓨터", "pc방",
            "노트북", "워크스테이션", "서버", "미니pc", "베어본", "egpu",
            "쿨러", "쿨링", "냉각", "cooler", "cooling", "팬", "fan", "수냉", "워터블럭", "water block",
            "백플레이트", "backplate", "라디에이터", "radiator", "방열판", "히트싱크",
            "지지대", "거치대", "브라켓", "라이저", "riser", "케이블", "cable", "가방", "케이스",
            "섀시", "샤시", "chassis", "no hardware",
            "교체품", "부품용", "중고", "리퍼", "refurb", "채굴", "mining", "딥러닝", "deep learning",
        ]
        compact = re.sub(r"\s+", "", name)
        if any(token in name or token.replace(" ", "") in compact for token in reject_tokens):
            return True
        return False
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

def category_from_danawa_block(block: str) -> str:
    m = re.search(r"id=[\"']productItem_categoryInfo_[^\"']+[\"'][^>]+value=[\"']([^\"']+)[\"']", block, re.I)
    return clean_visible_text(m.group(1)) if m else ""

def danawa_url_category_id(url: Any) -> str:
    raw = str(url or "")
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
    except Exception:
        return ""
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key.lower() == "cate" and value:
            return value
    return ""

def danawa_url_category_matches(part_type: Any, url: Any) -> bool:
    ctype = normalize_text(part_type)
    cate = danawa_url_category_id(url)
    if ctype == "gpu":
        return cate in GPU_DANAWA_CATEGORY_IDS if cate else False
    if ctype in {"mb", "motherboard", "mainboard"}:
        return cate in MB_DANAWA_CATEGORY_IDS if cate else True
    if ctype in {"storage", "ssd", "hdd"}:
        return cate in STORAGE_DANAWA_CATEGORY_IDS if cate else True
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
    match = _best_match_key(key, [canonical_name(p.get("name")) for p in parts])
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



def first_anchor_from_block(block: str) -> Tuple[str, str]:
    name_area = re.search(
        r"<p\b[^>]+class=[\"'][^\"']*prod_name[^\"']*[\"'][^>]*>(.*?)</p>",
        block,
        re.I | re.S,
    )
    area = name_area.group(1) if name_area else block
    link_match = re.search(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", area, re.I | re.S)
    if link_match:
        return link_match.group(1), strip_html(link_match.group(2))

    img_match = re.search(r"<img[^>]+alt=[\"']([^\"']+)[\"']", block, re.I | re.S)
    href_match = re.search(r"<a[^>]+href=[\"']([^\"']+)[\"']", block, re.I | re.S)
    return (href_match.group(1) if href_match else ""), clean_visible_text(img_match.group(1) if img_match else "")

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
    for block in danawa_candidate_blocks(html):
        if not re.search(r"prod_item|prod_main_info|price_sect|prod_pricelist|min_price_", block, re.I):
            continue
        category = category_from_danawa_block(block)
        price = price_from_danawa_block(block)
        if not price:
            continue
        href, product_name = first_anchor_from_block(block)
        url = urljoin(search_url, href) if href else search_url
        if not danawa_candidate_valid(part_type, query, product_name, category, url, price, catalog_price, gpu_maker_prefs):
            continue
        candidates.append({
            "name": product_name,
            "price": price,
            "url": url,
            "search_url": search_url,
            "image_url": image_from_danawa_block(block, search_url),
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
        nodes = soup.select("li.prod_item, .main_prodlist li, .prod_main_info")
        if not nodes:
            nodes = soup.select(".prod_list .prod_item, .prod_list li")

        candidates: List[Dict[str, Any]] = []
        for node in nodes:
            category_el = node.select_one("input[id^='productItem_categoryInfo_']")
            category = category_el.get("value") if category_el else ""
            hidden_price_el = node.select_one("input[id^='min_price_']")
            price = parse_price_value(hidden_price_el.get("value")) if hidden_price_el else None
            price_el = node.select_one(
                ".price_sect strong, .prod_pricelist strong, .prod_price strong, "
                ".price_sect a strong, a .num"
            )
            if not price:
                price = parse_price_value(price_el.get_text(" ")) if price_el else None
            if not price:
                continue

            link_el = node.select_one(".prod_name a, a[name='productName'], a.prod_name, a")
            href = link_el.get("href") if link_el else ""
            product_name = clean_visible_text(link_el.get_text(" ")) if link_el else ""
            if not product_name:
                img_el = node.select_one("img[alt]")
                product_name = clean_visible_text(img_el.get("alt")) if img_el else ""
            image_el = node.select_one("img[data-original], img[data-src], img[src]")
            image_url = ""
            if image_el:
                image_url = absolute_image_url(
                    image_el.get("data-original") or image_el.get("data-src") or image_el.get("src"),
                    search_url,
                )
            url = urljoin(search_url, href) if href else search_url
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

def fetch_danawa_top_product(
    query: Any,
    part_type: Any = "",
    timeout: float = 2.5,
    catalog_price: Any = 0,
    gpu_maker_prefs: Optional[List[str]] = None,
    include_image_preview: bool = True,
) -> Optional[Dict[str, Any]]:
    maker_prefs = normalize_gpu_maker_prefs(gpu_maker_prefs)
    search_specs: List[Tuple[str, List[str]]] = []
    if normalize_text(part_type) == "gpu" and maker_prefs:
        if len(maker_prefs) == 1:
            search_specs.append((danawa_query_for_part(query, part_type, maker_prefs[0]), maker_prefs))
        search_specs.append((danawa_query_for_part(query, part_type), maker_prefs))
        for maker in maker_prefs:
            maker_query = danawa_query_for_part(query, part_type, maker)
            if all(maker_query != existing for existing, _ in search_specs):
                search_specs.append((maker_query, [maker]))
    else:
        search_specs.append((danawa_query_for_part(query, part_type), []))

    best: Optional[Dict[str, Any]] = None
    for search_query, prefs in search_specs:
        search_url = danawa_search_url(search_query)
        if not search_url:
            continue

        req = Request(search_url, headers=DANAWA_HEADERS)
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
        html = raw.decode(charset, errors="ignore")
        result = parse_danawa_top_product(html, search_url, query, part_type, catalog_price, prefs)
        if not result or not result.get("price"):
            continue
        result["shop"] = "Danawa"
        result["currency"] = "KRW"
        result["price_source"] = "danawa_top_live"
        if best is None or safe_int(result.get("price"), 0) < safe_int(best.get("price"), 0):
            best = result
        if prefs and len(prefs) == 1 and best:
            break
    if best and include_image_preview and not best.get("image_url") and safe_external_url(best.get("url")):
        try:
            best["image_url"] = page_preview_meta(best.get("url"), best.get("name", "")).get("image_url") or ""
        except Exception:
            best["image_url"] = ""
    return best

# ─────────────────────────────────────────────────────────────
# Live Danawa product browser (direct-spec screen)
# ─────────────────────────────────────────────────────────────


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
    allowed = DANAWA_BROWSE_CATEGORY_IDS.get(ctype, set())
    category_id = danawa_url_category_id(url)
    if allowed and category_id:
        return category_id in allowed
    return danawa_category_matches(ctype, category)

def danawa_browse_candidate_valid(part_type: Any, product_name: Any, category: Any, url: Any, price: Any) -> bool:
    ctype = normalize_browse_part_type(part_type)
    product = clean_visible_text(product_name)
    target_url = safe_external_url(url)
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
        vendor = infer_cpu_metadata(name).get("vendor")
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

    performance_index, metric = component_performance_index(item, ctype)
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

COMPUZONE_CATEGORY_IDS = {
    "cpu": "1012", "mb": "1013", "ram": "1014", "storage": "1276",
    "hdd": "1015", "gpu": "1016", "case": "1147", "psu": "1148",
    "software": "1011",
}
MARKET_BROWSE_CACHE: Dict[Tuple[Any, ...], Dict[str, Any]] = {}


def compuzone_browse_url(part_type: str, query: str = "", page: int = 1, limit: int = 40) -> str:
    # This public endpoint renders the same product rows as the category UI.
    # Each scroll page is 20 rows; StartNum advances the requested outer page.
    return "https://www.compuzone.co.kr/product/product_list.php?" + urlencode({
        "actype": "getList", "BigDivNo": "9" if part_type == "software" else "4",
        "MediumDivNo": COMPUZONE_CATEGORY_IDS.get(part_type, ""), "DivNo": "0",
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
        if not code or code in seen or params.get("MediumDivNo") != COMPUZONE_CATEGORY_IDS.get(ctype):
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
    if any(token in lower for token in ("중고", "리퍼", "refurb", "노트북용", "sodimm", "so-dimm")):
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


def _market_fetch_html(url: str, provider: str, timeout: float = 8.0) -> str:
    headers = {**DANAWA_HEADERS, "Referer": "https://www.compuzone.co.kr/" if provider == "compuzone" else "https://search.danawa.com/"}
    with urlopen(Request(url, headers=headers), timeout=timeout) as response:
        raw = response.read(8_000_000)
        charset = response.headers.get_content_charset() or ("cp949" if provider == "compuzone" else "utf-8")
    return raw.decode(charset, errors="replace")


def _market_source_page(part_type: str, query: str, page: int, limit: int, provider: str, refresh: bool = False, timeout: float = 8.0, persist: bool = True) -> Dict[str, Any]:
    key = (part_type, normalize_text(query), page, limit, provider)
    now = datetime.utcnow()
    cached = MARKET_BROWSE_CACHE.get(key)
    if cached and not refresh and (now - cached["fetched_at"]).total_seconds() < DANAWA_BROWSE_CACHE_TTL_SECONDS:
        return {**cached["payload"], "cached": True}
    query_used = query or DANAWA_BROWSE_DEFAULT_QUERIES[part_type]
    url = danawa_browse_url(query_used, page, limit) if provider == "danawa" else compuzone_browse_url(part_type, query, page, limit)
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
        if query and (model_tokens(query) or re.search(r'\d\s*(?:GB|TB)\b', query, re.I)):
            items = [item for item in items if compatible_price_name(query, item["name"])]
        payload = {**base, "status": "live" if items else "empty", "items": items, "has_more": has_more,
                   "checked_at": now.isoformat(timespec="seconds") + "Z", "raw_count": raw_count}
        MARKET_BROWSE_CACHE[key] = {"fetched_at": now, "payload": payload}
        if len(MARKET_BROWSE_CACHE) > 240:
            oldest = min(MARKET_BROWSE_CACHE, key=lambda k: MARKET_BROWSE_CACHE[k]["fetched_at"])
            MARKET_BROWSE_CACHE.pop(oldest, None)
        if persist:
            remember_products(part_type, items)
        return payload
    except Exception:
        if cached and cached["payload"].get("items"):
            old = cached["payload"]
            items = [{**item, "price_status": "stale", "price_stale": True, "price_verified": False,
                      "price_source": provider + "_stale"} for item in old["items"]]
            return {**old, "status": "stale", "items": items, "cached": True, "error": "판매처 응답 지연으로 이전 확인 가격을 표시합니다."}
        return {**base, "status": "unavailable", "error": ("다나와" if provider == "danawa" else "컴퓨존") + " 상품 목록을 불러오지 못했습니다."}


def market_products_response(part_type: Any, query: Any = "", page: Any = 1, limit: Any = 40, refresh: Any = False, source: Any = "all", persist: bool = True) -> Dict[str, Any]:
    ctype = normalize_browse_part_type(part_type)
    provider = normalize_text(source) or "all"
    if not ctype or provider not in {"all", "danawa", "compuzone"}:
        return {"ok": False, "status": "invalid", "error": "지원하지 않는 부품 종류 또는 판매처입니다.", "items": []}
    query = clean_visible_text(query)[:120]
    page = max(1, min(100, safe_int(page, 1)))
    # Compuzone serves fixed 20-row scroll batches. Use that same page size for
    # both sources so subsequent pages do not skip products.
    limit = 20 if provider == "compuzone" else max(8, min(40, safe_int(limit, 40)))
    force = refresh is True or normalize_text(refresh) in {"1", "true", "yes"}
    providers = ["danawa", "compuzone"] if provider == "all" else [provider]
    with ThreadPoolExecutor(max_workers=len(providers)) as executor:
        futures = [executor.submit(_market_source_page, ctype, query, page, 20 if p == "compuzone" else limit, p, force, 8.0, persist) for p in providers]
        results = [future.result() for future in futures]
    items = []
    # Interleave retailers without treating two different SKUs as interchangeable.
    for index in range(max((len(result["items"]) for result in results), default=0)):
        items.extend(result["items"][index] for result in results if index < len(result["items"]))
    statuses = [result["status"] for result in results]
    status = "live" if "live" in statuses else "stale" if "stale" in statuses else "empty" if "empty" in statuses else "unavailable"
    return {
        "ok": status != "unavailable", "status": status, "type": ctype,
        "query": query, "query_used": query or DANAWA_BROWSE_DEFAULT_QUERIES[ctype],
        "page": page, "limit": limit, "items": items, "total": None,
        "has_more": any(result["has_more"] for result in results),
        "source": provider, "source_status": {result["provider"]: result["status"] for result in results},
        "source_urls": {result["provider"]: result["source_url"] for result in results},
        "cached": bool(results) and all(result["cached"] for result in results),
        "sort": "popular", "sort_label": "판매처 인기상품순",
        "error": next((result.get("error", "") for result in results if result.get("error")), ""),
    }


def danawa_products_response(part_type: Any, query: Any = "", page: Any = 1, limit: Any = 40, refresh: Any = False) -> Dict[str, Any]:
    """Backward-compatible alias used by earlier clients."""
    return market_products_response(part_type, query, page, limit, refresh, "danawa")


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
        if response.get("status") != "live":
            continue
        for item in response["items"]:
            if not compatible_price_name(query, item["name"]):
                continue
            if prefs and gpu_maker_normalize(item["name"]) not in prefs:
                continue
            if not price_sane_for_part(ctype, item["price"], query, catalog_price):
                continue
            matches.append(item)
    if not matches:
        return None
    best = dict(min(matches, key=lambda item: item["price"]))
    best.update(matched_by="market_exact_model", search_url=next((r["source_url"] for r in results if r["provider"] in best["price_source"]), ""))
    return best


def resolution_key(value: Any) -> str:
    s = normalize_text(value)
    if s in {"2160", "4k", "uhd", "3840x2160", "ultra hd"}:
        return "2160"
    if s in {"1440", "qhd", "wqhd", "2560x1440"}:
        return "1440"
    return "1080"

def refresh_value(value: Any) -> int:
    return max(30, safe_int(value, 60))

def vendor_normalize(value: Any) -> str:
    s = normalize_text(value)
    if not s or s in {"any", "nopref", "none", "무관"}:
        return "ANY"
    if "nvidia" in s or "geforce" in s:
        return "NVIDIA"
    if "amd" in s or "radeon" in s:
        return "AMD"
    return "ANY"

def genres_normalize(genres: Any) -> List[str]:
    if isinstance(genres, str):
        items = [x.strip().lower() for x in genres.replace(",", " ").split() if x.strip()]
        return items or ["default"]
    if isinstance(genres, list):
        out = [str(x).strip().lower() for x in genres if str(x).strip()]
        return out or ["default"]
    return ["default"]

def stable_seed(payload: Dict[str, Any]) -> int:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return abs(hash(blob)) % (2**32)

def guess_mime(path: Path) -> str:
    return {
        ".html": "text/html; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
    }.get(path.suffix.lower(), "application/octet-stream")

def component_performance_index(part: Dict[str, Any], part_type: str) -> Tuple[float, str]:
    """Return a 0-100 component-type-specific index for direct-build value display."""
    name = normalize_text(part.get("name"))
    tags = {normalize_text(tag) for tag in part.get("tags", [])}
    if part_type == "gpu":
        return clamp(gpu_base_perf(part, "1440"), 0.0, 100.0), "QHD 래스터 지수"
    if part_type == "cpu":
        return clamp(safe_float(part.get("perf"), 0.0), 0.0, 100.0), "CPU 처리 지수"
    if part_type == "ram":
        gb = safe_float(part.get("gb"), 0.0)
        speed = safe_float(part.get("speed"), 0.0)
        base = min(72.0, gb / 64.0 * 72.0)
        bandwidth = min(24.0, max(0.0, (speed - 2400.0) / 55.0))
        generation = 5.0 if normalize_text(part.get("type")) == "ddr5" else 0.0
        return clamp(base + bandwidth + generation, 0.0, 100.0), "메모리 용량·대역폭 지수"
    if part_type == "mb":
        socket = normalize_text(part.get("socket"))
        score = 46.0 + (18.0 if normalize_text(part.get("ram_type")) == "ddr5" else 0.0)
        score += 16.0 if socket in {"am5", "lga1851"} else 10.0 if socket == "lga1700" else 4.0
        score += {"high": 16.0, "mid": 9.0, "low": 3.0}.get(normalize_text(part.get("tier")), 0.0)
        return clamp(score, 0.0, 100.0), "확장성·전원부 지수"
    if part_type == "storage":
        capacity = safe_float(part.get("capacity"), 0.0)
        score = min(55.0, capacity / 4000.0 * 55.0)
        if "gen5" in name or "gen5" in tags:
            score += 42.0
        elif "gen4" in name or "gen4" in tags or "nvme" in name:
            score += 30.0
        elif "sata" in name or "sata" in tags:
            score += 12.0
        else:
            score += 20.0
        return clamp(score, 0.0, 100.0), "저장공간·속도 지수"
    if part_type == "hdd":
        capacity = safe_float(part.get("capacity"), 0.0)
        rpm = safe_float(part.get("rpm"), 0.0)
        return clamp(min(78.0, capacity / 12000.0 * 78.0) + (18.0 if rpm >= 7200 else 10.0 if rpm else 0.0), 0.0, 100.0), "저장공간·회전수 지수"
    if part_type == "psu":
        watt = safe_float(part.get("watt"), safe_float(part.get("recommendedWatt"), 0.0))
        score = min(78.0, watt / 1200.0 * 78.0)
        score += 22.0 if "platinum" in name else 16.0 if "gold" in name else 8.0 if "bronze" in name else 0.0
        return clamp(score, 0.0, 100.0), "출력·효율 지수"
    if part_type == "case":
        score = {"low": 48.0, "mid": 66.0, "high": 82.0}.get(normalize_text(part.get("tier")), 52.0)
        if "airflow" in tags:
            score += 8.0
        return clamp(score, 0.0, 100.0), "냉각·확장성 지수"
    if part_type == "software":
        if normalize_text(part.get("license")) == "none":
            return 0.0, "소프트웨어 구성 지수"
        score = 48.0
        if "pro" in name or "business" in tags:
            score += 28.0
        if "creative" in tags or "video" in tags:
            score += 20.0
        return clamp(score, 0.0, 100.0), "소프트웨어 구성 지수"
    return 0.0, "성능 지수"

def summarize_part(part: Dict[str, Any], part_type: str) -> Dict[str, Any]:
    raw_price = safe_int(part.get("price"), 0)
    raw_source = normalize_text(part.get("price_source"))
    raw_url = part.get("url") or part.get("shop_url") or part.get("product_url")
    verified_gpu_listing = verified_price_info(part)
    price_info = {} if verified_gpu_listing else (db_lookup_price_info(part, part_type) or {})
    if price_info.get("stale"):
        price_info = {}
    price = raw_price if verified_gpu_listing else price_info.get("price")
    if price is None:
        price = raw_price
    performance_index, performance_metric = component_performance_index(part, part_type)
    value_per_10000 = 0.0 if price <= 0 else round(performance_index / max(1.0, price / 10000.0), 3)
    out = {
        "id": part.get("id"),
        "name": part.get("name"),
        "product_name": (part.get("product_name") if verified_gpu_listing else price_info.get("name")) or part.get("product_name") or part.get("name"),
        "price": price,
        "base_price": safe_int(part.get("base_price"), 0) or raw_price,
        "tier": part.get("tier"),
        "shop": (part.get("shop") if verified_gpu_listing else price_info.get("shop")) or part.get("shop") or "Catalog",
        "url": (part.get("url") if verified_gpu_listing else price_info.get("url")) or part.get("url") or danawa_search_url(part.get("name")),
        "image_url": (part.get("image_url") if verified_gpu_listing else price_info.get("image_url")) or part.get("image_url") or part_image_endpoint(part, part_type),
        "currency": (part.get("currency") if verified_gpu_listing else price_info.get("currency")) or part.get("currency") or "KRW",
        "price_source": (part.get("price_source") if verified_gpu_listing else price_info.get("price_source")) or part.get("price_source") or ("db" if price_info else "catalog_search"),
        "price_source_label": (part.get("price_source_label") if verified_gpu_listing else price_info.get("matched_by")) or part.get("price_source_label") or ("catalog" if not price_info else "db"),
        "performance_index": round(performance_index, 1),
        "performance_metric": performance_metric,
        "value_per_10000krw": value_per_10000,
        "scraped_at": (part.get("scraped_at") if verified_gpu_listing else price_info.get("scraped_at")) or part.get("scraped_at"),
        "verified": bool(verified_gpu_listing or price_info),
        "price_status": "verified" if verified_gpu_listing or price_info else ("estimated" if price > 0 else "unavailable"),
    }
    if part_type == "cpu":
        out.update({
            "socket": part.get("socket"),
            "vendor": part.get("vendor"),
            "tdp": part.get("tdp"),
            "cores": part.get("cores"),
            "threads": part.get("threads"),
        })
    elif part_type == "gpu":
        out.update({
            "vram": part.get("vram"),
            "tdp": part.get("tdp"),
            "vendor": part.get("vendor"),
            "perf_1080": part.get("perf_1080"),
            "perf_1440": part.get("perf_1440"),
            "perf_2160": part.get("perf_2160"),
        })
    elif part_type == "ram":
        out.update({"brand": part.get("brand"), "type": part.get("type"), "gb": part.get("gb"), "speed": part.get("speed")})
    elif part_type == "mb":
        out.update({"socket": part.get("socket"), "ram_type": part.get("ram_type"), "brand": part.get("brand")})
    elif part_type == "psu":
        out.update({"brand": part.get("brand"), "recommendedWatt": part.get("watt"), "watt": part.get("watt")})
    elif part_type == "storage":
        out.update({"brand": part.get("brand"), "capacity": part.get("capacity")})
    elif part_type == "hdd":
        out.update({"brand": part.get("brand"), "capacity": part.get("capacity"), "rpm": part.get("rpm")})
    elif part_type == "case":
        out.update({"brand": part.get("brand"), "form_factor": part.get("form_factor"), "color": part.get("color")})
    elif part_type == "software":
        out.update({"brand": part.get("brand"), "license": part.get("license")})
    return out

def fps_capacity_label(
    average_fps: Any,
    low1_fps: Any,
    target_fps: Any,
    target_low1_fps: Any,
) -> str:
    """Describe target coverage separately from price efficiency.

    A build that clears the requested refresh target should never be marked
    insufficient just because its raw FPS-per-won ratio is modest.
    """
    average = safe_float(average_fps, 0.0)
    low1 = safe_float(low1_fps, 0.0)
    target = safe_float(target_fps, 0.0)
    low_target = safe_float(target_low1_fps, 0.0)
    if average <= 0 or target <= 0:
        return "측정 대기"

    average_coverage = average / target
    low1_coverage = low1 / low_target if low_target > 0 else average_coverage
    if average_coverage >= 1.20 and low1_coverage >= 1.0:
        return "목표 성능 여유"
    if average_coverage >= 1.0 and low1_coverage >= 0.88:
        return "목표 성능 충족"
    if average_coverage >= 0.85:
        return "거의 충족"
    if average_coverage >= 0.60:
        return "다소 부족"
    return "매우 부족"

def value_metrics(
    fps: Any,
    price: Any,
    target_fps: Any = 0.0,
    low1_fps: Any = 0.0,
    target_low1_fps: Any = 0.0,
) -> Dict[str, Any]:
    """Return cost efficiency and requested-performance coverage independently."""
    avg_fps = safe_float(fps, 0.0)
    total_price = safe_float(price, 0.0)
    target = safe_float(target_fps, 0.0)
    low1 = safe_float(low1_fps, 0.0)
    low_target = safe_float(target_low1_fps, 0.0)
    fps_per_1000 = avg_fps / max(1.0, total_price / 1000.0) if avg_fps > 0 and total_price > 0 else 0.0
    target_coverage = avg_fps / target if target > 0 else 0.0
    low1_target_coverage = low1 / low_target if low_target > 0 else 0.0
    return {
        "fps_per_1000krw": round(fps_per_1000, 4),
        "price_per_frame_krw": round(total_price / avg_fps, 2) if avg_fps > 0 and total_price > 0 else None,
        "score": round(fps_per_1000 * 100.0, 1),
        "target_fps": round(target, 1),
        "target_low1_fps": round(low_target, 1),
        "target_coverage": round(target_coverage, 3),
        "low1_target_coverage": round(low1_target_coverage, 3),
        "capacity_label": fps_capacity_label(avg_fps, low1, target, low_target),
    }

def value_label(value_score: float) -> str:
    if value_score >= 9.0:
        return "최상 가성비"
    if value_score >= 7.0:
        return "좋은 가성비"
    if value_score >= 5.0:
        return "적정"
    if value_score >= 3.0:
        return "다소 부족"
    return "매우 부족"

def low1_ratio_for_genres(genres: List[str]) -> float:
    if any(g in genres for g in ["fps", "valorant", "cs", "cs2", "competitive"]):
        return 0.86
    if any(g in genres for g in ["rpg", "aaa", "action"]):
        return 0.80
    if any(g in genres for g in ["mmo", "lostark", "wow", "mmorpg"]):
        return 0.77
    if any(g in genres for g in ["sim", "simulation", "cities"]):
        return 0.73
    if any(g in genres for g in ["openworld", "open_world"]):
        return 0.76
    if any(g in genres for g in ["subculture", "anime"]):
        return 0.82
    return 0.79


GAME_GENRE_FACTORS = {
    item["id"]: (item["genre"], {
        "fps": 1.55,
        "rpg": 0.76,
        "openworld": 0.70,
        "aaa": 0.66,
        "subculture": 1.05,
        "mmo": 1.15,
        "sim": 0.58,
    }.get(item["genre"], 1.0))
    for item in GAME_OPTIONS
}
GAME_GENRE_FACTORS.update({
    "valorant": ("fps", 2.20),
    "cs2": ("fps", 2.00),
    "csgo2": ("fps", 2.00),
    "csgo": ("fps", 2.50),
    "rainbow6": ("fps", 1.85),
    "cyberpunk2077": ("rpg", 0.48),
    "witcher3": ("rpg", 0.82),
    "elden_ring": ("rpg", 0.76),
    "baldurs_gate3": ("rpg", 0.70),
    "msfs2024": ("sim", 0.34),
})

def game_profile(game: str) -> Tuple[str, float]:
    g = normalize_text(game).replace(" ", "_")
    return GAME_GENRE_FACTORS.get(g, ("default", 1.0))

def option_factors(resolution: str, tier: str) -> Dict[str, float]:
    if resolution == "2160":
        base = {"low": 1.08, "medium": 0.88, "high": 0.70, "ultra": 0.56}
    elif resolution == "1440":
        base = {"low": 1.35, "medium": 1.05, "high": 0.84, "ultra": 0.67}
    else:
        base = {"low": 1.60, "medium": 1.25, "high": 1.00, "ultra": 0.80}

    tier_adjust = {"low": 0.95, "mid": 1.00, "high": 1.05}[tier]
    return {k: round(v * tier_adjust, 4) for k, v in base.items()}

def budget_allocations(total_budget: int, resolution: str, refresh: int, genre_class: str, tier: str) -> Dict[str, int]:
    if resolution == "2160":
        shares = {"gpu": 0.52, "cpu": 0.15, "ram": 0.10, "mb": 0.08, "psu": 0.08, "storage": 0.07}
    elif resolution == "1440":
        shares = {"gpu": 0.43, "cpu": 0.19, "ram": 0.11, "mb": 0.08, "psu": 0.08, "storage": 0.11}
    else:
        shares = {"gpu": 0.34, "cpu": 0.25, "ram": 0.12, "mb": 0.08, "psu": 0.08, "storage": 0.13}

    if refresh >= 144 and resolution == "1080":
        shares["cpu"] += 0.04
        shares["gpu"] -= 0.02
        shares["ram"] += 0.01

    if genre_class == "sim":
        shares["cpu"] += 0.03
        shares["gpu"] -= 0.02
    elif genre_class == "mmo":
        shares["cpu"] += 0.02
        shares["ram"] += 0.01
    elif genre_class == "rpg":
        shares["gpu"] += 0.01

    if tier == "low":
        shares["gpu"] -= 0.02
        shares["storage"] += 0.02
    elif tier == "high":
        shares["gpu"] += 0.03
        shares["storage"] -= 0.01

    total = sum(max(0.01, v) for v in shares.values())
    shares = {k: max(0.01, v) / total for k, v in shares.items()}
    alloc = {k + "Budget": int(total_budget * v) for k, v in shares.items()}
    gap = total_budget - sum(alloc.values())
    alloc["gpuBudget"] += gap
    return alloc

# ─────────────────────────────────────────────────────────────
# SQLite cache
# ─────────────────────────────────────────────────────────────

DB_CACHE: Dict[str, Any] = {
    "loaded": False,
    "components": [],
    "prices_by_name": {},
    "prices_by_url": {},
    "benchmarks_by_name": {},
    "summary": {},
}
# Benchmark lookup is invoked for every candidate. Cache the immutable DB
# result per model/game and clear it whenever the SQLite snapshot is reloaded.
BENCHMARK_LOOKUP_CACHE: Dict[Tuple[str, str, bool], Tuple[Dict[str, Any], ...]] = {}

def table_columns(conn: sqlite3.Connection, table: str) -> set:
    try:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()

def init_db_schema() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS components (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        type       TEXT NOT NULL,
        name       TEXT NOT NULL,
        brand      TEXT,
        model      TEXT,
        socket     TEXT,
        vram       INTEGER,
        tdp        INTEGER,
        perf_score INTEGER DEFAULT 0,
        msrp       INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(type, name)
    );
    CREATE TABLE IF NOT EXISTS prices (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        component_id INTEGER NOT NULL REFERENCES components(id),
        shop         TEXT NOT NULL,
        currency     TEXT NOT NULL DEFAULT 'KRW',
        price        INTEGER NOT NULL,
        url          TEXT,
        scraped_at   TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(component_id, shop, scraped_at)
    );
    CREATE TABLE IF NOT EXISTS benchmarks (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        component_id INTEGER NOT NULL REFERENCES components(id),
        game         TEXT NOT NULL,
        resolution   TEXT NOT NULL,
        setting      TEXT NOT NULL,
        avg_fps      REAL,
        low1_fps     REAL,
        source_url   TEXT,
        scraped_at   TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(component_id, game, resolution, setting, source_url)
    );
    """)

    component_defaults = {
        "brand": "TEXT",
        "model": "TEXT",
        "socket": "TEXT",
        "vram": "INTEGER",
        "tdp": "INTEGER",
        "perf_score": "INTEGER DEFAULT 0",
        "msrp": "INTEGER DEFAULT 0",
        "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
    }
    cols = table_columns(conn, "components")
    for col, ddl in component_defaults.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE components ADD COLUMN {col} {ddl}")

    price_defaults = {
        "currency": "TEXT NOT NULL DEFAULT 'KRW'",
        "url": "TEXT",
        "scraped_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
    }
    cols = table_columns(conn, "prices")
    for col, ddl in price_defaults.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE prices ADD COLUMN {col} {ddl}")

    conn.commit()
    conn.close()

def load_config() -> None:
    global HYBRID_CONFIG
    if CONFIG_PATH.exists():
        try:
            HYBRID_CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            HYBRID_CONFIG = {}
    else:
        HYBRID_CONFIG = {}

def _ensure_db_connection(create: bool = False) -> Optional[sqlite3.Connection]:
    if create:
        init_db_schema()
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def upsert_component(conn: sqlite3.Connection, part_type: str, name: str) -> int:
    ctype = normalize_text(part_type).upper() or "PART"
    clean_name = clean_visible_text(name)
    cur = conn.cursor()
    row = cur.execute("SELECT id FROM components WHERE type=? AND name=?", (ctype, clean_name)).fetchone()
    if row:
        return int(row["id"] if isinstance(row, sqlite3.Row) else row[0])

    cur.execute(
        "INSERT OR IGNORE INTO components(type, name, brand) VALUES (?,?,?)",
        (ctype, clean_name, vendor_normalize(clean_name) if ctype in {"CPU", "GPU"} else ""),
    )
    row = cur.execute("SELECT id FROM components WHERE type=? AND name=?", (ctype, clean_name)).fetchone()
    conn.commit()
    return int(row["id"] if isinstance(row, sqlite3.Row) else row[0])

def insert_price(conn: sqlite3.Connection, component_id: int, price: int, url: str, shop: str = "Danawa") -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO prices(component_id, shop, currency, price, url)
        VALUES (?,?,?,?,?)
        """,
        (component_id, shop, "KRW", int(price), url),
    )
    conn.commit()

def price_is_fresh(scraped_at: Any, max_age_hours: int = DANAWA_PRICE_MAX_AGE_HOURS) -> bool:
    raw = str(scraped_at or "").strip()
    if not raw:
        return False
    try:
        checked = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        now = datetime.now(checked.tzinfo) if checked.tzinfo else datetime.utcnow()
        age = now - checked
        return timedelta(0) <= age <= timedelta(hours=max_age_hours)
    except (ValueError, TypeError):
        return False

def market_product_url(url: Any) -> bool:
    try:
        parsed = urlparse(str(url or ""))
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"}:
            return False
        if host == "prod.danawa.com":
            return bool(re.search(r"(?:\?|&)pcode=\d+", parsed.query and "?" + parsed.query))
        return (host == "compuzone.co.kr" or host.endswith(".compuzone.co.kr")) and bool(
            re.search(r"(?:\?|&)(?:ProductNo|productno|product_no)=\d+", "?" + parsed.query)
        )
    except ValueError:
        return False

def verified_price_info(part: Dict[str, Any]) -> bool:
    source = normalize_text(part.get("price_source"))
    return (
        safe_int(part.get("price"), 0) > 0
        and not part.get("stale")
        and source not in {"", "catalog", "catalog_search", "catalog_fallback", "danawa_search", "estimated", "unavailable"}
        and market_product_url(part.get("url"))
        and price_is_fresh(part.get("scraped_at") or part.get("checked_at"))
    )

def _best_match_key(query: str, keys: Iterable[str]) -> Optional[str]:
    q = canonical_name(query)
    if not q:
        return None
    keys_list = list(keys)
    if q in keys_list:
        return q

    q_tokens = set(q.split())
    best = None
    best_score = 0.0
    for key in keys_list:
        k_tokens = set(key.split())
        inter = len(q_tokens & k_tokens)
        denom = max(1, len(q_tokens | k_tokens))
        score = inter / denom
        if q in key or key in q:
            score += 0.6
        if score > best_score:
            best = key
            best_score = score
    return best if best_score >= 0.25 else None

def load_db_cache() -> None:
    BENCHMARK_LOOKUP_CACHE.clear()
    conn = _ensure_db_connection()
    if conn is None:
        DB_CACHE.update({
            "loaded": False,
            "components": [],
            "prices_by_name": {},
            "prices_by_url": {},
            "benchmarks_by_name": {},
            "summary": {},
        })
        return

    cur = conn.cursor()

    components: List[Dict[str, Any]] = []
    try:
        cols = table_columns(conn, "components")
        select_cols = ["id", "type", "name"]
        select_cols.extend(col for col in ["brand", "model", "socket", "vram", "tdp"] if col in cols)
        rows = cur.execute(f"SELECT {', '.join(select_cols)} FROM components").fetchall()
        for r in rows:
            item = dict(r)
            for col in ["brand", "model", "socket", "vram", "tdp"]:
                item.setdefault(col, None)
            components.append(item)
    except Exception:
        components = []

    prices_by_name: Dict[str, Dict[str, Any]] = {}
    prices_by_url: Dict[str, Dict[str, Any]] = {}
    try:
        price_rows = cur.execute("""
            SELECT c.type, c.name, p.price, p.currency, p.shop, p.url, p.scraped_at
            FROM prices p
            JOIN components c ON c.id = p.component_id
            ORDER BY p.scraped_at DESC, p.id DESC
        """).fetchall()
        for r in price_rows:
            row = dict(r)
            name_key = canonical_name(row.get("name"))
            if name_key and name_key not in prices_by_name:
                prices_by_name[name_key] = row

            url_key = normalize_product_url(row.get("url"))
            if url_key and url_key not in prices_by_url:
                prices_by_url[url_key] = row
    except Exception:
        prices_by_name = {}
        prices_by_url = {}

    benchmarks_by_name: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    try:
        bench_rows = cur.execute("""
            SELECT c.type, c.name, b.game, b.resolution, b.setting, b.avg_fps, b.low1_fps, b.source_url, b.scraped_at
            FROM benchmarks b
            JOIN components c ON c.id = b.component_id
            ORDER BY b.scraped_at DESC, b.id DESC
        """).fetchall()
        for r in bench_rows:
            name_key = canonical_name(r["name"])
            if not name_key:
                continue
            game_key = normalize_text(r["game"]).replace(" ", "_")
            res_key = resolution_key(r["resolution"])
            setting = normalize_text(r["setting"])
            item = dict(r)
            item["avg_fps"] = safe_float(item.get("avg_fps"))
            item["low1_fps"] = safe_float(item.get("low1_fps"))
            benchmarks_by_name.setdefault(name_key, {}).setdefault(game_key, []).append(
                {**item, "resolution": res_key, "setting": setting}
            )
    except Exception:
        benchmarks_by_name = {}

    DB_CACHE.update({
        "loaded": True,
        "components": components,
        "prices_by_name": prices_by_name,
        "prices_by_url": prices_by_url,
        "benchmarks_by_name": benchmarks_by_name,
        "summary": {
            "components": len(components),
            "prices": max(len(prices_by_name), len(prices_by_url)),
            "benchmarks": sum(len(rows) for by_game in benchmarks_by_name.values() for rows in by_game.values()),
        },
    })
    conn.close()

def ensure_db_cache_loaded() -> None:
    if not DB_CACHE.get("loaded") and DB_PATH.exists():
        load_db_cache()

def db_lookup_price_info(part: Dict[str, Any], part_type: str) -> Optional[Dict[str, Any]]:
    ensure_db_cache_loaded()
    part_name = part.get("name")
    part_type_key = normalize_text(part_type)
    part_url = normalize_product_url(part.get("url") or part.get("shop_url") or part.get("product_url") or part.get("source_url"))
    catalog_price = safe_int(part.get("base_price"), 0) or safe_int(part.get("price"), 0)

    # 1) Prefer an exact product URL match when the crawler captured one.
    if part_url:
        url_rows = DB_CACHE.get("prices_by_url", {}) or {}
        row = url_rows.get(part_url)
        if row:
            try:
                price = int(row.get("price"))
            except Exception:
                price = 0
            if (
                price > 0
                and (not row.get("type") or normalize_text(row.get("type")) == part_type_key)
                and compatible_price_name(part_name, row.get("name"))
                and str(row.get("currency") or "KRW").upper() == "KRW"
                and market_product_url(row.get("url") or part_url)
                and price_sane_for_part(part_type, price, part_name, catalog_price)
                and danawa_url_category_matches(part_type, row.get("url") or part_url)
                and not danawa_url_rejected(part_type, row.get("url") or part_url)
            ):
                return {
                    "price": price,
                    "shop": row.get("shop") or "Danawa",
                    "url": row.get("url") or part.get("url") or danawa_search_url(part_name),
                    "currency": row.get("currency") or "KRW",
                    "scraped_at": row.get("scraped_at"),
                    "stale": not price_is_fresh(row.get("scraped_at")),
                    "matched_by": "url_exact",
                    "price_source": "db_url_exact",
                    "name": row.get("name"),
                    "type": row.get("type"),
                }

    # 2) Fallback to best name match.
    rows = DB_CACHE.get("prices_by_name", {}) or {}
    key = canonical_name(part_name)
    type_filtered = [
        k for k, row in rows.items()
        if (not row.get("type") or normalize_text(row.get("type")) == part_type_key)
        and compatible_price_name(part_name, row.get("name"))
    ]
    match = _best_match_key(key, type_filtered)
    if not match:
        return None
    row = rows.get(match) or {}
    if str(row.get("currency") or "KRW").upper() != "KRW" or not market_product_url(row.get("url")):
        return None
    if not compatible_price_name(part_name, row.get("name")):
        return None

    try:
        price = int(row.get("price"))
    except Exception:
        return None
    if price <= 0:
        return None

    if not price_sane_for_part(part_type, price, part_name, catalog_price):
        return None
    if normalize_text(part_type) in {"gpu", "storage", "ssd", "mb", "motherboard", "mainboard"}:
        if not danawa_url_category_matches(part_type, row.get("url")):
            return None
        if danawa_url_rejected(part_type, row.get("url")):
            return None

    return {
        "price": price,
        "shop": row.get("shop") or "Danawa",
        "url": row.get("url") or part.get("url") or danawa_search_url(part_name),
        "currency": row.get("currency") or "KRW",
        "scraped_at": row.get("scraped_at"),
        "stale": not price_is_fresh(row.get("scraped_at")),
        "matched_by": "name_match",
        "price_source": "db_name_exact" if key == canonical_name(row.get("name")) else "db_name_fuzzy",
        "name": row.get("name"),
        "type": row.get("type"),
    }

def db_lookup_price(part: Dict[str, Any], part_type: str) -> Optional[int]:
    info = db_lookup_price_info(part, part_type)
    if info and info.get("stale"):
        return None
    return safe_int(info.get("price"), 0) if info else None

def part_image_endpoint(part: Dict[str, Any], part_type: Any) -> str:
    name = clean_visible_text(part.get("product_name") or part.get("name"))
    if not name:
        return ""
    return "/api/part-image?" + urlencode({"type": normalize_text(part_type), "name": name})

def market_lookup_name(part: Dict[str, Any], part_type: Any) -> str:
    name = clean_visible_text(part.get("product_name") or part.get("name"))
    if normalize_text(part_type) == "gpu" and safe_int(part.get("vram"), 0) and not re.search(r"\b\d+\s*gb\b", name, re.I):
        name += f" {safe_int(part.get('vram'), 0)}GB"
    return name

def store_danawa_price(part: Dict[str, Any], part_type: str, live: Dict[str, Any]) -> Dict[str, Any]:
    component_name = clean_visible_text(live.get("product_name") or live.get("name") or part.get("name"))
    shop = live.get("shop") or "Danawa"
    checked_at = live.get("scraped_at") or datetime.utcnow().isoformat(timespec="seconds") + "Z"
    conn = _ensure_db_connection(create=True)
    if conn is not None:
        try:
            cid = upsert_component(conn, part_type, component_name)
            insert_price(conn, cid, safe_int(live.get("price"), 0), live.get("url") or "", shop=shop)
        finally:
            conn.close()
        load_db_cache()
    return {
        "price": safe_int(live.get("price"), 0),
        "shop": shop,
        "url": live.get("url") or danawa_search_url(component_name),
        "image_url": live.get("image_url") or part.get("image_url") or part_image_endpoint({"name": component_name}, part_type),
        "currency": "KRW",
        "scraped_at": checked_at,
        "stale": False,
        "verified": True,
        "price_status": "verified",
        "matched_by": live.get("matched_by") or ("compuzone_top" if shop == "Compuzone" else "danawa_top"),
        "price_source": live.get("price_source") or ("compuzone_top_live" if shop == "Compuzone" else "danawa_top_live"),
        "name": component_name,
        "product_name": live.get("name") or component_name,
        "type": normalize_text(part_type).upper(),
    }

def get_or_fetch_danawa_price(
    part: Dict[str, Any],
    part_type: str,
    force: bool = False,
    allow_stale: bool = False,
    gpu_maker_prefs: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    maker_prefs = normalize_gpu_maker_prefs(gpu_maker_prefs)
    if normalize_text(part_type) == "gpu" and maker_prefs:
        force = True
    cached = db_lookup_price_info(part, part_type)
    if cached and not force and not cached.get("stale"):
        return {
            **cached,
            "image_url": cached.get("image_url") or part.get("image_url") or part_image_endpoint(part, part_type),
            "price_source": cached.get("price_source") or "db_cache",
        }

    try:
        live = fetch_market_top_product(
            market_lookup_name(part, part_type),
            part_type,
            catalog_price=safe_int(part.get("base_price"), 0) or safe_int(part.get("price"), 0),
            gpu_maker_prefs=maker_prefs,
        )
        if live and safe_int(live.get("price"), 0) > 0:
            return store_danawa_price(part, part_type, live)
    except Exception:
        pass

    if cached and allow_stale and not maker_prefs:
        return {
            **cached,
            "image_url": cached.get("image_url") or part.get("image_url") or part_image_endpoint(part, part_type),
            "price_source": cached.get("price_source") or "db_stale",
        }
    return None

GPU_MARKET_PRICE_CHECKED_AT: Dict[str, datetime] = {}
RECOMMENDATION_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}

def is_recommendable_gpu(part: Dict[str, Any]) -> bool:
    """Apply exclusions to catalog, retailer and fallback paths alike."""
    identity = " ".join(str(part.get(key) or "") for key in ("id", "performance_ref_id", "name", "product_name"))
    return not re.search(r"rtx[\s_-]*30\d{2}", identity, re.I)

def resolve_verified_gpu_market_prices(
    gpu_pref: str = "ANY",
    gpu_maker_prefs: Optional[List[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Return only GPU models with a current, valid Danawa graphics-card price.

    The embedded catalog is useful for specs, but it must not be used as the
    deciding price for a recommendation. Discontinued models frequently have
    stale prices, and search results can otherwise fall back to the wrong item.
    """
    maker_prefs = normalize_gpu_maker_prefs(gpu_maker_prefs)
    candidates = [
        part for part in GPU_CATALOG
        if is_recommendable_gpu(part)
        and (gpu_pref == "ANY" or normalize_text(part.get("vendor")) == normalize_text(gpu_pref))
    ]
    resolved: Dict[str, Dict[str, Any]] = {}
    pending: Dict[Any, Dict[str, Any]] = {}
    executor = ThreadPoolExecutor(max_workers=8)
    try:
        for part in candidates:
            part_id = str(part.get("id") or canonical_name(part.get("name")))
            # A maker preference changes the actual SKU, so it cannot reuse the
            # generic chip-level cache.
            checked = GPU_MARKET_PRICE_CHECKED_AT.get(part_id)
            cache_recent = bool(checked and datetime.utcnow() - checked < timedelta(minutes=5))
            if not maker_prefs and part_id in GPU_MARKET_PRICE_CACHE and cache_recent:
                cached = GPU_MARKET_PRICE_CACHE[part_id]
                if cached and verified_price_info(cached):
                    resolved[part_id] = {**part, **cached}
                    continue
                if cached is None:
                    continue

            cached = None if maker_prefs else db_lookup_price_info(part, "gpu")
            if cached and not cached.get("stale"):
                info = {
                    "price": safe_int(cached.get("price"), 0),
                    "url": cached.get("url"),
                    "image_url": cached.get("image_url") or part.get("image_url"),
                    "shop": cached.get("shop") or "Danawa",
                    "currency": cached.get("currency") or "KRW",
                    "price_source": cached.get("price_source") or "db_current",
                    "price_source_label": cached.get("matched_by") or "db_current",
                    "product_name": cached.get("name") or part.get("name"),
                    "scraped_at": cached.get("scraped_at"),
                    "verified": True,
                    "price_status": "verified",
                }
                GPU_MARKET_PRICE_CACHE[part_id] = info
                GPU_MARKET_PRICE_CHECKED_AT[part_id] = datetime.utcnow()
                resolved[part_id] = {**part, "base_price": safe_int(part.get("price"), 0), **info}
                continue

            future = executor.submit(
                fetch_market_top_product,
                market_lookup_name(part, "gpu"),
                "gpu",
                4.0,
                safe_int(part.get("price"), 0),
                maker_prefs or None,
                False,
            )
            pending[future] = part

        try:
            for future in as_completed(pending, timeout=3.0):
                part = pending[future]
                part_id = str(part.get("id") or canonical_name(part.get("name")))
                try:
                    live = future.result()
                except Exception:
                    live = None
                if not live or safe_int(live.get("price"), 0) <= 0:
                    if not maker_prefs:
                        GPU_MARKET_PRICE_CACHE[part_id] = None
                        GPU_MARKET_PRICE_CHECKED_AT[part_id] = datetime.utcnow()
                    continue
                try:
                    saved = store_danawa_price(part, "gpu", live)
                except Exception:
                    saved = {
                        "price": safe_int(live.get("price"), 0),
                        "url": live.get("url"),
                        "image_url": live.get("image_url"),
                        "shop": live.get("shop") or "Danawa",
                        "currency": "KRW",
                        "price_source": live.get("price_source") or "danawa_top_live",
                        "price_source_label": "danawa_top",
                        "product_name": live.get("name") or part.get("name"),
                        "scraped_at": live.get("scraped_at") or datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    }
                if safe_int(saved.get("price"), 0) <= 0:
                    continue
                info = {
                    "price": safe_int(saved.get("price"), 0),
                    "url": saved.get("url") or live.get("url"),
                    "image_url": saved.get("image_url") or live.get("image_url"),
                    "shop": saved.get("shop") or "Danawa",
                    "currency": saved.get("currency") or "KRW",
                    "price_source": saved.get("price_source") or "danawa_top_live",
                    "price_source_label": saved.get("matched_by") or "danawa_top",
                    "product_name": saved.get("product_name") or live.get("name") or part.get("name"),
                    "scraped_at": saved.get("scraped_at"),
                    "verified": True,
                    "price_status": "verified",
                }
                if not maker_prefs:
                    GPU_MARKET_PRICE_CACHE[part_id] = info
                    GPU_MARKET_PRICE_CHECKED_AT[part_id] = datetime.utcnow()
                resolved[part_id] = {**part, "base_price": safe_int(part.get("price"), 0), **info}
        except TimeoutError:
            pass

        if not maker_prefs:
            for future, part in pending.items():
                if future.done():
                    continue
                future.cancel()
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    return resolved

def apply_price_info_to_part(part: Dict[str, Any], info: Optional[Dict[str, Any]]) -> None:
    if not part:
        return
    if not info:
        part["verified"] = verified_price_info(part)
        if not part["verified"]:
            part["price_status"] = "estimated" if safe_int(part.get("price"), 0) > 0 else "unavailable"
        return
    price = safe_int(info.get("price"), 0)
    if price > 0:
        part["price"] = price
    if info.get("url"):
        part["url"] = info.get("url")
    if info.get("image_url"):
        part["image_url"] = info.get("image_url")
    part["shop"] = info.get("shop") or "Danawa"
    part["currency"] = info.get("currency") or "KRW"
    part["price_source"] = info.get("price_source") or "danawa_top"
    part["price_source_label"] = info.get("matched_by") or "danawa_top"
    part["stale"] = bool(info.get("stale"))
    if info.get("scraped_at"):
        part["scraped_at"] = info.get("scraped_at")
    if info.get("product_name"):
        part["product_name"] = info.get("product_name")
    elif info.get("name"):
        part["product_name"] = info.get("name")
    part["verified"] = verified_price_info(part)
    part["price_status"] = "verified" if part["verified"] else ("stale" if part["stale"] else "estimated")

DISPLAY_PRICE_TYPES = {"cpu", "gpu", "ram", "mb", "storage", "psu", "hdd", "case", "software"}

def recompute_plan_total(plan: Dict[str, Any]) -> None:
    parts = plan.get("parts") or {}
    total = sum(safe_int(part.get("price"), 0) for part in parts.values() if isinstance(part, dict))
    plan["totalPrice"] = total
    plan["total_price"] = total
    plan.setdefault("debug", {})["total_price"] = total
    tier_budget = safe_int(plan.get("tierBudget"), 0)
    max_budget = safe_int(plan.get("budget_max"), 0) or tier_budget
    min_budget = safe_int(plan.get("budget_min"), 0)
    overrun = max(0, total - tier_budget) if tier_budget else 0
    plan["debug"]["overrun"] = overrun
    if tier_budget:
        budget_fit = max(-0.55, 1.0 - overrun / max(1.0, tier_budget * 0.16)) if overrun else 1.0 - min(0.22, (tier_budget - total) / tier_budget * 0.18)
        plan["debug"]["budget_fit"] = round(budget_fit, 4)
        plan.setdefault("predictions", {})["budget_fit"] = round(budget_fit, 4)
    plan["budget_overrun"] = max(0, total - max_budget) if max_budget else 0
    plan["budget_status"] = "over_budget" if max_budget and total > max_budget else "under_budget" if total < min_budget else "within_budget"
    selected_parts = [part for part in parts.values() if isinstance(part, dict)]
    verified_count = sum(1 for part in selected_parts if verified_price_info(part))
    plan["verified_part_count"] = verified_count
    plan["part_count"] = len(selected_parts)
    plan["total_is_estimate"] = verified_count < len(selected_parts)
    plan["price_status"] = "verified" if not plan["total_is_estimate"] else "estimated"
    for part_type in ("cpu", "gpu"):
        if isinstance(parts.get(part_type), dict) and part_type in plan.get("predictions", {}):
            plan["predictions"][part_type]["pred_price"] = safe_int(parts[part_type].get("price"), 0)
    fps = plan.setdefault("fps", {})
    high = safe_float(fps.get("fps_by_option", {}).get("high"), 0.0)
    high_low1 = safe_float(fps.get("low1_by_option", {}).get("high"), 0.0)
    plan["cost_per_frame"] = round(total / high) if total > 0 and high > 0 else None
    fps["cost_per_frame"] = plan["cost_per_frame"]
    fps["price_per_frame_krw"] = None
    fps["price_per_frame_by_option"] = {
        option: value_metrics(value, total)["price_per_frame_krw"]
        for option, value in fps.get("fps_by_option", {}).items()
    }
    fps["price_per_frame_basis"] = "total_build_price / average_fps"
    if high > 0:
        metrics = value_metrics(
            high,
            total,
            fps.get("target_fps"),
            high_low1,
            fps.get("target_low1_fps"),
        )
        fps["value_score"] = metrics["score"]
        fps["price_per_frame_krw"] = metrics["price_per_frame_krw"]
        fps["value_fps_per_1000krw"] = metrics["fps_per_1000krw"]
        fps["value_label"] = value_label(metrics["score"])
        fps["target_fps"] = metrics["target_fps"]
        fps["target_low1_fps"] = metrics["target_low1_fps"]
        fps["target_coverage"] = metrics["target_coverage"]
        fps["low1_target_coverage"] = metrics["low1_target_coverage"]
        fps["capacity_label"] = metrics["capacity_label"]

def refresh_plan_prices(
    plan: Dict[str, Any],
    price_cache: Optional[Dict[Tuple[str, str], Optional[Dict[str, Any]]]] = None,
    gpu_maker_prefs: Optional[List[str]] = None,
) -> None:
    parts = plan.get("parts") or {}
    for part_type, part in list(parts.items()):
        if not isinstance(part, dict) or not part.get("name"):
            continue
        normalized_type = normalize_text(part_type)
        if normalized_type not in DISPLAY_PRICE_TYPES:
            continue
        key = (normalized_type, canonical_name(part.get("name")))
        if price_cache is not None and key in price_cache:
            info = price_cache[key]
        else:
            info = get_or_fetch_danawa_price(part, part_type, gpu_maker_prefs=gpu_maker_prefs if normalized_type == "gpu" else None)
            if price_cache is not None:
                price_cache[key] = info
        apply_price_info_to_part(part, info)

    recompute_plan_total(plan)

def collect_display_parts(payload: Dict[str, Any]) -> Dict[Tuple[str, str], Tuple[Dict[str, Any], str]]:
    out: Dict[Tuple[str, str], Tuple[Dict[str, Any], str]] = {}
    for plan in (payload.get("results") or {}).values():
        for part_type, part in (plan.get("parts") or {}).items():
            normalized_type = normalize_text(part_type)
            if normalized_type not in DISPLAY_PRICE_TYPES:
                continue
            if not isinstance(part, dict) or not part.get("name"):
                continue
            key = (normalized_type, canonical_name(part.get("name")))
            out.setdefault(key, (part, part_type))
    return out

def resolve_recommendation_price_cache(
    wanted: Dict[Tuple[str, str], Tuple[Dict[str, Any], str]],
    gpu_maker_prefs: Optional[List[str]] = None,
) -> Dict[Tuple[str, str], Optional[Dict[str, Any]]]:
    resolved: Dict[Tuple[str, str], Optional[Dict[str, Any]]] = {}
    pending: Dict[Any, Tuple[Tuple[str, str], Dict[str, Any], str, Optional[Dict[str, Any]]]] = {}
    maker_prefs = normalize_gpu_maker_prefs(gpu_maker_prefs)

    executor = ThreadPoolExecutor(max_workers=6)
    try:
        for key, (part, part_type) in wanted.items():
            normalized_type = normalize_text(part_type)
            raw_source = normalize_text(part.get("price_source"))
            raw_url = part.get("url") or part.get("shop_url") or part.get("product_url")
            if verified_price_info(part):
                resolved[key] = {
                    "price": safe_int(part.get("price"), 0),
                    "url": raw_url,
                    "image_url": part.get("image_url"),
                    "shop": part.get("shop") or "Danawa",
                    "currency": part.get("currency") or "KRW",
                    "price_source": part.get("price_source") or "danawa_top_live",
                    "matched_by": part.get("price_source_label") or "danawa_top",
                    "product_name": part.get("product_name") or part.get("name"),
                    "scraped_at": part.get("scraped_at"),
                    "verified": True,
                    "price_status": "verified",
                }
                continue
            cached = None if normalized_type == "gpu" and maker_prefs else db_lookup_price_info(part, part_type)
            if cached and not cached.get("stale"):
                resolved[key] = cached
                continue
            future = executor.submit(
                fetch_market_top_product,
                market_lookup_name(part, part_type),
                part_type,
                2.5,
                safe_int(part.get("base_price"), 0) or safe_int(part.get("price"), 0),
                maker_prefs if normalized_type == "gpu" else None,
                False,
            )
            pending[future] = (key, part, part_type, cached)

        try:
            iterator = as_completed(pending, timeout=3.0)
            for future in iterator:
                key, part, part_type, cached = pending.pop(future)
                try:
                    live = future.result()
                    if live and safe_int(live.get("price"), 0) > 0:
                        resolved[key] = store_danawa_price(part, part_type, live)
                    else:
                        resolved[key] = cached if cached and not cached.get("stale") else None
                except Exception:
                    resolved[key] = cached if cached and not cached.get("stale") else None
        except TimeoutError:
            pass

        for future, (key, _part, _part_type, cached) in pending.items():
            future.cancel()
            resolved.setdefault(key, cached if cached and not cached.get("stale") else None)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    return resolved

def refresh_recommendation_prices(payload: Dict[str, Any]) -> None:
    maker_prefs = normalize_gpu_maker_prefs((payload.get("input") or {}).get("gpu_brands"))
    price_cache = resolve_recommendation_price_cache(collect_display_parts(payload), maker_prefs)
    for plan in (payload.get("results") or {}).values():
        for part_type, part in (plan.get("parts") or {}).items():
            normalized_type = normalize_text(part_type)
            key = (normalized_type, canonical_name(part.get("name") if isinstance(part, dict) else ""))
            if normalized_type in DISPLAY_PRICE_TYPES:
                apply_price_info_to_part(part, price_cache.get(key))
        recompute_plan_total(plan)

def game_genre_for_id(game: Any) -> str:
    key = normalized_game_key(game)
    item = next((row for row in GAME_OPTIONS if row.get("id") == key), None)
    return normalize_text((item or {}).get("genre") or game_profile(key)[0]) or "default"

def resolve_fps_part(part_type: str, raw: Any) -> Tuple[Optional[Dict[str, Any]], str]:
    """Resolve a direct-spec SKU to its benchmark profile.

    Live Danawa products carry ``performance_ref_id``.  The retail SKU keeps
    its own price/name in the UI, while FPS must use the chip-level profile to
    avoid treating different cooler/board-partner variants as different GPUs.
    """
    requested_id = raw.get("id") if isinstance(raw, dict) else raw
    requested_id = clean_visible_text(requested_id)
    reference_id = raw.get("performance_ref_id") if isinstance(raw, dict) else ""
    part = find_catalog_part(part_type, reference_id or requested_id)
    if part:
        resolved = dict(part)
        if isinstance(raw, dict) and part_type == "ram":
            # RAM capacity, generation, and speed materially affect the
            # estimate and can be read safely from the live product response.
            gb = safe_int(raw.get("gb"), 0)
            speed = safe_int(raw.get("speed"), 0)
            ram_type = clean_visible_text(raw.get("type"))
            if 4 <= gb <= 512:
                resolved["gb"] = gb
            if 1600 <= speed <= 10000:
                resolved["speed"] = speed
            if normalize_text(ram_type) in {"ddr4", "ddr5"}:
                resolved["type"] = ram_type.upper()
        return resolved, requested_id or clean_visible_text(part.get("id"))

    # A new RAM SKU may not resemble an embedded retail profile closely enough
    # to map by name.  Its three relevant specs are sufficient for this engine.
    if part_type == "ram" and isinstance(raw, dict):
        gb = safe_int(raw.get("gb"), 0)
        speed = safe_int(raw.get("speed"), 0)
        ram_type = normalize_text(raw.get("type"))
        if 4 <= gb <= 512 and 1600 <= speed <= 10000 and ram_type in {"ddr4", "ddr5"}:
            return {
                "id": requested_id or "live_ram",
                "name": clean_visible_text(raw.get("name")) or "Live RAM",
                "gb": gb,
                "speed": speed,
                "type": ram_type.upper(),
                "tier": "mid",
            }, requested_id or "live_ram"
    return None, requested_id

def fps_estimate_response(body: Dict[str, Any]) -> Dict[str, Any]:
    """Use the recommendation FPS engine for the direct-spec screen too."""
    if not isinstance(body, dict):
        raise ValueError("invalid fps request")

    parts: Dict[str, Dict[str, Any]] = {}
    input_ids: Dict[str, str] = {}
    for part_type in ("gpu", "cpu", "ram"):
        raw = body.get(part_type)
        part, selected_id = resolve_fps_part(part_type, raw)
        if not part:
            raise ValueError(f"unknown {part_type}")
        parts[part_type] = dict(part)
        input_ids[part_type] = selected_id or clean_visible_text(part.get("id"))

    game = normalized_game_key(body.get("game") or "cyberpunk2077")
    resolution = resolution_key(body.get("resolution") or "1080")
    refresh = refresh_value(body.get("refresh") or 60)
    tier = normalize_text(body.get("tier") or "mid")
    if tier not in TIER_RANK:
        tier = "mid"
    fps = estimate_fps_bundle(
        parts["gpu"],
        parts["cpu"],
        parts["ram"],
        game,
        resolution,
        refresh,
        tier,
        [game_genre_for_id(game)],
    )
    attach_graphics_modes(fps, parts["gpu"], parts["cpu"], game, resolution)
    return {
        "fps": fps,
        "input": {
            "gpu": input_ids["gpu"],
            "cpu": input_ids["cpu"],
            "ram": input_ids["ram"],
            "game": game,
            "resolution": resolution,
            "refresh": refresh,
            "tier": tier,
        },
    }

def price_lookup_response(body: Dict[str, Any]) -> Dict[str, Any]:
    items = body.get("items") if isinstance(body, dict) else []
    if not isinstance(items, list):
        items = []

    maker_prefs = normalize_gpu_maker_prefs(
        body.get("gpu_brands") or body.get("gpu_makers") or body.get("gpu_brand_prefs")
    ) if isinstance(body, dict) else []
    results: List[Dict[str, Any]] = []
    wanted = {}
    for item in items[:20]:
        if isinstance(item, dict) and item.get("name"):
            part_type = normalize_text(item.get("part_type") or item.get("type") or "part")
            # Request metadata is not evidence that the supplied price is current.
            wanted[(part_type, canonical_name(item["name"]))] = ({**item, "price_source": ""}, part_type)
    prices = resolve_recommendation_price_cache(wanted, maker_prefs)
    for item in items[:20]:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        part_type = normalize_text(item.get("part_type") or item.get("type") or "part")
        info = prices.get((part_type, canonical_name(item["name"])))
        if not info:
            results.append({
                "id": item.get("id"), "type": part_type, "name": item.get("name"),
                "price": None, "price_source": "unavailable", "price_status": "unavailable",
                "verified": False, "shop": None, "currency": "KRW",
                "url": item.get("url") or danawa_search_url(item.get("name")),
                "image_url": item.get("image_url") or part_image_endpoint(item, part_type),
                "scraped_at": None,
            })
            continue
        results.append({
            "id": item.get("id"),
            "type": part_type,
            "name": item.get("name"),
            "product_name": info.get("product_name") or info.get("name"),
            "price": safe_int(info.get("price"), 0),
            "shop": info.get("shop") or "Danawa",
            "currency": info.get("currency") or "KRW",
            "url": info.get("url") or danawa_search_url(item.get("name")),
            "image_url": info.get("image_url") or item.get("image_url") or part_image_endpoint(item, part_type),
            "scraped_at": info.get("scraped_at"),
            "price_source": info.get("price_source") or "danawa_top",
            "price_status": "verified" if verified_price_info(info) else "stale",
            "verified": verified_price_info(info),
        })

    return {
        "results": results,
        "db_loaded": DB_CACHE.get("loaded", False),
        "db_summary": DB_CACHE.get("summary", {}),
    }

def product_search_response(body: Dict[str, Any]) -> Dict[str, Any]:
    payload = price_lookup_response(body)
    payload["results"] = [row for row in payload.get("results", []) if safe_int(row.get("price"), 0) > 0]
    seen_ids = {row.get("id") for row in payload.get("results", []) if isinstance(row, dict)}
    items = body.get("items") if isinstance(body, dict) else []
    if isinstance(items, list):
        for item in items[:20]:
            if not isinstance(item, dict) or not item.get("name") or item.get("id") in seen_ids:
                continue
            fallback_price = safe_int(item.get("base_price"), 0) or safe_int(item.get("price"), 0)
            if fallback_price <= 0:
                continue
            part_type = normalize_text(item.get("type") or item.get("part_type") or "part")
            payload.setdefault("results", []).append({
                "id": item.get("id"),
                "type": part_type,
                "name": item.get("name"),
                "product_name": item.get("product_name") or item.get("name"),
                "price": fallback_price,
                "shop": item.get("shop") or "Catalog",
                "currency": item.get("currency") or "KRW",
                "url": item.get("url") or danawa_search_url(item.get("name")),
                "image_url": item.get("image_url") or part_image_endpoint(item, part_type),
                "scraped_at": item.get("scraped_at"),
                "price_source": "catalog_fallback",
                "price_status": "estimated",
                "verified": False,
            })
    payload["source"] = "danawa_compuzone_lookup"
    return payload

def game_key_variants(game: str) -> set:
    g = normalize_text(game).replace(" ", "_")
    variants = {g, g.replace("_", "")}
    aliases = {
        "csgo2": {"cs2", "counter_strike_2", "counterstrike2"},
        "cs2": {"csgo2", "counter_strike_2", "counterstrike2"},
        "cyberpunk2077": {"cyberpunk_2077", "cyberpunk_2077_phantom_liberty"},
        "baldurs_gate3": {"baldur's_gate_3", "baldurs_gate_3", "baldur_gate_3"},
        "cities_skylines2": {"cities_skylines_2"},
        "msfs2024": {"microsoft_flight_simulator_2024", "flight_simulator_2024"},
        "ffxiv": {"final_fantasy_xiv"},
        "pubg": {"playerunknowns_battlegrounds", "pubg_battlegrounds", "battlegrounds"},
        "genshin_impact": {"genshin", "원신"},
        "wuthering_waves": {"wutheringwaves", "명조", "명조워더링웨이브"},
        "ghost_of_tsushima": {"ghost_of_tsushima_directors_cut", "ghost_of_tsushima_director_s_cut"},
        "red_dead_redemption2": {"red_dead_redemption_2", "rdr2"},
        "horizon_forbidden_west": {"horizon_forbidden_west_complete_edition"},
        "god_of_war_ragnarok": {"god_of_war_ragnarok", "god_of_war_ragnarok_pc"},
        "black_myth_wukong": {"black_myth_wu_kong"},
        "hogwarts_legacy": {"hogwarts"},
        "zenless_zone_zero": {"zzz", "zenlesszonezero"},
    }
    variants.update(aliases.get(g, set()))
    return variants

def db_lookup_benchmarks(part: Dict[str, Any], game: str, fallback_all: bool = True) -> List[Dict[str, Any]]:
    ensure_db_cache_loaded()
    part_key = canonical_name(part.get("name"))
    game_key = normalize_text(game).replace(" ", "_")
    cache_key = (part_key, game_key, bool(fallback_all))
    cached = BENCHMARK_LOOKUP_CACHE.get(cache_key)
    if cached is not None:
        return list(cached)

    match = _best_match_key(part_key, DB_CACHE.get("benchmarks_by_name", {}).keys())
    if not match:
        BENCHMARK_LOOKUP_CACHE[cache_key] = ()
        return []
    by_game = DB_CACHE["benchmarks_by_name"].get(match, {})
    for variant in sorted(game_key_variants(game)):
        samples = by_game.get(variant, [])
        if samples:
            BENCHMARK_LOOKUP_CACHE[cache_key] = tuple(samples)
            return samples
    if not fallback_all:
        BENCHMARK_LOOKUP_CACHE[cache_key] = ()
        return []
    all_samples: List[Dict[str, Any]] = []
    for rows in by_game.values():
        all_samples.extend(rows)
    BENCHMARK_LOOKUP_CACHE[cache_key] = tuple(all_samples)
    return all_samples

def has_average_hierarchy_benchmark(part: Dict[str, Any]) -> bool:
    return bool(db_lookup_benchmarks(part, "average_games", fallback_all=False))

# ─────────────────────────────────────────────────────────────
# FPS estimation
# ─────────────────────────────────────────────────────────────


# Only workload priors, not FPS observations. Actual measured rows are loaded
# from game_benchmarks.json; uncertainty is reported when interpolation is needed.
for _game, _weight, _low1 in [
    ("fortnite", .48, .76), ("marvel_rivals", .40, .74),
    ("cod_black_ops6", .32, .76), ("dragons_dogma2", .55, .68),
    ("dying_light2", .22, .76), ("resident_evil4", .20, .78), ("alan_wake2", .16, .72),
]:
    GAME_FPS_PROFILES[_game] = {**GAME_FPS_PROFILES["default"], "cpu_weight": _weight, "low1": _low1, "ram_hungry": True}

# Game measurements with verified settings live in data/game_benchmarks.json.

# Game-engine caps should be respected before comparing a build with a monitor
# refresh target.  Benchmarks with an external unlocker are not representative
# of the default in-game experience.
GAME_FRAME_CAPS = {"elden_ring": 60.0, "genshin_impact": 60.0}

def normalized_game_key(game: Any) -> str:
    key = normalize_text(game).replace(" ", "_")
    aliases = {"cs2": "csgo2", "cyberpunk_2077": "cyberpunk2077", "apex_legends": "apex", "final_fantasy_xiv": "ffxiv"}
    for item in GAME_OPTIONS:
        if key == normalize_text(item["label"]).replace(" ", "_"):
            return item["id"]
    return aliases.get(key, key)

def game_frame_cap(game: Any) -> Optional[float]:
    return GAME_FRAME_CAPS.get(normalized_game_key(game))

def find_catalog_part(part_type: str, part_id: Any) -> Optional[Dict[str, Any]]:
    key = normalize_text(part_id)
    if not key:
        return None
    return next((part for part in CATALOGS.get(part_type, []) if normalize_text(part.get("id")) == key), None)

def target_fps_for_game(tier: str, refresh: int, game: str) -> float:
    game_class, _ = game_profile(game)
    target = tier_fps_target(tier, refresh, game_class)
    cap = game_frame_cap(game)
    return min(target, cap) if cap else target

def gpu_base_perf(gpu: Dict[str, Any], resolution: str) -> float:
    if resolution == "2160":
        return safe_float(gpu.get("perf_2160"), safe_float(gpu.get("perf_1440")) * 0.62)
    if resolution == "1440":
        return safe_float(gpu.get("perf_1440"), safe_float(gpu.get("perf_1080")) * 0.72)
    return safe_float(gpu.get("perf_1080"), 0.0)

def benchmark_row_for_gpu(gpu: Dict[str, Any]) -> Optional[Dict[str, float]]:
    gid = normalize_text(gpu.get("id"))
    if gid in BENCHMARK_FPS_BY_GPU:
        return BENCHMARK_FPS_BY_GPU[gid]
    name_key = canonical_name(gpu.get("name"))
    return BENCHMARK_FPS_BY_GPU.get(name_key)

def hierarchy_fps(gpu: Dict[str, Any], resolution: str, setting: str) -> Optional[float]:
    db_setting = "medium" if resolution == "1080" and setting in {"low", "medium"} else "high"
    db_hit = estimate_fps_from_db(gpu, "average_games", resolution, db_setting)
    if db_hit:
        base = db_hit[0]
        if setting == "ultra":
            return base * 0.83
        if setting == "high" or (resolution == "1080" and setting == "medium"):
            return base
        if setting == "medium":
            return base * 1.24
        return base * (1.14 if resolution == "1080" else 1.46)

    row = benchmark_row_for_gpu(gpu)
    if not row:
        return None
    high = row["h1080"] if resolution == "1080" else row["h1440"] if resolution == "1440" else row["h2160"]
    if setting == "ultra":
        return high * 0.83
    if setting == "high":
        return high
    if setting == "medium":
        return row["m1080"] if resolution == "1080" else high * 1.24
    return row["m1080"] * 1.14 if resolution == "1080" else high * 1.46

def cpu_fps_factor(cpu: Dict[str, Any], game: str, resolution: str, setting: str, raw_fps: float) -> float:
    g = normalize_text(game).replace(" ", "_")
    profile = GAME_FPS_PROFILES.get(g, GAME_FPS_PROFILES["default"])
    cpu_norm = clamp(safe_float(cpu.get("perf"), 0.0) / 100.0, 0.16, 1.08)
    quality_boost = {"low": 1.18, "medium": 1.08, "high": 1.0, "ultra": 0.94}.get(setting, 1.0)
    base_cap = profile["cpu_cap"].get(resolution, GAME_FPS_PROFILES["default"]["cpu_cap"][resolution])
    cpu_cap = base_cap * (0.48 + cpu_norm * 0.64) * quality_boost
    if raw_fps <= cpu_cap:
        return 1.0
    bottleneck = max(0.38, cpu_cap / max(1.0, raw_fps))
    return 1.0 - profile["cpu_weight"] * (1.0 - bottleneck)

def ram_fps_factor(ram: Dict[str, Any], game: str) -> float:
    g = normalize_text(game).replace(" ", "_")
    profile = GAME_FPS_PROFILES.get(g, GAME_FPS_PROFILES["default"])
    gb = safe_float(ram.get("gb"), 16.0)
    ram_type = normalize_text(ram.get("type"))
    speed = safe_float(ram.get("speed"), 0.0)
    if gb <= 8:
        return 0.88 if profile.get("ram_hungry") else 0.94
    if profile.get("ram_hungry") and gb < 32:
        return 0.96
    factor = 1.0
    if gb >= 32:
        factor += 0.015 if profile.get("ram_hungry") else 0.006
    if ram_type == "ddr5":
        factor += 0.012 if speed >= 5600 else 0.006
    elif ram_type == "ddr4" and speed >= 3200:
        factor += 0.004
    return round(min(1.035, factor), 4)

def quality_scale(resolution: str, setting: str) -> float:
    if setting == "ultra":
        return 0.83
    if setting == "high":
        return 1.0
    if setting == "medium":
        return 1.24
    return 1.14 * 1.24 if resolution == "1080" else 1.46

def average_benchmark_rows(rows: List[Dict[str, Any]]) -> Optional[Tuple[float, float]]:
    avg_values = [safe_float(x.get("avg_fps")) for x in rows if safe_float(x.get("avg_fps")) > 0]
    if not avg_values:
        return None
    low_values = [safe_float(x.get("low1_fps")) for x in rows if safe_float(x.get("low1_fps")) > 0]
    avg = sum(avg_values) / len(avg_values)
    low = sum(low_values) / len(low_values) if low_values else avg * 0.8
    return avg, low

def adjust_benchmark_quality(avg: float, low: float, source_setting: str, target_setting: str, resolution: str) -> Tuple[float, float]:
    ratio = quality_scale(resolution, target_setting) / max(0.01, quality_scale(resolution, source_setting))
    return avg * ratio, low * ratio

def estimate_fps_from_catalog(gpu: Dict[str, Any], cpu: Dict[str, Any], ram: Dict[str, Any],
                              game: str, resolution: str, setting: str) -> Tuple[float, float]:
    g = normalize_text(game).replace(" ", "_")
    profile = GAME_FPS_PROFILES.get(g, GAME_FPS_PROFILES["default"])
    base = hierarchy_fps(gpu, resolution, setting)
    if base is None:
        genre_class, game_factor = game_profile(game)
        opt_factor = {"low": 1.45, "medium": 1.12, "high": 1.00, "ultra": 0.83}.get(setting, 1.0)
        res_scale = {"1080": 4.30, "1440": 2.95, "2160": 1.72}.get(resolution, 2.6)
        perf = max(1.0, gpu_base_perf(gpu, resolution))
        raw = perf * res_scale * game_factor * opt_factor
        raw *= {"fps": 1.18, "rpg": 0.92, "mmo": 1.05, "sim": 0.86, "default": 1.0}.get(genre_class, 1.0)
    else:
        raw = base * profile["scale"].get(resolution, 1.0)
    avg = max(5.0, raw * cpu_fps_factor(cpu, game, resolution, setting, raw) * ram_fps_factor(ram, game))
    low1 = avg * safe_float(profile.get("low1"), 0.78)
    return round(avg, 1), round(low1, 1)

def estimate_fps_from_db(gpu: Dict[str, Any], game: str, resolution: str, setting: str) -> Optional[Tuple[float, float]]:
    samples = db_lookup_benchmarks(gpu, game, fallback_all=False)
    if not samples:
        return None

    exact = [s for s in samples if s.get("resolution") == resolution and normalize_text(s.get("setting")) == setting]
    exact_avg = average_benchmark_rows(exact)
    if exact_avg:
        avg, low = exact_avg
        return round(avg, 1), round(low, 1)

    same_res = [s for s in samples if s.get("resolution") == resolution]
    if same_res:
        by_setting = {
            key: [s for s in same_res if normalize_text(s.get("setting")) == key]
            for key in ["low", "medium", "high", "ultra"]
        }
        if setting == "low":
            source_setting = "medium" if by_setting["medium"] else "high"
        elif setting == "medium":
            source_setting = "high"
        elif setting == "ultra":
            source_setting = "high"
        else:
            source_setting = "medium" if by_setting["medium"] else "ultra"

        source_avg = average_benchmark_rows(by_setting.get(source_setting, []))
        if source_avg:
            avg, low = adjust_benchmark_quality(source_avg[0], source_avg[1], source_setting, setting, resolution)
            return round(avg, 1), round(low, 1)

        same_res_avg = average_benchmark_rows(same_res)
        if same_res_avg:
            return round(same_res_avg[0], 1), round(same_res_avg[1], 1)

    # Different resolutions cannot be averaged into the requested resolution.
    return None

def enforce_fps_order(fps_by_option: Dict[str, float], low1_by_option: Dict[str, float]) -> None:
    if "high" in fps_by_option and "medium" in fps_by_option and fps_by_option["medium"] <= fps_by_option["high"]:
        fps_by_option["medium"] = round(fps_by_option["high"] + max(1.0, fps_by_option["high"] * 0.05), 1)
        low1_by_option["medium"] = min(fps_by_option["medium"], round(low1_by_option.get("medium", fps_by_option["medium"] * 0.8), 1))
    if "medium" in fps_by_option and "low" in fps_by_option and fps_by_option["low"] <= fps_by_option["medium"]:
        fps_by_option["low"] = round(fps_by_option["medium"] + max(1.0, fps_by_option["medium"] * 0.05), 1)
        low1_by_option["low"] = min(fps_by_option["low"], round(low1_by_option.get("low", fps_by_option["low"] * 0.8), 1))
    if "high" in fps_by_option and "ultra" in fps_by_option and fps_by_option["ultra"] >= fps_by_option["high"]:
        fps_by_option["ultra"] = round(max(2.0, fps_by_option["high"] * 0.88), 1)
        low1_by_option["ultra"] = min(fps_by_option["ultra"], round(low1_by_option.get("ultra", fps_by_option["ultra"] * 0.8), 1))

def estimate_fps_bundle(gpu: Dict[str, Any], cpu: Dict[str, Any], ram: Dict[str, Any],
                        game: str, resolution: str, refresh: int, tier: str, genres: List[str]) -> Dict[str, Any]:
    fps_by_option: Dict[str, float] = {}
    low1_by_option: Dict[str, float] = {}
    option_evidence: Dict[str, Dict[str, Any]] = {}
    game = normalized_game_key(game)
    genre_class, _ = game_profile(game)
    low1_ratio = low1_ratio_for_genres(genres or [genre_class])
    profile = GAME_FPS_PROFILES.get(game, GAME_FPS_PROFILES["default"])
    cap = game_frame_cap(game)

    for opt in ["low", "medium", "high", "ultra"]:
        measured = estimate_from_measurements(gpu, cpu, ram, game, resolution, opt, profile, CATALOGS)
        if measured:
            avg, low, evidence = measured
        else:
            avg, low = estimate_fps_from_catalog(gpu, cpu, ram, game, resolution, opt)
            cpu_norm = clamp(safe_float(cpu.get("perf"), 0.0) / 100.0, .16, 1.08)
            cpu_ceiling = profile["cpu_cap"][resolution] * (.48 + cpu_norm * .64) * {"low":1.18,"medium":1.08,"high":1.,"ultra":.94}[opt]
            gpu_ceiling = max(avg, hierarchy_fps(gpu, resolution, opt) or avg) * profile["scale"][resolution]
            cpu_penalty = max(0, 1 - avg / max(avg, gpu_ceiling)) * 100
            gpu_penalty = max(0, 1 - avg / max(avg, cpu_ceiling)) * 100
            evidence = {
                "method": "model_estimate", "confidence": "low", "low1_estimated": True,
                "source_url": "", "source_title": "", "reference_gpu": "", "reference_cpu": "",
                "conditions": "게임별 실측 자료 없음 · Native · RT/프레임 생성 OFF",
                "range": {"min": round(avg * .60, 1), "max": round(avg * 1.40, 1)},
                "range_method": "heuristic_allowance_not_statistical_interval",
                "notes": ["해당 게임의 검증된 실측 데이터가 없어 GPU 지수와 게임 부하 모델로 추정했습니다", "1% Low는 추정치"],
                "bottleneck": {"estimated": True, "cpu_penalty_pct": cpu_penalty,
                               "gpu_penalty_pct": gpu_penalty, "limiting_component": "cpu" if cpu_penalty > gpu_penalty else "gpu",
                               "method": "workload_model", "note": "게임 부하 모델 추정 · 실측 병목률 아님"},
            }
        bottleneck = evidence.get("bottleneck") or {}
        if "gpu_penalty_pct" not in bottleneck:
            bottleneck["gpu_penalty_pct"] = max(0, 1 - avg / max(avg, safe_float(bottleneck.get("cpu_fps_ceiling"), avg))) * 100
        cpu_percent = round(clamp(safe_float(bottleneck.get("cpu_penalty_pct"), 0), 0, 100), 1)
        gpu_percent = round(clamp(safe_float(bottleneck.get("gpu_penalty_pct"), 0), 0, 100), 1)
        bottleneck.update({"cpu_percent": cpu_percent, "gpu_percent": gpu_percent,
                           "percent": max(cpu_percent, gpu_percent),
                           "limiting_component": "balanced" if max(cpu_percent, gpu_percent) < 10 else "cpu" if cpu_percent >= gpu_percent else "gpu",
                           "comparison_source_url": "https://pc-builds.com/ko/bottleneck-calculator/",
                           "note": "선택 게임·해상도·옵션의 성능 여유 차이를 퍼센트로 보정한 자체 추정 · PC-Builds 수치와는 다를 수 있음"})
        if cap:
            avg, low = min(avg, cap), min(low, cap)
            evidence["range"] = {key: round(min(value, cap), 1) for key, value in evidence["range"].items()}
        fps_by_option[opt] = round(avg, 1)
        low1_by_option[opt] = round(min(avg, max(1.0, low)), 1)
        option_evidence[opt] = evidence

    # Preserve every measured value. Preset interpolation is monotonic by
    # construction; a source measurement must not be rewritten to enforce order.
    high_avg, high_low = fps_by_option["high"], low1_by_option["high"]
    evidence = option_evidence["high"]
    target_fps = target_fps_for_game(tier, refresh, game)
    target_low1 = target_fps * low1_ratio
    metrics = value_metrics(high_avg, safe_float(gpu.get("price"), 0.0), target_fps, high_low, target_low1)
    fps_source = evidence["method"]
    return {
        "game": game, "fps_by_option": fps_by_option, "low1_by_option": low1_by_option,
        "avg_fps": high_avg, "low1_fps": high_low,
        "high_setting_avg_fps": high_avg, "high_setting_low1_fps": high_low,
        "hz_coverage": round(clamp(high_avg / max(1, refresh), 0.0, 1.6), 3),
        "value_label": value_label(metrics["score"]), "value_score": metrics["score"],
        "value_fps_per_1000krw": metrics["fps_per_1000krw"],
        "target_fps": metrics["target_fps"], "target_low1_fps": metrics["target_low1_fps"],
        "target_coverage": metrics["target_coverage"], "low1_target_coverage": metrics["low1_target_coverage"],
        "capacity_label": metrics["capacity_label"], "frame_cap": cap, "fps_source": fps_source,
        "fps_source_label": {"measured_benchmark": "동일 CPU·GPU 실측 참고", "benchmark_calibrated": "실측 기반 보정 추정", "model_estimate": "모델 추정 · 실측 자료 없음"}[fps_source],
        "confidence": evidence["confidence"], "option_evidence": option_evidence,
        "fps_range_by_option": {opt: item["range"] for opt, item in option_evidence.items()},
        "benchmark_source_url": evidence["source_url"], "benchmark_source_title": evidence["source_title"],
        "benchmark_reference_gpu": evidence["reference_gpu"], "benchmark_reference_cpu": evidence["reference_cpu"],
        "benchmark_conditions": evidence["conditions"], "estimation_notes": evidence["notes"],
        "low1_is_estimated": evidence["low1_estimated"],
        "bottleneck": evidence.get("bottleneck", {"estimated": True, "limiting_component": "unknown", "note": "게임별 실측 자료가 없어 병목을 신뢰성 있게 계산할 수 없습니다"}),
        "bottleneck_by_option": {opt: item.get("bottleneck") for opt, item in option_evidence.items()},
    }


def attach_graphics_modes(fps, gpu, cpu, game, resolution):
    def reference_native(row):
        match = next((item for item in load_measurements() if all(item.get(key) == row.get(key)
                     for key in ("game", "gpu_id", "cpu_id", "resolution", "preset", "source_url"))), None)
        if match:
            return match["avg_fps"]
        reference_gpu = next((p for p in GPU_CATALOG if p["id"] == row["gpu_id"]), gpu)
        reference_cpu = next((p for p in CPU_CATALOG if p["id"] == row["cpu_id"]), cpu)
        measured = estimate_from_measurements(reference_gpu, reference_cpu, {"gb":32}, game, row["resolution"], row["preset"], GAME_FPS_PROFILES.get(game, GAME_FPS_PROFILES["default"]), CATALOGS)
        return measured[0] if measured else fps["fps_by_option"][row["preset"]]
    fps["graphics_modes"] = graphics_scenarios(gpu, cpu, game, resolution, fps, reference_native)

# ─────────────────────────────────────────────────────────────
# Recommendation logic
# ─────────────────────────────────────────────────────────────

def part_price(part: Dict[str, Any], part_type: str) -> int:
    raw_price = safe_int(part.get("price"), 0)
    raw_source = normalize_text(part.get("price_source"))
    raw_url = part.get("url") or part.get("shop_url") or part.get("product_url")
    if verified_price_info(part):
        return raw_price
    db_price = db_lookup_price(part, part_type)
    if db_price is not None and db_price > 0:
        return db_price
    return raw_price

def choose_best(parts: List[Dict[str, Any]], scores: List[Tuple[float, Dict[str, Any]]]) -> Tuple[Dict[str, Any], float]:
    if not parts:
        return {}, 0.0
    best_score = -1e9
    best_part: Dict[str, Any] = parts[0]
    for score, part in scores:
        if score > best_score:
            best_score = score
            best_part = part
    return best_part, best_score

def score_gpu(part: Dict[str, Any], budget: int, resolution: str, tier: str, game: str, refresh: int, genres: List[str], rng: random.Random) -> float:
    price = max(1, part_price(part, "gpu"))
    perf = gpu_base_perf(part, resolution)
    genre_class, _ = game_profile(game)
    target_price = budget * (0.34 if resolution == "1080" else 0.43 if resolution == "1440" else 0.54)
    price_fit = 1.0 - min(1.0, abs(price - target_price) / max(1.0, target_price))
    target_perf = {
        "1080": {"low": 46.0, "mid": 62.0, "high": 80.0},
        "1440": {"low": 34.0, "mid": 52.0, "high": 70.0},
        "2160": {"low": 22.0, "mid": 40.0, "high": 56.0},
    }.get(resolution, {"low": 46.0, "mid": 62.0, "high": 80.0})[tier]
    perf_fit = 1.0 - min(1.0, abs(perf - target_perf) / max(12.0, target_perf))
    res_bonus = 0.16 if resolution == "2160" and perf >= 50 else 0.08 if resolution == "1440" else 0.04
    refresh_bonus = 0.08 if refresh >= 144 and resolution == "1080" else 0.03 if refresh >= 120 else 0.0
    tier_match = 0.08 if part.get("tier") == tier else 0.0
    db_bonus = 0.08 if db_lookup_benchmarks(part, game) else 0.0
    value_bonus = clamp((perf / max(1.0, price / 100000.0)) / 4.0, 0.0, 0.18)
    if genre_class == "fps" and resolution == "1080":
        value_bonus += 0.03
    if genre_class == "sim":
        value_bonus -= 0.02
    return (0.43 * price_fit + 0.23 * perf_fit + res_bonus + refresh_bonus + tier_match + db_bonus + value_bonus)

def score_cpu(part: Dict[str, Any], budget: int, resolution: str, refresh: int, tier: str, game: str, rng: random.Random) -> float:
    price = max(1, part_price(part, "cpu"))
    perf = safe_float(part.get("perf"), 0.0)
    target_price = budget * (0.27 if resolution == "1080" else 0.20 if resolution == "1440" else 0.15)
    if refresh >= 144 and resolution == "1080":
        target_price *= 1.10
    price_fit = 1.0 - min(1.0, abs(price - target_price) / max(1.0, target_price))
    perf_score = perf / 100.0
    tier_bonus = 0.08 if part.get("tier") == tier else 0.03 if (tier == "low" and part.get("tier") == "mid") or (tier == "mid" and part.get("tier") == "high") else 0.0
    game_class, _ = game_profile(game)
    genre_bonus = 0.07 if game_class in {"fps", "mmo"} and refresh >= 120 else 0.04 if game_class == "sim" else 0.0
    return (0.48 * price_fit + 0.32 * perf_score + tier_bonus + genre_bonus)

def score_ram(part: Dict[str, Any], budget: int, resolution: str, tier: str, game: str, rng: random.Random) -> float:
    price = max(1, part_price(part, "ram"))
    gb = safe_float(part.get("gb"), 0.0)
    target_price = budget * (0.11 if resolution == "1080" else 0.10 if resolution == "1440" else 0.09)
    price_fit = 1.0 - min(1.0, abs(price - target_price) / max(1.0, target_price))
    size_score = 0.45 if gb >= 64 else 0.32 if gb >= 32 else 0.20
    tier_bonus = 0.06 if part.get("tier") == tier else 0.03
    return (0.58 * price_fit + size_score + tier_bonus)

def score_mb(part: Dict[str, Any], cpu: Dict[str, Any], ram: Dict[str, Any], budget: int, tier: str, rng: random.Random) -> float:
    price = max(1, part_price(part, "mb"))
    target_price = budget * (0.09 if tier == "low" else 0.10 if tier == "mid" else 0.12)
    price_fit = 1.0 - min(1.0, abs(price - target_price) / max(1.0, target_price))
    compat = 0.0
    if cpu and ram:
        if normalize_text(part.get("socket")) == normalize_text(cpu.get("socket")):
            compat += 0.55
        if normalize_text(part.get("ram_type")) == normalize_text(ram.get("type")):
            compat += 0.35
        if compat == 0.0:
            compat = -1.0
    tier_bonus = 0.05 if part.get("tier") == tier else 0.02
    return (0.45 * price_fit + compat + tier_bonus)

def score_psu(part: Dict[str, Any], cpu: Dict[str, Any], gpu: Dict[str, Any], budget: int, tier: str, rng: random.Random) -> float:
    price = max(1, part_price(part, "psu"))
    target_price = budget * (0.08 if tier == "low" else 0.09 if tier == "mid" else 0.10)
    price_fit = 1.0 - min(1.0, abs(price - target_price) / max(1.0, target_price))
    watt = safe_float(part.get("watt"), 0.0)
    need = safe_float(cpu.get("tdp"), 65.0) + safe_float(gpu.get("tdp"), 150.0) + 180.0
    watt_fit = clamp((watt - need) / max(1.0, need * 0.9), -1.0, 1.0)
    watt_score = 0.55 if watt_fit >= 0 else -0.60
    tier_bonus = 0.05 if part.get("tier") == tier else 0.02
    return (0.48 * price_fit + watt_score + tier_bonus)

def score_storage(part: Dict[str, Any], budget: int, resolution: str, tier: str, rng: random.Random) -> float:
    price = max(1, part_price(part, "storage"))
    target_price = budget * (0.12 if tier == "low" else 0.11 if tier == "mid" else 0.10)
    price_fit = 1.0 - min(1.0, abs(price - target_price) / max(1.0, target_price))
    capacity = safe_float(part.get("capacity"), 0.0)
    cap_score = 0.42 if capacity >= 2000 else 0.28 if capacity >= 1000 else 0.16
    tier_bonus = 0.04 if part.get("tier") == tier else 0.01
    return (0.52 * price_fit + cap_score + tier_bonus)

def filter_compatible_mb(cpu_pool: List[Dict[str, Any]], mb_pool: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [board for board in mb_pool if any(platform_compatibility(cpu, board)["compatible"] for cpu in cpu_pool)]

def filter_compatible_ram(mb_pool: List[Dict[str, Any]], ram_pool: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ramtypes = {normalize_text(m.get("ram_type")) for m in mb_pool if m.get("ram_type")}
    out = [r for r in ram_pool if normalize_text(r.get("type")) in ramtypes]
    return out

TIER_RANK = {"low": 0, "mid": 1, "high": 2}

def tier_rank(value: Any) -> int:
    return TIER_RANK.get(normalize_text(value), 1)

def part_tags(part: Dict[str, Any]) -> set:
    return {normalize_text(x) for x in (part.get("tags") or [])}

def is_desktop_cpu(part: Dict[str, Any]) -> bool:
    tags = part_tags(part)
    socket = normalize_text(part.get("socket"))
    return socket not in {"bga1744"} and not ({"mobile", "u_series", "low_power"} & tags)

def is_desktop_mb(part: Dict[str, Any]) -> bool:
    tags = part_tags(part)
    socket = normalize_text(part.get("socket"))
    return socket not in {"bga1744"} and not ({"mobile", "u_series"} & tags)

def cached_part_price(part: Dict[str, Any], part_type: str, cache: Dict[Tuple[str, str], int]) -> int:
    key = (normalize_text(part_type), str(part.get("id") or canonical_name(part.get("name"))))
    if key not in cache:
        cache[key] = part_price(part, part_type)
    return cache[key]

def tier_budget_for_user(budget: int, tier: str, budget_min: int = 0) -> int:
    """Place LOW/MID/HIGH inside the selected budget range, not above it."""
    budget_max = max(300000, safe_int(budget, 1500000))
    lower = max(0, safe_int(budget_min, 0))
    if lower > 0 and lower < budget_max:
        span = budget_max - lower
        return lower + int(span * {"low": 0.30, "mid": 0.65, "high": 1.00}.get(tier, 1.00))
    return max(300000, int(budget_max * {"low": 0.55, "mid": 0.80, "high": 1.00}[tier]))

def recommended_psu_watt(cpu: Dict[str, Any], gpu: Dict[str, Any]) -> int:
    need = safe_float(cpu.get("tdp"), 65.0) + safe_float(gpu.get("tdp"), 150.0) + 180.0
    return int(math.ceil(need / 50.0) * 50)

def build_power_score(parts: Dict[str, Dict[str, Any]], resolution: str) -> float:
    gpu = parts.get("gpu") or {}
    cpu = parts.get("cpu") or {}
    ram = parts.get("ram") or {}
    storage = parts.get("storage") or {}
    gpu_score = clamp(gpu_base_perf(gpu, resolution) / 100.0, 0.0, 1.12) * 100.0
    cpu_score = clamp(safe_float(cpu.get("perf"), 0.0) / 100.0, 0.0, 1.08) * 100.0
    ram_score = clamp(safe_float(ram.get("gb"), 16.0) / 64.0, 0.0, 1.0) * 100.0
    storage_score = clamp(safe_float(storage.get("capacity"), 1000.0) / 2000.0, 0.0, 1.0) * 100.0
    return round(0.58 * gpu_score + 0.26 * cpu_score + 0.10 * ram_score + 0.06 * storage_score, 3)

def target_power_score(tier: str, resolution: str, refresh: int) -> float:
    targets = {
        "1080": {"low": 42.0, "mid": 56.0, "high": 70.0},
        "1440": {"low": 32.0, "mid": 46.0, "high": 60.0},
        "2160": {"low": 22.0, "mid": 34.0, "high": 48.0},
    }
    target = targets.get(resolution, targets["1080"])[tier]
    if refresh >= 144:
        target += 5.0 if resolution == "1080" else 3.0
    elif refresh >= 120:
        target += 2.0
    return target

def tier_fps_target(tier: str, refresh: int, game_class: str) -> float:
    base = max(45.0, float(refresh))
    if game_class in {"rpg", "sim"}:
        base = min(base, 90.0)
    return base * {"low": 0.78, "mid": 1.00, "high": 1.18}[tier]

def price_sum_for_parts(parts: Dict[str, Dict[str, Any]], price_cache: Dict[Tuple[str, str], int]) -> int:
    return sum(
        cached_part_price(part, part_type, price_cache)
        for part_type, part in parts.items()
        if isinstance(part, dict) and part_type in {"cpu", "gpu", "ram", "mb", "psu", "storage"}
    )

def tier_component_pools(
    tier: str,
    resolution: str,
    refresh: int,
    gpu_pref: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    cpu_pool = [p for p in CPU_CATALOG if is_desktop_cpu(p)]
    gpu_pool = [p for p in GPU_CATALOG if is_recommendable_gpu(p)]
    ram_pool = RAM_CATALOG[:]
    mb_pool = [p for p in MB_CATALOG if is_desktop_mb(p)]
    psu_pool = PSU_CATALOG[:]
    storage_pool = STORAGE_CATALOG[:]

    if gpu_pref != "ANY":
        gpu_pool = [g for g in gpu_pool if normalize_text(g.get("vendor")) == normalize_text(gpu_pref)]

    rank = TIER_RANK[tier]
    if tier == "low":
        cpu_pool = [p for p in cpu_pool if tier_rank(p.get("tier")) <= 1] or cpu_pool
        gpu_pool = [p for p in gpu_pool if tier_rank(p.get("tier")) <= 1] or gpu_pool
        ram_pool = [p for p in ram_pool if safe_float(p.get("gb"), 16) <= 32] or ram_pool
        storage_pool = [p for p in storage_pool if safe_float(p.get("capacity"), 1000) <= 2000] or storage_pool
    elif tier == "mid":
        cpu_pool = [p for p in cpu_pool if tier_rank(p.get("tier")) <= 2] or cpu_pool
        gpu_pool = [p for p in gpu_pool if tier_rank(p.get("tier")) <= 1] or gpu_pool
        ram_pool = [p for p in ram_pool if safe_float(p.get("gb"), 16) >= 16] or ram_pool
    else:
        cpu_pool = [p for p in cpu_pool if tier_rank(p.get("tier")) >= 1] or cpu_pool
        gpu_pool = [p for p in gpu_pool if tier_rank(p.get("tier")) >= 1] or gpu_pool
        ram_pool = [p for p in ram_pool if safe_float(p.get("gb"), 16) >= 32] or ram_pool

    if resolution == "2160" or refresh >= 144:
        gpu_pool = [p for p in gpu_pool if gpu_base_perf(p, resolution) >= (20 + rank * 10)] or gpu_pool

    return cpu_pool, gpu_pool, ram_pool, mb_pool, psu_pool, storage_pool

def rank_parts_for_tier(
    parts: List[Dict[str, Any]],
    part_type: str,
    tier_budget: int,
    resolution: str,
    refresh: int,
    tier: str,
    game: str,
    genres: List[str],
    price_cache: Dict[Tuple[str, str], int],
    rng: random.Random,
    limit: int,
) -> List[Dict[str, Any]]:
    if part_type == "gpu":
        scores = [(score_gpu(p, tier_budget, resolution, tier, game, refresh, genres, rng), p) for p in parts]
    elif part_type == "cpu":
        scores = [(score_cpu(p, tier_budget, resolution, refresh, tier, game, rng), p) for p in parts]
    elif part_type == "ram":
        scores = [(score_ram(p, tier_budget, resolution, tier, game, rng), p) for p in parts]
    elif part_type == "storage":
        scores = [(score_storage(p, tier_budget, resolution, tier, rng), p) for p in parts]
    else:
        scores = [(1.0 - cached_part_price(p, part_type, price_cache) / max(1.0, tier_budget), p) for p in parts]
    scores.sort(key=lambda item: (-item[0], cached_part_price(item[1], part_type, price_cache), part_cache_key(item[1])))
    ranked = [p for _score, p in scores[:limit]]
    # Keep affordable and fast endpoints in the search: price-fit ranking alone
    # can discard every CPU/GPU needed to form a monotone three-tier sequence.
    if parts and part_type in {"cpu", "gpu"} and limit >= 3:
        performance = (lambda p: gpu_base_perf(p, resolution)) if part_type == "gpu" else (lambda p: safe_float(p.get("perf"), 0.0))
        anchors = [
            min(parts, key=lambda p: (cached_part_price(p, part_type, price_cache), part_cache_key(p))),
            max(parts, key=lambda p: (performance(p), -cached_part_price(p, part_type, price_cache))),
        ]
        anchor_ids = {part_cache_key(p) for p in anchors}
        ranked = anchors[:1] if len(anchor_ids) == 1 else anchors
        ranked += [p for _score, p in scores if part_cache_key(p) not in anchor_ids][:limit - len(ranked)]
    return ranked or parts[:limit]

def mb_candidates_for(cpu: Dict[str, Any], ram: Dict[str, Any], mb_pool: List[Dict[str, Any]],
                      tier: str, tier_budget: int, price_cache: Dict[Tuple[str, str], int]) -> List[Dict[str, Any]]:
    compatible = [
        mb for mb in mb_pool
        if platform_compatibility(cpu, mb, ram)["compatible"]
    ]
    if not compatible:
        return []
    target_price = tier_budget * (0.08 if tier == "low" else 0.10 if tier == "mid" else 0.12)
    def mb_score(mb: Dict[str, Any]) -> float:
        price = cached_part_price(mb, "mb", price_cache)
        price_fit = 1.0 - min(1.0, abs(price - target_price) / max(1.0, target_price))
        tier_fit = 1.0 - min(1.0, abs(tier_rank(mb.get("tier")) - TIER_RANK[tier]) / 2.0)
        return 0.72 * price_fit + 0.28 * tier_fit
    return sorted(compatible, key=mb_score, reverse=True)[:2]

def psu_candidates_for(cpu: Dict[str, Any], gpu: Dict[str, Any], psu_pool: List[Dict[str, Any]],
                       tier: str, tier_budget: int, price_cache: Dict[Tuple[str, str], int]) -> List[Dict[str, Any]]:
    need = recommended_psu_watt(cpu, gpu)
    compatible = [psu for psu in psu_pool if safe_int(psu.get("watt"), 0) >= need]
    if not compatible:
        return []
    target_price = tier_budget * (0.07 if tier == "low" else 0.085 if tier == "mid" else 0.095)
    def psu_score(psu: Dict[str, Any]) -> float:
        price = cached_part_price(psu, "psu", price_cache)
        watt = safe_float(psu.get("watt"), 0.0)
        headroom = max(0.0, watt - need)
        price_fit = 1.0 - min(1.0, abs(price - target_price) / max(1.0, target_price))
        headroom_fit = 1.0 - min(1.0, abs(headroom - 120.0) / 420.0)
        tier_fit = 1.0 - min(1.0, abs(tier_rank(psu.get("tier")) - TIER_RANK[tier]) / 2.0)
        return 0.48 * price_fit + 0.34 * headroom_fit + 0.18 * tier_fit
    return sorted(compatible, key=psu_score, reverse=True)[:2]

def storage_candidates_for(storage_pool: List[Dict[str, Any]], tier: str, tier_budget: int,
                           price_cache: Dict[Tuple[str, str], int]) -> List[Dict[str, Any]]:
    target_capacity = 1000 if tier == "low" else 2000 if tier == "high" else 1400
    target_price = tier_budget * (0.11 if tier == "low" else 0.10 if tier == "mid" else 0.085)
    def storage_score(storage: Dict[str, Any]) -> float:
        price = cached_part_price(storage, "storage", price_cache)
        capacity = safe_float(storage.get("capacity"), 1000.0)
        cap_fit = 1.0 - min(1.0, abs(capacity - target_capacity) / max(1000.0, target_capacity))
        if tier == "high" and capacity >= 2000:
            cap_fit = 1.0
        price_fit = 1.0 - min(1.0, abs(price - target_price) / max(1.0, target_price))
        tier_fit = 1.0 - min(1.0, abs(tier_rank(storage.get("tier")) - TIER_RANK[tier]) / 2.0)
        return 0.45 * price_fit + 0.40 * cap_fit + 0.15 * tier_fit
    return sorted(storage_pool, key=storage_score, reverse=True)[:3]


def normalize_work_profile(value: Any) -> str:
    key = normalize_text(value).replace(" ", "_")
    key = WORK_ALIASES.get(key, key)
    return key if key in WORK_PROFILES else "video_4k"

@dataclass(frozen=True)
class RecommendationRequest:
    """Normalized recommendation input shared by ranking, plans, and API output."""

    budget: int
    budget_min: int
    budget_max: int
    resolution: str
    refresh: int
    genres: Tuple[str, ...]
    gpu_pref: str
    gpu_brands: Tuple[str, ...]
    game: str
    mode: str
    work_profile: str
    gpu_market_prices: Optional[Dict[str, Dict[str, Any]]] = None

    @classmethod
    def from_payload(cls, payload: Any) -> "RecommendationRequest":
        if isinstance(payload, cls):
            return payload
        data = payload if isinstance(payload, dict) else {}
        requested_budget = max(300000, safe_int(data.get("budget"), 1500000))
        budget_min = max(0, safe_int(data.get("budget_min"), 0))
        budget_max = max(requested_budget, safe_int(data.get("budget_max"), requested_budget))
        if budget_min > budget_max:
            budget_min = 0
        mode = normalize_text(data.get("mode", "game"))
        return cls(
            budget=budget_max,
            budget_min=budget_min,
            budget_max=budget_max,
            resolution=resolution_key(data.get("resolution", "1080")),
            refresh=refresh_value(data.get("refresh", 60)),
            genres=tuple(genres_normalize(data.get("genres") or data.get("genre"))),
            gpu_pref=vendor_normalize(data.get("gpu_pref", "ANY")),
            gpu_brands=tuple(normalize_gpu_maker_prefs(data.get("gpu_brands") or data.get("gpu_makers") or data.get("gpu_brand_prefs"))),
            game=normalized_game_key(data.get("game") or "cyberpunk2077"),
            mode="work" if mode == "work" else "game",
            work_profile=normalize_work_profile(data.get("work_profile") or data.get("work") or data.get("work_type")),
            gpu_market_prices=data.get("gpu_market_prices") if isinstance(data.get("gpu_market_prices"), dict) else None,
        )

    def as_payload(self, include_market_prices: bool = True) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "budget": self.budget,
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "resolution": self.resolution,
            "refresh": self.refresh,
            "genres": list(self.genres),
            "gpu_pref": self.gpu_pref,
            "gpu_brands": list(self.gpu_brands),
            "game": self.game,
            "mode": self.mode,
            "work_profile": self.work_profile,
        }
        if include_market_prices and self.gpu_market_prices is not None:
            payload["gpu_market_prices"] = self.gpu_market_prices
        return payload

def work_suitability(score: Any) -> Dict[str, Any]:
    value = safe_float(score, 0.0)
    if value >= 85:
        return {"label": "매우 적합", "level": "excellent"}
    if value >= 70:
        return {"label": "적합", "level": "good"}
    if value >= 50:
        return {"label": "보통", "level": "normal"}
    if value >= 35:
        return {"label": "부적합", "level": "poor"}
    return {"label": "매우 부적합", "level": "bad"}

def work_component_norms(
    gpu: Dict[str, Any],
    cpu: Dict[str, Any],
    ram: Dict[str, Any],
    storage: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    gpu_norm = clamp(max(
        safe_float(gpu.get("perf_1080"), 0.0),
        safe_float(gpu.get("perf_1440"), 0.0) * 1.25,
        safe_float(gpu.get("perf_2160"), 0.0) * 1.6,
    ) / 100.0, 0.0, 1.0)
    cpu_norm = clamp(safe_float(cpu.get("perf"), 0.0) / 100.0, 0.0, 1.0)
    ram_norm = clamp(safe_float(ram.get("gb"), 16.0) / 64.0, 0.0, 1.0)
    storage_tb = safe_float((storage or {}).get("capacity"), 1000.0) / 1000.0
    storage_norm = clamp(storage_tb / 2.0, 0.0, 1.0)
    return {"gpu": gpu_norm, "cpu": cpu_norm, "ram": ram_norm, "storage": storage_norm}

def score_work_profile(
    gpu: Dict[str, Any],
    cpu: Dict[str, Any],
    ram: Dict[str, Any],
    storage: Optional[Dict[str, Any]],
    profile_key: Any,
) -> int:
    key = normalize_work_profile(profile_key)
    profile = WORK_PROFILES[key]
    norms = work_component_norms(gpu, cpu, ram, storage)
    weights = profile["weights"]
    score = sum(safe_float(weights.get(k), 0.0) * safe_float(norms.get(k), 0.0) for k in weights) * 100.0

    requirements = profile.get("requirements") or {}
    req_gpu = safe_float(requirements.get("gpu"), 0.0)
    req_cpu = safe_float(requirements.get("cpu"), 0.0)
    req_ram = safe_float(requirements.get("ram_gb"), 0.0)
    req_storage = safe_float(requirements.get("storage_tb"), 0.0)
    gpu_score = norms["gpu"] * 100.0
    cpu_score = norms["cpu"] * 100.0
    ram_gb = safe_float(ram.get("gb"), 16.0)
    storage_tb = safe_float((storage or {}).get("capacity"), 1000.0) / 1000.0

    penalty = 0.0
    if req_gpu and gpu_score < req_gpu:
        penalty += min(22.0, (req_gpu - gpu_score) * 0.36)
    if req_cpu and cpu_score < req_cpu:
        penalty += min(18.0, (req_cpu - cpu_score) * 0.30)
    if req_ram and ram_gb < req_ram:
        penalty += 8.0 if ram_gb >= req_ram * 0.5 else 16.0
    if req_storage and storage_tb < req_storage:
        penalty += 4.0
    return int(round(clamp(score - penalty, 0.0, 100.0)))

def estimate_work_scores(
    gpu: Dict[str, Any],
    cpu: Dict[str, Any],
    ram: Dict[str, Any],
    storage: Optional[Dict[str, Any]] = None,
    selected_profile: Any = None,
) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    selected = normalize_work_profile(selected_profile)
    for key, profile in WORK_PROFILES.items():
        score = score_work_profile(gpu, cpu, ram, storage, key)
        suitability = work_suitability(score)
        out[key] = {
            "score": score,
            "label": suitability["label"],
            "level": suitability["level"],
            "name": profile["label"],
            "group": profile["group"],
            "selected": key == selected,
        }
    return out

def make_plan_from_raw_parts(
    user: Any,
    tier: str,
    raw_parts: Dict[str, Dict[str, Any]],
    tier_budget: int,
    alloc: Dict[str, int],
    total: int,
    score: float,
    budget_fit: float,
    overrun: int,
    power_score: float,
    fps_bundle: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    request = RecommendationRequest.from_payload(user)
    resolution = request.resolution
    refresh = request.refresh
    genres = list(request.genres)
    game = request.game
    mode = request.mode
    work_profile = request.work_profile
    gpu_pref = request.gpu_pref
    gpu_maker_prefs = list(request.gpu_brands)
    game_class, _ = game_profile(game)

    cpu = raw_parts["cpu"]
    gpu = raw_parts["gpu"]
    ram = raw_parts["ram"]
    mb = raw_parts["mb"]
    psu = raw_parts["psu"]
    storage = raw_parts["storage"]
    fps = dict(fps_bundle) if fps_bundle is not None else estimate_fps_bundle(gpu, cpu, ram, game, resolution, refresh, tier, genres)
    high_avg = safe_float(fps.get("fps_by_option", {}).get("high"), 0.0)
    high_low1 = safe_float(fps.get("low1_by_option", {}).get("high"), 0.0)

    why = [
        f"{'4K' if resolution == '2160' else 'QHD' if resolution == '1440' else 'FHD'} 기준으로 조합 전체 가격과 호환성 계산",
        f"{refresh}Hz 목표에 맞춘 GPU/CPU/RAM 병목 보정",
    ]
    if game_class == "fps":
        why.append("FPS 장르라 CPU 응답성과 1% Low 안정성을 더 반영")
    elif game_class == "rpg":
        why.append("AAA/RPG 장르라 GPU 평균 FPS와 VRAM 여유를 더 반영")
    elif game_class == "sim":
        why.append("시뮬레이션 장르라 CPU와 RAM 비중을 강화")
    if gpu_pref != "ANY":
        why.append(f"{gpu_pref} 선호를 우선 반영")
    if gpu_maker_prefs:
        why.append("GPU 제조사 가격 후보 우선: " + ", ".join(gpu_maker_label(x) for x in gpu_maker_prefs))
    if fps.get("fps_source") in {"measured_benchmark", "benchmark_calibrated"}:
        why.append("공개 게임별 실측 벤치마크를 기준 구성·해상도·프리셋별로 반영")
    if DB_CACHE.get("loaded"):
        why.append("SQLite 벤치마크/가격 데이터 우선 사용")

    overall = round(clamp(score / 2.0, 0.0, 1.0), 4)
    plan = {
        "tier": tier,
        "price_order_required": True,
        "tierBudget": tier_budget,
        "budget_min": request.budget_min,
        "budget_max": request.budget_max,
        "totalPrice": total,
        "total_price": total,
        "allocation": alloc,
        "parts": {
            "cpu": summarize_part(cpu, "cpu"),
            "gpu": summarize_part(gpu, "gpu"),
            "ram": summarize_part(ram, "ram"),
            "mb": summarize_part(mb, "mb"),
            "psu": summarize_part(psu, "psu"),
            "storage": summarize_part(storage, "storage"),
        },
        "predictions": {
            "tier": {"label": tier, "confidence": overall},
            "cpu": {"id": cpu.get("id"), "label": cpu.get("name"), "confidence": round(clamp(safe_float(cpu.get("perf"), 0.0) / 100.0, 0.0, 1.0), 4), "pred_price": part_price(cpu, "cpu")},
            "gpu": {"id": gpu.get("id"), "label": gpu.get("name"), "confidence": round(clamp(gpu_base_perf(gpu, resolution) / 100.0, 0.0, 1.0), 4), "pred_price": part_price(gpu, "gpu")},
            "ram": {"id": ram.get("id"), "label": ram.get("name"), "confidence": round(clamp(safe_float(ram.get("gb"), 0.0) / 64.0, 0.0, 1.0), 4)},
            "budget_fit": round(budget_fit, 4),
            "overall_score": overall,
        },
        "fps": fps,
        "compatibility": platform_compatibility(cpu, mb, ram),
        "estimatedFPS": {
            "low": fps.get("fps_by_option", {}).get("low"),
            "medium": fps.get("fps_by_option", {}).get("medium"),
            "high": fps.get("fps_by_option", {}).get("high"),
            "ultra": fps.get("fps_by_option", {}).get("ultra"),
        },
        "work_scores": estimate_work_scores(gpu, cpu, ram, storage, work_profile),
        "selected_work": {
            "id": work_profile,
            "name": WORK_PROFILES[work_profile]["label"],
            **work_suitability(score_work_profile(gpu, cpu, ram, storage, work_profile)),
            "score": score_work_profile(gpu, cpu, ram, storage, work_profile),
        },
        "note": "검증된 게임별 실측 FPS에 CPU·GPU 처리 한계를 반영합니다. 실측이 없는 옵션과 구성은 보정 추정으로 표시합니다.",
        "why": why,
        "debug": {
            "total_price": total,
            "overrun": overrun,
            "budget_fit": round(budget_fit, 4),
            "high_avg": high_avg,
            "high_low1": high_low1,
            "power_score": power_score,
            "candidate_score": round(score, 4),
            "recommended_psu_watt": recommended_psu_watt(cpu, gpu),
            "ordering_metrics": {
                "gpu": gpu_base_perf(gpu, resolution),
                "gpu_1080": gpu_base_perf(gpu, "1080"),
                "gpu_1440": gpu_base_perf(gpu, "1440"),
                "gpu_2160": gpu_base_perf(gpu, "2160"),
                "cpu": safe_float(cpu.get("perf"), 0.0),
                "ram": safe_float(ram.get("gb"), 0.0),
                "storage": safe_float(storage.get("capacity"), 0.0),
                "power": power_score,
                "fps": high_avg,
                "low1": high_low1,
                "work": score_work_profile(gpu, cpu, ram, storage, work_profile) if mode == "work" else 0.0,
            },
        },
    }
    recompute_plan_total(plan)
    return plan

def part_cache_key(part: Dict[str, Any]) -> str:
    return str(part.get("id") or canonical_name(part.get("name")))

class CandidateEvaluationCache:
    """Memoize repeated compatibility, FPS, and work-score evaluation per tier."""

    def __init__(
        self,
        request: RecommendationRequest,
        tier: str,
        tier_budget: int,
        price_cache: Dict[Tuple[str, str], int],
        mb_pool: List[Dict[str, Any]],
        psu_pool: List[Dict[str, Any]],
        shared_fps: Optional[Dict[Tuple[str, str, str], Dict[str, Any]]] = None,
    ) -> None:
        self.request = request
        self.tier = tier
        self.tier_budget = tier_budget
        self.price_cache = price_cache
        self.mb_pool = mb_pool
        self.psu_pool = psu_pool
        self.fps_by_parts: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        self.mb_options: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self.psu_options: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self.work_scores: Dict[Tuple[str, str, str, str], int] = {}
        self.shared_fps = shared_fps if shared_fps is not None else {}

    def fps_for(self, gpu: Dict[str, Any], cpu: Dict[str, Any], ram: Dict[str, Any]) -> Dict[str, Any]:
        key = (part_cache_key(gpu), part_cache_key(cpu), part_cache_key(ram))
        if key not in self.fps_by_parts:
            if key not in self.shared_fps:
                self.shared_fps[key] = estimate_fps_bundle(
                    gpu, cpu, ram, self.request.game, self.request.resolution,
                    self.request.refresh, "mid", list(self.request.genres),
                )
            bundle = dict(self.shared_fps[key])
            target = target_fps_for_game(self.tier, self.request.refresh, self.request.game)
            target_low1 = target * low1_ratio_for_genres(list(self.request.genres) or [game_profile(self.request.game)[0]])
            metrics = value_metrics(bundle["high_setting_avg_fps"], safe_float(gpu.get("price"), 0), target, bundle["high_setting_low1_fps"], target_low1)
            for field in ("target_fps", "target_low1_fps", "target_coverage", "low1_target_coverage", "capacity_label"):
                bundle[field] = metrics[field]
            self.fps_by_parts[key] = bundle
        return self.fps_by_parts[key]

    def motherboards_for(self, cpu: Dict[str, Any], ram: Dict[str, Any]) -> List[Dict[str, Any]]:
        key = (part_cache_key(cpu), part_cache_key(ram))
        if key not in self.mb_options:
            self.mb_options[key] = mb_candidates_for(
                cpu, ram, self.mb_pool, self.tier, self.tier_budget, self.price_cache,
            )
        return self.mb_options[key]

    def power_supplies_for(self, cpu: Dict[str, Any], gpu: Dict[str, Any]) -> List[Dict[str, Any]]:
        key = (part_cache_key(cpu), part_cache_key(gpu))
        if key not in self.psu_options:
            self.psu_options[key] = psu_candidates_for(
                cpu, gpu, self.psu_pool, self.tier, self.tier_budget, self.price_cache,
            )
        return self.psu_options[key]

    def work_score_for(
        self,
        gpu: Dict[str, Any],
        cpu: Dict[str, Any],
        ram: Dict[str, Any],
        storage: Dict[str, Any],
    ) -> int:
        key = (part_cache_key(gpu), part_cache_key(cpu), part_cache_key(ram), part_cache_key(storage))
        if key not in self.work_scores:
            self.work_scores[key] = score_work_profile(
                gpu, cpu, ram, storage, self.request.work_profile,
            )
        return self.work_scores[key]

def build_tier_candidates(user: Any, tier: str, rng: random.Random, limit: int = 36,
                          shared_fps: Optional[Dict[Tuple[str, str, str], Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    request = RecommendationRequest.from_payload(user)
    budget_min = request.budget_min
    budget_max = request.budget_max
    resolution = request.resolution
    refresh = request.refresh
    genres = list(request.genres)
    game = request.game
    mode = request.mode
    gpu_pref = request.gpu_pref
    gpu_maker_prefs = list(request.gpu_brands)
    game_class, _ = game_profile(game)

    tier_budget = tier_budget_for_user(budget_max, tier, budget_min)
    alloc = budget_allocations(tier_budget, resolution, refresh, game_class, tier)
    price_cache: Dict[Tuple[str, str], int] = {}

    cpu_pool, gpu_pool, ram_pool, mb_pool, psu_pool, storage_pool = tier_component_pools(
        tier, resolution, refresh, gpu_pref
    )
    market_gpu_prices = request.gpu_market_prices
    if isinstance(market_gpu_prices, dict) and market_gpu_prices:
        priced_gpu_pool = [
            market_gpu_prices[str(part.get("id"))]
            for part in gpu_pool
            if str(part.get("id")) in market_gpu_prices
            and is_recommendable_gpu(market_gpu_prices[str(part.get("id"))])
        ]
        if not priced_gpu_pool:
            priced_gpu_pool = [
                part for part in market_gpu_prices.values()
                if is_recommendable_gpu(part)
                and (gpu_pref == "ANY" or normalize_text(part.get("vendor")) == normalize_text(gpu_pref))
            ]
        gpu_pool = priced_gpu_pool
        # Verified inventory is preferred, but unverified reference prices must
        # not hide all compatible recommendations during a retailer outage.
        if not gpu_pool:
            gpu_pool = [p for p in GPU_CATALOG if is_recommendable_gpu(p)
                        and (gpu_pref == "ANY" or normalize_text(p.get("vendor")) == normalize_text(gpu_pref))]
    mb_pool = filter_compatible_mb(cpu_pool, mb_pool)
    ram_pool = filter_compatible_ram(mb_pool, ram_pool)

    cpu_ranked = rank_parts_for_tier(cpu_pool, "cpu", tier_budget, resolution, refresh, tier, game, genres, price_cache, rng, 10)
    gpu_ranked = rank_parts_for_tier(gpu_pool, "gpu", tier_budget, resolution, refresh, tier, game, genres, price_cache, rng, 10)
    ram_ranked = rank_parts_for_tier(ram_pool, "ram", tier_budget, resolution, refresh, tier, game, genres, price_cache, rng, len(ram_pool))
    storage_ranked = storage_candidates_for(storage_pool, tier, tier_budget, price_cache)
    evaluations = CandidateEvaluationCache(request, tier, tier_budget, price_cache, mb_pool, psu_pool, shared_fps)

    scored: List[Tuple[float, Dict[str, Any], int, float, int, float]] = []
    target_power = target_power_score(tier, resolution, refresh)
    target_fps = target_fps_for_game(tier, refresh, game)
    target_low1 = target_fps * low1_ratio_for_genres(genres or [game_class])
    max_total = budget_max

    for gpu in gpu_ranked:
        for cpu in cpu_ranked:
            for ram in ram_ranked:
                mb_options = evaluations.motherboards_for(cpu, ram)
                if not mb_options:
                    continue
                psu_options = evaluations.power_supplies_for(cpu, gpu)
                for mb in mb_options:
                    for psu in psu_options:
                        for storage in storage_ranked:
                            raw_parts = {"cpu": cpu, "gpu": gpu, "ram": ram, "mb": mb, "psu": psu, "storage": storage}
                            total = price_sum_for_parts(raw_parts, price_cache)
                            if total <= 0:
                                continue
                            overrun = max(0, total - tier_budget)
                            if total < budget_min or total > max_total:
                                continue

                            fps = evaluations.fps_for(gpu, cpu, ram)
                            high_avg = safe_float(fps.get("fps_by_option", {}).get("high"), 0.0)
                            low1_avg = safe_float(fps.get("low1_by_option", {}).get("high"), 0.0)
                            fps_ratio = high_avg / max(1.0, target_fps)
                            if fps_ratio <= 1.0:
                                fps_fit = clamp(fps_ratio, 0.0, 1.0)
                            else:
                                # Once the selected quality target is met, a much faster GPU
                                # should lose to a closer, lower-cost configuration.
                                fps_fit = 1.0 - min(0.42, (fps_ratio - 1.0) * 0.20)
                            low1_fit = clamp(low1_avg / max(1.0, target_low1), 0.0, 1.12)

                            if overrun:
                                budget_fit = max(-0.55, 1.0 - overrun / max(1.0, tier_budget * 0.16))
                            else:
                                underspend = (tier_budget - total) / max(1.0, tier_budget)
                                budget_fit = 1.0 - min(0.22, underspend * 0.18)

                            power = build_power_score(raw_parts, resolution)
                            power_fit = 1.0 - min(1.0, abs(power - target_power) / max(12.0, target_power))
                            value = clamp((high_avg / max(1.0, total / 1000.0)) / 0.18, 0.0, 1.0)
                            ram_gb = safe_float(ram.get("gb"), 16)
                            ram_fit = 0.84 if tier == "low" and ram_gb > 32 else 1.0
                            if tier in {"mid", "high"} and ram_gb < 32:
                                ram_fit = 0.70
                            psu_fit = 1.0 if safe_int(psu.get("watt"), 0) >= recommended_psu_watt(cpu, gpu) else 0.0
                            tier_fit = 1.0 - min(1.0, (
                                abs(tier_rank(gpu.get("tier")) - TIER_RANK[tier]) * 0.55 +
                                abs(tier_rank(cpu.get("tier")) - TIER_RANK[tier]) * 0.25 +
                                abs(tier_rank(ram.get("tier")) - TIER_RANK[tier]) * 0.20
                            ) / 1.8)

                            if mode == "work":
                                work_fit = evaluations.work_score_for(gpu, cpu, ram, storage) / 100.0
                                score = (
                                    0.34 * work_fit +
                                    0.19 * budget_fit +
                                    0.16 * power_fit +
                                    0.10 * value +
                                    0.10 * ram_fit +
                                    0.06 * tier_fit +
                                    0.05 * psu_fit
                                )
                            else:
                                score = (
                                    0.28 * fps_fit +
                                    0.16 * low1_fit +
                                    0.19 * budget_fit +
                                    0.14 * power_fit +
                                    0.10 * value +
                                    0.06 * ram_fit +
                                    0.04 * tier_fit +
                                    0.03 * psu_fit
                                )
                            if gpu_maker_prefs:
                                score += 0.015
                            if mode == "game":
                                # Penalize wasting GPU budget above the estimated CPU
                                # limit, while retaining real FPS and value as main scores.
                                cpu_loss = safe_float((fps.get("bottleneck") or {}).get("cpu_penalty_pct"), 0.0) / 100.0
                                score -= min(0.12, max(0.0, cpu_loss - 0.10) * 0.25)
                            scored.append((score, raw_parts, total, budget_fit, overrun, power))

    if not scored:
        # Loosen tier pools if a very small budget made every full build exceed the target.
        if not (gpu_pool and cpu_pool and ram_pool and mb_pool and psu_pool and storage_pool):
            return []
        storage = min(storage_pool, key=lambda p: cached_part_price(p, "storage", price_cache))
        for cpu in sorted(cpu_pool, key=lambda p: cached_part_price(p, "cpu", price_cache)):
            for gpu in sorted(gpu_pool, key=lambda p: cached_part_price(p, "gpu", price_cache)):
                psus = psu_candidates_for(cpu, gpu, psu_pool, tier, tier_budget, price_cache)
                if not psus:
                    continue
                for ram in sorted(ram_pool, key=lambda p: cached_part_price(p, "ram", price_cache)):
                    boards = mb_candidates_for(cpu, ram, mb_pool, tier, tier_budget, price_cache)
                    if not boards:
                        continue
                    fallback_parts = {"gpu": gpu, "cpu": cpu, "ram": ram, "storage": storage, "mb": boards[0], "psu": psus[0]}
                    total = price_sum_for_parts(fallback_parts, price_cache)
                    if total > 0:
                        power = build_power_score(fallback_parts, resolution)
                        scored.append((0.0, fallback_parts, total, max(-0.45, 1.0 - max(0, total - tier_budget) / max(1.0, tier_budget)), max(0, total - tier_budget), power))
                        break
                if scored:
                    break
            if scored:
                break

    if not scored:
        return []

    scored.sort(key=lambda item: (-item[0], item[2], tuple(part_cache_key(item[1][k]) for k in ["gpu", "cpu", "ram", "storage", "mb", "psu"])))
    # Reserve one candidate per CPU/GPU pair before considering memory or
    # motherboard variants. Previously the shortlist could contain 18 copies
    # of essentially the same performance, hiding valid ordered combinations.
    diverse = []
    repeated = []
    seen_pairs: set = set()
    for item in scored:
        pair = (part_cache_key(item[1]["gpu"]), part_cache_key(item[1]["cpu"]))
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            diverse.append(item)
        else:
            repeated.append(item)
    scored = diverse + repeated
    plans: List[Dict[str, Any]] = []
    seen: set = set()
    for score, raw_parts, total, budget_fit, overrun, power in scored:
        signature = tuple((raw_parts[k].get("id") for k in ["gpu", "cpu", "ram", "mb", "psu", "storage"]))
        if signature in seen:
            continue
        seen.add(signature)
        plans.append(make_plan_from_raw_parts(request, tier, raw_parts, tier_budget, alloc, total, score, budget_fit, overrun, power,
                                             evaluations.fps_for(raw_parts["gpu"], raw_parts["cpu"], raw_parts["ram"])))
        if len(plans) >= limit:
            break
    return plans

def plan_ordering_metrics(plan: Dict[str, Any]) -> Dict[str, float]:
    """Use comparable hardware/FPS measurements, never price or tier labels."""
    debug = plan.get("debug") or {}
    metrics = debug.get("ordering_metrics")
    if metrics:
        return {key: safe_float(value, 0.0) for key, value in metrics.items()}
    parts = plan.get("parts") or {}
    fps = plan.get("fps") or {}
    return {
        "gpu": safe_float((parts.get("gpu") or {}).get("performance_index"), gpu_base_perf(parts.get("gpu") or {}, "1080")),
        "gpu_1080": safe_float((parts.get("gpu") or {}).get("perf_1080"), 0.0),
        "gpu_1440": safe_float((parts.get("gpu") or {}).get("perf_1440"), 0.0),
        "gpu_2160": safe_float((parts.get("gpu") or {}).get("perf_2160"), 0.0),
        "cpu": safe_float((parts.get("cpu") or {}).get("performance_index"), safe_float((parts.get("cpu") or {}).get("perf"), 0.0)),
        "ram": safe_float((parts.get("ram") or {}).get("gb"), 0.0),
        "storage": safe_float((parts.get("storage") or {}).get("capacity"), 0.0),
        "power": safe_float(debug.get("power_score"), 0.0),
        "fps": safe_float((fps.get("fps_by_option") or {}).get("high", debug.get("high_avg")), 0.0),
        "low1": safe_float((fps.get("low1_by_option") or {}).get("high", debug.get("high_low1")), 0.0),
        "work": 0.0,
    }


def tier_upgrade_quality(lower: Dict[str, Any], upper: Dict[str, Any]) -> int:
    """-1 rejects any regression; 0/1/2 distinguish equal/small/clear upgrades.

    FPS may tie in a capped game. A faster GPU or CPU still provides a real
    tier distinction, whereas an expensive board or PSU alone does not.
    """
    lower_metrics = plan_ordering_metrics(lower)
    upper_metrics = plan_ordering_metrics(upper)
    lower_gpu = (lower.get("parts") or {}).get("gpu") or {}
    upper_gpu = (upper.get("parts") or {}).get("gpu") or {}
    lower_id = gpu_exact_model_key(lower_gpu.get("name")) or lower_gpu.get("performance_ref_id") or lower_gpu.get("id")
    upper_id = gpu_exact_model_key(upper_gpu.get("name")) or upper_gpu.get("performance_ref_id") or upper_gpu.get("id")
    if lower_id and lower_id == upper_id:
        return -1
    if lower.get("price_order_required") or upper.get("price_order_required"):
        if safe_int(upper.get("totalPrice"), 0) <= safe_int(lower.get("totalPrice"), 0):
            return -1
    if any(upper_metrics.get(key, 0.0) + 1e-6 < value for key, value in lower_metrics.items()):
        return -1
    gains = {
        key: upper_metrics.get(key, 0.0) - lower_metrics.get(key, 0.0)
        for key in ("gpu", "cpu", "fps", "work")
    }
    if any(gain >= max(2.0, lower_metrics.get(key, 0.0) * 0.05) for key, gain in gains.items()):
        return 2
    return 1 if any(gain > 1e-6 for gain in gains.values()) else 0


def select_ordered_tier_plans(candidate_sets: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    """Find the best valid chain with hard component and FPS constraints.

    Dynamic programming retains the best chain ending at each candidate.
    Missing tiers are allowed only when a complete ordered chain is impossible;
    even LOW/HIGH pairs with a missing MID must satisfy the same constraints.
    """
    tiers = ("low", "mid", "high")
    # Each entry contains (chain, upgrade-quality tuple, candidate-score sum).
    states: List[Tuple[Dict[str, Dict[str, Any]], Tuple[int, ...], float]] = []

    def chain_rank(state: Tuple[Dict[str, Dict[str, Any]], Tuple[int, ...], float]) -> Tuple[Any, ...]:
        chain, qualities, score = state
        # Maximize populated tiers, then prefer improvement at *every* step.
        return (len(chain), min(qualities, default=0), sum(qualities), score,
                -sum(safe_float(p.get("totalPrice"), 0.0) for p in chain.values()))

    for tier in tiers:
        previous_states = states[:]
        for plan in candidate_sets.get(tier) or []:
            score = safe_float((plan.get("debug") or {}).get("candidate_score"), 0.0)
            best = ({tier: plan}, (), score)
            for chain, qualities, prior_score in previous_states:
                prior = next(reversed(chain.values()))
                quality = tier_upgrade_quality(prior, plan)
                if quality < 0:
                    continue
                extended = ({**chain, tier: plan}, qualities + (quality,), prior_score + score)
                if chain_rank(extended) > chain_rank(best):
                    best = extended
            states.append(best)
    if not states:
        return {tier: {} for tier in tiers}
    selected, _qualities, _score = max(states, key=chain_rank)
    return {tier: selected.get(tier, {}) for tier in tiers}

def build_tier_plan(user: Any, tier: str, used_exact: set, used_family: set, used_vendor: set, rng: random.Random) -> Dict[str, Any]:
    candidates = build_tier_candidates(user, tier, rng, limit=1)
    return candidates[0] if candidates else {}

def complete_recommendation_tiers(results, candidate_sets, request):
    """Keep a compatible baseline visible even when no distinct upgrade exists."""
    available = [p for plans in candidate_sets.values() for p in plans if p.get("parts")]
    if not available:
        return results
    previous = None
    for tier in ("low", "mid", "high"):
        plan = results.get(tier) or {}
        if not plan.get("parts") or (previous and tier_upgrade_quality(previous, plan) < 0):
            if previous:
                alternatives = [p for p in candidate_sets.get(tier, []) if tier_upgrade_quality(previous, p) > 0]
                plan = max(alternatives, key=lambda p: p["debug"].get("candidate_score", 0)) if alternatives else copy.deepcopy(previous)
                if not alternatives:
                    plan["same_configuration"] = True
                    plan["note"] = "조건에 맞는 추가 업그레이드가 없어 앞 등급과 동일한 호환 구성을 표시합니다."
            else:
                plan = copy.deepcopy(min(available, key=lambda p: p["totalPrice"]))
        plan["tier"] = tier
        plan["tierBudget"] = tier_budget_for_user(request.budget_max, tier, request.budget_min)
        fps = plan.get("fps") or {}
        fps["target_fps"] = target_fps_for_game(tier, request.refresh, request.game)
        fps["target_low1_fps"] = fps["target_fps"] * low1_ratio_for_genres(list(request.genres) or [game_profile(request.game)[0]])
        plan.setdefault("predictions", {}).setdefault("tier", {})["label"] = tier
        recompute_plan_total(plan)
        results[tier] = plan
        previous = plan
    return results


def recommend(user: Any) -> Dict[str, Any]:
    request = RecommendationRequest.from_payload(user)
    cache_key = json.dumps(request.as_payload(include_market_prices=False), sort_keys=True, ensure_ascii=False)
    cached = RECOMMENDATION_CACHE.get(cache_key)
    if cached and time.monotonic() - cached[0] < 60:
        response = copy.deepcopy(cached[1])
        response["engine"]["cached"] = True
        return response
    market_gpu_prices = resolve_verified_gpu_market_prices(request.gpu_pref, list(request.gpu_brands))
    request = replace(request, gpu_market_prices=market_gpu_prices)

    seed = stable_seed(request.as_payload(include_market_prices=False))
    rng = random.Random(seed)
    shared_fps: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    candidate_sets = {
        tier: build_tier_candidates(request, tier, rng, limit=36, shared_fps=shared_fps)
        for tier in ["low", "mid", "high"]
    }
    results = select_ordered_tier_plans(candidate_sets)
    results = complete_recommendation_tiers(results, candidate_sets, request)

    warnings: List[str] = []
    if not DB_CACHE.get("loaded"):
        warnings.append("SQLite DB를 찾지 못해 일부 CPU/주변 부품은 내장 카탈로그 기준으로 계산했습니다.")
    if not market_gpu_prices:
        warnings.append("다나와·컴퓨존에서 현재 그래픽카드 가격을 확인하지 못해 카탈로그 참고 가격을 사용했습니다.")

    payload = {
        "input": request.as_payload(include_market_prices=False),
        "results": results,
        "warning": " ".join(warnings) if warnings else None,
        "engine": {
            "mode": "sqlite_hybrid_v1",
            "db_loaded": DB_CACHE.get("loaded", False),
            "catalog": {k: len(v) for k, v in CATALOGS.items()},
            "db_summary": DB_CACHE.get("summary", {}),
            "verified_gpu_prices": len(market_gpu_prices),
        },
    }
    refresh_recommendation_prices(payload)
    # Retail refresh may reverse totals; only retain genuine upgrades at the
    # final displayed prices, then fill any gap with an explicitly equal build.
    refreshed = {tier: [plan] if plan.get("parts") else [] for tier, plan in payload["results"].items()}
    payload["results"] = complete_recommendation_tiers(payload["results"], refreshed, request)
    priced_plans = [plan for plan in payload["results"].values() if plan.get("parts")]
    for plan in priced_plans:
        attach_graphics_modes(plan["fps"], plan["parts"]["gpu"], plan["parts"]["cpu"], request.game, request.resolution)
    if any(plan.get("total_is_estimate") for plan in priced_plans):
        warnings.append("현재 판매가를 확인하지 못한 부품은 참고 가격이며, 해당 합계는 예상 금액입니다.")
    if any(plan.get("budget_status") == "over_budget" for plan in priced_plans):
        warnings.append("판매가 갱신 후 예산 상한을 초과한 구성은 초과 금액을 별도로 표시합니다.")
    if len(priced_plans) < 3:
        warnings.append("일부 등급에서 예산·호환성과 LOW → MID → HIGH 성능 순서를 모두 충족하는 구성을 찾지 못했습니다.")
    if any(tier_upgrade_quality(lower, upper) == 0 for lower, upper in zip(priced_plans, priced_plans[1:])):
        warnings.append("현재 예산과 판매 후보에서는 일부 등급의 CPU·GPU 성능이 같습니다. 더 높은 등급이라고 FPS가 반드시 증가하지는 않습니다.")
    payload["warning"] = " ".join(warnings) if warnings else None
    payload["engine"]["db_loaded"] = DB_CACHE.get("loaded", False)
    payload["engine"]["db_summary"] = DB_CACHE.get("summary", {})
    payload["engine"]["evaluated_cpu_gpu_ram_combinations"] = len(shared_fps)
    payload["engine"]["cached"] = False
    if len(RECOMMENDATION_CACHE) >= 32:
        RECOMMENDATION_CACHE.pop(next(iter(RECOMMENDATION_CACHE)))
    RECOMMENDATION_CACHE[cache_key] = (time.monotonic(), copy.deepcopy(payload))
    return payload

# ─────────────────────────────────────────────────────────────
# HTTP helpers
# ─────────────────────────────────────────────────────────────

def catalog_response() -> Dict[str, Any]:
    def catalog_part(part: Dict[str, Any], part_type: str) -> Dict[str, Any]:
        return {**part, **summarize_part(part, part_type)}

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
        "db_loaded": DB_CACHE.get("loaded", False),
        "db_summary": DB_CACHE.get("summary", {}),
    }
    # Retail SKUs extend the browser while the curated reference models keep
    # recommendation/FPS calibration stable. Saved prices retain their age.
    catalog_keys = {
        "gpu": "gpus", "cpu": "cpus", "ram": "rams", "storage": "storages",
        "hdd": "hdds", "mb": "mbs", "psu": "psus", "case": "cases",
        "software": "software",
    }
    for part_type, key in catalog_keys.items():
        retail = saved_products(part_type)
        known = {part["id"] for part in response[key]}
        response[key].extend(part for part in retail if part["id"] not in known)
        known.update(part["id"] for part in retail)
        response[key].extend(part for part in imported_products(part_type) if part.get("id") not in known)
    response["catalog_sizes"] = {kind: len(response[key]) for kind, key in catalog_keys.items()}
    response["reference_catalog_sizes"] = {kind: len(items) for kind, items in CATALOGS.items()}
    return response


# Product imports are held only long enough for a human to inspect and confirm.
IMPORT_PREVIEWS: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def import_part_type(name: str, spec: str = "") -> str:
    text = normalize_text(name + " " + spec[:400])
    patterns = (
        ("gpu", r"\b(?:geforce|radeon|rtx\s*\d{4}|gtx\s*\d{4}|rx\s*\d{4})\b|그래픽카드"),
        ("ram", r"\b(?:ddr[45]|dimm|memory)\b|메모리"),
        ("mb", r"\b(?:motherboard|mainboard|b650|b850|b760|z790|z890|x870)\b|메인보드"),
        ("psu", r"\b(?:power supply|psu|[5-9]\d{2}w|1\d{3}w)\b|파워서플라이"),
        ("storage", r"\b(?:ssd|nvme|990\s*pro|sn850|p41)\b"),
        ("hdd", r"\b(?:hdd|hard disk)\b"),
        ("cpu", r"\b(?:ryzen|intel core|core ultra|processor)\b|프로세서"),
    )
    for part_type, pattern in patterns:
        if re.search(pattern, text, re.I):
            return part_type
    return ""


def normalize_import_product(raw: Dict[str, Any], requested_type: str = "") -> Dict[str, Any]:
    url = supported_product_url(raw.get("url"))
    name = clean_visible_text(raw.get("name"))[:300]
    if not url or not name or len(name) < 5:
        raise ValueError("Product information was incomplete")
    detected = import_part_type(name, str(raw.get("spec_text") or ""))
    requested = normalize_browse_part_type(requested_type)
    if detected and requested and detected != requested:
        raise ValueError("Product category does not match the selected component")
    part_type = detected or requested
    if not part_type or not market_component_name_valid(part_type, name):
        raise ValueError("Product category could not be verified")
    provider, code = product_page_key(url)
    price = safe_int(raw.get("price"), 0)
    if not 1000 <= price <= 20_000_000:
        price = 0
    item = enrich_danawa_browse_product(part_type, code, name, price, url,
                                        retailer_image_url(raw.get("image_url")), part_type, 0,
                                        clean_visible_text(raw.get("spec_text"))[:2000])
    item.update(id=f"{provider}_{part_type}_{code}", shop="Compuzone" if provider == "compuzone" else "Danawa",
                component_type=part_type, source_url=url, spec_text=clean_visible_text(raw.get("spec_text"))[:2000],
                price_source=f"{provider}_import", price_status="verified" if price else "unavailable",
                price_checked_at=datetime.utcnow().isoformat(timespec="seconds") + "Z" if price else "",
                tags=["user_imported"])
    if raw.get("brand"):
        item["brand"] = clean_visible_text(raw["brand"])[:80]
    item["manufacturer"] = item.get("brand") or item.get("vendor") or infer_brand(name)
    item["product_url"] = url
    return item


def import_duplicate(old: Dict[str, Any], new: Dict[str, Any]) -> bool:
    if old.get("id") == new.get("id"):
        return True
    if product_page_key(old.get("url")) and product_page_key(old.get("url")) == product_page_key(new.get("url")):
        return True
    old_brand = normalize_text(old.get("manufacturer") or infer_brand(old.get("name")))
    new_brand = normalize_text(new.get("manufacturer") or infer_brand(new.get("name")))
    return bool(old_brand and old_brand == new_brand and canonical_name(old.get("name")) == canonical_name(new.get("name"))
                and compatible_price_name(old.get("name"), new.get("name"))
                and compatible_price_name(new.get("name"), old.get("name")))


def stage_import(item: Dict[str, Any]) -> Dict[str, Any]:
    now = time.monotonic()
    for token, (expires, _) in list(IMPORT_PREVIEWS.items()):
        if expires < now:
            IMPORT_PREVIEWS.pop(token, None)
    token = secrets.token_urlsafe(24)
    IMPORT_PREVIEWS[token] = (now + 600, item)
    return {"token": token, "product": item}


def import_preview_response(body: Dict[str, Any]) -> Dict[str, Any]:
    url = supported_product_url(body.get("url"))
    if not url:
        return {"ok": False, "error": "Unsupported product URL"}
    try:
        raw = fetch_product_page(url)
        item = normalize_import_product(raw, body.get("type") or "")
        return {"ok": True, **stage_import(item)}
    except (OSError, ValueError, LookupError) as error:
        return {"ok": False, "error": str(error) if isinstance(error, ValueError) else "Could not retrieve this product"}


def import_search_response(part_type: Any, query: Any, source: Any = "all") -> Dict[str, Any]:
    ctype = normalize_browse_part_type(part_type)
    name = clean_visible_text(query)[:120]
    if not ctype or len(name) < 3 or supported_product_url(name):
        return {"ok": False, "error": "Enter a product name to search online", "candidates": []}
    result = market_products_response(ctype, name, 1, 40, False, source, persist=False)
    candidates = []
    wanted_brand = infer_brand(name)
    for raw in result.get("items", []):
        if not supported_product_url(raw.get("url")) or not compatible_price_name(name, raw.get("name")):
            continue
        if wanted_brand and normalize_text(wanted_brand) != normalize_text(infer_brand(raw.get("name"))):
            continue
        try:
            candidates.append(stage_import(normalize_import_product(raw, ctype)))
        except ValueError:
            continue
        if len(candidates) >= 20:
            break
    return {"ok": result.get("ok", False), "status": result.get("status"), "candidates": candidates,
            "error": result.get("error") or ""}


def import_commit_response(body: Dict[str, Any]) -> Dict[str, Any]:
    token = str(body.get("token") or "")
    staged = IMPORT_PREVIEWS.get(token)
    if not staged or staged[0] < time.monotonic():
        return {"ok": False, "error": "Product preview expired; search again"}
    item = staged[1]
    for old in [*imported_products(item["component_type"]), *saved_products(item["component_type"]),
                *CATALOGS.get(item["component_type"], [])]:
        if import_duplicate(old, item):
            return {"ok": True, "created": False, "product": old}
    saved, created = save_imported_product(item, import_duplicate)
    if created:
        IMPORT_PREVIEWS.pop(token, None)
    return {"ok": True, "created": created, "product": saved}

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
        if sku:
            if product_page_key(item.get("url")) == sku:
                exact.append(url)
        elif canonical_name(listed_name) == canonical_name(name):
            exact.append(url)
        elif requested and any(re.search(r"\d", token) for token in requested):
            listed = image_name_tokens(listed_name, ctype)
            if requested.issubset(listed):
                if ctype == "gpu" and gpu_exact_model_key(name) != gpu_exact_model_key(listed_name):
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
    cached = IMAGE_URL_CACHE.get(key)
    candidates = saved_part_image_urls(clean_name, part_type, product_url)
    if cached:
        candidates.append(cached)
    for url in sorted(set(candidates), key=lambda value: (image_source_priority(value), value)):
        if url not in excluded:
            IMAGE_URL_CACHE[key] = url
            return url
    # A known SKU is recovered from its own sales page in send_part_image.
    # Do not replace it with another product returned by a price search.
    if product_page_key(product_url) or excluded:
        return ""
    try:
        live = fetch_market_top_product(clean_name, part_type, timeout=3.0)
        image_url = retailer_image_url((live or {}).get("image_url"))
    except Exception:
        image_url = ""
    if image_url:
        if len(IMAGE_URL_CACHE) >= 2048:
            IMAGE_URL_CACHE.pop(next(iter(IMAGE_URL_CACHE)))
        IMAGE_URL_CACHE[key] = image_url
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
                IMAGE_URL_CACHE[(normalize_text(part_type), canonical_name(name), product_page_key(product_url))] = recovered_url
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
    if target in PREVIEW_CACHE:
        cached = PREVIEW_CACHE[target]
        return {**cached, "image_url": cached.get("image_url") or safe_external_url(fallback_image)}

    title = clean_visible_text(fallback_name)
    description = ""
    image_url = safe_external_url(fallback_image)
    try:
        req = Request(target, headers=DANAWA_HEADERS)
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
            image_url = image_url or absolute_image_url(meta_content_from_soup(soup, ["og:image", "twitter:image"]), target)
        else:
            m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
            if m:
                title = clean_visible_text(re.sub(r"<[^>]+>", " ", m.group(1)))
            m = re.search(r"<meta[^>]+(?:property|name)=[\"'](?:og:image|twitter:image)[\"'][^>]+content=[\"']([^\"']+)[\"']", html, re.I)
            if m:
                image_url = image_url or absolute_image_url(m.group(1), target)
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
    PREVIEW_CACHE[target] = out
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

def send_json(handler: BaseHTTPRequestHandler, status: int, payload: Dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
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
                "model_loaded": MODEL_LOADED,
                "engine": "sqlite_hybrid_v1",
                "db_loaded": DB_CACHE.get("loaded", False),
                "catalog_sizes": {k: len(v) for k, v in CATALOGS.items()},
                "db_summary": DB_CACHE.get("summary", {}),
            }
            send_json(self, 200, payload)
            return

        if path == "/api/catalog":
            send_json(self, 200, catalog_response())
            return

        if path in {"/api/products", "/api/danawa-products"}:
            payload = market_products_response(
                params.get("type") or params.get("part_type") or "",
                params.get("query") or "",
                params.get("page") or 1,
                params.get("limit") or 40,
                params.get("refresh") or "",
                params.get("source") or ("danawa" if path == "/api/danawa-products" else "all"),
            )
            send_json(self, 200 if payload.get("ok") else 502, payload)
            return

        if path == "/api/part-image":
            send_part_image(self, params)
            return

        if path == "/api/page-preview":
            send_page_preview(self, params)
            return

        fp = Path(STATIC_DIR) / ("index.html" if path in {"", "/"} else path.lstrip("/"))
        if fp.exists() and fp.is_file():
            data = fp.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", guess_mime(fp))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b"404 Not Found")

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
                send_json(self, 200, fps_estimate_response(body))
                return
            if path == "/api/price-lookup":
                send_json(self, 200, price_lookup_response(body))
                return
            if path == "/api/product-search":
                send_json(self, 200, product_search_response(body))
                return
            send_json(self, 200, recommend(body))
        except Exception as e:
            traceback.print_exc()
            send_json(self, 500, {"error": f"server error: {e}"})

# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--static-dir", type=str, default=str(APP_DIR))
    p.add_argument("--host", type=str, default="127.0.0.1")
    p.add_argument("--port", type=int, default=4000)
    return p.parse_args()

def main() -> None:
    global STATIC_DIR
    args = parse_args()
    STATIC_DIR = Path(args.static_dir).resolve()
    load_config()
    load_db_cache()

    print("Server ready.")
    print(f"  DB loaded: {DB_CACHE.get('loaded', False)}")
    print(f"  Catalog sizes: " + ", ".join(f"{k}={len(v)}" for k, v in CATALOGS.items()))
    if DB_CACHE.get("loaded"):
        print(f"  DB summary: {DB_CACHE.get('summary', {})}")
    print(f"Serving at http://{args.host}:{args.port}")

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    httpd.serve_forever()

if __name__ == "__main__":
    main()
