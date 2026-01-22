"""
State management for name generation modules.

This module provides dataclasses for managing name combiner and selector
configuration. The states mirror the exact CLI options from the tools.

CombinerState CLI Options:
    --run-dir          → source_patch (A or B, uses patch's corpus_dir)
    --syllables        → syllables (2, 3, or 4)
    --count            → count (default: 10000)
    --seed             → seed (None = random)
    --frequency-weight → frequency_weight (0.0-1.0, default: 1.0)

SelectorState CLI Options:
    --run-dir          → source_patch (A or B, uses patch's corpus_dir)
    --candidates       → Determined by combiner output (syllables)
    --name-class       → name_class (first_name, last_name, etc.)
    --count            → count (default: 100)
    --mode             → mode (hard or soft, default: hard)

Usage:
    >>> combiner = CombinerState()
    >>> combiner.syllables = 3
    >>> selector = SelectorState()
    >>> selector.name_class = "first_name"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class CombinerState:
    """
    State for name combiner configuration.

    Mirrors the exact CLI options from build_tools/name_combiner.

    Attributes:
        source_patch: Which patch's corpus to use ("A" or "B")
                      Maps to CLI --run-dir (uses patch's corpus_dir)
        syllables: Number of syllables per name (2, 3, or 4)
                   Maps to CLI --syllables
        count: Number of candidates to generate
               Maps to CLI --count (default: 10000)
        seed: RNG seed for deterministic output (None = random)
              Maps to CLI --seed
        frequency_weight: Weight for frequency-biased sampling (0.0-1.0)
                         Maps to CLI --frequency-weight (default: 1.0)

        outputs: List of generated candidate names (for display)
        last_output_path: Path where candidates were written
    """

    # Source selection - which patch's corpus to use
    # Maps to CLI --run-dir (via patch.corpus_dir)
    source_patch: Literal["A", "B"] = "A"

    # Number of syllables per candidate name (2, 3, or 4)
    # Maps to CLI --syllables (required, choices=[2, 3, 4])
    syllables: int = 2

    # Number of candidates to generate
    # Maps to CLI --count (default: 10000)
    count: int = 10000

    # RNG seed for deterministic output
    # Maps to CLI --seed (default: None = system entropy)
    seed: int | None = None

    # Weight for frequency-biased sampling
    # 0.0 = uniform sampling, 1.0 = fully frequency-weighted
    # Maps to CLI --frequency-weight (default: 1.0)
    frequency_weight: float = 1.0

    # Output storage (for display in TUI)
    outputs: list[str] = field(default_factory=list)
    last_output_path: str | None = None


# Available name classes from data/name_classes.yml
NAME_CLASSES = [
    "first_name",
    "last_name",
    "place_name",
    "location_name",
    "object_item",
    "organisation",
    "title_epithet",
]


@dataclass
class SelectorState:
    """
    State for name selector configuration.

    Mirrors the exact CLI options from build_tools/name_selector.

    Attributes:
        name_class: Name class policy to use for selection
                    Maps to CLI --name-class (required)
        count: Maximum number of names to output
               Maps to CLI --count (default: 100)
        mode: Evaluation mode - "hard" rejects, "soft" penalizes
              Maps to CLI --mode (default: "hard")

        outputs: List of selected names (for display)
        last_output_path: Path where selections were written
        last_candidates_path: Path to candidates file used
    """

    # Name class policy to use
    # Maps to CLI --name-class (required)
    # Available: first_name, last_name, place_name, location_name,
    #            object_item, organisation, title_epithet
    name_class: str = "first_name"

    # Maximum number of names to output
    # Maps to CLI --count (default: 100)
    count: int = 100

    # Evaluation mode
    # "hard" = reject candidates with discouraged features
    # "soft" = apply -10 penalty instead of rejection
    # Maps to CLI --mode (default: "hard")
    mode: Literal["hard", "soft"] = "hard"

    # Output storage (for display in TUI)
    outputs: list[str] = field(default_factory=list)
    last_output_path: str | None = None
    last_candidates_path: str | None = None
