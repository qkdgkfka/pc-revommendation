"""Import reviewed RT/native CSV pairs without changing the native FPS snapshot.

Usage: python3 scripts/import_rt_evidence.py --csv review.csv --support nvidia.json
Inputs: Back2Gaming's RTX 5070 review CSV and NVIDIA's official support JSON.
RT intensity is not specified by this CSV; never label its rows RT Ultra.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.refresh_game_data import B2G, CSV_URL, GAMES, GPU_MAP, normalized, number
from scripts.reviewed_game_sources import SUPPORT, ALIASES
from server_catalogs import GAME_OPTIONS


def parse_pairs(csv_text):
    rows = list(csv.DictReader(io.StringIO(csv_text.lstrip('\ufeff'))))
    key = lambda r: tuple(r[k] for k in ('Game Name', 'GPU Name', 'Model', 'Resolution'))
    native = {key(r): r for r in rows if r['Mode'] == 'Raster'}
    gpu_ids = dict(GPU_MAP, rtx5080='gpu_rtx5080')
    pairs = []
    for row in rows:
        if row['Mode'] != 'Ray Tracing' or row['Game Name'] not in GAMES:
            continue
        gpu = gpu_ids.get(normalized(row['GPU Name'].replace('NVIDIA GeForce ', '')))
        off = native.get(key(row))
        if not gpu or not off:
            continue
        on_fps, off_fps = number(row['Average FPS']), number(off['Average FPS'])
        if not on_fps or not off_fps or on_fps > off_fps:
            continue
        resolution = {'1920x1080':'1080', '2560x1440':'1440', '3840x2160':'2160'}.get(row['Resolution'])
        if not resolution:
            continue
        game, preset = GAMES[row['Game Name']]
        low = number(row['1% low average FPS'])
        off_low = number(off['1% low average FPS'])
        pairs.append(dict(game=game, gpu_id=gpu, cpu_id='cpu_r7_9800x3d',
                          resolution=resolution, preset='ultra', preset_label=preset,
                          gpu_model=row['Model'], native_fps=off_fps, rt_fps=on_fps,
                          low1_fps=low if low and low <= on_fps else None,
                          native_low1_fps=off_low if off_low and off_low <= off_fps else None,
                          ray_tracing=True, upscaling='native', frame_generation=False,
                          evidence_sha256=hashlib.sha256(json.dumps([off,row],sort_keys=True).encode()).hexdigest()))
    return pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--support', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'data/ray_tracing.json')
    args = parser.parse_args()
    csv_text = args.csv.read_text(encoding='utf-8-sig')
    support_text = args.support.read_text(encoding='utf-8-sig')
    icons = json.loads((ROOT/'data/game_icons.json').read_text(encoding='utf-8'))
    canonical = lambda name: normalized(unicodedata.normalize('NFKD', name))
    official = {canonical(r['name']): r for r in json.loads(support_text)['data']
                if r.get('type') == 'Game' and isinstance(r.get('name'), str)}
    support = {}
    for game in GAME_OPTIONS:
        name = ALIASES.get(game['id'], icons.get(game['id'], {}).get('name', ''))
        row = official.get(canonical(name.replace('®', '').replace('™', '')), {})
        if row.get('ray tracing'):
            support[game['id']] = row['name']
    pairs = parse_pairs(csv_text)
    data = dict(schema_version=1, checked_at=datetime.now(timezone.utc).isoformat(), source_url=B2G,
                data_url=CSV_URL, support_source_url=SUPPORT,
                csv_sha256=hashlib.sha256(csv_text.encode()).hexdigest(),
                conditions='원문 그래픽 설정 + RT · RT 세부 강도 미기재 · DLSS/FSR·프레임 생성 OFF',
                reference_ram='DDR5-6000 CL30', support=support, pairs=pairs)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'{len(pairs)} paired observations, {len(support)} supported games')


if __name__ == '__main__':
    main()
