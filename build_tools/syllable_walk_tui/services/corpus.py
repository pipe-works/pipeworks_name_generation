"""
Corpus directory validation and utilities for Syllable Walker TUI.

This module provides functions for validating and loading corpus data
from normalized syllable extraction output directories.
"""

import json
import sqlite3
from pathlib import Path


def validate_corpus_directory(path: Path) -> tuple[bool, str | None, str | None]:
    """
    Validate that a directory contains valid corpus files.

    Checks for either NLTK or Pyphen corpus structure:
    - nltk_syllables_unique.txt + nltk_syllables_frequencies.json
    - pyphen_syllables_unique.txt + pyphen_syllables_frequencies.json

    Args:
        path: Directory path to validate

    Returns:
        Tuple of (is_valid, corpus_type, error_message)
        - is_valid: True if valid corpus directory
        - corpus_type: "NLTK" or "Pyphen" if valid, None otherwise
        - error_message: Error description if invalid, None otherwise

    Examples:
        >>> validate_corpus_directory(Path("/path/to/20260110_115601_nltk"))
        (True, "NLTK", None)

        >>> validate_corpus_directory(Path("/invalid/path"))
        (False, None, "Directory does not exist")
    """
    # Check directory exists
    if not path.exists():
        return (False, None, "Directory does not exist")

    if not path.is_dir():
        return (False, None, "Path is not a directory")

    # Check for NLTK corpus
    nltk_syllables = path / "nltk_syllables_unique.txt"
    nltk_frequencies = path / "nltk_syllables_frequencies.json"

    if nltk_syllables.exists() and nltk_frequencies.exists():
        # Validate both are files
        if not nltk_syllables.is_file():
            return (False, None, "nltk_syllables_unique.txt is not a file")
        if not nltk_frequencies.is_file():
            return (False, None, "nltk_syllables_frequencies.json is not a file")

        return (True, "NLTK", None)

    # Check for Pyphen corpus
    pyphen_syllables = path / "pyphen_syllables_unique.txt"
    pyphen_frequencies = path / "pyphen_syllables_frequencies.json"

    if pyphen_syllables.exists() and pyphen_frequencies.exists():
        # Validate both are files
        if not pyphen_syllables.is_file():
            return (False, None, "pyphen_syllables_unique.txt is not a file")
        if not pyphen_frequencies.is_file():
            return (False, None, "pyphen_syllables_frequencies.json is not a file")

        return (True, "Pyphen", None)

    # No valid corpus found
    return (
        False,
        None,
        "No corpus files found. Directory must contain either:\n"
        "  - nltk_syllables_unique.txt + nltk_syllables_frequencies.json\n"
        "  - pyphen_syllables_unique.txt + pyphen_syllables_frequencies.json",
    )


def get_corpus_info(path: Path) -> str:
    """
    Get display-friendly corpus information string.

    Args:
        path: Path to corpus directory

    Returns:
        Short description string for UI display

    Examples:
        >>> get_corpus_info(Path("/path/to/20260110_115601_nltk"))
        "NLTK (20260110_115601_nltk)"
    """
    is_valid, corpus_type, error = validate_corpus_directory(path)

    if not is_valid:
        return f"Invalid: {error}"

    # Extract directory name for display
    dir_name = path.name

    return f"{corpus_type} ({dir_name})"


def load_corpus_data(path: Path) -> tuple[list[str], dict[str, int]]:
    """
    Load syllables and frequencies from a validated corpus directory.

    Args:
        path: Path to validated corpus directory

    Returns:
        Tuple of (syllables_list, frequencies_dict)
        - syllables_list: List of unique syllables (one per line from .txt file)
        - frequencies_dict: Dictionary mapping syllable to frequency count

    Raises:
        ValueError: If directory is invalid or files cannot be loaded
        FileNotFoundError: If expected corpus files are missing
        json.JSONDecodeError: If frequencies JSON is malformed

    Examples:
        >>> syllables, freqs = load_corpus_data(Path("/path/to/20260110_115601_nltk"))
        >>> len(syllables)
        15234
        >>> freqs["hello"]
        42

    Note:
        This function assumes the directory has already been validated with
        validate_corpus_directory(). It will attempt to load from either
        NLTK or Pyphen corpus files based on what exists.
    """
    # Validate directory first
    is_valid, corpus_type, error = validate_corpus_directory(path)
    if not is_valid:
        raise ValueError(f"Invalid corpus directory: {error}")

    # Determine which corpus files to load
    if corpus_type == "NLTK":
        syllables_file = path / "nltk_syllables_unique.txt"
        frequencies_file = path / "nltk_syllables_frequencies.json"
    elif corpus_type == "Pyphen":
        syllables_file = path / "pyphen_syllables_unique.txt"
        frequencies_file = path / "pyphen_syllables_frequencies.json"
    else:
        raise ValueError(f"Unknown corpus type: {corpus_type}")

    # Load syllables (one per line)
    try:
        with open(syllables_file, encoding="utf-8") as f:
            syllables = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        raise FileNotFoundError(f"Syllables file not found: {syllables_file}")
    except Exception as e:
        raise ValueError(f"Error reading syllables file: {e}") from e

    # Load frequencies (JSON dict)
    try:
        with open(frequencies_file, encoding="utf-8") as f:
            frequencies = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Frequencies file not found: {frequencies_file}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in frequencies file: {e.msg}", e.doc, e.pos
        ) from e
    except Exception as e:
        raise ValueError(f"Error reading frequencies file: {e}") from e

    # Validate data integrity
    if not syllables:
        raise ValueError("Syllables file is empty")

    if not frequencies:
        raise ValueError("Frequencies file is empty")

    # Sanity check: all syllables should have frequency data
    missing_freqs = [s for s in syllables if s not in frequencies]
    if missing_freqs:
        # This is a warning, not a fatal error - some syllables might be legitimately rare
        print(
            f"Warning: {len(missing_freqs)} syllables missing frequency data "
            f"(out of {len(syllables)} total)"
        )

    return syllables, frequencies


def load_annotated_data_from_sqlite(db_path: Path) -> list[dict]:
    """
    Load phonetic feature annotations from a SQLite corpus database.

    This function loads syllable data from an optimized SQLite database,
    which is much faster and more memory-efficient than loading from JSON.

    Args:
        db_path: Path to corpus.db file

    Returns:
        List of dictionaries, each containing:
        - syllable: The syllable string
        - frequency: Occurrence count in source corpus
        - features: Dict of boolean phonetic feature flags

    Raises:
        FileNotFoundError: If database file doesn't exist
        sqlite3.Error: If database is corrupted or incompatible

    Performance Notes:
        - Much faster than JSON loading (<100ms vs 1-2s)
        - Memory-efficient (loads on-demand)
        - Can be called on main thread without freezing UI

    Examples:
        >>> db_path = Path("/path/to/20260110_115601_nltk/data/corpus.db")
        >>> data = load_annotated_data_from_sqlite(db_path)
        >>> len(data)
        33640
    """
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {db_path}")

    try:
        # Open database in read-only mode
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query all syllables with features, ordered by syllable for determinism
        cursor.execute(
            """
            SELECT
                syllable, frequency,
                starts_with_vowel, starts_with_cluster, starts_with_heavy_cluster,
                contains_plosive, contains_fricative, contains_liquid, contains_nasal,
                short_vowel, long_vowel,
                ends_with_vowel, ends_with_nasal, ends_with_stop
            FROM syllables
            ORDER BY syllable
            """
        )

        # Convert rows to the expected dictionary format
        data = []
        for row in cursor.fetchall():
            data.append(
                {
                    "syllable": row["syllable"],
                    "frequency": row["frequency"],
                    "features": {
                        "starts_with_vowel": bool(row["starts_with_vowel"]),
                        "starts_with_cluster": bool(row["starts_with_cluster"]),
                        "starts_with_heavy_cluster": bool(row["starts_with_heavy_cluster"]),
                        "contains_plosive": bool(row["contains_plosive"]),
                        "contains_fricative": bool(row["contains_fricative"]),
                        "contains_liquid": bool(row["contains_liquid"]),
                        "contains_nasal": bool(row["contains_nasal"]),
                        "short_vowel": bool(row["short_vowel"]),
                        "long_vowel": bool(row["long_vowel"]),
                        "ends_with_vowel": bool(row["ends_with_vowel"]),
                        "ends_with_nasal": bool(row["ends_with_nasal"]),
                        "ends_with_stop": bool(row["ends_with_stop"]),
                    },
                }
            )

        conn.close()
        return data

    except sqlite3.Error as e:
        raise sqlite3.Error(f"Error reading SQLite database {db_path}: {e}") from e


def load_annotated_data(path: Path) -> tuple[list[dict], dict[str, str]]:
    """
    Load phonetic feature annotations from a validated corpus directory.

    This function intelligently loads from either SQLite (if available) or
    JSON (fallback for backwards compatibility). SQLite loading is much faster
    and more memory-efficient.

    Data structure (same for both sources):
    [
      {
        "syllable": "aa",
        "frequency": 1022,
        "features": {
          "starts_with_vowel": true,
          "starts_with_cluster": false,
          "starts_with_heavy_cluster": false,
          "contains_plosive": false,
          "contains_fricative": false,
          "contains_liquid": false,
          "contains_nasal": false,
          "short_vowel": false,
          "long_vowel": true,
          "ends_with_vowel": true,
          "ends_with_nasal": false,
          "ends_with_stop": false
        }
      },
      ...
    ]

    Args:
        path: Path to validated corpus directory

    Returns:
        Tuple of (data, metadata):
        - data: List of dictionaries, each containing:
            - syllable: The syllable string
            - frequency: Occurrence count in source corpus
            - features: Dict of boolean phonetic feature flags
        - metadata: Dictionary with loading information:
            - source: "sqlite" or "json"
            - file_name: Name of the file loaded from
            - load_time_ms: Approximate load time in milliseconds

    Raises:
        ValueError: If directory is invalid or file cannot be loaded
        FileNotFoundError: If neither SQLite nor JSON data is available
        json.JSONDecodeError: If JSON is malformed (when loading from JSON)

    Performance Notes:
        - SQLite: <100ms load time, memory-efficient (preferred)
        - JSON: 1-2s load time, loads entire file into memory (fallback)
        - Automatically chooses best available format

    Examples:
        >>> data, meta = load_annotated_data(Path("/path/to/20260110_115601_nltk"))
        >>> len(data)
        33640
        >>> meta["source"]
        "sqlite"
        >>> data[0]["syllable"]
        "aa"
        >>> data[0]["features"]["starts_with_vowel"]
        True
    """
    # Validate directory first to determine corpus type
    is_valid, corpus_type, error = validate_corpus_directory(path)
    if not is_valid:
        raise ValueError(f"Invalid corpus directory: {error}")

    # Check for SQLite database first (preferred, fast and memory-efficient)
    db_path = path / "data" / "corpus.db"
    if db_path.exists():
        try:
            import time

            start_time = time.time()
            data = load_annotated_data_from_sqlite(db_path)
            load_time_ms = int((time.time() - start_time) * 1000)

            metadata = {
                "source": "sqlite",
                "file_name": "corpus.db",
                "load_time_ms": str(load_time_ms),
            }
            return data, metadata
        except Exception as e:
            # If SQLite fails, fall back to JSON
            print(f"Warning: SQLite loading failed ({e}), falling back to JSON")

    # Fall back to JSON loading (backwards compatibility)
    # Determine which annotated file to load based on corpus type
    # These files live in the data/ subdirectory
    if corpus_type == "NLTK":
        annotated_file = path / "data" / "nltk_syllables_annotated.json"
    elif corpus_type == "Pyphen":
        annotated_file = path / "data" / "pyphen_syllables_annotated.json"
    else:
        raise ValueError(f"Unknown corpus type: {corpus_type}")

    # Check that the annotated data file exists
    # (not all corpus directories may have been annotated yet)
    if not annotated_file.exists():
        raise FileNotFoundError(
            f"No annotated data found in {path / 'data'}\n"
            f"Looked for:\n"
            f"  - corpus.db (preferred, SQLite format)\n"
            f"  - {annotated_file.name} (JSON format)\n"
            f"\n"
            f"This corpus directory may not have been processed with "
            f"syllable_feature_annotator yet, or you may need to run:\n"
            f"  python -m build_tools.corpus_sqlite_builder {path}"
        )

    # Load the JSON file
    # Note: This is a potentially slow operation (1-2 seconds for 15MB files)
    # The caller should run this in a background worker to avoid blocking the UI
    print(f"Loading from JSON (slower): {annotated_file.name}")
    try:
        import time

        start_time = time.time()
        with open(annotated_file, encoding="utf-8") as f:
            annotated_data = json.load(f)
        load_time_ms = int((time.time() - start_time) * 1000)
    except FileNotFoundError:
        # Already checked above, but handle race condition
        raise FileNotFoundError(f"Annotated data file not found: {annotated_file}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in annotated data file: {e.msg}", e.doc, e.pos
        ) from e
    except Exception as e:
        raise ValueError(f"Error reading annotated data file: {e}") from e

    # Validate that we got a non-empty list
    if not isinstance(annotated_data, list):
        raise ValueError(
            f"Annotated data should be a JSON array, got {type(annotated_data).__name__}"
        )

    if not annotated_data:
        raise ValueError("Annotated data file is empty")

    # Sanity check: verify first entry has expected structure
    # (don't check all entries for performance - that would be expensive)
    first_entry = annotated_data[0]
    if not isinstance(first_entry, dict):
        raise ValueError(
            f"Annotated data entries should be objects, got {type(first_entry).__name__}"
        )

    required_keys = {"syllable", "frequency", "features"}
    missing_keys = required_keys - set(first_entry.keys())
    if missing_keys:
        raise ValueError(
            f"Annotated data entries missing required keys: {missing_keys}\n"
            f"Found keys: {set(first_entry.keys())}"
        )

    metadata = {
        "source": "json",
        "file_name": annotated_file.name,
        "load_time_ms": str(load_time_ms),
    }
    return annotated_data, metadata
