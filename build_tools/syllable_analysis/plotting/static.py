"""Static matplotlib visualizations for analysis tools.

This module provides matplotlib-based static plotting functions for dimensionality
reduction visualizations. Functions create publication-quality PNG outputs with
comprehensive metadata.

Usage Example
-------------
::

    import numpy as np
    from pathlib import Path
    from build_tools.syllable_analysis.plotting.static import (
        create_tsne_scatter,
        save_static_plot,
        create_metadata_text
    )

    # Create visualization
    tsne_coords = np.array([[...], [...]])  # From t-SNE
    frequencies = [10, 25, 15, ...]
    fig = create_tsne_scatter(tsne_coords, frequencies)

    # Save to PNG
    output_path = Path("_working/output.png")
    save_static_plot(fig, output_path, dpi=300)

    # Generate metadata
    metadata = create_metadata_text(
        output_filename="output.png",
        dpi=300,
        perplexity=30,
        random_state=42,
        processing_time=2.5
    )
    Path("_working/output_meta.txt").write_text(metadata)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt  # type: ignore[import-not-found]
import numpy as np  # type: ignore[import-not-found]

from .styles import (
    AXIS_LABEL_FONT_SIZE,
    DEFAULT_ALPHA,
    DEFAULT_COLORMAP,
    DEFAULT_DPI,
    DEFAULT_FIGURE_SIZE,
    DEFAULT_MARKER_LINE_COLOR,
    DEFAULT_MARKER_LINE_WIDTH,
    TITLE_FONT_SIZE,
)


def create_tsne_scatter(
    tsne_coords: np.ndarray,
    frequencies: list[int],
    title: str = "t-SNE: Feature Signature Space",
    figsize: tuple[int, int] = DEFAULT_FIGURE_SIZE,
    cmap: str = DEFAULT_COLORMAP,
    alpha: float = DEFAULT_ALPHA,
) -> plt.Figure:
    """Create static matplotlib scatter plot of t-SNE coordinates.

    Generates a publication-quality scatter plot showing t-SNE dimensionality
    reduction results. Points are sized and colored by frequency, with larger
    and brighter points indicating higher-frequency syllables.

    Args:
        tsne_coords: 2D coordinate array of shape (n_samples, 2) from t-SNE reduction
        frequencies: Frequency values for each point (used for sizing and coloring)
        title: Plot title (default: "t-SNE: Feature Signature Space")
        figsize: Figure size in inches as (width, height) (default: (14, 10))
        cmap: Matplotlib colormap name (default: "viridis")
        alpha: Point transparency, 0.0=transparent to 1.0=opaque (default: 0.6)

    Returns:
        matplotlib Figure object with configured scatter plot

    Raises:
        ValueError: If tsne_coords shape is invalid or lengths don't match

    Example:
        >>> import numpy as np
        >>> coords = np.random.randn(100, 2)
        >>> freqs = list(range(1, 101))
        >>> fig = create_tsne_scatter(coords, freqs)
        >>> fig.savefig("output.png", dpi=300)
        >>> plt.close(fig)

    Notes:
        - Point size is proportional to frequency (frequency × 2)
        - Colorbar is added automatically to show frequency scale
        - Black edge lines improve visibility of overlapping points
        - Layout uses tight_layout() for optimal spacing
    """
    # Validate inputs
    if tsne_coords.ndim != 2 or tsne_coords.shape[1] != 2:
        raise ValueError(
            f"tsne_coords must be 2D array with shape (n, 2), got shape {tsne_coords.shape}"
        )
    if len(frequencies) != tsne_coords.shape[0]:
        raise ValueError(
            f"frequencies length ({len(frequencies)}) must match "
            f"tsne_coords rows ({tsne_coords.shape[0]})"
        )

    # Create figure and axis
    fig, ax = plt.subplots(figsize=figsize)

    # Convert frequencies to numpy array for scaling
    freq_array = np.array(frequencies)

    # Create scatter plot
    # - Position: t-SNE coordinates
    # - Size: frequency × 2 (larger points for common syllables)
    # - Color: frequency (using specified colormap)
    # - Alpha: transparency to show overlapping points
    # - Edge: black outline for visibility
    scatter = ax.scatter(
        tsne_coords[:, 0],
        tsne_coords[:, 1],
        c=freq_array,
        s=freq_array * 2,  # Size proportional to frequency
        cmap=cmap,
        alpha=alpha,
        edgecolors=DEFAULT_MARKER_LINE_COLOR,
        linewidth=DEFAULT_MARKER_LINE_WIDTH,
    )

    # Configure plot appearance
    ax.set_title(
        f"{title}\n(Size and color = frequency)",
        fontsize=TITLE_FONT_SIZE,
        fontweight="bold",
    )
    ax.set_xlabel("t-SNE Dimension 1", fontsize=AXIS_LABEL_FONT_SIZE)
    ax.set_ylabel("t-SNE Dimension 2", fontsize=AXIS_LABEL_FONT_SIZE)

    # Add colorbar with proper title
    plt.colorbar(scatter, ax=ax, label="Frequency Count")

    plt.tight_layout()

    return fig


def save_static_plot(
    fig: plt.Figure,
    output_path: Path,
    dpi: int = DEFAULT_DPI,
) -> None:
    """Save matplotlib figure to PNG file.

    Saves a matplotlib Figure to a high-resolution PNG file suitable for
    publication or presentation. Uses tight bounding box to minimize whitespace.

    Args:
        fig: Matplotlib Figure object to save
        output_path: Output PNG file path (parent directory must exist)
        dpi: Resolution in dots per inch (default: 300 for publication quality)

    Raises:
        FileNotFoundError: If parent directory doesn't exist
        PermissionError: If file cannot be written
        ValueError: If output_path doesn't end with .png

    Example:
        >>> import matplotlib.pyplot as plt
        >>> from pathlib import Path
        >>> fig, ax = plt.subplots()
        >>> ax.plot([1, 2, 3], [1, 4, 9])
        >>> save_static_plot(fig, Path("output.png"), dpi=300)
        >>> plt.close(fig)

    Notes:
        - Uses bbox_inches='tight' to remove excess whitespace
        - Higher DPI values create larger files but better quality
        - Common DPI values: 150 (screen), 300 (print), 600 (high-quality print)
        - Figure is NOT automatically closed after saving
    """
    # Validate output path
    if not str(output_path).endswith(".png"):
        raise ValueError(f"output_path must end with .png, got: {output_path}")
    if not output_path.parent.exists():
        raise FileNotFoundError(f"Parent directory does not exist: {output_path.parent}")

    # Save figure with tight bounding box
    fig.savefig(str(output_path), dpi=dpi, bbox_inches="tight")


def create_metadata_text(
    output_filename: str,
    dpi: int,
    perplexity: int,
    random_state: int,
    processing_time: float,
) -> str:
    """Generate formatted metadata text for static visualization.

    Creates a human-readable metadata report describing the visualization
    parameters, algorithm settings, and interpretation guide. Suitable for
    saving alongside PNG output files.

    Args:
        output_filename: Name of the output PNG file (e.g., "20260107_143022.tsne_visualization.png")
        dpi: Resolution used for PNG export
        perplexity: t-SNE perplexity parameter used
        random_state: Random seed used for reproducibility
        processing_time: Total processing time in seconds

    Returns:
        Formatted multi-line metadata string ready for file output

    Example:
        >>> metadata = create_metadata_text(
        ...     output_filename="20260107_143022.tsne_visualization.png",
        ...     dpi=300,
        ...     perplexity=30,
        ...     random_state=42,
        ...     processing_time=2.5
        ... )
        >>> Path("metadata.txt").write_text(metadata)

    Notes:
        - Includes timestamp of generation
        - Documents all algorithm parameters
        - Provides interpretation guidance
        - Uses Unicode box-drawing characters for formatting
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    metadata_lines = [
        "t-SNE VISUALIZATION METADATA",
        "=" * 60,
        f"Generated: {timestamp}",
        f"Output file: {output_filename}",
        f"Resolution: {dpi} DPI",
        f"Processing time: {processing_time:.2f} seconds",
        "",
        "ALGORITHM PARAMETERS",
        "-" * 60,
        "Method: t-SNE (t-distributed Stochastic Neighbor Embedding)",
        f"Perplexity: {perplexity}",
        f"Random state: {random_state}",
        "Distance metric: Hamming (optimal for binary features)",
        "Dimensions: 2D projection of 12-dimensional binary feature space",
        "Features: 12 phonetic features (onset, internal, nucleus, coda)",
        "",
        "VISUALIZATION ENCODING",
        "-" * 60,
        "X-axis: t-SNE Dimension 1",
        "Y-axis: t-SNE Dimension 2",
        "Point size: Proportional to syllable frequency",
        "Point color: Syllable frequency (viridis colormap)",
        "Edge color: Black outline for visibility",
        "",
        "INTERPRETATION GUIDE",
        "-" * 60,
        "- Nearby points: Similar phonetic feature patterns",
        "- Clusters: Natural groupings in feature space",
        "- Large/bright points: High-frequency syllables",
        "- Small/dark points: Low-frequency syllables",
        "- Isolated points: Unique or rare feature combinations",
        "",
        "=" * 60,
    ]

    return "\n".join(metadata_lines)
