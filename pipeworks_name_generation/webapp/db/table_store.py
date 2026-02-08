"""Low-level helpers for dynamic imported text tables.

Each imported ``*.txt`` file gets mapped to one physical SQLite table.
This module owns identifier safety and row-level table operations.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any


def quote_identifier(identifier: str) -> str:
    """Validate and quote a SQLite identifier.

    Args:
        identifier: Unquoted table or column identifier.

    Returns:
        Quoted identifier safe for SQL string interpolation.

    Raises:
        ValueError: If identifier contains unsafe characters.
    """
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise ValueError(f"Unsafe SQL identifier: {identifier!r}")
    return f'"{identifier}"'


def create_text_table(conn: sqlite3.Connection, table_name: str) -> None:
    """Create one physical text table for imported txt rows.

    The table schema is intentionally minimal:

    - ``id``: surrogate primary key
    - ``line_number``: source txt line number
    - ``value``: trimmed non-empty line value
    """
    quoted = quote_identifier(table_name)
    query = f"""
        CREATE TABLE IF NOT EXISTS {quoted} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_number INTEGER NOT NULL,
            value TEXT NOT NULL
        )
        """
    conn.execute(query)


def insert_text_rows(
    conn: sqlite3.Connection, table_name: str, rows: list[tuple[int, str]]
) -> None:
    """Insert parsed txt rows into a physical text table."""
    if not rows:
        return

    quoted = quote_identifier(table_name)
    query = f"""
        INSERT INTO {quoted} (line_number, value)
        VALUES (?, ?)
        """  # nosec B608
    conn.executemany(query, rows)


def fetch_text_rows(
    conn: sqlite3.Connection,
    table_name: str,
    *,
    offset: int,
    limit: int,
) -> list[dict[str, Any]]:
    """Fetch paginated rows from one physical txt table.

    Args:
        conn: Open SQLite connection.
        table_name: Validated physical table name.
        offset: Zero-based row offset.
        limit: Maximum rows to return.

    Returns:
        List of ``{"line_number": int, "value": str}`` mappings.
    """
    quoted = quote_identifier(table_name)
    query = f"""
        SELECT line_number, value
        FROM {quoted}
        ORDER BY line_number, id
        LIMIT ? OFFSET ?
        """  # nosec B608
    rows = conn.execute(query, (limit, offset)).fetchall()
    return [
        {
            "line_number": int(row["line_number"]),
            "value": str(row["value"]),
        }
        for row in rows
    ]


__all__ = [
    "quote_identifier",
    "create_text_table",
    "insert_text_rows",
    "fetch_text_rows",
]
