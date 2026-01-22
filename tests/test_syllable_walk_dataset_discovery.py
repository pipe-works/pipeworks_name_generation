"""Tests for syllable walker dataset discovery module.

This module tests all functionality of the dataset discovery system:
- DatasetInfo dataclass and serialization
- load_dataset_metadata() for extracting metadata from files
- discover_datasets() for scanning directories
- get_default_dataset() for selecting the most recent dataset
"""

import json
from pathlib import Path

import pytest

from build_tools.syllable_walk_web.dataset_discovery import (
    DatasetInfo,
    discover_datasets,
    get_default_dataset,
    load_dataset_metadata,
)

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def sample_syllables_data():
    """Sample syllable data for creating test files."""
    return [
        {
            "syllable": "ka",
            "frequency": 100,
            "features": {
                "starts_with_vowel": False,
                "ends_with_vowel": True,
            },
        },
        {
            "syllable": "ki",
            "frequency": 80,
            "features": {
                "starts_with_vowel": False,
                "ends_with_vowel": True,
            },
        },
        {
            "syllable": "ta",
            "frequency": 90,
            "features": {
                "starts_with_vowel": False,
                "ends_with_vowel": True,
            },
        },
    ]


@pytest.fixture
def nltk_annotated_file(tmp_path, sample_syllables_data):
    """Create a test NLTK annotated file with proper directory structure."""
    run_dir = tmp_path / "20260115_120000_nltk"
    data_dir = run_dir / "data"
    data_dir.mkdir(parents=True)

    file_path = data_dir / "nltk_syllables_annotated.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sample_syllables_data, f)

    return file_path


@pytest.fixture
def pyphen_annotated_file(tmp_path, sample_syllables_data):
    """Create a test pyphen annotated file with proper directory structure."""
    run_dir = tmp_path / "20260114_100000_pyphen"
    data_dir = run_dir / "data"
    data_dir.mkdir(parents=True)

    file_path = data_dir / "pyphen_syllables_annotated.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sample_syllables_data, f)

    return file_path


@pytest.fixture
def legacy_annotated_file(tmp_path, sample_syllables_data):
    """Create a test legacy annotated file (data/annotated/)."""
    legacy_dir = tmp_path / "data" / "annotated"
    legacy_dir.mkdir(parents=True)

    file_path = legacy_dir / "syllables_annotated.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sample_syllables_data, f)

    return file_path


@pytest.fixture
def output_dir_with_datasets(tmp_path, sample_syllables_data):
    """Create a _working/output directory with multiple datasets."""
    output_dir = tmp_path / "_working" / "output"

    # Create NLTK dataset (newer)
    nltk_run = output_dir / "20260115_120000_nltk" / "data"
    nltk_run.mkdir(parents=True)
    with open(nltk_run / "nltk_syllables_annotated.json", "w", encoding="utf-8") as f:
        json.dump(sample_syllables_data, f)

    # Create pyphen dataset (older)
    pyphen_run = output_dir / "20260114_100000_pyphen" / "data"
    pyphen_run.mkdir(parents=True)
    with open(pyphen_run / "pyphen_syllables_annotated.json", "w", encoding="utf-8") as f:
        json.dump(sample_syllables_data * 2, f)  # 6 syllables

    return output_dir


# ============================================================
# DatasetInfo Tests
# ============================================================


class TestDatasetInfo:
    """Tests for DatasetInfo dataclass."""

    def test_dataclass_creation(self):
        """Test DatasetInfo can be created with all required fields."""
        info = DatasetInfo(
            path=Path("/test/path.json"),
            name="Test Dataset",
            extractor_type="nltk",
            timestamp="20260115_120000",
            syllable_count=100,
            run_directory=Path("/test"),
            is_legacy=False,
        )

        assert info.path == Path("/test/path.json")
        assert info.name == "Test Dataset"
        assert info.extractor_type == "nltk"
        assert info.timestamp == "20260115_120000"
        assert info.syllable_count == 100
        assert info.run_directory == Path("/test")
        assert info.is_legacy is False

    def test_dataclass_optional_timestamp(self):
        """Test DatasetInfo with None timestamp."""
        info = DatasetInfo(
            path=Path("/test/path.json"),
            name="Test Dataset",
            extractor_type="unknown",
            timestamp=None,
            syllable_count=50,
            run_directory=Path("/test"),
            is_legacy=True,
        )

        assert info.timestamp is None

    def test_to_dict_method(self):
        """Test to_dict serialization."""
        test_path = Path("/test/path.json")
        test_dir = Path("/test")
        info = DatasetInfo(
            path=test_path,
            name="Test Dataset",
            extractor_type="nltk",
            timestamp="20260115_120000",
            syllable_count=100,
            run_directory=test_dir,
            is_legacy=False,
        )

        result = info.to_dict()

        assert isinstance(result, dict)
        # Compare as Path objects to handle platform differences
        assert result["path"] == str(test_path)
        assert result["name"] == "Test Dataset"
        assert result["extractor_type"] == "nltk"
        assert result["timestamp"] == "20260115_120000"
        assert result["syllable_count"] == 100
        assert result["run_directory"] == str(test_dir)
        assert result["is_legacy"] is False

    def test_to_dict_with_none_timestamp(self):
        """Test to_dict serialization handles None timestamp."""
        info = DatasetInfo(
            path=Path("/test/path.json"),
            name="Test Dataset",
            extractor_type="pyphen",
            timestamp=None,
            syllable_count=50,
            run_directory=Path("/test"),
            is_legacy=False,
        )

        result = info.to_dict()
        assert result["timestamp"] is None


# ============================================================
# load_dataset_metadata Tests
# ============================================================


class TestLoadDatasetMetadata:
    """Tests for load_dataset_metadata function."""

    def test_load_nltk_dataset(self, nltk_annotated_file):
        """Test loading metadata from NLTK annotated file."""
        info = load_dataset_metadata(nltk_annotated_file)

        assert info is not None
        assert info.extractor_type == "nltk"
        assert info.syllable_count == 3
        assert info.timestamp == "20260115_120000"
        assert info.is_legacy is False
        assert "NLTK" in info.name
        assert "3" in info.name  # syllable count in name

    def test_load_pyphen_dataset(self, pyphen_annotated_file):
        """Test loading metadata from pyphen annotated file."""
        info = load_dataset_metadata(pyphen_annotated_file)

        assert info is not None
        assert info.extractor_type == "pyphen"
        assert info.syllable_count == 3
        assert info.timestamp == "20260114_100000"
        assert info.is_legacy is False
        assert "PYPHEN" in info.name

    def test_load_legacy_dataset(self, legacy_annotated_file, sample_syllables_data):
        """Test loading metadata from legacy location."""
        info = load_dataset_metadata(legacy_annotated_file)

        assert info is not None
        assert info.is_legacy is True
        assert "Legacy" in info.name
        assert info.syllable_count == 3

    def test_load_nonexistent_file_returns_none(self):
        """Test loading nonexistent file returns None."""
        info = load_dataset_metadata(Path("/nonexistent/file.json"))
        assert info is None

    def test_load_invalid_json_returns_none(self, tmp_path):
        """Test loading invalid JSON returns None."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json{")

        info = load_dataset_metadata(invalid_file)
        assert info is None

    def test_load_non_list_json_returns_none(self, tmp_path):
        """Test loading JSON that is not a list returns None."""
        non_list_file = tmp_path / "dict.json"
        with open(non_list_file, "w", encoding="utf-8") as f:
            json.dump({"key": "value"}, f)

        info = load_dataset_metadata(non_list_file)
        assert info is None

    def test_load_unknown_extractor_type(self, tmp_path, sample_syllables_data):
        """Test loading file with unknown extractor type."""
        unknown_dir = tmp_path / "20260115_120000_unknown" / "data"
        unknown_dir.mkdir(parents=True)

        # File without pyphen_ or nltk_ prefix
        unknown_file = unknown_dir / "syllables_annotated.json"
        with open(unknown_file, "w", encoding="utf-8") as f:
            json.dump(sample_syllables_data, f)

        info = load_dataset_metadata(unknown_file)

        assert info is not None
        assert info.extractor_type == "unknown"
        assert "UNKNOWN" in info.name

    def test_load_detects_timestamp_from_directory(self, nltk_annotated_file):
        """Test timestamp is correctly extracted from directory name."""
        info = load_dataset_metadata(nltk_annotated_file)

        assert info is not None
        assert info.timestamp == "20260115_120000"

    def test_load_handles_missing_timestamp(self, tmp_path, sample_syllables_data):
        """Test handling directory without timestamp pattern."""
        no_timestamp_dir = tmp_path / "custom_run" / "data"
        no_timestamp_dir.mkdir(parents=True)

        file_path = no_timestamp_dir / "nltk_syllables_annotated.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(sample_syllables_data, f)

        info = load_dataset_metadata(file_path)

        assert info is not None
        assert info.timestamp is None
        assert "custom_run" in info.name

    def test_load_formats_timestamp_in_name(self, nltk_annotated_file):
        """Test timestamp is formatted nicely in the display name."""
        info = load_dataset_metadata(nltk_annotated_file)

        assert info is not None
        # Should contain formatted date like "2026-01-15 12:00"
        assert "2026-01-15" in info.name
        assert "12:00" in info.name

    def test_load_handles_invalid_timestamp_format(self, tmp_path, sample_syllables_data):
        """Test handling invalid timestamp format gracefully."""
        invalid_ts_dir = tmp_path / "INVALID_TS_nltk" / "data"
        invalid_ts_dir.mkdir(parents=True)

        file_path = invalid_ts_dir / "nltk_syllables_annotated.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(sample_syllables_data, f)

        info = load_dataset_metadata(file_path)

        # Should still load, just without formatted timestamp
        assert info is not None
        assert info.timestamp is None

    def test_load_resolves_path_to_absolute(self, nltk_annotated_file):
        """Test that returned path is resolved to absolute."""
        info = load_dataset_metadata(nltk_annotated_file)

        assert info is not None
        assert info.path.is_absolute()
        assert info.run_directory.is_absolute()


# ============================================================
# discover_datasets Tests
# ============================================================


class TestDiscoverDatasets:
    """Tests for discover_datasets function."""

    def test_discover_from_output_directory(self, output_dir_with_datasets):
        """Test discovering datasets from output directory."""
        datasets = discover_datasets(search_paths=[output_dir_with_datasets])

        assert len(datasets) == 2

    def test_discover_returns_sorted_by_timestamp(self, output_dir_with_datasets):
        """Test datasets are returned sorted by timestamp (newest first)."""
        datasets = discover_datasets(search_paths=[output_dir_with_datasets])

        assert len(datasets) == 2
        # NLTK (20260115) should come before pyphen (20260114)
        assert datasets[0].extractor_type == "nltk"
        assert datasets[1].extractor_type == "pyphen"

    def test_discover_with_legacy_location(self, tmp_path, sample_syllables_data):
        """Test discovering datasets including legacy location."""
        # Create legacy location
        legacy_dir = tmp_path / "data" / "annotated"
        legacy_dir.mkdir(parents=True)
        with open(legacy_dir / "syllables_annotated.json", "w", encoding="utf-8") as f:
            json.dump(sample_syllables_data, f)

        # Discover with legacy included
        datasets = discover_datasets(search_paths=[legacy_dir])

        assert len(datasets) == 1
        assert datasets[0].is_legacy is True

    def test_discover_excludes_legacy_when_disabled(self, tmp_path, sample_syllables_data):
        """Test include_legacy=False excludes legacy locations."""
        # Create both standard and legacy locations
        output_dir = tmp_path / "_working" / "output"
        nltk_run = output_dir / "20260115_120000_nltk" / "data"
        nltk_run.mkdir(parents=True)
        with open(nltk_run / "nltk_syllables_annotated.json", "w", encoding="utf-8") as f:
            json.dump(sample_syllables_data, f)

        # Without legacy
        datasets = discover_datasets(search_paths=[output_dir], include_legacy=False)
        assert len(datasets) == 1
        assert not any(ds.is_legacy for ds in datasets)

    def test_discover_skips_nonexistent_paths(self):
        """Test nonexistent paths are silently skipped."""
        datasets = discover_datasets(search_paths=[Path("/nonexistent/path")])
        assert datasets == []

    def test_discover_skips_invalid_files(self, tmp_path, sample_syllables_data):
        """Test invalid JSON files are silently skipped."""
        output_dir = tmp_path / "_working" / "output"

        # Valid file
        valid_run = output_dir / "20260115_120000_nltk" / "data"
        valid_run.mkdir(parents=True)
        with open(valid_run / "nltk_syllables_annotated.json", "w", encoding="utf-8") as f:
            json.dump(sample_syllables_data, f)

        # Invalid file
        invalid_run = output_dir / "20260114_100000_pyphen" / "data"
        invalid_run.mkdir(parents=True)
        with open(invalid_run / "pyphen_syllables_annotated.json", "w", encoding="utf-8") as f:
            f.write("not valid json")

        datasets = discover_datasets(search_paths=[output_dir])

        # Only valid file should be returned
        assert len(datasets) == 1
        assert datasets[0].extractor_type == "nltk"

    def test_discover_empty_directory(self, tmp_path):
        """Test discovering from empty directory returns empty list."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        datasets = discover_datasets(search_paths=[empty_dir])
        assert datasets == []

    def test_discover_skips_non_directory_run_dirs(self, tmp_path, sample_syllables_data):
        """Test files in output directory are skipped (not treated as run dirs)."""
        output_dir = tmp_path / "_working" / "output"
        output_dir.mkdir(parents=True)

        # Create a file instead of directory
        (output_dir / "some_file.txt").write_text("not a directory")

        # Create valid run directory
        valid_run = output_dir / "20260115_120000_nltk" / "data"
        valid_run.mkdir(parents=True)
        with open(valid_run / "nltk_syllables_annotated.json", "w", encoding="utf-8") as f:
            json.dump(sample_syllables_data, f)

        datasets = discover_datasets(search_paths=[output_dir])
        assert len(datasets) == 1

    def test_discover_skips_runs_without_data_dir(self, tmp_path, sample_syllables_data):
        """Test run directories without data/ subdirectory are skipped."""
        output_dir = tmp_path / "_working" / "output"

        # Run without data dir
        no_data_run = output_dir / "20260115_120000_nltk"
        no_data_run.mkdir(parents=True)
        (no_data_run / "some_file.txt").write_text("no data dir")

        # Valid run with data dir
        valid_run = output_dir / "20260114_100000_pyphen" / "data"
        valid_run.mkdir(parents=True)
        with open(valid_run / "pyphen_syllables_annotated.json", "w", encoding="utf-8") as f:
            json.dump(sample_syllables_data, f)

        datasets = discover_datasets(search_paths=[output_dir])
        assert len(datasets) == 1
        assert datasets[0].extractor_type == "pyphen"

    def test_discover_with_default_paths(self, monkeypatch, tmp_path, sample_syllables_data):
        """Test discover_datasets uses default paths when none provided."""
        # Change to tmp_path so default paths resolve there
        monkeypatch.chdir(tmp_path)

        # Create default _working/output structure
        output_dir = tmp_path / "_working" / "output"
        nltk_run = output_dir / "20260115_120000_nltk" / "data"
        nltk_run.mkdir(parents=True)
        with open(nltk_run / "nltk_syllables_annotated.json", "w", encoding="utf-8") as f:
            json.dump(sample_syllables_data, f)

        # Use default paths
        datasets = discover_datasets()

        assert len(datasets) >= 1
        assert any(ds.extractor_type == "nltk" for ds in datasets)

    def test_discover_legacy_sorts_after_non_legacy(self, tmp_path, sample_syllables_data):
        """Test legacy datasets sort after non-legacy ones."""
        # Create output dir with non-legacy dataset
        output_dir = tmp_path / "_working" / "output"
        nltk_run = output_dir / "20260115_120000_nltk" / "data"
        nltk_run.mkdir(parents=True)
        with open(nltk_run / "nltk_syllables_annotated.json", "w", encoding="utf-8") as f:
            json.dump(sample_syllables_data, f)

        # Create legacy location
        legacy_dir = tmp_path / "data" / "annotated"
        legacy_dir.mkdir(parents=True)
        with open(legacy_dir / "syllables_annotated.json", "w", encoding="utf-8") as f:
            json.dump(sample_syllables_data, f)

        datasets = discover_datasets(search_paths=[output_dir, legacy_dir])

        # Non-legacy should come first
        assert len(datasets) >= 2
        non_legacy = [ds for ds in datasets if not ds.is_legacy]
        legacy = [ds for ds in datasets if ds.is_legacy]
        assert len(non_legacy) >= 1
        assert len(legacy) >= 1
        # Non-legacy should appear before legacy in the list
        first_non_legacy_idx = next(i for i, ds in enumerate(datasets) if not ds.is_legacy)
        first_legacy_idx = next(i for i, ds in enumerate(datasets) if ds.is_legacy)
        assert first_non_legacy_idx < first_legacy_idx


# ============================================================
# get_default_dataset Tests
# ============================================================


class TestGetDefaultDataset:
    """Tests for get_default_dataset function."""

    def test_returns_most_recent_non_legacy(self, output_dir_with_datasets):
        """Test returns most recent non-legacy dataset."""
        datasets = discover_datasets(search_paths=[output_dir_with_datasets])
        default = get_default_dataset(datasets)

        assert default is not None
        assert default.extractor_type == "nltk"  # newer
        assert default.is_legacy is False

    def test_returns_legacy_if_only_option(self, legacy_annotated_file):
        """Test returns legacy dataset if it's the only option."""
        # legacy_annotated_file is at: tmp_path/data/annotated/syllables_annotated.json
        # discover_datasets expects the data/annotated directory for legacy detection
        legacy_dir = legacy_annotated_file.parent  # data/annotated/
        datasets = discover_datasets(search_paths=[legacy_dir])
        default = get_default_dataset(datasets)

        assert default is not None
        assert default.is_legacy is True

    def test_returns_none_for_empty_list(self):
        """Test returns None when no datasets provided."""
        default = get_default_dataset([])
        assert default is None

    def test_prefers_non_legacy_over_legacy(self, tmp_path, sample_syllables_data):
        """Test prefers non-legacy even if legacy exists."""
        # Create both
        output_dir = tmp_path / "_working" / "output"
        nltk_run = output_dir / "20260115_120000_nltk" / "data"
        nltk_run.mkdir(parents=True)
        with open(nltk_run / "nltk_syllables_annotated.json", "w", encoding="utf-8") as f:
            json.dump(sample_syllables_data, f)

        legacy_dir = tmp_path / "data" / "annotated"
        legacy_dir.mkdir(parents=True)
        with open(legacy_dir / "syllables_annotated.json", "w", encoding="utf-8") as f:
            json.dump(sample_syllables_data, f)

        datasets = discover_datasets(search_paths=[output_dir, legacy_dir])
        default = get_default_dataset(datasets)

        assert default is not None
        assert default.is_legacy is False

    def test_auto_discovers_when_none_provided(self, monkeypatch, tmp_path, sample_syllables_data):
        """Test auto-discovers datasets when None passed."""
        monkeypatch.chdir(tmp_path)

        # Create default structure
        output_dir = tmp_path / "_working" / "output"
        nltk_run = output_dir / "20260115_120000_nltk" / "data"
        nltk_run.mkdir(parents=True)
        with open(nltk_run / "nltk_syllables_annotated.json", "w", encoding="utf-8") as f:
            json.dump(sample_syllables_data, f)

        # Pass None to trigger auto-discovery
        default = get_default_dataset(None)

        assert default is not None
        assert default.extractor_type == "nltk"

    def test_returns_none_when_auto_discover_finds_nothing(self, monkeypatch, tmp_path):
        """Test returns None when auto-discovery finds nothing."""
        monkeypatch.chdir(tmp_path)

        # No datasets created
        default = get_default_dataset(None)

        assert default is None
