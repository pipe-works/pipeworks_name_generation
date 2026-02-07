"""Tests for the minimal Pipeworks webapp server and API helpers."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

import pipeworks_name_generation.webapp.server as server_module
from pipeworks_name_generation.webapp.config import ServerSettings
from pipeworks_name_generation.webapp.server import (
    WebAppHandler,
    _coerce_int,
    _connect_database,
    _extract_syllable_option_from_source_txt_name,
    _fetch_text_rows,
    _get_generation_selection_stats,
    _get_package_table,
    _import_package_pair,
    _initialize_schema,
    _insert_text_rows,
    _list_generation_package_options,
    _list_generation_syllable_options,
    _list_package_tables,
    _list_packages,
    _load_metadata_json,
    _map_source_txt_name_to_generation_class,
    _parse_optional_int,
    _parse_required_int,
    _port_is_available,
    _quote_identifier,
    _read_txt_rows,
    _slugify_identifier,
    build_settings_from_args,
    create_argument_parser,
    create_handler_class,
    find_available_port,
    main,
    parse_arguments,
    resolve_server_port,
    run_server,
    start_http_server,
)


def _build_sample_package_pair(tmp_path: Path) -> tuple[Path, Path]:
    """Create a realistic metadata+zip test pair with two ``*.txt`` files."""
    metadata_path = tmp_path / "goblin_flower-latin_selections_metadata.json"
    zip_path = tmp_path / "goblin_flower-latin_selections.zip"

    payload = {
        "common_name": "Goblin Flower Latin",
        "files_included": [
            "nltk_first_name_2syl.txt",
            "nltk_last_name_2syl.txt",
            "nltk_first_name_2syl.json",
        ],
    }
    metadata_path.write_text(json.dumps(payload), encoding="utf-8")

    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("selections/nltk_first_name_2syl.txt", "alfa\n\nbeta\ngamma\n")
        archive.writestr("selections/nltk_last_name_2syl.txt", "thorn\nbriar\n")
        archive.writestr("selections/nltk_first_name_2syl.json", '{"ignored": true}')

    return metadata_path, zip_path


class _HandlerHarness:
    """Small in-process harness for route testing without opening sockets."""

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

        # Bind handler methods directly so route logic executes unchanged.
        self._send_text = WebAppHandler._send_text.__get__(self, WebAppHandler)
        self._send_json = WebAppHandler._send_json.__get__(self, WebAppHandler)
        self._read_json_body = WebAppHandler._read_json_body.__get__(self, WebAppHandler)
        self._handle_import = WebAppHandler._handle_import.__get__(self, WebAppHandler)
        self._handle_generation = WebAppHandler._handle_generation.__get__(self, WebAppHandler)
        self.do_GET = WebAppHandler.do_GET.__get__(self, WebAppHandler)
        self.do_POST = WebAppHandler.do_POST.__get__(self, WebAppHandler)

    def send_response(self, status: int) -> None:
        """Store HTTP status code sent by handler logic."""
        self.response_status = status

    def send_header(self, name: str, value: str) -> None:
        """Capture response headers for assertions when needed."""
        self.response_headers[name] = value

    def end_headers(self) -> None:
        """Mirror BaseHTTPRequestHandler API; no-op for harness."""

    def send_error(self, code: int, message: str | None = None) -> None:
        """Capture error responses emitted by unknown-route handling."""
        self.error_status = code
        self.error_message = message

    def json_body(self) -> dict[str, Any]:
        """Decode written response body as JSON."""
        self.wfile.seek(0)
        payload = self.wfile.read().decode("utf-8")
        return json.loads(payload) if payload else {}


def test_slugify_identifier_normalizes_input() -> None:
    """Slugify should normalize punctuation, empties, and leading digits."""
    assert _slugify_identifier("Goblin Flower Latin", max_length=24) == "goblin_flower_latin"
    assert _slugify_identifier("%%%###", max_length=24) == "item"
    assert _slugify_identifier("123_name", max_length=24).startswith("n_")


def test_quote_identifier_rejects_unsafe_name() -> None:
    """SQL identifier quoting should reject non-identifier characters."""
    with pytest.raises(ValueError):
        _quote_identifier("drop table x;")


def test_import_package_pair_populates_schema_and_rows(tmp_path: Path) -> None:
    """Importer should create one SQLite table per listed txt file."""
    db_path = tmp_path / "webapp.sqlite3"
    metadata_path, zip_path = _build_sample_package_pair(tmp_path)

    with _connect_database(db_path) as conn:
        _initialize_schema(conn)
        result = _import_package_pair(conn, metadata_path=metadata_path, zip_path=zip_path)

        assert result["package_name"] == "Goblin Flower Latin"
        assert len(result["tables"]) == 2

        packages = _list_packages(conn)
        assert len(packages) == 1
        package_id = packages[0]["id"]

        tables = _list_package_tables(conn, package_id)
        assert len(tables) == 2
        assert {table["source_txt_name"] for table in tables} == {
            "nltk_first_name_2syl.txt",
            "nltk_last_name_2syl.txt",
        }

        first_table = tables[0]
        meta = _get_package_table(conn, int(first_table["id"]))
        assert meta is not None
        rows = _fetch_text_rows(conn, str(meta["table_name"]), offset=0, limit=20)
        assert rows
        assert all("value" in row for row in rows)


def test_import_package_pair_rejects_duplicate_pair(tmp_path: Path) -> None:
    """Importing the same metadata+zip pair twice should fail cleanly."""
    db_path = tmp_path / "webapp.sqlite3"
    metadata_path, zip_path = _build_sample_package_pair(tmp_path)

    with _connect_database(db_path) as conn:
        _initialize_schema(conn)
        _import_package_pair(conn, metadata_path=metadata_path, zip_path=zip_path)

        with pytest.raises(ValueError, match="already been imported"):
            _import_package_pair(conn, metadata_path=metadata_path, zip_path=zip_path)


def test_import_package_pair_rejects_invalid_files_included_type(tmp_path: Path) -> None:
    """Metadata ``files_included`` must be list when provided."""
    db_path = tmp_path / "webapp.sqlite3"
    metadata_path = tmp_path / "bad_metadata.json"
    zip_path = tmp_path / "ok.zip"
    metadata_path.write_text(
        json.dumps({"common_name": "Invalid", "files_included": "nltk_first_name_2syl.txt"}),
        encoding="utf-8",
    )
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("selections/nltk_first_name_2syl.txt", "alfa\n")

    with _connect_database(db_path) as conn:
        _initialize_schema(conn)
        with pytest.raises(ValueError, match="files_included"):
            _import_package_pair(conn, metadata_path=metadata_path, zip_path=zip_path)


def test_api_endpoints_import_and_browse_rows(tmp_path: Path) -> None:
    """End-to-end API flow should import package and expose rows via routes."""
    metadata_path, zip_path = _build_sample_package_pair(tmp_path)
    db_path = tmp_path / "webapi.sqlite3"

    health = _HandlerHarness(path="/api/health", db_path=db_path)
    health.do_GET()
    assert health.response_status == 200
    assert health.json_body()["ok"] is True

    importer = _HandlerHarness(
        path="/api/import",
        db_path=db_path,
        body={
            "metadata_json_path": str(metadata_path),
            "package_zip_path": str(zip_path),
        },
    )
    importer.do_POST()
    import_payload = importer.json_body()
    assert importer.response_status == 200
    assert import_payload["package_name"] == "Goblin Flower Latin"
    assert len(import_payload["tables"]) == 2

    packages = _HandlerHarness(path="/api/database/packages", db_path=db_path)
    packages.do_GET()
    packages_payload = packages.json_body()
    assert packages.response_status == 200
    assert packages_payload["packages"]
    package_id = int(packages_payload["packages"][0]["id"])

    tables = _HandlerHarness(
        path=f"/api/database/package-tables?package_id={package_id}",
        db_path=db_path,
    )
    tables.do_GET()
    tables_payload = tables.json_body()
    assert tables.response_status == 200
    assert tables_payload["tables"]
    table_id = int(tables_payload["tables"][0]["id"])

    rows = _HandlerHarness(
        path=f"/api/database/table-rows?table_id={table_id}&offset=0&limit=20",
        db_path=db_path,
    )
    rows.do_GET()
    rows_payload = rows.json_body()
    assert rows.response_status == 200
    assert rows_payload["rows"]
    assert rows_payload["limit"] == 20

    generation_options = _HandlerHarness(path="/api/generation/package-options", db_path=db_path)
    generation_options.do_GET()
    options_payload = generation_options.json_body()
    assert generation_options.response_status == 200
    assert options_payload["name_classes"]
    first_name_entry = next(
        entry for entry in options_payload["name_classes"] if entry["key"] == "first_name"
    )
    assert first_name_entry["packages"]
    syllables = _HandlerHarness(
        path=f"/api/generation/package-syllables?class_key=first_name&package_id={package_id}",
        db_path=db_path,
    )
    syllables.do_GET()
    syllables_payload = syllables.json_body()
    assert syllables.response_status == 200
    assert syllables_payload["syllable_options"] == [{"key": "2syl", "label": "2 syllables"}]

    selection_stats = _HandlerHarness(
        path=(
            "/api/generation/selection-stats"
            f"?class_key=first_name&package_id={package_id}&syllable_key=2syl"
        ),
        db_path=db_path,
    )
    selection_stats.do_GET()
    stats_payload = selection_stats.json_body()
    assert selection_stats.response_status == 200
    assert stats_payload["max_items"] == 3
    assert stats_payload["max_unique_combinations"] == 3

    missing = _HandlerHarness(path="/api/database/table-rows", db_path=db_path)
    missing.do_GET()
    missing_payload = missing.json_body()
    assert missing.response_status == 400
    assert "table_id" in missing_payload["error"]


def test_create_handler_class_binds_runtime_values(tmp_path: Path) -> None:
    """Bound handler class should reflect runtime ``verbose`` and ``db_path``."""
    db_path = tmp_path / "bound.sqlite3"
    bound = create_handler_class(verbose=False, db_path=db_path)
    assert bound.verbose is False
    assert bound.db_path == db_path


def test_generation_package_options_endpoint_without_imports(tmp_path: Path) -> None:
    """Generation options endpoint should return empty package lists before imports."""
    db_path = tmp_path / "db.sqlite3"
    with _connect_database(db_path) as conn:
        _initialize_schema(conn)

    harness = _HandlerHarness(path="/api/generation/package-options", db_path=db_path)
    harness.do_GET()
    payload = harness.json_body()
    assert harness.response_status == 200
    assert [entry["key"] for entry in payload["name_classes"]] == [
        "first_name",
        "last_name",
        "place_name",
        "location_name",
        "object_item",
        "organisation",
        "title_epithet",
    ]
    assert all(not entry["packages"] for entry in payload["name_classes"])


def test_log_message_respects_verbose_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Handler should only delegate log messages when verbose is enabled."""
    calls: list[tuple[str, tuple[Any, ...]]] = []

    def fake_super_log_message(self: Any, fmt: str, *args: Any) -> None:
        calls.append((fmt, args))

    monkeypatch.setattr(server_module.BaseHTTPRequestHandler, "log_message", fake_super_log_message)

    handler = WebAppHandler.__new__(WebAppHandler)
    handler.verbose = False
    WebAppHandler.log_message(handler, "x%s", "1")
    assert not calls

    handler.verbose = True
    WebAppHandler.log_message(handler, "y%s", "2")
    assert calls == [("y%s", ("2",))]


def test_read_json_body_validation_errors(tmp_path: Path) -> None:
    """Invalid request body/header shapes should raise clear ``ValueError`` messages."""
    harness = _HandlerHarness(path="/api/import", db_path=tmp_path / "db.sqlite3")

    harness.headers = {"Content-Length": "abc"}
    with pytest.raises(ValueError, match="Invalid Content-Length"):
        harness._read_json_body()

    harness.headers = {"Content-Length": "0"}
    harness.rfile = io.BytesIO(b"")
    with pytest.raises(ValueError, match="Request body is required"):
        harness._read_json_body()

    harness.headers = {"Content-Length": "1"}
    harness.rfile = io.BytesIO(b"{")
    with pytest.raises(ValueError, match="must be valid JSON"):
        harness._read_json_body()

    payload = json.dumps(["not", "object"]).encode("utf-8")
    harness.headers = {"Content-Length": str(len(payload))}
    harness.rfile = io.BytesIO(payload)
    with pytest.raises(ValueError, match="must be a JSON object"):
        harness._read_json_body()


def test_get_misc_routes_and_unknown(tmp_path: Path) -> None:
    """Root, favicon, and unknown GET routes should return expected responses."""
    db_path = tmp_path / "db.sqlite3"

    root = _HandlerHarness(path="/", db_path=db_path)
    root.do_GET()
    assert root.response_status == 200
    assert root.response_headers.get("Content-Type") == "text/html"
    root_html = root.wfile.getvalue().decode("utf-8")
    assert "Generation Placeholder" in root_html
    assert "API Builder" in root_html
    assert 'id="generation-package-first_name"' in root_html
    assert 'id="generation-syllables-first_name"' in root_html
    assert 'id="generation-send-first_name"' in root_html
    assert 'id="generation-package-title_epithet"' in root_html
    assert 'id="generation-toggle-btn"' in root_html
    assert 'id="generation-class-card-section"' in root_html
    assert "generation-class-grid-collapsed" in root_html
    assert 'id="api-builder-queue"' in root_html
    assert 'id="api-builder-combined"' in root_html
    assert 'id="api-builder-preview"' in root_html

    favicon = _HandlerHarness(path="/favicon.ico", db_path=db_path)
    favicon.do_GET()
    assert favicon.response_status == 204

    unknown = _HandlerHarness(path="/does-not-exist", db_path=db_path)
    unknown.do_GET()
    assert unknown.error_status == 404


def test_get_database_routes_validation_and_error_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Database and generation option GET handlers should expose runtime errors."""
    db_path = tmp_path / "db.sqlite3"

    # Validation error for package_id.
    missing_package = _HandlerHarness(path="/api/database/package-tables", db_path=db_path)
    missing_package.do_GET()
    assert missing_package.response_status == 400
    assert "package_id" in missing_package.json_body()["error"]

    missing_selection_stats_class = _HandlerHarness(
        path="/api/generation/selection-stats?package_id=1&syllable_key=2syl",
        db_path=db_path,
    )
    missing_selection_stats_class.do_GET()
    assert missing_selection_stats_class.response_status == 400
    assert "class_key" in missing_selection_stats_class.json_body()["error"]

    missing_selection_stats_syllable = _HandlerHarness(
        path="/api/generation/selection-stats?package_id=1&class_key=first_name",
        db_path=db_path,
    )
    missing_selection_stats_syllable.do_GET()
    assert missing_selection_stats_syllable.response_status == 400
    assert "syllable_key" in missing_selection_stats_syllable.json_body()["error"]

    unknown_class = _HandlerHarness(
        path="/api/generation/package-syllables?class_key=bad_key&package_id=1",
        db_path=db_path,
    )
    unknown_class.do_GET()
    assert unknown_class.response_status == 400
    assert "Unsupported generation class_key" in unknown_class.json_body()["error"]

    # Validation error for table_id.
    missing_table = _HandlerHarness(path="/api/database/table-rows", db_path=db_path)
    missing_table.do_GET()
    assert missing_table.response_status == 400
    assert "table_id" in missing_table.json_body()["error"]

    # Validation error for class_key/package_id in syllable options route.
    missing_class = _HandlerHarness(
        path="/api/generation/package-syllables?package_id=1",
        db_path=db_path,
    )
    missing_class.do_GET()
    assert missing_class.response_status == 400
    assert "class_key" in missing_class.json_body()["error"]

    missing_package = _HandlerHarness(
        path="/api/generation/package-syllables?class_key=first_name",
        db_path=db_path,
    )
    missing_package.do_GET()
    assert missing_package.response_status == 400
    assert "package_id" in missing_package.json_body()["error"]

    def boom(_db_path: Path) -> Any:
        raise RuntimeError("db down")

    monkeypatch.setattr(server_module, "_connect_database", boom)

    packages = _HandlerHarness(path="/api/database/packages", db_path=db_path)
    packages.do_GET()
    assert packages.response_status == 500
    assert "Failed to list packages" in packages.json_body()["error"]

    package_tables = _HandlerHarness(
        path="/api/database/package-tables?package_id=1",
        db_path=db_path,
    )
    package_tables.do_GET()
    assert package_tables.response_status == 500
    assert "Failed to list package tables" in package_tables.json_body()["error"]

    table_rows = _HandlerHarness(
        path="/api/database/table-rows?table_id=1&offset=0&limit=20",
        db_path=db_path,
    )
    table_rows.do_GET()
    assert table_rows.response_status == 500
    assert "Failed to load table rows" in table_rows.json_body()["error"]

    generation_options = _HandlerHarness(path="/api/generation/package-options", db_path=db_path)
    generation_options.do_GET()
    assert generation_options.response_status == 500
    assert "Failed to list generation package options" in generation_options.json_body()["error"]

    generation_syllables = _HandlerHarness(
        path="/api/generation/package-syllables?class_key=first_name&package_id=1",
        db_path=db_path,
    )
    generation_syllables.do_GET()
    assert generation_syllables.response_status == 500
    assert "Failed to list generation syllable options" in generation_syllables.json_body()["error"]

    selection_stats = _HandlerHarness(
        path="/api/generation/selection-stats?class_key=first_name&package_id=1&syllable_key=2syl",
        db_path=db_path,
    )
    selection_stats.do_GET()
    assert selection_stats.response_status == 500
    assert "Failed to compute generation selection stats" in selection_stats.json_body()["error"]


def test_table_rows_not_found_returns_404(tmp_path: Path) -> None:
    """Row endpoint should return 404 when the table id does not exist."""
    db_path = tmp_path / "db.sqlite3"
    with _connect_database(db_path) as conn:
        _initialize_schema(conn)

    missing = _HandlerHarness(path="/api/database/table-rows?table_id=999", db_path=db_path)
    missing.do_GET()
    assert missing.response_status == 404
    assert "not found" in missing.json_body()["error"]


def test_post_generate_and_unknown_routes(tmp_path: Path) -> None:
    """POST dispatcher should route generation and unknown paths correctly."""
    db_path = tmp_path / "db.sqlite3"

    gen = _HandlerHarness(
        path="/api/generate",
        db_path=db_path,
        body={"name_class": "first_name", "count": 3},
    )
    gen.do_POST()
    payload = gen.json_body()
    assert gen.response_status == 200
    assert len(payload["names"]) == 3

    unknown = _HandlerHarness(path="/api/nope", db_path=db_path, body={})
    unknown.do_POST()
    assert unknown.error_status == 404


def test_handle_import_validation_and_exception_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Import route should cover payload validation and failure branches."""
    db_path = tmp_path / "db.sqlite3"

    # Missing required fields.
    missing = _HandlerHarness(path="/api/import", db_path=db_path, body={})
    missing.do_POST()
    assert missing.response_status == 400
    assert "required" in missing.json_body()["error"]

    # Non-existing file paths should return 400.
    missing_files = _HandlerHarness(
        path="/api/import",
        db_path=db_path,
        body={
            "metadata_json_path": str(tmp_path / "missing.json"),
            "package_zip_path": str(tmp_path / "missing.zip"),
        },
    )
    missing_files.do_POST()
    assert missing_files.response_status == 400

    metadata_path, zip_path = _build_sample_package_pair(tmp_path)

    def fail_import(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("unexpected crash")

    monkeypatch.setattr(server_module, "_import_package_pair", fail_import)
    crashing = _HandlerHarness(
        path="/api/import",
        db_path=db_path,
        body={
            "metadata_json_path": str(metadata_path),
            "package_zip_path": str(zip_path),
        },
    )
    crashing.do_POST()
    assert crashing.response_status == 500
    assert "Import failed" in crashing.json_body()["error"]


def test_handle_generation_validation_paths(tmp_path: Path) -> None:
    """Generation route should reject invalid body and non-integer count values."""
    db_path = tmp_path / "db.sqlite3"

    empty = _HandlerHarness(path="/api/generate", db_path=db_path)
    empty.do_POST()
    assert empty.response_status == 400

    invalid_count = _HandlerHarness(
        path="/api/generate",
        db_path=db_path,
        body={"name_class": "last_name", "count": "abc"},
    )
    invalid_count.do_POST()
    assert invalid_count.response_status == 400
    assert "must be an integer" in invalid_count.json_body()["error"]


def test_import_package_pair_other_error_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Importer helper should cover missing inputs, bad zip, and rollback branch."""
    db_path = tmp_path / "db.sqlite3"
    metadata_path, zip_path = _build_sample_package_pair(tmp_path)

    with _connect_database(db_path) as conn:
        _initialize_schema(conn)

        with pytest.raises(FileNotFoundError, match="Metadata JSON does not exist"):
            _import_package_pair(
                conn,
                metadata_path=tmp_path / "missing-metadata.json",
                zip_path=zip_path,
            )

        with pytest.raises(FileNotFoundError, match="Package ZIP does not exist"):
            _import_package_pair(
                conn,
                metadata_path=metadata_path,
                zip_path=tmp_path / "missing.zip",
            )

        bad_zip = tmp_path / "bad.zip"
        bad_zip.write_text("not a zip", encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid ZIP file"):
            _import_package_pair(conn, metadata_path=metadata_path, zip_path=bad_zip)

        def fail_rows(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("read fail")

        monkeypatch.setattr(server_module, "_read_txt_rows", fail_rows)
        with pytest.raises(RuntimeError, match="read fail"):
            _import_package_pair(conn, metadata_path=metadata_path, zip_path=zip_path)


def test_import_with_optional_files_included_missing(tmp_path: Path) -> None:
    """Importer should accept metadata that omits ``files_included`` entirely."""
    metadata_path = tmp_path / "meta.json"
    zip_path = tmp_path / "pkg.zip"
    metadata_path.write_text(json.dumps({"common_name": "No List"}), encoding="utf-8")
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("selections/nltk_first_name_2syl.txt", "a\nb\n")

    with _connect_database(tmp_path / "db.sqlite3") as conn:
        _initialize_schema(conn)
        result = _import_package_pair(conn, metadata_path=metadata_path, zip_path=zip_path)
    assert result["tables"]


def test_generation_class_mapping_from_source_txt_names() -> None:
    """Source txt filename stems should map to expected generation class keys."""
    assert _map_source_txt_name_to_generation_class("nltk_first_name_2syl.txt") == "first_name"
    assert _map_source_txt_name_to_generation_class("nltk_last_name_all.txt") == "last_name"
    assert _map_source_txt_name_to_generation_class("nltk_place_name_all.txt") == "place_name"
    assert _map_source_txt_name_to_generation_class("nltk_location_name_all.txt") == "location_name"
    assert _map_source_txt_name_to_generation_class("nltk_object_item_all.txt") == "object_item"
    assert _map_source_txt_name_to_generation_class("nltk_organisation_all.txt") == "organisation"
    assert _map_source_txt_name_to_generation_class("nltk_title_epithet_all.txt") == "title_epithet"
    assert _map_source_txt_name_to_generation_class("nltk_unknown_domain.txt") is None


def test_extract_syllable_option_from_source_txt_names() -> None:
    """Syllable mode parser should normalize numeric and all-file naming patterns."""
    assert _extract_syllable_option_from_source_txt_name("nltk_first_name_2syl.txt") == "2syl"
    assert _extract_syllable_option_from_source_txt_name("nltk_first_name_3syl.txt") == "3syl"
    assert _extract_syllable_option_from_source_txt_name("nltk_first_name_all.txt") == "all"
    assert _extract_syllable_option_from_source_txt_name("nltk_first_name_sample.txt") is None


def test_list_generation_package_options_grouped_by_class(tmp_path: Path) -> None:
    """Generation options helper should return per-class package dropdown entries."""
    metadata_path, zip_path = _build_sample_package_pair(tmp_path)
    db_path = tmp_path / "webapp.sqlite3"

    with _connect_database(db_path) as conn:
        _initialize_schema(conn)
        _import_package_pair(conn, metadata_path=metadata_path, zip_path=zip_path)
        grouped = _list_generation_package_options(conn)

    grouped_map = {entry["key"]: entry["packages"] for entry in grouped}
    assert grouped_map["first_name"]
    assert grouped_map["last_name"]
    assert grouped_map["place_name"] == []
    assert grouped_map["location_name"] == []
    assert grouped_map["object_item"] == []
    assert grouped_map["organisation"] == []
    assert grouped_map["title_epithet"] == []


def test_list_generation_syllable_options_for_package_class(tmp_path: Path) -> None:
    """Per-package syllable options should be deduplicated and sorted for one class."""
    db_path = tmp_path / "db.sqlite3"
    with _connect_database(db_path) as conn:
        _initialize_schema(conn)
        imported = conn.execute(
            """
            INSERT INTO imported_packages (
                package_name,
                imported_at,
                metadata_json_path,
                package_zip_path
            ) VALUES (?, ?, ?, ?)
            """,
            ("Custom Package", "2026-02-07T00:00:00+00:00", "/tmp/meta.json", "/tmp/pkg.zip"),
        )
        if imported.lastrowid is None:
            raise AssertionError("Expected sqlite row id for imported package insert.")
        package_id = int(imported.lastrowid)
        conn.executemany(
            """
            INSERT INTO package_tables (package_id, source_txt_name, table_name, row_count)
            VALUES (?, ?, ?, ?)
            """,
            [
                (package_id, "nltk_first_name_4syl.txt", "t1", 10),
                (package_id, "nltk_first_name_2syl.txt", "t2", 10),
                (package_id, "nltk_first_name_all.txt", "t3", 10),
                (package_id, "nltk_last_name_3syl.txt", "t4", 10),
                (package_id, "nltk_first_name_2syl_alt.txt", "t5", 10),
            ],
        )
        conn.commit()

        first_name_options = _list_generation_syllable_options(
            conn, class_key="first_name", package_id=package_id
        )
        last_name_options = _list_generation_syllable_options(
            conn, class_key="last_name", package_id=package_id
        )

    assert first_name_options == [
        {"key": "2syl", "label": "2 syllables"},
        {"key": "4syl", "label": "4 syllables"},
        {"key": "all", "label": "All syllables"},
    ]
    assert last_name_options == [{"key": "3syl", "label": "3 syllables"}]


def test_list_generation_syllable_options_rejects_unknown_class(tmp_path: Path) -> None:
    """Unknown class keys should fail with ``ValueError``."""
    with _connect_database(tmp_path / "db.sqlite3") as conn:
        _initialize_schema(conn)
        with pytest.raises(ValueError, match="Unsupported generation class_key"):
            _list_generation_syllable_options(conn, class_key="not_real", package_id=1)


def test_get_generation_selection_stats_counts_rows_and_uniques(tmp_path: Path) -> None:
    """Selection stats should report row totals and deduped values per filter."""
    with _connect_database(tmp_path / "db.sqlite3") as conn:
        _initialize_schema(conn)
        imported = conn.execute(
            """
            INSERT INTO imported_packages (
                package_name,
                imported_at,
                metadata_json_path,
                package_zip_path
            ) VALUES (?, ?, ?, ?)
            """,
            ("Stats Package", "2026-02-07T00:00:00+00:00", "/tmp/meta.json", "/tmp/pkg.zip"),
        )
        if imported.lastrowid is None:
            raise AssertionError("Expected sqlite row id for imported package insert.")
        package_id = int(imported.lastrowid)

        conn.executemany(
            """
            INSERT INTO package_tables (package_id, source_txt_name, table_name, row_count)
            VALUES (?, ?, ?, ?)
            """,
            [
                (package_id, "nltk_first_name_2syl.txt", "stats_t1", 2),
                (package_id, "nltk_first_name_2syl_alt.txt", "stats_t2", 2),
                (package_id, "nltk_first_name_3syl.txt", "stats_t3", 1),
            ],
        )
        conn.executescript("""
            CREATE TABLE stats_t1 (id INTEGER PRIMARY KEY AUTOINCREMENT, line_number INTEGER, value TEXT);
            CREATE TABLE stats_t2 (id INTEGER PRIMARY KEY AUTOINCREMENT, line_number INTEGER, value TEXT);
            CREATE TABLE stats_t3 (id INTEGER PRIMARY KEY AUTOINCREMENT, line_number INTEGER, value TEXT);
        """)
        conn.executemany(
            "INSERT INTO stats_t1 (line_number, value) VALUES (?, ?)",
            [(1, "alfa"), (2, "beta")],
        )
        conn.executemany(
            "INSERT INTO stats_t2 (line_number, value) VALUES (?, ?)",
            [(1, "beta"), (2, "gamma")],
        )
        conn.executemany(
            "INSERT INTO stats_t3 (line_number, value) VALUES (?, ?)",
            [(1, "delta")],
        )
        conn.commit()

        stats_2syl = _get_generation_selection_stats(
            conn,
            class_key="first_name",
            package_id=package_id,
            syllable_key="2syl",
        )
        stats_3syl = _get_generation_selection_stats(
            conn,
            class_key="first_name",
            package_id=package_id,
            syllable_key="3syl",
        )

    assert stats_2syl == {"max_items": 4, "max_unique_combinations": 3}
    assert stats_3syl == {"max_items": 1, "max_unique_combinations": 1}


def test_get_generation_selection_stats_rejects_invalid_syllable(tmp_path: Path) -> None:
    """Selection stats helper should reject unsupported syllable mode keys."""
    with _connect_database(tmp_path / "db.sqlite3") as conn:
        _initialize_schema(conn)
        with pytest.raises(ValueError, match="Unsupported generation syllable_key"):
            _get_generation_selection_stats(
                conn,
                class_key="first_name",
                package_id=1,
                syllable_key="banana",
            )


def test_metadata_and_txt_helpers_error_paths(tmp_path: Path) -> None:
    """Metadata/txt helper functions should raise on invalid structures and bytes."""
    not_object = tmp_path / "metadata.json"
    not_object.write_text(json.dumps(["bad"]), encoding="utf-8")
    with pytest.raises(ValueError, match="root must be an object"):
        _load_metadata_json(not_object)

    archive_path = tmp_path / "archive.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("valid.txt", "alpha\nbeta\n")
        archive.writestr("bad.txt", b"\xff\xfe")

    with zipfile.ZipFile(archive_path, "r") as archive:
        with pytest.raises(ValueError, match="missing from zip"):
            _read_txt_rows(archive, "missing.txt")
        with pytest.raises(ValueError, match="not valid UTF-8"):
            _read_txt_rows(archive, "bad.txt")


def test_insert_rows_empty_and_get_missing_meta(tmp_path: Path) -> None:
    """Empty row inserts should no-op and table metadata should return None for unknown ids."""
    with _connect_database(tmp_path / "db.sqlite3") as conn:
        _initialize_schema(conn)
        _insert_text_rows(conn, "arbitrary", [])
        assert _get_package_table(conn, 12345) is None


def test_integer_parsing_helpers_cover_default_and_bounds() -> None:
    """Integer parsing helpers should enforce required/default and bound logic."""
    assert _parse_optional_int({}, "offset", default=7, minimum=0) == 7

    with pytest.raises(ValueError, match="required query parameter"):
        _parse_required_int({}, "table_id", minimum=1)
    with pytest.raises(ValueError, match="must be an integer"):
        _coerce_int("x", key="limit")
    with pytest.raises(ValueError, match=">= 1"):
        _coerce_int("0", key="table_id", minimum=1)
    with pytest.raises(ValueError, match="<= 5"):
        _coerce_int("6", key="limit", maximum=5)


def test_port_discovery_and_resolution_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """Port helpers should cover available, unavailable, and no-free-port branches."""

    class FakeSocketOK:
        """Socket test double that allows bind calls."""

        def __enter__(self) -> "FakeSocketOK":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def setsockopt(self, *args: Any) -> None:
            return None

        def bind(self, *args: Any) -> None:
            return None

    class FakeSocketFail(FakeSocketOK):
        """Socket test double that fails bind calls."""

        def bind(self, *args: Any) -> None:
            raise OSError("in use")

    monkeypatch.setattr(server_module.socket, "socket", lambda *args: FakeSocketOK())
    assert _port_is_available("127.0.0.1", 8123) is True

    monkeypatch.setattr(server_module.socket, "socket", lambda *args: FakeSocketFail())
    assert _port_is_available("127.0.0.1", 8123) is False

    availability = {8000: False, 8001: True}
    monkeypatch.setattr(
        server_module,
        "_port_is_available",
        lambda _host, port: availability.get(port, False),
    )
    assert find_available_port(host="127.0.0.1", start=8000, end=8001) == 8001
    assert resolve_server_port("127.0.0.1", 8001) == 8001

    with pytest.raises(OSError, match="already in use"):
        resolve_server_port("127.0.0.1", 8000)

    with pytest.raises(OSError, match="No free ports"):
        find_available_port(host="127.0.0.1", start=8100, end=8101)


def test_server_start_run_and_main_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Server factory/runner/main entrypoints should cover success and error paths."""

    class DummyHTTPServer:
        """HTTPServer test double that records constructor args."""

        def __init__(self, address: tuple[str, int], handler_class: type[Any]) -> None:
            self.address = address
            self.handler_class = handler_class

    monkeypatch.setattr(server_module, "HTTPServer", DummyHTTPServer)
    monkeypatch.setattr(server_module, "resolve_server_port", lambda host, port: 8123)

    settings = ServerSettings(
        host="127.0.0.1",
        port=None,
        db_path=tmp_path / "db.sqlite3",
        verbose=False,
    )
    http_server, resolved_port = start_http_server(settings)
    assert isinstance(http_server, DummyHTTPServer)
    assert resolved_port == 8123

    class DummyRuntimeServer:
        """Runtime server double with deterministic shutdown behavior."""

        def __init__(self, *, raise_interrupt: bool) -> None:
            self.raise_interrupt = raise_interrupt
            self.closed = False

        def serve_forever(self) -> None:
            if self.raise_interrupt:
                raise KeyboardInterrupt()

        def server_close(self) -> None:
            self.closed = True

    runtime = DummyRuntimeServer(raise_interrupt=True)
    monkeypatch.setattr(server_module, "start_http_server", lambda _settings: (runtime, 8124))
    assert run_server(ServerSettings(verbose=True)) == 0
    assert runtime.closed is True
    assert "Serving Pipeworks Name Generator UI" in capsys.readouterr().out

    parser = create_argument_parser()
    args = parser.parse_args(["--host", "0.0.0.0", "--port", "8999", "--quiet"])
    assert args.host == "0.0.0.0"
    assert args.port == 8999
    assert args.quiet is True

    parsed = parse_arguments(["--config", "server.ini"])
    assert str(parsed.config).endswith("server.ini")

    ini = tmp_path / "server.ini"
    ini.write_text("[server]\nhost=127.0.0.1\nport=8011\nverbose=true\n", encoding="utf-8")
    namespace = type(
        "Args",
        (),
        {"config": str(ini), "host": "0.0.0.0", "port": 8012, "quiet": True},
    )()
    built = build_settings_from_args(namespace)
    assert built.host == "0.0.0.0"
    assert built.port == 8012
    assert built.verbose is False

    monkeypatch.setattr(server_module, "parse_arguments", lambda _argv=None: namespace)
    monkeypatch.setattr(server_module, "build_settings_from_args", lambda _args: settings)
    monkeypatch.setattr(server_module, "run_server", lambda _settings: 0)
    assert main(["--config", str(ini)]) == 0

    def boom_parse(_argv: Any = None) -> Any:
        raise RuntimeError("parse failed")

    monkeypatch.setattr(server_module, "parse_arguments", boom_parse)
    assert main([]) == 1
    assert "Error: parse failed" in capsys.readouterr().out
