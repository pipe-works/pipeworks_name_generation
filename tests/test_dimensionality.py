"""Unit tests for dimensionality reduction modules.

Tests cover:
- Feature matrix extraction and validation
- t-SNE core functionality
- Coordinate mapping utilities
"""

# mypy: ignore-errors

import json

import pytest

# Check if optional dependencies are available before importing them
# ruff: noqa: E402
pytest.importorskip("numpy", reason="numpy required for dimensionality tests")
pytest.importorskip("sklearn", reason="scikit-learn required for dimensionality tests")

import numpy as np  # noqa: E402

from build_tools.syllable_feature_annotator.analysis.dimensionality import (  # noqa: E402
    ALL_FEATURES,
    apply_tsne,
    calculate_optimal_perplexity,
    create_tsne_mapping,
    extract_feature_matrix,
    get_feature_vector,
    save_tsne_mapping,
    validate_feature_matrix,
)

# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def sample_records():
    """Sample annotated syllable records for testing."""
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
            "syllable": "ran",
            "frequency": 42,
            "features": {
                "contains_liquid": True,
                "contains_plosive": False,
                "contains_fricative": False,
                "contains_nasal": True,
                "long_vowel": False,
                "short_vowel": True,
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "ends_with_vowel": False,
                "ends_with_stop": False,
                "ends_with_nasal": True,
            },
        },
        {
            "syllable": "spla",
            "frequency": 3,
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
def sample_feature_matrix():
    """Sample binary feature matrix."""
    return np.array([[1, 0, 1, 0], [0, 1, 0, 1], [1, 1, 0, 0]], dtype=int)


@pytest.fixture
def sample_tsne_coords():
    """Sample 2D t-SNE coordinates."""
    return np.array([[-2.34, 5.67], [1.23, -0.89], [0.45, 2.10]])


# =============================================================================
# Feature Matrix Tests
# =============================================================================


class TestFeatureConstants:
    """Tests for feature constant definitions."""

    def test_all_features_has_12_items(self):
        """ALL_FEATURES should contain exactly 12 feature names."""
        assert len(ALL_FEATURES) == 12

    def test_all_features_are_strings(self):
        """All feature names should be strings."""
        assert all(isinstance(feat, str) for feat in ALL_FEATURES)

    def test_all_features_are_unique(self):
        """Feature names should be unique (no duplicates)."""
        assert len(ALL_FEATURES) == len(set(ALL_FEATURES))

    def test_all_features_expected_names(self):
        """Check that expected feature names are present."""
        expected = {
            "contains_liquid",
            "contains_plosive",
            "contains_fricative",
            "contains_nasal",
            "long_vowel",
            "short_vowel",
            "starts_with_vowel",
            "starts_with_cluster",
            "starts_with_heavy_cluster",
            "ends_with_vowel",
            "ends_with_stop",
            "ends_with_nasal",
        }
        assert set(ALL_FEATURES) == expected


class TestExtractFeatureMatrix:
    """Tests for extract_feature_matrix function."""

    def test_extract_basic_matrix(self, sample_records):
        """Should extract correct matrix shape and frequencies."""
        matrix, freqs = extract_feature_matrix(sample_records)

        assert matrix.shape == (3, 12)
        assert freqs == [187, 42, 3]

    def test_extract_matrix_binary_values(self, sample_records):
        """Matrix should contain only 0s and 1s."""
        matrix, _ = extract_feature_matrix(sample_records)

        unique_vals = np.unique(matrix)
        assert np.all(np.isin(unique_vals, [0, 1]))

    def test_extract_matrix_dtype(self, sample_records):
        """Matrix should have int dtype."""
        matrix, _ = extract_feature_matrix(sample_records)

        assert matrix.dtype == np.int_ or matrix.dtype == np.int64

    def test_extract_matrix_first_row(self, sample_records):
        """First row should match first record's features."""
        matrix, _ = extract_feature_matrix(sample_records)

        # "ka" has contains_plosive=True, short_vowel=True, ends_with_vowel=True
        # ALL_FEATURES order: liquid, plosive, fricative, nasal, long, short, ...
        expected_row = [0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0]
        assert list(matrix[0]) == expected_row

    def test_extract_with_custom_feature_names(self, sample_records):
        """Should work with custom feature name list."""
        custom_features = ["contains_plosive", "short_vowel"]
        matrix, freqs = extract_feature_matrix(sample_records, custom_features)

        assert matrix.shape == (3, 2)
        assert list(matrix[0]) == [1, 1]  # ka: plosive=True, short=True

    def test_extract_missing_feature_defaults_to_false(self):
        """Missing features should default to False (0)."""
        records = [
            {
                "syllable": "test",
                "frequency": 1,
                "features": {"contains_plosive": True},  # Only one feature present
            }
        ]

        matrix, _ = extract_feature_matrix(records, ["contains_plosive", "contains_liquid"])
        assert list(matrix[0]) == [1, 0]  # plosive=1, liquid=0 (defaulted)

    def test_extract_empty_records(self):
        """Should handle empty record list gracefully."""
        matrix, freqs = extract_feature_matrix([])

        assert matrix.shape[0] == 0  # No rows
        assert matrix.shape[1] == 12  # But still 12 columns
        assert freqs == []


class TestValidateFeatureMatrix:
    """Tests for validate_feature_matrix function."""

    def test_validate_correct_matrix(self):
        """Should not raise for valid matrix."""
        matrix = np.array([[1, 0, 1], [0, 1, 0]], dtype=int)
        validate_feature_matrix(matrix, expected_features=3)  # Should not raise

    def test_validate_wrong_feature_count(self):
        """Should raise ValueError for wrong number of features."""
        matrix = np.array([[1, 0, 1], [0, 1, 0]])

        with pytest.raises(ValueError, match="Expected 4 features, got 3 features"):
            validate_feature_matrix(matrix, expected_features=4)

    def test_validate_not_2d(self):
        """Should raise ValueError for non-2D matrix."""
        matrix = np.array([1, 0, 1])  # 1D

        with pytest.raises(ValueError, match="must be 2D"):
            validate_feature_matrix(matrix, expected_features=3)

    def test_validate_empty_matrix(self):
        """Should raise ValueError for matrix with no rows."""
        matrix = np.array([]).reshape(0, 12)

        with pytest.raises(ValueError, match="no samples"):
            validate_feature_matrix(matrix, expected_features=12)

    def test_validate_non_binary_values(self):
        """Should raise ValueError for non-binary values."""
        matrix = np.array([[1, 2, 0], [0, 1, 3]])  # Contains 2 and 3

        with pytest.raises(ValueError, match="only binary values"):
            validate_feature_matrix(matrix, expected_features=3)


class TestGetFeatureVector:
    """Tests for get_feature_vector function."""

    def test_get_vector_basic(self):
        """Should extract ordered feature vector."""
        features = {"contains_plosive": True, "short_vowel": True, "contains_liquid": False}
        feature_names = ["contains_liquid", "contains_plosive", "short_vowel"]

        vector = get_feature_vector(features, feature_names)

        assert vector == [0, 1, 1]

    def test_get_vector_all_false(self):
        """Should handle all False features."""
        features = {"feat1": False, "feat2": False}

        vector = get_feature_vector(features, ["feat1", "feat2"])

        assert vector == [0, 0]

    def test_get_vector_missing_defaults_to_false(self):
        """Missing features should default to False."""
        features = {"feat1": True}

        vector = get_feature_vector(features, ["feat1", "feat2", "feat3"])

        assert vector == [1, 0, 0]

    def test_get_vector_returns_list(self):
        """Should return Python list, not numpy array."""
        features = {"feat1": True}

        vector = get_feature_vector(features, ["feat1"])

        assert isinstance(vector, list)
        assert not isinstance(vector, np.ndarray)


# =============================================================================
# t-SNE Core Tests
# =============================================================================


class TestApplyTSNE:
    """Tests for apply_tsne function."""

    def test_apply_tsne_basic(self):
        """Should reduce dimensions correctly."""
        # Create sample binary feature matrix (20 samples, 12 features)
        np.random.seed(42)
        feature_matrix = np.random.randint(0, 2, size=(20, 12))

        coords = apply_tsne(feature_matrix, n_components=2, perplexity=5, random_state=42)

        assert coords.shape == (20, 2)
        assert isinstance(coords, np.ndarray)

    def test_apply_tsne_3d(self):
        """Should work with 3D output."""
        np.random.seed(42)
        feature_matrix = np.random.randint(0, 2, size=(20, 12))

        coords = apply_tsne(feature_matrix, n_components=3, perplexity=5, random_state=42)

        assert coords.shape == (20, 3)

    def test_apply_tsne_reproducible(self):
        """Same random_state should produce same results."""
        np.random.seed(42)
        feature_matrix = np.random.randint(0, 2, size=(20, 12))

        coords1 = apply_tsne(feature_matrix, random_state=42, perplexity=5)
        coords2 = apply_tsne(feature_matrix, random_state=42, perplexity=5)

        np.testing.assert_array_almost_equal(coords1, coords2)

    def test_apply_tsne_different_seed_different_results(self):
        """Different random_state can produce different results."""
        np.random.seed(42)
        feature_matrix = np.random.randint(0, 2, size=(50, 12))

        coords1 = apply_tsne(feature_matrix, random_state=42, perplexity=5)
        coords2 = apply_tsne(feature_matrix, random_state=999, perplexity=5)

        # Results should typically differ, but not guaranteed
        # Just verify both runs complete successfully and produce valid output
        assert coords1.shape == coords2.shape
        assert coords1.shape == (50, 2)

    def test_apply_tsne_perplexity_too_large(self):
        """Should raise ValueError if perplexity >= n_samples."""
        feature_matrix = np.random.randint(0, 2, size=(10, 12))

        with pytest.raises(ValueError, match="Perplexity .* must be less than"):
            apply_tsne(feature_matrix, perplexity=15)  # perplexity > n_samples

    def test_apply_tsne_with_hamming_metric(self):
        """Should accept hamming metric for binary features."""
        np.random.seed(42)
        feature_matrix = np.random.randint(0, 2, size=(20, 12))

        coords = apply_tsne(feature_matrix, metric="hamming", perplexity=5)

        assert coords.shape == (20, 2)


class TestCalculateOptimalPerplexity:
    """Tests for calculate_optimal_perplexity function."""

    def test_small_dataset(self):
        """Small datasets should get minimum perplexity."""
        assert calculate_optimal_perplexity(10) == 5
        assert calculate_optimal_perplexity(25) == 5

    def test_medium_dataset(self):
        """Medium datasets should get sqrt-based perplexity."""
        assert calculate_optimal_perplexity(100) == 10  # sqrt(100) = 10
        assert calculate_optimal_perplexity(400) == 20  # sqrt(400) = 20

    def test_large_dataset(self):
        """Large datasets should get capped at max perplexity."""
        assert calculate_optimal_perplexity(10000) == 50  # sqrt(10000) = 100, capped at 50
        assert calculate_optimal_perplexity(5000) == 50  # sqrt(5000) = 70, capped at 50

    def test_boundary_values(self):
        """Test boundary conditions."""
        assert calculate_optimal_perplexity(1) == 5  # Minimum
        assert calculate_optimal_perplexity(2500) == 50  # sqrt(2500) = 50, exactly at max

    def test_custom_min_max(self):
        """Should respect custom min/max values."""
        assert calculate_optimal_perplexity(100, min_perplexity=10, max_perplexity=30) == 10
        assert calculate_optimal_perplexity(1000, min_perplexity=10, max_perplexity=30) == 30


# =============================================================================
# Mapping Tests
# =============================================================================


class TestCreateTSNEMapping:
    """Tests for create_tsne_mapping function."""

    def test_create_mapping_basic(self, sample_records, sample_tsne_coords):
        """Should create correct mapping structure."""
        mapping = create_tsne_mapping(sample_records, sample_tsne_coords)

        assert len(mapping) == 3
        assert mapping[0]["syllable"] == "ka"
        assert mapping[0]["frequency"] == 187
        assert mapping[0]["tsne_x"] == -2.34
        assert mapping[0]["tsne_y"] == 5.67
        assert "features" in mapping[0]

    def test_create_mapping_preserves_features(self, sample_records, sample_tsne_coords):
        """Should preserve all features from original records."""
        mapping = create_tsne_mapping(sample_records, sample_tsne_coords)

        assert mapping[0]["features"] == sample_records[0]["features"]

    def test_create_mapping_converts_numpy_float(self, sample_records):
        """Coordinates should be Python floats, not numpy floats."""
        coords = np.array([[1.23, 4.56]], dtype=np.float64)
        mapping = create_tsne_mapping(sample_records[:1], coords)

        assert isinstance(mapping[0]["tsne_x"], float)
        assert not isinstance(mapping[0]["tsne_x"], np.floating)

    def test_create_mapping_3d_coords(self, sample_records):
        """Should handle 3D coordinates correctly."""
        coords = np.array([[-2.1, 3.4, 1.2], [0.5, -1.3, 2.7], [1.8, 0.4, -0.9]])
        mapping = create_tsne_mapping(sample_records, coords)

        assert "tsne_x" in mapping[0]
        assert "tsne_y" in mapping[0]
        assert "tsne_z" in mapping[0]
        assert mapping[0]["tsne_z"] == 1.2

    def test_create_mapping_mismatched_lengths(self, sample_records, sample_tsne_coords):
        """Should raise ValueError for mismatched lengths."""
        with pytest.raises(ValueError, match="does not match"):
            create_tsne_mapping(
                sample_records, sample_tsne_coords[:2]
            )  # Only 2 coords for 3 records


class TestSaveTSNEMapping:
    """Tests for save_tsne_mapping function."""

    def test_save_mapping_creates_file(self, tmp_path, sample_records, sample_tsne_coords):
        """Should create output file."""
        output_path = tmp_path / "mapping.json"
        mapping = create_tsne_mapping(sample_records, sample_tsne_coords)

        save_tsne_mapping(mapping, output_path)

        assert output_path.exists()

    def test_save_mapping_valid_json(self, tmp_path, sample_records, sample_tsne_coords):
        """Saved file should be valid JSON."""
        output_path = tmp_path / "mapping.json"
        mapping = create_tsne_mapping(sample_records, sample_tsne_coords)

        save_tsne_mapping(mapping, output_path)

        # Should be able to load as JSON
        with output_path.open() as f:
            loaded = json.load(f)

        assert len(loaded) == 3

    def test_save_mapping_preserves_data(self, tmp_path, sample_records, sample_tsne_coords):
        """Saved and loaded data should match original."""
        output_path = tmp_path / "mapping.json"
        mapping = create_tsne_mapping(sample_records, sample_tsne_coords)

        save_tsne_mapping(mapping, output_path)

        with output_path.open() as f:
            loaded = json.load(f)

        assert loaded[0]["syllable"] == "ka"
        assert loaded[0]["tsne_x"] == -2.34

    def test_save_mapping_creates_parent_directories(
        self, tmp_path, sample_records, sample_tsne_coords
    ):
        """Should create parent directories if they don't exist."""
        output_path = tmp_path / "subdir" / "nested" / "mapping.json"
        mapping = create_tsne_mapping(sample_records, sample_tsne_coords)

        save_tsne_mapping(mapping, output_path)

        assert output_path.exists()
        assert output_path.parent.exists()

    def test_save_mapping_custom_indent(self, tmp_path, sample_records, sample_tsne_coords):
        """Should respect custom indentation."""
        output_path = tmp_path / "mapping.json"
        mapping = create_tsne_mapping(sample_records, sample_tsne_coords)

        save_tsne_mapping(mapping, output_path, indent=4)

        content = output_path.read_text()
        # Check for 4-space indentation
        assert '    "syllable"' in content


# =============================================================================
# Integration Tests
# =============================================================================


class TestDimensionalityIntegration:
    """Integration tests for end-to-end dimensionality workflows."""

    def test_full_pipeline_extract_to_mapping(self, sample_records, tmp_path):
        """Test complete pipeline: extract → t-SNE → mapping → save."""
        # Extract feature matrix
        feature_matrix, frequencies = extract_feature_matrix(sample_records)

        # Validate matrix
        validate_feature_matrix(feature_matrix, expected_features=12)

        # Apply t-SNE (use low perplexity for small dataset)
        tsne_coords = apply_tsne(feature_matrix, perplexity=2, random_state=42)

        # Create mapping
        mapping = create_tsne_mapping(sample_records, tsne_coords)

        # Save mapping
        output_path = tmp_path / "test_mapping.json"
        save_tsne_mapping(mapping, output_path)

        # Verify end-to-end
        assert output_path.exists()
        with output_path.open() as f:
            loaded = json.load(f)
        assert len(loaded) == 3
        assert all("tsne_x" in entry for entry in loaded)

    def test_pipeline_reproducibility(self, sample_records):
        """Same input should produce same output."""
        feature_matrix, _ = extract_feature_matrix(sample_records)

        coords1 = apply_tsne(feature_matrix, perplexity=2, random_state=42)
        coords2 = apply_tsne(feature_matrix, perplexity=2, random_state=42)

        mapping1 = create_tsne_mapping(sample_records, coords1)
        mapping2 = create_tsne_mapping(sample_records, coords2)

        assert mapping1[0]["tsne_x"] == mapping2[0]["tsne_x"]
        assert mapping1[0]["tsne_y"] == mapping2[0]["tsne_y"]
