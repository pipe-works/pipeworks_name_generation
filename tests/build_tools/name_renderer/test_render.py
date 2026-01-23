"""
Tests for the name_renderer module.

Tests the pure rendering functions that transform raw names
into human-readable styled formats.
"""

from build_tools.name_renderer import (
    get_available_styles,
    get_style_description,
    render,
    render_full_name,
)


class TestRender:
    """Tests for the render() function."""

    def test_title_case_simple(self):
        """Title case renders single lowercase word correctly."""
        assert render("orma", "first_name") == "Orma"

    def test_title_case_multi_syllable(self):
        """Title case renders multi-syllable names correctly."""
        assert render("striden", "last_name") == "Striden"

    def test_title_case_already_capitalized(self):
        """Title case handles already capitalized input."""
        # Python's title() will still work on mixed case
        assert render("ORMA", "first_name") == "Orma"

    def test_upper_style(self):
        """Upper style renders to all uppercase."""
        assert render("orma", "first_name", style="upper") == "ORMA"

    def test_lower_style(self):
        """Lower style renders to all lowercase."""
        assert render("Orma", "first_name", style="lower") == "orma"
        assert render("ORMA", "first_name", style="lower") == "orma"

    def test_empty_name(self):
        """Empty name returns empty string."""
        assert render("", "first_name") == ""
        assert render("", "first_name", style="upper") == ""

    def test_unknown_style_defaults_to_title(self):
        """Unknown style falls back to title case."""
        assert render("orma", "first_name", style="unknown") == "Orma"

    def test_name_class_is_accepted(self):
        """Different name classes are accepted (reserved for future use)."""
        # All these should work without error
        assert render("test", "first_name") == "Test"
        assert render("test", "last_name") == "Test"
        assert render("test", "place_name") == "Test"
        assert render("test", "organisation") == "Test"

    def test_whitespace_handling(self):
        """Names with spaces are handled by title case."""
        # title() capitalizes each word
        assert render("hello world", "first_name") == "Hello World"

    def test_deterministic(self):
        """Same input always produces same output (determinism)."""
        for _ in range(10):
            assert render("orma", "first_name") == "Orma"


class TestRenderFullName:
    """Tests for the render_full_name() function."""

    def test_combines_names_with_space(self):
        """Full name combines first and last with space."""
        assert render_full_name("orma", "striden") == "Orma Striden"

    def test_title_case_default(self):
        """Default style is title case."""
        result = render_full_name("orma", "striden")
        assert result == "Orma Striden"

    def test_upper_style(self):
        """Upper style applies to both names."""
        result = render_full_name("orma", "striden", style="upper")
        assert result == "ORMA STRIDEN"

    def test_lower_style(self):
        """Lower style applies to both names."""
        result = render_full_name("Orma", "Striden", style="lower")
        assert result == "orma striden"

    def test_empty_first_name(self):
        """Empty first name returns just last name."""
        assert render_full_name("", "striden") == "Striden"

    def test_empty_last_name(self):
        """Empty last name returns just first name."""
        assert render_full_name("orma", "") == "Orma"

    def test_both_empty(self):
        """Both empty returns empty string."""
        assert render_full_name("", "") == ""

    def test_deterministic(self):
        """Same input always produces same output (determinism)."""
        for _ in range(10):
            assert render_full_name("orma", "striden") == "Orma Striden"


class TestGetAvailableStyles:
    """Tests for the get_available_styles() function."""

    def test_returns_list(self):
        """Returns a list of strings."""
        styles = get_available_styles()
        assert isinstance(styles, list)
        assert all(isinstance(s, str) for s in styles)

    def test_contains_expected_styles(self):
        """Contains title, upper, and lower styles."""
        styles = get_available_styles()
        assert "title" in styles
        assert "upper" in styles
        assert "lower" in styles

    def test_returns_copy(self):
        """Returns a copy, not the original list."""
        styles1 = get_available_styles()
        styles2 = get_available_styles()
        # Modifying one shouldn't affect the other
        styles1.append("test")
        assert "test" not in styles2


class TestGetStyleDescription:
    """Tests for the get_style_description() function."""

    def test_title_description(self):
        """Title style has appropriate description."""
        desc = get_style_description("title")
        assert "Title" in desc or "title" in desc.lower()
        assert "Orma" in desc

    def test_upper_description(self):
        """Upper style has appropriate description."""
        desc = get_style_description("upper")
        assert "UPPER" in desc or "upper" in desc.lower()
        assert "ORMA" in desc

    def test_lower_description(self):
        """Lower style has appropriate description."""
        desc = get_style_description("lower")
        assert "lower" in desc.lower()
        assert "orma" in desc

    def test_unknown_style(self):
        """Unknown style returns fallback description."""
        desc = get_style_description("unknown")
        assert "Unknown" in desc or "unknown" in desc.lower()


class TestRendererPurity:
    """Tests ensuring the renderer is a pure function with no side effects."""

    def test_no_modification_of_input(self):
        """Input string is not modified."""
        name = "orma"
        original = name
        render(name, "first_name")
        assert name == original

    def test_no_global_state(self):
        """Multiple calls don't affect each other."""
        # Call with different styles
        render("test", "first_name", style="upper")
        render("test", "first_name", style="lower")
        # Default should still work
        assert render("test", "first_name") == "Test"

    def test_reversibility(self):
        """Rendering can be conceptually reversed (lowercase recovers original)."""
        original = "orma"
        rendered = render(original, "first_name", style="title")
        recovered = render(rendered, "first_name", style="lower")
        assert recovered == original
