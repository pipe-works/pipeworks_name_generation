"""Tests for plotting modules (static and interactive visualizations).

Tests cover:
- Style constants validation
- Static matplotlib plotting functions
- Interactive Plotly plotting functions (conditional)
- HTML generation and manipulation
- Metadata generation
- Error handling and validation
"""

# mypy: ignore-errors

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

# Import plotting modules
from build_tools.syllable_analysis.plotting import (
    PLOTLY_AVAILABLE,
    create_metadata_text,
    create_tsne_scatter,
    save_static_plot,
)
from build_tools.syllable_analysis.plotting.styles import (
    DEFAULT_ALPHA,
    DEFAULT_COLORMAP,
    DEFAULT_DPI,
    DEFAULT_FIGURE_SIZE,
)

# Conditional imports for Plotly
if PLOTLY_AVAILABLE:
    from build_tools.syllable_analysis.plotting import (
        build_hover_text,
        create_interactive_scatter,
        create_metadata_footer,
        inject_responsive_css,
        save_interactive_html,
    )


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_tsne_coords():
    """Sample t-SNE coordinates for testing."""
    return np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [-1.0, -2.0], [-3.0, -4.0]])


@pytest.fixture
def sample_frequencies():
    """Sample frequency values for testing."""
    return [10, 25, 15, 50, 5]


@pytest.fixture
def sample_records():
    """Sample annotated syllable records for testing."""
    return [
        {
            "syllable": "ka",
            "frequency": 100,
            "features": {
                "contains_plosive": True,
                "contains_liquid": False,
                "starts_with_vowel": False,
                "ends_with_vowel": True,
            },
        },
        {
            "syllable": "mi",
            "frequency": 50,
            "features": {
                "contains_nasal": True,
                "short_vowel": True,
                "starts_with_vowel": False,
                "ends_with_vowel": True,
            },
        },
        {
            "syllable": "kran",
            "frequency": 25,
            "features": {
                "contains_plosive": True,
                "contains_liquid": True,
                "contains_nasal": True,
                "starts_with_cluster": True,
                "ends_with_nasal": True,
            },
        },
    ]


@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary output directory for test files."""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir()
    return output_dir


# ============================================================================
# Tests: Style Constants
# ============================================================================


class TestStyleConstants:
    """Tests for style constants validation."""

    def test_colormap_is_valid(self):
        """Test that default colormap is valid."""
        assert DEFAULT_COLORMAP in plt.colormaps()

    def test_figure_size_is_tuple(self):
        """Test that figure size is a tuple of two numbers."""
        assert isinstance(DEFAULT_FIGURE_SIZE, tuple)
        assert len(DEFAULT_FIGURE_SIZE) == 2
        assert all(isinstance(x, (int, float)) for x in DEFAULT_FIGURE_SIZE)

    def test_alpha_in_valid_range(self):
        """Test that alpha is between 0 and 1."""
        assert 0.0 <= DEFAULT_ALPHA <= 1.0

    def test_dpi_is_positive(self):
        """Test that DPI is a positive integer."""
        assert isinstance(DEFAULT_DPI, int)
        assert DEFAULT_DPI > 0


# ============================================================================
# Tests: Static Plotting (create_tsne_scatter)
# ============================================================================


class TestCreateTsneScatter:
    """Tests for create_tsne_scatter function."""

    def test_creates_figure(self, sample_tsne_coords, sample_frequencies):
        """Test that function creates a matplotlib Figure."""
        fig = create_tsne_scatter(sample_tsne_coords, sample_frequencies)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_figure_has_scatter_plot(self, sample_tsne_coords, sample_frequencies):
        """Test that figure contains a scatter plot."""
        fig = create_tsne_scatter(sample_tsne_coords, sample_frequencies)
        ax = fig.axes[0]
        # Check that there's at least one PathCollection (scatter plot)
        assert any(
            isinstance(child, matplotlib.collections.PathCollection) for child in ax.get_children()
        )
        plt.close(fig)

    def test_custom_title(self, sample_tsne_coords, sample_frequencies):
        """Test that custom title is applied."""
        custom_title = "Custom Test Title"
        fig = create_tsne_scatter(sample_tsne_coords, sample_frequencies, title=custom_title)
        ax = fig.axes[0]
        assert custom_title in ax.get_title()
        plt.close(fig)

    def test_custom_figsize(self, sample_tsne_coords, sample_frequencies):
        """Test that custom figure size is applied."""
        custom_size = (10, 8)
        fig = create_tsne_scatter(sample_tsne_coords, sample_frequencies, figsize=custom_size)
        # Figure size in inches
        assert fig.get_size_inches()[0] == pytest.approx(custom_size[0], rel=0.1)
        assert fig.get_size_inches()[1] == pytest.approx(custom_size[1], rel=0.1)
        plt.close(fig)

    def test_invalid_coords_shape_raises_error(self, sample_frequencies):
        """Test that invalid coordinate shape raises ValueError."""
        invalid_coords = np.array([1, 2, 3, 4, 5])  # 1D array
        with pytest.raises(ValueError, match="must be 2D array"):
            create_tsne_scatter(invalid_coords, sample_frequencies)

    def test_mismatched_lengths_raises_error(self, sample_tsne_coords):
        """Test that mismatched frequencies length raises ValueError."""
        wrong_frequencies = [10, 20]  # Too short
        with pytest.raises(ValueError, match="frequencies length.*must match"):
            create_tsne_scatter(sample_tsne_coords, wrong_frequencies)

    def test_empty_coordinates(self):
        """Test handling of empty coordinate array."""
        empty_coords = np.empty((0, 2))
        empty_freqs: list[int] = []
        fig = create_tsne_scatter(empty_coords, empty_freqs)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


# ============================================================================
# Tests: Static Plotting (save_static_plot)
# ============================================================================


class TestSaveStaticPlot:
    """Tests for save_static_plot function."""

    def test_saves_png_file(self, temp_output_dir, sample_tsne_coords, sample_frequencies):
        """Test that function saves PNG file."""
        fig = create_tsne_scatter(sample_tsne_coords, sample_frequencies)
        output_path = temp_output_dir / "test.png"
        save_static_plot(fig, output_path, dpi=150)
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        plt.close(fig)

    def test_custom_dpi(self, temp_output_dir, sample_tsne_coords, sample_frequencies):
        """Test that custom DPI is applied."""
        fig = create_tsne_scatter(sample_tsne_coords, sample_frequencies)
        output_path = temp_output_dir / "test_dpi.png"
        save_static_plot(fig, output_path, dpi=100)
        assert output_path.exists()
        plt.close(fig)

    def test_invalid_extension_raises_error(
        self, temp_output_dir, sample_tsne_coords, sample_frequencies
    ):
        """Test that non-PNG extension raises ValueError."""
        fig = create_tsne_scatter(sample_tsne_coords, sample_frequencies)
        output_path = temp_output_dir / "test.jpg"
        with pytest.raises(ValueError, match="must end with .png"):
            save_static_plot(fig, output_path)
        plt.close(fig)

    def test_missing_parent_dir_raises_error(self, sample_tsne_coords, sample_frequencies):
        """Test that missing parent directory raises FileNotFoundError."""
        fig = create_tsne_scatter(sample_tsne_coords, sample_frequencies)
        output_path = Path("/nonexistent/directory/test.png")
        with pytest.raises(FileNotFoundError, match="Parent directory does not exist"):
            save_static_plot(fig, output_path)
        plt.close(fig)


# ============================================================================
# Tests: Static Plotting (create_metadata_text)
# ============================================================================


class TestCreateMetadataText:
    """Tests for create_metadata_text function."""

    def test_returns_string(self):
        """Test that function returns a string."""
        metadata = create_metadata_text(
            output_filename="test.png", dpi=300, perplexity=30, random_state=42, processing_time=2.5
        )
        assert isinstance(metadata, str)

    def test_includes_filename(self):
        """Test that metadata includes filename."""
        metadata = create_metadata_text(
            output_filename="test.png", dpi=300, perplexity=30, random_state=42, processing_time=2.5
        )
        assert "test.png" in metadata

    def test_includes_parameters(self):
        """Test that metadata includes algorithm parameters."""
        metadata = create_metadata_text(
            output_filename="test.png", dpi=300, perplexity=30, random_state=42, processing_time=2.5
        )
        assert "Perplexity: 30" in metadata
        assert "Random state: 42" in metadata
        assert "300 DPI" in metadata

    def test_includes_processing_time(self):
        """Test that metadata includes processing time."""
        metadata = create_metadata_text(
            output_filename="test.png", dpi=300, perplexity=30, random_state=42, processing_time=2.5
        )
        assert "2.50 seconds" in metadata

    def test_includes_interpretation_guide(self):
        """Test that metadata includes interpretation guidance."""
        metadata = create_metadata_text(
            output_filename="test.png", dpi=300, perplexity=30, random_state=42, processing_time=2.5
        )
        assert "INTERPRETATION GUIDE" in metadata
        assert "Nearby points" in metadata


# ============================================================================
# Tests: Interactive Plotting (build_hover_text) - Conditional
# ============================================================================


@pytest.mark.skipif(not PLOTLY_AVAILABLE, reason="Plotly not installed")
class TestBuildHoverText:
    """Tests for build_hover_text function."""

    def test_basic_hover_text(self, sample_records):
        """Test basic hover text generation."""
        hover_text = build_hover_text(sample_records[0], max_features=4)
        assert "<b>ka</b>" in hover_text
        assert "Frequency: 100" in hover_text

    def test_feature_truncation(self, sample_records):
        """Test that features are truncated when exceeding max_features."""
        record = sample_records[2]  # Has 5 features
        hover_text = build_hover_text(record, max_features=2)
        assert "+3 more" in hover_text

    def test_no_truncation_when_under_limit(self, sample_records):
        """Test that no truncation occurs when features <= max_features."""
        record = sample_records[0]  # Has 2 active features
        hover_text = build_hover_text(record, max_features=4)
        assert "+0 more" not in hover_text
        assert "more</i>" not in hover_text


# ============================================================================
# Tests: Interactive Plotting (create_interactive_scatter) - Conditional
# ============================================================================


@pytest.mark.skipif(not PLOTLY_AVAILABLE, reason="Plotly not installed")
class TestCreateInteractiveScatter:
    """Tests for create_interactive_scatter function."""

    def test_creates_plotly_figure(self, sample_records, sample_tsne_coords):
        """Test that function creates a Plotly Figure."""
        import plotly.graph_objects as go

        fig = create_interactive_scatter(sample_records, sample_tsne_coords[:3])
        assert isinstance(fig, go.Figure)

    def test_custom_title(self, sample_records, sample_tsne_coords):
        """Test that custom title is applied."""
        custom_title = "Custom Interactive Title"
        fig = create_interactive_scatter(sample_records, sample_tsne_coords[:3], title=custom_title)
        assert fig.layout.title.text == custom_title

    def test_invalid_coords_shape_raises_error(self, sample_records):
        """Test that invalid coordinate shape raises ValueError."""
        invalid_coords = np.array([1, 2, 3])  # 1D array
        with pytest.raises(ValueError, match="must be 2D array"):
            create_interactive_scatter(sample_records, invalid_coords)

    def test_mismatched_lengths_raises_error(self, sample_records, sample_tsne_coords):
        """Test that mismatched records length raises ValueError."""
        with pytest.raises(ValueError, match="records length.*must match"):
            create_interactive_scatter(
                sample_records[:2], sample_tsne_coords
            )  # 2 records, 5 coords


# ============================================================================
# Tests: Interactive Plotting (inject_responsive_css) - Conditional
# ============================================================================


@pytest.mark.skipif(not PLOTLY_AVAILABLE, reason="Plotly not installed")
class TestInjectResponsiveCSS:
    """Tests for inject_responsive_css function."""

    def test_injects_css_after_head(self):
        """Test that CSS is injected after <head> tag."""
        html = "<html><head></head><body></body></html>"
        result = inject_responsive_css(html, min_width=1250)
        assert "<style>" in result
        assert "min-width: 1250px" in result

    def test_custom_min_width(self):
        """Test that custom min_width is applied."""
        html = "<html><head></head><body></body></html>"
        result = inject_responsive_css(html, min_width=800)
        assert "min-width: 800px" in result

    def test_preserves_existing_content(self):
        """Test that existing HTML content is preserved."""
        html = "<html><head><title>Test</title></head><body><p>Content</p></body></html>"
        result = inject_responsive_css(html)
        assert "<title>Test</title>" in result
        assert "<p>Content</p>" in result


# ============================================================================
# Tests: Interactive Plotting (create_metadata_footer) - Conditional
# ============================================================================


@pytest.mark.skipif(not PLOTLY_AVAILABLE, reason="Plotly not installed")
class TestCreateMetadataFooter:
    """Tests for create_metadata_footer function."""

    def test_returns_html_string(self):
        """Test that function returns HTML string."""
        footer = create_metadata_footer(perplexity=30, random_state=42)
        assert isinstance(footer, str)
        assert "<div" in footer

    def test_includes_parameters(self):
        """Test that footer includes algorithm parameters."""
        footer = create_metadata_footer(perplexity=30, random_state=42)
        assert "Perplexity" in footer
        assert "30" in footer
        assert "Random State" in footer
        assert "42" in footer

    def test_includes_usage_instructions(self):
        """Test that footer includes usage instructions."""
        footer = create_metadata_footer(perplexity=30, random_state=42)
        assert "Usage:" in footer
        assert "Hover" in footer


# ============================================================================
# Tests: Interactive Plotting (save_interactive_html) - Conditional
# ============================================================================


@pytest.mark.skipif(not PLOTLY_AVAILABLE, reason="Plotly not installed")
class TestSaveInteractiveHtml:
    """Tests for save_interactive_html function."""

    def test_saves_html_file(self, temp_output_dir, sample_records, sample_tsne_coords):
        """Test that function saves HTML file."""
        fig = create_interactive_scatter(sample_records, sample_tsne_coords[:3])
        output_path = temp_output_dir / "test.html"
        save_interactive_html(fig, output_path, perplexity=30, random_state=42)
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_html_contains_plotly_code(self, temp_output_dir, sample_records, sample_tsne_coords):
        """Test that HTML file contains Plotly visualization code."""
        fig = create_interactive_scatter(sample_records, sample_tsne_coords[:3])
        output_path = temp_output_dir / "test.html"
        save_interactive_html(fig, output_path, perplexity=30, random_state=42)

        html_content = output_path.read_text()
        assert "plotly" in html_content.lower()

    def test_html_contains_responsive_css(
        self, temp_output_dir, sample_records, sample_tsne_coords
    ):
        """Test that HTML file contains responsive CSS."""
        fig = create_interactive_scatter(sample_records, sample_tsne_coords[:3])
        output_path = temp_output_dir / "test.html"
        save_interactive_html(fig, output_path, perplexity=30, random_state=42, min_width=1250)

        html_content = output_path.read_text()
        assert "min-width: 1250px" in html_content

    def test_html_contains_metadata_footer(
        self, temp_output_dir, sample_records, sample_tsne_coords
    ):
        """Test that HTML file contains metadata footer."""
        fig = create_interactive_scatter(sample_records, sample_tsne_coords[:3])
        output_path = temp_output_dir / "test.html"
        save_interactive_html(fig, output_path, perplexity=30, random_state=42)

        html_content = output_path.read_text()
        assert "t-SNE Visualization Parameters" in html_content
        assert "Perplexity" in html_content

    def test_invalid_extension_raises_error(
        self, temp_output_dir, sample_records, sample_tsne_coords
    ):
        """Test that non-HTML extension raises ValueError."""
        fig = create_interactive_scatter(sample_records, sample_tsne_coords[:3])
        output_path = temp_output_dir / "test.png"
        with pytest.raises(ValueError, match="must end with .html"):
            save_interactive_html(fig, output_path, perplexity=30, random_state=42)

    def test_missing_parent_dir_raises_error(self, sample_records, sample_tsne_coords):
        """Test that missing parent directory raises FileNotFoundError."""
        fig = create_interactive_scatter(sample_records, sample_tsne_coords[:3])
        output_path = Path("/nonexistent/directory/test.html")
        with pytest.raises(FileNotFoundError, match="Parent directory does not exist"):
            save_interactive_html(fig, output_path, perplexity=30, random_state=42)


# ============================================================================
# Tests: Import Error Handling
# ============================================================================


class TestPlotlyImportErrors:
    """Tests for Plotly import error handling."""

    @pytest.mark.skipif(PLOTLY_AVAILABLE, reason="Plotly is installed")
    def test_plotly_not_available_flag(self):
        """Test that PLOTLY_AVAILABLE is False when Plotly not installed."""
        assert not PLOTLY_AVAILABLE

    @pytest.mark.skipif(not PLOTLY_AVAILABLE, reason="Plotly is installed")
    def test_plotly_available_flag(self):
        """Test that PLOTLY_AVAILABLE is True when Plotly is installed."""
        assert PLOTLY_AVAILABLE
