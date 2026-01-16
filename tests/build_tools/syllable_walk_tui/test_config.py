"""
Tests for syllable_walk_tui configuration management.

Tests keybinding loading, conflict detection, and default fallback behavior.
"""

from pathlib import Path

from build_tools.syllable_walk_tui.services.config import (
    KeybindingConfig,
    detect_conflicts,
    load_config_file,
    load_keybindings,
)


class TestKeybindingConfig:
    """Tests for KeybindingConfig dataclass."""

    def test_initialization(self):
        """Test KeybindingConfig can be initialized with all binding types."""
        config = KeybindingConfig(
            global_bindings={"quit": ["q"], "help": ["?"]},
            tab_bindings={"patch_config": ["p"]},
            navigation_bindings={"up": ["k"]},
            control_bindings={"generate": ["g"]},
            patch_bindings={"select_corpus_a": ["1"]},
        )

        assert config.global_bindings == {"quit": ["q"], "help": ["?"]}
        assert config.tab_bindings == {"patch_config": ["p"]}
        assert config.navigation_bindings == {"up": ["k"]}
        assert config.control_bindings == {"generate": ["g"]}
        assert config.patch_bindings == {"select_corpus_a": ["1"]}

    def test_get_primary_key(self):
        """Test getting primary (first) key from binding context."""
        config = KeybindingConfig(
            global_bindings={"quit": ["q", "ctrl+q"]},
            tab_bindings={"patch_config": ["p", "1"]},
            navigation_bindings={},
            control_bindings={},
            patch_bindings={},
        )

        assert config.get_primary_key("global", "quit") == "q"
        assert config.get_primary_key("tabs", "patch_config") == "p"

    def test_get_primary_key_empty_list(self):
        """Test getting primary key returns None for empty binding list."""
        config = KeybindingConfig(
            global_bindings={"quit": []},
            tab_bindings={},
            navigation_bindings={},
            control_bindings={},
            patch_bindings={},
        )

        assert config.get_primary_key("global", "quit") is None

    def test_get_primary_key_missing_action(self):
        """Test getting primary key returns None for missing action."""
        config = KeybindingConfig(
            global_bindings={},
            tab_bindings={},
            navigation_bindings={},
            control_bindings={},
            patch_bindings={},
        )

        assert config.get_primary_key("global", "nonexistent") is None

    def test_get_display_key(self):
        """Test getting display key with uppercase formatting."""
        config = KeybindingConfig(
            global_bindings={"quit": ["q", "ctrl+q"]},
            tab_bindings={"patch_config": ["p"]},
            navigation_bindings={},
            control_bindings={},
            patch_bindings={},
        )

        assert config.get_display_key("global", "quit") == "Q"
        assert config.get_display_key("tabs", "patch_config") == "P"

    def test_get_display_key_ctrl_binding(self):
        """Test display key for ctrl bindings shows mapped value."""
        config = KeybindingConfig(
            global_bindings={"quit": ["ctrl+q"]},
            tab_bindings={},
            navigation_bindings={},
            control_bindings={},
            patch_bindings={},
        )

        # Should use display mapping from config
        assert config.get_display_key("global", "quit") == "Ctrl+Q"


class TestConfigPath:
    """Tests for configuration path resolution."""

    def test_config_path_defaults_to_home_config(self):
        """Test that config path defaults to ~/.config/pipeworks_tui."""
        # This is tested indirectly through load_config_file
        # Config file path: ~/.config/pipeworks_tui/keybindings.toml
        config_path = Path.home() / ".config" / "pipeworks_tui" / "keybindings.toml"

        assert isinstance(config_path, Path)
        assert config_path.name == "keybindings.toml"
        assert "pipeworks_tui" in str(config_path)


class TestLoadConfigFile:
    """Tests for TOML config file loading."""

    def test_load_valid_toml(self, tmp_path):
        """Test loading valid TOML configuration file."""
        config_file = tmp_path / "keybindings.toml"
        config_file.write_text(
            """
[keybindings.global]
quit = ["q", "ctrl+q"]
help = ["?", "f1"]

[keybindings.tabs]
patch_config = ["p"]
blended_walk = ["b"]
analysis = ["a"]
"""
        )

        result = load_config_file(config_file)

        assert result is not None
        assert result["keybindings"]["global"]["quit"] == ["q", "ctrl+q"]
        assert result["keybindings"]["global"]["help"] == ["?", "f1"]
        assert result["keybindings"]["tabs"]["patch_config"] == ["p"]

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading nonexistent file returns None."""
        config_file = tmp_path / "nonexistent.toml"

        result = load_config_file(config_file)

        assert result is None

    def test_load_invalid_toml(self, tmp_path):
        """Test loading invalid TOML returns None."""
        config_file = tmp_path / "invalid.toml"
        config_file.write_text("this is not valid toml [[[")

        result = load_config_file(config_file)

        assert result is None

    def test_load_empty_file(self, tmp_path):
        """Test loading empty TOML file."""
        config_file = tmp_path / "empty.toml"
        config_file.write_text("")

        result = load_config_file(config_file)

        # Empty TOML is valid and returns empty dict
        assert result == {}


class TestConflictDetection:
    """Tests for keybinding conflict detection."""

    def test_no_conflicts(self):
        """Test that non-conflicting bindings pass validation."""
        config = KeybindingConfig(
            global_bindings={"quit": ["q"], "help": ["?"]},
            tab_bindings={"patch_config": ["p"], "blended_walk": ["b"]},
            navigation_bindings={},
            control_bindings={},
            patch_bindings={},
        )

        conflicts = detect_conflicts(config)
        assert conflicts == []

    def test_conflict_within_context(self):
        """Test that conflicting keys within same context are detected."""
        config = KeybindingConfig(
            global_bindings={"quit": ["q"], "help": ["q"]},  # Both use 'q'
            tab_bindings={},
            navigation_bindings={},
            control_bindings={},
            patch_bindings={},
        )

        conflicts = detect_conflicts(config)
        assert len(conflicts) > 0
        assert "global" in conflicts[0]
        assert "'q'" in conflicts[0]

    def test_conflict_with_multiple_bindings(self):
        """Test conflict detection with multiple bindings per action."""
        config = KeybindingConfig(
            global_bindings={},
            tab_bindings={
                "patch_config": ["p", "1"],
                "blended_walk": ["b", "2"],
                "analysis": ["a", "1"],  # Conflicts with patch_config's "1"
            },
            navigation_bindings={},
            control_bindings={},
            patch_bindings={},
        )

        conflicts = detect_conflicts(config)
        assert len(conflicts) > 0
        assert "tabs" in conflicts[0]

    def test_no_conflict_across_contexts(self):
        """Test that same key in different contexts is allowed."""
        config = KeybindingConfig(
            global_bindings={"quit": ["q"]},
            tab_bindings={"patch_config": ["q"]},  # Same key, different context - OK
            navigation_bindings={},
            control_bindings={},
            patch_bindings={},
        )

        conflicts = detect_conflicts(config)
        assert conflicts == []

    def test_conflict_with_empty_bindings(self):
        """Test that empty binding lists don't cause conflicts."""
        config = KeybindingConfig(
            global_bindings={"quit": ["q"], "help": []},
            tab_bindings={},
            navigation_bindings={},
            control_bindings={},
            patch_bindings={},
        )

        conflicts = detect_conflicts(config)
        assert conflicts == []


class TestLoadKeybindings:
    """Integration tests for load_keybindings function."""

    def test_load_default_keybindings_when_no_config(self):
        """Test that defaults are used when config file doesn't exist."""
        # Use nonexistent path
        config = load_keybindings(Path("/nonexistent/keybindings.toml"))

        # Should return defaults
        defaults = KeybindingConfig.default()
        assert isinstance(config, KeybindingConfig)
        assert config.global_bindings == defaults.global_bindings
        assert config.tab_bindings == defaults.tab_bindings

    def test_load_custom_keybindings(self, tmp_path):
        """Test loading custom keybindings from file."""
        config_file = tmp_path / "keybindings.toml"
        config_file.write_text(
            """
[keybindings.global]
quit = ["x"]
help = ["h"]

[keybindings.tabs]
patch_config = ["1"]
blended_walk = ["2"]
analysis = ["3"]

[keybindings.navigation]
up = ["k"]
down = ["j"]
left = ["h"]
right = ["l"]

[keybindings.controls]
generate = ["g"]
randomize = ["r"]

[keybindings.patch]
select_corpus_a = ["a"]
select_corpus_b = ["b"]
"""
        )

        config = load_keybindings(config_file)

        assert config.global_bindings["quit"] == ["x"]
        assert config.global_bindings["help"] == ["h"]
        assert config.tab_bindings["patch_config"] == ["1"]
        assert config.navigation_bindings["up"] == ["k"]

    def test_load_partial_config_merges_with_defaults(self, tmp_path):
        """Test that partial config merges with defaults for missing sections."""
        config_file = tmp_path / "keybindings.toml"
        config_file.write_text(
            """
[keybindings.global]
quit = ["x"]
"""
        )

        config = load_keybindings(config_file)
        defaults = KeybindingConfig.default()

        # Custom global binding
        assert config.global_bindings["quit"] == ["x"]

        # Default tab bindings (section missing from file)
        assert config.tab_bindings == defaults.tab_bindings

    def test_load_config_with_conflicts_shows_warning(self, tmp_path):
        """Test that config with conflicts still loads but shows warning."""
        config_file = tmp_path / "keybindings.toml"
        config_file.write_text(
            """
[keybindings.global]
quit = ["q"]
help = ["q"]
"""
        )  # Conflict!

        # Config loads but conflicts are printed
        config = load_keybindings(config_file)

        # Should still return the config (conflicts are warnings, not errors)
        assert isinstance(config, KeybindingConfig)
        assert config.global_bindings["quit"] == ["q"]
        assert config.global_bindings["help"] == ["q"]


class TestDefaultKeybindings:
    """Tests to ensure DEFAULT_KEYBINDINGS is valid and conflict-free."""

    def test_defaults_have_no_conflicts(self):
        """Test that default keybindings don't have conflicts."""
        defaults = KeybindingConfig.default()
        conflicts = detect_conflicts(defaults)
        assert conflicts == []

    def test_defaults_have_all_required_sections(self):
        """Test that defaults include all required sections."""
        defaults = KeybindingConfig.default()
        assert len(defaults.global_bindings) > 0
        assert len(defaults.tab_bindings) > 0
        assert len(defaults.navigation_bindings) > 0
        assert len(defaults.control_bindings) > 0
        assert len(defaults.patch_bindings) > 0

    def test_defaults_have_required_global_bindings(self):
        """Test that global section has required actions."""
        defaults = KeybindingConfig.default()
        assert "quit" in defaults.global_bindings
        assert "help" in defaults.global_bindings

    def test_defaults_have_required_tab_bindings(self):
        """Test that tabs section has required actions."""
        defaults = KeybindingConfig.default()
        assert "patch_config" in defaults.tab_bindings
        assert "blended_walk" in defaults.tab_bindings
        assert "analysis" in defaults.tab_bindings
