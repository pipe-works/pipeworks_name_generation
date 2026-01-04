"""
Build-time tools for pipeworks_name_generation.

This package contains tools for analyzing corpora and generating phonetic
pattern data. These tools are NOT runtime dependencies - they're used during
development to prepare data files.

Tools:
- syllable_extractor: Extract syllables from text using pyphen hyphenation
"""

__all__ = ['syllable_extractor']
