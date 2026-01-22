"""
Syllable Walker - Phonetic Feature Space Exploration

The syllable walker is a phonetic exploration tool that generates sequences of syllables by "walking" through
phonetic feature space using cost-based random selection. It enables corpus analysis, pattern discovery, and
exploration of phonetic relationships. This is a **build-time analysis tool only** - not used during runtime
name generation.

The walker explores syllable datasets by moving probabilistically from one syllable to phonetically
similar syllables. Each step considers:

- **Phonetic distance** - How many features change (Hamming distance)
- **Frequency bias** - Preference for common vs rare syllables
- **Temperature** - Amount of randomness in selection
- **Inertia** - Tendency to stay at current syllable

Key Features:

- Four pre-configured profiles (clerical, dialect, goblin, ritual)
- Custom parameter control for fine-tuned exploration
- Deterministic walks (same seed = same walk, reproducible)
- Batch processing to generate thousands of walks for analysis
- Fast operation (<10ms per walk after initialization)
- Large corpus support (efficiently handles 500k+ syllables)

Main Components:

- SyllableWalker: Core walking algorithm with efficient neighbor graph
- WalkProfile: Configuration preset for different walking behaviors
- WALK_PROFILES: Predefined profiles (clerical, dialect, goblin, ritual)

Usage:
    >>> from build_tools.syllable_walk import SyllableWalker
    >>>
    >>> # Load annotated syllables
    >>> walker = SyllableWalker("data/annotated/syllables_annotated.json")
    >>>
    >>> # Walk using a profile
    >>> walk = walker.walk_from_profile(
    ...     start="ka",
    ...     profile="dialect",
    ...     steps=5,
    ...     seed=42
    ... )
    >>>
    >>> # Display walk sequence
    >>> print(" → ".join(s["syllable"] for s in walk))
    ka → ki → ti → ta → da → de

CLI Usage:

    .. code-block:: bash

       # Walk with a profile
       python -m build_tools.syllable_walk data.json --start ka --profile dialect --steps 5

       # Batch walks for analysis
       python -m build_tools.syllable_walk data.json --batch 100 --profile ritual

       # For web interface, use the separate syllable_walk_web module:
       python -m build_tools.syllable_walk_web
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
