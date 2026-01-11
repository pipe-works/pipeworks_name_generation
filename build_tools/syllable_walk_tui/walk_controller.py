"""
Walk Controller - Bridge Between TUI and Syllable Walker

This module translates TUI module states (oscillator, envelope, filter, etc.)
into syllable_walk parameters and generates outputs.
"""

import random
from pathlib import Path
from typing import Optional

from build_tools.syllable_walk import SyllableWalker


class WalkController:
    """
    Translates TUI control states into syllable walk parameters.

    The controller manages:
    - Corpus loading (NLTK vs Pyphen)
    - Walk parameter mapping from TUI controls
    - Word generation from syllable sequences
    """

    def __init__(self):
        """
        Initialize the walk controller.

        The controller starts with no corpus loaded. Use load_corpus()
        to load a specific corpus file.
        """
        self.corpus_type: Optional[str] = None
        self.corpus_path: Optional[str] = None
        self.walker: Optional[SyllableWalker] = None

    def load_corpus(self, corpus_path: str, corpus_type: Optional[str] = None):
        """
        Load a corpus from the given path.

        Args:
            corpus_path: Path to annotated syllables JSON file
            corpus_type: Optional type identifier ("nltk" or "pyphen")
                        If not provided, attempts to infer from filename

        Raises:
            FileNotFoundError: If corpus file doesn't exist
            ValueError: If file is not a valid annotated syllables JSON
        """
        path = Path(corpus_path)
        if not path.exists():
            raise FileNotFoundError(f"Corpus not found: {corpus_path}")

        # Infer type from filename if not provided
        if corpus_type is None:
            if "pyphen" in path.name:
                corpus_type = "pyphen"
            elif "nltk" in path.name:
                corpus_type = "nltk"
            else:
                corpus_type = "unknown"

        # Load the walker
        self.walker = SyllableWalker(str(path))
        self.corpus_path = corpus_path
        self.corpus_type = corpus_type

    def generate_word(
        self,
        steps: int = 5,
        temperature: float = 1.0,
        frequency_weight: float = 0.0,
        max_flips: int = 2,
        seed: Optional[int] = None,
    ) -> str:
        """
        Generate a single word by walking through syllable space.

        Args:
            steps: Number of syllables in the walk
            temperature: Exploration temperature (0.1-5.0)
            frequency_weight: Bias toward common/rare (-2.0 to 2.0)
            max_flips: Max feature flips per step (1-3)
            seed: Random seed for reproducibility

        Returns:
            A single word formed by concatenating walk syllables
        """
        if not self.walker:
            raise RuntimeError("Walker not initialized")

        # Pick a random starting syllable if no seed provided
        if seed is None:
            seed = random.randint(0, 1_000_000)  # noqa: S311

        # Use the seed to pick a random starting syllable
        rng = random.Random(seed)  # noqa: S311
        start_idx = rng.randint(0, len(self.walker.syllables) - 1)

        # Perform the walk
        walk = self.walker.walk(
            start=start_idx,
            steps=steps,
            max_flips=max_flips,
            temperature=temperature,
            frequency_weight=frequency_weight,
            seed=seed + 1,  # Offset seed so start != walk randomness
        )

        # Collapse syllables into a word
        syllables = [step["syllable"] for step in walk]
        return "".join(syllables)

    def generate_words(
        self,
        count: int,
        steps: int = 5,
        temperature: float = 1.0,
        frequency_weight: float = 0.0,
        max_flips: int = 2,
    ) -> list[str]:
        """
        Generate multiple words with randomized seeds.

        Args:
            count: Number of words to generate
            steps: Syllables per word
            temperature: Exploration temperature
            frequency_weight: Frequency bias
            max_flips: Max feature flips per step

        Returns:
            List of generated words
        """
        words = []
        for _ in range(count):
            word = self.generate_word(
                steps=steps,
                temperature=temperature,
                frequency_weight=frequency_weight,
                max_flips=max_flips,
                seed=None,  # Random seed for each word
            )
            words.append(word)
        return words

    def get_corpus_info(self) -> dict:
        """
        Get information about the current corpus.

        Returns:
            Dict with corpus metadata. If no corpus loaded, returns
            dict with loaded=False.
        """
        if not self.walker:
            return {"loaded": False}

        return {
            "loaded": True,
            "corpus_type": self.corpus_type or "unknown",
            "corpus_path": self.corpus_path,
            "syllable_count": len(self.walker.syllables),
            "max_neighbor_distance": self.walker.max_neighbor_distance,
        }
