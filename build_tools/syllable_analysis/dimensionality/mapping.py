"""Coordinate mapping utilities for dimensionality reduction results.

This module provides functions for creating and saving mappings between syllables
and their reduced-dimension coordinates (e.g., from t-SNE, PCA, UMAP).
"""

import json
from pathlib import Path
from typing import Dict, List

import numpy as np  # type: ignore[import-not-found]


def create_tsne_mapping(records: List[Dict], tsne_coords: np.ndarray) -> List[Dict]:
    """Create syllable→features→coordinates mapping.

    Combines annotated syllable records with their t-SNE coordinates to create
    a comprehensive mapping structure. This is useful for:
    - Post-hoc cluster analysis
    - Cross-referencing visualizations
    - Interactive exploration
    - Sharing visualizations with collaborators

    Args:
        records: Original annotated syllable records from load_annotated_syllables().
                Each record should have:
                - syllable (str): The syllable text
                - frequency (int): Occurrence count
                - features (dict): Boolean feature flags
        tsne_coords: t-SNE coordinate array (n_syllables × n_dimensions).
                    Typically 2D for visualization, but can be 3D or higher.

    Returns:
        List of mapping records with structure:
        [
            {
                "syllable": "kran",
                "frequency": 7,
                "tsne_x": -2.34,
                "tsne_y": 5.67,
                "features": {...}
            },
            ...
        ]

    Raises:
        ValueError: If records and tsne_coords have mismatched lengths

    Example:
        >>> records = [
        ...     {"syllable": "ka", "frequency": 187, "features": {...}},
        ...     {"syllable": "ran", "frequency": 42, "features": {...}}
        ... ]
        >>> coords = np.array([[-2.1, 3.4], [1.5, -0.8]])
        >>> mapping = create_tsne_mapping(records, coords)
        >>> mapping[0]["tsne_x"]
        -2.1
        >>> mapping[0]["syllable"]
        'ka'

    Notes:
        - Array indices preserve order from input records
        - Coordinates are converted from numpy float64 to Python float for JSON compatibility
        - All original record fields are preserved in the mapping
        - For 2D t-SNE: creates tsne_x and tsne_y fields
        - For 3D+ t-SNE: creates tsne_x, tsne_y, tsne_z, ... fields
    """
    if len(records) != len(tsne_coords):
        raise ValueError(
            f"Records count ({len(records)}) does not match coordinates count ({len(tsne_coords)})"
        )

    n_dimensions = tsne_coords.shape[1]

    # Build mapping: combine records with their t-SNE coordinates
    mapping = []
    for i, record in enumerate(records):
        entry = {
            "syllable": record["syllable"],
            "frequency": record["frequency"],
        }

        # Add coordinate fields (tsne_x, tsne_y, tsne_z, ...)
        coord_labels = ["tsne_x", "tsne_y", "tsne_z", "tsne_w"]  # Support up to 4D
        for dim in range(n_dimensions):
            label = coord_labels[dim] if dim < len(coord_labels) else f"tsne_dim{dim}"
            entry[label] = float(tsne_coords[i, dim])  # Convert numpy float to Python float

        # Add features
        entry["features"] = record["features"]

        mapping.append(entry)

    return mapping


def save_tsne_mapping(mapping: List[Dict], output_path: Path, indent: int = 2) -> None:
    """Save t-SNE mapping to JSON file.

    Writes the syllable→coordinates mapping as formatted JSON for human readability
    and programmatic access.

    Args:
        mapping: Mapping data from create_tsne_mapping()
        output_path: Output file path (should end in .json)
        indent: JSON indentation for readability (default: 2)

    Example:
        >>> from pathlib import Path
        >>> mapping = [{"syllable": "ka", "tsne_x": -2.1, "tsne_y": 3.4, "features": {...}}]
        >>> save_tsne_mapping(mapping, Path("output.json"))

    Notes:
        - Output is formatted with indentation for human readability
        - Uses ensure_ascii=False to preserve Unicode characters
        - UTF-8 encoding ensures international character support
        - Parent directories are created if they don't exist
    """
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save as formatted JSON
    output_path.write_text(json.dumps(mapping, indent=indent, ensure_ascii=False), encoding="utf-8")
