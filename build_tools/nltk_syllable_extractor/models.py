"""
Data models for NLTK-based syllable extraction results.

This module defines the data structures used to represent extraction results
and their associated metadata for the NLTK syllable extractor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class ExtractionResult:
    """
    Container for syllable extraction results and associated metadata.

    This dataclass stores both the extracted syllables and all relevant
    metadata about the extraction process for reporting and persistence.

    Attributes:
        syllables: List of all syllables extracted (includes duplicates)
        language_code: Language code used (always "en_US" for NLTK extractor)
        min_syllable_length: Minimum syllable length constraint
        max_syllable_length: Maximum syllable length constraint
        input_path: Path to the input text file
        timestamp: When the extraction was performed
        only_hyphenated: Whether whole words were excluded
        length_distribution: Map of syllable length to count
        sample_syllables: Representative sample of extracted syllables
        total_words: Total words found in source text
        fallback_count: Words not in CMUDict (used fallback heuristics)
        rejected_syllables: Syllables rejected due to length constraints
        processed_words: Words that were successfully processed
    """

    syllables: list[str]
    language_code: str
    min_syllable_length: int
    max_syllable_length: int
    input_path: Path
    timestamp: datetime = field(default_factory=datetime.now)
    only_hyphenated: bool = True
    length_distribution: dict[int, int] = field(default_factory=dict)
    sample_syllables: list[str] = field(default_factory=list)
    total_words: int = 0
    fallback_count: int = 0
    rejected_syllables: int = 0
    processed_words: int = 0

    def __post_init__(self):
        """Calculate derived fields after initialization."""
        # Calculate length distribution (from unique syllables for display)
        unique_syllables = set(self.syllables)
        for syllable in unique_syllables:
            length = len(syllable)
            self.length_distribution[length] = self.length_distribution.get(length, 0) + 1

        # Generate sample syllables (first 15 unique, sorted)
        sample_size = min(15, len(unique_syllables))
        self.sample_syllables = sorted(unique_syllables)[:sample_size]

    def format_metadata(self) -> str:
        """
        Format extraction metadata as a human-readable string.

        Returns:
            Multi-line string containing all extraction metadata formatted
            for display or file output.
        """
        lines = []
        lines.append("=" * 70)
        lines.append("NLTK SYLLABLE EXTRACTION METADATA")
        lines.append("=" * 70)
        lines.append(f"Extraction Date:    {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("Extractor:          nltk_syllable_extractor (CMUDict + onset/coda)")
        lines.append(f"Language Code:      {self.language_code}")
        lines.append(
            f"Syllable Length:    {self.min_syllable_length}-{self.max_syllable_length} characters"
        )
        lines.append(f"Input File:         {self.input_path}")
        lines.append(f"Total Syllables:    {len(self.syllables):,}")
        lines.append(f"Unique Syllables:   {len(set(self.syllables)):,}")
        lines.append("=" * 70)

        # Processing statistics
        lines.append("\nProcessing Statistics:")
        lines.append(f"  Total Words:        {self.total_words:,}")
        lines.append(f"  Processed Words:    {self.processed_words:,}")
        lines.append(f"  Fallback Used:      {self.fallback_count:,} (not in CMUDict)")
        lines.append(f"  Rejected Syllables: {self.rejected_syllables:,} (length filter)")
        if self.total_words > 0:
            processed_pct = (self.processed_words / self.total_words) * 100
            fallback_pct = (self.fallback_count / self.total_words) * 100
            lines.append(f"  Process Rate:       {processed_pct:.1f}%")
            lines.append(f"  Fallback Rate:      {fallback_pct:.1f}%")

        # Length distribution
        if self.length_distribution:
            lines.append("\nSyllable Length Distribution:")
            for length in sorted(self.length_distribution.keys()):
                count = self.length_distribution[length]
                bar = "█" * min(40, count)
                lines.append(f"  {length:2d} chars: {count:4d} {bar}")

        # Sample syllables
        if self.sample_syllables:
            unique_count = len(set(self.syllables))
            lines.append(f"\nSample Syllables (first {len(self.sample_syllables)}):")
            for syllable in self.sample_syllables:
                lines.append(f"  - {syllable}")
            if unique_count > len(self.sample_syllables):
                lines.append(f"  ... and {unique_count - len(self.sample_syllables)} more")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)


@dataclass
class FileProcessingResult:
    """
    Result of processing a single file in batch mode.

    This dataclass stores the outcome of processing one file during batch
    operations, including success status, extracted syllables count, and
    any error information if processing failed.

    Attributes:
        input_path: Path to the input file that was processed
        success: Whether processing completed successfully
        syllables_count: Number of unique syllables extracted (0 if failed)
        language_code: Language code used (always "en_US")
        syllables_output_path: Path where syllables were saved (None if failed)
        metadata_output_path: Path where metadata was saved (None if failed)
        error_message: Error message if processing failed (None if success)
        processing_time: Time taken to process this file in seconds

    Example:
        >>> result = FileProcessingResult(
        ...     input_path=Path("book.txt"),
        ...     success=True,
        ...     syllables_count=245,
        ...     language_code="en_US",
        ...     syllables_output_path=Path("output.syllables.en_US.txt"),
        ...     metadata_output_path=Path("output.meta.en_US.txt"),
        ...     processing_time=2.45
        ... )
        >>> print(f"Processed {result.syllables_count} syllables")
        Processed 245 syllables
    """

    input_path: Path
    success: bool
    syllables_count: int
    language_code: str
    syllables_output_path: Path | None = None
    metadata_output_path: Path | None = None
    error_message: str | None = None
    processing_time: float = 0.0


@dataclass
class BatchResult:
    """
    Aggregate results from a batch processing operation.

    This dataclass stores summary statistics and individual file results
    from processing multiple files in batch mode.

    Attributes:
        total_files: Total number of files attempted in the batch
        successful: Number of files processed successfully
        failed: Number of files that failed to process
        results: List of individual FileProcessingResult objects
        total_time: Total time taken for entire batch operation in seconds
        output_directory: Directory where all outputs were saved

    Example:
        >>> result = BatchResult(
        ...     total_files=5,
        ...     successful=4,
        ...     failed=1,
        ...     results=[...],
        ...     total_time=12.34,
        ...     output_directory=Path("_working/output")
        ... )
        >>> print(f"Success rate: {result.successful/result.total_files*100:.1f}%")
        Success rate: 80.0%
    """

    total_files: int
    successful: int
    failed: int
    results: list[FileProcessingResult]
    total_time: float
    output_directory: Path

    def format_summary(self) -> str:
        """
        Format batch processing summary as a human-readable string.

        Creates a detailed summary report showing overall statistics,
        successful extractions with details, and failed files with
        error messages.

        Returns:
            Multi-line formatted string with batch statistics and results

        Example:
            >>> summary = batch_result.format_summary()
            >>> print(summary)
            ======================================================================
            BATCH PROCESSING SUMMARY
            ======================================================================
            Total Files:        5
            Successful:         4 (80.0%)
            ...
        """
        lines = []
        lines.append("=" * 70)
        lines.append("BATCH PROCESSING SUMMARY")
        lines.append("=" * 70)
        lines.append(f"Total Files:        {self.total_files}")
        lines.append(
            f"Successful:         {self.successful} "
            f"({self.successful/self.total_files*100:.1f}%)"
        )
        lines.append(f"Failed:             {self.failed} ({self.failed/self.total_files*100:.1f}%)")
        lines.append(f"Total Time:         {self.total_time:.2f}s")
        lines.append(f"Output Directory:   {self.output_directory}")
        lines.append("=" * 70)

        # Successful files summary
        if self.successful > 0:
            lines.append("\nSuccessful Extractions:")
            for result in self.results:
                if result.success:
                    lines.append(
                        f"  ✓ {result.input_path.name:40s} "
                        f"({result.syllables_count:4d} syllables, "
                        f"{result.language_code:6s}, "
                        f"{result.processing_time:.2f}s)"
                    )

        # Failed files summary
        if self.failed > 0:
            lines.append("\nFailed Extractions:")
            for result in self.results:
                if not result.success:
                    lines.append(f"  ✗ {result.input_path.name:40s} - {result.error_message}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)
