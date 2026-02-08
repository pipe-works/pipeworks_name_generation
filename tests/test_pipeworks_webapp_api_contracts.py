"""Contract tests for webapp JSON endpoints.

These tests focus on response payload shapes and error semantics that should
remain stable across refactors.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

from pipeworks_name_generation.renderer import render_names
from pipeworks_name_generation.webapp import endpoint_adapters as endpoint_adapters_module
from pipeworks_name_generation.webapp.generation import (
    _coerce_render_style,
    get_cached_generation_package_options,
)
from pipeworks_name_generation.webapp.handler import WebAppHandler
from pipeworks_name_generation.webapp.http import _parse_optional_int, _parse_required_int
from pipeworks_name_generation.webapp.routes import database as database_routes
from pipeworks_name_generation.webapp.routes import generation as generation_routes


class _HandlerHarness:
    """Small in-process handler harness for contract tests."""

    schema_ready: bool = False
    schema_initialized_paths: set[str] = set()

    def __init__(self, *, path: str, db_path: Path, body: dict[str, Any] | None = None) -> None:
        payload = b""
        if body is not None:
            payload = json.dumps(body).encode("utf-8")

        self.path = path
        self.db_path = db_path
        self.verbose = False
        self.headers = {"Content-Length": str(len(payload))}
        self.rfile = io.BytesIO(payload)
        self.wfile = io.BytesIO()
        self.response_status = 0
        self.response_headers: dict[str, str] = {}
        self.error_status: int | None = None
        self.error_message: str | None = None

        self._ensure_schema = WebAppHandler._ensure_schema.__get__(self, WebAppHandler)
        self._send_text = WebAppHandler._send_text.__get__(self, WebAppHandler)
        self._send_json = WebAppHandler._send_json.__get__(self, WebAppHandler)
        self._read_json_body = WebAppHandler._read_json_body.__get__(self, WebAppHandler)

    def send_response(self, status: int) -> None:
        self.response_status = status

    def send_header(self, name: str, value: str) -> None:
        self.response_headers[name] = value

    def end_headers(self) -> None:
        pass

    def send_error(self, code: int, message: str | None = None) -> None:
        self.error_status = code
        self.error_message = message

    def json_body(self) -> dict[str, Any]:
        self.wfile.seek(0)
        payload = self.wfile.read().decode("utf-8")
        return json.loads(payload) if payload else {}


def _build_sample_db(tmp_path: Path) -> Path:
    """Create a small sqlite db with one package and two txt tables."""
    db_path = tmp_path / "contract.sqlite3"
    from pipeworks_name_generation.webapp.db import (
        connect_database,
        create_text_table,
        initialize_schema,
        insert_text_rows,
    )

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
            ("Contract Package", "2026-02-08T00:00:00+00:00", "meta.json", "pack.zip"),
        )
        if inserted.lastrowid is None:
            raise AssertionError("Expected sqlite row id for imported package insert.")
        package_id = int(inserted.lastrowid)

        conn.execute(
            """
            INSERT INTO package_tables (package_id, source_txt_name, table_name, row_count)
            VALUES (?, ?, ?, ?)
            """,
            (package_id, "nltk_first_name_2syl.txt", "contract_t1", 2),
        )
        conn.execute(
            """
            INSERT INTO package_tables (package_id, source_txt_name, table_name, row_count)
            VALUES (?, ?, ?, ?)
            """,
            (package_id, "nltk_last_name_all.txt", "contract_t2", 2),
        )
        create_text_table(conn, "contract_t1")
        create_text_table(conn, "contract_t2")
        insert_text_rows(conn, "contract_t1", [(1, "alfa"), (2, "beta")])
        insert_text_rows(conn, "contract_t2", [(1, "thorn"), (2, "briar")])
        conn.commit()

    return db_path


def test_generation_package_options_contract(tmp_path: Path) -> None:
    """Package options should include name class entries with package arrays."""
    db_path = _build_sample_db(tmp_path)
    handler = _HandlerHarness(path="/api/generation/package-options", db_path=db_path)

    generation_routes.get_package_options(
        handler,
        connect_database=endpoint_adapters_module._connect_database,
        initialize_schema=handler._ensure_schema,
        list_generation_package_options=lambda conn: get_cached_generation_package_options(
            conn, db_path=handler.db_path
        ),
    )

    payload = handler.json_body()
    assert "name_classes" in payload
    assert isinstance(payload["name_classes"], list)
    first_entry = payload["name_classes"][0]
    assert "key" in first_entry
    assert "label" in first_entry
    assert "packages" in first_entry


def test_generation_package_syllables_contract(tmp_path: Path) -> None:
    """Syllable options should return class_key/package_id and option list."""
    db_path = _build_sample_db(tmp_path)
    handler = _HandlerHarness(path="/api/generation/package-syllables", db_path=db_path)

    generation_routes.get_package_syllables(
        handler,
        {"class_key": ["first_name"], "package_id": ["1"]},
        parse_required_int=_parse_required_int,
        connect_database=endpoint_adapters_module._connect_database,
        initialize_schema=handler._ensure_schema,
        list_generation_syllable_options=endpoint_adapters_module._list_generation_syllable_options,
    )

    payload = handler.json_body()
    assert payload["class_key"] == "first_name"
    assert payload["package_id"] == 1
    assert "syllable_options" in payload
    assert isinstance(payload["syllable_options"], list)


def test_generation_selection_stats_contract(tmp_path: Path) -> None:
    """Selection stats should include max_items and max_unique_combinations."""
    db_path = _build_sample_db(tmp_path)
    handler = _HandlerHarness(path="/api/generation/selection-stats", db_path=db_path)

    generation_routes.get_selection_stats(
        handler,
        {
            "class_key": ["first_name"],
            "package_id": ["1"],
            "syllable_key": ["2syl"],
        },
        parse_required_int=_parse_required_int,
        connect_database=endpoint_adapters_module._connect_database,
        initialize_schema=handler._ensure_schema,
        get_generation_selection_stats=endpoint_adapters_module._get_generation_selection_stats,
    )

    payload = handler.json_body()
    assert payload["class_key"] == "first_name"
    assert payload["package_id"] == 1
    assert payload["syllable_key"] == "2syl"
    assert "max_items" in payload
    assert "max_unique_combinations" in payload


def test_generate_contract_json(tmp_path: Path) -> None:
    """Generate should return names list and metadata fields."""
    db_path = _build_sample_db(tmp_path)
    handler = _HandlerHarness(
        path="/api/generate",
        db_path=db_path,
        body={
            "class_key": "first_name",
            "package_id": 1,
            "syllable_key": "2syl",
            "generation_count": 2,
            "unique_only": True,
            "seed": 123,
            "output_format": "json",
        },
    )

    generation_routes.post_generate(
        handler,
        coerce_generation_count=endpoint_adapters_module._coerce_generation_count,
        coerce_optional_seed=endpoint_adapters_module._coerce_optional_seed,
        coerce_bool=endpoint_adapters_module._coerce_bool,
        coerce_output_format=endpoint_adapters_module._coerce_output_format,
        coerce_render_style=_coerce_render_style,
        connect_database=endpoint_adapters_module._connect_database,
        initialize_schema=handler._ensure_schema,
        collect_generation_source_values=endpoint_adapters_module._collect_generation_source_values,
        sample_generation_values=endpoint_adapters_module._sample_generation_values,
        render_values=render_names,
    )

    payload = handler.json_body()
    assert payload["source"] == "sqlite"
    assert payload["class_key"] == "first_name"
    assert payload["package_id"] == 1
    assert payload["syllable_key"] == "2syl"
    assert payload["generation_count"] == 2
    assert payload["unique_only"] is True
    assert payload["output_format"] == "json"
    assert isinstance(payload["names"], list)


def test_generate_contract_txt_format(tmp_path: Path) -> None:
    """Generate should include text payload when output_format=txt."""
    db_path = _build_sample_db(tmp_path)
    handler = _HandlerHarness(
        path="/api/generate",
        db_path=db_path,
        body={
            "class_key": "last_name",
            "package_id": 1,
            "syllable_key": "all",
            "generation_count": 1,
            "unique_only": False,
            "output_format": "txt",
        },
    )

    generation_routes.post_generate(
        handler,
        coerce_generation_count=endpoint_adapters_module._coerce_generation_count,
        coerce_optional_seed=endpoint_adapters_module._coerce_optional_seed,
        coerce_bool=endpoint_adapters_module._coerce_bool,
        coerce_output_format=endpoint_adapters_module._coerce_output_format,
        coerce_render_style=_coerce_render_style,
        connect_database=endpoint_adapters_module._connect_database,
        initialize_schema=handler._ensure_schema,
        collect_generation_source_values=endpoint_adapters_module._collect_generation_source_values,
        sample_generation_values=endpoint_adapters_module._sample_generation_values,
        render_values=render_names,
    )

    payload = handler.json_body()
    assert payload["output_format"] == "txt"
    assert "text" in payload


def test_database_packages_contract(tmp_path: Path) -> None:
    """Database packages endpoint should return list of packages."""
    db_path = _build_sample_db(tmp_path)
    handler = _HandlerHarness(path="/api/database/packages", db_path=db_path)

    database_routes.get_packages(
        handler,
        connect_database=endpoint_adapters_module._connect_database,
        initialize_schema=handler._ensure_schema,
        list_packages=endpoint_adapters_module._list_packages,
    )

    payload = handler.json_body()
    assert "packages" in payload
    assert isinstance(payload["packages"], list)


def test_database_tables_contract(tmp_path: Path) -> None:
    """Database tables endpoint should return tables array."""
    db_path = _build_sample_db(tmp_path)
    handler = _HandlerHarness(path="/api/database/tables", db_path=db_path)

    database_routes.get_package_tables(
        handler,
        {"package_id": ["1"]},
        parse_required_int=_parse_required_int,
        connect_database=endpoint_adapters_module._connect_database,
        initialize_schema=handler._ensure_schema,
        list_package_tables=endpoint_adapters_module._list_package_tables,
    )

    payload = handler.json_body()
    assert "tables" in payload
    assert isinstance(payload["tables"], list)


def test_database_table_rows_contract(tmp_path: Path) -> None:
    """Database table rows endpoint should return rows and counts."""
    db_path = _build_sample_db(tmp_path)
    handler = _HandlerHarness(path="/api/database/table", db_path=db_path)

    database_routes.get_table_rows(
        handler,
        {"table_id": ["1"], "offset": ["0"], "limit": ["1"]},
        default_page_limit=25,
        max_page_limit=100,
        parse_required_int=_parse_required_int,
        parse_optional_int=_parse_optional_int,
        connect_database=endpoint_adapters_module._connect_database,
        initialize_schema=handler._ensure_schema,
        get_package_table=endpoint_adapters_module._get_package_table,
        fetch_text_rows=endpoint_adapters_module._fetch_text_rows,
    )

    payload = handler.json_body()
    assert "table" in payload
    assert payload["table"]["id"] == 1
    assert payload["offset"] == 0
    assert payload["limit"] == 1
    assert payload["total_rows"] >= 1
    assert "rows" in payload
    assert isinstance(payload["rows"], list)
