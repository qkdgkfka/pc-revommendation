#!/usr/bin/env python3
"""Refresh the bundled fallback catalogue using actual retailer search pages."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server_fixed as server
from market_catalog import PART_TYPES, SNAPSHOT_PATH


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, default=5)
    parser.add_argument("--source", choices=("all", "danawa", "compuzone"), default="danawa")
    args = parser.parse_args()
    products = {kind: {} for kind in PART_TYPES}
    if SNAPSHOT_PATH.exists():
        previous = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        for kind, items in previous.get("products", {}).items():
            if kind in products:
                products[kind].update({item["id"]: item for item in items})

    def fetch(kind, page):
        if hasattr(server, "market_products_response"):
            return server.market_products_response(kind, "", page, 40, True, args.source)
        url = server.danawa_browse_url(server.DANAWA_BROWSE_DEFAULT_QUERIES[kind], page, 40)
        request = server.Request(url, headers=server.DANAWA_HEADERS)
        with server.urlopen(request, timeout=10) as response:
            html = response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
        return {"items": server.parse_danawa_browse_products(html, url, kind, 1000)}

    # Keep upstream traffic bounded; failures preserve the previous snapshot.
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending = {pool.submit(fetch, kind, page): (kind, page)
                   for kind in PART_TYPES for page in range(1, min(20, max(1, args.pages)) + 1)}
        for future in as_completed(pending):
            kind, page = pending[future]
            try:
                response = future.result()
                observed = datetime.now(timezone.utc).isoformat()
                for row in response.get("items", []):
                    if row.get("stale") or row.get("price_status") in {"stale", "estimated", "unavailable"}:
                        continue
                    row["part_type"] = kind
                    row.setdefault("price_checked_at", observed)
                    row.setdefault("source_url", row.get("url", ""))
                    products[kind][row["id"]] = row
                print(f"{kind} page {page}: {len(response.get('items', []))} products", flush=True)
            except Exception as error:
                print(f"{kind} page {page}: unavailable ({type(error).__name__})", flush=True)

    counts = {kind: len(items) for kind, items in products.items()}
    if not any(counts.values()):
        raise SystemExit("No retailer products were available; catalogue was not changed.")
    payload = {
        "schema_version": 1,
        "description": "Observed retail listings; prices expire after 24 hours and are rechecked at selection.",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
        "products": {kind: list(items.values()) for kind, items in products.items()},
    }
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = SNAPSHOT_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(SNAPSHOT_PATH)
    print(json.dumps(counts, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
