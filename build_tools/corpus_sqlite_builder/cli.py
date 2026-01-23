"""
Command-line interface for corpus SQLite builder.

This module provides the CLI for converting annotated JSON files to SQLite databases.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .converter import convert_json_to_sqlite, find_annotated_json


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and return the argument parser for this tool.

    Returns:
        Configured ArgumentParser ready to parse command-line arguments
    """
    parser = argparse.ArgumentParser(
        prog="python -m build_tools.corpus_sqlite_builder",
        description=(
            "Convert annotated JSON files to SQLite databases for efficient querying.\n\n"
            "This tool converts large JSON files (*_syllables_annotated.json) into "
            "optimized SQLite databases (corpus.db) for memory-efficient, high-performance "
            "queries in interactive tools like the TUI.\n\n"
            "The JSON file remains the canonical source of truth. The SQLite database "
            "is derived data that can be regenerated at any time."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
========

.. code-block:: bash

   # Convert single corpus (auto-discovers JSON in data/ subdirectory)
   python -m build_tools.corpus_sqlite_builder \\
     _working/output/20260110_115453_pyphen/

   # Force overwrite existing database
   python -m build_tools.corpus_sqlite_builder \\
     _working/output/20260110_115453_pyphen/ --force

   # Dry run to check what would be converted
   python -m build_tools.corpus_sqlite_builder \\
     _working/output/20260110_115453_pyphen/ --dry-run

   # Batch convert all corpora in output directory
   python -m build_tools.corpus_sqlite_builder --batch _working/output/

Output
======

Creates corpus.db in the data/ subdirectory of the corpus::

   _working/output/20260110_115453_pyphen/data/corpus.db
        """,
    )

    parser.add_argument(
        "corpus_dir",
        type=Path,
        nargs="?",
        help=(
            "Path to corpus directory containing data/ subdirectory with annotated JSON. "
            "Example: _working/output/20260110_115453_pyphen/"
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Overwrite existing corpus.db file if it exists. "
            "Default: False (raise error if database exists)"
        ),
    )

    parser.add_argument(
        "--batch",
        type=Path,
        metavar="OUTPUT_DIR",
        help=(
            "Batch convert all corpora in the specified output directory. "
            "Example: --batch _working/output/ "
            "Will discover and convert all corpus directories."
        ),
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=10000,
        metavar="N",
        help=(
            "Number of records to insert per database transaction. "
            "Larger values are faster but use more memory. "
            "Default: 10000"
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Show what would be converted without actually creating the database. "
            "Useful for checking if JSON files are discoverable."
        ),
    )

    return parser


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        args: List of argument strings to parse. If None, uses sys.argv.

    Returns:
        Parsed arguments namespace
    """
    parser = create_argument_parser()
    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """
    Main entry point for the CLI.

    Args:
        args: List of argument strings. If None, uses sys.argv.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parsed_args = parse_arguments(args)

    # Handle batch mode
    if parsed_args.batch:
        return run_batch_conversion(parsed_args)

    # Single corpus mode requires corpus_dir
    if not parsed_args.corpus_dir:
        print("Error: corpus_dir is required (or use --batch)", file=sys.stderr)
        return 1

    return run_single_conversion(parsed_args)


def run_single_conversion(args: argparse.Namespace) -> int:
    """
    Convert a single corpus directory.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    corpus_dir = args.corpus_dir

    if not corpus_dir.exists():
        print(f"Error: Corpus directory not found: {corpus_dir}", file=sys.stderr)
        return 1

    # Check for annotated JSON
    data_dir = corpus_dir / "data"
    json_path = find_annotated_json(data_dir)

    if json_path is None:
        print(f"Error: No annotated JSON found in {data_dir}", file=sys.stderr)
        print("Looking for: *_syllables_annotated.json", file=sys.stderr)
        return 1

    # Dry run mode
    if args.dry_run:
        print(f"Would convert: {json_path}")
        print(f"Output: {data_dir / 'corpus.db'}")
        db_path = data_dir / "corpus.db"
        if db_path.exists():
            print("Note: Database already exists (would need --force)")
        return 0

    # Perform conversion
    try:
        db_path = convert_json_to_sqlite(
            corpus_dir=corpus_dir,
            force=args.force,
            batch_size=args.batch_size,
        )
        print(f"\n✓ Conversion complete: {db_path}")
        return 0

    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Use --force to overwrite existing database.", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        return 1


def run_batch_conversion(args: argparse.Namespace) -> int:
    """
    Convert multiple corpus directories.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    output_dir = args.batch

    if not output_dir.exists() or not output_dir.is_dir():
        print(f"Error: Output directory not found: {output_dir}", file=sys.stderr)
        return 1

    # Discover corpus directories
    corpus_dirs = []
    for item in output_dir.iterdir():
        if not item.is_dir():
            continue

        # Check if it has a data/ subdirectory with annotated JSON
        data_dir = item / "data"
        if find_annotated_json(data_dir):
            corpus_dirs.append(item)

    if not corpus_dirs:
        print(f"No corpus directories found in {output_dir}", file=sys.stderr)
        return 1

    print(f"Found {len(corpus_dirs)} corpus directories")
    print()

    # Convert each corpus
    success_count = 0
    error_count = 0

    for i, corpus_dir in enumerate(corpus_dirs, 1):
        print(f"[{i}/{len(corpus_dirs)}] Converting: {corpus_dir.name}")
        print("-" * 60)

        try:
            db_path = convert_json_to_sqlite(
                corpus_dir=corpus_dir,
                force=args.force,
                batch_size=args.batch_size,
            )
            print(f"✓ Success: {db_path}")
            success_count += 1

        except FileExistsError:
            print("⊗ Skipped: Database already exists (use --force to overwrite)")
            error_count += 1

        except Exception as e:
            print(f"✗ Error: {e}", file=sys.stderr)
            error_count += 1

        print()

    # Summary
    print("=" * 60)
    print("Batch conversion complete:")
    print(f"  Success: {success_count}")
    print(f"  Errors/Skipped: {error_count}")
    print(f"  Total: {len(corpus_dirs)}")

    return 0 if error_count == 0 else 1
