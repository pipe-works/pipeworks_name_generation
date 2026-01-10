"""
Syllable Feature Annotator - Phonetic Feature Detection

The syllable feature annotator attaches phonetic features to normalized syllables, creating
a feature-annotated dataset for downstream pattern generation. This is a **build-time tool only** -
not used during runtime name generation.

The tool sits between the syllable normaliser and pattern development:

1. **Input**: Normalized syllables from syllable_normaliser
2. **Process**: Apply 12 feature detectors to each syllable
3. **Output**: Feature-annotated syllable dataset

Design Principles:

- **Pure observation** - Observes patterns, never interprets or filters
- **Deterministic** - Same input always produces same output
- **Feature independence** - No detector depends on another
- **Language agnostic** - Structural patterns only, no linguistic knowledge
- **Conservative detection** - Approximate patterns without overthinking

Feature Set (12 features):

**Onset Features (3)**:
    - starts_with_vowel: Open onset (vowel-initial)
    - starts_with_cluster: Initial consonant cluster (2+ consonants)
    - starts_with_heavy_cluster: Heavy initial cluster (3+ consonants)

**Internal Features (4)**:
    - contains_plosive: Contains plosive consonant (p, t, k, b, d, g)
    - contains_fricative: Contains fricative consonant (f, s, z, v, h)
    - contains_liquid: Contains liquid consonant (l, r, w)
    - contains_nasal: Contains nasal consonant (m, n)

**Nucleus Features (2)**:
    - short_vowel: Exactly one vowel (weight proxy)
    - long_vowel: Two or more vowels (weight proxy)

**Coda Features (3)**:
    - ends_with_vowel: Open syllable (vowel-final)
    - ends_with_nasal: Nasal coda
    - ends_with_stop: Stop coda

Quick Start
-----------
Command-line usage::

    $ python -m build_tools.syllable_feature_annotator \\
        --syllables data/normalized/syllables_unique.txt \\
        --frequencies data/normalized/syllables_frequencies.json \\
        --output data/annotated/syllables_annotated.json \\
        --verbose

Programmatic usage::

    >>> from pathlib import Path
    >>> from build_tools.syllable_feature_annotator import run_annotation_pipeline
    >>> result = run_annotation_pipeline(
    ...     syllables_path=Path("data/normalized/syllables_unique.txt"),
    ...     frequencies_path=Path("data/normalized/syllables_frequencies.json"),
    ...     output_path=Path("data/annotated/syllables_annotated.json"),
    ...     verbose=True
    ... )
    >>> print(f"Annotated {result.statistics.syllable_count} syllables")

Annotate syllables in code::

    >>> from build_tools.syllable_feature_annotator import (
    ...     annotate_corpus,
    ...     FEATURE_DETECTORS
    ... )
    >>> syllables = ["ka", "kran", "spla"]
    >>> frequencies = {"ka": 187, "kran": 7, "spla": 2}
    >>> result = annotate_corpus(syllables, frequencies, FEATURE_DETECTORS)
    >>> for record in result.annotated_syllables:
    ...     print(f"{record.syllable}: {sum(record.features.values())} features")

Public API
----------
This package exports the following components for programmatic use:

**Pipeline Functions**:
    - run_annotation_pipeline: Complete end-to-end pipeline with I/O
    - annotate_corpus: Annotate syllables without I/O
    - annotate_syllable: Annotate single syllable

**Data Models**:
    - AnnotatedSyllable: Single annotated syllable record
    - AnnotationStatistics: Processing statistics
    - AnnotationResult: Complete result with syllables and stats

**Feature Detection**:
    - FEATURE_DETECTORS: Registry of all 12 feature detector functions
    - Individual detector functions (starts_with_vowel, contains_plosive, etc.)

**Phoneme Sets**:
    - VOWELS, PLOSIVES, FRICATIVES, NASALS, LIQUIDS, STOPS

**File I/O**:
    - load_syllables: Load syllables from text file
    - load_frequencies: Load frequencies from JSON
    - save_annotated_syllables: Save annotated output to JSON

Architecture
------------
The package is organized into focused modules:

**phoneme_sets.py**: Character class definitions (VOWELS, PLOSIVES, etc.)
**feature_rules.py**: Pure feature detector functions (12 detectors)
**annotator.py**: Core orchestration and data models
**file_io.py**: Simple I/O helpers
**cli.py**: Command-line interface with argument parsing
**__main__.py**: Module entry point for python -m

Integration with Pipeline
-------------------------
This tool is designed to work with the syllable normalizer::

    # Step 1: Normalize syllables
    $ python -m build_tools.pyphen_syllable_normaliser \\
        --source data/corpus/ \\
        --output data/normalized/

    # Step 2: Annotate with features
    $ python -m build_tools.syllable_feature_annotator \\
        --syllables data/normalized/syllables_unique.txt \\
        --frequencies data/normalized/syllables_frequencies.json \\
        --output data/annotated/syllables_annotated.json

    # Step 3: Use annotated data for pattern generation (future)

Output Format
-------------
The annotator produces JSON with this structure::

    [
      {
        "syllable": "kran",
        "frequency": 7,
        "features": {
          "starts_with_vowel": false,
          "starts_with_cluster": true,
          "starts_with_heavy_cluster": false,
          "contains_plosive": true,
          "contains_fricative": false,
          "contains_liquid": true,
          "contains_nasal": true,
          "short_vowel": true,
          "long_vowel": false,
          "ends_with_vowel": false,
          "ends_with_nasal": true,
          "ends_with_stop": false
        }
      }
    ]

Notes
-----
- This is a build-time tool only (not used during runtime name generation)
- The annotator is deterministic (same input → same output)
- Features are structural observations, not linguistic interpretations
- All 12 features are applied to every syllable (no selective detection)
- Processing is fast: typically <1 second for 1,000-10,000 syllables

See Also
--------
- CLAUDE.md: Complete project documentation
- syllable_normaliser: Upstream tool that produces input data
- feature_rules.py: Detailed documentation of each feature detector
"""

# Core pipeline functions
from build_tools.syllable_feature_annotator.annotator import (
    AnnotatedSyllable,
    AnnotationResult,
    AnnotationStatistics,
    annotate_corpus,
    annotate_syllable,
    run_annotation_pipeline,
)

# Feature detection
from build_tools.syllable_feature_annotator.feature_rules import (
    FEATURE_DETECTORS,
    contains_fricative,
    contains_liquid,
    contains_nasal,
    contains_plosive,
    ends_with_nasal,
    ends_with_stop,
    ends_with_vowel,
    long_vowel,
    short_vowel,
    starts_with_cluster,
    starts_with_heavy_cluster,
    starts_with_vowel,
)

# File I/O helpers
from build_tools.syllable_feature_annotator.file_io import (
    load_frequencies,
    load_syllables,
    save_annotated_syllables,
)

# Phoneme sets (character classes)
from build_tools.syllable_feature_annotator.phoneme_sets import (
    FRICATIVES,
    LIQUIDS,
    NASALS,
    PLOSIVES,
    STOPS,
    VOWELS,
)

__all__ = [
    # Pipeline functions
    "run_annotation_pipeline",
    "annotate_corpus",
    "annotate_syllable",
    # Data models
    "AnnotatedSyllable",
    "AnnotationStatistics",
    "AnnotationResult",
    # Feature detection
    "FEATURE_DETECTORS",
    "starts_with_vowel",
    "starts_with_cluster",
    "starts_with_heavy_cluster",
    "contains_plosive",
    "contains_fricative",
    "contains_liquid",
    "contains_nasal",
    "short_vowel",
    "long_vowel",
    "ends_with_vowel",
    "ends_with_nasal",
    "ends_with_stop",
    # Phoneme sets
    "VOWELS",
    "PLOSIVES",
    "FRICATIVES",
    "NASALS",
    "LIQUIDS",
    "STOPS",
    # File I/O
    "load_syllables",
    "load_frequencies",
    "save_annotated_syllables",
]

# Package metadata
__version__ = "0.1.0"
__author__ = "pipeworks_name_generation contributors"
__description__ = "Deterministic phonetic feature annotation for syllables"


# Backward compatibility imports for analysis tools (DEPRECATED)
# Analysis tools have been moved to build_tools.syllable_analysis
# These will be removed in a future version
import warnings as _warnings


def _deprecated_import_warning(old_path: str, new_path: str) -> None:
    """Issue deprecation warning for moved analysis tools."""
    _warnings.warn(
        f"Importing from '{old_path}' is deprecated. "
        f"Use '{new_path}' instead. "
        "This compatibility layer will be removed in version 0.2.0.",
        DeprecationWarning,
        stacklevel=3,
    )


def __getattr__(name: str):
    """Lazy import with deprecation warning for moved analysis tools."""
    # Random sampler functions
    if name == "sample_syllables":
        _deprecated_import_warning(
            "build_tools.syllable_feature_annotator.random_sampler",
            "build_tools.syllable_analysis.random_sampler",
        )
        from build_tools.syllable_analysis.random_sampler import sample_syllables  # noqa: F401

        return locals()[name]

    # Functions moved to syllable_analysis.common during refactoring
    if name in ("load_annotated_syllables", "save_samples"):
        _deprecated_import_warning(
            "build_tools.syllable_feature_annotator",
            "build_tools.syllable_analysis.common",
        )
        if name == "load_annotated_syllables":
            from build_tools.syllable_analysis.common import load_annotated_syllables  # noqa: F401

            return load_annotated_syllables
        elif name == "save_samples":
            # save_samples was renamed to save_json_output
            from build_tools.syllable_analysis.common import save_json_output  # noqa: F401

            return save_json_output

    # Feature signatures functions
    if name in (
        "extract_signature",
        "analyze_feature_signatures",
        "format_signature_report",
        "run_analysis",
        "save_report",
    ):
        _deprecated_import_warning(
            "build_tools.syllable_feature_annotator.feature_signatures",
            "build_tools.syllable_analysis.feature_signatures",
        )
        from build_tools.syllable_analysis.feature_signatures import (  # noqa: F401
            analyze_feature_signatures,
            extract_signature,
            format_signature_report,
            run_analysis,
            save_report,
        )

        return locals()[name]

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
