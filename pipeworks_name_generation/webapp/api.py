"""API-only entrypoint for the Pipeworks Name Generator server.

This module reuses the shared CLI settings and runtime server, but forces
API-only routing so UI/static endpoints are not served.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from typing import Sequence

from pipeworks_name_generation.webapp import cli as webapp_cli
from pipeworks_name_generation.webapp.config import ServerSettings
from pipeworks_name_generation.webapp.server import run_server


def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser for the API-only server."""
    parser = webapp_cli.create_argument_parser()
    parser.prog = "pipeworks-name-api"
    parser.description = "Run the Pipeworks Name Generator API server."
    return parser


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the API-only server."""
    parser = create_argument_parser()
    return parser.parse_args(list(argv) if argv is not None else None)


def build_settings_from_args(args: argparse.Namespace) -> ServerSettings:
    """Build server settings and force API-only routing."""
    settings = webapp_cli.build_settings_from_args(args)
    return replace(settings, serve_ui=False)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for running the API-only server."""
    return webapp_cli.main(
        argv,
        parse_args=parse_arguments,
        build_settings=build_settings_from_args,
        run=run_server,
        printer=print,
    )


if __name__ == "__main__":
    raise SystemExit(main())
