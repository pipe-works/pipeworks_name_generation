"""Data I/O operations for analysis tools.

This module provides centralized data loading and saving functions for all
analysis tools, eliminating code duplication and ensuring consistent error
handling and validation.

Key Features
------------
- Load annotated syllables with optional validation
- Load frequency data from normalizer output
- Save JSON data with consistent formatting
- Unified error handling across all analysis tools
- Support for Unicode content (ensure_ascii=False by default)

Usage
-----
Loading annotated syllables::

    from build_tools.syllable_analysis.common import load_annotated_syllables
    from pathlib import Path

    records = load_annotated_syllables(Path("data/annotated/syllables_annotated.json"))

Loading frequency data::

    from build_tools.syllable_analysis.common import load_frequency_data

    frequencies = load_frequency_data(Path("data/normalized/syllables_frequencies.json"))

Saving JSON output::

    from build_tools.syllable_analysis.common import save_json_output

    data = {"results": [...]}
    save_json_output(data, Path("output.json"))

Module Contents
---------------
- load_annotated_syllables(): Load syllables_annotated.json with validation
- load_frequency_data(): Load syllables_frequencies.json
- save_json_output(): Save data as formatted JSON
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast


def load_annotated_syllables(input_path: Path, validate: bool = True) -> list[dict[str, Any]]:
    """Load annotated syllables from JSON file with optional validation.

    This function loads the output of the syllable feature annotator, which contains
    syllables with their frequencies and phonetic feature annotations. It provides
    optional validation to ensure the data structure is correct.

    Parameters
    ----------
    input_path : Path
        Path to syllables_annotated.json file
    validate : bool, default=True
        Whether to validate the structure of loaded data. When True, checks:
        - Data is a list
        - List is non-empty
        - First record has required keys: 'syllable', 'frequency', 'features'

    Returns
    -------
    list[dict[str, Any]]
        List of syllable records, each containing:
        - syllable (str): The syllable text
        - frequency (int): Occurrence count in corpus
        - features (dict): Boolean feature flags (12 features)

    Raises
    ------
    FileNotFoundError
        If input file does not exist
    json.JSONDecodeError
        If file is not valid JSON
    ValueError
        If validation is enabled and data structure is invalid

    Examples
    --------
    Basic loading with validation::

        >>> from pathlib import Path
        >>> records = load_annotated_syllables(Path("data/annotated/syllables_annotated.json"))
        >>> len(records)
        1247
        >>> records[0].keys()
        dict_keys(['syllable', 'frequency', 'features'])

    Loading without validation (faster, use when structure is guaranteed)::

        >>> records = load_annotated_syllables(Path("data/annotated/syllables_annotated.json"),
        ...                                     validate=False)

    Error handling::

        >>> try:
        ...     records = load_annotated_syllables(Path("nonexistent.json"))
        ... except FileNotFoundError as e:
        ...     print(f"File not found: {e}")

    Notes
    -----
    Expected file format (syllables_annotated.json)::

        [
            {
                "syllable": "ka",
                "frequency": 187,
                "features": {
                    "contains_liquid": false,
                    "contains_plosive": true,
                    "contains_fricative": false,
                    "contains_nasal": false,
                    "long_vowel": false,
                    "short_vowel": true,
                    "starts_with_vowel": false,
                    "starts_with_cluster": false,
                    "starts_with_heavy_cluster": false,
                    "ends_with_vowel": true,
                    "ends_with_stop": false,
                    "ends_with_nasal": false
                }
            },
            ...
        ]

    This file is produced by the syllable feature annotator pipeline and is the
    primary input for analysis tools.

    Performance
    -----------
    Loading a typical corpus of 1,000-10,000 syllables takes <100ms.
    Validation adds negligible overhead (~1ms).
    """
    # Check file exists before attempting to open
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Load JSON data
    with input_path.open(encoding="utf-8") as f:
        records = json.load(f)

    # Validate structure if requested
    if validate:
        # Check it's a list
        if not isinstance(records, list):
            raise ValueError(
                f"Expected list of records, got {type(records).__name__}. "
                f"File may not be in syllables_annotated.json format."
            )

        # Check list is not empty
        if not records:
            raise ValueError(
                "Input file contains no records. "
                "Ensure the file contains an array of syllable objects."
            )

        # Check first record has expected structure
        required_keys = {"syllable", "frequency", "features"}
        actual_keys = set(records[0].keys())

        if not required_keys.issubset(actual_keys):
            missing_keys = required_keys - actual_keys
            raise ValueError(
                f"Records missing required keys: {', '.join(missing_keys)}. "
                f"Expected format: {{'syllable': str, 'frequency': int, 'features': dict}}. "
                f"Found keys: {', '.join(actual_keys)}"
            )

    return cast(list[dict[str, Any]], records)


def load_frequency_data(frequencies_path: Path) -> dict[str, int]:
    """Load frequency mapping from JSON file.

    This function loads the output of the syllable normalizer's frequency analysis,
    which maps each canonical syllable to its occurrence count in the raw corpus.

    Parameters
    ----------
    frequencies_path : Path
        Path to syllables_frequencies.json file

    Returns
    -------
    dict[str, int]
        Dictionary mapping syllable strings to their frequency counts

    Raises
    ------
    FileNotFoundError
        If input file does not exist
    json.JSONDecodeError
        If file is not valid JSON
    ValueError
        If data structure is invalid (not a dict)

    Examples
    --------
    Basic loading::

        >>> from pathlib import Path
        >>> frequencies = load_frequency_data(Path("data/normalized/syllables_frequencies.json"))
        >>> frequencies["ka"]
        187
        >>> len(frequencies)
        1247

    Checking most common syllables::

        >>> sorted_freqs = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)
        >>> sorted_freqs[:3]
        [('ka', 187), ('ra', 162), ('mi', 145)]

    Error handling::

        >>> try:
        ...     frequencies = load_frequency_data(Path("nonexistent.json"))
        ... except FileNotFoundError:
        ...     print("File not found")

    Notes
    -----
    Expected file format (syllables_frequencies.json)::

        {
            "ka": 187,
            "ra": 162,
            "mi": 145,
            "ta": 98,
            ...
        }

    This file is produced by the syllable normalizer's frequency analysis step
    and captures pre-deduplication counts (how many times each syllable appeared
    in the raw corpus before creating the unique syllable list).

    The frequencies can be used for:
    - Weighted analysis (prioritize common syllables)
    - Filtering (exclude rare syllables)
    - Visualization (size/color by frequency)
    - Statistical analysis

    Performance
    -----------
    Loading a typical frequency file (1,000-10,000 entries) takes <50ms.
    """
    # Check file exists
    if not frequencies_path.exists():
        raise FileNotFoundError(f"Frequency file not found: {frequencies_path}")

    # Load JSON data
    with frequencies_path.open(encoding="utf-8") as f:
        frequencies = json.load(f)

    # Validate it's a dictionary
    if not isinstance(frequencies, dict):
        raise ValueError(
            f"Expected dictionary mapping syllables to frequencies, got {type(frequencies).__name__}. "
            f"File may not be in syllables_frequencies.json format."
        )

    return frequencies


def save_json_output(
    data: Any, output_path: Path, indent: int | None = 2, ensure_ascii: bool = False
) -> None:
    """Save data as formatted JSON file.

    This function provides consistent JSON output formatting across all analysis tools.
    It ensures proper Unicode handling, readable indentation, and creates parent
    directories if needed.

    Parameters
    ----------
    data : Any
        Data to serialize as JSON (must be JSON-serializable)
    output_path : Path
        Output file path (parent directories will be created if needed)
    indent : int | None, default=2
        Number of spaces for JSON indentation. Use 2 for readability,
        None for compact output
    ensure_ascii : bool, default=False
        If True, escape non-ASCII characters. If False (default), preserve
        Unicode characters for better readability

    Raises
    ------
    TypeError
        If data is not JSON-serializable
    OSError
        If file cannot be written (permissions, disk full, etc.)

    Examples
    --------
    Save analysis results::

        >>> from pathlib import Path
        >>> results = {"total": 1247, "unique": 892}
        >>> save_json_output(results, Path("output/results.json"))

    Save with compact formatting::

        >>> save_json_output(results, Path("output/compact.json"), indent=None)

    Save with ASCII-only encoding::

        >>> save_json_output(results, Path("output/ascii.json"), ensure_ascii=True)

    Auto-create parent directories::

        >>> save_json_output(results, Path("output/new/dir/results.json"))
        >>> # Creates output/new/dir/ automatically

    Notes
    -----
    Default settings (indent=2, ensure_ascii=False) are optimized for:
    - Human readability (indented)
    - Unicode support (preserve accented characters, emojis, etc.)
    - Version control friendliness (consistent line breaks)

    File encoding is always UTF-8 for maximum compatibility.

    Performance
    -----------
    Saving 1,000-10,000 records typically takes <100ms.
    Using indent=None (compact) is ~20% faster but much less readable.
    """
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON with specified formatting
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
