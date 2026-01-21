"""
Name Combiner - Structural Name Candidate Generation

Generates N-syllable name candidates from an annotated syllable corpus by
combining syllables and aggregating their features to the name level.
This is a **build-time tool only** - not used during runtime name generation.

This module is the first stage of the Selection Policy Layer. It performs
structural combination without policy evaluation - that responsibility belongs
to the name_selector module.

Architectural Boundary:
    Candidate generation is a structural step, not a decision-making step.
    All governance, admissibility, and rejection logic remains exclusively
    within the name_selector module.

Features:
- Deterministic combination with seed control
- Frequency-weighted syllable sampling
- Feature aggregation to name level (majority rule for nucleus)
- Output to extraction run's candidates/ directory

Aggregation Rules:
- Onset features (starts_with_*): First syllable only
- Coda features (ends_with_*): Final syllable only
- Internal features (contains_*): Boolean OR across all syllables
- Nucleus features (short_vowel, long_vowel): Majority rule (>50%)

Usage:
    >>> from build_tools.name_combiner import combine_syllables, aggregate_features
    >>> candidates = combine_syllables(annotated_data, syllable_count=2, count=100)
    >>> for candidate in candidates:
    ...     print(f"{candidate['name']}: {candidate['features']}")

CLI::

    python -m build_tools.name_combiner \\
        --run-dir _working/output/20260110_115453_pyphen/ \\
        --syllables 2 \\
        --count 10000 \\
        --seed 42
"""

from build_tools.name_combiner.aggregator import aggregate_features
from build_tools.name_combiner.combiner import combine_syllables

__all__ = [
    "aggregate_features",
    "combine_syllables",
]
