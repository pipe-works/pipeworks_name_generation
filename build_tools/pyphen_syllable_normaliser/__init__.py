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

The pipeline produces 5 output files (with pyphen_ prefix for provenance):

- pyphen_syllables_raw.txt: Aggregated raw syllables (all occurrences preserved)
- pyphen_syllables_canonicalised.txt: Normalized canonical syllables
- pyphen_syllables_frequencies.json: Frequency intelligence (syllable → count)
- pyphen_syllables_unique.txt: Deduplicated canonical syllable inventory
- pyphen_normalization_meta.txt: Detailed statistics and metadata report

Usage:
    >>> from pathlib import Path
    >>> from build_tools.pyphen_syllable_normaliser import (
    ...     NormalizationConfig,
    ...     run_full_pipeline
    ... )
    >>>
    >>> # Create configuration
    >>> config = NormalizationConfig(min_length=2, max_length=8)
    >>>
    >>> # Run pipeline on a pyphen run directory
    >>> result = run_full_pipeline(
    ...     run_directory=Path("_working/output/20260110_143022_pyphen/"),
    ...     config=config,
    ...     verbose=True
    ... )
    >>>
    >>> # Access results
    >>> print(f"Processed {result.stats.raw_count:,} raw syllables")
    >>> print(f"Canonical: {result.stats.after_canonicalization:,}")
    >>> print(f"Unique: {result.stats.unique_canonical:,}")

CLI Usage:

    .. code-block:: bash

       # Process specific pyphen run directory (in-place)
       python -m build_tools.pyphen_syllable_normaliser --run-dir _working/output/20260110_143022_pyphen/

       # Auto-detect all pyphen run directories
       python -m build_tools.pyphen_syllable_normaliser --source _working/output/
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
