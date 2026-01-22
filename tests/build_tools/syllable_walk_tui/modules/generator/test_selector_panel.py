"""
Tests for SelectorPanel UI component.

Tests that SelectorPanel provides controls matching the name_selector CLI options.
"""

from __future__ import annotations

import pytest
from textual.app import App
from textual.widgets import Button, Label

from build_tools.syllable_walk_tui.modules.generator.selector_panel import SelectorPanel
from build_tools.tui_common.controls import IntSpinner, JKSelect, RadioOption


class TestSelectorPanel:
    """Tests for the SelectorPanel widget."""

    def test_has_default_css(self) -> None:
        """Should have DEFAULT_CSS defined."""
        assert SelectorPanel.DEFAULT_CSS is not None
        assert len(SelectorPanel.DEFAULT_CSS) > 0

    def test_css_includes_panel_header(self) -> None:
        """CSS should include panel-header class."""
        assert "panel-header" in SelectorPanel.DEFAULT_CSS

    def test_css_includes_output_section(self) -> None:
        """CSS should include output-section class."""
        assert "output-section" in SelectorPanel.DEFAULT_CSS

    def test_css_includes_meta_line(self) -> None:
        """CSS should include meta-line class."""
        assert "meta-line" in SelectorPanel.DEFAULT_CSS

    def test_css_includes_placeholder(self) -> None:
        """CSS should include placeholder class."""
        assert "placeholder" in SelectorPanel.DEFAULT_CSS

    def test_css_includes_mode_label(self) -> None:
        """CSS should include mode-label class."""
        assert "mode-label" in SelectorPanel.DEFAULT_CSS

    def test_css_includes_mode_options(self) -> None:
        """CSS should include mode-options class."""
        assert "mode-options" in SelectorPanel.DEFAULT_CSS

    def test_css_includes_order_label(self) -> None:
        """CSS should include order-label class."""
        assert "order-label" in SelectorPanel.DEFAULT_CSS

    def test_css_includes_order_options(self) -> None:
        """CSS should include order-options class."""
        assert "order-options" in SelectorPanel.DEFAULT_CSS

    def test_css_includes_names_scroll(self) -> None:
        """CSS should include names-scroll class."""
        assert "names-scroll" in SelectorPanel.DEFAULT_CSS

    def test_css_includes_names_header(self) -> None:
        """CSS should include names-header class."""
        assert "names-header" in SelectorPanel.DEFAULT_CSS

    def test_css_includes_names_list(self) -> None:
        """CSS should include names-list class."""
        assert "names-list" in SelectorPanel.DEFAULT_CSS


class TestSelectorPanelInit:
    """Tests for SelectorPanel initialization."""

    def test_default_patch_name(self) -> None:
        """Default patch name should be 'A'."""
        panel = SelectorPanel()
        assert panel.patch_name == "A"

    def test_custom_patch_name_a(self) -> None:
        """Should accept patch name 'A'."""
        panel = SelectorPanel(patch_name="A")
        assert panel.patch_name == "A"

    def test_custom_patch_name_b(self) -> None:
        """Should accept patch name 'B'."""
        panel = SelectorPanel(patch_name="B")
        assert panel.patch_name == "B"


class TestSelectorPanelMethods:
    """Tests for SelectorPanel methods."""

    def test_update_output_accepts_none(self) -> None:
        """update_output should accept None (shows placeholder)."""
        panel = SelectorPanel()
        # Should not raise
        panel.update_output(None)

    def test_update_output_accepts_meta_dict(self) -> None:
        """update_output should accept metadata dict."""
        panel = SelectorPanel()
        meta = {
            "arguments": {
                "name_class": "first_name",
                "count": 100,
                "mode": "hard",
            },
            "statistics": {
                "total_evaluated": 10000,
                "admitted": 7500,
                "admitted_percentage": 75.0,
                "rejected": 2500,
            },
            "output": {
                "selections_count": 100,
                "selections_file": "/path/to/selections/pyphen_first_name_2syl.json",
            },
        }
        # Should not raise
        panel.update_output(meta)

    def test_update_output_handles_empty_meta(self) -> None:
        """update_output should handle empty metadata dict."""
        panel = SelectorPanel()
        # Should not raise
        panel.update_output({})

    def test_update_output_handles_partial_meta(self) -> None:
        """update_output should handle partial metadata dict."""
        panel = SelectorPanel()
        meta = {
            "arguments": {"name_class": "first_name"},
            # No "statistics" or "output" keys
        }
        # Should not raise
        panel.update_output(meta)

    def test_clear_output(self) -> None:
        """clear_output should reset to placeholder."""
        panel = SelectorPanel()
        # Should not raise
        panel.clear_output()

    def test_set_mode_hard(self) -> None:
        """set_mode should accept 'hard'."""
        panel = SelectorPanel()
        # Should not raise
        panel.set_mode("hard")

    def test_set_mode_soft(self) -> None:
        """set_mode should accept 'soft'."""
        panel = SelectorPanel()
        # Should not raise
        panel.set_mode("soft")

    def test_set_order_random(self) -> None:
        """set_order should accept 'random'."""
        panel = SelectorPanel()
        # Should not raise
        panel.set_order("random")

    def test_set_order_alphabetical(self) -> None:
        """set_order should accept 'alphabetical'."""
        panel = SelectorPanel()
        # Should not raise
        panel.set_order("alphabetical")

    def test_update_output_with_names(self) -> None:
        """update_output should accept names list."""
        panel = SelectorPanel()
        meta = {
            "arguments": {
                "name_class": "first_name",
                "count": 100,
                "mode": "hard",
                "order": "random",
            },
            "statistics": {
                "total_evaluated": 10000,
                "admitted": 7500,
                "admitted_percentage": 75.0,
                "rejected": 2500,
            },
            "output": {
                "selections_count": 100,
                "selections_file": "/path/to/selections/pyphen_first_name_2syl.json",
            },
        }
        names = ["kali", "sora", "mira", "vela", "nori"]
        # Should not raise
        panel.update_output(meta, names)

    def test_update_output_with_none_names(self) -> None:
        """update_output should accept None for names."""
        panel = SelectorPanel()
        meta = {
            "arguments": {"name_class": "first_name"},
        }
        # Should not raise
        panel.update_output(meta, None)

    def test_update_output_with_empty_names(self) -> None:
        """update_output should handle empty names list."""
        panel = SelectorPanel()
        meta = {
            "arguments": {"name_class": "first_name"},
        }
        # Should not raise
        panel.update_output(meta, [])


class TestSelectorPanelMounted:
    """Tests for SelectorPanel when mounted in an app."""

    @pytest.mark.asyncio
    async def test_compose_creates_expected_widgets(self) -> None:
        """compose should create all expected child widgets."""

        class TestApp(App):
            def compose(self):
                yield SelectorPanel(patch_name="A", id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app

            # Check header label
            labels = app.query(Label)
            labels_text = [str(label.render()) for label in labels]
            assert any("PATCH A NAME SELECTOR" in text for text in labels_text)

            # Check name class select
            select = app.query_one("#selector-name-class-a", JKSelect)
            assert select is not None

            # Check count spinner
            spinner = app.query_one("#selector-count-a", IntSpinner)
            assert spinner is not None
            assert spinner.value == 100

            # Check mode options
            hard_opt = app.query_one("#selector-mode-hard-a", RadioOption)
            soft_opt = app.query_one("#selector-mode-soft-a", RadioOption)
            assert hard_opt is not None
            assert soft_opt is not None

            # Check order options
            random_opt = app.query_one("#selector-order-random-a", RadioOption)
            alpha_opt = app.query_one("#selector-order-alphabetical-a", RadioOption)
            assert random_opt is not None
            assert alpha_opt is not None

            # Check select button
            button = app.query_one("#select-names-a", Button)
            assert button is not None

    @pytest.mark.asyncio
    async def test_compose_creates_patch_b_widgets(self) -> None:
        """compose should create widgets with patch B IDs."""

        class TestApp(App):
            def compose(self):
                yield SelectorPanel(patch_name="B", id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app

            # Check patch B specific IDs
            assert app.query_one("#selector-name-class-b", JKSelect)
            assert app.query_one("#selector-count-b", IntSpinner)
            assert app.query_one("#selector-mode-hard-b", RadioOption)
            assert app.query_one("#selector-order-random-b", RadioOption)
            assert app.query_one("#select-names-b", Button)

    @pytest.mark.asyncio
    async def test_update_output_displays_metadata(self) -> None:
        """update_output should display metadata in output label."""

        class TestApp(App):
            def compose(self):
                yield SelectorPanel(patch_name="A", id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            panel = app.query_one("#test-panel", SelectorPanel)

            meta = {
                "arguments": {
                    "name_class": "first_name",
                    "count": 100,
                    "mode": "hard",
                    "order": "random",
                },
                "statistics": {
                    "total_evaluated": 10000,
                    "admitted": 7500,
                    "admitted_percentage": 75.0,
                    "rejected": 2500,
                },
                "output": {
                    "selections_count": 100,
                    "selections_file": "/path/to/selections/pyphen_first_name_2syl.json",
                },
            }
            panel.update_output(meta)
            await pilot.pause()

            output_label = app.query_one("#selector-output-a", Label)
            text = str(output_label.render())
            assert "first_name" in text
            assert "Evaluated: 10,000" in text

    @pytest.mark.asyncio
    async def test_update_output_handles_simple_path(self) -> None:
        """update_output should handle selections_file without /selections/ path."""

        class TestApp(App):
            def compose(self):
                yield SelectorPanel(patch_name="A", id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            panel = app.query_one("#test-panel", SelectorPanel)

            meta = {
                "arguments": {"name_class": "first_name"},
                "statistics": {},
                "output": {
                    "selections_count": 50,
                    "selections_file": "simple_output.json",
                },
            }
            panel.update_output(meta)
            await pilot.pause()

            output_label = app.query_one("#selector-output-a", Label)
            text = str(output_label.render())
            assert "simple_output.json" in text

    @pytest.mark.asyncio
    async def test_update_output_displays_names(self) -> None:
        """update_output should display names in names label."""

        class TestApp(App):
            def compose(self):
                yield SelectorPanel(patch_name="A", id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            panel = app.query_one("#test-panel", SelectorPanel)

            meta = {"arguments": {"name_class": "first_name"}}
            names = ["kali", "sora", "mira"]
            panel.update_output(meta, names)
            await pilot.pause()

            names_label = app.query_one("#selector-names-a", Label)
            text = str(names_label.render())
            assert "kali" in text
            assert "sora" in text
            assert "mira" in text

    @pytest.mark.asyncio
    async def test_update_output_none_shows_placeholder(self) -> None:
        """update_output with None should show placeholder."""

        class TestApp(App):
            def compose(self):
                yield SelectorPanel(patch_name="A", id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            panel = app.query_one("#test-panel", SelectorPanel)

            panel.update_output(None)
            await pilot.pause()

            output_label = app.query_one("#selector-output-a", Label)
            text = str(output_label.render())
            assert "Generate candidates first" in text

    @pytest.mark.asyncio
    async def test_set_mode_hard_updates_radio_options(self) -> None:
        """set_mode('hard') should select hard option."""

        class TestApp(App):
            def compose(self):
                yield SelectorPanel(patch_name="A", id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            panel = app.query_one("#test-panel", SelectorPanel)

            panel.set_mode("hard")
            await pilot.pause()

            hard_opt = app.query_one("#selector-mode-hard-a", RadioOption)
            soft_opt = app.query_one("#selector-mode-soft-a", RadioOption)
            assert hard_opt.is_selected is True
            assert soft_opt.is_selected is False

    @pytest.mark.asyncio
    async def test_set_mode_soft_updates_radio_options(self) -> None:
        """set_mode('soft') should select soft option."""

        class TestApp(App):
            def compose(self):
                yield SelectorPanel(patch_name="A", id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            panel = app.query_one("#test-panel", SelectorPanel)

            panel.set_mode("soft")
            await pilot.pause()

            hard_opt = app.query_one("#selector-mode-hard-a", RadioOption)
            soft_opt = app.query_one("#selector-mode-soft-a", RadioOption)
            assert hard_opt.is_selected is False
            assert soft_opt.is_selected is True

    @pytest.mark.asyncio
    async def test_set_order_random_updates_radio_options(self) -> None:
        """set_order('random') should select random option."""

        class TestApp(App):
            def compose(self):
                yield SelectorPanel(patch_name="A", id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            panel = app.query_one("#test-panel", SelectorPanel)

            panel.set_order("random")
            await pilot.pause()

            random_opt = app.query_one("#selector-order-random-a", RadioOption)
            alpha_opt = app.query_one("#selector-order-alphabetical-a", RadioOption)
            assert random_opt.is_selected is True
            assert alpha_opt.is_selected is False

    @pytest.mark.asyncio
    async def test_set_order_alphabetical_updates_radio_options(self) -> None:
        """set_order('alphabetical') should select alphabetical option."""

        class TestApp(App):
            def compose(self):
                yield SelectorPanel(patch_name="A", id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            panel = app.query_one("#test-panel", SelectorPanel)

            panel.set_order("alphabetical")
            await pilot.pause()

            random_opt = app.query_one("#selector-order-random-a", RadioOption)
            alpha_opt = app.query_one("#selector-order-alphabetical-a", RadioOption)
            assert random_opt.is_selected is False
            assert alpha_opt.is_selected is True

    @pytest.mark.asyncio
    async def test_clear_output_resets_display(self) -> None:
        """clear_output should reset to placeholder state."""

        class TestApp(App):
            def compose(self):
                yield SelectorPanel(patch_name="A", id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            panel = app.query_one("#test-panel", SelectorPanel)

            # First set some output
            meta = {"arguments": {"name_class": "first_name"}}
            panel.update_output(meta, ["test"])
            await pilot.pause()

            # Then clear it
            panel.clear_output()
            await pilot.pause()

            output_label = app.query_one("#selector-output-a", Label)
            text = str(output_label.render())
            assert "Generate candidates first" in text

            names_label = app.query_one("#selector-names-a", Label)
            names_text = str(names_label.render())
            assert names_text.strip() == ""
