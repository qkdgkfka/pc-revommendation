"""Optional rendering scenarios; generated display FPS is not render FPS.

Exact RT/FG rows come from the same reviewed snapshot as native measurements.
Other scenarios are explicitly wide-range workload estimates, not benchmarks.
"""
from functools import lru_cache
import json
import re
from pathlib import Path
from rendering_calibration import calibration_data, upscale_prediction, fg_prediction, calibration_context

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
        from game_database import load_snapshot
        data = load_snapshot() or json.loads((Path(__file__).parent / "data/game_benchmarks.json").read_text(encoding="utf-8"))
        return tuple(r for r in data.get("graphics_measurements", []) if r.get("avg_fps", 0) > 0 and r.get("source_url", "").startswith("https://") and len(r.get("evidence_sha256", "")) == 64)
    except (OSError, ValueError, TypeError):
        return ()


@lru_cache(maxsize=1)
def feature_support():
    from game_database import load_snapshot
    data=load_snapshot()
    if data is None:
        try:data=json.loads((Path(__file__).parent/"data/game_benchmarks.json").read_text(encoding="utf8"))
        except (OSError,ValueError):data={}
    return data.get("feature_support", {})

def graphics_scenarios(gpu, cpu, game, resolution, fps, reference_estimator):
    native = float(fps["fps_by_option"]["high"])
    identity = " ".join(str(gpu.get(k) or "") for k in ("name", "id", "performance_ref_id")).lower()
    nvidia = "rtx" in identity
    amd = "rx" in identity
    technology = "DLSS" if nvidia else "FSR" if amd else None
    fsr_support = calibration_data()["fsr_support"].get(game,{})
    fg_capable = bool(re.search(r"rtx[\s_-]*[45]\d{3}", identity))
    mfg_capable = bool(re.search(r"rtx[\s_-]*50\d{2}", identity))
    rows = [{"id": "native", "label": "기본 · RT / FG 끔", "avg_fps": native,
             "technology": technology, "render_fps": native, "range": fps["fps_range_by_option"]["high"],
             "supported": True, "generated": False, "method": fps["fps_source"], "note": "풀옵 · 네이티브"}]
    support=feature_support().get(game)
    dlss = support["dlss"] if support is not None else game in DLSS_GAMES
    game_fg = support["fg"] if support is not None else game in DLSS_FG_GAMES
    game_mfg = support["mfg"] if support is not None else game in MFG_GAMES
    gpu_id=gpu.get("performance_ref_id") or gpu.get("id")
    cpu_id=cpu.get("performance_ref_id") or cpu.get("id")
    def closeness(row):
        return (str(row.get("resolution"))==str(resolution),row.get("gpu_id")==gpu_id,
                row.get("cpu_id")==cpu_id,row.get("preset")=="high")
    seen=set()
    for row in sorted(graphics_measurements(),key=closeness,reverse=True):
        if row["game"] != game or not nvidia or not dlss:
            continue
        if row["generated"] or row["mode"] != "upscale":
            continue
        if row["mode"] in seen:continue
        source_native = reference_estimator(row)
        target_native = float(fps["fps_by_option"].get(row["preset"],native))
        scale = target_native / source_native if source_native > 0 else 1.0
        value = round(row["avg_fps"] * scale, 1)
        exact = ((gpu.get("performance_ref_id") or gpu.get("id")) == row["gpu_id"]
                 and (cpu.get("performance_ref_id") or cpu.get("id")) == row["cpu_id"]
                 and str(resolution) == row["resolution"] and row["preset"] == "high"
                 and abs(target_native-source_native)<=.1)
        if not exact:continue
        seen.add(row["mode"])
        rows.append({"technology": technology, "id": row["mode"], "label": row["label"], "supported": True,
                     "avg_fps": row["avg_fps"] if exact else value,
                     "range": {"min": round(value * (.9 if exact else .65), 1), "max": round(value * (1.1 if exact else 1.35), 1)},
                     "render_fps": None if row["generated"] else value, "generated": row["generated"],
                     "method": "mode_measurement" if exact else "mode_calibrated_estimate",
                     "source_url": row["source_url"], "reference_resolution": row["resolution"], "preset_label":row.get("preset_label", row["preset"]),
                     "note": row["note"] + (" · 원문 구성 실측" if exact else " · 원문 GPU·CPU·해상도 대비 보정 추정")})

    upscaler = "DLSS Quality" if nvidia and dlss else (fsr_support.get("version","FSR")+" Quality") if amd and fsr_support.get("fsr") else None
    if upscaler:
        calibrated=next((row for row in rows if row["id"]=="upscale"),None)
        estimate=upscale_prediction(native,gpu,game,resolution,technology,fps.get("bottleneck") or {},
                                    version=fsr_support.get("version") if amd else None)
        if calibrated:
            render=calibrated["avg_fps"]
        elif estimate:
            render,samples=estimate
            render=round(render,1)
            rows.append({"id":"upscale","technology":technology,"label":upscaler,"supported":True,
                         "avg_fps":render,"render_fps":render,"generated":False,
                         "method":"mode_calibrated_estimate",
                         "range":{"min":round(min(native,render)*.8,1),"max":round(render*1.25,1)},
                         "source_url":samples[0]["source_url"],
                         **calibration_context(samples,gpu,game,resolution),
                         "note":"Quality 전후 실측 비율과 CPU 제한을 반영한 추정"})
        else:
            render=None
            rows.append({"id":"upscale_unavailable", "label":upscaler, "supported":False,
                         "avg_fps":None, "method":"unavailable", "unavailable_reason":"missing_evidence",
                         "note":"기능은 지원되지만 검증된 Quality 전후 측정 자료가 없습니다."})
        fg = (nvidia and fg_capable and game_fg) or (amd and fsr_support.get("fg") and bool(re.search(r"rx[\s_-]*[5679]\d{3}",identity)))
        if fg and render:
            for factor,key in [(2,"fg2")]+([(4,"mfg4")] if mfg_capable and game_mfg else []):
                prediction=fg_prediction(render,gpu,game,resolution,technology,factor,
                                         cohort_generation=bool(nvidia and mfg_capable and game_mfg),
                                         version=fsr_support.get("version") if amd else None)
                if prediction is None:
                    rows.append({"id":key+"_unavailable", "label":"MFG 4×" if factor==4 else "FG 2×",
                                 "supported":False, "avg_fps":None, "method":"unavailable",
                                 "unavailable_reason":"missing_evidence",
                                 "note":"이 배율의 검증된 프레임 생성 전후 측정 자료가 없습니다."})
                    continue
                rows.append(dict(prediction,id=key,technology=technology,
                    label=upscaler+(" + MFG 4×" if factor==4 else " + FG 2×"),
                    supported=True,generated=True,method="workload_estimate",
                    source_url=prediction["calibration_sources"][0],
                    support_note=("NVIDIA App 오버라이드가 필요할 수 있음" if nvidia and support and "NV" in support.get("mfg_note" if factor==4 else "fg_note","") else ""),
                    note="FG 전후 실측에서 구한 처리 시간으로 보정 · 다른 구성·장면은 추정"))
    if not any(row["id"] == "rt" or row["id"].startswith("rt_") for row in rows):
        rows.append({"id": "rt_unavailable", "label": "RT", "supported": False, "avg_fps": None, "method": "unavailable", "note": "이 게임·GPU의 검증된 RT 측정 자료 없음"})
    if not upscaler:
        rows.append({"id": "upscale_unavailable", "label": "DLSS / FSR · FG", "supported": False,
                     "avg_fps": None, "method": "unavailable", "unavailable_reason":"support_unconfirmed",
                     "note": "게임·GPU 조합의 해당 기능 지원이 확인되지 않음"})
    for row in rows:row.setdefault("technology",technology)
    return rows
