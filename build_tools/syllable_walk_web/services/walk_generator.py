"""
Walk generation service for the web application.

Generates syllable walks using the existing SyllableWalker.
"""

from __future__ import annotations

from typing import Any


def generate_walks(
    walker: Any,  # SyllableWalker
    *,
    profile: str | None = None,
    steps: int = 5,
    count: int = 2,
    max_flips: int = 2,
    temperature: float = 0.7,
    frequency_weight: float = 0.0,
    neighbor_limit: int | None = 10,
    min_length: int | None = 2,
    max_length: int | None = 5,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    """Generate walks using the SyllableWalker.

    If *profile* is given, uses ``walk_from_profile``. Otherwise uses
    explicit parameters via ``walk``.

    Args:
        walker: Initialised SyllableWalker instance.
        profile: Named profile (clerical/dialect/goblin/ritual) or None.
        steps: Number of walk steps (name length = steps + 1).
        count: Number of walks to generate.
        max_flips: Maximum feature flips per step.
        temperature: Exploration temperature (0.1–5.0).
        frequency_weight: Frequency bias (-2.0 to 2.0).
        neighbor_limit: Max neighbors to consider per step; ``None`` disables cap.
        min_length: Minimum syllable length filter; ``None`` disables bound.
        max_length: Maximum syllable length filter; ``None`` disables bound.
        seed: Optional seed for determinism.

    Returns:
        List of walk result dicts, each with keys:
        ``formatted`` (str), ``syllables`` (list[str]), ``steps`` (list[dict]).

    Raises:
        ValueError: If requested constraints are invalid.
    """
    if neighbor_limit is not None and neighbor_limit < 1:
        raise ValueError(f"neighbor_limit must be >= 1, got {neighbor_limit}")
    if min_length is not None and min_length < 1:
        raise ValueError(f"min_length must be >= 1, got {min_length}")
    if max_length is not None and max_length < 1:
        raise ValueError(f"max_length must be >= 1, got {max_length}")
    if min_length is not None and max_length is not None and min_length > max_length:
        raise ValueError(f"min_length ({min_length}) must be <= max_length ({max_length})")

    results = []

    for i in range(count):
        # Each walk in a batch gets seed+i so they produce different results
        # while remaining deterministic: the same (seed, count) pair always
        # produces the same set of walks.
        walk_seed = (seed + i) if seed is not None else None

        start = walker.get_random_syllable(
            seed=walk_seed,
            min_length=min_length,
            max_length=max_length,
        )

        # walk_from_profile uses pre-tuned parameter sets (temperature,
        # max_flips, etc.); "custom" is a sentinel meaning "use explicit
        # parameters from the request".
        if profile and profile != "custom":
            walk = walker.walk_from_profile(
                start=start,
                profile=profile,
                steps=steps,
                neighbor_limit=neighbor_limit,
                min_length=min_length,
                max_length=max_length,
                seed=walk_seed,
            )
        else:
            walk = walker.walk(
                start=start,
                steps=steps,
                max_flips=max_flips,
                temperature=temperature,
                frequency_weight=frequency_weight,
                neighbor_limit=neighbor_limit,
                min_length=min_length,
                max_length=max_length,
                seed=walk_seed,
            )

        # Format the walk
        syllable_texts = [step["syllable"] for step in walk]
        # Middle dot (·) is the project-wide syllable boundary convention,
        # matching the TUI and combiner output formats.
        formatted = "\u00b7".join(syllable_texts)

        results.append(
            {
                "formatted": formatted,
                "syllables": syllable_texts,
                "steps": walk,
            }
        )

    return results
