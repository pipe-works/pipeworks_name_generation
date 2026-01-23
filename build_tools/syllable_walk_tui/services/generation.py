"""
Walk generation service for Syllable Walker TUI.

Provides functions for generating phonetic walks using SyllableWalker.
"""

import json
import os
import tempfile
from dataclasses import dataclass
from typing import TYPE_CHECKING

from build_tools.syllable_walk.walker import SyllableWalker

if TYPE_CHECKING:
    from build_tools.syllable_walk_tui.modules.oscillator import PatchState


@dataclass
class WalkResult:
    """Result from walk generation."""

    walks: list[str]
    error: str | None = None


def generate_walks_for_patch(patch: "PatchState") -> WalkResult:
    """
    Generate walks for a patch using SyllableWalker.

    This function:
    1. Creates SyllableWalker from patch's annotated data
    2. Filters syllables by min/max length constraints
    3. Generates walks with current patch parameters
    4. Returns formatted walk strings

    Args:
        patch: PatchState with corpus data and walk parameters

    Returns:
        WalkResult with walks list and optional error message

    Note:
        Caller is responsible for validating patch.is_ready_for_generation()
        before calling this function.

    Examples:
        >>> result = generate_walks_for_patch(patch)
        >>> if result.error:
        ...     print(f"Generation failed: {result.error}")
        >>> else:
        ...     for walk in result.walks:
        ...         print(walk)  # "syl1 → syl2 → syl3"
    """
    try:
        # Create temporary JSON file for SyllableWalker
        # (SyllableWalker expects a file path, not in-memory data)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(patch.annotated_data, f)
            temp_path = f.name

        try:
            # Create walker (this will pre-compute neighbor graph)
            walker = SyllableWalker(temp_path, verbose=False)

            # Filter syllables by length (simple filtering)
            valid_syllables = [
                syl for syl in walker.syllables if patch.min_length <= len(syl) <= patch.max_length
            ]

            if not valid_syllables:
                return WalkResult(
                    walks=[],
                    error="No syllables match length constraints",
                )

            # Generate walks based on walk_count parameter
            walks = []
            for i in range(patch.walk_count):
                # Pick random starting syllable using patch RNG
                start = patch.rng.choice(valid_syllables)

                # Generate walk using patch parameters
                walk = walker.walk(
                    start=start,
                    steps=patch.walk_length,
                    max_flips=patch.max_flips,
                    temperature=patch.temperature,
                    frequency_weight=patch.frequency_weight,
                    seed=patch.seed + i,  # Offset seed for variety
                )

                # Format walk as string: "syl1 → syl2 → syl3"
                walk_text = " → ".join(step["syllable"] for step in walk)
                walks.append(walk_text)

            return WalkResult(walks=walks, error=None)

        finally:
            # Clean up temp file
            os.unlink(temp_path)

    except Exception as e:
        return WalkResult(walks=[], error=str(e))
