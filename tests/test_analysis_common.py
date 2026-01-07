"""Unit tests for analysis common modules.

This test module covers the shared utility modules in:
build_tools/syllable_feature_annotator/analysis/common/

Test Coverage
-------------
- paths.py: Path management and default path configuration
- data_io.py: Data loading and saving operations
- output.py: Output file and directory management
"""

import json
import tempfile
from pathlib import Path

import pytest

from build_tools.syllable_analysis.common.data_io import (
    load_annotated_syllables,
    load_frequency_data,
    save_json_output,
)
from build_tools.syllable_analysis.common.output import (
    ensure_output_dir,
    generate_output_pair,
    generate_timestamped_path,
)

# Import modules under test
from build_tools.syllable_analysis.common.paths import AnalysisPathConfig, default_paths

# =============================================================================
# Test Suite: paths.py - Path Management
# =============================================================================


class TestAnalysisPathConfig:
    """Test suite for AnalysisPathConfig class."""

    def test_init_with_default_root(self):
        """Test initialization with auto-detected root."""
        config = AnalysisPathConfig()

        # Should auto-detect root
        assert config.root is not None
        assert isinstance(config.root, Path)
        assert config.root.is_absolute()

        # Root should be the project root (contains pyproject.toml)
        assert (config.root / "pyproject.toml").exists()
        assert config.root.name == "pipeworks_name_generation"

    def test_init_with_custom_root(self):
        """Test initialization with explicit custom root."""
        custom_root = Path("/custom/project/root")
        config = AnalysisPathConfig(root=custom_root)

        assert config.root == custom_root

    def test_detect_project_root(self):
        """Test project root detection from file location."""
        root = AnalysisPathConfig._detect_project_root()

        # Should return absolute path
        assert root.is_absolute()

        # Should point to project root
        assert root.name == "pipeworks_name_generation"
        assert (root / "pyproject.toml").exists()

        # Verify it contains expected directories
        assert (root / "build_tools").exists()
        assert (root / "data").exists()
        assert (root / "tests").exists()

    def test_annotated_syllables_path(self):
        """Test annotated syllables path property."""
        config = AnalysisPathConfig()
        path = config.annotated_syllables

        # Should return correct path structure
        assert isinstance(path, Path)
        assert path.name == "syllables_annotated.json"
        assert path.parent.name == "annotated"
        assert path.parent.parent.name == "data"

        # Should be under project root
        assert str(path).startswith(str(config.root))

    def test_syllables_frequencies_path(self):
        """Test syllables frequencies path property."""
        config = AnalysisPathConfig()
        path = config.syllables_frequencies

        # Should return correct path structure
        assert isinstance(path, Path)
        assert path.name == "syllables_frequencies.json"
        assert path.parent.name == "normalized"
        assert path.parent.parent.name == "data"

        # Should be under project root
        assert str(path).startswith(str(config.root))

    def test_analysis_output_dir_tsne(self):
        """Test analysis output directory for t-SNE tool."""
        config = AnalysisPathConfig()
        output_dir = config.analysis_output_dir("tsne")

        # Should return correct path structure
        assert isinstance(output_dir, Path)
        assert output_dir.name == "tsne"
        assert output_dir.parent.name == "analysis"
        assert output_dir.parent.parent.name == "_working"

        # Should be under project root
        assert str(output_dir).startswith(str(config.root))

    def test_analysis_output_dir_feature_signatures(self):
        """Test analysis output directory for feature signatures tool."""
        config = AnalysisPathConfig()
        output_dir = config.analysis_output_dir("feature_signatures")

        # Should return correct path structure
        assert isinstance(output_dir, Path)
        assert output_dir.name == "feature_signatures"
        assert output_dir.parent.name == "analysis"

        # Should be under project root
        assert str(output_dir).startswith(str(config.root))

    def test_analysis_output_dir_random_sampler(self):
        """Test analysis output directory for random sampler tool."""
        config = AnalysisPathConfig()
        output_dir = config.analysis_output_dir("random_sampler")

        # Should return correct path structure
        assert isinstance(output_dir, Path)
        assert output_dir.name == "random_sampler"

    def test_custom_root_affects_all_paths(self):
        """Test that custom root affects all path properties."""
        custom_root = Path("/custom/root")
        config = AnalysisPathConfig(root=custom_root)

        # All paths should be under custom root
        assert str(config.annotated_syllables).startswith(str(custom_root))
        assert str(config.syllables_frequencies).startswith(str(custom_root))
        assert str(config.analysis_output_dir("tsne")).startswith(str(custom_root))

    def test_paths_are_consistent(self):
        """Test that multiple calls return consistent paths."""
        config = AnalysisPathConfig()

        # Multiple calls should return same paths
        assert config.annotated_syllables == config.annotated_syllables
        assert config.syllables_frequencies == config.syllables_frequencies
        assert config.analysis_output_dir("tsne") == config.analysis_output_dir("tsne")

    def test_analysis_output_dir_different_tools(self):
        """Test that different tool names produce different output directories."""
        config = AnalysisPathConfig()

        tsne_dir = config.analysis_output_dir("tsne")
        sigs_dir = config.analysis_output_dir("feature_signatures")
        sampler_dir = config.analysis_output_dir("random_sampler")

        # All should be different
        assert tsne_dir != sigs_dir
        assert tsne_dir != sampler_dir
        assert sigs_dir != sampler_dir

        # But all should share the same parent
        assert tsne_dir.parent == sigs_dir.parent == sampler_dir.parent


class TestDefaultPaths:
    """Test suite for module-level default_paths singleton."""

    def test_default_paths_exists(self):
        """Test that default_paths singleton is created."""
        assert default_paths is not None
        assert isinstance(default_paths, AnalysisPathConfig)

    def test_default_paths_has_valid_root(self):
        """Test that default_paths has valid project root."""
        assert default_paths.root is not None
        assert default_paths.root.is_absolute()
        assert (default_paths.root / "pyproject.toml").exists()

    def test_default_paths_is_singleton(self):
        """Test that default_paths behaves as singleton across imports."""
        # Import default_paths again
        from build_tools.syllable_analysis.common.paths import default_paths as default_paths_2

        # Should be the same instance
        assert default_paths is default_paths_2
        assert default_paths.root == default_paths_2.root

    def test_default_paths_provides_all_properties(self):
        """Test that default_paths provides all expected path properties."""
        # Should have all properties accessible
        assert hasattr(default_paths, "annotated_syllables")
        assert hasattr(default_paths, "syllables_frequencies")
        assert hasattr(default_paths, "analysis_output_dir")

        # All should return Path objects
        assert isinstance(default_paths.annotated_syllables, Path)
        assert isinstance(default_paths.syllables_frequencies, Path)
        assert isinstance(default_paths.analysis_output_dir("test"), Path)

    def test_default_paths_can_be_used_directly(self):
        """Test that default_paths can be used as intended in real code."""
        # This simulates how it would be used in analysis tools
        input_path = default_paths.annotated_syllables
        output_dir = default_paths.analysis_output_dir("tsne")

        assert input_path.name == "syllables_annotated.json"
        assert output_dir.name == "tsne"


# =============================================================================
# Pytest Configuration
# =============================================================================


@pytest.fixture
def temp_root():
    """Provide a temporary directory for testing custom roots."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def analysis_path_config_with_temp_root(temp_root):
    """Provide AnalysisPathConfig with temporary root for testing."""
    return AnalysisPathConfig(root=temp_root)


class TestAnalysisPathConfigWithTempRoot:
    """Test AnalysisPathConfig with temporary root directory."""

    def test_custom_root_in_temp_directory(self, analysis_path_config_with_temp_root, temp_root):
        """Test that custom root works with temporary directory."""
        config = analysis_path_config_with_temp_root

        assert config.root == temp_root
        assert str(config.annotated_syllables).startswith(str(temp_root))

    def test_paths_under_temp_root(self, analysis_path_config_with_temp_root, temp_root):
        """Test that all paths are under temporary root."""
        config = analysis_path_config_with_temp_root

        # All paths should be under temp root
        paths_to_check = [
            config.annotated_syllables,
            config.syllables_frequencies,
            config.analysis_output_dir("tsne"),
            config.analysis_output_dir("test_tool"),
        ]

        for path in paths_to_check:
            assert str(path).startswith(str(temp_root))
            # Verify path structure even if directories don't exist
            assert path.is_relative_to(temp_root)


# =============================================================================
# Test Suite: data_io.py - Data Loading and Saving
# =============================================================================


class TestLoadAnnotatedSyllables:
    """Test suite for load_annotated_syllables() function."""

    @pytest.fixture
    def valid_syllables_data(self):
        """Provide valid syllables data for testing."""
        return [
            {
                "syllable": "ka",
                "frequency": 187,
                "features": {
                    "contains_liquid": False,
                    "contains_plosive": True,
                    "starts_with_vowel": False,
                },
            },
            {
                "syllable": "ra",
                "frequency": 162,
                "features": {
                    "contains_liquid": True,
                    "contains_plosive": False,
                    "starts_with_vowel": False,
                },
            },
        ]

    @pytest.fixture
    def valid_syllables_file(self, tmp_path, valid_syllables_data):
        """Create a temporary file with valid syllables data."""
        file_path = tmp_path / "syllables_annotated.json"
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(valid_syllables_data, f)
        return file_path

    def test_load_valid_file(self, valid_syllables_file, valid_syllables_data):
        """Test loading a valid syllables file."""
        records = load_annotated_syllables(valid_syllables_file)

        assert isinstance(records, list)
        assert len(records) == len(valid_syllables_data)
        assert records == valid_syllables_data

    def test_load_with_validation_enabled(self, valid_syllables_file):
        """Test loading with validation explicitly enabled."""
        records = load_annotated_syllables(valid_syllables_file, validate=True)

        assert isinstance(records, list)
        assert len(records) > 0
        # Check first record has required keys
        assert "syllable" in records[0]
        assert "frequency" in records[0]
        assert "features" in records[0]

    def test_load_with_validation_disabled(self, valid_syllables_file):
        """Test loading with validation disabled."""
        records = load_annotated_syllables(valid_syllables_file, validate=False)

        # Should still load successfully
        assert isinstance(records, list)
        assert len(records) > 0

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading a file that doesn't exist."""
        nonexistent = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError) as exc_info:
            load_annotated_syllables(nonexistent)

        assert "Input file not found" in str(exc_info.value)
        assert str(nonexistent) in str(exc_info.value)

    def test_load_invalid_json(self, tmp_path):
        """Test loading a file with invalid JSON."""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{ this is not valid JSON }", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            load_annotated_syllables(invalid_json)

    def test_load_wrong_type_not_list(self, tmp_path):
        """Test validation fails when data is not a list."""
        wrong_type = tmp_path / "wrong_type.json"
        with wrong_type.open("w", encoding="utf-8") as f:
            json.dump({"not": "a list"}, f)

        with pytest.raises(ValueError) as exc_info:
            load_annotated_syllables(wrong_type, validate=True)

        assert "Expected list of records" in str(exc_info.value)

    def test_load_empty_list(self, tmp_path):
        """Test validation fails when list is empty."""
        empty_list = tmp_path / "empty.json"
        with empty_list.open("w", encoding="utf-8") as f:
            json.dump([], f)

        with pytest.raises(ValueError) as exc_info:
            load_annotated_syllables(empty_list, validate=True)

        assert "contains no records" in str(exc_info.value)

    def test_load_missing_required_keys(self, tmp_path):
        """Test validation fails when records are missing required keys."""
        missing_keys = tmp_path / "missing_keys.json"
        with missing_keys.open("w", encoding="utf-8") as f:
            json.dump([{"syllable": "ka"}], f)  # Missing 'frequency' and 'features'

        with pytest.raises(ValueError) as exc_info:
            load_annotated_syllables(missing_keys, validate=True)

        assert "missing required keys" in str(exc_info.value)

    def test_load_with_unicode_content(self, tmp_path):
        """Test loading file with Unicode characters."""
        unicode_data = [
            {
                "syllable": "café",
                "frequency": 10,
                "features": {"starts_with_vowel": False},
            }
        ]
        unicode_file = tmp_path / "unicode.json"
        with unicode_file.open("w", encoding="utf-8") as f:
            json.dump(unicode_data, f, ensure_ascii=False)

        records = load_annotated_syllables(unicode_file)

        assert records[0]["syllable"] == "café"

    def test_load_large_file(self, tmp_path):
        """Test loading a file with many records."""
        # Create 1000 syllable records
        large_data = [
            {
                "syllable": f"syl{i}",
                "frequency": i,
                "features": {"starts_with_vowel": i % 2 == 0},
            }
            for i in range(1000)
        ]
        large_file = tmp_path / "large.json"
        with large_file.open("w", encoding="utf-8") as f:
            json.dump(large_data, f)

        records = load_annotated_syllables(large_file)

        assert len(records) == 1000
        assert records[0]["syllable"] == "syl0"
        assert records[-1]["syllable"] == "syl999"


class TestLoadFrequencyData:
    """Test suite for load_frequency_data() function."""

    @pytest.fixture
    def valid_frequency_data(self):
        """Provide valid frequency data for testing."""
        return {"ka": 187, "ra": 162, "mi": 145, "ta": 98}

    @pytest.fixture
    def valid_frequency_file(self, tmp_path, valid_frequency_data):
        """Create a temporary file with valid frequency data."""
        file_path = tmp_path / "syllables_frequencies.json"
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(valid_frequency_data, f)
        return file_path

    def test_load_valid_frequency_file(self, valid_frequency_file, valid_frequency_data):
        """Test loading a valid frequency file."""
        frequencies = load_frequency_data(valid_frequency_file)

        assert isinstance(frequencies, dict)
        assert frequencies == valid_frequency_data
        assert frequencies["ka"] == 187

    def test_load_nonexistent_frequency_file(self, tmp_path):
        """Test loading a frequency file that doesn't exist."""
        nonexistent = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError) as exc_info:
            load_frequency_data(nonexistent)

        assert "Frequency file not found" in str(exc_info.value)

    def test_load_invalid_json_frequency_file(self, tmp_path):
        """Test loading a frequency file with invalid JSON."""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{ not valid }", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            load_frequency_data(invalid_json)

    def test_load_wrong_type_not_dict(self, tmp_path):
        """Test loading fails when data is not a dictionary."""
        wrong_type = tmp_path / "wrong_type.json"
        with wrong_type.open("w", encoding="utf-8") as f:
            json.dump(["not", "a", "dict"], f)

        with pytest.raises(ValueError) as exc_info:
            load_frequency_data(wrong_type)

        assert "Expected dictionary" in str(exc_info.value)

    def test_load_empty_frequency_dict(self, tmp_path):
        """Test loading an empty frequency dictionary."""
        empty_dict = tmp_path / "empty.json"
        with empty_dict.open("w", encoding="utf-8") as f:
            json.dump({}, f)

        frequencies = load_frequency_data(empty_dict)

        # Empty dict is technically valid
        assert isinstance(frequencies, dict)
        assert len(frequencies) == 0

    def test_load_frequency_with_unicode_keys(self, tmp_path):
        """Test loading frequencies with Unicode syllable names."""
        unicode_data = {"café": 10, "naïve": 5, "résumé": 3}
        unicode_file = tmp_path / "unicode_freq.json"
        with unicode_file.open("w", encoding="utf-8") as f:
            json.dump(unicode_data, f, ensure_ascii=False)

        frequencies = load_frequency_data(unicode_file)

        assert frequencies["café"] == 10
        assert frequencies["naïve"] == 5


class TestSaveJsonOutput:
    """Test suite for save_json_output() function."""

    def test_save_simple_dict(self, tmp_path):
        """Test saving a simple dictionary."""
        data = {"key": "value", "number": 42}
        output_path = tmp_path / "output.json"

        save_json_output(data, output_path)

        # Verify file was created
        assert output_path.exists()

        # Verify content is correct
        with output_path.open(encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == data

    def test_save_list_of_dicts(self, tmp_path):
        """Test saving a list of dictionaries."""
        data = [{"id": 1, "name": "first"}, {"id": 2, "name": "second"}]
        output_path = tmp_path / "list.json"

        save_json_output(data, output_path)

        with output_path.open(encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == data

    def test_save_with_default_indent(self, tmp_path):
        """Test saving with default indent (2 spaces)."""
        data = {"key": "value"}
        output_path = tmp_path / "indented.json"

        save_json_output(data, output_path)

        # Check that file is indented
        content = output_path.read_text(encoding="utf-8")
        assert "\n" in content  # Should have line breaks
        assert "  " in content  # Should have indentation

    def test_save_with_no_indent(self, tmp_path):
        """Test saving with no indentation (compact)."""
        data = {"key": "value", "nested": {"inner": "data"}}
        output_path = tmp_path / "compact.json"

        save_json_output(data, output_path, indent=None)

        content = output_path.read_text(encoding="utf-8")
        # Compact format should have no extra whitespace
        assert '{"key":"value"' in content or '{"key": "value"' in content

    def test_save_with_custom_indent(self, tmp_path):
        """Test saving with custom indentation."""
        data = {"key": "value"}
        output_path = tmp_path / "custom_indent.json"

        save_json_output(data, output_path, indent=4)

        content = output_path.read_text(encoding="utf-8")
        # Should have 4-space indentation
        assert "    " in content

    def test_save_with_unicode_content(self, tmp_path):
        """Test saving with Unicode content (default ensure_ascii=False)."""
        data = {"syllable": "café", "description": "naïve résumé"}
        output_path = tmp_path / "unicode.json"

        save_json_output(data, output_path)

        content = output_path.read_text(encoding="utf-8")
        # Unicode characters should be preserved
        assert "café" in content
        assert "naïve" in content
        assert "\\u" not in content  # Should not be escaped

    def test_save_with_ensure_ascii_true(self, tmp_path):
        """Test saving with ensure_ascii=True (escape Unicode)."""
        data = {"syllable": "café"}
        output_path = tmp_path / "ascii.json"

        save_json_output(data, output_path, ensure_ascii=True)

        content = output_path.read_text(encoding="utf-8")
        # Unicode should be escaped
        assert "\\u" in content or "cafe" in content
        assert "é" not in content

    def test_save_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created automatically."""
        nested_path = tmp_path / "level1" / "level2" / "output.json"
        data = {"test": "value"}

        # Parent directories don't exist yet
        assert not nested_path.parent.exists()

        save_json_output(data, nested_path)

        # Should have created parent directories
        assert nested_path.exists()
        assert nested_path.parent.exists()

    def test_save_overwrites_existing_file(self, tmp_path):
        """Test that existing files are overwritten."""
        output_path = tmp_path / "overwrite.json"

        # Write initial data
        initial_data = {"version": 1}
        save_json_output(initial_data, output_path)

        # Overwrite with new data
        new_data = {"version": 2}
        save_json_output(new_data, output_path)

        # Should have new data
        with output_path.open(encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == new_data
        assert loaded["version"] == 2

    def test_save_complex_nested_structure(self, tmp_path):
        """Test saving a complex nested data structure."""
        data = {
            "metadata": {"version": "1.0", "created": "2024-01-01"},
            "results": [
                {"id": 1, "values": [1, 2, 3], "nested": {"deep": {"value": True}}},
                {"id": 2, "values": [4, 5, 6], "nested": {"deep": {"value": False}}},
            ],
        }
        output_path = tmp_path / "complex.json"

        save_json_output(data, output_path)

        with output_path.open(encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == data
        assert loaded["results"][0]["nested"]["deep"]["value"] is True


# =============================================================================
# Test Suite: output.py - Output File and Directory Management
# =============================================================================


class TestEnsureOutputDir:
    """Test suite for ensure_output_dir() function."""

    def test_create_new_directory(self, tmp_path):
        """Test creating a new directory."""
        new_dir = tmp_path / "new_directory"

        # Directory shouldn't exist yet
        assert not new_dir.exists()

        # Create it
        result = ensure_output_dir(new_dir)

        # Should now exist
        assert new_dir.exists()
        assert new_dir.is_dir()
        # Should return the same path
        assert result == new_dir

    def test_create_nested_directories(self, tmp_path):
        """Test creating nested directories (like mkdir -p)."""
        nested_dir = tmp_path / "level1" / "level2" / "level3"

        # None of the directories exist yet
        assert not nested_dir.exists()

        # Create all at once
        result = ensure_output_dir(nested_dir)

        # All should now exist
        assert nested_dir.exists()
        assert (tmp_path / "level1").exists()
        assert (tmp_path / "level1" / "level2").exists()
        assert result == nested_dir

    def test_idempotent_operation(self, tmp_path):
        """Test that calling multiple times is safe (idempotent)."""
        test_dir = tmp_path / "test_dir"

        # Create first time
        result1 = ensure_output_dir(test_dir)
        assert test_dir.exists()

        # Create again - should not raise error
        result2 = ensure_output_dir(test_dir)
        assert test_dir.exists()

        # Should return same path both times
        assert result1 == result2

    def test_existing_directory(self, tmp_path):
        """Test with a directory that already exists."""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        # Should not raise error
        result = ensure_output_dir(existing_dir)

        assert existing_dir.exists()
        assert result == existing_dir

    def test_returns_path_for_chaining(self, tmp_path):
        """Test that returned path can be used for chaining."""
        base_dir = tmp_path / "base"

        # Can chain with / operator
        file_path = ensure_output_dir(base_dir) / "output.json"

        assert base_dir.exists()
        assert file_path.parent == base_dir
        assert file_path.name == "output.json"


class TestGenerateTimestampedPath:
    """Test suite for generate_timestamped_path() function."""

    def test_generate_basic_path(self, tmp_path):
        """Test generating a basic timestamped path."""
        path = generate_timestamped_path(output_dir=tmp_path, suffix="test_output", extension="txt")

        assert isinstance(path, Path)
        assert path.parent == tmp_path
        assert ".test_output.txt" in path.name

    def test_timestamp_format(self, tmp_path):
        """Test that timestamp has correct format (YYYYMMDD_HHMMSS)."""
        path = generate_timestamped_path(tmp_path, "output", "txt")

        # Extract timestamp (first part before first dot)
        timestamp = path.stem.split(".")[0]

        # Should be 15 characters: YYYYMMDD_HHMMSS
        assert len(timestamp) == 15
        # Should have underscore in the middle
        assert "_" in timestamp
        # Should be all digits except underscore
        assert timestamp.replace("_", "").isdigit()

    def test_custom_extension(self, tmp_path):
        """Test with different file extensions."""
        extensions = ["txt", "json", "png", "html", "csv"]

        for ext in extensions:
            path = generate_timestamped_path(tmp_path, "output", ext)
            assert path.suffix == f".{ext}"

    def test_suffix_in_filename(self, tmp_path):
        """Test that suffix appears in filename."""
        suffixes = ["tsne_visualization", "metadata", "results", "feature_signatures"]

        for suffix in suffixes:
            path = generate_timestamped_path(tmp_path, suffix, "txt")
            assert suffix in path.name

    def test_explicit_timestamp(self, tmp_path):
        """Test using explicit timestamp instead of auto-generated."""
        explicit_timestamp = "20260107_120000"

        path = generate_timestamped_path(tmp_path, "output", "txt", timestamp=explicit_timestamp)

        assert explicit_timestamp in path.name
        assert path.name.startswith(explicit_timestamp)

    def test_filename_structure(self, tmp_path):
        """Test that filename has correct structure."""
        path = generate_timestamped_path(tmp_path, "test_suffix", "ext", "20260107_120000")

        # Should be: {timestamp}.{suffix}.{extension}
        assert path.name == "20260107_120000.test_suffix.ext"

    def test_different_output_dirs(self, tmp_path):
        """Test with different output directories."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"

        path1 = generate_timestamped_path(dir1, "output", "txt")
        path2 = generate_timestamped_path(dir2, "output", "txt")

        assert path1.parent == dir1
        assert path2.parent == dir2
        assert path1.parent != path2.parent

    def test_timestamp_uniqueness(self, tmp_path):
        """Test that consecutive calls generate different timestamps."""
        import time

        path1 = generate_timestamped_path(tmp_path, "output", "txt")
        time.sleep(1.1)  # Wait just over 1 second
        path2 = generate_timestamped_path(tmp_path, "output", "txt")

        # Filenames should be different (different timestamps)
        assert path1.name != path2.name


class TestGenerateOutputPair:
    """Test suite for generate_output_pair() function."""

    def test_generate_basic_pair(self, tmp_path):
        """Test generating a basic pair of output paths."""
        primary, metadata = generate_output_pair(
            output_dir=tmp_path,
            primary_suffix="visualization",
            metadata_suffix="metadata",
        )

        assert isinstance(primary, Path)
        assert isinstance(metadata, Path)
        assert primary.parent == tmp_path
        assert metadata.parent == tmp_path

    def test_matching_timestamps(self, tmp_path):
        """Test that both files get the same timestamp."""
        primary, metadata = generate_output_pair(tmp_path, "primary", "metadata")

        # Extract timestamps (first part before first dot)
        primary_timestamp = primary.stem.split(".")[0]
        metadata_timestamp = metadata.stem.split(".")[0]

        # Should be identical
        assert primary_timestamp == metadata_timestamp

    def test_different_suffixes(self, tmp_path):
        """Test that suffixes are different and correct."""
        primary, metadata = generate_output_pair(tmp_path, "tsne_visualization", "tsne_metadata")

        assert "tsne_visualization" in primary.name
        assert "tsne_metadata" in metadata.name
        assert "tsne_visualization" not in metadata.name
        assert "tsne_metadata" not in primary.name

    def test_custom_extensions(self, tmp_path):
        """Test with custom file extensions."""
        primary, metadata = generate_output_pair(
            tmp_path,
            "viz",
            "meta",
            primary_ext="png",
            metadata_ext="json",
        )

        assert primary.suffix == ".png"
        assert metadata.suffix == ".json"

    def test_default_extensions(self, tmp_path):
        """Test that default extension is 'txt' for both files."""
        primary, metadata = generate_output_pair(tmp_path, "primary", "metadata")

        assert primary.suffix == ".txt"
        assert metadata.suffix == ".txt"

    def test_visualization_metadata_pair(self, tmp_path):
        """Test typical use case: visualization PNG + metadata TXT."""
        viz, meta = generate_output_pair(
            tmp_path,
            "tsne_visualization",
            "tsne_metadata",
            primary_ext="png",
            metadata_ext="txt",
        )

        # Check structure
        assert viz.suffix == ".png"
        assert meta.suffix == ".txt"
        assert "tsne_visualization" in viz.name
        assert "tsne_metadata" in meta.name

        # Check timestamps match
        assert viz.stem.split(".")[0] == meta.stem.split(".")[0]

    def test_json_json_pair(self, tmp_path):
        """Test pair with both files as JSON."""
        data, meta = generate_output_pair(
            tmp_path,
            "results",
            "metadata",
            primary_ext="json",
            metadata_ext="json",
        )

        assert data.suffix == ".json"
        assert meta.suffix == ".json"

    def test_sorting_behavior(self, tmp_path):
        """Test that paired files sort together in listings."""
        # Generate two pairs with slight time difference
        import time

        pair1_primary, pair1_meta = generate_output_pair(tmp_path, "primary", "metadata")
        time.sleep(1.1)
        pair2_primary, pair2_meta = generate_output_pair(tmp_path, "primary", "metadata")

        # Create all files
        for path in [pair1_primary, pair1_meta, pair2_primary, pair2_meta]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

        # Get sorted listing
        all_files = sorted(tmp_path.glob("*"))

        # Pairs should be adjacent in sorted order
        assert all_files.index(pair1_primary) + 1 == all_files.index(pair1_meta) or all_files.index(
            pair1_meta
        ) + 1 == all_files.index(pair1_primary)

    def test_filename_structure_both_files(self, tmp_path):
        """Test that both files have correct filename structure."""
        primary, metadata = generate_output_pair(
            tmp_path,
            "primary_suffix",
            "metadata_suffix",
            primary_ext="ext1",
            metadata_ext="ext2",
        )

        # Both should follow: {timestamp}.{suffix}.{extension}
        primary_parts = primary.name.split(".")
        metadata_parts = metadata.name.split(".")

        # Should have 3 parts: timestamp, suffix, extension
        assert len(primary_parts) == 3
        assert len(metadata_parts) == 3

        # Timestamps should match
        assert primary_parts[0] == metadata_parts[0]
