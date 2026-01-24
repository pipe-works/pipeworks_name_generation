"""Walk profile definitions for syllable walker.

This module defines WalkProfile dataclass and predefined profiles that
encode different walking behaviors (conservative, balanced, chaotic, etc.).

Profiles provide convenient presets for common use cases:
- Clerical: Conservative, favors common syllables
- Dialect: Balanced exploration, neutral frequency
- Goblin: Chaotic, favors rare syllables
- Ritual: Maximum exploration, strongly favors rare

Example:
    >>> from build_tools.syllable_walk.profiles import WALK_PROFILES
    >>> profile = WALK_PROFILES["goblin"]
    >>> profile.temperature
    1.5
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WalkProfile:
    """Configuration profile for a syllable walk.

    A profile encapsulates all parameters needed for a walk, providing
    named presets for different behaviors.

    Attributes:
        name: Human-readable profile name (e.g., "Dialect Walk")
        description: Brief description of profile behavior
        max_flips: Maximum feature flips allowed per step (1-3)
        temperature: Exploration temperature (0.1-5.0)
        frequency_weight: Frequency bias (-2.0 to 2.0)

    Example:
        >>> profile = WalkProfile(
        ...     name="Custom Walk",
        ...     description="High temperature, neutral frequency",
        ...     max_flips=2,
        ...     temperature=2.0,
        ...     frequency_weight=0.0
        ... )
        >>> print(profile)
        Custom Walk: High temperature, neutral frequency
    """

    name: str
    description: str
    max_flips: int
    temperature: float
    frequency_weight: float

    def __str__(self) -> str:
        """String representation showing name and description."""
        return f"{self.name}: {self.description}"


# Predefined walk profiles
# These profiles were designed to provide distinct, evocative behaviors
WALK_PROFILES: dict[str, WalkProfile] = {
    "clerical": WalkProfile(
        name="Clerical Walk",
        description="Conservative, favors common syllables, minimal phonetic change",
        max_flips=1,
        temperature=0.3,
        frequency_weight=1.0,
    ),
    "dialect": WalkProfile(
        name="Dialect Walk",
        description="Moderate exploration, neutral frequency bias",
        max_flips=2,
        temperature=0.7,
        frequency_weight=0.0,
    ),
    "goblin": WalkProfile(
        name="Goblin Walk",
        description="Chaotic, favors rare syllables, high phonetic variation",
        max_flips=2,
        temperature=1.5,
        frequency_weight=-0.5,
    ),
    "ritual": WalkProfile(
        name="Ritual Walk",
        description="Maximum exploration, strongly favors rare syllables",
        max_flips=3,
        temperature=2.5,
        frequency_weight=-1.0,
    ),
}


def get_profile(name: str) -> WalkProfile:
    """Get a walk profile by name.

    Args:
        name: Profile name (case-insensitive)

    Returns:
        WalkProfile object

    Raises:
        ValueError: If profile name not found

    Example:
        >>> profile = get_profile("goblin")
        >>> profile.temperature
        1.5
        >>> profile = get_profile("GOBLIN")  # Case-insensitive
        >>> profile.temperature
        1.5
    """
    name_lower = name.lower()
    if name_lower not in WALK_PROFILES:
        available = ", ".join(WALK_PROFILES.keys())
        raise ValueError(f"Unknown profile '{name}'. Available: {available}")
    return WALK_PROFILES[name_lower]


def list_profiles() -> dict[str, WalkProfile]:
    """Get all available walk profiles.

    Returns:
        Dictionary mapping profile names to WalkProfile objects (copy)

    Example:
        >>> profiles = list_profiles()
        >>> for name, profile in profiles.items():
        ...     print(f"{name}: {profile.description}")
        clerical: Conservative, favors common syllables, minimal phonetic change
        dialect: Moderate exploration, neutral frequency bias
        goblin: Chaotic, favors rare syllables, high phonetic variation
        ritual: Maximum exploration, strongly favors rare syllables
    """
    return WALK_PROFILES.copy()
