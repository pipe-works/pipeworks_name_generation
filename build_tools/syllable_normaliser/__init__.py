"""
Syllable Normaliser - 3-Step Normalization Pipeline

The syllable normaliser transforms raw syllable files into canonical form through a 3-step pipeline,
creating the authoritative syllable inventory for pattern development. This is a **build-time tool only** -
not used during runtime name generation.

3-Step Normalization Pipeline:

1. **Aggregation** - Combine multiple input files while preserving all occurrences
2. **Canonicalization** - Unicode normalization, diacritic stripping, charset validation
3. **Frequency Analysis** - Count occurrences and generate frequency intelligence

Features:

- Unicode normalization (NFKD, NFC, NFD, NFKC)
- Diacritic stripping using unicodedata
- Configurable charset and length constraints
- Frequency intelligence capture (pre-deduplication counts)
- Deterministic processing (same input = same output)
- Comprehensive metadata reporting
- 5 output files for complete analysis

The pipeline produces 5 output files:

- syllables_raw.txt: Aggregated raw syllables (all occurrences preserved)
- syllables_canonicalised.txt: Normalized canonical syllables
- syllables_frequencies.json: Frequency intelligence (syllable → count)
- syllables_unique.txt: Deduplicated canonical syllable inventory
- normalization_meta.txt: Detailed statistics and metadata report

Usage:
    >>> from pathlib import Path
    >>> from build_tools.syllable_normaliser import (
    ...     NormalizationConfig,
    ...     run_full_pipeline,
    ...     discover_input_files
    ... )
    >>>
    >>> # Discover input files
    >>> files = discover_input_files(Path("data/corpus/"), pattern="*.txt")
    >>>
    >>> # Create configuration
    >>> config = NormalizationConfig(min_length=2, max_length=8)
    >>>
    >>> # Run pipeline
    >>> result = run_full_pipeline(
    ...     input_files=files,
    ...     output_dir=Path("_working/normalized"),
    ...     config=config,
    ...     verbose=True
    ... )
    >>>
    >>> # Access results
    >>> print(f"Processed {result.stats.raw_count:,} raw syllables")
    >>> print(f"Canonical: {result.stats.after_canonicalization:,}")
    >>> print(f"Unique: {result.stats.unique_canonical:,}")

CLI Usage:
    # Full pipeline with default settings
    python -m build_tools.syllable_normaliser --source data/corpus/ --output _working/normalized/

    # Custom length constraints
    python -m build_tools.syllable_normaliser --source data/ --min 3 --max 6
"""

# File aggregation
from .aggregator import FileAggregator, discover_input_files

# CLI entry point
from .cli import create_argument_parser, main, run_full_pipeline

# Frequency analysis
from .frequency import (
    FrequencyAnalyzer,
    load_frequencies_from_file,
    load_unique_syllables_from_file,
)

# Data models
from .models import FrequencyEntry, NormalizationConfig, NormalizationResult, NormalizationStats

# Core normalization
from .normalizer import SyllableNormalizer, normalize_batch

__all__ = [
    # Data models
    "FrequencyEntry",
    "NormalizationConfig",
    "NormalizationResult",
    "NormalizationStats",
    # Core normalization
    "SyllableNormalizer",
    "normalize_batch",
    # File aggregation
    "FileAggregator",
    "discover_input_files",
    # Frequency analysis
    "FrequencyAnalyzer",
    "load_frequencies_from_file",
    "load_unique_syllables_from_file",
    # CLI
    "run_full_pipeline",
    "create_argument_parser",
    "main",
]

__version__ = "0.1.0"
