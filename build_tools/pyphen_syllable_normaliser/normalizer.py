"""
Core normalization logic for syllable canonicalization.

This module provides the SyllableNormalizer class which handles the transformation
of raw syllables into canonical form through Unicode normalization, diacritic
stripping, lowercase conversion, and validation.
"""

from __future__ import annotations

import unicodedata
from typing import Literal, cast

from .models import NormalizationConfig


class SyllableNormalizer:
    """
    Normalizes syllables to canonical form.

    This class applies a multi-step normalization pipeline to transform raw
    syllables into a standardized canonical representation. The pipeline
    includes Unicode normalization, diacritic removal, case normalization,
    and validation against charset and length constraints.

    Attributes:
        config: Configuration specifying normalization parameters such as
            allowed charset, length constraints, and Unicode normalization form.

    Example:
        >>> from build_tools.pyphen_syllable_normaliser import NormalizationConfig
        >>> config = NormalizationConfig(min_length=2, max_length=8)
        >>> normalizer = SyllableNormalizer(config)
        >>> normalizer.normalize("Café")
        'cafe'
        >>> normalizer.normalize("x")  # Too short
        None
        >>> normalizer.normalize("résumé123")  # Invalid characters
        None
    """

    def __init__(self, config: NormalizationConfig):
        """
        Initialize normalizer with configuration.

        Args:
            config: NormalizationConfig instance specifying normalization
                parameters including charset, length constraints, and
                Unicode normalization form.

        Example:
            >>> config = NormalizationConfig(
            ...     min_length=3,
            ...     max_length=10,
            ...     allowed_charset="abcdefghijklmnopqrstuvwxyz",
            ...     unicode_form="NFKD"
            ... )
            >>> normalizer = SyllableNormalizer(config)
        """
        self.config = config

    def normalize(self, syllable: str) -> str | None:
        """
        Normalize a single syllable to canonical form.

        Applies the complete normalization pipeline:
        1. Unicode normalization (NFKD by default)
        2. Strip diacritics (remove combining characters)
        3. Lowercase conversion
        4. Trim whitespace
        5. Validate charset (only allowed characters)
        6. Check length constraints

        Args:
            syllable: Raw syllable string to normalize.

        Returns:
            Normalized canonical syllable string, or None if the syllable
            is rejected due to:
            - Becoming empty after normalization
            - Containing invalid characters
            - Not meeting length constraints

        Example:
            >>> config = NormalizationConfig()
            >>> normalizer = SyllableNormalizer(config)
            >>> normalizer.normalize("Café")
            'cafe'
            >>> normalizer.normalize("  HELLO  ")
            'hello'
            >>> normalizer.normalize("résumé")
            'resume'
            >>> normalizer.normalize("")  # Empty
            None
            >>> normalizer.normalize("x")  # Too short (min_length=2)
            None
            >>> normalizer.normalize("hello123")  # Invalid chars
            None
        """
        # Step 1: Unicode normalization
        form = cast(Literal["NFC", "NFD", "NFKC", "NFKD"], self.config.unicode_form)
        normalized = unicodedata.normalize(form, syllable)

        # Step 2: Strip diacritics (remove combining characters)
        normalized = self.strip_diacritics(normalized)

        # Step 3: Lowercase conversion
        normalized = normalized.lower()

        # Step 4: Trim whitespace
        normalized = normalized.strip()

        # Check if empty after normalization
        if not normalized:
            return None

        # Step 5: Validate charset (only allowed characters)
        if not self._is_valid_charset(normalized):
            return None

        # Step 6: Check length constraints
        if not self._is_valid_length(normalized):
            return None

        return normalized

    def strip_diacritics(self, text: str) -> str:
        """
        Remove diacritics (accent marks) from Unicode text.

        Uses Unicode normalization (NFD/NFKD) to decompose characters into
        base characters and combining marks, then removes the combining marks.
        This converts accented characters like 'é' → 'e', 'ñ' → 'n', etc.

        Args:
            text: Unicode string potentially containing diacritics.

        Returns:
            String with all combining diacritical marks removed.

        Example:
            >>> normalizer = SyllableNormalizer(NormalizationConfig())
            >>> normalizer.strip_diacritics("café")
            'cafe'
            >>> normalizer.strip_diacritics("naïve")
            'naive'
            >>> normalizer.strip_diacritics("Zürich")
            'Zurich'
            >>> normalizer.strip_diacritics("São Paulo")
            'Sao Paulo'

        Note:
            This method assumes the text has already been normalized to
            NFD or NFKD form. The normalize() method handles this automatically.
        """
        # Filter out combining characters (category Mn = Mark, nonspacing)
        return "".join(char for char in text if unicodedata.category(char) != "Mn")

    def _is_valid_charset(self, syllable: str) -> bool:
        """
        Check if syllable contains only allowed characters.

        Args:
            syllable: Syllable string to validate.

        Returns:
            True if all characters are in allowed_charset, False otherwise.

        Example:
            >>> config = NormalizationConfig(allowed_charset="abcdefghijklmnopqrstuvwxyz")
            >>> normalizer = SyllableNormalizer(config)
            >>> normalizer._is_valid_charset("hello")
            True
            >>> normalizer._is_valid_charset("hello123")
            False
            >>> normalizer._is_valid_charset("hello-world")
            False
        """
        return all(char in self.config.allowed_charset for char in syllable)

    def _is_valid_length(self, syllable: str) -> bool:
        """
        Check if syllable meets length constraints.

        Args:
            syllable: Syllable string to validate.

        Returns:
            True if syllable length is between min_length and max_length
            (inclusive), False otherwise.

        Example:
            >>> config = NormalizationConfig(min_length=2, max_length=8)
            >>> normalizer = SyllableNormalizer(config)
            >>> normalizer._is_valid_length("ab")
            True
            >>> normalizer._is_valid_length("hello")
            True
            >>> normalizer._is_valid_length("x")
            False
            >>> normalizer._is_valid_length("verylongword")
            False
        """
        length = len(syllable)
        return self.config.min_length <= length <= self.config.max_length


def normalize_batch(
    syllables: list[str], config: NormalizationConfig
) -> tuple[list[str], dict[str, int]]:
    """
    Normalize a batch of syllables and collect rejection statistics.

    This is a convenience function for normalizing multiple syllables at once
    while tracking why syllables were rejected.

    Args:
        syllables: List of raw syllable strings to normalize.
        config: NormalizationConfig specifying normalization parameters.

    Returns:
        Tuple of (normalized_syllables, rejection_stats) where:
        - normalized_syllables: List of successfully normalized syllables
        - rejection_stats: Dictionary with rejection counts:
            - "rejected_empty": Syllables that became empty after normalization
            - "rejected_charset": Syllables with invalid characters
            - "rejected_length": Syllables outside length constraints

    Example:
        >>> config = NormalizationConfig(min_length=2, max_length=8)
        >>> syllables = ["Café", "x", "Hello", "world123", "  résumé  "]
        >>> normalized, stats = normalize_batch(syllables, config)
        >>> normalized
        ['cafe', 'hello', 'resume']
        >>> stats
        {'rejected_empty': 0, 'rejected_charset': 1, 'rejected_length': 1}

    Note:
        This function processes syllables in order and preserves duplicates.
        For frequency analysis, use the frequency.py module which handles
        deduplication and counting.
    """
    normalizer = SyllableNormalizer(config)
    normalized_syllables: list[str] = []
    rejection_stats = {
        "rejected_empty": 0,
        "rejected_charset": 0,
        "rejected_length": 0,
    }

    for syllable in syllables:
        # Try each normalization step to track specific rejection reasons
        # Step 1-4: Unicode normalization, diacritic stripping, lowercase, trim
        form = cast(Literal["NFC", "NFD", "NFKC", "NFKD"], config.unicode_form)
        temp = unicodedata.normalize(form, syllable)
        temp = normalizer.strip_diacritics(temp)
        temp = temp.lower().strip()

        # Check if empty after normalization
        if not temp:
            rejection_stats["rejected_empty"] += 1
            continue

        # Check charset
        if not normalizer._is_valid_charset(temp):
            rejection_stats["rejected_charset"] += 1
            continue

        # Check length
        if not normalizer._is_valid_length(temp):
            rejection_stats["rejected_length"] += 1
            continue

        # All checks passed
        normalized_syllables.append(temp)

    return normalized_syllables, rejection_stats
