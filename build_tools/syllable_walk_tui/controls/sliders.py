"""
Float slider control widget - Re-export from tui_common.

**DEPRECATED**: This module re-exports FloatSlider from tui_common for
backward compatibility. New code should import directly from tui_common:

.. code-block:: python

    # Preferred
    from build_tools.tui_common.controls import FloatSlider

    # Deprecated (still works)
    from build_tools.syllable_walk_tui.controls.sliders import FloatSlider
"""

# Re-export from shared package
from build_tools.tui_common.controls.sliders import FloatSlider

__all__ = ["FloatSlider"]
