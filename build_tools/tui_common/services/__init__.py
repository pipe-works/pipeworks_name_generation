"""
Shared Services for Textual-based TUIs.

This module provides backend services for configuration management,
keybinding loading, and other non-UI functionality.

**Available Services:**

- :class:`KeybindingConfig` - Dataclass holding keybinding configuration
- :func:`load_keybindings` - Load keybindings from TOML with defaults
- :func:`detect_conflicts` - Validate keybindings for conflicts

**Configuration Pattern:**

.. code-block:: python

    from build_tools.tui_common.services import load_keybindings

    # Load from default location (~/.config/pipeworks_tui/keybindings.toml)
    config = load_keybindings()

    # Get primary key for an action
    quit_key = config.get_primary_key("global", "quit")  # "q"

    # Get display-friendly key name
    quit_display = config.get_display_key("global", "quit")  # "q"
"""

from build_tools.tui_common.services.config import (
    KeybindingConfig,
    detect_conflicts,
    load_config_file,
    load_keybindings,
    merge_config,
)

__all__ = [
    "KeybindingConfig",
    "load_keybindings",
    "load_config_file",
    "merge_config",
    "detect_conflicts",
]
