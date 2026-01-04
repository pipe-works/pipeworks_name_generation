"""
Command-line interface for the syllable extractor.

This module provides interactive CLI functionality for syllable extraction,
including language selection, user input prompts, and tab completion.
"""

import glob
import os
import sys
from pathlib import Path

from .extractor import SyllableExtractor
from .file_io import DEFAULT_OUTPUT_DIR, generate_output_filename, save_metadata
from .languages import SUPPORTED_LANGUAGES
from .models import ExtractionResult

# Try to enable readline for tab completion (Unix/Mac)
# On Windows, pyreadline3 provides similar functionality
try:
    import readline

    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False


def path_completer(text, state):
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


def setup_tab_completion():
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


def select_language() -> str:
    """
    Interactive prompt to select a language from supported options.

    Returns:
        The pyphen language code for the selected language

    Note:
        Exits the program if the user provides invalid input after
        multiple attempts or requests to quit.
    """
    print("\n" + "=" * 70)
    print("SYLLABLE EXTRACTOR - Language Selection")
    print("=" * 70)
    print("\nSupported Languages:")
    print("-" * 70)

    # Display languages in a formatted list
    languages = sorted(SUPPORTED_LANGUAGES.items())
    for idx, (name, code) in enumerate(languages, 1):
        print(f"{idx:2d}. {name:25s} ({code})")

    print("-" * 70)
    print("\nYou can select by:")
    print("  - Number (e.g., '13' for English UK)")
    print("  - Language name (e.g., 'English (US)')")
    print("  - Language code (e.g., 'en_US')")
    print("  - Type 'quit' to exit")
    print("=" * 70)

    while True:
        selection = input("\nSelect a language: ").strip()

        if selection.lower() == "quit":
            print("Exiting.")
            sys.exit(0)

        # Try to match by number
        if selection.isdigit():
            idx = int(selection) - 1
            if 0 <= idx < len(languages):
                selected_name, selected_code = languages[idx]
                print(f"\nSelected: {selected_name} ({selected_code})")
                return selected_code
            else:
                print(f"Error: Please enter a number between 1 and {len(languages)}")
                continue

        # Try to match by language name
        if selection in SUPPORTED_LANGUAGES:
            selected_code = SUPPORTED_LANGUAGES[selection]
            print(f"\nSelected: {selection} ({selected_code})")
            return selected_code

        # Try to match by language code
        if selection in SUPPORTED_LANGUAGES.values():
            # Find the language name for this code
            selected_name = next(
                name for name, code in SUPPORTED_LANGUAGES.items() if code == selection
            )
            print(f"\nSelected: {selected_name} ({selection})")
            return selection

        print("Error: Invalid selection. Please try again or type 'quit' to exit.")


def main():
    """
    Main entry point for the syllable extractor CLI.

    Workflow:
        1. Prompt user to select a language
        2. Configure extraction parameters (min/max syllable length)
        3. Prompt for input file path
        4. Extract syllables from input file
        5. Generate timestamped output filenames
        6. Save syllables and metadata to separate files
        7. Display summary to console

    Output Files:
        - YYYYMMDD_HHMMSS.syllables.txt: One syllable per line, sorted
        - YYYYMMDD_HHMMSS.meta.txt: Extraction metadata and statistics

    Both files are saved to _working/output/ by default.
    """
    print("\n" + "=" * 70)
    print("PYPHEN SYLLABLE EXTRACTOR")
    print("=" * 70)
    print("\nThis tool extracts syllables from text files using dictionary-based")
    print("hyphenation rules. Output is saved to _working/output/ by default.")
    print("=" * 70)

    # Step 1: Select language
    language_code = select_language()

    # Step 2: Configure extraction parameters
    print("\n" + "-" * 70)
    print("EXTRACTION SETTINGS")
    print("-" * 70)

    # Get min syllable length
    while True:
        min_len_str = input("\nMinimum syllable length (default: 2): ").strip()
        if not min_len_str:
            min_len = 2
            break
        try:
            min_len = int(min_len_str)
            if min_len < 1:
                print("Error: Minimum length must be at least 1")
                continue
            break
        except ValueError:
            print("Error: Please enter a valid number")

    # Get max syllable length
    while True:
        max_len_str = input("Maximum syllable length (default: 8): ").strip()
        if not max_len_str:
            max_len = 8
            break
        try:
            max_len = int(max_len_str)
            if max_len < min_len:
                print(f"Error: Maximum must be >= minimum ({min_len})")
                continue
            break
        except ValueError:
            print("Error: Please enter a valid number")

    print(f"\n✓ Settings: syllables between {min_len}-{max_len} characters")

    # Step 3: Initialize extractor
    try:
        extractor = SyllableExtractor(language_code, min_len, max_len)
        print(f"✓ Hyphenation dictionary loaded for: {language_code}")
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)

    # Step 4: Get input file path
    print("\n" + "-" * 70)
    print("INPUT FILE SELECTION")
    print("-" * 70)
    if READLINE_AVAILABLE:
        print("💡 Tip: Use TAB for path completion (~ for home directory)")
    print()

    while True:
        input_path_str = input_with_completion(
            "Enter input file path (or 'quit' to exit): "
        ).strip()

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

        break

    # Step 5: Extract syllables
    print(f"\n⏳ Processing {input_path}...")
    try:
        syllables = extractor.extract_syllables_from_file(input_path)
        print(f"✓ Extracted {len(syllables)} unique syllables")
    except Exception as e:
        print(f"\nError during extraction: {e}")
        sys.exit(1)

    # Step 6: Generate output filenames and create result object
    syllables_path, metadata_path = generate_output_filename()

    result = ExtractionResult(
        syllables=syllables,
        language_code=language_code,
        min_syllable_length=min_len,
        max_syllable_length=max_len,
        input_path=input_path,
        only_hyphenated=True,
    )

    # Step 7: Save syllables
    print(f"\n⏳ Saving syllables to {syllables_path}...")
    try:
        extractor.save_syllables(syllables, syllables_path)
        print("✓ Syllables saved successfully")
    except Exception as e:
        print(f"\nError saving syllables: {e}")
        sys.exit(1)

    # Step 8: Save metadata
    print(f"⏳ Saving metadata to {metadata_path}...")
    try:
        save_metadata(result, metadata_path)
        print("✓ Metadata saved successfully")
    except Exception as e:
        print(f"\nError saving metadata: {e}")
        sys.exit(1)

    # Step 9: Display summary to console
    print("\n" + result.format_metadata())
    print(f"\n✓ Output files saved to: {DEFAULT_OUTPUT_DIR}/")
    print(f"  - Syllables: {syllables_path.name}")
    print(f"  - Metadata:  {metadata_path.name}")
    print("\n✓ Done!\n")
