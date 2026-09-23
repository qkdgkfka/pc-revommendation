"""Pure product identity, manufacturer, capacity and component metadata helpers.

Retailer adapters and API serializers use these same rules. RAM's legacy `type`
field remains its DDR generation; `component_type` identifies the component.
Purchase-page URLs and `image_url` remain separate fields at every boundary.
"""
from __future__ import annotations

from html import unescape
import math
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from server_catalogs import COMMON_GPU_MODEL_NUMBERS

DANAWA_BROWSE_DEFAULT_QUERIES = {
    "cpu": "CPU",
    "gpu": "그래픽카드",
    "ram": "RAM 메모리",
    "mb": "메인보드",
    "storage": "SSD",
    "hdd": "HDD",
    "psu": "파워서플라이",
    "case": "PC 케이스",
    "software": "Windows 소프트웨어",
}

def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        x = float(v)
        if math.isnan(x) or math.isinf(x):
            return default
        return x
    except Exception:
        return default

def safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except Exception:
        return default

def normalize_text(v: Any) -> str:
    return " ".join(str(v or "").strip().lower().split())

def canonical_name(v: Any) -> str:
    t = normalize_text(v)
    for token in ["geforce", "radeon", "graphics", "graphic", "series", "desktop", "(tm)", "(r)", "processor"]:
        t = t.replace(token, "")
    return t.replace("  ", " ").strip()

def clean_visible_text(value: Any) -> str:
    return re.sub(r"\s+", " ", unescape(str(value or ""))).strip()

def parse_price_value(text: Any) -> Optional[int]:
    digits = re.sub(r"[^\d]", "", str(text or ""))
    if not digits:
        return None
    value = int(digits)
    return value if value >= 1000 else None

GPU_MAKER_ALIASES: Dict[str, Tuple[str, ...]] = {
    "msi": ("msi", "엠에스아이"),
    "gigabyte": ("gigabyte", "기가바이트"),
    "palit": ("palit", "팰릿", "팔릿"),
    "colorful": ("colorful", "컬러풀"),
    "asus": ("asus", "에이수스", "아수스"),
    "zotac": ("zotac", "조텍"),
    "galax": ("galax", "갤럭시"),
    "emtek": ("emtek", "이엠텍"),
    "inno3d": ("inno3d", "이노3d", "이노쓰리디"),
    "gainward": ("gainward", "게인워드"),
    "sapphire": ("sapphire", "사파이어"),
    "powercolor": ("powercolor", "파워컬러"),
    "xfx": ("xfx",),
    "asrock": ("asrock", "애즈락"),
    "biostar": ("biostar", "바이오스타"),
    "manli": ("manli", "만리"),
}

GPU_MAKER_LABELS: Dict[str, str] = {
    "msi": "MSI",
    "gigabyte": "Gigabyte",
    "palit": "Palit",
    "colorful": "Colorful",
    "asus": "ASUS",
    "zotac": "ZOTAC",
    "galax": "GALAX",
    "emtek": "Emtek",
    "inno3d": "INNO3D",
    "gainward": "Gainward",
    "sapphire": "Sapphire",
    "powercolor": "PowerColor",
    "xfx": "XFX",
    "asrock": "ASRock",
}

def gpu_maker_normalize(value: Any) -> str:
    text = normalize_text(strip_html(str(value or "")))
    compact = re.sub(r"[^0-9a-z가-힣]+", "", text)
    for key, aliases in GPU_MAKER_ALIASES.items():
        for alias in aliases:
            alias_norm = normalize_text(alias)
            alias_compact = re.sub(r"[^0-9a-z가-힣]+", "", alias_norm)
            if alias_norm and alias_norm in text:
                return key
            if alias_compact and alias_compact in compact:
                return key
    return ""

def normalize_gpu_maker_prefs(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = [x.strip() for x in re.split(r"[,/ ]+", value) if x.strip()]
    elif isinstance(value, list):
        raw_items = [str(x).strip() for x in value if str(x).strip()]
    else:
        raw_items = [str(value).strip()]
    out: List[str] = []
    for raw in raw_items:
        key = gpu_maker_normalize(raw) or normalize_text(raw)
        if key in {"any", "all", "none", "nopref", "무관", "선호없음"}:
            continue
        if key and key not in out:
            out.append(key)
    return out

def gpu_maker_label(key: str) -> str:
    return GPU_MAKER_LABELS.get(key, key.upper())

def query_model_name(query: Any) -> str:
    q = clean_visible_text(query)
    maker = gpu_maker_normalize(q)
    if maker:
        for alias in GPU_MAKER_ALIASES.get(maker, ()):
            q = re.sub(rf"\b{re.escape(alias)}\b", " ", q, flags=re.I)
        q = re.sub(r"\s+", " ", q).strip()
    # Danawa's GPU results are more reliable with the actual chip model than
    # with vendor marketing prefixes such as "NVIDIA GeForce" or "AMD Radeon".
    model = gpu_exact_model_key(q)
    if model:
        match = re.match(r"(rtx|gtx|rx)(\d{3,5})(tisuper|super|ti|xtx|xt|gre)?", model, re.I)
        if match:
            prefix, number, modifier = match.groups()
            suffix = {
                "tisuper": " Ti Super", "super": " Super", "ti": " Ti",
                "xtx": " XTX", "xt": " XT", "gre": " GRE",
            }.get((modifier or "").lower(), "")
            q = f"{prefix.upper()} {number}{suffix}"
            vram = re.search(r"\b(8|12|16|20|24|32)\s*gb\b", clean_visible_text(query), re.I)
            if vram:
                q += f" {vram.group(1)}GB"
    return q

def strip_html(value: str) -> str:
    return clean_visible_text(re.sub(r"<[^>]+>", " ", value or ""))

def normalize_browse_part_type(value: Any) -> str:
    key = normalize_text(value)
    aliases = {
        "memory": "ram", "ssd": "storage", "motherboard": "mb", "mainboard": "mb",
        "power": "psu", "chassis": "case",
    }
    key = aliases.get(key, key)
    return key if key in DANAWA_BROWSE_DEFAULT_QUERIES else ""

def parse_ram_metadata(text: Any) -> Dict[str, Any]:
    raw = clean_visible_text(text)
    lower = raw.lower()
    result: Dict[str, Any] = {}
    ram_type = re.search(r"\bddr\s*([45])\b", lower, re.I)
    if ram_type:
        result["type"] = f"DDR{ram_type.group(1)}"

    capacities = [safe_int(value, 0) for value in re.findall(r"\b(\d{1,3})\s*gb\b", lower, re.I)]
    kits = [
        safe_int(size, 0) * safe_int(count, 0)
        for size, count in re.findall(r"\b(\d{1,3})\s*gb\s*[x×*]\s*(\d+)\b", lower, re.I)
    ]
    capacity = max([value for value in capacities + kits if 4 <= value <= 512] or [0])
    if capacity:
        result["gb"] = capacity

    speed_match = re.search(r"\bddr\s*[45]\s*[- ]?(\d{4,5})\b", lower, re.I)
    if not speed_match:
        speed_match = re.search(r"\b(\d{4,5})\s*(?:mhz|mt/s|mts)\b", lower, re.I)
    speed = safe_int(speed_match.group(1), 0) if speed_match else 0
    if 1600 <= speed <= 10000:
        result["speed"] = speed
    return result

def capacity_mb_from_text(text: Any) -> int:
    raw = clean_visible_text(text).lower()
    values: List[int] = []
    for value in re.findall(r"\b(\d+(?:\.\d+)?)\s*tb\b", raw, re.I):
        try:
            values.append(int(float(value) * 1000))
        except Exception:
            pass
    values.extend(safe_int(value, 0) for value in re.findall(r"\b(\d{2,6})\s*gb\b", raw, re.I))
    valid = [value for value in values if 32 <= value <= 100_000]
    return max(valid) if valid else 0

def infer_cpu_metadata(text: Any) -> Dict[str, Any]:
    name = normalize_text(text)
    result: Dict[str, Any] = {}
    if "ryzen" in name or "amd" in name:
        result["vendor"] = "AMD"
        model = re.search(r"\b([56789]\d{3,4})(?:x3d|x|g|f)?\b", name, re.I)
        model_number = safe_int(model.group(1), 0) if model else 0
        if model_number >= 7000:
            result["socket"] = "AM5"
        elif model_number >= 1000:
            result["socket"] = "AM4"
    elif "intel" in name or "core" in name or "ultra" in name:
        result["vendor"] = "Intel"
        if "ultra" in name and re.search(r"\b[2-9]\d{2}[a-z]*\b", name):
            result["socket"] = "LGA1851"
        elif re.search(r"\bi[3579][ -]?(1[2-4]\d{3})[a-z]*\b", name, re.I):
            result["socket"] = "LGA1700"
    return result

def infer_mb_metadata(text: Any) -> Dict[str, Any]:
    name = normalize_text(text)
    result: Dict[str, Any] = {}
    if re.search(r"\b(?:a520|b450|b550|x470|x570)\b", name, re.I):
        result.update({"socket": "AM4", "ram_type": "DDR4"})
    elif re.search(r"\b(?:a620|b650|b850|x670|x870)\b", name, re.I):
        result.update({"socket": "AM5", "ram_type": "DDR5"})
    elif re.search(r"\b(?:h610|b660|b760|z690|z790)\b", name, re.I):
        result.update({"socket": "LGA1700", "ram_type": "DDR4" if "ddr4" in name else "DDR5"})
    elif re.search(r"\b(?:b860|z890)\b", name, re.I):
        result.update({"socket": "LGA1851", "ram_type": "DDR5"})
    return result

def infer_gpu_vram(text: Any) -> int:
    values = [safe_int(value, 0) for value in re.findall(r"\b(\d{1,2})\s*gb\b", clean_visible_text(text), re.I)]
    valid = [value for value in values if 4 <= value <= 64]
    return max(valid) if valid else 0

def infer_psu_watt(text: Any) -> int:
    values = [safe_int(value, 0) for value in re.findall(r"\b(\d{3,4})\s*w\b", clean_visible_text(text), re.I)]
    valid = [value for value in values if 300 <= value <= 3000]
    return max(valid) if valid else 0

def infer_hdd_rpm(text: Any) -> int:
    match = re.search(r"\b(5400|5900|7200)\s*(?:rpm)?\b", clean_visible_text(text), re.I)
    return safe_int(match.group(1), 0) if match else 0

def infer_brand(text: Any, fallback: str = "") -> str:
    name = clean_visible_text(text)
    if not name:
        return fallback
    known = [
        "ASUS", "ASRock", "AMD", "Antec", "Corsair", "Crucial", "ESSENCORE", "FSP",
        "GIGABYTE", "G.SKILL", "Intel", "Kingston", "KLEVV", "Lian Li", "Lexar", "MSI",
        "NVIDIA", "NZXT", "PALIT", "Samsung", "Seagate", "Seasonic", "SK hynix",
        "Toshiba", "Western Digital", "WD", "ZOTAC", "마이크로닉스", "이엠텍", "제이씨현",
    ]
    lower = name.lower()
    for brand in known:
        if brand.lower() in lower:
            return brand
    return name.split()[0] if name.split() else fallback

def normalize_product_url(url: Any) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
    except Exception:
        return raw.lower()

    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    path = re.sub(r"/+$", "", parts.path or "")
    query_items = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        k = key.lower()
        if k.startswith("utm_") or k in {"ref", "ref_src", "source", "spm", "gclid", "fbclid", "yclid", "igshid"}:
            continue
        query_items.append((key, value))
    query = urlencode(sorted(query_items), doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))

def model_tokens(v: Any) -> set:
    t = canonical_name(v)
    patterns = [
        r"\b(?:rtx|gtx|rx)\s*\d{3,5}\b",
        r"\bultra\s*[3579]?\s*\d{3}[a-z]*\b",
        r"\bi[3579][-\s]?\d{4,5}[a-z]*\b",
        r"\b(?:a|b|h|x|z)\d{3,4}\b",
        r"\bddr[45]\b",
        r"\b\d+\s*(?:gb|tb|w)\b",
        r"\b\d{4,5}x3d\b",
        r"\b\d{3}[a-z]\b",
        r"\b\d{4,5}[a-z]{0,3}\b",
    ]
    found = []
    for pattern in patterns:
        found.extend(re.findall(pattern, t))
    return {re.sub(r"[^a-z0-9]", "", x) for x in found}

def gpu_exact_model_key(v: Any) -> str:
    t = canonical_name(v).replace("-", " ")
    m = re.search(
        r"\b(rtx|gtx|rx)\s*([0-9]{3,5})\s*(ti\s*super|super|ti|xtx|xt|gre)?\b",
        t,
        re.I,
    )
    if not m:
        return ""
    prefix, number, modifier = m.group(1).lower(), m.group(2), re.sub(r"\s+", "", (m.group(3) or "").lower())
    return f"{prefix}{number}{modifier}"

def gpu_model_number_from_key(key: str) -> str:
    m = re.search(r"\d{3,5}", key or "")
    return m.group(0) if m else ""

def gpu_model_number_mentions(v: Any) -> set:
    t = canonical_name(v)
    return {number for number in COMMON_GPU_MODEL_NUMBERS if re.search(rf"(?<!\d){re.escape(number)}(?!\d)", t)}

def compatible_gpu_price_name(catalog_name: Any, price_name: Any) -> bool:
    catalog_key = gpu_exact_model_key(catalog_name)
    price_key = gpu_exact_model_key(price_name)
    if not catalog_key:
        return True
    if not price_key or catalog_key != price_key:
        return False
    target_number = gpu_model_number_from_key(catalog_key)
    extra_numbers = gpu_model_number_mentions(price_name) - ({target_number} if target_number else set())
    requested_vram = re.search(r"\b(\d+)\s*gb\b", canonical_name(catalog_name))
    listed_vram = re.search(r"\b(\d+)\s*gb\b", canonical_name(price_name))
    if requested_vram and (not listed_vram or requested_vram.group(1) != listed_vram.group(1)):
        return False
    return not extra_numbers

def variant_tokens(v: Any) -> set:
    words = set(canonical_name(v).replace("-", " ").split())
    return words & {"super", "ti", "xtx", "xt", "gre", "x3d", "kf", "f", "k", "u"}

def compatible_price_name(catalog_name: Any, price_name: Any) -> bool:
    """Reject a nearby model or a cheaper capacity/edition of the requested item.

    Retail names may translate brands, so compare the model and material specs
    instead of requiring every word in the English catalog name to appear.
    """
    requested = canonical_name(catalog_name)
    listed = canonical_name(price_name)
    if not requested or not listed:
        return False
    if gpu_exact_model_key(catalog_name):
        return compatible_gpu_price_name(catalog_name, price_name)

    def identifiers(text: str) -> set:
        text = re.sub(r"\bi[3579][-\s]*", " ", text)
        text = re.sub(r"\b(?:ddr\s*[45]|gddr\s*[567]|gen\s*[345]|pcie\s*[345]|atx)\b", " ", text)
        text = re.sub(r"\b\d+(?:\.\d+)?\s*(?:gb|tb|w|mhz|mt/s)\b", " ", text)
        # CPU numeric models, motherboard chipsets, SSD/case/PSU model codes.
        return set(re.findall(r"\b(?:[a-z]{1,10}\d+[a-z0-9]*|\d{3,5}[a-z]{0,3}(?:3d)?)\b", text))

    requested_models = identifiers(requested)
    listed_models = identifiers(listed)
    if requested_models and not requested_models.issubset(listed_models):
        return False

    requested_ram = parse_ram_metadata(requested)
    if requested_ram.get("type"):
        listed_ram = parse_ram_metadata(listed)
        for spec in ("type", "gb", "speed"):
            if requested_ram.get(spec) and requested_ram[spec] != listed_ram.get(spec):
                return False
    else:
        requested_capacity = capacity_mb_from_text(requested)
        if requested_capacity and requested_capacity != capacity_mb_from_text(listed):
            return False

    watts = re.search(r"\b(\d{3,4})\s*w\b", requested)
    if watts and not re.search(rf"\b{watts.group(1)}\s*w\b", listed):
        return False

    # Editions change price even when the principal model number is shared.
    edition_groups = [
        {"pro", "evo", "plus"}, {"home", "business"},
        {"fpp", "dsp", "oem", "esd"}, {"bronze", "gold", "platinum", "titanium"},
    ]
    for editions in edition_groups:
        wanted = set(re.findall(r"\b[a-z]+\b", requested)) & editions
        found = set(re.findall(r"\b[a-z]+\b", listed)) & editions
        if wanted and wanted != found:
            return False
    if "windows" in requested:
        version = re.search(r"windows\s*(\d+)", requested)
        if version and not re.search(rf"(?:windows|윈도우)\s*{version.group(1)}\b", listed):
            return False
    return True

def image_name_tokens(name: Any, part_type: str) -> set:
    """Normalize spelling/retail annotations only; never substitute a nearby model."""
    text = normalize_text(name)
    aliases = {
        "삼성전자": "samsung", "삼성": "samsung", "커세어": "corsair",
        "마이크론": "crucial", "micron": "crucial", "western digital": "wd",
        "웨스턴디지털": "wd", "sk 하이닉스": "skhynix", "sk hynix": "skhynix",
        "sk하이닉스": "skhynix", "팀그룹": "teamgroup", "마이크로닉스": "micronics",
        "기가바이트": "gigabyte", "에이수스": "asus", "애즈락": "asrock",
        "시소닉": "seasonic", "인텔": "intel", "라이젠": "ryzen",
    }
    for alias, value in aliases.items():
        text = text.replace(alias, value)
    # Kit count matters: a 16GB stick is not a 32GB (16x2) kit.
    text = re.sub(r"(\d+)\s*(?:gb|g)?\s*[x×*]\s*(\d+)", r" kit\1x\2 ", text)
    text = re.sub(r"\b(\d+)\s*(gb|tb|w)\b", r"\1\2", text)
    text = re.sub(r"\b(?:nvme|ssd|sata|gen\s*\d|m\.2|정품|벌크)\b", " ", text)
    text = re.sub(r"\b(ddr[345])[- ]?(\d{4,5})\b", r"\1 \2", text)
    if part_type == "cpu":
        text = re.sub(r"(?:ryzen|core)[ -]?(?:i?[3579])?", " ", text)
    if part_type == "psu":
        # Certifications may be present only in the spec table; the model and
        # ATX revision remain in the identity tokens.
        text = re.sub(r"80\s*(?:plus|\+)|gold|bronze|silver|platinum|titanium", " ", text)
        text = re.sub(r"atx\s*(\d)\.(\d)", r"atx\1\2", text)
    return set(re.findall(r"[a-z0-9가-힣]+", text))
