"""
Command-line interface for the Pipe-Works Build Tools web application.

Provides ``python -m build_tools.syllable_walk_web`` entry point.
"""

from __future__ import annotations

import argparse
import sys


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser for the web server.

    Returns:
        Configured ArgumentParser ready to parse command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Launch the Pipe-Works Build Tools web application. "
            "Combines Pipeline (extraction/normalization/annotation) and "
            "Walker (dual-patch syllable walking, name generation) tools "
            "in a browser-based interface."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples::

  # Launch on auto-detected port (default)
  python -m build_tools.syllable_walk_web

  # Launch on a specific port
  python -m build_tools.syllable_walk_web --port 9000

  # Launch in quiet mode (suppress HTTP request logs)
  python -m build_tools.syllable_walk_web --quiet
        """,
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=(
            "Port to serve on. If not specified, automatically finds an "
            "available port starting from 8000. Default: auto-detect"
        ),
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress HTTP request logging. Default: False",
    )

    parser.add_argument(
        "--output-base",
        type=str,
        default=None,
        help=("Base directory for pipeline run discovery. " "Default: _working/output"),
    )

    return parser


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed arguments namespace.
    """
    parser = create_argument_parser()
    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """CLI entry point.

    Returns:
        Exit code: 0 for success, 1 for error, 130 for keyboard interrupt.
    """
    parsed = parse_arguments(args)

    try:
        from pathlib import Path

        from build_tools.syllable_walk_web.server import run_server

        output_base = Path(parsed.output_base) if parsed.output_base else None

        return run_server(
            port=parsed.port,
            verbose=not parsed.quiet,
            output_base=output_base,
        )
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
