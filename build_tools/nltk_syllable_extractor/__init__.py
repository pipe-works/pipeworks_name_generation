"""
NLTK Syllable Extractor - Phonetically-Guided Syllable Extraction

The NLTK syllable extractor uses CMU Pronouncing Dictionary (via cmudict pip package)
with onset/coda principles for phonetically-guided orthographic syllabification.
This is a **build-time tool only** - not used during runtime name generation.

The tool supports two modes:

- **Interactive Mode** - Guided prompts for single-file processing
- **Batch Mode** - Automated processing of multiple files via command-line arguments

Features:

- Phonetically-guided syllabification using CMU Pronouncing Dictionary (via cmudict package)
- Onset/coda principles for natural consonant cluster splitting
- English only (CMUDict limitation)
- Preserves all syllables including duplicates (extraction only, no filtering)
- Configurable syllable length constraints (defaults to no filtering)
- Deterministic extraction (same input = same output)
- Unicode support
- Comprehensive metadata and statistics
- Automatic provenance tracking via corpus_db ledger (batch mode)

Key Differences from pyphen Extractor:

- Uses phonetic information (CMUDict) rather than typographic hyphenation rules
- Respects phonotactic constraints via onset/coda principles
- Produces more "natural" phonetic splits (e.g., "Andrew" → "An-drew" not "And-rew")
- English only vs pyphen's 40+ languages
- Complementary tool, not a replacement

Main Components:

- NltkSyllableExtractor: Core extraction class
- ExtractionResult: Data model for extraction results
- FileProcessingResult: Result for single file in batch mode
- BatchResult: Aggregate results for batch processing

Usage:
    >>> from pathlib import Path
    >>> from build_tools.nltk_syllable_extractor import NltkSyllableExtractor
    >>>
    >>> # Initialize extractor for English (defaults to no length filtering)
    >>> extractor = NltkSyllableExtractor('en_US')
    >>>
    >>> # Extract syllables from text (preserves duplicates)
    >>> syllables, stats = extractor.extract_syllables_from_text("Hello wonderful world")
    >>> print(syllables)  # Note: includes all syllables with duplicates
    ['hel', 'lo', 'won', 'der', 'ful', 'world']
    >>> print(f"Total: {len(syllables)}, Unique: {len(set(syllables))}")
    Total: 6, Unique: 6
    >>>
    >>> # Extract from a file
    >>> syllables, stats = extractor.extract_syllables_from_file(Path('input.txt'))
    >>>
    >>> # Save results (preserves duplicates)
    >>> extractor.save_syllables(syllables, Path('output.txt'))

CLI Usage:

    .. code-block:: bash

       # Interactive mode
       python -m build_tools.nltk_syllable_extractor

       # Single file
       python -m build_tools.nltk_syllable_extractor --file input.txt

       # Batch processing
       python -m build_tools.nltk_syllable_extractor --source ~/docs/ --recursive
"""

# CLI entry point (for python -m usage)
# Shared utilities (re-exported for backwards compatibility)
from build_tools.tui_common.cli_utils import discover_files

# Interactive and batch modes
from .batch import process_batch, process_single_file, run_batch
from .cli import main

# Core extraction functionality
from .extractor import NltkSyllableExtractor

# File I/O operations
from .file_io import DEFAULT_OUTPUT_DIR, generate_output_filename, save_metadata
from .interactive import run_interactive

# Data models
from .models import BatchResult, ExtractionResult, FileProcessingResult

# Backwards compatibility aliases (deprecated, use new names)
main_interactive = run_interactive
main_batch = run_batch
process_single_file_batch = process_single_file

__all__ = [
    # Core classes
    "NltkSyllableExtractor",
    "ExtractionResult",
    "FileProcessingResult",
    "BatchResult",
    # File I/O
    "DEFAULT_OUTPUT_DIR",
    "generate_output_filename",
    "save_metadata",
    # CLI - Interactive and Batch
    "main",
    "run_interactive",
    "run_batch",
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
