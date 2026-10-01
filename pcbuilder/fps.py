"""Game FPS estimation and optional graphics scenarios."""
from __future__ import annotations

import logging
import sqlite3
import copy
from threading import RLock
from product_metadata import (
    canonical_name,
    clean_visible_text,
    normalize_text,
    safe_float,
    safe_int,
)
from game_benchmarks import estimate_from_measurements, load_measurements
from graphics_estimates import graphics_scenarios
from typing import Any, Dict, List, Optional, Tuple
from server_catalogs import (
    CPU_CATALOG,
    GPU_CATALOG,
    CATALOGS,
    GAME_OPTIONS,
    BENCHMARK_FPS_BY_GPU,
    GAME_FPS_PROFILES,
)
from . import runtime as state
from . import database
from . import pricing
from . import retail
from . import utils
from .cache import MemoryCache
from .revisions import database_stamp, file_stamp, fingerprint

_fps_cache = MemoryCache(max_entries=2048)
_benchmark_lock = RLock()
_benchmark_revision = None


def _fps_revision():
    """Refresh all file-backed estimator inputs after an in-process replacement."""
    global _benchmark_revision
    import game_benchmarks
    import game_database
    import graphics_estimates
    import rendering_calibration
    fields = ('id', 'name', 'performance_ref_id', 'perf', 'perf_1080', 'perf_1440',
              'perf_2160', 'gb', 'type', 'speed')
    references = tuple((kind, tuple(tuple(part.get(field) for field in fields) for part in rows))
                       for kind, rows in sorted(CATALOGS.items()) if kind in {'gpu', 'cpu', 'ram'})
    revision = (database_stamp(), file_stamp(game_benchmarks.SNAPSHOT_PATH),
                file_stamp(game_database.DB_PATH), file_stamp(str(game_database.DB_PATH) + '-wal'),
                file_stamp(rendering_calibration.CALIBRATION_PATH),
                references)
    if revision != _benchmark_revision:
        with _benchmark_lock:
            if revision != _benchmark_revision:
                game_benchmarks.clear_caches()
                for function in (graphics_estimates.graphics_measurements,
                                 graphics_estimates.feature_support,
                                 rendering_calibration.calibration_data):
                    clear = getattr(function, 'cache_clear', None)
                    if clear:
                        clear()
                _benchmark_revision = revision
    return revision


def game_genre_for_id(game: Any) -> str:
    key = normalized_game_key(game)
    item = next((row for row in GAME_OPTIONS if row.get("id") == key), None)
    return normalize_text((item or {}).get("genre") or pricing.game_profile(key)[0]) or "default"

def resolve_fps_part(part_type: str, raw: Any) -> Tuple[Optional[Dict[str, Any]], str]:
    """Resolve a direct-spec SKU to its benchmark profile.

    Live Danawa products carry ``performance_ref_id``.  The retail SKU keeps
    its own price/name in the UI, while FPS must use the chip-level profile to
    avoid treating different cooler/board-partner variants as different GPUs.
    """
    requested_id = raw.get("id") if isinstance(raw, dict) else raw
    requested_id = clean_visible_text(requested_id)
    reference_id = raw.get("performance_ref_id") if isinstance(raw, dict) else ""
    part = find_catalog_part(part_type, reference_id or requested_id)
    if part:
        resolved = dict(part)
        if isinstance(raw, dict) and part_type == "ram":
            # RAM capacity, generation, and speed materially affect the
            # estimate and can be read safely from the live product response.
            gb = safe_int(raw.get("gb"), 0)
            speed = safe_int(raw.get("speed"), 0)
            ram_type = clean_visible_text(raw.get("type"))
            if 4 <= gb <= 512:
                resolved["gb"] = gb
            if 1600 <= speed <= 10000:
                resolved["speed"] = speed
            if normalize_text(ram_type) in {"ddr4", "ddr5"}:
                resolved["type"] = ram_type.upper()
        return resolved, requested_id or clean_visible_text(part.get("id"))

    # A new RAM SKU may not resemble an embedded retail profile closely enough
    # to map by name.  Its three relevant specs are sufficient for this engine.
    if part_type == "ram" and isinstance(raw, dict):
        gb = safe_int(raw.get("gb"), 0)
        speed = safe_int(raw.get("speed"), 0)
        ram_type = normalize_text(raw.get("type"))
        if 4 <= gb <= 512 and 1600 <= speed <= 10000 and ram_type in {"ddr4", "ddr5"}:
            return {
                "id": requested_id or "live_ram",
                "name": clean_visible_text(raw.get("name")) or "Live RAM",
                "gb": gb,
                "speed": speed,
                "type": ram_type.upper(),
                "tier": "mid",
            }, requested_id or "live_ram"
    return None, requested_id

def fps_estimate_response(body: Dict[str, Any]) -> Dict[str, Any]:
    """Use the recommendation FPS engine for the direct-spec screen too."""
    if not isinstance(body, dict):
        raise ValueError("invalid fps request")

    parts: Dict[str, Dict[str, Any]] = {}
    input_ids: Dict[str, str] = {}
    for part_type in ("gpu", "cpu", "ram"):
        raw = body.get(part_type)
        part, selected_id = resolve_fps_part(part_type, raw)
        if not part:
            raise ValueError(f"unknown {part_type}")
        parts[part_type] = dict(part)
        input_ids[part_type] = selected_id or clean_visible_text(part.get("id"))

    game = normalized_game_key(body.get("game") or "cyberpunk2077")
    resolution = utils.resolution_key(body.get("resolution") or "1080")
    refresh = utils.refresh_value(body.get("refresh") or 60)
    tier = normalize_text(body.get("tier") or "mid")
    if tier not in state.TIER_RANK:
        tier = "mid"
    fps = estimate_fps_bundle(
        parts["gpu"],
        parts["cpu"],
        parts["ram"],
        game,
        resolution,
        refresh,
        tier,
        [game_genre_for_id(game)],
    )
    attach_graphics_modes(fps, parts["gpu"], parts["cpu"], game, resolution)
    return {
        "fps": fps,
        "input": {
            "gpu": input_ids["gpu"],
            "cpu": input_ids["cpu"],
            "ram": input_ids["ram"],
            "game": game,
            "resolution": resolution,
            "refresh": refresh,
            "tier": tier,
        },
    }

def game_key_variants(game: str) -> set:
    g = normalize_text(game).replace(" ", "_")
    variants = {g, g.replace("_", "")}
    aliases = {
        "csgo2": {"cs2", "counter_strike_2", "counterstrike2"},
        "cs2": {"csgo2", "counter_strike_2", "counterstrike2"},
        "cyberpunk2077": {"cyberpunk_2077", "cyberpunk_2077_phantom_liberty"},
        "baldurs_gate3": {"baldur's_gate_3", "baldurs_gate_3", "baldur_gate_3"},
        "cities_skylines2": {"cities_skylines_2"},
        "msfs2024": {"microsoft_flight_simulator_2024", "flight_simulator_2024"},
        "ffxiv": {"final_fantasy_xiv"},
        "pubg": {"playerunknowns_battlegrounds", "pubg_battlegrounds", "battlegrounds"},
        "genshin_impact": {"genshin", "원신"},
        "wuthering_waves": {"wutheringwaves", "명조", "명조워더링웨이브"},
        "ghost_of_tsushima": {"ghost_of_tsushima_directors_cut", "ghost_of_tsushima_director_s_cut"},
        "red_dead_redemption2": {"red_dead_redemption_2", "rdr2"},
        "horizon_forbidden_west": {"horizon_forbidden_west_complete_edition"},
        "god_of_war_ragnarok": {"god_of_war_ragnarok", "god_of_war_ragnarok_pc"},
        "black_myth_wukong": {"black_myth_wu_kong"},
        "hogwarts_legacy": {"hogwarts"},
        "zenless_zone_zero": {"zzz", "zenlesszonezero"},
    }
    variants.update(aliases.get(g, set()))
    return variants

def db_lookup_benchmarks(part: Dict[str, Any], game: str, fallback_all: bool = True) -> List[Dict[str, Any]]:
    database.ensure_db_cache_loaded()
    part_key = canonical_name(part.get("name"))
    game_key = normalize_text(game).replace(" ", "_")
    cache_key = (part_key, game_key, bool(fallback_all))
    cached = state.BENCHMARK_LOOKUP_CACHE.get(cache_key)
    if cached is not None:
        return list(cached)

    match = database._best_match_key(part_key, state.DB_CACHE.get("benchmarks_by_name", {}).keys())
    if not match:
        state.BENCHMARK_LOOKUP_CACHE[cache_key] = ()
        return []
    by_game = state.DB_CACHE["benchmarks_by_name"].get(match, {})
    for variant in sorted(game_key_variants(game)):
        samples = by_game.get(variant, [])
        if samples:
            state.BENCHMARK_LOOKUP_CACHE[cache_key] = tuple(samples)
            return samples
    if not fallback_all:
        state.BENCHMARK_LOOKUP_CACHE[cache_key] = ()
        return []
    all_samples: List[Dict[str, Any]] = []
    for rows in by_game.values():
        all_samples.extend(rows)
    state.BENCHMARK_LOOKUP_CACHE[cache_key] = tuple(all_samples)
    return all_samples


def normalized_game_key(game: Any) -> str:
    key = normalize_text(game).replace(" ", "_")
    aliases = {"cs2": "csgo2", "cyberpunk_2077": "cyberpunk2077", "apex_legends": "apex", "final_fantasy_xiv": "ffxiv"}
    for item in GAME_OPTIONS:
        if key == normalize_text(item["label"]).replace(" ", "_"):
            return item["id"]
    return aliases.get(key, key)

def game_frame_cap(game: Any) -> Optional[float]:
    return state.GAME_FRAME_CAPS.get(normalized_game_key(game))

def find_catalog_part(part_type: str, part_id: Any) -> Optional[Dict[str, Any]]:
    key = normalize_text(part_id)
    if not key:
        return None
    return next((part for part in CATALOGS.get(part_type, []) if normalize_text(part.get("id")) == key), None)

def target_fps_for_game(tier: str, refresh: int, game: str) -> float:
    game_class, _ = pricing.game_profile(game)
    target = float(refresh)
    cap = game_frame_cap(game)
    return min(target, cap) if cap else target

def gpu_base_perf(gpu: Dict[str, Any], resolution: str) -> float:
    if resolution == "2160":
        return safe_float(gpu.get("perf_2160"), safe_float(gpu.get("perf_1440")) * 0.62)
    if resolution == "1440":
        return safe_float(gpu.get("perf_1440"), safe_float(gpu.get("perf_1080")) * 0.72)
    return safe_float(gpu.get("perf_1080"), 0.0)

def benchmark_row_for_gpu(gpu: Dict[str, Any]) -> Optional[Dict[str, float]]:
    gid = normalize_text(gpu.get("id"))
    if gid in BENCHMARK_FPS_BY_GPU:
        return BENCHMARK_FPS_BY_GPU[gid]
    name_key = canonical_name(gpu.get("name"))
    return BENCHMARK_FPS_BY_GPU.get(name_key)

def hierarchy_fps(gpu: Dict[str, Any], resolution: str, setting: str) -> Optional[float]:
    db_setting = "medium" if resolution == "1080" and setting in {"low", "medium"} else "high"
    db_hit = estimate_fps_from_db(gpu, "average_games", resolution, db_setting)
    if db_hit:
        base = db_hit[0]
        if setting == "ultra":
            return base * 0.83
        if setting == "high" or (resolution == "1080" and setting == "medium"):
            return base
        if setting == "medium":
            return base * 1.24
        return base * (1.14 if resolution == "1080" else 1.46)

    row = benchmark_row_for_gpu(gpu)
    if not row:
        return None
    high = row["h1080"] if resolution == "1080" else row["h1440"] if resolution == "1440" else row["h2160"]
    if setting == "ultra":
        return high * 0.83
    if setting == "high":
        return high
    if setting == "medium":
        return row["m1080"] if resolution == "1080" else high * 1.24
    return row["m1080"] * 1.14 if resolution == "1080" else high * 1.46

def cpu_fps_factor(cpu: Dict[str, Any], game: str, resolution: str, setting: str, raw_fps: float) -> float:
    g = normalize_text(game).replace(" ", "_")
    profile = GAME_FPS_PROFILES.get(g, GAME_FPS_PROFILES["default"])
    cpu_norm = retail.clamp(safe_float(cpu.get("perf"), 0.0) / 100.0, 0.16, 1.08)
    quality_boost = {"low": 1.18, "medium": 1.08, "high": 1.0, "ultra": 0.94}.get(setting, 1.0)
    base_cap = profile["cpu_cap"].get(resolution, GAME_FPS_PROFILES["default"]["cpu_cap"][resolution])
    cpu_cap = base_cap * (0.48 + cpu_norm * 0.64) * quality_boost
    if raw_fps <= cpu_cap:
        return 1.0
    bottleneck = max(0.38, cpu_cap / max(1.0, raw_fps))
    return 1.0 - profile["cpu_weight"] * (1.0 - bottleneck)

def ram_fps_factor(ram: Dict[str, Any], game: str) -> float:
    g = normalize_text(game).replace(" ", "_")
    profile = GAME_FPS_PROFILES.get(g, GAME_FPS_PROFILES["default"])
    gb = safe_float(ram.get("gb"), 16.0)
    ram_type = normalize_text(ram.get("type"))
    speed = safe_float(ram.get("speed"), 0.0)
    if gb <= 8:
        return 0.88 if profile.get("ram_hungry") else 0.94
    if profile.get("ram_hungry") and gb < 32:
        return 0.96
    factor = 1.0
    if gb >= 32:
        factor += 0.015 if profile.get("ram_hungry") else 0.006
    if ram_type == "ddr5":
        factor += 0.012 if speed >= 5600 else 0.006
    elif ram_type == "ddr4" and speed >= 3200:
        factor += 0.004
    return round(min(1.035, factor), 4)

def quality_scale(resolution: str, setting: str) -> float:
    if setting == "ultra":
        return 0.83
    if setting == "high":
        return 1.0
    if setting == "medium":
        return 1.24
    return 1.14 * 1.24 if resolution == "1080" else 1.46

def average_benchmark_rows(rows: List[Dict[str, Any]]) -> Optional[Tuple[float, float]]:
    avg_values = [safe_float(x.get("avg_fps")) for x in rows if safe_float(x.get("avg_fps")) > 0]
    if not avg_values:
        return None
    low_values = [safe_float(x.get("low1_fps")) for x in rows if safe_float(x.get("low1_fps")) > 0]
    avg = sum(avg_values) / len(avg_values)
    low = sum(low_values) / len(low_values) if low_values else avg * 0.8
    return avg, low

def adjust_benchmark_quality(avg: float, low: float, source_setting: str, target_setting: str, resolution: str) -> Tuple[float, float]:
    ratio = quality_scale(resolution, target_setting) / max(0.01, quality_scale(resolution, source_setting))
    return avg * ratio, low * ratio

def estimate_fps_from_catalog(gpu: Dict[str, Any], cpu: Dict[str, Any], ram: Dict[str, Any],
                              game: str, resolution: str, setting: str) -> Tuple[float, float]:
    g = normalize_text(game).replace(" ", "_")
    profile = GAME_FPS_PROFILES.get(g, GAME_FPS_PROFILES["default"])
    base = hierarchy_fps(gpu, resolution, setting)
    if base is None:
        genre_class, game_factor = pricing.game_profile(game)
        opt_factor = {"low": 1.45, "medium": 1.12, "high": 1.00, "ultra": 0.83}.get(setting, 1.0)
        res_scale = {"1080": 4.30, "1440": 2.95, "2160": 1.72}.get(resolution, 2.6)
        perf = max(1.0, gpu_base_perf(gpu, resolution))
        raw = perf * res_scale * game_factor * opt_factor
        raw *= {"fps": 1.18, "rpg": 0.92, "mmo": 1.05, "sim": 0.86, "default": 1.0}.get(genre_class, 1.0)
    else:
        raw = base * profile["scale"].get(resolution, 1.0)
    avg = max(5.0, raw * cpu_fps_factor(cpu, game, resolution, setting, raw) * ram_fps_factor(ram, game))
    low1 = avg * safe_float(profile.get("low1"), 0.78)
    return round(avg, 1), round(low1, 1)

def estimate_fps_from_db(gpu: Dict[str, Any], game: str, resolution: str, setting: str) -> Optional[Tuple[float, float]]:
    samples = db_lookup_benchmarks(gpu, game, fallback_all=False)
    if not samples:
        return None

    exact = [s for s in samples if s.get("resolution") == resolution and normalize_text(s.get("setting")) == setting]
    exact_avg = average_benchmark_rows(exact)
    if exact_avg:
        avg, low = exact_avg
        return round(avg, 1), round(low, 1)

    same_res = [s for s in samples if s.get("resolution") == resolution]
    if same_res:
        by_setting = {
            key: [s for s in same_res if normalize_text(s.get("setting")) == key]
            for key in ["low", "medium", "high", "ultra"]
        }
        if setting == "low":
            source_setting = "medium" if by_setting["medium"] else "high"
        elif setting == "medium":
            source_setting = "high"
        elif setting == "ultra":
            source_setting = "high"
        else:
            source_setting = "medium" if by_setting["medium"] else "ultra"

        source_avg = average_benchmark_rows(by_setting.get(source_setting, []))
        if source_avg:
            avg, low = adjust_benchmark_quality(source_avg[0], source_avg[1], source_setting, setting, resolution)
            return round(avg, 1), round(low, 1)

        same_res_avg = average_benchmark_rows(same_res)
        if same_res_avg:
            return round(same_res_avg[0], 1), round(same_res_avg[1], 1)

    # Different resolutions cannot be averaged into the requested resolution.
    return None


def estimate_fps_bundle(gpu: Dict[str, Any], cpu: Dict[str, Any], ram: Dict[str, Any],
                        game: str, resolution: str, refresh: int, tier: str, genres: List[str]) -> Dict[str, Any]:
    key = (_fps_revision(), fingerprint((gpu, cpu, ram, game, resolution, refresh, tier, genres)),
           id(estimate_from_measurements), id(estimate_fps_from_catalog),
           id(load_measurements), id(pricing.game_profile),
           fingerprint(GAME_FPS_PROFILES.get(normalized_game_key(game), GAME_FPS_PROFILES['default'])))
    cached = _fps_cache.get_or_compute(key, lambda: _estimate_fps_bundle_uncached(
        gpu, cpu, ram, game, resolution, refresh, tier, genres), ttl=300)
    return copy.deepcopy(cached)


def _estimate_fps_bundle_uncached(gpu: Dict[str, Any], cpu: Dict[str, Any], ram: Dict[str, Any],
                                game: str, resolution: str, refresh: int, tier: str, genres: List[str]) -> Dict[str, Any]:
    fps_by_option: Dict[str, float] = {}
    low1_by_option: Dict[str, float] = {}
    option_evidence: Dict[str, Dict[str, Any]] = {}
    game = normalized_game_key(game)
    genre_class, _ = pricing.game_profile(game)
    low1_ratio = pricing.low1_ratio_for_genres(genres or [genre_class])
    profile = GAME_FPS_PROFILES.get(game, GAME_FPS_PROFILES["default"])
    cap = game_frame_cap(game)

    for opt in ["low", "medium", "high", "ultra"]:
        measured = estimate_from_measurements(gpu, cpu, ram, game, resolution, opt, profile, CATALOGS)
        if measured:
            avg, low, evidence = measured
        else:
            avg, low = estimate_fps_from_catalog(gpu, cpu, ram, game, resolution, opt)
            cpu_norm = retail.clamp(safe_float(cpu.get("perf"), 0.0) / 100.0, .16, 1.08)
            cpu_ceiling = profile["cpu_cap"][resolution] * (.48 + cpu_norm * .64) * {"low":1.18,"medium":1.08,"high":1.,"ultra":.94}[opt]
            gpu_ceiling = max(avg, hierarchy_fps(gpu, resolution, opt) or avg) * profile["scale"][resolution]
            cpu_penalty = max(0, 1 - avg / max(avg, gpu_ceiling)) * 100
            gpu_penalty = max(0, 1 - avg / max(avg, cpu_ceiling)) * 100
            evidence = {
                "method": "model_estimate", "confidence": "low", "low1_estimated": True,
                "source_url": "", "source_title": "", "reference_gpu": "", "reference_cpu": "",
                "conditions": "게임별 실측 자료 없음 · Native · RT/프레임 생성 OFF",
                "range": {"min": round(avg * .60, 1), "max": round(avg * 1.40, 1)},
                "range_method": "heuristic_allowance_not_statistical_interval",
                "notes": ["해당 게임의 검증된 실측 데이터가 없어 GPU 지수와 게임 부하 모델로 추정했습니다", "1% Low는 추정치"],
                "bottleneck": {"estimated": True, "cpu_penalty_pct": cpu_penalty,
                               "gpu_penalty_pct": gpu_penalty, "limiting_component": "cpu" if cpu_penalty > gpu_penalty else "gpu",
                               "method": "workload_model", "note": "게임 부하 모델 추정 · 실측 병목률 아님"},
            }
        bottleneck = evidence.get("bottleneck") or {}
        if "gpu_penalty_pct" not in bottleneck:
            bottleneck["gpu_penalty_pct"] = max(0, 1 - avg / max(avg, safe_float(bottleneck.get("cpu_fps_ceiling"), avg))) * 100
        cpu_percent = round(retail.clamp(safe_float(bottleneck.get("cpu_penalty_pct"), 0), 0, 100), 1)
        gpu_percent = round(retail.clamp(safe_float(bottleneck.get("gpu_penalty_pct"), 0), 0, 100), 1)
        bottleneck.update({"cpu_percent": cpu_percent, "gpu_percent": gpu_percent,
                           "percent": max(cpu_percent, gpu_percent),
                           "limiting_component": "balanced" if max(cpu_percent, gpu_percent) < 10 else "cpu" if cpu_percent >= gpu_percent else "gpu",
                           "comparison_source_url": "https://pc-builds.com/ko/bottleneck-calculator/",
                           "note": "선택 게임·해상도·옵션의 성능 여유 차이를 퍼센트로 보정한 자체 추정 · PC-Builds 수치와는 다를 수 있음"})
        if cap:
            avg, low = min(avg, cap), min(low, cap)
            evidence["range"] = {key: round(min(value, cap), 1) for key, value in evidence["range"].items()}
        fps_by_option[opt] = round(avg, 1)
        low1_by_option[opt] = round(min(avg, max(1.0, low)), 1)
        option_evidence[opt] = evidence

    # Preserve every measured value. Preset interpolation is monotonic by
    # construction; a source measurement must not be rewritten to enforce order.
    high_avg, high_low = fps_by_option["high"], low1_by_option["high"]
    evidence = option_evidence["high"]
    target_fps = target_fps_for_game(tier, refresh, game)
    target_low1 = target_fps * low1_ratio
    metrics = pricing.value_metrics(high_avg, safe_float(gpu.get("price"), 0.0), target_fps, high_low, target_low1)
    fps_source = evidence["method"]
    return {
        "game": game, "fps_by_option": fps_by_option, "low1_by_option": low1_by_option,
        "avg_fps": high_avg, "low1_fps": high_low,
        "high_setting_avg_fps": high_avg, "high_setting_low1_fps": high_low,
        "hz_coverage": round(retail.clamp(high_avg / max(1, refresh), 0.0, 1.6), 3),
        "value_label": pricing.value_label(metrics["score"]), "value_score": metrics["score"],
        "value_fps_per_1000krw": metrics["fps_per_1000krw"],
        "target_fps": metrics["target_fps"], "target_low1_fps": metrics["target_low1_fps"],
        "target_coverage": metrics["target_coverage"], "low1_target_coverage": metrics["low1_target_coverage"],
        "capacity_label": metrics["capacity_label"], "frame_cap": cap, "fps_source": fps_source,
        "fps_source_label": {"measured_benchmark": "동일 CPU·GPU 실측 참고", "benchmark_calibrated": "실측 기반 보정 추정", "model_estimate": "모델 추정 · 실측 자료 없음"}[fps_source],
        "confidence": evidence["confidence"], "option_evidence": option_evidence,
        "fps_range_by_option": {opt: item["range"] for opt, item in option_evidence.items()},
        "benchmark_source_url": evidence["source_url"], "benchmark_source_title": evidence["source_title"],
        "benchmark_reference_gpu": evidence["reference_gpu"], "benchmark_reference_cpu": evidence["reference_cpu"],
        "benchmark_conditions": evidence["conditions"], "estimation_notes": evidence["notes"],
        "low1_is_estimated": evidence["low1_estimated"],
        "bottleneck": evidence.get("bottleneck", {"estimated": True, "limiting_component": "unknown", "note": "게임별 실측 자료가 없어 병목을 신뢰성 있게 계산할 수 없습니다"}),
        "bottleneck_by_option": {opt: item.get("bottleneck") for opt, item in option_evidence.items()},
    }

def attach_graphics_modes(fps, gpu, cpu, game, resolution, *, persist=False):
    _fps_revision()
    def reference_native(row):
        match = next((item for item in load_measurements() if all(item.get(key) == row.get(key)
                     for key in ("game", "gpu_id", "cpu_id", "resolution", "preset", "source_url"))), None)
        if match:
            return match["avg_fps"]
        reference_gpu = next((p for p in GPU_CATALOG if p["id"] == row["gpu_id"]), gpu)
        reference_cpu = next((p for p in CPU_CATALOG if p["id"] == row["cpu_id"]), cpu)
        measured = estimate_from_measurements(reference_gpu, reference_cpu, {"gb":32}, game, row["resolution"], row["preset"], GAME_FPS_PROFILES.get(game, GAME_FPS_PROFILES["default"]), CATALOGS)
        return measured[0] if measured else fps["fps_by_option"][row["preset"]]
    fps["graphics_modes"] = graphics_scenarios(gpu, cpu, game, resolution, fps, reference_native)
    if not persist:
        return
    # Offline precomputation may persist scenarios; HTTP requests are read-only.
    try:
        from game_database import save_prediction, digest
        from graphics_estimates import graphics_measurements, feature_support
        from rendering_calibration import calibration_data
        conditions={"gpu":gpu.get("performance_ref_id") or gpu.get("id"),
                    "cpu":cpu.get("performance_ref_id") or cpu.get("id"),
                    "game":game,"resolution":resolution,"preset":"high",
                    "native_options":fps["fps_by_option"],"bottleneck":fps.get("bottleneck")}
        revision="graphics-v4-reviewed-pairs:"+digest([list(graphics_measurements()),feature_support(),calibration_data()])
        save_prediction(conditions,fps["graphics_modes"],revision)
    except (sqlite3.Error, OSError, ValueError):
        logging.warning("Could not persist graphics prediction", exc_info=True)

def part_price(part: Dict[str, Any], part_type: str) -> int:
    raw_price = safe_int(part.get("price"), 0)
    raw_source = normalize_text(part.get("price_source"))
    raw_url = part.get("url") or part.get("shop_url") or part.get("product_url")
    if database.verified_price_info(part):
        return raw_price
    db_price = database.db_lookup_price(part, part_type)
    if db_price is not None and db_price > 0:
        return db_price
    return raw_price
