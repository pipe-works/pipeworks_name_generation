"""
Shared CLI utilities for build tools.

This module provides common functionality used across multiple CLI tools,
including tab completion, file discovery, and corpus database integration.

These utilities were extracted from the syllable extractor CLIs to eliminate
duplication and ensure consistent behavior across tools.
"""

from __future__ import annotations

import glob
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Try to enable readline for tab completion (Unix/Mac)
# On Windows, pyreadline3 provides similar functionality
try:
    import readline

    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False

# Corpus DB integration (optional)
try:
    from build_tools.corpus_db import CorpusLedger  # noqa: F401

    CORPUS_DB_AVAILABLE = True
except ImportError:
    CORPUS_DB_AVAILABLE = False


def record_corpus_db_safe(operation: str, func: Callable[[], Any], quiet: bool = False) -> Any:
    """
    Execute corpus_db operation with safe error handling.

    If corpus_db recording fails, logs warning to stderr but allows
    extraction to continue. Ensures corpus_db is purely observational.

    Args:
        operation: Description of operation (e.g., "start run")
        func: Callable performing the corpus_db operation
        quiet: If True, suppress warning messages

    Returns:
        Result of func() if successful, None if failed
    """
    try:
        return func()
    except Exception as e:
        if not quiet:
            print(f"Warning: Failed to record {operation} to corpus_db: {e}", file=sys.stderr)
        return None


def path_completer(text: str, state: int) -> str | None:
    """
    Tab completion function for file paths.

    This enables bash-like tab completion for navigating directories
    and selecting files.

    Args:
        text: The current text being completed
        state: The completion state (0 for first call, incremented for each match)

    Returns:
        The next completion match, or None when no more matches
    """
    # Expand user home directory (~)
    text = os.path.expanduser(text)

    # If text is empty or just a partial path, add wildcard
    if os.path.isdir(text):
        # If it's a directory, show contents
        text = os.path.join(text, "*")
    else:
        # Otherwise, treat as partial filename
        text += "*"

    # Get all matching paths
    matches = glob.glob(text)

    # Add trailing slash to directories for better UX
    matches = [f"{match}/" if os.path.isdir(match) else match for match in matches]

    # Return the state-th match
    try:
        return matches[state]
    except IndexError:
        return None


def setup_tab_completion() -> None:
    """
    Configure readline for tab completion with file paths.

    This enables:
    - Tab completion for file and directory names
    - Tilde (~) expansion for home directory
    - Standard bash-like completion behavior
    """
    if not READLINE_AVAILABLE:
        return

    # Set the completer function
    readline.set_completer(path_completer)

    # Configure tab completion
    # Use tab for completion
    readline.parse_and_bind("tab: complete")

    # Set delimiters (don't break on /, -, etc. in paths)
    readline.set_completer_delims(" \t\n")


def input_with_completion(prompt: str) -> str:
    """
    Get user input with tab completion enabled.

    Args:
        prompt: The prompt to display

    Returns:
        User input string
    """
    if READLINE_AVAILABLE:
        setup_tab_completion()

    return input(prompt)


def discover_files(source: Path, pattern: str = "*.txt", recursive: bool = False) -> list[Path]:
    """
    Discover text files in a directory matching the specified pattern.

    This function searches for files matching a glob pattern in the specified
    directory, optionally recursing into subdirectories. Results are sorted
    alphabetically for deterministic processing order.

    Args:
        source: Directory to search for files. Must be an existing directory.
        pattern: Glob pattern for file matching (default: "*.txt").
                Examples: "*.txt", "*.md", "data_*.csv"
        recursive: If True, search recursively into subdirectories using rglob.
                  If False, search only the top level (default: False).

    Returns:
        List of Path objects for matching files, sorted alphabetically.
        Returns empty list if no files match.

    Raises:
        ValueError: If source is not a directory or doesn't exist.

    Example:
        >>> # Find all .txt files in a directory
        >>> files = discover_files(Path("/data/texts"))
        >>> print(f"Found {len(files)} files")

        >>> # Find all .md files recursively
        >>> files = discover_files(Path("/data"), pattern="*.md", recursive=True)

        >>> # Find files with custom pattern
        >>> files = discover_files(Path("/data"), pattern="book_*.txt")
    """
    if not source.exists():
        raise ValueError(f"Source path does not exist: {source}")

    if not source.is_dir():
        raise ValueError(f"Source path is not a directory: {source}")

    if recursive:
        # Use rglob for recursive search
        files = list(source.rglob(pattern))
    else:
        # Use glob for non-recursive search
        files = list(source.glob(pattern))

    # Filter to only regular files (not directories)
    files = [f for f in files if f.is_file()]

    # Sort alphabetically for deterministic processing order
    return sorted(files)


__all__ = [
    "READLINE_AVAILABLE",
    "CORPUS_DB_AVAILABLE",
    "record_corpus_db_safe",
    "path_completer",
    "setup_tab_completion",
    "input_with_completion",
    "discover_files",
]
