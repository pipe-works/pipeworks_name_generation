"""
State management for Syllable Walker TUI.

This module provides dataclasses for managing application state,
including patch configurations and isolated RNG instances.
"""

import random
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PatchState:
    """
    State for a single patch configuration.

    Maintains isolated RNG instance to avoid global random state contamination.

    Attributes:
        name: Identifier for this patch (e.g., "A" or "B")
        seed: Random seed for reproducible generation
        rng: Isolated Random instance for this patch
        corpus_dir: Path to corpus directory (None if not selected)
        corpus_type: Detected corpus type ("NLTK" or "Pyphen", None if not selected)

        # Quick metadata (loaded immediately, ~50KB)
        syllables: List of unique syllables loaded from corpus (None if not loaded)
        frequencies: Dictionary mapping syllable to frequency count (None if not loaded)

        # Full phonetic feature data (loaded in background, ~15MB)
        annotated_data: List of syllable dicts with phonetic features (None if not loaded)
        is_loading_annotated: Flag indicating background loading in progress
        loading_error: Error message if annotated data failed to load (None if no error)

        # Walk profile parameters (defaults to "Dialect" profile)
        min_length: Minimum syllable character count (1-10)
        max_length: Maximum syllable character count (1-10)
        walk_length: Number of syllables to chain (2-20)
        max_flips: Maximum feature changes per step (1-3)
        temperature: Exploration randomness, higher = more chaos (0.1-5.0)
        frequency_weight: Bias toward common (+) or rare (-) syllables (-2.0 to 2.0)
        neighbor_limit: Candidate pool size per step (5-50)
        outputs: Generated names from last generation
    """

    name: str
    seed: int = field(default_factory=lambda: random.SystemRandom().randint(0, 2**32 - 1))
    current_profile: str = "dialect"  # Current profile selection (or "custom" for manual)
    corpus_dir: Path | None = None
    corpus_type: str | None = None

    # Quick metadata (loaded synchronously)
    syllables: list[str] | None = None
    frequencies: dict[str, int] | None = None

    # Full annotated data (loaded asynchronously in background)
    annotated_data: list[dict] | None = None
    is_loading_annotated: bool = False
    loading_error: str | None = None

    # Walk profile parameters (defaults match "Dialect" profile from profiles.py)
    min_length: int = 2  # Syllable character count min
    max_length: int = 5  # Syllable character count max
    walk_length: int = 5  # Number of syllables to chain
    max_flips: int = 2  # Feature changes per step (1-3)
    temperature: float = 0.7  # Exploration randomness (0.1-5.0)
    frequency_weight: float = 0.0  # Bias toward common (+) or rare (-) (-2.0 to 2.0)
    neighbor_limit: int = 10  # Candidate pool size per step
    outputs: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize isolated RNG instance after dataclass initialization."""
        self.rng = random.Random(self.seed)  # nosec B311 - Not for cryptographic use

    def generate_seed(self) -> int:
        """
        Generate a new random seed using system entropy.

        Returns:
            New random seed value

        Note:
            Uses SystemRandom to avoid global random state contamination.
        """
        self.seed = random.SystemRandom().randint(0, 2**32 - 1)
        self.rng = random.Random(self.seed)  # nosec B311 - Not for cryptographic use
        return self.seed

    def is_ready_for_generation(self) -> bool:
        """
        Check if patch has all required data loaded for name generation.

        A patch is ready when:
        1. Corpus directory is selected
        2. Quick metadata (syllables, frequencies) is loaded
        3. Annotated data with phonetic features is loaded
        4. Not currently loading
        5. No loading errors

        Returns:
            True if patch can generate names, False otherwise
        """
        return (
            self.corpus_dir is not None
            and self.syllables is not None
            and self.frequencies is not None
            and self.annotated_data is not None
            and not self.is_loading_annotated
            and self.loading_error is None
        )


@dataclass
class AppState:
    """
    Global application state.

    Attributes:
        patch_a: Configuration for patch A
        patch_b: Configuration for patch B
        current_focus: Currently focused panel ("patch_a", "patch_b", or "stats")
        last_browse_dir: Last directory browsed (for remembering location)
    """

    patch_a: PatchState = field(default_factory=lambda: PatchState(name="A"))
    patch_b: PatchState = field(default_factory=lambda: PatchState(name="B"))
    current_focus: str = "patch_a"
    last_browse_dir: Path | None = None
