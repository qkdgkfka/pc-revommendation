#!/usr/bin/env python3
from __future__ import annotations

"""
train_model.py

This script does not train a neural network.
It builds a calibration artifact from:
- recommendation feedback (JSONL)
- the local SQLite database, when available

Outputs:
- artifacts/hybrid_config.json
- artifacts/catalog_snapshot.json
- artifacts/benchmark_summary.json
"""

import argparse
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
ARTIFACT_DIR = APP_DIR / "artifacts"
DB_PATH = DATA_DIR / "pc.db"
FEEDBACK_PATH = APP_DIR / "recommendation_feedback.jsonl"

DEFAULT_PROFILE_MULTIPLIERS = {
    "gpu": 1.00,
    "cpu": 1.00,
    "ram": 1.00,
    "mb": 1.00,
    "psu": 1.00,
    "storage": 1.00,
}

DEFAULT_CATALOGS = {
    "cpu_catalog": [],
    "gpu_catalog": [],
    "ram_catalog": [],
    "mb_catalog": [],
    "psu_catalog": [],
    "storage_catalog": [],
}

def normalize_text(v: Any) -> str:
    return " ".join(str(v or "").strip().lower().split())

def resolution_key(value: Any) -> str:
    s = normalize_text(value)
    if s in {"2160", "4k", "uhd", "3840x2160", "ultra hd"}:
        return "2160"
    if s in {"1440", "qhd", "wqhd", "2560x1440"}:
        return "1440"
    return "1080"

def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        x = float(v)
        if math.isnan(x) or math.isinf(x):
            return default
        return x
    except Exception:
        return default

def load_feedback(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows

def compute_profile_multipliers(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    if not rows:
        return dict(DEFAULT_PROFILE_MULTIPLIERS)

    rewards = defaultdict(float)
    counts = defaultdict(int)

    for row in rows:
        inp = row.get("input", {}) or {}
        reward = safe_float(row.get("reward", 1.0), 1.0)
        if reward <= 0:
            continue

        genres = inp.get("genres", [])
        if isinstance(genres, str):
            genres = [genres]
        genres = [normalize_text(g) for g in genres if normalize_text(g)]
        resolution = resolution_key(inp.get("resolution", "1080"))
        refresh = int(safe_float(inp.get("refresh", 60), 60))

        counts["rows"] += 1
        if resolution == "2160":
            rewards["gpu"] += 0.14
        elif resolution == "1440":
            rewards["gpu"] += 0.08
        else:
            rewards["cpu"] += 0.03

        if refresh >= 144:
            rewards["cpu"] += 0.05
            rewards["gpu"] += 0.04

        if any(g in genres for g in ["fps", "competitive", "valorant", "cs", "cs2"]):
            rewards["cpu"] += 0.06
            rewards["gpu"] += 0.03
        if any(g in genres for g in ["rpg", "aaa", "action"]):
            rewards["gpu"] += 0.05
        if any(g in genres for g in ["mmo", "mmorpg"]):
            rewards["cpu"] += 0.04
            rewards["ram"] += 0.03
        if any(g in genres for g in ["sim", "simulation"]):
            rewards["cpu"] += 0.06
            rewards["ram"] += 0.04
            rewards["storage"] += 0.03
        if any(g in genres for g in ["prod", "productivity", "creator"]):
            rewards["cpu"] += 0.07
            rewards["ram"] += 0.05
            rewards["storage"] += 0.03

    total = max(1, counts["rows"])
    return {
        "gpu": 1.0 + min(0.20, rewards["gpu"] / total),
        "cpu": 1.0 + min(0.15, rewards["cpu"] / total),
        "ram": 1.0 + min(0.12, rewards["ram"] / total),
        "mb": 1.0 + min(0.05, rewards["cpu"] / total * 0.2),
        "psu": 1.0 + min(0.05, rewards["gpu"] / total * 0.2),
        "storage": 1.0 + min(0.08, rewards["storage"] / total),
    }

def load_db_summary(db_path: Path) -> Dict[str, Any]:
    if not db_path.exists():
        return {"loaded": False, "components": 0, "prices": 0, "benchmarks": 0, "by_type": {}}

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    summary = {"loaded": True, "components": 0, "prices": 0, "benchmarks": 0, "by_type": {}}
    try:
        rows = cur.execute("SELECT type, COUNT(*) AS cnt FROM components GROUP BY type").fetchall()
        summary["by_type"] = {r["type"]: int(r["cnt"]) for r in rows}
        summary["components"] = sum(summary["by_type"].values())
    except Exception:
        pass

    try:
        summary["prices"] = int(cur.execute("SELECT COUNT(*) FROM prices").fetchone()[0])
    except Exception:
        pass

    try:
        summary["benchmarks"] = int(cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0])
    except Exception:
        pass

    conn.close()
    return summary

def load_benchmark_summary(db_path: Path) -> Dict[str, Any]:
    if not db_path.exists():
        return {"loaded": False, "by_game": {}, "by_resolution": {}, "by_component_type": {}}

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    summary = {
        "loaded": True,
        "by_game": {},
        "by_resolution": {},
        "by_component_type": {},
        "samples": [],
    }

    try:
        rows = cur.execute("""
            SELECT c.type, c.name, b.game, b.resolution, b.setting, b.avg_fps, b.low1_fps, b.source_url
            FROM benchmarks b
            JOIN components c ON c.id = b.component_id
        """).fetchall()
        by_game = defaultdict(list)
        by_res = defaultdict(list)
        by_type = defaultdict(list)

        for r in rows:
            item = {
                "type": r["type"],
                "name": r["name"],
                "game": r["game"],
                "resolution": resolution_key(r["resolution"]),
                "setting": normalize_text(r["setting"]),
                "avg_fps": safe_float(r["avg_fps"]),
                "low1_fps": safe_float(r["low1_fps"]),
                "source_url": r["source_url"],
            }
            summary["samples"].append(item)
            by_game[normalize_text(r["game"])].append(item)
            by_res[resolution_key(r["resolution"])].append(item)
            by_type[normalize_text(r["type"])].append(item)

        def aggregate(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
            if not rows:
                return {}
            avg_values = [x["avg_fps"] for x in rows if x["avg_fps"] > 0]
            low_values = [x["low1_fps"] for x in rows if x["low1_fps"] > 0]
            return {
                "count": len(rows),
                "avg_fps": round(mean(avg_values), 2) if avg_values else None,
                "low1_fps": round(mean(low_values), 2) if low_values else None,
            }

        summary["by_game"] = {k: aggregate(v) for k, v in by_game.items()}
        summary["by_resolution"] = {k: aggregate(v) for k, v in by_res.items()}
        summary["by_component_type"] = {k: aggregate(v) for k, v in by_type.items()}
    except Exception:
        pass
    finally:
        conn.close()

    return summary

def build_catalog_snapshot() -> Dict[str, Any]:
    return DEFAULT_CATALOGS

def build_config(feedback_rows: List[Dict[str, Any]], db_summary: Dict[str, Any], benchmark_summary: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "profile_multipliers": compute_profile_multipliers(feedback_rows),
        "db_summary": db_summary,
        "benchmark_summary": benchmark_summary,
        "meta": {
            "feedback_rows": len(feedback_rows),
            "has_db": bool(db_summary.get("loaded")),
            "benchmark_samples": len(benchmark_summary.get("samples", [])),
        },
    }

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--feedback", type=str, default=str(FEEDBACK_PATH))
    p.add_argument("--db", type=str, default=str(DB_PATH))
    p.add_argument("--out-dir", type=str, default=str(ARTIFACT_DIR))
    return p.parse_args()

def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    feedback_rows = load_feedback(Path(args.feedback))
    db_summary = load_db_summary(Path(args.db))
    benchmark_summary = load_benchmark_summary(Path(args.db))
    config = build_config(feedback_rows, db_summary, benchmark_summary)

    (out_dir / "hybrid_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "catalog_snapshot.json").write_text(
        json.dumps(build_catalog_snapshot(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "benchmark_summary.json").write_text(
        json.dumps(benchmark_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved: {out_dir / 'hybrid_config.json'}")
    print(f"Saved: {out_dir / 'catalog_snapshot.json'}")
    print(f"Saved: {out_dir / 'benchmark_summary.json'}")
    print("Calibration complete.")

if __name__ == "__main__":
    main()
