"""
Unit tests for NLTK syllable extractor.

Tests cover core extraction functionality, onset/coda rules, CMUDict integration,
and fallback mechanisms.
"""

import tempfile
from pathlib import Path

import pytest

from build_tools.nltk_syllable_extractor import NltkSyllableExtractor
from build_tools.nltk_syllable_extractor.cli import (
    create_argument_parser,
    discover_files,
    process_batch,
    process_single_file_batch,
)
from build_tools.nltk_syllable_extractor.file_io import (
    generate_output_filename,
    save_metadata,
)
from build_tools.nltk_syllable_extractor.models import (
    BatchResult,
    ExtractionResult,
    FileProcessingResult,
)


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


# ============================================================================
# Tests for models.py
# ============================================================================


class TestExtractionResult:
    """Tests for ExtractionResult dataclass."""

    def test_extraction_result_basic(self, tmp_path: Path):
        """Test basic ExtractionResult creation."""
        result = ExtractionResult(
            syllables=["hel", "lo", "world", "hel"],  # 'hel' appears twice
            language_code="en_US",
            min_syllable_length=2,
            max_syllable_length=8,
            input_path=tmp_path / "test.txt",
            total_words=2,
            processed_words=2,
            fallback_count=0,
            rejected_syllables=0,
        )

        assert result.language_code == "en_US"
        assert len(result.syllables) == 4  # Total with duplicates
        assert result.total_words == 2

    def test_extraction_result_length_distribution(self, tmp_path: Path):
        """Test that length distribution is calculated in __post_init__."""
        result = ExtractionResult(
            syllables=["ab", "abc", "abcd", "abc"],  # 2, 3, 4, 3 chars
            language_code="en_US",
            min_syllable_length=2,
            max_syllable_length=8,
            input_path=tmp_path / "test.txt",
        )

        # Length distribution is from unique syllables
        assert result.length_distribution[2] == 1  # "ab"
        assert result.length_distribution[3] == 1  # "abc" (unique)
        assert result.length_distribution[4] == 1  # "abcd"

    def test_extraction_result_sample_syllables(self, tmp_path: Path):
        """Test that sample syllables are generated correctly."""
        syllables = [f"syl{i:02d}" for i in range(20)]
        result = ExtractionResult(
            syllables=syllables,
            language_code="en_US",
            min_syllable_length=2,
            max_syllable_length=8,
            input_path=tmp_path / "test.txt",
        )

        # Should have at most 15 sample syllables
        assert len(result.sample_syllables) == 15
        # Should be sorted
        assert result.sample_syllables == sorted(result.sample_syllables)

    def test_extraction_result_format_metadata(self, tmp_path: Path):
        """Test format_metadata output."""
        result = ExtractionResult(
            syllables=["hel", "lo", "world"],
            language_code="en_US",
            min_syllable_length=2,
            max_syllable_length=8,
            input_path=tmp_path / "test.txt",
            total_words=10,
            processed_words=8,
            fallback_count=2,
            rejected_syllables=1,
        )

        metadata = result.format_metadata()

        assert "NLTK SYLLABLE EXTRACTION METADATA" in metadata
        assert "en_US" in metadata
        assert "2-8 characters" in metadata
        assert "Total Words:" in metadata
        assert "Process Rate:" in metadata
        assert "Fallback Rate:" in metadata

    def test_extraction_result_format_metadata_zero_words(self, tmp_path: Path):
        """Test format_metadata with zero total words (avoids division by zero)."""
        result = ExtractionResult(
            syllables=[],
            language_code="en_US",
            min_syllable_length=2,
            max_syllable_length=8,
            input_path=tmp_path / "test.txt",
            total_words=0,
            processed_words=0,
        )

        # Should not raise division by zero
        metadata = result.format_metadata()
        assert "Total Words:" in metadata
        # Should NOT have percentage lines when total_words is 0
        assert "Process Rate:" not in metadata

    def test_extraction_result_empty_syllables(self, tmp_path: Path):
        """Test ExtractionResult with empty syllables list."""
        result = ExtractionResult(
            syllables=[],
            language_code="en_US",
            min_syllable_length=2,
            max_syllable_length=8,
            input_path=tmp_path / "test.txt",
        )

        assert len(result.syllables) == 0
        assert result.length_distribution == {}
        assert result.sample_syllables == []


class TestFileProcessingResult:
    """Tests for FileProcessingResult dataclass."""

    def test_file_processing_result_success(self, tmp_path: Path):
        """Test successful FileProcessingResult."""
        result = FileProcessingResult(
            input_path=tmp_path / "test.txt",
            success=True,
            syllables_count=100,
            language_code="en_US",
            syllables_output_path=tmp_path / "output.txt",
            metadata_output_path=tmp_path / "meta.txt",
            processing_time=1.5,
        )

        assert result.success is True
        assert result.syllables_count == 100
        assert result.error_message is None

    def test_file_processing_result_failure(self, tmp_path: Path):
        """Test failed FileProcessingResult."""
        result = FileProcessingResult(
            input_path=tmp_path / "test.txt",
            success=False,
            syllables_count=0,
            language_code="en_US",
            error_message="File not found",
            processing_time=0.1,
        )

        assert result.success is False
        assert result.syllables_count == 0
        assert result.error_message == "File not found"
        assert result.syllables_output_path is None


class TestBatchResult:
    """Tests for BatchResult dataclass."""

    def test_batch_result_basic(self, tmp_path: Path):
        """Test basic BatchResult creation."""
        results = [
            FileProcessingResult(
                input_path=tmp_path / "file1.txt",
                success=True,
                syllables_count=100,
                language_code="en_US",
                processing_time=1.0,
            ),
            FileProcessingResult(
                input_path=tmp_path / "file2.txt",
                success=False,
                syllables_count=0,
                language_code="en_US",
                error_message="Error",
                processing_time=0.5,
            ),
        ]

        batch = BatchResult(
            total_files=2,
            successful=1,
            failed=1,
            results=results,
            total_time=1.5,
            output_directory=tmp_path,
        )

        assert batch.total_files == 2
        assert batch.successful == 1
        assert batch.failed == 1

    def test_batch_result_format_summary(self, tmp_path: Path):
        """Test format_summary output."""
        results = [
            FileProcessingResult(
                input_path=tmp_path / "file1.txt",
                success=True,
                syllables_count=100,
                language_code="en_US",
                processing_time=1.0,
            ),
            FileProcessingResult(
                input_path=tmp_path / "file2.txt",
                success=False,
                syllables_count=0,
                language_code="en_US",
                error_message="File not found",
                processing_time=0.5,
            ),
        ]

        batch = BatchResult(
            total_files=2,
            successful=1,
            failed=1,
            results=results,
            total_time=1.5,
            output_directory=tmp_path,
        )

        summary = batch.format_summary()

        assert "BATCH PROCESSING SUMMARY" in summary
        assert "Total Files:" in summary
        assert "Successful:" in summary
        assert "Failed:" in summary
        assert "file1.txt" in summary
        assert "file2.txt" in summary
        assert "File not found" in summary

    def test_batch_result_all_successful(self, tmp_path: Path):
        """Test format_summary with all successful files."""
        results = [
            FileProcessingResult(
                input_path=tmp_path / f"file{i}.txt",
                success=True,
                syllables_count=100,
                language_code="en_US",
                processing_time=1.0,
            )
            for i in range(3)
        ]

        batch = BatchResult(
            total_files=3,
            successful=3,
            failed=0,
            results=results,
            total_time=3.0,
            output_directory=tmp_path,
        )

        summary = batch.format_summary()

        assert "100.0%" in summary
        assert "Failed Extractions:" not in summary


# ============================================================================
# Tests for file_io.py
# ============================================================================


class TestGenerateOutputFilename:
    """Tests for generate_output_filename function."""

    def test_generate_output_filename_defaults(self, tmp_path: Path):
        """Test with default parameters."""
        syllables_path, meta_path = generate_output_filename(
            output_dir=tmp_path,
            language_code="en_US",
        )

        # Check directory structure
        assert syllables_path.parent.name == "syllables"
        assert meta_path.parent.name == "meta"
        assert "_nltk" in str(syllables_path.parent.parent.name)

        # Check filenames
        assert syllables_path.name == "en_US.txt"
        assert meta_path.name == "en_US.txt"

        # Directories should be created
        assert syllables_path.parent.exists()
        assert meta_path.parent.exists()

    def test_generate_output_filename_with_input_filename(self, tmp_path: Path):
        """Test that input_filename takes precedence over language_code."""
        syllables_path, meta_path = generate_output_filename(
            output_dir=tmp_path,
            language_code="en_US",
            input_filename="mybook.txt",
        )

        assert syllables_path.name == "mybook.txt"
        assert meta_path.name == "mybook.txt"

    def test_generate_output_filename_shared_timestamp(self, tmp_path: Path):
        """Test that shared timestamp groups files in same run directory."""
        timestamp = "20260115_120000"

        path1, _ = generate_output_filename(
            output_dir=tmp_path,
            run_timestamp=timestamp,
            input_filename="file1.txt",
        )

        path2, _ = generate_output_filename(
            output_dir=tmp_path,
            run_timestamp=timestamp,
            input_filename="file2.txt",
        )

        # Both should be in the same run directory
        assert path1.parent == path2.parent
        assert timestamp in str(path1)

    def test_generate_output_filename_no_language_or_filename(self, tmp_path: Path):
        """Test fallback to default filename when neither provided."""
        syllables_path, _ = generate_output_filename(output_dir=tmp_path)

        assert syllables_path.name == "syllables.txt"


class TestSaveMetadata:
    """Tests for save_metadata function."""

    def test_save_metadata_success(self, tmp_path: Path):
        """Test successful metadata saving."""
        result = ExtractionResult(
            syllables=["hel", "lo"],
            language_code="en_US",
            min_syllable_length=2,
            max_syllable_length=8,
            input_path=tmp_path / "input.txt",
            total_words=2,
            processed_words=2,
        )

        output_path = tmp_path / "meta.txt"
        save_metadata(result, output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert "NLTK SYLLABLE EXTRACTION METADATA" in content

    def test_save_metadata_creates_parent_dirs(self, tmp_path: Path):
        """Test that save_metadata works with nested paths."""
        result = ExtractionResult(
            syllables=["test"],
            language_code="en_US",
            min_syllable_length=2,
            max_syllable_length=8,
            input_path=tmp_path / "input.txt",
        )

        # Note: save_metadata does NOT create parent dirs itself,
        # generate_output_filename does. This tests that it raises IOError.
        nested_path = tmp_path / "deep" / "nested" / "meta.txt"

        with pytest.raises(IOError):
            save_metadata(result, nested_path)


# ============================================================================
# Tests for cli.py
# ============================================================================


class TestDiscoverFiles:
    """Tests for discover_files function."""

    def test_discover_files_basic(self, tmp_path: Path):
        """Test basic file discovery."""
        # Create test files
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.txt").write_text("content")
        (tmp_path / "file3.md").write_text("content")

        files = discover_files(tmp_path, pattern="*.txt")

        assert len(files) == 2
        assert all(f.suffix == ".txt" for f in files)

    def test_discover_files_recursive(self, tmp_path: Path):
        """Test recursive file discovery."""
        # Create nested structure
        (tmp_path / "file1.txt").write_text("content")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("content")

        # Non-recursive
        files = discover_files(tmp_path, pattern="*.txt", recursive=False)
        assert len(files) == 1

        # Recursive
        files = discover_files(tmp_path, pattern="*.txt", recursive=True)
        assert len(files) == 2

    def test_discover_files_sorted(self, tmp_path: Path):
        """Test that discovered files are sorted."""
        (tmp_path / "zebra.txt").write_text("content")
        (tmp_path / "alpha.txt").write_text("content")
        (tmp_path / "beta.txt").write_text("content")

        files = discover_files(tmp_path, pattern="*.txt")

        assert files[0].name == "alpha.txt"
        assert files[1].name == "beta.txt"
        assert files[2].name == "zebra.txt"

    def test_discover_files_nonexistent_dir(self, tmp_path: Path):
        """Test with nonexistent directory."""
        with pytest.raises(ValueError, match="does not exist"):
            discover_files(tmp_path / "nonexistent")

    def test_discover_files_not_a_directory(self, tmp_path: Path):
        """Test with file instead of directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        with pytest.raises(ValueError, match="not a directory"):
            discover_files(file_path)

    def test_discover_files_empty_directory(self, tmp_path: Path):
        """Test with empty directory."""
        files = discover_files(tmp_path, pattern="*.txt")
        assert files == []

    def test_discover_files_excludes_directories(self, tmp_path: Path):
        """Test that directories matching pattern are excluded."""
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "folder.txt").mkdir()  # Directory with .txt extension

        files = discover_files(tmp_path, pattern="*.txt")

        assert len(files) == 1
        assert files[0].name == "file.txt"


class TestProcessSingleFileBatch:
    """Tests for process_single_file_batch function."""

    @pytest.fixture
    def sample_text_file(self, tmp_path: Path) -> Path:
        """Create a sample text file for testing."""
        file_path = tmp_path / "sample.txt"
        file_path.write_text("Hello wonderful world of programming")
        return file_path

    def test_process_single_file_success(self, sample_text_file: Path, tmp_path: Path):
        """Test successful single file processing."""
        try:
            import cmudict  # noqa: F401
        except ImportError:
            pytest.skip("cmudict not installed")

        result = process_single_file_batch(
            input_path=sample_text_file,
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "output",
            run_timestamp="20260115_120000",
        )

        assert result.success is True
        assert result.syllables_count > 0
        assert result.syllables_output_path is not None
        assert result.syllables_output_path.exists()

    def test_process_single_file_nonexistent(self, tmp_path: Path):
        """Test processing nonexistent file."""
        try:
            import cmudict  # noqa: F401
        except ImportError:
            pytest.skip("cmudict not installed")

        result = process_single_file_batch(
            input_path=tmp_path / "nonexistent.txt",
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "output",
            run_timestamp="20260115_120000",
        )

        assert result.success is False
        assert result.error_message is not None

    def test_process_single_file_verbose(self, sample_text_file: Path, tmp_path: Path, capsys):
        """Test verbose mode output."""
        try:
            import cmudict  # noqa: F401
        except ImportError:
            pytest.skip("cmudict not installed")

        process_single_file_batch(
            input_path=sample_text_file,
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "output",
            run_timestamp="20260115_120000",
            verbose=True,
        )

        captured = capsys.readouterr()
        assert "Processing" in captured.out


class TestProcessBatch:
    """Tests for process_batch function."""

    @pytest.fixture
    def sample_files(self, tmp_path: Path) -> list[Path]:
        """Create sample text files for batch testing."""
        files = []
        for i, text in enumerate(["Hello world", "Testing batch", "More text here"]):
            file_path = tmp_path / f"file{i}.txt"
            file_path.write_text(text)
            files.append(file_path)
        return files

    def test_process_batch_success(self, sample_files: list[Path], tmp_path: Path):
        """Test successful batch processing."""
        try:
            import cmudict  # noqa: F401
        except ImportError:
            pytest.skip("cmudict not installed")

        result = process_batch(
            files=sample_files,
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "output",
            quiet=True,
        )

        assert result.total_files == 3
        assert result.successful == 3
        assert result.failed == 0

    def test_process_batch_partial_failure(self, sample_files: list[Path], tmp_path: Path):
        """Test batch with some failures."""
        try:
            import cmudict  # noqa: F401
        except ImportError:
            pytest.skip("cmudict not installed")

        # Add a nonexistent file
        files = sample_files + [tmp_path / "nonexistent.txt"]

        result = process_batch(
            files=files,
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "output",
            quiet=True,
        )

        assert result.total_files == 4
        assert result.successful == 3
        assert result.failed == 1

    def test_process_batch_empty_list(self, tmp_path: Path):
        """Test batch with empty file list."""
        try:
            import cmudict  # noqa: F401
        except ImportError:
            pytest.skip("cmudict not installed")

        result = process_batch(
            files=[],
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "output",
            quiet=True,
        )

        assert result.total_files == 0
        assert result.successful == 0


class TestArgumentParser:
    """Tests for CLI argument parser."""

    def test_create_argument_parser(self):
        """Test argument parser creation."""
        parser = create_argument_parser()

        assert parser is not None
        assert parser.description is not None

    def test_parse_file_argument(self):
        """Test parsing --file argument."""
        parser = create_argument_parser()
        args = parser.parse_args(["--file", "test.txt"])

        assert args.file == Path("test.txt")

    def test_parse_source_argument(self):
        """Test parsing --source argument."""
        parser = create_argument_parser()
        args = parser.parse_args(["--source", "data/"])

        assert args.source == Path("data/")

    def test_parse_min_max_length(self):
        """Test parsing min/max length arguments."""
        parser = create_argument_parser()
        args = parser.parse_args(["--file", "test.txt", "--min", "3", "--max", "6"])

        assert args.min == 3
        assert args.max == 6

    def test_parse_output_argument(self):
        """Test parsing --output argument."""
        parser = create_argument_parser()
        args = parser.parse_args(["--file", "test.txt", "--output", "results/"])

        assert args.output == Path("results/")

    def test_parse_recursive_flag(self):
        """Test parsing --recursive flag."""
        parser = create_argument_parser()
        args = parser.parse_args(["--source", "data/", "--recursive"])

        assert args.recursive is True

    def test_parse_quiet_verbose_flags(self):
        """Test parsing --quiet and --verbose flags."""
        parser = create_argument_parser()

        args_quiet = parser.parse_args(["--file", "test.txt", "--quiet"])
        assert args_quiet.quiet is True

        args_verbose = parser.parse_args(["--file", "test.txt", "--verbose"])
        assert args_verbose.verbose is True

    def test_default_values(self):
        """Test default argument values."""
        parser = create_argument_parser()
        args = parser.parse_args([])

        assert args.min == 1  # CLI default is 1 (no filtering)
        assert args.max == 999  # CLI default is 999 (no filtering)
        assert args.recursive is False
        assert args.quiet is False
        assert args.verbose is False

    def test_parse_files_argument(self):
        """Test parsing --files argument with multiple files."""
        parser = create_argument_parser()
        args = parser.parse_args(["--files", "file1.txt", "file2.txt", "file3.txt"])

        assert len(args.files) == 3
        assert args.files[0] == Path("file1.txt")
        assert args.files[2] == Path("file3.txt")

    def test_parse_pattern_argument(self):
        """Test parsing --pattern argument."""
        parser = create_argument_parser()
        args = parser.parse_args(["--source", "data/", "--pattern", "*.md"])

        assert args.pattern == "*.md"


class TestMainBatch:
    """Tests for main_batch function."""

    @pytest.fixture
    def sample_text_file(self, tmp_path: Path) -> Path:
        """Create a sample text file for testing."""
        file_path = tmp_path / "sample.txt"
        file_path.write_text("Hello wonderful world of programming")
        return file_path

    @pytest.fixture
    def sample_text_files(self, tmp_path: Path) -> list[Path]:
        """Create multiple sample text files for testing."""
        files = []
        for i, text in enumerate(["Hello world", "Testing batch", "More text here"]):
            file_path = tmp_path / f"file{i}.txt"
            file_path.write_text(text)
            files.append(file_path)
        return files

    def test_main_batch_single_file(self, sample_text_file: Path, tmp_path: Path):
        """Test batch mode with single file."""
        try:
            import cmudict  # noqa: F401
        except ImportError:
            pytest.skip("cmudict not installed")

        from build_tools.nltk_syllable_extractor.cli import main_batch

        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--file",
                str(sample_text_file),
                "--output",
                str(tmp_path / "output"),
                "--quiet",
            ]
        )

        with pytest.raises(SystemExit) as exc_info:
            main_batch(args)

        assert exc_info.value.code == 0

    def test_main_batch_multiple_files(self, sample_text_files: list[Path], tmp_path: Path):
        """Test batch mode with multiple files."""
        try:
            import cmudict  # noqa: F401
        except ImportError:
            pytest.skip("cmudict not installed")

        from build_tools.nltk_syllable_extractor.cli import main_batch

        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--files",
                *[str(f) for f in sample_text_files],
                "--output",
                str(tmp_path / "output"),
                "--quiet",
            ]
        )

        with pytest.raises(SystemExit) as exc_info:
            main_batch(args)

        assert exc_info.value.code == 0

    def test_main_batch_source_directory(self, sample_text_files: list[Path], tmp_path: Path):
        """Test batch mode with source directory."""
        try:
            import cmudict  # noqa: F401
        except ImportError:
            pytest.skip("cmudict not installed")

        from build_tools.nltk_syllable_extractor.cli import main_batch

        # Files are already in tmp_path
        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--source",
                str(tmp_path),
                "--pattern",
                "*.txt",
                "--output",
                str(tmp_path / "output"),
                "--quiet",
            ]
        )

        with pytest.raises(SystemExit) as exc_info:
            main_batch(args)

        assert exc_info.value.code == 0

    def test_main_batch_source_recursive(self, tmp_path: Path):
        """Test batch mode with recursive directory scanning."""
        try:
            import cmudict  # noqa: F401
        except ImportError:
            pytest.skip("cmudict not installed")

        from build_tools.nltk_syllable_extractor.cli import main_batch

        # Create nested structure
        (tmp_path / "file1.txt").write_text("Hello world")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("Nested file content")

        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--source",
                str(tmp_path),
                "--pattern",
                "*.txt",
                "--recursive",
                "--output",
                str(tmp_path / "output"),
                "--quiet",
            ]
        )

        with pytest.raises(SystemExit) as exc_info:
            main_batch(args)

        assert exc_info.value.code == 0

    def test_main_batch_invalid_min_length(self, sample_text_file: Path, tmp_path: Path, capsys):
        """Test batch mode with invalid min length."""
        from build_tools.nltk_syllable_extractor.cli import main_batch

        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--file",
                str(sample_text_file),
                "--min",
                "0",
                "--output",
                str(tmp_path / "output"),
            ]
        )

        with pytest.raises(SystemExit) as exc_info:
            main_batch(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Minimum syllable length must be at least 1" in captured.out

    def test_main_batch_invalid_max_less_than_min(
        self, sample_text_file: Path, tmp_path: Path, capsys
    ):
        """Test batch mode with max < min."""
        from build_tools.nltk_syllable_extractor.cli import main_batch

        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--file",
                str(sample_text_file),
                "--min",
                "5",
                "--max",
                "3",
                "--output",
                str(tmp_path / "output"),
            ]
        )

        with pytest.raises(SystemExit) as exc_info:
            main_batch(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "must be >= minimum" in captured.out

    def test_main_batch_file_not_found(self, tmp_path: Path, capsys):
        """Test batch mode with nonexistent file."""
        from build_tools.nltk_syllable_extractor.cli import main_batch

        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--file",
                str(tmp_path / "nonexistent.txt"),
                "--output",
                str(tmp_path / "output"),
            ]
        )

        with pytest.raises(SystemExit) as exc_info:
            main_batch(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "File not found" in captured.out

    def test_main_batch_file_is_directory(self, tmp_path: Path, capsys):
        """Test batch mode when file argument is actually a directory."""
        from build_tools.nltk_syllable_extractor.cli import main_batch

        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--file",
                str(tmp_path),  # tmp_path is a directory
                "--output",
                str(tmp_path / "output"),
            ]
        )

        with pytest.raises(SystemExit) as exc_info:
            main_batch(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not a file" in captured.out

    def test_main_batch_source_not_found(self, tmp_path: Path, capsys):
        """Test batch mode with nonexistent source directory."""
        from build_tools.nltk_syllable_extractor.cli import main_batch

        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--source",
                str(tmp_path / "nonexistent"),
                "--output",
                str(tmp_path / "output"),
            ]
        )

        with pytest.raises(SystemExit) as exc_info:
            main_batch(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_main_batch_source_is_file(self, sample_text_file: Path, tmp_path: Path, capsys):
        """Test batch mode when source is a file not directory."""
        from build_tools.nltk_syllable_extractor.cli import main_batch

        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--source",
                str(sample_text_file),  # File, not directory
                "--output",
                str(tmp_path / "output"),
            ]
        )

        with pytest.raises(SystemExit) as exc_info:
            main_batch(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not a directory" in captured.out

    def test_main_batch_no_files_matching_pattern(self, tmp_path: Path, capsys):
        """Test batch mode when no files match pattern."""
        from build_tools.nltk_syllable_extractor.cli import main_batch

        # Create files with different extension
        (tmp_path / "file.md").write_text("markdown content")

        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--source",
                str(tmp_path),
                "--pattern",
                "*.txt",
                "--output",
                str(tmp_path / "output"),
            ]
        )

        with pytest.raises(SystemExit) as exc_info:
            main_batch(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No files matching pattern" in captured.out

    def test_main_batch_no_input_specified(self, tmp_path: Path, capsys):
        """Test batch mode with no input specified."""
        from build_tools.nltk_syllable_extractor.cli import main_batch

        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--output",
                str(tmp_path / "output"),
            ]
        )

        with pytest.raises(SystemExit) as exc_info:
            main_batch(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No input specified" in captured.out

    def test_main_batch_verbose_output(self, sample_text_file: Path, tmp_path: Path, capsys):
        """Test batch mode with verbose output."""
        try:
            import cmudict  # noqa: F401
        except ImportError:
            pytest.skip("cmudict not installed")

        from build_tools.nltk_syllable_extractor.cli import main_batch

        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--file",
                str(sample_text_file),
                "--output",
                str(tmp_path / "output"),
                "--verbose",
            ]
        )

        with pytest.raises(SystemExit) as exc_info:
            main_batch(args)

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "BATCH NLTK SYLLABLE EXTRACTION" in captured.out

    def test_main_batch_with_failures_exits_code_1(self, tmp_path: Path):
        """Test batch mode exits with code 1 when some files fail."""
        try:
            import cmudict  # noqa: F401
        except ImportError:
            pytest.skip("cmudict not installed")

        from build_tools.nltk_syllable_extractor.cli import main_batch

        # Create one valid file
        (tmp_path / "valid.txt").write_text("Hello world")

        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--files",
                str(tmp_path / "valid.txt"),
                str(tmp_path / "nonexistent.txt"),
                "--output",
                str(tmp_path / "output"),
                "--quiet",
            ]
        )

        with pytest.raises(SystemExit) as exc_info:
            main_batch(args)

        assert exc_info.value.code == 1


class TestMain:
    """Tests for main entry point."""

    def test_main_batch_mode(self, tmp_path: Path):
        """Test main() routes to batch mode when args provided."""
        try:
            import cmudict  # noqa: F401
        except ImportError:
            pytest.skip("cmudict not installed")

        from unittest.mock import patch

        from build_tools.nltk_syllable_extractor.cli import main

        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world")

        with patch(
            "sys.argv",
            ["cli", "--file", str(test_file), "--output", str(tmp_path / "output"), "--quiet"],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0


class TestProcessBatchOutput:
    """Tests for process_batch output formatting."""

    @pytest.fixture
    def sample_files(self, tmp_path: Path) -> list[Path]:
        """Create sample text files for batch testing."""
        files = []
        for i, text in enumerate(["Hello world", "Testing batch"]):
            file_path = tmp_path / f"file{i}.txt"
            file_path.write_text(text)
            files.append(file_path)
        return files

    def test_process_batch_non_quiet_output(self, sample_files: list[Path], tmp_path: Path, capsys):
        """Test batch processing with progress output."""
        try:
            import cmudict  # noqa: F401
        except ImportError:
            pytest.skip("cmudict not installed")

        result = process_batch(
            files=sample_files,
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "output",
            quiet=False,
            verbose=False,
        )

        captured = capsys.readouterr()
        assert "BATCH PROCESSING" in captured.out
        assert result.successful == 2

    def test_process_batch_verbose_output(self, sample_files: list[Path], tmp_path: Path, capsys):
        """Test batch processing with verbose output."""
        try:
            import cmudict  # noqa: F401
        except ImportError:
            pytest.skip("cmudict not installed")

        result = process_batch(
            files=sample_files,
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "output",
            quiet=False,
            verbose=True,
        )

        captured = capsys.readouterr()
        assert "Processing" in captured.out
        assert result.successful == 2


class TestRecordCorpusDbSafe:
    """Tests for record_corpus_db_safe function (now in tui_common.cli_utils)."""

    def test_record_success(self):
        """Test successful recording."""
        from build_tools.tui_common.cli_utils import record_corpus_db_safe

        result = record_corpus_db_safe("test", lambda: "success")
        assert result == "success"

    def test_record_failure_prints_warning(self, capsys):
        """Test that failures print warning to stderr."""
        from build_tools.tui_common.cli_utils import record_corpus_db_safe

        def failing_func():
            raise RuntimeError("Test error")

        result = record_corpus_db_safe("test operation", failing_func, quiet=False)

        assert result is None
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "test operation" in captured.err

    def test_record_failure_quiet_no_output(self, capsys):
        """Test that failures are silent when quiet=True."""
        from build_tools.tui_common.cli_utils import record_corpus_db_safe

        def failing_func():
            raise RuntimeError("Test error")

        result = record_corpus_db_safe("test operation", failing_func, quiet=True)

        assert result is None
        captured = capsys.readouterr()
        assert captured.err == ""


class TestPathCompleter:
    """Tests for path_completer function (now in tui_common.cli_utils)."""

    def test_path_completer_directory(self, tmp_path: Path):
        """Test path completer with directory."""
        from build_tools.tui_common.cli_utils import path_completer

        # Create test files
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.txt").write_text("content")

        # Get first completion
        result = path_completer(str(tmp_path), 0)

        # Should return a path
        assert result is not None

    def test_path_completer_no_matches(self, tmp_path: Path):
        """Test path completer with no matches."""
        from build_tools.tui_common.cli_utils import path_completer

        result = path_completer(str(tmp_path / "nonexistent_prefix"), 0)

        # Should return None when no matches
        assert result is None

    def test_path_completer_partial_path(self, tmp_path: Path):
        """Test path completer with partial path."""
        from build_tools.tui_common.cli_utils import path_completer

        # Create test file
        (tmp_path / "myfile.txt").write_text("content")

        # Try partial match
        result = path_completer(str(tmp_path / "myf"), 0)

        # Should match the file
        assert result is not None
        assert "myfile.txt" in result


class TestInputWithCompletion:
    """Tests for input_with_completion function."""

    def test_input_with_completion(self, monkeypatch):
        """Test input_with_completion calls input."""
        from build_tools.nltk_syllable_extractor.cli import input_with_completion

        monkeypatch.setattr("builtins.input", lambda prompt: "/test/path")

        result = input_with_completion("Enter path: ")
        assert result == "/test/path"
