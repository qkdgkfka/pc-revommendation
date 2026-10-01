"""Verify a local production build and measure read-only catalog/FPS HTTP calls."""
import argparse
import gzip
import json
from pathlib import Path
import re
import statistics
import time
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:4000')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()

    def get(path, headers=None, body=None):
        request = Request(args.url.rstrip('/') + path, data=body, headers=headers or {})
        start = time.perf_counter()
        with urlopen(request, timeout=15) as response:
            return response.status, dict(response.headers), response.read(), (time.perf_counter() - start) * 1000

    status, headers, html, _ = get('/', {'Accept-Encoding': 'gzip'})
    assert status == 200 and headers['Cache-Control'] == 'no-cache'
    html = gzip.decompress(html).decode() if headers.get('Content-Encoding') == 'gzip' else html.decode()
    assets = re.findall(r'(?:src|href)="(/assets/[^" ]+\.(?:js|css))"', html)
    assert assets, 'Build assets missing from HTML'
    metrics = []
    for asset in assets:
        status, headers, data, _ = get(asset, {'Accept-Encoding': 'gzip'})
        assert status == 200 and headers.get('Content-Encoding') == 'gzip'
        assert 'immutable' in headers['Cache-Control'] and headers['Vary'] == 'Accept-Encoding'
        metrics.append({'asset': asset, 'gzip_bytes': len(data), 'raw_bytes': len(gzip.decompress(data))})
    css_asset = next(item['asset'] for item in metrics if item['asset'].endswith('.css'))
    _, css_headers, css, _ = get(css_asset)
    font_url = re.search(r'url\((/assets/[^)]+\.woff2)\)', css.decode()).group(1)
    status, headers, font, _ = get(font_url)
    assert 'immutable' in headers['Cache-Control']
    assert status == 200 and headers['Content-Type'] == 'font/woff2'

    status, headers, raw, cold = get('/api/catalog?compact=1', {'Accept-Encoding': 'gzip'})
    assert status == 200 and headers.get('Content-Encoding') == 'gzip'
    catalog = json.loads(gzip.decompress(raw))
    assert catalog['games'] and 'filter_facets' in catalog
    warm = [get('/api/catalog?compact=1', {'Accept-Encoding': 'gzip'})[3] for _ in range(10)]
    body = json.dumps({'gpu': 'gpu_rtx5070', 'cpu': 'cpu_r5_7600', 'ram': 'ram_32_ddr5',
                       'game': 'cyberpunk2077', 'resolution': '1440', 'refresh': 60}).encode()
    first_fps = get('/api/estimate-fps', {'Content-Type': 'application/json', 'Accept-Encoding': 'gzip'}, body)
    assert first_fps[1]['Cache-Control'] == 'no-store'
    fps = json.loads(gzip.decompress(first_fps[2]))
    assert fps['fps']['fps_by_option']['high'] > 0
    fps_warm = [get('/api/estimate-fps', {'Content-Type': 'application/json'}, body)[3] for _ in range(10)]
    result = {
        'initial_assets': metrics,
        'initial_raw_bytes': sum(item['raw_bytes'] for item in metrics),
        'initial_gzip_bytes': sum(item['gzip_bytes'] for item in metrics),
        'catalog_gzip_bytes': len(raw), 'catalog_first_http_ms': round(cold, 3),
        'catalog_warm_http_median_ms': round(statistics.median(warm), 3),
        'fps_first_http_ms': round(first_fps[3], 3),
        'fps_warm_http_median_ms': round(statistics.median(fps_warm), 3),
        'font_bytes': len(font), 'games': len(catalog['games']), 'fps_source': fps['fps']['fps_source'],
    }
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
