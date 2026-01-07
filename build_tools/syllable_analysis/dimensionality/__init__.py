"""Dimensionality reduction utilities for feature signature analysis.

This subpackage provides tools for dimensionality reduction and coordinate mapping
of high-dimensional feature vectors.

Modules
-------
feature_matrix : Feature extraction and matrix generation
tsne_core : t-SNE dimensionality reduction
mapping : Coordinate mapping utilities
"""

from build_tools.syllable_analysis.dimensionality.feature_matrix import (
    ALL_FEATURES,
    extract_feature_matrix,
    get_feature_vector,
    validate_feature_matrix,
)
from build_tools.syllable_analysis.dimensionality.mapping import (
    create_tsne_mapping,
    save_tsne_mapping,
)
from build_tools.syllable_analysis.dimensionality.tsne_core import (
    apply_tsne,
    calculate_optimal_perplexity,
)

__all__ = [
    # Feature matrix
    "ALL_FEATURES",
    "extract_feature_matrix",
    "get_feature_vector",
    "validate_feature_matrix",
    # t-SNE core
    "apply_tsne",
    "calculate_optimal_perplexity",
    # Mapping
    "create_tsne_mapping",
    "save_tsne_mapping",
]
