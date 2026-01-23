"""
Batch mode for the NLTK syllable extractor.

This module provides batch processing functionality for extracting syllables
from multiple files using NLTK's CMU Pronouncing Dictionary.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import List

from build_tools.tui_common.batch import (
    collect_files_from_args,
    run_batch_extraction,
    validate_extraction_params,
)
from build_tools.tui_common.ledger import ExtractionLedgerContext

from .extractor import NltkSyllableExtractor
from .file_io import DEFAULT_OUTPUT_DIR, generate_output_filename, save_metadata
from .models import BatchResult, ExtractionResult, FileProcessingResult

# Version for ledger
try:
    from build_tools.nltk_syllable_extractor import __version__ as _extractor_version
except (ImportError, AttributeError):
    _extractor_version = "unknown"


def process_single_file(
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
        returned in the FileProcessingResult.error_message field.
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

    This is a backwards-compatible wrapper around run_batch_extraction.

    Args:
        files: List of input file paths to process
        min_len: Minimum syllable length to include
        max_len: Maximum syllable length to include
        output_dir: Output directory for all results (created if needed)
        quiet: If True, suppress all output except errors (default: False)
        verbose: If True, show detailed progress for each file (default: False).

    Returns:
        BatchResult with overall statistics and individual file results.
    """
    file_processor = _create_file_processor(
        min_len=min_len,
        max_len=max_len,
    )

    return run_batch_extraction(  # type: ignore[no-any-return]
        files=files,
        output_dir=output_dir,
        process_file_func=file_processor,
        batch_result_class=BatchResult,
        extractor_name="nltk",
        language_display="en_US (CMUDict)",
        min_len=min_len,
        max_len=max_len,
        quiet=quiet,
        verbose=verbose,
    )


def _create_file_processor(min_len: int, max_len: int):
    """Create a single-file processor function with bound parameters."""

    def processor(
        input_path: Path,
        output_dir: Path,
        run_timestamp: str,
        verbose: bool,
    ) -> FileProcessingResult:
        return process_single_file(
            input_path=input_path,
            min_len=min_len,
            max_len=max_len,
            output_dir=output_dir,
            run_timestamp=run_timestamp,
            verbose=verbose,
        )

    return processor


def run_batch(args: argparse.Namespace) -> None:
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
            - min: Minimum syllable length (default: 1)
            - max: Maximum syllable length (default: 999)
            - output: Output directory (default: _working/output/)
            - quiet: Suppress progress indicators
            - verbose: Show detailed processing information

    Exit Codes:
        0: All files processed successfully
        1: One or more files failed to process

    Raises:
        SystemExit: On validation errors or processing completion
    """
    # Validate parameters
    validate_extraction_params(args.min, args.max)

    # Collect files to process
    try:
        files_to_process, source_dir = collect_files_from_args(
            file_arg=args.file,
            files_arg=args.files,
            source_arg=args.source,
            pattern=args.pattern,
            recursive=args.recursive,
        )
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

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

    # Use ledger context for corpus DB integration
    with ExtractionLedgerContext(
        extractor_tool="nltk_syllable_extractor",
        extractor_version=_extractor_version,
        pyphen_lang=None,  # Not applicable for NLTK
        min_len=args.min,
        max_len=args.max,
        recursive=args.recursive,
        pattern=args.pattern,
        quiet=args.quiet,
    ) as ledger_ctx:
        # Record inputs
        ledger_ctx.record_inputs(files_to_process, source_dir=source_dir)

        # Create file processor with bound parameters
        file_processor = _create_file_processor(
            min_len=args.min,
            max_len=args.max,
        )

        # Process batch
        batch_result = run_batch_extraction(
            files=files_to_process,
            output_dir=output_dir,
            process_file_func=file_processor,
            batch_result_class=BatchResult,
            extractor_name="nltk",
            language_display="en_US (CMUDict)",
            min_len=args.min,
            max_len=args.max,
            quiet=args.quiet,
            verbose=args.verbose,
        )

        # Record outputs
        for result in batch_result.results:
            if result.success and result.syllables_output_path is not None:
                ledger_ctx.record_output(
                    output_path=result.syllables_output_path,
                    unique_syllable_count=result.syllables_count,
                    meta_path=result.metadata_output_path,
                )

        # Set result based on batch outcome
        ledger_ctx.set_result(success=(batch_result.failed == 0))

    # Display summary
    if not args.quiet:
        print("\n" + batch_result.format_summary())

    # Exit with appropriate code
    if batch_result.failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)
