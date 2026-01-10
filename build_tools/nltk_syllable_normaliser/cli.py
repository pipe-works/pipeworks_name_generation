"""
Command-line interface for NLTK syllable normalization pipeline.

This module provides the main CLI entry point for the nltk_syllable_normaliser tool,
which processes NLTK extractor output with fragment cleaning + normalization pipeline.
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Import shared components from pyphen normaliser
from build_tools.pyphen_syllable_normaliser import (
    FileAggregator,
    FrequencyAnalyzer,
    NormalizationConfig,
    NormalizationResult,
    NormalizationStats,
    discover_input_files,
    normalize_batch,
)

from .fragment_cleaner import FragmentCleaner


def detect_nltk_run_directories(source_dir: Path) -> List[Path]:
    """
    Detect NLTK run directories within source directory.

    Searches for directories matching the pattern YYYYMMDD_HHMMSS_nltk/
    which contain a syllables/ subdirectory.

    Args:
        source_dir: Directory to search for NLTK run directories.

    Returns:
        List of Path objects pointing to NLTK run directories,
        sorted by directory name (chronological order).

    Example:
        >>> source = Path("_working/output/")
        >>> runs = detect_nltk_run_directories(source)
        >>> for run in runs:
        ...     print(run.name)
        20260110_095213_nltk
        20260110_143022_nltk
    """
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")

    if not source_dir.is_dir():
        raise ValueError(f"Path is not a directory: {source_dir}")

    # Find directories ending with _nltk that have syllables/ subdirectory
    nltk_dirs = []
    for item in source_dir.iterdir():
        if item.is_dir() and item.name.endswith("_nltk"):
            syllables_dir = item / "syllables"
            if syllables_dir.exists() and syllables_dir.is_dir():
                nltk_dirs.append(item)

    return sorted(nltk_dirs)


def run_full_pipeline(
    run_directory: Path,
    config: NormalizationConfig,
    verbose: bool = False,
    skip_fragment_cleaning: bool = False,
) -> NormalizationResult:
    """
    Run complete NLTK normalization pipeline with in-place processing.

    Executes the full NLTK-specific workflow:
    1. Aggregate syllables from run_directory/syllables/*.txt
    2. Fragment cleaning (NLTK-specific preprocessing)
    3. Canonicalize syllables (Unicode normalization, etc.)
    4. Frequency analysis
    5. Write 5 output files to run_directory (in-place)

    Args:
        run_directory: NLTK run directory (e.g., _working/output/20260110_095213_nltk/).
        config: NormalizationConfig specifying normalization parameters.
        verbose: If True, print detailed progress information.
        skip_fragment_cleaning: If True, skip fragment cleaning step (for comparison).

    Returns:
        NormalizationResult containing all outputs, statistics, and file paths.

    Raises:
        FileNotFoundError: If run_directory or syllables/ subdirectory doesn't exist.
        ValueError: If run_directory is not a directory.

    Example:
        >>> from pathlib import Path
        >>> config = NormalizationConfig(min_length=2, max_length=8)
        >>> run_dir = Path("_working/output/20260110_095213_nltk/")
        >>> result = run_full_pipeline(
        ...     run_directory=run_dir,
        ...     config=config,
        ...     verbose=True
        ... )
        >>> result.stats.raw_count
        15234
        >>> result.stats.unique_canonical
        4821
    """
    start_time = time.time()
    timestamp = datetime.now()

    # Validate run directory
    if not run_directory.exists():
        raise FileNotFoundError(f"Run directory does not exist: {run_directory}")

    if not run_directory.is_dir():
        raise ValueError(f"Path is not a directory: {run_directory}")

    syllables_dir = run_directory / "syllables"
    if not syllables_dir.exists():
        raise FileNotFoundError(
            f"Syllables directory does not exist: {syllables_dir}. "
            f"Expected NLTK run directory structure with syllables/ subdirectory."
        )

    # Define output file paths (in run directory, with nltk_ prefix)
    raw_file = run_directory / "nltk_syllables_raw.txt"
    canonical_file = run_directory / "nltk_syllables_canonicalised.txt"
    frequency_file = run_directory / "nltk_syllables_frequencies.json"
    unique_file = run_directory / "nltk_syllables_unique.txt"
    meta_file = run_directory / "nltk_normalization_meta.txt"

    print("\n" + "=" * 70)
    print("NLTK SYLLABLE NORMALIZATION PIPELINE")
    print("=" * 70)
    print(f"Run Directory:       {run_directory.name}")
    print(f"Syllables Source:    {syllables_dir}")
    print(f"Fragment Cleaning:   {'Disabled' if skip_fragment_cleaning else 'Enabled'}")
    print(f"Timestamp:           {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Discover input files from syllables/ subdirectory
    print("\n⏳ Discovering input files...")
    input_files = discover_input_files(syllables_dir, pattern="*.txt", recursive=False)
    print(f"✓ Found {len(input_files)} syllable files")

    if verbose:
        for f in input_files[:5]:
            print(f"  - {f.name}")
        if len(input_files) > 5:
            print(f"  ... and {len(input_files) - 5} more")

    # Step 1: Aggregate files
    print("\n⏳ Step 1: Aggregating syllable files...")
    aggregator = FileAggregator()
    raw_syllables = aggregator.aggregate_files(input_files)
    aggregator.save_raw_syllables(raw_syllables, raw_file)

    raw_count = len(raw_syllables)
    print(f"✓ Aggregated {raw_count:,} syllables → {raw_file.name}")

    if verbose:
        print(f"  Sample raw: {raw_syllables[:5]}")

    # Step 2: Fragment Cleaning (NLTK-specific)
    after_fragment_cleaning = raw_count
    if not skip_fragment_cleaning:
        print("\n⏳ Step 2: Cleaning fragments (NLTK-specific)...")
        cleaner = FragmentCleaner()
        cleaned_syllables = cleaner.clean_fragments(raw_syllables)
        after_fragment_cleaning = len(cleaned_syllables)

        reduction = raw_count - after_fragment_cleaning
        print(f"✓ Cleaned {raw_count:,} → {after_fragment_cleaning:,} syllables")
        print(f"  Merged {reduction:,} single-letter fragments")

        if verbose:
            print(f"  Sample cleaned: {cleaned_syllables[:5]}")

        # Use cleaned syllables for canonicalization
        syllables_for_canon = cleaned_syllables
    else:
        print("\n⏳ Step 2: Fragment cleaning skipped")
        syllables_for_canon = raw_syllables

    # Step 3: Canonicalization
    print("\n⏳ Step 3: Canonicalizing syllables...")
    canonical_syllables, rejection_stats = normalize_batch(syllables_for_canon, config)

    # Save canonicalized syllables
    with canonical_file.open("w", encoding="utf-8") as file_handle:
        for syllable in canonical_syllables:
            file_handle.write(f"{syllable}\n")

    after_canonicalization = len(canonical_syllables)
    print(f"✓ Canonicalized {after_canonicalization:,} syllables → {canonical_file.name}")

    rejected_total = (
        rejection_stats["rejected_empty"]
        + rejection_stats["rejected_charset"]
        + rejection_stats["rejected_length"]
    )
    print(f"  Rejected: {rejected_total:,} syllables")

    if verbose:
        print(f"    Empty: {rejection_stats['rejected_empty']:,}")
        print(f"    Invalid charset: {rejection_stats['rejected_charset']:,}")
        print(f"    Length constraint: {rejection_stats['rejected_length']:,}")
        print(f"  Sample canonical: {canonical_syllables[:5]}")

    # Step 4: Frequency analysis
    print("\n⏳ Step 4: Analyzing frequencies...")
    analyzer = FrequencyAnalyzer()

    # Calculate frequencies
    frequencies = analyzer.calculate_frequencies(canonical_syllables)
    analyzer.save_frequencies(frequencies, frequency_file)
    print(f"✓ Saved frequency data → {frequency_file.name}")

    # Extract unique syllables
    unique_syllables = analyzer.extract_unique_syllables(canonical_syllables)
    analyzer.save_unique_syllables(unique_syllables, unique_file)
    unique_count = len(unique_syllables)
    print(f"✓ Extracted {unique_count:,} unique syllables → {unique_file.name}")

    if verbose:
        # Show top 5 most frequent
        entries = analyzer.create_frequency_entries(frequencies)
        print("\n  Top 5 most frequent:")
        for entry in entries[:5]:
            print(
                f"    {entry.canonical:10s} ({entry.frequency:5,} occurrences, {entry.percentage:5.1f}%)"
            )

    # Create statistics object (with NLTK-specific stats)
    stats = NormalizationStats(
        raw_count=raw_count,
        after_canonicalization=after_canonicalization,
        rejected_charset=rejection_stats["rejected_charset"],
        rejected_length=rejection_stats["rejected_length"],
        rejected_empty=rejection_stats["rejected_empty"],
        unique_canonical=unique_count,
        processing_time=time.time() - start_time,
    )

    # Create result object
    result = NormalizationResult(
        config=config,
        stats=stats,
        frequencies=frequencies,
        unique_syllables=unique_syllables,
        input_files=input_files,
        output_dir=run_directory,  # Output is in run directory (in-place)
        timestamp=timestamp,
        raw_file=raw_file,
        canonical_file=canonical_file,
        frequency_file=frequency_file,
        unique_file=unique_file,
        meta_file=meta_file,
    )

    # Save metadata report
    print("\n⏳ Generating metadata report...")
    metadata_content = result.format_metadata()

    # Add NLTK-specific metadata
    nltk_metadata = "\n\nNLTK-Specific Processing:\n"
    nltk_metadata += (
        f"  Fragment Cleaning:     {'Disabled' if skip_fragment_cleaning else 'Enabled'}\n"
    )
    if not skip_fragment_cleaning:
        reduction = raw_count - after_fragment_cleaning
        nltk_metadata += f"  Before Cleaning:       {raw_count:,} syllables\n"
        nltk_metadata += f"  After Cleaning:        {after_fragment_cleaning:,} syllables\n"
        nltk_metadata += f"  Fragments Merged:      {reduction:,}\n"

    metadata_content += nltk_metadata

    with meta_file.open("w", encoding="utf-8") as file_handle:
        file_handle.write(metadata_content)
    print(f"✓ Saved metadata report → {meta_file.name}")

    # Print summary
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print(f"Total Time:          {stats.processing_time:.2f}s")
    print(f"Raw Syllables:       {stats.raw_count:,}")
    if not skip_fragment_cleaning:
        print(f"After Cleaning:      {after_fragment_cleaning:,}")
    print(f"Canonical:           {stats.after_canonicalization:,}")
    print(f"Unique:              {stats.unique_canonical:,}")
    print(f"Rejection Rate:      {stats.rejection_rate:.1f}%")
    print("=" * 70 + "\n")

    return result


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and return the argument parser for NLTK syllable normaliser.

    Returns:
        Configured ArgumentParser ready to parse command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="NLTK Syllable Normaliser - Fragment cleaning + 3-step normalization pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process specific NLTK run directory
  python -m build_tools.nltk_syllable_normaliser --run-dir _working/output/20260110_095213_nltk/

  # Auto-detect and process all NLTK run directories
  python -m build_tools.nltk_syllable_normaliser --source _working/output/

  # Custom normalization config
  python -m build_tools.nltk_syllable_normaliser \\
    --run-dir _working/output/20260110_095213_nltk/ \\
    --min 2 --max 8

  # Skip fragment cleaning (for comparison with pyphen)
  python -m build_tools.nltk_syllable_normaliser \\
    --run-dir _working/output/20260110_095213_nltk/ \\
    --no-fragment-cleaning
        """,
    )

    # Input specification (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--run-dir",
        type=Path,
        help="Specific NLTK run directory to process (e.g., _working/output/20260110_095213_nltk/)",
    )
    input_group.add_argument(
        "--source",
        type=Path,
        help="Directory to scan for NLTK run directories (auto-detects *_nltk/ directories)",
    )

    # Normalization configuration
    parser.add_argument(
        "--min",
        type=int,
        default=2,
        help="Minimum syllable length (characters). Default: 2",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=20,
        help="Maximum syllable length (characters). Default: 20",
    )
    parser.add_argument(
        "--charset",
        type=str,
        default="abcdefghijklmnopqrstuvwxyz",
        help="Allowed character set for syllables. Default: a-z",
    )
    parser.add_argument(
        "--unicode-form",
        type=str,
        choices=["NFC", "NFD", "NFKC", "NFKD"],
        default="NFKD",
        help="Unicode normalization form. Default: NFKD",
    )

    # NLTK-specific options
    parser.add_argument(
        "--no-fragment-cleaning",
        action="store_true",
        help="Skip fragment cleaning step (for comparison purposes)",
    )

    # Output control
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output with detailed progress information",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress all output except errors",
    )

    return parser


def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = create_argument_parser()
    return parser.parse_args(args)


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for CLI.

    Args:
        argv: Command-line arguments (for testing). If None, uses sys.argv.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    args = parse_arguments(argv)

    # Validate arguments
    if args.min < 1:
        print("ERROR: --min must be >= 1", file=sys.stderr)
        return 1

    if args.max < args.min:
        print(f"ERROR: --max ({args.max}) must be >= --min ({args.min})", file=sys.stderr)
        return 1

    # Create normalization config
    config = NormalizationConfig(
        min_length=args.min,
        max_length=args.max,
        allowed_charset=args.charset,
        unicode_form=args.unicode_form,
    )

    try:
        # Determine run directories to process
        if args.run_dir:
            run_dirs = [args.run_dir]
        else:
            # Auto-detect NLTK run directories
            run_dirs = detect_nltk_run_directories(args.source)
            if not run_dirs:
                print(f"No NLTK run directories found in: {args.source}", file=sys.stderr)
                print(
                    "NLTK run directories should match pattern: YYYYMMDD_HHMMSS_nltk/",
                    file=sys.stderr,
                )
                return 1

            if not args.quiet:
                print(f"Found {len(run_dirs)} NLTK run directories:")
                for run_dir in run_dirs:
                    print(f"  - {run_dir.name}")

        # Process each run directory
        for run_dir in run_dirs:
            _ = run_full_pipeline(
                run_directory=run_dir,
                config=config,
                verbose=args.verbose,
                skip_fragment_cleaning=args.no_fragment_cleaning,
            )

            if not args.quiet:
                print(f"\n✓ Successfully processed: {run_dir.name}")
                print(f"  Outputs written to: {run_dir}")

        return 0

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
