"""Interactive Plotly visualizations for analysis tools.

This module provides Plotly-based interactive plotting functions for dimensionality
reduction visualizations. Functions create standalone HTML files with zoom, pan,
hover, and export capabilities.

Plotly is an optional dependency. If not installed, functions will raise ImportError
with installation instructions.

Usage Example
-------------
::

    import numpy as np
    from pathlib import Path
    from build_tools.syllable_analysis.plotting.interactive import (
        create_interactive_scatter,
        save_interactive_html,
        PLOTLY_AVAILABLE
    )

    if not PLOTLY_AVAILABLE:
        print("Plotly not installed - skipping interactive visualization")
    else:
        # Create visualization
        records = [
            {"syllable": "ka", "frequency": 100, "features": {...}},
            ...
        ]
        tsne_coords = np.array([[...], [...]])
        fig = create_interactive_scatter(records, tsne_coords)

        # Save to HTML
        output_path = Path("_working/output.html")
        save_interactive_html(fig, output_path, perplexity=30, random_state=42)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np  # type: ignore[import-not-found]

from .styles import (
    DEFAULT_COLORSCALE,
    DEFAULT_EXPORT_HEIGHT,
    DEFAULT_EXPORT_SCALE,
    DEFAULT_EXPORT_WIDTH,
    DEFAULT_MARKER_LINE_WIDTH,
    DEFAULT_PLOT_HEIGHT,
    DEFAULT_PLOT_MIN_WIDTH,
    INTERACTIVE_TITLE_FONT_SIZE,
)

# Try to import Plotly - this is an optional dependency
try:
    import plotly.graph_objects as go  # type: ignore[import-not-found]

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None  # type: ignore[assignment]


def create_interactive_scatter(
    records: list[dict],
    tsne_coords: np.ndarray,
    title: str = "t-SNE: Feature Signature Space (Interactive)",
) -> "go.Figure":
    """Create interactive Plotly scatter plot of t-SNE coordinates.

    Generates an interactive HTML-compatible visualization with rich hover tooltips,
    zoom/pan controls, and export capabilities. Points are sized (log scale) and
    colored by frequency.

    Args:
        records: List of annotated syllable records. Each must contain:
            - syllable (str): Syllable text
            - frequency (int): Occurrence count
            - features (dict): Boolean feature flags (12 features)
        tsne_coords: 2D coordinate array of shape (n_samples, 2) from t-SNE
        title: Plot title (default: "t-SNE: Feature Signature Space (Interactive)")

    Returns:
        Plotly Figure object with configured interactive scatter plot

    Raises:
        ImportError: If Plotly is not installed
        ValueError: If inputs are invalid or lengths don't match

    Example:
        >>> records = [
        ...     {"syllable": "ka", "frequency": 100, "features": {"contains_plosive": True}},
        ...     {"syllable": "mi", "frequency": 50, "features": {"contains_nasal": True}},
        ... ]
        >>> coords = np.array([[1.0, 2.0], [3.0, 4.0]])
        >>> fig = create_interactive_scatter(records, coords)
        >>> fig.show()  # Opens in browser

    Notes:
        - Point size uses log1p scale for better visibility across frequency ranges
        - Hover text shows syllable, frequency, feature count, and up to 4 features
        - If more than 4 features, shows "...+N more" truncation
        - Viridis colorscale provides perceptually uniform coloring
        - Fixed height (900px) with responsive width for consistent aspect ratio
        - Plotly CDN used when saving to HTML for smaller file size
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError(
            "Plotly is required for interactive visualization. " "Install with: pip install plotly"
        )

    # Validate inputs
    if tsne_coords.ndim != 2 or tsne_coords.shape[1] != 2:
        raise ValueError(
            f"tsne_coords must be 2D array with shape (n, 2), got shape {tsne_coords.shape}"
        )
    if len(records) != tsne_coords.shape[0]:
        raise ValueError(
            f"records length ({len(records)}) must match "
            f"tsne_coords rows ({tsne_coords.shape[0]})"
        )

    # Extract data for visualization
    syllables = [r["syllable"] for r in records]
    frequencies = np.array([r["frequency"] for r in records])

    # Build rich hover text with syllable details
    hover_texts = []
    for record in records:
        hover_text = build_hover_text(record, max_features=4)
        hover_texts.append(hover_text)

    # Create figure with main scatter trace
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=tsne_coords[:, 0],
            y=tsne_coords[:, 1],
            mode="markers",
            marker=dict(
                size=np.log1p(frequencies) * 3,  # Log scale for better visibility
                color=frequencies,
                colorscale=DEFAULT_COLORSCALE,
                showscale=True,
                colorbar=dict(
                    title=dict(text="Frequency", side="right"),
                    len=0.75,
                    thickness=15,
                    xpad=10,
                ),
                line=dict(width=DEFAULT_MARKER_LINE_WIDTH, color="black"),
                opacity=0.7,
            ),
            text=syllables,
            hovertext=hover_texts,
            hoverinfo="text",
            customdata=[[i] for i in range(len(records))],  # Store index for future use
            name="Syllables",
        )
    )

    # Configure layout for optimal viewing with responsive sizing
    fig.update_layout(
        title={
            "text": title,
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": INTERACTIVE_TITLE_FONT_SIZE, "family": "Arial, sans-serif"},
        },
        xaxis_title="t-SNE Dimension 1",
        yaxis_title="t-SNE Dimension 2",
        hovermode="closest",
        autosize=True,  # Enable responsive sizing
        height=DEFAULT_PLOT_HEIGHT,
        template="plotly_white",
        showlegend=True,
    )

    return fig


def build_hover_text(record: dict, max_features: int = 4) -> str:
    """Build rich hover text for a single syllable record.

    Creates HTML-formatted hover text showing syllable details, frequency,
    and active features. Features are truncated if more than max_features
    are present.

    Args:
        record: Syllable record with 'syllable', 'frequency', 'features' keys
        max_features: Maximum features to show before truncating (default: 4)

    Returns:
        HTML-formatted hover text string

    Example:
        >>> record = {
        ...     "syllable": "kran",
        ...     "frequency": 150,
        ...     "features": {
        ...         "contains_plosive": True,
        ...         "contains_liquid": True,
        ...         "contains_nasal": True,
        ...         "starts_with_cluster": True,
        ...         "ends_with_nasal": True,
        ...     }
        ... }
        >>> text = build_hover_text(record, max_features=4)
        >>> print(text)
        <b>kran</b><br>Frequency: 150<br>Features: 5/12<br><i>contains_plosive, ...</i><br>...

    Notes:
        - Syllable shown in bold
        - Frequency shown with comma separators (e.g., "1,234")
        - Feature count shows active/total (e.g., "5/12")
        - First N features shown in italics
        - If more than N features, shows "+M more" truncation message
    """
    active_features = [feat for feat, val in record["features"].items() if val]
    hover_text = (
        f"<b>{record['syllable']}</b><br>"
        f"Frequency: {record['frequency']:,}<br>"
        f"Features: {len(active_features)}/12<br>"
        f"<i>{', '.join(active_features[:max_features])}</i>"
    )
    if len(active_features) > max_features:
        hover_text += f"<br><i>... +{len(active_features) - max_features} more</i>"
    return hover_text


def save_interactive_html(
    fig: "go.Figure",
    output_path: Path,
    perplexity: int,
    random_state: int,
    min_width: int = DEFAULT_PLOT_MIN_WIDTH,
) -> None:
    """Save interactive Plotly figure as standalone HTML.

    Creates a self-contained HTML file with embedded Plotly visualization that can be:
    - Opened directly in any web browser
    - Shared with collaborators
    - Embedded in reports or documentation
    - Explored with zoom, pan, hover, and export controls

    The HTML file uses Plotly CDN for JavaScript dependencies (smaller file size)
    and includes responsive CSS and a metadata footer.

    Args:
        fig: Plotly Figure object from create_interactive_scatter()
        output_path: Output HTML file path (parent directory must exist)
        perplexity: t-SNE perplexity parameter (for metadata footer)
        random_state: Random seed used (for metadata footer)
        min_width: Minimum width constraint in pixels (default: 1250)

    Raises:
        ImportError: If Plotly is not installed
        FileNotFoundError: If parent directory doesn't exist
        ValueError: If output_path doesn't end with .html

    Example:
        >>> fig = create_interactive_scatter(records, tsne_coords)
        >>> output_path = Path("_working/visualization.html")
        >>> save_interactive_html(fig, output_path, perplexity=30, random_state=42)

    Notes:
        - Plotly CDN used for smaller file size vs. full JS bundle
        - Mode bar configured with additional tools (hoverclosest, hovercompare)
        - Export to PNG button configured for high-resolution (1600x1200, 2x scale)
        - Responsive CSS ensures minimum width of 1250px
        - Metadata footer includes algorithm parameters and generation time
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("Plotly is required for interactive visualization.")

    # Validate output path
    if not str(output_path).endswith(".html"):
        raise ValueError(f"output_path must end with .html, got: {output_path}")
    if not output_path.parent.exists():
        raise FileNotFoundError(f"Parent directory does not exist: {output_path.parent}")

    # Extract timestamp from filename or generate new one
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save as standalone HTML with configuration
    fig.write_html(
        str(output_path),
        include_plotlyjs="cdn",  # Use CDN for smaller file size
        config={
            "displayModeBar": True,
            "displaylogo": False,
            "modeBarButtonsToAdd": ["hoverclosest", "hovercompare"],
            "toImageButtonOptions": {
                "format": "png",
                "filename": f"tsne_interactive_{timestamp}",
                "height": DEFAULT_EXPORT_HEIGHT,
                "width": DEFAULT_EXPORT_WIDTH,
                "scale": DEFAULT_EXPORT_SCALE,
            },
        },
    )

    # Inject responsive CSS
    html_content = output_path.read_text(encoding="utf-8")
    html_content = inject_responsive_css(html_content, min_width=min_width)
    output_path.write_text(html_content, encoding="utf-8")

    # Append metadata footer to HTML
    metadata_html = create_metadata_footer(perplexity, random_state)
    with output_path.open("a", encoding="utf-8") as f:
        f.write(metadata_html)


def inject_responsive_css(
    html_content: str,
    min_width: int = DEFAULT_PLOT_MIN_WIDTH,
) -> str:
    """Inject responsive CSS into HTML content.

    Adds CSS rules to ensure the plot has a minimum width and proper scrolling
    behavior. This prevents the plot from becoming too narrow on small screens
    while allowing horizontal scrolling when necessary.

    Args:
        html_content: Original HTML content from Plotly
        min_width: Minimum width constraint in pixels (default: 1250)

    Returns:
        HTML content with injected CSS in <head> section

    Example:
        >>> html = "<html><head></head><body>...</body></html>"
        >>> modified = inject_responsive_css(html, min_width=1250)
        >>> "<style>" in modified
        True

    Notes:
        - CSS is inserted after the opening <head> tag
        - Sets body margin/padding to 0 for full-width layout
        - Enables horizontal scrolling when plot exceeds viewport width
        - Sets fixed height (900px) matching plot configuration
        - Uses !important to override Plotly's inline styles
    """
    responsive_css = f"""
<style>
    body {{
        margin: 0;
        padding: 0;
        overflow-x: auto;
    }}
    .plotly-graph-div {{
        min-width: {min_width}px !important;
        width: 100% !important;
        height: {DEFAULT_PLOT_HEIGHT}px !important;
    }}
</style>
"""

    # Insert CSS after <head> tag
    html_content = html_content.replace("<head>", f"<head>\n{responsive_css}")

    return html_content


def create_metadata_footer(perplexity: int, random_state: int) -> str:
    """Create HTML metadata footer with algorithm parameters.

    Generates a styled HTML block showing t-SNE parameters and generation
    information. Designed to be appended to the end of the HTML file.

    Args:
        perplexity: t-SNE perplexity parameter used
        random_state: Random seed used for reproducibility

    Returns:
        HTML string with formatted metadata table

    Example:
        >>> footer = create_metadata_footer(perplexity=30, random_state=42)
        >>> "t-SNE Visualization Parameters" in footer
        True

    Notes:
        - Uses inline CSS for styling (no external dependencies)
        - Light gray background (#f5f5f5) for visual separation
        - Monospace font for technical parameters
        - Includes usage instructions for toolbar
        - Shows current timestamp of generation
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    metadata_html = f"""
<!-- t-SNE Visualization Metadata -->
<div style="margin: 20px; padding: 15px; background-color: #f5f5f5;
            border-radius: 8px; font-family: 'Courier New', monospace; font-size: 13px;
            border: 1px solid #ddd;">
    <div style="font-weight: bold; font-size: 14px; margin-bottom: 10px; color: #333;">
        t-SNE Visualization Parameters
    </div>
    <table style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 4px; color: #666;">Algorithm:</td>
            <td style="padding: 4px; color: #000;">t-SNE (t-distributed Stochastic Neighbor Embedding)</td>
        </tr>
        <tr>
            <td style="padding: 4px; color: #666;">Perplexity:</td>
            <td style="padding: 4px; color: #000;">{perplexity}</td>
        </tr>
        <tr>
            <td style="padding: 4px; color: #666;">Random State:</td>
            <td style="padding: 4px; color: #000;">{random_state}</td>
        </tr>
        <tr>
            <td style="padding: 4px; color: #666;">Distance Metric:</td>
            <td style="padding: 4px; color: #000;">Hamming (optimal for binary features)</td>
        </tr>
        <tr>
            <td style="padding: 4px; color: #666;">Generated:</td>
            <td style="padding: 4px; color: #000;">{timestamp}</td>
        </tr>
    </table>
    <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 11px; color: #777;">
        <b>Usage:</b> Hover over points to see syllable details. Use toolbar for zoom, pan, and export.
    </div>
</div>
"""

    return metadata_html
