"""
Renderer module for name presentation.

Provides the RenderScreen modal for viewing selected names with
proper styling and formatting. Consumes build_tools.name_renderer
for rendering logic.

Usage::

    The RenderScreen is opened via the 'r' keybinding from the main
    TUI view. It displays names from both patches with:
    - Title case (default) or other styles
    - Combined full name view (A first + B last)

Keybindings::
    r: Open render screen (from main view)
    s: Cycle rendering style (title/upper/lower)
    c: Toggle combined names panel
    q/Esc: Close and return to main view
"""

from build_tools.syllable_walk_tui.modules.renderer.screen import RenderScreen

__all__ = ["RenderScreen"]
