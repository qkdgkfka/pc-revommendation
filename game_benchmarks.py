"""Measured native game FPS with explicit, bounded hardware interpolation.

Only snapshot rows are measurements. CPU/GPU ceilings and interpolation are
estimates: a review's fastest observation gives a lower bound on that test CPU's
ceiling, and the game profile supplies an explicitly reported headroom allowance.
A calibrated smooth frame-time maximum preserves the source observation while
making GPU upgrades saturate at the estimated CPU limit. Uncertainty allowances
are not statistical confidence intervals.
"""
from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

SNAPSHOT_PATH = Path(__file__).resolve().parent / "data" / "game_benchmarks.json"
_RESOLUTIONS = {"1080", "1440", "2160"}
_PRESETS = {"low", "medium", "high", "ultra"}
_PRESET_ORDER = {"low": 0, "medium": 1, "high": 2, "ultra": 3}
_CPU_QUALITY = {"low": 1.10, "medium": 1.04, "high": 1.0, "ultra": .96}
_FRAME_POWER = 4.0


def _positive_number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) and result > 0 else None


@lru_cache(maxsize=1)
def load_measurements():
    try:
        payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    if not isinstance(payload, dict) or not isinstance(payload.get("measurements"), list):
        return ()
    rows = []
    for row in payload["measurements"]:
        if not isinstance(row, dict):
            continue
        fps = _positive_number(row.get("avg_fps"))
        low = _positive_number(row.get("low1_fps"))
        text_keys = ("game", "cpu_id", "gpu_id", "source_url", "source_title",
                     "reference_cpu", "preset_label", "published_at", "evidence_sha256")
        if not all(isinstance(row.get(key), str) and row[key].strip() for key in text_keys):
            continue
        try:
            source = urlsplit(row["source_url"])
            valid_url = source.scheme == "https" and bool(source.hostname)
        except ValueError:
            valid_url = False
        valid = (fps is not None and valid_url
                 and re.fullmatch(r"[0-9a-fA-F]{64}", row["evidence_sha256"])
                 and row.get("resolution") in _RESOLUTIONS
                 and row.get("preset") in _PRESETS
                 and row.get("ray_tracing") is False
                 and row.get("frame_generation") is False
                 and row.get("upscaling") == "native"
                 and (row.get("low1_fps") is None or (low is not None and low <= fps)))
        if valid:
            rows.append({**row, "avg_fps": fps, "low1_fps": low,
                         "collected_at": payload.get("collected_at", "")})
    return tuple(rows)


class _IdentityKey:
    """Cache snapshots/catalog lists without rehashing every row.

    Retaining the object prevents id reuse. Replacing a snapshot or catalog list
    invalidates its index automatically; in-place structural edits should call
    clear_caches(). Existing catalog row dictionaries remain live in the index.
    """
    __slots__ = ("value", "length")

    def __init__(self, value):
        self.value, self.length = value, len(value)

    def __hash__(self):
        return hash((id(self.value), self.length))

    def __eq__(self, other):
        return (isinstance(other, _IdentityKey) and self.value is other.value
                and self.length == other.length)


def _test_group(row):
    # Never pool different reviews, CPUs, game versions, or quality presets.
    return (row["game"], row["cpu_id"], row["source_url"], row["published_at"],
            row.get("game_version", ""), row["preset"], row.get("preset_label", ""), row.get("workload_note", ""))


@lru_cache(maxsize=1)
def _measurement_index(key):
    by_game, fastest = defaultdict(list), {}
    for row in key.value:
        by_game[row["game"]].append(row)
        group = _test_group(row)
        if group not in fastest or row["avg_fps"] > fastest[group]["avg_fps"]:
            fastest[group] = row
    return {game: tuple(rows) for game, rows in by_game.items()}, fastest


@lru_cache(maxsize=8)
def _catalog_index(key):
    return {row["id"]: row for row in key.value if isinstance(row, dict) and row.get("id")}


@lru_cache(maxsize=2048)
def _reference_row(game, gpu_id, cpu_id, resolution, preset, rows_key, gpu_key, cpu_key):
    by_game, _ = _measurement_index(rows_key)
    gpu_index, cpu_index = _catalog_index(gpu_key), _catalog_index(cpu_key)
    candidates = [row for row in by_game.get(game, ())
                  if row["gpu_id"] in gpu_index and row["cpu_id"] in cpu_index]
    if not candidates:
        return None
    # Exact conditions win, including CPU when two reviews test the same GPU.
    # Otherwise retain the GPU's own evidence before interpolating another GPU.
    return max(candidates, key=lambda row: (
        (row["gpu_id"], row["cpu_id"], row["resolution"], row["preset"])
        == (gpu_id, cpu_id, resolution, preset),
        row["gpu_id"] == gpu_id, row["resolution"] == resolution,
        row["preset"] == preset,
        -abs(_PRESET_ORDER[row["preset"]] - _PRESET_ORDER[preset]),
        row["cpu_id"] == cpu_id,
        -abs(int(row["resolution"]) - int(resolution)),
    ))


def clear_caches():
    """Call after an in-process benchmark refresh or structural catalog edit."""
    load_measurements.cache_clear()
    _measurement_index.cache_clear()
    _catalog_index.cache_clear()
    _reference_row.cache_clear()


def quality_factor(preset, cpu_weight):
    # Extrapolation only: never changes a stored source preset or its FPS.
    return {"low": 1.22 if cpu_weight >= .42 else 1.38,
            "medium": 1.12 if cpu_weight >= .42 else 1.20,
            "high": 1.0, "ultra": .83}.get(preset, 1.0)


def _performance(gpu, resolution):
    return _positive_number(gpu.get("perf_" + resolution))


def _resolve_profile(part, index):
    reference = part.get("performance_ref_id")
    if reference:
        # A retail SKU's own price/cooler is not an independent chip benchmark.
        return index.get(reference)
    return index.get(part.get("id"), part)


def _smooth_limit(gpu_fps, cpu_fps):
    lower, higher = min(gpu_fps, cpu_fps), max(gpu_fps, cpu_fps)
    return lower / (1.0 + (lower / higher) ** _FRAME_POWER) ** (1.0 / _FRAME_POWER)


def estimate_from_measurements(gpu, cpu, ram, game, resolution, preset, profile, catalogs):
    resolution = str(resolution)
    if resolution not in _RESOLUTIONS or preset not in _PRESETS:
        return None
    rows_key = _IdentityKey(load_measurements())
    gpu_key, cpu_key = _IdentityKey(catalogs.get("gpu", ())), _IdentityKey(catalogs.get("cpu", ()))
    gpu_index, cpu_index = _catalog_index(gpu_key), _catalog_index(cpu_key)
    gpu, cpu = _resolve_profile(gpu, gpu_index), _resolve_profile(cpu, cpu_index)
    if not gpu or not cpu:
        return None
    gpu_id, cpu_id = gpu.get("id"), cpu.get("id")
    row = _reference_row(game, gpu_id, cpu_id, resolution, preset, rows_key, gpu_key, cpu_key)
    if row is None:
        return None
    source_gpu, source_cpu = gpu_index[row["gpu_id"]], cpu_index[row["cpu_id"]]
    target_gpu_perf, source_gpu_perf = _performance(gpu, resolution), _performance(source_gpu, row["resolution"])
    target_cpu_perf, source_cpu_perf = _positive_number(cpu.get("perf")), _positive_number(source_cpu.get("perf"))
    if None in (target_gpu_perf, source_gpu_perf, target_cpu_perf, source_cpu_perf):
        return None
    same_gpu, same_cpu = gpu_id == row["gpu_id"], cpu_id == row["cpu_id"]
    same_resolution, same_preset = row["resolution"] == resolution, row["preset"] == preset
    weight = min(.90, max(.05, _positive_number(profile.get("cpu_weight")) or .24))
    cpu_ratio = target_cpu_perf / source_cpu_perf
    _, fastest = _measurement_index(rows_key)
    cpu_anchor = fastest[_test_group(row)]
    # A GPU-limited 4K result is not a CPU limit. Normalize its pixel workload
    # before inferring CPU headroom, retaining the measured FPS as the GPU
    # calibration point. This is an estimate, not a measured CPU benchmark.
    anchor_gpu = gpu_index.get(cpu_anchor["gpu_id"], source_gpu)
    anchor_perf = _performance(anchor_gpu, cpu_anchor["resolution"])
    anchor_1080_perf = _performance(anchor_gpu, "1080")
    anchor_resolution_scale = max(1.0, anchor_1080_perf / anchor_perf) if anchor_perf and anchor_1080_perf else 1.0
    cpu_anchor_fraction = .65 + .30 * weight
    reference_cpu_ceiling = float(cpu_anchor["avg_fps"]) * anchor_resolution_scale / cpu_anchor_fraction
    reference_average = float(row["avg_fps"])
    reference_gpu_ceiling = reference_average / (
        1.0 - (reference_average / reference_cpu_ceiling) ** _FRAME_POWER
    ) ** (1.0 / _FRAME_POWER)
    gpu_scale = target_gpu_perf / source_gpu_perf
    gpu_scale *= quality_factor(preset, weight) / quality_factor(row["preset"], weight)
    gpu_ceiling = reference_gpu_ceiling * gpu_scale
    cpu_ceiling = reference_cpu_ceiling * cpu_ratio * _CPU_QUALITY[preset] / _CPU_QUALITY[row["preset"]]
    limited_average = _smooth_limit(gpu_ceiling, cpu_ceiling)
    gb = _positive_number(ram.get("gb")) or 16.0
    ram_scale = .85 if gb <= 8 else .94 if gb < 16 else .98 if gb < 32 and profile.get("ram_hungry") else 1.0
    measured = same_gpu and same_cpu and same_resolution and same_preset and ram_scale == 1.0
    average = reference_average if measured else limited_average * ram_scale
    scale = average / reference_average
    low_is_estimated = row.get("low1_fps") is None or not measured
    low_ratio = min(1.0, _positive_number(profile.get("low1")) or .78)
    low = float(row.get("low1_fps") or reference_average * low_ratio) * scale
    missing = []
    if row.get("workload_note"):
        missing.append(row["workload_note"])
    if any(token in row["preset_label"].lower() for token in ("custom", "competitive", "article settings")):
        missing.append("원문 개별 그래픽 설정 기준이며 일반 프리셋과 차이가 있을 수 있습니다")
    if not same_gpu:
        missing.append("GPU 성능 지수로 보정")
    if not same_cpu:
        missing.append("테스트 CPU 대비 처리 성능과 게임별 부하로 보정")
    if not same_resolution:
        missing.append("다른 해상도의 측정치를 성능 지수로 보정")
    if not same_preset:
        missing.append(f"원본 {row['preset_label']} 프리셋에서 옵션 배율로 추정")
    if ram_scale != 1:
        missing.append("메모리 용량 부족 보정")
    if low_is_estimated:
        missing.append("1% Low는 추정치")
    if anchor_resolution_scale > 1.0:
        missing.append("고해상도 측정의 GPU 부하를 보정해 CPU 여유를 추정")
    missing.append("병목률은 게임 실측 기준의 모델 추정이며 별도 CPU 벤치마크 실측값이 아닙니다")
    missing.append("패치·테스트 장면·메모리·드라이버 차이에 따라 실제 FPS가 달라집니다")
    uncertainty = .10 if measured else min(.50, .18 + (.12 if not same_gpu else 0) + (.10 if not same_resolution else 0) + (.08 if cpu_ratio < .6 else 0))
    confidence = "high" if measured else "medium" if same_gpu and same_resolution and cpu_ratio >= .6 else "low"
    limiter = "cpu" if cpu_ceiling < gpu_ceiling * .9 else "gpu" if gpu_ceiling < cpu_ceiling * .9 else "balanced"
    bottleneck = {
        "estimated": True, "method": "benchmark_calibrated_frame_time_limit",
        "limiting_component": limiter,
        "cpu_fps_ceiling": round(cpu_ceiling, 1), "gpu_fps_ceiling": round(gpu_ceiling, 1),
        "cpu_frame_time_ms": round(1000.0 / cpu_ceiling, 2),
        "gpu_frame_time_ms": round(1000.0 / gpu_ceiling, 2),
        "cpu_penalty_pct": round(100.0 * max(0.0, 1.0 - limited_average / gpu_ceiling), 1),
        "reference_observed_fps": cpu_anchor["avg_fps"],
        "reference_observed_resolution": cpu_anchor["resolution"],
        "reference_observed_gpu_id": cpu_anchor["gpu_id"],
        "reference_resolution_scale": round(anchor_resolution_scale, 3),
        "assumed_cpu_headroom_factor": round(1.0 / cpu_anchor_fraction, 3),
        "note": "선택한 게임·해상도·옵션의 추정입니다. CPU 제한율은 추정 GPU 상한 대비 감소량이며 범용 병목 퍼센트가 아닙니다.",
    }
    evidence = {
        "method": "measured_benchmark" if measured else "benchmark_calibrated",
        "confidence": confidence, "range": {"min": round(average * (1 - uncertainty), 1), "max": round(average * (1 + uncertainty), 1)},
        "source_url": row["source_url"], "source_title": row["source_title"],
        "chart_url": row.get("chart_url", ""), "reference_gpu": source_gpu.get("name", row["gpu_id"]),
        "reference_cpu": row["reference_cpu"], "reference_preset": row["preset_label"],
        "reference_resolution": row["resolution"], "reference_avg_fps": row["avg_fps"],
        "reference_low1_fps": row.get("low1_fps"), "reference_ram": row.get("reference_ram", "not reported"),
        "published_at": row["published_at"], "collected_at": row["collected_at"],
        "low1_estimated": low_is_estimated, "bottleneck": bottleneck,
        "notes": missing, "conditions": f"{row['resolution']}p · {row['preset_label']} · Native · RT/프레임 생성 OFF",
        "range_method": "heuristic_allowance_not_statistical_interval",
    }
    return round(average, 1), round(min(average, low), 1), evidence
