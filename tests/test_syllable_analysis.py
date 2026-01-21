"""Tests for syllable analysis module.

This module tests the common utilities and analysis functions:
- Data I/O: load_annotated_syllables, load_frequency_data, save_json_output
- Path utilities: AnalysisPathConfig, default_paths, ensure_output_dir
- Random sampler: sample_syllables
- Feature signatures: extract_signature, analyze_feature_signatures
"""

import json

import pytest

from build_tools.syllable_analysis import (
    analyze_feature_signatures,
    default_paths,
    ensure_output_dir,
    extract_signature,
    format_signature_report,
    generate_output_pair,
    generate_timestamped_path,
    load_annotated_syllables,
    load_frequency_data,
    run_analysis,
    sample_syllables,
    save_json_output,
    save_report,
)
from build_tools.syllable_analysis.feature_signatures import (
    create_argument_parser as create_fs_argument_parser,
)
from build_tools.syllable_analysis.feature_signatures import (
    main as feature_signatures_main,
)
from build_tools.syllable_analysis.feature_signatures import (
    parse_args as parse_fs_args,
)
from build_tools.syllable_analysis.random_sampler import (
    create_argument_parser as create_rs_argument_parser,
)
from build_tools.syllable_analysis.random_sampler import (
    main as random_sampler_main,
)
from build_tools.syllable_analysis.random_sampler import (
    parse_arguments as parse_rs_arguments,
)

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def sample_annotated_data():
    """Sample annotated syllable data for testing."""
    return [
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
            "syllable": "an",
            "frequency": 80,
            "features": {
                "starts_with_vowel": True,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": False,
                "contains_fricative": False,
                "contains_liquid": False,
                "contains_nasal": True,
                "short_vowel": True,
                "long_vowel": False,
                "ends_with_vowel": False,
                "ends_with_nasal": True,
                "ends_with_stop": False,
            },
        },
        {
            "syllable": "str",
            "frequency": 50,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": True,
                "starts_with_heavy_cluster": True,
                "contains_plosive": True,
                "contains_fricative": True,
                "contains_liquid": False,
                "contains_nasal": False,
                "short_vowel": False,
                "long_vowel": False,
                "ends_with_vowel": False,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
    ]


@pytest.fixture
def annotated_json_file(tmp_path, sample_annotated_data):
    """Create a temporary annotated JSON file."""
    file_path = tmp_path / "syllables_annotated.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sample_annotated_data, f)
    return file_path


# ============================================================
# Data I/O Tests
# ============================================================


class TestLoadAnnotatedSyllables:
    """Test load_annotated_syllables function."""

    def test_loads_valid_file(self, annotated_json_file):
        """Test loading a valid annotated JSON file."""
        records = load_annotated_syllables(annotated_json_file)

        assert len(records) == 3
        assert records[0]["syllable"] == "ka"
        assert "features" in records[0]

    def test_loads_without_validation(self, annotated_json_file):
        """Test loading without validation."""
        records = load_annotated_syllables(annotated_json_file, validate=False)
        assert len(records) == 3

    def test_raises_for_nonexistent_file(self, tmp_path):
        """Test raises FileNotFoundError for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            load_annotated_syllables(tmp_path / "nonexistent.json")

    def test_raises_for_invalid_json(self, tmp_path):
        """Test raises for invalid JSON file."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            load_annotated_syllables(invalid_file)

    def test_raises_for_empty_list(self, tmp_path):
        """Test raises ValueError for empty data."""
        empty_file = tmp_path / "empty.json"
        with open(empty_file, "w", encoding="utf-8") as f:
            json.dump([], f)

        with pytest.raises(ValueError, match="no records"):
            load_annotated_syllables(empty_file)

    def test_raises_for_non_list(self, tmp_path):
        """Test raises ValueError for non-list data."""
        dict_file = tmp_path / "dict.json"
        with open(dict_file, "w", encoding="utf-8") as f:
            json.dump({"key": "value"}, f)

        with pytest.raises(ValueError, match="Expected list of records"):
            load_annotated_syllables(dict_file)

    def test_raises_for_missing_keys(self, tmp_path):
        """Test raises ValueError for data missing required keys."""
        invalid_file = tmp_path / "missing_keys.json"
        with open(invalid_file, "w", encoding="utf-8") as f:
            json.dump([{"syllable": "ka"}], f)  # Missing 'frequency' and 'features'

        with pytest.raises(ValueError, match="missing required keys"):
            load_annotated_syllables(invalid_file)


class TestLoadFrequencyData:
    """Test load_frequency_data function."""

    def test_loads_valid_frequency_file(self, tmp_path):
        """Test loading a valid frequency JSON file."""
        freq_file = tmp_path / "frequencies.json"
        freq_data = {"ka": 100, "an": 80, "ba": 60}
        with open(freq_file, "w", encoding="utf-8") as f:
            json.dump(freq_data, f)

        result = load_frequency_data(freq_file)

        assert result == freq_data
        assert result["ka"] == 100

    def test_raises_for_nonexistent_file(self, tmp_path):
        """Test raises FileNotFoundError for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            load_frequency_data(tmp_path / "nonexistent.json")

    def test_raises_for_non_dict(self, tmp_path):
        """Test raises ValueError for non-dict JSON."""
        list_file = tmp_path / "list.json"
        with open(list_file, "w", encoding="utf-8") as f:
            json.dump([1, 2, 3], f)

        with pytest.raises(ValueError, match="Expected dictionary"):
            load_frequency_data(list_file)


class TestSaveJsonOutput:
    """Test save_json_output function."""

    def test_saves_to_file(self, tmp_path):
        """Test saving data to file."""
        data = {"test": "value", "number": 42}
        output_path = tmp_path / "output.json"

        save_json_output(data, output_path)

        assert output_path.exists()
        with open(output_path, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == data

    def test_creates_parent_directories(self, tmp_path):
        """Test creates parent directories if needed."""
        data = [1, 2, 3]
        output_path = tmp_path / "nested" / "dir" / "output.json"

        save_json_output(data, output_path)

        assert output_path.exists()

    def test_preserves_unicode(self, tmp_path):
        """Test preserves unicode characters."""
        data = {"unicode": "héllo wörld 日本語"}
        output_path = tmp_path / "unicode.json"

        save_json_output(data, output_path)

        with open(output_path, encoding="utf-8") as f:
            content = f.read()
        assert "héllo" in content
        assert "日本語" in content


# ============================================================
# Path Utilities Tests
# ============================================================


class TestAnalysisPathConfig:
    """Test AnalysisPathConfig class."""

    def test_default_paths_exist(self):
        """Test default path configuration has expected attributes."""
        assert hasattr(default_paths, "annotated_syllables")
        assert hasattr(default_paths, "syllables_frequencies")
        assert hasattr(default_paths, "analysis_output_dir")

    def test_analysis_output_dir(self):
        """Test analysis_output_dir method."""
        path = default_paths.analysis_output_dir("test_tool")
        assert "test_tool" in str(path)


class TestEnsureOutputDir:
    """Test ensure_output_dir function."""

    def test_creates_directory(self, tmp_path):
        """Test creates output directory."""
        output_dir = tmp_path / "new_dir"

        result = ensure_output_dir(output_dir)

        assert result.exists()
        assert result.is_dir()
        assert result == output_dir

    def test_handles_existing_directory(self, tmp_path):
        """Test handles existing directory."""
        output_dir = tmp_path / "existing"
        output_dir.mkdir()

        result = ensure_output_dir(output_dir)

        assert result == output_dir

    def test_creates_nested_directories(self, tmp_path):
        """Test creates nested directories."""
        output_dir = tmp_path / "a" / "b" / "c"

        result = ensure_output_dir(output_dir)

        assert result.exists()


class TestGenerateOutputPair:
    """Test generate_output_pair function."""

    def test_generates_json_and_txt_pair(self, tmp_path):
        """Test generates paired paths with matching timestamps."""
        primary_path, meta_path = generate_output_pair(
            tmp_path,
            primary_suffix="primary",
            metadata_suffix="metadata",
            primary_ext="json",
            metadata_ext="txt",
        )

        assert primary_path.suffix == ".json"
        assert meta_path.suffix == ".txt"
        # Both should share the same timestamp (first part of filename)
        primary_timestamp = primary_path.name.split(".")[0]
        meta_timestamp = meta_path.name.split(".")[0]
        assert primary_timestamp == meta_timestamp


class TestGenerateTimestampedPath:
    """Test generate_timestamped_path function."""

    def test_generates_timestamped_path(self, tmp_path):
        """Test generates path with timestamp."""
        path = generate_timestamped_path(tmp_path, "test", "json")

        assert path.parent == tmp_path
        assert path.suffix == ".json"
        # Format: {timestamp}.{suffix}.{extension}
        assert ".test." in path.name


# ============================================================
# Random Sampler Tests
# ============================================================


class TestSampleSyllables:
    """Test sample_syllables function."""

    def test_returns_requested_count(self, sample_annotated_data):
        """Test returns the requested number of samples."""
        samples = sample_syllables(sample_annotated_data, 2)
        assert len(samples) == 2

    def test_deterministic_with_seed(self, sample_annotated_data):
        """Test same seed produces same results."""
        samples1 = sample_syllables(sample_annotated_data, 2, seed=42)
        samples2 = sample_syllables(sample_annotated_data, 2, seed=42)

        assert samples1 == samples2

    def test_different_seeds_may_differ(self, sample_annotated_data):
        """Test different seeds can produce different results."""
        # Run with different seeds - results may or may not differ by chance
        result1 = sample_syllables(sample_annotated_data, 2, seed=1)
        result2 = sample_syllables(sample_annotated_data, 2, seed=2)
        # Both should return valid results
        assert len(result1) == 2
        assert len(result2) == 2

    def test_raises_for_oversized_sample(self, sample_annotated_data):
        """Test raises ValueError for sample larger than data."""
        with pytest.raises(ValueError, match="Cannot sample"):
            sample_syllables(sample_annotated_data, 100)


# ============================================================
# Feature Signatures Tests
# ============================================================


class TestExtractSignature:
    """Test extract_signature function."""

    def test_extracts_signature_tuple(self, sample_annotated_data):
        """Test extracts signature as tuple of active feature names."""
        record = sample_annotated_data[0]  # "ka"
        signature = extract_signature(record["features"])

        assert isinstance(signature, tuple)
        # Signature contains only the names of True features (sorted)
        assert all(isinstance(v, str) for v in signature)
        # "ka" has: contains_plosive=True, short_vowel=True, ends_with_vowel=True
        assert "contains_plosive" in signature
        assert "short_vowel" in signature
        assert "ends_with_vowel" in signature

    def test_signature_is_consistent(self, sample_annotated_data):
        """Test same features produce same signature."""
        features = sample_annotated_data[0]["features"]

        sig1 = extract_signature(features)
        sig2 = extract_signature(features)

        assert sig1 == sig2


class TestAnalyzeFeatureSignatures:
    """Test analyze_feature_signatures function."""

    def test_returns_counter(self, sample_annotated_data):
        """Test returns Counter of signature occurrences."""
        from collections import Counter

        result = analyze_feature_signatures(sample_annotated_data)

        assert isinstance(result, Counter)
        # Total of all counts should equal number of records
        assert sum(result.values()) == 3

    def test_counts_unique_signatures(self, sample_annotated_data):
        """Test counts unique signatures."""
        result = analyze_feature_signatures(sample_annotated_data)

        # Each test syllable has a unique signature
        assert len(result) == 3


class TestFormatSignatureReport:
    """Test format_signature_report function."""

    def test_returns_formatted_string(self, sample_annotated_data):
        """Test returns formatted report string."""
        signature_counter = analyze_feature_signatures(sample_annotated_data)
        total_syllables = len(sample_annotated_data)
        report = format_signature_report(signature_counter, total_syllables)

        assert isinstance(report, str)
        assert "FEATURE SIGNATURE ANALYSIS" in report
        assert "3" in report  # Total syllables

    def test_report_with_limit(self, sample_annotated_data):
        """Test report with limited signatures."""
        signature_counter = analyze_feature_signatures(sample_annotated_data)
        total_syllables = len(sample_annotated_data)
        report = format_signature_report(signature_counter, total_syllables, limit=2)

        assert isinstance(report, str)
        assert "SIGNATURE RANKINGS" in report


class TestSaveReport:
    """Test save_report function."""

    def test_saves_report_file(self, tmp_path):
        """Test saving report to file."""
        output_dir = tmp_path / "output"
        report = "Test report content"

        result_path = save_report(report, output_dir)

        assert result_path.exists()
        assert result_path.suffix == ".txt"
        content = result_path.read_text(encoding="utf-8")
        assert content == report

    def test_creates_output_directory(self, tmp_path):
        """Test creates output directory if needed."""
        output_dir = tmp_path / "nested" / "dir"

        save_report("content", output_dir)

        assert output_dir.exists()


class TestRunAnalysis:
    """Test run_analysis function."""

    def test_runs_complete_analysis(self, annotated_json_file, tmp_path):
        """Test running complete analysis pipeline."""
        output_dir = tmp_path / "analysis"

        result = run_analysis(annotated_json_file, output_dir)

        assert "total_syllables" in result
        assert "unique_signatures" in result
        assert "output_path" in result
        assert "signature_counter" in result
        assert result["total_syllables"] == 3
        assert result["output_path"].exists()

    def test_runs_with_limit(self, annotated_json_file, tmp_path):
        """Test running analysis with limit."""
        output_dir = tmp_path / "analysis"

        result = run_analysis(annotated_json_file, output_dir, limit=2)

        assert result["total_syllables"] == 3


# ============================================================
# CLI Tests
# ============================================================


class TestFeatureSignaturesCLI:
    """Test feature_signatures CLI functions."""

    def test_create_argument_parser(self):
        """Test creating argument parser."""
        parser = create_fs_argument_parser()

        assert parser is not None
        # Check expected arguments exist by parsing empty args (defaults)
        args = parser.parse_args([])
        assert hasattr(args, "input")
        assert hasattr(args, "output")
        assert hasattr(args, "limit")

    def test_parse_args_defaults(self):
        """Test parsing with default arguments."""
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["prog"]):
            args = parse_fs_args()
            assert args.limit is None

    def test_parse_args_with_limit(self):
        """Test parsing with limit argument."""
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["prog", "--limit", "50"]):
            args = parse_fs_args()
            assert args.limit == 50

    def test_main_with_nonexistent_input(self, capsys, tmp_path):
        """Test main function with nonexistent input file."""
        import sys
        from unittest.mock import patch

        fake_input = tmp_path / "nonexistent.json"
        with patch.object(sys, "argv", ["prog", "--input", str(fake_input)]):
            feature_signatures_main()

        captured = capsys.readouterr()
        assert "not found" in captured.out or "Error" in captured.out

    def test_main_success(self, annotated_json_file, tmp_path, capsys):
        """Test main function with valid inputs."""
        import sys
        from unittest.mock import patch

        output_dir = tmp_path / "output"
        with patch.object(
            sys,
            "argv",
            ["prog", "--input", str(annotated_json_file), "--output", str(output_dir)],
        ):
            feature_signatures_main()

        captured = capsys.readouterr()
        assert "Analyzed" in captured.out or "syllables" in captured.out


class TestRandomSamplerCLI:
    """Test random_sampler CLI functions."""

    def test_create_argument_parser(self):
        """Test creating argument parser."""
        parser = create_rs_argument_parser()

        assert parser is not None
        # Check expected arguments exist
        args = parser.parse_args([])
        assert hasattr(args, "input")
        assert hasattr(args, "output")
        assert hasattr(args, "samples")
        assert hasattr(args, "seed")

    def test_parse_arguments_defaults(self):
        """Test parsing with default arguments."""
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["prog"]):
            args = parse_rs_arguments()
            assert args.samples == 100
            assert args.seed is None

    def test_parse_arguments_with_options(self):
        """Test parsing with custom arguments."""
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", ["prog", "--samples", "50", "--seed", "42"]):
            args = parse_rs_arguments()
            assert args.samples == 50
            assert args.seed == 42

    def test_main_success(self, annotated_json_file, tmp_path, capsys):
        """Test main function success path."""
        import sys
        from unittest.mock import patch

        output_file = tmp_path / "samples.json"
        with patch.object(
            sys,
            "argv",
            [
                "prog",
                "--input",
                str(annotated_json_file),
                "--output",
                str(output_file),
                "--samples",
                "2",
                "--seed",
                "42",
            ],
        ):
            exit_code = random_sampler_main()

        assert exit_code == 0
        assert output_file.exists()
        captured = capsys.readouterr()
        assert "Successfully saved" in captured.out

    def test_main_with_nonexistent_input(self, tmp_path, capsys):
        """Test main function with nonexistent input."""
        import sys
        from unittest.mock import patch

        with patch.object(
            sys,
            "argv",
            ["prog", "--input", str(tmp_path / "nonexistent.json")],
        ):
            exit_code = random_sampler_main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_main_with_invalid_sample_count(self, annotated_json_file, tmp_path, capsys):
        """Test main function with sample count larger than data."""
        import sys
        from unittest.mock import patch

        with patch.object(
            sys,
            "argv",
            [
                "prog",
                "--input",
                str(annotated_json_file),
                "--output",
                str(tmp_path / "samples.json"),
                "--samples",
                "1000",  # More than 3 records in fixture
            ],
        ):
            exit_code = random_sampler_main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_main_with_invalid_json(self, tmp_path, capsys):
        """Test main function with invalid JSON input."""
        import sys
        from unittest.mock import patch

        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json", encoding="utf-8")

        with patch.object(
            sys,
            "argv",
            ["prog", "--input", str(invalid_file)],
        ):
            exit_code = random_sampler_main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err


# ============================================================
# Integration Tests
# ============================================================


class TestIntegration:
    """Integration tests for analysis module."""

    def test_load_sample_save_workflow(self, annotated_json_file, tmp_path):
        """Test complete load -> sample -> save workflow."""
        # Load
        records = load_annotated_syllables(annotated_json_file)
        assert len(records) == 3

        # Sample
        samples = sample_syllables(records, 2, seed=42)
        assert len(samples) == 2

        # Save
        output_path = tmp_path / "samples.json"
        save_json_output(samples, output_path)
        assert output_path.exists()

        # Verify saved content
        with open(output_path, encoding="utf-8") as f:
            loaded = json.load(f)
        assert len(loaded) == 2

    def test_analysis_with_file_output(self, annotated_json_file, tmp_path):
        """Test feature signature analysis with file output."""
        records = load_annotated_syllables(annotated_json_file)
        signature_counter = analyze_feature_signatures(records)
        report = format_signature_report(signature_counter, len(records))

        output_path = tmp_path / "report.txt"
        output_path.write_text(report, encoding="utf-8")

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert len(content) > 0
