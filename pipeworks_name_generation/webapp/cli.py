"""CLI entry point for the end-user package importer web application."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeworks_name_generation.webapp.config import (
    ServerSettings,
    apply_runtime_overrides,
    load_server_settings,
)
from pipeworks_name_generation.webapp.server import run_server


def create_argument_parser() -> argparse.ArgumentParser:
    """Create parser for web app startup arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Start the Pipeworks Name Generator end-user web UI for importing "
            "metadata JSON + ZIP package pairs into SQLite."
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("server.ini"),
        help="Path to server INI file. Default: server.ini",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Optional host override (e.g. 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=(
            "Optional manual port override. If omitted, uses INI port; "
            "if neither is set, auto-selects a free port in 8000-8999."
        ),
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Optional sqlite database path override.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress startup messages.",
    )
    return parser


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = create_argument_parser()
    return parser.parse_args(args)


def build_settings_from_args(parsed: argparse.Namespace) -> ServerSettings:
    """Build effective server settings from INI + CLI overrides.

    Args:
        parsed: Parsed CLI args

    Returns:
        Effective ``ServerSettings`` object
    """
    ini_settings = load_server_settings(parsed.config)

    # ``--quiet`` only provides an explicit override when user passes it.
    verbose_override = False if parsed.quiet else None

    return apply_runtime_overrides(
        ini_settings,
        host=parsed.host,
        port=parsed.port,
        db_path=parsed.db_path,
        verbose=verbose_override,
    )


def main(args: list[str] | None = None) -> int:
    """Run the web application CLI."""
    parsed = parse_arguments(args)

    try:
        settings = build_settings_from_args(parsed)
        return run_server(settings)
    except Exception as exc:
        print(f"Error starting web app: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
