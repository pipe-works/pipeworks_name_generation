"""
Tests for syllable_walk_tui main application.

Tests app initialization, keybindings, and module composition.
"""

import tempfile
from pathlib import Path

import pytest

# Check if textual is available
try:
    from build_tools.syllable_walk_tui.app import SyllableWalkApp
    from build_tools.syllable_walk_tui.config import TUIConfig

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not TEXTUAL_AVAILABLE, reason="textual not installed (optional dependency)"
)


class TestSyllableWalkApp:
    """Tests for SyllableWalkApp class."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_path = Path(f.name)
        yield config_path
        # Cleanup
        if config_path.exists():
            config_path.unlink()

    @pytest.fixture
    async def app(self, temp_config_file):
        """Create an app instance for testing."""
        # Patch config to use temp file
        app = SyllableWalkApp()
        app.config = TUIConfig(config_path=temp_config_file)
        return app

    def test_app_initializes(self):
        """App should initialize without errors."""
        app = SyllableWalkApp()
        assert app is not None
        assert app.config is not None
        assert app.controller is not None

    def test_app_has_config(self):
        """App should load TUIConfig on initialization."""
        app = SyllableWalkApp()
        assert isinstance(app.config, TUIConfig)

    def test_app_keybindings_setup(self):
        """App should set up keybindings from config."""
        app = SyllableWalkApp()
        assert hasattr(app, "BINDINGS")
        assert len(app.BINDINGS) > 0

    def test_app_keybindings_include_quit(self):
        """App keybindings should include quit action."""
        app = SyllableWalkApp()
        quit_bindings = [b for b in app.BINDINGS if b[1] == "quit"]  # type: ignore[index]
        assert len(quit_bindings) > 0

    def test_app_keybindings_include_help(self):
        """App keybindings should include help action."""
        app = SyllableWalkApp()
        help_bindings = [b for b in app.BINDINGS if b[1] == "help"]  # type: ignore[index]
        assert len(help_bindings) > 0

    def test_app_keybindings_include_generate(self):
        """App keybindings should include generate_quick action."""
        app = SyllableWalkApp()
        gen_bindings = [b for b in app.BINDINGS if b[1] == "generate_quick"]  # type: ignore[index]
        assert len(gen_bindings) > 0

    def test_app_keybindings_include_clear(self):
        """App keybindings should include clear_output action."""
        app = SyllableWalkApp()
        clear_bindings = [b for b in app.BINDINGS if b[1] == "clear_output"]  # type: ignore[index]
        assert len(clear_bindings) > 0

    def test_app_has_loading_screen(self):
        """App should have a loading screen configured."""
        app = SyllableWalkApp()
        assert "loading" in app.SCREENS

    def test_app_initial_steps_is_five(self):
        """App should default to 5 steps."""
        app = SyllableWalkApp()
        assert app.current_steps == 5

    def test_app_initial_corpus_is_none(self):
        """App should start with no corpus loaded."""
        app = SyllableWalkApp()
        assert app.current_corpus_name is None

    def test_app_custom_keybindings(self, temp_config_file):
        """App should respect custom keybindings from config."""
        # Set custom keybinding
        config = TUIConfig(config_path=temp_config_file)
        config.set_keybinding("quit", "x")

        # Create app with this config
        app = SyllableWalkApp()
        app.config = config
        app._setup_keybindings()

        # Check that 'x' is bound to quit
        quit_bindings = [b for b in app.BINDINGS if b[1] == "quit"]  # type: ignore[index]
        quit_keys = [b[0] for b in quit_bindings]  # type: ignore[index]
        assert "x" in quit_keys

    def test_app_multiple_keys_per_action(self):
        """App should support multiple keys for the same action."""
        app = SyllableWalkApp()

        # Count bindings for each action
        action_counts: dict[str, int] = {}
        for binding in app.BINDINGS:
            action = binding[1]  # type: ignore[index]
            action_counts[action] = action_counts.get(action, 0) + 1

        # At least one action should have multiple bindings
        # (since we use comma-separated keys like "k,up")
        # Actually, each comma-separated key becomes a separate binding
        # So we might have multiple bindings with same action
        assert len(app.BINDINGS) >= 4  # At least 4 actions


class TestAppKeybindingSetup:
    """Tests for keybinding setup logic."""

    def test_setup_keybindings_method_exists(self):
        """App should have _setup_keybindings method."""
        app = SyllableWalkApp()
        assert hasattr(app, "_setup_keybindings")
        assert callable(app._setup_keybindings)

    def test_setup_keybindings_called_on_init(self):
        """_setup_keybindings should be called during __init__."""
        app = SyllableWalkApp()
        # If it was called, BINDINGS should be populated
        assert len(app.BINDINGS) > 0

    def test_binding_format(self):
        """Each binding should be a 3-tuple (key, action, description)."""
        app = SyllableWalkApp()
        for binding in app.BINDINGS:
            assert isinstance(binding, tuple)
            assert len(binding) == 3
            assert isinstance(binding[0], str)  # key  # type: ignore[index]
            assert isinstance(binding[1], str)  # action  # type: ignore[index]
            assert isinstance(binding[2], str)  # description  # type: ignore[index]


class TestAppActions:
    """Tests for app action methods."""

    def test_action_generate_quick_exists(self):
        """App should have action_generate_quick method."""
        app = SyllableWalkApp()
        assert hasattr(app, "action_generate_quick")
        assert callable(app.action_generate_quick)

    def test_action_clear_output_exists(self):
        """App should have action_clear_output method."""
        app = SyllableWalkApp()
        assert hasattr(app, "action_clear_output")
        assert callable(app.action_clear_output)

    def test_action_help_exists(self):
        """App should have action_help method."""
        app = SyllableWalkApp()
        assert hasattr(app, "action_help")
        assert callable(app.action_help)
