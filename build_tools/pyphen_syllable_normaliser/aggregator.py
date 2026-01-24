"""
File aggregation for syllable normalization pipeline.

This module handles Step 1 of the normalization pipeline: combining multiple
input files into a single raw syllable file while preserving all occurrences
and maintaining raw counts.
"""

from __future__ import annotations

from pathlib import Path


class FileAggregator:
    """
    Aggregates syllables from multiple input files.

    This class handles the first step of the normalization pipeline: combining
    syllables from multiple .txt files into a single raw aggregated file. All
    occurrences are preserved (no deduplication), maintaining the original
    frequency distribution from the input files.

    Example:
        >>> from pathlib import Path
        >>> aggregator = FileAggregator()
        >>> input_files = [Path("file1.txt"), Path("file2.txt")]
        >>> syllables = aggregator.aggregate_files(input_files)
        >>> len(syllables)  # Total from both files
        450
        >>> aggregator.save_raw_syllables(syllables, Path("syllables_raw.txt"))
    """

    def aggregate_files(self, input_files: list[Path]) -> list[str]:
        """
        Aggregate syllables from multiple input files.

        Reads all syllables from the provided input files and combines them
        into a single list. Each line in each input file is treated as one
        syllable. Empty lines are skipped. All occurrences are preserved
        (no deduplication).

        Args:
            input_files: List of Path objects pointing to input .txt files.
                Each file should contain one syllable per line.

        Returns:
            List of all syllables from all input files, preserving duplicates
            and maintaining the original order (file by file).

        Raises:
            FileNotFoundError: If any input file does not exist.
            PermissionError: If any input file cannot be read.
            UnicodeDecodeError: If any input file contains invalid UTF-8.

        Example:
            >>> aggregator = FileAggregator()
            >>> files = [Path("corpus1.txt"), Path("corpus2.txt")]
            >>> syllables = aggregator.aggregate_files(files)
            >>> syllables[:3]
            ['hello', 'world', 'test']

        Note:
            Files are processed in the order provided. If deterministic
            ordering is required, ensure input_files is sorted before calling.
        """
        all_syllables: list[str] = []

        for file_path in input_files:
            syllables = self.read_syllables_from_file(file_path)
            all_syllables.extend(syllables)

        return all_syllables

    def read_syllables_from_file(self, file_path: Path) -> list[str]:
        """
        Read syllables from a single file.

        Reads a file line by line, treating each line as one syllable.
        Empty lines (whitespace only) are skipped. No normalization or
        transformation is applied - syllables are preserved exactly as
        they appear in the file.

        Args:
            file_path: Path to the input file to read.

        Returns:
            List of syllable strings from the file, one per non-empty line.

        Raises:
            FileNotFoundError: If the file does not exist.
            PermissionError: If the file cannot be read.
            UnicodeDecodeError: If the file contains invalid UTF-8.

        Example:
            >>> aggregator = FileAggregator()
            >>> syllables = aggregator.read_syllables_from_file(Path("input.txt"))
            >>> syllables
            ['ka', 'ra', 'mi', 'ka', 'ta']

        Note:
            Leading and trailing whitespace is stripped from each line,
            but the syllable content itself is not modified. This allows
            files with varying whitespace formatting to be processed
            consistently.
        """
        syllables: list[str] = []

        with file_path.open("r", encoding="utf-8") as f:
            for line in f:
                # Strip whitespace and skip empty lines
                syllable = line.strip()
                if syllable:
                    syllables.append(syllable)

        return syllables

    def save_raw_syllables(self, syllables: list[str], output_path: Path) -> None:
        """
        Save raw aggregated syllables to file.

        Writes syllables to the output file, one per line, in the order
        provided. This creates the syllables_raw.txt file for the pipeline.
        All syllables are written exactly as provided (no normalization).

        Args:
            syllables: List of syllable strings to write.
            output_path: Path where the raw syllables file should be saved.

        Raises:
            PermissionError: If the output file cannot be written.
            OSError: If there are filesystem issues (disk full, etc.).

        Example:
            >>> aggregator = FileAggregator()
            >>> syllables = ['ka', 'ra', 'mi', 'ka', 'ta']
            >>> aggregator.save_raw_syllables(syllables, Path("syllables_raw.txt"))
            # File contains:
            # ka
            # ra
            # mi
            # ka
            # ta

        Note:
            This method creates the output file if it doesn't exist and
            overwrites it if it does. The output directory must already exist.
        """
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write syllables one per line
        with output_path.open("w", encoding="utf-8") as f:
            for syllable in syllables:
                f.write(f"{syllable}\n")


def discover_input_files(
    source_dir: Path, pattern: str = "*.txt", recursive: bool = False
) -> list[Path]:
    """
    Discover input files in a directory matching a pattern.

    Scans a directory for files matching the specified glob pattern.
    Returns files in sorted order for deterministic processing.

    Args:
        source_dir: Directory to scan for input files.
        pattern: Glob pattern for matching files. Default: "*.txt".
        recursive: If True, scan subdirectories recursively using "**/" prefix.
            Default: False (only scan the immediate directory).

    Returns:
        Sorted list of Path objects for all matching files.

    Raises:
        ValueError: If source_dir is not a directory.
        FileNotFoundError: If source_dir does not exist.

    Example:
        >>> from pathlib import Path
        >>> # Non-recursive scan
        >>> files = discover_input_files(Path("data/"), pattern="*.txt")
        >>> files
        [Path('data/corpus1.txt'), Path('data/corpus2.txt')]
        >>>
        >>> # Recursive scan
        >>> files = discover_input_files(
        ...     Path("data/"),
        ...     pattern="*.txt",
        ...     recursive=True
        ... )
        >>> files
        [Path('data/corpus1.txt'),
         Path('data/subdir/corpus3.txt'),
         Path('data/subdir/corpus4.txt')]

    Note:
        Files are always returned in sorted order to ensure deterministic
        processing. This is critical for reproducible normalization results.
    """
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")

    if not source_dir.is_dir():
        raise ValueError(f"Source path is not a directory: {source_dir}")

    # Use glob or rglob depending on recursive flag
    if recursive:
        # Recursive: scan all subdirectories
        files = list(source_dir.rglob(pattern))
    else:
        # Non-recursive: scan only immediate directory
        files = list(source_dir.glob(pattern))

    # Filter to only files (exclude directories)
    files = [f for f in files if f.is_file()]

    # Sort for deterministic order
    return sorted(files)
