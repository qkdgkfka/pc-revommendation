"""Measure catalog preparation using unchanged local data and no retailer requests."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--iterations', type=int, default=10)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error('--iterations must be positive')
    sys.path.insert(0, str(args.project.resolve()))
    import server_fixed as server

    server.load_config()
    server.load_db_cache()
    start = time.perf_counter()
    catalog = server.catalog_response(compact=True)
    cold_ms = (time.perf_counter() - start) * 1000
    times = []
    for _ in range(args.iterations):
        start = time.perf_counter()
        assert server.catalog_response(compact=True) == catalog
        times.append((time.perf_counter() - start) * 1000)
    raw = json.dumps(catalog, ensure_ascii=False, sort_keys=True).encode()
    result = {
        'project': str(args.project.resolve()), 'iterations': args.iterations,
        'compact_catalog_cold_ms': round(cold_ms, 3),
        'compact_catalog_warm_median_ms': round(statistics.median(times), 3),
        'compact_catalog_warm_samples_ms': [round(value, 3) for value in times],
        'catalog_sha256': hashlib.sha256(raw).hexdigest(),
        'catalog_raw_bytes': len(raw), 'catalog_gzip_bytes': len(gzip.compress(raw, mtime=0)),
    }
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
