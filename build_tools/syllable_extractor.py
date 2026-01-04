"""
Syllable Extractor using pyphen hyphenation library.

This module provides functionality to extract syllables from text files using
dictionary-based hyphenation. It supports multiple languages via pyphen's
LibreOffice hyphenation dictionaries.

Note: This is a build-time tool, not intended for runtime use in the core
name generation system.
"""

import glob
import os
import re
import sys
from pathlib import Path
from typing import Set

try:
    import pyphen
except ImportError:
    print("Error: pyphen is not installed.")
    print("Install it with: pip install pyphen")
    sys.exit(1)

# Try to enable readline for tab completion (Unix/Mac)
# On Windows, pyreadline3 provides similar functionality
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False


# Mapping of language names to pyphen locale codes
# Based on pyphen's LibreOffice dictionary support
SUPPORTED_LANGUAGES = {
    "Afrikaans": "af_ZA",
    "Albanian": "sq_AL",
    "Assamese": "as_IN",
    "Basque": "eu",
    "Belarusian": "be_BY",
    "Bulgarian": "bg_BG",
    "Catalan": "ca",
    "Croatian": "hr_HR",
    "Czech": "cs_CZ",
    "Danish": "da_DK",
    "Dutch": "nl_NL",
    "English (UK)": "en_GB",
    "English (US)": "en_US",
    "Esperanto": "eo",
    "Estonian": "et_EE",
    "French": "fr",
    "Galician": "gl",
    "German": "de_DE",
    "German (Austria)": "de_AT",
    "German (Switzerland)": "de_CH",
    "Greek": "el_GR",
    "Hungarian": "hu_HU",
    "Icelandic": "is_IS",
    "Indonesian": "id_ID",
    "Italian": "it_IT",
    "Kannada": "kn_IN",
    "Lithuanian": "lt_LT",
    "Latvian": "lv_LV",
    "Marathi": "mr_IN",
    "Mongolian": "mn_MN",
    "Norwegian (Bokmål)": "nb_NO",
    "Norwegian (Nynorsk)": "nn_NO",
    "Oriya": "or_IN",
    "Polish": "pl_PL",
    "Portuguese (Brazil)": "pt_BR",
    "Portuguese (Portugal)": "pt_PT",
    "Punjabi": "pa_IN",
    "Romanian": "ro_RO",
    "Russian": "ru_RU",
    "Sanskrit": "sa_IN",
    "Serbian (Cyrillic)": "sr_Cyrl",
    "Serbian (Latin)": "sr_Latn",
    "Slovak": "sk_SK",
    "Slovenian": "sl_SI",
    "Spanish": "es",
    "Swedish": "sv_SE",
    "Telugu": "te_IN",
    "Thai": "th_TH",
    "Ukrainian": "uk_UA",
    "Zulu": "zu_ZA",
}


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
        text = os.path.join(text, '*')
    else:
        # Otherwise, treat as partial filename
        text += '*'

    # Get all matching paths
    matches = glob.glob(text)

    # Add trailing slash to directories for better UX
    matches = [
        f"{match}/" if os.path.isdir(match) else match
        for match in matches
    ]

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
    readline.set_completer_delims(' \t\n')


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


class SyllableExtractor:
    """
    Extracts syllables from text using pyphen hyphenation dictionaries.

    This class provides methods to process text files and extract individual
    syllables based on language-specific hyphenation rules.
    """

    def __init__(self, language_code: str, min_syllable_length: int = 1, max_syllable_length: int = 10):
        """
        Initialize the syllable extractor with a specific language.

        Args:
            language_code: Pyphen language/locale code (e.g., 'en_US', 'de_DE')
            min_syllable_length: Minimum syllable length to include (default: 1)
            max_syllable_length: Maximum syllable length to include (default: 10)

        Raises:
            ValueError: If the language code is not supported by pyphen
        """
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

    def extract_syllables_from_text(self, text: str, only_hyphenated: bool = True) -> Set[str]:
        """
        Extract unique syllables from a block of text.

        Args:
            text: Input text to process
            only_hyphenated: If True, only include syllables from words that pyphen
                           actually hyphenated (default: True). This filters out
                           whole words that couldn't be syllabified.

        Returns:
            Set of unique syllables extracted from the text

        Note:
            - Only processes words containing alphabetic characters
            - Case-insensitive (converts to lowercase)
            - Removes punctuation and special characters
            - Filters syllables by min/max length constraints
            - When only_hyphenated=True, excludes words pyphen couldn't split
        """
        # Extract words using regex (alphanumeric sequences)
        words = re.findall(r'\b[a-zA-ZÀ-ÿ]+\b', text)

        syllables: Set[str] = set()

        for word in words:
            # Convert to lowercase for consistency
            word_lower = word.lower()

            # Get hyphenated version of the word
            # pyphen.inserted() returns the word with hyphens at syllable boundaries
            hyphenated = self.dictionary.inserted(word_lower, hyphen='-')

            # Check if the word was actually hyphenated
            # If no hyphens were inserted, the word couldn't be syllabified
            if only_hyphenated and '-' not in hyphenated:
                continue

            # Split on hyphens to get individual syllables
            word_syllables = hyphenated.split('-')

            # Filter syllables by length and add to set
            for syllable in word_syllables:
                if self.min_syllable_length <= len(syllable) <= self.max_syllable_length:
                    syllables.add(syllable)

        return syllables

    def extract_syllables_from_file(self, input_path: Path) -> Set[str]:
        """
        Extract unique syllables from a text file.

        Args:
            input_path: Path to the input text file

        Returns:
            Set of unique syllables extracted from the file

        Raises:
            FileNotFoundError: If the input file doesn't exist
            IOError: If there's an error reading the file
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            raise IOError(f"Error reading file {input_path}: {e}")

        return self.extract_syllables_from_text(text)

    def save_syllables(self, syllables: Set[str], output_path: Path) -> None:
        """
        Save syllables to a text file (one syllable per line, sorted).

        Args:
            syllables: Set of syllables to save
            output_path: Path to the output file

        Raises:
            IOError: If there's an error writing the file
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for syllable in sorted(syllables):
                    f.write(f"{syllable}\n")
        except Exception as e:
            raise IOError(f"Error writing file {output_path}: {e}")


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

        if selection.lower() == 'quit':
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
        2. Prompt for input file path
        3. Prompt for output file path
        4. Extract syllables and save to output file
        5. Display summary statistics
    """
    print("\n" + "=" * 70)
    print("PYPHEN SYLLABLE EXTRACTOR")
    print("=" * 70)
    print("\nThis tool extracts syllables from text files using dictionary-based")
    print("hyphenation rules. The output is a sorted list of unique syllables.")
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
        input_path_str = input_with_completion("Enter input file path (or 'quit' to exit): ").strip()

        if input_path_str.lower() == 'quit':
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

    # Step 5: Get output file path
    print()
    if READLINE_AVAILABLE:
        print("💡 Tip: Use TAB for path completion")
    output_path_str = input_with_completion("Enter output file path (default: syllables.txt): ").strip()

    # Expand user home directory
    if output_path_str:
        output_path_str = os.path.expanduser(output_path_str)
        output_path = Path(output_path_str)
    else:
        output_path = Path("syllables.txt")

    # Confirm overwrite if file exists
    if output_path.exists():
        confirm = input(f"\n⚠ Warning: {output_path} exists. Overwrite? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            sys.exit(0)

    # Step 6: Extract syllables
    print(f"\n⏳ Processing {input_path}...")
    try:
        syllables = extractor.extract_syllables_from_file(input_path)
        print(f"✓ Extracted {len(syllables)} unique syllables")
    except Exception as e:
        print(f"\nError during extraction: {e}")
        sys.exit(1)

    # Step 7: Save syllables
    print(f"\n⏳ Saving syllables to {output_path}...")
    try:
        extractor.save_syllables(syllables, output_path)
        print("✓ Syllables saved successfully")
    except Exception as e:
        print(f"\nError saving syllables: {e}")
        sys.exit(1)

    # Step 8: Display summary
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Language:           {language_code}")
    print(f"Syllable length:    {min_len}-{max_len} characters")
    print(f"Input file:         {input_path}")
    print(f"Output file:        {output_path}")
    print(f"Unique syllables:   {len(syllables)}")
    print("Only hyphenated:    Yes (whole words excluded)")
    print("=" * 70)

    # Show syllable length distribution
    if syllables:
        print("\nSyllable Length Distribution:")
        by_length = {}
        for syll in syllables:
            length = len(syll)
            by_length.setdefault(length, []).append(syll)

        for length in sorted(by_length.keys()):
            count = len(by_length[length])
            bar = "█" * min(40, count)
            print(f"  {length:2d} chars: {count:4d} {bar}")

    # Show sample syllables
    if syllables:
        sample_size = min(15, len(syllables))
        sample = sorted(syllables)[:sample_size]
        print(f"\nSample syllables (first {sample_size}):")
        for syllable in sample:
            print(f"  - {syllable}")
        if len(syllables) > sample_size:
            print(f"  ... and {len(syllables) - sample_size} more")

    print("\n✓ Done!\n")


if __name__ == "__main__":
    main()
