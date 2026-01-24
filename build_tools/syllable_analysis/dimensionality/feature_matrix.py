"""Feature matrix extraction for dimensionality reduction.

This module provides utilities for extracting numerical feature matrices from
annotated syllable records. The matrices are suitable for dimensionality reduction
algorithms like t-SNE, PCA, UMAP, etc.
"""

from __future__ import annotations

import numpy as np  # type: ignore[import-not-found]

# All features tracked by the annotator (order matters for consistent feature vectors)
# This canonical ordering ensures the same syllable always produces the same feature vector
ALL_FEATURES = [
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
]


def extract_feature_matrix(
    records: list[dict], feature_names: list[str] = ALL_FEATURES
) -> tuple[np.ndarray, list[int]]:
    """Extract binary feature matrix from annotated syllable records.

    Converts feature dictionaries to a numerical matrix suitable for
    dimensionality reduction algorithms. Each row represents a syllable,
    each column represents a feature (0 or 1).

    Args:
        records: List of annotated syllable records with 'features' and 'frequency' keys.
                Each record should have structure:
                {
                    "syllable": "ka",
                    "frequency": 187,
                    "features": {"contains_liquid": False, "contains_plosive": True, ...}
                }
        feature_names: Ordered list of feature names to extract (default: ALL_FEATURES).
                      Order determines column order in output matrix.

    Returns:
        Tuple of (feature_matrix, frequencies):
            - feature_matrix: numpy array of shape (n_syllables, n_features) with binary values
            - frequencies: List of frequency counts for each syllable

    Example:
        >>> records = [
        ...     {
        ...         "syllable": "ka",
        ...         "frequency": 187,
        ...         "features": {"contains_liquid": False, "contains_plosive": True, ...}
        ...     }
        ... ]
        >>> matrix, freqs = extract_feature_matrix(records)
        >>> matrix.shape
        (1, 12)
        >>> freqs
        [187]

    Notes:
        - Missing features default to False (0)
        - Feature values are converted to int (True→1, False→0)
        - Output matrix dtype is int for memory efficiency
        - Empty record list returns (0, n_features) shaped array
    """
    feature_matrix = []
    frequencies = []

    for record in records:
        # Extract feature values in consistent order
        feature_vector = [int(record["features"].get(feat, False)) for feat in feature_names]
        feature_matrix.append(feature_vector)
        frequencies.append(record["frequency"])

    # Handle empty case explicitly to ensure correct shape
    if not feature_matrix:
        return np.empty((0, len(feature_names)), dtype=int), frequencies

    return np.array(feature_matrix, dtype=int), frequencies


def validate_feature_matrix(feature_matrix: np.ndarray, expected_features: int = 12) -> None:
    """Validate feature matrix shape and contents.

    Ensures the feature matrix has the expected structure for dimensionality
    reduction algorithms.

    Args:
        feature_matrix: Binary feature matrix
        expected_features: Expected number of features (default: 12)

    Raises:
        ValueError: If validation fails (wrong shape, non-binary values, etc.)

    Example:
        >>> matrix = np.array([[1, 0, 1], [0, 1, 0]])
        >>> validate_feature_matrix(matrix, expected_features=3)  # OK
        >>> validate_feature_matrix(matrix, expected_features=4)  # Raises ValueError
    """
    if feature_matrix.ndim != 2:
        raise ValueError(
            f"Feature matrix must be 2D, got {feature_matrix.ndim}D with shape {feature_matrix.shape}"
        )

    if feature_matrix.shape[1] != expected_features:
        raise ValueError(
            f"Expected {expected_features} features, got {feature_matrix.shape[1]} features"
        )

    if feature_matrix.shape[0] == 0:
        raise ValueError("Feature matrix has no samples (0 rows)")

    # Check for binary values (0 or 1 only)
    unique_values = np.unique(feature_matrix)
    if not np.all(np.isin(unique_values, [0, 1])):
        raise ValueError(
            f"Feature matrix must contain only binary values (0, 1), found: {unique_values}"
        )


def get_feature_vector(
    features: dict[str, bool], feature_names: list[str] = ALL_FEATURES
) -> list[int]:
    """Extract a single feature vector from a feature dictionary.

    Converts a dictionary of feature flags to an ordered binary vector.
    Useful for extracting vectors from individual syllables.

    Args:
        features: Dictionary of feature name → boolean value
        feature_names: Ordered list of feature names (default: ALL_FEATURES)

    Returns:
        Binary feature vector matching feature_names order

    Example:
        >>> features = {"contains_liquid": True, "contains_plosive": False}
        >>> vector = get_feature_vector(features, ["contains_liquid", "contains_plosive"])
        >>> vector
        [1, 0]

    Notes:
        - Missing features default to False (0)
        - Order of output matches order of feature_names
        - Output is Python list, not numpy array (for flexibility)
    """
    return [int(features.get(feat, False)) for feat in feature_names]
