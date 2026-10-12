"""Explicit recommendation preferences. These never alter measured FPS."""
import re

# A selected amount is a target; unlimited mode has no synthetic budget.
BUDGET_HEADROOM = 0.20


def budget_fit_score(total, target):
    if not target:
        return 1.0
    # Never reward spending more just to reach a minimum amount.
    return max(-1.0, 1.0 - max(0, total - target) / (target * 0.35))


def performance_fit(value, target):
    """Prefer meeting a tier's specification, with diminishing excess capacity."""
    ratio = max(0.0, value) / max(1.0, target)
    return min(1.0, ratio) - min(0.8, max(0.0, ratio - 1.0) * 0.6)


def gaming_gpu_target(resolution, refresh, tier):
    # Catalog performance indices, not FPS promises. 4K high-refresh anchors:
    # RTX 5070 Ti / RTX 5080 / RTX 5090 or comparable available hardware.
    if resolution == "2160" and refresh >= 120:
        return {"low": 52.0, "mid": 65.0, "high": 90.0}[tier]
    targets = {
        "1080": {"low": 46.0, "mid": 62.0, "high": 80.0},
        "1440": {"low": 38.0, "mid": 55.0, "high": 74.0},
        "2160": {"low": 32.0, "mid": 48.0, "high": 65.0},
    }
    return targets.get(resolution, targets["1080"])[tier] * (1.18 if refresh >= 144 else 1.08 if refresh >= 120 else 1.0)


def gaming_power_weights(resolution):
    return {"1080": (0.64, 0.24), "1440": (0.70, 0.18), "2160": (0.76, 0.12)}.get(resolution, (0.64, 0.24))


def gaming_objective(*, gpu_perf, gpu_target, fps_ratio, low1_ratio,
                     budget_fit, unlimited, ram_gb, cpu_loss, parts):
    # Hardware suitability differentiates tiers even for capped games. Actual
    # FPS/1% Low and CPU bottlenecks remain independent evidence, never edited.
    score = (4.0 * performance_fit(gpu_perf, gpu_target)
             + 2.0 * min(1.0, fps_ratio)
             + 0.7 * min(1.0, low1_ratio)
             + 0.3 * min(1.0, ram_gb / 32.0)
             - min(0.6, max(0.0, cpu_loss - 0.10) * 1.5))
    if not unlimited:
        score += 1.4 * budget_fit
    return score + 0.3 * build_preference(parts, "game")

def identity(part):
    return " ".join(str(part.get(k) or "") for k in ("product_name","name")).lower()

def cpu_vendor(part):
    name=identity(part)
    # Retail names take precedence over stale/inconsistent derived metadata.
    if re.search(r"intel|인텔|코어|core",name):return "intel"
    if re.search(r"amd|ryzen|라이젠",name):return "amd"
    return str(part.get("vendor") or "").lower()

def intel_generation(part):
    name=identity(part)
    if re.search(r"(?:ultra|울트라).*?(?<![0-9])2[0-9]{2}(?:k|kf|f|t)?(?![a-z0-9])",name):
        return 15  # Internal ordering only; public name is Core Ultra 200S.
    models=re.findall(r"(?<![a-z0-9])([0-9]{4,5})(?:kf|k|f|t|s)?(?![a-z0-9])",name)
    generations=[int(n[:2]) for n in models if len(n)==5 and n.startswith(("10","11","12","13","14"))]
    return max(generations,default=0)

def cpu_allowed(part):
    vendor=cpu_vendor(part)
    if vendor=="intel":return intel_generation(part)>=13
    # A legacy Intel socket cannot become AMD through stale name matching.
    if str(part.get("socket","")).upper().startswith("LGA"):return False
    return vendor=="amd"

def cpu_preference(part, mode):
    if cpu_vendor(part)=="amd":return .10 if mode=="game" else 0.0
    return .05 if intel_generation(part)>=15 else .015 if intel_generation(part)==14 else 0.0

def gpu_product_band(part):
    name=identity(part)
    # Auditable product-family preference, not a claim about measured quality.
    if re.search(r"\b(?:suprim|strix|aorus|nitro|trio)\b|hall of fame",name):return "premium"
    if re.search(r"\b(?:phoenix|aero itx|shadow)\b",name):return "entry"
    if re.search(r"\b(?:ventus|dual|prime|eagle|pulse|swift|qick|twin edge|windforce)\b|gaming oc",name):return "preferred"
    return "unknown"

def gpu_preference(part):
    return {"preferred":.06,"unknown":.02,"entry":0.0,"premium":.005}[gpu_product_band(part)]

def storage_preference(part):
    name=identity(part)+" "+str(part.get("interface") or "").lower()
    if "sata" in name:return .01 if re.search(r"m[. ]?2",name) else 0.0
    if "nvme" in name or re.search(r"m[. ]?2",name):return .07
    return 0.0

def build_preference(parts, mode):
    return cpu_preference(parts["cpu"],mode)+gpu_preference(parts["gpu"])+storage_preference(parts["storage"])

def objective_score(base_score, fps_ratio, parts, mode):
    if mode=="game":
        base_score=4.0*min(1.0,fps_ratio)+(1.0 if fps_ratio>=1.0 else 0.0)+.25*base_score
    return base_score+build_preference(parts,mode)
