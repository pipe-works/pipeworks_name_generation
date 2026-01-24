"""
Frequency analysis for canonical syllables.

This module handles Step 3 of the normalization pipeline: analyzing frequency
distribution of canonical syllables and generating frequency intelligence
data structures. This captures "how often each canonical syllable occurs
before we collapse identity" - essential for understanding natural language
patterns in the source corpus.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import cast

from .models import FrequencyEntry


class FrequencyAnalyzer:
    """
    Analyzes frequency distribution of canonical syllables.

    This class handles the intelligence capture phase of the normalization
    pipeline. It counts occurrences of each canonical syllable, creates
    frequency rankings, and generates output files for downstream analysis
    and feature annotation.

    Example:
        >>> from pathlib import Path
        >>> analyzer = FrequencyAnalyzer()
        >>> syllables = ['ka', 'ra', 'mi', 'ka', 'ta', 'ka']
        >>> frequencies = analyzer.calculate_frequencies(syllables)
        >>> frequencies
        {'ka': 3, 'ra': 1, 'mi': 1, 'ta': 1}
        >>> analyzer.save_frequencies(frequencies, Path("syllables_frequencies.json"))
        >>> unique = analyzer.extract_unique_syllables(syllables)
        >>> unique
        ['ka', 'mi', 'ra', 'ta']
    """

    def calculate_frequencies(self, syllables: list[str]) -> dict[str, int]:
        """
        Calculate frequency counts for canonical syllables.

        Counts how many times each unique syllable appears in the input list.
        This captures the natural frequency distribution from the source corpus
        before deduplication.

        Args:
            syllables: List of canonical syllables (may contain duplicates).

        Returns:
            Dictionary mapping each unique syllable to its occurrence count.

        Example:
            >>> analyzer = FrequencyAnalyzer()
            >>> syllables = ['ka', 'ra', 'mi', 'ka', 'ta', 'ka', 'ra']
            >>> frequencies = analyzer.calculate_frequencies(syllables)
            >>> frequencies
            {'ka': 3, 'ra': 2, 'mi': 1, 'ta': 1}
            >>> sum(frequencies.values())  # Total syllable count
            7

        Note:
            The returned dictionary is not sorted. Use create_frequency_entries()
            to generate sorted frequency rankings.
        """
        return dict(Counter(syllables))

    def create_frequency_entries(self, frequencies: dict[str, int]) -> list[FrequencyEntry]:
        """
        Create ranked frequency entries from frequency counts.

        Converts a frequency dictionary into a list of FrequencyEntry objects
        with ranking information and percentage calculations. Entries are
        sorted by frequency (descending) then alphabetically (ascending).

        Args:
            frequencies: Dictionary mapping syllable to occurrence count.

        Returns:
            List of FrequencyEntry objects sorted by frequency (highest first),
            with alphabetical secondary sort for ties.

        Example:
            >>> analyzer = FrequencyAnalyzer()
            >>> frequencies = {'ka': 187, 'ra': 162, 'mi': 145, 'ta': 98}
            >>> entries = analyzer.create_frequency_entries(frequencies)
            >>> entries[0]
            FrequencyEntry(canonical='ka', frequency=187, rank=1, percentage=31.5)
            >>> entries[0].canonical
            'ka'
            >>> entries[0].rank
            1

        Note:
            Percentage is calculated as (frequency / total_count) * 100.
            Ranks start at 1 (most frequent syllable has rank=1).
        """
        total_count = sum(frequencies.values())
        if total_count == 0:
            return []

        # Sort by frequency (descending), then alphabetically (ascending)
        sorted_items = sorted(frequencies.items(), key=lambda x: (-x[1], x[0]))

        entries: list[FrequencyEntry] = []
        for rank, (syllable, count) in enumerate(sorted_items, start=1):
            percentage = (count / total_count) * 100
            entry = FrequencyEntry(
                canonical=syllable, frequency=count, rank=rank, percentage=percentage
            )
            entries.append(entry)

        return entries

    def extract_unique_syllables(self, syllables: list[str]) -> list[str]:
        """
        Extract unique syllables and return in sorted order.

        Removes duplicates from the syllable list and returns a sorted list
        of unique canonical syllables. This creates the authoritative syllable
        inventory for downstream feature annotation.

        Args:
            syllables: List of canonical syllables (may contain duplicates).

        Returns:
            Sorted list of unique syllable strings (alphabetical order).

        Example:
            >>> analyzer = FrequencyAnalyzer()
            >>> syllables = ['ka', 'ra', 'mi', 'ka', 'ta', 'ka', 'ra']
            >>> unique = analyzer.extract_unique_syllables(syllables)
            >>> unique
            ['ka', 'mi', 'ra', 'ta']
            >>> len(unique)
            4

        Note:
            Sorting is alphabetical (a-z) for deterministic output.
            Empty syllable lists return an empty list.
        """
        return sorted(set(syllables))

    def save_frequencies(self, frequencies: dict[str, int], output_path: Path) -> None:
        """
        Save frequency dictionary to JSON file.

        Writes the frequency intelligence to a JSON file for downstream
        analysis. The output is formatted with indentation for readability
        and sorted by key for deterministic output.

        Args:
            frequencies: Dictionary mapping syllable to occurrence count.
            output_path: Path where the JSON file should be saved.

        Raises:
            PermissionError: If the output file cannot be written.
            OSError: If there are filesystem issues (disk full, etc.).

        Example:
            >>> analyzer = FrequencyAnalyzer()
            >>> frequencies = {'ka': 187, 'ra': 162, 'mi': 145}
            >>> analyzer.save_frequencies(frequencies, Path("syllables_frequencies.json"))
            # File contains:
            # {
            #   "ka": 187,
            #   "mi": 145,
            #   "ra": 162
            # }

        Note:
            The JSON is formatted with 2-space indentation and keys are
            sorted alphabetically for consistent diffs in version control.
        """
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON with sorted keys and pretty formatting
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(frequencies, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")  # Trailing newline for POSIX compliance

    def save_unique_syllables(self, unique_syllables: list[str], output_path: Path) -> None:
        """
        Save unique syllables to text file.

        Writes the deduplicated canonical syllable inventory to a text file,
        one syllable per line. This creates the authoritative syllable list
        for feature annotation and downstream processing.

        Args:
            unique_syllables: Sorted list of unique canonical syllables.
            output_path: Path where the text file should be saved.

        Raises:
            PermissionError: If the output file cannot be written.
            OSError: If there are filesystem issues (disk full, etc.).

        Example:
            >>> analyzer = FrequencyAnalyzer()
            >>> unique = ['ka', 'mi', 'ra', 'ta']
            >>> analyzer.save_unique_syllables(unique, Path("syllables_unique.txt"))
            # File contains:
            # ka
            # mi
            # ra
            # ta

        Note:
            Syllables should be pre-sorted (alphabetically) before calling
            this method. Use extract_unique_syllables() which returns
            sorted output, or sort manually.
        """
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write syllables one per line
        with output_path.open("w", encoding="utf-8") as f:
            for syllable in unique_syllables:
                f.write(f"{syllable}\n")


def load_frequencies_from_file(file_path: Path) -> dict[str, int]:
    """
    Load frequency dictionary from JSON file.

    Reads a previously saved syllables_frequencies.json file and returns
    the frequency dictionary. Useful for analysis and inspection of
    normalization results.

    Args:
        file_path: Path to the JSON frequency file.

    Returns:
        Dictionary mapping syllable to occurrence count.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        PermissionError: If the file cannot be read.

    Example:
        >>> from pathlib import Path
        >>> frequencies = load_frequencies_from_file(Path("syllables_frequencies.json"))
        >>> frequencies['ka']
        187
        >>> len(frequencies)
        412

    Note:
        The JSON file must have been created by save_frequencies() or
        follow the same format: {"syllable": count, ...}
    """
    with file_path.open("r", encoding="utf-8") as f:
        return cast(dict[str, int], json.load(f))


def load_unique_syllables_from_file(file_path: Path) -> list[str]:
    """
    Load unique syllables from text file.

    Reads a previously saved syllables_unique.txt file and returns the
    syllable list. Useful for loading the authoritative syllable inventory
    for feature annotation or analysis.

    Args:
        file_path: Path to the text file containing unique syllables.

    Returns:
        List of syllable strings (one per line from file).

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be read.
        UnicodeDecodeError: If the file contains invalid UTF-8.

    Example:
        >>> from pathlib import Path
        >>> syllables = load_unique_syllables_from_file(Path("syllables_unique.txt"))
        >>> syllables[:5]
        ['ka', 'mi', 'ra', 'ta', 'wa']
        >>> len(syllables)
        412

    Note:
        Empty lines are skipped. Leading/trailing whitespace is stripped
        from each line.
    """
    syllables: list[str] = []
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            syllable = line.strip()
            if syllable:
                syllables.append(syllable)
    return syllables
