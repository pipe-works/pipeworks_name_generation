"""
Tests for corpus_sqlite_builder CLI module.

Tests command-line argument parsing, main entry point, and conversion workflows.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from build_tools.corpus_sqlite_builder.cli import (
    create_argument_parser,
    main,
    parse_arguments,
    run_batch_conversion,
    run_single_conversion,
)


@pytest.fixture
def sample_annotated_data() -> list[dict]:
    """Sample annotated syllable data for testing."""
    return [
        {
            "syllable": "test",
            "frequency": 100,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": True,
                "contains_fricative": False,
                "contains_liquid": False,
                "contains_nasal": False,
                "short_vowel": True,
                "long_vowel": False,
                "ends_with_vowel": False,
                "ends_with_nasal": False,
                "ends_with_stop": True,
            },
        },
    ]


@pytest.fixture
def mock_corpus_dir(tmp_path: Path, sample_annotated_data: list[dict]) -> Path:
    """Create a mock corpus directory with annotated JSON."""
    corpus_dir = tmp_path / "20260114_000000_test"
    data_dir = corpus_dir / "data"
    data_dir.mkdir(parents=True)

    # Write annotated JSON
    json_path = data_dir / "test_syllables_annotated.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(sample_annotated_data, f)

    return corpus_dir


@pytest.fixture
def mock_batch_output_dir(tmp_path: Path, sample_annotated_data: list[dict]) -> Path:
    """Create a mock output directory with multiple corpora."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create two corpus directories
    for name in ["20260114_000000_pyphen", "20260114_000001_nltk"]:
        corpus_dir = output_dir / name
        data_dir = corpus_dir / "data"
        data_dir.mkdir(parents=True)

        json_path = data_dir / f"{name.split('_')[-1]}_syllables_annotated.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(sample_annotated_data, f)

    return output_dir


class TestArgumentParser:
    """Tests for argument parser creation and parsing."""

    def test_create_argument_parser(self):
        """Test argument parser is created with correct configuration."""
        parser = create_argument_parser()

        assert parser.prog == "python -m build_tools.corpus_sqlite_builder"
        assert parser.description is not None
        assert "Convert annotated JSON" in parser.description

    def test_parse_arguments_defaults(self):
        """Test default argument values."""
        # Parse with no arguments (will have corpus_dir as None)
        args = parse_arguments([])

        assert args.corpus_dir is None
        assert args.force is False
        assert args.batch is None
        assert args.batch_size == 10000
        assert args.dry_run is False

    def test_parse_arguments_corpus_dir(self, tmp_path: Path):
        """Test parsing corpus directory argument."""
        args = parse_arguments([str(tmp_path)])

        assert args.corpus_dir == tmp_path

    def test_parse_arguments_force_flag(self, tmp_path: Path):
        """Test parsing --force flag."""
        args = parse_arguments([str(tmp_path), "--force"])

        assert args.force is True

    def test_parse_arguments_batch_flag(self, tmp_path: Path):
        """Test parsing --batch flag."""
        args = parse_arguments(["--batch", str(tmp_path)])

        assert args.batch == tmp_path

    def test_parse_arguments_batch_size(self, tmp_path: Path):
        """Test parsing --batch-size argument."""
        args = parse_arguments([str(tmp_path), "--batch-size", "5000"])

        assert args.batch_size == 5000

    def test_parse_arguments_dry_run(self, tmp_path: Path):
        """Test parsing --dry-run flag."""
        args = parse_arguments([str(tmp_path), "--dry-run"])

        assert args.dry_run is True

    def test_parse_arguments_all_options(self, tmp_path: Path):
        """Test parsing all options together."""
        args = parse_arguments(
            [
                str(tmp_path),
                "--force",
                "--batch-size",
                "20000",
                "--dry-run",
            ]
        )

        assert args.corpus_dir == tmp_path
        assert args.force is True
        assert args.batch_size == 20000
        assert args.dry_run is True


class TestMain:
    """Tests for main entry point."""

    def test_main_no_arguments(self):
        """Test main with no arguments returns error."""
        exit_code = main([])

        assert exit_code == 1

    def test_main_nonexistent_corpus_dir(self, tmp_path: Path):
        """Test main with nonexistent corpus directory."""
        nonexistent = tmp_path / "nonexistent"

        exit_code = main([str(nonexistent)])

        assert exit_code == 1

    def test_main_single_conversion_success(self, mock_corpus_dir: Path):
        """Test main with successful single conversion."""
        exit_code = main([str(mock_corpus_dir)])

        assert exit_code == 0

        # Verify database was created
        db_path = mock_corpus_dir / "data" / "corpus.db"
        assert db_path.exists()

    def test_main_batch_mode_success(self, mock_batch_output_dir: Path):
        """Test main in batch mode."""
        exit_code = main(["--batch", str(mock_batch_output_dir)])

        assert exit_code == 0

    def test_main_batch_mode_nonexistent_dir(self, tmp_path: Path):
        """Test batch mode with nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"

        exit_code = main(["--batch", str(nonexistent)])

        assert exit_code == 1


class TestRunSingleConversion:
    """Tests for run_single_conversion function."""

    def test_run_single_conversion_success(self, mock_corpus_dir: Path):
        """Test successful single conversion."""
        args = parse_arguments([str(mock_corpus_dir)])

        exit_code = run_single_conversion(args)

        assert exit_code == 0
        assert (mock_corpus_dir / "data" / "corpus.db").exists()

    def test_run_single_conversion_nonexistent_dir(self, tmp_path: Path):
        """Test conversion with nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"
        args = parse_arguments([str(nonexistent)])

        exit_code = run_single_conversion(args)

        assert exit_code == 1

    def test_run_single_conversion_no_json(self, tmp_path: Path):
        """Test conversion when no annotated JSON exists."""
        corpus_dir = tmp_path / "corpus"
        data_dir = corpus_dir / "data"
        data_dir.mkdir(parents=True)

        args = parse_arguments([str(corpus_dir)])

        exit_code = run_single_conversion(args)

        assert exit_code == 1

    def test_run_single_conversion_dry_run(self, mock_corpus_dir: Path):
        """Test dry run mode."""
        args = parse_arguments([str(mock_corpus_dir), "--dry-run"])

        exit_code = run_single_conversion(args)

        assert exit_code == 0
        # Database should NOT be created in dry run
        assert not (mock_corpus_dir / "data" / "corpus.db").exists()

    def test_run_single_conversion_dry_run_existing_db(self, mock_corpus_dir: Path):
        """Test dry run mode when database already exists."""
        # First create the database
        main([str(mock_corpus_dir)])

        args = parse_arguments([str(mock_corpus_dir), "--dry-run"])

        exit_code = run_single_conversion(args)

        assert exit_code == 0

    def test_run_single_conversion_already_exists(self, mock_corpus_dir: Path):
        """Test conversion when database already exists without force."""
        # First conversion
        main([str(mock_corpus_dir)])

        # Second conversion should fail
        args = parse_arguments([str(mock_corpus_dir)])

        exit_code = run_single_conversion(args)

        assert exit_code == 1

    def test_run_single_conversion_force_overwrite(self, mock_corpus_dir: Path):
        """Test conversion with force overwrite."""
        # First conversion
        main([str(mock_corpus_dir)])

        # Second conversion with force
        args = parse_arguments([str(mock_corpus_dir), "--force"])

        exit_code = run_single_conversion(args)

        assert exit_code == 0

    def test_run_single_conversion_custom_batch_size(self, mock_corpus_dir: Path):
        """Test conversion with custom batch size."""
        args = parse_arguments([str(mock_corpus_dir), "--batch-size", "1"])

        exit_code = run_single_conversion(args)

        assert exit_code == 0

    def test_run_single_conversion_handles_exception(self, mock_corpus_dir: Path):
        """Test conversion handles unexpected exceptions."""
        args = parse_arguments([str(mock_corpus_dir)])

        with patch(
            "build_tools.corpus_sqlite_builder.cli.convert_json_to_sqlite",
            side_effect=RuntimeError("Simulated error"),
        ):
            exit_code = run_single_conversion(args)

        assert exit_code == 1


class TestRunBatchConversion:
    """Tests for run_batch_conversion function."""

    def test_run_batch_conversion_success(self, mock_batch_output_dir: Path):
        """Test successful batch conversion."""
        args = parse_arguments(["--batch", str(mock_batch_output_dir)])

        exit_code = run_batch_conversion(args)

        assert exit_code == 0

        # Verify databases were created
        for name in ["20260114_000000_pyphen", "20260114_000001_nltk"]:
            db_path = mock_batch_output_dir / name / "data" / "corpus.db"
            assert db_path.exists()

    def test_run_batch_conversion_nonexistent_dir(self, tmp_path: Path):
        """Test batch conversion with nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"
        args = parse_arguments(["--batch", str(nonexistent)])

        exit_code = run_batch_conversion(args)

        assert exit_code == 1

    def test_run_batch_conversion_empty_dir(self, tmp_path: Path):
        """Test batch conversion with empty directory (no corpora)."""
        output_dir = tmp_path / "empty_output"
        output_dir.mkdir()

        args = parse_arguments(["--batch", str(output_dir)])

        exit_code = run_batch_conversion(args)

        assert exit_code == 1

    def test_run_batch_conversion_partial_success(self, mock_batch_output_dir: Path):
        """Test batch conversion with some failures."""
        # Convert first corpus, so second run will have one failure
        first_corpus = mock_batch_output_dir / "20260114_000000_pyphen"
        main([str(first_corpus)])

        # Now batch convert without force - one will fail (already exists)
        args = parse_arguments(["--batch", str(mock_batch_output_dir)])

        exit_code = run_batch_conversion(args)

        assert exit_code == 1  # Partial failure

    def test_run_batch_conversion_with_force(self, mock_batch_output_dir: Path):
        """Test batch conversion with force flag."""
        # First conversion
        args = parse_arguments(["--batch", str(mock_batch_output_dir)])
        run_batch_conversion(args)

        # Second conversion with force
        args = parse_arguments(["--batch", str(mock_batch_output_dir), "--force"])

        exit_code = run_batch_conversion(args)

        assert exit_code == 0

    def test_run_batch_conversion_skips_non_directories(self, mock_batch_output_dir: Path):
        """Test that batch conversion skips files in output directory."""
        # Create a file in the output directory
        (mock_batch_output_dir / "random_file.txt").write_text("test")

        args = parse_arguments(["--batch", str(mock_batch_output_dir)])

        exit_code = run_batch_conversion(args)

        assert exit_code == 0

    def test_run_batch_conversion_skips_dirs_without_json(self, mock_batch_output_dir: Path):
        """Test that batch conversion skips directories without annotated JSON."""
        # Create a directory without annotated JSON
        empty_corpus = mock_batch_output_dir / "20260114_000002_empty"
        (empty_corpus / "data").mkdir(parents=True)

        args = parse_arguments(["--batch", str(mock_batch_output_dir)])

        exit_code = run_batch_conversion(args)

        assert exit_code == 0

    def test_run_batch_conversion_handles_exception(self, mock_batch_output_dir: Path):
        """Test batch conversion handles exceptions during conversion."""
        args = parse_arguments(["--batch", str(mock_batch_output_dir)])

        # Make convert_json_to_sqlite raise an exception for one corpus
        original_convert = __import__(
            "build_tools.corpus_sqlite_builder.cli",
            fromlist=["convert_json_to_sqlite"],
        ).convert_json_to_sqlite

        call_count = [0]

        def mock_convert(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Simulated error")
            return original_convert(*args, **kwargs)

        with patch(
            "build_tools.corpus_sqlite_builder.cli.convert_json_to_sqlite",
            side_effect=mock_convert,
        ):
            exit_code = run_batch_conversion(args)

        # Should return error because of the exception
        assert exit_code == 1
