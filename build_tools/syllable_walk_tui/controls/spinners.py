"""
Integer spinner control widget - Re-export from tui_common.

**DEPRECATED**: This module re-exports IntSpinner from tui_common for
backward compatibility. New code should import directly from tui_common:

.. code-block:: python

    # Preferred
    from build_tools.tui_common.controls import IntSpinner

    # Deprecated (still works)
    from build_tools.syllable_walk_tui.controls.spinners import IntSpinner
"""

# Re-export from shared package
from build_tools.tui_common.controls.spinners import IntSpinner

__all__ = ["IntSpinner"]
