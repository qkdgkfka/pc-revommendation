"""Product prices, summaries and value calculations."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from datetime import datetime, timedelta
import math
import re
from product_metadata import (
    canonical_name,
    normalize_gpu_maker_prefs,
    normalize_text,
    safe_float,
    safe_int,
)
from typing import Any, Dict, List, Optional, Tuple
from server_catalogs import GPU_CATALOG
from . import runtime as state
from . import database
from . import fps as fps_service
from . import retail


def component_performance_index(part: Dict[str, Any], part_type: str) -> Tuple[float, str]:
    """Return a 0-100 component-type-specific index for direct-build value display."""
    name = normalize_text(part.get("name"))
    tags = {normalize_text(tag) for tag in part.get("tags", [])}
    if part_type == "gpu":
        return retail.clamp(fps_service.gpu_base_perf(part, "1440"), 0.0, 100.0), "QHD 래스터 지수"
    if part_type == "cpu":
        return retail.clamp(safe_float(part.get("perf"), 0.0), 0.0, 100.0), "CPU 처리 지수"
    if part_type == "ram":
        gb = safe_float(part.get("gb"), 0.0)
        speed = safe_float(part.get("speed"), 0.0)
        base = min(72.0, gb / 64.0 * 72.0)
        bandwidth = min(24.0, max(0.0, (speed - 2400.0) / 55.0))
        generation = 5.0 if normalize_text(part.get("type")) == "ddr5" else 0.0
        return retail.clamp(base + bandwidth + generation, 0.0, 100.0), "메모리 용량·대역폭 지수"
    if part_type == "mb":
        socket = normalize_text(part.get("socket"))
        score = 46.0 + (18.0 if normalize_text(part.get("ram_type")) == "ddr5" else 0.0)
        score += 16.0 if socket in {"am5", "lga1851"} else 10.0 if socket == "lga1700" else 4.0
        score += {"high": 16.0, "mid": 9.0, "low": 3.0}.get(normalize_text(part.get("tier")), 0.0)
        return retail.clamp(score, 0.0, 100.0), "확장성·전원부 지수"
    if part_type == "storage":
        capacity = safe_float(part.get("capacity"), 0.0)
        score = min(55.0, capacity / 4000.0 * 55.0)
        if "gen5" in name or "gen5" in tags:
            score += 42.0
        elif "gen4" in name or "gen4" in tags or "nvme" in name:
            score += 30.0
        elif "sata" in name or "sata" in tags:
            score += 12.0
        else:
            score += 20.0
        return retail.clamp(score, 0.0, 100.0), "저장공간·속도 지수"
    if part_type == "hdd":
        capacity = safe_float(part.get("capacity"), 0.0)
        rpm = safe_float(part.get("rpm"), 0.0)
        return retail.clamp(min(78.0, capacity / 12000.0 * 78.0) + (18.0 if rpm >= 7200 else 10.0 if rpm else 0.0), 0.0, 100.0), "저장공간·회전수 지수"
    if part_type == "psu":
        watt = safe_float(part.get("watt"), safe_float(part.get("recommendedWatt"), 0.0))
        score = min(78.0, watt / 1200.0 * 78.0)
        score += 22.0 if "platinum" in name else 16.0 if "gold" in name else 8.0 if "bronze" in name else 0.0
        return retail.clamp(score, 0.0, 100.0), "출력·효율 지수"
    if part_type == "case":
        score = {"low": 48.0, "mid": 66.0, "high": 82.0}.get(normalize_text(part.get("tier")), 52.0)
        if "airflow" in tags:
            score += 8.0
        return retail.clamp(score, 0.0, 100.0), "냉각·확장성 지수"
    if part_type == "software":
        if normalize_text(part.get("license")) == "none":
            return 0.0, "소프트웨어 구성 지수"
        score = 48.0
        if "pro" in name or "business" in tags:
            score += 28.0
        if "creative" in tags or "video" in tags:
            score += 20.0
        return retail.clamp(score, 0.0, 100.0), "소프트웨어 구성 지수"
    return 0.0, "성능 지수"

def summarize_part(part: Dict[str, Any], part_type: str) -> Dict[str, Any]:
    raw_price = safe_int(part.get("price"), 0)
    raw_source = normalize_text(part.get("price_source"))
    raw_url = part.get("url") or part.get("shop_url") or part.get("product_url")
    verified_gpu_listing = database.verified_price_info(part)
    price_info = {} if verified_gpu_listing else (database.db_lookup_price_info(part, part_type) or {})
    if price_info.get("stale"):
        price_info = {}
    price = raw_price if verified_gpu_listing else price_info.get("price")
    if price is None:
        price = raw_price
    performance_index, performance_metric = component_performance_index(part, part_type)
    value_per_10000 = 0.0 if price <= 0 else round(performance_index / max(1.0, price / 10000.0), 3)
    out = {
        "id": part.get("id"),
        "performance_ref_id": part.get("performance_ref_id") or part.get("id"),
        "name": part.get("name"),
        "product_name": (part.get("product_name") if verified_gpu_listing else price_info.get("name")) or part.get("product_name") or part.get("name"),
        "price": price,
        "base_price": safe_int(part.get("base_price"), 0) or raw_price,
        "tier": part.get("tier"),
        "shop": (part.get("shop") if verified_gpu_listing else price_info.get("shop")) or part.get("shop") or "Catalog",
        "url": (part.get("url") if verified_gpu_listing else price_info.get("url")) or part.get("url") or retail.danawa_search_url(part.get("name")),
        "image_url": (part.get("image_url") if verified_gpu_listing else price_info.get("image_url")) or part.get("image_url") or database.part_image_endpoint(part, part_type),
        "currency": (part.get("currency") if verified_gpu_listing else price_info.get("currency")) or part.get("currency") or "KRW",
        "price_source": (part.get("price_source") if verified_gpu_listing else price_info.get("price_source")) or part.get("price_source") or ("db" if price_info else "catalog_search"),
        "price_source_label": (part.get("price_source_label") if verified_gpu_listing else price_info.get("matched_by")) or part.get("price_source_label") or ("catalog" if not price_info else "db"),
        "performance_index": round(performance_index, 1),
        "performance_metric": performance_metric,
        "value_per_10000krw": value_per_10000,
        "scraped_at": ((part.get("price_checked_at") or part.get("scraped_at")) if verified_gpu_listing else price_info.get("scraped_at")) or part.get("scraped_at"),
        "verified": bool(verified_gpu_listing or price_info),
        "price_status": (part.get("price_status") or "verified") if verified_gpu_listing else "verified" if price_info else ("estimated" if price > 0 else "unavailable"),
    }
    if part_type == "cpu":
        out.update({
            "socket": part.get("socket"),
            "vendor": part.get("vendor"),
            "tdp": part.get("tdp"),
            "cores": part.get("cores"),
            "threads": part.get("threads"),
        })
    elif part_type == "gpu":
        out.update({
            "vram": part.get("vram"),
            "tdp": part.get("tdp"),
            "vendor": part.get("vendor"),
            "perf_1080": part.get("perf_1080"),
            "perf_1440": part.get("perf_1440"),
            "perf_2160": part.get("perf_2160"),
        })
    elif part_type == "ram":
        out.update({"brand": part.get("brand"), "type": part.get("type"), "gb": part.get("gb"), "speed": part.get("speed")})
    elif part_type == "mb":
        out.update({"socket": part.get("socket"), "ram_type": part.get("ram_type"), "brand": part.get("brand")})
    elif part_type == "psu":
        out.update({"brand": part.get("brand"), "recommendedWatt": part.get("watt"), "watt": part.get("watt")})
    elif part_type == "storage":
        out.update({"brand": part.get("brand"), "capacity": part.get("capacity")})
    elif part_type == "hdd":
        out.update({"brand": part.get("brand"), "capacity": part.get("capacity"), "rpm": part.get("rpm")})
    elif part_type == "case":
        out.update({"brand": part.get("brand"), "form_factor": part.get("form_factor"), "color": part.get("color")})
    elif part_type == "software":
        out.update({"brand": part.get("brand"), "license": part.get("license")})
    return out

def fps_capacity_label(
    average_fps: Any,
    low1_fps: Any,
    target_fps: Any,
    target_low1_fps: Any,
) -> str:
    """Describe target coverage separately from price efficiency.

    A build that clears the requested refresh target should never be marked
    insufficient just because its raw FPS-per-won ratio is modest.
    """
    average = safe_float(average_fps, 0.0)
    low1 = safe_float(low1_fps, 0.0)
    target = safe_float(target_fps, 0.0)
    low_target = safe_float(target_low1_fps, 0.0)
    if average <= 0 or target <= 0:
        return "측정 대기"

    average_coverage = average / target
    low1_coverage = low1 / low_target if low_target > 0 else average_coverage
    if average_coverage >= 1.20 and low1_coverage >= 1.0:
        return "목표 성능 여유"
    if average_coverage >= 1.0 and low1_coverage >= 0.88:
        return "목표 성능 충족"
    if average_coverage >= 0.85:
        return "거의 충족"
    if average_coverage >= 0.60:
        return "다소 부족"
    return "매우 부족"

def value_metrics(
    fps: Any,
    price: Any,
    target_fps: Any = 0.0,
    low1_fps: Any = 0.0,
    target_low1_fps: Any = 0.0,
) -> Dict[str, Any]:
    """Return cost efficiency and requested-performance coverage independently."""
    avg_fps = safe_float(fps, 0.0)
    total_price = safe_float(price, 0.0)
    target = safe_float(target_fps, 0.0)
    low1 = safe_float(low1_fps, 0.0)
    low_target = safe_float(target_low1_fps, 0.0)
    fps_per_1000 = avg_fps / max(1.0, total_price / 1000.0) if avg_fps > 0 and total_price > 0 else 0.0
    target_coverage = avg_fps / target if target > 0 else 0.0
    low1_target_coverage = low1 / low_target if low_target > 0 else 0.0
    return {
        "fps_per_1000krw": round(fps_per_1000, 4),
        "price_per_frame_krw": round(total_price / avg_fps, 2) if avg_fps > 0 and total_price > 0 else None,
        "score": round(fps_per_1000 * 100.0, 1),
        "target_fps": round(target, 1),
        "target_low1_fps": round(low_target, 1),
        "target_coverage": round(target_coverage, 3),
        "low1_target_coverage": round(low1_target_coverage, 3),
        "capacity_label": fps_capacity_label(avg_fps, low1, target, low_target),
    }

def value_label(value_score: float) -> str:
    if value_score >= 9.0:
        return "최상 가성비"
    if value_score >= 7.0:
        return "좋은 가성비"
    if value_score >= 5.0:
        return "적정"
    if value_score >= 3.0:
        return "다소 부족"
    return "매우 부족"

def low1_ratio_for_genres(genres: List[str]) -> float:
    if any(g in genres for g in ["fps", "valorant", "cs", "cs2", "competitive"]):
        return 0.86
    if any(g in genres for g in ["rpg", "aaa", "action"]):
        return 0.80
    if any(g in genres for g in ["mmo", "lostark", "wow", "mmorpg"]):
        return 0.77
    if any(g in genres for g in ["sim", "simulation", "cities"]):
        return 0.73
    if any(g in genres for g in ["openworld", "open_world"]):
        return 0.76
    if any(g in genres for g in ["subculture", "anime"]):
        return 0.82
    return 0.79

def game_profile(game: str) -> Tuple[str, float]:
    g = normalize_text(game).replace(" ", "_")
    return state.GAME_GENRE_FACTORS.get(g, ("default", 1.0))


def budget_allocations(total_budget: int, resolution: str, refresh: int, genre_class: str, tier: str) -> Dict[str, int]:
    if resolution == "2160":
        shares = {"gpu": 0.52, "cpu": 0.15, "ram": 0.10, "mb": 0.08, "psu": 0.08, "storage": 0.07}
    elif resolution == "1440":
        shares = {"gpu": 0.43, "cpu": 0.19, "ram": 0.11, "mb": 0.08, "psu": 0.08, "storage": 0.11}
    else:
        shares = {"gpu": 0.34, "cpu": 0.25, "ram": 0.12, "mb": 0.08, "psu": 0.08, "storage": 0.13}

    if refresh >= 144 and resolution == "1080":
        shares["cpu"] += 0.04
        shares["gpu"] -= 0.02
        shares["ram"] += 0.01

    if genre_class == "sim":
        shares["cpu"] += 0.03
        shares["gpu"] -= 0.02
    elif genre_class == "mmo":
        shares["cpu"] += 0.02
        shares["ram"] += 0.01
    elif genre_class == "rpg":
        shares["gpu"] += 0.01

    if tier == "low":
        shares["gpu"] -= 0.02
        shares["storage"] += 0.02
    elif tier == "high":
        shares["gpu"] += 0.03
        shares["storage"] -= 0.01

    total = sum(max(0.01, v) for v in shares.values())
    shares = {k: max(0.01, v) / total for k, v in shares.items()}
    alloc = {k + "Budget": int(total_budget * v) for k, v in shares.items()}
    gap = total_budget - sum(alloc.values())
    alloc["gpuBudget"] += gap
    return alloc

def is_recommendable_gpu(part: Dict[str, Any]) -> bool:
    """Apply exclusions to catalog, retailer and fallback paths alike."""
    identity = " ".join(str(part.get(key) or "") for key in ("id", "performance_ref_id", "name", "product_name"))
    return not re.search(r"rtx[\s_-]*30\d{2}", identity, re.I)

def resolve_verified_gpu_market_prices(
    gpu_pref: str = "ANY",
    gpu_maker_prefs: Optional[List[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Return only GPU models with a current, valid Danawa graphics-card price.

    The embedded catalog is useful for specs, but it must not be used as the
    deciding price for a recommendation. Discontinued models frequently have
    stale prices, and search results can otherwise fall back to the wrong item.
    """
    maker_prefs = normalize_gpu_maker_prefs(gpu_maker_prefs)
    candidates = [
        part for part in GPU_CATALOG
        if is_recommendable_gpu(part)
        and (gpu_pref == "ANY" or normalize_text(part.get("vendor")) == normalize_text(gpu_pref))
    ]
    resolved: Dict[str, Dict[str, Any]] = {}
    pending: Dict[Any, Dict[str, Any]] = {}
    executor = ThreadPoolExecutor(max_workers=8)
    try:
        for part in candidates:
            part_id = str(part.get("id") or canonical_name(part.get("name")))
            # A maker preference changes the actual SKU, so it cannot reuse the
            # generic chip-level cache.
            checked = state.GPU_MARKET_PRICE_CHECKED_AT.get(part_id)
            cache_recent = bool(checked and datetime.utcnow() - checked < timedelta(minutes=5))
            if not maker_prefs and part_id in state.GPU_MARKET_PRICE_CACHE and cache_recent:
                cached = state.GPU_MARKET_PRICE_CACHE[part_id]
                if cached and database.verified_price_info(cached):
                    resolved[part_id] = {**part, **cached}
                    continue
                if cached is None:
                    continue

            cached = None if maker_prefs else database.db_lookup_price_info(part, "gpu")
            if cached and not cached.get("stale"):
                info = {
                    "price": safe_int(cached.get("price"), 0),
                    "url": cached.get("url"),
                    "image_url": cached.get("image_url") or part.get("image_url"),
                    "shop": cached.get("shop") or "Danawa",
                    "currency": cached.get("currency") or "KRW",
                    "price_source": cached.get("price_source") or "db_current",
                    "price_source_label": cached.get("matched_by") or "db_current",
                    "product_name": cached.get("name") or part.get("name"),
                    "scraped_at": cached.get("scraped_at"),
                    "verified": True,
                    "price_status": "verified",
                }
                state.GPU_MARKET_PRICE_CACHE[part_id] = info
                state.GPU_MARKET_PRICE_CHECKED_AT[part_id] = datetime.utcnow()
                resolved[part_id] = {**part, "base_price": safe_int(part.get("price"), 0), **info}
                continue

            future = executor.submit(
                retail.fetch_market_top_product,
                database.market_lookup_name(part, "gpu"),
                "gpu",
                4.0,
                safe_int(part.get("price"), 0),
                maker_prefs or None,
                False,
            )
            pending[future] = part

        try:
            for future in as_completed(pending, timeout=3.0):
                part = pending[future]
                part_id = str(part.get("id") or canonical_name(part.get("name")))
                try:
                    live = future.result()
                except Exception:
                    live = None
                if not live or safe_int(live.get("price"), 0) <= 0:
                    if not maker_prefs:
                        state.GPU_MARKET_PRICE_CACHE[part_id] = None
                        state.GPU_MARKET_PRICE_CHECKED_AT[part_id] = datetime.utcnow()
                    continue
                try:
                    saved = database.store_danawa_price(part, "gpu", live)
                except Exception:
                    saved = {
                        "price": safe_int(live.get("price"), 0),
                        "url": live.get("url"),
                        "image_url": live.get("image_url"),
                        "shop": live.get("shop") or "Danawa",
                        "currency": "KRW",
                        "price_source": live.get("price_source") or "danawa_top_live",
                        "price_source_label": "danawa_top",
                        "product_name": live.get("name") or part.get("name"),
                        "scraped_at": live.get("scraped_at") or datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    }
                if safe_int(saved.get("price"), 0) <= 0:
                    continue
                info = {
                    "price": safe_int(saved.get("price"), 0),
                    "url": saved.get("url") or live.get("url"),
                    "image_url": saved.get("image_url") or live.get("image_url"),
                    "shop": saved.get("shop") or "Danawa",
                    "currency": saved.get("currency") or "KRW",
                    "price_source": saved.get("price_source") or "danawa_top_live",
                    "price_source_label": saved.get("matched_by") or "danawa_top",
                    "product_name": saved.get("product_name") or live.get("name") or part.get("name"),
                    "scraped_at": saved.get("scraped_at"),
                    "verified": True,
                    "price_status": "verified",
                }
                if not maker_prefs:
                    state.GPU_MARKET_PRICE_CACHE[part_id] = info
                    state.GPU_MARKET_PRICE_CHECKED_AT[part_id] = datetime.utcnow()
                resolved[part_id] = {**part, "base_price": safe_int(part.get("price"), 0), **info}
        except TimeoutError:
            pass

        if not maker_prefs:
            for future, part in pending.items():
                if future.done():
                    continue
                future.cancel()
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    return resolved

def apply_price_info_to_part(part: Dict[str, Any], info: Optional[Dict[str, Any]]) -> None:
    if not part:
        return
    if not info:
        part["verified"] = database.verified_price_info(part)
        if not part["verified"]:
            part["price_status"] = "estimated" if safe_int(part.get("price"), 0) > 0 else "unavailable"
        return
    price = safe_int(info.get("price"), 0)
    if price > 0:
        part["price"] = price
    if info.get("url"):
        part["url"] = info.get("url")
    if info.get("image_url"):
        part["image_url"] = info.get("image_url")
    part["shop"] = info.get("shop") or "Danawa"
    part["currency"] = info.get("currency") or "KRW"
    part["price_source"] = info.get("price_source") or "danawa_top"
    part["price_source_label"] = info.get("matched_by") or "danawa_top"
    part["stale"] = bool(info.get("stale"))
    observed_at = info.get("price_checked_at") or info.get("scraped_at")
    if observed_at:
        part["scraped_at"] = observed_at
        part["price_checked_at"] = observed_at
    if info.get("product_name"):
        part["product_name"] = info.get("product_name")
    elif info.get("name"):
        part["product_name"] = info.get("name")
    part["verified"] = database.verified_price_info(part)
    part["price_status"] = ("cached" if info.get("price_status") == "cached" else "verified") if part["verified"] else ("stale" if part["stale"] else "estimated")

def recompute_plan_total(plan: Dict[str, Any]) -> None:
    parts = plan.get("parts") or {}
    total = sum(safe_int(part.get("price"), 0) for part in parts.values() if isinstance(part, dict))
    plan["totalPrice"] = total
    plan["total_price"] = total
    plan.setdefault("debug", {})["total_price"] = total
    tier_budget = safe_int(plan.get("tierBudget"), 0)
    max_budget = safe_int(plan.get("budget_max"), 0) or tier_budget
    min_budget = safe_int(plan.get("budget_min"), 0)
    overrun = max(0, total - tier_budget) if tier_budget else 0
    plan["debug"]["overrun"] = overrun
    if tier_budget:
        budget_fit = max(-0.55, 1.0 - overrun / max(1.0, tier_budget * 0.16)) if overrun else 1.0 - min(0.22, (tier_budget - total) / tier_budget * 0.18)
        plan["debug"]["budget_fit"] = round(budget_fit, 4)
        plan.setdefault("predictions", {})["budget_fit"] = round(budget_fit, 4)
    plan["budget_overrun"] = max(0, total - max_budget) if max_budget else 0
    plan["budget_status"] = "over_budget" if max_budget and total > max_budget else "under_budget" if total < min_budget else "within_budget"
    selected_parts = [part for part in parts.values() if isinstance(part, dict)]
    verified_count = sum(1 for part in selected_parts if database.verified_price_info(part))
    plan["verified_part_count"] = verified_count
    plan["part_count"] = len(selected_parts)
    plan["total_is_estimate"] = verified_count < len(selected_parts)
    plan["price_status"] = "verified" if not plan["total_is_estimate"] else "estimated"
    for part_type in ("cpu", "gpu"):
        if isinstance(parts.get(part_type), dict) and part_type in plan.get("predictions", {}):
            plan["predictions"][part_type]["pred_price"] = safe_int(parts[part_type].get("price"), 0)
    fps = plan.setdefault("fps", {})
    high = safe_float(fps.get("fps_by_option", {}).get("high"), 0.0)
    high_low1 = safe_float(fps.get("low1_by_option", {}).get("high"), 0.0)
    plan["cost_per_frame"] = round(total / high) if total > 0 and high > 0 else None
    fps["cost_per_frame"] = plan["cost_per_frame"]
    fps["price_per_frame_krw"] = None
    fps["price_per_frame_by_option"] = {
        option: value_metrics(value, total)["price_per_frame_krw"]
        for option, value in fps.get("fps_by_option", {}).items()
    }
    fps["price_per_frame_basis"] = "total_build_price / average_fps"
    if high > 0:
        metrics = value_metrics(
            high,
            total,
            fps.get("target_fps"),
            high_low1,
            fps.get("target_low1_fps"),
        )
        fps["value_score"] = metrics["score"]
        fps["price_per_frame_krw"] = metrics["price_per_frame_krw"]
        fps["value_fps_per_1000krw"] = metrics["fps_per_1000krw"]
        fps["value_label"] = value_label(metrics["score"])
        fps["target_fps"] = metrics["target_fps"]
        fps["target_low1_fps"] = metrics["target_low1_fps"]
        fps["target_coverage"] = metrics["target_coverage"]
        fps["low1_target_coverage"] = metrics["low1_target_coverage"]
        fps["capacity_label"] = metrics["capacity_label"]


def collect_display_parts(payload: Dict[str, Any]) -> Dict[Tuple[str, str], Tuple[Dict[str, Any], str]]:
    out: Dict[Tuple[str, str], Tuple[Dict[str, Any], str]] = {}
    for plan in (payload.get("results") or {}).values():
        for part_type, part in (plan.get("parts") or {}).items():
            normalized_type = normalize_text(part_type)
            if normalized_type not in state.DISPLAY_PRICE_TYPES:
                continue
            if not isinstance(part, dict) or not part.get("name"):
                continue
            key = (normalized_type, canonical_name(part.get("name")))
            out.setdefault(key, (part, part_type))
    return out

def resolve_recommendation_price_cache(
    wanted: Dict[Tuple[str, str], Tuple[Dict[str, Any], str]],
    gpu_maker_prefs: Optional[List[str]] = None,
) -> Dict[Tuple[str, str], Optional[Dict[str, Any]]]:
    resolved: Dict[Tuple[str, str], Optional[Dict[str, Any]]] = {}
    pending: Dict[Any, Tuple[Tuple[str, str], Dict[str, Any], str, Optional[Dict[str, Any]]]] = {}
    maker_prefs = normalize_gpu_maker_prefs(gpu_maker_prefs)

    executor = ThreadPoolExecutor(max_workers=6)
    try:
        for key, (part, part_type) in wanted.items():
            normalized_type = normalize_text(part_type)
            raw_source = normalize_text(part.get("price_source"))
            raw_url = part.get("url") or part.get("shop_url") or part.get("product_url")
            if database.verified_price_info(part):
                resolved[key] = {
                    "price": safe_int(part.get("price"), 0),
                    "url": raw_url,
                    "image_url": part.get("image_url"),
                    "shop": part.get("shop") or "Danawa",
                    "currency": part.get("currency") or "KRW",
                    "price_source": part.get("price_source") or "danawa_top_live",
                    "matched_by": part.get("price_source_label") or "danawa_top",
                    "product_name": part.get("product_name") or part.get("name"),
                    "scraped_at": part.get("price_checked_at") or part.get("scraped_at"),
                    "verified": True,
                    "price_status": part.get("price_status") or "verified",
                }
                continue
            cached = None if normalized_type == "gpu" and maker_prefs else database.db_lookup_price_info(part, part_type)
            if cached and not cached.get("stale"):
                resolved[key] = cached
                continue
            future = executor.submit(
                retail.fetch_market_top_product,
                database.market_lookup_name(part, part_type),
                part_type,
                2.5,
                safe_int(part.get("base_price"), 0) or safe_int(part.get("price"), 0),
                maker_prefs if normalized_type == "gpu" else None,
                False,
            )
            pending[future] = (key, part, part_type, cached)

        try:
            # Requests queued behind the six workers need their own timeout window.
            iterator = as_completed(pending, timeout=max(3.0, math.ceil(len(pending) / 6) * 3.0))
            for future in iterator:
                key, part, part_type, cached = pending.pop(future)
                try:
                    live = future.result()
                    if live and safe_int(live.get("price"), 0) > 0:
                        resolved[key] = database.store_danawa_price(part, part_type, live)
                    else:
                        resolved[key] = cached if cached and not cached.get("stale") else None
                except Exception:
                    resolved[key] = cached if cached and not cached.get("stale") else None
        except TimeoutError:
            pass

        for future, (key, _part, _part_type, cached) in pending.items():
            future.cancel()
            resolved.setdefault(key, cached if cached and not cached.get("stale") else None)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    return resolved

def refresh_recommendation_prices(payload: Dict[str, Any]) -> None:
    maker_prefs = normalize_gpu_maker_prefs((payload.get("input") or {}).get("gpu_brands"))
    price_cache = resolve_recommendation_price_cache(collect_display_parts(payload), maker_prefs)
    for plan in (payload.get("results") or {}).values():
        for part_type, part in (plan.get("parts") or {}).items():
            normalized_type = normalize_text(part_type)
            key = (normalized_type, canonical_name(part.get("name") if isinstance(part, dict) else ""))
            if normalized_type in state.DISPLAY_PRICE_TYPES:
                apply_price_info_to_part(part, price_cache.get(key))
        recompute_plan_total(plan)

def price_lookup_response(body: Dict[str, Any]) -> Dict[str, Any]:
    items = body.get("items") if isinstance(body, dict) else []
    if not isinstance(items, list):
        items = []

    maker_prefs = normalize_gpu_maker_prefs(
        body.get("gpu_brands") or body.get("gpu_makers") or body.get("gpu_brand_prefs")
    ) if isinstance(body, dict) else []
    results: List[Dict[str, Any]] = []
    wanted = {}
    for item in items[:20]:
        if isinstance(item, dict) and item.get("name"):
            part_type = normalize_text(item.get("part_type") or item.get("type") or "part")
            # Request metadata is not evidence that the supplied price is current.
            wanted[(part_type, canonical_name(item["name"]))] = ({**item, "price_source": ""}, part_type)
    prices = resolve_recommendation_price_cache(wanted, maker_prefs)
    for item in items[:20]:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        part_type = normalize_text(item.get("part_type") or item.get("type") or "part")
        info = prices.get((part_type, canonical_name(item["name"])))
        if not info:
            results.append({
                "id": item.get("id"), "type": part_type, "name": item.get("name"),
                "price": None, "price_source": "unavailable", "price_status": "unavailable",
                "verified": False, "shop": None, "currency": "KRW",
                "url": item.get("url") or retail.danawa_search_url(item.get("name")),
                "image_url": item.get("image_url") or database.part_image_endpoint(item, part_type),
                "scraped_at": None,
            })
            continue
        results.append({
            "id": item.get("id"),
            "type": part_type,
            "name": item.get("name"),
            "product_name": info.get("product_name") or info.get("name"),
            "price": safe_int(info.get("price"), 0),
            "shop": info.get("shop") or "Danawa",
            "currency": info.get("currency") or "KRW",
            "url": info.get("url") or retail.danawa_search_url(item.get("name")),
            "image_url": info.get("image_url") or item.get("image_url") or database.part_image_endpoint(item, part_type),
            "scraped_at": info.get("scraped_at"),
            "price_source": info.get("price_source") or "danawa_top",
            "price_status": ("cached" if info.get("price_status") == "cached" else "verified") if database.verified_price_info(info) else "stale",
            "verified": database.verified_price_info(info),
        })

    return {
        "results": results,
        "db_loaded": state.DB_CACHE.get("loaded", False),
        "db_summary": state.DB_CACHE.get("summary", {}),
    }

def product_search_response(body: Dict[str, Any]) -> Dict[str, Any]:
    payload = price_lookup_response(body)
    payload["results"] = [row for row in payload.get("results", []) if safe_int(row.get("price"), 0) > 0]
    seen_ids = {row.get("id") for row in payload.get("results", []) if isinstance(row, dict)}
    items = body.get("items") if isinstance(body, dict) else []
    if isinstance(items, list):
        for item in items[:20]:
            if not isinstance(item, dict) or not item.get("name") or item.get("id") in seen_ids:
                continue
            fallback_price = safe_int(item.get("base_price"), 0) or safe_int(item.get("price"), 0)
            if fallback_price <= 0:
                continue
            part_type = normalize_text(item.get("type") or item.get("part_type") or "part")
            payload.setdefault("results", []).append({
                "id": item.get("id"),
                "type": part_type,
                "name": item.get("name"),
                "product_name": item.get("product_name") or item.get("name"),
                "price": fallback_price,
                "shop": item.get("shop") or "Catalog",
                "currency": item.get("currency") or "KRW",
                "url": item.get("url") or retail.danawa_search_url(item.get("name")),
                "image_url": item.get("image_url") or database.part_image_endpoint(item, part_type),
                "scraped_at": item.get("scraped_at"),
                "price_source": "catalog_fallback",
                "price_status": "estimated",
                "verified": False,
            })
    payload["source"] = "danawa_compuzone_lookup"
    return payload
