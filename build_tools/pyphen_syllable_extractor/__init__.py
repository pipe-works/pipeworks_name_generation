"""
Syllable Extractor - Dictionary-Based Syllable Extraction

The syllable extractor uses dictionary-based hyphenation to extract syllables from text files.
This is a **build-time tool only** - not used during runtime name generation.

The tool supports two modes:

- **Interactive Mode** - Guided prompts for single-file processing
- **Batch Mode** - Automated processing of multiple files via command-line arguments

Features:

- Dictionary-based hyphenation using pyphen (LibreOffice dictionaries)
- Support for 40+ languages
- Automatic language detection (optional, via langdetect)
- Configurable syllable length constraints
- Deterministic extraction (same input = same output)
- Unicode support for accented characters
- Comprehensive metadata and statistics
- Automatic provenance tracking via corpus_db ledger (batch mode)

Main Components:

- SyllableExtractor: Core extraction class
- ExtractionResult: Data model for extraction results
- FileProcessingResult: Result for single file in batch mode
- BatchResult: Aggregate results for batch processing
- SUPPORTED_LANGUAGES: Dictionary of supported language codes

Usage:
    >>> from pathlib import Path
    >>> from build_tools.pyphen_syllable_extractor import SyllableExtractor
    >>>
    >>> # Initialize extractor for English (US)
    >>> extractor = SyllableExtractor('en_US', min_syllable_length=2, max_syllable_length=8)
    >>>
    >>> # Extract syllables from text
    >>> syllables = extractor.extract_syllables_from_text("Hello wonderful world")
    >>> print(sorted(syllables))
    ['der', 'ful', 'hel', 'lo', 'won', 'world']
    >>>
    >>> # Extract from a file
    >>> syllables = extractor.extract_syllables_from_file(Path('input.txt'))
    >>>
    >>> # Save results
    >>> extractor.save_syllables(syllables, Path('output.txt'))

CLI Usage:

    .. code-block:: bash

       # Interactive mode
       python -m build_tools.pyphen_syllable_extractor

       # Single file with specific language
       python -m build_tools.pyphen_syllable_extractor --file input.txt --lang en_US

       # Batch processing with auto-detection
       python -m build_tools.pyphen_syllable_extractor --source ~/docs/ --recursive --auto
"""

# CLI entry point (for python -m usage)
# Shared utilities (re-exported for backwards compatibility)
from build_tools.tui_common.cli_utils import discover_files

# Interactive and batch modes
from .batch import process_batch, process_single_file, run_batch
from .cli import main

# Core extraction functionality
from .extractor import SyllableExtractor

# File I/O operations
from .file_io import DEFAULT_OUTPUT_DIR, generate_output_filename, save_metadata
from .interactive import run_interactive, select_language

# Language detection (optional - requires langdetect)
from .language_detection import (
    detect_language_code,
    get_alternative_locales,
    get_default_locale,
    is_detection_available,
    list_supported_languages,
)

# Language configuration
from .languages import (
    SUPPORTED_LANGUAGES,
    get_language_code,
    get_language_name,
    validate_language_code,
)

# Data models
from .models import BatchResult, ExtractionResult, FileProcessingResult

# Backwards compatibility aliases (deprecated, use new names)
main_interactive = run_interactive
main_batch = run_batch
process_single_file_batch = process_single_file

__all__ = [
    # Core classes
    "SyllableExtractor",
    "ExtractionResult",
    "FileProcessingResult",
    "BatchResult",
    # Language utilities
    "SUPPORTED_LANGUAGES",
    "get_language_code",
    "get_language_name",
    "validate_language_code",
    # Language detection (optional)
    "detect_language_code",
    "is_detection_available",
    "get_alternative_locales",
    "get_default_locale",
    "list_supported_languages",
    # File I/O
    "DEFAULT_OUTPUT_DIR",
    "generate_output_filename",
    "save_metadata",
    # CLI - Interactive and Batch
    "main",
    "run_interactive",
    "run_batch",
    "select_language",
    # Batch processing utilities
    "discover_files",
    "process_single_file",
    "process_batch",
    # Backwards compatibility (deprecated)
    "main_interactive",
    "main_batch",
    "process_single_file_batch",
]

__version__ = "0.1.0"
