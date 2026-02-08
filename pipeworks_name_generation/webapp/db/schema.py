"""Database schema bootstrap helpers for webapp storage."""

from __future__ import annotations

import sqlite3


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Create metadata tables used by import and database browsing.

    Args:
        conn: Open SQLite connection.
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS imported_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_name TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            metadata_json_path TEXT NOT NULL,
            package_zip_path TEXT NOT NULL,
            UNIQUE(metadata_json_path, package_zip_path)
        );

        CREATE TABLE IF NOT EXISTS package_tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id INTEGER NOT NULL,
            source_txt_name TEXT NOT NULL,
            table_name TEXT NOT NULL,
            row_count INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(package_id) REFERENCES imported_packages(id) ON DELETE CASCADE,
            UNIQUE(package_id, source_txt_name)
        );
        """)
    conn.commit()


__all__ = ["initialize_schema"]
