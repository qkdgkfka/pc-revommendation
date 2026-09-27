"""Frame-time estimates calibrated from paired SR and FG observations.

Effective overhead includes scheduling/presentation work; it is not a latency
measurement. Cross-game/hardware predictions remain estimates with heuristic
bounds. DLSS and FSR observations are never pooled together.
"""
from functools import lru_cache
from pathlib import Path
from statistics import median
import json
import math
import re

@lru_cache(maxsize=1)
def calibration_data():
    from game_database import load_snapshot
    data=load_snapshot()
    if data is None:
        try:data=json.loads((Path(__file__).parent/"data/game_benchmarks.json").read_text(encoding="utf8"))
        except (OSError,ValueError):data={}
    def valid(row,fields):
        try:
            return (row.get("technology") in ("DLSS","FSR")
                    and row.get("source_url","").startswith("https://")
                    and re.fullmatch(r"[0-9a-f]{64}",row.get("evidence_sha256","")) is not None
                    and all(math.isfinite(float(row[k])) and float(row[k])>0 for k in fields))
        except (KeyError,TypeError,ValueError):return False
    return {
        "fg_calibration":[r for r in data.get("fg_calibration",[]) if valid(r,("base_fps","display_fps"))
                          and r.get("factor") in (2,3,4)
                          and r["display_fps"]<r["base_fps"]*r["factor"]],
        "upscale_calibration":[r for r in data.get("upscale_calibration",[]) if valid(r,("native_fps","upscale_fps"))],
        "fsr_support":data.get("fsr_support",{})
    }

def profile(gpu):
    from server_catalogs import GPU_CATALOG
    ident=gpu.get("performance_ref_id") or gpu.get("id")
    return next((r for r in GPU_CATALOG if r["id"]==ident),gpu)

def selected_pairs(kind,technology,gpu,game,resolution,factor=None):
    rows=[r for r in calibration_data()[kind] if r["technology"]==technology
          and (factor is None or r["factor"]==factor)]
    if not rows:return []
    target=profile(gpu)
    # Keep 2x and 4x on the same hardware-generation cohort: an older game's
    # DLSS3/RTX4070 pair must not supply 2x while DLSS4/RTX50 supplies 4x.
    if technology=="DLSS" and kind=="fg_calibration":
        generation=re.search(r"rtx([45])",target.get("id",""))
        same_gen=[r for r in rows if generation and "rtx"+generation[1] in r["gpu_id"]]
        if same_gen:rows=same_gen
    same_game=[r for r in rows if r["game"]==game]
    if same_game:rows=same_game
    same_gpu=[r for r in rows if r["gpu_id"]==target.get("id")]
    if same_gpu:rows=same_gpu
    same_res=[r for r in rows if r["resolution"]==str(resolution)]
    if same_res:rows=same_res
    return rows

def upscale_prediction(native,gpu,game,resolution,technology,bottleneck):
    samples=selected_pairs("upscale_calibration",technology,gpu,game,resolution)
    if not samples:return None
    time_ratio=median(r["native_fps"]/r["upscale_fps"] for r in samples)
    # Preserve CPU-limited work instead of multiplying total FPS by a GPU gain.
    cpu_fraction=min(1.,max(0.,float(bottleneck.get("cpu_penalty_pct") or 0)/100))
    frame_ms=1000/native*(cpu_fraction+(1-cpu_fraction)*time_ratio)
    value=1000/frame_ms
    cpu_limit=float(bottleneck.get("cpu_fps_ceiling") or value)
    value=min(value,max(native,cpu_limit))
    return value,samples

def fg_prediction(base,gpu,game,resolution,technology,factor):
    samples=selected_pairs("fg_calibration",technology,gpu,game,resolution,factor)
    if not samples or not math.isfinite(base) or base<=0:return None
    target=profile(gpu)
    target_perf=float(target.get("perf_2160") or 0)
    costs=[]
    for row in samples:
        cost=1000*factor/row["display_fps"]-1000/row["base_fps"]
        source=profile({"id":row["gpu_id"]})
        source_perf=float(source.get("perf_2160") or 0)
        # Pixel count and catalog throughput are extrapolation assumptions,
        # not measurements of tensor/optical-flow throughput.
        pixel_scale=(int(resolution)/int(row["resolution"]))**2
        hardware_scale=source_perf/target_perf if source_perf and target_perf else 1.
        costs.append(cost*pixel_scale*hardware_scale)
    cost=median(costs)
    display=factor*1000/(1000/base+cost)
    # Outside original conditions do not extrapolate beyond the observed
    # median gain. This also avoids near-4x claims at low base FPS.
    gain_limit=median(r["display_fps"]/r["base_fps"] for r in samples)
    display=min(display,base*gain_limit)
    effective_cost=1000*factor/display-1000/base
    return dict(avg_fps=round(display,1),render_fps=round(display/factor,1),
                base_render_fps=round(base,1),overhead_ms=round(effective_cost,3),
                calibration_overhead_ms=round(cost,3),
                observed_gain_limit=round(gain_limit,3),
                calibration_sources=sorted({r["source_url"] for r in samples}),
                calibration_sample_count=len(samples),
                range={"min":round(display*.65,1),"max":round(min(display*1.25,base*max(r["display_fps"]/r["base_fps"] for r in samples)),1)})
