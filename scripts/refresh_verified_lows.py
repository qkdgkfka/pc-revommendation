"""Refresh the original Back2Gaming AVG/1% low dataset with replayable evidence.

Run from the repository: python3 scripts/refresh_verified_lows.py
No minimum-FPS or percentile column is accepted as an average 1% low.
The source's reported statistic is preserved; raw per-frame traces are not public.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from game_database import save_snapshot
from scripts.refresh_game_data import B2G as REVIEW_URL, CSV_URL, GAMES, GPU_IDS, normalized, parse_b2g

MAX_RESPONSE_BYTES = 4_000_000
LOW_COLUMN = '1% low average FPS'
WORKLOADS = {
    'csgo2': 'Mirage map custom scene',
    'dota2': 'Dacha Dubai 2024 Xtreme Gaming vs. Team Liquid replay at 56:25',
    'pubg': 'Custom scene; exact route not specified in this review',
    'rainbow6': 'In-game benchmark',
    'baldurs_gate3': 'Lower City area custom loop',
    'black_myth_wukong': 'Forest of Wolves loop, past Wandering Wight along the stream',
    'cyberpunk2077': 'In-game benchmark',
    'f1_24': 'Singapore, night, wet; in-game benchmark',
    'ghost_of_tsushima': 'Kushi Temple',
    'hogwarts_legacy': 'Hogsmeade Square loop',
    'horizon_forbidden_west': "Devil's Grasp loop",
    'the_last_of_us1': 'Prologue, town panic area',
    'spider_man2': 'Financial District at ground level',
    'msfs2024': 'Melbourne discovery',
    'ratchet_clank': 'Nefarious City loop',
    'resident_evil4': 'Custom scene; exact route not specified in this review',
    'starfield': 'Wilderness outside Jamison',
    'space_marine2': 'Sequence not specified in the review text',
}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def fetch(url):
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (PCBuilder benchmark source validation)'})
    with urlopen(request, timeout=25) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError('Source exceeds response size limit')
    return raw


def parse_source(html, csv_text, collected_at):
    """Validate the public schema, then normalize actual CSV observations only."""
    soup = BeautifulSoup(html, 'html.parser')
    published = updated = None
    for script in soup.select('script[type="application/ld+json"]'):
        data = json.loads(script.string or script.get_text())
        for item in data.get('@graph', [data]):
            if item.get('@type') == 'ItemPage' and item.get('url') == REVIEW_URL:
                published, updated = item.get('datePublished'), item.get('dateModified')
    if not published:
        raise ValueError('Original publication date is required')
    datetime.fromisoformat(published.replace('Z', '+00:00'))

    reader = csv.DictReader(io.StringIO(csv_text.lstrip('\ufeff')))
    required = {'Game Name', 'GPU Name', 'Average FPS', LOW_COLUMN, 'Model', 'Resolution', 'Mode'}
    if set(reader.fieldnames or []) != required:
        raise ValueError('Source metric/schema changed; explicit 1% low average FPS required')
    records = list(reader)
    preferred = {}
    for item in sorted(records, key=lambda r: 'Founders Edition' not in (r.get('Model') or '')):
        key = tuple(item.get(k) for k in ('Game Name', 'GPU Name', 'Resolution', 'Mode'))
        preferred.setdefault(key, item.get('Model'))
    seen = {}
    for item in records:
        if item.get('Mode') != 'Raster' or item.get('Game Name') not in GAMES:
            continue
        group = tuple(item.get(k) for k in ('Game Name', 'GPU Name', 'Resolution', 'Mode'))
        if item.get('Model') != preferred[group]:
            continue  # The existing collector retains the reference card when present.
        gpu = 'gpu_' + normalized(item['GPU Name'].replace('NVIDIA GeForce ', ''))
        if gpu not in GPU_IDS:
            continue
        if None in item or None in item.values():
            raise ValueError('Malformed CSV row')
        for label in ('Average FPS', LOW_COLUMN):
            if not re.fullmatch(r'\d+(?:\.\d+)?', item[label].strip()):
                raise ValueError('Invalid FPS in source row: ' + label)
        avg, low = float(item['Average FPS']), float(item[LOW_COLUMN])
        if not 0 < low <= avg <= 1500:
            raise ValueError('Impossible AVG/low pair in source row')
        key = tuple(item[k] for k in ('Game Name', 'GPU Name', 'Model', 'Resolution', 'Mode'))
        if key in seen and seen[key] != (avg, low):
            raise ValueError('Conflicting duplicate source measurements')
        seen[key] = (avg, low)

    rows, pending = parse_b2g(html, csv_text)
    for row in rows:
        row.update(
            published_at=published,
            source_updated_at=updated,
            collected_at=collected_at,
            low_metric='reported_1_percent_low_average',
            low_metric_label=LOW_COLUMN,
            low_metric_note='Publisher-labelled CapFrameX 1% low average; raw frame traces and aggregation configuration are not published.',
            reference_ram='G.Skill Trident Z5 NEO RGB DDR5-6000 CL30-38-38-96; capacity not reported',
            reference_ram_gb=None,
            hardware_source=REVIEW_URL,
            workload_note=WORKLOADS[row['game']],
            collection_method='verified_original_csv',
            source_dataset='Back2Gaming GPUDB-Q1-2025 RTX5070 review',
            raw_csv_sha256=sha256(csv_text.encode('utf-8')),
            raw_html_sha256=sha256(html.encode('utf-8')),
        )
    return rows, pending


def _atomic_bytes(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def refresh(snapshot_path, database_path, evidence_dir, fetcher=fetch):
    """Fail before mutation on fetch/parser errors; retain unrelated snapshot data."""
    snapshot_path, evidence_dir = Path(snapshot_path), Path(evidence_dir)
    checked = datetime.now(timezone.utc).isoformat()
    raw_html, raw_csv = fetcher(REVIEW_URL), fetcher(CSV_URL)
    if any(not isinstance(raw, bytes) or len(raw) > MAX_RESPONSE_BYTES for raw in (raw_html, raw_csv)):
        raise ValueError('Invalid or oversized source response')
    html, csv_text = raw_html.decode('utf-8-sig'), raw_csv.decode('utf-8-sig')
    rows, pending = parse_source(html, csv_text, checked)
    evidence = []
    for label, url, raw in [('review', REVIEW_URL, raw_html), ('csv', CSV_URL, raw_csv)]:
        digest = sha256(raw)
        name = 'back2gaming-5070-' + label + '-' + digest[:16] + '.gz'
        _atomic_bytes(evidence_dir / name, gzip.compress(raw, mtime=0))
        evidence.append({'url': url, 'filename': name, 'sha256': digest,
                         'uncompressed_bytes': len(raw), 'collected_at': checked})
    for row in rows:
        row['raw_html_sha256'], row['raw_csv_sha256'] = sha256(raw_html), sha256(raw_csv)
        row['evidence_files'] = [item['filename'] for item in evidence]

    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    prior = [r for r in snapshot.get('measurements', []) if r.get('source_url') == REVIEW_URL]
    snapshot['measurements'] = [r for r in snapshot.get('measurements', [])
                                if r.get('source_url') != REVIEW_URL] + rows
    snapshot['pending_measurements'] = [r for r in snapshot.get('pending_measurements', [])
                                       if r.get('source_url') != REVIEW_URL] + pending
    source = {'url': REVIEW_URL, 'html_sha256': sha256(raw_html), 'csv_sha256': sha256(raw_csv),
              'collected_at': checked, 'raw_evidence': evidence,
              'low_metric_label': LOW_COLUMN, 'validated_measurements': len(rows)}
    snapshot['sources'] = [s for s in snapshot.get('sources', []) if s.get('url') != REVIEW_URL] + [source]
    snapshot['collected_at'] = checked
    encoded = (json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    # SQLite updates only game snapshot tables inside its transaction. A failed
    # DB write leaves the previous JSON untouched. JSON replacement is atomic.
    save_snapshot(snapshot, Path(database_path))
    _atomic_bytes(snapshot_path, encoded)
    return {'source_url': REVIEW_URL, 'collected_at': checked, 'previous_rows': len(prior),
            'validated_rows': len(rows), 'added_rows': len(rows) - len(prior),
            'low_metric_label': LOW_COLUMN, 'raw_evidence': evidence,
            'total_measurements': len(snapshot['measurements'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=ROOT / 'data/game_benchmarks.json')
    parser.add_argument('--database', type=Path, default=ROOT / 'data/pc.db')
    parser.add_argument('--evidence-dir', type=Path, default=ROOT / 'data/benchmark_evidence')
    args = parser.parse_args()
    print(json.dumps(refresh(args.snapshot, args.database, args.evidence_dir), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
