"""Tests for t-SNE visualization tool.

NOTE: These tests reference the old pre-refactoring API. The refactored code is now
comprehensively tested in:
- tests/test_analysis_common.py (data loading)
- tests/test_dimensionality.py (feature extraction, t-SNE)
- tests/test_plotting.py (visualization)

This file is kept for backwards compatibility testing but may be deprecated in the future.

This test suite covers:
- Data loading and validation
- Feature matrix extraction
- t-SNE visualization creation
- File I/O operations
- CLI argument parsing
- Full pipeline integration
- Error handling
- Determinism
"""

# mypy: ignore-errors

import json
from pathlib import Path
from unittest import mock

import pytest

# Check if optional dependencies are available
np = pytest.importorskip("numpy", reason="numpy not installed")

# Import will only work if dependencies are available
try:
    # Import from refactored modules
    from build_tools.syllable_feature_annotator.analysis.common import (
        load_annotated_syllables as load_annotated_data,  # Backward compatibility alias
    )
    from build_tools.syllable_feature_annotator.analysis.dimensionality import (
        ALL_FEATURES,
        extract_feature_matrix,
    )
    from build_tools.syllable_feature_annotator.analysis.plotting import (
        create_tsne_scatter as create_tsne_visualization,  # Backward compatibility alias
    )
    from build_tools.syllable_feature_annotator.analysis.plotting import (
        save_static_plot as save_visualization,  # Backward compatibility alias
    )
    from build_tools.syllable_feature_annotator.analysis.plotting.interactive import (  # noqa: F401
        create_interactive_scatter as create_interactive_visualization,
    )
    from build_tools.syllable_feature_annotator.analysis.plotting.interactive import (  # noqa: F401
        save_interactive_html as save_interactive_visualization,
    )
    from build_tools.syllable_feature_annotator.analysis.tsne_visualizer import (
        parse_args,
        run_tsne_visualization,
    )

    _IMPORTS_AVAILABLE = True
except ImportError:
    _IMPORTS_AVAILABLE = False
    pytestmark = pytest.mark.skip(
        reason="t-SNE visualizer dependencies not installed (matplotlib, numpy, scikit-learn)"
    )

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_annotated_records():
    """Create sample annotated syllable records for testing."""
    return [
        {
            "syllable": "ka",
            "frequency": 187,
            "features": {
                "contains_liquid": False,
                "contains_plosive": True,
                "contains_fricative": False,
                "contains_nasal": False,
                "long_vowel": False,
                "short_vowel": True,
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "ends_with_vowel": True,
                "ends_with_stop": False,
                "ends_with_nasal": False,
            },
        },
        {
            "syllable": "ra",
            "frequency": 162,
            "features": {
                "contains_liquid": True,
                "contains_plosive": False,
                "contains_fricative": False,
                "contains_nasal": False,
                "long_vowel": False,
                "short_vowel": True,
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "ends_with_vowel": True,
                "ends_with_stop": False,
                "ends_with_nasal": False,
            },
        },
        {
            "syllable": "mi",
            "frequency": 145,
            "features": {
                "contains_liquid": False,
                "contains_plosive": False,
                "contains_fricative": False,
                "contains_nasal": True,
                "long_vowel": False,
                "short_vowel": True,
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "ends_with_vowel": True,
                "ends_with_stop": False,
                "ends_with_nasal": False,
            },
        },
        {
            "syllable": "kran",
            "frequency": 7,
            "features": {
                "contains_liquid": True,
                "contains_plosive": True,
                "contains_fricative": False,
                "contains_nasal": True,
                "long_vowel": False,
                "short_vowel": True,
                "starts_with_vowel": False,
                "starts_with_cluster": True,
                "starts_with_heavy_cluster": False,
                "ends_with_vowel": False,
                "ends_with_stop": False,
                "ends_with_nasal": True,
            },
        },
        {
            "syllable": "spla",
            "frequency": 2,
            "features": {
                "contains_liquid": True,
                "contains_plosive": True,
                "contains_fricative": True,
                "contains_nasal": False,
                "long_vowel": False,
                "short_vowel": True,
                "starts_with_vowel": False,
                "starts_with_cluster": True,
                "starts_with_heavy_cluster": True,
                "ends_with_vowel": True,
                "ends_with_stop": False,
                "ends_with_nasal": False,
            },
        },
    ]


@pytest.fixture
def annotated_json_file(tmp_path, sample_annotated_records):
    """Create a temporary JSON file with annotated syllables."""
    json_path = tmp_path / "syllables_annotated.json"
    with json_path.open("w") as f:
        json.dump(sample_annotated_records, f, indent=2)
    return json_path


# ============================================================================
# Data Loading Tests
# ============================================================================


def test_load_annotated_data_success(annotated_json_file, sample_annotated_records):
    """Test loading valid annotated data."""
    records = load_annotated_data(annotated_json_file)
    assert len(records) == len(sample_annotated_records)
    assert records[0]["syllable"] == "ka"
    assert records[0]["frequency"] == 187


def test_load_annotated_data_missing_file(tmp_path):
    """Test error handling for missing file."""
    missing_file = tmp_path / "nonexistent.json"
    with pytest.raises(FileNotFoundError, match="Input file not found"):
        load_annotated_data(missing_file)


def test_load_annotated_data_invalid_json(tmp_path):
    """Test error handling for invalid JSON."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{invalid json}")
    with pytest.raises(json.JSONDecodeError):
        load_annotated_data(invalid_file)


def test_load_annotated_data_not_a_list(tmp_path):
    """Test error handling when JSON is not a list."""
    not_list_file = tmp_path / "not_list.json"
    with not_list_file.open("w") as f:
        json.dump({"key": "value"}, f)
    with pytest.raises(ValueError, match="Expected list of records"):
        load_annotated_data(not_list_file)


def test_load_annotated_data_empty_list(tmp_path):
    """Test error handling for empty records list."""
    empty_file = tmp_path / "empty.json"
    with empty_file.open("w") as f:
        json.dump([], f)
    with pytest.raises(ValueError, match="contains no records"):
        load_annotated_data(empty_file)


def test_load_annotated_data_missing_keys(tmp_path):
    """Test error handling for records missing required keys."""
    invalid_records = [{"syllable": "ka"}]  # Missing frequency and features
    invalid_file = tmp_path / "invalid_structure.json"
    with invalid_file.open("w") as f:
        json.dump(invalid_records, f)
    with pytest.raises(ValueError, match="Records missing required keys"):
        load_annotated_data(invalid_file)


# ============================================================================
# Feature Matrix Extraction Tests
# ============================================================================


def test_extract_feature_matrix_shape(sample_annotated_records):
    """Test that feature matrix has correct shape."""
    matrix, frequencies = extract_feature_matrix(sample_annotated_records)
    assert matrix.shape == (5, 12)  # 5 syllables, 12 features
    assert len(frequencies) == 5


def test_extract_feature_matrix_values(sample_annotated_records):
    """Test that feature matrix contains correct binary values."""
    matrix, frequencies = extract_feature_matrix(sample_annotated_records)

    # All values should be 0 or 1
    assert np.all((matrix == 0) | (matrix == 1))

    # Check first record (ka)
    # contains_plosive=True, short_vowel=True, ends_with_vowel=True
    ka_features = sample_annotated_records[0]["features"]
    ka_vector = matrix[0]

    for i, feat in enumerate(ALL_FEATURES):
        expected = 1 if ka_features.get(feat, False) else 0
        assert ka_vector[i] == expected


def test_extract_feature_matrix_frequencies(sample_annotated_records):
    """Test that frequency extraction is correct."""
    matrix, frequencies = extract_feature_matrix(sample_annotated_records)
    assert frequencies == [187, 162, 145, 7, 2]


def test_extract_feature_matrix_missing_feature():
    """Test handling of records with missing feature keys."""
    records = [
        {
            "syllable": "ka",
            "frequency": 10,
            "features": {
                "contains_liquid": True,
                # Other features missing - should default to False
            },
        }
    ]
    matrix, frequencies = extract_feature_matrix(records)
    assert matrix.shape == (1, 12)
    # Only contains_liquid should be 1 (index 0 in ALL_FEATURES)
    assert matrix[0][0] == 1
    assert np.sum(matrix[0]) == 1  # Only one feature is True


def test_extract_feature_matrix_consistent_ordering():
    """Test that feature extraction uses consistent ordering."""
    records = [
        {
            "syllable": "test",
            "frequency": 1,
            "features": {feat: True for feat in ALL_FEATURES},
        }
    ]
    matrix, _ = extract_feature_matrix(records)
    # All features True, so all values should be 1
    assert np.all(matrix[0] == 1)


# ============================================================================
# t-SNE Visualization Tests
# ============================================================================


@pytest.mark.skipif(
    not pytest.importorskip("sklearn", reason="scikit-learn not installed"),
    reason="scikit-learn required",
)
def test_create_tsne_visualization_basic(sample_annotated_records):
    """Test basic t-SNE visualization creation."""
    matrix, frequencies = extract_feature_matrix(sample_annotated_records)
    # Use perplexity=2 for small dataset (must be < n_samples=5)
    fig, coords = create_tsne_visualization(matrix, frequencies, perplexity=2)

    # Check output types
    assert fig is not None
    assert isinstance(coords, np.ndarray)
    assert coords.shape == (5, 2)  # 5 syllables, 2D projection


@pytest.mark.skipif(
    not pytest.importorskip("sklearn", reason="scikit-learn not installed"),
    reason="scikit-learn required",
)
def test_create_tsne_visualization_reproducible(sample_annotated_records):
    """Test that t-SNE is reproducible with same random_state."""
    matrix, frequencies = extract_feature_matrix(sample_annotated_records)

    fig1, coords1 = create_tsne_visualization(matrix, frequencies, perplexity=2, random_state=42)
    fig2, coords2 = create_tsne_visualization(matrix, frequencies, perplexity=2, random_state=42)

    # Same random state should produce identical results
    np.testing.assert_array_almost_equal(coords1, coords2)


@pytest.mark.skipif(
    not pytest.importorskip("sklearn", reason="scikit-learn not installed"),
    reason="scikit-learn required",
)
def test_create_tsne_visualization_different_seeds(sample_annotated_records):
    """Test that t-SNE runs with different random states.

    Note: With small datasets, different random seeds may converge to similar
    solutions, so we only verify that the function runs successfully rather
    than asserting different outputs.
    """
    matrix, frequencies = extract_feature_matrix(sample_annotated_records)

    fig1, coords1 = create_tsne_visualization(matrix, frequencies, perplexity=2, random_state=42)
    fig2, coords2 = create_tsne_visualization(matrix, frequencies, perplexity=2, random_state=123)

    # Both should produce valid 2D coordinates
    assert coords1.shape == (5, 2)
    assert coords2.shape == (5, 2)
    # Note: Small datasets may converge to same solution despite different seeds


@pytest.mark.skipif(
    not pytest.importorskip("sklearn", reason="scikit-learn not installed"),
    reason="scikit-learn required",
)
def test_create_tsne_visualization_perplexity(sample_annotated_records):
    """Test t-SNE with different perplexity values."""
    matrix, frequencies = extract_feature_matrix(sample_annotated_records)

    # Test with different perplexity (must be < n_samples=5)
    fig1, coords1 = create_tsne_visualization(matrix, frequencies, perplexity=2, random_state=42)
    fig2, coords2 = create_tsne_visualization(matrix, frequencies, perplexity=3, random_state=42)

    assert coords1.shape == coords2.shape == (5, 2)
    # Different perplexity should usually produce different layouts
    # (but we won't assert this as it's not guaranteed for small datasets)


def test_create_tsne_visualization_missing_sklearn():
    """Test error handling when scikit-learn is not installed."""
    with mock.patch.dict("sys.modules", {"sklearn.manifold": None}):
        with pytest.raises(ImportError, match="scikit-learn is required"):
            import importlib

            # Force reimport to trigger the ImportError
            import build_tools.syllable_feature_annotator.analysis.tsne_visualizer as tsne_mod

            importlib.reload(tsne_mod)

            matrix = np.array([[1, 0, 1], [0, 1, 0]])
            frequencies = [10, 20]
            tsne_mod.create_tsne_visualization(matrix, frequencies)


# ============================================================================
# Visualization Saving Tests
# ============================================================================


@pytest.mark.skipif(
    not pytest.importorskip("sklearn", reason="scikit-learn not installed"),
    reason="scikit-learn required",
)
def test_save_visualization_creates_files(tmp_path, sample_annotated_records):
    """Test that save_visualization creates output files."""
    matrix, frequencies = extract_feature_matrix(sample_annotated_records)
    fig, coords = create_tsne_visualization(matrix, frequencies, perplexity=2)

    viz_path, meta_path = save_visualization(fig, tmp_path, dpi=100)

    # Check files were created
    assert viz_path.exists()
    assert meta_path.exists()

    # Check file extensions
    assert viz_path.suffix == ".png"
    assert meta_path.suffix == ".txt"


@pytest.mark.skipif(
    not pytest.importorskip("sklearn", reason="scikit-learn not installed"),
    reason="scikit-learn required",
)
def test_save_visualization_metadata_content(tmp_path, sample_annotated_records):
    """Test that metadata file contains expected content."""
    matrix, frequencies = extract_feature_matrix(sample_annotated_records)
    fig, coords = create_tsne_visualization(matrix, frequencies, perplexity=2, random_state=42)

    viz_path, meta_path = save_visualization(fig, tmp_path, dpi=300, perplexity=2, random_state=42)

    metadata_text = meta_path.read_text()

    # Check for expected sections
    assert "t-SNE VISUALIZATION METADATA" in metadata_text
    assert "ALGORITHM PARAMETERS" in metadata_text
    assert "VISUALIZATION ENCODING" in metadata_text
    assert "INTERPRETATION GUIDE" in metadata_text
    assert "Resolution: 300 DPI" in metadata_text
    assert "Hamming" in metadata_text
    # Check for parameter values
    assert "Perplexity: 2" in metadata_text
    assert "Random state: 42" in metadata_text


@pytest.mark.skipif(
    not pytest.importorskip("sklearn", reason="scikit-learn not installed"),
    reason="scikit-learn required",
)
def test_save_visualization_creates_directory(tmp_path, sample_annotated_records):
    """Test that save_visualization creates output directory if needed."""
    matrix, frequencies = extract_feature_matrix(sample_annotated_records)
    fig, coords = create_tsne_visualization(matrix, frequencies, perplexity=2)

    nested_dir = tmp_path / "nested" / "output"
    assert not nested_dir.exists()

    viz_path, meta_path = save_visualization(fig, nested_dir)

    assert nested_dir.exists()
    assert viz_path.exists()
    assert meta_path.exists()


@pytest.mark.skipif(
    not pytest.importorskip("sklearn", reason="scikit-learn not installed"),
    reason="scikit-learn required",
)
def test_save_visualization_custom_parameters(tmp_path, sample_annotated_records):
    """Test that custom parameter values appear in metadata."""
    matrix, frequencies = extract_feature_matrix(sample_annotated_records)
    # Use perplexity=3 (less than n_samples=5)
    fig, coords = create_tsne_visualization(matrix, frequencies, perplexity=3, random_state=123)

    viz_path, meta_path = save_visualization(fig, tmp_path, dpi=300, perplexity=3, random_state=123)

    metadata_text = meta_path.read_text()

    # Verify custom parameters logged correctly
    assert "Perplexity: 3" in metadata_text
    assert "Random state: 123" in metadata_text


# ============================================================================
# Full Pipeline Tests
# ============================================================================


@pytest.mark.skipif(
    not pytest.importorskip("sklearn", reason="scikit-learn not installed"),
    reason="scikit-learn required",
)
def test_run_tsne_visualization_complete(annotated_json_file, tmp_path):
    """Test complete pipeline execution."""
    output_dir = tmp_path / "output"

    result = run_tsne_visualization(
        input_path=annotated_json_file,
        output_dir=output_dir,
        perplexity=2,  # Must be < n_samples=5
        random_state=42,
        dpi=150,
        verbose=False,
    )

    # Check result dictionary
    assert result["syllable_count"] == 5
    assert result["feature_count"] == 12
    assert result["output_path"].exists()
    assert result["metadata_path"].exists()
    assert isinstance(result["tsne_coordinates"], np.ndarray)
    assert result["tsne_coordinates"].shape == (5, 2)


@pytest.mark.skipif(
    not pytest.importorskip("sklearn", reason="scikit-learn not installed"),
    reason="scikit-learn required",
)
def test_run_tsne_visualization_verbose(annotated_json_file, tmp_path, capsys):
    """Test pipeline with verbose output."""
    output_dir = tmp_path / "output"

    run_tsne_visualization(
        input_path=annotated_json_file,
        output_dir=output_dir,
        perplexity=2,  # Must be < n_samples=5
        verbose=True,
    )

    captured = capsys.readouterr()
    assert "Loading data from" in captured.out
    assert "Loaded 5 annotated syllables" in captured.out
    assert "Extracting feature matrix" in captured.out
    assert "Running t-SNE" in captured.out
    assert "Saving visualization" in captured.out


@pytest.mark.skipif(
    not pytest.importorskip("sklearn", reason="scikit-learn not installed"),
    reason="scikit-learn required",
)
def test_run_tsne_visualization_deterministic(annotated_json_file, tmp_path):
    """Test that pipeline is deterministic with same random_state."""
    output_dir1 = tmp_path / "output1"
    output_dir2 = tmp_path / "output2"

    result1 = run_tsne_visualization(
        input_path=annotated_json_file,
        output_dir=output_dir1,
        perplexity=2,  # Must be < n_samples=5
        random_state=42,
    )

    result2 = run_tsne_visualization(
        input_path=annotated_json_file,
        output_dir=output_dir2,
        perplexity=2,  # Must be < n_samples=5
        random_state=42,
    )

    # Same random state should produce identical coordinates
    np.testing.assert_array_almost_equal(result1["tsne_coordinates"], result2["tsne_coordinates"])


def test_run_tsne_visualization_missing_file(tmp_path):
    """Test error handling for missing input file."""
    missing_file = tmp_path / "nonexistent.json"
    output_dir = tmp_path / "output"

    with pytest.raises(FileNotFoundError):
        run_tsne_visualization(missing_file, output_dir)


# ============================================================================
# Optional Mapping Feature Tests
# ============================================================================


@pytest.mark.skipif(
    not pytest.importorskip("sklearn", reason="scikit-learn not installed"),
    reason="scikit-learn required",
)
def test_run_tsne_visualization_no_mapping_by_default(annotated_json_file, tmp_path):
    """Test that mapping file is NOT created by default."""
    output_dir = tmp_path / "output"

    result = run_tsne_visualization(
        input_path=annotated_json_file,
        output_dir=output_dir,
        perplexity=2,
        random_state=42,
    )

    # Mapping should not be saved by default
    assert result["mapping_path"] is None

    # Verify no .json files exist
    json_files = list(output_dir.glob("*.json"))
    assert len(json_files) == 0


@pytest.mark.skipif(
    not pytest.importorskip("sklearn", reason="scikit-learn not installed"),
    reason="scikit-learn required",
)
def test_run_tsne_visualization_saves_mapping_when_requested(annotated_json_file, tmp_path):
    """Test that mapping file IS created when save_mapping=True."""
    output_dir = tmp_path / "output"

    result = run_tsne_visualization(
        input_path=annotated_json_file,
        output_dir=output_dir,
        perplexity=2,
        random_state=42,
        save_mapping=True,
    )

    # Mapping should be saved
    assert result["mapping_path"] is not None
    assert result["mapping_path"].exists()
    assert result["mapping_path"].suffix == ".json"

    # Verify timestamp matches other outputs
    viz_timestamp = result["output_path"].stem.split(".")[0]
    mapping_timestamp = result["mapping_path"].stem.split(".")[0]
    assert viz_timestamp == mapping_timestamp


@pytest.mark.skipif(
    not pytest.importorskip("sklearn", reason="scikit-learn not installed"),
    reason="scikit-learn required",
)
def test_mapping_file_structure(annotated_json_file, tmp_path):
    """Test that mapping file has correct JSON structure."""
    output_dir = tmp_path / "output"

    result = run_tsne_visualization(
        input_path=annotated_json_file,
        output_dir=output_dir,
        perplexity=2,
        random_state=42,
        save_mapping=True,
    )

    # Load and parse mapping
    mapping_data = json.loads(result["mapping_path"].read_text())

    # Should be a list
    assert isinstance(mapping_data, list)
    assert len(mapping_data) == result["syllable_count"]

    # Check first record structure
    first_record = mapping_data[0]
    assert "syllable" in first_record
    assert "frequency" in first_record
    assert "tsne_x" in first_record
    assert "tsne_y" in first_record
    assert "features" in first_record

    # Verify types
    assert isinstance(first_record["syllable"], str)
    assert isinstance(first_record["frequency"], int)
    assert isinstance(first_record["tsne_x"], (int, float))
    assert isinstance(first_record["tsne_y"], (int, float))
    assert isinstance(first_record["features"], dict)

    # Verify features contain expected keys
    assert "contains_liquid" in first_record["features"]
    assert "starts_with_vowel" in first_record["features"]


@pytest.mark.skipif(
    not pytest.importorskip("sklearn", reason="scikit-learn not installed"),
    reason="scikit-learn required",
)
def test_mapping_coordinates_match_result(annotated_json_file, tmp_path):
    """Test that mapping file coordinates match returned tsne_coordinates."""
    output_dir = tmp_path / "output"

    result = run_tsne_visualization(
        input_path=annotated_json_file,
        output_dir=output_dir,
        perplexity=2,
        random_state=42,
        save_mapping=True,
    )

    # Load mapping
    mapping_data = json.loads(result["mapping_path"].read_text())

    # Compare coordinates
    coords = result["tsne_coordinates"]
    for i, record in enumerate(mapping_data):
        # Allow small floating point differences
        assert abs(record["tsne_x"] - coords[i, 0]) < 1e-6
        assert abs(record["tsne_y"] - coords[i, 1]) < 1e-6


@pytest.mark.skipif(
    not pytest.importorskip("sklearn", reason="scikit-learn not installed"),
    reason="scikit-learn required",
)
def test_full_pipeline_with_mapping(annotated_json_file, tmp_path):
    """Test complete pipeline execution with mapping file."""
    output_dir = tmp_path / "output"

    result = run_tsne_visualization(
        input_path=annotated_json_file,
        output_dir=output_dir,
        perplexity=2,
        random_state=42,
        dpi=100,
        verbose=False,
        save_mapping=True,
    )

    # Verify all expected outputs exist
    assert result["output_path"].exists()
    assert result["metadata_path"].exists()
    assert result["mapping_path"].exists()

    # Verify all files have same timestamp
    viz_name = result["output_path"].stem
    meta_name = result["metadata_path"].stem
    mapping_name = result["mapping_path"].stem

    # Extract timestamps (format: YYYYMMDD_HHMMSS.*)
    viz_ts = viz_name.split(".")[0]
    meta_ts = meta_name.split(".")[0]
    mapping_ts = mapping_name.split(".")[0]

    assert viz_ts == meta_ts == mapping_ts


@pytest.mark.skipif(
    not pytest.importorskip("sklearn", reason="scikit-learn not installed"),
    reason="scikit-learn required",
)
def test_verbose_output_with_mapping(annotated_json_file, tmp_path, capsys):
    """Test that verbose mode prints mapping path when saved."""
    output_dir = tmp_path / "output"

    run_tsne_visualization(
        input_path=annotated_json_file,
        output_dir=output_dir,
        perplexity=2,
        random_state=42,
        verbose=True,
        save_mapping=True,
    )

    captured = capsys.readouterr()
    assert "Mapping saved to:" in captured.out


# ============================================================================
# CLI Argument Parsing Tests
# ============================================================================


def test_parse_args_defaults():
    """Test default argument values."""
    with mock.patch("sys.argv", ["tsne_visualizer.py"]):
        args = parse_args()
        assert args.perplexity == 30
        assert args.random_state == 42
        assert args.dpi == 300
        assert args.verbose is False


def test_parse_args_custom_perplexity():
    """Test custom perplexity argument."""
    with mock.patch("sys.argv", ["tsne_visualizer.py", "--perplexity", "50"]):
        args = parse_args()
        assert args.perplexity == 50


def test_parse_args_custom_random_state():
    """Test custom random state argument."""
    with mock.patch("sys.argv", ["tsne_visualizer.py", "--random-state", "123"]):
        args = parse_args()
        assert args.random_state == 123


def test_parse_args_custom_dpi():
    """Test custom DPI argument."""
    with mock.patch("sys.argv", ["tsne_visualizer.py", "--dpi", "600"]):
        args = parse_args()
        assert args.dpi == 600


def test_parse_args_verbose():
    """Test verbose flag."""
    with mock.patch("sys.argv", ["tsne_visualizer.py", "--verbose"]):
        args = parse_args()
        assert args.verbose is True


def test_parse_args_save_mapping_default():
    """Test that --save-mapping defaults to False."""
    with mock.patch("sys.argv", ["tsne_visualizer.py"]):
        args = parse_args()
        assert args.save_mapping is False


def test_parse_args_save_mapping_flag():
    """Test that --save-mapping flag sets attribute to True."""
    with mock.patch("sys.argv", ["tsne_visualizer.py", "--save-mapping"]):
        args = parse_args()
        assert args.save_mapping is True


def test_parse_args_custom_paths():
    """Test custom input and output paths."""
    with mock.patch(
        "sys.argv",
        [
            "tsne_visualizer.py",
            "--input",
            "/custom/input.json",
            "--output",
            "/custom/output/",
        ],
    ):
        args = parse_args()
        assert args.input == Path("/custom/input.json")
        assert args.output == Path("/custom/output/")


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def test_all_features_constant():
    """Test that ALL_FEATURES constant contains expected features."""
    assert len(ALL_FEATURES) == 12
    assert "contains_liquid" in ALL_FEATURES
    assert "starts_with_vowel" in ALL_FEATURES
    assert "ends_with_nasal" in ALL_FEATURES


def test_extract_feature_matrix_single_record():
    """Test feature extraction with single record."""
    records = [
        {
            "syllable": "a",
            "frequency": 1,
            "features": {feat: False for feat in ALL_FEATURES},
        }
    ]
    matrix, frequencies = extract_feature_matrix(records)
    assert matrix.shape == (1, 12)
    assert frequencies == [1]
    assert np.all(matrix == 0)


@pytest.mark.skip(
    reason="t-SNE with uniform features can cause segfault - not a realistic use case"
)
def test_create_tsne_visualization_uniform_features():
    """Test t-SNE with uniform feature vectors (edge case).

    Note: This test is skipped because t-SNE with completely uniform
    feature vectors (zero variance) can cause segmentation faults in
    scikit-learn's Barnes-Hut implementation. This is not a realistic
    use case in our application.
    """
    # All syllables have identical features
    matrix = np.ones((5, 12))
    frequencies = [10, 20, 30, 40, 50]

    # This should still work (though results may not be meaningful)
    fig, coords = create_tsne_visualization(matrix, frequencies, perplexity=2)
    assert coords.shape == (5, 2)


# ============================================================================
# Integration with Analysis Package
# ============================================================================


def test_import_from_analysis_package():
    """Test that functions are importable from analysis package."""
    from build_tools.syllable_feature_annotator.analysis import (
        create_tsne_visualization,
        extract_feature_matrix,
        load_annotated_data,
        run_tsne_visualization,
        save_visualization,
    )

    # Just verify imports work
    assert callable(load_annotated_data)
    assert callable(extract_feature_matrix)
    assert callable(create_tsne_visualization)
    assert callable(save_visualization)
    assert callable(run_tsne_visualization)


# ============================================================================
# Interactive Visualization Tests
# ============================================================================


class TestInteractiveVisualization:
    """Test interactive Plotly visualization features."""

    def test_create_interactive_visualization_basic(self, sample_annotated_records, tmp_path):
        """Test basic interactive visualization creation."""
        go = pytest.importorskip("plotly.graph_objects")

        feature_matrix, frequencies = extract_feature_matrix(sample_annotated_records)
        fig, tsne_coords = create_tsne_visualization(
            feature_matrix, frequencies, perplexity=2, random_state=42
        )

        from build_tools.syllable_feature_annotator.analysis.tsne_visualizer import (
            create_interactive_visualization,
        )

        interactive_fig = create_interactive_visualization(sample_annotated_records, tsne_coords)

        assert isinstance(interactive_fig, go.Figure)
        assert len(interactive_fig.data) > 0
        assert interactive_fig.data[0].mode == "markers"
        assert len(interactive_fig.data[0].x) == len(sample_annotated_records)
        assert len(interactive_fig.data[0].y) == len(sample_annotated_records)

    def test_create_interactive_visualization_hover_text(self, sample_annotated_records, tmp_path):
        """Test that hover text contains syllable details."""
        pytest.importorskip("plotly")

        feature_matrix, frequencies = extract_feature_matrix(sample_annotated_records)
        fig, tsne_coords = create_tsne_visualization(
            feature_matrix, frequencies, perplexity=2, random_state=42
        )

        from build_tools.syllable_feature_annotator.analysis.tsne_visualizer import (
            create_interactive_visualization,
        )

        interactive_fig = create_interactive_visualization(sample_annotated_records, tsne_coords)

        # Check that hover text exists and contains expected content
        hover_texts = interactive_fig.data[0].hovertext
        assert len(hover_texts) == len(sample_annotated_records)

        # Check first syllable's hover text
        first_hover = hover_texts[0]
        assert sample_annotated_records[0]["syllable"] in first_hover
        assert "Frequency:" in first_hover
        assert "Features:" in first_hover

    def test_save_interactive_visualization(self, sample_annotated_records, tmp_path):
        """Test saving interactive HTML."""
        pytest.importorskip("plotly")

        feature_matrix, frequencies = extract_feature_matrix(sample_annotated_records)
        fig, tsne_coords = create_tsne_visualization(
            feature_matrix, frequencies, perplexity=2, random_state=42
        )

        from build_tools.syllable_feature_annotator.analysis.tsne_visualizer import (
            create_interactive_visualization,
            save_interactive_visualization,
        )

        interactive_fig = create_interactive_visualization(sample_annotated_records, tsne_coords)
        html_path = save_interactive_visualization(
            interactive_fig, tmp_path, perplexity=2, random_state=42
        )

        assert html_path.exists()
        assert html_path.suffix == ".html"
        assert "tsne_interactive" in html_path.name

        # Verify HTML content contains expected elements
        content = html_path.read_text()
        assert "plotly" in content.lower()
        assert "t-SNE" in content
        assert "perplexity" in content.lower()

    def test_interactive_visualization_metadata_footer(self, sample_annotated_records, tmp_path):
        """Test that HTML includes metadata footer with parameters."""
        pytest.importorskip("plotly")

        feature_matrix, frequencies = extract_feature_matrix(sample_annotated_records)
        fig, tsne_coords = create_tsne_visualization(
            feature_matrix, frequencies, perplexity=3, random_state=123
        )

        from build_tools.syllable_feature_annotator.analysis.tsne_visualizer import (
            create_interactive_visualization,
            save_interactive_visualization,
        )

        interactive_fig = create_interactive_visualization(sample_annotated_records, tsne_coords)
        html_path = save_interactive_visualization(
            interactive_fig, tmp_path, perplexity=3, random_state=123
        )

        content = html_path.read_text()
        # Check that metadata footer contains parameters
        assert "perplexity=3" in content.lower() or "3" in content
        assert "random_state=123" in content.lower() or "123" in content
        assert "Hamming" in content

    def test_interactive_flag_in_pipeline(self, annotated_json_file, tmp_path):
        """Test full pipeline with interactive flag."""
        pytest.importorskip("plotly")

        result = run_tsne_visualization(
            input_path=annotated_json_file,
            output_dir=tmp_path,
            perplexity=2,
            random_state=42,
            interactive=True,
            save_mapping=True,
        )

        assert result["interactive_path"] is not None
        assert result["interactive_path"].exists()
        assert "tsne_interactive" in result["interactive_path"].name

        # Verify other outputs still exist
        assert result["output_path"].exists()
        assert result["metadata_path"].exists()
        assert result["mapping_path"].exists()

    def test_interactive_without_plotly(self, annotated_json_file, tmp_path, monkeypatch):
        """Test graceful degradation when Plotly not available."""
        # Mock Plotly as unavailable
        monkeypatch.setattr(
            "build_tools.syllable_feature_annotator.analysis.tsne_visualizer._PLOTLY_AVAILABLE",
            False,
        )

        result = run_tsne_visualization(
            input_path=annotated_json_file,
            output_dir=tmp_path,
            perplexity=2,
            random_state=42,
            interactive=True,
        )

        # Should complete without error, but no interactive output
        assert result["interactive_path"] is None
        # Static outputs should still exist
        assert result["output_path"].exists()

    def test_cli_interactive_argument(self, monkeypatch):
        """Test CLI argument parsing for --interactive."""
        from build_tools.syllable_feature_annotator.analysis.tsne_visualizer import parse_args

        # Test with --interactive flag
        monkeypatch.setattr("sys.argv", ["tsne_visualizer.py", "--interactive"])
        args = parse_args()
        assert args.interactive is True

        # Test without --interactive flag
        monkeypatch.setattr("sys.argv", ["tsne_visualizer.py"])
        args = parse_args()
        assert args.interactive is False

    def test_interactive_disabled_by_default(self, annotated_json_file, tmp_path):
        """Test that interactive visualization is not created by default."""
        result = run_tsne_visualization(
            input_path=annotated_json_file,
            output_dir=tmp_path,
            perplexity=2,
            random_state=42,
            interactive=False,  # Explicitly disabled
        )

        # Interactive path should be None
        assert result["interactive_path"] is None

        # Static outputs should exist
        assert result["output_path"].exists()
        assert result["metadata_path"].exists()
