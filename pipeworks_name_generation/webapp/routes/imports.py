"""Import route handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol


class _ImportHandler(Protocol):
    """Structural protocol for import endpoint handler behavior."""

    db_path: Path

    def _read_json_body(self) -> dict[str, Any]: ...

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None: ...


def post_import(
    handler: _ImportHandler,
    *,
    connect_database: Callable[..., Any],
    initialize_schema: Callable[..., None],
    import_package_pair: Callable[..., dict[str, Any]],
) -> None:
    """Import one metadata+zip pair and create tables for included txt data."""
    try:
        payload = handler._read_json_body()
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return

    metadata_raw = str(payload.get("metadata_json_path", "")).strip()
    zip_raw = str(payload.get("package_zip_path", "")).strip()
    if not metadata_raw or not zip_raw:
        handler._send_json(
            {"error": "Both 'metadata_json_path' and 'package_zip_path' are required."},
            status=400,
        )
        return

    metadata_path = Path(metadata_raw).expanduser()
    zip_path = Path(zip_raw).expanduser()

    try:
        with connect_database(handler.db_path) as conn:
            initialize_schema(conn)
            result = import_package_pair(conn, metadata_path=metadata_path, zip_path=zip_path)
        handler._send_json(result)
    except (FileNotFoundError, ValueError) as exc:
        handler._send_json({"error": str(exc)}, status=400)
    except Exception as exc:  # nosec B110 - converted into controlled API response
        handler._send_json({"error": f"Import failed: {exc}"}, status=500)


__all__ = ["post_import"]
