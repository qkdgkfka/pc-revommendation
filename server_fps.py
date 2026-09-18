from typing import Dict, Any, Tuple


BENCHMARK_FPS_BY_GPU = {
    "gpu_rtx4090": {"m1080":195.6, "h1080":150.1, "h1440":126.6, "h2160":85.0},
    "gpu_rtx4080super": {"m1080":177.2, "h1080":131.1, "h1440":105.8, "h2160":64.8},
    "gpu_rtx4070tisuper": {"m1080":161.3, "h1080":116.9, "h1440":92.0, "h2160":54.8},
    "gpu_rtx4070super": {"m1080":148.4, "h1080":105.8, "h1440":78.6, "h2160":46.1},
    "gpu_rtx4070": {"m1080":130.7, "h1080":92.1, "h1440":68.3, "h2160":39.3},
    "gpu_rtx5070ti": {"m1080":171.5, "h1080":155.4, "h1440":116.8, "h2160":68.6},
    "gpu_rtx5070": {"m1080":152.6, "h1080":132.6, "h1440":96.4, "h2160":54.3},
    "gpu_rtx5060ti16": {"m1080":121.8, "h1080":105.2, "h1440":73.4, "h2160":40.2},
    "gpu_rtx5060": {"m1080":102.0, "h1080":88.5, "h1440":59.8, "h2160":21.8},
    "gpu_rtx4060": {"m1080":83.9, "h1080":57.7, "h1440":38.9, "h2160":16.9},
    "gpu_rtx4060ti": {"m1080":103.5, "h1080":71.8, "h1440":49.3, "h2160":21.5},
    "gpu_rx9070xt": {"m1080":180.1, "h1080":156.6, "h1440":116.5, "h2160":65.8},
    "gpu_rx9070": {"m1080":162.0, "h1080":140.9, "h1440":104.0, "h2160":57.7},
    "gpu_rx7900xtx": {"m1080":174.1, "h1080":125.1, "h1440":102.6, "h2160":64.3},
    "gpu_rx7900xt": {"m1080":163.1, "h1080":115.5, "h1440":92.0, "h2160":55.0},
    "gpu_rx7800xt": {"m1080":133.2, "h1080":89.7, "h1440":69.0, "h2160":40.6},
    "gpu_rx7700xt": {"m1080":114.5, "h1080":78.5, "h1440":60.6, "h2160":34.6},
    "gpu_rx7600": {"m1080":79.3, "h1080":42.2, "h1440":27.9, "h2160":12.7},
    "gpu_rx6600": {"m1080":64.1, "h1080":37.2, "h1440":24.1, "h2160":12.2},
    "nvidia rtx 4090": {"m1080":195.6, "h1080":150.1, "h1440":126.6, "h2160":85.0},
    "nvidia rtx 4080 super": {"m1080":177.2, "h1080":131.1, "h1440":105.8, "h2160":64.8},
    "nvidia rtx 4070 ti super": {"m1080":161.3, "h1080":116.9, "h1440":92.0, "h2160":54.8},
    "nvidia rtx 5070 ti": {"m1080":171.5, "h1080":155.4, "h1440":116.8, "h2160":68.6},
    "nvidia rtx 5070": {"m1080":152.6, "h1080":132.6, "h1440":96.4, "h2160":54.3},
    "nvidia rtx 5060 ti 16gb": {"m1080":121.8, "h1080":105.2, "h1440":73.4, "h2160":40.2},
    "nvidia rtx 5060": {"m1080":102.0, "h1080":88.5, "h1440":59.8, "h2160":21.8},
    "nvidia rtx 4070 super": {"m1080":148.4, "h1080":105.8, "h1440":78.6, "h2160":46.1},
    "nvidia rtx 4070": {"m1080":130.7, "h1080":92.1, "h1440":68.3, "h2160":39.3},
    "nvidia rtx 4060 ti": {"m1080":103.5, "h1080":71.8, "h1440":49.3, "h2160":21.5},
    "nvidia rtx 4060": {"m1080":83.9, "h1080":57.7, "h1440":38.9, "h2160":16.9},
    "amd rx 7900 xtx": {"m1080":174.1, "h1080":125.1, "h1440":102.6, "h2160":64.3},
    "amd rx 9070 xt": {"m1080":180.1, "h1080":156.6, "h1440":116.5, "h2160":65.8},
    "amd rx 9070": {"m1080":162.0, "h1080":140.9, "h1440":104.0, "h2160":57.7},
    "amd rx 7900 xt": {"m1080":163.1, "h1080":115.5, "h1440":92.0, "h2160":55.0},
    "amd rx 7800 xt": {"m1080":133.2, "h1080":89.7, "h1440":69.0, "h2160":40.6},
    "amd rx 7700 xt": {"m1080":114.5, "h1080":78.5, "h1440":60.6, "h2160":34.6},
    "amd rx 7600": {"m1080":79.3, "h1080":42.2, "h1440":27.9, "h2160":12.7},
    "amd rx 6600": {"m1080":64.1, "h1080":37.2, "h1440":24.1, "h2160":12.2},
}

GAME_FPS_PROFILES = {
    "valorant": {"scale":{"1080":2.55,"1440":2.35,"2160":2.05}, "cpu_weight":0.58, "cpu_cap":{"1080":620,"1440":560,"2160":500}, "low1":0.86},
    "csgo2": {"scale":{"1080":2.05,"1440":1.85,"2160":1.55}, "cpu_weight":0.52, "cpu_cap":{"1080":520,"1440":470,"2160":410}, "low1":0.84},
    "cs2": {"scale":{"1080":2.05,"1440":1.85,"2160":1.55}, "cpu_weight":0.52, "cpu_cap":{"1080":520,"1440":470,"2160":410}, "low1":0.84},
    "csgo": {"scale":{"1080":2.50,"1440":2.25,"2160":1.90}, "cpu_weight":0.55, "cpu_cap":{"1080":650,"1440":590,"2160":520}, "low1":0.85},
    "overwatch2": {"scale":{"1080":1.45,"1440":1.35,"2160":1.16}, "cpu_weight":0.34, "cpu_cap":{"1080":410,"1440":360,"2160":300}, "low1":0.82},
    "apex": {"scale":{"1080":1.20,"1440":1.12,"2160":0.96}, "cpu_weight":0.30, "cpu_cap":{"1080":330,"1440":290,"2160":240}, "low1":0.80},
    "rainbow6": {"scale":{"1080":1.70,"1440":1.55,"2160":1.32}, "cpu_weight":0.38, "cpu_cap":{"1080":480,"1440":420,"2160":350}, "low1":0.83},
    "pubg": {"scale":{"1080":1.42,"1440":1.30,"2160":1.08}, "cpu_weight":0.46, "cpu_cap":{"1080":360,"1440":320,"2160":265}, "low1":0.76, "ram_hungry":True},
    "cyberpunk2077": {"scale":{"1080":0.62,"1440":0.60,"2160":0.58}, "cpu_weight":0.10, "cpu_cap":{"1080":210,"1440":185,"2160":155}, "low1":0.76, "ram_hungry":True},
    "witcher3": {"scale":{"1080":0.92,"1440":0.88,"2160":0.82}, "cpu_weight":0.16, "cpu_cap":{"1080":260,"1440":230,"2160":190}, "low1":0.78},
    "elden_ring": {"scale":{"1080":0.82,"1440":0.78,"2160":0.72}, "cpu_weight":0.22, "cpu_cap":{"1080":180,"1440":160,"2160":140}, "low1":0.78},
    "baldurs_gate3": {"scale":{"1080":0.86,"1440":0.82,"2160":0.76}, "cpu_weight":0.28, "cpu_cap":{"1080":220,"1440":195,"2160":165}, "low1":0.76, "ram_hungry":True},
    "ghost_of_tsushima": {"scale":{"1080":0.78,"1440":0.74,"2160":0.68}, "cpu_weight":0.18, "cpu_cap":{"1080":260,"1440":230,"2160":190}, "low1":0.78, "ram_hungry":True},
    "red_dead_redemption2": {"scale":{"1080":0.72,"1440":0.68,"2160":0.62}, "cpu_weight":0.20, "cpu_cap":{"1080":245,"1440":215,"2160":178}, "low1":0.76, "ram_hungry":True},
    "horizon_forbidden_west": {"scale":{"1080":0.66,"1440":0.62,"2160":0.56}, "cpu_weight":0.16, "cpu_cap":{"1080":230,"1440":205,"2160":170}, "low1":0.75, "ram_hungry":True},
    "god_of_war_ragnarok": {"scale":{"1080":0.82,"1440":0.78,"2160":0.70}, "cpu_weight":0.18, "cpu_cap":{"1080":250,"1440":220,"2160":180}, "low1":0.77, "ram_hungry":True},
    "black_myth_wukong": {"scale":{"1080":0.56,"1440":0.52,"2160":0.46}, "cpu_weight":0.14, "cpu_cap":{"1080":210,"1440":185,"2160":150}, "low1":0.72, "ram_hungry":True},
    "hogwarts_legacy": {"scale":{"1080":0.64,"1440":0.60,"2160":0.54}, "cpu_weight":0.24, "cpu_cap":{"1080":220,"1440":195,"2160":160}, "low1":0.70, "ram_hungry":True},
    "starfield": {"scale":{"1080":0.52,"1440":0.49,"2160":0.43}, "cpu_weight":0.40, "cpu_cap":{"1080":150,"1440":130,"2160":105}, "low1":0.68, "ram_hungry":True},
    "genshin_impact": {"scale":{"1080":1.35,"1440":1.20,"2160":1.00}, "cpu_weight":0.24, "cpu_cap":{"1080":240,"1440":210,"2160":180}, "low1":0.82},
    "wuthering_waves": {"scale":{"1080":1.06,"1440":0.96,"2160":0.80}, "cpu_weight":0.30, "cpu_cap":{"1080":260,"1440":225,"2160":185}, "low1":0.78, "ram_hungry":True},
    "zenless_zone_zero": {"scale":{"1080":1.28,"1440":1.14,"2160":0.94}, "cpu_weight":0.24, "cpu_cap":{"1080":260,"1440":225,"2160":185}, "low1":0.82},
    "lostark": {"scale":{"1080":1.28,"1440":1.18,"2160":1.00}, "cpu_weight":0.42, "cpu_cap":{"1080":370,"1440":320,"2160":270}, "low1":0.78},
    "wow": {"scale":{"1080":1.35,"1440":1.24,"2160":1.05}, "cpu_weight":0.48, "cpu_cap":{"1080":360,"1440":310,"2160":260}, "low1":0.76, "ram_hungry":True},
    "ffxiv": {"scale":{"1080":1.16,"1440":1.08,"2160":0.92}, "cpu_weight":0.30, "cpu_cap":{"1080":310,"1440":270,"2160":225}, "low1":0.79},
    "cities_skylines2": {"scale":{"1080":0.45,"1440":0.42,"2160":0.38}, "cpu_weight":0.50, "cpu_cap":{"1080":110,"1440":95,"2160":78}, "low1":0.70, "ram_hungry":True},
    "msfs2024": {"scale":{"1080":0.42,"1440":0.39,"2160":0.35}, "cpu_weight":0.55, "cpu_cap":{"1080":105,"1440":90,"2160":75}, "low1":0.68, "ram_hungry":True},
    "farming_sim": {"scale":{"1080":0.92,"1440":0.86,"2160":0.76}, "cpu_weight":0.28, "cpu_cap":{"1080":240,"1440":205,"2160":170}, "low1":0.76},
    "default": {"scale":{"1080":1.00,"1440":0.96,"2160":0.90}, "cpu_weight":0.24, "cpu_cap":{"1080":260,"1440":230,"2160":190}, "low1":0.78},
}

# Only workload priors, not FPS observations. Actual measured rows are loaded
# from game_benchmarks.json; uncertainty is reported when interpolation is needed.
for _game, _weight, _low1 in [
    ("fortnite", .48, .76), ("marvel_rivals", .40, .74),
    ("cod_black_ops6", .32, .76), ("dragons_dogma2", .55, .68),
    ("dying_light2", .22, .76), ("resident_evil4", .20, .78), ("alan_wake2", .16, .72),
]:
    GAME_FPS_PROFILES[_game] = {**GAME_FPS_PROFILES["default"], "cpu_weight": _weight, "low1": _low1, "ram_hungry": True}

# Game measurements with verified settings live in data/game_benchmarks.json.

# Game-engine caps should be respected before comparing a build with a monitor
# refresh target.  Benchmarks with an external unlocker are not representative
# of the default in-game experience.
GAME_FRAME_CAPS = {"elden_ring": 60.0, "genshin_impact": 60.0}

def normalized_game_key(game: Any) -> str:
    key = normalize_text(game).replace(" ", "_")
    aliases = {"cs2": "csgo2", "cyberpunk_2077": "cyberpunk2077", "apex_legends": "apex", "final_fantasy_xiv": "ffxiv"}
    for item in GAME_OPTIONS:
        if key == normalize_text(item["label"]).replace(" ", "_"):
            return item["id"]
    return aliases.get(key, key)

def game_frame_cap(game: Any) -> Optional[float]:
    return GAME_FRAME_CAPS.get(normalized_game_key(game))

def find_catalog_part(part_type: str, part_id: Any) -> Optional[Dict[str, Any]]:
    key = normalize_text(part_id)
    if not key:
        return None
    return next((part for part in CATALOGS.get(part_type, []) if normalize_text(part.get("id")) == key), None)

def target_fps_for_game(tier: str, refresh: int, game: str) -> float:
    game_class, _ = game_profile(game)
    target = tier_fps_target(tier, refresh, game_class)
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
    cpu_norm = clamp(safe_float(cpu.get("perf"), 0.0) / 100.0, 0.16, 1.08)
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
        genre_class, game_factor = game_profile(game)
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

def enforce_fps_order(fps_by_option: Dict[str, float], low1_by_option: Dict[str, float]) -> None:
    if "high" in fps_by_option and "medium" in fps_by_option and fps_by_option["medium"] <= fps_by_option["high"]:
        fps_by_option["medium"] = round(fps_by_option["high"] + max(1.0, fps_by_option["high"] * 0.05), 1)
        low1_by_option["medium"] = min(fps_by_option["medium"], round(low1_by_option.get("medium", fps_by_option["medium"] * 0.8), 1))
    if "medium" in fps_by_option and "low" in fps_by_option and fps_by_option["low"] <= fps_by_option["medium"]:
        fps_by_option["low"] = round(fps_by_option["medium"] + max(1.0, fps_by_option["medium"] * 0.05), 1)
        low1_by_option["low"] = min(fps_by_option["low"], round(low1_by_option.get("low", fps_by_option["low"] * 0.8), 1))
    if "high" in fps_by_option and "ultra" in fps_by_option and fps_by_option["ultra"] >= fps_by_option["high"]:
        fps_by_option["ultra"] = round(max(2.0, fps_by_option["high"] * 0.88), 1)
        low1_by_option["ultra"] = min(fps_by_option["ultra"], round(low1_by_option.get("ultra", fps_by_option["ultra"] * 0.8), 1))

def estimate_fps_bundle(gpu: Dict[str, Any], cpu: Dict[str, Any], ram: Dict[str, Any],
                        game: str, resolution: str, refresh: int, tier: str, genres: List[str]) -> Dict[str, Any]:
    fps_by_option: Dict[str, float] = {}
    low1_by_option: Dict[str, float] = {}
    option_evidence: Dict[str, Dict[str, Any]] = {}
    game = normalized_game_key(game)
    genre_class, _ = game_profile(game)
    low1_ratio = low1_ratio_for_genres(genres or [genre_class])
    profile = GAME_FPS_PROFILES.get(game, GAME_FPS_PROFILES["default"])
    cap = game_frame_cap(game)

    for opt in ["low", "medium", "high", "ultra"]:
        measured = estimate_from_measurements(gpu, cpu, ram, game, resolution, opt, profile, CATALOGS)
        if measured:
            avg, low, evidence = measured
        else:
            avg, low = estimate_fps_from_catalog(gpu, cpu, ram, game, resolution, opt)
            cpu_norm = clamp(safe_float(cpu.get("perf"), 0.0) / 100.0, .16, 1.08)
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
        cpu_percent = round(clamp(safe_float(bottleneck.get("cpu_penalty_pct"), 0), 0, 100), 1)
        gpu_percent = round(clamp(safe_float(bottleneck.get("gpu_penalty_pct"), 0), 0, 100), 1)
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
    metrics = value_metrics(high_avg, safe_float(gpu.get("price"), 0.0), target_fps, high_low, target_low1)
    fps_source = evidence["method"]
    return {
        "game": game, "fps_by_option": fps_by_option, "low1_by_option": low1_by_option,
        "avg_fps": high_avg, "low1_fps": high_low,
        "high_setting_avg_fps": high_avg, "high_setting_low1_fps": high_low,
        "hz_coverage": round(clamp(high_avg / max(1, refresh), 0.0, 1.6), 3),
        "value_label": value_label(metrics["score"]), "value_score": metrics["score"],
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


def attach_graphics_modes(fps, gpu, cpu, game, resolution):
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

