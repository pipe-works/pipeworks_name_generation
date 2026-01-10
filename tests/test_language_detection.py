"""
Comprehensive test suite for language auto-detection functionality.

This module tests the language_detection module, including:
- ISO code to pyphen locale mapping
- Auto-detection with various languages
- Error handling and fallbacks
- Integration with SyllableExtractor
"""

import warnings
from pathlib import Path

import pytest

from build_tools.pyphen_syllable_extractor import (
    SyllableExtractor,
    detect_language_code,
    get_alternative_locales,
    get_default_locale,
    is_detection_available,
    list_supported_languages,
)


class TestLanguageDetectionAvailability:
    """Test suite for checking language detection availability."""

    def test_is_detection_available(self):
        """Test that language detection is available after installing langdetect."""
        assert is_detection_available() is True

    def test_list_supported_languages(self):
        """Test that list_supported_languages returns a dictionary."""
        langs = list_supported_languages()
        assert isinstance(langs, dict)
        assert len(langs) > 30  # Should have 40+ languages
        assert "en" in langs
        assert "de" in langs
        assert "fr" in langs


class TestLanguageCodeMapping:
    """Test suite for ISO to pyphen language code mapping."""

    def test_get_default_locale_english(self):
        """Test default locale for English."""
        assert get_default_locale("en") == "en_US"

    def test_get_default_locale_german(self):
        """Test default locale for German."""
        assert get_default_locale("de") == "de_DE"

    def test_get_default_locale_french(self):
        """Test default locale for French."""
        assert get_default_locale("fr") == "fr"

    def test_get_default_locale_portuguese(self):
        """Test default locale for Portuguese."""
        assert get_default_locale("pt") == "pt_PT"

    def test_get_default_locale_unknown(self):
        """Test that unknown language returns None."""
        assert get_default_locale("xx") is None
        assert get_default_locale("zz") is None

    def test_get_alternative_locales_english(self):
        """Test alternative locales for English."""
        alternatives = get_alternative_locales("en")
        assert alternatives is not None
        assert "en_US" in alternatives
        assert "en_GB" in alternatives
        assert len(alternatives) == 2

    def test_get_alternative_locales_german(self):
        """Test alternative locales for German."""
        alternatives = get_alternative_locales("de")
        assert alternatives is not None
        assert "de_DE" in alternatives
        assert "de_AT" in alternatives
        assert "de_CH" in alternatives
        assert len(alternatives) == 3

    def test_get_alternative_locales_portuguese(self):
        """Test alternative locales for Portuguese."""
        alternatives = get_alternative_locales("pt")
        assert alternatives is not None
        assert "pt_PT" in alternatives
        assert "pt_BR" in alternatives

    def test_get_alternative_locales_no_alternatives(self):
        """Test language with only one locale."""
        # French has only one variant in pyphen
        alternatives = get_alternative_locales("fr")
        assert alternatives is None

    def test_get_alternative_locales_unknown(self):
        """Test that unknown language returns None."""
        alternatives = get_alternative_locales("xx")
        assert alternatives is None


class TestLanguageDetection:
    """Test suite for auto-detection functionality."""

    def test_detect_english_text(self):
        """Test detection of English text."""
        text = "Hello world, this is a test of language detection functionality"
        code = detect_language_code(text)
        assert code == "en_US"

    def test_detect_german_text(self):
        """Test detection of German text."""
        text = "Hallo Welt, dies wird ein Test der Spracherkennung und funktioniert sehr gut"
        code = detect_language_code(text)
        assert code == "de_DE"

    def test_detect_french_text(self):
        """Test detection of French text."""
        text = "Bonjour le monde, comment allez-vous aujourd'hui? Très bien merci"
        code = detect_language_code(text)
        assert code == "fr"

    def test_detect_spanish_text(self):
        """Test detection of Spanish text."""
        text = "Hola mundo, este es una prueba de detección de idioma"
        code = detect_language_code(text)
        assert code == "es"

    def test_detect_italian_text(self):
        """Test detection of Italian text."""
        text = "Ciao mondo, questo è un test di rilevamento della lingua"
        code = detect_language_code(text)
        assert code == "it_IT"

    def test_detect_portuguese_text(self):
        """Test detection of Portuguese text."""
        text = "Olá mundo, este é um teste de detecção de idioma que funciona bem"
        code = detect_language_code(text)
        assert code == "pt_PT"

    def test_detect_dutch_text(self):
        """Test detection of Dutch text.

        Note: langdetect may return Afrikaans (af_ZA) for Dutch text
        since they're linguistically similar. We accept both.
        """
        text = "Hallo wereld, dit is een test van taaldetectie die goed werkt"
        code = detect_language_code(text)
        # Accept Dutch or Afrikaans (linguistically similar, langdetect can confuse them)
        assert code in ("nl_NL", "af_ZA"), f"Expected nl_NL or af_ZA, got {code}"

    def test_detect_russian_text(self):
        """Test detection of Russian text."""
        text = "Привет мир, это тест определения языка который работает хорошо"
        code = detect_language_code(text)
        assert code == "ru_RU"

    def test_short_text_uses_default(self):
        """Test that short text returns default language with warning."""
        text = "Hi"
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            code = detect_language_code(text, default="de_DE")
            assert code == "de_DE"
            assert len(w) == 1
            assert "too short" in str(w[0].message).lower()

    def test_empty_text_uses_default(self):
        """Test that empty text returns default."""
        text = ""
        code = detect_language_code(text, default="en_US")
        assert code == "en_US"

    def test_custom_default_language(self):
        """Test using custom default language."""
        text = "x"  # Too short
        code = detect_language_code(text, default="fr")
        assert code == "fr"

    def test_custom_min_confidence_length(self):
        """Test custom minimum text length."""
        text = "Hello world beautiful"  # 21 chars
        # With high minimum, should use default
        code = detect_language_code(text, min_confidence_length=50, default="de_DE")
        assert code == "de_DE"

        # With low minimum, should detect (longer text for reliability)
        long_text = "Hello world this is a longer text for better detection"
        code = detect_language_code(long_text, min_confidence_length=10, default="de_DE")
        assert code == "en_US"

    def test_suppress_warnings(self):
        """Test suppressing warnings."""
        text = "Hi"
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            code = detect_language_code(text, suppress_warnings=True)
            assert code == "en_US"
            assert len(w) == 0  # No warnings

    def test_unsupported_detected_language_uses_default(self):
        """Test that unsupported detected language falls back to default."""
        # Use text in a language not supported by pyphen (e.g., Chinese)
        text = "这是一个测试文本用于语言检测功能的测试和验证"
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            code = detect_language_code(text, default="en_US")
            # Should fall back to default since Chinese is not in pyphen
            assert code == "en_US"


class TestSyllableExtractorIntegration:
    """Test suite for integration with SyllableExtractor."""

    def test_extract_with_auto_language_english(self):
        """Test auto-detection with English text extraction."""
        text = "Hello beautiful wonderful world, this is absolutely magnificent"
        syllables, stats, lang = SyllableExtractor.extract_with_auto_language(text)

        assert lang == "en_US"
        assert isinstance(syllables, set)
        assert len(syllables) > 0
        assert isinstance(stats, dict)
        assert stats["total_words"] == 8  # 8 words in the text

    def test_extract_with_auto_language_german(self):
        """Test auto-detection with German text extraction."""
        text = "Hallo Welt, dies wird ein wunderbare Test der Spracherkennung und Silbentrennung"
        syllables, stats, lang = SyllableExtractor.extract_with_auto_language(text)

        assert lang == "de_DE"
        assert isinstance(syllables, set)
        assert len(syllables) > 0

    def test_extract_with_auto_language_french(self):
        """Test auto-detection with French text extraction."""
        text = "Bonjour le monde merveilleux, comment allez-vous aujourd'hui?"
        syllables, stats, lang = SyllableExtractor.extract_with_auto_language(text)

        assert lang == "fr"
        assert isinstance(syllables, set)
        assert len(syllables) > 0

    def test_extract_with_custom_parameters(self):
        """Test auto-detection with custom parameters."""
        text = "Hello beautiful wonderful world magnificently spectacular"
        syllables, stats, lang = SyllableExtractor.extract_with_auto_language(
            text, min_syllable_length=3, max_syllable_length=6, only_hyphenated=True
        )

        assert lang == "en_US"
        # All syllables should respect length constraints
        for syll in syllables:
            assert 3 <= len(syll) <= 6

    def test_extract_with_custom_default_language(self):
        """Test auto-detection with custom default language."""
        text = "x"  # Too short, will use default
        syllables, stats, lang = SyllableExtractor.extract_with_auto_language(
            text, default_language="de_DE", suppress_warnings=True
        )

        assert lang == "de_DE"

    def test_extract_file_with_auto_language(self, tmp_path):
        """Test auto-detection from file."""
        # Create test file with English text
        test_file = tmp_path / "test_english.txt"
        test_file.write_text(
            "Hello beautiful wonderful world, this is a test of file extraction",
            encoding="utf-8",
        )

        syllables, stats, lang = SyllableExtractor.extract_file_with_auto_language(test_file)

        assert lang == "en_US"
        assert isinstance(syllables, set)
        assert len(syllables) > 0
        assert stats["total_words"] == 11

    def test_extract_file_with_auto_language_german(self, tmp_path):
        """Test auto-detection from German file."""
        test_file = tmp_path / "test_german.txt"
        test_file.write_text(
            "Hallo Welt, dies wird ein wunderbarer Test der Spracherkennung und Silbentrennung",
            encoding="utf-8",
        )

        syllables, stats, lang = SyllableExtractor.extract_file_with_auto_language(
            test_file, min_syllable_length=2, max_syllable_length=8
        )

        assert lang == "de_DE"
        assert isinstance(syllables, set)
        for syll in syllables:
            assert 2 <= len(syll) <= 8

    def test_extract_file_nonexistent(self):
        """Test that nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            SyllableExtractor.extract_file_with_auto_language(Path("/nonexistent/file.txt"))


class TestEdgeCases:
    """Test suite for edge cases and error conditions."""

    def test_detection_with_numbers_and_punctuation(self):
        """Test detection with mixed content."""
        text = "Hello123 world!!! How are you??? 456 test test test"
        code = detect_language_code(text)
        assert code == "en_US"  # Should still detect English

    def test_detection_with_urls(self):
        """Test detection with URLs in text."""
        text = "Visit https://example.com for more information about this wonderful website"
        code = detect_language_code(text)
        assert code == "en_US"

    def test_very_long_text(self):
        """Test detection with very long text."""
        text = " ".join(["Hello beautiful world"] * 100)
        code = detect_language_code(text)
        assert code == "en_US"

    def test_mixed_language_text(self):
        """Test detection with mixed languages (unpredictable)."""
        text = "Hello world Bonjour monde Hallo Welt"
        # Mixed language detection is unreliable, just verify it returns something valid
        code = detect_language_code(text)
        assert isinstance(code, str)
        assert len(code) > 0

    def test_whitespace_only_text(self):
        """Test detection with only whitespace."""
        text = "   \n\n\t\t   "
        code = detect_language_code(text, default="en_US")
        assert code == "en_US"  # Should use default

    def test_special_characters_only(self):
        """Test detection with only special characters."""
        text = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        code = detect_language_code(text, default="en_US")
        assert code == "en_US"  # Should use default


class TestDeterminism:
    """Test suite for deterministic behavior."""

    def test_detection_consistency(self):
        """Test that detection is consistent for the same text."""
        text = "Hello beautiful wonderful world, this is a test"
        results = [detect_language_code(text) for _ in range(5)]
        # langdetect has some randomness, but for long enough text it should be stable
        # Most results should be the same
        assert results.count("en_US") >= 4

    def test_extraction_consistency(self):
        """Test that extraction with auto-detection is consistent."""
        text = "Hello beautiful wonderful world magnificently spectacular"
        results = [
            SyllableExtractor.extract_with_auto_language(text, suppress_warnings=True)
            for _ in range(3)
        ]

        # All should detect same language
        langs = [r[2] for r in results]
        assert all(lang == "en_US" for lang in langs)

        # All should extract same syllables
        syllable_sets = [r[0] for r in results]
        assert all(s == syllable_sets[0] for s in syllable_sets)


class TestDocumentationExamples:
    """Test suite verifying that documentation examples work correctly."""

    def test_example_from_docstring(self):
        """Test the main example from detect_language_code docstring."""
        text = "Hello world, this is a test of language detection functionality"
        code = detect_language_code(text)
        assert code == "en_US"

    def test_french_example(self):
        """Test French detection example."""
        text = "Bonjour le monde, comment allez-vous aujourd'hui? Très bien merci"
        code = detect_language_code(text)
        assert code == "fr"

    def test_custom_default_example(self):
        """Test custom default example."""
        code = detect_language_code("x", default="de_DE", suppress_warnings=True)
        assert code == "de_DE"

    def test_alternative_locales_example(self):
        """Test alternative locales example."""
        alternatives = get_alternative_locales("en")
        assert alternatives is not None
        assert "en_US" in alternatives
        assert "en_GB" in alternatives
