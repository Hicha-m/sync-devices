"""SQLite bootstrap and explicit schema upgrade path (stdlib only)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 2


def connect(path: str | Path = "local/sync-devices.db") -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=5)
    try:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=5000")
        if str(path) != ":memory:":
            db.execute("PRAGMA journal_mode=WAL")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1, SCHEMA_VERSION):
            raise RuntimeError(f"Unsupported schema version {version}; explicit migration required")
        if version == 0:
            db.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
            db.execute("PRAGMA user_version=1")
        if version in (0, 1):
            db.executescript(Path(__file__).with_name("migrate_v2.sql").read_text(encoding="utf-8"))
            db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        return db
    except Exception:
        db.close()
        raise
