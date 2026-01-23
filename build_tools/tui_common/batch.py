"""
Shared batch processing utilities for syllable extractors.

This module provides common batch processing orchestration that can be used
by both pyphen and NLTK syllable extractors. It abstracts the common patterns
of processing multiple files while allowing extractor-specific logic.

Usage::

    from build_tools.tui_common.batch import run_batch_extraction

    # Define extractor-specific single-file processor
    def process_file(input_path, output_dir, run_timestamp, verbose):
        # ... extraction logic ...
        return FileProcessingResult(...)

    # Run batch with shared orchestration
    result = run_batch_extraction(
        files=files_to_process,
        output_dir=output_dir,
        process_file_func=process_file,
        extractor_name="pyphen",
        language_display="en_US",
        min_len=2,
        max_len=8,
        quiet=False,
        verbose=True,
    )
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, List, Protocol, TypeVar

if TYPE_CHECKING:
    pass


class FileProcessingResultProtocol(Protocol):
    """Protocol for file processing result objects."""

    input_path: Path
    success: bool
    syllables_count: int
    language_code: str
    error_message: str | None
    processing_time: float
    syllables_output_path: Path | None
    metadata_output_path: Path | None


T = TypeVar("T", bound=FileProcessingResultProtocol)


# Type alias for single-file processor function
SingleFileProcessor = Callable[[Path, Path, str, bool], FileProcessingResultProtocol]


def run_batch_extraction(
    files: List[Path],
    output_dir: Path,
    process_file_func: SingleFileProcessor,
    batch_result_class: type[Any],
    extractor_name: str,
    language_display: str,
    min_len: int,
    max_len: int,
    quiet: bool = False,
    verbose: bool = False,
) -> Any:
    """
    Run batch extraction with shared orchestration logic.

    This function provides the common batch processing pattern:
    - Generate shared timestamp for the batch run
    - Create output directory
    - Display batch header
    - Process each file with progress indicators
    - Collect and return results

    Args:
        files: List of input file paths to process
        output_dir: Output directory for all results
        process_file_func: Callable that processes a single file.
            Signature: (input_path, output_dir, run_timestamp, verbose) -> FileProcessingResult
        batch_result_class: Class to use for BatchResult (from models module)
        extractor_name: Name of extractor for display ("pyphen" or "nltk")
        language_display: Language string for display (e.g., "en_US", "auto")
        min_len: Minimum syllable length (for display)
        max_len: Maximum syllable length (for display)
        quiet: Suppress all output except errors
        verbose: Show detailed progress for each file

    Returns:
        BatchResult with overall statistics and individual file results.

    Example:
        >>> from build_tools.pyphen_syllable_extractor.models import BatchResult
        >>>
        >>> def my_processor(path, out_dir, timestamp, verbose):
        ...     # Process file and return FileProcessingResult
        ...     pass
        >>>
        >>> result = run_batch_extraction(
        ...     files=[Path("a.txt"), Path("b.txt")],
        ...     output_dir=Path("output/"),
        ...     process_file_func=my_processor,
        ...     batch_result_class=BatchResult,
        ...     extractor_name="pyphen",
        ...     language_display="en_US",
        ...     min_len=2,
        ...     max_len=8,
        ... )
    """
    start_time = time.perf_counter()

    # Generate a single timestamp for the entire batch run
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Compute run directory path for display
    run_dir = output_dir / f"{run_timestamp}_{extractor_name}"

    if not quiet:
        print(f"\n{'='*70}")
        print(f"BATCH PROCESSING - {len(files)} files")
        print(f"{'='*70}")
        print(f"Language:         {language_display}")
        print(f"Syllable Length:  {min_len}-{max_len} characters")
        print(f"Run Directory:    {run_dir}")
        print(f"{'='*70}\n")

    results: List[FileProcessingResultProtocol] = []
    successful = 0
    failed = 0

    for idx, file_path in enumerate(files, 1):
        if not quiet and not verbose:
            # Progress indicator (non-verbose mode)
            print(f"[{idx}/{len(files)}] Processing {file_path.name}...", end=" ", flush=True)

        result = process_file_func(
            file_path,
            output_dir,
            run_timestamp,
            verbose and not quiet,
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

    return batch_result_class(
        total_files=len(files),
        successful=successful,
        failed=failed,
        results=results,
        total_time=total_time,
        output_directory=run_dir,
    )


def collect_files_from_args(
    file_arg: Path | None,
    files_arg: List[Path] | None,
    source_arg: Path | None,
    pattern: str,
    recursive: bool,
) -> tuple[List[Path], Path | None]:
    """
    Collect files to process from CLI arguments.

    Validates and resolves paths from the three mutually exclusive input modes:
    - Single file (--file)
    - Multiple files (--files)
    - Directory scan (--source)

    Args:
        file_arg: Single file path (from --file)
        files_arg: List of file paths (from --files)
        source_arg: Directory path (from --source)
        pattern: File pattern for directory scanning
        recursive: Whether to scan directories recursively

    Returns:
        Tuple of (list of resolved file paths, source directory or None)

    Raises:
        ValueError: If validation fails (file not found, not a file, etc.)
        SystemExit: If no input is specified

    Example:
        >>> files, source_dir = collect_files_from_args(
        ...     file_arg=Path("input.txt"),
        ...     files_arg=None,
        ...     source_arg=None,
        ...     pattern="*.txt",
        ...     recursive=False,
        ... )
    """
    import sys

    from build_tools.tui_common.cli_utils import discover_files

    files_to_process: List[Path] = []
    source_dir: Path | None = None

    if file_arg:
        # Single file
        file_path = Path(file_arg).expanduser().resolve()
        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        files_to_process.append(file_path)

    elif files_arg:
        # Multiple files
        for file_str in files_arg:
            file_path = Path(file_str).expanduser().resolve()
            if not file_path.exists():
                raise ValueError(f"File not found: {file_path}")
            if not file_path.is_file():
                raise ValueError(f"Path is not a file: {file_path}")
            files_to_process.append(file_path)

    elif source_arg:
        # Directory scanning
        source_path = Path(source_arg).expanduser().resolve()
        if not source_path.exists():
            raise ValueError(f"Source directory not found: {source_path}")
        if not source_path.is_dir():
            raise ValueError(f"Source path is not a directory: {source_path}")

        files_to_process = discover_files(source=source_path, pattern=pattern, recursive=recursive)

        if not files_to_process:
            raise ValueError(f"No files matching pattern '{pattern}' found in {source_path}")

        source_dir = source_path

    else:
        print("Error: No input specified. Use --file, --files, or --source")
        sys.exit(1)

    return files_to_process, source_dir


def validate_extraction_params(min_len: int, max_len: int) -> None:
    """
    Validate extraction parameters.

    Args:
        min_len: Minimum syllable length
        max_len: Maximum syllable length

    Raises:
        SystemExit: If validation fails
    """
    import sys

    if min_len < 1:
        print("Error: Minimum syllable length must be at least 1")
        sys.exit(1)

    if max_len < min_len:
        print(f"Error: Maximum syllable length ({max_len}) must be >= minimum ({min_len})")
        sys.exit(1)


__all__ = [
    "run_batch_extraction",
    "collect_files_from_args",
    "validate_extraction_params",
    "SingleFileProcessor",
]
