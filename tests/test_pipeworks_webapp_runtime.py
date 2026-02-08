"""Unit tests for runtime bootstrap helpers in the webapp package."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, cast

from pipeworks_name_generation.webapp.config import ServerSettings
from pipeworks_name_generation.webapp.runtime import (
    create_bound_handler_class,
    run_server,
    start_http_server,
)


class _BaseHandler(BaseHTTPRequestHandler):
    """Minimal handler base for bound-class wiring tests."""


class _DummyHTTPServer:
    """Test double for HTTPServer constructor behavior."""

    def __init__(self, address: tuple[str, int], handler_class: type[Any]) -> None:
        self.address = address
        self.handler_class = handler_class


class _DummyRuntimeServer:
    """Runtime server double used for lifecycle tests."""

    def __init__(self, *, raise_interrupt: bool = False) -> None:
        self.raise_interrupt = raise_interrupt
        self.closed = False

    def serve_forever(self) -> None:
        if self.raise_interrupt:
            raise KeyboardInterrupt()

    def server_close(self) -> None:
        self.closed = True


def test_create_bound_handler_class_sets_runtime_attributes(tmp_path: Path) -> None:
    """Bound handler should carry runtime DB path and schema readiness metadata."""
    db_path = tmp_path / "name_packages.sqlite3"
    bound = create_bound_handler_class(
        _BaseHandler,
        verbose=False,
        db_path=db_path,
        schema_ready=True,
    )
    bound_runtime = cast(Any, bound)

    assert bound_runtime.verbose is False
    assert bound_runtime.db_path == db_path
    assert bound_runtime.schema_ready is True
    assert str(db_path.resolve()) in bound_runtime.schema_initialized_paths


def test_start_http_server_calls_storage_initializer(tmp_path: Path) -> None:
    """HTTP server bootstrap should initialize storage before binding address."""
    settings = ServerSettings(host="127.0.0.1", port=None, db_path=tmp_path / "db.sqlite3")
    calls: list[str] = []

    def fake_resolve_port(host: str, port: int | None) -> int:
        assert host == "127.0.0.1"
        assert port is None
        return 8123

    def fake_create_handler(verbose: bool, db_path: Path) -> type[_BaseHandler]:
        assert verbose is True
        assert db_path == settings.db_path
        return _BaseHandler

    def fake_initialize_storage(db_path: Path) -> None:
        calls.append(str(db_path))

    server, resolved_port = start_http_server(
        settings,
        resolve_port=fake_resolve_port,
        create_handler=fake_create_handler,
        initialize_storage=fake_initialize_storage,
        http_server_cls=_DummyHTTPServer,
    )

    assert isinstance(server, _DummyHTTPServer)
    assert resolved_port == 8123
    assert calls == [str(settings.db_path)]


def test_run_server_handles_interrupt_and_closes_server() -> None:
    """Runtime loop should close server and return success on interrupt."""
    runtime = _DummyRuntimeServer(raise_interrupt=True)
    messages: list[str] = []

    result = run_server(
        ServerSettings(verbose=True),
        start_server=lambda _settings: (runtime, 8124),
        printer=messages.append,
    )

    assert result == 0
    assert runtime.closed is True
    assert any("Serving Pipeworks Name Generator UI" in line for line in messages)
