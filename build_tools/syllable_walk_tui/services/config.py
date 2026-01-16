"""
Configuration management for Syllable Walker TUI.

This module handles loading and validating user-configurable keybindings
from TOML files, with fallback to sensible defaults.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Python 3.11+ has tomllib built-in, otherwise use tomli
if sys.version_info >= (3, 11):
    import tomllib as tomli

    TOMLI_AVAILABLE = True
else:
    try:
        import tomli

        TOMLI_AVAILABLE = True
    except ImportError:
        TOMLI_AVAILABLE = False
        tomli = None  # type: ignore


@dataclass
class KeybindingConfig:
    """
    Keybinding configuration for the TUI application.

    Attributes:
        global_bindings: Global actions (quit, help)
        tab_bindings: Tab/screen switching (patch_config, blended_walk, analysis)
        navigation_bindings: Panel/control navigation (up, down, left, right, etc.)
        control_bindings: Control manipulation (activate, increment, decrement)
        patch_bindings: Patch operations (generate, copy, paste, reset, swap)
    """

    global_bindings: dict[str, list[str]] = field(default_factory=dict)
    tab_bindings: dict[str, list[str]] = field(default_factory=dict)
    navigation_bindings: dict[str, list[str]] = field(default_factory=dict)
    control_bindings: dict[str, list[str]] = field(default_factory=dict)
    patch_bindings: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def default(cls) -> "KeybindingConfig":
        """
        Create default keybinding configuration.

        Returns:
            KeybindingConfig with sensible defaults
        """
        return cls(
            global_bindings={
                "quit": ["q", "ctrl+q"],
                "help": ["question_mark", "f1"],
            },
            tab_bindings={
                "patch_config": ["p"],
                "blended_walk": ["b"],
                "analysis": ["a"],
            },
            navigation_bindings={
                "up": ["k", "up"],
                "down": ["j", "down"],
                "left": ["h", "left"],
                "right": ["l", "right"],
                "next_panel": ["tab", "ctrl+n"],
                "prev_panel": ["shift+tab", "ctrl+p"],
            },
            control_bindings={
                "activate": ["enter", "space"],
                "increment": ["plus", "equal", "right_square_bracket"],
                "decrement": ["minus", "left_square_bracket"],
            },
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

        Args:
            context: Keybinding context ("global", "tabs", "navigation", etc.)
            action: Action name (e.g., "quit", "patch_config")

        Returns:
            Primary key string, or None if not found
        """
        bindings_map = {
            "global": self.global_bindings,
            "tabs": self.tab_bindings,
            "navigation": self.navigation_bindings,
            "controls": self.control_bindings,
            "patch": self.patch_bindings,
        }

        bindings = bindings_map.get(context, {})
        keys = bindings.get(action, [])
        return keys[0] if keys else None

    def get_display_key(self, context: str, action: str) -> str:
        """
        Get human-readable key name for display in UI.

        Args:
            context: Keybinding context
            action: Action name

        Returns:
            Display-friendly key name (e.g., "q", "Ctrl+Q", "Enter")
        """
        key = self.get_primary_key(context, action)
        if not key:
            return "?"

        # Convert Textual key names to display-friendly names
        key_display_map = {
            "question_mark": "?",
            "ctrl+q": "Ctrl+Q",
            "ctrl+c": "Ctrl+C",
            "ctrl+v": "Ctrl+V",
            "ctrl+n": "Ctrl+N",
            "ctrl+p": "Ctrl+P",
            "f1": "F1",
            "f5": "F5",
            "enter": "Enter",
            "space": "Space",
            "tab": "Tab",
            "shift+tab": "Shift+Tab",
            "plus": "+",
            "equal": "=",
            "minus": "-",
            "left_square_bracket": "[",
            "right_square_bracket": "]",
            "up": "↑",
            "down": "↓",
            "left": "←",
            "right": "→",
        }

        return key_display_map.get(key, key.upper())


def detect_conflicts(config: KeybindingConfig) -> list[str]:
    """
    Detect conflicting keybindings within each context.

    Args:
        config: Keybinding configuration to validate

    Returns:
        List of conflict warning messages (empty if no conflicts)
    """
    conflicts = []

    contexts = {
        "global": config.global_bindings,
        "tabs": config.tab_bindings,
        "navigation": config.navigation_bindings,
        "controls": config.control_bindings,
        "patch": config.patch_bindings,
    }

    for context_name, bindings in contexts.items():
        seen: dict[str, str] = {}

        for action, keys in bindings.items():
            for key in keys:
                if key in seen:
                    conflicts.append(
                        f"Conflict in '{context_name}': key '{key}' is bound to both "
                        f"'{action}' and '{seen[key]}'"
                    )
                else:
                    seen[key] = action

    return conflicts


def load_config_file(config_path: Path | None = None) -> dict[str, Any] | None:
    """
    Load keybinding configuration from TOML file.

    Args:
        config_path: Path to config file, or None to use default location
                     (~/.config/pipeworks_tui/keybindings.toml)

    Returns:
        Parsed TOML configuration as dict, or None if file doesn't exist
        or tomli is not available
    """
    if not TOMLI_AVAILABLE:
        return None

    if config_path is None:
        config_dir = Path.home() / ".config" / "pipeworks_tui"
        config_path = config_dir / "keybindings.toml"

    if not config_path.exists():
        return None

    try:
        with open(config_path, "rb") as f:
            return tomli.load(f)
    except Exception as e:
        print(f"Warning: Failed to load config from {config_path}: {e}")
        return None


def merge_config(defaults: KeybindingConfig, user_config: dict[str, Any]) -> KeybindingConfig:
    """
    Merge user configuration with defaults.

    Args:
        defaults: Default keybinding configuration
        user_config: User-provided configuration from TOML file

    Returns:
        Merged configuration (user overrides defaults)
    """
    # Extract keybindings section
    keybindings = user_config.get("keybindings", {})

    # Merge each context
    merged = KeybindingConfig(
        global_bindings=keybindings.get("global", defaults.global_bindings),
        tab_bindings=keybindings.get("tabs", defaults.tab_bindings),
        navigation_bindings=keybindings.get("navigation", defaults.navigation_bindings),
        control_bindings=keybindings.get("controls", defaults.control_bindings),
        patch_bindings=keybindings.get("patch", defaults.patch_bindings),
    )

    return merged


def load_keybindings(config_path: Path | None = None) -> KeybindingConfig:
    """
    Load keybindings from config file with fallback to defaults.

    Args:
        config_path: Optional path to config file

    Returns:
        Keybinding configuration (user config merged with defaults)

    Note:
        If config file doesn't exist or has errors, returns defaults.
        Prints conflicts to stderr if detected.
    """
    defaults = KeybindingConfig.default()

    # Try to load user config
    user_config = load_config_file(config_path)

    if user_config is None:
        # No user config, use defaults
        config = defaults
    else:
        # Merge user config with defaults
        config = merge_config(defaults, user_config)

    # Check for conflicts
    conflicts = detect_conflicts(config)
    if conflicts:
        print("Warning: Keybinding conflicts detected:")
        for conflict in conflicts:
            print(f"  - {conflict}")

    return config
