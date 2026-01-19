"""
Comprehensive test suite for syllable_normaliser package.

Tests all components of the 3-step normalization pipeline:
1. Data models (configuration, statistics, results)
2. Core normalization (Unicode, diacritics, charset, length)
3. File aggregation (discovering, reading, combining files)
4. Frequency analysis (counting, ranking, deduplication)
5. CLI and integration (full pipeline end-to-end)
"""

import json
from pathlib import Path

import pytest

from build_tools.pyphen_syllable_normaliser import (
    FileAggregator,
    FrequencyAnalyzer,
    NormalizationConfig,
    NormalizationResult,
    NormalizationStats,
    SyllableNormalizer,
    discover_input_files,
    load_frequencies_from_file,
    load_unique_syllables_from_file,
    normalize_batch,
    run_full_pipeline,
)

# ============================================================================
# Test Data Models
# ============================================================================


class TestNormalizationConfig:
    """Test NormalizationConfig dataclass and validation."""

    def test_default_configuration(self):
        """Test that default configuration values are correct."""
        config = NormalizationConfig()
        assert config.min_length == 2
        assert config.max_length == 20
        assert config.allowed_charset == "abcdefghijklmnopqrstuvwxyz"
        assert config.unicode_form == "NFKD"

    def test_custom_configuration(self):
        """Test creating config with custom values."""
        config = NormalizationConfig(
            min_length=3, max_length=10, allowed_charset="abc", unicode_form="NFC"
        )
        assert config.min_length == 3
        assert config.max_length == 10
        assert config.allowed_charset == "abc"
        assert config.unicode_form == "NFC"

    def test_validation_min_length_too_small(self):
        """Test that min_length < 1 raises ValueError."""
        with pytest.raises(ValueError, match="min_length must be >= 1"):
            NormalizationConfig(min_length=0)

    def test_validation_max_less_than_min(self):
        """Test that max_length < min_length raises ValueError."""
        with pytest.raises(ValueError, match="max_length .* must be >= min_length"):
            NormalizationConfig(min_length=10, max_length=5)

    def test_validation_invalid_unicode_form(self):
        """Test that invalid unicode_form raises ValueError."""
        with pytest.raises(ValueError, match="unicode_form must be one of"):
            NormalizationConfig(unicode_form="INVALID")


class TestNormalizationStats:
    """Test NormalizationStats dataclass and computed properties."""

    def test_default_statistics(self):
        """Test that default statistics values are zero."""
        stats = NormalizationStats()
        assert stats.raw_count == 0
        assert stats.after_canonicalization == 0
        assert stats.rejected_charset == 0
        assert stats.rejected_length == 0
        assert stats.rejected_empty == 0
        assert stats.unique_canonical == 0
        assert stats.processing_time == 0.0

    def test_total_rejected_property(self):
        """Test that total_rejected computes correct sum."""
        stats = NormalizationStats(rejected_charset=10, rejected_length=5, rejected_empty=3)
        assert stats.total_rejected == 18

    def test_rejection_rate_property(self):
        """Test that rejection_rate computes correct percentage."""
        stats = NormalizationStats(
            raw_count=100, rejected_charset=10, rejected_length=5, rejected_empty=5
        )
        assert stats.rejection_rate == 20.0

    def test_rejection_rate_zero_raw_count(self):
        """Test that rejection_rate returns 0.0 when raw_count is zero."""
        stats = NormalizationStats(raw_count=0, rejected_charset=5)
        assert stats.rejection_rate == 0.0


class TestNormalizationResult:
    """Test NormalizationResult dataclass and format_metadata method."""

    def test_result_creation(self, tmp_path: Path):
        """Test creating a NormalizationResult with all fields."""
        config = NormalizationConfig()
        stats = NormalizationStats(raw_count=100, unique_canonical=50)
        frequencies = {"ka": 10, "ra": 8}
        unique_syllables = ["ka", "ra"]
        input_files = [tmp_path / "test.txt"]

        result = NormalizationResult(
            config=config,
            stats=stats,
            frequencies=frequencies,
            unique_syllables=unique_syllables,
            input_files=input_files,
            output_dir=tmp_path,
        )

        assert result.config == config
        assert result.stats == stats
        assert result.frequencies == frequencies
        assert result.unique_syllables == unique_syllables
        assert result.input_files == input_files
        assert result.output_dir == tmp_path

    def test_format_metadata_contains_key_sections(self, tmp_path: Path):
        """Test that format_metadata includes all required sections."""
        config = NormalizationConfig()
        stats = NormalizationStats(
            raw_count=100,
            after_canonicalization=80,
            rejected_charset=10,
            rejected_length=5,
            rejected_empty=5,
            unique_canonical=50,
            processing_time=1.5,
        )
        frequencies = {"ka": 20, "ra": 15, "mi": 10}

        result = NormalizationResult(
            config=config,
            stats=stats,
            frequencies=frequencies,
            unique_syllables=["ka", "mi", "ra"],
            input_files=[tmp_path / "test.txt"],
            output_dir=tmp_path,
        )

        metadata = result.format_metadata()

        # Check for key sections
        assert "SYLLABLE NORMALIZATION METADATA" in metadata
        assert "Processing Statistics:" in metadata
        assert "Rejection Breakdown:" in metadata
        assert "Normalization Configuration:" in metadata
        assert "Top" in metadata and "Most Frequent Syllables:" in metadata
        assert "Output Files:" in metadata

        # Check for specific values
        assert "100" in metadata  # raw_count
        assert "80" in metadata  # after_canonicalization
        assert "50" in metadata  # unique_canonical


# ============================================================================
# Test Core Normalization
# ============================================================================


class TestSyllableNormalizer:
    """Test SyllableNormalizer class and normalization logic."""

    def test_basic_normalization(self):
        """Test basic lowercase and trim normalization."""
        config = NormalizationConfig()
        normalizer = SyllableNormalizer(config)

        assert normalizer.normalize("Hello") == "hello"
        assert normalizer.normalize("  world  ") == "world"
        assert normalizer.normalize("UPPER") == "upper"

    def test_diacritic_stripping(self):
        """Test that diacritics are correctly removed."""
        config = NormalizationConfig()
        normalizer = SyllableNormalizer(config)

        assert normalizer.normalize("café") == "cafe"
        assert normalizer.normalize("naïve") == "naive"
        assert normalizer.normalize("résumé") == "resume"
        assert normalizer.normalize("Zürich") == "zurich"

    def test_unicode_normalization(self):
        """Test Unicode NFKD normalization."""
        config = NormalizationConfig(unicode_form="NFKD", min_length=1)
        normalizer = SyllableNormalizer(config)

        # Unicode normalization converts accented characters
        # é (single char U+00E9) decomposes and diacritics are stripped
        assert normalizer.normalize("é") == "e"
        assert normalizer.normalize("café") == "cafe"
        assert normalizer.normalize("àéîôù") == "aeiou"

    def test_empty_after_normalization(self):
        """Test that empty strings return None."""
        config = NormalizationConfig()
        normalizer = SyllableNormalizer(config)

        assert normalizer.normalize("") is None
        assert normalizer.normalize("   ") is None
        assert normalizer.normalize("\t\n") is None

    def test_invalid_charset_rejection(self):
        """Test that syllables with invalid characters are rejected."""
        config = NormalizationConfig(allowed_charset="abcdefghijklmnopqrstuvwxyz")
        normalizer = SyllableNormalizer(config)

        assert normalizer.normalize("hello") == "hello"
        assert normalizer.normalize("hello123") is None
        assert normalizer.normalize("hello-world") is None
        assert normalizer.normalize("hello@world") is None

    def test_length_constraint_rejection(self):
        """Test that syllables outside length constraints are rejected."""
        config = NormalizationConfig(min_length=2, max_length=8)
        normalizer = SyllableNormalizer(config)

        # Too short
        assert normalizer.normalize("x") is None
        assert normalizer.normalize("a") is None

        # Within range
        assert normalizer.normalize("ab") == "ab"
        assert normalizer.normalize("hello") == "hello"
        assert normalizer.normalize("eightchr") == "eightchr"

        # Too long
        assert normalizer.normalize("verylongword") is None

    def test_strip_diacritics_method(self):
        """Test strip_diacritics method directly."""
        config = NormalizationConfig()
        normalizer = SyllableNormalizer(config)

        # Note: strip_diacritics expects pre-normalized (NFD/NFKD) input
        import unicodedata

        text_nfd = unicodedata.normalize("NFD", "café")
        assert normalizer.strip_diacritics(text_nfd) == "cafe"


class TestNormalizeBatch:
    """Test normalize_batch function for batch processing."""

    def test_batch_normalization_success(self):
        """Test normalizing a batch of valid syllables."""
        config = NormalizationConfig(min_length=2, max_length=8)
        syllables = ["Café", "Hello", "World", "résumé"]

        normalized, stats = normalize_batch(syllables, config)

        assert len(normalized) == 4
        assert "cafe" in normalized
        assert "hello" in normalized
        assert "world" in normalized
        assert "resume" in normalized

    def test_batch_normalization_with_rejections(self):
        """Test batch normalization tracks rejection reasons."""
        config = NormalizationConfig(min_length=2, max_length=8)
        syllables = [
            "hello",  # Valid
            "x",  # Too short (rejected_length)
            "hello123",  # Invalid chars (rejected_charset)
            "  ",  # Empty (rejected_empty)
            "world",  # Valid
            "verylongword",  # Too long (rejected_length)
        ]

        normalized, stats = normalize_batch(syllables, config)

        assert len(normalized) == 2
        assert normalized == ["hello", "world"]
        assert stats["rejected_length"] == 2
        assert stats["rejected_charset"] == 1
        assert stats["rejected_empty"] == 1

    def test_batch_normalization_preserves_duplicates(self):
        """Test that batch normalization preserves duplicate syllables."""
        config = NormalizationConfig()
        syllables = ["ka", "ra", "ka", "mi", "ka"]

        normalized, _ = normalize_batch(syllables, config)

        assert len(normalized) == 5
        assert normalized.count("ka") == 3


# ============================================================================
# Test File Aggregation
# ============================================================================


class TestFileAggregator:
    """Test FileAggregator class for combining input files."""

    def test_read_syllables_from_file(self, tmp_path: Path):
        """Test reading syllables from a single file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello\nworld\ntest\n", encoding="utf-8")

        aggregator = FileAggregator()
        syllables = aggregator.read_syllables_from_file(test_file)

        assert syllables == ["hello", "world", "test"]

    def test_read_syllables_skips_empty_lines(self, tmp_path: Path):
        """Test that empty lines are skipped."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello\n\nworld\n  \ntest\n", encoding="utf-8")

        aggregator = FileAggregator()
        syllables = aggregator.read_syllables_from_file(test_file)

        assert syllables == ["hello", "world", "test"]

    def test_aggregate_multiple_files(self, tmp_path: Path):
        """Test aggregating syllables from multiple files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("ka\nra\n", encoding="utf-8")
        file2.write_text("mi\nta\n", encoding="utf-8")

        aggregator = FileAggregator()
        syllables = aggregator.aggregate_files([file1, file2])

        assert len(syllables) == 4
        assert syllables == ["ka", "ra", "mi", "ta"]

    def test_aggregate_preserves_duplicates(self, tmp_path: Path):
        """Test that aggregation preserves duplicate syllables."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("ka\nra\nka\n", encoding="utf-8")
        file2.write_text("ka\nmi\n", encoding="utf-8")

        aggregator = FileAggregator()
        syllables = aggregator.aggregate_files([file1, file2])

        assert len(syllables) == 5
        assert syllables.count("ka") == 3

    def test_save_raw_syllables(self, tmp_path: Path):
        """Test saving raw syllables to file."""
        output_file = tmp_path / "pyphen_syllables_raw.txt"
        syllables = ["ka", "ra", "mi"]

        aggregator = FileAggregator()
        aggregator.save_raw_syllables(syllables, output_file)

        content = output_file.read_text(encoding="utf-8")
        assert content == "ka\nra\nmi\n"


class TestDiscoverInputFiles:
    """Test discover_input_files function."""

    def test_discover_files_non_recursive(self, tmp_path: Path):
        """Test discovering files in immediate directory."""
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.txt").touch()
        (tmp_path / "file3.md").touch()

        files = discover_input_files(tmp_path, pattern="*.txt", recursive=False)

        assert len(files) == 2
        assert all(f.suffix == ".txt" for f in files)

    def test_discover_files_recursive(self, tmp_path: Path):
        """Test discovering files recursively."""
        (tmp_path / "file1.txt").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").touch()

        files = discover_input_files(tmp_path, pattern="*.txt", recursive=True)

        assert len(files) == 2

    def test_discover_files_sorted_order(self, tmp_path: Path):
        """Test that files are returned in sorted order."""
        (tmp_path / "c.txt").touch()
        (tmp_path / "a.txt").touch()
        (tmp_path / "b.txt").touch()

        files = discover_input_files(tmp_path, pattern="*.txt")

        file_names = [f.name for f in files]
        assert file_names == ["a.txt", "b.txt", "c.txt"]

    def test_discover_files_nonexistent_directory(self, tmp_path: Path):
        """Test that FileNotFoundError is raised for nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(FileNotFoundError, match="does not exist"):
            discover_input_files(nonexistent)

    def test_discover_files_not_a_directory(self, tmp_path: Path):
        """Test that ValueError is raised when path is not a directory."""
        file_path = tmp_path / "file.txt"
        file_path.touch()

        with pytest.raises(ValueError, match="not a directory"):
            discover_input_files(file_path)


# ============================================================================
# Test Frequency Analysis
# ============================================================================


class TestFrequencyAnalyzer:
    """Test FrequencyAnalyzer class."""

    def test_calculate_frequencies(self):
        """Test frequency calculation from syllable list."""
        analyzer = FrequencyAnalyzer()
        syllables = ["ka", "ra", "mi", "ka", "ta", "ka", "ra"]

        frequencies = analyzer.calculate_frequencies(syllables)

        assert frequencies == {"ka": 3, "ra": 2, "mi": 1, "ta": 1}

    def test_create_frequency_entries(self):
        """Test creating ranked frequency entries."""
        analyzer = FrequencyAnalyzer()
        frequencies = {"ka": 187, "ra": 162, "mi": 145, "ta": 98}

        entries = analyzer.create_frequency_entries(frequencies)

        assert len(entries) == 4
        assert entries[0].canonical == "ka"
        assert entries[0].rank == 1
        assert entries[0].frequency == 187
        # Total is 592, so 187/592 * 100 = ~31.59%
        assert 31.0 < entries[0].percentage < 32.0

    def test_create_frequency_entries_empty(self):
        """Test creating entries from empty frequency dict."""
        analyzer = FrequencyAnalyzer()
        entries = analyzer.create_frequency_entries({})

        assert entries == []

    def test_extract_unique_syllables(self):
        """Test extracting and sorting unique syllables."""
        analyzer = FrequencyAnalyzer()
        syllables = ["ka", "ra", "mi", "ka", "ta", "ka", "ra"]

        unique = analyzer.extract_unique_syllables(syllables)

        assert unique == ["ka", "mi", "ra", "ta"]
        assert len(unique) == 4

    def test_save_and_load_frequencies(self, tmp_path: Path):
        """Test saving and loading frequency JSON."""
        analyzer = FrequencyAnalyzer()
        frequencies = {"ka": 187, "ra": 162, "mi": 145}
        output_file = tmp_path / "frequencies.json"

        # Save
        analyzer.save_frequencies(frequencies, output_file)

        # Load
        loaded = load_frequencies_from_file(output_file)

        assert loaded == frequencies

    def test_save_and_load_unique_syllables(self, tmp_path: Path):
        """Test saving and loading unique syllables."""
        analyzer = FrequencyAnalyzer()
        unique = ["ka", "mi", "ra", "ta"]
        output_file = tmp_path / "unique.txt"

        # Save
        analyzer.save_unique_syllables(unique, output_file)

        # Load
        loaded = load_unique_syllables_from_file(output_file)

        assert loaded == unique


# ============================================================================
# Test Full Pipeline Integration
# ============================================================================


class TestFullPipeline:
    """Integration tests for the complete normalization pipeline."""

    def test_full_pipeline_end_to_end(self, tmp_path: Path):
        """Test complete pipeline from input files to all outputs."""
        # Create pyphen run directory structure
        run_dir = tmp_path / "20260110_143022_pyphen"
        syllables_dir = run_dir / "syllables"
        syllables_dir.mkdir(parents=True)

        file1 = syllables_dir / "corpus1.txt"
        file2 = syllables_dir / "corpus2.txt"

        file1.write_text("Café\nHello\nWorld\nCafé\n", encoding="utf-8")
        file2.write_text("résumé\nHello\ntest\n", encoding="utf-8")

        # Run pipeline (in-place processing)
        config = NormalizationConfig(min_length=2, max_length=20)
        result = run_full_pipeline(run_directory=run_dir, config=config, verbose=False, quiet=True)

        # Verify output files exist
        assert result.raw_file.exists()
        assert result.canonical_file.exists()
        assert result.frequency_file.exists()
        assert result.unique_file.exists()
        assert result.meta_file.exists()

        # Verify raw file contains all syllables (7 total)
        raw_content = result.raw_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(raw_content) == 7

        # Verify canonical file
        canonical_content = result.canonical_file.read_text(encoding="utf-8").strip().split("\n")
        assert "cafe" in canonical_content
        assert "hello" in canonical_content
        assert "resume" in canonical_content

        # Verify frequencies
        frequencies = json.loads(result.frequency_file.read_text(encoding="utf-8"))
        assert frequencies["cafe"] == 2  # Appeared twice in input
        assert frequencies["hello"] == 2  # Appeared twice in input
        assert frequencies["resume"] == 1

        # Verify unique syllables
        unique_content = result.unique_file.read_text(encoding="utf-8").strip().split("\n")
        unique_sorted = sorted(unique_content)
        assert unique_sorted == ["cafe", "hello", "resume", "test", "world"]

        # Verify statistics
        assert result.stats.raw_count == 7
        assert result.stats.after_canonicalization == 7
        assert result.stats.unique_canonical == 5

    def test_pipeline_with_rejections(self, tmp_path: Path):
        """Test pipeline handles rejected syllables correctly."""
        # Create pyphen run directory structure
        run_dir = tmp_path / "20260110_150000_pyphen"
        syllables_dir = run_dir / "syllables"
        syllables_dir.mkdir(parents=True)

        test_file = syllables_dir / "test.txt"

        test_file.write_text(
            "hello\n"  # Valid
            "x\n"  # Too short
            "hello123\n"  # Invalid chars
            "world\n"  # Valid
            "verylongword\n",  # Too long
            encoding="utf-8",
        )

        config = NormalizationConfig(min_length=2, max_length=8)

        result = run_full_pipeline(run_directory=run_dir, config=config, verbose=False, quiet=True)

        # Check statistics
        # Note: Empty lines are filtered during aggregation, not during canonicalization
        assert result.stats.raw_count == 5
        assert result.stats.after_canonicalization == 2
        assert result.stats.rejected_length == 2  # "x" and "verylongword"
        assert result.stats.rejected_charset == 1  # "hello123"
        assert result.stats.rejected_empty == 0  # Empty lines filtered during aggregation

    def test_pipeline_determinism(self, tmp_path: Path):
        """Test that pipeline produces deterministic output."""
        # Create two pyphen run directories with identical input
        run_dir1 = tmp_path / "20260110_160000_pyphen"
        syllables_dir1 = run_dir1 / "syllables"
        syllables_dir1.mkdir(parents=True)
        test_file1 = syllables_dir1 / "test.txt"
        test_file1.write_text("ka\nra\nmi\nka\nta\n", encoding="utf-8")

        run_dir2 = tmp_path / "20260110_170000_pyphen"
        syllables_dir2 = run_dir2 / "syllables"
        syllables_dir2.mkdir(parents=True)
        test_file2 = syllables_dir2 / "test.txt"
        test_file2.write_text("ka\nra\nmi\nka\nta\n", encoding="utf-8")

        config = NormalizationConfig()

        # Run pipeline twice on different run directories
        result1 = run_full_pipeline(
            run_directory=run_dir1, config=config, verbose=False, quiet=True
        )

        result2 = run_full_pipeline(
            run_directory=run_dir2, config=config, verbose=False, quiet=True
        )

        # Verify identical statistics
        assert result1.stats.raw_count == result2.stats.raw_count
        assert result1.stats.after_canonicalization == result2.stats.after_canonicalization
        assert result1.stats.unique_canonical == result2.stats.unique_canonical

        # Verify identical frequencies
        freq1 = json.loads(result1.frequency_file.read_text(encoding="utf-8"))
        freq2 = json.loads(result2.frequency_file.read_text(encoding="utf-8"))
        assert freq1 == freq2

        # Verify identical unique syllables
        unique1 = result1.unique_file.read_text(encoding="utf-8")
        unique2 = result2.unique_file.read_text(encoding="utf-8")
        assert unique1 == unique2


class TestRunDirectoryDetection:
    """Tests for pyphen run directory detection."""

    def test_detect_pyphen_run_directories(self, tmp_path: Path):
        """Test auto-detection of pyphen run directories."""
        from build_tools.pyphen_syllable_normaliser.cli import detect_pyphen_run_directories

        # Create multiple pyphen run directories
        run1 = tmp_path / "20260110_100000_pyphen"
        (run1 / "syllables").mkdir(parents=True)

        run2 = tmp_path / "20260110_110000_pyphen"
        (run2 / "syllables").mkdir(parents=True)

        run3 = tmp_path / "20260110_120000_pyphen"
        (run3 / "syllables").mkdir(parents=True)

        # Create non-pyphen directory (should be ignored)
        other = tmp_path / "20260110_130000_nltk"
        (other / "syllables").mkdir(parents=True)

        # Create pyphen directory without syllables/ subdirectory (should be ignored)
        incomplete = tmp_path / "20260110_140000_pyphen"
        incomplete.mkdir()

        # Detect pyphen run directories
        detected = detect_pyphen_run_directories(tmp_path)

        # Should find 3 pyphen runs, sorted chronologically
        assert len(detected) == 3
        assert detected[0].name == "20260110_100000_pyphen"
        assert detected[1].name == "20260110_110000_pyphen"
        assert detected[2].name == "20260110_120000_pyphen"

    def test_detect_no_pyphen_directories(self, tmp_path: Path):
        """Test detection when no pyphen directories exist."""
        from build_tools.pyphen_syllable_normaliser.cli import detect_pyphen_run_directories

        # Create only NLTK directories
        nltk_run = tmp_path / "20260110_100000_nltk"
        (nltk_run / "syllables").mkdir(parents=True)

        # Detect pyphen run directories
        detected = detect_pyphen_run_directories(tmp_path)

        # Should find nothing
        assert len(detected) == 0

    def test_detect_nonexistent_directory(self, tmp_path: Path):
        """Test detection with nonexistent source directory."""
        from build_tools.pyphen_syllable_normaliser.cli import detect_pyphen_run_directories

        nonexistent = tmp_path / "does_not_exist"

        with pytest.raises(FileNotFoundError):
            detect_pyphen_run_directories(nonexistent)

    def test_detect_not_a_directory(self, tmp_path: Path):
        """Test detection raises ValueError when path is a file, not directory."""
        from build_tools.pyphen_syllable_normaliser.cli import detect_pyphen_run_directories

        file_path = tmp_path / "some_file.txt"
        file_path.touch()

        with pytest.raises(ValueError, match="not a directory"):
            detect_pyphen_run_directories(file_path)


# ============================================================================
# Test CLI Main Function
# ============================================================================


class TestCLIMain:
    """Tests for the main() CLI entry point."""

    def test_main_with_run_dir(self, tmp_path: Path):
        """Test main() with explicit --run-dir argument."""
        from build_tools.pyphen_syllable_normaliser.cli import main

        # Create pyphen run directory structure
        run_dir = tmp_path / "20260110_143022_pyphen"
        syllables_dir = run_dir / "syllables"
        syllables_dir.mkdir(parents=True)

        test_file = syllables_dir / "test.txt"
        test_file.write_text("hello\nworld\ntest\n", encoding="utf-8")

        result = main(["--run-dir", str(run_dir), "--quiet"])

        assert result == 0
        assert (run_dir / "pyphen_syllables_raw.txt").exists()
        assert (run_dir / "pyphen_syllables_unique.txt").exists()

    def test_main_with_source_auto_detect(self, tmp_path: Path):
        """Test main() with --source to auto-detect pyphen directories."""
        from build_tools.pyphen_syllable_normaliser.cli import main

        # Create multiple pyphen run directories
        run_dir1 = tmp_path / "20260110_100000_pyphen"
        (run_dir1 / "syllables").mkdir(parents=True)
        (run_dir1 / "syllables" / "test.txt").write_text("ka\nra\n", encoding="utf-8")

        run_dir2 = tmp_path / "20260110_110000_pyphen"
        (run_dir2 / "syllables").mkdir(parents=True)
        (run_dir2 / "syllables" / "test.txt").write_text("mi\nta\n", encoding="utf-8")

        result = main(["--source", str(tmp_path), "--quiet"])

        assert result == 0
        # Both directories should have been processed
        assert (run_dir1 / "pyphen_syllables_unique.txt").exists()
        assert (run_dir2 / "pyphen_syllables_unique.txt").exists()

    def test_main_no_pyphen_directories_found(self, tmp_path: Path, capsys):
        """Test main() when no pyphen directories exist in source."""
        from build_tools.pyphen_syllable_normaliser.cli import main

        # Create only NLTK directory (not pyphen)
        nltk_dir = tmp_path / "20260110_100000_nltk"
        (nltk_dir / "syllables").mkdir(parents=True)

        result = main(["--source", str(tmp_path)])

        assert result == 1
        captured = capsys.readouterr()
        assert "No pyphen run directories found" in captured.err

    def test_main_min_less_than_one(self, tmp_path: Path, capsys):
        """Test main() with --min < 1 returns error."""
        from build_tools.pyphen_syllable_normaliser.cli import main

        run_dir = tmp_path / "20260110_143022_pyphen"
        (run_dir / "syllables").mkdir(parents=True)

        result = main(["--run-dir", str(run_dir), "--min", "0"])

        assert result == 1
        captured = capsys.readouterr()
        assert "--min must be >= 1" in captured.err

    def test_main_max_less_than_min(self, tmp_path: Path, capsys):
        """Test main() with --max < --min returns error."""
        from build_tools.pyphen_syllable_normaliser.cli import main

        run_dir = tmp_path / "20260110_143022_pyphen"
        (run_dir / "syllables").mkdir(parents=True)

        result = main(["--run-dir", str(run_dir), "--min", "10", "--max", "5"])

        assert result == 1
        captured = capsys.readouterr()
        assert "--max (5) must be >= --min (10)" in captured.err

    def test_main_custom_config(self, tmp_path: Path):
        """Test main() with custom configuration options."""
        from build_tools.pyphen_syllable_normaliser.cli import main

        run_dir = tmp_path / "20260110_143022_pyphen"
        syllables_dir = run_dir / "syllables"
        syllables_dir.mkdir(parents=True)

        test_file = syllables_dir / "test.txt"
        test_file.write_text("hello\nx\nverylongwordthatwillbefiltered\nworld\n", encoding="utf-8")

        result = main(
            [
                "--run-dir",
                str(run_dir),
                "--min",
                "3",
                "--max",
                "10",
                "--charset",
                "abcdefghijklmnopqrstuvwxyz",
                "--unicode-form",
                "NFC",
                "--quiet",
            ]
        )

        assert result == 0
        # Check that short syllables were filtered
        unique_content = (run_dir / "pyphen_syllables_unique.txt").read_text()
        assert "hello" in unique_content
        assert "world" in unique_content
        # "x" is too short (< 3)
        assert "x" not in unique_content

    def test_main_verbose_output(self, tmp_path: Path, capsys):
        """Test main() with --verbose flag."""
        from build_tools.pyphen_syllable_normaliser.cli import main

        run_dir = tmp_path / "20260110_143022_pyphen"
        syllables_dir = run_dir / "syllables"
        syllables_dir.mkdir(parents=True)

        test_file = syllables_dir / "test.txt"
        test_file.write_text("hello\nworld\n", encoding="utf-8")

        result = main(["--run-dir", str(run_dir), "--verbose"])

        assert result == 0
        captured = capsys.readouterr()
        # Verbose should show sample output
        assert "Sample" in captured.out or "Top" in captured.out

    def test_main_file_not_found_error(self, tmp_path: Path, capsys):
        """Test main() handles FileNotFoundError gracefully."""
        from build_tools.pyphen_syllable_normaliser.cli import main

        nonexistent = tmp_path / "nonexistent_dir"

        result = main(["--run-dir", str(nonexistent), "--quiet"])

        assert result == 1
        captured = capsys.readouterr()
        assert "ERROR" in captured.err

    def test_main_verbose_shows_traceback_on_error(self, tmp_path: Path, capsys):
        """Test main() with --verbose shows traceback on error."""
        from build_tools.pyphen_syllable_normaliser.cli import main

        nonexistent = tmp_path / "nonexistent_dir"

        result = main(["--run-dir", str(nonexistent), "--verbose"])

        assert result == 1
        captured = capsys.readouterr()
        assert "ERROR" in captured.err
        # Verbose should show traceback
        assert "Traceback" in captured.err or "FileNotFoundError" in captured.err


class TestRunFullPipelineErrorPaths:
    """Tests for error handling in run_full_pipeline."""

    def test_run_full_pipeline_nonexistent_directory(self, tmp_path: Path):
        """Test run_full_pipeline raises FileNotFoundError for nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"
        config = NormalizationConfig()

        with pytest.raises(FileNotFoundError, match="does not exist"):
            run_full_pipeline(nonexistent, config, quiet=True)

    def test_run_full_pipeline_not_a_directory(self, tmp_path: Path):
        """Test run_full_pipeline raises ValueError when path is a file."""
        file_path = tmp_path / "some_file.txt"
        file_path.touch()
        config = NormalizationConfig()

        with pytest.raises(ValueError, match="not a directory"):
            run_full_pipeline(file_path, config, quiet=True)

    def test_run_full_pipeline_missing_syllables_dir(self, tmp_path: Path):
        """Test run_full_pipeline raises error when syllables/ subdirectory missing."""
        run_dir = tmp_path / "20260110_143022_pyphen"
        run_dir.mkdir()
        # Don't create syllables/ subdirectory
        config = NormalizationConfig()

        with pytest.raises(FileNotFoundError, match="Syllables directory does not exist"):
            run_full_pipeline(run_dir, config, quiet=True)


class TestArgumentParser:
    """Tests for argument parser creation and parsing."""

    def test_create_argument_parser(self):
        """Test create_argument_parser returns valid ArgumentParser."""
        from build_tools.pyphen_syllable_normaliser.cli import create_argument_parser

        parser = create_argument_parser()

        assert parser is not None
        assert parser.description is not None
        assert "Pyphen" in parser.description

    def test_parse_arguments_run_dir(self, tmp_path: Path):
        """Test parse_arguments with --run-dir."""
        from build_tools.pyphen_syllable_normaliser.cli import parse_arguments

        args = parse_arguments(["--run-dir", str(tmp_path)])

        assert args.run_dir == tmp_path
        assert args.source is None

    def test_parse_arguments_source(self, tmp_path: Path):
        """Test parse_arguments with --source."""
        from build_tools.pyphen_syllable_normaliser.cli import parse_arguments

        args = parse_arguments(["--source", str(tmp_path)])

        assert args.source == tmp_path
        assert args.run_dir is None

    def test_parse_arguments_default_values(self, tmp_path: Path):
        """Test parse_arguments has correct default values."""
        from build_tools.pyphen_syllable_normaliser.cli import parse_arguments

        args = parse_arguments(["--run-dir", str(tmp_path)])

        assert args.min == 2
        assert args.max == 20
        assert args.charset == "abcdefghijklmnopqrstuvwxyz"
        assert args.unicode_form == "NFKD"
        assert args.verbose is False
        assert args.quiet is False

    def test_parse_arguments_all_options(self, tmp_path: Path):
        """Test parse_arguments with all options specified."""
        from build_tools.pyphen_syllable_normaliser.cli import parse_arguments

        args = parse_arguments(
            [
                "--run-dir",
                str(tmp_path),
                "--min",
                "3",
                "--max",
                "15",
                "--charset",
                "abc",
                "--unicode-form",
                "NFC",
                "--verbose",
            ]
        )

        assert args.run_dir == tmp_path
        assert args.min == 3
        assert args.max == 15
        assert args.charset == "abc"
        assert args.unicode_form == "NFC"
        assert args.verbose is True

    def test_parse_arguments_mutually_exclusive(self):
        """Test that --run-dir and --source are mutually exclusive."""
        from build_tools.pyphen_syllable_normaliser.cli import parse_arguments

        with pytest.raises(SystemExit):
            parse_arguments(["--run-dir", "/path1", "--source", "/path2"])

    def test_parse_arguments_requires_input(self):
        """Test that either --run-dir or --source is required."""
        from build_tools.pyphen_syllable_normaliser.cli import parse_arguments

        with pytest.raises(SystemExit):
            parse_arguments([])

    def test_parse_arguments_verbose_short_flag(self, tmp_path: Path):
        """Test -v short flag for verbose."""
        from build_tools.pyphen_syllable_normaliser.cli import parse_arguments

        args = parse_arguments(["--run-dir", str(tmp_path), "-v"])

        assert args.verbose is True

    def test_parse_arguments_quiet_short_flag(self, tmp_path: Path):
        """Test -q short flag for quiet."""
        from build_tools.pyphen_syllable_normaliser.cli import parse_arguments

        args = parse_arguments(["--run-dir", str(tmp_path), "-q"])

        assert args.quiet is True
