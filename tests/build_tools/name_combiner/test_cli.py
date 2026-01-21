"""Tests for name combiner CLI."""

import json
from pathlib import Path

import pytest

from build_tools.name_combiner.cli import (
    create_argument_parser,
    discover_annotated_json,
    main,
    parse_arguments,
)


def make_annotated_data() -> list[dict]:
    """Create sample annotated data for testing."""
    features = {
        "starts_with_vowel": False,
        "starts_with_cluster": False,
        "starts_with_heavy_cluster": False,
        "contains_plosive": True,
        "contains_fricative": False,
        "contains_liquid": False,
        "contains_nasal": False,
        "short_vowel": True,
        "long_vowel": False,
        "ends_with_vowel": True,
        "ends_with_nasal": False,
        "ends_with_stop": False,
    }
    return [
        {"syllable": "ka", "frequency": 100, "features": features.copy()},
        {"syllable": "li", "frequency": 50, "features": features.copy()},
        {"syllable": "ra", "frequency": 75, "features": features.copy()},
    ]


class TestCreateArgumentParser:
    """Test argument parser creation."""

    def test_parser_created(self):
        """Parser should be created successfully."""
        parser = create_argument_parser()
        assert parser is not None

    def test_required_arguments(self):
        """Parser should require run-dir and syllables."""
        parser = create_argument_parser()
        # Should fail without required args
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_default_values(self):
        """Parser should have correct default values."""
        parser = create_argument_parser()
        args = parser.parse_args(["--run-dir", "/tmp/test", "--syllables", "2"])
        assert args.count == 10000
        assert args.seed is None
        assert args.frequency_weight == 1.0


class TestParseArguments:
    """Test argument parsing."""

    def test_parses_all_arguments(self):
        """Should parse all arguments correctly."""
        args = parse_arguments(
            [
                "--run-dir",
                "/tmp/test",
                "--syllables",
                "3",
                "--count",
                "500",
                "--seed",
                "42",
                "--frequency-weight",
                "0.5",
            ]
        )
        assert args.run_dir == Path("/tmp/test")
        assert args.syllables == 3
        assert args.count == 500
        assert args.seed == 42
        assert args.frequency_weight == 0.5


class TestDiscoverAnnotatedJson:
    """Test annotated JSON discovery."""

    def test_discovers_pyphen_file(self, tmp_path):
        """Should discover pyphen annotated file."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        pyphen_file = data_dir / "pyphen_syllables_annotated.json"
        pyphen_file.write_text("[]")

        path, prefix = discover_annotated_json(tmp_path)

        assert path == pyphen_file
        assert prefix == "pyphen"

    def test_discovers_nltk_file(self, tmp_path):
        """Should discover nltk annotated file."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        nltk_file = data_dir / "nltk_syllables_annotated.json"
        nltk_file.write_text("[]")

        path, prefix = discover_annotated_json(tmp_path)

        assert path == nltk_file
        assert prefix == "nltk"

    def test_prefers_pyphen_over_nltk(self, tmp_path):
        """Should prefer pyphen when both exist."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "pyphen_syllables_annotated.json").write_text("[]")
        (data_dir / "nltk_syllables_annotated.json").write_text("[]")

        path, prefix = discover_annotated_json(tmp_path)

        assert prefix == "pyphen"

    def test_raises_on_missing_data_dir(self, tmp_path):
        """Should raise FileNotFoundError when data/ is missing."""
        with pytest.raises(FileNotFoundError, match="No data/ directory"):
            discover_annotated_json(tmp_path)

    def test_raises_on_missing_annotated_json(self, tmp_path):
        """Should raise FileNotFoundError when no annotated JSON exists."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="No annotated JSON found"):
            discover_annotated_json(tmp_path)


class TestMain:
    """Test main CLI entry point."""

    def test_success_with_valid_input(self, tmp_path):
        """Should succeed with valid input."""
        # Set up run directory structure
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        annotated_file = data_dir / "pyphen_syllables_annotated.json"
        annotated_file.write_text(json.dumps(make_annotated_data()))

        result = main(
            [
                "--run-dir",
                str(tmp_path),
                "--syllables",
                "2",
                "--count",
                "10",
                "--seed",
                "42",
            ]
        )

        assert result == 0

        # Verify output was created
        output_file = tmp_path / "candidates" / "pyphen_candidates_2syl.json"
        assert output_file.exists()

        # Verify output structure
        with open(output_file) as f:
            output = json.load(f)
        assert "metadata" in output
        assert "candidates" in output
        assert len(output["candidates"]) == 10
        assert output["metadata"]["syllable_count"] == 2
        assert output["metadata"]["seed"] == 42

    def test_deterministic_output(self, tmp_path):
        """Same seed should produce identical output."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        annotated_file = data_dir / "pyphen_syllables_annotated.json"
        annotated_file.write_text(json.dumps(make_annotated_data()))

        # First run
        main(
            [
                "--run-dir",
                str(tmp_path),
                "--syllables",
                "2",
                "--count",
                "10",
                "--seed",
                "42",
            ]
        )
        output_file = tmp_path / "candidates" / "pyphen_candidates_2syl.json"
        with open(output_file) as f:
            output1 = json.load(f)

        # Second run with same seed
        main(
            [
                "--run-dir",
                str(tmp_path),
                "--syllables",
                "2",
                "--count",
                "10",
                "--seed",
                "42",
            ]
        )
        with open(output_file) as f:
            output2 = json.load(f)

        # Candidates should be identical
        names1 = [c["name"] for c in output1["candidates"]]
        names2 = [c["name"] for c in output2["candidates"]]
        assert names1 == names2

    def test_error_on_missing_run_dir(self, tmp_path):
        """Should return error code when run directory doesn't exist."""
        nonexistent = tmp_path / "nonexistent"

        result = main(
            [
                "--run-dir",
                str(nonexistent),
                "--syllables",
                "2",
            ]
        )

        assert result == 1

    def test_error_on_missing_annotated_json(self, tmp_path):
        """Should return error code when annotated JSON is missing."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        result = main(
            [
                "--run-dir",
                str(tmp_path),
                "--syllables",
                "2",
            ]
        )

        assert result == 1

    def test_error_on_invalid_json(self, tmp_path):
        """Should return error code on invalid JSON."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        annotated_file = data_dir / "pyphen_syllables_annotated.json"
        annotated_file.write_text("not valid json")

        result = main(
            [
                "--run-dir",
                str(tmp_path),
                "--syllables",
                "2",
            ]
        )

        assert result == 1

    def test_nltk_prefix_used(self, tmp_path):
        """Should use nltk prefix when nltk file is discovered."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        annotated_file = data_dir / "nltk_syllables_annotated.json"
        annotated_file.write_text(json.dumps(make_annotated_data()))

        result = main(
            [
                "--run-dir",
                str(tmp_path),
                "--syllables",
                "2",
                "--count",
                "5",
            ]
        )

        assert result == 0

        # Verify output filename uses nltk prefix
        output_file = tmp_path / "candidates" / "nltk_candidates_2syl.json"
        assert output_file.exists()

    def test_frequency_weight_applied(self, tmp_path):
        """Should apply frequency weight parameter."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        annotated_file = data_dir / "pyphen_syllables_annotated.json"
        annotated_file.write_text(json.dumps(make_annotated_data()))

        result = main(
            [
                "--run-dir",
                str(tmp_path),
                "--syllables",
                "2",
                "--count",
                "10",
                "--frequency-weight",
                "0.0",
            ]
        )

        assert result == 0

        # Verify metadata records the weight
        output_file = tmp_path / "candidates" / "pyphen_candidates_2syl.json"
        with open(output_file) as f:
            output = json.load(f)
        assert output["metadata"]["frequency_weight"] == 0.0
