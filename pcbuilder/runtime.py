"""Shared configuration and mutable service caches."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
from market_search import ProductPager
from threading import RLock
from typing import Any, Dict, Optional, Tuple
from server_catalogs import GAME_OPTIONS, GAME_FPS_PROFILES


APP_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = APP_DIR / "data"

ARTIFACT_DIR = APP_DIR / "artifacts"

DB_PATH = DATA_DIR / "pc.db"

CONFIG_PATH = ARTIFACT_DIR / "hybrid_config.json"

STATIC_DIR = APP_DIR / 'dist'

MODEL_LOADED = True

HYBRID_CONFIG: Dict[str, Any] = {}

DANAWA_PRICE_MAX_AGE_HOURS = 24

DANAWA_BROWSE_CACHE_TTL_SECONDS = 300

DANAWA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.6",
}

IMAGE_URL_CACHE: Dict[Tuple[str, str], str] = {}

PREVIEW_CACHE: Dict[str, Dict[str, str]] = {}

GPU_MARKET_PRICE_CACHE: Dict[str, Optional[Dict[str, Any]]] = {}


GPU_DANAWA_CATEGORY_IDS = {"112753"}

STORAGE_DANAWA_CATEGORY_IDS = {"112760"}

MB_DANAWA_CATEGORY_IDS = {"112751"}

DANAWA_BROWSE_CATEGORY_IDS = {
    "cpu": {"113990", "113973"},
    "gpu": GPU_DANAWA_CATEGORY_IDS,
    "ram": {"112752"},
    "mb": MB_DANAWA_CATEGORY_IDS,
    "storage": STORAGE_DANAWA_CATEGORY_IDS,
    "hdd": {"1131401"},
    "psu": {"112777"},
    "case": {"112775"},
}

COMPUZONE_CATEGORY_IDS = {
    "cpu": "1012", "mb": "1013", "ram": "1014", "storage": "1276",
    "hdd": "1015", "gpu": "1016", "case": "1147", "psu": "1148",
    "software": "1011",
}

MARKET_BROWSE_CACHE: Dict[Tuple[Any, ...], Dict[str, Any]] = {}

MARKET_SEARCH_CACHE: Dict[Tuple[Any, ...], ProductPager] = {}

MARKET_SEARCH_LOCK = RLock()

GAME_GENRE_FACTORS = {
    item["id"]: (item["genre"], {
        "fps": 1.55,
        "rpg": 0.76,
        "openworld": 0.70,
        "aaa": 0.66,
        "subculture": 1.05,
        "mmo": 1.15,
        "sim": 0.58,
    }.get(item["genre"], 1.0))
    for item in GAME_OPTIONS
}

GAME_GENRE_FACTORS.update({
    "valorant": ("fps", 2.20),
    "cs2": ("fps", 2.00),
    "csgo2": ("fps", 2.00),
    "csgo": ("fps", 2.50),
    "rainbow6": ("fps", 1.85),
    "cyberpunk2077": ("rpg", 0.48),
    "witcher3": ("rpg", 0.82),
    "elden_ring": ("rpg", 0.76),
    "baldurs_gate3": ("rpg", 0.70),
    "msfs2024": ("sim", 0.34),
})

DB_CACHE: Dict[str, Any] = {
    "loaded": False,
    "components": [],
    "prices_by_name": {},
    "prices_by_url": {},
    "benchmarks_by_name": {},
    "summary": {},
}

BENCHMARK_LOOKUP_CACHE: Dict[Tuple[Any, ...], Tuple[Dict[str, Any], ...]] = {}

GPU_MARKET_PRICE_CHECKED_AT: Dict[str, datetime] = {}

RECOMMENDATION_CACHE: Dict[Tuple[Any, ...], Tuple[float, Dict[str, Any], float]] = {}

DISPLAY_PRICE_TYPES = {"cpu", "gpu", "ram", "mb", "storage", "psu", "hdd", "case", "software"}

for _game, _weight, _low1 in [
    ("fortnite", .48, .76), ("marvel_rivals", .40, .74),
    ("cod_black_ops6", .32, .76), ("dragons_dogma2", .55, .68),
    ("dying_light2", .22, .76), ("resident_evil4", .20, .78), ("alan_wake2", .16, .72),
]:
    GAME_FPS_PROFILES[_game] = {**GAME_FPS_PROFILES["default"], "cpu_weight": _weight, "low1": _low1, "ram_hungry": True}

GAME_FRAME_CAPS = {"elden_ring": 60.0, "genshin_impact": 60.0}

TIER_RANK = {"low": 0, "mid": 1, "high": 2}

