"""Tests for the directory browser API handler.

This module tests handle_browse_directory():
- Valid directory listing with correct structure
- Hidden file filtering
- File type filtering (only .txt, .text, .csv, .tsv)
- Sort order (directories first, then files)
- Error handling (invalid path, not a directory, permission denied)
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from build_tools.syllable_walk_web.api.browse import handle_browse_directory

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def browse_dir(tmp_path):
    """Create a temp directory with a mix of files and subdirectories."""
    # Directories
    (tmp_path / "subdir_alpha").mkdir()
    (tmp_path / "subdir_beta").mkdir()
    (tmp_path / ".hidden_dir").mkdir()

    # Files
    (tmp_path / "readme.txt").write_text("hello")
    (tmp_path / "data.csv").write_text("a,b,c")
    (tmp_path / "notes.text").write_text("notes")
    (tmp_path / "spreadsheet.tsv").write_text("a\tb")
    (tmp_path / "image.png").write_bytes(b"PNG")
    (tmp_path / "script.py").write_text("print(1)")
    (tmp_path / ".hidden_file.txt").write_text("secret")

    return tmp_path


# ============================================================
# Success Cases
# ============================================================


class TestBrowseDirectorySuccess:
    """Test successful directory browsing."""

    def test_returns_path_and_parent(self, browse_dir):
        """Test response includes resolved path and parent."""
        result = handle_browse_directory({"path": str(browse_dir)})
        assert "entries" in result
        assert result["path"] == str(browse_dir)
        assert result["parent"] == str(browse_dir.parent)

    def test_lists_directories(self, browse_dir):
        """Test that directories are included in entries."""
        result = handle_browse_directory({"path": str(browse_dir)})
        dir_names = [e["name"] for e in result["entries"] if e["type"] == "directory"]
        assert "subdir_alpha" in dir_names
        assert "subdir_beta" in dir_names

    def test_lists_text_files(self, browse_dir):
        """Test that .txt, .csv, .text, .tsv files are included."""
        result = handle_browse_directory({"path": str(browse_dir)})
        file_names = [e["name"] for e in result["entries"] if e["type"] == "file"]
        assert "readme.txt" in file_names
        assert "data.csv" in file_names
        assert "notes.text" in file_names
        assert "spreadsheet.tsv" in file_names

    def test_excludes_non_text_files(self, browse_dir):
        """Test that .png, .py etc. are excluded."""
        result = handle_browse_directory({"path": str(browse_dir)})
        file_names = [e["name"] for e in result["entries"] if e["type"] == "file"]
        assert "image.png" not in file_names
        assert "script.py" not in file_names

    def test_excludes_hidden_files(self, browse_dir):
        """Test that dotfiles and hidden directories are excluded."""
        result = handle_browse_directory({"path": str(browse_dir)})
        all_names = [e["name"] for e in result["entries"]]
        assert ".hidden_dir" not in all_names
        assert ".hidden_file.txt" not in all_names

    def test_directories_first_then_files(self, browse_dir):
        """Test entries are sorted with directories first, then files."""
        result = handle_browse_directory({"path": str(browse_dir)})
        types = [e["type"] for e in result["entries"]]
        # All directories should come before all files
        dir_indices = [i for i, t in enumerate(types) if t == "directory"]
        file_indices = [i for i, t in enumerate(types) if t == "file"]
        if dir_indices and file_indices:
            assert max(dir_indices) < min(file_indices)

    def test_file_entries_have_size(self, browse_dir):
        """Test file entries include a size field."""
        result = handle_browse_directory({"path": str(browse_dir)})
        files = [e for e in result["entries"] if e["type"] == "file"]
        for f in files:
            assert "size" in f
            assert isinstance(f["size"], int)

    def test_empty_directory(self, tmp_path):
        """Test browsing an empty directory returns empty entries."""
        result = handle_browse_directory({"path": str(tmp_path)})
        assert result["entries"] == []

    def test_default_path(self):
        """Test that default path (.) resolves to cwd."""
        result = handle_browse_directory({})
        assert "entries" in result
        assert result["path"] == str(Path(".").resolve())

    def test_tilde_expansion(self):
        """Test that ~ is expanded to home directory."""
        result = handle_browse_directory({"path": "~"})
        assert "error" not in result
        assert result["path"] == str(Path.home())


# ============================================================
# Error Cases
# ============================================================


class TestBrowseDirectoryErrors:
    """Test directory browsing error handling."""

    def test_not_a_directory(self, tmp_path):
        """Test error when path points to a file."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("x")
        result = handle_browse_directory({"path": str(file_path)})
        assert "error" in result

    def test_nonexistent_path(self):
        """Test error for nonexistent path."""
        result = handle_browse_directory({"path": "/nonexistent/xyz"})
        assert "error" in result

    def test_permission_denied(self, tmp_path):
        """Test error when directory is unreadable."""
        restricted = tmp_path / "restricted"
        restricted.mkdir()
        # Create a file inside so iterdir has something to fail on
        (restricted / "secret.txt").write_text("data")

        with patch("pathlib.Path.iterdir", side_effect=PermissionError("no")):
            result = handle_browse_directory({"path": str(restricted)})
            assert "error" in result
