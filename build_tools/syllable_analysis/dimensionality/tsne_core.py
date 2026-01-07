"""t-SNE dimensionality reduction core functionality.

This module provides the core t-SNE application logic, isolated from visualization
and I/O concerns. It can be used for any dimensionality reduction task on feature
matrices.
"""

import numpy as np  # type: ignore[import-not-found]


def apply_tsne(
    feature_matrix: np.ndarray,
    n_components: int = 2,
    perplexity: int = 30,
    random_state: int = 42,
    metric: str = "hamming",
) -> np.ndarray:
    """Apply t-SNE dimensionality reduction to feature matrix.

    t-SNE (t-distributed Stochastic Neighbor Embedding) is a technique for
    dimensionality reduction that projects high-dimensional data into lower
    dimensions while preserving local structure.

    Args:
        feature_matrix: Input feature matrix (n_samples, n_features).
                       For binary features, should contain only 0s and 1s.
        n_components: Number of dimensions for output (default: 2).
                     2D is typical for visualization, 3D also common.
        perplexity: t-SNE perplexity parameter (default: 30).
                   Controls balance between local and global structure.
                   Typical range: 5-50. Higher values consider more neighbors.
                   Should be less than n_samples.
        random_state: Random seed for reproducibility (default: 42).
                     Same seed ensures identical output for same input.
        metric: Distance metric (default: 'hamming').
               'hamming' is optimal for binary features (counts # of differences).
               Other options: 'euclidean', 'manhattan', 'cosine', etc.

    Returns:
        Reduced coordinates array of shape (n_samples, n_components).
        For default n_components=2, output is (n_samples, 2) with x,y coordinates.

    Raises:
        ImportError: If scikit-learn is not installed
        ValueError: If perplexity is invalid (too large for sample size)

    Example:
        >>> import numpy as np
        >>> from build_tools.syllable_analysis.dimensionality import apply_tsne
        >>> # Create sample binary feature matrix (100 samples, 12 features)
        >>> feature_matrix = np.random.randint(0, 2, size=(100, 12))
        >>> # Apply t-SNE to reduce to 2D
        >>> coords_2d = apply_tsne(feature_matrix, n_components=2, perplexity=30)
        >>> coords_2d.shape
        (100, 2)

    Notes:
        - Processing time scales roughly O(n²) with sample size
        - Perplexity should be less than n_samples (typically n_samples/3 max)
        - Hamming distance is best for binary features (our use case)
        - Fixed random_state ensures reproducible results
        - For large datasets (>10,000 samples), consider using approximate methods
    """
    try:
        from sklearn.manifold import TSNE  # type: ignore[import-not-found]
    except ImportError as e:
        raise ImportError(
            "scikit-learn is required for t-SNE. Install with: pip install scikit-learn"
        ) from e

    # Validate perplexity is reasonable for sample size
    n_samples = feature_matrix.shape[0]
    if perplexity >= n_samples:
        raise ValueError(
            f"Perplexity ({perplexity}) must be less than number of samples ({n_samples}). "
            f"Suggested: perplexity <= {n_samples // 3}"
        )

    # Apply t-SNE
    tsne = TSNE(
        n_components=n_components,
        perplexity=perplexity,
        random_state=random_state,
        metric=metric,
    )
    reduced_coords = tsne.fit_transform(feature_matrix)

    return reduced_coords


def calculate_optimal_perplexity(
    n_samples: int, min_perplexity: int = 5, max_perplexity: int = 50
) -> int:
    """Suggest optimal perplexity value based on dataset size.

    Perplexity is a key t-SNE parameter that balances local vs global structure.
    This function provides a reasonable default based on dataset size.

    Rule of thumb:
        - Perplexity should be between 5 and 50
        - Perplexity should be less than n_samples
        - Common heuristic: perplexity ≈ sqrt(n_samples), clamped to [5, 50]

    Args:
        n_samples: Number of samples in dataset
        min_perplexity: Minimum perplexity value (default: 5)
        max_perplexity: Maximum perplexity value (default: 50)

    Returns:
        Suggested perplexity value

    Example:
        >>> calculate_optimal_perplexity(100)
        10
        >>> calculate_optimal_perplexity(1000)
        31
        >>> calculate_optimal_perplexity(10000)
        50
        >>> calculate_optimal_perplexity(10)
        5

    Notes:
        - For small datasets (<25 samples): use min_perplexity (5)
        - For large datasets (>2500 samples): use max_perplexity (50)
        - For medium datasets: use sqrt(n_samples)
        - This is a heuristic, not a strict rule - experiment for best results
    """
    # Use square root heuristic
    suggested = int(np.sqrt(n_samples))

    # Clamp to valid range
    return max(min_perplexity, min(suggested, max_perplexity))
