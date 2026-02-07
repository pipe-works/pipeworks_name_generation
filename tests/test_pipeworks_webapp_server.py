"""Unit tests for webapp server routing and port resolution."""

from __future__ import annotations

import io
import json
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pipeworks_name_generation.webapp.config import ServerSettings
from pipeworks_name_generation.webapp.importer import ImportResult
from pipeworks_name_generation.webapp.server import (
    HTML_TEMPLATE,
    WebAppHandler,
    find_available_port,
    resolve_server_port,
    start_http_server,
)


def _build_handler(path: str) -> MagicMock:
    """Build a mocked handler instance with bound methods for direct route testing."""
    handler = MagicMock(spec=WebAppHandler)
    handler.path = path
    handler.headers = {}
    handler.rfile = io.BytesIO()
    handler.wfile = io.BytesIO()
    handler.db_path = Path("/tmp/test.sqlite3")
    handler.verbose = False

    handler._send_text = MagicMock()
    handler._send_json = MagicMock()
    handler.send_error = MagicMock()

    handler.do_GET = WebAppHandler.do_GET.__get__(handler, WebAppHandler)
    handler.do_POST = WebAppHandler.do_POST.__get__(handler, WebAppHandler)
    return handler


def test_find_available_port_returns_first_free_port() -> None:
    """Port finder should return the first bindable port in range."""
    with patch(
        "pipeworks_name_generation.webapp.server._port_is_available",
        side_effect=[False, True],
    ):
        assert find_available_port(start=8000, end=8001) == 8001


def test_find_available_port_raises_when_exhausted() -> None:
    """Port finder should raise when all tested ports are occupied."""
    with patch("pipeworks_name_generation.webapp.server._port_is_available", return_value=False):
        with pytest.raises(OSError, match="No free ports available"):
            find_available_port(start=8000, end=8001)


def test_resolve_server_port_manual_and_auto_modes() -> None:
    """Manual configured ports should be validated; auto mode should call scanner."""
    with patch("pipeworks_name_generation.webapp.server._port_is_available", return_value=True):
        assert resolve_server_port("127.0.0.1", 8123) == 8123

    with patch("pipeworks_name_generation.webapp.server._port_is_available", return_value=False):
        with pytest.raises(OSError, match="already in use"):
            resolve_server_port("127.0.0.1", 8123)

    with patch("pipeworks_name_generation.webapp.server.find_available_port", return_value=8010):
        assert resolve_server_port("127.0.0.1", None) == 8010


def test_start_http_server_initializes_schema_and_constructs_server() -> None:
    """Server startup should initialize DB schema and build HTTPServer with resolved port."""
    settings = ServerSettings(
        host="127.0.0.1", port=None, db_path=Path("db.sqlite3"), verbose=False
    )

    fake_conn = SimpleNamespace()
    with (
        patch(
            "pipeworks_name_generation.webapp.server.connect_database",
            return_value=nullcontext(fake_conn),
        ) as connect_mock,
        patch("pipeworks_name_generation.webapp.server.initialize_schema") as init_mock,
        patch("pipeworks_name_generation.webapp.server.resolve_server_port", return_value=8099),
        patch("pipeworks_name_generation.webapp.server.HTTPServer") as http_server_mock,
    ):
        server, port = start_http_server(settings)

    connect_mock.assert_called_once_with(settings.db_path)
    init_mock.assert_called_once_with(fake_conn)
    http_server_mock.assert_called_once()
    assert server == http_server_mock.return_value
    assert port == 8099


def test_do_get_root_and_health_routes() -> None:
    """GET / and GET /api/health should dispatch expected responses."""
    root_handler = _build_handler("/")
    root_handler.do_GET()
    root_handler._send_text.assert_called_once_with(HTML_TEMPLATE, content_type="text/html")

    health_handler = _build_handler("/api/health")
    health_handler.do_GET()
    health_handler._send_json.assert_called_once_with({"ok": True})


def test_do_get_imports_route_lists_rows() -> None:
    """GET /api/imports should return list payload from DB layer."""
    handler = _build_handler("/api/imports")
    fake_conn = SimpleNamespace()

    with (
        patch(
            "pipeworks_name_generation.webapp.server.connect_database",
            return_value=nullcontext(fake_conn),
        ),
        patch("pipeworks_name_generation.webapp.server.initialize_schema") as init_mock,
        patch(
            "pipeworks_name_generation.webapp.server.list_imported_packages",
            return_value=[{"id": 1, "common_name": "demo"}],
        ) as list_mock,
    ):
        handler.do_GET()

    init_mock.assert_called_once_with(fake_conn)
    list_mock.assert_called_once_with(fake_conn)
    handler._send_json.assert_called_once_with({"imports": [{"id": 1, "common_name": "demo"}]})


def test_do_post_import_validation_errors() -> None:
    """POST /api/import should reject invalid body/payload states."""
    # Invalid JSON payload
    invalid_json = _build_handler("/api/import")
    invalid_json.headers = {"Content-Length": "9"}
    invalid_json.rfile = io.BytesIO(b"{bad json")
    invalid_json.do_POST()
    invalid_json._send_json.assert_called_once_with(
        {"error": "Request body must be valid JSON."},
        status=400,
    )

    # Missing required keys
    missing_fields = _build_handler("/api/import")
    body = json.dumps({}).encode("utf-8")
    missing_fields.headers = {"Content-Length": str(len(body))}
    missing_fields.rfile = io.BytesIO(body)
    missing_fields.do_POST()
    missing_fields._send_json.assert_called_once_with(
        {"error": "Both 'metadata_json_path' and 'package_zip_path' are required."},
        status=400,
    )


def test_do_post_import_success_path() -> None:
    """POST /api/import should call importer and return success payload."""
    handler = _build_handler("/api/import")

    body = json.dumps(
        {
            "metadata_json_path": "/tmp/meta.json",
            "package_zip_path": "/tmp/pkg.zip",
        }
    ).encode("utf-8")
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = io.BytesIO(body)

    fake_conn = SimpleNamespace()
    with (
        patch(
            "pipeworks_name_generation.webapp.server.connect_database",
            return_value=nullcontext(fake_conn),
        ),
        patch("pipeworks_name_generation.webapp.server.initialize_schema"),
        patch(
            "pipeworks_name_generation.webapp.server.import_package_pair",
            return_value=ImportResult(package_id=7, message="ok"),
        ) as import_mock,
    ):
        handler.do_POST()

    import_mock.assert_called_once()
    handler._send_json.assert_called_once_with({"success": True, "package_id": 7, "message": "ok"})
