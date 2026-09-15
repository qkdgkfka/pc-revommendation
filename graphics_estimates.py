"""Optional rendering scenarios; generated display FPS is not render FPS.

Exact RT/FG rows come from the same reviewed snapshot as native measurements.
Other scenarios are explicitly wide-range workload estimates, not benchmarks.
"""
from functools import lru_cache
import json
import re
from pathlib import Path

NVIDIA_SOURCE = "https://www.nvidia.com/en-us/geforce/news/dlss-4-multi-frame-generation-out-now/"
AMD_SOURCE = "https://www.amd.com/en/products/graphics/technologies/fidelityfx/supported-games.html"
# Feature support is game specific. Competitive games without these features
# must never receive an invented DLSS/FG uplift.
DLSS_GAMES = {"cyberpunk2077", "hogwarts_legacy", "marvel_rivals", "alan_wake2", "black_myth_wukong", "starfield", "dragons_dogma2", "dying_light2", "witcher3", "ghost_of_tsushima", "horizon_forbidden_west", "god_of_war_ragnarok", "baldurs_gate3", "red_dead_redemption2", "fortnite", "cod_black_ops6"}
DLSS_FG_GAMES = DLSS_GAMES - {"baldurs_gate3", "red_dead_redemption2", "fortnite", "cod_black_ops6"}
MFG_GAMES = {"cyberpunk2077", "hogwarts_legacy", "marvel_rivals", "alan_wake2", "black_myth_wukong", "starfield", "dragons_dogma2", "dying_light2", "god_of_war_ragnarok"}
FSR_GAMES = DLSS_GAMES - {"fortnite"}
FSR_FG_GAMES = {"cyberpunk2077", "starfield", "ghost_of_tsushima", "horizon_forbidden_west", "god_of_war_ragnarok", "marvel_rivals"}


@lru_cache(maxsize=1)
def graphics_measurements():
    try:
        data = json.loads((Path(__file__).parent / "data/game_benchmarks.json").read_text())
        return tuple(r for r in data.get("graphics_measurements", []) if r.get("avg_fps", 0) > 0 and r.get("source_url", "").startswith("https://") and len(r.get("evidence_sha256", "")) == 64)
    except (OSError, ValueError, TypeError):
        return ()


def graphics_scenarios(gpu, cpu, game, resolution, fps, reference_estimator):
    native = float(fps["fps_by_option"]["high"])
    identity = " ".join(str(gpu.get(k) or "") for k in ("name", "id", "performance_ref_id")).lower()
    nvidia = "rtx" in identity
    amd = "rx" in identity
    fg_capable = bool(re.search(r"rtx[\s_-]*[45]\d{3}", identity))
    mfg_capable = bool(re.search(r"rtx[\s_-]*50\d{2}", identity))
    rows = [{"id": "native", "label": "기본 · RT / FG 끔", "avg_fps": native,
             "render_fps": native, "range": fps["fps_range_by_option"]["high"],
             "supported": True, "generated": False, "method": fps["fps_source"], "note": "고옵 · 네이티브"}]
    for row in graphics_measurements():
        if row["game"] != game or not nvidia:
            continue
        if row["generated"] and not fg_capable:
            continue
        existing = next((r for r in rows if r["id"] == row["mode"]), None)
        if existing and existing.get("reference_resolution") == resolution:
            continue
        if existing:
            rows.remove(existing)
        source_native = reference_estimator(row)
        target_native = float(fps["fps_by_option"][row["preset"]])
        scale = target_native / source_native if source_native > 0 else 1.0
        value = round(row["avg_fps"] * scale, 1)
        exact = ((gpu.get("performance_ref_id") or gpu.get("id")) == row["gpu_id"]
                 and (cpu.get("performance_ref_id") or cpu.get("id")) == row["cpu_id"]
                 and str(resolution) == row["resolution"])
        rows.append({"id": row["mode"], "label": row["label"], "supported": True,
                     "avg_fps": row["avg_fps"] if exact else value,
                     "range": {"min": round(value * (.9 if exact else .65), 1), "max": round(value * (1.1 if exact else 1.35), 1)},
                     "render_fps": None if row["generated"] else value, "generated": row["generated"],
                     "method": "mode_measurement" if exact else "mode_calibrated_estimate",
                     "source_url": row["source_url"], "reference_resolution": row["resolution"],
                     "note": row["note"] + (" · 원문 구성 실측" if exact else " · 원문 GPU·CPU·해상도 대비 보정 추정")})

    upscaler = "DLSS Quality" if nvidia and game in DLSS_GAMES else "FSR Quality" if amd and game in FSR_GAMES else None
    if upscaler:
        # Model reduced pixel work, retaining CPU-limited work and overhead.
        # The range, not the midpoint, is the useful precision of this scenario.
        cpu_loss = float((fps.get("bottleneck") or {}).get("cpu_penalty_pct") or 0) / 100
        gain = 1 + {"1080": .20, "1440": .32, "2160": .45}[resolution] * (1 - min(.95, cpu_loss))
        render = round(native * gain, 1)
        source = NVIDIA_SOURCE if nvidia else AMD_SOURCE
        rows.append({"id": "upscale", "label": upscaler, "supported": True, "avg_fps": render, "render_fps": render,
                     "range": {"min": round(native * .95, 1), "max": round(render * 1.25, 1)},
                     "generated": False, "method": "workload_estimate", "source_url": source,
                     "note": "실측 아님 · Quality 렌더링 부하와 CPU 병목을 반영한 대략적 범위 · 링크는 지원 정보"})
        fg = (nvidia and fg_capable and game in DLSS_FG_GAMES) or (amd and game in FSR_FG_GAMES)
        if fg:
            for factor, key in [(2, "fg2")] + ([(4, "mfg4")] if mfg_capable and game in MFG_GAMES else []):
                render_after = round(render * .90, 1)
                displayed = round(render_after * factor, 1)
                rows.append({"id": key, "label": upscaler + (" + MFG 4×" if factor == 4 else " + FG 2×"),
                             "supported": True, "avg_fps": displayed, "render_fps": render_after,
                             "range": {"min": round(displayed * .7, 1), "max": round(displayed * 1.2, 1)},
                             "generated": True, "method": "workload_estimate", "source_url": source,
                             "note": "실측 아님 · 생성 프레임 포함 표시 FPS · 조작 응답성은 실제 렌더 FPS 기준" + (" · 기본 FPS가 낮아 FG 효과 제한" if render_after < 50 else "")})
    if not any(row["id"] == "rt" or row["id"].startswith("rt_") for row in rows):
        rows.append({"id": "rt_unavailable", "label": "RT", "supported": False, "avg_fps": None, "method": "unavailable", "note": "이 게임·GPU의 검증된 RT 측정 자료 없음"})
    if not upscaler:
        rows.append({"id": "upscale_unavailable", "label": "DLSS / FSR · FG", "supported": False, "avg_fps": None, "method": "unavailable", "note": "게임·GPU 조합의 해당 기능 지원이 확인되지 않음"})
    return rows
