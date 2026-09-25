"""Persist observed retail products without presenting saved prices as live quotes."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from threading import RLock
from urllib.parse import urlparse
from retail_database import read_products


DATA_DIR = Path(__file__).resolve().parent / "data"
SNAPSHOT_PATH = DATA_DIR / "product_catalog.json"
CACHE_PATH = DATA_DIR / "market_cache.json"
PART_TYPES = ("cpu", "gpu", "mb", "ram", "storage", "hdd", "psu", "case", "software")
MAX_PRICE_AGE_HOURS = 24
_lock = RLock()
_file_cache = {}
_rows_cache = {}
_EMPTY_CATALOG = {}


def _read_catalog(path):
    try:
        stat = path.stat()
        stamp = (stat.st_mtime_ns, stat.st_size, stat.st_ino)
        if path in _file_cache and _file_cache[path][0] == stamp:
            return _file_cache[path][1]
        payload = json.loads(path.read_text(encoding="utf-8"))
        products = payload.get("products", {})
        if not isinstance(products, dict):
            return _EMPTY_CATALOG
        _file_cache[path] = (stamp, products)
        return products
    except (OSError, ValueError, TypeError):
        return _EMPTY_CATALOG


def _verified_retail_row(item):
    if not isinstance(item, dict) or not item.get("id") or not item.get("name"):
        return False
    try:
        host = (urlparse(item.get("url", "")).hostname or "").lower()
        price = float(item.get("price", 0))
        checked = item.get("price_checked_at") or item.get("scraped_at")
        return bool(checked and 1000 <= price <= 20_000_000 and host in {
            "prod.danawa.com", "www.compuzone.co.kr", "compuzone.co.kr",
        })
    except (ValueError, TypeError):
        return False


def _saved_rows(part_type):
    """Reuse validation/merging until either source snapshot is replaced.

    Called under _lock. The source dictionaries are retained for identity checks;
    callers receive fresh row copies and price age is calculated separately.
    """
    snapshot = _read_catalog(SNAPSHOT_PATH)
    runtime = _read_catalog(CACHE_PATH)
    database = read_products(DATA_DIR / "pc.db")
    cached = _rows_cache.get(part_type)
    if cached and cached[0] is snapshot and cached[1] is runtime and cached[2] is database:
        return cached[3]
    combined = {}
    for source in (snapshot, runtime, database):
        for item in source.get(part_type, []):
            if _verified_retail_row(item):
                previous = combined.get(item["id"], {})
                checked = str(item.get("price_checked_at") or item.get("scraped_at") or "")
                old_checked = str(previous.get("price_checked_at") or previous.get("scraped_at") or "")
                if checked >= old_checked:
                    combined[item["id"]] = dict(item)
                elif item.get("image_url") == previous.get("image_url") and item.get("image_checked_at"):
                    previous["image_checked_at"] = item["image_checked_at"]
    rows = tuple(combined.values())
    _rows_cache[part_type] = (snapshot, runtime, database, rows)
    return rows


def saved_products(part_type, now=None):
    """Return timestamped fallback choices; a saved quote is never labelled live."""
    if part_type not in PART_TYPES:
        return []
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    with _lock:
        rows = _saved_rows(part_type)
    output = []
    for saved in rows:
        item = dict(saved)
        checked = str(item.get("price_checked_at") or item.get("scraped_at"))
        try:
            observed = datetime.fromisoformat(checked.replace("Z", "+00:00"))
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
            age = (current - observed).total_seconds()
            fresh = 0 <= age < MAX_PRICE_AGE_HOURS * 3600
        except ValueError:
            fresh = False
        provider = "compuzone" if "compuzone" in item["url"].lower() else "danawa"
        item.update(
            part_type=part_type,
            price_checked_at=checked,
            price_source=provider + "_snapshot",
            price_status="cached" if fresh else "stale",
            price_verified=fresh,
            price_stale=not fresh,
            stale=not fresh,
            source_url=item.get("source_url") or item["url"],
        )
        output.append(item)
    return output


def remember_products(part_type, items):
    """Save successful fetches atomically. Network failure never erases choices."""
    if part_type not in PART_TYPES:
        return
    accepted = [dict(item) for item in items if _verified_retail_row(item)]
    if not accepted:
        return
    with _lock:
        products = dict(_read_catalog(CACHE_PATH))
        indexed = {item["id"]: item for item in products.get(part_type, [])}
        indexed.update({item["id"]: item for item in accepted})
        products[part_type] = list(indexed.values())[-1200:]
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        temporary = CACHE_PATH.with_suffix(".tmp")
        try:
            temporary.write_text(json.dumps({
                "schema_version": 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "products": products,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(CACHE_PATH)
        except OSError:
            # A read-only installation can still browse live results.
            pass
