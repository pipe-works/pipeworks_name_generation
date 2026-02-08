"""Importer workflow for metadata JSON + ZIP package pairs."""

from __future__ import annotations

import json
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeworks_name_generation.webapp.db.repositories import build_package_table_name
from pipeworks_name_generation.webapp.db.table_store import create_text_table, insert_text_rows


def load_metadata_json(metadata_path: Path) -> dict[str, Any]:
    """Load metadata JSON and enforce object-root structure.

    Args:
        metadata_path: Path to metadata JSON file.

    Returns:
        Parsed JSON object.

    Raises:
        ValueError: If the root JSON value is not an object.
    """
    with open(metadata_path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Metadata JSON root must be an object.")
    return payload


def read_txt_rows(archive: zipfile.ZipFile, entry_name: str) -> list[tuple[int, str]]:
    """Read one txt entry and return ``(line_number, value)`` tuples.

    Empty and whitespace-only lines are skipped during import so DB tables only
    store meaningful values.
    """
    try:
        payload = archive.read(entry_name)
    except KeyError as exc:
        raise ValueError(f"TXT entry missing from zip: {entry_name}") from exc

    try:
        decoded = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"TXT entry is not valid UTF-8: {entry_name}") from exc

    rows: list[tuple[int, str]] = []
    for line_number, line in enumerate(decoded.splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        rows.append((line_number, text))
    return rows


def import_package_pair(
    conn: sqlite3.Connection, *, metadata_path: Path, zip_path: Path
) -> dict[str, Any]:
    """Import one metadata+zip pair and create one SQLite table per ``*.txt``.

    The importer ignores JSON files inside the archive. It uses metadata
    ``files_included`` (when provided) to limit which ``*.txt`` entries are
    imported.

    Args:
        conn: Open SQLite connection.
        metadata_path: Path to ``*_metadata.json`` file.
        zip_path: Path to package zip file.

    Returns:
        API-style summary payload describing imported package and created tables.

    Raises:
        FileNotFoundError: If metadata or zip path does not exist.
        ValueError: For invalid metadata, duplicate imports, or zip format/data
            issues.
    """
    metadata_resolved = metadata_path.resolve()
    zip_resolved = zip_path.resolve()

    if not metadata_resolved.exists():
        raise FileNotFoundError(f"Metadata JSON does not exist: {metadata_resolved}")
    if not zip_resolved.exists():
        raise FileNotFoundError(f"Package ZIP does not exist: {zip_resolved}")

    payload = load_metadata_json(metadata_resolved)
    package_name = str(payload.get("common_name", "")).strip() or zip_resolved.stem

    raw_files_included = payload.get("files_included")
    if raw_files_included is None:
        files_included: list[Any] = []
    elif isinstance(raw_files_included, list):
        files_included = raw_files_included
    else:
        raise ValueError("Metadata key 'files_included' must be a list when provided.")

    allowed_txt_names = {
        str(name).strip() for name in files_included if str(name).strip().lower().endswith(".txt")
    }

    try:
        with zipfile.ZipFile(zip_resolved, "r") as archive:
            entries = sorted(
                name
                for name in archive.namelist()
                if not name.endswith("/") and name.lower().endswith(".txt")
            )

            if allowed_txt_names:
                entries = [entry for entry in entries if Path(entry).name in allowed_txt_names]

            cursor = conn.execute(
                """
                INSERT INTO imported_packages (
                    package_name,
                    imported_at,
                    metadata_json_path,
                    package_zip_path
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    package_name,
                    datetime.now(timezone.utc).isoformat(),
                    str(metadata_resolved),
                    str(zip_resolved),
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("SQLite did not return a row id for imported package insert.")
            package_id = int(cursor.lastrowid)

            created_tables: list[dict[str, Any]] = []
            for index, entry_name in enumerate(entries, start=1):
                txt_rows = read_txt_rows(archive, entry_name)
                table_name = build_package_table_name(
                    package_name, Path(entry_name).stem, package_id, index
                )
                create_text_table(conn, table_name)
                insert_text_rows(conn, table_name, txt_rows)

                conn.execute(
                    """
                    INSERT INTO package_tables (package_id, source_txt_name, table_name, row_count)
                    VALUES (?, ?, ?, ?)
                    """,
                    (package_id, Path(entry_name).name, table_name, len(txt_rows)),
                )
                created_tables.append(
                    {
                        "source_txt_name": Path(entry_name).name,
                        "table_name": table_name,
                        "row_count": len(txt_rows),
                    }
                )

            conn.commit()
            return {
                "message": f"Imported package '{package_name}' with {len(created_tables)} txt table(s).",
                "package_id": package_id,
                "package_name": package_name,
                "tables": created_tables,
            }
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ValueError("This metadata/zip pair has already been imported.") from exc
    except zipfile.BadZipFile as exc:
        conn.rollback()
        raise ValueError(f"Invalid ZIP file: {zip_resolved}") from exc
    except Exception:
        conn.rollback()
        raise


__all__ = ["load_metadata_json", "read_txt_rows", "import_package_pair"]
