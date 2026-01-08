"""Syllable Walker: Explore phonetic feature space via random walks.

This package provides tools for exploring syllable datasets through cost-based
random walks in phonetic feature space. The walker navigates from syllable to
syllable based on feature similarity, frequency, and configurable exploration
parameters.

Main Components:
    - SyllableWalker: Core walking algorithm with efficient neighbor graph
    - WalkProfile: Configuration preset for different walking behaviors
    - WALK_PROFILES: Predefined profiles (clerical, dialect, goblin, ritual)

Example:
    >>> from build_tools.syllable_walk import SyllableWalker
    >>> walker = SyllableWalker("data/annotated/syllables_annotated.json")
    >>> walk = walker.walk_from_profile(start="ka", profile="dialect", steps=5, seed=42)
    >>> print(" → ".join(s["syllable"] for s in walk))
    ka → ki → ti → ta → da → de

Command-Line Usage:
    python -m build_tools.syllable_walk data.json --start ka --profile dialect

For detailed documentation, see: claude/build_tools/syllable_walk.md
"""

from build_tools.syllable_walk.profiles import (
    WALK_PROFILES,
    WalkProfile,
    get_profile,
    list_profiles,
)
from build_tools.syllable_walk.walker import SyllableWalker

# Public API
__all__ = [
    "SyllableWalker",
    "WalkProfile",
    "WALK_PROFILES",
    "get_profile",
    "list_profiles",
]
