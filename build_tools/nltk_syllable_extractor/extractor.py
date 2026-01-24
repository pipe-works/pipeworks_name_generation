"""
Core CMUDict-based syllable extraction functionality.

This module provides the NltkSyllableExtractor class for extracting syllables
from text using CMU Pronouncing Dictionary with phonetically-guided
orthographic syllabification based on onset/coda principles.
"""

from __future__ import annotations

import re
from pathlib import Path

# Optional dependency - only needed at runtime, not for documentation builds
try:
    import cmudict

    CMUDICT_AVAILABLE = True
except ImportError:
    cmudict = None  # type: ignore[assignment]
    CMUDICT_AVAILABLE = False


class NltkSyllableExtractor:
    """
    Extracts syllables from text using CMU Pronouncing Dictionary.

    This class uses phonetic information from CMUDict to guide orthographic
    syllable splitting, respecting English phonotactic constraints via
    onset/coda principles.

    The extractor works by:
    1. Reading text input (string or file)
    2. Tokenizing into words using regex
    3. Looking up phonetic transcriptions in CMUDict
    4. Using vowel phonemes to identify syllable boundaries
    5. Mapping phonetic structure back to orthographic positions
    6. Applying onset/coda rules to split consonant clusters
    7. Filtering syllables by length constraints
    8. Returning unique syllables (case-insensitive)

    Key Differences from pyphen:
        - Uses phonetic information (CMUDict) rather than typographic rules
        - Respects consonant cluster constraints (onset/coda principles)
        - Produces more "natural" phonetic splits
        - English only (CMUDict limitation)
        - Includes fallback for out-of-vocabulary words

    Typical Usage:
        >>> # Basic extraction
        >>> extractor = NltkSyllableExtractor('en_US', min_syllable_length=2, max_syllable_length=8)
        >>> syllables = extractor.extract_syllables_from_text("Hello wonderful world")
        >>> print(sorted(syllables))
        ['der', 'ful', 'hel', 'lo', 'won', 'world']

        >>> # Extract from file and save
        >>> syllables = extractor.extract_syllables_from_file(Path('input.txt'))
        >>> extractor.save_syllables(syllables, Path('output.txt'))

    Attributes:
        language_code: The language code (always 'en_US' for NLTK extractor)
        min_syllable_length: Minimum syllable length to include in results
        max_syllable_length: Maximum syllable length to include in results
        cmu_dict: The loaded CMU Pronouncing Dictionary

    Note:
        This is a build-time tool. The nltk dependency should not be used
        at runtime in the core name generation system.
    """

    # Valid English onset clusters (for onset/coda split decisions)
    VALID_ONSETS = {
        "bl",
        "br",
        "cl",
        "cr",
        "dr",
        "fl",
        "fr",
        "gl",
        "gr",
        "pl",
        "pr",
        "sl",
        "sm",
        "sn",
        "sp",
        "st",
        "sw",
        "tr",
        "tw",
        "thr",
        "scr",
        "shr",
        "spl",
        "spr",
        "str",
        "squ",
        "ch",
        "sh",
        "th",
        "wh",
        "ph",
        "gh",
    }

    VOWELS = "aeiouy"

    def __init__(
        self, language_code: str, min_syllable_length: int = 1, max_syllable_length: int = 999
    ):
        """
        Initialize the NLTK syllable extractor.

        Args:
            language_code: Language code (must be 'en_US' for NLTK extractor)
            min_syllable_length: Minimum syllable length to include (default: 1, no filtering)
            max_syllable_length: Maximum syllable length to include (default: 999, no filtering)

        Raises:
            ImportError: If cmudict is not installed
            ValueError: If the language code is not 'en_US'
        """
        if not CMUDICT_AVAILABLE:
            raise ImportError(
                "cmudict is not installed. This is a build-time dependency.\n"
                "Install it with: pip install cmudict"
            )

        if language_code != "en_US":
            raise ValueError(
                f"Language code '{language_code}' is not supported by nltk_syllable_extractor.\n"
                "Only 'en_US' is supported (CMUDict limitation)."
            )

        self.language_code = language_code
        self.min_syllable_length = min_syllable_length
        self.max_syllable_length = max_syllable_length
        self.cmu_dict = cmudict.dict()

    def extract_syllables_from_text(
        self, text: str, only_hyphenated: bool = True
    ) -> tuple[list[str], dict[str, int]]:
        """
        Extract all syllables from a block of text (preserves duplicates).

        This method processes input text by tokenizing it into words, applying
        CMUDict phonetic lookup and onset/coda principles to extract individual
        syllables that meet the configured length constraints.

        Args:
            text: Input text to process. Can contain any characters, but only
                  alphabetic sequences will be processed as words.
            only_hyphenated: If True, only include syllables from words that were
                           successfully split (CMUDict lookup succeeded). Set to False
                           to include fallback syllabification for unknown words.

        Returns:
            Tuple of (syllables, statistics) where:
                - syllables: List of all lowercase syllable strings (includes duplicates)
                - statistics: Dict with the following keys:
                    - 'total_words': Total number of words found in source text
                    - 'processed_words': Words that were successfully processed
                    - 'fallback_count': Words not in CMUDict (used fallback heuristics)
                    - 'rejected_syllables': Syllables rejected due to length constraints

        Note:
            - Only processes words containing alphabetic characters (a-z, A-Z)
            - Case-insensitive processing (all output is lowercase)
            - Automatically removes punctuation and special characters
            - Filters syllables by configured min/max length constraints
            - When only_hyphenated=True, excludes words not in CMUDict
            - Deterministic: same input always produces same output
            - Uses first pronunciation when multiple exist (deterministic)
            - Words are extracted using regex pattern: \\b[a-zA-Z]+\\b

        Example:
            >>> extractor = NltkSyllableExtractor('en_US', min_syllable_length=2, max_syllable_length=8)
            >>> syllables, stats = extractor.extract_syllables_from_text("Hello world!")
            >>> print(syllables)
            ['hel', 'lo', 'world']
            >>> print(stats['total_words'])
            2
        """
        # Extract words using regex (alphanumeric sequences)
        words = re.findall(r"\b[a-zA-Z]+\b", text)

        syllables: list[str] = []
        stats = {
            "total_words": len(words),
            "fallback_count": 0,
            "rejected_syllables": 0,
            "processed_words": 0,
        }

        for word in words:
            # Convert to lowercase for CMUDict lookup
            word_lower = word.lower()

            # Extract syllables from word
            word_syllables = self._extract_orthographic_syllables(word_lower)

            # Track if CMUDict lookup failed (word not in dictionary)
            if word_lower not in self.cmu_dict:
                stats["fallback_count"] += 1

            # If CMUDict lookup failed and only_hyphenated is True, skip
            if not word_syllables and only_hyphenated:
                continue

            # If we got syllables (either from CMUDict or fallback)
            if word_syllables:
                stats["processed_words"] += 1

                # Filter syllables by length and add to list (preserves duplicates)
                for syllable in word_syllables:
                    if self.min_syllable_length <= len(syllable) <= self.max_syllable_length:
                        syllables.append(syllable)
                    else:
                        stats["rejected_syllables"] += 1

        return syllables, stats

    def _extract_orthographic_syllables(self, word: str) -> list[str]:
        """
        Extract orthographic syllables from a word using CMUDict.

        Uses vowel positions and phonetic syllable structure to determine
        boundaries, then maps back to spelling.

        Args:
            word: Lowercase word to syllabify

        Returns:
            List of orthographic syllables, empty list if word cannot be processed
        """
        # Normalize word: remove non-alphabetic characters
        word_clean = re.sub(r"[^a-z]", "", word.lower())

        if not word_clean:
            return []

        if len(word_clean) == 1:
            return [word_clean]

        # Get pronunciation from CMU Dictionary
        if word_clean not in self.cmu_dict:
            # Fallback: simple vowel-based splitting
            return self._fallback_split(word_clean)

        # Use first pronunciation (deterministic)
        pronunciation = self.cmu_dict[word_clean][0]

        # Extract phonetic syllables
        phonetic_syllables = self._extract_phonetic_syllables(pronunciation)

        if len(phonetic_syllables) <= 1:
            return [word_clean]

        # Map phonetic syllables to orthographic positions
        return self._map_to_orthographic(word_clean, phonetic_syllables)

    def _extract_phonetic_syllables(self, phonemes: list[str]) -> list[list[str]]:
        """
        Extract phonetic syllables from phoneme list.

        Each syllable ends with a vowel phoneme (marked with stress digit).

        Args:
            phonemes: List of phoneme strings from CMUDict

        Returns:
            List of syllables, where each syllable is a list of phonemes
        """
        syllables = []
        current_syllable = []

        for phoneme in phonemes:
            current_syllable.append(phoneme)
            # Vowel phonemes end with stress digits (0, 1, or 2)
            if phoneme[-1].isdigit():
                syllables.append(current_syllable)
                current_syllable = []

        # Add any remaining consonants to last syllable
        if current_syllable:
            syllables.append(current_syllable)

        return syllables

    def _map_to_orthographic(self, word: str, phonetic_syllables: list[list[str]]) -> list[str]:
        """
        Map phonetic syllables to orthographic character positions.

        Strategy:
        1. Find orthographic vowel positions
        2. For each pair of vowel positions, determine split point using:
           - Consonants between vowels
           - Onset/coda principles
           - Phonetic syllable structure for guidance

        Args:
            word: The word to split
            phonetic_syllables: List of phonetic syllables from CMUDict

        Returns:
            List of orthographic syllables
        """
        # Find orthographic vowel positions
        vowel_positions = [i for i, c in enumerate(word) if c in self.VOWELS]

        # Count vowel phonemes (should equal number of vowel positions)
        vowel_phoneme_count = sum(1 for syl in phonetic_syllables for p in syl if p[-1].isdigit())

        # If counts don't match, fall back
        if len(vowel_positions) < vowel_phoneme_count:
            return self._fallback_split(word)

        # Build split points between consecutive vowel positions
        split_points = []

        for i in range(len(vowel_positions) - 1):
            current_vowel_pos = vowel_positions[i]
            next_vowel_pos = vowel_positions[i + 1]

            # Find end of current vowel group (consecutive vowels)
            vowel_end = current_vowel_pos
            while vowel_end + 1 < len(word) and word[vowel_end + 1] in self.VOWELS:
                vowel_end += 1

            # Get consonants between current and next vowel
            consonants_between = word[vowel_end + 1 : next_vowel_pos]
            num_consonants = len(consonants_between)

            if num_consonants == 0:
                # Adjacent vowels - split between them
                split_point = vowel_end + 1
            elif num_consonants == 1:
                # Single consonant: keep with next vowel (onset principle)
                split_point = vowel_end + 1
            else:
                # Multiple consonants: use onset/coda principles
                # Try to find a valid onset cluster at the end
                split_point = vowel_end + 1  # Default: split after first consonant

                # Check for valid onset clusters (try 3, 2, then 1 consonant)
                for cluster_len in range(min(3, num_consonants), 0, -1):
                    potential_onset = consonants_between[-cluster_len:]
                    if self._is_valid_onset(potential_onset):
                        split_point = vowel_end + 1 + (num_consonants - cluster_len)
                        break

            if 0 < split_point < len(word):
                split_points.append(split_point)

        return self._build_syllables(word, split_points)

    def _fallback_split(self, word: str) -> list[str]:
        """
        Fallback syllable splitting using vowel groups and onset/coda rules.

        This is used when CMUDict lookup fails.

        Args:
            word: The word to split

        Returns:
            List of syllables using heuristic rules
        """
        # Find vowel groups
        vowel_groups = []
        i = 0
        while i < len(word):
            if word[i] in self.VOWELS:
                start = i
                while i < len(word) and word[i] in self.VOWELS:
                    i += 1
                vowel_groups.append((start, i))
            else:
                i += 1

        if len(vowel_groups) <= 1:
            return [word]

        split_points = []

        for i in range(len(vowel_groups) - 1):
            current_vowel_end = vowel_groups[i][1]
            next_vowel_start = vowel_groups[i + 1][0]

            consonants_between = word[current_vowel_end:next_vowel_start]
            num_consonants = len(consonants_between)

            if num_consonants == 0:
                split_points.append(current_vowel_end)
            elif num_consonants == 1:
                split_points.append(current_vowel_end)
            else:
                split_pos = current_vowel_end + 1

                for cluster_len in range(min(3, num_consonants), 0, -1):
                    potential_onset = consonants_between[-cluster_len:]
                    if self._is_valid_onset(potential_onset):
                        split_pos = current_vowel_end + num_consonants - cluster_len
                        break

                split_points.append(split_pos)

        return self._build_syllables(word, split_points)

    def _is_valid_onset(self, consonant_cluster: str) -> bool:
        """
        Check if a consonant cluster is a valid English onset.

        Args:
            consonant_cluster: String of consonants to check

        Returns:
            True if valid onset cluster, False otherwise
        """
        return consonant_cluster.lower() in self.VALID_ONSETS

    def _build_syllables(self, word: str, split_points: list[int]) -> list[str]:
        """
        Build syllables from split points.

        Args:
            word: The word to split
            split_points: List of character positions where splits occur

        Returns:
            List of syllable strings
        """
        if not split_points:
            return [word]

        syllables = []
        start = 0

        # Sort and deduplicate split points
        split_points = sorted(set(split_points))

        for split_point in split_points:
            if 0 < split_point < len(word):
                syllables.append(word[start:split_point])
                start = split_point

        # Add final syllable
        if start < len(word):
            syllables.append(word[start:])

        return [s for s in syllables if s]

    def extract_syllables_from_file(self, input_path: Path) -> tuple[list[str], dict[str, int]]:
        """
        Extract all syllables from a text file (preserves duplicates).

        This is a convenience wrapper around extract_syllables_from_text() that
        handles file reading with proper encoding (UTF-8) and error handling.

        Args:
            input_path: Path to the input text file. File should be UTF-8 encoded
                       plain text. Binary files or non-text formats will cause errors.

        Returns:
            Tuple of (syllables, statistics) where:
                - syllables: List of all lowercase syllable strings (includes duplicates)
                - statistics: Dict with processing statistics (see extract_syllables_from_text)

        Raises:
            FileNotFoundError: If the input file doesn't exist at the specified path
            IOError: If there's an error reading the file (permissions, encoding, etc.)

        Example:
            >>> from pathlib import Path
            >>> extractor = NltkSyllableExtractor('en_US', min_syllable_length=2, max_syllable_length=8)
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

    def save_syllables(self, syllables: list[str], output_path: Path) -> None:
        """
        Save syllables to a text file (one syllable per line, preserves all).

        Writes syllables with UTF-8 encoding, one syllable per line. Syllables
        are written in the order they appear in the list (preserving duplicates).
        This format is ideal for downstream processing by normalizer tools.

        Args:
            syllables: List of syllables to save (may contain duplicates).
                      Written in the order provided.
            output_path: Path to the output file. Parent directories must exist.
                        If the file exists, it will be overwritten.

        Raises:
            IOError: If there's an error writing the file (permissions, disk space, etc.)

        Example:
            >>> from pathlib import Path
            >>> extractor = NltkSyllableExtractor('en_US')
            >>> syllables = ['hel', 'lo', 'world', 'hel']  # Note: 'hel' appears twice
            >>> extractor.save_syllables(syllables, Path('output.txt'))
            # Creates file with content (preserving duplicates and order):
            # hel
            # lo
            # world
            # hel

        Note:
            The output file uses UTF-8 encoding with Unix-style line endings (\\n).
            Each line contains exactly one syllable with no leading/trailing whitespace.
            Duplicates are preserved. Use downstream tools for deduplication if needed.
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                for syllable in syllables:
                    f.write(f"{syllable}\n")
        except Exception as e:
            raise IOError(f"Error writing file {output_path}: {e}")
