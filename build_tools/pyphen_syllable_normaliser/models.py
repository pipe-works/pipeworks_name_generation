"""
Data models for syllable normalization.

This module defines the data structures used to represent normalization
configuration, statistics, and results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class NormalizationConfig:
    """
    Configuration for syllable normalization process.

    This dataclass stores all parameters that control how syllables are
    normalized to canonical form.

    Attributes:
        min_length: Minimum syllable length (characters). Syllables shorter
            than this are rejected. Default: 2
        max_length: Maximum syllable length (characters). Syllables longer
            than this are rejected. Default: 20
        allowed_charset: String of allowed characters. Only syllables
            containing these characters (after normalization) are kept.
            Default: "abcdefghijklmnopqrstuvwxyz"
        unicode_form: Unicode normalization form. Options: "NFC", "NFD",
            "NFKC", "NFKD". Default: "NFKD" (compatibility decomposition)

    Example:
        >>> config = NormalizationConfig(min_length=3, max_length=10)
        >>> config.min_length
        3
        >>> config.allowed_charset
        'abcdefghijklmnopqrstuvwxyz'
    """

    min_length: int = 2
    max_length: int = 20
    allowed_charset: str = "abcdefghijklmnopqrstuvwxyz"
    unicode_form: str = "NFKD"

    def __post_init__(self):
        """Validate configuration parameters after initialization."""
        if self.min_length < 1:
            raise ValueError(f"min_length must be >= 1, got {self.min_length}")
        if self.max_length < self.min_length:
            raise ValueError(
                f"max_length ({self.max_length}) must be >= min_length ({self.min_length})"
            )
        if self.unicode_form not in ("NFC", "NFD", "NFKC", "NFKD"):
            raise ValueError(
                f"unicode_form must be one of NFC, NFD, NFKC, NFKD, got {self.unicode_form}"
            )


@dataclass
class NormalizationStats:
    """
    Statistics from the syllable normalization process.

    This dataclass tracks counts and metrics throughout the normalization
    pipeline, useful for understanding data quality and processing results.

    Attributes:
        raw_count: Total number of syllables in raw input (before normalization)
        after_canonicalization: Number of syllables after normalization
        rejected_charset: Syllables rejected due to invalid characters
        rejected_length: Syllables rejected due to length constraints
        rejected_empty: Syllables that became empty after normalization
        unique_canonical: Number of unique canonical syllables
        processing_time: Total processing time in seconds

    Example:
        >>> stats = NormalizationStats(
        ...     raw_count=1000,
        ...     after_canonicalization=950,
        ...     rejected_charset=30,
        ...     rejected_length=20,
        ...     rejected_empty=0,
        ...     unique_canonical=412,
        ...     processing_time=1.5
        ... )
        >>> stats.rejection_rate
        5.0
    """

    raw_count: int = 0
    after_canonicalization: int = 0
    rejected_charset: int = 0
    rejected_length: int = 0
    rejected_empty: int = 0
    unique_canonical: int = 0
    processing_time: float = 0.0

    @property
    def total_rejected(self) -> int:
        """Calculate total number of rejected syllables."""
        return self.rejected_charset + self.rejected_length + self.rejected_empty

    @property
    def rejection_rate(self) -> float:
        """Calculate rejection rate as percentage of raw count."""
        if self.raw_count == 0:
            return 0.0
        return (self.total_rejected / self.raw_count) * 100


@dataclass
class FrequencyEntry:
    """
    Single syllable with frequency and ranking information.

    This dataclass represents one syllable in the frequency analysis,
    including its occurrence count and relative ranking.

    Attributes:
        canonical: The canonical form of the syllable (e.g., "ka")
        frequency: Number of times this syllable appears
        rank: Frequency rank (1 = most common, 2 = second most common, etc.)
        percentage: Percentage of total syllables (0-100)

    Example:
        >>> entry = FrequencyEntry(canonical="ka", frequency=187, rank=1, percentage=10.2)
        >>> print(f"{entry.canonical}: {entry.frequency} ({entry.percentage:.1f}%)")
        ka: 187 (10.2%)
    """

    canonical: str
    frequency: int
    rank: int
    percentage: float


@dataclass
class NormalizationResult:
    """
    Complete result from the syllable normalization pipeline.

    This dataclass encapsulates all outputs from the normalization process,
    including configuration, statistics, frequencies, and file paths.

    Attributes:
        config: Configuration used for normalization
        stats: Statistics from the processing
        frequencies: Dictionary mapping canonical syllable to frequency count
        unique_syllables: Sorted list of unique canonical syllables
        input_files: List of input file paths that were processed
        output_dir: Directory where output files were saved
        timestamp: When the normalization was performed
        raw_file: Path to raw aggregated file (syllables_raw.txt)
        canonical_file: Path to canonicalized file (syllables_canonicalised.txt)
        frequency_file: Path to frequency JSON (syllables_frequencies.json)
        unique_file: Path to unique syllables (syllables_unique.txt)
        meta_file: Path to metadata report (normalization_meta.txt)

    Example:
        >>> result = NormalizationResult(
        ...     config=NormalizationConfig(),
        ...     stats=NormalizationStats(raw_count=1000),
        ...     frequencies={"ka": 187, "ra": 162},
        ...     unique_syllables=["ka", "ra"],
        ...     input_files=[Path("file1.txt")],
        ...     output_dir=Path("_working/normalized"),
        ...     timestamp=datetime.now(),
        ...     raw_file=Path("syllables_raw.txt"),
        ...     canonical_file=Path("syllables_canonicalised.txt"),
        ...     frequency_file=Path("syllables_frequencies.json"),
        ...     unique_file=Path("syllables_unique.txt"),
        ...     meta_file=Path("normalization_meta.txt")
        ... )
        >>> result.stats.raw_count
        1000
    """

    config: NormalizationConfig
    stats: NormalizationStats
    frequencies: dict[str, int]
    unique_syllables: list[str]
    input_files: list[Path]
    output_dir: Path
    timestamp: datetime = field(default_factory=datetime.now)
    raw_file: Path = field(default=Path("syllables_raw.txt"))
    canonical_file: Path = field(default=Path("syllables_canonicalised.txt"))
    frequency_file: Path = field(default=Path("syllables_frequencies.json"))
    unique_file: Path = field(default=Path("syllables_unique.txt"))
    meta_file: Path = field(default=Path("normalization_meta.txt"))

    def format_metadata(self) -> str:
        """
        Format normalization metadata as a human-readable string.

        Creates a detailed report including statistics, rejection breakdown,
        and top frequencies.

        Returns:
            Multi-line string containing all normalization metadata formatted
            for display or file output.

        Example:
            >>> result = NormalizationResult(...)
            >>> print(result.format_metadata())
            ======================================================================
            SYLLABLE NORMALIZATION METADATA
            ======================================================================
            Timestamp:           2026-01-05 17:30:22
            ...
        """
        lines = []
        lines.append("=" * 70)
        lines.append("SYLLABLE NORMALIZATION METADATA")
        lines.append("=" * 70)
        lines.append(f"Timestamp:           {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Input Files:         {len(self.input_files)} files processed")
        lines.append(f"Output Directory:    {self.output_dir}")
        lines.append("=" * 70)

        # Processing statistics
        lines.append("\nProcessing Statistics:")
        lines.append(f"  Raw Syllables:           {self.stats.raw_count:,}")
        lines.append(f"  After Canonicalization:  {self.stats.after_canonicalization:,}")
        lines.append(f"  Total Rejected:          {self.stats.total_rejected:,}")
        lines.append(f"  Unique Canonical:        {self.stats.unique_canonical:,}")
        lines.append(f"  Processing Time:         {self.stats.processing_time:.2f}s")

        # Rejection breakdown
        if self.stats.total_rejected > 0:
            lines.append("\nRejection Breakdown:")
            if self.stats.rejected_charset > 0:
                lines.append(f"  Invalid charset:    {self.stats.rejected_charset:,} syllables")
            if self.stats.rejected_length > 0:
                lines.append(f"  Length constraint:  {self.stats.rejected_length:,} syllables")
            if self.stats.rejected_empty > 0:
                lines.append(f"  Empty after norm:   {self.stats.rejected_empty:,} syllables")
            lines.append(f"  Rejection Rate:     {self.stats.rejection_rate:.1f}%")

        # Configuration
        lines.append("\nNormalization Configuration:")
        lines.append(f"  Min Length:         {self.config.min_length}")
        lines.append(f"  Max Length:         {self.config.max_length}")
        lines.append(f"  Unicode Form:       {self.config.unicode_form}")
        lines.append(f"  Allowed Charset:    {self.config.allowed_charset}")

        # Top frequencies
        if self.frequencies:
            # Sort by frequency descending
            sorted_freqs = sorted(self.frequencies.items(), key=lambda x: x[1], reverse=True)
            top_n = min(20, len(sorted_freqs))
            total_count = sum(self.frequencies.values())

            lines.append(f"\nTop {top_n} Most Frequent Syllables:")
            for i, (syllable, count) in enumerate(sorted_freqs[:top_n], 1):
                percentage = (count / total_count * 100) if total_count > 0 else 0
                lines.append(
                    f"  {i:2d}. {syllable:10s} ({count:5,} occurrences, {percentage:5.1f}%)"
                )

            if len(sorted_freqs) > top_n:
                lines.append(f"  ... and {len(sorted_freqs) - top_n} more")

        # Output files
        lines.append("\nOutput Files:")
        lines.append(f"  Raw:              {self.raw_file.name}")
        lines.append(f"  Canonicalized:    {self.canonical_file.name}")
        lines.append(f"  Frequencies:      {self.frequency_file.name}")
        lines.append(f"  Unique:           {self.unique_file.name}")
        lines.append(f"  Metadata:         {self.meta_file.name}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)
