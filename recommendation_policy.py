"""Explicit recommendation preferences. These never alter measured FPS."""
import re

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
