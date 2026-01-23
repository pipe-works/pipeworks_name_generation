"""
Command-line interface for the pyphen syllable extractor.

This module provides the CLI entry point and argument parser for the
pyphen-based syllable extractor. The actual processing logic is in:

- ``interactive.py`` - Interactive mode with language selection
- ``batch.py`` - Batch mode for processing multiple files

Usage::

    # Interactive mode (no arguments)
    python -m build_tools.pyphen_syllable_extractor

    # Batch mode (with arguments)
    python -m build_tools.pyphen_syllable_extractor --file input.txt
    python -m build_tools.pyphen_syllable_extractor --source ~/corpus/ --recursive
"""

from __future__ import annotations

import argparse
from pathlib import Path

# Backwards compatibility re-exports (deprecated, import from package instead)
from build_tools.tui_common.cli_utils import (  # noqa: F401
    CORPUS_DB_AVAILABLE,
    READLINE_AVAILABLE,
    discover_files,
    input_with_completion,
    record_corpus_db_safe,
)

from .batch import process_batch, process_single_file, run_batch  # noqa: F401
from .file_io import DEFAULT_OUTPUT_DIR
from .interactive import run_interactive

# Re-export CorpusLedger for backwards compatibility when available
if CORPUS_DB_AVAILABLE:
    from build_tools.corpus_db import CorpusLedger  # noqa: F401

# Backwards compatibility aliases
main_batch = run_batch
main_interactive = run_interactive
process_single_file_batch = process_single_file


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser for batch mode.

    This function sets up the argparse parser with all command-line options
    for batch processing mode. The parser supports mutually exclusive groups
    for input specification and language selection.

    Returns:
        Configured ArgumentParser instance ready to parse sys.argv.

    Example:
        >>> parser = create_argument_parser()
        >>> args = parser.parse_args(["--file", "input.txt", "--lang", "en_US"])
        >>> print(args.file)
        PosixPath('input.txt')
    """
    parser = argparse.ArgumentParser(
        description="Syllable Extractor - Extract syllables from text using pyphen hyphenation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
========

.. code-block:: bash

   # Interactive mode (no arguments)
   python -m build_tools.pyphen_syllable_extractor

   # Single file (language auto-detected or defaults to en_US)
   python -m build_tools.pyphen_syllable_extractor --file input.txt

   # Single file with explicit language
   python -m build_tools.pyphen_syllable_extractor --file input.txt --lang en_US

   # Multiple files with automatic language detection
   python -m build_tools.pyphen_syllable_extractor --files file1.txt file2.txt file3.txt --auto

   # Directory scan (language auto-detected or defaults to en_US)
   python -m build_tools.pyphen_syllable_extractor --source /data/texts/ --pattern "*.txt"

   # Directory scan (recursive)
   python -m build_tools.pyphen_syllable_extractor --source /data/ --pattern "*.md" --recursive

   # Custom output directory and syllable lengths
   python -m build_tools.pyphen_syllable_extractor --source /data/ --output /results/ --min 3 --max 6
""",
    )

    # Input specification (mutually exclusive group)
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--file", type=Path, help="Process a single file")
    input_group.add_argument(
        "--files", type=Path, nargs="+", metavar="FILE", help="Process multiple files"
    )
    input_group.add_argument("--source", type=Path, help="Directory to scan for files")

    # Language specification (mutually exclusive, optional with intelligent defaults)
    lang_group = parser.add_mutually_exclusive_group()
    lang_group.add_argument(
        "--lang",
        type=str,
        help="Language code (e.g., en_US, de_DE, fr). "
        "If omitted, uses --auto if langdetect is installed, otherwise en_US.",
    )
    lang_group.add_argument(
        "--auto",
        action="store_true",
        help="Automatically detect language (requires langdetect). "
        "This is the default if langdetect is installed and --lang is not specified.",
    )

    # Directory scanning options
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.txt",
        help="File pattern for directory scanning (default: *.txt)",
    )
    parser.add_argument("--recursive", action="store_true", help="Search directories recursively")

    # Extraction parameters
    parser.add_argument(
        "--min", type=int, default=2, metavar="N", help="Minimum syllable length (default: 2)"
    )
    parser.add_argument(
        "--max", type=int, default=8, metavar="N", help="Maximum syllable length (default: 8)"
    )

    # Output options
    parser.add_argument(
        "--output", type=Path, help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress all output except errors")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    return parser


def main() -> None:
    """
    Main entry point for the pyphen syllable extractor CLI.

    This function determines whether to run in interactive or batch mode
    based on the presence of command-line arguments.

    Modes:
        - Interactive Mode: No arguments provided. Prompts user for all settings.
        - Batch Mode: Arguments provided. Processes files based on CLI flags.

    Examples:
        Interactive mode (no arguments)::

            $ python -m build_tools.pyphen_syllable_extractor

        Batch mode (with arguments)::

            $ python -m build_tools.pyphen_syllable_extractor --file input.txt --lang en_US
            $ python -m build_tools.pyphen_syllable_extractor --files *.txt --auto
            $ python -m build_tools.pyphen_syllable_extractor --source ~/docs/ --recursive --auto
    """
    # Create argument parser
    parser = create_argument_parser()

    # Parse arguments
    args = parser.parse_args()

    # Determine mode: batch if any input argument provided, otherwise interactive
    has_batch_args = args.file or args.files or args.source

    if has_batch_args:
        # Batch mode - import here to avoid circular imports and speed up --help
        from .batch import run_batch

        run_batch(args)
    else:
        # Interactive mode - import here to avoid circular imports and speed up --help
        from .interactive import run_interactive

        run_interactive()
