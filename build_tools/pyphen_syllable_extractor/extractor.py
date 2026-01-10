"""
Core syllable extraction functionality.

This module provides the main SyllableExtractor class for extracting syllables
from text using pyphen's dictionary-based hyphenation.
"""

import re
from pathlib import Path
from typing import Dict, Set

# Optional dependency - only needed at runtime, not for documentation builds
try:
    import pyphen  # type: ignore[import-not-found, import-untyped]

    PYPHEN_AVAILABLE = True
except ImportError:
    pyphen = None  # type: ignore[assignment]
    PYPHEN_AVAILABLE = False


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
            ImportError: If pyphen is not installed
            ValueError: If the language code is not supported by pyphen
        """
        if not PYPHEN_AVAILABLE:
            raise ImportError(
                "pyphen is not installed. This is a build-time dependency.\n"
                "Install it with: pip install pyphen"
            )

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

    def extract_syllables_from_text(
        self, text: str, only_hyphenated: bool = True
    ) -> tuple[Set[str], Dict[str, int]]:
        """
        Extract unique syllables from a block of text.

        This method processes input text by tokenizing it into words, applying
        hyphenation rules via pyphen, and extracting individual syllables that
        meet the configured length constraints.

        Args:
            text: Input text to process. Can contain any characters, but only
                  alphabetic sequences (including accented characters) will be
                  processed as words.
            only_hyphenated: If True, only include syllables from words that pyphen
                           actually hyphenated (default: True). This filters out
                           whole words that couldn't be syllabified. Set to False
                           to include all words, even if they can't be split.

        Returns:
            Tuple of (syllables, statistics) where:
                - syllables: Set of unique lowercase syllable strings
                - statistics: Dict with the following keys:
                    - 'total_words': Total number of words found in source text
                    - 'processed_words': Words that were successfully hyphenated/processed
                    - 'skipped_unhyphenated': Words skipped (only when only_hyphenated=True)
                    - 'rejected_syllables': Syllables rejected due to length constraints

        Note:
            - Only processes words containing alphabetic characters (a-z, A-Z, À-ÿ)
            - Case-insensitive processing (all output is lowercase)
            - Automatically removes punctuation and special characters
            - Filters syllables by configured min/max length constraints
            - When only_hyphenated=True, excludes words pyphen couldn't split
            - Deterministic: same input always produces same output
            - Words are extracted using regex pattern: \\b[a-zA-ZÀ-ÿ]+\\b

        Example:
            >>> extractor = SyllableExtractor('en_US', min_syllable_length=2, max_syllable_length=8)
            >>> syllables, stats = extractor.extract_syllables_from_text("Hello world!")
            >>> print(sorted(syllables))
            ['hel', 'lo', 'world']
            >>> print(stats['total_words'])
            2
        """
        # Extract words using regex (alphanumeric sequences)
        words = re.findall(r"\b[a-zA-ZÀ-ÿ]+\b", text)

        syllables: Set[str] = set()
        stats = {
            "total_words": len(words),
            "skipped_unhyphenated": 0,
            "rejected_syllables": 0,
            "processed_words": 0,
        }

        for word in words:
            # Convert to lowercase for consistency
            word_lower = word.lower()

            # Get hyphenated version of the word
            # pyphen.inserted() returns the word with hyphens at syllable boundaries
            hyphenated = self.dictionary.inserted(word_lower, hyphen="-")

            # Check if the word was actually hyphenated
            # If no hyphens were inserted, the word couldn't be syllabified
            if only_hyphenated and "-" not in hyphenated:
                stats["skipped_unhyphenated"] += 1
                continue

            stats["processed_words"] += 1

            # Split on hyphens to get individual syllables
            word_syllables = hyphenated.split("-")

            # Filter syllables by length and add to set
            for syllable in word_syllables:
                if self.min_syllable_length <= len(syllable) <= self.max_syllable_length:
                    syllables.add(syllable)
                else:
                    stats["rejected_syllables"] += 1

        return syllables, stats

    def extract_syllables_from_file(self, input_path: Path) -> tuple[Set[str], Dict[str, int]]:
        """
        Extract unique syllables from a text file.

        This is a convenience wrapper around extract_syllables_from_text() that
        handles file reading with proper encoding (UTF-8) and error handling.

        Args:
            input_path: Path to the input text file. File should be UTF-8 encoded
                       plain text. Binary files or non-text formats will cause errors.

        Returns:
            Tuple of (syllables, statistics) where:
                - syllables: Set of unique lowercase syllable strings
                - statistics: Dict with processing statistics (see extract_syllables_from_text)

        Raises:
            FileNotFoundError: If the input file doesn't exist at the specified path
            IOError: If there's an error reading the file (permissions, encoding, etc.)

        Example:
            >>> from pathlib import Path
            >>> extractor = SyllableExtractor('en_US', min_syllable_length=2, max_syllable_length=8)
            >>> syllables, stats = extractor.extract_syllables_from_file(Path('book.txt'))
            >>> print(f"Extracted {len(syllables)} unique syllables from {stats['total_words']} words")
            Extracted 1250 unique syllables from 50000 words
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

        Writes syllables in alphabetical order with UTF-8 encoding, one syllable
        per line. This format is ideal for version control and easy importing into
        other tools.

        Args:
            syllables: Set of syllables to save. Each syllable should be a string.
                      The set will be sorted alphabetically before writing.
            output_path: Path to the output file. Parent directories must exist.
                        If the file exists, it will be overwritten.

        Raises:
            IOError: If there's an error writing the file (permissions, disk space, etc.)

        Example:
            >>> from pathlib import Path
            >>> extractor = SyllableExtractor('en_US')
            >>> syllables = {'hel', 'lo', 'world'}
            >>> extractor.save_syllables(syllables, Path('output.txt'))
            # Creates file with content:
            # hel
            # lo
            # world

        Note:
            The output file uses UTF-8 encoding with Unix-style line endings (\\n).
            Each line contains exactly one syllable with no leading/trailing whitespace.
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                for syllable in sorted(syllables):
                    f.write(f"{syllable}\n")
        except Exception as e:
            raise IOError(f"Error writing file {output_path}: {e}")

    @staticmethod
    def extract_with_auto_language(
        text: str,
        min_syllable_length: int = 1,
        max_syllable_length: int = 10,
        only_hyphenated: bool = True,
        default_language: str = "en_US",
        min_detection_length: int = 20,
        suppress_warnings: bool = False,
    ) -> tuple[Set[str], Dict[str, int], str]:
        """
        Extract syllables with automatic language detection.

        This convenience method combines language detection with syllable extraction.
        It automatically detects the language of the input text and creates an
        appropriate SyllableExtractor instance for that language.

        Args:
            text: Input text to process. Should be at least 20-50 characters for
                  reliable language detection.
            min_syllable_length: Minimum syllable length to include (default: 1)
            max_syllable_length: Maximum syllable length to include (default: 10)
            only_hyphenated: If True, only include syllables from hyphenated words
                           (default: True)
            default_language: Language code to use if detection fails (default: "en_US")
            min_detection_length: Minimum text length for detection attempt (default: 20)
            suppress_warnings: If True, suppress language detection warnings (default: False)

        Returns:
            Tuple of (syllables, statistics, detected_language_code) where:
                - syllables: Set of unique lowercase syllable strings
                - statistics: Dict with processing statistics
                - detected_language_code: The pyphen language code that was used

        Raises:
            ImportError: If langdetect is not installed (unless suppress_warnings=True)

        Example:
            >>> # Auto-detect English text
            >>> text = "Hello beautiful world, this is wonderful"
            >>> syllables, stats, lang = SyllableExtractor.extract_with_auto_language(text)
            >>> print(f"Detected language: {lang}")
            Detected language: en_US
            >>> print(f"Found {len(syllables)} syllables")
            Found 8 syllables

            >>> # Auto-detect French text
            >>> text = "Bonjour le monde, comment allez-vous aujourd'hui?"
            >>> syllables, stats, lang = SyllableExtractor.extract_with_auto_language(text)
            >>> print(f"Detected language: {lang}")
            Detected language: fr

            >>> # With custom parameters
            >>> syllables, stats, lang = SyllableExtractor.extract_with_auto_language(
            ...     text="Das sind deutsche Wörter",
            ...     min_syllable_length=2,
            ...     max_syllable_length=8,
            ...     default_language="en_US"
            ... )
            >>> print(lang)
            de_DE

        Note:
            - Requires langdetect: pip install langdetect
            - Detection accuracy depends on text length (20-50+ chars recommended)
            - For production use, consider setting suppress_warnings=True
            - Short text will fall back to default_language with a warning
        """
        from .language_detection import detect_language_code

        # Detect language
        language_code = detect_language_code(
            text,
            default=default_language,
            min_confidence_length=min_detection_length,
            suppress_warnings=suppress_warnings,
        )

        # Create extractor with detected language
        extractor = SyllableExtractor(
            language_code=language_code,
            min_syllable_length=min_syllable_length,
            max_syllable_length=max_syllable_length,
        )

        # Extract syllables
        syllables, stats = extractor.extract_syllables_from_text(text, only_hyphenated)

        return syllables, stats, language_code

    @staticmethod
    def extract_file_with_auto_language(
        input_path: Path,
        min_syllable_length: int = 1,
        max_syllable_length: int = 10,
        only_hyphenated: bool = True,
        default_language: str = "en_US",
        min_detection_length: int = 20,
        suppress_warnings: bool = False,
    ) -> tuple[Set[str], Dict[str, int], str]:
        """
        Extract syllables from a file with automatic language detection.

        This convenience method reads a file, detects its language, and extracts
        syllables using the appropriate language-specific hyphenation rules.

        Args:
            input_path: Path to the input text file
            min_syllable_length: Minimum syllable length to include (default: 1)
            max_syllable_length: Maximum syllable length to include (default: 10)
            only_hyphenated: If True, only include syllables from hyphenated words
                           (default: True)
            default_language: Language code to use if detection fails (default: "en_US")
            min_detection_length: Minimum text length for detection attempt (default: 20)
            suppress_warnings: If True, suppress language detection warnings (default: False)

        Returns:
            Tuple of (syllables, statistics, detected_language_code) where:
                - syllables: Set of unique lowercase syllable strings
                - statistics: Dict with processing statistics
                - detected_language_code: The pyphen language code that was used

        Raises:
            FileNotFoundError: If the input file doesn't exist
            IOError: If there's an error reading the file
            ImportError: If langdetect is not installed (unless suppress_warnings=True)

        Example:
            >>> from pathlib import Path
            >>> syllables, stats, lang = SyllableExtractor.extract_file_with_auto_language(
            ...     Path('document.txt'),
            ...     min_syllable_length=2,
            ...     max_syllable_length=8
            ... )
            >>> print(f"Detected: {lang}, Found: {len(syllables)} syllables")
            Detected: de_DE, Found: 1500 syllables
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            raise IOError(f"Error reading file {input_path}: {e}")

        return SyllableExtractor.extract_with_auto_language(
            text=text,
            min_syllable_length=min_syllable_length,
            max_syllable_length=max_syllable_length,
            only_hyphenated=only_hyphenated,
            default_language=default_language,
            min_detection_length=min_detection_length,
            suppress_warnings=suppress_warnings,
        )
