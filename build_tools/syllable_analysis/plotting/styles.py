"""Shared styling constants for analysis visualizations.

This module provides consistent styling defaults for both static (matplotlib)
and interactive (Plotly) visualizations across all analysis tools.

Usage Example
-------------
::

    from build_tools.syllable_analysis.plotting.styles import (
        DEFAULT_COLORMAP,
        DEFAULT_FIGURE_SIZE,
        DEFAULT_DPI
    )

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=DEFAULT_FIGURE_SIZE)
    scatter = ax.scatter(x, y, cmap=DEFAULT_COLORMAP)
    fig.savefig("output.png", dpi=DEFAULT_DPI)

Constants
---------
Color Schemes
    DEFAULT_COLORMAP : str
        Matplotlib colormap name (default: "viridis")
    DEFAULT_COLORSCALE : str
        Plotly colorscale name (default: "Viridis")

Layout Dimensions
    DEFAULT_FIGURE_SIZE : tuple[int, int]
        Matplotlib figure size in inches (width, height)
    DEFAULT_PLOT_HEIGHT : int
        Plotly plot height in pixels
    DEFAULT_PLOT_MIN_WIDTH : int
        Minimum width for responsive plots in pixels

Visual Properties
    DEFAULT_ALPHA : float
        Point transparency (0.0-1.0)
    DEFAULT_MARKER_LINE_WIDTH : float
        Marker edge line width
    DEFAULT_MARKER_LINE_COLOR : str
        Marker edge line color

Export Settings
    DEFAULT_DPI : int
        Static plot resolution in dots per inch
    DEFAULT_EXPORT_WIDTH : int
        Interactive plot export width in pixels
    DEFAULT_EXPORT_HEIGHT : int
        Interactive plot export height in pixels
    DEFAULT_EXPORT_SCALE : int
        Interactive plot export scale multiplier

Font Settings
    TITLE_FONT_SIZE : int
        Static plot title font size in points
    AXIS_LABEL_FONT_SIZE : int
        Static plot axis label font size in points
    INTERACTIVE_TITLE_FONT_SIZE : int
        Interactive plot title font size in pixels
"""

# Color schemes
DEFAULT_COLORMAP = "viridis"
DEFAULT_COLORSCALE = "Viridis"

# Layout dimensions
DEFAULT_FIGURE_SIZE = (14, 10)
DEFAULT_PLOT_HEIGHT = 900
DEFAULT_PLOT_MIN_WIDTH = 1250

# Visual properties
DEFAULT_ALPHA = 0.6
DEFAULT_MARKER_LINE_WIDTH = 0.5
DEFAULT_MARKER_LINE_COLOR = "black"

# Export settings
DEFAULT_DPI = 300
DEFAULT_EXPORT_WIDTH = 1600
DEFAULT_EXPORT_HEIGHT = 1200
DEFAULT_EXPORT_SCALE = 2

# Font settings
TITLE_FONT_SIZE = 16
AXIS_LABEL_FONT_SIZE = 12
INTERACTIVE_TITLE_FONT_SIZE = 20
