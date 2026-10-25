"""Minimal SQLite database bootstrap with a versioned schema.

Uses only the Python standard library. Calling connect() never starts a network server.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_VERSION = 1


def connect(path: str | Path = "local/sync-devices.db") -> sqlite3.Connection:
    """Open a SQLite database, enable integrity checks, and initialize schema v1.

    New databases are created automatically. Schema upgrades are deliberately not
    guessed: they must be implemented with explicit, versioned migrations.
    """
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=5)
    try:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=5000")
        if str(path) != ":memory:":
            db.execute("PRAGMA journal_mode=WAL")
        current_version = db.execute("PRAGMA user_version").fetchone()[0]
        if current_version not in (0, SCHEMA_VERSION):
            raise RuntimeError(
                f"Unsupported schema version {current_version}; "
                "an explicit migration is required"
            )
        if current_version == 0:
            script = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
            db.executescript(script)
            db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        return db
    except Exception:
        db.close()
        raise
