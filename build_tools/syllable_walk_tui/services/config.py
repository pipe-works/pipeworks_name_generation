"""
Configuration management for Syllable Walker TUI.

This module extends the base ``tui_common.KeybindingConfig`` with syllable_walk-specific
functionality, particularly the ``patch_bindings`` attribute for patch operations
(generate, copy, paste, reset, swap).

This is **not** a deprecated re-export - it provides genuine extensions to the base config.
Import from here when working with syllable_walk_tui:

.. code-block:: python

    from build_tools.syllable_walk_tui.services.config import KeybindingConfig, load_keybindings

For the base config without patch_bindings, use tui_common directly:

.. code-block:: python

    from build_tools.tui_common.services import KeybindingConfig as BaseKeybindingConfig
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Re-export from shared package
from build_tools.tui_common.services.config import (
    TOMLI_AVAILABLE,
    detect_conflicts,
    load_config_file,
    merge_config,
)
from build_tools.tui_common.services.config import KeybindingConfig as BaseKeybindingConfig


@dataclass
class KeybindingConfig(BaseKeybindingConfig):
    """
    Keybinding configuration for Syllable Walker TUI.

    This is a backward-compatible subclass that adds the ``patch_bindings``
    attribute expected by the syllable_walk_tui codebase.

    Attributes:
        global_bindings: Global actions (quit, help)
        tab_bindings: Tab/screen switching (patch_config, blended_walk, analysis)
        navigation_bindings: Panel/control navigation (up, down, left, right, etc.)
        control_bindings: Control manipulation (activate, increment, decrement)
        patch_bindings: Patch operations (generate, copy, paste, reset, swap)
    """

    # Syllable Walk TUI uses patch_bindings for patch-specific operations
    patch_bindings: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def default(cls) -> KeybindingConfig:
        """
        Create default keybinding configuration for Syllable Walker TUI.

        Returns:
            KeybindingConfig with sensible defaults including patch bindings
        """
        base = BaseKeybindingConfig.default()
        return cls(
            global_bindings=base.global_bindings,
            tab_bindings={
                "patch_config": ["p"],
                "blended_walk": ["b"],
                "analysis": ["a"],
            },
            navigation_bindings=base.navigation_bindings,
            control_bindings=base.control_bindings,
            action_bindings=base.action_bindings,
            patch_bindings={
                "generate": ["g", "f5"],
                "copy": ["y", "ctrl+c"],
                "paste": ["p", "ctrl+v"],
                "reset": ["r"],
                "swap": ["x"],
            },
        )

    def get_primary_key(self, context: str, action: str) -> str | None:
        """
        Get the primary (first) keybinding for an action.

        Extends base class to support 'patch' context.

        Args:
            context: Keybinding context ("global", "tabs", "navigation", "patch", etc.)
            action: Action name (e.g., "quit", "patch_config")

        Returns:
            Primary key string, or None if not found
        """
        if context == "patch":
            keys = self.patch_bindings.get(action, [])
            return keys[0] if keys else None
        return super().get_primary_key(context, action)


def load_keybindings(config_path: Path | None = None) -> KeybindingConfig:
    """
    Load keybindings from config file with fallback to defaults.

    This version returns a KeybindingConfig subclass with patch_bindings support.

    Args:
        config_path: Optional path to config file

    Returns:
        KeybindingConfig (user config merged with defaults)
    """
    defaults = KeybindingConfig.default()

    # Try to load user config
    user_config = load_config_file(config_path)

    if user_config is None:
        config = defaults
    else:
        # Extract keybindings section
        keybindings = user_config.get("keybindings", {})

        config = KeybindingConfig(
            global_bindings=keybindings.get("global", defaults.global_bindings),
            tab_bindings=keybindings.get("tabs", defaults.tab_bindings),
            navigation_bindings=keybindings.get("navigation", defaults.navigation_bindings),
            control_bindings=keybindings.get("controls", defaults.control_bindings),
            action_bindings=keybindings.get("actions", defaults.action_bindings),
            patch_bindings=keybindings.get("patch", defaults.patch_bindings),
        )

    # Check for conflicts (from shared module)
    conflicts = detect_conflicts(config)
    if conflicts:
        print("Warning: Keybinding conflicts detected:")
        for conflict in conflicts:
            print(f"  - {conflict}")

    return config


# Re-export for backward compatibility
__all__ = [
    "KeybindingConfig",
    "load_keybindings",
    "load_config_file",
    "merge_config",
    "detect_conflicts",
    "TOMLI_AVAILABLE",
]
