"""Import service for package metadata JSON + package ZIP pairs.

The importer is intentionally pair-based. Filenames do not need to match; the
user provides both paths explicitly and validation ensures both files exist.
"""

from __future__ import annotations

import json
import sqlite3
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeworks_name_generation.webapp.db import insert_imported_package

REQUIRED_METADATA_KEYS = {
    "schema_version",
    "created_at",
    "author",
    "version",
    "common_name",
    "intended_use",
    "source_run",
    "source_dir",
    "examples",
    "include",
    "files_included",
}


@dataclass
class ImportResult:
    """Result of an import operation."""

    package_id: int | None
    message: str


def import_package_pair(
    conn: sqlite3.Connection,
    metadata_json_path: Path,
    package_zip_path: Path,
) -> ImportResult:
    """Import a metadata/ZIP pair into SQLite.

    Args:
        conn: Active sqlite connection
        metadata_json_path: Metadata JSON file path
        package_zip_path: Package ZIP file path

    Returns:
        ImportResult describing success/failure

    Raises:
        FileNotFoundError: If either file path does not exist
        ValueError: If metadata is invalid
        zipfile.BadZipFile: If package ZIP is invalid
    """
    metadata_path = metadata_json_path.expanduser().resolve()
    zip_path = package_zip_path.expanduser().resolve()

    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata JSON does not exist: {metadata_path}")
    if not zip_path.exists():
        raise FileNotFoundError(f"Package ZIP does not exist: {zip_path}")

    payload = _load_metadata_payload(metadata_path)
    _validate_metadata_payload(payload)

    zip_entries = _read_zip_entries(zip_path)
    imported_at = datetime.now(timezone.utc).isoformat()

    try:
        package_id = insert_imported_package(
            conn,
            imported_at=imported_at,
            metadata_payload=payload,
            metadata_json_path=metadata_path,
            package_zip_path=zip_path,
            zip_entries=zip_entries,
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError("This metadata/zip pair is already imported.") from exc

    return ImportResult(package_id=package_id, message="Import completed successfully.")


def _load_metadata_payload(metadata_json_path: Path) -> dict[str, Any]:
    """Load and decode metadata JSON payload."""
    with open(metadata_json_path, encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError("Metadata JSON root must be an object.")

    return payload


def _validate_metadata_payload(payload: dict[str, Any]) -> None:
    """Validate metadata payload against expected packager schema.

    Args:
        payload: Parsed metadata object

    Raises:
        ValueError: If required keys/types are missing or malformed
    """
    missing = sorted(REQUIRED_METADATA_KEYS - set(payload.keys()))
    if missing:
        raise ValueError(f"Metadata JSON is missing required keys: {', '.join(missing)}")

    if not isinstance(payload.get("intended_use"), list):
        raise ValueError("Metadata key 'intended_use' must be a list.")
    if not isinstance(payload.get("examples"), dict):
        raise ValueError("Metadata key 'examples' must be an object.")
    if not isinstance(payload.get("include"), dict):
        raise ValueError("Metadata key 'include' must be an object.")
    if not isinstance(payload.get("files_included"), list):
        raise ValueError("Metadata key 'files_included' must be a list.")


def _read_zip_entries(zip_path: Path) -> list[str]:
    """Read ZIP file member names in deterministic sorted order."""
    with zipfile.ZipFile(zip_path, "r") as archive:
        entries = archive.namelist()
    return sorted(entries)
