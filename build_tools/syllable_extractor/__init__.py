"""
Syllable extraction toolkit for phonetic name generation.

This package provides tools for extracting syllables from text files using
dictionary-based hyphenation via pyphen's LibreOffice dictionaries.

Main Components:
    - SyllableExtractor: Core extraction class
    - ExtractionResult: Data model for extraction results
    - SUPPORTED_LANGUAGES: Dictionary of supported language codes
    - CLI functions: Interactive command-line interface

Usage:
    # Programmatic usage
    from build_tools.syllable_extractor import SyllableExtractor

    extractor = SyllableExtractor('en_US', min_syllable_length=2, max_syllable_length=8)
    syllables = extractor.extract_syllables_from_text("Hello world")

    # CLI usage
    python -m build_tools.syllable_extractor
"""

# CLI entry point (for python -m usage)
from .cli import main

# Core extraction functionality
from .extractor import SyllableExtractor

# File I/O operations
from .file_io import DEFAULT_OUTPUT_DIR, generate_output_filename, save_metadata

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
from .models import ExtractionResult

__all__ = [
    # Core classes
    "SyllableExtractor",
    "ExtractionResult",
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
    # CLI
    "main",
]

__version__ = "0.1.0"
