"""Command-line parsing and settings composition for the webapp server."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable, Sequence

from pipeworks_name_generation.webapp.config import (
    ServerSettings,
    apply_runtime_overrides,
    load_server_settings,
)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser for this server."""
    parser = argparse.ArgumentParser(
        prog="pipeworks-name-webapp",
        description="Run the simple Pipeworks Name Generator web server.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("server.ini"),
        help="Path to INI config file (default: server.ini)",
    )
    parser.add_argument("--host", type=str, default=None, help="Override server host.")
    parser.add_argument("--port", type=int, default=None, help="Override server port.")
    parser.add_argument(
        "--favorites-db",
        type=Path,
        default=None,
        help="Override favorites SQLite database path.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable verbose startup/request logs.",
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Serve API routes only (no UI or static assets).",
    )
    return parser


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = create_argument_parser()
    return parser.parse_args(list(argv) if argv is not None else None)


def build_settings_from_args(args: argparse.Namespace) -> ServerSettings:
    """Build effective settings from INI config and CLI overrides."""
    config_path = args.config if isinstance(args.config, Path) else Path(args.config)
    loaded = load_server_settings(config_path)
    verbose_override = False if args.quiet else None
    serve_ui_override = False if args.api_only else None
    return apply_runtime_overrides(
        loaded,
        host=args.host,
        port=args.port,
        db_path=None,
        favorites_db_path=args.favorites_db,
        verbose=verbose_override,
        serve_ui=serve_ui_override,
    )


def main(
    argv: Sequence[str] | None,
    *,
    parse_args: Callable[[Sequence[str] | None], argparse.Namespace],
    build_settings: Callable[[argparse.Namespace], ServerSettings],
    run: Callable[[ServerSettings], int],
    printer: Callable[[str], None] = print,
) -> int:
    """CLI entrypoint wrapper for running the server with dependency injection."""
    try:
        args = parse_args(argv)
        settings = build_settings(args)
        return run(settings)
    except Exception as exc:
        printer(f"Error: {exc}")
        return 1


__all__ = [
    "create_argument_parser",
    "parse_arguments",
    "build_settings_from_args",
    "main",
]
