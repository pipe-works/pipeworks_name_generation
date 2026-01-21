"""Tests for name selector CLI."""

import json
from pathlib import Path

import pytest

from build_tools.name_selector.cli import (
    create_argument_parser,
    extract_prefix_and_syllables,
    main,
    parse_arguments,
)


def make_candidates_data() -> dict:
    """Create sample candidates data for testing."""
    features = {
        "starts_with_vowel": False,
        "starts_with_cluster": False,
        "starts_with_heavy_cluster": False,
        "contains_plosive": True,
        "contains_fricative": False,
        "contains_liquid": True,
        "contains_nasal": False,
        "short_vowel": True,
        "long_vowel": False,
        "ends_with_vowel": True,
        "ends_with_nasal": False,
        "ends_with_stop": False,
    }
    return {
        "metadata": {
            "syllable_count": 2,
            "seed": 42,
        },
        "candidates": [
            {"name": "kali", "syllables": ["ka", "li"], "features": features.copy()},
            {"name": "lira", "syllables": ["li", "ra"], "features": features.copy()},
            {"name": "raka", "syllables": ["ra", "ka"], "features": features.copy()},
        ],
    }


def make_policy_yaml() -> str:
    """Create sample policy YAML for testing."""
    return """
version: "1.0"
name_classes:
  first_name:
    description: "Test first name policy"
    syllable_range: [2, 3]
    features:
      ends_with_vowel: preferred
      ends_with_stop: discouraged
  last_name:
    description: "Test last name policy"
    syllable_range: [2, 4]
    features:
      ends_with_stop: preferred
"""


class TestCreateArgumentParser:
    """Test argument parser creation."""

    def test_parser_created(self):
        """Parser should be created successfully."""
        parser = create_argument_parser()
        assert parser is not None

    def test_required_arguments(self):
        """Parser should require run-dir, candidates, and name-class."""
        parser = create_argument_parser()
        # Should fail without required args
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_default_values(self):
        """Parser should have correct default values."""
        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--run-dir",
                "/tmp/test",
                "--candidates",
                "candidates/test.json",
                "--name-class",
                "first_name",
            ]
        )
        assert args.count == 100
        assert args.mode == "hard"
        assert args.policy_file is None


class TestParseArguments:
    """Test argument parsing."""

    def test_parses_all_arguments(self):
        """Should parse all arguments correctly."""
        args = parse_arguments(
            [
                "--run-dir",
                "/tmp/test",
                "--candidates",
                "candidates/test.json",
                "--name-class",
                "first_name",
                "--policy-file",
                "/tmp/policy.yml",
                "--count",
                "50",
                "--mode",
                "soft",
            ]
        )
        assert args.run_dir == Path("/tmp/test")
        assert args.candidates == Path("candidates/test.json")
        assert args.name_class == "first_name"
        assert args.policy_file == Path("/tmp/policy.yml")
        assert args.count == 50
        assert args.mode == "soft"


class TestExtractPrefixAndSyllables:
    """Test filename parsing."""

    def test_extracts_pyphen_2syl(self):
        """Should extract pyphen prefix and 2 syllables."""
        prefix, syllables = extract_prefix_and_syllables("pyphen_candidates_2syl.json")
        assert prefix == "pyphen"
        assert syllables == 2

    def test_extracts_nltk_3syl(self):
        """Should extract nltk prefix and 3 syllables."""
        prefix, syllables = extract_prefix_and_syllables("nltk_candidates_3syl.json")
        assert prefix == "nltk"
        assert syllables == 3

    def test_extracts_4syl(self):
        """Should extract 4 syllables."""
        prefix, syllables = extract_prefix_and_syllables("pyphen_candidates_4syl.json")
        assert syllables == 4

    def test_raises_on_missing_candidates(self):
        """Should raise ValueError when 'candidates' is missing."""
        with pytest.raises(ValueError, match="Unexpected candidates filename format"):
            extract_prefix_and_syllables("pyphen_2syl.json")

    def test_raises_on_missing_syl_suffix(self):
        """Should raise ValueError when 'syl' suffix is missing."""
        with pytest.raises(ValueError, match="Cannot extract syllable count"):
            extract_prefix_and_syllables("pyphen_candidates_2.json")

    def test_raises_on_non_numeric(self):
        """Should raise ValueError when syllable count isn't numeric."""
        with pytest.raises(ValueError, match="Cannot parse syllable count"):
            extract_prefix_and_syllables("pyphen_candidates_abcsyl.json")


class TestMain:
    """Test main CLI entry point."""

    def test_success_with_valid_input(self, tmp_path):
        """Should succeed with valid input."""
        # Set up run directory structure
        candidates_dir = tmp_path / "candidates"
        candidates_dir.mkdir()
        candidates_file = candidates_dir / "pyphen_candidates_2syl.json"
        candidates_file.write_text(json.dumps(make_candidates_data()))

        # Create policy file
        policy_file = tmp_path / "policy.yml"
        policy_file.write_text(make_policy_yaml())

        result = main(
            [
                "--run-dir",
                str(tmp_path),
                "--candidates",
                "candidates/pyphen_candidates_2syl.json",
                "--name-class",
                "first_name",
                "--policy-file",
                str(policy_file),
                "--count",
                "10",
            ]
        )

        assert result == 0

        # Verify output was created
        output_file = tmp_path / "selections" / "pyphen_first_name_2syl.json"
        assert output_file.exists()

        # Verify output structure
        with open(output_file) as f:
            output = json.load(f)
        assert "metadata" in output
        assert "selections" in output
        assert output["metadata"]["name_class"] == "first_name"
        assert output["metadata"]["mode"] == "hard"

    def test_soft_mode(self, tmp_path):
        """Should run in soft mode when specified."""
        # Set up run directory structure
        candidates_dir = tmp_path / "candidates"
        candidates_dir.mkdir()
        candidates_file = candidates_dir / "pyphen_candidates_2syl.json"
        candidates_file.write_text(json.dumps(make_candidates_data()))

        # Create policy file
        policy_file = tmp_path / "policy.yml"
        policy_file.write_text(make_policy_yaml())

        result = main(
            [
                "--run-dir",
                str(tmp_path),
                "--candidates",
                "candidates/pyphen_candidates_2syl.json",
                "--name-class",
                "first_name",
                "--policy-file",
                str(policy_file),
                "--mode",
                "soft",
            ]
        )

        assert result == 0

        # Verify mode in metadata
        output_file = tmp_path / "selections" / "pyphen_first_name_2syl.json"
        with open(output_file) as f:
            output = json.load(f)
        assert output["metadata"]["mode"] == "soft"

    def test_error_on_missing_run_dir(self, tmp_path):
        """Should return error code when run directory doesn't exist."""
        nonexistent = tmp_path / "nonexistent"

        result = main(
            [
                "--run-dir",
                str(nonexistent),
                "--candidates",
                "candidates/test.json",
                "--name-class",
                "first_name",
            ]
        )

        assert result == 1

    def test_error_on_missing_candidates_file(self, tmp_path):
        """Should return error code when candidates file is missing."""
        result = main(
            [
                "--run-dir",
                str(tmp_path),
                "--candidates",
                "candidates/nonexistent.json",
                "--name-class",
                "first_name",
            ]
        )

        assert result == 1

    def test_error_on_invalid_json(self, tmp_path):
        """Should return error code on invalid JSON."""
        candidates_dir = tmp_path / "candidates"
        candidates_dir.mkdir()
        candidates_file = candidates_dir / "test.json"
        candidates_file.write_text("not valid json")

        result = main(
            [
                "--run-dir",
                str(tmp_path),
                "--candidates",
                "candidates/test.json",
                "--name-class",
                "first_name",
            ]
        )

        assert result == 1

    def test_error_on_missing_policy_file(self, tmp_path):
        """Should return error code when policy file is missing."""
        candidates_dir = tmp_path / "candidates"
        candidates_dir.mkdir()
        candidates_file = candidates_dir / "pyphen_candidates_2syl.json"
        candidates_file.write_text(json.dumps(make_candidates_data()))

        result = main(
            [
                "--run-dir",
                str(tmp_path),
                "--candidates",
                "candidates/pyphen_candidates_2syl.json",
                "--name-class",
                "first_name",
                "--policy-file",
                str(tmp_path / "nonexistent.yml"),
            ]
        )

        assert result == 1

    def test_error_on_unknown_name_class(self, tmp_path):
        """Should return error code for unknown name class."""
        candidates_dir = tmp_path / "candidates"
        candidates_dir.mkdir()
        candidates_file = candidates_dir / "pyphen_candidates_2syl.json"
        candidates_file.write_text(json.dumps(make_candidates_data()))

        policy_file = tmp_path / "policy.yml"
        policy_file.write_text(make_policy_yaml())

        result = main(
            [
                "--run-dir",
                str(tmp_path),
                "--candidates",
                "candidates/pyphen_candidates_2syl.json",
                "--name-class",
                "nonexistent_class",
                "--policy-file",
                str(policy_file),
            ]
        )

        assert result == 1

    def test_error_on_invalid_policy_yaml(self, tmp_path):
        """Should return error code on invalid policy YAML."""
        candidates_dir = tmp_path / "candidates"
        candidates_dir.mkdir()
        candidates_file = candidates_dir / "pyphen_candidates_2syl.json"
        candidates_file.write_text(json.dumps(make_candidates_data()))

        policy_file = tmp_path / "policy.yml"
        policy_file.write_text("not_a_dict: true")

        result = main(
            [
                "--run-dir",
                str(tmp_path),
                "--candidates",
                "candidates/pyphen_candidates_2syl.json",
                "--name-class",
                "first_name",
                "--policy-file",
                str(policy_file),
            ]
        )

        assert result == 1

    def test_handles_unexpected_filename_format(self, tmp_path):
        """Should handle unexpected filename format gracefully."""
        candidates_dir = tmp_path / "candidates"
        candidates_dir.mkdir()
        # Non-standard filename
        candidates_file = candidates_dir / "custom_names.json"
        candidates_file.write_text(json.dumps(make_candidates_data()))

        policy_file = tmp_path / "policy.yml"
        policy_file.write_text(make_policy_yaml())

        result = main(
            [
                "--run-dir",
                str(tmp_path),
                "--candidates",
                "candidates/custom_names.json",
                "--name-class",
                "first_name",
                "--policy-file",
                str(policy_file),
            ]
        )

        # Should still succeed, using defaults
        assert result == 0

        # Output should use "unknown" prefix and metadata syllable count
        output_file = tmp_path / "selections" / "unknown_first_name_2syl.json"
        assert output_file.exists()

    def test_nltk_prefix_used(self, tmp_path):
        """Should use nltk prefix when candidates have nltk prefix."""
        candidates_dir = tmp_path / "candidates"
        candidates_dir.mkdir()
        candidates_file = candidates_dir / "nltk_candidates_3syl.json"
        candidates_file.write_text(json.dumps(make_candidates_data()))

        policy_file = tmp_path / "policy.yml"
        policy_file.write_text(make_policy_yaml())

        result = main(
            [
                "--run-dir",
                str(tmp_path),
                "--candidates",
                "candidates/nltk_candidates_3syl.json",
                "--name-class",
                "first_name",
                "--policy-file",
                str(policy_file),
            ]
        )

        assert result == 0

        # Verify output filename uses nltk prefix and 3syl
        output_file = tmp_path / "selections" / "nltk_first_name_3syl.json"
        assert output_file.exists()

    def test_different_name_classes(self, tmp_path):
        """Should produce different outputs for different name classes."""
        candidates_dir = tmp_path / "candidates"
        candidates_dir.mkdir()
        candidates_file = candidates_dir / "pyphen_candidates_2syl.json"
        candidates_file.write_text(json.dumps(make_candidates_data()))

        policy_file = tmp_path / "policy.yml"
        policy_file.write_text(make_policy_yaml())

        # Run for first_name
        main(
            [
                "--run-dir",
                str(tmp_path),
                "--candidates",
                "candidates/pyphen_candidates_2syl.json",
                "--name-class",
                "first_name",
                "--policy-file",
                str(policy_file),
            ]
        )

        # Run for last_name
        main(
            [
                "--run-dir",
                str(tmp_path),
                "--candidates",
                "candidates/pyphen_candidates_2syl.json",
                "--name-class",
                "last_name",
                "--policy-file",
                str(policy_file),
            ]
        )

        # Both outputs should exist
        assert (tmp_path / "selections" / "pyphen_first_name_2syl.json").exists()
        assert (tmp_path / "selections" / "pyphen_last_name_2syl.json").exists()

    def test_rejection_reasons_displayed(self, tmp_path, capsys):
        """Should display rejection reasons when candidates are rejected."""
        # Create candidates with discouraged features
        candidates_with_rejections = {
            "metadata": {"syllable_count": 2},
            "candidates": [
                {
                    "name": "kalt",
                    "syllables": ["kal", "t"],
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
                        "ends_with_stop": True,  # Discouraged in first_name
                    },
                },
                {
                    "name": "kali",
                    "syllables": ["ka", "li"],
                    "features": {
                        "starts_with_vowel": False,
                        "starts_with_cluster": False,
                        "starts_with_heavy_cluster": False,
                        "contains_plosive": True,
                        "contains_fricative": False,
                        "contains_liquid": True,
                        "contains_nasal": False,
                        "short_vowel": True,
                        "long_vowel": False,
                        "ends_with_vowel": True,
                        "ends_with_nasal": False,
                        "ends_with_stop": False,
                    },
                },
            ],
        }

        candidates_dir = tmp_path / "candidates"
        candidates_dir.mkdir()
        candidates_file = candidates_dir / "pyphen_candidates_2syl.json"
        candidates_file.write_text(json.dumps(candidates_with_rejections))

        policy_file = tmp_path / "policy.yml"
        policy_file.write_text(make_policy_yaml())

        result = main(
            [
                "--run-dir",
                str(tmp_path),
                "--candidates",
                "candidates/pyphen_candidates_2syl.json",
                "--name-class",
                "first_name",
                "--policy-file",
                str(policy_file),
            ]
        )

        assert result == 0

        # Check that rejection reasons were printed
        captured = capsys.readouterr()
        assert "Rejection reasons:" in captured.out
        assert "ends_with_stop" in captured.out


class TestMainModule:
    """Test __main__.py entry point."""

    def test_import_main(self):
        """Should be able to import main from __main__."""
        from build_tools.name_selector.__main__ import main as main_entry

        assert callable(main_entry)

    def test_combiner_import_main(self):
        """Should be able to import main from combiner __main__."""
        from build_tools.name_combiner.__main__ import main as main_entry

        assert callable(main_entry)
