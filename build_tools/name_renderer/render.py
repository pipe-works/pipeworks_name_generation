"""
Name rendering for human readability.

This module provides pure presentation functions for rendering names.
It is a "presentation lens" - deterministic, reversible, and side-effect free.

Key Design Principles:
    - Does NOT influence generation, selection, or policy
    - All operations are deterministic and reversible
    - No file I/O, no global state, no hidden configuration
    - Safe to remove or replace without affecting any outputs

The renderer improves human readability only. If a name looks "wrong",
the correct fix is policy or selection, not rendering.
"""

from typing import Literal

# Valid style types for type checking
StyleType = Literal["title", "upper", "lower"]

# Available rendering styles
AVAILABLE_STYLES: list[str] = ["title", "upper", "lower"]


def render(name: str, name_class: str, *, style: str = "title") -> str:
    """
    Render a name for human display.

    Applies presentation styling to a raw name without modifying
    its structure or content. The name_class parameter is available
    for future name-class-aware rendering rules.

    Args:
        name: Raw name string (typically lowercase from selector)
        name_class: Name class used for selection (first_name, last_name, etc.)
                   Currently unused but reserved for future styling rules.
        style: Presentation style to apply:
               - "title": Title Case (default) - "orma" -> "Orma"
               - "upper": UPPERCASE - "orma" -> "ORMA"
               - "lower": lowercase - "Orma" -> "orma"

    Returns:
        Rendered name string with styling applied.
        Empty string if input is empty.

    Examples:
        >>> render("orma", "first_name")
        'Orma'
        >>> render("striden", "last_name", style="upper")
        'STRIDEN'
        >>> render("ORMA", "first_name", style="lower")
        'orma'

    Note:
        The name_class parameter is intentionally unused in this initial
        implementation. It provides a hook for future name-class-aware
        styling (e.g., organisations in CAPS, first names in Title Case).
    """
    # Handle empty input
    if not name:
        return ""

    # Apply style transformation
    if style == "title":
        return name.title()
    elif style == "upper":
        return name.upper()
    elif style == "lower":
        return name.lower()
    else:
        # Unknown style - default to title case
        return name.title()


def render_full_name(first: str, last: str, *, style: str = "title") -> str:
    """
    Combine and render a full name (first + last).

    Creates a properly formatted full name by combining first and last
    name components with appropriate spacing and styling.

    Args:
        first: First name (raw string, typically lowercase)
        last: Last name (raw string, typically lowercase)
        style: Presentation style to apply to both names:
               - "title": Title Case (default)
               - "upper": UPPERCASE
               - "lower": lowercase

    Returns:
        Combined and rendered full name.
        Handles missing components gracefully (returns just the present name).
        Returns empty string if both inputs are empty.

    Examples:
        >>> render_full_name("orma", "striden")
        'Orma Striden'
        >>> render_full_name("orma", "striden", style="upper")
        'ORMA STRIDEN'
        >>> render_full_name("orma", "")
        'Orma'
        >>> render_full_name("", "striden")
        'Striden'

    Note:
        This function is designed for the common "FirstName LastName"
        pattern. For more complex name structures (middle names, suffixes),
        consider extending with additional parameters.
    """
    # Render each component (empty strings handled by render())
    rendered_first = render(first, "first_name", style=style)
    rendered_last = render(last, "last_name", style=style)

    # Combine with space, handling missing components
    if rendered_first and rendered_last:
        return f"{rendered_first} {rendered_last}"
    elif rendered_first:
        return rendered_first
    elif rendered_last:
        return rendered_last
    else:
        return ""


def get_available_styles() -> list[str]:
    """
    Return list of available rendering styles.

    Provides the list of valid style names that can be passed
    to render() and render_full_name().

    Returns:
        List of style names: ["title", "upper", "lower"]

    Example:
        >>> get_available_styles()
        ['title', 'upper', 'lower']
    """
    return AVAILABLE_STYLES.copy()


def get_style_description(style: str) -> str:
    """
    Get human-readable description of a rendering style.

    Useful for UI display when showing style options to users.

    Args:
        style: Style name (title, upper, lower)

    Returns:
        Human-readable description of the style.
        Returns "Unknown style" for invalid inputs.

    Examples:
        >>> get_style_description("title")
        'Title Case (Orma)'
        >>> get_style_description("upper")
        'UPPERCASE (ORMA)'
    """
    descriptions = {
        "title": "Title Case (Orma)",
        "upper": "UPPERCASE (ORMA)",
        "lower": "lowercase (orma)",
    }
    return descriptions.get(style, "Unknown style")
