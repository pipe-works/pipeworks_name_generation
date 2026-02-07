"""SQLite persistence for imported name package pairs.

This module stores imported package metadata and ZIP inventory so the web UI
can show what has been imported and from where.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


def connect_database(db_path: Path) -> sqlite3.Connection:
    """Create a SQLite connection configured for this app.

    Args:
        db_path: Database file path

    Returns:
        Configured sqlite3 connection
    """
    # Ensure parent directory exists so first run can create the DB file.
    if db_path.parent and str(db_path.parent) != ".":
        db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Create required tables if they do not already exist.

    Args:
        conn: Active sqlite connection
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS imported_packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imported_at TEXT NOT NULL,
            common_name TEXT NOT NULL,
            version TEXT,
            author TEXT,
            created_at TEXT,
            source_run TEXT,
            source_dir TEXT,
            metadata_json_path TEXT NOT NULL,
            package_zip_path TEXT NOT NULL,
            intended_use_json TEXT NOT NULL,
            examples_json TEXT NOT NULL,
            include_json TEXT NOT NULL,
            files_included_json TEXT NOT NULL,
            UNIQUE(metadata_json_path, package_zip_path)
        );

        CREATE TABLE IF NOT EXISTS package_zip_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id INTEGER NOT NULL,
            entry_name TEXT NOT NULL,
            FOREIGN KEY(package_id) REFERENCES imported_packages(id) ON DELETE CASCADE
        );
        """)
    conn.commit()


def insert_imported_package(
    conn: sqlite3.Connection,
    *,
    imported_at: str,
    metadata_payload: dict[str, Any],
    metadata_json_path: Path,
    package_zip_path: Path,
    zip_entries: list[str],
) -> int:
    """Insert a new imported package and its ZIP entries.

    Args:
        conn: Active sqlite connection
        imported_at: UTC timestamp for this import
        metadata_payload: Parsed metadata JSON object
        metadata_json_path: Source metadata file path
        package_zip_path: Source package ZIP file path
        zip_entries: Archive file list

    Returns:
        Inserted package row id

    Raises:
        sqlite3.IntegrityError: If the metadata/zip pair already exists
    """
    cursor = conn.execute(
        """
        INSERT INTO imported_packages (
            imported_at,
            common_name,
            version,
            author,
            created_at,
            source_run,
            source_dir,
            metadata_json_path,
            package_zip_path,
            intended_use_json,
            examples_json,
            include_json,
            files_included_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            imported_at,
            str(metadata_payload.get("common_name", "")),
            str(metadata_payload.get("version", "")),
            str(metadata_payload.get("author", "")),
            str(metadata_payload.get("created_at", "")),
            str(metadata_payload.get("source_run", "")),
            str(metadata_payload.get("source_dir", "")),
            str(metadata_json_path),
            str(package_zip_path),
            json.dumps(metadata_payload.get("intended_use", [])),
            json.dumps(metadata_payload.get("examples", {})),
            json.dumps(metadata_payload.get("include", {})),
            json.dumps(metadata_payload.get("files_included", [])),
        ),
    )
    if cursor.lastrowid is None:
        raise RuntimeError("SQLite did not return a row id for imported package insert.")
    package_id = int(cursor.lastrowid)

    conn.executemany(
        "INSERT INTO package_zip_entries (package_id, entry_name) VALUES (?, ?)",
        [(package_id, entry_name) for entry_name in zip_entries],
    )
    conn.commit()

    return package_id


def list_imported_packages(conn: sqlite3.Connection, limit: int = 100) -> list[dict[str, Any]]:
    """List imported package records for UI/API display.

    Args:
        conn: Active sqlite connection
        limit: Maximum number of rows

    Returns:
        List of package dictionaries sorted by newest first
    """
    rows = conn.execute(
        """
        SELECT
            id,
            imported_at,
            common_name,
            version,
            author,
            created_at,
            source_run,
            source_dir,
            metadata_json_path,
            package_zip_path,
            intended_use_json,
            examples_json,
            include_json,
            files_included_json
        FROM imported_packages
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    results: list[dict[str, Any]] = []
    for row in rows:
        # JSON columns are stored as text for portability; decode for API output.
        results.append(
            {
                "id": row["id"],
                "imported_at": row["imported_at"],
                "common_name": row["common_name"],
                "version": row["version"],
                "author": row["author"],
                "created_at": row["created_at"],
                "source_run": row["source_run"],
                "source_dir": row["source_dir"],
                "metadata_json_path": row["metadata_json_path"],
                "package_zip_path": row["package_zip_path"],
                "intended_use": json.loads(row["intended_use_json"]),
                "examples": json.loads(row["examples_json"]),
                "include": json.loads(row["include_json"]),
                "files_included": json.loads(row["files_included_json"]),
                "zip_entry_count": _count_zip_entries(conn, int(row["id"])),
            }
        )

    return results


def _count_zip_entries(conn: sqlite3.Connection, package_id: int) -> int:
    """Count ZIP entries for a stored package id."""
    row = conn.execute(
        "SELECT COUNT(*) AS count FROM package_zip_entries WHERE package_id = ?",
        (package_id,),
    ).fetchone()
    return int(row["count"] if row is not None else 0)
