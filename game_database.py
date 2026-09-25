"""Reviewed observations and calculated scenarios are stored separately."""
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "data/pc.db"
KINDS = ("measurements", "graphics_measurements", "pending_measurements")

def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()

def schema(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS game_snapshot (id INTEGER PRIMARY KEY CHECK(id=1), metadata TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS game_observations (
      kind TEXT NOT NULL, record_key TEXT NOT NULL, game TEXT, gpu_id TEXT, cpu_id TEXT,
      resolution TEXT, preset TEXT, mode TEXT, avg_fps REAL, source_url TEXT,
      payload TEXT NOT NULL, PRIMARY KEY(kind,record_key));
    CREATE INDEX IF NOT EXISTS game_observations_lookup ON game_observations(game,kind,resolution);
    CREATE TABLE IF NOT EXISTS game_predictions (
      cache_key TEXT PRIMARY KEY, model_revision TEXT NOT NULL, conditions TEXT NOT NULL,
      scenarios TEXT NOT NULL, calculated_at TEXT NOT NULL);
    """)

def save_snapshot(snapshot, path=None):
    with closing(sqlite3.connect(path or DB_PATH, timeout=10)) as db:
        schema(db)
        with db:
            db.execute("DELETE FROM game_observations")
            for kind in KINDS:
                for row in snapshot.get(kind, []):
                    db.execute("INSERT OR REPLACE INTO game_observations VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (kind,digest(row),row.get("game"),row.get("gpu_id"),row.get("cpu_id"),
                         row.get("resolution"),row.get("preset"),row.get("mode","native"),
                         row.get("avg_fps"),row.get("source_url"),encoded(row)))
            meta={k:v for k,v in snapshot.items() if k not in KINDS}
            meta["_present_kinds"]=[k for k in KINDS if k in snapshot]
            db.execute("INSERT OR REPLACE INTO game_snapshot VALUES (1,?)",(encoded(meta),))

def load_snapshot(path=None):
    target=Path(path or DB_PATH)
    if not target.exists(): return None
    try:
        with closing(sqlite3.connect(target.as_uri()+"?mode=ro",uri=True,timeout=1)) as db:
            item=db.execute("SELECT metadata FROM game_snapshot WHERE id=1").fetchone()
            if not item:return None
            data=json.loads(item[0])
            for kind in data.pop("_present_kinds"):
                data[kind]=[json.loads(row[0]) for row in db.execute(
                    "SELECT payload FROM game_observations WHERE kind=? ORDER BY rowid",(kind,))]
            return data
    except (sqlite3.Error,ValueError,KeyError):return None

def save_prediction(conditions, scenarios, revision, path=None):
    key=digest([revision,conditions])
    with closing(sqlite3.connect(path or DB_PATH,timeout=2)) as db:
        schema(db)
        with db:
            db.execute("INSERT OR REPLACE INTO game_predictions VALUES (?,?,?,?,?)",
                       (key,revision,encoded(conditions),encoded(scenarios),datetime.now(timezone.utc).isoformat()))

def read_prediction(conditions, revision, path=None):
    target=Path(path or DB_PATH)
    if not target.exists():return None
    try:
        with closing(sqlite3.connect(target.as_uri()+"?mode=ro",uri=True,timeout=1)) as db:
            row=db.execute("SELECT scenarios FROM game_predictions WHERE cache_key=?",
                           (digest([revision,conditions]),)).fetchone()
            return json.loads(row[0]) if row else None
    except (sqlite3.Error,ValueError):return None
