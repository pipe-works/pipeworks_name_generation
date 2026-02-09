"""Administrative database routes (backup/export/import)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol


class _DatabaseAdminHandler(Protocol):
    """Structural protocol for database admin endpoint behavior."""

    db_path: Path
    db_export_path: Path | None
    db_backup_path: Path | None

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None: ...

    def _read_json_body(self) -> dict[str, Any]: ...


class DatabaseAdminError(ValueError):
    """Raised when database admin input validation fails."""


def _coerce_bool(value: Any, *, field: str) -> bool:
    """Convert a payload value into a strict boolean."""
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return False
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in {"true", "1", "yes", "y"}:
            return True
        if cleaned in {"false", "0", "no", "n"}:
            return False
    if isinstance(value, int):
        return bool(value)
    raise DatabaseAdminError(f"{field} must be a boolean.")


def _coerce_path(value: Any, *, field: str, required: bool) -> Path | None:
    """Normalize a file path input."""
    raw = str(value).strip() if value is not None else ""
    if not raw:
        if required:
            raise DatabaseAdminError(f"{field} is required.")
        return None
    return Path(raw).expanduser()


def post_database_backup(
    handler: _DatabaseAdminHandler,
    *,
    backup_database: Callable[..., Any],
) -> None:
    """Create a backup copy of the SQLite database."""
    try:
        payload = handler._read_json_body()
        output_path = _coerce_path(payload.get("output_path"), field="output_path", required=False)
        if output_path is None:
            output_path = handler.db_backup_path
        overwrite = _coerce_bool(payload.get("overwrite"), field="overwrite")
        result = backup_database(
            handler.db_path,
            output_path=output_path,
            overwrite=overwrite,
        )
    except (DatabaseAdminError, ValueError) as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    except Exception as exc:  # pragma: no cover - defensive error response
        handler._send_json({"error": f"Backup failed: {exc}"}, status=500)
        return

    handler._send_json(
        {
            "message": "Backup completed.",
            "backup_path": str(result.path),
            "bytes": result.bytes_written,
            "sha256": result.sha256,
            "created_at": result.created_at,
        }
    )


def post_database_export(
    handler: _DatabaseAdminHandler,
    *,
    export_database: Callable[..., Any],
) -> None:
    """Export the SQLite database to a file path."""
    try:
        payload = handler._read_json_body()
        output_path = _coerce_path(payload.get("output_path"), field="output_path", required=False)
        if output_path is None:
            output_path = handler.db_export_path
        if output_path is None:
            raise DatabaseAdminError(
                "output_path is required (or set db_export_path in server.ini)."
            )
        overwrite = _coerce_bool(payload.get("overwrite"), field="overwrite")
        result = export_database(
            handler.db_path,
            output_path=output_path,
            overwrite=overwrite,
        )
    except (DatabaseAdminError, ValueError) as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    except Exception as exc:  # pragma: no cover - defensive error response
        handler._send_json({"error": f"Export failed: {exc}"}, status=500)
        return

    handler._send_json(
        {
            "message": "Export completed.",
            "export_path": str(result.path),
            "bytes": result.bytes_written,
            "sha256": result.sha256,
            "created_at": result.created_at,
        }
    )


def post_database_import(
    handler: _DatabaseAdminHandler,
    *,
    restore_database: Callable[..., Any],
) -> None:
    """Restore the SQLite database from a file path."""
    try:
        payload = handler._read_json_body()
        import_path = _coerce_path(payload.get("import_path"), field="import_path", required=True)
        overwrite = _coerce_bool(payload.get("overwrite"), field="overwrite")
        create_backup = _coerce_bool(payload.get("create_backup", True), field="create_backup")
        backup_path = _coerce_path(payload.get("backup_path"), field="backup_path", required=False)
        result = restore_database(
            handler.db_path,
            import_path=import_path,
            overwrite=overwrite,
            create_backup=create_backup,
            backup_path=backup_path,
        )
    except (DatabaseAdminError, ValueError) as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    except Exception as exc:  # pragma: no cover - defensive error response
        handler._send_json({"error": f"Import failed: {exc}"}, status=500)
        return

    handler._send_json(
        {
            "message": "Import completed.",
            "import_path": str(import_path) if import_path else None,
            "restored_path": str(result.restored_path),
            "backup_path": str(result.backup_path) if result.backup_path else None,
            "bytes": result.bytes_written,
            "sha256": result.sha256,
            "created_at": result.created_at,
        }
    )


__all__ = [
    "post_database_backup",
    "post_database_export",
    "post_database_import",
]
