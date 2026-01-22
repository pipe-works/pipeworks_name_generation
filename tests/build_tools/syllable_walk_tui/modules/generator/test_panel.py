"""
Tests for CombinerPanel UI component.

Tests that CombinerPanel provides controls matching the name_combiner CLI options.
"""

from __future__ import annotations

from build_tools.syllable_walk_tui.modules.generator.panel import CombinerPanel


class TestCombinerPanel:
    """Tests for the CombinerPanel widget."""

    def test_has_default_css(self) -> None:
        """Should have DEFAULT_CSS defined."""
        assert CombinerPanel.DEFAULT_CSS is not None
        assert len(CombinerPanel.DEFAULT_CSS) > 0

    def test_css_includes_panel_header(self) -> None:
        """CSS should include panel-header class."""
        assert "panel-header" in CombinerPanel.DEFAULT_CSS

    def test_css_includes_output_section(self) -> None:
        """CSS should include output-section class."""
        assert "output-section" in CombinerPanel.DEFAULT_CSS

    def test_css_includes_meta_line(self) -> None:
        """CSS should include meta-line class."""
        assert "meta-line" in CombinerPanel.DEFAULT_CSS

    def test_css_includes_placeholder(self) -> None:
        """CSS should include placeholder class."""
        assert "placeholder" in CombinerPanel.DEFAULT_CSS


class TestCombinerPanelInit:
    """Tests for CombinerPanel initialization."""

    def test_default_patch_name(self) -> None:
        """Default patch name should be 'A'."""
        panel = CombinerPanel()
        assert panel.patch_name == "A"

    def test_custom_patch_name_a(self) -> None:
        """Should accept patch name 'A'."""
        panel = CombinerPanel(patch_name="A")
        assert panel.patch_name == "A"

    def test_custom_patch_name_b(self) -> None:
        """Should accept patch name 'B'."""
        panel = CombinerPanel(patch_name="B")
        assert panel.patch_name == "B"


class TestCombinerPanelMethods:
    """Tests for CombinerPanel methods."""

    def test_update_output_accepts_none(self) -> None:
        """update_output should accept None (shows placeholder)."""
        panel = CombinerPanel()
        # Should not raise
        panel.update_output(None)

    def test_update_output_accepts_meta_dict(self) -> None:
        """update_output should accept metadata dict."""
        panel = CombinerPanel()
        meta = {
            "arguments": {
                "syllables": 2,
                "count": 10000,
                "seed": 42,
                "frequency_weight": 1.0,
            },
            "output": {
                "candidates_generated": 10000,
                "unique_names": 7500,
                "unique_percentage": 75.0,
                "candidates_file": "/path/to/candidates/nltk_candidates_2syl.json",
            },
        }
        # Should not raise
        panel.update_output(meta)

    def test_update_output_handles_empty_meta(self) -> None:
        """update_output should handle empty metadata dict."""
        panel = CombinerPanel()
        # Should not raise
        panel.update_output({})

    def test_update_output_handles_partial_meta(self) -> None:
        """update_output should handle partial metadata dict."""
        panel = CombinerPanel()
        meta = {
            "arguments": {"syllables": 2},
            # No "output" key
        }
        # Should not raise
        panel.update_output(meta)

    def test_clear_output(self) -> None:
        """clear_output should reset to placeholder."""
        panel = CombinerPanel()
        # Should not raise
        panel.clear_output()
