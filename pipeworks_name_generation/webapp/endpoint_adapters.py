"""Endpoint adapter functions for webapp HTTP dispatch.

These adapters bridge route dispatch to route-domain modules while keeping
``WebAppHandler`` focused on transport concerns.
"""

from __future__ import annotations

from typing import Any

from pipeworks_name_generation.webapp.constants import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from pipeworks_name_generation.webapp.frontend import get_index_html, get_static_text_asset
from pipeworks_name_generation.webapp.generation import (
    _coerce_bool,
    _coerce_generation_count,
    _coerce_optional_seed,
    _coerce_output_format,
    _collect_generation_source_values,
    _get_generation_selection_stats,
    _list_generation_package_options,
    _list_generation_syllable_options,
    _sample_generation_values,
)
from pipeworks_name_generation.webapp.http import _parse_optional_int, _parse_required_int
from pipeworks_name_generation.webapp.routes import database as database_routes
from pipeworks_name_generation.webapp.routes import generation as generation_routes
from pipeworks_name_generation.webapp.routes import imports as import_routes
from pipeworks_name_generation.webapp.routes import static as static_routes
from pipeworks_name_generation.webapp.storage import (
    _connect_database,
    _fetch_text_rows,
    _get_package_table,
    _import_package_pair,
    _list_package_tables,
    _list_packages,
)


def get_root(handler: Any, _query: dict[str, list[str]]) -> None:
    """Serve the single-page web UI shell."""
    static_routes.get_root(handler, get_index_html())


def get_static_app_css(handler: Any, _query: dict[str, list[str]]) -> None:
    """Serve main webapp stylesheet."""
    try:
        content, content_type = get_static_text_asset("app.css")
        static_routes.get_text_asset(handler, content=content, content_type=content_type)
    except FileNotFoundError:
        handler.send_error(404, "Not Found")


def get_static_app_js(handler: Any, _query: dict[str, list[str]]) -> None:
    """Serve main webapp client-side script bundle."""
    try:
        content, content_type = get_static_text_asset("app.js")
        static_routes.get_text_asset(handler, content=content, content_type=content_type)
    except FileNotFoundError:
        handler.send_error(404, "Not Found")


def get_health(handler: Any, _query: dict[str, list[str]]) -> None:
    """Return a lightweight liveness response."""
    static_routes.get_health(handler)


def get_generation_package_options(handler: Any, _query: dict[str, list[str]]) -> None:
    """Return package options grouped by generation class."""
    generation_routes.get_package_options(
        handler,
        connect_database=_connect_database,
        initialize_schema=handler._ensure_schema,
        list_generation_package_options=_list_generation_package_options,
    )


def get_generation_package_syllables(handler: Any, query: dict[str, list[str]]) -> None:
    """Return available syllable options for one class/package selection."""
    generation_routes.get_package_syllables(
        handler,
        query,
        parse_required_int=_parse_required_int,
        connect_database=_connect_database,
        initialize_schema=handler._ensure_schema,
        list_generation_syllable_options=_list_generation_syllable_options,
    )


def get_generation_selection_stats(handler: Any, query: dict[str, list[str]]) -> None:
    """Return max item and max unique counts for one selection scope."""
    generation_routes.get_selection_stats(
        handler,
        query,
        parse_required_int=_parse_required_int,
        connect_database=_connect_database,
        initialize_schema=handler._ensure_schema,
        get_generation_selection_stats=_get_generation_selection_stats,
    )


def get_database_packages(handler: Any, _query: dict[str, list[str]]) -> None:
    """Return imported package metadata used by the Database View tab."""
    database_routes.get_packages(
        handler,
        connect_database=_connect_database,
        initialize_schema=handler._ensure_schema,
        list_packages=_list_packages,
    )


def get_database_package_tables(handler: Any, query: dict[str, list[str]]) -> None:
    """Return available imported txt tables for a selected package id."""
    database_routes.get_package_tables(
        handler,
        query,
        parse_required_int=_parse_required_int,
        connect_database=_connect_database,
        initialize_schema=handler._ensure_schema,
        list_package_tables=_list_package_tables,
    )


def get_database_table_rows(handler: Any, query: dict[str, list[str]]) -> None:
    """Return paginated rows from one imported physical txt-backed table."""
    database_routes.get_table_rows(
        handler,
        query,
        default_page_limit=DEFAULT_PAGE_LIMIT,
        max_page_limit=MAX_PAGE_LIMIT,
        parse_required_int=_parse_required_int,
        parse_optional_int=_parse_optional_int,
        connect_database=_connect_database,
        initialize_schema=handler._ensure_schema,
        get_package_table=_get_package_table,
        fetch_text_rows=_fetch_text_rows,
    )


def get_favicon(handler: Any, _query: dict[str, list[str]]) -> None:
    """Reply to browser favicon probes without noisy 404 logs."""
    static_routes.get_favicon(handler)


def post_import(handler: Any) -> None:
    """Import one metadata+zip pair and create tables for included txt data."""
    import_routes.post_import(
        handler,
        connect_database=_connect_database,
        initialize_schema=handler._ensure_schema,
        import_package_pair=_import_package_pair,
    )


def post_generate(handler: Any) -> None:
    """Generate names from SQLite tables for one selected class scope."""
    generation_routes.post_generate(
        handler,
        coerce_generation_count=_coerce_generation_count,
        coerce_optional_seed=_coerce_optional_seed,
        coerce_bool=_coerce_bool,
        coerce_output_format=_coerce_output_format,
        connect_database=_connect_database,
        initialize_schema=handler._ensure_schema,
        collect_generation_source_values=_collect_generation_source_values,
        sample_generation_values=_sample_generation_values,
    )


__all__ = [
    "get_root",
    "get_static_app_css",
    "get_static_app_js",
    "get_health",
    "get_generation_package_options",
    "get_generation_package_syllables",
    "get_generation_selection_stats",
    "get_database_packages",
    "get_database_package_tables",
    "get_database_table_rows",
    "get_favicon",
    "post_import",
    "post_generate",
]
