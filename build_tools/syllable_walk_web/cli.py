"""Command-line interface for syllable walker web interface.

This module provides the CLI for starting the web-based syllable walker
interface that allows browsing name selections and generating walks.

Usage::

    python -m build_tools.syllable_walk_web [options]

Examples::

    # Start web interface (auto-discovers port starting at 8000)
    python -m build_tools.syllable_walk_web

    # Start on specific port
    python -m build_tools.syllable_walk_web --port 9000

    # Quiet mode (suppress startup messages)
    python -m build_tools.syllable_walk_web --quiet
"""

import argparse
import sys
from typing import List, Optional

from build_tools.syllable_walk_web.server import run_server


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and return the argument parser for syllable walker web interface.

    This function creates the ArgumentParser with all CLI options but does not
    parse arguments. This separation allows Sphinx documentation tools to
    introspect the parser and auto-generate CLI documentation.

    Returns:
        Configured ArgumentParser ready to parse command-line arguments

    Examples:
        Create parser and inspect options::

            >>> parser = create_argument_parser()
            >>> parser.prog
            'cli.py'

        Use parser to parse arguments::

            >>> parser = create_argument_parser()
            >>> args = parser.parse_args(["--port", "9000"])
            >>> args.port
            9000

    Notes:
        - This function is used by both the CLI and documentation generation
        - For normal CLI usage, use main() which calls this internally
        - Sphinx-argparse can introspect this function to generate docs
    """
    parser = argparse.ArgumentParser(
        description="Start the syllable walker web interface for browsing name selections "
        "and exploring syllable walks interactively.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
========

.. code-block:: bash

   # Start web interface (auto-discovers port starting at 8000)
   python -m build_tools.syllable_walk_web

   # Start on specific port
   python -m build_tools.syllable_walk_web --port 9000

   # Quiet mode (suppress startup messages)
   python -m build_tools.syllable_walk_web --quiet

The web interface provides:
  - Run selection dropdown to browse available pipeline runs
  - Tabbed selections browser (first_name, last_name, place_name)
  - Quick walk generator with profile presets (clerical, dialect, goblin, ritual)

For detailed documentation, see: claude/build_tools/syllable_walk.md
        """,
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        metavar="PORT",
        help=(
            "Port number for the web server. "
            "If not specified, auto-discovers an available port starting at 8000. "
            "If specified, uses that exact port (fails if unavailable). "
            "Valid range: 1024-65535 (ports below 1024 require root/admin). "
            "Default: auto-discover starting at 8000"
        ),
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help=(
            "Suppress startup messages and verbose output. Only prints "
            "the server URL and errors. Useful for scripting or when "
            "running in automated environments."
        ),
    )

    return parser


def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        args: List of argument strings to parse. If None, uses sys.argv[1:].
              This parameter is useful for testing.

    Returns:
        Parsed arguments as argparse.Namespace object

    Example:
        >>> args = parse_arguments(["--port", "9000"])
        >>> args.port
        9000
    """
    parser = create_argument_parser()
    return parser.parse_args(args)


def main() -> int:
    """
    Main entry point for syllable walker web interface CLI.

    Parses arguments and starts the web server.

    Returns:
        Exit code:
        - 0: Success (server stopped normally)
        - 1: Error (port unavailable, etc.)
        - 130: Keyboard interrupt (Ctrl+C)

    Notes:
        - Errors are printed to stderr
        - The server runs until stopped with Ctrl+C
    """
    args = parse_arguments()

    try:
        run_server(
            port=args.port,
            verbose=not args.quiet,
        )
        return 0
    except OSError as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        if args.port:
            print(f"\nPort {args.port} may already be in use.", file=sys.stderr)
            print("Try using a different port with --port option.", file=sys.stderr)
        else:
            print("\nCould not find an available port.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
