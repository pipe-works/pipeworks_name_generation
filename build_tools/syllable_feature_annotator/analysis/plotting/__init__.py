"""Plotting utilities for analysis visualizations.

This subpackage provides both static (matplotlib) and interactive (Plotly)
visualization functions for dimensionality reduction and feature analysis.

Modules
-------
styles
    Shared styling constants for consistent visualization appearance
static
    Matplotlib-based static plotting for publication-quality PNG outputs
interactive
    Plotly-based interactive plotting for exploratory HTML visualizations

Usage Example
-------------
Static Visualization::

    from build_tools.syllable_feature_annotator.analysis.plotting import (
        create_tsne_scatter,
        save_static_plot
    )

    fig = create_tsne_scatter(tsne_coords, frequencies)
    save_static_plot(fig, Path("output.png"), dpi=300)

Interactive Visualization::

    from build_tools.syllable_feature_annotator.analysis.plotting import (
        PLOTLY_AVAILABLE,
        create_interactive_scatter,
        save_interactive_html
    )

    if PLOTLY_AVAILABLE:
        fig = create_interactive_scatter(records, tsne_coords)
        save_interactive_html(fig, Path("output.html"), perplexity=30, random_state=42)
    else:
        print("Plotly not installed - skipping interactive visualization")

Notes
-----
- Matplotlib is always available (required dependency for static plots)
- Plotly is optional (check PLOTLY_AVAILABLE before using interactive functions)
- All styling constants can be imported from the styles module or this package
"""

# Style constants
# Interactive plotting (Plotly - optional)
from .interactive import PLOTLY_AVAILABLE

# Static plotting (matplotlib - always available)
from .static import create_metadata_text, create_tsne_scatter, save_static_plot
from .styles import (
    AXIS_LABEL_FONT_SIZE,
    DEFAULT_ALPHA,
    DEFAULT_COLORMAP,
    DEFAULT_COLORSCALE,
    DEFAULT_DPI,
    DEFAULT_EXPORT_HEIGHT,
    DEFAULT_EXPORT_SCALE,
    DEFAULT_EXPORT_WIDTH,
    DEFAULT_FIGURE_SIZE,
    DEFAULT_MARKER_LINE_COLOR,
    DEFAULT_MARKER_LINE_WIDTH,
    DEFAULT_PLOT_HEIGHT,
    DEFAULT_PLOT_MIN_WIDTH,
    INTERACTIVE_TITLE_FONT_SIZE,
    TITLE_FONT_SIZE,
)

# Conditionally import Plotly functions if available
if PLOTLY_AVAILABLE:
    from .interactive import (
        build_hover_text,
        create_interactive_scatter,
        create_metadata_footer,
        inject_responsive_css,
        save_interactive_html,
    )

    __all__ = [
        # Style constants
        "DEFAULT_COLORMAP",
        "DEFAULT_COLORSCALE",
        "DEFAULT_FIGURE_SIZE",
        "DEFAULT_PLOT_HEIGHT",
        "DEFAULT_PLOT_MIN_WIDTH",
        "DEFAULT_ALPHA",
        "DEFAULT_MARKER_LINE_WIDTH",
        "DEFAULT_MARKER_LINE_COLOR",
        "DEFAULT_DPI",
        "DEFAULT_EXPORT_WIDTH",
        "DEFAULT_EXPORT_HEIGHT",
        "DEFAULT_EXPORT_SCALE",
        "TITLE_FONT_SIZE",
        "AXIS_LABEL_FONT_SIZE",
        "INTERACTIVE_TITLE_FONT_SIZE",
        # Static plotting
        "create_tsne_scatter",
        "save_static_plot",
        "create_metadata_text",
        # Interactive plotting
        "PLOTLY_AVAILABLE",
        "create_interactive_scatter",
        "build_hover_text",
        "save_interactive_html",
        "inject_responsive_css",
        "create_metadata_footer",
    ]
else:
    # Plotly not available - only export static functions
    __all__ = [
        # Style constants
        "DEFAULT_COLORMAP",
        "DEFAULT_COLORSCALE",
        "DEFAULT_FIGURE_SIZE",
        "DEFAULT_PLOT_HEIGHT",
        "DEFAULT_PLOT_MIN_WIDTH",
        "DEFAULT_ALPHA",
        "DEFAULT_MARKER_LINE_WIDTH",
        "DEFAULT_MARKER_LINE_COLOR",
        "DEFAULT_DPI",
        "DEFAULT_EXPORT_WIDTH",
        "DEFAULT_EXPORT_HEIGHT",
        "DEFAULT_EXPORT_SCALE",
        "TITLE_FONT_SIZE",
        "AXIS_LABEL_FONT_SIZE",
        "INTERACTIVE_TITLE_FONT_SIZE",
        # Static plotting
        "create_tsne_scatter",
        "save_static_plot",
        "create_metadata_text",
        # Plotly availability flag
        "PLOTLY_AVAILABLE",
    ]
