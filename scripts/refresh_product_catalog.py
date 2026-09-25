#!/usr/bin/env python3
"""Collect actual retailer SKUs, verify photos, and persist them in data/pc.db."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server_fixed as server
from market_catalog import PART_TYPES, saved_products
from retail_database import save_products, read_products

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages",type=int,default=6)
    parser.add_argument("--start-page",type=int,default=1)
    parser.add_argument("--source",choices=("all","danawa","compuzone"),default="all")
    parser.add_argument("--types",default="cpu,gpu,mb,ram,storage,psu")
    parser.add_argument("--models",action="store_true",help="Also search reference CPU/GPU models")
    args=parser.parse_args()
    kinds=args.types.split(",")
    if any(k not in PART_TYPES for k in kinds):
        parser.error("Unknown component type")
    products={kind:{} for kind in kinds}
    before={kind:len(saved_products(kind)) for kind in kinds}
    tasks=[(kind,"",page) for kind in kinds for page in range(max(1,args.start_page),min(20,max(1,args.pages))+1)]
    if args.models:
        for kind in ("cpu","gpu"):
            if kind not in kinds: continue
            for part in server.CATALOGS[kind]:
                name=server.query_model_name(part["name"]) if kind=="gpu" else server.re.sub(r"\b(?:Intel|AMD|Core|Ryzen|[3579])\b"," ",part["name"],flags=server.re.I).strip()
                tasks.append((kind,name,1))
    failures=[]
    def fetch(task):
        kind,query,page=task
        time.sleep(0.25)
        return server.market_products_response(kind,query,page,40,True,args.source,persist=False)
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(fetch,task):task for task in tasks}
        for future in as_completed(futures):
            kind,query,page=futures[future]
            response=future.result()
            for row in response.get("items",[]):
                if row.get("price_status")!="verified" or not server.verified_price_info(row):
                    continue
                if not server.retail_quote_valid(kind,row["name"],row):
                    continue
                products[kind][row["id"]]=row
            if response.get("status")=="unavailable":
                failures.append({"type":kind,"query":query,"page":page})
            print(f"{kind} {query or 'category'} page {page}: {len(response.get('items',[]))}",flush=True)
    report={"before":before,"fetched":{},"verified":{},"photo_failed":{},"external_failures":failures}
    def verify(row):
        row=dict(row)
        url=server.retailer_image_url(row.get("image_url"))
        photo=server.fetch_product_image(url) if url else None
        if not photo:
            url=server.fetch_product_page_image(row["url"])
            photo=server.fetch_product_image(url) if url else None
        if not photo or photo[1] not in {"image/jpeg","image/png","image/webp","image/gif","image/avif"}:
            return None
        row.update(image_url=url,image_checked_at=datetime.now(timezone.utc).isoformat())
        return row
    for kind,rows in products.items():
        verified=[]
        with ThreadPoolExecutor(max_workers=6) as pool:
            for row in pool.map(verify,rows.values()):
                if row: verified.append(row)
        save_products(server.DB_PATH,kind,verified)
        report["fetched"][kind]=len(rows)
        report["verified"][kind]=len(verified)
        report["photo_failed"][kind]=len(rows)-len(verified)
        print(f"{kind}: {len(verified)}/{len(rows)} price + photo verified and saved",flush=True)
    report["stored"]={k:len(v) for k,v in read_products(server.DB_PATH).items()}
    report["finished_at"]=datetime.now(timezone.utc).isoformat()
    destination=ROOT/"data"/"retail_crawl_report.json"
    destination.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
