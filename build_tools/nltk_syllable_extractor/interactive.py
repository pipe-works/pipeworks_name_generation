"""
Interactive mode for the NLTK syllable extractor.

This module provides the interactive CLI workflow for single-file extraction
using NLTK's CMU Pronouncing Dictionary. Unlike the pyphen extractor, this
tool only supports English (CMUDict limitation).
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

from .extractor import NltkSyllableExtractor
from .file_io import DEFAULT_OUTPUT_DIR, generate_output_filename, save_metadata
from .models import ExtractionResult

# Version for ledger
try:
    from build_tools.nltk_syllable_extractor import __version__ as _extractor_version
except (ImportError, AttributeError):
    _extractor_version = "unknown"


def run_interactive() -> None:
    """
    Interactive mode entry point for the NLTK syllable extractor CLI.

    Workflow:
        1. Display tool information and CMUDict notice
        2. Configure extraction parameters (min/max syllable length)
        3. Prompt for input file path
        4. Extract syllables using CMUDict + onset/coda principles
        5. Generate timestamped output filenames
        6. Save syllables and metadata to separate files
        7. Display summary to console

    Output Files:
        - YYYYMMDD_HHMMSS.syllables.en_US.txt: One syllable per line, sorted
        - YYYYMMDD_HHMMSS.meta.en_US.txt: Extraction metadata and statistics

    Both files are saved to _working/output/ by default.
    """
    # Display banner
    print_banner(
        "NLTK SYLLABLE EXTRACTOR",
        [
            "This tool extracts syllables using NLTK's CMU Pronouncing Dictionary",
            "with phonetically-guided orthographic splitting (onset/coda principles).",
            "",
            "⚠️  English only (CMUDict limitation)",
            "Output is saved to _working/output/ by default.",
        ],
    )

    # Configure extraction parameters
    print_section("EXTRACTION SETTINGS")
    min_len, max_len = prompt_extraction_settings(
        default_min=1,
        default_max=999,
        min_label="Minimum syllable length (1 = no filtering)",
        max_label="Maximum syllable length (999 = no filtering)",
    )

    # Initialize extractor
    try:
        extractor = NltkSyllableExtractor("en_US", min_len, max_len)
        print("✓ CMU Pronouncing Dictionary loaded")
    except (ImportError, LookupError) as e:
        print(f"\nError: {e}")
        sys.exit(1)

    # Get input file path
    print_section("INPUT FILE SELECTION")
    input_path = prompt_input_file()

    # Use ledger context for corpus DB integration
    with ExtractionLedgerContext(
        extractor_tool="nltk_syllable_extractor",
        extractor_version=_extractor_version,
        pyphen_lang=None,  # Not applicable for NLTK
        min_len=min_len,
        max_len=max_len,
    ) as ledger_ctx:
        # Record input
        ledger_ctx.record_input(input_path)

        # Extract syllables
        print(f"\n⏳ Processing {input_path}...")
        try:
            syllables, stats = extractor.extract_syllables_from_file(input_path)
            print(f"✓ Extracted {len(syllables)} unique syllables")
        except Exception as e:
            print(f"\nError during extraction: {e}")
            ledger_ctx.set_result(success=False)
            sys.exit(1)

        # Generate output filenames and create result object
        syllables_path, metadata_path = generate_output_filename(language_code="en_US")

        result = ExtractionResult(
            syllables=syllables,
            language_code="en_US",
            min_syllable_length=min_len,
            max_syllable_length=max_len,
            input_path=input_path,
            only_hyphenated=True,
            total_words=stats["total_words"],
            fallback_count=stats["fallback_count"],
            rejected_syllables=stats["rejected_syllables"],
            processed_words=stats["processed_words"],
        )

        # Save syllables
        print(f"\n⏳ Saving syllables to {syllables_path}...")
        try:
            extractor.save_syllables(syllables, syllables_path)
            print("✓ Syllables saved successfully")
        except Exception as e:
            print(f"\nError saving syllables: {e}")
            ledger_ctx.set_result(success=False)
            sys.exit(1)

        # Save metadata
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

    # Display summary to console
    print("\n" + result.format_metadata())
    print_extraction_complete(syllables_path, metadata_path, DEFAULT_OUTPUT_DIR)
