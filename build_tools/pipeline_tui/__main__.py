"""
Entry point for Pipeline Build Tools TUI.

This module allows running the TUI with:

.. code-block:: bash

    python -m build_tools.pipeline_tui
    python -m build_tools.pipeline_tui --source ~/corpora
    python -m build_tools.pipeline_tui --help
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and return the argument parser for the Pipeline TUI.

    Returns:
        Configured ArgumentParser ready to parse command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Interactive TUI for running syllable extraction pipelines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples::

  # Launch the TUI
  python -m build_tools.pipeline_tui

  # Start with a specific source directory
  python -m build_tools.pipeline_tui --source ~/corpora/english

  # Start with a specific output directory
  python -m build_tools.pipeline_tui --output _working/output
        """,
    )

    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Initial source directory for input files. Default: None (browse to select)",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Initial output directory for results. Default: _working/output",
    )

    parser.add_argument(
        "--theme",
        type=str,
        default="nord",
        choices=["nord", "dracula", "monokai", "textual-dark", "textual-light"],
        help="Color theme for the TUI. Default: nord",
    )

    return parser


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        args: List of arguments to parse, or None to use sys.argv

    Returns:
        Parsed arguments namespace
    """
    parser = create_argument_parser()
    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """
    Main entry point for the Pipeline TUI.

    Args:
        args: Command-line arguments. If None, uses sys.argv.

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    parsed = parse_arguments(args)

    try:
        # Import here to avoid circular imports and speed up --help
        from build_tools.pipeline_tui.core.app import PipelineTuiApp

        # Create and run the app
        app = PipelineTuiApp(
            source_dir=parsed.source,
            output_dir=parsed.output,
            theme=parsed.theme,
        )
        app.run()
        return 0

    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
