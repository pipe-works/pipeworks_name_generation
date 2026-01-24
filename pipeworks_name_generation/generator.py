"""Core name generation - minimal proof of concept version.

This is the SIMPLEST possible implementation that passes tests.
Features to add later:
- Pattern loading from YAML files
- Phonotactic constraints
- Custom pattern sets
- Performance optimization

For now: Hardcoded syllables, basic logic.
"""

from __future__ import annotations

import random


class NameGenerator:
    """Generate phonetically-plausible names deterministically.

    This is a minimal proof-of-concept implementation with hardcoded
    syllables. Pattern loading and advanced features will be added later.

    The key requirement is DETERMINISM: same seed = same name, always.
    This is critical for games where entity IDs must map to consistent names.

    Args:
        pattern: Pattern set name (currently only "simple" is supported)

    Raises:
        ValueError: If pattern is not recognized

    Example:
        >>> gen = NameGenerator(pattern="simple")
        >>> name = gen.generate(seed=42)
        >>> assert gen.generate(seed=42) == name  # Deterministic!
    """

    # Hardcoded syllables for proof of concept
    # These are phonetically plausible combinations
    # TODO: Load from pattern files in next phase
    _SIMPLE_SYLLABLES = [
        # Soft/flowing syllables
        "ka",
        "la",
        "thin",
        "mar",
        "in",
        "del",
        "so",
        "ra",
        "vyn",
        "tha",
        "len",
        "is",
        "el",
        "an",
        "dor",
        "mir",
        "eth",
        "al",
        # Harder syllables
        "grim",
        "thor",
        "ak",
        "bor",
        "din",
        "wyn",
        "krag",
        "durn",
        "mok",
        "gor",
        "thrak",
        "zar",
    ]

    def __init__(self, pattern: str) -> None:
        """Initialize generator with a pattern set.

        Args:
            pattern: Pattern set name (only "simple" supported in POC)

        Raises:
            ValueError: If pattern is not recognized
        """
        # Validate pattern
        if pattern != "simple":
            raise ValueError(
                f"Unknown pattern: '{pattern}'. "
                f"Only 'simple' is currently supported in proof of concept."
            )

        self.pattern = pattern
        self._syllables = self._SIMPLE_SYLLABLES.copy()

    def generate(self, seed: int, syllables: int | None = None) -> str:
        """Generate a single name deterministically.

        This is the core method. Given the same seed, it MUST produce
        the same name every time. This determinism is critical for games.

        Args:
            seed: Random seed for deterministic generation.
                  Same seed = same name, always.
            syllables: Number of syllables to use (defaults to random 2-3).
                      Must be between 1 and len(available syllables).

        Returns:
            Generated name string, capitalized (e.g., "Kalathin")

        Raises:
            ValueError: If syllable count is invalid

        Example:
            >>> gen = NameGenerator(pattern="simple")
            >>> gen.generate(seed=1)
            'Marindel'
            >>> gen.generate(seed=1)  # Same seed
            'Marindel'  # Same name!
            >>> gen.generate(seed=2)  # Different seed
            'Soravyn'  # Different name
        """
        # Create deterministic random generator
        # CRITICAL: Use Random(seed), not random.seed()
        # Random(seed) creates isolated RNG, avoiding global state
        # nosec B311: random.Random is intentionally used for deterministic generation,
        # not cryptographic purposes
        rng = random.Random(seed)  # nosec B311

        # Decide syllable count if not specified
        if syllables is None:
            syllables = rng.randint(2, 3)

        # Validate syllable count
        if syllables < 1:
            raise ValueError("Syllable count must be at least 1")
        if syllables > len(self._syllables):
            raise ValueError(
                f"Cannot generate {syllables} syllables with only "
                f"{len(self._syllables)} available syllables"
            )

        # Select syllables without replacement
        # This prevents "kakaka" type repetition
        chosen = rng.sample(self._syllables, k=syllables)

        # Combine syllables and capitalize first letter only
        name = "".join(chosen).capitalize()

        return name

    def generate_batch(
        self,
        count: int,
        base_seed: int,
        unique: bool = True,
    ) -> list[str]:
        """Generate multiple names at once.

        This is useful for bulk generation (e.g., populating a town with NPCs).

        Args:
            count: Number of names to generate
            base_seed: Starting seed (incremented for each name)
            unique: If True, ensure all names are different

        Returns:
            List of generated names

        Raises:
            ValueError: If unable to generate enough unique names

        Example:
            >>> gen = NameGenerator(pattern="simple")
            >>> names = gen.generate_batch(count=3, base_seed=100)
            >>> len(names)
            3
            >>> names == gen.generate_batch(count=3, base_seed=100)
            True  # Deterministic!
        """
        names: list[str] = []
        seed = base_seed
        attempts = 0
        max_attempts = count * 100  # Prevent infinite loop

        while len(names) < count and attempts < max_attempts:
            name = self.generate(seed=seed)

            if unique and name in names:
                # Name collision, try next seed
                seed += 1
                attempts += 1
                continue

            names.append(name)
            seed += 1
            attempts += 1

        if len(names) < count:
            raise ValueError(
                f"Could not generate {count} unique names. "
                f"Only generated {len(names)}. Try a larger syllable pool."
            )

        return names

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"NameGenerator(pattern='{self.pattern}')"
