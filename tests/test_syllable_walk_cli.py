"""Tests for syllable walker CLI.

This module tests the command-line interface including:
- Argument parsing and validation
- Mode handlers (single, compare, batch, search)
- Error handling and exit codes
- Output formatting
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from build_tools.syllable_walk.cli import create_argument_parser, main, parse_arguments


class TestArgumentParser:
    """Test CLI argument parser."""

    def test_parser_creation(self):
        """Test parser can be created."""
        parser = create_argument_parser()
        assert parser is not None
        assert parser.description is not None
        assert "syllable" in str(parser.description).lower()

    def test_parse_basic_args(self):
        """Test parsing basic arguments."""
        args = parse_arguments(["data.json", "--start", "ka"])
        assert args.data_file == Path("data.json")
        assert args.start == "ka"

    def test_parse_profile_arg(self):
        """Test parsing profile argument."""
        args = parse_arguments(["data.json", "--profile", "goblin"])
        assert args.profile == "goblin"

    def test_parse_steps_arg(self):
        """Test parsing steps argument."""
        args = parse_arguments(["data.json", "--steps", "10"])
        assert args.steps == 10

    def test_parse_seed_arg(self):
        """Test parsing seed argument."""
        args = parse_arguments(["data.json", "--seed", "42"])
        assert args.seed == 42

    def test_parse_custom_params(self):
        """Test parsing custom parameters."""
        args = parse_arguments(
            [
                "data.json",
                "--max-flips",
                "2",
                "--temperature",
                "1.5",
                "--frequency-weight",
                "-0.8",
            ]
        )
        assert args.max_flips == 2
        assert args.temperature == 1.5
        assert args.frequency_weight == -0.8

    def test_parse_compare_profiles_flag(self):
        """Test parsing --compare-profiles flag."""
        args = parse_arguments(["data.json", "--compare-profiles"])
        assert args.compare_profiles is True

    def test_parse_batch_arg(self):
        """Test parsing --batch argument."""
        args = parse_arguments(["data.json", "--batch", "50"])
        assert args.batch == 50

    def test_parse_search_arg(self):
        """Test parsing --search argument."""
        args = parse_arguments(["data.json", "--search", "ka"])
        assert args.search == "ka"

    def test_parse_output_arg(self):
        """Test parsing --output argument."""
        args = parse_arguments(["data.json", "--output", "results.json"])
        assert args.output == Path("results.json")

    def test_parse_quiet_flag(self):
        """Test parsing --quiet flag."""
        args = parse_arguments(["data.json", "--quiet"])
        assert args.quiet is True

    def test_parse_verbose_flag(self):
        """Test parsing --verbose flag."""
        args = parse_arguments(["data.json", "--verbose"])
        assert args.verbose is True

    def test_parse_max_neighbor_distance(self):
        """Test parsing --max-neighbor-distance."""
        args = parse_arguments(["data.json", "--max-neighbor-distance", "2"])
        assert args.max_neighbor_distance == 2

    def test_default_values(self):
        """Test default argument values."""
        args = parse_arguments(["data.json"])
        assert args.profile == "dialect"
        assert args.steps == 5
        assert args.max_neighbor_distance == 3
        assert args.quiet is False
        assert args.verbose is False
        assert args.compare_profiles is False


class TestCLIValidation:
    """Test CLI argument validation."""

    def test_quiet_and_verbose_mutually_exclusive(self, sample_data_file):
        """Test that --quiet and --verbose cannot be used together."""
        with patch("sys.argv", ["cli", str(sample_data_file), "--quiet", "--verbose"]):
            exit_code = main()
            assert exit_code == 2  # Validation error

    def test_nonexistent_file_returns_error(self):
        """Test that nonexistent data file returns error code."""
        with patch("sys.argv", ["cli", "/nonexistent/file.json"]):
            exit_code = main()
            assert exit_code == 1  # File not found error


class TestSingleWalkMode:
    """Test single walk generation mode."""

    def test_single_walk_with_start_syllable(self, sample_data_file, capsys):
        """Test single walk with specified start syllable."""
        with patch("sys.argv", ["cli", str(sample_data_file), "--start", "ka", "--steps", "3"]):
            exit_code = main()
            assert exit_code == 0

            captured = capsys.readouterr()
            assert "ka" in captured.out

    def test_single_walk_random_start(self, sample_data_file):
        """Test single walk with random start syllable."""
        with patch("sys.argv", ["cli", str(sample_data_file), "--steps", "3", "--seed", "42"]):
            exit_code = main()
            assert exit_code == 0

    def test_single_walk_with_profile(self, sample_data_file, capsys):
        """Test single walk with specific profile."""
        with patch(
            "sys.argv", ["cli", str(sample_data_file), "--start", "ka", "--profile", "goblin"]
        ):
            exit_code = main()
            assert exit_code == 0

            captured = capsys.readouterr()
            # Should mention the walk somehow
            assert "ka" in captured.out

    def test_single_walk_with_custom_params(self, sample_data_file):
        """Test single walk with custom parameters."""
        with patch(
            "sys.argv",
            [
                "cli",
                str(sample_data_file),
                "--start",
                "ka",
                "--max-flips",
                "2",
                "--temperature",
                "1.5",
                "--frequency-weight",
                "0.5",
            ],
        ):
            exit_code = main()
            assert exit_code == 0

    def test_single_walk_invalid_start_syllable(self, sample_data_file, capsys):
        """Test single walk with invalid start syllable."""
        with patch("sys.argv", ["cli", str(sample_data_file), "--start", "INVALID_XYZ"]):
            exit_code = main()
            assert exit_code == 1

            captured = capsys.readouterr()
            assert "not found" in captured.err

    def test_single_walk_with_output_file(self, sample_data_file, tmp_path):
        """Test single walk with output to file."""
        output_file = tmp_path / "walk.json"
        with patch(
            "sys.argv",
            [
                "cli",
                str(sample_data_file),
                "--start",
                "ka",
                "--steps",
                "3",
                "--output",
                str(output_file),
            ],
        ):
            exit_code = main()
            assert exit_code == 0
            assert output_file.exists()

            # Verify JSON format
            with open(output_file) as f:
                data = json.load(f)
                assert "path" in data
                assert "syllables" in data
                assert data["start"] == "ka"


class TestCompareProfilesMode:
    """Test profile comparison mode."""

    def test_compare_profiles_with_start(self, sample_data_file, capsys):
        """Test comparing all profiles from specified start."""
        with patch(
            "sys.argv", ["cli", str(sample_data_file), "--start", "ka", "--compare-profiles"]
        ):
            exit_code = main()
            assert exit_code == 0

            captured = capsys.readouterr()
            # Should show all profile names
            assert "Clerical" in captured.out
            assert "Dialect" in captured.out
            assert "Goblin" in captured.out
            assert "Ritual" in captured.out

    def test_compare_profiles_random_start(self, sample_data_file, capsys):
        """Test comparing all profiles from random start."""
        with patch(
            "sys.argv", ["cli", str(sample_data_file), "--compare-profiles", "--seed", "42"]
        ):
            exit_code = main()
            assert exit_code == 0

            captured = capsys.readouterr()
            assert "Profile Comparison" in captured.out

    def test_compare_profiles_invalid_start(self, sample_data_file):
        """Test compare profiles with invalid start syllable."""
        with patch(
            "sys.argv", ["cli", str(sample_data_file), "--start", "INVALID", "--compare-profiles"]
        ):
            exit_code = main()
            assert exit_code == 1


class TestBatchMode:
    """Test batch walk generation mode."""

    def test_batch_generation(self, sample_data_file, capsys):
        """Test batch generation of multiple walks."""
        with patch("sys.argv", ["cli", str(sample_data_file), "--batch", "5", "--quiet"]):
            exit_code = main()
            assert exit_code == 0

    def test_batch_with_output_file(self, sample_data_file, tmp_path):
        """Test batch generation with output file."""
        output_file = tmp_path / "batch.json"
        with patch(
            "sys.argv",
            [
                "cli",
                str(sample_data_file),
                "--batch",
                "5",
                "--output",
                str(output_file),
                "--quiet",
            ],
        ):
            exit_code = main()
            assert exit_code == 0
            assert output_file.exists()

            # Verify JSON format
            with open(output_file) as f:
                data = json.load(f)
                assert "walks" in data
                assert data["count"] == 5
                assert len(data["walks"]) == 5

    def test_batch_with_fixed_start(self, sample_data_file, tmp_path):
        """Test batch generation with fixed start syllable."""
        output_file = tmp_path / "batch_fixed.json"
        with patch(
            "sys.argv",
            [
                "cli",
                str(sample_data_file),
                "--batch",
                "3",
                "--start",
                "ka",
                "--output",
                str(output_file),
                "--quiet",
            ],
        ):
            exit_code = main()
            assert exit_code == 0

    def test_batch_shows_progress(self, sample_data_file, capsys):
        """Test batch mode shows progress messages."""
        with patch("sys.argv", ["cli", str(sample_data_file), "--batch", "3"]):
            exit_code = main()
            assert exit_code == 0

            captured = capsys.readouterr()
            assert "Progress" in captured.out or "walks" in captured.out.lower()


class TestSearchMode:
    """Test syllable search mode."""

    def test_search_finds_matches(self, sample_data_file, capsys):
        """Test search finds matching syllables."""
        with patch("sys.argv", ["cli", str(sample_data_file), "--search", "ka"]):
            exit_code = main()
            assert exit_code == 0

            captured = capsys.readouterr()
            assert "Found" in captured.out
            assert "ka" in captured.out

    def test_search_no_matches(self, sample_data_file, capsys):
        """Test search with no matches."""
        with patch("sys.argv", ["cli", str(sample_data_file), "--search", "ZZZZZ"]):
            exit_code = main()
            assert exit_code == 0  # Still success, just no results

            captured = capsys.readouterr()
            assert "No syllables found" in captured.out

    def test_search_shows_frequency(self, sample_data_file, capsys):
        """Test search shows frequency information."""
        with patch("sys.argv", ["cli", str(sample_data_file), "--search", "ka"]):
            exit_code = main()
            assert exit_code == 0

            captured = capsys.readouterr()
            assert "frequency" in captured.out.lower()


class TestOutputControl:
    """Test output control flags."""

    def test_quiet_suppresses_output(self, sample_data_file, capsys):
        """Test --quiet suppresses progress messages."""
        with patch("sys.argv", ["cli", str(sample_data_file), "--start", "ka", "--quiet"]):
            exit_code = main()
            assert exit_code == 0

            captured = capsys.readouterr()
            # Should have minimal output (just the walk result)
            assert "Initializing" not in captured.out
            assert "Walker ready" not in captured.out

    def test_verbose_shows_details(self, sample_data_file, capsys):
        """Test --verbose shows detailed output."""
        with patch("sys.argv", ["cli", str(sample_data_file), "--start", "ka", "--verbose"]):
            exit_code = main()
            assert exit_code == 0

            captured = capsys.readouterr()
            # Should show initialization details
            assert "Loading" in captured.out or "Building" in captured.out


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_keyboard_interrupt_handled(self, sample_data_file):
        """Test keyboard interrupt returns correct exit code."""
        # Mock walker initialization to raise KeyboardInterrupt
        with patch("build_tools.syllable_walk.cli.SyllableWalker") as mock_walker:
            mock_walker.side_effect = KeyboardInterrupt()
            with patch("sys.argv", ["cli", str(sample_data_file)]):
                exit_code = main()
                assert exit_code == 130

    def test_exception_handled(self, sample_data_file):
        """Test general exceptions are caught and reported."""
        # Mock walker initialization to raise exception
        with patch("build_tools.syllable_walk.cli.SyllableWalker") as mock_walker:
            mock_walker.side_effect = RuntimeError("Test error")
            with patch("sys.argv", ["cli", str(sample_data_file)]):
                exit_code = main()
                assert exit_code == 1

    def test_exception_with_verbose_shows_traceback(self, sample_data_file, capsys):
        """Test exceptions show traceback in verbose mode."""
        with patch("build_tools.syllable_walk.cli.SyllableWalker") as mock_walker:
            mock_walker.side_effect = RuntimeError("Test error for traceback")
            with patch("sys.argv", ["cli", str(sample_data_file), "--verbose"]):
                exit_code = main()
                assert exit_code == 1

                captured = capsys.readouterr()
                assert "Test error for traceback" in captured.err
                assert "Traceback" in captured.err

    def test_missing_data_file_returns_error(self, capsys):
        """Test that missing data_file argument returns error code."""
        with patch("sys.argv", ["cli"]):
            exit_code = main()
            assert exit_code == 1

            captured = capsys.readouterr()
            assert "data_file is required" in captured.err


class TestWebMode:
    """Test web server mode."""

    def test_web_mode_returns_exit_code(self, sample_data_file):
        """Test web mode returns correct exit code on success."""
        with patch("build_tools.syllable_walk.cli.run_server") as mock_run:
            with patch("sys.argv", ["cli", str(sample_data_file), "--web"]):
                exit_code = main()
                assert exit_code == 0
                mock_run.assert_called_once()

    def test_web_mode_file_not_found(self, capsys):
        """Test web mode handles FileNotFoundError."""
        with patch("build_tools.syllable_walk.cli.run_server") as mock_run:
            mock_run.side_effect = FileNotFoundError("No dataset found")
            with patch("sys.argv", ["cli", "--web"]):
                exit_code = main()
                assert exit_code == 1

                captured = capsys.readouterr()
                assert "Error" in captured.err

    def test_web_mode_port_in_use(self, sample_data_file, capsys):
        """Test web mode handles port in use error."""
        with patch("build_tools.syllable_walk.cli.run_server") as mock_run:
            mock_run.side_effect = OSError("Address already in use")
            with patch("sys.argv", ["cli", str(sample_data_file), "--web", "--port", "5000"]):
                exit_code = main()
                assert exit_code == 1

                captured = capsys.readouterr()
                assert "Error starting server" in captured.err
                assert "5000" in captured.err

    def test_web_mode_general_error(self, sample_data_file, capsys):
        """Test web mode handles general exceptions."""
        with patch("build_tools.syllable_walk.cli.run_server") as mock_run:
            mock_run.side_effect = RuntimeError("Server crashed")
            with patch("sys.argv", ["cli", str(sample_data_file), "--web"]):
                exit_code = main()
                assert exit_code == 1

                captured = capsys.readouterr()
                assert "Error" in captured.err

    def test_web_mode_auto_discover(self):
        """Test web mode auto-discovers port."""
        with patch("build_tools.syllable_walk.cli.run_server") as mock_run:
            with patch("sys.argv", ["cli", "--web"]):
                main()
                mock_run.assert_called_once()
                # port should be None for auto-discovery
                assert mock_run.call_args[1]["port"] is None


class TestBatchModeExtended:
    """Extended tests for batch mode coverage."""

    def test_batch_with_output_prints_saved_message(self, sample_data_file, tmp_path, capsys):
        """Test batch with output file prints saved message."""
        output_file = tmp_path / "batch_output.json"
        with patch(
            "sys.argv",
            [
                "cli",
                str(sample_data_file),
                "--batch",
                "3",
                "--output",
                str(output_file),
            ],
        ):
            exit_code = main()
            assert exit_code == 0

            captured = capsys.readouterr()
            assert "Saved" in captured.out or "saved" in captured.out.lower()

    def test_batch_without_output_shows_summary(self, sample_data_file, capsys):
        """Test batch without output shows summary."""
        with patch("sys.argv", ["cli", str(sample_data_file), "--batch", "3"]):
            exit_code = main()
            assert exit_code == 0

            captured = capsys.readouterr()
            assert "Total walks" in captured.out or "Summary" in captured.out


class TestSearchModeExtended:
    """Extended tests for search mode coverage."""

    def test_search_many_matches_truncates(self, tmp_path, capsys):
        """Test search with many matches shows truncation message."""
        # Create data with many matching syllables
        syllables = []
        for i in range(30):
            syllables.append(
                {
                    "syllable": f"ka{i}",
                    "frequency": 100 - i,
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
                        "ends_with_vowel": True,
                        "ends_with_nasal": False,
                        "ends_with_stop": False,
                    },
                }
            )

        data_file = tmp_path / "many_syllables.json"
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(syllables, f)

        with patch("sys.argv", ["cli", str(data_file), "--search", "ka"]):
            exit_code = main()
            assert exit_code == 0

            captured = capsys.readouterr()
            assert "Found" in captured.out
            # Should show truncation message (more than 20 matches)
            assert "more" in captured.out or "Narrow" in captured.out


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def sample_data_file(tmp_path):
    """Create a small sample syllables_annotated.json file for testing."""
    data = [
        {
            "syllable": "ka",
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
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
        {
            "syllable": "ki",
            "frequency": 80,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": True,
                "contains_fricative": False,
                "contains_liquid": False,
                "contains_nasal": False,
                "short_vowel": False,
                "long_vowel": True,
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
        {
            "syllable": "ta",
            "frequency": 90,
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
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
    ]

    file_path = tmp_path / "test_syllables.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    return file_path
