"""Database-browse route handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol


class _DatabaseHandler(Protocol):
    """Structural protocol for database endpoint handler behavior."""

    db_path: Path

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None: ...


def get_packages(
    handler: _DatabaseHandler,
    *,
    connect_database: Callable[..., Any],
    initialize_schema: Callable[..., None],
    list_packages: Callable[..., list[dict[str, Any]]],
) -> None:
    """Return imported package metadata used by the Database View tab."""
    try:
        with connect_database(handler.db_path) as conn:
            initialize_schema(conn)
            packages = list_packages(conn)
        handler._send_json({"packages": packages, "db_path": str(handler.db_path)})
    except Exception as exc:  # nosec B110 - converted into controlled API response
        handler._send_json({"error": f"Failed to list packages: {exc}"}, status=500)


def get_package_tables(
    handler: _DatabaseHandler,
    query: dict[str, list[str]],
    *,
    parse_required_int: Callable[..., int],
    connect_database: Callable[..., Any],
    initialize_schema: Callable[..., None],
    list_package_tables: Callable[..., list[dict[str, Any]]],
) -> None:
    """Return available imported txt tables for a selected package id."""
    try:
        package_id = parse_required_int(query, "package_id", minimum=1)
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return

    try:
        with connect_database(handler.db_path) as conn:
            initialize_schema(conn)
            tables = list_package_tables(conn, package_id)
        handler._send_json({"tables": tables})
    except Exception as exc:  # nosec B110 - converted into controlled API response
        handler._send_json({"error": f"Failed to list package tables: {exc}"}, status=500)


def get_table_rows(
    handler: _DatabaseHandler,
    query: dict[str, list[str]],
    *,
    default_page_limit: int,
    max_page_limit: int,
    parse_required_int: Callable[..., int],
    parse_optional_int: Callable[..., int],
    connect_database: Callable[..., Any],
    initialize_schema: Callable[..., None],
    get_package_table: Callable[..., dict[str, Any] | None],
    fetch_text_rows: Callable[..., list[dict[str, Any]]],
) -> None:
    """Return paginated rows from one imported physical txt-backed table."""
    try:
        table_id = parse_required_int(query, "table_id", minimum=1)
        offset = parse_optional_int(query, "offset", default=0, minimum=0)
        limit = parse_optional_int(
            query,
            "limit",
            default=default_page_limit,
            minimum=1,
            maximum=max_page_limit,
        )
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return

    try:
        with connect_database(handler.db_path) as conn:
            initialize_schema(conn)
            table_meta = get_package_table(conn, table_id)
            if table_meta is None:
                handler._send_json({"error": "Table id not found."}, status=404)
                return

            rows = fetch_text_rows(conn, table_meta["table_name"], offset=offset, limit=limit)
            handler._send_json(
                {
                    "table": table_meta,
                    "rows": rows,
                    "offset": offset,
                    "limit": limit,
                    "total_rows": table_meta["row_count"],
                }
            )
    except Exception as exc:  # nosec B110 - converted into controlled API response
        handler._send_json({"error": f"Failed to load table rows: {exc}"}, status=500)


__all__ = ["get_packages", "get_package_tables", "get_table_rows"]
