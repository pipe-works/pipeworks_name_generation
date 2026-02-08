"""Unit tests for dynamic text table helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeworks_name_generation.webapp.db import (
    connect_database,
    create_text_table,
    fetch_text_rows,
    insert_text_rows,
    quote_identifier,
)


def test_quote_identifier_validates() -> None:
    """Identifier quoting should accept safe names and reject unsafe ones."""
    assert quote_identifier("table_1") == '"table_1"'
    with pytest.raises(ValueError, match="Unsafe SQL identifier"):
        quote_identifier("bad-name")


def test_create_insert_fetch_rows(tmp_path: Path) -> None:
    """Inserted rows should be returned in stable line_number order."""
    db_path = tmp_path / "tables.sqlite3"
    with connect_database(db_path) as conn:
        create_text_table(conn, "test_table")
        insert_text_rows(
            conn,
            "test_table",
            [
                (2, "beta"),
                (1, "alpha"),
                (3, "gamma"),
            ],
        )
        conn.commit()

        rows = fetch_text_rows(conn, "test_table", offset=0, limit=2)
        assert rows == [
            {"line_number": 1, "value": "alpha"},
            {"line_number": 2, "value": "beta"},
        ]

        rows_tail = fetch_text_rows(conn, "test_table", offset=2, limit=2)
        assert rows_tail == [{"line_number": 3, "value": "gamma"}]


def test_insert_text_rows_noop(tmp_path: Path) -> None:
    """Empty inserts should not fail or add rows."""
    db_path = tmp_path / "empty.sqlite3"
    with connect_database(db_path) as conn:
        create_text_table(conn, "empty_table")
        insert_text_rows(conn, "empty_table", [])
        conn.commit()

        rows = fetch_text_rows(conn, "empty_table", offset=0, limit=10)
        assert rows == []
