"""Unit tests for runtime bootstrap helpers in the webapp package."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, cast

from pipeworks_name_generation.webapp.config import ServerSettings
from pipeworks_name_generation.webapp.runtime import (
    create_bound_handler_class,
    find_preferred_auto_port,
    resolve_server_port,
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
        extra_attrs={"get_routes": {"/api/health": "get_health"}},
    )
    bound_runtime = cast(Any, bound)

    assert bound_runtime.verbose is False
    assert bound_runtime.db_path == db_path
    assert bound_runtime.schema_ready is True
    assert str(db_path.resolve()) in bound_runtime.schema_initialized_paths
    assert bound_runtime.get_routes == {"/api/health": "get_health"}


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


def test_run_server_prints_api_label_when_ui_disabled() -> None:
    """Runtime loop should announce API-only mode when UI is disabled."""
    runtime = _DummyRuntimeServer(raise_interrupt=True)
    messages: list[str] = []

    result = run_server(
        ServerSettings(verbose=True, serve_ui=False),
        start_server=lambda _settings: (runtime, 8124),
        printer=messages.append,
    )

    assert result == 0
    assert runtime.closed is True
    assert any("Serving Pipeworks Name Generator API" in line for line in messages)


def test_find_preferred_auto_port_uses_primary_range_first() -> None:
    """Auto-port selection should return from the primary 8000-range when available."""
    calls: list[tuple[int, int]] = []

    def fake_find_in_range(_host: str, start: int, end: int) -> int:
        calls.append((start, end))
        if (start, end) == (8000, 8099):
            return 8005
        raise OSError("unexpected fallback call")

    selected = find_preferred_auto_port("127.0.0.1", find_in_range=fake_find_in_range)

    assert selected == 8005
    assert calls == [(8000, 8099)]


def test_find_preferred_auto_port_falls_back_after_primary_exhausted() -> None:
    """Auto-port selection should check 8100-8999 only after 8000-8099 fails."""
    calls: list[tuple[int, int]] = []

    def fake_find_in_range(_host: str, start: int, end: int) -> int:
        calls.append((start, end))
        if (start, end) == (8000, 8099):
            raise OSError("primary full")
        if (start, end) == (8100, 8999):
            return 8123
        raise OSError("unexpected range")

    selected = find_preferred_auto_port("127.0.0.1", find_in_range=fake_find_in_range)

    assert selected == 8123
    assert calls == [(8000, 8099), (8100, 8999)]


def test_resolve_server_port_falls_back_when_configured_8000_port_is_busy() -> None:
    """Configured 8000-range ports should fallback to another free auto port."""
    availability = {8000: False, 8001: True}

    def fake_is_available(_host: str, port: int) -> bool:
        return availability.get(port, False)

    def fake_find_port(host: str, start: int, end: int) -> int:
        for candidate in range(start, end + 1):
            if fake_is_available(host, candidate):
                return candidate
        raise OSError(f"No free ports available in range {start}-{end}.")

    selected = resolve_server_port(
        "127.0.0.1",
        8000,
        is_available=fake_is_available,
        find_port=fake_find_port,
    )

    assert selected == 8001


def test_resolve_server_port_raises_for_busy_out_of_range_configured_port() -> None:
    """Configured ports outside auto range should still fail when unavailable."""

    def fake_is_available(_host: str, _port: int) -> bool:
        return False

    try:
        resolve_server_port("127.0.0.1", 9500, is_available=fake_is_available)
    except OSError as exc:
        assert "Configured port 9500 is already in use." in str(exc)
    else:
        raise AssertionError("Expected OSError for unavailable out-of-range configured port.")
