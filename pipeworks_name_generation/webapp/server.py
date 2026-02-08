"""Simple web server with Import, Generation, and Database View tabs.

This version stores package imports in SQLite and creates one SQLite data table
for each imported ``*.txt`` selection file. JSON files are intentionally ignored
for now, per current requirements.
"""

from __future__ import annotations

import argparse
import socket
from http.server import HTTPServer
from pathlib import Path
from typing import Sequence

from pipeworks_name_generation.webapp import cli as webapp_cli
from pipeworks_name_generation.webapp import runtime as webapp_runtime
from pipeworks_name_generation.webapp.config import ServerSettings
from pipeworks_name_generation.webapp.db import (
    connect_database as _connect_database,
)
from pipeworks_name_generation.webapp.db import (
    initialize_schema as _initialize_schema,
)
from pipeworks_name_generation.webapp.handler import WebAppHandler


def _port_is_available(host: str, port: int) -> bool:
    """Return ``True`` when a host/port can be bound by this process."""
    return webapp_runtime.port_is_available(host, port, socket_factory=socket.socket)


def find_available_port(host: str = "127.0.0.1", start: int = 8000, end: int = 8999) -> int:
    """Find the first available TCP port in ``start..end``.

    Raises:
        OSError: When no free port is available in the given range.
    """
    return webapp_runtime.find_available_port(
        host=host, start=start, end=end, is_available=_port_is_available
    )


def resolve_server_port(host: str, configured_port: int | None) -> int:
    """Resolve runtime port using manual config or auto-discovery.

    Args:
        host: Bind host for availability checks.
        configured_port: Optional explicit port from config/CLI.

    Returns:
        Concrete port to bind.

    Raises:
        OSError: If a configured port is unavailable or no auto port is free.
    """
    return webapp_runtime.resolve_server_port(
        host=host,
        configured_port=configured_port,
        is_available=_port_is_available,
        find_port=find_available_port,
    )


def create_handler_class(verbose: bool, db_path: Path) -> type[WebAppHandler]:
    """Create handler class bound to runtime verbosity and DB path.

    The runtime bootstrap initializes schema before creating the handler class,
    so ``schema_ready`` is set to ``True`` to skip per-request schema checks on
    the hot path.
    """
    return webapp_runtime.create_bound_handler_class(
        WebAppHandler,
        verbose=verbose,
        db_path=db_path,
        schema_ready=True,
    )


def _initialize_database_storage(db_path: Path) -> None:
    """Ensure the SQLite file and schema exist before serving requests."""
    with _connect_database(db_path) as conn:
        _initialize_schema(conn)


def start_http_server(settings: ServerSettings) -> tuple[HTTPServer, int]:
    """Create a configured ``HTTPServer`` instance."""
    return webapp_runtime.start_http_server(
        settings,
        resolve_port=resolve_server_port,
        create_handler=create_handler_class,
        initialize_storage=_initialize_database_storage,
        http_server_cls=HTTPServer,
    )


def run_server(settings: ServerSettings) -> int:
    """Run the server until interrupted.

    Args:
        settings: Effective runtime settings from config and CLI overrides.

    Returns:
        Process-style exit code (``0`` on normal shutdown).
    """
    return webapp_runtime.run_server(
        settings,
        start_server=start_http_server,
        printer=print,
    )


def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser for this server."""
    return webapp_cli.create_argument_parser()


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    return webapp_cli.parse_arguments(argv)


def build_settings_from_args(args: argparse.Namespace) -> ServerSettings:
    """Build effective settings from INI config and CLI overrides."""
    return webapp_cli.build_settings_from_args(args)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for running this server."""
    return webapp_cli.main(
        argv,
        parse_args=parse_arguments,
        build_settings=build_settings_from_args,
        run=run_server,
        printer=print,
    )


if __name__ == "__main__":
    raise SystemExit(main())
