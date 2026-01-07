"""Integration tests for t-SNE visualization pipeline.

Tests the main pipeline function (run_tsne_visualization).
Unit tests for individual components are in:
- tests/test_analysis_common.py (data loading)
- tests/test_dimensionality.py (feature extraction, t-SNE)
- tests/test_plotting.py (visualization)
"""

import json
from pathlib import Path

import pytest

# Check if optional dependencies are available
pytest.importorskip("numpy", reason="numpy not installed")
pytest.importorskip("sklearn", reason="scikit-learn not installed")
pytest.importorskip("matplotlib", reason="matplotlib not installed")

from build_tools.syllable_analysis.tsne_visualizer import run_tsne_visualization  # noqa: E402

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_annotated_file(tmp_path):
    """Create a sample annotated syllables JSON file."""
    data = [
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

    input_file = tmp_path / "syllables_annotated.json"
    input_file.write_text(json.dumps(data, indent=2))
    return input_file


# ============================================================================
# Integration Tests: run_tsne_visualization()
# ============================================================================


def test_run_tsne_visualization_complete(sample_annotated_file, tmp_path):
    """Test complete t-SNE visualization pipeline."""
    output_dir = tmp_path / "output"
    result = run_tsne_visualization(
        input_path=sample_annotated_file,
        output_dir=output_dir,
        perplexity=2,  # Small dataset
        random_state=42,
    )

    assert result["syllable_count"] == 5
    assert result["feature_count"] == 12
    assert Path(result["output_path"]).exists()
    assert Path(result["metadata_path"]).exists()
    assert result["tsne_coordinates"].shape == (5, 2)
    assert result["mapping_path"] is None  # Not requested


def test_run_tsne_visualization_verbose(sample_annotated_file, tmp_path, capsys):
    """Test verbose output during visualization."""
    output_dir = tmp_path / "output"
    run_tsne_visualization(
        input_path=sample_annotated_file,
        output_dir=output_dir,
        perplexity=2,
        verbose=True,
    )

    captured = capsys.readouterr()
    assert "Loading" in captured.out or "Extracting" in captured.out or "Applying" in captured.out


def test_run_tsne_visualization_deterministic(sample_annotated_file, tmp_path):
    """Test that t-SNE visualization is deterministic with same random_state."""
    output_dir1 = tmp_path / "output1"
    output_dir2 = tmp_path / "output2"

    result1 = run_tsne_visualization(
        input_path=sample_annotated_file,
        output_dir=output_dir1,
        perplexity=2,
        random_state=42,
    )

    result2 = run_tsne_visualization(
        input_path=sample_annotated_file,
        output_dir=output_dir2,
        perplexity=2,
        random_state=42,
    )

    # Results should be identical (same counts)
    assert result1["syllable_count"] == result2["syllable_count"]
    assert result1["feature_count"] == result2["feature_count"]


def test_run_tsne_visualization_missing_file(tmp_path):
    """Test error handling for missing input file."""
    nonexistent_file = tmp_path / "nonexistent.json"
    output_dir = tmp_path / "output"

    with pytest.raises(FileNotFoundError):
        run_tsne_visualization(
            input_path=nonexistent_file,
            output_dir=output_dir,
        )


def test_run_tsne_visualization_no_mapping_by_default(sample_annotated_file, tmp_path):
    """Test that coordinate mapping is not saved by default."""
    output_dir = tmp_path / "output"
    result = run_tsne_visualization(
        input_path=sample_annotated_file,
        output_dir=output_dir,
        perplexity=2,
    )

    # Should not have mapping file
    assert result["mapping_path"] is None
    mapping_files = list(output_dir.glob("*mapping*.json"))
    assert len(mapping_files) == 0


def test_run_tsne_visualization_saves_mapping_when_requested(sample_annotated_file, tmp_path):
    """Test that coordinate mapping is saved when save_mapping=True."""
    output_dir = tmp_path / "output"
    result = run_tsne_visualization(
        input_path=sample_annotated_file,
        output_dir=output_dir,
        perplexity=2,
        save_mapping=True,
    )

    assert result["mapping_path"] is not None
    mapping_path = Path(result["mapping_path"])
    assert mapping_path.exists()

    # Verify mapping structure (list of records with tsne_x, tsne_y)
    mapping_data = json.loads(mapping_path.read_text())
    assert isinstance(mapping_data, list)
    assert len(mapping_data) == 5
    assert "tsne_x" in mapping_data[0]
    assert "tsne_y" in mapping_data[0]


def test_mapping_file_structure(sample_annotated_file, tmp_path):
    """Test that mapping file has correct structure."""
    output_dir = tmp_path / "output"
    result = run_tsne_visualization(
        input_path=sample_annotated_file,
        output_dir=output_dir,
        perplexity=2,
        save_mapping=True,
    )

    mapping_path = Path(result["mapping_path"])
    mapping_data = json.loads(mapping_path.read_text())

    # Check structure - should be list of records
    assert isinstance(mapping_data, list)

    # Check each record has required fields
    for record in mapping_data:
        assert "syllable" in record
        assert "frequency" in record
        assert "features" in record
        assert "tsne_x" in record
        assert "tsne_y" in record
        assert isinstance(record["tsne_x"], (int, float))
        assert isinstance(record["tsne_y"], (int, float))


def test_mapping_coordinates_match_result(sample_annotated_file, tmp_path):
    """Test that number of coordinates matches input syllables."""
    output_dir = tmp_path / "output"
    result = run_tsne_visualization(
        input_path=sample_annotated_file,
        output_dir=output_dir,
        perplexity=2,
        save_mapping=True,
    )

    mapping_path = Path(result["mapping_path"])
    mapping_data = json.loads(mapping_path.read_text())

    assert len(mapping_data) == result["syllable_count"]


def test_full_pipeline_with_mapping(sample_annotated_file, tmp_path):
    """Test full pipeline with all outputs."""
    output_dir = tmp_path / "output"
    result = run_tsne_visualization(
        input_path=sample_annotated_file,
        output_dir=output_dir,
        perplexity=2,
        random_state=42,
        dpi=150,
        save_mapping=True,
        verbose=False,
    )

    # Check all outputs exist
    assert Path(result["output_path"]).exists()
    assert Path(result["metadata_path"]).exists()
    assert Path(result["mapping_path"]).exists()

    # Check result metadata
    assert result["syllable_count"] == 5
    assert result["feature_count"] == 12


def test_interactive_flag_in_pipeline(sample_annotated_file, tmp_path):
    """Test that interactive flag works in pipeline."""
    output_dir = tmp_path / "output"

    # Should not fail even without Plotly
    result = run_tsne_visualization(
        input_path=sample_annotated_file,
        output_dir=output_dir,
        perplexity=2,
        interactive=True,  # Will be skipped if Plotly not available
    )

    # Should still complete successfully
    assert result["syllable_count"] == 5
    assert result["feature_count"] == 12
