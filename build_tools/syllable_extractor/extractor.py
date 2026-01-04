"""
Core syllable extraction functionality.

This module provides the main SyllableExtractor class for extracting syllables
from text using pyphen's dictionary-based hyphenation.
"""

import re
import sys
from pathlib import Path
from typing import Set

try:
    import pyphen  # type: ignore[import-untyped]
except ImportError:
    print("Error: pyphen is not installed.")
    print("Install it with: pip install pyphen")
    sys.exit(1)


class SyllableExtractor:
    """
    Extracts syllables from text using pyphen hyphenation dictionaries.

    This class provides methods to process text files and extract individual
    syllables based on language-specific hyphenation rules from LibreOffice's
    dictionary collection.

    The extractor works by:
    1. Reading text input (string or file)
    2. Tokenizing into words using regex
    3. Applying language-specific hyphenation rules via pyphen
    4. Splitting hyphenated words into syllables
    5. Filtering syllables by length constraints
    6. Returning unique syllables (case-insensitive)

    Key Features:
        - Support for 40+ languages via pyphen
        - Configurable syllable length constraints
        - Option to include/exclude non-hyphenated words
        - Case-insensitive processing
        - Unicode support for accented characters
        - Deterministic extraction (same input = same output)

    Typical Usage:
        >>> # Basic extraction
        >>> extractor = SyllableExtractor('en_US', min_syllable_length=2, max_syllable_length=8)
        >>> syllables = extractor.extract_syllables_from_text("Hello wonderful world")
        >>> print(sorted(syllables))
        ['der', 'ful', 'hel', 'lo', 'won', 'world']

        >>> # Extract from file and save
        >>> syllables = extractor.extract_syllables_from_file(Path('input.txt'))
        >>> extractor.save_syllables(syllables, Path('output.txt'))

    Attributes:
        dictionary: Pyphen hyphenation dictionary for the selected language
        language_code: The pyphen language/locale code (e.g., 'en_US', 'de_DE')
        min_syllable_length: Minimum syllable length to include in results
        max_syllable_length: Maximum syllable length to include in results

    Note:
        This is a build-time tool. The pyphen dependency should not be used
        at runtime in the core name generation system.
    """

    def __init__(
        self, language_code: str, min_syllable_length: int = 1, max_syllable_length: int = 10
    ):
        """
        Initialize the syllable extractor with a specific language.

        Args:
            language_code: Pyphen language/locale code (e.g., 'en_US', 'de_DE')
            min_syllable_length: Minimum syllable length to include (default: 1)
            max_syllable_length: Maximum syllable length to include (default: 10)

        Raises:
            ValueError: If the language code is not supported by pyphen
        """
        try:
            self.dictionary = pyphen.Pyphen(lang=language_code)
            self.language_code = language_code
            self.min_syllable_length = min_syllable_length
            self.max_syllable_length = max_syllable_length
        except KeyError:
            available = ", ".join(sorted(pyphen.LANGUAGES.keys()))
            raise ValueError(
                f"Language code '{language_code}' is not supported by pyphen.\n"
                f"Available codes: {available}"
            )

    def extract_syllables_from_text(self, text: str, only_hyphenated: bool = True) -> Set[str]:
        """
        Extract unique syllables from a block of text.

        Args:
            text: Input text to process
            only_hyphenated: If True, only include syllables from words that pyphen
                           actually hyphenated (default: True). This filters out
                           whole words that couldn't be syllabified.

        Returns:
            Set of unique syllables extracted from the text

        Note:
            - Only processes words containing alphabetic characters
            - Case-insensitive (converts to lowercase)
            - Removes punctuation and special characters
            - Filters syllables by min/max length constraints
            - When only_hyphenated=True, excludes words pyphen couldn't split
        """
        # Extract words using regex (alphanumeric sequences)
        words = re.findall(r"\b[a-zA-ZÀ-ÿ]+\b", text)

        syllables: Set[str] = set()

        for word in words:
            # Convert to lowercase for consistency
            word_lower = word.lower()

            # Get hyphenated version of the word
            # pyphen.inserted() returns the word with hyphens at syllable boundaries
            hyphenated = self.dictionary.inserted(word_lower, hyphen="-")

            # Check if the word was actually hyphenated
            # If no hyphens were inserted, the word couldn't be syllabified
            if only_hyphenated and "-" not in hyphenated:
                continue

            # Split on hyphens to get individual syllables
            word_syllables = hyphenated.split("-")

            # Filter syllables by length and add to set
            for syllable in word_syllables:
                if self.min_syllable_length <= len(syllable) <= self.max_syllable_length:
                    syllables.add(syllable)

        return syllables

    def extract_syllables_from_file(self, input_path: Path) -> Set[str]:
        """
        Extract unique syllables from a text file.

        Args:
            input_path: Path to the input text file

        Returns:
            Set of unique syllables extracted from the file

        Raises:
            FileNotFoundError: If the input file doesn't exist
            IOError: If there's an error reading the file
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            raise IOError(f"Error reading file {input_path}: {e}")

        return self.extract_syllables_from_text(text)

    def save_syllables(self, syllables: Set[str], output_path: Path) -> None:
        """
        Save syllables to a text file (one syllable per line, sorted).

        Args:
            syllables: Set of syllables to save
            output_path: Path to the output file

        Raises:
            IOError: If there's an error writing the file
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                for syllable in sorted(syllables):
                    f.write(f"{syllable}\n")
        except Exception as e:
            raise IOError(f"Error writing file {output_path}: {e}")
