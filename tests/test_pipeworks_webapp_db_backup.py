"""Tests for database backup/export/import helpers and routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pipeworks_name_generation.webapp.db import (
    backup_database,
    connect_database,
    export_database,
    initialize_schema,
    restore_database,
)
from pipeworks_name_generation.webapp.db.repositories import list_packages
from pipeworks_name_generation.webapp.db.table_store import create_text_table, insert_text_rows
from pipeworks_name_generation.webapp.routes import database_admin as database_admin_routes


def _seed_database(db_path: Path, package_name: str) -> None:
    """Create a minimal package + table set for tests."""
    with connect_database(db_path) as conn:
        initialize_schema(conn)
        inserted = conn.execute(
            """
            INSERT INTO imported_packages (
                package_name,
                imported_at,
                metadata_json_path,
                package_zip_path
            ) VALUES (?, ?, ?, ?)
            """,
            (package_name, "2026-02-09T00:00:00+00:00", "meta.json", "pack.zip"),
        )
        package_id = inserted.lastrowid
        assert package_id is not None
        conn.execute(
            """
            INSERT INTO package_tables (package_id, source_txt_name, table_name, row_count)
            VALUES (?, ?, ?, ?)
            """,
            (int(package_id), "example.txt", "example_table", 2),
        )
        create_text_table(conn, "example_table")
        insert_text_rows(conn, "example_table", [(1, "alfa"), (2, "beta")])
        conn.commit()


class _HandlerHarness:
    """Minimal handler harness for database admin route tests."""

    def __init__(
        self,
        *,
        db_path: Path,
        body: dict[str, Any] | None = None,
        db_export_path: Path | None = None,
        db_backup_path: Path | None = None,
    ) -> None:
        self.db_path = db_path
        self.db_export_path = db_export_path
        self.db_backup_path = db_backup_path
        self._body = body or {}
        self.response_status: int | None = None
        self.response_payload: dict[str, Any] | None = None

    def _read_json_body(self) -> dict[str, Any]:
        return dict(self._body)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        self.response_status = status
        self.response_payload = payload


def test_backup_database_creates_copy(tmp_path: Path) -> None:
    """Backup should produce a readable SQLite copy."""
    src_db = tmp_path / "source.sqlite3"
    _seed_database(src_db, "Source Package")

    backup_path = tmp_path / "backup.sqlite3"
    result = backup_database(src_db, output_path=backup_path)

    assert result.path == backup_path
    assert backup_path.exists()
    assert result.bytes_written > 0

    with connect_database(backup_path) as conn:
        packages = list_packages(conn)
    assert packages[0]["package_name"] == "Source Package"


def test_backup_database_rejects_missing_db(tmp_path: Path) -> None:
    """Backup should reject missing source databases."""
    with pytest.raises(ValueError):
        backup_database(tmp_path / "missing.sqlite3", output_path=tmp_path / "backup.sqlite3")


def test_restore_database_overwrites_and_creates_backup(tmp_path: Path) -> None:
    """Restore should replace the destination and create a backup when requested."""
    dest_db = tmp_path / "dest.sqlite3"
    import_db = tmp_path / "import.sqlite3"
    _seed_database(dest_db, "Original Package")
    _seed_database(import_db, "Imported Package")

    result = restore_database(
        dest_db,
        import_path=import_db,
        overwrite=True,
        create_backup=True,
    )

    assert result.backup_path is not None
    assert result.backup_path.exists()

    with connect_database(dest_db) as conn:
        packages = list_packages(conn)
    assert packages[0]["package_name"] == "Imported Package"


def test_restore_database_requires_overwrite(tmp_path: Path) -> None:
    """Restore should refuse to overwrite without explicit consent."""
    dest_db = tmp_path / "dest.sqlite3"
    import_db = tmp_path / "import.sqlite3"
    _seed_database(dest_db, "Original Package")
    _seed_database(import_db, "Imported Package")

    with pytest.raises(ValueError):
        restore_database(dest_db, import_path=import_db, overwrite=False)


def test_database_export_route_requires_path(tmp_path: Path) -> None:
    """Export route should require an output_path."""
    db_path = tmp_path / "db.sqlite3"
    _seed_database(db_path, "Export Package")

    handler = _HandlerHarness(db_path=db_path, body={})
    database_admin_routes.post_database_export(handler, export_database=export_database)

    assert handler.response_status == 400
    assert "output_path" in (handler.response_payload or {}).get("error", "")


def test_database_import_route_requires_path(tmp_path: Path) -> None:
    """Import route should require an import_path."""
    db_path = tmp_path / "db.sqlite3"
    _seed_database(db_path, "Import Package")

    handler = _HandlerHarness(db_path=db_path, body={})
    database_admin_routes.post_database_import(handler, restore_database=restore_database)

    assert handler.response_status == 400
    assert "import_path" in (handler.response_payload or {}).get("error", "")


def test_database_backup_route_writes_file(tmp_path: Path) -> None:
    """Backup route should create a backup file and respond with metadata."""
    db_path = tmp_path / "db.sqlite3"
    _seed_database(db_path, "Backup Package")

    output_path = tmp_path / "backup.sqlite3"
    handler = _HandlerHarness(
        db_path=db_path,
        body={},
        db_backup_path=output_path,
    )
    database_admin_routes.post_database_backup(handler, backup_database=backup_database)

    assert handler.response_status == 200
    assert output_path.exists()
    assert (handler.response_payload or {}).get("backup_path") == str(output_path)


def test_database_export_route_uses_configured_path(tmp_path: Path) -> None:
    """Export route should use handler-configured export path when provided."""
    db_path = tmp_path / "db.sqlite3"
    _seed_database(db_path, "Configured Export Package")

    output_path = tmp_path / "export.sqlite3"
    handler = _HandlerHarness(
        db_path=db_path,
        body={},
        db_export_path=output_path,
    )
    database_admin_routes.post_database_export(handler, export_database=export_database)

    assert handler.response_status == 200
    assert output_path.exists()
    assert (handler.response_payload or {}).get("export_path") == str(output_path)


def test_backup_database_rejects_existing_path_without_overwrite(tmp_path: Path) -> None:
    """Backup should refuse to overwrite an existing file without permission."""
    src_db = tmp_path / "source.sqlite3"
    _seed_database(src_db, "Existing Backup Source")

    output_path = tmp_path / "backup.sqlite3"
    output_path.write_text("placeholder", encoding="utf-8")

    with pytest.raises(ValueError):
        backup_database(src_db, output_path=output_path, overwrite=False)


def test_backup_database_rejects_directory_path(tmp_path: Path) -> None:
    """Backup should reject directory output paths."""
    src_db = tmp_path / "source.sqlite3"
    _seed_database(src_db, "Directory Backup Source")

    with pytest.raises(ValueError):
        backup_database(src_db, output_path=tmp_path)


def test_backup_database_rejects_directory_source(tmp_path: Path) -> None:
    """Backup should reject non-file source paths."""
    output_path = tmp_path / "backup.sqlite3"
    with pytest.raises(ValueError):
        backup_database(tmp_path, output_path=output_path)


def test_restore_database_without_backup(tmp_path: Path) -> None:
    """Restore can skip creating a pre-restore backup."""
    dest_db = tmp_path / "dest.sqlite3"
    import_db = tmp_path / "import.sqlite3"
    _seed_database(dest_db, "Original Package")
    _seed_database(import_db, "Imported Package")

    result = restore_database(
        dest_db,
        import_path=import_db,
        overwrite=True,
        create_backup=False,
    )

    assert result.backup_path is None


def test_restore_database_rejects_invalid_import(tmp_path: Path) -> None:
    """Restore should reject files that are not valid SQLite databases."""
    dest_db = tmp_path / "dest.sqlite3"
    _seed_database(dest_db, "Original Package")

    import_path = tmp_path / "not-a-db.sqlite3"
    import_path.write_text("not sqlite content", encoding="utf-8")

    with pytest.raises(ValueError):
        restore_database(dest_db, import_path=import_path, overwrite=True)


def test_database_backup_route_accepts_body_path_and_bool(tmp_path: Path) -> None:
    """Backup route should accept explicit output_path and string booleans."""
    db_path = tmp_path / "db.sqlite3"
    _seed_database(db_path, "Backup Path Package")

    output_path = tmp_path / "backup.sqlite3"
    handler = _HandlerHarness(
        db_path=db_path,
        body={"output_path": str(output_path), "overwrite": "true"},
    )
    database_admin_routes.post_database_backup(handler, backup_database=backup_database)

    assert handler.response_status == 200
    assert output_path.exists()


def test_database_export_route_rejects_invalid_bool(tmp_path: Path) -> None:
    """Export route should reject invalid boolean values."""
    db_path = tmp_path / "db.sqlite3"
    _seed_database(db_path, "Bad Bool Package")

    handler = _HandlerHarness(
        db_path=db_path,
        body={"output_path": str(tmp_path / "export.sqlite3"), "overwrite": "maybe"},
    )
    database_admin_routes.post_database_export(handler, export_database=export_database)

    assert handler.response_status == 400
    assert "overwrite" in (handler.response_payload or {}).get("error", "")
