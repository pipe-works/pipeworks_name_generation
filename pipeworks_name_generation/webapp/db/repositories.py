"""Repository helpers for webapp metadata tables.

This module owns CRUD-style access for ``imported_packages`` and
``package_tables`` rows plus naming helpers used while importing txt files.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any


def slugify_identifier(value: str, max_length: int) -> str:
    """Convert free text into an ASCII-safe SQL identifier chunk."""
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    slug = slug[:max_length].strip("_")
    if not slug:
        slug = "item"
    if slug[0].isdigit():
        slug = f"n_{slug}"
    return slug


def build_package_table_name(package_name: str, txt_stem: str, package_id: int, index: int) -> str:
    """Create a safe SQLite table name that references package and txt source."""
    package_slug = slugify_identifier(package_name, max_length=24)
    txt_slug = slugify_identifier(txt_stem, max_length=24)
    return f"pkg_{package_id}_{package_slug}_{txt_slug}_{index}"


def list_packages(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return imported package list for the Database View tab."""
    rows = conn.execute("""
        SELECT id, package_name, imported_at
        FROM imported_packages
        ORDER BY id DESC
        """).fetchall()
    return [
        {
            "id": int(row["id"]),
            "package_name": str(row["package_name"]),
            "imported_at": str(row["imported_at"]),
        }
        for row in rows
    ]


def list_package_tables(conn: sqlite3.Connection, package_id: int) -> list[dict[str, Any]]:
    """Return txt tables for one package id."""
    rows = conn.execute(
        """
        SELECT id, source_txt_name, table_name, row_count
        FROM package_tables
        WHERE package_id = ?
        ORDER BY source_txt_name
        """,
        (package_id,),
    ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "source_txt_name": str(row["source_txt_name"]),
            "table_name": str(row["table_name"]),
            "row_count": int(row["row_count"]),
        }
        for row in rows
    ]


def get_package_table(conn: sqlite3.Connection, table_id: int) -> dict[str, Any] | None:
    """Return one package table metadata row by id."""
    row = conn.execute(
        """
        SELECT id, package_id, source_txt_name, table_name, row_count
        FROM package_tables
        WHERE id = ?
        """,
        (table_id,),
    ).fetchone()
    if row is None:
        return None

    return {
        "id": int(row["id"]),
        "package_id": int(row["package_id"]),
        "source_txt_name": str(row["source_txt_name"]),
        "table_name": str(row["table_name"]),
        "row_count": int(row["row_count"]),
    }


__all__ = [
    "slugify_identifier",
    "build_package_table_name",
    "list_packages",
    "list_package_tables",
    "get_package_table",
]
