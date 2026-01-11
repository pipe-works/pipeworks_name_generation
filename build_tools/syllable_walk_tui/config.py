"""
TUI Configuration - Save/Load User Preferences

Manages persistent config like last used corpus directory.
"""

import json
from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """
    Get the project root directory (pipeworks_name_generation/).

    Returns the project root regardless of where the app is run from.
    This is the directory containing the build_tools/ folder.
    """
    # This file is at: pipeworks_name_generation/build_tools/syllable_walk_tui/config.py
    # Project root is 3 levels up
    return Path(__file__).resolve().parent.parent.parent


class TUIConfig:
    """
    Manages TUI configuration persistence.

    Config is saved to ~/.syllable_walk_tui_config.json
    """

    DEFAULT_CONFIG_PATH = Path.home() / ".syllable_walk_tui_config.json"

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize config manager.

        Args:
            config_path: Optional custom config file path.
                        Defaults to ~/.syllable_walk_tui_config.json
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.data = self._load()

    def _load(self) -> dict:
        """Load config from file, or return defaults if not found."""
        if not self.config_path.exists():
            return self._get_defaults()

        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception:
            # If corrupted, return defaults
            return self._get_defaults()

    def _get_defaults(self) -> dict:
        """Get default config values."""
        project_root = get_project_root()
        return {
            "last_corpus_directory": str(project_root / "_working" / "output"),
            "last_corpus_path": None,
            "last_corpus_type": None,
            "keybindings": {
                "quit": "q",
                "clear_output": "c",
                "generate_quick": "g",
                "help": "question_mark",
                "navigate_up": "k,up",
                "navigate_down": "j,down",
                "navigate_left": "h,left",
                "navigate_right": "l,right",
                "select": "enter",
            },
        }

    def save(self):
        """Save current config to file."""
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception:  # noqa: S110
            # Silent fail - config is nice-to-have, not critical
            pass

    def get_last_corpus_directory(self) -> str:
        """Get the last directory user browsed for corpora."""
        return self.data.get("last_corpus_directory", str(get_project_root()))

    def set_last_corpus_directory(self, directory: str):
        """Save the last directory user browsed."""
        self.data["last_corpus_directory"] = directory
        self.save()

    def get_last_corpus(self) -> Optional[dict]:
        """
        Get info about the last loaded corpus.

        Returns:
            Dict with path and type, or None if never loaded
        """
        path = self.data.get("last_corpus_path")
        if not path:
            return None

        return {
            "path": path,
            "type": self.data.get("last_corpus_type"),
        }

    def set_last_corpus(self, path: str, corpus_type: str):
        """
        Save info about the last loaded corpus.

        Args:
            path: Full path to the corpus file
            corpus_type: Type identifier ("nltk", "pyphen", etc.)
        """
        self.data["last_corpus_path"] = path
        self.data["last_corpus_type"] = corpus_type

        # Also update directory
        corpus_path = Path(path)
        self.data["last_corpus_directory"] = str(corpus_path.parent)

        self.save()

    def get_keybindings(self) -> dict[str, str]:
        """
        Get keybindings configuration.

        Returns:
            Dict mapping action names to key strings.
            Multiple keys can be comma-separated (e.g., "j,down").
        """
        return self.data.get("keybindings", self._get_defaults()["keybindings"])

    def set_keybinding(self, action: str, keys: str):
        """
        Set a keybinding for an action.

        Args:
            action: Action name (e.g., "navigate_up")
            keys: Key string or comma-separated keys (e.g., "k,up")
        """
        if "keybindings" not in self.data:
            self.data["keybindings"] = self._get_defaults()["keybindings"]

        self.data["keybindings"][action] = keys
        self.save()
