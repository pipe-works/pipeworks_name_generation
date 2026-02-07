"""Tests for SQLite persistence and package-pair import logic."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from pipeworks_name_generation.webapp.db import (
    connect_database,
    initialize_schema,
    list_imported_packages,
)
from pipeworks_name_generation.webapp.importer import import_package_pair


def _write_sample_metadata(metadata_path: Path) -> None:
    """Write metadata payload matching packager schema."""
    payload = {
        "schema_version": 1,
        "created_at": "2026-02-07 14:55:09",
        "author": "tester",
        "version": "1.0.0",
        "common_name": "goblin_flower-latin",
        "intended_use": ["first_name", "last_name"],
        "source_run": "20260130_185023_nltk",
        "source_dir": "/tmp/source",
        "examples": {
            "first_name": ["ofke", "dishrgela"],
            "last_name": ["gaped", "itsdeusgly"],
        },
        "include": {"json": True, "txt": True, "meta": True, "manifest": True},
        "files_included": [
            "first_name_sample.json",
            "last_name_sample.json",
            "nltk_first_name_all.json",
        ],
    }
    metadata_path.write_text(json.dumps(payload), encoding="utf-8")


def _write_sample_zip(zip_path: Path) -> None:
    """Write a small package ZIP with variable entries."""
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("manifest.json", "{}")
        archive.writestr("selections/first_name_sample.json", "{}")
        archive.writestr("selections/nltk_first_name_all.json", "{}")


def test_import_package_pair_and_list(tmp_path: Path) -> None:
    """Import should persist pair and expose it through list query."""
    db_path = tmp_path / "app.sqlite3"
    metadata_path = tmp_path / "custom_metadata_name.json"
    zip_path = tmp_path / "another_package_name.zip"
    _write_sample_metadata(metadata_path)
    _write_sample_zip(zip_path)

    with connect_database(db_path) as conn:
        initialize_schema(conn)
        result = import_package_pair(conn, metadata_path, zip_path)
        rows = list_imported_packages(conn)

    assert result.package_id is not None
    assert rows
    assert rows[0]["common_name"] == "goblin_flower-latin"
    assert rows[0]["metadata_json_path"].endswith("custom_metadata_name.json")
    assert rows[0]["package_zip_path"].endswith("another_package_name.zip")
    assert rows[0]["zip_entry_count"] == 3


def test_import_duplicate_pair_rejected(tmp_path: Path) -> None:
    """Importing the same pair twice should raise a validation error."""
    db_path = tmp_path / "app.sqlite3"
    metadata_path = tmp_path / "meta.json"
    zip_path = tmp_path / "package.zip"
    _write_sample_metadata(metadata_path)
    _write_sample_zip(zip_path)

    with connect_database(db_path) as conn:
        initialize_schema(conn)
        import_package_pair(conn, metadata_path, zip_path)
        with pytest.raises(ValueError, match="already imported"):
            import_package_pair(conn, metadata_path, zip_path)


def test_import_missing_file_errors(tmp_path: Path) -> None:
    """Missing metadata/zip paths should raise FileNotFoundError."""
    db_path = tmp_path / "app.sqlite3"

    with connect_database(db_path) as conn:
        initialize_schema(conn)
        with pytest.raises(FileNotFoundError, match="Metadata JSON"):
            import_package_pair(conn, tmp_path / "missing.json", tmp_path / "package.zip")


def test_import_invalid_metadata_schema_errors(tmp_path: Path) -> None:
    """Invalid metadata payload should be rejected with ValueError."""
    db_path = tmp_path / "app.sqlite3"
    metadata_path = tmp_path / "meta.json"
    zip_path = tmp_path / "package.zip"
    metadata_path.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
    _write_sample_zip(zip_path)

    with connect_database(db_path) as conn:
        initialize_schema(conn)
        with pytest.raises(ValueError, match="missing required keys"):
            import_package_pair(conn, metadata_path, zip_path)


def test_import_bad_zip_errors(tmp_path: Path) -> None:
    """Corrupt ZIP payload should raise zipfile.BadZipFile."""
    db_path = tmp_path / "app.sqlite3"
    metadata_path = tmp_path / "meta.json"
    zip_path = tmp_path / "package.zip"
    _write_sample_metadata(metadata_path)
    zip_path.write_text("not a zip", encoding="utf-8")

    with connect_database(db_path) as conn:
        initialize_schema(conn)
        with pytest.raises(zipfile.BadZipFile):
            import_package_pair(conn, metadata_path, zip_path)
