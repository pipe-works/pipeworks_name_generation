"""
Command-line interface for the NLTK syllable extractor.

This module provides the CLI entry point and argument parser for the
NLTK-based syllable extractor. The actual processing logic is in:

- ``interactive.py`` - Interactive mode for single-file extraction
- ``batch.py`` - Batch mode for processing multiple files

Note: This extractor only supports English (CMUDict limitation).

Usage::

    # Interactive mode (no arguments)
    python -m build_tools.nltk_syllable_extractor

    # Batch mode (with arguments)
    python -m build_tools.nltk_syllable_extractor --file input.txt
    python -m build_tools.nltk_syllable_extractor --source ~/corpus/ --recursive
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
    for batch processing mode.

    Returns:
        Configured ArgumentParser instance ready to parse sys.argv.

    Example:
        >>> parser = create_argument_parser()
        >>> args = parser.parse_args(["--file", "input.txt"])
        >>> print(args.file)
        PosixPath('input.txt')
    """
    parser = argparse.ArgumentParser(
        description="NLTK Syllable Extractor - Extract syllables using CMUDict with onset/coda principles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
========

.. code-block:: bash

   # Interactive mode (no arguments)
   python -m build_tools.nltk_syllable_extractor

   # Single file
   python -m build_tools.nltk_syllable_extractor --file input.txt

   # Multiple files
   python -m build_tools.nltk_syllable_extractor --files file1.txt file2.txt file3.txt

   # Directory scan (non-recursive)
   python -m build_tools.nltk_syllable_extractor --source /data/texts/ --pattern "*.txt"

   # Directory scan (recursive)
   python -m build_tools.nltk_syllable_extractor --source /data/ --pattern "*.md" --recursive

   # Custom output directory and syllable lengths
   python -m build_tools.nltk_syllable_extractor --source /data/ --output /results/ --min 3 --max 6

Note: This extractor only supports English (CMUDict). For other languages, use pyphen_syllable_extractor.
""",
    )

    # Input specification (mutually exclusive group)
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--file", type=Path, help="Process a single file")
    input_group.add_argument(
        "--files", type=Path, nargs="+", metavar="FILE", help="Process multiple files"
    )
    input_group.add_argument("--source", type=Path, help="Directory to scan for files")

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
        "--min",
        type=int,
        default=1,
        metavar="N",
        help="Minimum syllable length (default: 1, no filtering)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=999,
        metavar="N",
        help="Maximum syllable length (default: 999, no filtering)",
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
    Main entry point for the NLTK syllable extractor CLI.

    This function determines whether to run in interactive or batch mode
    based on the presence of command-line arguments.

    Modes:
        - Interactive Mode: No arguments provided. Prompts user for all settings.
        - Batch Mode: Arguments provided. Processes files based on CLI flags.

    Examples:
        Interactive mode (no arguments)::

            $ python -m build_tools.nltk_syllable_extractor

        Batch mode (with arguments)::

            $ python -m build_tools.nltk_syllable_extractor --file input.txt
            $ python -m build_tools.nltk_syllable_extractor --files *.txt
            $ python -m build_tools.nltk_syllable_extractor --source ~/docs/ --recursive
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
