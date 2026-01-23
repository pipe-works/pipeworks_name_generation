"""
Tests for the RenderScreen modal.

Tests the TUI component for displaying rendered names.
"""

from build_tools.syllable_walk_tui.modules.renderer import RenderScreen


class TestRenderScreenInit:
    """Tests for RenderScreen initialization."""

    def test_init_with_names(self):
        """Screen initializes with name lists."""
        screen = RenderScreen(
            names_a=["orma", "striden"],
            names_b=["krath", "velum"],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        assert screen.names_a == ["orma", "striden"]
        assert screen.names_b == ["krath", "velum"]
        assert screen.name_class_a == "first_name"
        assert screen.name_class_b == "last_name"

    def test_init_empty_lists(self):
        """Screen handles empty name lists."""
        screen = RenderScreen(
            names_a=[],
            names_b=["krath"],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        assert screen.names_a == []
        assert screen.names_b == ["krath"]

    def test_init_both_empty(self):
        """Screen handles both lists empty."""
        screen = RenderScreen(
            names_a=[],
            names_b=[],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        assert screen.names_a == []
        assert screen.names_b == []

    def test_default_style_is_title(self):
        """Default rendering style is title case."""
        screen = RenderScreen(
            names_a=["test"],
            names_b=["test"],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        assert screen.current_style == "title"

    def test_combined_off_by_default(self):
        """Combined names panel is hidden by default."""
        screen = RenderScreen(
            names_a=["test"],
            names_b=["test"],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        assert screen.show_combined is False


class TestRenderScreenMethods:
    """Tests for RenderScreen helper methods."""

    def test_render_names_list_applies_style(self):
        """_render_names_list applies current style."""
        screen = RenderScreen(
            names_a=["orma", "krath"],
            names_b=[],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        result = screen._render_names_list(["orma", "krath"], "first_name")
        assert "Orma" in result
        assert "Krath" in result

    def test_render_names_list_empty(self):
        """_render_names_list handles empty list."""
        screen = RenderScreen(
            names_a=[],
            names_b=[],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        result = screen._render_names_list([], "first_name")
        assert "no names" in result.lower()

    def test_render_combined_names(self):
        """_render_combined_names combines A and B names."""
        screen = RenderScreen(
            names_a=["orma", "krath"],
            names_b=["striden", "velum"],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        result = screen._render_combined_names()
        assert "Orma Striden" in result
        assert "Krath Velum" in result

    def test_render_combined_names_unequal_lengths(self):
        """_render_combined_names handles unequal list lengths."""
        screen = RenderScreen(
            names_a=["orma", "krath", "extra"],
            names_b=["striden"],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        result = screen._render_combined_names()
        # Should only combine up to shorter length
        assert "Orma Striden" in result
        # Extra names from A shouldn't appear with B
        lines = result.strip().split("\n")
        assert len(lines) == 1

    def test_render_combined_needs_both_patches(self):
        """_render_combined_names needs names in both patches."""
        # Only A has names
        screen = RenderScreen(
            names_a=["orma"],
            names_b=[],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        result = screen._render_combined_names()
        assert "need names" in result.lower() or "both patches" in result.lower()


class TestRenderScreenStyleCycling:
    """Tests for style cycling functionality."""

    def test_style_cycles_through_all(self):
        """Cycling moves through all available styles."""
        screen = RenderScreen(
            names_a=["test"],
            names_b=["test"],
            name_class_a="first_name",
            name_class_b="last_name",
        )

        styles_seen = [screen.current_style]

        # Cycle through styles
        for _ in range(len(screen.available_styles)):
            screen.current_style_index = (screen.current_style_index + 1) % len(
                screen.available_styles
            )
            styles_seen.append(screen.current_style)

        # Should have seen all styles (plus wrap back to first)
        assert "title" in styles_seen
        assert "upper" in styles_seen
        assert "lower" in styles_seen

    def test_style_index_wraps(self):
        """Style index wraps around at end of list."""
        screen = RenderScreen(
            names_a=["test"],
            names_b=["test"],
            name_class_a="first_name",
            name_class_b="last_name",
        )

        # Move to last style
        screen.current_style_index = len(screen.available_styles) - 1

        # Cycle one more time
        screen.current_style_index = (screen.current_style_index + 1) % len(screen.available_styles)

        # Should be back at 0
        assert screen.current_style_index == 0


class TestRenderScreenBindings:
    """Tests for keybinding configuration."""

    @staticmethod
    def _get_binding_keys(bindings: list) -> list[str]:
        """Extract key strings from bindings (handles both tuple and Binding)."""
        keys = []
        for b in bindings:
            if isinstance(b, tuple):
                keys.append(b[0])
            else:
                # Binding object has .key attribute
                keys.append(b.key)
        return keys

    def test_has_close_binding(self):
        """Screen has escape/q binding to close."""
        binding_keys = self._get_binding_keys(RenderScreen.BINDINGS)
        assert "escape" in binding_keys or "q" in binding_keys

    def test_has_style_binding(self):
        """Screen has 's' binding for style cycling."""
        binding_keys = self._get_binding_keys(RenderScreen.BINDINGS)
        assert "s" in binding_keys

    def test_has_combine_binding(self):
        """Screen has 'c' binding for combine toggle."""
        binding_keys = self._get_binding_keys(RenderScreen.BINDINGS)
        assert "c" in binding_keys
