"""Runtime bootstrap helpers for the webapp server process.

These helpers isolate bind-port resolution and HTTP server lifecycle behavior so
``server.py`` can focus on request handling and high-level orchestration.
"""

from __future__ import annotations

import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, TypeVar, cast

from pipeworks_name_generation.webapp.config import ServerSettings

HandlerT = TypeVar("HandlerT", bound=BaseHTTPRequestHandler)


def port_is_available(
    host: str,
    port: int,
    *,
    socket_factory: Callable[..., Any] = socket.socket,
) -> bool:
    """Return ``True`` when a host/port can be bound by this process."""
    with socket_factory(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def find_available_port(
    host: str = "127.0.0.1",
    start: int = 8000,
    end: int = 8999,
    *,
    is_available: Callable[[str, int], bool] = port_is_available,
) -> int:
    """Find the first available TCP port in ``start..end``.

    Raises:
        OSError: When no free port is available in the given range.
    """
    for port in range(start, end + 1):
        if is_available(host, port):
            return port
    raise OSError(f"No free ports available in range {start}-{end}.")


def resolve_server_port(
    host: str,
    configured_port: int | None,
    *,
    is_available: Callable[[str, int], bool] = port_is_available,
    find_port: Callable[[str, int, int], int] | None = None,
) -> int:
    """Resolve runtime port using manual config or auto-discovery.

    Args:
        host: Bind host for availability checks.
        configured_port: Optional explicit port from config/CLI.
        is_available: Port availability predicate.
        find_port: Optional custom free-port finder.

    Returns:
        Concrete port to bind.

    Raises:
        OSError: If a configured port is unavailable or no auto port is free.
    """
    finder = find_port or (lambda h, s, e: find_available_port(h, s, e, is_available=is_available))
    if configured_port is not None:
        if not is_available(host, configured_port):
            raise OSError(f"Configured port {configured_port} is already in use.")
        return configured_port
    return finder(host, 8000, 8999)


def create_bound_handler_class(
    handler_base: type[HandlerT],
    *,
    verbose: bool,
    db_path: Path,
    schema_ready: bool = False,
) -> type[HandlerT]:
    """Create handler class bound to runtime verbosity and DB path."""
    bound_handler = cast(type[HandlerT], type("BoundHandler", (handler_base,), {}))

    setattr(bound_handler, "verbose", verbose)
    setattr(bound_handler, "db_path", db_path)
    setattr(bound_handler, "schema_ready", schema_ready)
    setattr(
        bound_handler,
        "schema_initialized_paths",
        {str(db_path.expanduser().resolve())} if schema_ready else set(),
    )
    return bound_handler


def start_http_server(
    settings: ServerSettings,
    *,
    resolve_port: Callable[[str, int | None], int],
    create_handler: Callable[[bool, Path], type[BaseHTTPRequestHandler]],
    initialize_storage: Callable[[Path], None] | None = None,
    http_server_cls: Callable[[tuple[str, int], type[BaseHTTPRequestHandler]], Any] | None = None,
) -> tuple[Any, int]:
    """Create a configured ``HTTPServer`` instance.

    Args:
        settings: Effective runtime settings.
        resolve_port: Host/port resolution callback.
        create_handler: Handler factory bound to runtime verbosity and DB path.
        initialize_storage: Optional one-time startup hook for DB/schema prep.
        http_server_cls: Concrete HTTP server class.
    """
    if initialize_storage is not None:
        initialize_storage(settings.db_path)

    port = resolve_port(settings.host, settings.port)
    handler_class = create_handler(settings.verbose, settings.db_path)
    server_factory = http_server_cls or HTTPServer
    server = server_factory((settings.host, port), handler_class)
    return server, port


def run_server(
    settings: ServerSettings,
    *,
    start_server: Callable[[ServerSettings], tuple[Any, int]],
    printer: Callable[[str], None] = print,
) -> int:
    """Run the server until interrupted.

    Args:
        settings: Effective runtime settings from config and CLI overrides.
        start_server: Factory that returns ``(server, port)``.
        printer: Output callable used for startup/shutdown messages.

    Returns:
        Process-style exit code (``0`` on normal shutdown).
    """
    server, port = start_server(settings)

    if settings.verbose:
        printer(f"Serving Pipeworks Name Generator UI at http://{settings.host}:{port}")
        printer(f"SQLite DB path: {settings.db_path}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        if settings.verbose:
            printer("\\nStopping server...")
    finally:
        server.server_close()

    return 0


__all__ = [
    "port_is_available",
    "find_available_port",
    "resolve_server_port",
    "create_bound_handler_class",
    "start_http_server",
    "run_server",
]
