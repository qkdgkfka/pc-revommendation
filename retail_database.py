"""Verified retailer SKUs and immutable price observations in the existing SQLite DB."""
from contextlib import closing
import json
import sqlite3
from pathlib import Path
from threading import RLock
from urllib.parse import urlparse

_cache = {}
_lock = RLock()
_EMPTY = {}

def save_products(path, kind, items):
    accepted=[]
    for item in items:
        try:
            valid=(item.get("id") and item.get("name") and item.get("price_checked_at")
                   and item.get("image_checked_at") and item.get("image_url")
                   and 1000 <= float(item.get("price",0)) <= 20_000_000
                   and urlparse(item.get("url","")).hostname in
                       {"prod.danawa.com","www.compuzone.co.kr","compuzone.co.kr"})
        except (ValueError, TypeError):
            valid=False
        if valid:
            accepted.append(item)
    if not accepted:
        return 0
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with _lock, closing(sqlite3.connect(path,timeout=20)) as conn, conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS retail_products (
                part_type TEXT NOT NULL, sku TEXT NOT NULL, name TEXT NOT NULL,
                price INTEGER NOT NULL, product_url TEXT NOT NULL, image_url TEXT NOT NULL,
                price_checked_at TEXT NOT NULL, image_checked_at TEXT NOT NULL,
                metadata TEXT NOT NULL, PRIMARY KEY(part_type,sku));
            CREATE TABLE IF NOT EXISTS retail_price_history (
                part_type TEXT NOT NULL, sku TEXT NOT NULL, price INTEGER NOT NULL,
                checked_at TEXT NOT NULL, product_url TEXT NOT NULL,
                PRIMARY KEY(part_type,sku,checked_at));
        """)
        for item in accepted:
            checked=item["price_checked_at"]
            conn.execute("""INSERT INTO retail_products VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(part_type,sku) DO UPDATE SET name=excluded.name,
                price=excluded.price,product_url=excluded.product_url,image_url=excluded.image_url,
                price_checked_at=excluded.price_checked_at,image_checked_at=excluded.image_checked_at,
                metadata=excluded.metadata
                WHERE julianday(excluded.price_checked_at)>=julianday(retail_products.price_checked_at)""",
                (kind,item["id"],item["name"],int(item["price"]),item["url"],item["image_url"],
                 checked,item["image_checked_at"],json.dumps(item,ensure_ascii=False)))
            conn.execute("INSERT OR IGNORE INTO retail_price_history VALUES (?,?,?,?,?)",
                         (kind,item["id"],int(item["price"]),checked,item["url"]))
    return len(accepted)

def read_products(path):
    path=Path(path)
    if not path.exists():
        return _EMPTY
    with _lock:
        stat=path.stat()
        stamp=(stat.st_mtime_ns,stat.st_size)
        if path in _cache and _cache[path][0]==stamp:
            return _cache[path][1]
        with closing(sqlite3.connect(path.as_uri()+"?mode=ro",uri=True,timeout=20)) as conn:
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='retail_products'").fetchone():
                products=_EMPTY
            else:
                products={}
                for kind,metadata in conn.execute("SELECT part_type,metadata FROM retail_products"):
                    products.setdefault(kind,[]).append(json.loads(metadata))
        _cache[path]=(stamp,products)
        return products
