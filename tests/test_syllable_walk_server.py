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


# ============================================================
# Parse Path Tests
# ============================================================


class TestParsePath:
    """Test _parse_path method."""

    def test_parse_path_simple(self):
        """Test parsing simple path without query params."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.path = "/api/runs"
        handler._parse_path = SimplifiedWalkerHandler._parse_path.__get__(
            handler, SimplifiedWalkerHandler
        )

        path, query = handler._parse_path()

        assert path == "/api/runs"
        assert query == {}

    def test_parse_path_with_query_params(self):
        """Test parsing path with query parameters."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.path = "/api/walk?start=ka&steps=5"
        handler._parse_path = SimplifiedWalkerHandler._parse_path.__get__(
            handler, SimplifiedWalkerHandler
        )

        path, query = handler._parse_path()

        assert path == "/api/walk"
        assert query["start"] == "ka"
        assert query["steps"] == "5"

    def test_parse_path_with_nested_path(self):
        """Test parsing nested path."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.path = "/api/runs/20260121_084017_nltk/selections/first_name"
        handler._parse_path = SimplifiedWalkerHandler._parse_path.__get__(
            handler, SimplifiedWalkerHandler
        )

        path, query = handler._parse_path()

        assert path == "/api/runs/20260121_084017_nltk/selections/first_name"
        assert query == {}


# ============================================================
# API Handler Method Tests
# ============================================================


class TestHandleListRuns:
    """Test _handle_list_runs method."""

    def test_handle_list_runs_returns_runs(self):
        """Test _handle_list_runs returns discovered runs."""
        SimplifiedWalkerHandler.current_run = None

        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler._send_json_response = MagicMock()

        mock_runs = [
            MagicMock(to_dict=MagicMock(return_value={"id": "run1"})),
            MagicMock(to_dict=MagicMock(return_value={"id": "run2"})),
        ]

        handler._handle_list_runs = SimplifiedWalkerHandler._handle_list_runs.__get__(
            handler, SimplifiedWalkerHandler
        )

        with patch("build_tools.syllable_walk.server.discover_runs", return_value=mock_runs):
            handler._handle_list_runs()

        handler._send_json_response.assert_called_once()
        response = handler._send_json_response.call_args[0][0]
        assert "runs" in response
        assert len(response["runs"]) == 2
        assert response["current_run"] is None

    def test_handle_list_runs_with_current_run(self):
        """Test _handle_list_runs includes current run info."""
        mock_current = MagicMock()
        mock_current.path.name = "20260121_084017_nltk"
        SimplifiedWalkerHandler.current_run = mock_current

        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler._send_json_response = MagicMock()

        handler._handle_list_runs = SimplifiedWalkerHandler._handle_list_runs.__get__(
            handler, SimplifiedWalkerHandler
        )

        with patch("build_tools.syllable_walk.server.discover_runs", return_value=[]):
            handler._handle_list_runs()

        response = handler._send_json_response.call_args[0][0]
        assert response["current_run"] == "20260121_084017_nltk"

        # Clean up
        SimplifiedWalkerHandler.current_run = None

    def test_handle_list_runs_error(self):
        """Test _handle_list_runs handles errors."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler._send_error_response = MagicMock()

        handler._handle_list_runs = SimplifiedWalkerHandler._handle_list_runs.__get__(
            handler, SimplifiedWalkerHandler
        )

        with patch(
            "build_tools.syllable_walk.server.discover_runs",
            side_effect=Exception("Discovery failed"),
        ):
            handler._handle_list_runs()

        handler._send_error_response.assert_called_once()
        assert "Discovery failed" in str(handler._send_error_response.call_args)


class TestHandleGetSelection:
    """Test _handle_get_selection method."""

    def test_handle_get_selection_invalid_path_format(self):
        """Test _handle_get_selection with invalid path format."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler._send_error_response = MagicMock()

        handler._handle_get_selection = SimplifiedWalkerHandler._handle_get_selection.__get__(
            handler, SimplifiedWalkerHandler
        )

        handler._handle_get_selection("/api/runs/short")

        handler._send_error_response.assert_called_once()
        assert "Invalid path" in str(handler._send_error_response.call_args)

    def test_handle_get_selection_run_not_found(self):
        """Test _handle_get_selection when run doesn't exist."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler._send_error_response = MagicMock()

        handler._handle_get_selection = SimplifiedWalkerHandler._handle_get_selection.__get__(
            handler, SimplifiedWalkerHandler
        )

        with patch("build_tools.syllable_walk.server.get_run_by_id", return_value=None):
            handler._handle_get_selection("/api/runs/nonexistent_run/selections/first_name")

        handler._send_error_response.assert_called_once()
        assert "not found" in str(handler._send_error_response.call_args).lower()

    def test_handle_get_selection_name_class_not_found(self):
        """Test _handle_get_selection when name class doesn't exist."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler._send_error_response = MagicMock()

        mock_run = MagicMock()
        mock_run.selections = {"first_name": "/path/to/first.json"}

        handler._handle_get_selection = SimplifiedWalkerHandler._handle_get_selection.__get__(
            handler, SimplifiedWalkerHandler
        )

        with patch("build_tools.syllable_walk.server.get_run_by_id", return_value=mock_run):
            handler._handle_get_selection(
                "/api/runs/20260121_084017_nltk/selections/nonexistent_class"
            )

        handler._send_error_response.assert_called_once()
        assert "not found" in str(handler._send_error_response.call_args).lower()

    def test_handle_get_selection_success(self):
        """Test _handle_get_selection successful response."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler._send_json_response = MagicMock()

        mock_run = MagicMock()
        mock_run.selections = {"first_name": "/path/to/first.json"}

        selection_data = {"metadata": {}, "selections": [{"name": "kaki"}]}

        handler._handle_get_selection = SimplifiedWalkerHandler._handle_get_selection.__get__(
            handler, SimplifiedWalkerHandler
        )

        with patch("build_tools.syllable_walk.server.get_run_by_id", return_value=mock_run):
            with patch(
                "build_tools.syllable_walk.server.get_selection_data",
                return_value=selection_data,
            ):
                handler._handle_get_selection(
                    "/api/runs/20260121_084017_nltk/selections/first_name"
                )

        handler._send_json_response.assert_called_once_with(selection_data)

    def test_handle_get_selection_error(self):
        """Test _handle_get_selection handles exceptions."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler._send_error_response = MagicMock()

        handler._handle_get_selection = SimplifiedWalkerHandler._handle_get_selection.__get__(
            handler, SimplifiedWalkerHandler
        )

        with patch(
            "build_tools.syllable_walk.server.get_run_by_id",
            side_effect=Exception("Database error"),
        ):
            handler._handle_get_selection("/api/runs/20260121_084017_nltk/selections/first_name")

        handler._send_error_response.assert_called_once()
        assert "Database error" in str(handler._send_error_response.call_args)


class TestHandleGetStats:
    """Test _handle_get_stats method."""

    def test_handle_get_stats_no_run_selected(self):
        """Test _handle_get_stats when no run is selected."""
        SimplifiedWalkerHandler.current_run = None
        SimplifiedWalkerHandler.walker = None

        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler._send_json_response = MagicMock()

        handler._handle_get_stats = SimplifiedWalkerHandler._handle_get_stats.__get__(
            handler, SimplifiedWalkerHandler
        )

        handler._handle_get_stats()

        response = handler._send_json_response.call_args[0][0]
        assert response["current_run"] is None
        assert response["syllable_count"] == 0
        assert response["has_walker"] is False

    def test_handle_get_stats_with_run_selected(self):
        """Test _handle_get_stats with active run and walker."""
        mock_run = MagicMock()
        mock_run.path.name = "20260121_084017_nltk"
        SimplifiedWalkerHandler.current_run = mock_run

        mock_walker = MagicMock()
        mock_walker.syllables = ["ka", "ki", "ta"]
        SimplifiedWalkerHandler.walker = mock_walker

        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler._send_json_response = MagicMock()

        handler._handle_get_stats = SimplifiedWalkerHandler._handle_get_stats.__get__(
            handler, SimplifiedWalkerHandler
        )

        handler._handle_get_stats()

        response = handler._send_json_response.call_args[0][0]
        assert response["current_run"] == "20260121_084017_nltk"
        assert response["syllable_count"] == 3
        assert response["has_walker"] is True

        # Clean up
        SimplifiedWalkerHandler.current_run = None
        SimplifiedWalkerHandler.walker = None


class TestHandleSelectRun:
    """Test _handle_select_run method."""

    def test_handle_select_run_empty_body(self):
        """Test _handle_select_run with empty request body."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.headers = {"Content-Length": "0"}
        handler._send_error_response = MagicMock()

        handler._handle_select_run = SimplifiedWalkerHandler._handle_select_run.__get__(
            handler, SimplifiedWalkerHandler
        )

        handler._handle_select_run()

        handler._send_error_response.assert_called_once()
        assert "Empty" in str(handler._send_error_response.call_args)

    def test_handle_select_run_missing_run_id(self):
        """Test _handle_select_run with missing run_id parameter."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.headers = {"Content-Length": "2"}
        handler.rfile = io.BytesIO(b"{}")
        handler._send_error_response = MagicMock()

        handler._handle_select_run = SimplifiedWalkerHandler._handle_select_run.__get__(
            handler, SimplifiedWalkerHandler
        )

        handler._handle_select_run()

        handler._send_error_response.assert_called_once()
        assert "run_id" in str(handler._send_error_response.call_args)

    def test_handle_select_run_not_found(self):
        """Test _handle_select_run when run doesn't exist."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        body = json.dumps({"run_id": "nonexistent_run"}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_error_response = MagicMock()

        handler._handle_select_run = SimplifiedWalkerHandler._handle_select_run.__get__(
            handler, SimplifiedWalkerHandler
        )

        with patch("build_tools.syllable_walk.server.get_run_by_id", return_value=None):
            handler._handle_select_run()

        handler._send_error_response.assert_called_once()
        assert "not found" in str(handler._send_error_response.call_args).lower()

    def test_handle_select_run_already_selected(self):
        """Test _handle_select_run when run is already selected."""
        mock_run = MagicMock()
        mock_run.path.name = "20260121_084017_nltk"
        SimplifiedWalkerHandler.current_run = mock_run
        SimplifiedWalkerHandler.walker = MagicMock()
        SimplifiedWalkerHandler.walker.syllables = ["ka", "ki"]

        handler = MagicMock(spec=SimplifiedWalkerHandler)
        body = json.dumps({"run_id": "20260121_084017_nltk"}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json_response = MagicMock()
        handler.verbose = False

        handler._handle_select_run = SimplifiedWalkerHandler._handle_select_run.__get__(
            handler, SimplifiedWalkerHandler
        )

        with patch("build_tools.syllable_walk.server.get_run_by_id", return_value=mock_run):
            handler._handle_select_run()

        response = handler._send_json_response.call_args[0][0]
        assert response["success"] is True
        assert response["message"] == "Run already selected"

        # Clean up
        SimplifiedWalkerHandler.current_run = None
        SimplifiedWalkerHandler.walker = None

    def test_handle_select_run_invalid_json(self):
        """Test _handle_select_run with invalid JSON body."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.headers = {"Content-Length": "12"}
        handler.rfile = io.BytesIO(b"not valid json")
        handler._send_error_response = MagicMock()

        handler._handle_select_run = SimplifiedWalkerHandler._handle_select_run.__get__(
            handler, SimplifiedWalkerHandler
        )

        handler._handle_select_run()

        handler._send_error_response.assert_called_once()
        assert "Invalid JSON" in str(handler._send_error_response.call_args)

    def test_handle_select_run_success(self, sample_syllables_data):
        """Test _handle_select_run successful selection."""
        SimplifiedWalkerHandler.current_run = None
        SimplifiedWalkerHandler.walker = None

        mock_run = MagicMock()
        mock_run.path.name = "20260121_084017_nltk"
        mock_run.corpus_db_path = None
        mock_run.annotated_json_path = MagicMock()

        handler = MagicMock(spec=SimplifiedWalkerHandler)
        body = json.dumps({"run_id": "20260121_084017_nltk"}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json_response = MagicMock()
        handler.verbose = False

        handler._handle_select_run = SimplifiedWalkerHandler._handle_select_run.__get__(
            handler, SimplifiedWalkerHandler
        )

        mock_walker = MagicMock()
        mock_walker.syllables = sample_syllables_data

        with patch("build_tools.syllable_walk.server.get_run_by_id", return_value=mock_run):
            with patch(
                "build_tools.syllable_walk.server.load_syllables",
                return_value=(sample_syllables_data, "JSON (3 syllables)"),
            ):
                with patch(
                    "build_tools.syllable_walk.server.SyllableWalker.from_data",
                    return_value=mock_walker,
                ):
                    handler._handle_select_run()

        response = handler._send_json_response.call_args[0][0]
        assert response["success"] is True
        assert response["run_id"] == "20260121_084017_nltk"

        # Clean up
        SimplifiedWalkerHandler.current_run = None
        SimplifiedWalkerHandler.walker = None

    def test_handle_select_run_verbose_output(self, sample_syllables_data, capsys):
        """Test _handle_select_run prints verbose output."""
        SimplifiedWalkerHandler.current_run = None
        SimplifiedWalkerHandler.walker = None

        mock_run = MagicMock()
        mock_run.path.name = "20260121_084017_nltk"
        mock_run.corpus_db_path = None
        mock_run.annotated_json_path = MagicMock()

        handler = MagicMock(spec=SimplifiedWalkerHandler)
        body = json.dumps({"run_id": "20260121_084017_nltk"}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json_response = MagicMock()
        handler.verbose = True  # Enable verbose

        handler._handle_select_run = SimplifiedWalkerHandler._handle_select_run.__get__(
            handler, SimplifiedWalkerHandler
        )

        mock_walker = MagicMock()
        mock_walker.syllables = sample_syllables_data

        with patch("build_tools.syllable_walk.server.get_run_by_id", return_value=mock_run):
            with patch(
                "build_tools.syllable_walk.server.load_syllables",
                return_value=(sample_syllables_data, "JSON (3 syllables)"),
            ):
                with patch(
                    "build_tools.syllable_walk.server.SyllableWalker.from_data",
                    return_value=mock_walker,
                ):
                    handler._handle_select_run()

        captured = capsys.readouterr()
        assert "Loading run" in captured.out
        assert "Building neighbor graph" in captured.out

        # Clean up
        SimplifiedWalkerHandler.current_run = None
        SimplifiedWalkerHandler.walker = None

    def test_handle_select_run_error(self):
        """Test _handle_select_run handles exceptions."""
        SimplifiedWalkerHandler.current_run = None

        mock_run = MagicMock()
        mock_run.path.name = "20260121_084017_nltk"

        handler = MagicMock(spec=SimplifiedWalkerHandler)
        body = json.dumps({"run_id": "20260121_084017_nltk"}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_error_response = MagicMock()
        handler.verbose = False

        handler._handle_select_run = SimplifiedWalkerHandler._handle_select_run.__get__(
            handler, SimplifiedWalkerHandler
        )

        with patch("build_tools.syllable_walk.server.get_run_by_id", return_value=mock_run):
            with patch(
                "build_tools.syllable_walk.server.load_syllables",
                side_effect=Exception("Load failed"),
            ):
                handler._handle_select_run()

        handler._send_error_response.assert_called_once()
        assert "Load failed" in str(handler._send_error_response.call_args)


class TestHandleWalk:
    """Test _handle_walk method."""

    def test_handle_walk_success(self):
        """Test _handle_walk successful walk generation."""
        mock_walker = MagicMock()
        mock_walker.syllable_to_idx = {"ka": 0, "ki": 1, "ta": 2}
        mock_walker.get_random_syllable = MagicMock(return_value="ka")
        mock_walker.walk_from_profile = MagicMock(return_value=["ka", "ki", "ta", "ka", "ki"])
        SimplifiedWalkerHandler.walker = mock_walker

        handler = MagicMock(spec=SimplifiedWalkerHandler)
        body = json.dumps({"start": "ka", "profile": "dialect", "steps": 5}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json_response = MagicMock()

        handler._handle_walk = SimplifiedWalkerHandler._handle_walk.__get__(
            handler, SimplifiedWalkerHandler
        )

        handler._handle_walk()

        handler._send_json_response.assert_called_once()
        response = handler._send_json_response.call_args[0][0]
        assert "walk" in response
        assert response["profile"] == "dialect"
        assert response["start"] == "ka"

        # Clean up
        SimplifiedWalkerHandler.walker = None

    def test_handle_walk_with_random_start(self):
        """Test _handle_walk with random start syllable."""
        mock_walker = MagicMock()
        mock_walker.syllable_to_idx = {"ka": 0, "ki": 1}
        mock_walker.get_random_syllable = MagicMock(return_value="ki")
        mock_walker.walk_from_profile = MagicMock(return_value=["ki", "ka"])
        SimplifiedWalkerHandler.walker = mock_walker

        handler = MagicMock(spec=SimplifiedWalkerHandler)
        body = json.dumps({"profile": "dialect"}).encode()  # No start specified
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_json_response = MagicMock()

        handler._handle_walk = SimplifiedWalkerHandler._handle_walk.__get__(
            handler, SimplifiedWalkerHandler
        )

        handler._handle_walk()

        mock_walker.get_random_syllable.assert_called_once()

        # Clean up
        SimplifiedWalkerHandler.walker = None

    def test_handle_walk_unknown_syllable(self):
        """Test _handle_walk with unknown start syllable."""
        mock_walker = MagicMock()
        mock_walker.syllable_to_idx = {"ka": 0, "ki": 1}
        SimplifiedWalkerHandler.walker = mock_walker

        handler = MagicMock(spec=SimplifiedWalkerHandler)
        body = json.dumps({"start": "xyz"}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_error_response = MagicMock()

        handler._handle_walk = SimplifiedWalkerHandler._handle_walk.__get__(
            handler, SimplifiedWalkerHandler
        )

        handler._handle_walk()

        handler._send_error_response.assert_called_once()
        assert "Unknown syllable" in str(handler._send_error_response.call_args)

        # Clean up
        SimplifiedWalkerHandler.walker = None

    def test_handle_walk_invalid_json(self):
        """Test _handle_walk with invalid JSON body."""
        mock_walker = MagicMock()
        SimplifiedWalkerHandler.walker = mock_walker

        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.headers = {"Content-Length": "12"}
        handler.rfile = io.BytesIO(b"not valid json")
        handler._send_error_response = MagicMock()

        handler._handle_walk = SimplifiedWalkerHandler._handle_walk.__get__(
            handler, SimplifiedWalkerHandler
        )

        handler._handle_walk()

        handler._send_error_response.assert_called_once()
        assert "Invalid JSON" in str(handler._send_error_response.call_args)

        # Clean up
        SimplifiedWalkerHandler.walker = None

    def test_handle_walk_value_error(self):
        """Test _handle_walk handles ValueError from walker."""
        mock_walker = MagicMock()
        mock_walker.syllable_to_idx = {"ka": 0}
        mock_walker.walk_from_profile = MagicMock(side_effect=ValueError("Invalid profile"))
        SimplifiedWalkerHandler.walker = mock_walker

        handler = MagicMock(spec=SimplifiedWalkerHandler)
        body = json.dumps({"start": "ka", "profile": "invalid"}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_error_response = MagicMock()

        handler._handle_walk = SimplifiedWalkerHandler._handle_walk.__get__(
            handler, SimplifiedWalkerHandler
        )

        handler._handle_walk()

        handler._send_error_response.assert_called_once()
        assert "Invalid profile" in str(handler._send_error_response.call_args)

        # Clean up
        SimplifiedWalkerHandler.walker = None

    def test_handle_walk_server_error(self):
        """Test _handle_walk handles unexpected exceptions."""
        mock_walker = MagicMock()
        mock_walker.syllable_to_idx = {"ka": 0}
        mock_walker.walk_from_profile = MagicMock(side_effect=RuntimeError("Unexpected error"))
        SimplifiedWalkerHandler.walker = mock_walker

        handler = MagicMock(spec=SimplifiedWalkerHandler)
        body = json.dumps({"start": "ka"}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._send_error_response = MagicMock()

        handler._handle_walk = SimplifiedWalkerHandler._handle_walk.__get__(
            handler, SimplifiedWalkerHandler
        )

        handler._handle_walk()

        handler._send_error_response.assert_called_once()
        assert "Server error" in str(handler._send_error_response.call_args)

        # Clean up
        SimplifiedWalkerHandler.walker = None


# ============================================================
# Additional GET/POST Route Tests
# ============================================================


class TestDoGETRoutes:
    """Test do_GET routing for API endpoints."""

    def test_get_api_runs_calls_handler(self):
        """Test GET /api/runs routes to _handle_list_runs."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.path = "/api/runs"
        handler._parse_path = MagicMock(return_value=("/api/runs", {}))
        handler._handle_list_runs = MagicMock()

        handler.do_GET = SimplifiedWalkerHandler.do_GET.__get__(handler, SimplifiedWalkerHandler)
        handler.do_GET()

        handler._handle_list_runs.assert_called_once()

    def test_get_api_selections_calls_handler(self):
        """Test GET /api/runs/{id}/selections/{class} routes correctly."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.path = "/api/runs/20260121_084017_nltk/selections/first_name"
        handler._parse_path = MagicMock(
            return_value=(
                "/api/runs/20260121_084017_nltk/selections/first_name",
                {},
            )
        )
        handler._handle_get_selection = MagicMock()

        handler.do_GET = SimplifiedWalkerHandler.do_GET.__get__(handler, SimplifiedWalkerHandler)
        handler.do_GET()

        handler._handle_get_selection.assert_called_once_with(
            "/api/runs/20260121_084017_nltk/selections/first_name"
        )

    def test_get_api_stats_calls_handler(self):
        """Test GET /api/stats routes to _handle_get_stats."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.path = "/api/stats"
        handler._parse_path = MagicMock(return_value=("/api/stats", {}))
        handler._handle_get_stats = MagicMock()

        handler.do_GET = SimplifiedWalkerHandler.do_GET.__get__(handler, SimplifiedWalkerHandler)
        handler.do_GET()

        handler._handle_get_stats.assert_called_once()

    def test_get_404_handles_connection_error(self):
        """Test GET 404 handles connection errors gracefully."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.path = "/unknown"
        handler._parse_path = MagicMock(return_value=("/unknown", {}))
        handler.send_error = MagicMock(side_effect=BrokenPipeError())

        handler.do_GET = SimplifiedWalkerHandler.do_GET.__get__(handler, SimplifiedWalkerHandler)

        # Should not raise
        handler.do_GET()


class TestDoPOSTRoutes:
    """Test do_POST routing for API endpoints."""

    def test_post_api_walk_calls_handler(self):
        """Test POST /api/walk routes to _handle_walk."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.path = "/api/walk"
        handler._parse_path = MagicMock(return_value=("/api/walk", {}))
        handler._handle_walk = MagicMock()

        handler.do_POST = SimplifiedWalkerHandler.do_POST.__get__(handler, SimplifiedWalkerHandler)
        handler.do_POST()

        handler._handle_walk.assert_called_once()

    def test_post_api_select_run_calls_handler(self):
        """Test POST /api/select-run routes to _handle_select_run."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.path = "/api/select-run"
        handler._parse_path = MagicMock(return_value=("/api/select-run", {}))
        handler._handle_select_run = MagicMock()

        handler.do_POST = SimplifiedWalkerHandler.do_POST.__get__(handler, SimplifiedWalkerHandler)
        handler.do_POST()

        handler._handle_select_run.assert_called_once()

    def test_post_404_handles_connection_error(self):
        """Test POST 404 handles connection errors gracefully."""
        handler = MagicMock(spec=SimplifiedWalkerHandler)
        handler.path = "/unknown"
        handler._parse_path = MagicMock(return_value=("/unknown", {}))
        handler.send_error = MagicMock(side_effect=ConnectionResetError())

        handler.do_POST = SimplifiedWalkerHandler.do_POST.__get__(handler, SimplifiedWalkerHandler)

        # Should not raise
        handler.do_POST()


# ============================================================
# Additional run_server Tests
# ============================================================


class TestRunServerVerbose:
    """Additional run_server verbose output tests."""

    def test_run_server_displays_multiple_runs(self, capsys):
        """Test run_server displays multiple runs."""
        mock_runs = [
            MagicMock(display_name="Run 1", selections={"first_name": "/a", "last_name": "/b"}),
            MagicMock(display_name="Run 2", selections={"first_name": "/c"}),
            MagicMock(display_name="Run 3", selections={}),
            MagicMock(display_name="Run 4", selections={"place_name": "/d"}),
        ]

        with patch("build_tools.syllable_walk.server.discover_runs", return_value=mock_runs):
            with patch.object(HTTPServer, "serve_forever", side_effect=KeyboardInterrupt):
                with patch.object(HTTPServer, "shutdown"):
                    run_server(port=16000, verbose=True)

        captured = capsys.readouterr()
        assert "4 pipeline run(s)" in captured.out
        assert "Run 1" in captured.out
        assert "Run 2" in captured.out
        assert "Run 3" in captured.out
        # Run 4 should be summarized
        assert "and 1 more" in captured.out

    def test_run_server_auto_port_verbose(self, capsys):
        """Test run_server auto-port discovery verbose output."""
        with patch("build_tools.syllable_walk.server.find_available_port", return_value=8042):
            with patch("build_tools.syllable_walk.server.discover_runs", return_value=[]):
                with patch.object(HTTPServer, "serve_forever", side_effect=KeyboardInterrupt):
                    with patch.object(HTTPServer, "shutdown"):
                        run_server(port=None, verbose=True)

        captured = capsys.readouterr()
        assert "Auto-selected port: 8042" in captured.out
