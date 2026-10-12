"""Explicit recommendation preferences. These never alter measured FPS."""
import re
from component_quality import recognized_brand

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
                     budget_fit, unlimited, ram_gb, cpu_loss, parts,
                     resolution="1080", cpu_price=None, gpu_price=None):
    # Selected-game average/1% Low attainment drives the recommendation.
    # Catalog targets are a secondary preference, including for capped games;
    # these utility weights never change the FPS prediction or source data.
    average_fit = min(1.0, max(0.0, fps_ratio))
    # Missing low evidence transfers this objective's weight to average
    # attainment. It is neither zero performance nor an invented low FPS.
    low_fit = average_fit if low1_ratio is None else min(1.0, max(0.0, low1_ratio))
    shortfall = 1.0 - min(average_fit, low_fit)
    cpu_price = max(0.0, float(parts['cpu'].get('price') or 0) if cpu_price is None else cpu_price)
    gpu_price = max(0.0, float(parts['gpu'].get('price') or 0) if gpu_price is None else gpu_price)
    cpu_share = cpu_price / max(1.0, cpu_price + gpu_price)
    # A soft preference, not a CPU cutoff: meaningful measured FPS/1% Low
    # gains can still justify a faster CPU in CPU-limited games.
    cpu_allowance = {"1080": .35, "1440": .28, "2160": .22}.get(resolution, .35)
    cpu_spending_penalty = min(1.2, max(0.0, cpu_share - cpu_allowance) * 3.0) if gpu_price else 0.0
    score = (4.0 * average_fit
             + 2.0 * low_fit
             + 1.6 * min(1.25, max(0.0, gpu_perf) / max(1.0, gpu_target))
             + 0.3 * min(1.0, ram_gb / 32.0)
             - shortfall * min(0.6, max(0.0, cpu_loss - 0.10) * 1.5)
             - cpu_spending_penalty)
    if not unlimited:
        score += 1.4 * budget_fit
    return score + 0.3 * build_preference(parts, "game")

def identity(part):
    return " ".join(str(part.get(k) or "") for k in ("product_name","name")).lower()


def preferred_ram_brand(part):
    """Recognized module maker, never the supplier of an incidental memory IC."""
    return recognized_brand(part, 'ram')


def preferred_ram_candidates(parts):
    """Keep cheap compatible fallbacks; quality is scored on the whole build."""
    return list(parts)

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
