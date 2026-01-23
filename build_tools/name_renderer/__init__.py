"""
Name Renderer - Presentation layer for generated names.

A presentation lens that improves human readability without
affecting generation, selection, or policy. This module sits
downstream of selection and is consumed by presentation layers
(TUIs, web UIs, export tools).

Architectural Position:
    Corpus -> Syllables -> Candidates -> Selection -> (Renderer) -> Display

Key Property:
    Removing the renderer must not change any generated or selected output.

Design Principles:
    - Deterministic: Same input always produces same output
    - Reversible: Original name can be recovered (it's just casing)
    - Side-effect free: No file I/O, no global state
    - Safe to remove: Does not alter system truth

Usage:
    >>> from build_tools.name_renderer import render, render_full_name
    >>> render("orma", "first_name")
    'Orma'
    >>> render("striden", "last_name", style="upper")
    'STRIDEN'
    >>> render_full_name("orma", "striden")
    'Orma Striden'

Available Styles:
    - "title": Title Case (default) - "orma" -> "Orma"
    - "upper": UPPERCASE - "orma" -> "ORMA"
    - "lower": lowercase - "Orma" -> "orma"

See Also:
    - data/name_classes.yml for selection policy rules
    - build_tools/name_selector for selection logic
"""

from build_tools.name_renderer.render import (
    get_available_styles,
    get_style_description,
    render,
    render_full_name,
)

__all__ = [
    "render",
    "render_full_name",
    "get_available_styles",
    "get_style_description",
]

__version__ = "0.1.0"
