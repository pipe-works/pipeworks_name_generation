"""
Comprehensive test suite for syllable extractor batch processing functionality.

This module tests the batch mode CLI, including:
- File discovery with pattern matching and recursion
- Single file batch processing with error handling
- Batch processing of multiple files
- Result aggregation and formatting
- Argument parsing and validation
- Main batch function integration
"""

import argparse
from datetime import datetime
from pathlib import Path

import pytest

from build_tools.pyphen_syllable_extractor import (
    BatchResult,
    FileProcessingResult,
    discover_files,
    main_batch,
    process_batch,
    process_single_file_batch,
)
from build_tools.pyphen_syllable_extractor.cli import create_argument_parser


class TestFileDiscovery:
    """Test suite for file discovery functionality."""

    def test_discover_files_basic(self, tmp_path):
        """Test basic file discovery in a directory."""
        # Create test files
        (tmp_path / "file1.txt").write_text("content1", encoding="utf-8")
        (tmp_path / "file2.txt").write_text("content2", encoding="utf-8")
        (tmp_path / "ignore.md").write_text("ignore", encoding="utf-8")

        files = discover_files(tmp_path, pattern="*.txt", recursive=False)

        assert len(files) == 2
        assert all(f.suffix == ".txt" for f in files)
        assert all(f.is_file() for f in files)

    def test_discover_files_recursive(self, tmp_path):
        """Test recursive file discovery."""
        # Create nested structure
        (tmp_path / "file1.txt").write_text("content1", encoding="utf-8")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("content2", encoding="utf-8")
        subsubdir = subdir / "subsubdir"
        subsubdir.mkdir()
        (subsubdir / "file3.txt").write_text("content3", encoding="utf-8")

        # Non-recursive
        files_nonrec = discover_files(tmp_path, pattern="*.txt", recursive=False)
        assert len(files_nonrec) == 1

        # Recursive
        files_rec = discover_files(tmp_path, pattern="*.txt", recursive=True)
        assert len(files_rec) == 3

    def test_discover_files_pattern_matching(self, tmp_path):
        """Test pattern matching with different extensions."""
        (tmp_path / "doc1.txt").write_text("content", encoding="utf-8")
        (tmp_path / "doc2.md").write_text("content", encoding="utf-8")
        (tmp_path / "doc3.rst").write_text("content", encoding="utf-8")

        txt_files = discover_files(tmp_path, pattern="*.txt")
        assert len(txt_files) == 1

        md_files = discover_files(tmp_path, pattern="*.md")
        assert len(md_files) == 1

        all_files = discover_files(tmp_path, pattern="*.*")
        assert len(all_files) == 3

    def test_discover_files_empty_directory(self, tmp_path):
        """Test discovery in empty directory."""
        files = discover_files(tmp_path, pattern="*.txt")
        assert len(files) == 0
        assert files == []

    def test_discover_files_nonexistent_directory(self):
        """Test that nonexistent directory raises ValueError."""
        with pytest.raises(ValueError, match="does not exist"):
            discover_files(Path("/nonexistent/path"))

    def test_discover_files_not_a_directory(self, tmp_path):
        """Test that file path (not directory) raises ValueError."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content", encoding="utf-8")

        with pytest.raises(ValueError, match="not a directory"):
            discover_files(test_file)

    def test_discover_files_deterministic_ordering(self, tmp_path):
        """Test that file discovery returns sorted results (deterministic)."""
        # Create files in random order
        (tmp_path / "c.txt").write_text("content", encoding="utf-8")
        (tmp_path / "a.txt").write_text("content", encoding="utf-8")
        (tmp_path / "b.txt").write_text("content", encoding="utf-8")

        files = discover_files(tmp_path, pattern="*.txt")

        # Should be sorted alphabetically
        assert files[0].name == "a.txt"
        assert files[1].name == "b.txt"
        assert files[2].name == "c.txt"

    def test_discover_files_filters_directories(self, tmp_path):
        """Test that directories are filtered out, only files returned."""
        (tmp_path / "file.txt").write_text("content", encoding="utf-8")
        (tmp_path / "subdir.txt").mkdir()  # Directory with .txt extension

        files = discover_files(tmp_path, pattern="*.txt")

        assert len(files) == 1
        assert files[0].is_file()
        assert files[0].name == "file.txt"


class TestSingleFileBatchProcessing:
    """Test suite for single file batch processing."""

    def test_process_single_file_success(self, tmp_path):
        """Test successful processing of a single file."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text(
            "Hello beautiful wonderful world magnificently spectacular", encoding="utf-8"
        )
        output_dir = tmp_path / "output"

        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        result = process_single_file_batch(
            input_path=test_file,
            language_code="en_US",
            min_len=2,
            max_len=8,
            output_dir=output_dir,
            run_timestamp=run_timestamp,
            verbose=False,
        )

        assert result.success is True
        assert result.syllables_count > 0
        assert result.language_code == "en_US"
        assert result.error_message is None
        assert result.syllables_output_path is not None
        assert result.metadata_output_path is not None
        assert result.syllables_output_path.exists()
        assert result.metadata_output_path.exists()

    def test_process_single_file_with_auto_detection(self, tmp_path):
        """Test processing with automatic language detection."""
        test_file = tmp_path / "test_german.txt"
        test_file.write_text(
            "Hallo Welt, dies wird ein wunderbarer Test der Spracherkennung",
            encoding="utf-8",
        )
        output_dir = tmp_path / "output"
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        result = process_single_file_batch(
            input_path=test_file,
            language_code="auto",
            min_len=2,
            max_len=8,
            output_dir=output_dir,
            run_timestamp=run_timestamp,
            verbose=False,
        )

        assert result.success is True
        assert result.language_code == "de_DE"
        assert result.syllables_count > 0

    def test_process_single_file_nonexistent_file(self, tmp_path):
        """Test that nonexistent file returns error result (doesn't raise)."""
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        result = process_single_file_batch(
            input_path=Path("/nonexistent/file.txt"),
            language_code="en_US",
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "output",
            run_timestamp=run_timestamp,
            verbose=False,
        )

        assert result.success is False
        assert result.error_message is not None
        assert result.syllables_count == 0

    def test_process_single_file_invalid_language(self, tmp_path):
        """Test that invalid language code returns error result."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world", encoding="utf-8")

        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        result = process_single_file_batch(
            input_path=test_file,
            language_code="invalid_lang",
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "output",
            run_timestamp=run_timestamp,
            verbose=False,
        )

        assert result.success is False
        assert result.error_message is not None
        assert "language" in result.error_message.lower()

    def test_process_single_file_verbose_output(self, tmp_path, capsys):
        """Test that verbose mode produces output."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello beautiful world", encoding="utf-8")
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        process_single_file_batch(
            input_path=test_file,
            language_code="en_US",
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "output",
            run_timestamp=run_timestamp,
            verbose=True,
        )

        captured = capsys.readouterr()
        assert len(captured.out) > 0  # Should have verbose output

    def test_process_single_file_processing_time(self, tmp_path):
        """Test that processing time is recorded."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world beautiful", encoding="utf-8")

        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        result = process_single_file_batch(
            input_path=test_file,
            language_code="en_US",
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "output",
            run_timestamp=run_timestamp,
            verbose=False,
        )

        assert result.processing_time >= 0.0
        assert result.processing_time < 10.0  # Should be reasonably fast


class TestBatchProcessing:
    """Test suite for batch processing of multiple files."""

    def test_process_batch_multiple_files(self, tmp_path):
        """Test processing multiple files successfully."""
        # Create test files
        files = []
        for i in range(3):
            test_file = tmp_path / f"test{i}.txt"
            test_file.write_text("Hello beautiful wonderful world", encoding="utf-8")
            files.append(test_file)

        output_dir = tmp_path / "output"

        result = process_batch(
            files=files,
            language_code="en_US",
            min_len=2,
            max_len=8,
            output_dir=output_dir,
            quiet=True,
            verbose=False,
        )

        assert result.total_files == 3
        assert result.successful == 3
        assert result.failed == 0
        assert len(result.results) == 3
        assert all(r.success for r in result.results)

    def test_process_batch_with_failures(self, tmp_path):
        """Test batch processing with some failures."""
        # Create mix of valid and invalid files
        valid_file = tmp_path / "valid.txt"
        valid_file.write_text("Hello beautiful world", encoding="utf-8")

        files = [
            valid_file,
            Path("/nonexistent/file.txt"),  # Will fail
            tmp_path / "another_valid.txt",
        ]
        files[2].write_text("Hello wonderful world", encoding="utf-8")

        result = process_batch(
            files=files,
            language_code="en_US",
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "output",
            quiet=True,
            verbose=False,
        )

        assert result.total_files == 3
        assert result.successful == 2
        assert result.failed == 1
        assert len(result.results) == 3

    def test_process_batch_creates_output_directory(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world", encoding="utf-8")

        output_dir = tmp_path / "new_output_dir"
        assert not output_dir.exists()

        process_batch(
            files=[test_file],
            language_code="en_US",
            min_len=2,
            max_len=8,
            output_dir=output_dir,
            quiet=True,
            verbose=False,
        )

        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_process_batch_quiet_mode(self, tmp_path, capsys):
        """Test that quiet mode suppresses output."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world", encoding="utf-8")

        process_batch(
            files=[test_file],
            language_code="en_US",
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "output",
            quiet=True,
            verbose=False,
        )

        captured = capsys.readouterr()
        assert len(captured.out) == 0  # Quiet mode should suppress output

    def test_process_batch_verbose_mode(self, tmp_path, capsys):
        """Test that verbose mode produces detailed output."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello beautiful world", encoding="utf-8")

        process_batch(
            files=[test_file],
            language_code="en_US",
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "output",
            quiet=False,
            verbose=True,
        )

        captured = capsys.readouterr()
        assert len(captured.out) > 0  # Should have output

    def test_process_batch_total_time_recorded(self, tmp_path):
        """Test that total processing time is recorded."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world", encoding="utf-8")

        result = process_batch(
            files=[test_file],
            language_code="en_US",
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "output",
            quiet=True,
            verbose=False,
        )

        assert result.total_time > 0.0
        assert result.total_time < 30.0  # Should be reasonably fast


class TestBatchResult:
    """Test suite for BatchResult dataclass and formatting."""

    def test_batch_result_format_summary(self, tmp_path):
        """Test that format_summary produces valid output."""
        results = [
            FileProcessingResult(
                input_path=tmp_path / "file1.txt",
                success=True,
                syllables_count=100,
                language_code="en_US",
                syllables_output_path=tmp_path / "out1.txt",
                metadata_output_path=tmp_path / "meta1.txt",
                processing_time=1.5,
            ),
            FileProcessingResult(
                input_path=tmp_path / "file2.txt",
                success=False,
                syllables_count=0,
                language_code="en_US",
                error_message="File not found",
                processing_time=0.1,
            ),
        ]

        batch_result = BatchResult(
            total_files=2,
            successful=1,
            failed=1,
            results=results,
            total_time=1.6,
            output_directory=tmp_path,
        )

        summary = batch_result.format_summary()

        assert "BATCH PROCESSING SUMMARY" in summary
        assert "Total Files:        2" in summary
        assert "Successful:         1" in summary
        assert "Failed:             1" in summary
        assert "file1.txt" in summary
        assert "file2.txt" in summary
        assert "File not found" in summary

    def test_batch_result_language_distribution(self, tmp_path):
        """Test that language distribution is shown when multiple languages."""
        results = [
            FileProcessingResult(
                input_path=tmp_path / "en.txt",
                success=True,
                syllables_count=100,
                language_code="en_US",
                processing_time=1.0,
            ),
            FileProcessingResult(
                input_path=tmp_path / "de.txt",
                success=True,
                syllables_count=150,
                language_code="de_DE",
                processing_time=1.2,
            ),
        ]

        batch_result = BatchResult(
            total_files=2,
            successful=2,
            failed=0,
            results=results,
            total_time=2.2,
            output_directory=tmp_path,
        )

        summary = batch_result.format_summary()

        assert "Language Distribution:" in summary
        assert "en_US" in summary
        assert "de_DE" in summary


class TestArgumentParser:
    """Test suite for argument parser configuration."""

    def test_argument_parser_single_file(self):
        """Test parsing single file argument."""
        parser = create_argument_parser()
        args = parser.parse_args(["--file", "test.txt", "--lang", "en_US"])

        assert args.file == Path("test.txt")
        assert args.lang == "en_US"
        assert args.files is None
        assert args.source is None

    def test_argument_parser_multiple_files(self):
        """Test parsing multiple files argument."""
        parser = create_argument_parser()
        args = parser.parse_args(["--files", "a.txt", "b.txt", "c.txt", "--auto"])

        assert args.files == [Path("a.txt"), Path("b.txt"), Path("c.txt")]
        assert args.auto is True
        assert args.file is None
        assert args.source is None

    def test_argument_parser_source_directory(self):
        """Test parsing source directory with options."""
        parser = create_argument_parser()
        args = parser.parse_args(
            ["--source", "/path/to/dir", "--pattern", "*.md", "--recursive", "--lang", "de_DE"]
        )

        assert args.source == Path("/path/to/dir")
        assert args.pattern == "*.md"
        assert args.recursive is True
        assert args.lang == "de_DE"

    def test_argument_parser_custom_parameters(self):
        """Test parsing custom min/max/output parameters."""
        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--file",
                "test.txt",
                "--lang",
                "en_US",
                "--min",
                "3",
                "--max",
                "6",
                "--output",
                "/custom/output",
            ]
        )

        assert args.min == 3
        assert args.max == 6
        assert args.output == Path("/custom/output")

    def test_argument_parser_flags(self):
        """Test parsing quiet and verbose flags."""
        parser = create_argument_parser()

        # Quiet flag
        args_quiet = parser.parse_args(["--file", "test.txt", "--lang", "en_US", "--quiet"])
        assert args_quiet.quiet is True

        # Verbose flag
        args_verbose = parser.parse_args(["--file", "test.txt", "--lang", "en_US", "--verbose"])
        assert args_verbose.verbose is True

    def test_argument_parser_defaults(self):
        """Test default values for optional arguments."""
        parser = create_argument_parser()
        args = parser.parse_args(["--file", "test.txt", "--lang", "en_US"])

        assert args.min == 2  # Default
        assert args.max == 8  # Default
        assert args.pattern == "*.txt"  # Default
        assert args.recursive is False  # Default
        assert args.quiet is False  # Default
        assert args.verbose is False  # Default


class TestMainBatchFunction:
    """Test suite for main_batch function integration."""

    def test_main_batch_validates_min_length(self, tmp_path):
        """Test that main_batch validates minimum syllable length."""
        args = argparse.Namespace(
            file=str(tmp_path / "test.txt"),
            files=None,
            source=None,
            lang="en_US",
            auto=False,
            min=0,  # Invalid: must be >= 1
            max=8,
            output=None,
            pattern="*.txt",
            recursive=False,
            quiet=True,
            verbose=False,
        )

        with pytest.raises(SystemExit) as excinfo:
            main_batch(args)

        assert excinfo.value.code == 1

    def test_main_batch_validates_max_length(self, tmp_path):
        """Test that main_batch validates max >= min."""
        args = argparse.Namespace(
            file=str(tmp_path / "test.txt"),
            files=None,
            source=None,
            lang="en_US",
            auto=False,
            min=5,
            max=3,  # Invalid: max < min
            output=None,
            pattern="*.txt",
            recursive=False,
            quiet=True,
            verbose=False,
        )

        with pytest.raises(SystemExit) as excinfo:
            main_batch(args)

        assert excinfo.value.code == 1

    def test_main_batch_requires_language(self, tmp_path):
        """Test that either --lang or --auto must be specified."""
        args = argparse.Namespace(
            file=str(tmp_path / "test.txt"),
            files=None,
            source=None,
            lang=None,  # Missing
            auto=False,  # Missing
            min=2,
            max=8,
            output=None,
            pattern="*.txt",
            recursive=False,
            quiet=True,
            verbose=False,
        )

        with pytest.raises(SystemExit) as excinfo:
            main_batch(args)

        assert excinfo.value.code == 1

    def test_main_batch_exit_code_on_failure(self, tmp_path):
        """Test that main_batch exits with code 1 when files fail."""
        # Create args pointing to nonexistent file
        args = argparse.Namespace(
            file="/nonexistent/file.txt",
            files=None,
            source=None,
            lang="en_US",
            auto=False,
            min=2,
            max=8,
            output=str(tmp_path / "output"),
            pattern="*.txt",
            recursive=False,
            quiet=True,
            verbose=False,
        )

        with pytest.raises(SystemExit) as excinfo:
            main_batch(args)

        # Should exit with 1 because file doesn't exist (validation error)
        assert excinfo.value.code == 1


class TestIntegration:
    """Integration tests for end-to-end batch processing workflows."""

    def test_end_to_end_batch_workflow(self, tmp_path):
        """Test complete batch processing workflow from files to results."""
        import time

        # Create test files
        (tmp_path / "en1.txt").write_text(
            "Hello beautiful wonderful world magnificently", encoding="utf-8"
        )
        (tmp_path / "en2.txt").write_text(
            "Programming computers technology digital amazing", encoding="utf-8"
        )

        output_dir = tmp_path / "output"

        # Discover files
        files = discover_files(tmp_path, pattern="*.txt", recursive=False)
        assert len(files) == 2

        # Process files individually with small delay to ensure unique timestamps
        results_list = []
        for file_path in files:
            run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            result = process_single_file_batch(
                input_path=file_path,
                language_code="en_US",
                min_len=2,
                max_len=8,
                output_dir=output_dir,
                run_timestamp=run_timestamp,
                verbose=False,
            )
            results_list.append(result)
            time.sleep(0.01)  # Small delay to ensure unique timestamps

        # Verify results
        assert all(r.success for r in results_list)
        assert len(results_list) == 2
        assert output_dir.exists()

        # Verify output files were created in run-based subdirectory structure
        # Each file gets its own run directory since they have unique timestamps
        run_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
        assert len(run_dirs) >= 1  # At least one run directory created

        # Check that syllables and meta subdirectories exist
        for run_dir in run_dirs:
            assert (run_dir / "syllables").exists()
            assert (run_dir / "meta").exists()

    def test_deterministic_batch_processing(self, tmp_path):
        """Test that batch processing is deterministic (same input = same output)."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello beautiful wonderful world", encoding="utf-8")

        # Process twice
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        result1 = process_single_file_batch(
            input_path=test_file,
            language_code="en_US",
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "out1",
            run_timestamp=run_timestamp,
            verbose=False,
        )

        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        result2 = process_single_file_batch(
            input_path=test_file,
            language_code="en_US",
            min_len=2,
            max_len=8,
            output_dir=tmp_path / "out2",
            run_timestamp=run_timestamp,
            verbose=False,
        )

        # Results should be identical (except for paths and timing)
        assert result1.success == result2.success
        assert result1.syllables_count == result2.syllables_count
        assert result1.language_code == result2.language_code

        # Read output files and verify content is identical
        assert result1.syllables_output_path is not None
        assert result2.syllables_output_path is not None
        syllables1 = result1.syllables_output_path.read_text(encoding="utf-8")
        syllables2 = result2.syllables_output_path.read_text(encoding="utf-8")
        assert syllables1 == syllables2
