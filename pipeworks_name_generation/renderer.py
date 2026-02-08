"""Minimal, deterministic name rendering helpers.

This module provides optional post-processing for generated names. It focuses on
simple casing transforms so consumers can request a consistent presentation
without mutating the underlying source data. Advanced linguistic styling (for
example language-specific title casing rules) should live in higher-level
applications.
"""

from __future__ import annotations

from typing import Sequence

# Explicitly enumerated render styles keep API validation deterministic.
RENDER_STYLES: set[str] = {"raw", "lower", "upper", "title", "sentence"}


def normalize_render_style(raw_style: str | None) -> str:
    """Normalize and validate a render style value.

    Args:
        raw_style: User-supplied style string. ``None`` or blanks mean ``raw``.

    Returns:
        Canonical render style key.

    Raises:
        ValueError: If the style is not recognized.
    """
    if raw_style is None:
        return "raw"

    normalized = str(raw_style).strip().lower()
    if not normalized:
        return "raw"
    if normalized not in RENDER_STYLES:
        allowed = ", ".join(sorted(RENDER_STYLES))
        raise ValueError(f"Unknown render style: {raw_style!r}. Allowed: {allowed}.")
    return normalized


def render_name(name: str, style: str | None = None) -> str:
    """Render a single name using the requested style.

    Args:
        name: Input name string.
        style: Optional render style. ``None`` defaults to ``raw``.

    Returns:
        Rendered name string.
    """
    normalized = normalize_render_style(style)
    if normalized == "raw":
        return name
    if normalized == "lower":
        return name.lower()
    if normalized == "upper":
        return name.upper()
    if normalized == "sentence":
        if not name:
            return name
        return name[:1].upper() + name[1:].lower()

    # ``title`` uses Python's built-in title-casing. This is intentionally
    # simple and deterministic for a minimal renderer.
    return name.title()


def render_names(names: Sequence[str], style: str | None = None) -> list[str]:
    """Render a list of names with the requested style.

    Args:
        names: Sequence of input names.
        style: Optional render style. ``None`` defaults to ``raw``.

    Returns:
        New list of rendered names.
    """
    normalized = normalize_render_style(style)
    if normalized == "raw":
        return list(names)

    # Delegate to ``render_name`` so single-name logic stays centralized.
    return [render_name(name, normalized) for name in names]


__all__ = ["RENDER_STYLES", "normalize_render_style", "render_name", "render_names"]
