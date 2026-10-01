"""Compare search/recommend processing with fixed seller latency and disposable data."""
import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import statistics
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.project.resolve()))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
    import server_fixed as server
    import game_database
    from backend_patch import patch_backend

    with tempfile.TemporaryDirectory(prefix='pc-request-bench-') as directory:
        path = Path(directory) / 'pc.db'
        shutil.copy2(args.project / 'data/pc.db', path)
        game_database.DB_PATH = path
        with patch_backend(server, 'DB_PATH', path):
            server.load_config()
            server.load_db_cache()
            observed = datetime.now(timezone.utc).isoformat()
            chosen = {
                'gpu': {'gpu_rtx5060', 'gpu_rtx5070', 'gpu_rtx5080'},
                'cpu': {'cpu_r5_7600', 'cpu_r7_9800x3d'},
                'ram': {'ram_32_ddr5', 'ram_64_ddr5'},
            }
            inventory = {}
            for kind in ('cpu', 'gpu', 'ram', 'mb', 'storage', 'psu'):
                rows = copy.deepcopy(server.CATALOGS[kind])
                if kind in chosen:
                    rows = [row for row in rows if row['id'] in chosen[kind]]
                if kind == 'mb':
                    rows = [row for row in rows if row.get('socket') == 'AM5' and row.get('ram_type') == 'DDR5']
                inventory[kind] = [dict(row, product_name=row['name'], price_status='verified',
                                        price_source='danawa_live', price_checked_at=observed,
                                        url=f'https://prod.danawa.com/info/?pcode={index + 100}',
                                        image_url=f'https://img.danuri.io/fixture-{index}.jpg')
                                   for index, row in enumerate(rows)]

            source_calls = []
            def seller(kind, query, page, limit, provider, *rest):
                source_calls.append(provider)
                time.sleep(.02)
                return {'items': inventory[kind], 'status': 'live', 'has_more': False,
                        'source_url': 'https://example.com/fixture', 'cached': False}

            with patch_backend(server, '_market_source_page', side_effect=seller), \
                 patch_backend(server, 'saved_products', return_value=[]):
                start = time.perf_counter()
                search = server.market_products_response('cpu', 'Ryzen', source='all', persist=False)
                search_first = (time.perf_counter() - start) * 1000
                warm = []
                for _ in range(10):
                    start = time.perf_counter()
                    server.market_products_response('cpu', 'Ryzen', source='all', persist=False)
                    warm.append((time.perf_counter() - start) * 1000)
            server.RECOMMENDATION_CACHE.clear()
            with patch_backend(server, 'verified_recommendation_inventory', return_value=inventory) as retailer:
                start = time.perf_counter()
                recommendation = server.recommend({'budget': 3000000, 'game': 'cyberpunk2077', 'resolution': '1440'})
                recommend_first = (time.perf_counter() - start) * 1000
                repeats = []
                for _ in range(10):
                    start = time.perf_counter()
                    server.recommend({'budget': 3000000, 'game': 'cyberpunk2077', 'resolution': '1440'})
                    repeats.append((time.perf_counter() - start) * 1000)
            result = {
                'fixture_provider_latency_ms': 20, 'search_first_ms': round(search_first, 3),
                'search_warm_median_ms': round(statistics.median(warm), 3),
                'search_items': len(search['items']), 'search_seller_calls_for_11_requests': len(source_calls),
                'recommend_first_ms': round(recommend_first, 3),
                'recommend_warm_median_ms': round(statistics.median(repeats), 3),
                'recommend_inventory_calls_for_11_requests': retailer.call_count,
                'tier_totals': {tier: row.get('totalPrice') for tier, row in recommendation['results'].items()},
                'tier_high_fps': {tier: row.get('fps', {}).get('fps_by_option', {}).get('high')
                                  for tier, row in recommendation['results'].items()},
                'tier_parts': {tier: {kind: part['id'] for kind, part in row.get('parts', {}).items()}
                               for tier, row in recommendation['results'].items()},
            }
            if args.output:
                args.output.write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
