"""Native RT comparisons from paired review observations, never global RT ratios."""
from functools import lru_cache
import json
import math
from pathlib import Path

RT_DATA_PATH = Path(__file__).parent / 'data/ray_tracing.json'


@lru_cache(maxsize=1)
def rt_data():
    try:
        return json.loads(RT_DATA_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def positive(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) and value > 0 else None


def ray_tracing_scenario(gpu, cpu, game, resolution, fps):
    data = rt_data()
    pairs = data.get('pairs', [])
    if game not in data.get('support', {}) and not any(r.get('game') == game for r in pairs):
        return None
    gpu_id = gpu.get('performance_ref_id') or gpu.get('id')
    cpu_id = cpu.get('performance_ref_id') or cpu.get('id')
    candidates = [r for r in pairs if r.get('game') == game and r.get('gpu_id') == gpu_id
                  and str(r.get('resolution')) == str(resolution)
                  and r.get('upscaling') == 'native' and r.get('frame_generation') is False
                  and r.get('ray_tracing') is True
                  and positive(r.get('native_fps')) and positive(r.get('rt_fps'))
                  and r['rt_fps'] <= r['native_fps']]
    unavailable = dict(id='rt_unavailable', label='레이 트레이싱 · RT',
                       supported=False, game_supported=True, avg_fps=None, method='unavailable',
                       note='RT 지원 게임이지만 이 GPU·해상도의 비교 측정 자료가 부족합니다.')
    if not candidates:
        return unavailable
    # Prefer the reference board; retain the actual board name for other SKUs.
    row = min(candidates, key=lambda r: ('Founders Edition' not in r.get('gpu_model', ''),
                                        r.get('gpu_model', '')))
    same_cpu = cpu_id == row['cpu_id']
    scale = 1.0
    if not same_cpu:
        target = positive(fps.get('fps_by_option', {}).get(row['preset']))
        if not target:
            return unavailable
        # CPU transfers remain estimates. Do not invent gains over the review CPU.
        scale = min(1.0, target / row['native_fps'])
    cap = positive(fps.get('frame_cap')) or math.inf
    off, on = min(row['native_fps'] * scale, cap), min(row['rt_fps'] * scale, cap)
    low = positive(row.get('low1_fps')) if same_cpu else None
    off_low = positive(row.get('native_low1_fps')) if same_cpu else None
    return dict(id='rt', label='RT 켬 · 원문 설정', supported=True, game_supported=True,
                avg_fps=round(on, 1), render_fps=round(on, 1), rt_off_fps=round(off, 1),
                low1_fps=round(min(low, on), 1) if low else None,
                rt_off_low1_fps=round(min(off_low, off), 1) if off_low else None,
                generated=False, upscaling='native',
                method='mode_measurement' if same_cpu else 'mode_calibrated_estimate',
                confidence='medium' if same_cpu else 'low',
                source_url=data.get('source_url'), preset_label=row['preset_label'],
                reference_gpu=row.get('gpu_model'), reference_cpu=row['cpu_id'],
                reference_resolution=row['resolution'],
                note=data.get('conditions'),
                calibration_basis=None if same_cpu else '같은 GPU의 RT 전후 실측에 선택한 CPU의 기본 FPS 추정을 반영했습니다.')
