"""Tests for the syllable walker web HTTP server module.

This module tests the CorpusBuilderHandler request handler and server
lifecycle functions:
- Handler class attributes and configuration
- Static file serving with directory traversal protection
- JSON and ZIP response helpers
- GET and POST API route dispatch
- Port discovery and server startup
"""

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from build_tools.syllable_walk_web.server import (
    CorpusBuilderHandler,
    find_available_port,
    run_server,
    select_auto_port,
)
from build_tools.syllable_walk_web.state import ServerState

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def handler():
    """Create a CorpusBuilderHandler with mocked socket I/O.

    This avoids needing a real HTTP server for unit tests.
    """
    request = MagicMock()
    request.makefile.return_value = io.BytesIO()
    client_address = ("127.0.0.1", 9999)

    # Prevent __init__ from trying to handle a real request
    with patch.object(CorpusBuilderHandler, "__init__", lambda self, *a, **kw: None):
        h = CorpusBuilderHandler.__new__(CorpusBuilderHandler)
        h.request = request
        h.client_address = client_address
        h.server = MagicMock()
        h.requestline = "GET / HTTP/1.1"
        h.command = "GET"
        h.headers = {}  # type: ignore[assignment]

        # Set up a writable buffer for response output
        h.wfile = io.BytesIO()

        # Stub methods that write HTTP framing
        h.send_response = MagicMock()  # type: ignore[method-assign]
        h.send_header = MagicMock()  # type: ignore[method-assign]
        h.end_headers = MagicMock()  # type: ignore[method-assign]

        # Give it a fresh state
        h.state = ServerState()
        h.verbose = False

    return h


# ============================================================
# Handler Attributes
# ============================================================


class TestCorpusBuilderHandlerAttributes:
    """Test handler class-level attributes."""

    def test_server_version(self):
        """Test handler has a server version string."""
        assert "PipeWorks" in CorpusBuilderHandler.server_version

    def test_default_verbose_is_true(self):
        """Test verbose defaults to True on the class."""
        assert CorpusBuilderHandler.verbose is True

    def test_default_state_is_server_state(self):
        """Test default state is a ServerState instance."""
        assert isinstance(CorpusBuilderHandler.state, ServerState)


# ============================================================
# Response Helpers
# ============================================================


class TestSendJson:
    """Test _send_json response helper."""

    def test_sends_json_with_200(self, handler):
        """Test default JSON response is 200."""
        handler._send_json({"ok": True})
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_any_call("Content-Type", "application/json")

    def test_sends_json_with_custom_status(self, handler):
        """Test JSON response with custom status code."""
        handler._send_json({"error": "bad"}, status=400)
        handler.send_response.assert_called_once_with(400)

    def test_writes_body(self, handler):
        """Test that the JSON body is written to wfile."""
        handler._send_json({"key": "value"})
        body = handler.wfile.getvalue()
        assert json.loads(body) == {"key": "value"}


class TestSendError:
    """Test _send_error response helper."""

    def test_sends_error_json(self, handler):
        """Test error response sends JSON with error key."""
        handler._send_error(404, "Not found")
        body = handler.wfile.getvalue()
        result = json.loads(body)
        assert result["error"] == "Not found"
        handler.send_response.assert_called_once_with(404)


class TestSendZip:
    """Test _send_zip response helper."""

    def test_sends_zip_attachment(self, handler):
        """Test ZIP response has correct headers."""
        handler._send_zip(b"PK\x03\x04", "test.zip")
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_any_call("Content-Type", "application/zip")
        handler.send_header.assert_any_call(
            "Content-Disposition", 'attachment; filename="test.zip"'
        )

    def test_writes_zip_body(self, handler):
        """Test ZIP data is written to wfile."""
        zip_data = b"PK\x03\x04fakecontent"
        handler._send_zip(zip_data, "out.zip")
        assert handler.wfile.getvalue() == zip_data


class TestReadJsonBody:
    """Test _read_json_body request parser."""

    def test_empty_body_returns_empty_dict(self, handler):
        """Test zero-length body returns empty dict."""
        handler.headers = {"Content-Length": "0"}
        result = handler._read_json_body()
        assert result == {}

    def test_valid_json(self, handler):
        """Test valid JSON body is parsed correctly."""
        body = b'{"key": "value"}'
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        result = handler._read_json_body()
        assert result == {"key": "value"}

    def test_invalid_json_returns_none(self, handler):
        """Test malformed JSON returns None."""
        body = b"not json"
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        result = handler._read_json_body()
        assert result is None


# ============================================================
# Static File Serving
# ============================================================


class TestServeStatic:
    """Test static file serving logic."""

    def test_serve_existing_file(self, handler):
        """Test serving an existing static file (index.html)."""
        handler._serve_static("index.html")
        handler.send_response.assert_called_once_with(200)
        # Verify some content was written
        assert len(handler.wfile.getvalue()) > 0

    def test_index_uses_module_app_script(self, handler):
        """Test index.html loads app.js using an ES module script tag."""
        handler._serve_static("index.html")
        body = handler.wfile.getvalue().decode("utf-8")
        assert '<script type="module" src="static/js/app.js"></script>' in body

    def test_serve_nested_module_file(self, handler):
        """Test serving a nested JavaScript module under static/js."""
        handler._serve_static("js/core/status.js")
        handler.send_response.assert_called_once_with(200)
        body = handler.wfile.getvalue().decode("utf-8")
        assert "export function setStatus" in body

    def test_serve_nonexistent_file(self, handler):
        """Test 404 for missing file."""
        handler._serve_static("does_not_exist.html")
        handler.send_response.assert_called_once_with(404)

    def test_directory_traversal_blocked(self, handler):
        """Test directory traversal attempt is blocked with 403."""
        handler._serve_static("../../pyproject.toml")
        handler.send_response.assert_called_once_with(403)


# ============================================================
# GET Route Dispatch
# ============================================================


class TestRouteGet:
    """Test GET API route dispatch."""

    def test_unknown_route_returns_404(self, handler):
        """Test unknown API route returns 404."""
        handler._route_get("/api/nonexistent")
        handler.send_response.assert_called_once_with(404)

    def test_pipeline_status(self, handler):
        """Test GET /api/pipeline/status returns job status."""
        handler._route_get("/api/pipeline/status")
        handler.send_response.assert_called_once_with(200)
        body = json.loads(handler.wfile.getvalue())
        assert "status" in body

    def test_pipeline_runs(self, handler):
        """Test GET /api/pipeline/runs returns runs list."""
        handler.path = "/api/pipeline/runs"
        handler._route_get("/api/pipeline/runs")
        handler.send_response.assert_called_once_with(200)
        body = json.loads(handler.wfile.getvalue())
        assert "runs" in body

    def test_walker_stats(self, handler):
        """Test GET /api/walker/stats returns patch info."""
        handler._route_get("/api/walker/stats")
        handler.send_response.assert_called_once_with(200)
        body = json.loads(handler.wfile.getvalue())
        assert "patch_a" in body
        assert "patch_b" in body

    def test_walker_sessions(self, handler):
        """Test GET /api/walker/sessions returns sessions payload."""
        handler._route_get("/api/walker/sessions")
        handler.send_response.assert_called_once_with(200)
        body = json.loads(handler.wfile.getvalue())
        assert "sessions" in body

    def test_walker_sessions_error_status(self, handler):
        """GET sessions route should return 400 when handler returns error."""
        with patch(
            "build_tools.syllable_walk_web.api.walker.handle_sessions",
            return_value={"error": "listing-failed"},
        ):
            handler._route_get("/api/walker/sessions")
        handler.send_response.assert_called_once_with(400)

    def test_walker_analysis_invalid_patch(self, handler):
        """Test GET /api/walker/analysis/x with invalid patch returns 400."""
        handler._route_get("/api/walker/analysis/x")
        handler.send_response.assert_called_once_with(400)

    def test_settings(self, handler):
        """Test GET /api/settings returns output_base and sessions_base."""
        handler._route_get("/api/settings")
        handler.send_response.assert_called_once_with(200)
        body = json.loads(handler.wfile.getvalue())
        assert "output_base" in body
        assert "sessions_base" in body
        assert Path(body["sessions_base"]) == (Path("_working/output") / "sessions").resolve()

    def test_settings_prefers_explicit_sessions_base(self, handler, tmp_path):
        """Explicit sessions_base should override output_base/sessions fallback."""
        handler.state.sessions_base = tmp_path / "sessions_override"

        handler._route_get("/api/settings")
        handler.send_response.assert_called_once_with(200)
        body = json.loads(handler.wfile.getvalue())
        assert body["sessions_base"] == str((tmp_path / "sessions_override").resolve())

    def test_version(self, handler):
        """Test GET /api/version returns package version."""
        handler._route_get("/api/version")
        handler.send_response.assert_called_once_with(200)
        body = json.loads(handler.wfile.getvalue())
        from pipeworks_name_generation import __version__

        assert body == {"version": __version__}


# ============================================================
# POST Route Dispatch
# ============================================================


class TestRoutePost:
    """Test POST API route dispatch."""

    def test_unknown_route_returns_404(self, handler):
        """Test unknown POST route returns 404."""
        handler.headers = {"Content-Length": "0"}
        handler._route_post("/api/nonexistent")
        handler.send_response.assert_called_once_with(404)

    def test_browse_directory_with_valid_path(self, handler, tmp_path):
        """Test POST /api/browse-directory with a valid directory."""
        body = json.dumps({"path": str(tmp_path)}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._route_post("/api/browse-directory")
        handler.send_response.assert_called_once_with(200)
        result = json.loads(handler.wfile.getvalue())
        assert "entries" in result

    def test_pipeline_start_missing_source(self, handler):
        """Test POST /api/pipeline/start without source_path returns 400."""
        body = json.dumps({}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._route_post("/api/pipeline/start")
        handler.send_response.assert_called_once_with(400)

    def test_pipeline_cancel_when_idle(self, handler):
        """Test POST /api/pipeline/cancel when no job running returns 400."""
        handler.headers = {"Content-Length": "0"}
        handler._route_post("/api/pipeline/cancel")
        handler.send_response.assert_called_once_with(400)

    def test_walker_walk_no_corpus(self, handler):
        """Test POST /api/walker/walk without a loaded corpus returns error."""
        body = json.dumps({"patch": "a"}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._route_post("/api/walker/walk")
        handler.send_response.assert_called_once_with(400)

    def test_walker_save_session(self, handler):
        """Test POST /api/walker/save-session returns save response."""
        body = json.dumps({}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._route_post("/api/walker/save-session")
        handler.send_response.assert_called_once_with(200)
        result = json.loads(handler.wfile.getvalue())
        assert "status" in result
        assert "reason" in result

    def test_walker_save_session_invalid_json(self, handler):
        """Test POST /api/walker/save-session with malformed JSON returns 400."""
        body = b"{bad"
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._route_post("/api/walker/save-session")
        handler.send_response.assert_called_once_with(400)

    def test_walker_load_session_missing_id(self, handler):
        """Test POST /api/walker/load-session without session_id returns 400."""
        body = json.dumps({}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._route_post("/api/walker/load-session")
        handler.send_response.assert_called_once_with(400)

    def test_walker_load_session_invalid_json(self, handler):
        """Test POST /api/walker/load-session with malformed JSON returns 400."""
        body = b"{bad"
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._route_post("/api/walker/load-session")
        handler.send_response.assert_called_once_with(400)

    def test_walker_session_lock_heartbeat_missing_fields(self, handler):
        """Test POST /api/walker/session-lock/heartbeat validates request body."""
        body = json.dumps({}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._route_post("/api/walker/session-lock/heartbeat")
        handler.send_response.assert_called_once_with(400)

    def test_walker_session_lock_release_missing_fields(self, handler):
        """Test POST /api/walker/session-lock/release validates request body."""
        body = json.dumps({}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._route_post("/api/walker/session-lock/release")
        handler.send_response.assert_called_once_with(400)

    def test_walker_session_lock_heartbeat_success_path(self, handler):
        """Test POST /api/walker/session-lock/heartbeat success route wiring."""

        body = json.dumps({"session_id": "session_ok", "lock_holder_id": "holder_a"}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._route_post("/api/walker/session-lock/heartbeat")
        handler.send_response.assert_called_once_with(200)
        result = json.loads(handler.wfile.getvalue())
        assert result["status"] in {"held", "missing"}

    def test_walker_session_lock_release_success_path(self, handler):
        """Test POST /api/walker/session-lock/release success route wiring."""

        body = json.dumps({"session_id": "session_ok", "lock_holder_id": "holder_a"}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._route_post("/api/walker/session-lock/release")
        handler.send_response.assert_called_once_with(200)
        result = json.loads(handler.wfile.getvalue())
        assert result["status"] in {"released", "missing"}

    def test_walker_rebuild_reach_cache_without_loaded_walker(self, handler):
        """Test POST /api/walker/rebuild-reach-cache returns 400 when not ready."""
        body = json.dumps({"patch": "a"}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._route_post("/api/walker/rebuild-reach-cache")
        handler.send_response.assert_called_once_with(400)

    def test_walker_rebuild_reach_cache_invalid_json(self, handler):
        """Test POST /api/walker/rebuild-reach-cache malformed JSON returns 400."""
        body = b"{bad"
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._route_post("/api/walker/rebuild-reach-cache")
        handler.send_response.assert_called_once_with(400)

    def test_settings_output_base_invalid(self, handler):
        """Test POST /api/settings/output-base with nonexistent dir returns 400."""
        body = json.dumps({"path": "/nonexistent/path"}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._route_post("/api/settings/output-base")
        handler.send_response.assert_called_once_with(400)

    def test_settings_output_base_valid(self, handler, tmp_path):
        """Test POST /api/settings/output-base with valid dir updates state."""
        body = json.dumps({"path": str(tmp_path)}).encode()
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._route_post("/api/settings/output-base")
        handler.send_response.assert_called_once_with(200)
        assert handler.state.output_base == tmp_path.resolve()
        response = json.loads(handler.wfile.getvalue())
        assert response["output_base"] == str(tmp_path.resolve())
        assert response["sessions_base"] == str((tmp_path.resolve() / "sessions").resolve())


# ============================================================
# Logging
# ============================================================


class TestLogMessage:
    """Test log_message verbosity control."""

    def test_quiet_suppresses_logs(self, handler, capsys):
        """Test verbose=False suppresses log output."""
        handler.verbose = False
        handler.log_message("test %s", "msg")
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_verbose_emits_prefixed_logs(self, handler, capsys):
        """Test verbose=True emits service-prefixed output."""
        handler.verbose = True
        handler.log_message("test %s", "msg")
        captured = capsys.readouterr()
        assert "syllable-walk-web INFO:" in captured.err
        assert "test msg" in captured.err


# ============================================================
# find_available_port
# ============================================================


class TestFindAvailablePort:
    """Test find_available_port utility."""

    def test_finds_port_on_open_system(self):
        """Test returns first candidate when socket bind succeeds immediately."""
        with patch("socket.socket") as mock_cls:
            mock_sock = MagicMock()
            mock_sock.bind = MagicMock(return_value=None)
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_sock)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)

            port = find_available_port(start=49152, max_tries=10)
            assert port == 49152

    def test_returns_none_when_all_taken(self):
        """Test returns None when max_tries exhausted."""
        with patch("socket.socket") as mock_socket:
            mock_socket.return_value.__enter__ = MagicMock()
            mock_socket.return_value.__exit__ = MagicMock()
            mock_socket.return_value.__enter__.return_value.bind = MagicMock(
                side_effect=OSError("in use")
            )
            port = find_available_port(start=8000, max_tries=3)
            assert port is None

    def test_returns_first_available(self):
        """Test returns the first port that succeeds."""
        call_count = 0

        def bind_side_effect(addr):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise OSError("in use")
            # Third call succeeds

        with patch("socket.socket") as mock_cls:
            mock_sock = MagicMock()
            mock_sock.bind = bind_side_effect
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_sock)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)

            port = find_available_port(start=8000, max_tries=5)
            assert port == 8002


# ============================================================
# select_auto_port
# ============================================================


class TestSelectAutoPort:
    """Test preferred 8000-range selection with fallback behavior."""

    def test_returns_from_primary_8000_range(self):
        """Should return a primary-range port without checking fallback."""
        calls: list[tuple[int, int]] = []

        def fake_find_port(start: int, max_tries: int) -> int | None:
            calls.append((start, max_tries))
            if start == 8000:
                return 8004
            return 8120

        assert select_auto_port(find_port=fake_find_port) == 8004
        assert calls == [(8000, 100)]

    def test_uses_fallback_when_primary_exhausted(self):
        """Should check 8100-8999 only after 8000-8099 has no free ports."""
        calls: list[tuple[int, int]] = []

        def fake_find_port(start: int, max_tries: int) -> int | None:
            calls.append((start, max_tries))
            if start == 8000:
                return None
            if start == 8100:
                return 8120
            return None

        assert select_auto_port(find_port=fake_find_port) == 8120
        assert calls == [(8000, 100), (8100, 900)]


# ============================================================
# run_server
# ============================================================


class TestRunServer:
    """Test run_server lifecycle."""

    def test_returns_1_when_no_port(self):
        """Test returns exit code 1 when no port available."""
        with patch(
            "build_tools.syllable_walk_web.server.select_auto_port",
            return_value=None,
        ):
            code = run_server(port=None, verbose=False)
            assert code == 1

    def test_starts_and_shuts_down(self):
        """Test server starts and shuts down on KeyboardInterrupt."""
        with (
            patch("build_tools.syllable_walk_web.server.is_port_available", return_value=True),
            patch("build_tools.syllable_walk_web.server.ThreadingHTTPServer") as mock_server_cls,
        ):
            mock_server = MagicMock()
            mock_server.serve_forever.side_effect = KeyboardInterrupt()
            mock_server_cls.return_value = mock_server

            code = run_server(port=8765, verbose=False)
            assert code == 0
            mock_server.serve_forever.assert_called_once()
            mock_server.shutdown.assert_called_once()

    def test_sets_class_state(self):
        """Test run_server configures handler class attributes."""
        with (
            patch("build_tools.syllable_walk_web.server.is_port_available", return_value=True),
            patch("build_tools.syllable_walk_web.server.ThreadingHTTPServer") as mock_server_cls,
        ):
            mock_server = MagicMock()
            mock_server.serve_forever.side_effect = KeyboardInterrupt()
            mock_server_cls.return_value = mock_server

            output_base = Path("/tmp/test_output")
            run_server(port=8765, verbose=False, output_base=output_base)

            # Verify class attributes were set
            assert CorpusBuilderHandler.verbose is False
            assert CorpusBuilderHandler.state.output_base == output_base

    def test_falls_back_when_configured_8000_range_port_is_busy(self):
        """Busy configured 8000-range ports should fallback to auto-selected ports."""
        with (
            patch("build_tools.syllable_walk_web.server.is_port_available", return_value=False),
            patch("build_tools.syllable_walk_web.server.select_auto_port", return_value=8004),
            patch("build_tools.syllable_walk_web.server.ThreadingHTTPServer") as mock_server_cls,
        ):
            mock_server = MagicMock()
            mock_server.serve_forever.side_effect = KeyboardInterrupt()
            mock_server_cls.return_value = mock_server

            code = run_server(port=8000, verbose=False)
            assert code == 0
            assert mock_server_cls.call_args[0][0] == ("", 8004)

    def test_returns_1_for_busy_configured_out_of_range_port(self):
        """Busy configured ports outside 8000-8999 should fail fast."""
        with (
            patch("build_tools.syllable_walk_web.server.is_port_available", return_value=False),
            patch("build_tools.syllable_walk_web.server.ThreadingHTTPServer") as mock_server_cls,
        ):
            code = run_server(port=9500, verbose=False)
            assert code == 1
            mock_server_cls.assert_not_called()


# ============================================================
# run_server corpus_dir
# ============================================================


class TestRunServerCorpusDirs:
    """Test run_server stores per-patch corpus directories in state."""

    def test_stores_corpus_dir_a(self, tmp_path):
        """Test corpus_dir_a is stored in state."""
        with (
            patch("build_tools.syllable_walk_web.server.is_port_available", return_value=True),
            patch("build_tools.syllable_walk_web.server.ThreadingHTTPServer") as mock_cls,
        ):
            mock_server = MagicMock()
            mock_server.serve_forever.side_effect = KeyboardInterrupt()
            mock_cls.return_value = mock_server

            run_server(port=8765, verbose=False, corpus_dir_a=str(tmp_path))

            assert CorpusBuilderHandler.state.corpus_dir_a == tmp_path

    def test_stores_corpus_dir_b(self, tmp_path):
        """Test corpus_dir_b is stored in state."""
        with (
            patch("build_tools.syllable_walk_web.server.is_port_available", return_value=True),
            patch("build_tools.syllable_walk_web.server.ThreadingHTTPServer") as mock_cls,
        ):
            mock_server = MagicMock()
            mock_server.serve_forever.side_effect = KeyboardInterrupt()
            mock_cls.return_value = mock_server

            run_server(port=8765, verbose=False, corpus_dir_b=str(tmp_path))

            assert CorpusBuilderHandler.state.corpus_dir_b == tmp_path

    def test_corpus_dirs_default_to_none(self):
        """Test corpus_dirs are None when not configured."""
        with (
            patch("build_tools.syllable_walk_web.server.is_port_available", return_value=True),
            patch("build_tools.syllable_walk_web.server.ThreadingHTTPServer") as mock_cls,
        ):
            mock_server = MagicMock()
            mock_server.serve_forever.side_effect = KeyboardInterrupt()
            mock_cls.return_value = mock_server

            run_server(port=8765, verbose=False)

            assert CorpusBuilderHandler.state.corpus_dir_a is None
            assert CorpusBuilderHandler.state.corpus_dir_b is None

    def test_stores_sessions_dir_override(self, tmp_path):
        """Test sessions_dir override is stored in state as an absolute path."""
        with (
            patch("build_tools.syllable_walk_web.server.is_port_available", return_value=True),
            patch("build_tools.syllable_walk_web.server.ThreadingHTTPServer") as mock_cls,
        ):
            mock_server = MagicMock()
            mock_server.serve_forever.side_effect = KeyboardInterrupt()
            mock_cls.return_value = mock_server

            run_server(port=8765, verbose=False, sessions_dir=tmp_path / "sessions_dir")

            assert CorpusBuilderHandler.state.sessions_base == (tmp_path / "sessions_dir").resolve()
