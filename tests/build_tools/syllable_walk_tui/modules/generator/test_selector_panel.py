"""
Tests for SelectorPanel UI component.

Tests that SelectorPanel provides controls matching the name_selector CLI options.
"""

from __future__ import annotations

from build_tools.syllable_walk_tui.modules.generator.selector_panel import SelectorPanel


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
