"""Read-only dependency stamps and precise price freshness cache expiry."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import time

from . import runtime as state


def file_stamp(path):
    path = Path(path)
    try:
        stat = path.stat()
        return (str(path.resolve()), stat.st_mtime_ns, stat.st_size, stat.st_ino)
    except OSError:
        return (str(path.absolute()), None)


def database_stamp():
    return tuple(file_stamp(path) for path in (state.DB_PATH, str(state.DB_PATH) + '-wal'))


def data_revision():
    import market_catalog
    import product_import
    import game_benchmarks
    import game_database
    import rendering_calibration
    return (database_stamp(), state.DB_CACHE.get('_generation', 0),
            file_stamp(state.CONFIG_PATH),
            file_stamp(market_catalog.SNAPSHOT_PATH), file_stamp(market_catalog.CACHE_PATH),
            file_stamp(market_catalog.DATA_DIR / 'pc.db'),
            file_stamp(str(market_catalog.DATA_DIR / 'pc.db') + '-wal'),
            file_stamp(product_import.IMPORT_PATH), file_stamp(game_benchmarks.SNAPSHOT_PATH),
            file_stamp(game_database.DB_PATH), file_stamp(str(game_database.DB_PATH) + '-wal'),
            file_stamp(rendering_calibration.CALIBRATION_PATH))


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str,
                                     separators=(',', ':')).encode()).hexdigest()


def freshness_ttl(value, maximum=300):
    """Never retain a price status across its 24 hour boundary (or future date)."""
    current = time.time()
    expires = current + maximum
    seen = set()

    def visit(item):
        nonlocal expires
        if isinstance(item, dict):
            if id(item) in seen:
                return
            seen.add(id(item))
            checked = item.get('price_checked_at') or item.get('scraped_at') or item.get('checked_at')
            if checked:
                try:
                    observed = datetime.fromisoformat(str(checked).replace('Z', '+00:00'))
                    if observed.tzinfo is None:
                        observed = observed.replace(tzinfo=timezone.utc)
                    stamp = observed.timestamp()
                    boundary = stamp if stamp > current else stamp + state.DANAWA_PRICE_MAX_AGE_HOURS * 3600
                    if boundary > current:
                        expires = min(expires, boundary)
                except (ValueError, TypeError, OverflowError):
                    pass
            for child in item.values():
                visit(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                visit(child)

    visit(value)
    # Expire just before a boundary, avoiding inclusive/exclusive source policies.
    return max(0, expires - current - .001)
