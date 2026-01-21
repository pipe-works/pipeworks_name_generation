"""Tests for simplified syllable walker HTTP server module.

This module tests the web server functionality:
- SimplifiedWalkerHandler class and its methods
- HTTP GET/POST request handling
- API endpoints (/api/runs, /api/runs/{id}/selections/{class}, /api/select-run, /api/walk)
- run_server initialization and port discovery
"""

import io
import json
import socket
from http.server import HTTPServer
from unittest.mock import MagicMock, patch

import pytest

from build_tools.syllable_walk.run_discovery import RunInfo
from build_tools.syllable_walk.server import (
    SimplifiedWalkerHandler,
    find_available_port,
    run_server,
)

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def sample_syllables_data():
    """Sample syllable data for creating test files."""
    return [
        {
            "syllable": "ka",
            "frequency": 100,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": True,
                "contains_fricative": False,
                "contains_liquid": False,
                "contains_nasal": False,
                "short_vowel": True,
                "long_vowel": False,
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
        {
            "syllable": "ki",
            "frequency": 80,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": True,
                "contains_fricative": False,
                "contains_liquid": False,
                "contains_nasal": False,
                "short_vowel": False,
                "long_vowel": True,
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
        {
            "syllable": "ta",
            "frequency": 90,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": True,
                "contains_fricative": False,
                "contains_liquid": False,
                "contains_nasal": False,
                "short_vowel": True,
                "long_vowel": False,
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
    ]


@pytest.fixture
def mock_handler():
    """Create a mock HTTP handler for testing."""
    handler = MagicMock(spec=SimplifiedWalkerHandler)
    handler.wfile = io.BytesIO()
    handler.verbose = False
    return handler


@pytest.fixture
def sample_run_info(tmp_path, sample_syllables_data):
    """Create a sample RunInfo for testing."""
    run_dir = tmp_path / "20260121_084017_nltk"
    run_dir.mkdir(parents=True)

    # Create data directory with corpus.db and annotated JSON
    data_dir = run_dir / "data"
    data_dir.mkdir()

    annotated_json = data_dir / "nltk_syllables_annotated.json"
    with open(annotated_json, "w", encoding="utf-8") as f:
        json.dump(sample_syllables_data, f)

    # Create selections directory with selection file
    selections_dir = run_dir / "selections"
    selections_dir.mkdir()

    selection_data = {
        "metadata": {
            "name_class": "first_name",
            "admitted": 2,
            "rejected": 1,
            "total_evaluated": 3,
        },
        "selections": [
            {"name": "kaki", "syllables": ["ka", "ki"], "score": 2},
            {"name": "taki", "syllables": ["ta", "ki"], "score": 1},
        ],
    }
    selection_file = selections_dir / "nltk_first_name_2syl.json"
    with open(selection_file, "w", encoding="utf-8") as f:
        json.dump(selection_data, f)

    return RunInfo(
        path=run_dir.resolve(),
        extractor_type="nltk",
        timestamp="20260121_084017",
        display_name="NLTK - 2026-01-21 08:40 (3 syllables)",
        corpus_db_path=None,  # No DB for this test
        annotated_json_path=annotated_json.resolve(),
        syllable_count=3,
        selections={"first_name": selection_file.resolve()},
    )


# ============================================================
# SimplifiedWalkerHandler Class Attribute Tests
# ============================================================


class TestSimplifiedWalkerHandlerAttributes:
    """Test SimplifiedWalkerHandler class attributes."""

    def test_class_has_walker(self):
        """Test handler has walker class attribute."""
        assert hasattr(SimplifiedWalkerHandler, "walker")

    def test_class_has_current_run(self):
        """Test handler has current_run class attribute."""
        assert hasattr(SimplifiedWalkerHandler, "current_run")

    def test_class_has_verbose(self):
        """Test handler has verbose class attribute."""
        assert hasattr(SimplifiedWalkerHandler, "verbose")
        assert isinstance(SimplifiedWalkerHandler.verbose, bool)


# ============================================================
# Handler Method Tests
# ============================================================


class TestHandlerMethods:
    """Test SimplifiedWalkerHandler methods."""

    def test_log_message_suppresses_output(self, capsys):
        """Test log_message suppresses logging output."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.log_message = SimplifiedWalkerHandler.log_message.__get__(
            handler, SimplifiedWalkerHandler
        )

        handler.log_message("%s %s", "GET", "/")

        captured = capsys.readouterr()
        assert captured.out == ""


# ============================================================
# Response Method Tests
# ============================================================


class TestResponseMethods:
    """Test response sending methods."""

    def test_send_response_writes_to_wfile(self):
        """Test _send_response writes content to wfile."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.wfile = io.BytesIO()

        handler._send_response = SimplifiedWalkerHandler._send_response.__get__(
            handler, SimplifiedWalkerHandler
        )

        handler._send_response("test content")

        handler.send_response.assert_called_once_with(200)
        assert handler.send_header.call_count >= 2
        handler.end_headers.assert_called_once()

        handler.wfile.seek(0)
        content = handler.wfile.read()
        assert content == b"test content"

    def test_send_response_handles_broken_pipe(self):
        """Test _send_response handles BrokenPipeError gracefully."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.send_response.side_effect = BrokenPipeError()

        handler._send_response = SimplifiedWalkerHandler._send_response.__get__(
            handler, SimplifiedWalkerHandler
        )

        # Should not raise
        handler._send_response("test content")

    def test_send_json_response(self):
        """Test _send_json_response serializes and sends JSON."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.wfile = io.BytesIO()

        handler._send_response = MagicMock()
        handler._send_json_response = SimplifiedWalkerHandler._send_json_response.__get__(
            handler, SimplifiedWalkerHandler
        )

        test_data = {"key": "value", "count": 42}
        handler._send_json_response(test_data)

        handler._send_response.assert_called_once()
        call_args = handler._send_response.call_args
        assert call_args[0][0] == json.dumps(test_data)
        assert call_args[1]["content_type"] == "application/json"

    def test_send_error_response(self):
        """Test _send_error_response sends error JSON."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)

        handler._send_json_response = MagicMock()
        handler._send_error_response = SimplifiedWalkerHandler._send_error_response.__get__(
            handler, SimplifiedWalkerHandler
        )

        handler._send_error_response("Test error message", status=400)

        handler._send_json_response.assert_called_once_with(
            {"error": "Test error message"}, status=400
        )


# ============================================================
# GET Request Tests
# ============================================================


class TestDoGET:
    """Test do_GET request handling."""

    def test_get_root_returns_html(self):
        """Test GET / returns HTML page."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.path = "/"
        handler._parse_path = MagicMock(return_value=("/", {}))
        handler._send_response = MagicMock()

        handler.do_GET = SimplifiedWalkerHandler.do_GET.__get__(handler, SimplifiedWalkerHandler)
        handler.do_GET()

        handler._send_response.assert_called_once()
        call_args = handler._send_response.call_args
        assert call_args[1]["content_type"] == "text/html"

    def test_get_styles_returns_css(self):
        """Test GET /styles.css returns CSS."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.path = "/styles.css"
        handler._parse_path = MagicMock(return_value=("/styles.css", {}))
        handler._send_response = MagicMock()

        handler.do_GET = SimplifiedWalkerHandler.do_GET.__get__(handler, SimplifiedWalkerHandler)
        handler.do_GET()

        handler._send_response.assert_called_once()
        call_args = handler._send_response.call_args
        assert call_args[1]["content_type"] == "text/css"

    def test_get_unknown_path_returns_404(self):
        """Test GET unknown path returns 404."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.path = "/unknown/path"
        handler._parse_path = MagicMock(return_value=("/unknown/path", {}))

        handler.do_GET = SimplifiedWalkerHandler.do_GET.__get__(handler, SimplifiedWalkerHandler)
        handler.do_GET()

        handler.send_error.assert_called_once_with(404, "Not Found")


# ============================================================
# POST Request Tests
# ============================================================


class TestDoPOST:
    """Test do_POST request handling."""

    def test_post_api_walk_with_no_walker(self):
        """Test POST /api/walk with no walker loaded."""
        SimplifiedWalkerHandler.walker = None

        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.path = "/api/walk"
        handler._parse_path = MagicMock(return_value=("/api/walk", {}))
        handler._send_error_response = MagicMock()

        handler._handle_walk = SimplifiedWalkerHandler._handle_walk.__get__(
            handler, SimplifiedWalkerHandler
        )
        handler._handle_walk()

        handler._send_error_response.assert_called_once()
        assert "No run selected" in str(handler._send_error_response.call_args)

    def test_post_api_walk_empty_body(self):
        """Test POST /api/walk with empty body."""
        # Create mock walker
        SimplifiedWalkerHandler.walker = MagicMock()

        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.headers = {"Content-Length": "0"}
        handler._send_error_response = MagicMock()

        handler._handle_walk = SimplifiedWalkerHandler._handle_walk.__get__(
            handler, SimplifiedWalkerHandler
        )
        handler._handle_walk()

        handler._send_error_response.assert_called_once()
        assert "Empty request body" in str(handler._send_error_response.call_args)

    def test_post_unknown_path_returns_404(self):
        """Test POST unknown path returns 404."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.path = "/api/unknown"
        handler._parse_path = MagicMock(return_value=("/api/unknown", {}))

        handler.do_POST = SimplifiedWalkerHandler.do_POST.__get__(handler, SimplifiedWalkerHandler)
        handler.do_POST()

        handler.send_error.assert_called_once_with(404, "Not Found")


# ============================================================
# Port Discovery Tests
# ============================================================


class TestFindAvailablePort:
    """Test find_available_port function."""

    def test_finds_available_port(self):
        """Test find_available_port returns a port."""
        port = find_available_port(start=18000)
        assert isinstance(port, int)
        assert port >= 18000
        assert port < 18100

    def test_port_is_actually_available(self):
        """Test returned port can be bound."""
        port = find_available_port(start=18100)

        # Should be able to bind to it
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", port))  # nosec B104

    def test_skips_unavailable_ports(self):
        """Test skips ports that are in use."""
        # Bind to a port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", 18200))  # nosec B104
            s.listen(1)

            # Find should skip 18200
            port = find_available_port(start=18200, max_attempts=10)
            assert port > 18200

    def test_raises_when_no_ports_available(self):
        """Test raises OSError when no ports found."""
        # Mock socket.bind to always fail
        with patch("socket.socket.bind", side_effect=OSError("No ports")):
            with pytest.raises(OSError, match="No available ports"):
                find_available_port(start=19000, max_attempts=5)


# ============================================================
# run_server Tests
# ============================================================


class TestRunServer:
    """Test run_server function."""

    def test_run_server_initializes_handler(self):
        """Test run_server initializes handler attributes."""
        with patch.object(HTTPServer, "serve_forever", side_effect=KeyboardInterrupt):
            with patch.object(HTTPServer, "shutdown"):
                run_server(port=15000, verbose=False)

        # Handler should be configured
        assert SimplifiedWalkerHandler.verbose is False
        assert SimplifiedWalkerHandler.walker is None
        assert SimplifiedWalkerHandler.current_run is None

    def test_run_server_auto_discovers_port(self):
        """Test run_server auto-discovers available port."""
        with patch.object(HTTPServer, "serve_forever", side_effect=KeyboardInterrupt):
            with patch.object(HTTPServer, "shutdown"):
                # Port=None should trigger auto-discovery
                run_server(port=None, verbose=False)

    def test_run_server_specific_port_unavailable_raises(self):
        """Test run_server raises when specific port unavailable."""
        # Bind to a port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", 15100))  # nosec B104
            s.listen(1)

            with pytest.raises(OSError, match="not available"):
                run_server(port=15100, verbose=False)

    def test_run_server_verbose_output(self, capsys):
        """Test run_server verbose output."""
        with patch.object(HTTPServer, "serve_forever", side_effect=KeyboardInterrupt):
            with patch.object(HTTPServer, "shutdown"):
                run_server(port=15200, verbose=True)

        captured = capsys.readouterr()
        assert "Syllable Walker" in captured.out


# ============================================================
# Integration Tests
# ============================================================


class TestServerIntegration:
    """Integration tests for server behavior."""

    def test_handler_state_persists(self):
        """Test handler class state persists."""
        # Set state
        SimplifiedWalkerHandler.walker = MagicMock()
        SimplifiedWalkerHandler.current_run = MagicMock()
        SimplifiedWalkerHandler.verbose = True

        # Verify persistence
        assert SimplifiedWalkerHandler.walker is not None
        assert SimplifiedWalkerHandler.current_run is not None
        assert SimplifiedWalkerHandler.verbose is True

        # Clean up
        SimplifiedWalkerHandler.walker = None
        SimplifiedWalkerHandler.current_run = None
        SimplifiedWalkerHandler.verbose = False

    def test_handler_reset(self):
        """Test handler state can be reset."""
        SimplifiedWalkerHandler.walker = MagicMock()
        SimplifiedWalkerHandler.current_run = MagicMock()

        # Reset
        SimplifiedWalkerHandler.walker = None
        SimplifiedWalkerHandler.current_run = None

        assert SimplifiedWalkerHandler.walker is None
        assert SimplifiedWalkerHandler.current_run is None
