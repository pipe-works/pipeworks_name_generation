"""Unit tests for webapp metadata repository helpers."""

from __future__ import annotations

import re
from pathlib import Path

from pipeworks_name_generation.webapp.db import (
    build_package_table_name,
    connect_database,
    get_package_table,
    initialize_schema,
    list_package_tables,
    list_packages,
    slugify_identifier,
)


def test_slugify_identifier_normalizes_input() -> None:
    """Slugify should normalize punctuation, empties, and leading digits."""
    assert slugify_identifier("Goblin Flower Latin", max_length=24) == "goblin_flower_latin"
    assert slugify_identifier("%%%###", max_length=24) == "item"
    assert slugify_identifier("123_name", max_length=24).startswith("n_")


def test_slugify_identifier_respects_max_length() -> None:
    """Slugify should cap identifier length and avoid trailing underscores."""
    slug = slugify_identifier("a" * 80, max_length=24)
    assert len(slug) <= 24
    assert not slug.endswith("_")


def test_build_package_table_name_shape() -> None:
    """Table names should include package id, slugs, and index."""
    table_name = build_package_table_name("Goblin Flower Latin", "nltk_first_name_2syl", 2, 1)
    assert table_name.startswith("pkg_2_")
    assert table_name.endswith("_1")
    assert re.fullmatch(r"pkg_\d+_[a-z0-9_]+_[a-z0-9_]+_\d+", table_name)


def test_list_packages_and_tables(tmp_path: Path) -> None:
    """Repository helpers should return metadata rows in expected order."""
    db_path = tmp_path / "repo.sqlite3"
    with connect_database(db_path) as conn:
        initialize_schema(conn)
        conn.execute(
            """
            INSERT INTO imported_packages (package_name, imported_at, metadata_json_path, package_zip_path)
            VALUES (?, ?, ?, ?)
            """,
            ("Package A", "2026-02-01", "a.json", "a.zip"),
        )
        conn.execute(
            """
            INSERT INTO imported_packages (package_name, imported_at, metadata_json_path, package_zip_path)
            VALUES (?, ?, ?, ?)
            """,
            ("Package B", "2026-02-02", "b.json", "b.zip"),
        )
        conn.execute(
            """
            INSERT INTO package_tables (package_id, source_txt_name, table_name, row_count)
            VALUES (?, ?, ?, ?)
            """,
            (1, "first_name_2syl.txt", "pkg_1_first_name_2syl_1", 12),
        )
        conn.execute(
            """
            INSERT INTO package_tables (package_id, source_txt_name, table_name, row_count)
            VALUES (?, ?, ?, ?)
            """,
            (1, "last_name_2syl.txt", "pkg_1_last_name_2syl_2", 8),
        )
        conn.execute(
            """
            INSERT INTO package_tables (package_id, source_txt_name, table_name, row_count)
            VALUES (?, ?, ?, ?)
            """,
            (2, "first_name_all.txt", "pkg_2_first_name_all_1", 20),
        )
        conn.commit()

        packages = list_packages(conn)
        assert [pkg["package_name"] for pkg in packages] == ["Package B", "Package A"]

        tables = list_package_tables(conn, 1)
        assert {table["source_txt_name"] for table in tables} == {
            "first_name_2syl.txt",
            "last_name_2syl.txt",
        }

        table_row = get_package_table(conn, tables[0]["id"])
        assert table_row is not None
        assert table_row["package_id"] == 1
        assert table_row["row_count"] in {8, 12}

        missing = get_package_table(conn, 9999)
        assert missing is None
