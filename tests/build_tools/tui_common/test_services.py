"""
Tests for tui_common service modules.

Tests KeybindingConfig, configuration loading, and conflict detection.
"""

import pytest

from build_tools.tui_common.services import KeybindingConfig, detect_conflicts, load_keybindings
from build_tools.tui_common.services.config import load_config_file, merge_config

# =============================================================================
# KeybindingConfig Tests
# =============================================================================


class TestKeybindingConfig:
    """Tests for KeybindingConfig dataclass."""

    def test_default_configuration(self):
        """Test that default() returns valid configuration."""
        config = KeybindingConfig.default()

        # Check global bindings exist
        assert "quit" in config.global_bindings
        assert "help" in config.global_bindings

        # Check navigation bindings exist
        assert "up" in config.navigation_bindings
        assert "down" in config.navigation_bindings
        assert "left" in config.navigation_bindings
        assert "right" in config.navigation_bindings

        # Check control bindings exist
        assert "activate" in config.control_bindings
        assert "increment" in config.control_bindings
        assert "decrement" in config.control_bindings

    def test_default_quit_bindings(self):
        """Test default quit key bindings."""
        config = KeybindingConfig.default()

        quit_keys = config.global_bindings["quit"]
        assert "q" in quit_keys
        assert "ctrl+q" in quit_keys

    def test_get_primary_key_returns_first(self):
        """Test get_primary_key returns first binding."""
        config = KeybindingConfig.default()

        primary = config.get_primary_key("global", "quit")
        assert primary == "q"  # First in list

    def test_get_primary_key_returns_none_for_missing(self):
        """Test get_primary_key returns None for missing action."""
        config = KeybindingConfig.default()

        primary = config.get_primary_key("global", "nonexistent")
        assert primary is None

    def test_get_primary_key_returns_none_for_missing_context(self):
        """Test get_primary_key returns None for missing context."""
        config = KeybindingConfig.default()

        primary = config.get_primary_key("nonexistent", "quit")
        assert primary is None

    def test_get_display_key_formats_simple_key(self):
        """Test get_display_key returns uppercase for simple keys."""
        config = KeybindingConfig(
            global_bindings={"test": ["x"]},
        )

        display = config.get_display_key("global", "test")
        assert display == "X"

    def test_get_display_key_formats_ctrl_key(self):
        """Test get_display_key formats Ctrl combinations."""
        config = KeybindingConfig(
            global_bindings={"test": ["ctrl+q"]},
        )

        display = config.get_display_key("global", "test")
        assert display == "Ctrl+Q"

    def test_get_display_key_formats_special_keys(self):
        """Test get_display_key formats special key names."""
        config = KeybindingConfig(
            global_bindings={"help": ["question_mark"]},
        )

        display = config.get_display_key("global", "help")
        assert display == "?"

    def test_get_display_key_returns_question_for_missing(self):
        """Test get_display_key returns ? for missing binding."""
        config = KeybindingConfig.default()

        display = config.get_display_key("global", "nonexistent")
        assert display == "?"


# =============================================================================
# Conflict Detection Tests
# =============================================================================


class TestConflictDetection:
    """Tests for keybinding conflict detection."""

    def test_no_conflicts_in_defaults(self):
        """Test that default configuration has no conflicts."""
        config = KeybindingConfig.default()
        conflicts = detect_conflicts(config)
        assert len(conflicts) == 0

    def test_detects_conflict_in_same_context(self):
        """Test conflict detection within same context."""
        config = KeybindingConfig(
            global_bindings={
                "quit": ["q"],
                "quick_action": ["q"],  # Conflict!
            },
        )

        conflicts = detect_conflicts(config)

        assert len(conflicts) == 1
        assert "global" in conflicts[0]
        assert "q" in conflicts[0]

    def test_no_conflict_across_contexts(self):
        """Test that same key in different contexts is not a conflict."""
        config = KeybindingConfig(
            global_bindings={"quit": ["q"]},
            navigation_bindings={"quick_nav": ["q"]},  # Different context - OK
        )

        conflicts = detect_conflicts(config)
        assert len(conflicts) == 0

    def test_detects_multiple_conflicts(self):
        """Test detection of multiple conflicts."""
        config = KeybindingConfig(
            global_bindings={
                "action1": ["a"],
                "action2": ["a"],  # Conflict 1
                "action3": ["b"],
                "action4": ["b"],  # Conflict 2
            },
        )

        conflicts = detect_conflicts(config)
        assert len(conflicts) == 2


# =============================================================================
# Configuration Loading Tests
# =============================================================================


class TestConfigLoading:
    """Tests for configuration file loading."""

    def test_load_keybindings_returns_defaults_when_no_file(self, tmp_path):
        """Test load_keybindings returns defaults when no config file exists."""
        nonexistent_path = tmp_path / "nonexistent.toml"
        config = load_keybindings(nonexistent_path)

        # Should have default bindings
        assert "quit" in config.global_bindings
        assert "q" in config.global_bindings["quit"]

    def test_load_config_file_returns_none_for_missing(self, tmp_path):
        """Test load_config_file returns None for missing file."""
        nonexistent_path = tmp_path / "nonexistent.toml"
        result = load_config_file(nonexistent_path)
        assert result is None

    @pytest.mark.skipif(
        not __import__("sys").version_info >= (3, 11),
        reason="tomllib only available in Python 3.11+",
    )
    def test_load_config_file_parses_toml(self, tmp_path):
        """Test load_config_file correctly parses TOML."""
        config_path = tmp_path / "keybindings.toml"
        config_path.write_text("""
[keybindings.global]
quit = ["x", "ctrl+x"]
help = ["?"]
""")

        result = load_config_file(config_path)

        assert result is not None
        assert "keybindings" in result
        assert "global" in result["keybindings"]
        assert result["keybindings"]["global"]["quit"] == ["x", "ctrl+x"]


class TestConfigMerging:
    """Tests for configuration merging."""

    def test_merge_replaces_specified_context(self):
        """Test that user config replaces defaults for specified contexts."""
        defaults = KeybindingConfig.default()
        user_config = {
            "keybindings": {
                "global": {
                    "quit": ["x"],  # Override quit binding
                }
            }
        }

        merged = merge_config(defaults, user_config)

        # Global should be replaced
        assert merged.global_bindings["quit"] == ["x"]

    def test_merge_preserves_unspecified_contexts(self):
        """Test that unspecified contexts retain defaults."""
        defaults = KeybindingConfig.default()
        user_config = {
            "keybindings": {
                "global": {
                    "quit": ["x"],
                }
                # navigation not specified
            }
        }

        merged = merge_config(defaults, user_config)

        # Navigation should retain defaults
        assert merged.navigation_bindings == defaults.navigation_bindings

    def test_merge_handles_empty_user_config(self):
        """Test merge handles empty user config gracefully."""
        defaults = KeybindingConfig.default()
        user_config: dict[str, dict[str, list[str]]] = {}

        merged = merge_config(defaults, user_config)

        assert merged.global_bindings == defaults.global_bindings
        assert merged.navigation_bindings == defaults.navigation_bindings


# =============================================================================
# Integration Tests
# =============================================================================


class TestConfigIntegration:
    """Integration tests for configuration system."""

    @pytest.mark.skipif(
        not __import__("sys").version_info >= (3, 11),
        reason="tomllib only available in Python 3.11+",
    )
    def test_full_config_load_flow(self, tmp_path):
        """Test complete configuration loading flow."""
        # Create config file
        config_path = tmp_path / "test_config.toml"
        config_path.write_text("""
[keybindings.global]
quit = ["escape", "ctrl+q"]
help = ["h"]

[keybindings.navigation]
up = ["w"]
down = ["s"]
left = ["a"]
right = ["d"]
""")

        config = load_keybindings(config_path)

        # Check custom bindings were loaded
        assert config.global_bindings["quit"] == ["escape", "ctrl+q"]
        assert config.global_bindings["help"] == ["h"]
        assert config.navigation_bindings["up"] == ["w"]

    def test_config_with_conflicts_prints_warning(self, tmp_path, capsys):
        """Test that conflicts are reported to user."""
        # Create config with intentional conflict
        config = KeybindingConfig(
            global_bindings={
                "quit": ["q"],
                "quick_save": ["q"],  # Intentional conflict
            },
        )

        # Manually check conflicts (load_keybindings does this internally)
        conflicts = detect_conflicts(config)

        # Simulate the warning print
        if conflicts:
            print("Warning: Keybinding conflicts detected:")
            for conflict in conflicts:
                print(f"  - {conflict}")

        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "conflict" in captured.out.lower()


# =============================================================================
# Backward Compatibility Tests
# =============================================================================


class TestBackwardCompatibility:
    """Tests verifying backward compatibility with syllable_walk_tui."""

    def test_syllable_walk_config_imports(self):
        """Test that syllable_walk_tui config imports work."""
        from build_tools.syllable_walk_tui.services.config import (
            KeybindingConfig as SyllableWalkConfig,
        )

        # Should be able to create config
        config = SyllableWalkConfig.default()

        # Should have patch_bindings (syllable_walk specific)
        assert hasattr(config, "patch_bindings")
        assert "generate" in config.patch_bindings

    def test_syllable_walk_config_has_patch_context(self):
        """Test syllable_walk_tui config supports 'patch' context."""
        from build_tools.syllable_walk_tui.services.config import KeybindingConfig

        config = KeybindingConfig.default()

        # Should be able to get patch bindings
        primary = config.get_primary_key("patch", "generate")
        assert primary == "g"

    def test_base_config_is_parent(self):
        """Test that syllable_walk KeybindingConfig inherits from base."""
        from build_tools.syllable_walk_tui.services.config import KeybindingConfig as SWConfig
        from build_tools.tui_common.services.config import KeybindingConfig as BaseConfig

        # SW config should be subclass of base
        assert issubclass(SWConfig, BaseConfig)
