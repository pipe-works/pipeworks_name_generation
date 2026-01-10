"""
NLTK Syllable Normaliser - Fragment Cleaning + 3-Step Normalization Pipeline

The NLTK syllable normaliser extends the standard normalization pipeline with NLTK-specific
fragment cleaning to reconstruct phonetically coherent syllables from over-segmented output.
This is a **build-time tool only** - not used during runtime name generation.

NLTK-Specific Processing:

1. **Fragment Cleaning** - Merge single-letter fragments with neighbors (NLTK-specific)
2. **Aggregation** - Combine multiple input files while preserving all occurrences
3. **Canonicalization** - Unicode normalization, diacritic stripping, charset validation
4. **Frequency Analysis** - Count occurrences and generate frequency intelligence

Key Differences from Pyphen Normaliser:

- **Input Source**: Processes NLTK run directories with syllables/ subdirectory
- **Preprocessing**: Fragment cleaning step merges isolated phonemes
- **Output Location**: In-place in run directory (not separate output directory)
- **Output Prefix**: nltk_ prefix (for provenance tracking)

Features:

- Fragment cleaning (single vowel/consonant merging)
- Unicode normalization (NFKD, NFC, NFD, NFKC)
- Diacritic stripping using unicodedata
- Configurable charset and length constraints
- Frequency intelligence capture (pre-deduplication counts)
- Deterministic processing (same input = same output)
- Comprehensive metadata reporting
- 5 output files with nltk_ prefix for complete analysis

The pipeline produces 5 output files (with nltk_ prefix for provenance):

- nltk_syllables_raw.txt: Aggregated raw syllables (all occurrences preserved)
- nltk_syllables_canonicalised.txt: Normalized canonical syllables (after fragment cleaning)
- nltk_syllables_frequencies.json: Frequency intelligence (syllable → count)
- nltk_syllables_unique.txt: Deduplicated canonical syllable inventory
- nltk_normalization_meta.txt: Detailed statistics and metadata report

Usage:
    >>> from pathlib import Path
    >>> from build_tools.nltk_syllable_normaliser import (
    ...     NormalizationConfig,
    ...     run_full_pipeline,
    ... )
    >>>
    >>> # Process NLTK run directory in-place
    >>> run_dir = Path("_working/output/20260110_095213_nltk/")
    >>> result = run_full_pipeline(
    ...     run_directory=run_dir,
    ...     config=NormalizationConfig(min_length=2, max_length=8),
    ...     verbose=True
    ... )
    >>>
    >>> # Access results
    >>> print(f"Processed {result.stats.raw_count:,} raw syllables")
    >>> print(f"After cleaning: {result.stats.after_fragment_cleaning:,}")
    >>> print(f"Canonical: {result.stats.after_canonicalization:,}")
    >>> print(f"Unique: {result.stats.unique_canonical:,}")

CLI Usage:

    .. code-block:: bash

       # Process specific NLTK run directory
       python -m build_tools.nltk_syllable_normaliser --run-dir _working/output/20260110_095213_nltk/

       # Auto-detect NLTK run directories
       python -m build_tools.nltk_syllable_normaliser --source _working/output/

       # Custom configuration
       python -m build_tools.nltk_syllable_normaliser --run-dir <path> --min 2 --max 8
"""

# Import shared components from pyphen normaliser
from build_tools.pyphen_syllable_normaliser import (
    NormalizationConfig,
    NormalizationResult,
    NormalizationStats,
)

# NLTK-specific components
from .cli import create_argument_parser, main, run_full_pipeline
from .fragment_cleaner import FragmentCleaner

__all__ = [
    # Shared data models (from pyphen normaliser)
    "NormalizationConfig",
    "NormalizationResult",
    "NormalizationStats",
    # NLTK-specific components
    "FragmentCleaner",
    # CLI
    "run_full_pipeline",
    "create_argument_parser",
    "main",
]

__version__ = "0.1.0"
