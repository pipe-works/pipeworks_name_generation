"""
Shared interactive mode utilities for syllable extractors.

This module provides common interactive mode prompts and UI helpers
used by both pyphen and NLTK syllable extractors.

Usage::

    from build_tools.tui_common.interactive import (
        prompt_extraction_settings,
        prompt_input_file,
        print_banner,
        print_section,
    )

    # Display tool banner
    print_banner("PYPHEN SYLLABLE EXTRACTOR", [
        "This tool extracts syllables using dictionary-based hyphenation.",
        "Output is saved to _working/output/ by default.",
    ])

    # Get extraction settings
    min_len, max_len = prompt_extraction_settings(
        default_min=2,
        default_max=8,
    )

    # Get input file
    input_path = prompt_input_file()
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from build_tools.tui_common.cli_utils import READLINE_AVAILABLE, input_with_completion


def print_banner(title: str, description_lines: list[str], width: int = 70) -> None:
    """
    Print a formatted banner with title and description.

    Args:
        title: Main title text (displayed in all caps)
        description_lines: List of description lines to display
        width: Banner width in characters (default: 70)

    Example:
        >>> print_banner("MY TOOL", [
        ...     "This tool does something useful.",
        ...     "Output is saved to output/ by default.",
        ... ])
        ======================================================================
        MY TOOL
        ======================================================================

        This tool does something useful.
        Output is saved to output/ by default.
        ======================================================================
    """
    print("\n" + "=" * width)
    print(title)
    print("=" * width)
    if description_lines:
        print()
        for line in description_lines:
            print(line)
    print("=" * width)


def print_section(title: str, width: int = 70) -> None:
    """
    Print a section header.

    Args:
        title: Section title text
        width: Section width in characters (default: 70)

    Example:
        >>> print_section("EXTRACTION SETTINGS")
        ----------------------------------------------------------------------
        EXTRACTION SETTINGS
        ----------------------------------------------------------------------
    """
    print("\n" + "-" * width)
    print(title)
    print("-" * width)


def prompt_integer(
    prompt_text: str,
    default: int,
    min_value: int = 1,
    max_value: int | None = None,
    compare_to: int | None = None,
    compare_label: str = "minimum",
) -> int:
    """
    Prompt for an integer value with validation.

    Args:
        prompt_text: Text to display in the prompt
        default: Default value if user presses Enter
        min_value: Minimum allowed value (default: 1)
        max_value: Maximum allowed value (optional)
        compare_to: Value that this must be >= (for max > min validation)
        compare_label: Label for compare_to value in error message

    Returns:
        Validated integer value

    Example:
        >>> min_len = prompt_integer(
        ...     "Minimum syllable length",
        ...     default=2,
        ...     min_value=1,
        ... )
        >>> max_len = prompt_integer(
        ...     "Maximum syllable length",
        ...     default=8,
        ...     min_value=1,
        ...     compare_to=min_len,
        ...     compare_label="minimum",
        ... )
    """
    while True:
        value_str = input(f"\n{prompt_text} (default: {default}): ").strip()

        if not value_str:
            return default

        try:
            value = int(value_str)

            if value < min_value:
                print(f"Error: Value must be at least {min_value}")
                continue

            if max_value is not None and value > max_value:
                print(f"Error: Value must be at most {max_value}")
                continue

            if compare_to is not None and value < compare_to:
                print(f"Error: Value must be >= {compare_label} ({compare_to})")
                continue

            return value

        except ValueError:
            print("Error: Please enter a valid number")


def prompt_extraction_settings(
    default_min: int = 2,
    default_max: int = 8,
    min_label: str = "Minimum syllable length",
    max_label: str = "Maximum syllable length",
) -> tuple[int, int]:
    """
    Prompt for min/max syllable length extraction settings.

    Args:
        default_min: Default minimum syllable length
        default_max: Default maximum syllable length
        min_label: Label for minimum prompt
        max_label: Label for maximum prompt

    Returns:
        Tuple of (min_len, max_len)

    Example:
        >>> print_section("EXTRACTION SETTINGS")
        >>> min_len, max_len = prompt_extraction_settings()
        >>> print(f"✓ Settings: syllables between {min_len}-{max_len} characters")
    """
    min_len = prompt_integer(
        min_label,
        default=default_min,
        min_value=1,
    )

    max_len = prompt_integer(
        max_label,
        default=default_max,
        min_value=1,
        compare_to=min_len,
        compare_label="minimum",
    )

    print(f"\n✓ Settings: syllables between {min_len}-{max_len} characters")
    return min_len, max_len


def prompt_input_file(
    prompt_text: str = "Enter input file path (or 'quit' to exit): ",
) -> Path:
    """
    Prompt for an input file path with tab completion.

    Includes:
    - Tab completion hint (if readline available)
    - Home directory expansion (~)
    - File existence validation
    - 'quit' command to exit

    Args:
        prompt_text: Text to display in the prompt

    Returns:
        Validated Path to the input file

    Raises:
        SystemExit: If user types 'quit'

    Example:
        >>> print_section("INPUT FILE SELECTION")
        >>> input_path = prompt_input_file()
    """
    if READLINE_AVAILABLE:
        print("💡 Tip: Use TAB for path completion (~ for home directory)")
    print()

    while True:
        input_path_str = input_with_completion(prompt_text).strip()

        if input_path_str.lower() == "quit":
            print("Exiting.")
            sys.exit(0)

        # Expand user home directory
        input_path_str = os.path.expanduser(input_path_str)
        input_path = Path(input_path_str)

        if not input_path.exists():
            print(f"Error: File not found: {input_path}")
            continue

        if not input_path.is_file():
            print(f"Error: Path is not a file: {input_path}")
            continue

        return input_path


def print_extraction_complete(
    syllables_path: Path,
    metadata_path: Path,
    output_base_dir: Path,
) -> None:
    """
    Print extraction completion message with output paths.

    Args:
        syllables_path: Path to saved syllables file
        metadata_path: Path to saved metadata file
        output_base_dir: Base output directory for relative path display

    Example:
        >>> print_extraction_complete(
        ...     syllables_path=Path("output/20260110/syllables/test.txt"),
        ...     metadata_path=Path("output/20260110/meta/test.txt"),
        ...     output_base_dir=Path("output/"),
        ... )
    """
    # Get the run directory (parent of syllables dir)
    run_dir = syllables_path.parent.parent

    print(f"\n✓ Output saved to run directory: {run_dir}/")

    try:
        print(f"  - Syllables: {syllables_path.relative_to(output_base_dir)}")
        print(f"  - Metadata:  {metadata_path.relative_to(output_base_dir)}")
    except ValueError:
        # If relative_to fails, use absolute paths
        print(f"  - Syllables: {syllables_path}")
        print(f"  - Metadata:  {metadata_path}")

    print("\n✓ Done!\n")


__all__ = [
    "print_banner",
    "print_section",
    "prompt_integer",
    "prompt_extraction_settings",
    "prompt_input_file",
    "print_extraction_complete",
    "READLINE_AVAILABLE",
]
