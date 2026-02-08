"""Unit tests for webapp database-layer modules."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from pipeworks_name_generation.webapp.db import connect_database, initialize_schema


def test_connect_database_creates_parent_and_applies_pragmas(tmp_path: Path) -> None:
    """Database connections should create parent dirs and enforce PRAGMA policy."""
    db_path = tmp_path / "nested" / "name_packages.sqlite3"

    with connect_database(db_path) as conn:
        assert db_path.parent.exists()
        assert conn.row_factory is sqlite3.Row

        foreign_keys = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert int(foreign_keys) == 1

        journal_mode = str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        assert journal_mode == "wal"

        synchronous = conn.execute("PRAGMA synchronous").fetchone()[0]
        assert int(synchronous) == 1  # NORMAL

        busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        assert int(busy_timeout) == 5000


def test_initialize_schema_creates_expected_indexes(tmp_path: Path) -> None:
    """Schema initialization should create required metadata indexes."""
    db_path = tmp_path / "schema.sqlite3"

    with connect_database(db_path) as conn:
        initialize_schema(conn)

        indexes = {str(row["name"]) for row in conn.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'index'
                ORDER BY name
                """).fetchall()}

    assert "idx_package_tables_package_id" in indexes
    assert "idx_package_tables_package_id_source_txt" in indexes
    assert "idx_imported_packages_imported_at" in indexes
