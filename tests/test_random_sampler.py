"""
Comprehensive test suite for random sampler utility.

This test module covers the random_sampler utility in the syllable_feature_annotator:
- Loading annotated syllables from JSON
- Random sampling with configurable count
- Deterministic sampling with seeds
- Saving samples to JSON
- CLI argument parsing
- Error handling and edge cases
- Integration testing

Test Organization
-----------------
1. TestLoadAnnotatedSyllables: JSON loading and validation
2. TestSampleSyllables: Sampling logic and constraints
3. TestSaveSamples: File output operations
4. TestArgumentParsing: CLI argument handling
5. TestErrorHandling: Error cases and validation
6. TestDeterminism: Reproducibility with seeds
7. TestIntegration: End-to-end workflow

Running Tests
-------------
Run all tests::

    $ pytest tests/test_random_sampler.py -v

Run specific test class::

    $ pytest tests/test_random_sampler.py::TestDeterminism -v

Run with coverage::

    $ pytest tests/test_random_sampler.py --cov=build_tools.syllable_feature_annotator.random_sampler
"""

import json
from unittest.mock import patch

import pytest

from build_tools.syllable_feature_annotator.random_sampler import (
    load_annotated_syllables,
    main,
    parse_arguments,
    sample_syllables,
    save_samples,
)

# =========================================================================
# Test Fixtures
# =========================================================================


@pytest.fixture
def sample_annotated_data():
    """Create sample annotated syllable data for testing."""
    return [
        {
            "syllable": "ka",
            "frequency": 187,
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
            "syllable": "ran",
            "frequency": 162,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": False,
                "contains_fricative": False,
                "contains_liquid": True,
                "contains_nasal": True,
                "short_vowel": True,
                "long_vowel": False,
                "ends_with_vowel": False,
                "ends_with_nasal": True,
                "ends_with_stop": False,
            },
        },
        {
            "syllable": "spla",
            "frequency": 2,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": True,
                "starts_with_heavy_cluster": True,
                "contains_plosive": True,
                "contains_fricative": True,
                "contains_liquid": True,
                "contains_nasal": False,
                "short_vowel": True,
                "long_vowel": False,
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
        {
            "syllable": "mi",
            "frequency": 145,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": False,
                "contains_fricative": False,
                "contains_liquid": False,
                "contains_nasal": True,
                "short_vowel": True,
                "long_vowel": False,
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
        {
            "syllable": "ta",
            "frequency": 98,
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


@pytest.fixture
def temp_json_file(tmp_path, sample_annotated_data):
    """Create a temporary JSON file with sample data."""
    json_file = tmp_path / "test_annotated.json"
    with json_file.open("w") as f:
        json.dump(sample_annotated_data, f)
    return json_file


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


# =========================================================================
# Test LoadAnnotatedSyllables
# =========================================================================


class TestLoadAnnotatedSyllables:
    """Test loading annotated syllables from JSON files."""

    def test_load_valid_json(self, temp_json_file, sample_annotated_data):
        """Test loading valid JSON file."""
        records = load_annotated_syllables(temp_json_file)
        assert len(records) == 5
        assert records == sample_annotated_data

    def test_load_preserves_structure(self, temp_json_file):
        """Test that loading preserves all fields and structure."""
        records = load_annotated_syllables(temp_json_file)
        first_record = records[0]
        assert "syllable" in first_record
        assert "frequency" in first_record
        assert "features" in first_record
        assert isinstance(first_record["features"], dict)
        assert len(first_record["features"]) == 12  # 12 feature flags

    def test_load_nonexistent_file(self, tmp_path):
        """Test error handling for nonexistent file."""
        nonexistent = tmp_path / "does_not_exist.json"
        with pytest.raises(FileNotFoundError):
            load_annotated_syllables(nonexistent)

    def test_load_invalid_json(self, tmp_path):
        """Test error handling for invalid JSON."""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("not valid json {]")
        with pytest.raises(json.JSONDecodeError):
            load_annotated_syllables(invalid_json)

    def test_load_non_list_json(self, tmp_path):
        """Test error handling when JSON is not a list."""
        non_list_json = tmp_path / "non_list.json"
        with non_list_json.open("w") as f:
            json.dump({"syllable": "ka"}, f)
        with pytest.raises(ValueError, match="Expected list of records"):
            load_annotated_syllables(non_list_json)

    def test_load_empty_list(self, tmp_path):
        """Test loading empty JSON list."""
        empty_json = tmp_path / "empty.json"
        with empty_json.open("w") as f:
            json.dump([], f)
        records = load_annotated_syllables(empty_json)
        assert records == []


# =========================================================================
# Test SampleSyllables
# =========================================================================


class TestSampleSyllables:
    """Test random sampling functionality."""

    def test_sample_basic(self, sample_annotated_data):
        """Test basic sampling without seed."""
        samples = sample_syllables(sample_annotated_data, 3)
        assert len(samples) == 3
        assert all(s in sample_annotated_data for s in samples)

    def test_sample_all_records(self, sample_annotated_data):
        """Test sampling all available records."""
        samples = sample_syllables(sample_annotated_data, 5)
        assert len(samples) == 5
        assert set(s["syllable"] for s in samples) == set(
            s["syllable"] for s in sample_annotated_data
        )

    def test_sample_single_record(self, sample_annotated_data):
        """Test sampling a single record."""
        samples = sample_syllables(sample_annotated_data, 1)
        assert len(samples) == 1
        assert samples[0] in sample_annotated_data

    def test_sample_preserves_structure(self, sample_annotated_data):
        """Test that sampling preserves record structure."""
        samples = sample_syllables(sample_annotated_data, 2)
        for sample in samples:
            assert "syllable" in sample
            assert "frequency" in sample
            assert "features" in sample
            assert isinstance(sample["features"], dict)

    def test_sample_too_many_raises_error(self, sample_annotated_data):
        """Test that sampling more than available raises error."""
        with pytest.raises(ValueError, match="Cannot sample 10 records from 5"):
            sample_syllables(sample_annotated_data, 10)

    def test_sample_zero_records(self, sample_annotated_data):
        """Test sampling zero records."""
        samples = sample_syllables(sample_annotated_data, 0)
        assert samples == []

    def test_sample_uniqueness(self, sample_annotated_data):
        """Test that samples are unique (no duplicates)."""
        samples = sample_syllables(sample_annotated_data, 5)
        syllables = [s["syllable"] for s in samples]
        assert len(syllables) == len(set(syllables))


# =========================================================================
# Test SaveSamples
# =========================================================================


class TestSaveSamples:
    """Test saving samples to JSON files."""

    def test_save_basic(self, temp_output_dir, sample_annotated_data):
        """Test basic saving functionality."""
        output_file = temp_output_dir / "samples.json"
        samples = sample_annotated_data[:3]
        save_samples(samples, output_file)

        assert output_file.exists()
        with output_file.open() as f:
            loaded = json.load(f)
        assert loaded == samples

    def test_save_creates_directory(self, tmp_path, sample_annotated_data):
        """Test that save creates parent directory if needed."""
        output_file = tmp_path / "nested" / "dir" / "samples.json"
        samples = sample_annotated_data[:2]
        save_samples(samples, output_file)

        assert output_file.exists()
        with output_file.open() as f:
            loaded = json.load(f)
        assert loaded == samples

    def test_save_formatted_json(self, temp_output_dir, sample_annotated_data):
        """Test that JSON is saved with proper formatting."""
        output_file = temp_output_dir / "samples.json"
        samples = sample_annotated_data[:1]
        save_samples(samples, output_file)

        content = output_file.read_text()
        # Check that JSON is indented (not minified)
        assert "\n" in content
        assert "  " in content  # Indentation

    def test_save_empty_list(self, temp_output_dir):
        """Test saving empty sample list."""
        output_file = temp_output_dir / "empty.json"
        save_samples([], output_file)

        assert output_file.exists()
        with output_file.open() as f:
            loaded = json.load(f)
        assert loaded == []

    def test_save_overwrites_existing(self, temp_output_dir, sample_annotated_data):
        """Test that save overwrites existing files."""
        output_file = temp_output_dir / "samples.json"

        # Save first set
        save_samples(sample_annotated_data[:2], output_file)

        # Save second set (should overwrite)
        save_samples(sample_annotated_data[2:4], output_file)

        with output_file.open() as f:
            loaded = json.load(f)
        assert len(loaded) == 2
        assert loaded[0]["syllable"] == "spla"


# =========================================================================
# Test ArgumentParsing
# =========================================================================


class TestArgumentParsing:
    """Test CLI argument parsing."""

    def test_parse_no_arguments(self):
        """Test parsing with default arguments."""
        with patch("sys.argv", ["random_sampler.py"]):
            args = parse_arguments()
            assert args.samples == 100
            assert args.seed is None
            assert "syllables_annotated.json" in str(args.input)
            assert "random_samples.json" in str(args.output)

    def test_parse_samples_argument(self):
        """Test parsing --samples argument."""
        with patch("sys.argv", ["random_sampler.py", "--samples", "50"]):
            args = parse_arguments()
            assert args.samples == 50

    def test_parse_seed_argument(self):
        """Test parsing --seed argument."""
        with patch("sys.argv", ["random_sampler.py", "--seed", "42"]):
            args = parse_arguments()
            assert args.seed == 42

    def test_parse_input_output_paths(self, tmp_path):
        """Test parsing --input and --output arguments."""
        input_path = tmp_path / "input.json"
        output_path = tmp_path / "output.json"

        with patch(
            "sys.argv",
            [
                "random_sampler.py",
                "--input",
                str(input_path),
                "--output",
                str(output_path),
            ],
        ):
            args = parse_arguments()
            assert args.input == input_path
            assert args.output == output_path

    def test_parse_all_arguments(self, tmp_path):
        """Test parsing all arguments together."""
        input_path = tmp_path / "input.json"
        output_path = tmp_path / "output.json"

        with patch(
            "sys.argv",
            [
                "random_sampler.py",
                "--input",
                str(input_path),
                "--output",
                str(output_path),
                "--samples",
                "75",
                "--seed",
                "123",
            ],
        ):
            args = parse_arguments()
            assert args.input == input_path
            assert args.output == output_path
            assert args.samples == 75
            assert args.seed == 123


# =========================================================================
# Test ErrorHandling
# =========================================================================


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_main_nonexistent_input(self, tmp_path, capsys):
        """Test main function with nonexistent input file."""
        nonexistent = tmp_path / "does_not_exist.json"
        output = tmp_path / "output.json"

        with patch(
            "sys.argv",
            [
                "random_sampler.py",
                "--input",
                str(nonexistent),
                "--output",
                str(output),
            ],
        ):
            exit_code = main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.err

    def test_main_sample_too_many(self, temp_json_file, tmp_path, capsys):
        """Test main function when sampling more than available."""
        output = tmp_path / "output.json"

        with patch(
            "sys.argv",
            [
                "random_sampler.py",
                "--input",
                str(temp_json_file),
                "--output",
                str(output),
                "--samples",
                "1000",  # More than available (5)
            ],
        ):
            exit_code = main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "Cannot sample" in captured.err

    def test_main_invalid_json(self, tmp_path, capsys):
        """Test main function with invalid JSON input."""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("not valid json")
        output = tmp_path / "output.json"

        with patch(
            "sys.argv",
            [
                "random_sampler.py",
                "--input",
                str(invalid_json),
                "--output",
                str(output),
            ],
        ):
            exit_code = main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.err


# =========================================================================
# Test Determinism
# =========================================================================


class TestDeterminism:
    """Test deterministic sampling with seeds."""

    def test_same_seed_same_samples(self, sample_annotated_data):
        """Test that same seed produces same samples."""
        samples1 = sample_syllables(sample_annotated_data, 3, seed=42)
        samples2 = sample_syllables(sample_annotated_data, 3, seed=42)

        assert samples1 == samples2

    def test_different_seed_different_samples(self, sample_annotated_data):
        """Test that different seeds produce different samples."""
        samples1 = sample_syllables(sample_annotated_data, 3, seed=42)
        samples2 = sample_syllables(sample_annotated_data, 3, seed=123)

        # Different seeds should (very likely) produce different samples
        # Note: There's a small probability they could be the same by chance
        syllables1 = [s["syllable"] for s in samples1]
        syllables2 = [s["syllable"] for s in samples2]
        assert syllables1 != syllables2

    def test_none_seed_random_samples(self, sample_annotated_data):
        """Test that None seed produces random (non-deterministic) samples."""
        samples1 = sample_syllables(sample_annotated_data, 3, seed=None)
        samples2 = sample_syllables(sample_annotated_data, 3, seed=None)

        # Without seed, samples could be the same or different
        # Just verify they're valid samples
        assert len(samples1) == 3
        assert len(samples2) == 3
        assert all(s in sample_annotated_data for s in samples1)
        assert all(s in sample_annotated_data for s in samples2)

    def test_determinism_with_large_sample(self, sample_annotated_data):
        """Test determinism with larger sample size."""
        samples1 = sample_syllables(sample_annotated_data, 5, seed=999)
        samples2 = sample_syllables(sample_annotated_data, 5, seed=999)

        assert samples1 == samples2

    def test_seed_preserves_order(self, sample_annotated_data):
        """Test that seed preserves order of samples."""
        samples1 = sample_syllables(sample_annotated_data, 4, seed=42)
        samples2 = sample_syllables(sample_annotated_data, 4, seed=42)

        syllables1 = [s["syllable"] for s in samples1]
        syllables2 = [s["syllable"] for s in samples2]

        assert syllables1 == syllables2  # Same order


# =========================================================================
# Test Integration
# =========================================================================


class TestIntegration:
    """Test end-to-end integration."""

    def test_full_workflow(self, temp_json_file, temp_output_dir, sample_annotated_data):
        """Test complete workflow from load to save."""
        # Load
        records = load_annotated_syllables(temp_json_file)
        assert len(records) == 5

        # Sample
        samples = sample_syllables(records, 3, seed=42)
        assert len(samples) == 3

        # Save
        output_file = temp_output_dir / "samples.json"
        save_samples(samples, output_file)
        assert output_file.exists()

        # Verify saved content
        with output_file.open() as f:
            loaded = json.load(f)
        assert loaded == samples

    def test_main_success(self, temp_json_file, temp_output_dir, capsys):
        """Test main function with successful execution."""
        output_file = temp_output_dir / "samples.json"

        with patch(
            "sys.argv",
            [
                "random_sampler.py",
                "--input",
                str(temp_json_file),
                "--output",
                str(output_file),
                "--samples",
                "3",
                "--seed",
                "42",
            ],
        ):
            exit_code = main()

        assert exit_code == 0
        assert output_file.exists()

        captured = capsys.readouterr()
        assert "Loading" in captured.out
        assert "Sampling" in captured.out
        assert "Successfully saved" in captured.out

    def test_main_reproducibility(self, temp_json_file, temp_output_dir):
        """Test that main produces reproducible results with seed."""
        output1 = temp_output_dir / "samples1.json"
        output2 = temp_output_dir / "samples2.json"

        # Run first time
        with patch(
            "sys.argv",
            [
                "random_sampler.py",
                "--input",
                str(temp_json_file),
                "--output",
                str(output1),
                "--samples",
                "3",
                "--seed",
                "42",
            ],
        ):
            main()

        # Run second time with same seed
        with patch(
            "sys.argv",
            [
                "random_sampler.py",
                "--input",
                str(temp_json_file),
                "--output",
                str(output2),
                "--samples",
                "3",
                "--seed",
                "42",
            ],
        ):
            main()

        # Compare outputs
        with output1.open() as f:
            samples1 = json.load(f)
        with output2.open() as f:
            samples2 = json.load(f)

        assert samples1 == samples2

    def test_roundtrip_preserves_data(self, temp_json_file, temp_output_dir):
        """Test that data is preserved through load-sample-save cycle."""
        # Load original
        records = load_annotated_syllables(temp_json_file)

        # Sample all records
        samples = sample_syllables(records, len(records), seed=42)

        # Save
        output_file = temp_output_dir / "all_samples.json"
        save_samples(samples, output_file)

        # Load saved samples
        with output_file.open() as f:
            reloaded = json.load(f)

        # Verify all fields preserved for each record
        for original, sampled in zip(records, reloaded):
            assert original["syllable"] in [s["syllable"] for s in samples]
            assert "frequency" in sampled
            assert "features" in sampled
            assert len(sampled["features"]) == 12
