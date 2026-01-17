"""
Seed input and profile option widgets - Re-export from tui_common.

**DEPRECATED**: This module re-exports SeedInput and ProfileOption from
tui_common for backward compatibility. New code should import directly
from tui_common:

.. code-block:: python

    # Preferred
    from build_tools.tui_common.controls import SeedInput, RadioOption

    # Deprecated (still works)
    from build_tools.syllable_walk_tui.controls.inputs import SeedInput, ProfileOption

**Note**: ProfileOption has been renamed to RadioOption in tui_common.
ProfileOption is still available here as an alias for backward compatibility.
"""

# Re-export from shared package
from build_tools.tui_common.controls.inputs import RadioOption, SeedInput

# ProfileOption is an alias for RadioOption (backward compatibility)
ProfileOption = RadioOption

__all__ = ["SeedInput", "ProfileOption", "RadioOption"]
