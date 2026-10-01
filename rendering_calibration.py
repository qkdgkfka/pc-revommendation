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

CALIBRATION_PATH = Path(__file__).parent / "data/rendering_calibration.json"


def snapshot_quality_pairs(data):
    """Only pair native and Quality averages from the same reviewed conditions."""
    fields = ("game", "gpu_id", "cpu_id", "resolution", "preset", "source_url")
    pairs = []
    for row in data.get("graphics_measurements", []):
        if (row.get("mode") != "upscale" or row.get("generated")
                or row.get("ray_tracing") is True):
            continue
        label = row.get("upscaling") or row.get("label", "")
        match = re.fullmatch(r"(DLSS|FSR)(?: ([\d.]+))? Quality", label)
        if not match:
            continue
        technology = match[1]
        version = technology + " " + match[2] if match[2] else row.get("technology_version")
        if technology == "FSR" and not version:
            # A generic label cannot establish which FSR algorithm was measured.
            continue
        native = next((sample for sample in data.get("measurements", [])
                       if all(sample.get(key) == row.get(key) for key in fields)
                       and sample.get("ray_tracing") is False
                       and sample.get("frame_generation") is False
                       and sample.get("upscaling") == "native"), None)
        if native:
            pairs.append(dict(row, technology=technology, quality="Quality",
                              technology_version=version,
                              native_fps=native["avg_fps"], upscale_fps=row["avg_fps"],
                              conditions=row.get("note") or row.get("workload_note", "")))
    return pairs


@lru_cache(maxsize=1)
def calibration_data():
    from game_database import load_snapshot
    data=load_snapshot()
    if data is None:
        try:data=json.loads((Path(__file__).parent/"data/game_benchmarks.json").read_text(encoding="utf8"))
        except (OSError,ValueError):data={}
    try:
        reviewed = json.loads(CALIBRATION_PATH.read_text(encoding="utf8"))
    except (OSError, ValueError):
        reviewed = {}
    if not isinstance(data, dict): data = {}
    if not isinstance(reviewed, dict): reviewed = {}

    def valid(row,fields):
        try:
            return (isinstance(row, dict) and row.get("technology") in ("DLSS","FSR")
                    and isinstance(row.get("game"), str) and isinstance(row.get("gpu_id"), str)
                    and str(row.get("resolution")) in ("1080", "1440", "2160")
                    and row.get("source_url","").startswith("https://")
                    and re.fullmatch(r"[0-9a-f]{64}",row.get("evidence_sha256","")) is not None
                    and all(math.isfinite(float(row[k])) and float(row[k])>0 for k in fields))
        except (KeyError,TypeError,ValueError):return False
    # A native-data refresh must not erase independently reviewed SR/FG data.
    # An explicitly supplied snapshot field takes precedence, even when empty.
    fg = data.get("fg_calibration", reviewed.get("fg_calibration", []))
    upscale = list(data.get("upscale_calibration", reviewed.get("upscale_calibration", [])))
    upscale.extend(snapshot_quality_pairs(data))
    unique = {}
    for row in upscale:
        if valid(row, ("native_fps", "upscale_fps")):
            row = dict(row, native_fps=float(row["native_fps"]), upscale_fps=float(row["upscale_fps"]))
            key = tuple(row.get(k) for k in ("technology", "technology_version", "game", "gpu_id", "cpu_id", "resolution", "source_url"))
            unique[key] = row
    return {
        "fg_calibration":[dict(r, base_fps=float(r["base_fps"]), display_fps=float(r["display_fps"]))
                          for r in fg if valid(r,("base_fps","display_fps"))
                          and r.get("factor") in (2,3,4)
                          and float(r["display_fps"])<float(r["base_fps"])*r["factor"]],
        "upscale_calibration":list(unique.values()),
        "fsr_support":data.get("fsr_support", reviewed.get("fsr_support", {}))
    }

def profile(gpu):
    from server_catalogs import GPU_CATALOG
    ident=gpu.get("performance_ref_id") or gpu.get("id")
    return next((r for r in GPU_CATALOG if r["id"]==ident),gpu)

def selected_pairs(kind,technology,gpu,game,resolution,factor=None, *, cohort_generation=True, version=None):
    rows=[r for r in calibration_data()[kind] if r["technology"]==technology
          and (factor is None or r["factor"]==factor)
          and (technology != "FSR" or version is None
               or (r.get("technology_version") or "FSR 3") == version)]
    if not rows:return []
    target=profile(gpu)
    # Keep 2x and 4x on the same hardware-generation cohort: an older game's
    # DLSS3/RTX4070 pair must not supply 2x while DLSS4/RTX50 supplies 4x.
    if technology=="DLSS" and kind=="fg_calibration" and cohort_generation:
        generation=re.search(r"rtx([45])",target.get("id",""))
        same_gen=[r for r in rows if generation and "rtx"+generation[1] in r["gpu_id"]]
        if same_gen:rows=same_gen
    same_game=[r for r in rows if r["game"]==game]
    if same_game:rows=same_game
    if technology=="DLSS" and kind=="fg_calibration" and not cohort_generation:
        generation=re.search(r"rtx([45])",target.get("id",""))
        same_gen=[r for r in rows if generation and "rtx"+generation[1] in r["gpu_id"]]
        if same_gen:rows=same_gen
    # Resolution changes the SR workload materially. Prefer the requested
    # output resolution over another game's same-GPU chart at a different one.
    if kind == "upscale_calibration":
        same_res=[r for r in rows if str(r["resolution"])==str(resolution)]
        if same_res:rows=same_res
    same_gpu=[r for r in rows if r["gpu_id"]==target.get("id")]
    if same_gpu:rows=same_gpu
    same_res=[r for r in rows if r["resolution"]==str(resolution)]
    if same_res:rows=same_res
    return rows

def upscale_prediction(native,gpu,game,resolution,technology,bottleneck, *, version=None):
    if not math.isfinite(native) or native <= 0:return None
    samples=selected_pairs("upscale_calibration",technology,gpu,game,resolution,version=version)
    if not samples:return None
    time_ratio=median(r["native_fps"]/r["upscale_fps"] for r in samples)
    # Preserve CPU-limited work instead of multiplying total FPS by a GPU gain.
    cpu_fraction=min(1.,max(0.,float(bottleneck.get("cpu_penalty_pct") or 0)/100))
    frame_ms=1000/native*(cpu_fraction+(1-cpu_fraction)*time_ratio)
    value=1000/frame_ms
    cpu_limit=float(bottleneck.get("cpu_fps_ceiling") or value)
    value=min(value,max(native,cpu_limit))
    return value,samples


def calibration_context(samples, gpu, game, resolution):
    """Human-readable reference conditions, without claiming a matching scene."""
    scope = "same_game" if all(r["game"] == game for r in samples) else "cross_game"
    references = [{"game": r["game"], "gpu_id": r["gpu_id"], "resolution": str(r["resolution"]),
                   "conditions": r.get("conditions", ""), "source_url": r["source_url"]}
                  for r in samples]
    return dict(calibration_scope=scope, calibration_references=references,
                calibration_sample_count=len(samples),
                calibration_sources=sorted({r["source_url"] for r in samples}),
                calibration_basis=("동일 게임의 실측 기준" if scope == "same_game"
                                   else "다른 게임의 실측 기준 · 오차가 클 수 있음"),
                calibration_workload_note=("RT가 켜진 측정의 처리 비용을 반영한 추정" if any(
                    r.get("ray_tracing") or re.search(r"full ray|mandatory RT|ray.tracing", r.get("conditions", ""), re.I)
                    for r in samples) else ""),
                reference_resolution=" / ".join(sorted({str(r["resolution"]) for r in samples})))

def fg_prediction(base,gpu,game,resolution,technology,factor, *, cohort_generation=True, version=None):
    samples=selected_pairs("fg_calibration",technology,gpu,game,resolution,factor,
                          cohort_generation=cohort_generation,version=version)
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
                **calibration_context(samples, gpu, game, resolution),
                range={"min":round(display*.65,1),"max":round(min(display*1.25,base*max(r["display_fps"]/r["base_fps"] for r in samples)),1)})
