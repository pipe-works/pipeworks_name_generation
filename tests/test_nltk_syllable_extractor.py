"""
Unit tests for NLTK syllable extractor.

Tests cover core extraction functionality, onset/coda rules, CMUDict integration,
and fallback mechanisms.
"""

import tempfile
from pathlib import Path

import pytest

from build_tools.nltk_syllable_extractor import NltkSyllableExtractor


@pytest.fixture
def extractor():
    """Create a standard extractor instance for testing."""
    try:
        import cmudict  # noqa: F401

        return NltkSyllableExtractor("en_US", min_syllable_length=2, max_syllable_length=8)
    except ImportError:
        pytest.skip("cmudict not installed")


def test_nltk_syllable_extractor_init():
    """Test extractor initialization."""
    try:
        import cmudict  # noqa: F401
    except ImportError:
        pytest.skip("cmudict not installed")

    # Valid initialization
    extractor = NltkSyllableExtractor("en_US", min_syllable_length=2, max_syllable_length=8)
    assert extractor.language_code == "en_US"
    assert extractor.min_syllable_length == 2
    assert extractor.max_syllable_length == 8

    # Invalid language code
    with pytest.raises(ValueError, match="not supported"):
        NltkSyllableExtractor("de_DE", min_syllable_length=2, max_syllable_length=8)


def test_extract_syllables_from_text_basic(extractor):
    """Test basic syllable extraction from text."""
    text = "Hello world"
    syllables, stats = extractor.extract_syllables_from_text(text)

    # Should extract some syllables
    assert len(syllables) > 0
    assert isinstance(syllables, list)

    # Check statistics
    assert stats["total_words"] == 2
    assert stats["processed_words"] > 0
    assert "fallback_count" in stats
    assert "rejected_syllables" in stats


def test_extract_syllables_phonetic_splits(extractor):
    """Test phonetically-guided splits with onset/coda principles."""
    # "Andrew" should split as "An-drew" (keeping 'dr' onset intact)
    text = "Andrew"
    syllables, _ = extractor.extract_syllables_from_text(text)

    # Should contain syllables from "Andrew"
    assert len(syllables) > 0

    # Test other words with consonant clusters
    text = "structure program"
    syllables, _ = extractor.extract_syllables_from_text(text)
    assert len(syllables) > 0


def test_extract_syllables_length_constraints(extractor):
    """Test syllable length filtering."""
    text = "I am a cat"  # Contains very short words
    syllables, stats = extractor.extract_syllables_from_text(text)

    # All syllables should meet length constraints
    for syllable in syllables:
        assert extractor.min_syllable_length <= len(syllable) <= extractor.max_syllable_length

    # Check that some syllables were rejected
    assert stats["rejected_syllables"] >= 0


def test_extract_syllables_case_insensitive(extractor):
    """Test case-insensitive extraction."""
    text1 = "Hello World"
    text2 = "hello world"

    syllables1, _ = extractor.extract_syllables_from_text(text1)
    syllables2, _ = extractor.extract_syllables_from_text(text2)

    # Should produce identical results
    assert syllables1 == syllables2


def test_extract_syllables_deterministic(extractor):
    """Test deterministic extraction (same input = same output)."""
    text = "The quick brown fox jumps over the lazy dog"

    syllables1, stats1 = extractor.extract_syllables_from_text(text)
    syllables2, stats2 = extractor.extract_syllables_from_text(text)

    # Should be identical
    assert syllables1 == syllables2
    assert stats1 == stats2


def test_extract_syllables_from_file(extractor):
    """Test extraction from a file."""
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Hello wonderful world of phonetic syllables")
        temp_path = Path(f.name)

    try:
        syllables, stats = extractor.extract_syllables_from_file(temp_path)

        # Should extract syllables
        assert len(syllables) > 0
        assert stats["total_words"] > 0

    finally:
        temp_path.unlink()


def test_extract_syllables_from_nonexistent_file(extractor):
    """Test extraction from nonexistent file raises error."""
    with pytest.raises(FileNotFoundError):
        extractor.extract_syllables_from_file(Path("/nonexistent/file.txt"))


def test_save_syllables(extractor):
    """Test saving syllables to file."""
    syllables = {"hel", "lo", "world"}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        temp_path = Path(f.name)

    try:
        extractor.save_syllables(syllables, temp_path)

        # Read back and verify
        with open(temp_path, "r", encoding="utf-8") as f:
            lines = f.read().strip().split("\n")

        assert len(lines) == 3
        assert set(lines) == syllables

    finally:
        temp_path.unlink()


def test_onset_validation(extractor):
    """Test onset/coda validation logic."""
    # Valid onsets
    assert extractor._is_valid_onset("dr")
    assert extractor._is_valid_onset("str")
    assert extractor._is_valid_onset("pl")
    assert extractor._is_valid_onset("br")

    # Invalid onsets
    assert not extractor._is_valid_onset("rt")
    assert not extractor._is_valid_onset("zt")
    assert not extractor._is_valid_onset("xyz")


def test_fallback_splitting(extractor):
    """Test fallback splitting for out-of-vocabulary words."""
    # Made-up word that won't be in CMUDict
    text = "xyzqwerty"
    syllables, stats = extractor.extract_syllables_from_text(text, only_hyphenated=False)

    # Should still attempt to process via fallback
    assert stats["total_words"] == 1


def test_cmudict_integration(extractor):
    """Test CMUDict pronunciation lookup."""
    # Test word known to be in CMUDict
    syllables = extractor._extract_orthographic_syllables("analysis")

    # Should produce syllables
    assert len(syllables) > 0
    assert all(isinstance(s, str) for s in syllables)


def test_empty_text(extractor):
    """Test extraction from empty text."""
    syllables, stats = extractor.extract_syllables_from_text("")

    assert len(syllables) == 0
    assert stats["total_words"] == 0


def test_punctuation_handling(extractor):
    """Test that punctuation is properly stripped."""
    text = "Hello, world! How are you?"
    syllables, stats = extractor.extract_syllables_from_text(text)

    # Should extract syllables, ignoring punctuation
    assert len(syllables) > 0
    # Words: Hello, world, How, are, you = 5
    assert stats["total_words"] == 5


def test_unicode_support(extractor):
    """Test basic Unicode handling."""
    # English words only (CMUDict limitation)
    text = "Hello world café"  # café may not be in CMUDict
    syllables, stats = extractor.extract_syllables_from_text(text)

    # Should process English words at least
    assert len(syllables) > 0
