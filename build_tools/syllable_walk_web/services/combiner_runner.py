"""
Name combiner service for the web application.

Generates N-syllable name candidates from an annotated corpus.
"""

from __future__ import annotations

from typing import Any, Sequence


def run_combiner(
    annotated_data: Sequence[dict[str, Any]],
    *,
    syllable_count: int = 2,
    count: int = 10000,
    seed: int | None = None,
    frequency_weight: float = 1.0,
) -> list[dict[str, Any]]:
    """Generate name candidates from annotated syllables.

    Args:
        annotated_data: Annotated syllable records (from corpus loader).
        syllable_count: Number of syllables per name.
        count: Number of candidates to generate.
        seed: RNG seed for determinism.
        frequency_weight: 0.0 = uniform, 1.0 = frequency-weighted.

    Returns:
        List of candidate dicts with ``name``, ``syllables``, ``features``.
    """
    from build_tools.name_combiner.combiner import combine_syllables

    return combine_syllables(
        annotated_data=annotated_data,
        syllable_count=syllable_count,
        count=count,
        seed=seed,
        frequency_weight=frequency_weight,
    )
