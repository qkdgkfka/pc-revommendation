"""Pure request normalization and MIME helpers."""
from __future__ import annotations

from pathlib import Path
import json
from product_metadata import normalize_text, safe_int
from typing import Any, Dict, List
from . import runtime as state


def resolution_key(value: Any) -> str:
    s = normalize_text(value)
    if s in {"2160", "4k", "uhd", "3840x2160", "ultra hd"}:
        return "2160"
    if s in {"1440", "qhd", "wqhd", "2560x1440"}:
        return "1440"
    return "1080"

def refresh_value(value: Any) -> int:
    return max(30, safe_int(value, 60))

def vendor_normalize(value: Any) -> str:
    s = normalize_text(value)
    if not s or s in {"any", "nopref", "none", "무관"}:
        return "ANY"
    if "nvidia" in s or "geforce" in s:
        return "NVIDIA"
    if "amd" in s or "radeon" in s:
        return "AMD"
    return "ANY"

def genres_normalize(genres: Any) -> List[str]:
    if isinstance(genres, str):
        items = [x.strip().lower() for x in genres.replace(",", " ").split() if x.strip()]
        return items or ["default"]
    if isinstance(genres, list):
        out = [str(x).strip().lower() for x in genres if str(x).strip()]
        return out or ["default"]
    return ["default"]

def stable_seed(payload: Dict[str, Any]) -> int:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return abs(hash(blob)) % (2**32)

def guess_mime(path: Path) -> str:
    return {
        ".html": "text/html; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".woff2": "font/woff2",
        ".txt": "text/plain; charset=utf-8",
    }.get(path.suffix.lower(), "application/octet-stream")
