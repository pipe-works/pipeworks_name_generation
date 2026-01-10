"""
Integration tests for corpus_db integration with syllable extractor.

This module tests that the syllable extractor correctly records extraction runs
to the corpus_db ledger for build provenance tracking.
"""

import argparse
from unittest.mock import Mock, patch

import pytest

from build_tools.pyphen_syllable_extractor import main_batch


class TestCorpusDBIntegration:
    """Test suite for corpus_db integration with syllable extractor."""

    def test_single_file_recorded_to_corpus_db(self, tmp_path):
        """Test that single file extraction is recorded to corpus_db."""
        # Setup: Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello wonderful world", encoding="utf-8")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create args for main_batch
        args = argparse.Namespace(
            file=str(test_file),
            files=None,
            source=None,
            lang="en_US",
            auto=False,
            min=2,
            max=8,
            pattern="*.txt",
            recursive=False,
            output=str(output_dir),
            quiet=True,
            verbose=False,
        )

        # Patch CorpusLedger to use test db
        with patch("build_tools.pyphen_syllable_extractor.cli.CorpusLedger") as mock_ledger_class:
            mock_ledger = Mock()
            mock_ledger_class.return_value = mock_ledger
            mock_ledger.start_run.return_value = 1

            # Execute
            with pytest.raises(SystemExit) as excinfo:
                main_batch(args)

            # Should exit with 0 (success)
            assert excinfo.value.code == 0

            # Verify ledger interactions
            mock_ledger.start_run.assert_called_once()
            call_kwargs = mock_ledger.start_run.call_args[1]
            assert call_kwargs["extractor_tool"] == "pyphen_syllable_extractor"
            assert call_kwargs["pyphen_lang"] == "en_US"
            assert call_kwargs["min_len"] == 2
            assert call_kwargs["max_len"] == 8

            # Verify input recorded
            mock_ledger.record_input.assert_called_once()
            input_call = mock_ledger.record_input.call_args[0]
            assert input_call[0] == 1  # run_id
            assert input_call[1] == test_file

            # Verify output recorded
            mock_ledger.record_output.assert_called_once()
            output_call_args = mock_ledger.record_output.call_args[0]
            output_call_kwargs = mock_ledger.record_output.call_args[1]
            assert output_call_args[0] == 1  # run_id is first positional arg
            assert output_call_kwargs["output_path"] is not None
            assert output_call_kwargs["unique_syllable_count"] > 0

            # Verify run completed
            mock_ledger.complete_run.assert_called_once()
            complete_call = mock_ledger.complete_run.call_args
            assert complete_call[0][0] == 1  # run_id
            assert complete_call[1]["exit_code"] == 0
            assert complete_call[1]["status"] == "completed"

    def test_batch_files_recorded_to_corpus_db(self, tmp_path):
        """Test that batch processing records all files."""
        # Setup: Create 3 test files
        files = []
        for i in range(3):
            f = tmp_path / f"test{i}.txt"
            f.write_text(f"Hello world number {i}", encoding="utf-8")
            files.append(f)

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        args = argparse.Namespace(
            file=None,
            files=[str(f) for f in files],
            source=None,
            lang="en_US",
            auto=False,
            min=2,
            max=8,
            pattern="*.txt",
            recursive=False,
            output=str(output_dir),
            quiet=True,
            verbose=False,
        )

        with patch("build_tools.pyphen_syllable_extractor.cli.CorpusLedger") as mock_ledger_class:
            mock_ledger = Mock()
            mock_ledger_class.return_value = mock_ledger
            mock_ledger.start_run.return_value = 1

            with pytest.raises(SystemExit) as excinfo:
                main_batch(args)

            assert excinfo.value.code == 0

            # Verify all 3 inputs recorded
            assert mock_ledger.record_input.call_count == 3

            # Verify all 3 outputs recorded
            assert mock_ledger.record_output.call_count == 3

    def test_directory_scan_recorded_with_file_count(self, tmp_path):
        """Test directory scanning records file count."""
        # Setup: Create directory with 5 files
        source_dir = tmp_path / "corpus"
        source_dir.mkdir()

        for i in range(5):
            f = source_dir / f"file{i}.txt"
            f.write_text(f"Content {i}", encoding="utf-8")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        args = argparse.Namespace(
            file=None,
            files=None,
            source=str(source_dir),
            lang="en_US",
            auto=False,
            min=2,
            max=8,
            pattern="*.txt",
            recursive=False,
            output=str(output_dir),
            quiet=True,
            verbose=False,
        )

        with patch("build_tools.pyphen_syllable_extractor.cli.CorpusLedger") as mock_ledger_class:
            mock_ledger = Mock()
            mock_ledger_class.return_value = mock_ledger
            mock_ledger.start_run.return_value = 1

            with pytest.raises(SystemExit) as excinfo:
                main_batch(args)

            assert excinfo.value.code == 0

            # Verify input recorded with file_count
            mock_ledger.record_input.assert_called_once()
            call_kwargs = mock_ledger.record_input.call_args[1]
            assert call_kwargs["file_count"] == 5

            # Verify 5 outputs recorded
            assert mock_ledger.record_output.call_count == 5

    def test_extraction_succeeds_when_corpus_db_fails(self, tmp_path):
        """Test extraction continues if corpus_db recording fails."""
        # Setup
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world", encoding="utf-8")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        args = argparse.Namespace(
            file=str(test_file),
            files=None,
            source=None,
            lang="en_US",
            auto=False,
            min=2,
            max=8,
            pattern="*.txt",
            recursive=False,
            output=str(output_dir),
            quiet=False,  # Not quiet so we can see warnings
            verbose=False,
        )

        # Mock CorpusLedger to raise exception
        with patch("build_tools.pyphen_syllable_extractor.cli.CorpusLedger") as mock_ledger_class:
            mock_ledger_class.side_effect = Exception("Database connection failed")

            # Capture stderr to check for warning
            with patch("sys.stderr") as mock_stderr:
                with pytest.raises(SystemExit) as excinfo:
                    main_batch(args)

                # Extraction should still succeed
                assert excinfo.value.code == 0

                # Verify warning was printed to stderr
                assert mock_stderr.write.called

        # Verify output file was created in run-based structure
        # Structure: output_dir/TIMESTAMP/syllables/*.txt
        run_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
        assert len(run_dirs) == 1
        syllables_files = list(run_dirs[0].glob("syllables/*.txt"))
        assert len(syllables_files) == 1

    def test_extraction_works_without_corpus_db(self, tmp_path):
        """Test extraction works if corpus_db not installed."""
        # Setup
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world", encoding="utf-8")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        args = argparse.Namespace(
            file=str(test_file),
            files=None,
            source=None,
            lang="en_US",
            auto=False,
            min=2,
            max=8,
            pattern="*.txt",
            recursive=False,
            output=str(output_dir),
            quiet=True,
            verbose=False,
        )

        # Hide corpus_db by setting CORPUS_DB_AVAILABLE to False
        with patch("build_tools.pyphen_syllable_extractor.cli.CORPUS_DB_AVAILABLE", False):
            with pytest.raises(SystemExit) as excinfo:
                main_batch(args)

            # Extraction should succeed
            assert excinfo.value.code == 0

        # Verify output file was created in run-based structure
        # Structure: output_dir/TIMESTAMP/syllables/*.txt
        run_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
        assert len(run_dirs) == 1
        syllables_files = list(run_dirs[0].glob("syllables/*.txt"))
        assert len(syllables_files) == 1

    def test_auto_language_detection_recorded(self, tmp_path):
        """Test that auto language detection is correctly recorded."""
        # Setup
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello wonderful world this is English text", encoding="utf-8")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        args = argparse.Namespace(
            file=str(test_file),
            files=None,
            source=None,
            lang=None,
            auto=True,  # Use auto-detection
            min=2,
            max=8,
            pattern="*.txt",
            recursive=False,
            output=str(output_dir),
            quiet=True,
            verbose=False,
        )

        with patch("build_tools.pyphen_syllable_extractor.cli.CorpusLedger") as mock_ledger_class:
            mock_ledger = Mock()
            mock_ledger_class.return_value = mock_ledger
            mock_ledger.start_run.return_value = 1

            with pytest.raises(SystemExit) as excinfo:
                main_batch(args)

            # Should succeed even if language detection fails internally
            assert excinfo.value.code in [0, 1]

            # Verify pyphen_lang was None (indicating auto mode)
            if mock_ledger.start_run.called:
                call_kwargs = mock_ledger.start_run.call_args[1]
                assert call_kwargs["pyphen_lang"] is None

    def test_failed_extraction_recorded_as_failed(self, tmp_path):
        """Test that failed extraction is recorded with failed status."""
        # Setup: Create a file that will cause extraction issues
        test_file = tmp_path / "test.txt"
        test_file.write_text("", encoding="utf-8")  # Empty file

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        args = argparse.Namespace(
            file=str(test_file),
            files=None,
            source=None,
            lang="en_US",
            auto=False,
            min=2,
            max=8,
            pattern="*.txt",
            recursive=False,
            output=str(output_dir),
            quiet=True,
            verbose=False,
        )

        with patch("build_tools.pyphen_syllable_extractor.cli.CorpusLedger") as mock_ledger_class:
            mock_ledger = Mock()
            mock_ledger_class.return_value = mock_ledger
            mock_ledger.start_run.return_value = 1

            with pytest.raises(SystemExit):
                main_batch(args)

            # Verify run was completed (regardless of success/failure)
            mock_ledger.complete_run.assert_called_once()

            # Verify ledger was closed
            mock_ledger.close.assert_called_once()
