"""pipeworks_name_generation - Phonetically-grounded name generation.

This is the proof of concept version with minimal functionality.
"""

from pipeworks_name_generation.generator import NameGenerator
from pipeworks_name_generation.renderer import (
    RENDER_STYLES,
    normalize_render_style,
    render_name,
    render_names,
)

__all__ = [
    "NameGenerator",
    "RENDER_STYLES",
    "normalize_render_style",
    "render_name",
    "render_names",
]
__version__ = "0.5.17"
