"""
State management for the name combiner module.

This module provides the CombinerState dataclass for managing name combiner
configuration. The state mirrors the exact CLI options from name_combiner.

CLI Options Mapped:
    --run-dir          → source_patch (A or B, uses patch's corpus_dir)
    --syllables        → syllables (2, 3, or 4)
    --count            → count (default: 10000)
    --seed             → seed (None = random)
    --frequency-weight → frequency_weight (0.0-1.0, default: 1.0)

Usage:
    >>> state = CombinerState()
    >>> state.syllables = 3
    >>> state.count = 5000
    >>> state.seed = 42
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
