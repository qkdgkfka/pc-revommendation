"""SQLite snapshots and observed price storage."""
from __future__ import annotations

from urllib.parse import urlencode, urlparse
from datetime import datetime, timedelta
import json
import re
import sqlite3
from threading import RLock
from product_metadata import (
    canonical_name,
    clean_visible_text,
    compatible_price_name,
    normalize_gpu_maker_prefs,
    normalize_product_url,
    normalize_text,
    safe_float,
    safe_int,
)
from typing import Any, Dict, Iterable, List, Optional
from . import runtime as state
from . import retail
from . import utils
from .revisions import database_stamp

_db_lock = RLock()


def table_columns(conn: sqlite3.Connection, table: str) -> set:
    try:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()

def init_db_schema() -> None:
    state.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(state.DB_PATH))
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
    if state.CONFIG_PATH.exists():
        try:
            state.HYBRID_CONFIG = json.loads(state.CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            state.HYBRID_CONFIG = {}
    else:
        state.HYBRID_CONFIG = {}

def _ensure_db_connection(create: bool = False) -> Optional[sqlite3.Connection]:
    if create:
        init_db_schema()
    if not state.DB_PATH.exists():
        return None
    conn = (sqlite3.connect(str(state.DB_PATH)) if create else
            sqlite3.connect(state.DB_PATH.resolve().as_uri() + '?mode=ro', uri=True))
    conn.row_factory = sqlite3.Row
    if not create:
        conn.execute('PRAGMA query_only=ON')
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
        (ctype, clean_name, utils.vendor_normalize(clean_name) if ctype in {"CPU", "GPU"} else ""),
    )
    row = cur.execute("SELECT id FROM components WHERE type=? AND name=?", (ctype, clean_name)).fetchone()
    conn.commit()
    return int(row["id"] if isinstance(row, sqlite3.Row) else row[0])

def insert_price(conn: sqlite3.Connection, component_id: int, price: int, url: str, shop: str = "Danawa", checked_at: Optional[str] = None) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO prices(component_id, shop, currency, price, url, scraped_at)
        VALUES (?,?,?,?,?,?)
        """,
        (component_id, shop, "KRW", int(price), url, checked_at or datetime.utcnow().isoformat(timespec="seconds") + "Z"),
    )
    conn.commit()

def price_is_fresh(scraped_at: Any, max_age_hours: int = state.DANAWA_PRICE_MAX_AGE_HOURS) -> bool:
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
        and price_is_fresh(part.get("price_checked_at") or part.get("scraped_at") or part.get("checked_at"))
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
    with _db_lock:
        revision = database_stamp()
        _load_db_cache()
        # A concurrent replacement stays detectable on the next read.
        state.DB_CACHE['_file_revision'] = revision
        state.DB_CACHE['_generation'] = state.DB_CACHE.get('_generation', 0) + 1


def _load_db_cache() -> None:
    state.BENCHMARK_LOOKUP_CACHE.clear()
    conn = _ensure_db_connection()
    if conn is None:
        state.DB_CACHE.update({
            "loaded": False,
            "components": [],
            "prices_by_name": {},
            "prices_by_url": {},
            "benchmarks_by_name": {},
            "summary": {},
        })
        return

    # All tables belong to one SQLite read snapshot, including concurrent WAL writes.
    conn.execute('BEGIN')
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
            res_key = utils.resolution_key(r["resolution"])
            setting = normalize_text(r["setting"])
            item = dict(r)
            item["avg_fps"] = safe_float(item.get("avg_fps"))
            item["low1_fps"] = safe_float(item.get("low1_fps"))
            benchmarks_by_name.setdefault(name_key, {}).setdefault(game_key, []).append(
                {**item, "resolution": res_key, "setting": setting}
            )
    except Exception:
        benchmarks_by_name = {}

    state.DB_CACHE.update({
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
    stamp = database_stamp()
    if state.DB_CACHE.get('_file_revision') != stamp:
        with _db_lock:
            if state.DB_CACHE.get('_file_revision') != stamp:
                load_db_cache()

def db_lookup_price_info(part: Dict[str, Any], part_type: str) -> Optional[Dict[str, Any]]:
    ensure_db_cache_loaded()
    part_name = part.get("name")
    part_type_key = normalize_text(part_type)
    part_url = normalize_product_url(part.get("url") or part.get("shop_url") or part.get("product_url") or part.get("source_url"))
    catalog_price = safe_int(part.get("base_price"), 0) or safe_int(part.get("price"), 0)

    # 1) Prefer an exact product URL match when the crawler captured one.
    if part_url:
        url_rows = state.DB_CACHE.get("prices_by_url", {}) or {}
        row = url_rows.get(part_url)
        if row:
            try:
                price = int(row.get("price"))
            except Exception:
                price = 0
            if (
                price > 0
                and (not row.get("type") or normalize_text(row.get("type")) == part_type_key)
                and retail.retail_quote_valid(part_type_key, part_name, row)
                and str(row.get("currency") or "KRW").upper() == "KRW"
                and market_product_url(row.get("url") or part_url)
                and not retail.danawa_url_rejected(part_type, row.get("url") or part_url)
            ):
                return {
                    "price": price,
                    "shop": row.get("shop") or "Danawa",
                    "url": row.get("url") or part.get("url") or retail.danawa_search_url(part_name),
                    "currency": row.get("currency") or "KRW",
                    "scraped_at": row.get("scraped_at"),
                    "stale": not price_is_fresh(row.get("scraped_at")),
                    "matched_by": "url_exact",
                    "price_source": "db_url_exact",
                    "name": row.get("name"),
                    "type": row.get("type"),
                }

    # 2) Fallback to best name match.
    rows = state.DB_CACHE.get("prices_by_name", {}) or {}
    key = canonical_name(part_name)
    type_filtered = [
        k for k, row in rows.items()
        if (not row.get("type") or normalize_text(row.get("type")) == part_type_key)
        and retail.retail_quote_valid(part_type_key, part_name, row)
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

    if not retail.retail_quote_valid(part_type_key, part_name, row):
        return None

    return {
        "price": price,
        "shop": row.get("shop") or "Danawa",
        "url": row.get("url") or part.get("url") or retail.danawa_search_url(part_name),
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
    checked_at = live.get("price_checked_at") or live.get("scraped_at") or datetime.utcnow().isoformat(timespec="seconds") + "Z"
    conn = _ensure_db_connection(create=True)
    if conn is not None:
        try:
            cid = upsert_component(conn, part_type, component_name)
            insert_price(conn, cid, safe_int(live.get("price"), 0), live.get("url") or "", shop=shop, checked_at=checked_at)
        finally:
            conn.close()
        load_db_cache()
    return {
        "price": safe_int(live.get("price"), 0),
        "shop": shop,
        "url": live.get("url") or retail.danawa_search_url(component_name),
        "image_url": live.get("image_url") or part.get("image_url") or part_image_endpoint({"name": component_name}, part_type),
        "currency": "KRW",
        "scraped_at": checked_at,
        "stale": False,
        "verified": True,
        "price_status": live.get("price_status") or "verified",
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
        live = retail.fetch_market_top_product(
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
