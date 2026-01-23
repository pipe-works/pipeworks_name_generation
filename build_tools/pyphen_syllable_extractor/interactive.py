"""
Interactive mode for the pyphen syllable extractor.

This module provides the interactive CLI workflow for single-file extraction
with language selection and user prompts.
"""

from __future__ import annotations

import sys

from build_tools.tui_common.interactive import (
    print_banner,
    print_extraction_complete,
    print_section,
    prompt_extraction_settings,
    prompt_input_file,
)
from build_tools.tui_common.ledger import ExtractionLedgerContext

from .extractor import SyllableExtractor
from .file_io import DEFAULT_OUTPUT_DIR, generate_output_filename, save_metadata
from .language_detection import is_detection_available
from .languages import SUPPORTED_LANGUAGES
from .models import ExtractionResult

# Version for ledger
try:
    from build_tools.pyphen_syllable_extractor import __version__ as _extractor_version
except (ImportError, AttributeError):
    _extractor_version = "unknown"


def select_language() -> str:
    """
    Interactive prompt to select a language from supported options.

    Returns:
        The pyphen language code for the selected language, or "auto"
        for automatic language detection

    Note:
        Exits the program if the user provides invalid input after
        multiple attempts or requests to quit.
    """
    print("\n" + "=" * 70)
    print("SYLLABLE EXTRACTOR - Language Selection")
    print("=" * 70)

    # Check if auto-detection is available
    auto_available = is_detection_available()
    if auto_available:
        print("\n💡 Auto-detection available! Type 'auto' to automatically detect language.")

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
    if auto_available:
        print("  - Type 'auto' for automatic language detection")
    print("  - Type 'quit' to exit")
    print("=" * 70)

    while True:
        selection = input("\nSelect a language: ").strip()

        if selection.lower() == "quit":
            print("Exiting.")
            sys.exit(0)

        # Check for auto-detection
        if selection.lower() == "auto":
            if not auto_available:
                print(
                    "Error: Auto-detection not available. "
                    "Install langdetect: pip install langdetect"
                )
                continue
            print("\n✓ Selected: Automatic language detection")
            return "auto"

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


def run_interactive() -> None:
    """
    Interactive mode entry point for the pyphen syllable extractor CLI.

    Workflow:
        1. Prompt user to select a language (or 'auto' for automatic detection)
        2. Configure extraction parameters (min/max syllable length)
        3. Prompt for input file path
        4. Extract syllables from input file (with optional auto-detection)
        5. Generate timestamped output filenames
        6. Save syllables and metadata to separate files
        7. Display summary to console

    Language Detection:
        - If 'auto' is selected and langdetect is installed, the tool will
          automatically detect the language of the input text
        - Detection requires at least 20-50 characters for reliable results
        - Falls back to English (en_US) if detection fails

    Output Files:
        - YYYYMMDD_HHMMSS.syllables.LANG.txt: One syllable per line, sorted
        - YYYYMMDD_HHMMSS.meta.LANG.txt: Extraction metadata and statistics

    Both files are saved to _working/output/ by default.
    """
    # Display banner
    print_banner(
        "PYPHEN SYLLABLE EXTRACTOR",
        [
            "This tool extracts syllables from text files using dictionary-based",
            "hyphenation rules. Output is saved to _working/output/ by default.",
        ],
    )

    # Step 1: Select language
    language_code = select_language()

    # Step 2: Configure extraction parameters
    print_section("EXTRACTION SETTINGS")
    min_len, max_len = prompt_extraction_settings(default_min=2, default_max=8)

    # Step 3: Initialize extractor (skip if using auto-detection)
    if language_code != "auto":
        try:
            extractor = SyllableExtractor(language_code, min_len, max_len)
            print(f"✓ Hyphenation dictionary loaded for: {language_code}")
        except ValueError as e:
            print(f"\nError: {e}")
            sys.exit(1)

    # Step 4: Get input file path
    print_section("INPUT FILE SELECTION")
    input_path = prompt_input_file()

    # Use ledger context for corpus DB integration
    pyphen_lang = None if language_code == "auto" else language_code

    with ExtractionLedgerContext(
        extractor_tool="pyphen_syllable_extractor",
        extractor_version=_extractor_version,
        pyphen_lang=pyphen_lang,
        min_len=min_len,
        max_len=max_len,
    ) as ledger_ctx:
        # Record input
        ledger_ctx.record_input(input_path)

        # Step 5: Extract syllables
        print(f"\n⏳ Processing {input_path}...")
        try:
            if language_code == "auto":
                # Use auto-detection
                syllables, stats, detected_language = (
                    SyllableExtractor.extract_file_with_auto_language(
                        input_path,
                        min_syllable_length=min_len,
                        max_syllable_length=max_len,
                        suppress_warnings=True,
                    )
                )
                language_code = detected_language  # Update for metadata
                print(f"✓ Detected language: {detected_language}")
                print(f"✓ Extracted {len(syllables)} unique syllables")
                # Create extractor instance with detected language for saving
                extractor = SyllableExtractor(language_code, min_len, max_len)
            else:
                # Use manual language selection
                syllables, stats = extractor.extract_syllables_from_file(input_path)
                print(f"✓ Extracted {len(syllables)} unique syllables")
        except Exception as e:
            print(f"\nError during extraction: {e}")
            ledger_ctx.set_result(success=False)
            sys.exit(1)

        # Step 6: Generate output filenames and create result object
        syllables_path, metadata_path = generate_output_filename(language_code=language_code)

        result = ExtractionResult(
            syllables=syllables,
            language_code=language_code,
            min_syllable_length=min_len,
            max_syllable_length=max_len,
            input_path=input_path,
            only_hyphenated=True,
            total_words=stats["total_words"],
            skipped_unhyphenated=stats["skipped_unhyphenated"],
            rejected_syllables=stats["rejected_syllables"],
            processed_words=stats["processed_words"],
        )

        # Step 7: Save syllables
        print(f"\n⏳ Saving syllables to {syllables_path}...")
        try:
            extractor.save_syllables(syllables, syllables_path)
            print("✓ Syllables saved successfully")
        except Exception as e:
            print(f"\nError saving syllables: {e}")
            ledger_ctx.set_result(success=False)
            sys.exit(1)

        # Step 8: Save metadata
        print(f"⏳ Saving metadata to {metadata_path}...")
        try:
            save_metadata(result, metadata_path)
            print("✓ Metadata saved successfully")
        except Exception as e:
            print(f"\nError saving metadata: {e}")
            ledger_ctx.set_result(success=False)
            sys.exit(1)

        # Record output
        ledger_ctx.record_output(
            output_path=syllables_path,
            unique_syllable_count=len(syllables),
            meta_path=metadata_path,
        )
        ledger_ctx.set_result(success=True)

    # Step 9: Display summary to console
    print("\n" + result.format_metadata())
    print_extraction_complete(syllables_path, metadata_path, DEFAULT_OUTPUT_DIR)
