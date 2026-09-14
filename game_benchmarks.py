"""Game-specific evidence and transparent interpolation for the FPS API.

The snapshot contains measured native FPS only. CPU, GPU, resolution and preset
adjustments below are heuristic estimates and are reported as such per option.
The uncertainty band is an engineering allowance, not a statistical confidence
interval. Unverified legacy SQLite rows are never presented as measurements.
"""
from __future__ import annotations

from functools import lru_cache
import json
import math
from pathlib import Path

SNAPSHOT_PATH = Path(__file__).resolve().parent / "data" / "game_benchmarks.json"


@lru_cache(maxsize=1)
def load_measurements():
    try:
        payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    rows = []
    for row in payload.get("measurements", []):
        try:
            fps = float(row["avg_fps"])
            valid = (math.isfinite(fps) and fps > 0 and row["source_url"].startswith("https://")
                     and row["cpu_id"] and row["gpu_id"] and row["evidence_sha256"]
                     and row["resolution"] in {"1080", "1440", "2160"}
                     and row["preset"] in {"low", "medium", "high", "ultra"}
                     and row["ray_tracing"] is False and row["frame_generation"] is False
                     and row["upscaling"] == "native")
        except (KeyError, TypeError, ValueError):
            valid = False
        if valid:
            rows.append({**row, "collected_at": payload.get("collected_at", "")})
    return tuple(rows)


def quality_factor(preset, cpu_weight):
    # Extrapolation only: never changes the stored source preset or its FPS.
    return {"low": 1.22 if cpu_weight >= .42 else 1.38,
            "medium": 1.12 if cpu_weight >= .42 else 1.20,
            "high": 1.0, "ultra": .83}.get(preset, 1.0)


def _performance(gpu, resolution):
    return max(1.0, float(gpu.get("perf_" + resolution) or 1.0))


def estimate_from_measurements(gpu, cpu, ram, game, resolution, preset, profile, catalogs):
    rows = [r for r in load_measurements() if r["game"] == game]
    if not rows:
        return None
    gpu_id, cpu_id = gpu.get("id"), cpu.get("id")
    # Prefer the selected GPU's own evidence, then the exact resolution. Do not
    # average dissimilar presets, test runs, resolutions or upscaling modes.
    row = max(rows, key=lambda r: (r["gpu_id"] == gpu_id, r["resolution"] == resolution,
                                  r["preset"] == preset, r["gpu_id"] == "gpu_rtx5070"))
    source_gpu = next((g for g in catalogs["gpu"] if g.get("id") == row["gpu_id"]), None)
    source_cpu = next((c for c in catalogs["cpu"] if c.get("id") == row["cpu_id"]), None)
    if not source_gpu or not source_cpu:
        return None
    same_gpu = gpu_id == row["gpu_id"]
    same_cpu = cpu_id == row["cpu_id"]
    same_resolution = row["resolution"] == resolution
    same_preset = row["preset"] == preset
    weight = float(profile.get("cpu_weight", .24))
    scale = _performance(gpu, resolution) / _performance(source_gpu, row["resolution"])
    scale *= quality_factor(preset, weight) / quality_factor(row["preset"], weight)
    cpu_ratio = max(.15, min(1.15, float(cpu.get("perf") or 1) / max(1, float(source_cpu.get("perf") or 1))))
    # Always normalize to the article's actual CPU, rather than applying a
    # guessed ceiling that makes a Ryzen 7600 and 9800X3D look identical.
    cpu_scale = 1.0 if same_cpu else cpu_ratio ** (weight * {"1080": 1.0, "1440": .85, "2160": .60}[resolution])
    gb = float(ram.get("gb") or 16)
    ram_scale = .85 if gb <= 8 else .94 if gb < 16 else .98 if gb < 32 and profile.get("ram_hungry") else 1.0
    scale *= cpu_scale * ram_scale
    average = float(row["avg_fps"]) * scale
    low_is_estimated = row.get("low1_fps") is None or scale != 1.0 or not same_cpu
    low = float(row.get("low1_fps") or float(row["avg_fps"]) * float(profile.get("low1", .78))) * scale
    measured = same_gpu and same_cpu and same_resolution and same_preset and ram_scale == 1.0
    missing = []
    if not same_gpu:
        missing.append("GPU 성능 지수로 보정")
    if not same_cpu:
        missing.append("테스트 CPU 대비 성능과 게임의 CPU 민감도로 보정")
    if not same_resolution:
        missing.append("다른 해상도의 측정치를 성능 지수로 보정")
    if not same_preset:
        missing.append(f"원본 {row['preset_label']} 프리셋에서 옵션 배율로 추정")
    if ram_scale != 1:
        missing.append("메모리 용량 부족 보정")
    if low_is_estimated:
        missing.append("1% Low는 추정치")
    missing.append("패치·테스트 장면·메모리·드라이버 차이에 따라 실제 FPS가 달라집니다")
    uncertainty = .10 if measured else min(.50, .18 + (.12 if not same_gpu else 0) + (.10 if not same_resolution else 0) + (.08 if cpu_ratio < .6 else 0))
    confidence = "high" if measured else "medium" if same_gpu and same_resolution and cpu_ratio >= .6 else "low"
    evidence = {
        "method": "measured_benchmark" if measured else "benchmark_calibrated",
        "confidence": confidence, "range": {"min": round(average * (1 - uncertainty), 1), "max": round(average * (1 + uncertainty), 1)},
        "source_url": row["source_url"], "source_title": row["source_title"],
        "chart_url": row.get("chart_url", ""), "reference_gpu": source_gpu["name"],
        "reference_cpu": row["reference_cpu"], "reference_preset": row["preset_label"],
        "reference_resolution": row["resolution"], "reference_avg_fps": row["avg_fps"],
        "reference_low1_fps": row.get("low1_fps"), "published_at": row["published_at"],
        "collected_at": row["collected_at"], "low1_estimated": low_is_estimated,
        "notes": missing, "conditions": f"{row['resolution']}p · {row['preset_label']} · Native · RT/프레임 생성 OFF",
        "range_method": "heuristic_allowance_not_statistical_interval",
    }
    return round(average, 1), round(min(average, low), 1), evidence
