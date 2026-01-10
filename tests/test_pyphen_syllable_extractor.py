"""
Comprehensive test suite for the syllable_extractor build tool.

This module tests all functionality of the syllable extractor including:
- SyllableExtractor class initialization and configuration
- Syllable extraction from text and files
- ExtractionResult dataclass and metadata formatting
- Output file generation and saving
- Error handling and edge cases

Note: These tests require pyphen to be installed (build-time dependency only).
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

from build_tools.pyphen_syllable_extractor import (
    DEFAULT_OUTPUT_DIR,
    SUPPORTED_LANGUAGES,
    ExtractionResult,
    SyllableExtractor,
    generate_output_filename,
    save_metadata,
)


class TestSyllableExtractor:
    """Test suite for the SyllableExtractor class."""

    def test_init_valid_language(self):
        """Test initialization with a valid language code."""
        extractor = SyllableExtractor("en_US")
        assert extractor.language_code == "en_US"
        assert extractor.min_syllable_length == 1
        assert extractor.max_syllable_length == 10

    def test_init_custom_length_constraints(self):
        """Test initialization with custom syllable length constraints."""
        extractor = SyllableExtractor("en_US", min_syllable_length=2, max_syllable_length=8)
        assert extractor.min_syllable_length == 2
        assert extractor.max_syllable_length == 8

    def test_init_invalid_language(self):
        """Test initialization with an invalid language code raises ValueError."""
        with pytest.raises(ValueError, match="not supported by pyphen"):
            SyllableExtractor("invalid_language_code")

    def test_extract_syllables_from_simple_text(self):
        """Test extracting syllables from simple English text."""
        extractor = SyllableExtractor("en_US", min_syllable_length=2, max_syllable_length=8)
        text = "hello world beautiful wonderful"

        syllables, _ = extractor.extract_syllables_from_text(text)

        # Check that we got some syllables back
        assert isinstance(syllables, set)
        assert len(syllables) > 0

        # All syllables should be lowercase
        for syll in syllables:
            assert syll.islower()

        # All syllables should respect length constraints
        for syll in syllables:
            assert 2 <= len(syll) <= 8

    def test_extract_syllables_respects_min_length(self):
        """Test that minimum syllable length constraint is enforced."""
        extractor = SyllableExtractor("en_US", min_syllable_length=3, max_syllable_length=10)
        text = "I am a big dog"  # "I" and "a" are single letters

        syllables, _ = extractor.extract_syllables_from_text(text)

        # No syllables should be shorter than 3 characters
        for syll in syllables:
            assert len(syll) >= 3

    def test_extract_syllables_respects_max_length(self):
        """Test that maximum syllable length constraint is enforced."""
        extractor = SyllableExtractor("en_US", min_syllable_length=1, max_syllable_length=3)
        text = "extraordinarily beautiful"  # Long words with long syllables

        syllables, _ = extractor.extract_syllables_from_text(text)

        # No syllables should be longer than 3 characters
        for syll in syllables:
            assert len(syll) <= 3

    def test_extract_syllables_only_hyphenated_true(self):
        """Test that only_hyphenated=True excludes non-hyphenated words."""
        extractor = SyllableExtractor("en_US", min_syllable_length=1, max_syllable_length=10)
        text = "hello a I"  # "a" and "I" likely won't be hyphenated

        syllables_hyphenated, _ = extractor.extract_syllables_from_text(text, only_hyphenated=True)
        syllables_all, _ = extractor.extract_syllables_from_text(text, only_hyphenated=False)

        # With only_hyphenated=False, we should get more or equal syllables
        assert len(syllables_all) >= len(syllables_hyphenated)

    def test_extract_syllables_from_empty_text(self):
        """Test extracting syllables from empty text returns empty set."""
        extractor = SyllableExtractor("en_US")
        syllables, _ = extractor.extract_syllables_from_text("")
        assert syllables == set()

    def test_extract_syllables_removes_punctuation(self):
        """Test that punctuation is properly removed from text."""
        extractor = SyllableExtractor("en_US", min_syllable_length=2, max_syllable_length=10)
        text = "Hello, world! How are you? Fine."

        syllables, _ = extractor.extract_syllables_from_text(text)

        # No syllables should contain punctuation
        for syll in syllables:
            assert syll.isalpha()

    def test_extract_syllables_case_insensitive(self):
        """Test that extraction is case-insensitive."""
        extractor = SyllableExtractor("en_US", min_syllable_length=2, max_syllable_length=10)

        syllables_lower, _ = extractor.extract_syllables_from_text("hello world")
        syllables_upper, _ = extractor.extract_syllables_from_text("HELLO WORLD")
        syllables_mixed, _ = extractor.extract_syllables_from_text("HeLLo WoRLd")

        # All three should produce identical results
        assert syllables_lower == syllables_upper == syllables_mixed

    def test_extract_syllables_from_file(self, tmp_path):
        """Test extracting syllables from a file."""
        # Create a temporary test file
        test_file = tmp_path / "test_input.txt"
        test_file.write_text("hello beautiful wonderful world", encoding="utf-8")

        extractor = SyllableExtractor("en_US", min_syllable_length=2, max_syllable_length=8)
        syllables, _ = extractor.extract_syllables_from_file(test_file)

        assert isinstance(syllables, set)
        assert len(syllables) > 0

    def test_extract_syllables_from_nonexistent_file(self):
        """Test that extracting from nonexistent file raises FileNotFoundError."""
        extractor = SyllableExtractor("en_US")
        nonexistent_path = Path("/nonexistent/path/file.txt")

        with pytest.raises(FileNotFoundError):
            extractor.extract_syllables_from_file(nonexistent_path)

    def test_save_syllables(self, tmp_path):
        """Test saving syllables to a file."""
        output_file = tmp_path / "syllables.txt"
        test_syllables = {"hello", "world", "test", "alpha"}

        extractor = SyllableExtractor("en_US")
        extractor.save_syllables(test_syllables, output_file)

        # Verify file was created
        assert output_file.exists()

        # Verify contents are sorted, one per line
        content = output_file.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        assert len(lines) == len(test_syllables)
        assert lines == sorted(test_syllables)

    def test_save_empty_syllables(self, tmp_path):
        """Test saving an empty set of syllables."""
        output_file = tmp_path / "empty.txt"
        extractor = SyllableExtractor("en_US")
        extractor.save_syllables(set(), output_file)

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert content == ""

    def test_multiple_languages(self):
        """Test that multiple language codes work correctly."""
        # Test a few different languages
        test_languages = ["en_US", "de_DE", "fr", "es"]

        for lang_code in test_languages:
            if lang_code not in [code for code in SUPPORTED_LANGUAGES.values()]:
                continue

            extractor = SyllableExtractor(lang_code)
            assert extractor.language_code == lang_code

            # Test basic extraction
            syllables, _ = extractor.extract_syllables_from_text("hello world")
            assert isinstance(syllables, set)


class TestExtractionResult:
    """Test suite for the ExtractionResult dataclass."""

    def test_extraction_result_creation(self, tmp_path):
        """Test creating an ExtractionResult with all fields."""
        test_syllables = {"hel", "lo", "world", "test"}
        test_path = tmp_path / "input.txt"
        test_path.write_text("test content", encoding="utf-8")

        result = ExtractionResult(
            syllables=test_syllables,
            language_code="en_US",
            min_syllable_length=2,
            max_syllable_length=8,
            input_path=test_path,
        )

        assert result.syllables == test_syllables
        assert result.language_code == "en_US"
        assert result.min_syllable_length == 2
        assert result.max_syllable_length == 8
        assert result.input_path == test_path
        assert isinstance(result.timestamp, datetime)
        assert result.only_hyphenated is True

    def test_extraction_result_post_init_length_distribution(self):
        """Test that __post_init__ correctly calculates length distribution."""
        test_syllables = {"ab", "abc", "abcd", "abc", "ab"}  # Duplicates will be removed by set
        test_path = Path("test.txt")

        result = ExtractionResult(
            syllables=test_syllables,
            language_code="en_US",
            min_syllable_length=1,
            max_syllable_length=10,
            input_path=test_path,
        )

        # Should have counts for lengths 2, 3, and 4
        assert 2 in result.length_distribution
        assert 3 in result.length_distribution
        assert 4 in result.length_distribution

        # Check actual counts
        expected_distribution = {2: 1, 3: 1, 4: 1}  # One of each after set deduplication
        assert result.length_distribution == expected_distribution

    def test_extraction_result_sample_syllables(self):
        """Test that sample syllables are generated correctly."""
        # Create 20 syllables
        test_syllables = {f"syl{i:02d}" for i in range(20)}
        test_path = Path("test.txt")

        result = ExtractionResult(
            syllables=test_syllables,
            language_code="en_US",
            min_syllable_length=1,
            max_syllable_length=10,
            input_path=test_path,
        )

        # Should have exactly 15 samples (default limit)
        assert len(result.sample_syllables) == 15

        # Samples should be sorted
        assert result.sample_syllables == sorted(result.sample_syllables)

        # All samples should be from the original set
        assert all(syll in test_syllables for syll in result.sample_syllables)

    def test_extraction_result_sample_syllables_small_set(self):
        """Test sample syllables when set is smaller than sample size."""
        test_syllables = {"ab", "cd", "ef"}
        test_path = Path("test.txt")

        result = ExtractionResult(
            syllables=test_syllables,
            language_code="en_US",
            min_syllable_length=1,
            max_syllable_length=10,
            input_path=test_path,
        )

        # Should have all syllables since set is smaller than 15
        assert len(result.sample_syllables) == 3
        assert set(result.sample_syllables) == test_syllables

    def test_format_metadata(self, tmp_path):
        """Test formatting metadata as a string."""
        test_syllables = {"hello", "world", "test"}
        test_path = tmp_path / "input.txt"
        test_path.write_text("test", encoding="utf-8")

        result = ExtractionResult(
            syllables=test_syllables,
            language_code="en_US",
            min_syllable_length=2,
            max_syllable_length=8,
            input_path=test_path,
        )

        metadata_str = result.format_metadata()

        # Check that key information is present
        assert "SYLLABLE EXTRACTION METADATA" in metadata_str
        assert "en_US" in metadata_str
        assert "2-8 characters" in metadata_str
        assert str(test_path) in metadata_str
        assert "3" in metadata_str  # Number of syllables
        assert "Syllable Length Distribution:" in metadata_str
        assert "Sample Syllables" in metadata_str

    def test_format_metadata_with_empty_syllables(self, tmp_path):
        """Test formatting metadata when no syllables were extracted."""
        test_path = tmp_path / "input.txt"
        test_path.write_text("", encoding="utf-8")

        result = ExtractionResult(
            syllables=set(),
            language_code="en_US",
            min_syllable_length=2,
            max_syllable_length=8,
            input_path=test_path,
        )

        metadata_str = result.format_metadata()

        # Should still contain basic info
        assert "SYLLABLE EXTRACTION METADATA" in metadata_str
        assert "0" in metadata_str  # Zero syllables


class TestOutputFileGeneration:
    """Test suite for output file generation functions."""

    def test_generate_output_filename_default_dir(self):
        """Test generating output filenames with default directory."""
        syllables_path, metadata_path = generate_output_filename()

        # Check that paths are in run-based subdirectory structure
        # Structure: DEFAULT_OUTPUT_DIR/TIMESTAMP/syllables/filename.txt
        run_dir = syllables_path.parent.parent
        assert run_dir.parent == DEFAULT_OUTPUT_DIR
        assert syllables_path.parent.name == "syllables"
        assert metadata_path.parent.name == "meta"

        # Both should be in the same run directory
        assert syllables_path.parent.parent == metadata_path.parent.parent

        # Check default filename (no language code or input_filename)
        # Both use the same filename since they're in different subdirectories
        assert syllables_path.name == "syllables.txt"
        assert metadata_path.name == "syllables.txt"

        # Check run directory format (YYYYMMDD_HHMMSS_pyphen)
        dir_name = run_dir.name
        assert len(dir_name) == 22  # YYYYMMDD_HHMMSS_pyphen
        assert dir_name[8] == "_"  # First underscore
        assert dir_name[15:] == "_pyphen"  # Identifier suffix

    def test_generate_output_filename_custom_dir(self, tmp_path):
        """Test generating output filenames with custom directory."""
        custom_dir = tmp_path / "custom_output"

        syllables_path, metadata_path = generate_output_filename(custom_dir)

        # Check run-based structure under custom directory
        # Structure: custom_dir/TIMESTAMP/syllables/filename.txt
        run_dir = syllables_path.parent.parent
        assert run_dir.parent == custom_dir
        assert syllables_path.parent.name == "syllables"
        assert metadata_path.parent.name == "meta"

        # Check that directory structure was created
        assert custom_dir.exists()
        assert custom_dir.is_dir()
        assert run_dir.exists()
        assert run_dir.is_dir()

    def test_generate_output_filename_creates_directory(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        nonexistent_dir = tmp_path / "new_dir" / "nested_dir"
        assert not nonexistent_dir.exists()

        syllables_path, metadata_path = generate_output_filename(nonexistent_dir)

        # Directory should now exist
        assert nonexistent_dir.exists()
        assert nonexistent_dir.is_dir()

    def test_generate_output_filename_with_language_code(self, tmp_path):
        """Test generating output filenames with language code."""
        output_dir = tmp_path / "output"

        syllables_path, metadata_path = generate_output_filename(output_dir, language_code="en_US")

        # Check run-based structure
        # Structure: output_dir/TIMESTAMP/syllables/en_US.txt
        run_dir = syllables_path.parent.parent
        assert run_dir.parent == output_dir
        assert syllables_path.parent.name == "syllables"
        assert metadata_path.parent.name == "meta"

        # Both should be in the same run directory
        assert syllables_path.parent.parent == metadata_path.parent.parent

        # Check filename format includes language code
        assert syllables_path.name == "en_US.txt"
        assert metadata_path.name == "en_US.txt"

    def test_generate_output_filename_with_different_language_codes(self):
        """Test generating filenames with various language codes."""
        test_codes = ["de_DE", "fr", "es", "pt_BR", "ru_RU", "zh_CN"]

        for lang_code in test_codes:
            syllables_path, metadata_path = generate_output_filename(language_code=lang_code)

            # Check that language code is the filename
            assert syllables_path.name == f"{lang_code}.txt"
            assert metadata_path.name == f"{lang_code}.txt"

            # Check run-based structure
            assert syllables_path.parent.name == "syllables"
            assert metadata_path.parent.name == "meta"

    def test_generate_output_filename_without_language_code_backward_compatible(self):
        """Test that omitting language code uses default filenames."""
        syllables_path, metadata_path = generate_output_filename()

        # Without language code, both use same default filename (in different dirs)
        assert syllables_path.name == "syllables.txt"
        assert metadata_path.name == "syllables.txt"

        # Check run-based structure
        assert syllables_path.parent.name == "syllables"
        assert metadata_path.parent.name == "meta"

    def test_generate_output_filename_language_code_with_underscore(self):
        """Test handling of language codes with underscores (e.g., en_US, de_CH)."""
        syllables_path, metadata_path = generate_output_filename(language_code="en_US")

        # Verify underscore in language code is preserved in filename
        assert syllables_path.name == "en_US.txt"
        assert metadata_path.name == "en_US.txt"

        # Verify run-based structure
        assert syllables_path.parent.name == "syllables"
        assert metadata_path.parent.name == "meta"

    def test_save_metadata(self, tmp_path):
        """Test saving metadata to a file."""
        test_syllables = {"hello", "world"}
        test_input_path = tmp_path / "input.txt"
        test_input_path.write_text("test", encoding="utf-8")

        result = ExtractionResult(
            syllables=test_syllables,
            language_code="en_US",
            min_syllable_length=2,
            max_syllable_length=8,
            input_path=test_input_path,
        )

        metadata_path = tmp_path / "test.meta.txt"
        save_metadata(result, metadata_path)

        # Verify file was created
        assert metadata_path.exists()

        # Verify content
        content = metadata_path.read_text(encoding="utf-8")
        assert "SYLLABLE EXTRACTION METADATA" in content
        assert "en_US" in content


class TestIntegration:
    """Integration tests for complete extraction workflows."""

    def test_full_extraction_workflow(self, tmp_path):
        """Test the complete extraction workflow end-to-end."""
        # Step 1: Create input file
        input_file = tmp_path / "input.txt"
        input_file.write_text(
            "The quick brown fox jumps over the lazy dog. "
            "Beautiful wonderful extraordinary magnificent.",
            encoding="utf-8",
        )

        # Step 2: Initialize extractor
        extractor = SyllableExtractor("en_US", min_syllable_length=2, max_syllable_length=8)

        # Step 3: Extract syllables
        syllables, stats = extractor.extract_syllables_from_file(input_file)

        # Step 4: Verify extraction
        assert len(syllables) > 0
        for syll in syllables:
            assert 2 <= len(syll) <= 8
            assert syll.islower()
            assert syll.isalpha()

        # Step 5: Generate output paths
        output_dir = tmp_path / "output"
        syllables_path, metadata_path = generate_output_filename(output_dir)

        # Step 6: Save syllables
        extractor.save_syllables(syllables, syllables_path)
        assert syllables_path.exists()

        # Step 7: Create and save metadata
        result = ExtractionResult(
            syllables=syllables,
            language_code="en_US",
            min_syllable_length=2,
            max_syllable_length=8,
            input_path=input_file,
            total_words=stats["total_words"],
            skipped_unhyphenated=stats["skipped_unhyphenated"],
            rejected_syllables=stats["rejected_syllables"],
            processed_words=stats["processed_words"],
        )
        save_metadata(result, metadata_path)
        assert metadata_path.exists()

        # Step 8: Verify syllables file content
        saved_syllables = syllables_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(saved_syllables) == len(syllables)
        assert saved_syllables == sorted(syllables)

        # Step 9: Verify metadata file content
        metadata_content = metadata_path.read_text(encoding="utf-8")
        assert "en_US" in metadata_content
        assert "2-8 characters" in metadata_content

    def test_extraction_with_unicode_text(self, tmp_path):
        """Test extraction with text containing accented characters."""
        input_file = tmp_path / "unicode_input.txt"
        input_file.write_text("café résumé naïve", encoding="utf-8")

        extractor = SyllableExtractor("en_US", min_syllable_length=2, max_syllable_length=8)
        syllables, _ = extractor.extract_syllables_from_file(input_file)

        # Should extract some syllables without crashing
        assert isinstance(syllables, set)

    def test_extraction_deterministic(self, tmp_path):
        """Test that extraction is deterministic."""
        input_file = tmp_path / "input.txt"
        input_file.write_text("hello beautiful wonderful world", encoding="utf-8")

        extractor = SyllableExtractor("en_US", min_syllable_length=2, max_syllable_length=8)

        # Extract syllables twice
        syllables1, _ = extractor.extract_syllables_from_file(input_file)
        syllables2, _ = extractor.extract_syllables_from_file(input_file)

        # Should be identical
        assert syllables1 == syllables2


class TestEdgeCases:
    """Test suite for edge cases and error conditions."""

    def test_syllable_length_constraints_equal(self):
        """Test when min and max syllable lengths are equal."""
        extractor = SyllableExtractor("en_US", min_syllable_length=3, max_syllable_length=3)
        syllables, _ = extractor.extract_syllables_from_text("hello beautiful world")

        # All syllables should be exactly 3 characters
        for syll in syllables:
            assert len(syll) == 3

    def test_very_long_text(self):
        """Test extraction from very long text."""
        # Create text with 1000 words
        long_text = " ".join(["hello world beautiful"] * 334)

        extractor = SyllableExtractor("en_US", min_syllable_length=2, max_syllable_length=8)
        syllables, _ = extractor.extract_syllables_from_text(long_text)

        # Should still produce valid results
        assert len(syllables) > 0
        for syll in syllables:
            assert 2 <= len(syll) <= 8

    def test_text_with_numbers(self):
        """Test that numbers are excluded from syllable extraction."""
        extractor = SyllableExtractor("en_US", min_syllable_length=1, max_syllable_length=10)
        text = "hello123 world456 test789"

        syllables, _ = extractor.extract_syllables_from_text(text)

        # No syllables should contain digits
        for syll in syllables:
            assert not any(c.isdigit() for c in syll)

    def test_text_with_only_special_characters(self):
        """Test extraction from text with only special characters."""
        extractor = SyllableExtractor("en_US")
        text = "!@#$%^&*()_+-=[]{}|;':\",./<>?"

        syllables, _ = extractor.extract_syllables_from_text(text)

        # Should return empty set
        assert syllables == set()

    def test_single_letter_words(self):
        """Test handling of single-letter words."""
        extractor = SyllableExtractor("en_US", min_syllable_length=1, max_syllable_length=10)
        text = "I a b c d"

        syllables, _ = extractor.extract_syllables_from_text(text, only_hyphenated=False)

        # May or may not extract single letters depending on pyphen behavior
        # Just verify it doesn't crash
        assert isinstance(syllables, set)


class TestErrorHandling:
    """Test suite for error handling scenarios."""

    def test_save_syllables_io_error(self, tmp_path):
        """Test that IOError is raised when save_syllables fails."""
        extractor = SyllableExtractor("en_US")
        test_syllables = {"hello", "world"}

        # Create a directory where we expect a file (will cause error)
        bad_path = tmp_path / "bad_file.txt"
        bad_path.mkdir()

        with pytest.raises(IOError, match="Error writing file"):
            extractor.save_syllables(test_syllables, bad_path)

    def test_save_metadata_io_error(self, tmp_path):
        """Test that IOError is raised when save_metadata fails."""
        test_syllables = {"hello", "world"}
        test_input_path = tmp_path / "input.txt"
        test_input_path.write_text("test", encoding="utf-8")

        result = ExtractionResult(
            syllables=test_syllables,
            language_code="en_US",
            min_syllable_length=2,
            max_syllable_length=8,
            input_path=test_input_path,
        )

        # Create a directory where we expect a file (will cause error)
        bad_path = tmp_path / "bad_meta.txt"
        bad_path.mkdir()

        with pytest.raises(IOError, match="Error writing metadata file"):
            save_metadata(result, bad_path)

    def test_extract_from_file_io_error(self, tmp_path):
        """Test that IOError is raised when reading file fails."""
        extractor = SyllableExtractor("en_US")

        # Create a directory (not a file) to cause read error
        bad_file = tmp_path / "directory_not_file"
        bad_file.mkdir()

        with pytest.raises(IOError, match="Error reading file"):
            extractor.extract_syllables_from_file(bad_file)

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Permission handling differs on Windows (uses ACLs, not Unix permissions)",
    )
    def test_extract_from_file_permission_error(self, tmp_path):
        """Test handling of file permission errors on Unix-like systems."""
        import os
        import stat

        extractor = SyllableExtractor("en_US")

        # Create a file and remove read permissions (Unix-like systems only)
        restricted_file = tmp_path / "restricted.txt"
        restricted_file.write_text("test content", encoding="utf-8")

        try:
            # Remove all permissions
            os.chmod(restricted_file, 0o000)

            with pytest.raises(IOError):
                extractor.extract_syllables_from_file(restricted_file)
        finally:
            # Restore permissions for cleanup
            os.chmod(restricted_file, stat.S_IRUSR | stat.S_IWUSR)


class TestHelperFunctions:
    """Test suite for module-level helper functions."""

    def test_generate_output_filename_timestamp_format(self):
        """Test that run directory has correct timestamp format with pyphen identifier."""
        syllables_path, metadata_path = generate_output_filename()

        # Extract run directory name
        run_dir = syllables_path.parent.parent
        dir_name = run_dir.name

        # Should be YYYYMMDD_HHMMSS_pyphen format (22 characters)
        assert len(dir_name) == 22
        assert dir_name[8] == "_"  # First underscore
        assert dir_name[15:] == "_pyphen"  # Identifier suffix

        # All characters except underscores should be digits in timestamp part
        assert dir_name[:8].isdigit()  # YYYYMMDD
        assert dir_name[9:15].isdigit()  # HHMMSS

    def test_generate_output_filename_creates_nested_dirs(self, tmp_path):
        """Test that deeply nested directories are created."""
        deep_path = tmp_path / "level1" / "level2" / "level3" / "level4"
        assert not deep_path.exists()

        syllables_path, metadata_path = generate_output_filename(deep_path)

        # All parent directories should be created
        assert deep_path.exists()
        assert deep_path.is_dir()

    def test_save_metadata_creates_valid_content(self, tmp_path):
        """Test that save_metadata creates properly formatted content."""
        test_syllables = {"alpha", "beta", "gamma", "delta"}
        test_input_path = tmp_path / "input.txt"
        test_input_path.write_text("test", encoding="utf-8")

        result = ExtractionResult(
            syllables=test_syllables,
            language_code="de_DE",
            min_syllable_length=3,
            max_syllable_length=7,
            input_path=test_input_path,
            only_hyphenated=False,
        )

        metadata_path = tmp_path / "metadata.txt"
        save_metadata(result, metadata_path)

        content = metadata_path.read_text(encoding="utf-8")

        # Verify all expected sections are present
        assert "SYLLABLE EXTRACTION METADATA" in content
        assert "de_DE" in content
        assert "3-7 characters" in content
        assert str(test_input_path) in content
        assert "4" in content  # Number of syllables
        assert "Only Hyphenated:    No" in content
        assert "Syllable Length Distribution:" in content
        assert "Sample Syllables" in content


class TestExtractionResultEdgeCases:
    """Test edge cases for ExtractionResult dataclass."""

    def test_extraction_result_with_large_syllable_set(self, tmp_path):
        """Test ExtractionResult with a large number of syllables."""
        # Create 1000 unique syllables
        large_syllable_set = {f"syl{i:04d}" for i in range(1000)}
        test_path = tmp_path / "input.txt"
        test_path.write_text("test", encoding="utf-8")

        result = ExtractionResult(
            syllables=large_syllable_set,
            language_code="en_US",
            min_syllable_length=1,
            max_syllable_length=10,
            input_path=test_path,
        )

        # Sample should be limited to 15
        assert len(result.sample_syllables) == 15

        # Total count should be correct
        assert len(result.syllables) == 1000

        # Metadata should format correctly
        metadata = result.format_metadata()
        assert "1000" in metadata

    def test_extraction_result_length_distribution_various_lengths(self):
        """Test length distribution with syllables of various lengths."""
        # Create syllables of lengths 2-10 (adding digit increases length by 1)
        test_syllables = set()
        for length in range(1, 10):
            for i in range(5):  # 5 syllables of each length
                test_syllables.add("a" * length + str(i))

        test_path = Path("test.txt")

        result = ExtractionResult(
            syllables=test_syllables,
            language_code="en_US",
            min_syllable_length=1,
            max_syllable_length=11,
            input_path=test_path,
        )

        # Should have distribution for lengths 2-10 (a + digit creates 2 chars minimum)
        for length in range(2, 11):
            assert length in result.length_distribution
            assert result.length_distribution[length] > 0

    def test_extraction_result_custom_timestamp(self, tmp_path):
        """Test ExtractionResult with custom timestamp."""
        from datetime import datetime

        test_syllables = {"test"}
        test_path = tmp_path / "input.txt"
        test_path.write_text("test", encoding="utf-8")

        custom_time = datetime(2025, 1, 1, 12, 0, 0)

        result = ExtractionResult(
            syllables=test_syllables,
            language_code="en_US",
            min_syllable_length=1,
            max_syllable_length=10,
            input_path=test_path,
            timestamp=custom_time,
        )

        assert result.timestamp == custom_time

        # Check it appears in formatted metadata
        metadata = result.format_metadata()
        assert "2025-01-01 12:00:00" in metadata

    def test_format_metadata_with_long_sample_list(self, tmp_path):
        """Test metadata formatting when sample list shows 'and X more' message."""
        # Create 100 syllables
        test_syllables = {f"syl{i:03d}" for i in range(100)}
        test_path = tmp_path / "input.txt"
        test_path.write_text("test", encoding="utf-8")

        result = ExtractionResult(
            syllables=test_syllables,
            language_code="en_US",
            min_syllable_length=1,
            max_syllable_length=10,
            input_path=test_path,
        )

        metadata = result.format_metadata()

        # Should show "... and 85 more" (100 - 15 = 85)
        assert "and 85 more" in metadata

    def test_format_metadata_with_unicode_path(self, tmp_path):
        """Test metadata formatting with unicode characters in path."""
        test_syllables = {"test"}
        # Create path with unicode characters
        test_path = tmp_path / "tëst_fîlé_日本語.txt"
        test_path.write_text("test", encoding="utf-8")

        result = ExtractionResult(
            syllables=test_syllables,
            language_code="en_US",
            min_syllable_length=1,
            max_syllable_length=10,
            input_path=test_path,
        )

        metadata = result.format_metadata()

        # Should contain the unicode path
        assert str(test_path) in metadata


class TestModuleConstants:
    """Test module-level constants and configuration."""

    def test_default_output_dir_is_defined(self):
        """Test that DEFAULT_OUTPUT_DIR is properly configured."""
        assert DEFAULT_OUTPUT_DIR == Path("_working/output")
        assert isinstance(DEFAULT_OUTPUT_DIR, Path)

    def test_supported_languages_has_expected_entries(self):
        """Test that SUPPORTED_LANGUAGES contains expected languages."""
        # Test for common languages
        assert "English (US)" in SUPPORTED_LANGUAGES
        assert "English (UK)" in SUPPORTED_LANGUAGES
        assert "German" in SUPPORTED_LANGUAGES
        assert "French" in SUPPORTED_LANGUAGES
        assert "Spanish" in SUPPORTED_LANGUAGES

        # Test codes
        assert SUPPORTED_LANGUAGES["English (US)"] == "en_US"
        assert SUPPORTED_LANGUAGES["English (UK)"] == "en_GB"
        assert SUPPORTED_LANGUAGES["German"] == "de_DE"


class TestLanguageSupport:
    """Test suite for multi-language support."""

    def test_supported_languages_dict_is_valid(self):
        """Test that SUPPORTED_LANGUAGES dictionary is properly structured."""
        assert len(SUPPORTED_LANGUAGES) > 0

        for name, code in SUPPORTED_LANGUAGES.items():
            assert isinstance(name, str)
            assert isinstance(code, str)
            assert len(name) > 0
            assert len(code) > 0

    def test_all_supported_languages_are_valid(self):
        """Test that all languages in SUPPORTED_LANGUAGES can be initialized."""
        # Test a representative sample to avoid slow tests
        sample_languages = ["en_US", "de_DE", "fr", "es", "ru_RU"]

        for lang_code in sample_languages:
            if lang_code in SUPPORTED_LANGUAGES.values():
                extractor = SyllableExtractor(lang_code)
                assert extractor.language_code == lang_code

    def test_extract_with_different_languages(self):
        """Test extraction works with different language dictionaries."""
        test_cases = [
            ("en_US", "hello beautiful world"),
            ("de_DE", "hallo schöne welt"),
            ("fr", "bonjour belle monde"),
        ]

        for lang_code, text in test_cases:
            extractor = SyllableExtractor(lang_code, min_syllable_length=2, max_syllable_length=10)
            syllables, _ = extractor.extract_syllables_from_text(text)

            # Should extract some syllables without crashing
            assert isinstance(syllables, set)


class TestSyllableExtractionEdgeCases:
    """Additional edge case tests for syllable extraction."""

    def test_extract_with_very_short_syllable_constraint(self):
        """Test extraction with minimum length of 1."""
        extractor = SyllableExtractor("en_US", min_syllable_length=1, max_syllable_length=2)
        text = "hello world"

        syllables, _ = extractor.extract_syllables_from_text(text)

        # All syllables should be 1-2 characters
        for syll in syllables:
            assert 1 <= len(syll) <= 2

    def test_extract_with_very_long_syllable_constraint(self):
        """Test extraction with very large maximum length."""
        extractor = SyllableExtractor("en_US", min_syllable_length=1, max_syllable_length=100)
        text = "extraordinarily beautiful"

        syllables, _ = extractor.extract_syllables_from_text(text)

        # Should accept all syllables
        assert len(syllables) > 0

    def test_extract_from_text_with_repeated_words(self):
        """Test that repeated words don't increase syllable count."""
        extractor = SyllableExtractor("en_US", min_syllable_length=2, max_syllable_length=10)
        text = "hello hello hello world world world"

        syllables, _ = extractor.extract_syllables_from_text(text)

        # Should be same as "hello world" since we use a set
        syllables_unique, _ = extractor.extract_syllables_from_text("hello world")

        assert syllables == syllables_unique

    def test_extract_with_mixed_case_produces_lowercase(self):
        """Test that all extracted syllables are lowercase."""
        extractor = SyllableExtractor("en_US", min_syllable_length=2, max_syllable_length=10)
        text = "HELLO WoRLD Beautiful WONDERFUL"

        syllables, _ = extractor.extract_syllables_from_text(text)

        # All syllables should be lowercase
        for syll in syllables:
            assert syll == syll.lower()
            assert syll.islower()

    def test_extract_from_empty_file(self, tmp_path):
        """Test extracting from an empty file."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")

        extractor = SyllableExtractor("en_US")
        syllables, _ = extractor.extract_syllables_from_file(empty_file)

        assert syllables == set()

    def test_extract_from_whitespace_only_file(self, tmp_path):
        """Test extracting from a file with only whitespace."""
        whitespace_file = tmp_path / "whitespace.txt"
        whitespace_file.write_text("   \n\n\t\t   \n   ", encoding="utf-8")

        extractor = SyllableExtractor("en_US")
        syllables, _ = extractor.extract_syllables_from_file(whitespace_file)

        assert syllables == set()

    def test_extract_with_accented_characters(self):
        """Test extraction with various accented characters."""
        extractor = SyllableExtractor("fr", min_syllable_length=2, max_syllable_length=10)
        text = "été café résumé naïve déjà"

        syllables, _ = extractor.extract_syllables_from_text(text)

        # Should handle accented characters without crashing
        assert isinstance(syllables, set)

    def test_save_syllables_preserves_unicode(self, tmp_path):
        """Test that saving syllables preserves unicode characters."""
        output_file = tmp_path / "unicode_syllables.txt"
        test_syllables = {"café", "naïve", "résumé", "日本"}

        extractor = SyllableExtractor("en_US")
        extractor.save_syllables(test_syllables, output_file)

        # Read back and verify
        content = output_file.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        assert len(lines) == len(test_syllables)
        assert set(lines) == test_syllables


class TestExtractionResultDataclass:
    """Test ExtractionResult dataclass specific behavior."""

    def test_extraction_result_default_values(self, tmp_path):
        """Test that ExtractionResult uses correct default values."""
        test_syllables = {"test"}
        test_path = tmp_path / "input.txt"
        test_path.write_text("test", encoding="utf-8")

        # Create with minimal args
        result = ExtractionResult(
            syllables=test_syllables,
            language_code="en_US",
            min_syllable_length=2,
            max_syllable_length=8,
            input_path=test_path,
        )

        # Check defaults
        assert result.only_hyphenated is True
        assert isinstance(result.timestamp, datetime)
        assert isinstance(result.length_distribution, dict)
        assert isinstance(result.sample_syllables, list)

    def test_extraction_result_only_hyphenated_false(self, tmp_path):
        """Test ExtractionResult with only_hyphenated=False."""
        test_syllables = {"test", "word", "syllable"}
        test_path = tmp_path / "input.txt"
        test_path.write_text("test", encoding="utf-8")

        result = ExtractionResult(
            syllables=test_syllables,
            language_code="en_US",
            min_syllable_length=2,
            max_syllable_length=10,
            input_path=test_path,
            only_hyphenated=False,
        )

        assert result.only_hyphenated is False

        # Check it appears in metadata
        metadata = result.format_metadata()
        assert "Only Hyphenated:    No" in metadata

    def test_format_metadata_bar_chart_rendering(self, tmp_path):
        """Test that length distribution includes bar chart visualization."""
        # Create syllables with known distribution
        test_syllables = {"ab", "cd", "ef"}  # All length 2
        test_path = tmp_path / "input.txt"
        test_path.write_text("test", encoding="utf-8")

        result = ExtractionResult(
            syllables=test_syllables,
            language_code="en_US",
            min_syllable_length=1,
            max_syllable_length=10,
            input_path=test_path,
        )

        metadata = result.format_metadata()

        # Should contain bar chart with █ character
        assert "█" in metadata
        assert "2 chars:" in metadata
        assert "3" in metadata  # Count of 3 syllables

    def test_format_metadata_separator_lines(self, tmp_path):
        """Test that metadata has proper separator formatting."""
        test_syllables = {"test"}
        test_path = tmp_path / "input.txt"
        test_path.write_text("test", encoding="utf-8")

        result = ExtractionResult(
            syllables=test_syllables,
            language_code="en_US",
            min_syllable_length=1,
            max_syllable_length=10,
            input_path=test_path,
        )

        metadata = result.format_metadata()

        # Should have separator lines
        assert "=" * 70 in metadata
        assert "SYLLABLE EXTRACTION METADATA" in metadata
