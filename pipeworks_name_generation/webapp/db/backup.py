"""SQLite backup/export/restore helpers for the webapp database.

These utilities provide safe, deterministic file-level operations for the
webapp SQLite database. They intentionally avoid HTTP concerns and focus on
filesystem + SQLite behavior only.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pipeworks_name_generation.webapp.db.connection import connect_database


@dataclass(frozen=True)
class BackupResult:
    """Summary metadata returned after a backup or export."""

    path: Path
    bytes_written: int
    sha256: str
    created_at: str


@dataclass(frozen=True)
class RestoreResult:
    """Summary metadata returned after a restore/import operation."""

    restored_path: Path
    bytes_written: int
    sha256: str
    created_at: str
    backup_path: Path | None = None


def _hash_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Compute a SHA-256 digest for a file on disk."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ensure_sqlite_file(path: Path, *, label: str) -> Path:
    """Validate that a path exists and is a readable SQLite database."""
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise ValueError(f"{label} does not exist: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"{label} must be a file: {resolved}")

    try:
        uri = f"{resolved.as_uri()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            conn.execute("PRAGMA schema_version").fetchone()
    except sqlite3.OperationalError:
        # Some environments reject read-only URI connections (for example macOS
        # privacy or filesystem restrictions). Fall back to a plain connection
        # for validation before declaring the file invalid.
        try:
            with sqlite3.connect(resolved) as conn:
                conn.execute("PRAGMA query_only = ON")
                conn.execute("PRAGMA schema_version").fetchone()
        except sqlite3.DatabaseError as exc:
            raise ValueError(f"{label} is not a valid SQLite database: {resolved}") from exc
    except sqlite3.DatabaseError as exc:
        raise ValueError(f"{label} is not a valid SQLite database: {resolved}") from exc

    return resolved


def _ensure_output_path(path: Path, *, overwrite: bool, label: str) -> Path:
    """Validate output path intent and ensure parent directories exist."""
    resolved = path.expanduser().resolve()
    if resolved.exists() and not overwrite:
        raise ValueError(f"{label} already exists: {resolved}")
    if resolved.exists() and resolved.is_dir():
        raise ValueError(f"{label} must be a file path, not a directory: {resolved}")
    if resolved.parent and str(resolved.parent) != ".":
        resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _timestamped_path(base_path: Path, *, suffix: str) -> Path:
    """Create a timestamped filename alongside the base path."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    extension = base_path.suffix or ".sqlite3"
    return base_path.with_name(f"{base_path.stem}_{suffix}_{timestamp}{extension}")


def _run_backup(source_path: Path, destination_path: Path) -> None:
    """Copy an SQLite database using SQLite's backup API."""
    with connect_database(source_path) as source_conn:
        with sqlite3.connect(destination_path) as dest_conn:
            source_conn.backup(dest_conn)
            dest_conn.commit()


def backup_database(
    db_path: Path,
    *,
    output_path: Path | None = None,
    overwrite: bool = False,
) -> BackupResult:
    """Create a point-in-time backup of the webapp database.

    Args:
        db_path: Source SQLite database to back up.
        output_path: Optional destination file. When omitted, a timestamped
            sibling file is created next to ``db_path``.
        overwrite: When ``True``, allow replacing an existing file.

    Returns:
        ``BackupResult`` with the path and content hash of the backup.
    """
    source = _ensure_sqlite_file(db_path, label="Database")
    target = output_path or _timestamped_path(source, suffix="backup")
    resolved_target = _ensure_output_path(target, overwrite=overwrite, label="Backup path")

    _run_backup(source, resolved_target)
    created_at = datetime.now(timezone.utc).isoformat()
    return BackupResult(
        path=resolved_target,
        bytes_written=resolved_target.stat().st_size,
        sha256=_hash_file(resolved_target),
        created_at=created_at,
    )


def export_database(
    db_path: Path,
    *,
    output_path: Path,
    overwrite: bool = False,
) -> BackupResult:
    """Export the database to a file path.

    This is a convenience wrapper over :func:`backup_database` that keeps the
    naming explicit for API users.
    """
    return backup_database(db_path, output_path=output_path, overwrite=overwrite)


def restore_database(
    db_path: Path,
    *,
    import_path: Path,
    overwrite: bool = False,
    create_backup: bool = True,
    backup_path: Path | None = None,
) -> RestoreResult:
    """Restore the webapp database from an existing SQLite file.

    Args:
        db_path: Destination database path used by the webapp.
        import_path: Existing SQLite file to restore from.
        overwrite: When ``True``, allow replacing an existing destination DB.
        create_backup: When ``True`` and the destination exists, create a
            timestamped backup first.
        backup_path: Optional explicit backup path used when ``create_backup``
            is enabled.

    Returns:
        ``RestoreResult`` with the restored DB path and optional backup path.
    """
    source = _ensure_sqlite_file(import_path, label="Import file")
    destination = db_path.expanduser().resolve()

    if source == destination:
        raise ValueError("Import file path must be different from the destination DB path.")

    backup_created: Path | None = None
    if destination.exists():
        if not overwrite:
            raise ValueError(
                "Destination database already exists. Pass overwrite=true to replace it."
            )
        if create_backup:
            backup_target = backup_path or _timestamped_path(destination, suffix="pre_restore")
            backup_created = backup_database(
                destination, output_path=backup_target, overwrite=overwrite
            ).path

    if destination.parent and str(destination.parent) != ".":
        destination.parent.mkdir(parents=True, exist_ok=True)

    _run_backup(source, destination)
    created_at = datetime.now(timezone.utc).isoformat()
    return RestoreResult(
        restored_path=destination,
        bytes_written=destination.stat().st_size,
        sha256=_hash_file(destination),
        created_at=created_at,
        backup_path=backup_created,
    )


__all__ = [
    "BackupResult",
    "RestoreResult",
    "backup_database",
    "export_database",
    "restore_database",
]
