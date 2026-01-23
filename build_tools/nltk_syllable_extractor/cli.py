"""
Command-line interface for the NLTK-based syllable extractor.

This module provides both interactive and batch processing functionality
for syllable extraction using NLTK's CMU Pronouncing Dictionary.
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

from .extractor import NltkSyllableExtractor
from .file_io import DEFAULT_OUTPUT_DIR, generate_output_filename, save_metadata
from .models import BatchResult, ExtractionResult, FileProcessingResult

# Corpus DB integration (import CorpusLedger only if available)
if CORPUS_DB_AVAILABLE:
    from build_tools.corpus_db import CorpusLedger

# Version for ledger
try:
    from build_tools.nltk_syllable_extractor import __version__ as EXTRACTOR_VERSION  # noqa: N812
except (ImportError, AttributeError):
    EXTRACTOR_VERSION = "unknown"


def process_single_file_batch(
    input_path: Path,
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

        # Extract syllables
        extractor = NltkSyllableExtractor("en_US", min_len, max_len)
        syllables, stats = extractor.extract_syllables_from_file(input_path)

        # Generate output filenames using input filename and shared run timestamp
        syllables_path, metadata_path = generate_output_filename(
            output_dir=output_dir,
            run_timestamp=run_timestamp,
            input_filename=input_path.name,
        )

        # Save syllables
        extractor.save_syllables(syllables, syllables_path)

        # Save metadata
        result = ExtractionResult(
            syllables=syllables,
            language_code="en_US",
            min_syllable_length=min_len,
            max_syllable_length=max_len,
            input_path=input_path,
            only_hyphenated=True,
            total_words=stats["total_words"],
            fallback_count=stats["fallback_count"],
            rejected_syllables=stats["rejected_syllables"],
            processed_words=stats["processed_words"],
        )
        save_metadata(result, metadata_path)

        processing_time = time.perf_counter() - start_time

        if verbose:
            print(f"  ✓ Extracted {len(syllables)} syllables (en_US)")

        return FileProcessingResult(
            input_path=input_path,
            success=True,
            syllables_count=len(syllables),
            language_code="en_US",
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
            language_code="en_US",
            error_message=str(e),
            processing_time=processing_time,
        )


def process_batch(
    files: List[Path],
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
        print("Language:         en_US (CMUDict)")
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

Note: This extractor only supports English (CMUDict). For other languages, use syllable_extractor (pyphen).
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


def main_interactive():
    """
    Interactive mode entry point for the NLTK syllable extractor CLI.

    Workflow:
        1. Display tool information and CMUDict notice
        2. Configure extraction parameters (min/max syllable length)
        3. Prompt for input file path
        4. Extract syllables using CMUDict + onset/coda principles
        5. Generate timestamped output filenames
        6. Save syllables and metadata to separate files
        7. Display summary to console

    Output Files:
        - YYYYMMDD_HHMMSS.syllables.en_US.txt: One syllable per line, sorted
        - YYYYMMDD_HHMMSS.meta.en_US.txt: Extraction metadata and statistics

    Corpus Database Integration:
        All interactive mode extractions are automatically recorded to the corpus
        database ledger for build provenance tracking. Recording is optional -
        extraction succeeds even if ledger fails.

    Both files are saved to _working/output/ by default.
    """
    print("\n" + "=" * 70)
    print("NLTK SYLLABLE EXTRACTOR")
    print("=" * 70)
    print("\nThis tool extracts syllables using NLTK's CMU Pronouncing Dictionary")
    print("with phonetically-guided orthographic splitting (onset/coda principles).")
    print("\n⚠️  English only (CMUDict limitation)")
    print("Output is saved to _working/output/ by default.")
    print("=" * 70)

    # Configure extraction parameters
    print("\n" + "-" * 70)
    print("EXTRACTION SETTINGS")
    print("-" * 70)

    # Get min syllable length
    while True:
        min_len_str = input("\nMinimum syllable length (default: 1, no filtering): ").strip()
        if not min_len_str:
            min_len = 1
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
        max_len_str = input("Maximum syllable length (default: 999, no filtering): ").strip()
        if not max_len_str:
            max_len = 999
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

    # Initialize extractor
    try:
        extractor = NltkSyllableExtractor("en_US", min_len, max_len)
        print("✓ CMU Pronouncing Dictionary loaded")
    except (ImportError, LookupError) as e:
        print(f"\nError: {e}")
        sys.exit(1)

    # Get input file path
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
            run_id = ledger.start_run(
                extractor_tool="nltk_syllable_extractor",
                extractor_version=EXTRACTOR_VERSION,
                pyphen_lang=None,  # Not applicable for NLTK extractor
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

    # Extract syllables
    print(f"\n⏳ Processing {input_path}...")
    try:
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

    # Generate output filenames and create result object
    syllables_path, metadata_path = generate_output_filename(language_code="en_US")

    result = ExtractionResult(
        syllables=syllables,
        language_code="en_US",
        min_syllable_length=min_len,
        max_syllable_length=max_len,
        input_path=input_path,
        only_hyphenated=True,
        total_words=stats["total_words"],
        fallback_count=stats["fallback_count"],
        rejected_syllables=stats["rejected_syllables"],
        processed_words=stats["processed_words"],
    )

    # Save syllables
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

    # Save metadata
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
        record_corpus_db_safe("close ledger", lambda: ledger.close(), quiet=True)

    # Display summary to console
    print("\n" + result.format_metadata())

    # Get the run directory (parent of syllables dir)
    run_dir = syllables_path.parent.parent
    print(f"\n✓ Output saved to run directory: {run_dir}/")
    print(f"  - Syllables: {syllables_path.relative_to(DEFAULT_OUTPUT_DIR)}")
    print(f"  - Metadata:  {metadata_path.relative_to(DEFAULT_OUTPUT_DIR)}")
    print("\n✓ Done!\n")


def main_batch(args: argparse.Namespace):
    """
    Batch mode entry point for the NLTK syllable extractor CLI.

    This function processes multiple files based on command-line arguments,
    providing progress indicators and comprehensive error reporting.

    Args:
        args: Parsed command-line arguments from argparse.Namespace containing:
            - file: Single file path (optional)
            - files: List of file paths (optional)
            - source: Directory path for scanning (optional)
            - pattern: File pattern for directory scanning (default: "*.txt")
            - recursive: Whether to scan directories recursively
            - min: Minimum syllable length (default: 2)
            - max: Maximum syllable length (default: 8)
            - output: Output directory (default: _working/output/)
            - quiet: Suppress progress indicators
            - verbose: Show detailed processing information

    Corpus Database Integration:
        All batch mode extractions are automatically recorded to the corpus
        database ledger for build provenance tracking. Recording is optional -
        extraction succeeds even if ledger fails.

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

    # Initialize corpus_db ledger for provenance tracking
    run_id = None
    ledger = None

    if CORPUS_DB_AVAILABLE:
        try:
            ledger = CorpusLedger()
            run_id = ledger.start_run(
                extractor_tool="nltk_syllable_extractor",
                extractor_version=EXTRACTOR_VERSION,
                pyphen_lang=None,  # Not applicable for NLTK
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
            record_corpus_db_safe(
                "input", lambda: ledger.record_input(run_id, files_to_process[0]), quiet=args.quiet
            )
        elif args.files:
            for file_path in files_to_process:
                record_corpus_db_safe(
                    "input",
                    lambda fp=file_path: ledger.record_input(run_id, fp),  # type: ignore[misc]
                    quiet=args.quiet,
                )
        elif args.source:
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
        print("BATCH NLTK SYLLABLE EXTRACTION")
        print("=" * 70)
        print(f"Files to process:   {len(files_to_process)}")
        print("Language:           en_US (CMUDict + onset/coda)")
        print(f"Syllable length:    {args.min}-{args.max} characters")
        print(f"Output directory:   {output_dir}")
        print("=" * 70 + "\n")

    # Process batch
    batch_result = process_batch(
        files=files_to_process,
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
        record_corpus_db_safe("close ledger", lambda: ledger.close(), quiet=True)

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
    Main entry point for the NLTK syllable extractor CLI.

    This function determines whether to run in interactive or batch mode
    based on the presence of command-line arguments.

    Modes:
        - Interactive Mode: No arguments provided. Prompts user for all settings.
        - Batch Mode: Arguments provided. Processes files based on CLI flags.

    Examples:
        Interactive mode (no arguments):
            $ python -m build_tools.nltk_syllable_extractor

        Batch mode (with arguments):
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
        # Batch mode
        main_batch(args)
    else:
        # Interactive mode
        main_interactive()
