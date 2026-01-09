"""
Command-line interface for corpus database viewer.

Provides argument parsing and main entry point for the interactive TUI.
"""

import argparse
import sys
from pathlib import Path


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and return the argument parser for corpus_db_viewer.

    Returns
    -------
    argparse.ArgumentParser
        Configured ArgumentParser ready to parse command-line arguments
    """
    parser = argparse.ArgumentParser(
        prog="corpus_db_viewer",
        description="Interactive TUI for viewing corpus database provenance records",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Launch viewer with default database
  python -m build_tools.corpus_db_viewer

  # Specify custom database path
  python -m build_tools.corpus_db_viewer --db /path/to/database.db

  # Set custom export directory
  python -m build_tools.corpus_db_viewer --export-dir _working/my_exports/

Keyboard Shortcuts (in TUI):
  ↑/↓         Navigate rows
  ←/→         Previous/Next page
  PageUp/Dn   Jump pages
  Home/End    First/Last page

  t           Switch table (table selector)
  i           Show schema info
  e           Export current view
  r           Refresh data

  q           Quit application
  ?           Show help screen

Navigation:
  - Use arrow keys to navigate through table data
  - Press 't' to open table selector and choose a different table
  - Press 'i' to view detailed schema information
  - Press 'e' to export the current table or view to CSV/JSON

Export:
  - Exports are saved to the export directory (default: _working/exports/)
  - Files are named: <table_name>_<timestamp>.<format>
  - Both CSV and JSON formats are supported
        """,
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/raw/syllable_extractor.db"),
        dest="db_path",
        help="Path to corpus database. Default: data/raw/syllable_extractor.db",
    )

    parser.add_argument(
        "--export-dir",
        type=Path,
        default=Path("_working/exports/"),
        dest="export_dir",
        help="Directory for exported data. Default: _working/exports/",
    )

    parser.add_argument(
        "--page-size",
        type=int,
        default=50,
        dest="page_size",
        help="Number of rows per page. Default: 50",
    )

    return parser


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Parameters
    ----------
    args : list[str] | None, optional
        List of argument strings. If None, uses sys.argv[1:]
        (Supports testing)

    Returns
    -------
    argparse.Namespace
        Parsed arguments
    """
    parser = create_argument_parser()
    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """
    Main CLI entry point.

    Parameters
    ----------
    args : list[str] | None, optional
        List of argument strings. If None, uses sys.argv[1:]

    Returns
    -------
    int
        Exit code (0 for success, 1 for error)
    """
    parsed_args = parse_arguments(args)

    # Validate database exists
    if not parsed_args.db_path.exists():
        print(
            f"Error: Database not found: {parsed_args.db_path}",
            file=sys.stderr,
        )
        print(
            "\nPlease ensure the database file exists or specify a different path with --db",
            file=sys.stderr,
        )
        return 1

    # Ensure export directory exists
    try:
        parsed_args.export_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(
            f"Error: Could not create export directory: {parsed_args.export_dir}",
            file=sys.stderr,
        )
        print(f"Reason: {e}", file=sys.stderr)
        return 1

    # Import here to avoid import errors if textual not installed
    try:
        from .app import CorpusDBViewerApp
    except ImportError as e:
        print(
            "Error: Textual library not found. Please install dependencies:",
            file=sys.stderr,
        )
        print("  pip install textual", file=sys.stderr)
        print(f"\nDetails: {e}", file=sys.stderr)
        return 1

    # Launch TUI application
    try:
        app = CorpusDBViewerApp(
            db_path=parsed_args.db_path,
            export_dir=parsed_args.export_dir,
            page_size=parsed_args.page_size,
        )
        app.run()
        return 0
    except KeyboardInterrupt:
        # User pressed Ctrl+C
        print("\nInterrupted by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
