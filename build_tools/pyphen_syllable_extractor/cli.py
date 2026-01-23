"""
Command-line interface for the syllable extractor.

This module provides both interactive and batch processing functionality
for syllable extraction, including language selection, user input prompts,
tab completion, and command-line argument parsing for batch operations.
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import List

# Shared CLI utilities
from build_tools.tui_common.cli_utils import (
    CORPUS_DB_AVAILABLE,
    READLINE_AVAILABLE,
    discover_files,
    input_with_completion,
    record_corpus_db_safe,
)

from .extractor import SyllableExtractor
from .file_io import DEFAULT_OUTPUT_DIR, generate_output_filename, save_metadata
from .language_detection import is_detection_available
from .languages import SUPPORTED_LANGUAGES
from .models import BatchResult, ExtractionResult, FileProcessingResult

# Corpus DB integration (import CorpusLedger only if available)
if CORPUS_DB_AVAILABLE:
    from build_tools.corpus_db import CorpusLedger

# Version for ledger
try:
    from build_tools.pyphen_syllable_extractor import __version__ as EXTRACTOR_VERSION  # noqa: N812
except (ImportError, AttributeError):
    EXTRACTOR_VERSION = "unknown"


def select_language() -> str:
    """
    Interactive prompt to select a language from supported options.

    Returns:
        The pyphen language code for the selected language, or "auto"
        for automatic language detection

    Note:
        Exits the program if the user provides invalid input after
        multiple attempts or requests to quit.
    """
    print("\n" + "=" * 70)
    print("SYLLABLE EXTRACTOR - Language Selection")
    print("=" * 70)

    # Check if auto-detection is available
    auto_available = is_detection_available()
    if auto_available:
        print("\n💡 Auto-detection available! Type 'auto' to automatically detect language.")

    print("\nSupported Languages:")
    print("-" * 70)

    # Display languages in a formatted list
    languages = sorted(SUPPORTED_LANGUAGES.items())
    for idx, (name, code) in enumerate(languages, 1):
        print(f"{idx:2d}. {name:25s} ({code})")

    print("-" * 70)
    print("\nYou can select by:")
    print("  - Number (e.g., '13' for English UK)")
    print("  - Language name (e.g., 'English (US)')")
    print("  - Language code (e.g., 'en_US')")
    if auto_available:
        print("  - Type 'auto' for automatic language detection")
    print("  - Type 'quit' to exit")
    print("=" * 70)

    while True:
        selection = input("\nSelect a language: ").strip()

        if selection.lower() == "quit":
            print("Exiting.")
            sys.exit(0)

        # Check for auto-detection
        if selection.lower() == "auto":
            if not auto_available:
                print(
                    "Error: Auto-detection not available. "
                    "Install langdetect: pip install langdetect"
                )
                continue
            print("\n✓ Selected: Automatic language detection")
            return "auto"

        # Try to match by number
        if selection.isdigit():
            idx = int(selection) - 1
            if 0 <= idx < len(languages):
                selected_name, selected_code = languages[idx]
                print(f"\nSelected: {selected_name} ({selected_code})")
                return selected_code
            else:
                print(f"Error: Please enter a number between 1 and {len(languages)}")
                continue

        # Try to match by language name
        if selection in SUPPORTED_LANGUAGES:
            selected_code = SUPPORTED_LANGUAGES[selection]
            print(f"\nSelected: {selection} ({selected_code})")
            return selected_code

        # Try to match by language code
        if selection in SUPPORTED_LANGUAGES.values():
            # Find the language name for this code
            selected_name = next(
                name for name, code in SUPPORTED_LANGUAGES.items() if code == selection
            )
            print(f"\nSelected: {selected_name} ({selection})")
            return selection

        print("Error: Invalid selection. Please try again or type 'quit' to exit.")


def process_single_file_batch(
    input_path: Path,
    language_code: str,
    min_len: int,
    max_len: int,
    output_dir: Path,
    run_timestamp: str,
    verbose: bool = False,
) -> FileProcessingResult:
    """
    Process a single file in batch mode with comprehensive error handling.

    This function attempts to extract syllables from a single file and saves
    the results. Unlike interactive mode, this function catches all exceptions
    and returns a result object indicating success or failure, allowing batch
    processing to continue even when individual files fail.

    Args:
        input_path: Path to the input text file to process
        language_code: Language code (e.g., "en_US", "de_DE") or "auto" for
                      automatic language detection
        min_len: Minimum syllable length to include in results
        max_len: Maximum syllable length to include in results
        output_dir: Directory where output files should be saved
        run_timestamp: Timestamp for the batch run (shared across all files in batch)
        verbose: If True, print detailed progress messages (default: False)

    Returns:
        FileProcessingResult object with success status, syllables count,
        output paths (if successful), or error message (if failed).

    Note:
        This function never raises exceptions. All errors are caught and
        returned in the FileProcessingResult.error_message field. This
        design allows batch processing to continue despite individual failures.

    Example:
        >>> timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        >>> result = process_single_file_batch(
        ...     Path("book.txt"),
        ...     language_code="en_US",
        ...     min_len=2,
        ...     max_len=8,
        ...     output_dir=Path("output/"),
        ...     run_timestamp=timestamp,
        ...     verbose=True
        ... )
        >>> if result.success:
        ...     print(f"Extracted {result.syllables_count} syllables")
        ... else:
        ...     print(f"Failed: {result.error_message}")
    """
    start_time = time.perf_counter()

    try:
        if verbose:
            print(f"⏳ Processing {input_path.name}...")

        # Extract syllables (with auto-detection if requested)
        if language_code == "auto":
            syllables, stats, detected_lang = SyllableExtractor.extract_file_with_auto_language(
                input_path,
                min_syllable_length=min_len,
                max_syllable_length=max_len,
                suppress_warnings=True,
            )
            actual_language = detected_lang
        else:
            extractor = SyllableExtractor(language_code, min_len, max_len)
            syllables, stats = extractor.extract_syllables_from_file(input_path)
            actual_language = language_code

        # Generate output filenames using input filename and shared run timestamp
        syllables_path, metadata_path = generate_output_filename(
            output_dir=output_dir,
            run_timestamp=run_timestamp,
            input_filename=input_path.name,
        )

        # Save syllables (create extractor if needed for auto-detection case)
        if language_code == "auto":
            extractor = SyllableExtractor(actual_language, min_len, max_len)

        extractor.save_syllables(syllables, syllables_path)

        # Save metadata
        result = ExtractionResult(
            syllables=syllables,
            language_code=actual_language,
            min_syllable_length=min_len,
            max_syllable_length=max_len,
            input_path=input_path,
            only_hyphenated=True,
            total_words=stats["total_words"],
            skipped_unhyphenated=stats["skipped_unhyphenated"],
            rejected_syllables=stats["rejected_syllables"],
            processed_words=stats["processed_words"],
        )
        save_metadata(result, metadata_path)

        processing_time = time.perf_counter() - start_time

        if verbose:
            print(f"  ✓ Extracted {len(syllables)} syllables ({actual_language})")

        return FileProcessingResult(
            input_path=input_path,
            success=True,
            syllables_count=len(syllables),
            language_code=actual_language,
            syllables_output_path=syllables_path,
            metadata_output_path=metadata_path,
            processing_time=processing_time,
        )

    except Exception as e:
        processing_time = time.perf_counter() - start_time

        if verbose:
            print(f"  ✗ Failed: {str(e)}")

        return FileProcessingResult(
            input_path=input_path,
            success=False,
            syllables_count=0,
            language_code=language_code,
            error_message=str(e),
            processing_time=processing_time,
        )


def process_batch(
    files: List[Path],
    language_code: str,
    min_len: int,
    max_len: int,
    output_dir: Path,
    quiet: bool = False,
    verbose: bool = False,
) -> BatchResult:
    """
    Process multiple files sequentially in batch mode.

    This function processes a list of files one at a time, extracting syllables
    from each and saving results to the specified output directory. All files
    in the batch share a single timestamped run directory, grouping them as
    one logical batch operation.

    Args:
        files: List of input file paths to process
        language_code: Language code (e.g., "en_US") or "auto" for detection
        min_len: Minimum syllable length to include
        max_len: Maximum syllable length to include
        output_dir: Output directory for all results (created if needed)
        quiet: If True, suppress all output except errors (default: False)
        verbose: If True, show detailed progress for each file (default: False).
                Ignored if quiet=True.

    Returns:
        BatchResult with overall statistics and individual file results.

    Example:
        >>> files = [Path("book1.txt"), Path("book2.txt"), Path("book3.txt")]
        >>> result = process_batch(
        ...     files,
        ...     language_code="auto",
        ...     min_len=2,
        ...     max_len=8,
        ...     output_dir=Path("output/")
        ... )
        >>> print(f"Processed {result.successful}/{result.total_files} files")
        >>> print(result.format_summary())

    Note:
        Processing is sequential (not parallel). Files are processed in the
        order provided in the files list. All outputs share a single run
        directory identified by the batch start timestamp.
    """
    start_time = time.perf_counter()

    # Generate a single timestamp for the entire batch run
    from datetime import datetime

    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Compute run directory path for display
    run_dir = output_dir / run_timestamp

    if not quiet:
        print(f"\n{'='*70}")
        print(f"BATCH PROCESSING - {len(files)} files")
        print(f"{'='*70}")
        print(f"Language:         {language_code}")
        print(f"Syllable Length:  {min_len}-{max_len} characters")
        print(f"Run Directory:    {run_dir}")
        print(f"{'='*70}\n")

    results = []
    successful = 0
    failed = 0

    for idx, file_path in enumerate(files, 1):
        if not quiet and not verbose:
            # Progress indicator (non-verbose mode)
            print(f"[{idx}/{len(files)}] Processing {file_path.name}...", end=" ", flush=True)

        result = process_single_file_batch(
            file_path,
            language_code,
            min_len,
            max_len,
            output_dir,
            run_timestamp,
            verbose=verbose and not quiet,
        )

        results.append(result)

        if result.success:
            successful += 1
            if not quiet and not verbose:
                print("✓")
        else:
            failed += 1
            if not quiet and not verbose:
                print(f"✗ {result.error_message}")

    total_time = time.perf_counter() - start_time

    return BatchResult(
        total_files=len(files),
        successful=successful,
        failed=failed,
        results=results,
        total_time=total_time,
        output_directory=run_dir,  # Use run directory, not base output directory
    )


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
   python -m build_tools.syllable_extractor

   # Single file (language auto-detected or defaults to en_US)
   python -m build_tools.syllable_extractor --file input.txt

   # Single file with explicit language
   python -m build_tools.syllable_extractor --file input.txt --lang en_US

   # Multiple files with automatic language detection
   python -m build_tools.syllable_extractor --files file1.txt file2.txt file3.txt --auto

   # Directory scan (language auto-detected or defaults to en_US)
   python -m build_tools.syllable_extractor --source /data/texts/ --pattern "*.txt"

   # Directory scan (recursive)
   python -m build_tools.syllable_extractor --source /data/ --pattern "*.md" --recursive

   # Custom output directory and syllable lengths
   python -m build_tools.syllable_extractor --source /data/ --output /results/ --min 3 --max 6
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


def main_interactive():
    """
    Interactive mode entry point for the syllable extractor CLI.

    Workflow:
        1. Prompt user to select a language (or 'auto' for automatic detection)
        2. Configure extraction parameters (min/max syllable length)
        3. Prompt for input file path
        4. Extract syllables from input file (with optional auto-detection)
        5. Generate timestamped output filenames
        6. Save syllables and metadata to separate files
        7. Display summary to console

    Language Detection:
        - If 'auto' is selected and langdetect is installed, the tool will
          automatically detect the language of the input text
        - Detection requires at least 20-50 characters for reliable results
        - Falls back to English (en_US) if detection fails

    Output Files:
        - YYYYMMDD_HHMMSS.syllables.LANG.txt: One syllable per line, sorted
        - YYYYMMDD_HHMMSS.meta.LANG.txt: Extraction metadata and statistics

    Corpus Database Integration:
        All interactive mode extractions are automatically recorded to the corpus
        database ledger (data/raw/syllable_extractor.db) for build provenance
        tracking. Recording is optional - extraction succeeds even if ledger fails.

    Both files are saved to _working/output/ by default.
    """
    print("\n" + "=" * 70)
    print("PYPHEN SYLLABLE EXTRACTOR")
    print("=" * 70)
    print("\nThis tool extracts syllables from text files using dictionary-based")
    print("hyphenation rules. Output is saved to _working/output/ by default.")
    print("=" * 70)

    # Step 1: Select language
    language_code = select_language()

    # Step 2: Configure extraction parameters
    print("\n" + "-" * 70)
    print("EXTRACTION SETTINGS")
    print("-" * 70)

    # Get min syllable length
    while True:
        min_len_str = input("\nMinimum syllable length (default: 2): ").strip()
        if not min_len_str:
            min_len = 2
            break
        try:
            min_len = int(min_len_str)
            if min_len < 1:
                print("Error: Minimum length must be at least 1")
                continue
            break
        except ValueError:
            print("Error: Please enter a valid number")

    # Get max syllable length
    while True:
        max_len_str = input("Maximum syllable length (default: 8): ").strip()
        if not max_len_str:
            max_len = 8
            break
        try:
            max_len = int(max_len_str)
            if max_len < min_len:
                print(f"Error: Maximum must be >= minimum ({min_len})")
                continue
            break
        except ValueError:
            print("Error: Please enter a valid number")

    print(f"\n✓ Settings: syllables between {min_len}-{max_len} characters")

    # Step 3: Initialize extractor (skip if using auto-detection)
    if language_code != "auto":
        try:
            extractor = SyllableExtractor(language_code, min_len, max_len)
            print(f"✓ Hyphenation dictionary loaded for: {language_code}")
        except ValueError as e:
            print(f"\nError: {e}")
            sys.exit(1)

    # Step 4: Get input file path
    print("\n" + "-" * 70)
    print("INPUT FILE SELECTION")
    print("-" * 70)
    if READLINE_AVAILABLE:
        print("💡 Tip: Use TAB for path completion (~ for home directory)")
    print()

    while True:
        input_path_str = input_with_completion(
            "Enter input file path (or 'quit' to exit): "
        ).strip()

        if input_path_str.lower() == "quit":
            print("Exiting.")
            sys.exit(0)

        # Expand user home directory
        input_path_str = os.path.expanduser(input_path_str)
        input_path = Path(input_path_str)

        if not input_path.exists():
            print(f"Error: File not found: {input_path}")
            continue

        if not input_path.is_file():
            print(f"Error: Path is not a file: {input_path}")
            continue

        break

    # Initialize corpus_db ledger for provenance tracking
    run_id = None
    ledger = None

    if CORPUS_DB_AVAILABLE:
        try:
            ledger = CorpusLedger()
            pyphen_lang = None if language_code == "auto" else language_code

            run_id = ledger.start_run(
                extractor_tool="pyphen_syllable_extractor",
                extractor_version=EXTRACTOR_VERSION,
                pyphen_lang=pyphen_lang,
                min_len=min_len,
                max_len=max_len,
                command_line=" ".join(sys.argv),
            )
        except Exception as e:
            print(f"Warning: Failed to initialize corpus_db: {e}", file=sys.stderr)
            run_id = None
            ledger = None

    # Record input to corpus_db
    if run_id is not None and ledger is not None:
        record_corpus_db_safe("input", lambda: ledger.record_input(run_id, input_path), quiet=False)

    # Step 5: Extract syllables
    print(f"\n⏳ Processing {input_path}...")
    try:
        if language_code == "auto":
            # Use auto-detection
            syllables, stats, detected_language = SyllableExtractor.extract_file_with_auto_language(
                input_path,
                min_syllable_length=min_len,
                max_syllable_length=max_len,
                suppress_warnings=True,
            )
            language_code = detected_language  # Update for metadata
            print(f"✓ Detected language: {detected_language}")
            print(f"✓ Extracted {len(syllables)} unique syllables")
            # Create extractor instance with detected language for saving
            extractor = SyllableExtractor(language_code, min_len, max_len)
        else:
            # Use manual language selection
            syllables, stats = extractor.extract_syllables_from_file(input_path)
            print(f"✓ Extracted {len(syllables)} unique syllables")
    except Exception as e:
        print(f"\nError during extraction: {e}")
        # Record failed run to corpus_db before exiting
        if run_id is not None and ledger is not None:
            record_corpus_db_safe(
                "complete run",
                lambda: ledger.complete_run(run_id, exit_code=1, status="failed"),
                quiet=True,
            )
            record_corpus_db_safe("close ledger", lambda: ledger.close(), quiet=True)
        sys.exit(1)

    # Step 6: Generate output filenames and create result object
    syllables_path, metadata_path = generate_output_filename(language_code=language_code)

    result = ExtractionResult(
        syllables=syllables,
        language_code=language_code,
        min_syllable_length=min_len,
        max_syllable_length=max_len,
        input_path=input_path,
        only_hyphenated=True,
        total_words=stats["total_words"],
        skipped_unhyphenated=stats["skipped_unhyphenated"],
        rejected_syllables=stats["rejected_syllables"],
        processed_words=stats["processed_words"],
    )

    # Step 7: Save syllables
    print(f"\n⏳ Saving syllables to {syllables_path}...")
    try:
        extractor.save_syllables(syllables, syllables_path)
        print("✓ Syllables saved successfully")
    except Exception as e:
        print(f"\nError saving syllables: {e}")
        # Record failed run to corpus_db before exiting
        if run_id is not None and ledger is not None:
            record_corpus_db_safe(
                "complete run",
                lambda: ledger.complete_run(run_id, exit_code=1, status="failed"),
                quiet=True,
            )
            record_corpus_db_safe("close ledger", lambda: ledger.close(), quiet=True)
        sys.exit(1)

    # Step 8: Save metadata
    print(f"⏳ Saving metadata to {metadata_path}...")
    try:
        save_metadata(result, metadata_path)
        print("✓ Metadata saved successfully")
    except Exception as e:
        print(f"\nError saving metadata: {e}")
        # Record failed run to corpus_db before exiting
        if run_id is not None and ledger is not None:
            record_corpus_db_safe(
                "complete run",
                lambda: ledger.complete_run(run_id, exit_code=1, status="failed"),
                quiet=True,
            )
            record_corpus_db_safe("close ledger", lambda: ledger.close(), quiet=True)
        sys.exit(1)

    # Record output to corpus_db
    if run_id is not None and ledger is not None:
        record_corpus_db_safe(
            "output",
            lambda: ledger.record_output(
                run_id,
                output_path=syllables_path,
                unique_syllable_count=len(syllables),
                meta_path=metadata_path,
            ),
            quiet=False,
        )

    # Complete corpus_db run recording
    if run_id is not None and ledger is not None:
        record_corpus_db_safe(
            "complete run",
            lambda: ledger.complete_run(run_id, exit_code=0, status="completed"),
            quiet=False,
        )

        # Close ledger connection
        record_corpus_db_safe("close ledger", lambda: ledger.close(), quiet=True)

    # Step 9: Display summary to console
    print("\n" + result.format_metadata())

    # Get the run directory (parent of syllables dir)
    run_dir = syllables_path.parent.parent
    print(f"\n✓ Output saved to run directory: {run_dir}/")
    print(f"  - Syllables: {syllables_path.relative_to(DEFAULT_OUTPUT_DIR)}")
    print(f"  - Metadata:  {metadata_path.relative_to(DEFAULT_OUTPUT_DIR)}")
    print("\n✓ Done!\n")


def main_batch(args: argparse.Namespace):
    """
    Batch mode entry point for the syllable extractor CLI.

    This function processes multiple files based on command-line arguments,
    providing progress indicators and comprehensive error reporting.

    Args:
        args: Parsed command-line arguments from argparse.Namespace containing:
            - file: Single file path (optional)
            - files: List of file paths (optional)
            - source: Directory path for scanning (optional)
            - pattern: File pattern for directory scanning (default: "*.txt")
            - recursive: Whether to scan directories recursively
            - lang: Manual language code (mutually exclusive with auto)
            - auto: Use automatic language detection (mutually exclusive with lang)
            - min: Minimum syllable length (default: 2)
            - max: Maximum syllable length (default: 8)
            - output: Output directory (default: _working/output/)
            - quiet: Suppress progress indicators
            - verbose: Show detailed processing information

    Corpus Database Integration:
        All batch mode extractions are automatically recorded to the corpus
        database ledger (data/raw/syllable_extractor.db) for build provenance
        tracking. Recording is optional - extraction succeeds even if ledger
        fails.

    Exit Codes:
        0: All files processed successfully
        1: One or more files failed to process

    Raises:
        SystemExit: On validation errors or processing completion
    """
    # Validate parameters
    if args.min < 1:
        print("Error: Minimum syllable length must be at least 1")
        sys.exit(1)

    if args.max < args.min:
        print(f"Error: Maximum syllable length ({args.max}) must be >= minimum ({args.min})")
        sys.exit(1)

    # Determine language code with intelligent defaults
    if args.auto:
        language_code = "auto"
    elif args.lang:
        language_code = args.lang
    else:
        # Default behavior: auto-detect if available, otherwise en_US
        if is_detection_available():
            language_code = "auto"
            if not args.quiet:
                print("ℹ️  No language specified - using automatic detection (--auto)")
        else:
            language_code = "en_US"
            if not args.quiet:
                print("ℹ️  No language specified - defaulting to English US (en_US)")

    # Initialize corpus_db ledger for provenance tracking
    run_id = None
    ledger = None

    if CORPUS_DB_AVAILABLE:
        try:
            ledger = CorpusLedger()
            pyphen_lang = None if language_code == "auto" else language_code

            run_id = ledger.start_run(
                extractor_tool="pyphen_syllable_extractor",
                extractor_version=EXTRACTOR_VERSION,
                pyphen_lang=pyphen_lang,
                min_len=args.min,
                max_len=args.max,
                recursive=args.recursive,
                pattern=args.pattern,
                command_line=" ".join(sys.argv),
            )
        except Exception as e:
            if not args.quiet:
                print(f"Warning: Failed to initialize corpus_db: {e}", file=sys.stderr)
            run_id = None
            ledger = None

    # Collect files to process
    files_to_process: List[Path] = []

    try:
        if args.file:
            # Single file
            file_path = Path(args.file).expanduser().resolve()
            if not file_path.exists():
                print(f"Error: File not found: {file_path}")
                sys.exit(1)
            if not file_path.is_file():
                print(f"Error: Path is not a file: {file_path}")
                sys.exit(1)
            files_to_process.append(file_path)

        elif args.files:
            # Multiple files
            for file_str in args.files:
                file_path = Path(file_str).expanduser().resolve()
                if not file_path.exists():
                    print(f"Error: File not found: {file_path}")
                    sys.exit(1)
                if not file_path.is_file():
                    print(f"Error: Path is not a file: {file_path}")
                    sys.exit(1)
                files_to_process.append(file_path)

        elif args.source:
            # Directory scanning
            source_path = Path(args.source).expanduser().resolve()
            if not source_path.exists():
                print(f"Error: Source directory not found: {source_path}")
                sys.exit(1)
            if not source_path.is_dir():
                print(f"Error: Source path is not a directory: {source_path}")
                sys.exit(1)

            files_to_process = discover_files(
                source=source_path, pattern=args.pattern, recursive=args.recursive
            )

            if not files_to_process:
                print(f"Error: No files matching pattern '{args.pattern}' found in {source_path}")
                sys.exit(1)

        else:
            print("Error: No input specified. Use --file, --files, or --source")
            sys.exit(1)

    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Record inputs to corpus_db
    if run_id is not None and ledger is not None:
        if args.file:
            # Single file
            record_corpus_db_safe(
                "input", lambda: ledger.record_input(run_id, files_to_process[0]), quiet=args.quiet
            )
        elif args.files:
            # Multiple files - record each
            for file_path in files_to_process:
                record_corpus_db_safe(
                    "input",
                    lambda fp=file_path: ledger.record_input(run_id, fp),  # type: ignore[misc]
                    quiet=args.quiet,
                )
        elif args.source:
            # Directory - record with file count
            source_path = Path(args.source).expanduser().resolve()
            record_corpus_db_safe(
                "input",
                lambda: ledger.record_input(run_id, source_path, file_count=len(files_to_process)),
                quiet=args.quiet,
            )

    # Determine output directory
    output_dir = Path(args.output).expanduser().resolve() if args.output else DEFAULT_OUTPUT_DIR

    # Display batch configuration
    if not args.quiet:
        print("\n" + "=" * 70)
        print("BATCH SYLLABLE EXTRACTION")
        print("=" * 70)
        print(f"Files to process:   {len(files_to_process)}")
        print(f"Language:           {language_code}")
        print(f"Syllable length:    {args.min}-{args.max} characters")
        print(f"Output directory:   {output_dir}")
        print("=" * 70 + "\n")

    # Process batch
    batch_result = process_batch(
        files=files_to_process,
        language_code=language_code,
        min_len=args.min,
        max_len=args.max,
        output_dir=output_dir,
        quiet=args.quiet,
        verbose=args.verbose,
    )

    # Record outputs to corpus_db
    if run_id is not None and ledger is not None:
        for result in batch_result.results:
            if result.success:
                record_corpus_db_safe(
                    "output",
                    lambda r=result: ledger.record_output(  # type: ignore[misc]
                        run_id,
                        output_path=r.syllables_output_path,
                        unique_syllable_count=r.syllables_count,
                        meta_path=r.metadata_output_path,
                    ),
                    quiet=args.quiet,
                )

    # Complete corpus_db run recording
    if run_id is not None and ledger is not None:
        exit_code = 1 if batch_result.failed > 0 else 0
        status = "completed" if batch_result.failed == 0 else "failed"

        record_corpus_db_safe(
            "complete run",
            lambda: ledger.complete_run(run_id, exit_code=exit_code, status=status),
            quiet=args.quiet,
        )

        # Close ledger connection
        record_corpus_db_safe(
            "close ledger",
            lambda: ledger.close(),
            quiet=True,  # Don't warn on close failures
        )

    # Display summary
    if not args.quiet:
        print("\n" + batch_result.format_summary())

    # Exit with appropriate code
    if batch_result.failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)


def main():
    """
    Main entry point for the syllable extractor CLI.

    This function determines whether to run in interactive or batch mode
    based on the presence of command-line arguments.

    Modes:
        - Interactive Mode: No arguments provided. Prompts user for all settings.
        - Batch Mode: Arguments provided. Processes files based on CLI flags.

    Examples:
        Interactive mode (no arguments):
            $ python -m build_tools.syllable_extractor

        Batch mode (with arguments):
            $ python -m build_tools.syllable_extractor --file input.txt --lang en_US
            $ python -m build_tools.syllable_extractor --files *.txt --auto
            $ python -m build_tools.syllable_extractor --source ~/docs/ --recursive --auto
    """
    # Create argument parser
    parser = create_argument_parser()

    # Parse arguments
    args = parser.parse_args()

    # Determine mode: batch if any input argument provided, otherwise interactive
    has_batch_args = args.file or args.files or args.source

    if has_batch_args:
        # Batch mode
        main_batch(args)
    else:
        # Interactive mode
        main_interactive()
