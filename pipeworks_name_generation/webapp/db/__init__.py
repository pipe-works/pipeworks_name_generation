"""Database-layer modules for the webapp backend."""

from .connection import connect_database
from .importer import import_package_pair, load_metadata_json, read_txt_rows
from .repositories import (
    build_package_table_name,
    get_package_table,
    list_package_tables,
    list_packages,
    slugify_identifier,
)
from .schema import initialize_schema
from .table_store import create_text_table, fetch_text_rows, insert_text_rows, quote_identifier

__all__ = [
    "connect_database",
    "initialize_schema",
    "import_package_pair",
    "load_metadata_json",
    "read_txt_rows",
    "build_package_table_name",
    "slugify_identifier",
    "list_packages",
    "list_package_tables",
    "get_package_table",
    "quote_identifier",
    "create_text_table",
    "insert_text_rows",
    "fetch_text_rows",
]
