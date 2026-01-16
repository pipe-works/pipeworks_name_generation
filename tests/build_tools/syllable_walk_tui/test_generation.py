"""Tests for walk generation functionality in TUI.

Note: Uses type: ignore comments for pilot.app access since Textual's
Pilot returns App[Any] but we know it's SyllableWalkerApp at runtime.
"""

from pathlib import Path

import pytest

from build_tools.syllable_walk_tui.core import SyllableWalkerApp


@pytest.fixture
def sample_corpus():
    """Create a minimal test corpus."""
    return [
        {
            "syllable": "ka",
            "frequency": 100,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": True,
                "contains_fricative": False,
                "contains_liquid": False,
                "contains_nasal": False,
                "short_vowel": True,
                "long_vowel": False,
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
        {
            "syllable": "ki",
            "frequency": 80,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": True,
                "contains_fricative": False,
                "contains_liquid": False,
                "contains_nasal": False,
                "short_vowel": True,
                "long_vowel": False,
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
        {
            "syllable": "ta",
            "frequency": 90,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": True,
                "contains_fricative": False,
                "contains_liquid": False,
                "contains_nasal": False,
                "short_vowel": True,
                "long_vowel": False,
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
    ]


@pytest.mark.asyncio
async def test_generate_button_exists():
    """Test that generate button is present in oscillator panel."""
    app = SyllableWalkerApp()
    async with app.run_test() as pilot:
        # Check both patches have generate buttons
        assert pilot.app.query_one("#generate-A")
        assert pilot.app.query_one("#generate-B")


@pytest.mark.asyncio
async def test_generation_requires_corpus(sample_corpus):
    """Test that generation requires corpus to be loaded."""
    app = SyllableWalkerApp()
    async with app.run_test() as pilot:
        # Try to generate without corpus
        # Note: Use direct method call instead of click (button may be scrolled)
        pilot.app._generate_walks_for_patch("A")  # type: ignore[attr-defined]
        await pilot.pause(0.5)

        # Outputs should be empty (corpus not loaded)
        assert pilot.app.state.patch_a.outputs == []  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_generation_creates_walks(sample_corpus):
    """Test that generation creates walks and stores them."""
    app = SyllableWalkerApp()
    async with app.run_test() as pilot:
        # Load corpus (simplified - set all required fields for is_ready_for_generation())
        pilot.app.state.patch_a.corpus_dir = Path("/tmp/test_corpus")  # type: ignore[attr-defined]
        pilot.app.state.patch_a.annotated_data = sample_corpus  # type: ignore[attr-defined]
        pilot.app.state.patch_a.syllables = ["ka", "ki", "ta"]  # type: ignore[attr-defined]
        pilot.app.state.patch_a.frequencies = {"ka": 100, "ki": 80, "ta": 90}  # type: ignore[attr-defined]

        # Generate walks using direct method call (button may be scrolled out of view)
        pilot.app._generate_walks_for_patch("A")  # type: ignore[attr-defined]
        await pilot.pause(2.0)  # Wait for walker initialization + generation

        # Check that walks were generated
        assert len(pilot.app.state.patch_a.outputs) == 10  # type: ignore[attr-defined]

        # Check walk format (should have arrows)
        for walk in pilot.app.state.patch_a.outputs:  # type: ignore[attr-defined]
            assert "→" in walk
            assert any(syl in walk for syl in ["ka", "ki", "ta"])


@pytest.mark.asyncio
async def test_generation_uses_patch_parameters(sample_corpus):
    """Test that generation respects patch parameters."""
    app = SyllableWalkerApp()
    async with app.run_test() as pilot:
        # Load corpus (set all required fields for is_ready_for_generation())
        pilot.app.state.patch_a.corpus_dir = Path("/tmp/test_corpus")  # type: ignore[attr-defined]
        pilot.app.state.patch_a.annotated_data = sample_corpus  # type: ignore[attr-defined]
        pilot.app.state.patch_a.syllables = ["ka", "ki", "ta"]  # type: ignore[attr-defined]
        pilot.app.state.patch_a.frequencies = {"ka": 100, "ki": 80, "ta": 90}  # type: ignore[attr-defined]

        # Set specific walk length
        pilot.app.state.patch_a.walk_length = 3  # type: ignore[attr-defined]

        # Generate using direct method call (button may be scrolled out of view)
        pilot.app._generate_walks_for_patch("A")  # type: ignore[attr-defined]
        await pilot.pause(2.0)  # Wait for walker initialization + generation

        # Check that walks have correct length
        # Note: walk_length is the number of steps (transitions), so result has walk_length + 1 syllables
        # (start syllable + walk_length steps)
        for walk in pilot.app.state.patch_a.outputs:  # type: ignore[attr-defined]
            parts = walk.split(" → ")
            assert len(parts) == 4  # walk_length + 1 syllables (start + 3 steps)


@pytest.mark.asyncio
async def test_output_display_updates(sample_corpus):
    """Test that output label gets updated after generation."""
    app = SyllableWalkerApp()
    async with app.run_test() as pilot:
        # Load corpus (set all required fields for is_ready_for_generation())
        pilot.app.state.patch_a.corpus_dir = Path("/tmp/test_corpus")  # type: ignore[attr-defined]
        pilot.app.state.patch_a.annotated_data = sample_corpus  # type: ignore[attr-defined]
        pilot.app.state.patch_a.syllables = ["ka", "ki", "ta"]  # type: ignore[attr-defined]
        pilot.app.state.patch_a.frequencies = {"ka": 100, "ki": 80, "ta": 90}  # type: ignore[attr-defined]

        # Get output label before generation
        output_label = pilot.app.query_one("#output-A")  # type: ignore[attr-defined]
        initial_text = str(output_label.render())

        # Generate using direct method call (button may be scrolled out of view)
        pilot.app._generate_walks_for_patch("A")  # type: ignore[attr-defined]
        await pilot.pause(2.0)

        # Check that output label changed
        final_text = str(output_label.render())
        assert final_text != initial_text
        assert "→" in final_text
