"""Compatible candidate ranking and ordered PC recommendations."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from dataclasses import dataclass
import json
import math
import random
import re
import copy
import time
from threading import RLock
from market_catalog import saved_products
from product_metadata import (
    canonical_name,
    gpu_exact_model_key,
    gpu_maker_label,
    gpu_maker_normalize,
    normalize_gpu_maker_prefs,
    normalize_text,
    safe_float,
    safe_int,
)
from product_images import fetch_product_image, retailer_image_url, product_page_key
from component_compatibility import platform_compatibility
from typing import Any, Dict, List, Optional, Tuple
from recommendation_policy import (
    cpu_allowed,
    cpu_preference,
    gpu_product_band,
    gpu_preference,
    storage_preference,
    BUDGET_HEADROOM,
    budget_fit_score,
    performance_fit,
    gaming_gpu_target,
    gaming_power_weights,
    gaming_objective,
    build_preference,
)
from server_catalogs import (
    CPU_CATALOG,
    GPU_CATALOG,
    RAM_CATALOG,
    MB_CATALOG,
    PSU_CATALOG,
    STORAGE_CATALOG,
    CATALOGS,
    WORK_PROFILES,
    WORK_ALIASES,
)
from . import runtime as state
from . import database
from . import fps as fps_service
from . import pricing
from . import retail
from . import utils
from .cache import SingleFlight
from .revisions import data_revision, fingerprint, freshness_ttl

_recommend_flight = SingleFlight(max_pending=64)
_recommend_cache_lock = RLock()


def _recommend_key(request):
    import graphics_estimates
    import rendering_calibration
    dependencies = (id(verified_recommendation_inventory), id(saved_products),
                    id(fetch_product_image), id(fps_service.estimate_from_measurements),
                    id(graphics_estimates.calibration_data), id(graphics_estimates.graphics_measurements),
                    id(graphics_estimates.feature_support), id(rendering_calibration.calibration_data))
    return (json.dumps(request.as_payload(include_market_prices=False), sort_keys=True, ensure_ascii=False),
            data_revision(), fingerprint(CATALOGS), dependencies)


def score_gpu(part: Dict[str, Any], budget: int, resolution: str, tier: str, game: str, refresh: int, genres: List[str], rng: random.Random) -> float:
    price = max(1, fps_service.part_price(part, "gpu"))
    perf = fps_service.gpu_base_perf(part, resolution)
    genre_class, _ = pricing.game_profile(game)
    target_price = budget * (0.40 if resolution == "1080" else 0.49 if resolution == "1440" else 0.58)
    price_fit = 1.0 - min(1.0, abs(price - target_price) / max(1.0, target_price))
    target_perf = gaming_gpu_target(resolution, refresh, tier)
    perf_fit = performance_fit(perf, target_perf)
    if not budget:
        return perf_fit + 0.05 * gpu_preference(part)
    res_bonus = 0.16 if resolution == "2160" and perf >= 50 else 0.08 if resolution == "1440" else 0.04
    refresh_bonus = 0.08 if refresh >= 144 and resolution == "1080" else 0.03 if refresh >= 120 else 0.0
    tier_match = 0.08 if part.get("tier") == tier else 0.0
    db_bonus = 0.08 if fps_service.db_lookup_benchmarks(part, game) else 0.0
    value_bonus = retail.clamp((perf / max(1.0, price / 100000.0)) / 4.0, 0.0, 0.18)
    if genre_class == "fps" and resolution == "1080":
        value_bonus += 0.03
    if genre_class == "sim":
        value_bonus -= 0.02
    return (0.23 * price_fit + 0.53 * perf_fit + res_bonus + refresh_bonus + tier_match + db_bonus + value_bonus + gpu_preference(part))

def score_cpu(part: Dict[str, Any], budget: int, resolution: str, refresh: int, tier: str, game: str, rng: random.Random) -> float:
    price = max(1, fps_service.part_price(part, "cpu"))
    perf = safe_float(part.get("perf"), 0.0)
    if not budget:
        target = {"low": 70, "mid": 84, "high": 98}[tier]
        return performance_fit(perf, target) + 0.05 * cpu_preference(part, "game")
    target_price = budget * (0.23 if resolution == "1080" else 0.17 if resolution == "1440" else 0.13)
    if refresh >= 144 and resolution == "1080":
        target_price *= 1.10
    price_fit = 1.0 - min(1.0, abs(price - target_price) / max(1.0, target_price))
    perf_score = perf / 100.0
    tier_bonus = 0.08 if part.get("tier") == tier else 0.03 if (tier == "low" and part.get("tier") == "mid") or (tier == "mid" and part.get("tier") == "high") else 0.0
    game_class, _ = pricing.game_profile(game)
    genre_bonus = 0.07 if game_class in {"fps", "mmo"} and refresh >= 120 else 0.04 if game_class == "sim" else 0.0
    return (0.48 * price_fit + 0.32 * perf_score + tier_bonus + genre_bonus + cpu_preference(part, "work"))

def score_ram(part: Dict[str, Any], budget: int, resolution: str, tier: str, game: str, rng: random.Random) -> float:
    price = max(1, fps_service.part_price(part, "ram"))
    gb = safe_float(part.get("gb"), 0.0)
    if not budget:
        return performance_fit(gb, 32)
    target_price = budget * (0.11 if resolution == "1080" else 0.10 if resolution == "1440" else 0.09)
    price_fit = 1.0 - min(1.0, abs(price - target_price) / max(1.0, target_price))
    size_score = 0.45 if gb >= 64 else 0.32 if gb >= 32 else 0.20
    tier_bonus = 0.06 if part.get("tier") == tier else 0.03
    return (0.58 * price_fit + size_score + tier_bonus)


def score_storage(part: Dict[str, Any], budget: int, resolution: str, tier: str, rng: random.Random) -> float:
    price = max(1, fps_service.part_price(part, "storage"))
    target_price = budget * (0.12 if tier == "low" else 0.11 if tier == "mid" else 0.10)
    price_fit = 1.0 - min(1.0, abs(price - target_price) / max(1.0, target_price))
    capacity = safe_float(part.get("capacity"), 0.0)
    cap_score = 0.42 if capacity >= 2000 else 0.28 if capacity >= 1000 else 0.16
    tier_bonus = 0.04 if part.get("tier") == tier else 0.01
    return (0.52 * price_fit + cap_score + tier_bonus + storage_preference(part))

def filter_compatible_mb(cpu_pool: List[Dict[str, Any]], mb_pool: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [board for board in mb_pool if any(platform_compatibility(cpu, board)["compatible"] for cpu in cpu_pool)]

def filter_compatible_ram(mb_pool: List[Dict[str, Any]], ram_pool: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ramtypes = {normalize_text(m.get("ram_type")) for m in mb_pool if m.get("ram_type")}
    out = [r for r in ram_pool if normalize_text(r.get("type")) in ramtypes]
    return out

def tier_rank(value: Any) -> int:
    return state.TIER_RANK.get(normalize_text(value), 1)

def part_tags(part: Dict[str, Any]) -> set:
    return {normalize_text(x) for x in (part.get("tags") or [])}

def is_desktop_cpu(part: Dict[str, Any]) -> bool:
    tags = part_tags(part)
    socket = normalize_text(part.get("socket"))
    return socket not in {"bga1744"} and not ({"mobile", "u_series", "low_power"} & tags)

def is_desktop_mb(part: Dict[str, Any]) -> bool:
    tags = part_tags(part)
    socket = normalize_text(part.get("socket"))
    return socket not in {"bga1744"} and not ({"mobile", "u_series"} & tags)

def cached_part_price(part: Dict[str, Any], part_type: str, cache: Dict[Tuple[str, str], int]) -> int:
    key = (normalize_text(part_type), str(part.get("id") or canonical_name(part.get("name"))))
    if key not in cache:
        cache[key] = fps_service.part_price(part, part_type)
    return cache[key]

def tier_budget_for_user(budget: int, tier: str, budget_min: int = 0) -> int:
    """Place LOW/MID/HIGH inside the selected budget range, not above it."""
    budget_max = max(300000, safe_int(budget, 1500000))
    lower = max(0, safe_int(budget_min, 0))
    if lower > 0 and lower < budget_max:
        span = budget_max - lower
        return lower + int(span * {"low": 0.30, "mid": 0.65, "high": 1.00}.get(tier, 1.00))
    return max(300000, int(budget_max * {"low": 0.55, "mid": 0.80, "high": 1.00}[tier]))

def recommended_psu_watt(cpu: Dict[str, Any], gpu: Dict[str, Any]) -> int:
    need = safe_float(cpu.get("tdp"), 65.0) + safe_float(gpu.get("tdp"), 150.0) + 180.0
    return int(math.ceil(need / 50.0) * 50)

def build_power_score(parts: Dict[str, Dict[str, Any]], resolution: str) -> float:
    gpu = parts.get("gpu") or {}
    cpu = parts.get("cpu") or {}
    ram = parts.get("ram") or {}
    storage = parts.get("storage") or {}
    gpu_score = retail.clamp(fps_service.gpu_base_perf(gpu, resolution) / 100.0, 0.0, 1.12) * 100.0
    cpu_score = retail.clamp(safe_float(cpu.get("perf"), 0.0) / 100.0, 0.0, 1.08) * 100.0
    ram_score = retail.clamp(safe_float(ram.get("gb"), 16.0) / 64.0, 0.0, 1.0) * 100.0
    storage_score = retail.clamp(safe_float(storage.get("capacity"), 1000.0) / 2000.0, 0.0, 1.0) * 100.0
    gpu_weight, cpu_weight = gaming_power_weights(resolution)
    return round(gpu_weight * gpu_score + cpu_weight * cpu_score + 0.08 * ram_score + 0.04 * storage_score, 3)

def target_power_score(tier: str, resolution: str, refresh: int) -> float:
    targets = {
        "1080": {"low": 42.0, "mid": 56.0, "high": 70.0},
        "1440": {"low": 32.0, "mid": 46.0, "high": 60.0},
        "2160": {"low": 22.0, "mid": 34.0, "high": 48.0},
    }
    target = targets.get(resolution, targets["1080"])[tier]
    if refresh >= 144:
        target += 5.0 if resolution == "1080" else 3.0
    elif refresh >= 120:
        target += 2.0
    return target


def price_sum_for_parts(parts: Dict[str, Dict[str, Any]], price_cache: Dict[Tuple[str, str], int]) -> int:
    return sum(
        cached_part_price(part, part_type, price_cache)
        for part_type, part in parts.items()
        if isinstance(part, dict) and part_type in {"cpu", "gpu", "ram", "mb", "psu", "storage"}
    )

def verified_recommendation_inventory() -> Dict[str, List[Dict[str, Any]]]:
    """Only observed retail SKUs with usable specs and a fetched real photograph."""
    kinds = ("cpu", "gpu", "ram", "mb", "psu", "storage")
    inventory = {kind: [] for kind in kinds}
    required = {
        "cpu": ("perf", "socket", "tdp"), "gpu": ("perf_1080", "perf_1440", "perf_2160", "vram", "tdp"),
        "ram": ("type", "gb", "speed"), "mb": ("socket", "ram_type"),
        "psu": ("watt",), "storage": ("capacity",),
    }
    def candidates(kind):
        response = retail.market_products_response(kind, source="all", limit=40)
        rows = {product_page_key(row.get("url")): dict(row) for row in saved_products(kind)}
        rows.update({product_page_key(row.get("url")): dict(row) for row in response["items"]})
        selected, groups = [], {}
        for row in sorted(rows.values(), key=lambda r: (-gpu_preference(r) if kind=="gpu" else 0, safe_int(r.get("price"), 0))):
            name = row.get("product_name") or row.get("name") or ""
            if not (database.verified_price_info(row) and retail.retail_quote_valid(kind, name, row)
                    and all(row.get(field) for field in required[kind])
                    and retailer_image_url(row.get("image_url"))):
                continue
            if kind == "cpu" and not cpu_allowed(row):
                continue
            if kind == "gpu" and not pricing.is_recommendable_gpu(row):
                continue
            # Keep platform/capacity diversity without downloading every retailer SKU.
            group = ((row.get("performance_ref_id") or name), gpu_maker_normalize(name) if kind == "gpu" else "") if kind in {"cpu", "gpu"} else tuple(row.get(field) for field in required[kind])
            if kind == "gpu":group = (*group, gpu_product_band(row))
            if kind == "mb":
                chipset = re.search(r"(?<![A-Z0-9])([ABHXZ]\d{3}E?)(?=[^A-Z0-9]|M|I|$)", name.upper())
                group = (row.get("socket"), row.get("ram_type"), chipset.group(1) if chipset else name)
            if groups.get(group, 0) >= 2:
                continue
            groups[group] = groups.get(group, 0) + 1
            row["scraped_at"] = row.get("price_checked_at") or row.get("scraped_at")
            selected.append(row)
        # Sample across the price range instead of discarding all later/high-end models.
        limit = 128 if kind in {"cpu", "gpu"} else 48
        if len(selected) > limit:
            selected = [selected[round(i * (len(selected) - 1) / (limit - 1))] for i in range(limit)]
        return selected

    def photograph(kind, part):
        photo = fetch_product_image(part["image_url"])
        if not photo or photo[1] not in {"image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"}:
            return None
        return kind, part

    early_photos = ThreadPoolExecutor(max_workers=4)
    executor = ThreadPoolExecutor(max_workers=16)
    pending = []
    try:
        # Overlap a bounded amount of photo work with seller lookup. At handover,
        # retain running work but move queued photos to the original category
        # order, so a fast GPU batch cannot starve a later CPU/board category.
        photos_by_kind = {}
        with ThreadPoolExecutor(max_workers=6) as sellers:
            batches = {sellers.submit(candidates, kind): kind for kind in kinds}
            for batch in as_completed(batches):
                kind = batches[batch]
                photos_by_kind[kind] = [(part, early_photos.submit(photograph, kind, part))
                                        for part in batch.result()]
        for kind in kinds:
            for part, future in photos_by_kind[kind]:
                pending.append(executor.submit(photograph, kind, part) if future.cancel() else future)
        for future in as_completed(pending, timeout=12):
            result = future.result()
            if result:
                kind, part = result
                inventory[kind].append(part)
    except TimeoutError:
        pass  # Incomplete photo verification never creates a recommendation candidate.
    finally:
        early_photos.shutdown(wait=False, cancel_futures=True)
        executor.shutdown(wait=False, cancel_futures=True)
    for rows in inventory.values():
        rows.sort(key=lambda row: (row["price"], row["id"]))
    return inventory

def tier_component_pools(
    tier: str,
    resolution: str,
    refresh: int,
    gpu_pref: str,
    inventory: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    mode: str = "game",
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    source = {"cpu": CPU_CATALOG, "gpu": GPU_CATALOG, "ram": RAM_CATALOG,
              "mb": MB_CATALOG, "psu": PSU_CATALOG, "storage": STORAGE_CATALOG} if inventory is None else inventory
    cpu_pool = [p for p in source.get("cpu", []) if is_desktop_cpu(p) and cpu_allowed(p)]
    gpu_pool = [p for p in source.get("gpu", []) if pricing.is_recommendable_gpu(p)]
    ram_pool = list(source.get("ram", []))
    mb_pool = [p for p in source.get("mb", []) if is_desktop_mb(p)]
    psu_pool = list(source.get("psu", []))
    storage_pool = list(source.get("storage", []))

    if gpu_pref != "ANY":
        gpu_pool = [g for g in gpu_pool if normalize_text(g.get("vendor")) == normalize_text(gpu_pref)]

    if mode == "work":
        return cpu_pool, gpu_pool, ram_pool, mb_pool, psu_pool, storage_pool
    if tier == "low":
        # Keep modern Intel and AMD candidates even in LOW; price decides feasibility.
        # Chip tiers are not a substitute for the requested FPS and budget.
        ram_pool = [p for p in ram_pool if safe_float(p.get("gb"), 16) <= 32] or ram_pool
        storage_pool = [p for p in storage_pool if safe_float(p.get("capacity"), 1000) <= 2000] or storage_pool
    elif tier == "mid":
        cpu_pool = [p for p in cpu_pool if tier_rank(p.get("tier")) <= 2] or cpu_pool
        # Chip tiers are not a substitute for the requested FPS and budget.
        ram_pool = [p for p in ram_pool if safe_float(p.get("gb"), 16) >= 16] or ram_pool
    else:
        # An efficient CPU can fund a faster GPU at high resolutions.
        # Keep affordable GPUs for capped games and constrained budgets.
        ram_pool = [p for p in ram_pool if safe_float(p.get("gb"), 16) >= 32] or ram_pool

    return cpu_pool, gpu_pool, ram_pool, mb_pool, psu_pool, storage_pool


def performance_model_key(part, kind):
    """Retail SKUs of the same silicon share one search slot."""
    if kind == "gpu":
        return gpu_exact_model_key(part.get("product_name") or part.get("name")) or part.get("performance_ref_id") or part_cache_key(part)
    return part.get("performance_ref_id") or part_cache_key(part)

def rank_parts_for_tier(
    parts: List[Dict[str, Any]],
    part_type: str,
    tier_budget: int,
    resolution: str,
    refresh: int,
    tier: str,
    game: str,
    genres: List[str],
    price_cache: Dict[Tuple[str, str], int],
    rng: random.Random,
    limit: int,
    mode: str = "game",
    work_profile: str = "video_4k",
) -> List[Dict[str, Any]]:
    if mode == "work" and part_type in {"cpu", "gpu"}:
        requirements = WORK_PROFILES[work_profile]["requirements"]
        target = min(100.0, requirements.get(part_type, 50) * {"low": 1.0, "mid": 1.25, "high": 1.6}[tier])
        def work_rank(part):
            perf = (max(safe_float(part.get("perf_1080"), 0), safe_float(part.get("perf_1440"), 0) * 1.25,
                        safe_float(part.get("perf_2160"), 0) * 1.6) if part_type == "gpu" else safe_float(part.get("perf"), 0))
            fit = performance_fit(min(100, perf), target)
            if tier_budget:
                share = WORK_PROFILES[work_profile]["weights"].get(part_type, 0.2)
                fit += 0.2 * budget_fit_score(cached_part_price(part, part_type, price_cache), tier_budget * share)
            return fit
        scores = [(work_rank(p), p) for p in parts]
    elif part_type == "gpu":
        scores = [(score_gpu(p, tier_budget, resolution, tier, game, refresh, genres, rng), p) for p in parts]
    elif part_type == "cpu":
        scores = [(score_cpu(p, tier_budget, resolution, refresh, tier, game, rng), p) for p in parts]
    elif part_type == "ram":
        scores = [(score_ram(p, tier_budget, resolution, tier, game, rng), p) for p in parts]
    elif part_type == "storage":
        scores = [(score_storage(p, tier_budget, resolution, tier, rng), p) for p in parts]
    else:
        scores = [(1.0 - cached_part_price(p, part_type, price_cache) / max(1.0, tier_budget), p) for p in parts]
    if part_type in {"gpu", "cpu"}:
        # The cheapest verified SKU represents each performance model. A more
        # expensive cooler/retailer must not hide a feasible complete build.
        scores.sort(key=lambda item: (cached_part_price(item[1], part_type, price_cache), -item[0], part_cache_key(item[1])))
        unique = {}
        for score, part in scores:
            unique.setdefault(performance_model_key(part, part_type), (score, part))
        scores = list(unique.values())
        parts = [part for _, part in scores]
    scores.sort(key=lambda item: (-item[0], cached_part_price(item[1], part_type, price_cache), part_cache_key(item[1])))
    ranked = [p for _score, p in scores[:limit]]
    # Keep affordable and fast endpoints in the search: price-fit ranking alone
    # can discard every CPU/GPU needed to form a monotone three-tier sequence.
    if parts and part_type in {"cpu", "gpu"} and limit >= 3:
        performance = (lambda p: fps_service.gpu_base_perf(p, resolution)) if part_type == "gpu" else (lambda p: safe_float(p.get("perf"), 0.0))
        anchors = [
            min(parts, key=lambda p: (cached_part_price(p, part_type, price_cache), part_cache_key(p))),
            max(parts, key=lambda p: (performance(p), -cached_part_price(p, part_type, price_cache))),
        ]
        anchor_ids = {part_cache_key(p) for p in anchors}
        ranked = anchors[:1] if len(anchor_ids) == 1 else anchors
        ranked += [p for _score, p in scores if part_cache_key(p) not in anchor_ids][:limit - len(ranked)]
    return ranked or parts[:limit]

def mb_candidates_for(cpu: Dict[str, Any], ram: Dict[str, Any], mb_pool: List[Dict[str, Any]],
                      tier: str, tier_budget: int, price_cache: Dict[Tuple[str, str], int]) -> List[Dict[str, Any]]:
    compatible = [
        mb for mb in mb_pool
        if platform_compatibility(cpu, mb, ram)["compatible"]
    ]
    if not compatible:
        return []
    if not tier_budget:
        return sorted(compatible, key=lambda p: (cached_part_price(p, "mb", price_cache), part_cache_key(p)))[:2]
    target_price = tier_budget * (0.08 if tier == "low" else 0.10 if tier == "mid" else 0.12)
    def mb_score(mb: Dict[str, Any]) -> float:
        price = cached_part_price(mb, "mb", price_cache)
        price_fit = 1.0 - min(1.0, abs(price - target_price) / max(1.0, target_price))
        tier_fit = 1.0 - min(1.0, abs(tier_rank(mb.get("tier")) - state.TIER_RANK[tier]) / 2.0)
        return 0.72 * price_fit + 0.28 * tier_fit
    best = max(compatible, key=mb_score)
    cheap = min(compatible, key=lambda p: cached_part_price(p, "mb", price_cache))
    return list({part_cache_key(p): p for p in (best, cheap)}.values())

def psu_candidates_for(cpu: Dict[str, Any], gpu: Dict[str, Any], psu_pool: List[Dict[str, Any]],
                       tier: str, tier_budget: int, price_cache: Dict[Tuple[str, str], int]) -> List[Dict[str, Any]]:
    need = recommended_psu_watt(cpu, gpu)
    compatible = [psu for psu in psu_pool if safe_int(psu.get("watt"), 0) >= need]
    if not compatible:
        return []
    if not tier_budget:
        return sorted(compatible, key=lambda p: (cached_part_price(p, "psu", price_cache), part_cache_key(p)))[:2]
    target_price = tier_budget * (0.07 if tier == "low" else 0.085 if tier == "mid" else 0.095)
    def psu_score(psu: Dict[str, Any]) -> float:
        price = cached_part_price(psu, "psu", price_cache)
        watt = safe_float(psu.get("watt"), 0.0)
        headroom = max(0.0, watt - need)
        price_fit = 1.0 - min(1.0, abs(price - target_price) / max(1.0, target_price))
        headroom_fit = 1.0 - min(1.0, abs(headroom - 120.0) / 420.0)
        tier_fit = 1.0 - min(1.0, abs(tier_rank(psu.get("tier")) - state.TIER_RANK[tier]) / 2.0)
        return 0.48 * price_fit + 0.34 * headroom_fit + 0.18 * tier_fit
    best = max(compatible, key=psu_score)
    cheap = min(compatible, key=lambda p: cached_part_price(p, "psu", price_cache))
    return list({part_cache_key(p): p for p in (best, cheap)}.values())

def storage_candidates_for(storage_pool: List[Dict[str, Any]], tier: str, tier_budget: int,
                           price_cache: Dict[Tuple[str, str], int]) -> List[Dict[str, Any]]:
    target_capacity = 1000 if tier == "low" else 2000 if tier == "high" else 1400
    target_price = tier_budget * (0.11 if tier == "low" else 0.10 if tier == "mid" else 0.085)
    def storage_score(storage: Dict[str, Any]) -> float:
        price = cached_part_price(storage, "storage", price_cache)
        capacity = safe_float(storage.get("capacity"), 1000.0)
        if not tier_budget:
            return performance_fit(capacity, target_capacity) + storage_preference(storage)
        cap_fit = 1.0 - min(1.0, abs(capacity - target_capacity) / max(1000.0, target_capacity))
        if tier == "high" and capacity >= 2000:
            cap_fit = 1.0
        price_fit = 1.0 - min(1.0, abs(price - target_price) / max(1.0, target_price))
        tier_fit = 1.0 - min(1.0, abs(tier_rank(storage.get("tier")) - state.TIER_RANK[tier]) / 2.0)
        return 0.45 * price_fit + 0.40 * cap_fit + 0.15 * tier_fit + storage_preference(storage)
    # Preserve a cheap fallback and an NVMe option if available.
    ranked=sorted(storage_pool, key=lambda p: (-storage_score(p), cached_part_price(p, "storage", price_cache)))[:3]
    anchors=[min(storage_pool,key=lambda p:cached_part_price(p,"storage",price_cache))] if storage_pool else []
    nvme=[p for p in storage_pool if storage_preference(p)>=.07]
    if nvme:anchors.append(min(nvme,key=lambda p:cached_part_price(p,"storage",price_cache)))
    return list({part_cache_key(p):p for p in ranked+anchors}.values())

def normalize_work_profile(value: Any) -> str:
    key = normalize_text(value).replace(" ", "_")
    key = WORK_ALIASES.get(key, key)
    return key if key in WORK_PROFILES else "video_4k"

@dataclass(frozen=True)
class RecommendationRequest:
    """Normalized recommendation input shared by ranking, plans, and API output."""

    budget: Optional[int]
    budget_min: int
    budget_max: Optional[int]
    resolution: str
    refresh: int
    genres: Tuple[str, ...]
    gpu_pref: str
    gpu_brands: Tuple[str, ...]
    game: str
    mode: str
    work_profile: str
    budget_mode: str = "soft"
    gpu_market_prices: Optional[Dict[str, Dict[str, Any]]] = None

    @classmethod
    def from_payload(cls, payload: Any) -> "RecommendationRequest":
        if isinstance(payload, cls):
            return payload
        data = payload if isinstance(payload, dict) else {}
        budget_mode = "unlimited" if data.get("budget_mode") == "unlimited" else "soft"
        requested_budget = max(300000, safe_int(data.get("budget"), 1500000))
        budget_min = max(0, safe_int(data.get("budget_min"), 0))
        budget_max = max(300000, safe_int(data.get("budget_max"), requested_budget))
        if budget_min > budget_max:
            budget_min = 0
        if budget_mode == "unlimited":
            budget_min, budget_max = 0, None
        mode = normalize_text(data.get("mode", "game"))
        return cls(
            budget=budget_max,
            budget_min=budget_min,
            budget_max=budget_max,
            budget_mode=budget_mode,
            resolution=utils.resolution_key(data.get("resolution", "1080")),
            refresh=utils.refresh_value(data.get("refresh", 60)),
            genres=tuple(utils.genres_normalize(data.get("genres") or data.get("genre"))),
            gpu_pref=utils.vendor_normalize(data.get("gpu_pref", "ANY")),
            gpu_brands=tuple(normalize_gpu_maker_prefs(data.get("gpu_brands") or data.get("gpu_makers") or data.get("gpu_brand_prefs"))),
            game=fps_service.normalized_game_key(data.get("game") or "cyberpunk2077"),
            mode="work" if mode == "work" else "game",
            work_profile=normalize_work_profile(data.get("work_profile") or data.get("work") or data.get("work_type")),
            gpu_market_prices=data.get("gpu_market_prices") if isinstance(data.get("gpu_market_prices"), dict) else None,
        )

    def as_payload(self, include_market_prices: bool = True) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "budget": self.budget,
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "budget_mode": self.budget_mode,
            "resolution": self.resolution,
            "refresh": self.refresh,
            "genres": list(self.genres),
            "gpu_pref": self.gpu_pref,
            "gpu_brands": list(self.gpu_brands),
            "game": self.game,
            "mode": self.mode,
            "work_profile": self.work_profile,
        }
        if include_market_prices and self.gpu_market_prices is not None:
            payload["gpu_market_prices"] = self.gpu_market_prices
        return payload

    @property
    def unlimited(self):
        return self.budget_mode == "unlimited"

    @property
    def search_ceiling(self):
        return math.inf if self.unlimited else int(self.budget_max * (1 + BUDGET_HEADROOM))

    def tier_budget(self, tier):
        return 0 if self.unlimited else tier_budget_for_user(self.budget_max, tier, self.budget_min)

def work_suitability(score: Any) -> Dict[str, Any]:
    value = safe_float(score, 0.0)
    if value >= 85:
        return {"label": "매우 적합", "level": "excellent"}
    if value >= 70:
        return {"label": "적합", "level": "good"}
    if value >= 50:
        return {"label": "보통", "level": "normal"}
    if value >= 35:
        return {"label": "부적합", "level": "poor"}
    return {"label": "매우 부적합", "level": "bad"}

def work_component_norms(
    gpu: Dict[str, Any],
    cpu: Dict[str, Any],
    ram: Dict[str, Any],
    storage: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    gpu_norm = retail.clamp(max(
        safe_float(gpu.get("perf_1080"), 0.0),
        safe_float(gpu.get("perf_1440"), 0.0) * 1.25,
        safe_float(gpu.get("perf_2160"), 0.0) * 1.6,
    ) / 100.0, 0.0, 1.0)
    cpu_norm = retail.clamp(safe_float(cpu.get("perf"), 0.0) / 100.0, 0.0, 1.0)
    ram_norm = retail.clamp(safe_float(ram.get("gb"), 16.0) / 64.0, 0.0, 1.0)
    storage_tb = safe_float((storage or {}).get("capacity"), 1000.0) / 1000.0
    storage_norm = retail.clamp(storage_tb / 2.0, 0.0, 1.0)
    return {"gpu": gpu_norm, "cpu": cpu_norm, "ram": ram_norm, "storage": storage_norm}

def score_work_profile(
    gpu: Dict[str, Any],
    cpu: Dict[str, Any],
    ram: Dict[str, Any],
    storage: Optional[Dict[str, Any]],
    profile_key: Any,
) -> int:
    key = normalize_work_profile(profile_key)
    profile = WORK_PROFILES[key]
    norms = work_component_norms(gpu, cpu, ram, storage)
    weights = profile["weights"]
    score = sum(safe_float(weights.get(k), 0.0) * safe_float(norms.get(k), 0.0) for k in weights) * 100.0

    requirements = profile.get("requirements") or {}
    req_gpu = safe_float(requirements.get("gpu"), 0.0)
    req_cpu = safe_float(requirements.get("cpu"), 0.0)
    req_ram = safe_float(requirements.get("ram_gb"), 0.0)
    req_storage = safe_float(requirements.get("storage_tb"), 0.0)
    gpu_score = norms["gpu"] * 100.0
    cpu_score = norms["cpu"] * 100.0
    ram_gb = safe_float(ram.get("gb"), 16.0)
    storage_tb = safe_float((storage or {}).get("capacity"), 1000.0) / 1000.0

    penalty = 0.0
    if req_gpu and gpu_score < req_gpu:
        penalty += min(22.0, (req_gpu - gpu_score) * 0.36)
    if req_cpu and cpu_score < req_cpu:
        penalty += min(18.0, (req_cpu - cpu_score) * 0.30)
    if req_ram and ram_gb < req_ram:
        penalty += 8.0 if ram_gb >= req_ram * 0.5 else 16.0
    if req_storage and storage_tb < req_storage:
        penalty += 4.0
    return int(round(retail.clamp(score - penalty, 0.0, 100.0)))

def estimate_work_scores(
    gpu: Dict[str, Any],
    cpu: Dict[str, Any],
    ram: Dict[str, Any],
    storage: Optional[Dict[str, Any]] = None,
    selected_profile: Any = None,
) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    selected = normalize_work_profile(selected_profile)
    for key, profile in WORK_PROFILES.items():
        score = score_work_profile(gpu, cpu, ram, storage, key)
        suitability = work_suitability(score)
        out[key] = {
            "score": score,
            "label": suitability["label"],
            "level": suitability["level"],
            "name": profile["label"],
            "group": profile["group"],
            "selected": key == selected,
        }
    return out

def make_plan_from_raw_parts(
    user: Any,
    tier: str,
    raw_parts: Dict[str, Dict[str, Any]],
    tier_budget: int,
    alloc: Dict[str, int],
    total: int,
    score: float,
    budget_fit: float,
    overrun: int,
    power_score: float,
    fps_bundle: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    request = RecommendationRequest.from_payload(user)
    resolution = request.resolution
    refresh = request.refresh
    genres = list(request.genres)
    game = request.game
    mode = request.mode
    work_profile = request.work_profile
    gpu_pref = request.gpu_pref
    gpu_maker_prefs = list(request.gpu_brands)
    game_class, _ = pricing.game_profile(game)

    cpu = raw_parts["cpu"]
    gpu = raw_parts["gpu"]
    ram = raw_parts["ram"]
    mb = raw_parts["mb"]
    psu = raw_parts["psu"]
    storage = raw_parts["storage"]
    fps = dict(fps_bundle) if fps_bundle is not None else fps_service.estimate_fps_bundle(gpu, cpu, ram, game, resolution, refresh, tier, genres)
    high_avg = safe_float(fps.get("fps_by_option", {}).get("high"), 0.0)
    high_low1 = safe_float(fps.get("low1_by_option", {}).get("high"), 0.0)

    why = [
        f"{'4K' if resolution == '2160' else 'QHD' if resolution == '1440' else 'FHD'} 기준으로 조합 전체 가격과 호환성 계산",
        f"{refresh}Hz 목표에 맞춘 GPU/CPU/RAM 병목 보정",
    ]
    if game_class == "fps":
        why.append("FPS 장르라 CPU 응답성과 1% Low 안정성을 더 반영")
    elif game_class == "rpg":
        why.append("AAA/RPG 장르라 GPU 평균 FPS와 VRAM 여유를 더 반영")
    elif game_class == "sim":
        why.append("시뮬레이션 장르라 CPU와 RAM 비중을 강화")
    if gpu_pref != "ANY":
        why.append(f"{gpu_pref} 선호를 우선 반영")
    if gpu_maker_prefs:
        why.append("GPU 제조사 가격 후보 우선: " + ", ".join(gpu_maker_label(x) for x in gpu_maker_prefs))
    if fps.get("fps_source") in {"measured_benchmark", "benchmark_calibrated"}:
        why.append("공개 게임별 실측 벤치마크를 기준 구성·해상도·프리셋별로 반영")
    if state.DB_CACHE.get("loaded"):
        why.append("SQLite 벤치마크/가격 데이터 우선 사용")

    overall = round(retail.clamp(score / 2.0, 0.0, 1.0), 4)
    plan = {
        "tier": tier,
        "mode": mode,
        "budget_mode": request.budget_mode,
        "tierBudget": tier_budget,
        "budget_min": request.budget_min,
        "budget_max": request.budget_max,
        "budget_headroom_pct": 0 if request.unlimited else int(BUDGET_HEADROOM * 100),
        "totalPrice": total,
        "total_price": total,
        "allocation": alloc,
        "parts": {
            "cpu": pricing.summarize_part(cpu, "cpu"),
            "gpu": pricing.summarize_part(gpu, "gpu"),
            "ram": pricing.summarize_part(ram, "ram"),
            "mb": pricing.summarize_part(mb, "mb"),
            "psu": pricing.summarize_part(psu, "psu"),
            "storage": pricing.summarize_part(storage, "storage"),
        },
        "predictions": {
            "tier": {"label": tier, "confidence": overall},
            "cpu": {"id": cpu.get("id"), "label": cpu.get("name"), "confidence": round(retail.clamp(safe_float(cpu.get("perf"), 0.0) / 100.0, 0.0, 1.0), 4), "pred_price": fps_service.part_price(cpu, "cpu")},
            "gpu": {"id": gpu.get("id"), "label": gpu.get("name"), "confidence": round(retail.clamp(fps_service.gpu_base_perf(gpu, resolution) / 100.0, 0.0, 1.0), 4), "pred_price": fps_service.part_price(gpu, "gpu")},
            "ram": {"id": ram.get("id"), "label": ram.get("name"), "confidence": round(retail.clamp(safe_float(ram.get("gb"), 0.0) / 64.0, 0.0, 1.0), 4)},
            "budget_fit": round(budget_fit, 4),
            "overall_score": overall,
        },
        "fps": fps,
        "compatibility": platform_compatibility(cpu, mb, ram),
        "estimatedFPS": {
            "low": fps.get("fps_by_option", {}).get("low"),
            "medium": fps.get("fps_by_option", {}).get("medium"),
            "high": fps.get("fps_by_option", {}).get("high"),
            "ultra": fps.get("fps_by_option", {}).get("ultra"),
        },
        "work_scores": estimate_work_scores(gpu, cpu, ram, storage, work_profile),
        "selected_work": {
            "id": work_profile,
            "name": WORK_PROFILES[work_profile]["label"],
            **work_suitability(score_work_profile(gpu, cpu, ram, storage, work_profile)),
            "score": score_work_profile(gpu, cpu, ram, storage, work_profile),
        },
        "note": "검증된 게임별 실측 FPS에 CPU·GPU 처리 한계를 반영합니다. 실측이 없는 옵션과 구성은 보정 추정으로 표시합니다.",
        "why": why,
        "debug": {
            "total_price": total,
            "overrun": overrun,
            "budget_fit": round(budget_fit, 4),
            "high_avg": high_avg,
            "high_low1": high_low1,
            "power_score": power_score,
            "candidate_score": round(score, 4),
            "recommended_psu_watt": recommended_psu_watt(cpu, gpu),
            "ordering_metrics": {
                "gpu": fps_service.gpu_base_perf(gpu, resolution),
                "gpu_1080": fps_service.gpu_base_perf(gpu, "1080"),
                "gpu_1440": fps_service.gpu_base_perf(gpu, "1440"),
                "gpu_2160": fps_service.gpu_base_perf(gpu, "2160"),
                "cpu": safe_float(cpu.get("perf"), 0.0),
                "ram": safe_float(ram.get("gb"), 0.0),
                "storage": safe_float(storage.get("capacity"), 0.0),
                "power": power_score,
                "fps": high_avg,
                "low1": high_low1,
                "work": score_work_profile(gpu, cpu, ram, storage, work_profile) if mode == "work" else 0.0,
            },
        },
    }
    pricing.recompute_plan_total(plan)
    return plan

def part_cache_key(part: Dict[str, Any]) -> str:
    return str(part.get("id") or canonical_name(part.get("name")))

class CandidateEvaluationCache:
    """Memoize repeated compatibility, FPS, and work-score evaluation per tier."""

    def __init__(
        self,
        request: RecommendationRequest,
        tier: str,
        tier_budget: int,
        price_cache: Dict[Tuple[str, str], int],
        mb_pool: List[Dict[str, Any]],
        psu_pool: List[Dict[str, Any]],
        shared_fps: Optional[Dict[Tuple[str, str, str], Dict[str, Any]]] = None,
    ) -> None:
        self.request = request
        self.tier = tier
        self.tier_budget = tier_budget
        self.price_cache = price_cache
        self.mb_pool = mb_pool
        self.psu_pool = psu_pool
        self.fps_by_parts: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        self.mb_options: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self.psu_options: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self.work_scores: Dict[Tuple[str, str, str, str], int] = {}
        self.shared_fps = shared_fps if shared_fps is not None else {}

    def fps_for(self, gpu: Dict[str, Any], cpu: Dict[str, Any], ram: Dict[str, Any],
                *, complete: bool = True) -> Dict[str, Any]:
        key = (part_cache_key(gpu), part_cache_key(cpu), part_cache_key(ram))
        def sufficient(bundle):
            return bundle is not None and (not complete or 'low' in bundle['fps_by_option'])
        if not sufficient(self.fps_by_parts.get(key)):
            if not sufficient(self.shared_fps.get(key)):
                self.shared_fps[key] = fps_service.estimate_fps_bundle(
                    gpu, cpu, ram, self.request.game, self.request.resolution,
                    self.request.refresh, "mid", list(self.request.genres),
                    high_only=not complete,
                )
            bundle = dict(self.shared_fps[key])
            target = fps_service.target_fps_for_game(self.tier, self.request.refresh, self.request.game)
            target_low1 = target * pricing.low1_ratio_for_genres(list(self.request.genres) or [pricing.game_profile(self.request.game)[0]])
            metrics = pricing.value_metrics(bundle["high_setting_avg_fps"], safe_float(gpu.get("price"), 0), target, bundle["high_setting_low1_fps"], target_low1)
            for field in ("target_fps", "target_low1_fps", "target_coverage", "low1_target_coverage", "capacity_label"):
                bundle[field] = metrics[field]
            self.fps_by_parts[key] = bundle
        return self.fps_by_parts[key]

    def motherboards_for(self, cpu: Dict[str, Any], ram: Dict[str, Any]) -> List[Dict[str, Any]]:
        key = (part_cache_key(cpu), part_cache_key(ram))
        if key not in self.mb_options:
            self.mb_options[key] = mb_candidates_for(
                cpu, ram, self.mb_pool, self.tier, self.tier_budget, self.price_cache,
            )
        return self.mb_options[key]

    def power_supplies_for(self, cpu: Dict[str, Any], gpu: Dict[str, Any]) -> List[Dict[str, Any]]:
        key = (part_cache_key(cpu), part_cache_key(gpu))
        if key not in self.psu_options:
            self.psu_options[key] = psu_candidates_for(
                cpu, gpu, self.psu_pool, self.tier, self.tier_budget, self.price_cache,
            )
        return self.psu_options[key]

    def work_score_for(
        self,
        gpu: Dict[str, Any],
        cpu: Dict[str, Any],
        ram: Dict[str, Any],
        storage: Dict[str, Any],
    ) -> int:
        key = (part_cache_key(gpu), part_cache_key(cpu), part_cache_key(ram), part_cache_key(storage))
        if key not in self.work_scores:
            self.work_scores[key] = score_work_profile(
                gpu, cpu, ram, storage, self.request.work_profile,
            )
        return self.work_scores[key]

def build_tier_candidates(user: Any, tier: str, rng: random.Random, limit: int = 36,
                          shared_fps: Optional[Dict[Tuple[str, str, str], Dict[str, Any]]] = None,
                          inventory: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> List[Dict[str, Any]]:
    request = RecommendationRequest.from_payload(user)
    resolution = request.resolution
    refresh = request.refresh
    genres = list(request.genres)
    game = request.game
    mode = request.mode
    gpu_pref = request.gpu_pref
    gpu_maker_prefs = list(request.gpu_brands)
    game_class, _ = pricing.game_profile(game)

    tier_budget = request.tier_budget(tier)
    alloc = pricing.budget_allocations(tier_budget, resolution, refresh, game_class, tier)
    price_cache: Dict[Tuple[str, str], int] = {}

    cpu_pool, gpu_pool, ram_pool, mb_pool, psu_pool, storage_pool = tier_component_pools(
        tier, resolution, refresh, gpu_pref, inventory, mode=mode
    )
    if inventory is not None and gpu_maker_prefs:
        gpu_pool = [p for p in gpu_pool if gpu_maker_normalize(p.get("name")) in gpu_maker_prefs]
    market_gpu_prices = request.gpu_market_prices
    if inventory is None and isinstance(market_gpu_prices, dict) and market_gpu_prices:
        priced_gpu_pool = [
            market_gpu_prices[str(part.get("id"))]
            for part in gpu_pool
            if str(part.get("id")) in market_gpu_prices
            and pricing.is_recommendable_gpu(market_gpu_prices[str(part.get("id"))])
        ]
        if not priced_gpu_pool:
            priced_gpu_pool = [
                part for part in market_gpu_prices.values()
                if pricing.is_recommendable_gpu(part)
                and (gpu_pref == "ANY" or normalize_text(part.get("vendor")) == normalize_text(gpu_pref))
            ]
        gpu_pool = priced_gpu_pool
        # Verified inventory is preferred, but unverified reference prices must
        # not hide all compatible recommendations during a retailer outage.
        if not gpu_pool:
            gpu_pool = [p for p in GPU_CATALOG if pricing.is_recommendable_gpu(p)
                        and (gpu_pref == "ANY" or normalize_text(p.get("vendor")) == normalize_text(gpu_pref))]
    mb_pool = filter_compatible_mb(cpu_pool, mb_pool)
    ram_pool = filter_compatible_ram(mb_pool, ram_pool)
    if mode == "work" and request.unlimited:
        requirements = WORK_PROFILES[request.work_profile]["requirements"]
        cpu_pool = [p for p in cpu_pool if safe_float(p.get("perf"), 0) >= requirements.get("cpu", 0)]
        gpu_pool = [p for p in gpu_pool if work_component_norms(p, {}, {})["gpu"] * 100 >= requirements.get("gpu", 0)]
        ram_pool = [p for p in ram_pool if safe_float(p.get("gb"), 0) >= requirements.get("ram_gb", 16)]
        storage_pool = [p for p in storage_pool if safe_float(p.get("capacity"), 0) >= requirements.get("storage_tb", 1) * 1000]

    pools={"cpu":cpu_pool,"gpu":gpu_pool,"ram":ram_pool,"mb":mb_pool,"psu":psu_pool,"storage":storage_pool}
    if any(not pool for pool in pools.values()):
        return []
    # Even an unrealistically cheap mix cannot fit: skip combinatorial search.
    lower_bound=sum(min(cached_part_price(p,kind,price_cache) for p in pool) for kind,pool in pools.items())
    if lower_bound > request.search_ceiling:
        return []

    cpu_ranked = rank_parts_for_tier(cpu_pool, "cpu", tier_budget, resolution, refresh, tier, game, genres, price_cache, rng, 10, mode, request.work_profile)
    for group in ([p for p in cpu_pool if cpu_preference(p, mode)>=.10],
                  [p for p in cpu_pool if cpu_preference(p, mode)==.05]):
        if group:
            preferred=min(group,key=lambda p:cached_part_price(p,"cpu",price_cache))
            if preferred not in cpu_ranked:cpu_ranked.append(preferred)
    gpu_ranked = rank_parts_for_tier(gpu_pool, "gpu", tier_budget, resolution, refresh, tier, game, genres, price_cache, rng, 10, mode, request.work_profile)
    ram_ranked = rank_parts_for_tier(ram_pool, "ram", tier_budget, resolution, refresh, tier, game, genres, price_cache, rng, len(ram_pool))
    storage_ranked = storage_candidates_for(storage_pool, tier, tier_budget, price_cache)
    evaluations = CandidateEvaluationCache(request, tier, tier_budget, price_cache, mb_pool, psu_pool, shared_fps)

    best_by_pair = {}
    def candidate_rank(item):
        return (-item[0], item[2], tuple(part_cache_key(item[1][k]) for k in ("gpu", "cpu", "ram", "storage", "mb", "psu")))
    target_fps = fps_service.target_fps_for_game(tier, refresh, game)
    target_low1 = target_fps * pricing.low1_ratio_for_genres(genres or [game_class])
    max_total = request.search_ceiling

    for gpu in gpu_ranked:
        gpu_model = performance_model_key(gpu, "gpu")
        for cpu in cpu_ranked:
            pair = (gpu_model, performance_model_key(cpu, "cpu"))
            for ram in ram_ranked:
                mb_options = evaluations.motherboards_for(cpu, ram)
                if not mb_options:
                    continue
                psu_options = evaluations.power_supplies_for(cpu, gpu)
                if not psu_options:
                    continue
                # Board/PSU performance is absent from the objective after
                # compatibility checks. Lower total never scores worse, and
                # equal scores already prefer total then IDs. Other accessories
                # cannot survive the existing CPU/GPU-pair reduction below.
                mb_options = [min(mb_options, key=lambda p: (cached_part_price(p, "mb", price_cache), part_cache_key(p)))]
                psu_options = [min(psu_options, key=lambda p: (cached_part_price(p, "psu", price_cache), part_cache_key(p)))]
                for mb in mb_options:
                    for psu in psu_options:
                        for storage in storage_ranked:
                            raw_parts = {"cpu": cpu, "gpu": gpu, "ram": ram, "mb": mb, "psu": psu, "storage": storage}
                            total = price_sum_for_parts(raw_parts, price_cache)
                            if total <= 0:
                                continue
                            overrun = max(0, total - tier_budget) if tier_budget else 0
                            if total > max_total:
                                continue

                            fps = evaluations.fps_for(gpu, cpu, ram, complete=False)
                            high_avg = safe_float(fps.get("fps_by_option", {}).get("high"), 0.0)
                            low1_avg = safe_float(fps.get("low1_by_option", {}).get("high"), 0.0)
                            fps_ratio = high_avg / max(1.0, target_fps)
                            budget_fit = budget_fit_score(total, tier_budget)
                            power = build_power_score(raw_parts, resolution)
                            if mode == "work":
                                work_score = evaluations.work_score_for(gpu, cpu, ram, storage)
                                work_target = {"low": 65, "mid": 82, "high": 100}[tier]
                                score = 6.0 * performance_fit(work_score, work_target)
                                if not request.unlimited:
                                    score += 1.4 * budget_fit
                                score += 0.3 * build_preference(raw_parts, mode)
                            else:
                                score = gaming_objective(
                                    gpu_perf=fps_service.gpu_base_perf(gpu, resolution),
                                    gpu_target=gaming_gpu_target(resolution, refresh, tier),
                                    fps_ratio=fps_ratio,
                                    low1_ratio=low1_avg / max(1.0, target_low1),
                                    budget_fit=budget_fit, unlimited=request.unlimited,
                                    ram_gb=safe_float(ram.get("gb"), 16),
                                    cpu_loss=safe_float((fps.get("bottleneck") or {}).get("cpu_penalty_pct"), 0) / 100,
                                    parts=raw_parts,
                                )
                                score += 0.15 * min(1.0, safe_float(storage.get("capacity"), 0) / (2000 if tier == "high" else 1000))
                            item = (score, raw_parts, total, budget_fit, overrun, power)
                            rank = candidate_rank(item)
                            if pair not in best_by_pair or rank < best_by_pair[pair][0]:
                                best_by_pair[pair] = (rank, item)

    if not best_by_pair:
        return []

    scored = [item for _, item in sorted(best_by_pair.values(), key=lambda entry: entry[0])]
    # Round-robin silicon families before another CPU or board-partner SKU.
    # Each family retains alternative CPUs so global ordering can avoid a
    # locally optimal CPU that would block a faster GPU in the next tier.
    groups = {}
    for item in scored:
        gpu_key = performance_model_key(item[1]["gpu"], "gpu")
        groups.setdefault(gpu_key, []).append(item)
    scored = [group[index] for index in range(max(map(len, groups.values())))
              for group in groups.values() if index < len(group)]
    plans: List[Dict[str, Any]] = []
    seen: set = set()
    for score, raw_parts, total, budget_fit, overrun, power in scored:
        signature = tuple((raw_parts[k].get("id") for k in ["gpu", "cpu", "ram", "mb", "psu", "storage"]))
        if signature in seen:
            continue
        seen.add(signature)
        plans.append(make_plan_from_raw_parts(request, tier, raw_parts, tier_budget, alloc, total, score, budget_fit, overrun, power,
                                             evaluations.fps_for(raw_parts["gpu"], raw_parts["cpu"], raw_parts["ram"])))
        if len(plans) >= limit:
            break
    return plans

def plan_ordering_metrics(plan: Dict[str, Any]) -> Dict[str, float]:
    """Use comparable hardware/FPS measurements, never price or tier labels."""
    debug = plan.get("debug") or {}
    metrics = debug.get("ordering_metrics")
    if metrics:
        return {key: safe_float(value, 0.0) for key, value in metrics.items()}
    parts = plan.get("parts") or {}
    fps = plan.get("fps") or {}
    return {
        "gpu": safe_float((parts.get("gpu") or {}).get("performance_index"), fps_service.gpu_base_perf(parts.get("gpu") or {}, "1080")),
        "gpu_1080": safe_float((parts.get("gpu") or {}).get("perf_1080"), 0.0),
        "gpu_1440": safe_float((parts.get("gpu") or {}).get("perf_1440"), 0.0),
        "gpu_2160": safe_float((parts.get("gpu") or {}).get("perf_2160"), 0.0),
        "cpu": safe_float((parts.get("cpu") or {}).get("performance_index"), safe_float((parts.get("cpu") or {}).get("perf"), 0.0)),
        "ram": safe_float((parts.get("ram") or {}).get("gb"), 0.0),
        "storage": safe_float((parts.get("storage") or {}).get("capacity"), 0.0),
        "power": safe_float(debug.get("power_score"), 0.0),
        "fps": safe_float((fps.get("fps_by_option") or {}).get("high", debug.get("high_avg")), 0.0),
        "low1": safe_float((fps.get("low1_by_option") or {}).get("high", debug.get("high_low1")), 0.0),
        "work": 0.0,
    }

def tier_upgrade_quality(lower: Dict[str, Any], upper: Dict[str, Any]) -> int:
    """-1 rejects any regression; 0/1/2 distinguish equal/small/clear upgrades.

    FPS may tie in a capped game. A faster GPU or CPU still provides a real
    tier distinction, whereas an expensive board or PSU alone does not.
    """
    lower_metrics = plan_ordering_metrics(lower)
    upper_metrics = plan_ordering_metrics(upper)
    lower_gpu = (lower.get("parts") or {}).get("gpu") or {}
    upper_gpu = (upper.get("parts") or {}).get("gpu") or {}
    lower_id = performance_model_key(lower_gpu, "gpu")
    upper_id = performance_model_key(upper_gpu, "gpu")
    work = lower.get("mode") == "work" and upper.get("mode") == "work"
    if not work and lower_id and lower_id == upper_id:
        return -1
    if lower.get("price_order_required") or upper.get("price_order_required"):
        if safe_int(upper.get("totalPrice"), 0) <= safe_int(lower.get("totalPrice"), 0):
            return -1
    compared = {"cpu", "ram", "storage", "work"} if work else set(lower_metrics)
    if any(upper_metrics.get(key, 0.0) + 1e-6 < lower_metrics.get(key, 0.0) for key in compared):
        return -1
    gains = {
        key: upper_metrics.get(key, 0.0) - lower_metrics.get(key, 0.0)
        for key in ("gpu", "cpu", "fps", "work")
    }
    if not work and gains["gpu"] < max(2.0, lower_metrics.get("gpu", 0.0) * 0.05):
        return -1
    if work and gains["work"] < 2.0:
        return -1
    if any(gain >= max(2.0, lower_metrics.get(key, 0.0) * 0.05) for key, gain in gains.items()):
        return 2
    return 1 if any(gain > 1e-6 for gain in gains.values()) else 0

def select_ordered_tier_plans(candidate_sets: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    """Find the best valid chain with hard component and FPS constraints.

    Dynamic programming retains the best chain ending at each candidate.
    Missing tiers are allowed only when a complete ordered chain is impossible;
    even LOW/HIGH pairs with a missing MID must satisfy the same constraints.
    """
    tiers = ("low", "mid", "high")
    # Each entry contains (chain, upgrade-quality tuple, candidate-score sum).
    states: List[Tuple[Dict[str, Dict[str, Any]], Tuple[int, ...], float]] = []

    def chain_rank(state: Tuple[Dict[str, Dict[str, Any]], Tuple[int, ...], float]) -> Tuple[Any, ...]:
        chain, qualities, score = state
        # Prefer meaningful hardware steps before marginal local score gains.
        return (len(chain), min(qualities, default=0), score, sum(qualities),
                -sum(safe_float(p.get("totalPrice"), 0.0) for p in chain.values()))

    for tier in tiers:
        previous_states = states[:]
        for plan in candidate_sets.get(tier) or []:
            score = safe_float((plan.get("debug") or {}).get("candidate_score"), 0.0)
            best = ({tier: plan}, (), score)
            for chain, qualities, prior_score in previous_states:
                prior = next(reversed(chain.values()))
                quality = tier_upgrade_quality(prior, plan)
                if quality < 0:
                    continue
                extended = ({**chain, tier: plan}, qualities + (quality,), prior_score + score)
                if chain_rank(extended) > chain_rank(best):
                    best = extended
            states.append(best)
    if not states:
        return {tier: {} for tier in tiers}
    selected, _qualities, _score = max(states, key=chain_rank)
    return {tier: selected.get(tier, {}) for tier in tiers}


def complete_recommendation_tiers(results, candidate_sets, request):
    """Finalize the selected chain without inventing or copying missing tiers."""
    completed = {}
    previous = None
    for tier in ("low", "mid", "high"):
        source = results.get(tier) or {}
        if not source.get("parts") or (previous and tier_upgrade_quality(previous, source) <= 0):
            completed[tier] = {
                "tier": tier, "unavailable_reason": "no_distinct_upgrade",
                "note": "선택한 조건과 판매 후보에서 성능 차이가 있는 추가 구성을 찾지 못했습니다. 예산이나 GPU 선호 조건을 조정해 주세요.",
            }
            continue
        plan = copy.deepcopy(source)
        plan.pop("same_configuration", None)
        plan["tier"] = tier
        plan["budget_mode"] = request.budget_mode
        plan["tierBudget"] = request.tier_budget(tier)
        plan.setdefault("predictions", {}).setdefault("tier", {})["label"] = tier
        pricing.recompute_plan_total(plan)
        completed[tier] = plan
        previous = plan
    return completed

def recommend(user: Any) -> Dict[str, Any]:
    request = RecommendationRequest.from_payload(user)
    database.ensure_db_cache_loaded()
    cache_key = _recommend_key(request)
    # Sharing a computation never publishes saved results before latest lookup completes.
    response = _recommend_flight.run(cache_key, lambda: _recommend_uncached(request, cache_key))
    return copy.deepcopy(response)


def _recommend_uncached(request, cache_key):
    with _recommend_cache_lock:
        cached = state.RECOMMENDATION_CACHE.get(cache_key)
    if cached and time.monotonic() - cached[0] < (cached[2] if len(cached) > 2 else 60):
        response = copy.deepcopy(cached[1])
        response["engine"]["cached"] = True
        return response
    inventory = verified_recommendation_inventory()
    market_gpu_prices = {str(p["id"]): p for p in inventory["gpu"]}

    seed = utils.stable_seed(request.as_payload(include_market_prices=False))
    rng = random.Random(seed)
    shared_fps: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    candidate_sets = {
        tier: build_tier_candidates(request, tier, rng, limit=36, shared_fps=shared_fps, inventory=inventory)
        for tier in ["low", "mid", "high"]
    }
    results = select_ordered_tier_plans(candidate_sets)
    results = complete_recommendation_tiers(results, candidate_sets, request)

    warnings: List[str] = []
    if not all(inventory.values()):
        warnings.append("실제 판매가와 제품 사진이 확인된 부품으로 호환 구성을 만들 수 없습니다. 잠시 후 다시 조회해주세요.")

    payload = {
        "input": request.as_payload(include_market_prices=False),
        "results": results,
        "warning": " ".join(warnings) if warnings else None,
        "engine": {
            "mode": "specification_tiers_v2",
            "db_loaded": state.DB_CACHE.get("loaded", False),
            "catalog": {k: len(v) for k, v in CATALOGS.items()},
            "db_summary": state.DB_CACHE.get("summary", {}),
            "verified_gpu_prices": len(market_gpu_prices),
            "verified_inventory_counts": {kind: len(rows) for kind, rows in inventory.items()},
        },
    }
    # Keep verified retail SKUs and their observed prices intact after selection.
    priced_plans = [plan for plan in payload["results"].values() if plan.get("parts")]
    for plan in priced_plans:
        fps_service.attach_graphics_modes(plan["fps"], plan["parts"]["gpu"], plan["parts"]["cpu"], request.game, request.resolution)
    if any(plan.get("total_is_estimate") for plan in priced_plans):
        warnings.append("현재 판매가를 확인하지 못한 부품은 참고 가격이며, 해당 합계는 예상 금액입니다.")
    if any(plan.get("budget_status") == "over_budget" for plan in priced_plans):
        warnings.append("성능 차이를 확보하기 위해 목표 예산을 최대 20% 초과하는 후보도 검토했습니다. 카드에서 초과 금액을 확인해 주세요.")
    if len(priced_plans) < 3:
        warnings.append("일부 등급에서 조건에 맞는 성능 업그레이드 후보가 부족합니다. 동일한 구성은 반복해서 표시하지 않습니다.")
    payload["warning"] = " ".join(warnings) if warnings else None
    payload["engine"]["db_loaded"] = state.DB_CACHE.get("loaded", False)
    payload["engine"]["db_summary"] = state.DB_CACHE.get("summary", {})
    payload["engine"]["evaluated_cpu_gpu_ram_combinations"] = len(shared_fps)
    payload["engine"]["cached"] = False
    # A replacement during calculation must never relabel older work as the new revision.
    # Retail refresh writes also skip this insertion; the next stable request can cache.
    final_key = _recommend_key(request)
    if final_key == cache_key:
        with _recommend_cache_lock:
            if len(state.RECOMMENDATION_CACHE) >= 32:
                state.RECOMMENDATION_CACHE.pop(next(iter(state.RECOMMENDATION_CACHE)))
            state.RECOMMENDATION_CACHE[cache_key] = (
                time.monotonic(), copy.deepcopy(payload), freshness_ttl(payload, maximum=60))
    return payload
