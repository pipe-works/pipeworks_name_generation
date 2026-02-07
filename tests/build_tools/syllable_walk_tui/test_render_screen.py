"""
Tests for the RenderScreen modal.

Tests the TUI component for displaying rendered names.
Includes both unit tests for methods and async integration tests
for the full screen lifecycle.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from textual.app import App
from textual.widgets import Label, Static

from build_tools.syllable_walk_tui.modules.renderer import RenderScreen

# =============================================================================
# Unit Tests - RenderScreen Initialization
# =============================================================================


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

    def test_available_styles_populated(self):
        """Available styles list is populated from name_renderer."""
        screen = RenderScreen(
            names_a=["test"],
            names_b=["test"],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        assert len(screen.available_styles) >= 3
        assert "title" in screen.available_styles
        assert "upper" in screen.available_styles
        assert "lower" in screen.available_styles

    def test_current_style_index_starts_at_zero(self):
        """Style index starts at 0 (title case)."""
        screen = RenderScreen(
            names_a=["test"],
            names_b=["test"],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        assert screen.current_style_index == 0


# =============================================================================
# Unit Tests - RenderScreen Helper Methods
# =============================================================================


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

    def test_render_names_list_upper_style(self):
        """_render_names_list applies upper style correctly."""
        screen = RenderScreen(
            names_a=["orma"],
            names_b=[],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        # Set to upper style
        screen.current_style_index = screen.available_styles.index("upper")
        result = screen._render_names_list(["orma"], "first_name")
        assert "ORMA" in result

    def test_render_names_list_lower_style(self):
        """_render_names_list applies lower style correctly."""
        screen = RenderScreen(
            names_a=["Orma"],
            names_b=[],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        # Set to lower style
        screen.current_style_index = screen.available_styles.index("lower")
        result = screen._render_names_list(["Orma"], "first_name")
        assert "orma" in result

    def test_render_names_list_multiple_names(self):
        """_render_names_list joins multiple names with newlines."""
        screen = RenderScreen(
            names_a=["orma", "krath", "velum"],
            names_b=[],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        result = screen._render_names_list(["orma", "krath", "velum"], "first_name")
        lines = result.split("\n")
        assert len(lines) == 3
        assert "Orma" in lines[0]
        assert "Krath" in lines[1]
        assert "Velum" in lines[2]

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

    def test_render_combined_needs_a_names(self):
        """_render_combined_names needs names in A patch."""
        # Only B has names
        screen = RenderScreen(
            names_a=[],
            names_b=["striden"],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        result = screen._render_combined_names()
        assert "need names" in result.lower() or "both patches" in result.lower()

    def test_render_combined_upper_style(self):
        """_render_combined_names applies upper style."""
        screen = RenderScreen(
            names_a=["orma"],
            names_b=["striden"],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        screen.current_style_index = screen.available_styles.index("upper")
        result = screen._render_combined_names()
        assert "ORMA STRIDEN" in result

    def test_render_combined_lower_style(self):
        """_render_combined_names applies lower style."""
        screen = RenderScreen(
            names_a=["Orma"],
            names_b=["Striden"],
            name_class_a="first_name",
            name_class_b="last_name",
        )
        screen.current_style_index = screen.available_styles.index("lower")
        result = screen._render_combined_names()
        assert "orma striden" in result


# =============================================================================
# Unit Tests - Style Cycling
# =============================================================================


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

    def test_current_style_property(self):
        """current_style property returns correct style string."""
        screen = RenderScreen(
            names_a=["test"],
            names_b=["test"],
            name_class_a="first_name",
            name_class_b="last_name",
        )

        # At index 0, should be first style in list
        assert screen.current_style == screen.available_styles[0]

        # Move to index 1
        screen.current_style_index = 1
        assert screen.current_style == screen.available_styles[1]


# =============================================================================
# Unit Tests - Keybinding Configuration
# =============================================================================


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

    def test_has_both_close_bindings(self):
        """Screen has both escape and q for closing."""
        binding_keys = self._get_binding_keys(RenderScreen.BINDINGS)
        assert "escape" in binding_keys
        assert "q" in binding_keys


# =============================================================================
# Async Integration Tests - Screen Composition
# =============================================================================


@pytest.fixture
def render_screen_app():
    """Create an App that hosts a RenderScreen for testing."""

    class TestApp(App):
        def __init__(
            self,
            names_a: list[str] | None = None,
            names_b: list[str] | None = None,
        ):
            super().__init__()
            # Use None check instead of 'or' to properly handle empty lists
            self.names_a = names_a if names_a is not None else ["orma", "krath"]
            self.names_b = names_b if names_b is not None else ["striden", "velum"]

        def compose(self):
            yield RenderScreen(
                names_a=self.names_a,
                names_b=self.names_b,
                name_class_a="first_name",
                name_class_b="last_name",
            )

    return TestApp


class TestRenderScreenCompose:
    """Tests for RenderScreen compose() method."""

    @pytest.mark.asyncio
    async def test_compose_shows_header(self, render_screen_app):
        """Test that modal shows NAME RENDERER header."""
        async with render_screen_app().run_test() as pilot:
            labels = pilot.app.query(Label)
            label_texts = [str(lbl.render()) for lbl in labels]

            assert any("NAME RENDERER" in text for text in label_texts)

    @pytest.mark.asyncio
    async def test_compose_shows_patch_a_section(self, render_screen_app):
        """Test that modal shows PATCH A section."""
        async with render_screen_app().run_test() as pilot:
            labels = pilot.app.query(Label)
            label_texts = [str(lbl.render()) for lbl in labels]

            assert any("PATCH A" in text for text in label_texts)

    @pytest.mark.asyncio
    async def test_compose_shows_patch_b_section(self, render_screen_app):
        """Test that modal shows PATCH B section."""
        async with render_screen_app().run_test() as pilot:
            labels = pilot.app.query(Label)
            label_texts = [str(lbl.render()) for lbl in labels]

            assert any("PATCH B" in text for text in label_texts)

    @pytest.mark.asyncio
    async def test_compose_shows_name_class_labels(self, render_screen_app):
        """Test that modal shows name class labels."""
        async with render_screen_app().run_test() as pilot:
            labels = pilot.app.query(Label)
            label_texts = [str(lbl.render()) for lbl in labels]

            assert any("first_name" in text for text in label_texts)
            assert any("last_name" in text for text in label_texts)

    @pytest.mark.asyncio
    async def test_compose_shows_footer(self, render_screen_app):
        """Test that modal shows footer with keybindings."""
        async with render_screen_app().run_test() as pilot:
            labels = pilot.app.query(Label)
            label_texts = [str(lbl.render()) for lbl in labels]

            # Footer should mention key bindings
            assert any("Esc" in text or "Close" in text for text in label_texts)

    @pytest.mark.asyncio
    async def test_compose_shows_style_label(self, render_screen_app):
        """Test that modal shows current style label."""
        async with render_screen_app().run_test() as pilot:
            style_label = pilot.app.query_one("#style-label", Label)
            text = str(style_label.render())

            assert "Style:" in text
            assert "Title" in text or "title" in text.lower()

    @pytest.mark.asyncio
    async def test_compose_shows_rendered_names_a(self, render_screen_app):
        """Test that modal shows rendered names from Patch A."""
        async with render_screen_app().run_test() as pilot:
            names_a_widget = pilot.app.query_one("#names-a", Static)
            text = str(names_a_widget.render())

            # Names should be title-cased
            assert "Orma" in text
            assert "Krath" in text

    @pytest.mark.asyncio
    async def test_compose_shows_rendered_names_b(self, render_screen_app):
        """Test that modal shows rendered names from Patch B."""
        async with render_screen_app().run_test() as pilot:
            names_b_widget = pilot.app.query_one("#names-b", Static)
            text = str(names_b_widget.render())

            assert "Striden" in text
            assert "Velum" in text

    @pytest.mark.asyncio
    async def test_compose_with_empty_names_a(self, render_screen_app):
        """Test that modal handles empty Patch A names."""
        app = render_screen_app(names_a=[], names_b=["striden"])

        async with app.run_test() as pilot:
            names_a_widget = pilot.app.query_one("#names-a", Static)
            text = str(names_a_widget.render())

            assert "no names" in text.lower()

    @pytest.mark.asyncio
    async def test_compose_with_empty_names_b(self, render_screen_app):
        """Test that modal handles empty Patch B names."""
        app = render_screen_app(names_a=["orma"], names_b=[])

        async with app.run_test() as pilot:
            names_b_widget = pilot.app.query_one("#names-b", Static)
            text = str(names_b_widget.render())

            assert "no names" in text.lower()

    @pytest.mark.asyncio
    async def test_compose_shows_combined_panel(self, render_screen_app):
        """Test that combined panel exists (hidden by default)."""
        async with render_screen_app().run_test() as pilot:
            combined_panel = pilot.app.query_one("#combined-panel")
            assert combined_panel is not None

    @pytest.mark.asyncio
    async def test_combined_panel_hidden_initially(self, render_screen_app):
        """Test that combined panel is hidden on mount."""
        async with render_screen_app().run_test() as pilot:
            combined_panel = pilot.app.query_one("#combined-panel")
            # Panel should have display=False after mount
            assert combined_panel.display is False


# =============================================================================
# Async Integration Tests - Actions
# =============================================================================


class TestRenderScreenActions:
    """Tests for RenderScreen action methods."""

    @pytest.mark.asyncio
    async def test_action_close_screen_exists(self, render_screen_app):
        """Test that action_close_screen method exists."""
        async with render_screen_app().run_test() as pilot:
            screen = pilot.app.query_one(RenderScreen)
            assert hasattr(screen, "action_close_screen")

    @pytest.mark.asyncio
    async def test_action_cycle_style_exists(self, render_screen_app):
        """Test that action_cycle_style method exists."""
        async with render_screen_app().run_test() as pilot:
            screen = pilot.app.query_one(RenderScreen)
            assert hasattr(screen, "action_cycle_style")

    @pytest.mark.asyncio
    async def test_action_toggle_combine_exists(self, render_screen_app):
        """Test that action_toggle_combine method exists."""
        async with render_screen_app().run_test() as pilot:
            screen = pilot.app.query_one(RenderScreen)
            assert hasattr(screen, "action_toggle_combine")

    @pytest.mark.asyncio
    async def test_cycle_style_via_keypress(self, render_screen_app):
        """Test cycling style via 's' keypress."""
        async with render_screen_app().run_test() as pilot:
            screen = pilot.app.query_one(RenderScreen)
            initial_style = screen.current_style

            # Press 's' to cycle style
            await pilot.press("s")
            await pilot.pause()

            # Style should have changed
            assert screen.current_style != initial_style

    @pytest.mark.asyncio
    async def test_cycle_style_updates_display(self, render_screen_app):
        """Test that cycling style updates the names display."""
        async with render_screen_app().run_test() as pilot:
            # Initial style should show title case
            names_a_widget = pilot.app.query_one("#names-a", Static)
            initial_text = str(names_a_widget.render())
            assert "Orma" in initial_text

            # Cycle to upper
            screen = pilot.app.query_one(RenderScreen)
            screen.current_style_index = screen.available_styles.index("upper")
            screen._refresh_names_display()
            await pilot.pause()

            # Should now show uppercase
            updated_text = str(names_a_widget.render())
            assert "ORMA" in updated_text

    @pytest.mark.asyncio
    async def test_toggle_combine_via_keypress(self, render_screen_app):
        """Test toggling combine panel via 'c' keypress."""
        async with render_screen_app().run_test() as pilot:
            screen = pilot.app.query_one(RenderScreen)
            combined_panel = pilot.app.query_one("#combined-panel")

            # Initially hidden
            assert screen.show_combined is False
            assert combined_panel.display is False

            # Press 'c' to toggle
            await pilot.press("c")
            await pilot.pause()

            # Should now be visible
            assert screen.show_combined is True
            assert combined_panel.display is True

    @pytest.mark.asyncio
    async def test_toggle_combine_twice_hides_panel(self, render_screen_app):
        """Test that toggling combine twice hides the panel."""
        async with render_screen_app().run_test() as pilot:
            combined_panel = pilot.app.query_one("#combined-panel")

            # Toggle on
            await pilot.press("c")
            await pilot.pause()
            assert combined_panel.display is True

            # Toggle off
            await pilot.press("c")
            await pilot.pause()
            assert combined_panel.display is False

    @pytest.mark.asyncio
    async def test_combined_names_shows_combinations(self, render_screen_app):
        """Test that combined panel shows A+B name combinations."""
        async with render_screen_app().run_test() as pilot:
            # Show combined panel
            await pilot.press("c")
            await pilot.pause()

            combined_names = pilot.app.query_one("#combined-names", Static)
            text = str(combined_names.render())

            # Should show combined names
            assert "Orma Striden" in text
            assert "Krath Velum" in text

    @pytest.mark.asyncio
    async def test_escape_key_bound_to_close(self, render_screen_app):
        """Test that escape key is bound to close action."""
        # Verify the binding exists
        binding_keys = []
        for binding in RenderScreen.BINDINGS:
            if isinstance(binding, tuple):
                binding_keys.append(binding[0])
            else:
                binding_keys.append(binding.key)

        assert "escape" in binding_keys

    @pytest.mark.asyncio
    async def test_q_key_bound_to_close(self, render_screen_app):
        """Test that 'q' key is bound to close action."""
        # Verify the binding exists
        binding_keys = []
        for binding in RenderScreen.BINDINGS:
            if isinstance(binding, tuple):
                binding_keys.append(binding[0])
            else:
                binding_keys.append(binding.key)

        assert "q" in binding_keys


# =============================================================================
# Async Integration Tests - Refresh Display
# =============================================================================


class TestRenderScreenRefresh:
    """Tests for _refresh_names_display method."""

    @pytest.mark.asyncio
    async def test_refresh_updates_names_a(self, render_screen_app):
        """Test that refresh updates Patch A names."""
        async with render_screen_app().run_test() as pilot:
            screen = pilot.app.query_one(RenderScreen)

            # Change to upper style
            screen.current_style_index = screen.available_styles.index("upper")
            screen._refresh_names_display()
            await pilot.pause()

            names_a_widget = pilot.app.query_one("#names-a", Static)
            text = str(names_a_widget.render())
            assert "ORMA" in text
            assert "KRATH" in text

    @pytest.mark.asyncio
    async def test_refresh_updates_names_b(self, render_screen_app):
        """Test that refresh updates Patch B names."""
        async with render_screen_app().run_test() as pilot:
            screen = pilot.app.query_one(RenderScreen)

            # Change to lower style
            screen.current_style_index = screen.available_styles.index("lower")
            screen._refresh_names_display()
            await pilot.pause()

            names_b_widget = pilot.app.query_one("#names-b", Static)
            text = str(names_b_widget.render())
            assert "striden" in text
            assert "velum" in text

    @pytest.mark.asyncio
    async def test_refresh_updates_combined_names(self, render_screen_app):
        """Test that refresh updates combined names."""
        async with render_screen_app().run_test() as pilot:
            screen = pilot.app.query_one(RenderScreen)

            # Show combined panel and change style
            screen.show_combined = True
            screen._update_combined_visibility()
            await pilot.pause()

            # Change to upper style
            screen.current_style_index = screen.available_styles.index("upper")
            screen._refresh_names_display()
            await pilot.pause()

            combined_names = pilot.app.query_one("#combined-names", Static)
            text = str(combined_names.render())
            assert "ORMA STRIDEN" in text

    @pytest.mark.asyncio
    async def test_refresh_updates_style_label(self, render_screen_app):
        """Test that refresh updates the style label."""
        async with render_screen_app().run_test() as pilot:
            screen = pilot.app.query_one(RenderScreen)

            # Change to upper style
            screen.current_style_index = screen.available_styles.index("upper")
            screen._refresh_names_display()
            await pilot.pause()

            style_label = pilot.app.query_one("#style-label", Label)
            text = str(style_label.render())
            assert "UPPER" in text or "upper" in text.lower()


# =============================================================================
# Async Integration Tests - Update Combined Visibility
# =============================================================================


class TestRenderScreenCombinedVisibility:
    """Tests for _update_combined_visibility method."""

    @pytest.mark.asyncio
    async def test_update_visibility_shows_panel(self, render_screen_app):
        """Test that setting show_combined=True shows the panel."""
        async with render_screen_app().run_test() as pilot:
            screen = pilot.app.query_one(RenderScreen)
            combined_panel = pilot.app.query_one("#combined-panel")

            screen.show_combined = True
            screen._update_combined_visibility()
            await pilot.pause()

            assert combined_panel.display is True

    @pytest.mark.asyncio
    async def test_update_visibility_hides_panel(self, render_screen_app):
        """Test that setting show_combined=False hides the panel."""
        async with render_screen_app().run_test() as pilot:
            screen = pilot.app.query_one(RenderScreen)
            combined_panel = pilot.app.query_one("#combined-panel")

            # First show it
            screen.show_combined = True
            screen._update_combined_visibility()
            await pilot.pause()

            # Then hide it
            screen.show_combined = False
            screen._update_combined_visibility()
            await pilot.pause()

            assert combined_panel.display is False


# =============================================================================
# Async Integration Tests - Many Names
# =============================================================================


class TestRenderScreenManyNames:
    """Tests for RenderScreen with many names."""

    @pytest.mark.asyncio
    async def test_shows_all_names_from_patch_a(self, render_screen_app):
        """Test that all names from Patch A are displayed."""
        many_names = [f"name{i}" for i in range(10)]
        app = render_screen_app(names_a=many_names, names_b=[])

        async with app.run_test() as pilot:
            names_a_widget = pilot.app.query_one("#names-a", Static)
            text = str(names_a_widget.render())

            # All names should be present (title-cased)
            for i in range(10):
                assert f"Name{i}" in text

    @pytest.mark.asyncio
    async def test_combined_with_many_pairs(self, render_screen_app):
        """Test combined view with many name pairs."""
        names_a = ["first1", "first2", "first3", "first4", "first5"]
        names_b = ["last1", "last2", "last3", "last4", "last5"]
        app = render_screen_app(names_a=names_a, names_b=names_b)

        async with app.run_test() as pilot:
            screen = pilot.app.query_one(RenderScreen)
            result = screen._render_combined_names()

            # All pairs should be present
            assert "First1 Last1" in result
            assert "First5 Last5" in result
            assert result.count("\n") == 4  # 5 names = 4 newlines


class TestRenderScreenSampleExport:
    """Tests for renderer sample export helpers."""

    def test_export_sample_warns_when_names_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Export should warn when there are no names to sample."""
        screen = RenderScreen(
            names_a=[],
            names_b=[],
            name_class_a="first_name",
            name_class_b="last_name",
        )

        notices: list[tuple[str, str]] = []

        def _capture_notify(message: str, *args: object, **kwargs: object) -> None:
            severity = str(kwargs.get("severity", "information"))
            notices.append((message, severity))

        monkeypatch.setattr(screen, "notify", _capture_notify)
        screen._export_sample([], "first_name", Path("/tmp"), "A")

        assert notices[-1] == ("Patch A: No names to sample.", "warning")

    def test_export_sample_warns_when_dir_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Export should warn when selections dir is unavailable."""
        screen = RenderScreen(
            names_a=["alma"],
            names_b=[],
            name_class_a="first_name",
            name_class_b="last_name",
        )

        notices: list[tuple[str, str]] = []

        def _capture_notify(message: str, *args: object, **kwargs: object) -> None:
            severity = str(kwargs.get("severity", "information"))
            notices.append((message, severity))

        monkeypatch.setattr(screen, "notify", _capture_notify)
        screen._export_sample(["alma"], "first_name", None, "A")

        assert "No selections directory available." in notices[-1][0]
        assert notices[-1][1] == "warning"

    def test_export_sample_reports_service_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Export should surface service-layer errors."""
        screen = RenderScreen(
            names_a=["alma"],
            names_b=[],
            name_class_a="first_name",
            name_class_b="last_name",
        )

        notices: list[tuple[str, str]] = []

        def _capture_notify(message: str, *args: object, **kwargs: object) -> None:
            severity = str(kwargs.get("severity", "information"))
            notices.append((message, severity))

        monkeypatch.setattr(screen, "notify", _capture_notify)

        with patch(
            "build_tools.syllable_walk_tui.services.exporter.export_sample_json",
            return_value=(Path("/tmp/first_name_sample.json"), "write failed"),
        ):
            screen._export_sample(["alma"], "first_name", Path("/tmp"), "A")

        assert notices[-1] == ("Patch A: write failed", "error")

    def test_export_sample_reports_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Export should notify with success message when file is written."""
        screen = RenderScreen(
            names_a=["alma"],
            names_b=[],
            name_class_a="first_name",
            name_class_b="last_name",
        )

        notices: list[tuple[str, str]] = []

        def _capture_notify(message: str, *args: object, **kwargs: object) -> None:
            severity = str(kwargs.get("severity", "information"))
            notices.append((message, severity))

        monkeypatch.setattr(screen, "notify", _capture_notify)

        with patch(
            "build_tools.syllable_walk_tui.services.exporter.export_sample_json",
            return_value=(Path("/tmp/first_name_sample.json"), None),
        ):
            screen._export_sample(["alma"], "first_name", Path("/tmp"), "A")

        assert notices[-1] == ("Patch A: Sample exported → first_name_sample.json", "information")

    def test_export_button_handlers_delegate_to_export_sample(self) -> None:
        """Export button handlers should call _export_sample with patch-specific args."""
        screen = RenderScreen(
            names_a=["alma"],
            names_b=["bera"],
            name_class_a="first_name",
            name_class_b="last_name",
            selections_dir_a=Path("/tmp/a"),
            selections_dir_b=Path("/tmp/b"),
        )
        calls: list[tuple[list[str], str, Path | None, str]] = []

        def _capture(
            names: list[str], name_class: str, selections_dir: Path | None, patch_label: str
        ):
            calls.append((names, name_class, selections_dir, patch_label))

        with patch.object(screen, "_export_sample", side_effect=_capture):
            screen.on_export_sample_a()
            screen.on_export_sample_b()

        assert calls[0] == (["alma"], "first_name", Path("/tmp/a"), "A")
        assert calls[1] == (["bera"], "last_name", Path("/tmp/b"), "B")
