"""
Directory validators for Pipeline TUI browsers.

This module provides validation functions for the DirectoryBrowserScreen
that check whether directories are suitable for source input or output.

**Validator Function Signature:**

All validators return a tuple of ``(is_valid, type_label, message)``:

- ``is_valid``: True if directory can be selected
- ``type_label``: Short label describing valid directories (e.g., "source")
- ``message``: Error message if invalid, or description if valid

**Example Usage:**

.. code-block:: python

    from build_tools.tui_common.controls import DirectoryBrowserScreen
    from build_tools.pipeline_tui.services.validators import validate_source_directory

    result = await app.push_screen_wait(
        DirectoryBrowserScreen(
            title="Select Source",
            validator=validate_source_directory,
        )
    )
"""

from __future__ import annotations

from pathlib import Path


def validate_source_directory(path: Path) -> tuple[bool, str, str]:
    """
    Validate a directory as a source for text extraction.

    A valid source directory contains at least one ``.txt`` file,
    either directly or in subdirectories.

    Args:
        path: Directory path to validate

    Returns:
        Tuple of (is_valid, type_label, message):
        - is_valid: True if directory contains extractable files
        - type_label: "source" if valid
        - message: File count if valid, error description if invalid
    """
    if not path.is_dir():
        return (False, "", "Not a directory")

    # Count .txt files (direct children and recursive)
    direct_txt = list(path.glob("*.txt"))
    all_txt = list(path.glob("**/*.txt"))

    if not all_txt:
        return (False, "", "No .txt files found")

    # Build informative message
    if len(direct_txt) == len(all_txt):
        msg = f"Found {len(all_txt)} text file(s)"
    else:
        msg = f"Found {len(all_txt)} text file(s) ({len(direct_txt)} direct)"

    return (True, "source", msg)


def validate_output_directory(path: Path) -> tuple[bool, str, str]:
    """
    Validate a directory as an output location for pipeline results.

    Any existing directory is valid. Non-existent paths are invalid
    (the pipeline will create timestamped subdirectories, but the
    parent must exist).

    Args:
        path: Directory path to validate

    Returns:
        Tuple of (is_valid, type_label, message):
        - is_valid: True if directory exists and is writable
        - type_label: "output" if valid
        - message: Status description
    """
    if not path.exists():
        return (False, "", "Directory does not exist")

    if not path.is_dir():
        return (False, "", "Not a directory")

    # Check if writable by attempting to check access
    # Note: This is a basic check; actual write may still fail
    try:
        # Check if we can list the directory (basic access test)
        list(path.iterdir())
    except PermissionError:
        return (False, "", "Permission denied")

    # Count existing pipeline runs (directories matching timestamp pattern)
    existing_runs = [
        d
        for d in path.iterdir()
        if d.is_dir() and (d.name.endswith("_pyphen") or d.name.endswith("_nltk"))
    ]

    if existing_runs:
        msg = f"Valid output ({len(existing_runs)} existing runs)"
    else:
        msg = "Valid output directory"

    return (True, "output", msg)


def validate_corpus_directory(path: Path) -> tuple[bool, str, str]:
    """
    Validate a directory as a processed corpus (for syllable_walk_tui compatibility).

    A valid corpus directory contains either NLTK or pyphen normalized output:

    - NLTK corpus: ``nltk_syllables_unique.txt`` and ``nltk_syllables_frequencies.json``
    - Pyphen corpus: ``pyphen_syllables_unique.txt`` and ``pyphen_syllables_frequencies.json``

    This function is provided for compatibility with syllable_walk_tui,
    which needs to select processed corpus directories.

    Args:
        path: Directory path to validate

    Returns:
        Tuple of (is_valid, corpus_type, message):
        - is_valid: True if directory contains valid corpus files
        - corpus_type: "nltk" or "pyphen" if valid, empty if invalid
        - message: Corpus info if valid, error description if invalid
    """
    if not path.is_dir():
        return (False, "", "Not a directory")

    # Check for NLTK corpus files
    nltk_unique = path / "nltk_syllables_unique.txt"
    nltk_freq = path / "nltk_syllables_frequencies.json"
    if nltk_unique.exists() and nltk_freq.exists():
        # Count syllables for info message
        try:
            syllable_count = sum(1 for _ in nltk_unique.open())
            return (True, "nltk", f"NLTK corpus ({syllable_count:,} syllables)")
        except Exception:
            return (True, "nltk", "NLTK corpus")

    # Check for pyphen corpus files
    pyphen_unique = path / "pyphen_syllables_unique.txt"
    pyphen_freq = path / "pyphen_syllables_frequencies.json"
    if pyphen_unique.exists() and pyphen_freq.exists():
        # Count syllables for info message
        try:
            syllable_count = sum(1 for _ in pyphen_unique.open())
            return (True, "pyphen", f"Pyphen corpus ({syllable_count:,} syllables)")
        except Exception:
            return (True, "pyphen", "Pyphen corpus")

    # No valid corpus found
    return (
        False,
        "",
        "No corpus files found (missing *_syllables_unique.txt or *_frequencies.json)",
    )
