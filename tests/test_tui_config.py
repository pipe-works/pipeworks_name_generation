"""
Tests for syllable_walk_tui configuration management.

Tests configuration persistence, keybindings, and path resolution.
"""

import tempfile
from pathlib import Path

import pytest

from build_tools.syllable_walk_tui.config import TUIConfig, get_project_root


class TestProjectRoot:
    """Tests for project root resolution."""

    def test_get_project_root_returns_valid_path(self):
        """Project root should be a valid existing directory."""
        root = get_project_root()
        assert root.exists()
        assert root.is_dir()

    def test_get_project_root_contains_build_tools(self):
        """Project root should contain the build_tools directory."""
        root = get_project_root()
        assert (root / "build_tools").exists()

    def test_get_project_root_is_absolute(self):
        """Project root should be an absolute path."""
        root = get_project_root()
        assert root.is_absolute()


class TestTUIConfig:
    """Tests for TUIConfig class."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_path = Path(f.name)
        yield config_path
        # Cleanup
        if config_path.exists():
            config_path.unlink()

    def test_config_creates_with_defaults(self, temp_config_file):
        """Config should initialize with default values."""
        config = TUIConfig(config_path=temp_config_file)
        assert config.data is not None
        assert "last_corpus_directory" in config.data
        assert "keybindings" in config.data

    def test_config_saves_and_loads(self, temp_config_file):
        """Config should persist to disk and reload correctly."""
        # Create and save config
        config1 = TUIConfig(config_path=temp_config_file)
        config1.set_last_corpus("/some/path.json", "pyphen")
        config1.save()

        # Load config from same file
        config2 = TUIConfig(config_path=temp_config_file)
        assert config2.data["last_corpus_path"] == "/some/path.json"
        assert config2.data["last_corpus_type"] == "pyphen"

    def test_default_keybindings_exist(self, temp_config_file):
        """Default keybindings should be configured."""
        config = TUIConfig(config_path=temp_config_file)
        keybindings = config.get_keybindings()

        # Check essential keybindings
        assert "quit" in keybindings
        assert "help" in keybindings
        assert "navigate_up" in keybindings
        assert "navigate_down" in keybindings

    def test_default_keybindings_include_hjkl(self, temp_config_file):
        """Default keybindings should include hjkl navigation."""
        config = TUIConfig(config_path=temp_config_file)
        keybindings = config.get_keybindings()

        # Check hjkl keys are present
        assert "k" in keybindings["navigate_up"]
        assert "j" in keybindings["navigate_down"]
        assert "h" in keybindings["navigate_left"]
        assert "l" in keybindings["navigate_right"]

    def test_default_keybindings_include_arrows(self, temp_config_file):
        """Default keybindings should include arrow keys."""
        config = TUIConfig(config_path=temp_config_file)
        keybindings = config.get_keybindings()

        # Check arrow keys are present
        assert "up" in keybindings["navigate_up"]
        assert "down" in keybindings["navigate_down"]
        assert "left" in keybindings["navigate_left"]
        assert "right" in keybindings["navigate_right"]

    def test_set_keybinding(self, temp_config_file):
        """Should be able to customize keybindings."""
        config = TUIConfig(config_path=temp_config_file)
        config.set_keybinding("quit", "ctrl+c")

        keybindings = config.get_keybindings()
        assert keybindings["quit"] == "ctrl+c"

    def test_set_keybinding_persists(self, temp_config_file):
        """Customized keybindings should persist to disk."""
        config1 = TUIConfig(config_path=temp_config_file)
        config1.set_keybinding("quit", "ctrl+c")

        # Reload from disk
        config2 = TUIConfig(config_path=temp_config_file)
        keybindings = config2.get_keybindings()
        assert keybindings["quit"] == "ctrl+c"

    def test_get_last_corpus_directory_default(self, temp_config_file):
        """Default corpus directory should be project_root/_working/output."""
        config = TUIConfig(config_path=temp_config_file)
        directory = config.get_last_corpus_directory()

        assert "_working/output" in directory
        # Should be an absolute path
        assert Path(directory).is_absolute()

    def test_set_last_corpus_updates_directory(self, temp_config_file):
        """Setting last corpus should update the directory."""
        config = TUIConfig(config_path=temp_config_file)
        corpus_path = "/some/dir/data/corpus.json"
        config.set_last_corpus(corpus_path, "pyphen")

        # Directory should be updated to parent of corpus file
        assert config.get_last_corpus_directory() == "/some/dir/data"

    def test_get_last_corpus_returns_none_initially(self, temp_config_file):
        """get_last_corpus should return None when no corpus has been loaded."""
        config = TUIConfig(config_path=temp_config_file)
        assert config.get_last_corpus() is None

    def test_get_last_corpus_returns_info(self, temp_config_file):
        """get_last_corpus should return path and type info."""
        config = TUIConfig(config_path=temp_config_file)
        config.set_last_corpus("/some/corpus.json", "nltk")

        corpus_info = config.get_last_corpus()
        assert corpus_info is not None
        assert corpus_info["path"] == "/some/corpus.json"
        assert corpus_info["type"] == "nltk"

    def test_corrupted_config_falls_back_to_defaults(self, temp_config_file):
        """Corrupted config file should fall back to defaults."""
        # Write invalid JSON
        with open(temp_config_file, "w") as f:
            f.write("{ invalid json }")

        # Should not crash, should use defaults
        config = TUIConfig(config_path=temp_config_file)
        assert config.data is not None
        assert "keybindings" in config.data

    def test_multiple_keys_format(self, temp_config_file):
        """Keybindings should support multiple keys (comma-separated)."""
        config = TUIConfig(config_path=temp_config_file)
        keybindings = config.get_keybindings()

        # Check that navigate_up has multiple keys
        nav_up = keybindings["navigate_up"]
        assert "," in nav_up  # Should be comma-separated
        keys = [k.strip() for k in nav_up.split(",")]
        assert len(keys) >= 2  # Should have at least 2 keys
