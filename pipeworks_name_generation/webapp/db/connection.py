"""SQLite connection helpers for the webapp persistence layer.

This module owns connection-level concerns only: opening the SQLite database,
creating parent directories, and applying connection PRAGMA defaults.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def connect_database(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection configured for webapp usage.

    Args:
        db_path: Filesystem path to the SQLite database file.

    Returns:
        Open ``sqlite3.Connection`` with ``sqlite3.Row`` row factory.
    """
    resolved = db_path.expanduser()
    if resolved.parent and str(resolved.parent) != ".":
        resolved.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


__all__ = ["connect_database"]
