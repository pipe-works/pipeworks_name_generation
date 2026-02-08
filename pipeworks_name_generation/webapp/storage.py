"""Compatibility facade over the refactored webapp database layer.

Historically, webapp storage helpers lived in this single module and were
imported by tests and route code via underscored names. The implementation now
lives under ``pipeworks_name_generation.webapp.db``.

This facade keeps the existing helper surface stable while delegating concrete
behavior to focused database modules.
"""

from __future__ import annotations

from pipeworks_name_generation.webapp.db import (
    build_package_table_name,
    connect_database,
    create_text_table,
    fetch_text_rows,
    get_package_table,
    import_package_pair,
    initialize_schema,
    insert_text_rows,
    list_package_tables,
    list_packages,
    load_metadata_json,
    quote_identifier,
    read_txt_rows,
    slugify_identifier,
)

# Backward-compatible underscored aliases used across route code/tests.
_connect_database = connect_database
_initialize_schema = initialize_schema
_import_package_pair = import_package_pair
_load_metadata_json = load_metadata_json
_read_txt_rows = read_txt_rows
_build_package_table_name = build_package_table_name
_slugify_identifier = slugify_identifier
_quote_identifier = quote_identifier
_create_text_table = create_text_table
_insert_text_rows = insert_text_rows
_list_packages = list_packages
_list_package_tables = list_package_tables
_get_package_table = get_package_table
_fetch_text_rows = fetch_text_rows

__all__ = [
    "_connect_database",
    "_initialize_schema",
    "_import_package_pair",
    "_load_metadata_json",
    "_read_txt_rows",
    "_build_package_table_name",
    "_slugify_identifier",
    "_quote_identifier",
    "_create_text_table",
    "_insert_text_rows",
    "_list_packages",
    "_list_package_tables",
    "_get_package_table",
    "_fetch_text_rows",
]
