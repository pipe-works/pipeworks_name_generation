"""Tests for minimal name renderer helpers."""

from __future__ import annotations

import pytest

from pipeworks_name_generation.renderer import (
    RENDER_STYLES,
    normalize_render_style,
    render_name,
    render_names,
)


def test_normalize_render_style_defaults_and_validation() -> None:
    """Normalizer should default to raw and reject unknown styles."""
    assert normalize_render_style(None) == "raw"
    assert normalize_render_style("") == "raw"
    assert normalize_render_style("  ") == "raw"
    assert normalize_render_style("UPPER") == "upper"

    with pytest.raises(ValueError):
        normalize_render_style("glitter")


def test_render_name_styles() -> None:
    """Render helper should apply known casing transformations."""
    name = "goblin-flower"

    assert render_name(name, "raw") == name
    assert render_name(name, "lower") == "goblin-flower"
    assert render_name(name, "upper") == "GOBLIN-FLOWER"
    assert render_name(name, "sentence") == "Goblin-flower"
    assert render_name(name, "title") == "Goblin-Flower"


def test_render_names_bulk() -> None:
    """Bulk rendering should preserve list cardinality and order."""
    names = ["alfa", "briar"]
    rendered = render_names(names, "upper")

    assert rendered == ["ALFA", "BRIAR"]
    assert names == ["alfa", "briar"]
    assert RENDER_STYLES
