# crawl_data.py – 실제 벤치마크 데이터 크롤러
# Changes: TechPowerUp/Tom's Hardware site-specific parsers, GPU name normalization,
#          structured URL templates, manual CSV import support
from __future__ import annotations

import csv
import re
from retailer_parsing import danawa_candidate_blocks, price_from_danawa_block
import time
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, quote_plus, urljoin, urlsplit
from urllib.request import Request, urlopen

try:
    import requests
except Exception:  # pragma: no cover - requests is optional.
    requests = None

try:
    from bs4 import BeautifulSoup, Tag
except Exception:  # pragma: no cover - BeautifulSoup is optional.
    BeautifulSoup = None
    Tag = object

DB_PATH = Path("data/pc.db")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PCBenchBot/1.0; +contact@example.com)",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.6",
}

# ─────────────────────────────────────────────────────────────
# GPU name normalisation table
# ─────────────────────────────────────────────────────────────
GPU_ALIAS: Dict[str, str] = {
    # NVIDIA
    "rtx 4090":              "NVIDIA RTX 4090",
    "rtx 4080 super":        "NVIDIA RTX 4080 Super",
    "rtx 4080":              "NVIDIA RTX 4080",
    "rtx 4070 ti super":     "NVIDIA RTX 4070 Ti Super",
    "rtx 4070 ti":           "NVIDIA RTX 4070 Ti",
    "rtx 4070 super":        "NVIDIA RTX 4070 Super",
    "rtx 4070":              "NVIDIA RTX 4070",
    "rtx 4060 ti":           "NVIDIA RTX 4060 Ti",
    "rtx 4060":              "NVIDIA RTX 4060",
    "rtx 3090":              "NVIDIA RTX 3090",
    "rtx 3080 12gb":         "NVIDIA RTX 3080 12GB",
    "rtx 3080":              "NVIDIA RTX 3080",
    "rtx 3070":              "NVIDIA RTX 3070",
    "rtx 3060 ti":           "NVIDIA RTX 3060 Ti",
    "rtx 3060":              "NVIDIA RTX 3060",
    "gtx 1660 super":        "NVIDIA GTX 1660 Super",
    "gtx 1660":              "NVIDIA GTX 1660",
    # AMD
    "rx 7900 xtx":           "AMD RX 7900 XTX",
    "rx 7900 xt":            "AMD RX 7900 XT",
    "rx 7900 gre":           "AMD RX 7900 GRE",
    "rx 7800 xt":            "AMD RX 7800 XT",
    "rx 7700 xt":            "AMD RX 7700 XT",
    "rx 7600 xt":            "AMD RX 7600 XT",
    "rx 7600":               "AMD RX 7600",
    "rx 6900 xt":            "AMD RX 6900 XT",
    "rx 6800 xt":            "AMD RX 6800 XT",
    "rx 6800":               "AMD RX 6800",
    "rx 6700 xt":            "AMD RX 6700 XT",
    "rx 6600 xt":            "AMD RX 6600 XT",
    "rx 6600":               "AMD RX 6600",
    "rx 6500 xt":            "AMD RX 6500 XT",
}

RESOLUTION_MAP = {
    "1080p": "1080", "fhd": "1080", "1920x1080": "1080", "full hd": "1080",
    "1440p": "1440", "qhd": "1440", "2560x1440": "1440",
    "4k": "2160", "uhd": "2160", "3840x2160": "2160",
}

SETTING_MAP = {
    "ultra": "ultra", "maximum": "ultra", "max": "ultra",
    "high": "high",
    "medium": "medium", "mid": "medium",
    "low": "low", "minimum": "low", "min": "low",
}

# Source URL templates – fill in real review/benchmark URLs here
# Each entry: (site_tag, url_template, component_name, component_type)
# Use {game} as placeholder if the URL contains the game name
SOURCE_URLS: List[Tuple[str, str, str, str]] = [
    # Public GPU hierarchy table with geometric-mean raster FPS by resolution.
    ("tomshw", "https://www.tomshardware.com/reviews/gpu-hierarchy,4388.html", "GPU Benchmark Hierarchy", "GPU"),

    # TechPowerUp GPU reviews (example – add real review URLs when you need per-game rows)
    # ("tpu", "https://www.techpowerup.com/review/nvidia-geforce-rtx-4090/4.html", "NVIDIA RTX 4090", "GPU"),
    # ("tpu", "https://www.techpowerup.com/review/amd-radeon-rx-7900-xtx/4.html", "AMD RX 7900 XTX", "GPU"),
]

PRICE_TARGETS: List[Tuple[str, str]] = [
    ("GPU", "NVIDIA GeForce RTX 4090"),
    ("GPU", "NVIDIA GeForce RTX 4080 Super"),
    ("GPU", "NVIDIA GeForce RTX 4070 Ti Super"),
    ("GPU", "NVIDIA GeForce RTX 4070 Super"),
    ("GPU", "NVIDIA GeForce RTX 4070"),
    ("GPU", "NVIDIA GeForce RTX 4060 Ti"),
    ("GPU", "NVIDIA GeForce RTX 4060"),
    ("GPU", "NVIDIA GeForce RTX 3080"),
    ("GPU", "NVIDIA GeForce RTX 3070"),
    ("GPU", "NVIDIA GeForce RTX 3060"),
    ("GPU", "AMD Radeon RX 7900 XTX"),
    ("GPU", "AMD Radeon RX 7900 XT"),
    ("GPU", "AMD Radeon RX 7900 GRE"),
    ("GPU", "AMD Radeon RX 7800 XT"),
    ("GPU", "AMD Radeon RX 7700 XT"),
    ("GPU", "AMD Radeon RX 7600 XT"),
    ("GPU", "AMD Radeon RX 7600"),
    ("GPU", "AMD Radeon RX 6800 XT"),
    ("GPU", "AMD Radeon RX 6700 XT"),
    ("GPU", "AMD Radeon RX 6600"),
    ("CPU", "AMD Ryzen 5 5600"),
    ("CPU", "AMD Ryzen 7 5700X"),
    ("CPU", "Intel Core i5-12400F"),
    ("CPU", "Intel Core i5-13600KF"),
    ("CPU", "Intel Core i9-14900K"),
    ("CPU", "Intel Core i7-14700K"),
    ("CPU", "Intel Core i5-14600K"),
    ("CPU", "Intel Core i5-14400"),
    ("CPU", "Intel Core i9-13900K"),
    ("CPU", "Intel Core i7-13700K"),
    ("CPU", "Intel Core i5-13600K"),
    ("CPU", "Intel Core i5-13400F"),
    ("CPU", "Intel Core i3-13100F"),
    ("CPU", "Intel Core i7-1365U"),
    ("CPU", "Intel Core i5-1335U"),
    ("CPU", "Intel Core i3-1315U"),
    ("CPU", "AMD Ryzen 9 7950X"),
    ("CPU", "AMD Ryzen 7 7800X3D"),
    ("CPU", "AMD Ryzen 7 7700X"),
    ("CPU", "AMD Ryzen 5 7600X"),
    ("CPU", "AMD Ryzen 7 9700X"),
    ("CPU", "AMD Ryzen 5 5600X"),
    ("CPU", "Intel Core Ultra 5 245K"),
    ("RAM", "DDR4 16GB 3200"),
    ("RAM", "DDR4 32GB 3200"),
    ("RAM", "DDR5 32GB 6000"),
    ("RAM", "DDR5 64GB 6000"),
    ("MB", "B550 ATX"),
    ("MB", "B650 ATX"),
    ("MB", "B760 ATX DDR4"),
    ("MB", "B760 ATX DDR5"),
    ("MB", "Z890 ATX"),
    ("STORAGE", "NVMe SSD 1TB"),
    ("STORAGE", "NVMe SSD 2TB"),
    ("STORAGE", "NVMe SSD 4TB"),
    ("PSU", "650W 80+ Bronze"),
    ("PSU", "750W 80+ Gold"),
    ("PSU", "850W 80+ Gold"),
    ("PSU", "1000W 80+ Gold"),
]

PRICE_HINTS: Dict[str, int] = {
    "nvidia geforce rtx 4090": 2200000,
    "nvidia geforce rtx 4080 super": 1060000,
    "nvidia geforce rtx 4070 ti super": 800000,
    "nvidia geforce rtx 4070 super": 580000,
    "nvidia geforce rtx 4070": 500000,
    "nvidia geforce rtx 4060 ti": 370000,
    "nvidia geforce rtx 4060": 260000,
    "nvidia geforce rtx 3080": 600000,
    "nvidia geforce rtx 3070": 380000,
    "nvidia geforce rtx 3060": 280000,
    "amd radeon rx 7900 xtx": 1100000,
    "amd radeon rx 7900 xt": 950000,
    "amd radeon rx 7900 gre": 700000,
    "amd radeon rx 7800 xt": 620000,
    "amd radeon rx 7700 xt": 430000,
    "amd radeon rx 7600 xt": 380000,
    "amd radeon rx 7600": 300000,
    "amd radeon rx 6800 xt": 550000,
    "amd radeon rx 6700 xt": 330000,
    "amd radeon rx 6600": 190000,
}

GPU_DANAWA_CATEGORY_IDS = {"112753"}
STORAGE_DANAWA_CATEGORY_IDS = {"112760"}

# ─────────────────────────────────────────────────────────────
# DB initialisation
# ─────────────────────────────────────────────────────────────
def init_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS components (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        type       TEXT NOT NULL,
        name       TEXT NOT NULL UNIQUE,
        brand      TEXT,
        model      TEXT,
        socket     TEXT,
        vram       INTEGER,
        perf_score INTEGER,
        tdp        INTEGER,
        msrp       INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
    cols = {row[1] for row in conn.execute("PRAGMA table_info(components)").fetchall()}
    if "brand" not in cols:
        conn.execute("ALTER TABLE components ADD COLUMN brand TEXT")
    if "model" not in cols:
        conn.execute("ALTER TABLE components ADD COLUMN model TEXT")
    if "socket" not in cols:
        conn.execute("ALTER TABLE components ADD COLUMN socket TEXT")
    if "vram" not in cols:
        conn.execute("ALTER TABLE components ADD COLUMN vram INTEGER")
    if "perf_score" not in cols:
        conn.execute("ALTER TABLE components ADD COLUMN perf_score INTEGER DEFAULT 0")
    if "msrp" not in cols:
        conn.execute("ALTER TABLE components ADD COLUMN msrp INTEGER DEFAULT 0")
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────────────────────
# Name normalisation helpers
# ─────────────────────────────────────────────────────────────
def normalize_gpu_name(raw: str) -> str:
    """Map a scraped GPU name to our canonical name."""
    s = re.sub(r"\s+", " ", raw.lower().strip())
    # Remove vendor prefix duplicates like "nvidia geforce rtx 4090" -> "rtx 4090"
    s = re.sub(r"^(nvidia\s+)?(geforce\s+)?", "", s)
    s = re.sub(r"^(amd\s+)?(radeon\s+)?", "", s)
    s = s.strip()
    return GPU_ALIAS.get(s, raw.strip())

def normalize_resolution(raw: str) -> str:
    s = raw.lower().strip()
    for k, v in RESOLUTION_MAP.items():
        if k in s:
            return v
    m = re.search(r"(\d{3,4})\s*x\s*(\d{3,4})", s)
    if m:
        h = int(m.group(2))
        return "2160" if h >= 2000 else "1440" if h >= 1350 else "1080"
    m2 = re.search(r"(\d{3,4})p?", s)
    if m2:
        p = int(m2.group(1))
        return "2160" if p >= 2000 else "1440" if p >= 1350 else "1080"
    return "1080"

def normalize_setting(raw: str) -> str:
    s = raw.lower().strip()
    for k, v in SETTING_MAP.items():
        if k in s:
            return v
    return "high"

def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def to_float(s: str) -> Optional[float]:
    m = re.search(r"(\d[\d,]*\.?\d*)", s.replace(" ", ""))
    return float(m.group(1).replace(",", "")) if m else None

def fps_from_score_cell(s: str) -> Optional[float]:
    """Extract FPS from cells like '67.4% (133.2)'."""
    m = re.search(r"\((\d[\d,]*\.?\d*)\)", s)
    if m:
        return float(m.group(1).replace(",", ""))
    return to_float(s)

# ─────────────────────────────────────────────────────────────
# HTTP helpers
# ─────────────────────────────────────────────────────────────
def fetch_html(url: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            if requests is not None:
                r = requests.get(url, headers=HEADERS, timeout=20)
                r.raise_for_status()
                return r.text

            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=20) as resp:
                raw = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="ignore")
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return ""

# ─────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────
def upsert_component(conn: sqlite3.Connection, ctype: str, name: str,
                     brand: str = "", perf_score: int = 0, tdp: int = 0) -> int:
    cur = conn.cursor()
    cur.execute("SELECT id FROM components WHERE type=? AND name=?", (ctype, name))
    row = cur.fetchone()
    if row is None:
        cur.execute("SELECT id FROM components WHERE name=?", (name,))
        row = cur.fetchone()

    if row is not None:
        cid = int(row[0])
        cur.execute("""
            UPDATE components
            SET brand=?,
                perf_score=CASE WHEN ? > 0 THEN ? ELSE perf_score END,
                tdp=CASE WHEN ? > 0 THEN ? ELSE tdp END
            WHERE id=?
        """, (brand, perf_score, perf_score, tdp, tdp, cid))
    else:
        cur.execute("""
            INSERT INTO components(type, name, brand, perf_score, tdp)
            VALUES (?,?,?,?,?)
        """, (ctype, name, brand, perf_score, tdp))
        cid = int(cur.lastrowid)
    conn.commit()
    return cid

def upsert_benchmark(conn: sqlite3.Connection, component_id: int, game: str,
                     resolution: str, setting: str, avg_fps: Optional[float],
                     low1_fps: Optional[float], source_url: str) -> None:
    conn.execute("""
        INSERT OR REPLACE INTO benchmarks
            (component_id, game, resolution, setting, avg_fps, low1_fps, source_url)
        VALUES (?,?,?,?,?,?,?)
    """, (component_id, game, resolution, setting, avg_fps, low1_fps, source_url))

def upsert_price(conn: sqlite3.Connection, component_id: int, shop: str,
                 price: int, url: str, currency: str = "KRW") -> None:
    conn.execute("""
        INSERT OR IGNORE INTO prices
            (component_id, shop, currency, price, url)
        VALUES (?,?,?,?,?)
    """, (component_id, shop, currency, price, url))

def danawa_search_url(query: str) -> str:
    return "https://search.danawa.com/dsearch.php?query=" + quote_plus(query.strip())

def parse_price_value(text: str) -> Optional[int]:
    digits = re.sub(r"[^\d]", "", text or "")
    if not digits:
        return None
    value = int(digits)
    return value if value >= 1000 else None

def strip_html(s: str) -> str:
    return clean_text(re.sub(r"<[^>]+>", " ", s or ""))

def canonical_product_name(value: str) -> str:
    t = clean_text(value).lower()
    for token in ["geforce", "radeon", "graphics", "graphic", "series", "desktop", "(tm)", "(r)", "processor"]:
        t = t.replace(token, "")
    return clean_text(t)

def danawa_url_category_id(url: str) -> str:
    try:
        parts = urlsplit(url or "")
    except Exception:
        return ""
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key.lower() == "cate" and value:
            return value
    return ""

def danawa_url_category_matches(part_type: str, url: str) -> bool:
    ctype = clean_text(part_type).lower()
    if ctype == "gpu":
        cate = danawa_url_category_id(url)
        return cate in GPU_DANAWA_CATEGORY_IDS if cate else False
    if ctype in {"storage", "ssd"}:
        cate = danawa_url_category_id(url)
        return cate in STORAGE_DANAWA_CATEGORY_IDS if cate else True
    return True

def reference_price_for_part(part_type: str, query: str) -> int:
    if clean_text(part_type).lower() != "gpu":
        return 0
    key = clean_text(query).lower()
    if key in PRICE_HINTS:
        return PRICE_HINTS[key]
    q_tokens = set(canonical_product_name(key).split())
    best_name = ""
    best_score = 0.0
    for name in PRICE_HINTS:
        n_tokens = set(canonical_product_name(name).split())
        inter = len(q_tokens & n_tokens)
        score = inter / max(1, len(q_tokens | n_tokens))
        if score > best_score:
            best_name = name
            best_score = score
    return PRICE_HINTS.get(best_name, 0) if best_score >= 0.4 else 0

def price_sane_for_part(part_type: str, price: int, query: str) -> bool:
    if price <= 0:
        return False
    ctype = clean_text(part_type).lower()
    reference = reference_price_for_part(part_type, query)
    if reference <= 0:
        return price >= (80000 if ctype == "gpu" else 1000)
    if ctype == "gpu":
        return max(70000, int(reference * 0.45)) <= price <= int(reference * 1.85)
    return price >= 1000

def danawa_category_matches(part_type: str, category: str) -> bool:
    ctype = clean_text(part_type).lower()
    label = clean_text(category).lower()
    if not ctype or not label:
        return False if ctype == "gpu" else True
    expected = {
        "gpu": ("그래픽", "vga"),
        "cpu": ("cpu", "프로세서"),
        "ram": ("ram", "메모리"),
        "memory": ("ram", "메모리"),
        "storage": ("ssd", "hdd", "저장", "스토리지"),
        "ssd": ("ssd", "저장", "스토리지"),
        "psu": ("파워", "power"),
        "mb": ("메인보드", "mainboard", "motherboard"),
        "motherboard": ("메인보드", "mainboard", "motherboard"),
    }.get(ctype)
    return True if not expected else any(token in label for token in expected)

def danawa_query_for_part(query: str, part_type: str) -> str:
    q = clean_text(query)
    ctype = clean_text(part_type).lower()
    suffix = {
        "gpu": "그래픽카드",
        "ram": "메모리",
        "memory": "메모리",
        "storage": "SSD",
        "ssd": "SSD",
        "psu": "파워",
        "mb": "메인보드",
        "motherboard": "메인보드",
    }.get(ctype, "")
    if suffix and suffix.lower() not in q.lower():
        return f"{q} {suffix}"
    return q

def danawa_name_rejected(part_type: str, product_name: str, category: str = "") -> bool:
    ctype = clean_text(part_type).lower()
    name = clean_text(product_name).lower()
    label = clean_text(category).lower()
    if ctype == "gpu":
        if not name:
            return True
        reject_tokens = [
            "조립pc", "조립 pc", "완본체", "본체", "데스크탑", "데스크톱", "컴퓨터", "pc방",
            "노트북", "워크스테이션", "서버", "미니pc", "베어본", "egpu",
            "쿨러", "cooler", "cooling", "팬", "fan", "수냉", "워터블럭", "water block",
            "백플레이트", "backplate", "라디에이터", "radiator", "방열판", "히트싱크",
            "지지대", "거치대", "브라켓", "라이저", "riser", "케이블", "cable", "가방", "케이스",
            "섀시", "샤시", "chassis", "no hardware",
            "교체품", "부품용", "중고", "리퍼", "refurb", "채굴", "mining",
        ]
        compact = re.sub(r"\s+", "", name)
        return any(token in name or token.replace(" ", "") in compact for token in reject_tokens)
    if label and danawa_category_matches(part_type, label):
        return False
    if ctype in {"ram", "memory"}:
        return any(token in name for token in ["메인보드", "메인 보드", " cpu ", "키트", "kit", "h610m", "b550", "b650", "b760"])
    if ctype in {"storage", "ssd"}:
        reject_tokens = [
            "노트북", "게이밍 pc", "데스크탑", "컴퓨터 본체", "외장", "portable",
            "케이스", "enclosure", "도킹", "dock", "허브", "hub", "usb", "sd카드", "메모리카드",
        ]
        return any(token in name for token in reject_tokens)
    if ctype == "psu":
        return any(token in name for token in ["케이블", "연장", "변환"])
    return False

def category_from_danawa_block(block: str) -> str:
    m = re.search(r"id=[\"']productItem_categoryInfo_[^\"']+[\"'][^>]+value=[\"']([^\"']+)[\"']", block, re.I)
    return clean_text(m.group(1)) if m else ""

def product_model_tokens(value: str) -> set:
    t = re.sub(r"\s+", " ", value.lower())
    patterns = [
        r"\b(?:rtx|gtx|rx)\s*\d{3,5}\b",
        r"\bultra\s*[3579]?\s*\d{3}[a-z]*\b",
        r"\bi[3579][-\s]?\d{4,5}[a-z]*\b",
        r"\b(?:a|b|h|x|z)\d{3,4}\b",
        r"\bddr[45]\b",
        r"\b\d+\s*(?:gb|tb|w)\b",
        r"\b\d{4,5}x3d\b",
        r"\b\d{3}[a-z]\b",
        r"\b\d{4,5}[a-z]{0,3}\b",
    ]
    out = []
    for pattern in patterns:
        out.extend(re.findall(pattern, t))
    return {re.sub(r"[^a-z0-9]", "", x) for x in out}

def product_variant_tokens(value: str) -> set:
    words = set(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())
    return words & {"super", "ti", "xtx", "xt", "gre", "x3d", "kf", "f", "k", "u"}

def compatible_product_name(query: str, product_name: str) -> bool:
    q_models = product_model_tokens(query)
    p_models = product_model_tokens(product_name)
    if q_models and p_models and not (q_models & p_models):
        return False
    if q_models and p_models and product_variant_tokens(query) != product_variant_tokens(product_name):
        return False
    return True

def danawa_candidate_valid(part_type: str, query: str, product_name: str,
                           category: str, url: str, price: int) -> bool:
    ctype = clean_text(part_type).lower()
    if ctype == "gpu":
        if not (danawa_category_matches(part_type, category) or danawa_url_category_matches(part_type, url)):
            return False
        if danawa_name_rejected(part_type, product_name, category):
            return False
        if query and product_name and not compatible_product_name(query, product_name):
            return False
        return price_sane_for_part(part_type, price, query)

    if category and not danawa_category_matches(part_type, category):
        return False
    if ctype in {"storage", "ssd"} and not danawa_url_category_matches(part_type, url):
        return False
    if danawa_name_rejected(part_type, product_name, category):
        return False
    if ctype in {"storage", "ssd"} and "nvme" in clean_text(query).lower():
        if not any(token in clean_text(product_name).lower() for token in ["nvme", "m.2", "m2"]):
            return False
    if query and product_name and not compatible_product_name(query, product_name):
        return False
    return price_sane_for_part(part_type, price, query)


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
    return (href_match.group(1) if href_match else ""), clean_text(img_match.group(1) if img_match else "")


def parse_danawa_top_product_regex(
    html: str,
    search_url: str,
    query: str = "",
    part_type: str = "",
) -> Optional[Dict[str, object]]:
    candidates: List[Dict[str, object]] = []
    for block in danawa_candidate_blocks(html):
        if not re.search(r"prod_item|prod_main_info|price_sect|prod_pricelist|min_price_", block, re.I):
            continue
        category = category_from_danawa_block(block)
        price = price_from_danawa_block(block)
        if not price:
            continue
        href, product_name = first_anchor_from_block(block)
        url = urljoin(search_url, href) if href else search_url
        if not danawa_candidate_valid(part_type, query, product_name, category, url, price):
            continue
        candidates.append({
            "name": product_name,
            "price": price,
            "url": url,
            "category": category,
        })

    if candidates:
        candidates.sort(key=lambda item: (int(item.get("price") or 0), len(clean_text(str(item.get("name") or "")))))
        return candidates[0]

    if not part_type:
        text = strip_html(html)
        m = re.search(r"(\d[\d,]{4,})\s*원", text)
        if m:
            return {"name": "", "price": parse_price_value(m.group(1)), "url": search_url}
    return None

def parse_danawa_top_product(
    html: str,
    search_url: str,
    query: str = "",
    part_type: str = "",
) -> Optional[Dict[str, object]]:
    if BeautifulSoup is None:
        return parse_danawa_top_product_regex(html, search_url, query, part_type)

    soup = BeautifulSoup(html, "html.parser")
    product_nodes = soup.select("li.prod_item, .main_prodlist li, .prod_main_info")
    if not product_nodes:
        product_nodes = soup.select(".prod_list .prod_item, .prod_list li")

    candidates: List[Dict[str, object]] = []
    for node in product_nodes:
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
        link_el = node.select_one(".prod_name a, a[name='productName'], a")
        href = link_el.get("href") if link_el else ""
        product_name = clean_text(link_el.get_text(" ")) if link_el else ""
        if not product_name:
            img_el = node.select_one("img[alt]")
            product_name = clean_text(img_el.get("alt")) if img_el else ""
        url = urljoin(search_url, href) if href else search_url
        if not danawa_candidate_valid(part_type, query, product_name, category, url, price):
            continue
        candidates.append({
            "name": product_name,
            "price": price,
            "url": url,
            "category": clean_text(category),
        })

    if candidates:
        candidates.sort(key=lambda item: (int(item.get("price") or 0), len(clean_text(str(item.get("name") or "")))))
        return candidates[0]

    price_el = soup.select_one(".price_sect strong, .prod_pricelist strong, .prod_price strong")
    price = parse_price_value(price_el.get_text(" ")) if price_el else None
    if price:
        link_el = soup.select_one(".prod_name a, a[name='productName'], a")
        href = link_el.get("href") if link_el else ""
        product_name = clean_text(link_el.get_text(" ")) if link_el else ""
        url = urljoin(search_url, href) if href else search_url
        if (not part_type and (not query or not product_name or compatible_product_name(query, product_name))) or danawa_candidate_valid(part_type, query, product_name, "", url, price):
            return {
                "name": product_name,
                "price": price,
                "url": url,
            }

    if not part_type:
        m = re.search(r"(\d[\d,]{4,})\s*원", soup.get_text(" "))
        if m:
            return {"name": "", "price": parse_price_value(m.group(1)), "url": search_url}
    return parse_danawa_top_product_regex(html, search_url, query, part_type)

def parse_danawa_price(html: str, search_url: str) -> Tuple[Optional[int], str]:
    product = parse_danawa_top_product(html, search_url)
    if not product:
        return None, search_url
    return product.get("price"), str(product.get("url") or search_url)

# ─────────────────────────────────────────────────────────────
# Site-specific parsers
# ─────────────────────────────────────────────────────────────
@dataclass
class BenchmarkRow:
    component_name: str
    component_type: str
    game: str
    resolution: str
    setting: str
    avg_fps: Optional[float]
    low1_fps: Optional[float]
    source_url: str = ""
    extra: dict = field(default_factory=dict)

def html_tables_regex(html: str) -> List[Tuple[List[str], List[List[str]]]]:
    """Small dependency-free table extractor used when BeautifulSoup is unavailable."""
    tables: List[Tuple[List[str], List[List[str]]]] = []
    for table in re.findall(r"<table\b[^>]*>(.*?)</table>", html or "", re.I | re.S):
        parsed_rows: List[List[str]] = []
        for tr in re.findall(r"<tr\b[^>]*>(.*?)</tr>", table, re.I | re.S):
            cells = [
                strip_html(cell)
                for cell in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr, re.I | re.S)
            ]
            if cells:
                parsed_rows.append(cells)
        if parsed_rows:
            tables.append(([h.lower() for h in parsed_rows[0]], parsed_rows[1:]))
    return tables


def parse_tpu_gpu_review(html: str, source_url: str, component_name: str) -> List[BenchmarkRow]:
    """
    TechPowerUp GPU review page.
    Benchmarks are shown in HTML tables with columns:
      Resolution | Game | Low Quality | Medium Quality | High Quality | Average FPS | 1% Low
    Table structure varies by review – this handles the common patterns.
    """
    if BeautifulSoup is None:
        return parse_generic_benchmark_table(html, source_url, component_name)

    soup = BeautifulSoup(html, "html.parser")
    rows: List[BenchmarkRow] = []

    for table in soup.find_all("table"):
        headers = [clean_text(th.get_text(" ")).lower() for th in table.find_all("th")]
        if not headers:
            continue

        # Identify columns
        col: Dict[str, int] = {}
        for i, h in enumerate(headers):
            if "game"  in h or "title" in h:           col["game"]   = i
            if "resol" in h or "1080"  in h or "1440" in h: col["res"] = i
            if "setting" in h or "quality" in h:        col["set"]    = i
            if "average" in h or "avg" in h:            col["avg"]    = i
            if "1%" in h or "min" in h or "low" in h:  col["low1"]   = i

        if "avg" not in col:
            continue

        for tr in table.find_all("tr")[1:]:
            cells = [clean_text(td.get_text(" ")) for td in tr.find_all(["td", "th"])]
            if len(cells) <= col.get("avg", 99):
                continue
            game_raw  = cells[col["game"]]  if "game" in col and col["game"] < len(cells) else "Unknown"
            res_raw   = cells[col["res"]]   if "res"  in col and col["res"]  < len(cells) else "1080p"
            set_raw   = cells[col["set"]]   if "set"  in col and col["set"]  < len(cells) else "High"
            avg_fps   = to_float(cells[col["avg"]])
            low1_fps  = to_float(cells[col["low1"]]) if "low1" in col and col["low1"] < len(cells) else None

            rows.append(BenchmarkRow(
                component_name=normalize_gpu_name(component_name),
                component_type="GPU",
                game=clean_text(game_raw),
                resolution=normalize_resolution(res_raw),
                setting=normalize_setting(set_raw),
                avg_fps=avg_fps,
                low1_fps=low1_fps,
                source_url=source_url,
            ))
    return rows


def parse_tomshw_gpu_hierarchy(html: str, source_url: str) -> List[BenchmarkRow]:
    """
    Tom's Hardware GPU hierarchy page.
    Extracts the public rasterization table:
      GPU | 1080p Medium | 1080p Ultra | 1440p Ultra | 4K Ultra
    The article reports geometric-mean FPS in parentheses, e.g. "67.4% (133.2)".
    """
    if BeautifulSoup is None:
        for headers, body_rows in html_tables_regex(html):
            if not any("gpu" in h or "card" in h for h in headers):
                continue

            name_col = next((i for i, h in enumerate(headers) if "graphics card" in h or "gpu" in h or h == "card"), 0)
            metric_cols: List[Tuple[int, str, str]] = []
            for i, h in enumerate(headers):
                if "1080p" in h and "medium" in h:
                    metric_cols.append((i, "1080", "medium"))
                elif "1080p" in h and ("ultra" in h or "high" in h):
                    metric_cols.append((i, "1080", "high"))
                elif "1440p" in h and ("ultra" in h or "high" in h):
                    metric_cols.append((i, "1440", "high"))
                elif ("4k" in h or "2160" in h) and ("ultra" in h or "high" in h):
                    metric_cols.append((i, "2160", "high"))

            if not metric_cols:
                continue

            rows: List[BenchmarkRow] = []
            for cells in body_rows:
                if len(cells) <= name_col:
                    continue
                name = normalize_gpu_name(cells[name_col])
                if not name:
                    continue
                for col_idx, resolution, setting in metric_cols:
                    if len(cells) <= col_idx:
                        continue
                    fps = fps_from_score_cell(cells[col_idx])
                    if fps is None:
                        continue
                    rows.append(BenchmarkRow(
                        component_name=name,
                        component_type="GPU",
                        game="average_games",
                        resolution=resolution,
                        setting=setting,
                        avg_fps=round(fps, 1),
                        low1_fps=None,
                        source_url=source_url,
                    ))
            if rows:
                return rows
        return []

    soup = BeautifulSoup(html, "html.parser")

    for table in soup.find_all("table"):
        headers = [clean_text(th.get_text(" ")).lower() for th in table.find_all("th")]
        if not any("gpu" in h or "card" in h for h in headers):
            continue

        name_col = next((i for i, h in enumerate(headers) if "graphics card" in h or "gpu" in h or h == "card"), 0)
        metric_cols: List[Tuple[int, str, str]] = []
        for i, h in enumerate(headers):
            if "1080p" in h and "medium" in h:
                metric_cols.append((i, "1080", "medium"))
            elif "1080p" in h and ("ultra" in h or "high" in h):
                metric_cols.append((i, "1080", "high"))
            elif "1440p" in h and ("ultra" in h or "high" in h):
                metric_cols.append((i, "1440", "high"))
            elif ("4k" in h or "2160" in h) and ("ultra" in h or "high" in h):
                metric_cols.append((i, "2160", "high"))

        if not metric_cols:
            continue

        rows: List[BenchmarkRow] = []
        for tr in table.find_all("tr")[1:]:
            cells = [clean_text(td.get_text(" ")) for td in tr.find_all(["td", "th"])]
            if len(cells) <= name_col:
                continue
            name = normalize_gpu_name(cells[name_col])
            if not name:
                continue
            for col_idx, resolution, setting in metric_cols:
                if len(cells) <= col_idx:
                    continue
                fps = fps_from_score_cell(cells[col_idx])
                if fps is None:
                    continue
                rows.append(BenchmarkRow(
                    component_name=name,
                    component_type="GPU",
                    game="average_games",
                    resolution=resolution,
                    setting=setting,
                    avg_fps=round(fps, 1),
                    low1_fps=None,
                    source_url=source_url,
                ))
        if rows:
            return rows
    return []


def parse_generic_benchmark_table(html: str, source_url: str, component_name: str) -> List[BenchmarkRow]:
    """
    Generic parser for benchmark pages with HTML tables.
    Looks for: Game | Resolution | Setting | Average FPS | 1% Low
    """
    if BeautifulSoup is None:
        rows: List[BenchmarkRow] = []
        for headers, body_rows in html_tables_regex(html):
            avg_idx  = next((i for i, h in enumerate(headers) if "average" in h or "avg" in h), None)
            low_idx  = next((i for i, h in enumerate(headers) if "1%" in h or "minimum" in h), None)
            game_idx = next((i for i, h in enumerate(headers) if "game" in h or "title" in h), None)
            res_idx  = next((i for i, h in enumerate(headers) if "resol" in h or "res" in h), None)
            set_idx  = next((i for i, h in enumerate(headers) if "setting" in h or "quality" in h or "preset" in h), None)

            if avg_idx is None:
                continue

            for cells in body_rows:
                if len(cells) <= avg_idx:
                    continue
                game = cells[game_idx] if game_idx is not None and game_idx < len(cells) else "Unknown"
                res_raw = cells[res_idx] if res_idx is not None and res_idx < len(cells) else "1080p"
                set_raw = cells[set_idx] if set_idx is not None and set_idx < len(cells) else "High"
                avg_fps = to_float(cells[avg_idx])
                low1_fps = to_float(cells[low_idx]) if low_idx is not None and low_idx < len(cells) else None

                rows.append(BenchmarkRow(
                    component_name=normalize_gpu_name(component_name),
                    component_type="GPU",
                    game=clean_text(game),
                    resolution=normalize_resolution(res_raw),
                    setting=normalize_setting(set_raw),
                    avg_fps=avg_fps,
                    low1_fps=low1_fps,
                    source_url=source_url,
                ))
        return rows

    soup = BeautifulSoup(html, "html.parser")
    rows: List[BenchmarkRow] = []

    for table in soup.find_all("table"):
        headers = [clean_text(th.get_text(" ")).lower() for th in table.find_all("th")]
        if not headers:
            continue

        avg_idx  = next((i for i, h in enumerate(headers) if "average" in h or "avg" in h), None)
        low_idx  = next((i for i, h in enumerate(headers) if "1%" in h or "minimum" in h), None)
        game_idx = next((i for i, h in enumerate(headers) if "game" in h or "title" in h), None)
        res_idx  = next((i for i, h in enumerate(headers) if "resol" in h or "res" in h), None)
        set_idx  = next((i for i, h in enumerate(headers) if "setting" in h or "quality" in h or "preset" in h), None)

        if avg_idx is None:
            continue

        for tr in table.find_all("tr")[1:]:
            cells = [clean_text(td.get_text(" ")) for td in tr.find_all(["td", "th"])]
            if len(cells) <= avg_idx:
                continue

            game     = cells[game_idx]  if game_idx is not None and game_idx < len(cells) else "Unknown"
            res_raw  = cells[res_idx]   if res_idx  is not None and res_idx  < len(cells) else "1080p"
            set_raw  = cells[set_idx]   if set_idx  is not None and set_idx  < len(cells) else "High"
            avg_fps  = to_float(cells[avg_idx])
            low1_fps = to_float(cells[low_idx]) if low_idx is not None and low_idx < len(cells) else None

            rows.append(BenchmarkRow(
                component_name=normalize_gpu_name(component_name),
                component_type="GPU",
                game=clean_text(game),
                resolution=normalize_resolution(res_raw),
                setting=normalize_setting(set_raw),
                avg_fps=avg_fps,
                low1_fps=low1_fps,
                source_url=source_url,
            ))
    return rows


# ─────────────────────────────────────────────────────────────
# CSV import (manual benchmark data entry)
# ─────────────────────────────────────────────────────────────
def import_csv(path: Path, db_path: Path = DB_PATH) -> int:
    """
    Import benchmarks from a CSV file.
    Required columns: component_name, component_type, game, resolution, setting, avg_fps
    Optional columns: low1_fps, source_url

    Example CSV:
      component_name,component_type,game,resolution,setting,avg_fps,low1_fps,source_url
      "NVIDIA RTX 4090",GPU,valorant,1080,low,540,480,https://...
    """
    conn = sqlite3.connect(str(db_path))
    count = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name   = normalize_gpu_name(row.get("component_name", "").strip())
            ctype  = row.get("component_type", "GPU").strip().upper()
            game   = clean_text(row.get("game", ""))
            res    = normalize_resolution(row.get("resolution", "1080p"))
            sett   = normalize_setting(row.get("setting", "high"))
            avg    = to_float(row.get("avg_fps", "") or "")
            low1   = to_float(row.get("low1_fps", "") or "")
            url    = row.get("source_url", "csv_import").strip()

            if not name or not game or avg is None:
                continue

            cid = upsert_component(conn, ctype, name)
            upsert_benchmark(conn, cid, game, res, sett, avg, low1, url)
            count += 1

    conn.commit()
    conn.close()
    print(f"[import_csv] Imported {count} rows from {path}")
    return count


# ─────────────────────────────────────────────────────────────
# Main crawl loop
# ─────────────────────────────────────────────────────────────
def crawl_url(url: str, component_name: str, component_type: str,
              conn: sqlite3.Connection, site_tag: str = "generic") -> int:
    print(f"  [fetch] {url}")
    html = fetch_html(url)

    if site_tag == "tpu":
        bench_rows = parse_tpu_gpu_review(html, url, component_name)
    elif site_tag == "tomshw":
        bench_rows = parse_tomshw_gpu_hierarchy(html, url)
    else:
        bench_rows = parse_generic_benchmark_table(html, url, component_name)

    if not bench_rows:
        print(f"  [warn] No benchmark rows parsed from {url}")
        return 0

    if site_tag == "tomshw":
        conn.execute(
            "DELETE FROM benchmarks WHERE source_url=? AND game=?",
            (url, "average_games"),
        )

    count = 0
    for br in bench_rows:
        cid = upsert_component(conn, br.component_type, br.component_name)
        upsert_benchmark(conn, cid, br.game, br.resolution, br.setting,
                         br.avg_fps, br.low1_fps, br.source_url)
        count += 1

    conn.commit()
    print(f"  [ok] Stored {count} benchmark rows")
    return count


def crawl_all(db_path: Path = DB_PATH) -> None:
    if not SOURCE_URLS:
        print("[warn] SOURCE_URLS is empty – no pages to crawl.")
        print("       Add real benchmark page URLs to SOURCE_URLS in crawl_data.py,")
        print("       or use --import-csv to load data from a CSV file.")
        return

    init_db(db_path)
    conn = sqlite3.connect(str(db_path))
    total = 0

    for site_tag, url, component_name, component_type in SOURCE_URLS:
        print(f"[crawl] {component_name} ({site_tag}) ← {url}")
        try:
            total += crawl_url(url, component_name, component_type, conn, site_tag)
        except Exception as e:
            print(f"  [error] {e}")
        time.sleep(2)

    conn.close()
    print(f"\n[done] Total benchmark rows stored: {total}")


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
def crawl_danawa_price(conn: sqlite3.Connection, ctype: str, name: str) -> bool:
    search_url = danawa_search_url(danawa_query_for_part(name, ctype))
    html = fetch_html(search_url)
    product = parse_danawa_top_product(html, search_url, name, ctype)
    price = int(product.get("price")) if product and product.get("price") else None
    product_url = str(product.get("url")) if product and product.get("url") else search_url
    if not price:
        print(f"  [warn] price not found: {name}")
        return False
    cid = upsert_component(conn, ctype, name)
    upsert_price(conn, cid, "Danawa", price, product_url or search_url)
    conn.commit()
    product_name = str(product.get("name") or name) if product else name
    print(f"  [ok] {name}: {price:,} KRW ({product_name})")
    return True

def crawl_prices(db_path: Path = DB_PATH, limit: int = 0, delay: float = 1.0) -> None:
    init_db(db_path)
    conn = sqlite3.connect(str(db_path))
    targets = PRICE_TARGETS[:limit] if limit and limit > 0 else PRICE_TARGETS
    stored = 0
    for ctype, name in targets:
        print(f"[price] {name}")
        try:
            if crawl_danawa_price(conn, ctype, name):
                stored += 1
        except Exception as e:
            print(f"  [error] {e}")
        time.sleep(max(0.0, delay))
    conn.close()
    print(f"\n[done] Price rows stored: {stored}/{len(targets)}")

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="PC Benchmark Crawler / CSV Importer")
    p.add_argument("--db", default=str(DB_PATH), help="SQLite DB path")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("crawl", help="Crawl all SOURCE_URLS")

    price = sub.add_parser("crawl-prices", help="Crawl Danawa prices for catalog parts")
    price.add_argument("--limit", type=int, default=0, help="Maximum number of parts to crawl")
    price.add_argument("--delay", type=float, default=1.0, help="Delay between requests in seconds")

    imp = sub.add_parser("import-csv", help="Import benchmarks from a CSV file")
    imp.add_argument("csv_path", help="Path to CSV file")

    init = sub.add_parser("init-db", help="Initialise DB schema only")

    args = p.parse_args()
    db = Path(args.db)

    if args.cmd == "crawl":
        crawl_all(db)
    elif args.cmd == "crawl-prices":
        crawl_prices(db, limit=args.limit, delay=args.delay)
    elif args.cmd == "import-csv":
        init_db(db)
        import_csv(Path(args.csv_path), db)
    elif args.cmd == "init-db":
        init_db(db)
        print(f"DB initialised at {db}")
    else:
        p.print_help()
