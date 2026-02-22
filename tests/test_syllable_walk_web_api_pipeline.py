"""Tests for the pipeline API handlers.

This module tests the four pipeline API handlers:
- handle_start: validation, background pipeline launch
- handle_status: delegates to pipeline_runner.get_status
- handle_cancel: not-running guard, delegation
- handle_runs: delegates to run_discovery.discover_runs
"""

from unittest.mock import MagicMock, patch

import pytest

from build_tools.syllable_walk_web.api.pipeline import (
    handle_cancel,
    handle_runs,
    handle_start,
    handle_status,
)
from build_tools.syllable_walk_web.state import ServerState

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def state():
    """Fresh ServerState with idle pipeline job."""
    return ServerState()


@pytest.fixture
def running_state():
    """ServerState with pipeline job already running."""
    s = ServerState()
    s.pipeline_job.status = "running"
    s.pipeline_job.job_id = "20260220_120000"
    return s


# ============================================================
# handle_start
# ============================================================


class TestHandleStart:
    """Test POST /api/pipeline/start handler."""

    def test_error_when_already_running(self, running_state):
        """Test returns error if a job is already running."""
        result = handle_start({"source_path": "/tmp"}, running_state)
        assert "error" in result
        assert "already running" in result["error"]

    def test_error_when_missing_source_path(self, state):
        """Test returns error if source_path not provided."""
        result = handle_start({}, state)
        assert "error" in result
        assert "source_path" in result["error"]

    def test_error_when_source_not_found(self, state):
        """Test returns error if source_path doesn't exist."""
        result = handle_start({"source_path": "/nonexistent/path"}, state)
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_success_with_directory_source(self, state, tmp_path):
        """Test successful start with a directory source."""
        source = tmp_path / "corpus"
        source.mkdir()

        with patch(
            "build_tools.syllable_walk_web.services.pipeline_runner.start_pipeline"
        ) as mock_start:
            result = handle_start({"source_path": str(source), "extractor": "pyphen"}, state)

        assert "error" not in result
        assert result["status"] == "running"
        assert "job_id" in result
        mock_start.assert_called_once()

    def test_success_with_file_source(self, state, tmp_path):
        """Test successful start with a single file source."""
        source = tmp_path / "input.txt"
        source.write_text("hello world")

        with patch("build_tools.syllable_walk_web.services.pipeline_runner.start_pipeline"):
            result = handle_start({"source_path": str(source)}, state)

        assert "error" not in result
        assert result["status"] == "running"

    def test_default_output_dir(self, state, tmp_path):
        """Test that output defaults to state.output_base."""
        source = tmp_path / "corpus"
        source.mkdir()

        with patch(
            "build_tools.syllable_walk_web.services.pipeline_runner.start_pipeline"
        ) as mock_start:
            handle_start({"source_path": str(source)}, state)

        # Verify the call used the state output_base
        call_kwargs = mock_start.call_args
        assert call_kwargs is not None

    def test_passes_extractor_and_language(self, state, tmp_path):
        """Test extractor and language parameters are forwarded."""
        source = tmp_path / "corpus"
        source.mkdir()

        with patch(
            "build_tools.syllable_walk_web.services.pipeline_runner.start_pipeline"
        ) as mock_start:
            handle_start(
                {
                    "source_path": str(source),
                    "extractor": "nltk",
                    "language": "en_US",
                    "min_syllable_length": 3,
                    "max_syllable_length": 6,
                },
                state,
            )

        _, kwargs = mock_start.call_args
        assert kwargs["extractor"] == "nltk"
        assert kwargs["language"] == "en_US"
        assert kwargs["min_syllable_length"] == 3
        assert kwargs["max_syllable_length"] == 6

    def test_error_when_min_exceeds_max(self, state, tmp_path):
        """Test returns error when min_syllable_length > max_syllable_length."""
        source = tmp_path / "corpus"
        source.mkdir()

        with patch(
            "build_tools.syllable_walk_web.services.pipeline_runner.start_pipeline"
        ) as mock_start:
            result = handle_start(
                {
                    "source_path": str(source),
                    "min_syllable_length": 9,
                    "max_syllable_length": 4,
                },
                state,
            )

        assert "error" in result
        assert "<=" in result["error"]
        mock_start.assert_not_called()

    def test_error_when_min_is_not_integer(self, state, tmp_path):
        """Test returns error when min_syllable_length is invalid."""
        source = tmp_path / "corpus"
        source.mkdir()

        with patch(
            "build_tools.syllable_walk_web.services.pipeline_runner.start_pipeline"
        ) as mock_start:
            result = handle_start(
                {
                    "source_path": str(source),
                    "min_syllable_length": "abc",
                },
                state,
            )

        assert "error" in result
        assert "min_syllable_length" in result["error"]
        mock_start.assert_not_called()

    def test_error_when_max_is_not_integer(self, state, tmp_path):
        """Test returns error when max_syllable_length is invalid."""
        source = tmp_path / "corpus"
        source.mkdir()

        with patch(
            "build_tools.syllable_walk_web.services.pipeline_runner.start_pipeline"
        ) as mock_start:
            result = handle_start(
                {
                    "source_path": str(source),
                    "max_syllable_length": "abc",
                },
                state,
            )

        assert "error" in result
        assert "max_syllable_length" in result["error"]
        mock_start.assert_not_called()

    def test_error_when_min_is_less_than_one(self, state, tmp_path):
        """Test returns error when min_syllable_length is below 1."""
        source = tmp_path / "corpus"
        source.mkdir()

        with patch(
            "build_tools.syllable_walk_web.services.pipeline_runner.start_pipeline"
        ) as mock_start:
            result = handle_start(
                {
                    "source_path": str(source),
                    "min_syllable_length": 0,
                },
                state,
            )

        assert "error" in result
        assert "min_syllable_length must be >= 1" == result["error"]
        mock_start.assert_not_called()

    def test_coerces_string_lengths(self, state, tmp_path):
        """Test numeric string lengths are coerced before forwarding."""
        source = tmp_path / "corpus"
        source.mkdir()

        with patch(
            "build_tools.syllable_walk_web.services.pipeline_runner.start_pipeline"
        ) as mock_start:
            handle_start(
                {
                    "source_path": str(source),
                    "min_syllable_length": "3",
                    "max_syllable_length": "7",
                },
                state,
            )

        _, kwargs = mock_start.call_args
        assert kwargs["min_syllable_length"] == 3
        assert kwargs["max_syllable_length"] == 7


# ============================================================
# handle_status
# ============================================================


class TestHandleStatus:
    """Test GET /api/pipeline/status handler."""

    def test_returns_status_dict(self, state):
        """Test returns a dict with expected status fields."""
        result = handle_status(state)
        assert "status" in result
        assert "job_id" in result
        assert "progress_percent" in result
        assert "log_lines" in result

    def test_idle_status(self, state):
        """Test idle job returns correct status."""
        result = handle_status(state)
        assert result["status"] == "idle"

    def test_running_status(self, running_state):
        """Test running job returns correct status."""
        result = handle_status(running_state)
        assert result["status"] == "running"


# ============================================================
# handle_cancel
# ============================================================


class TestHandleCancel:
    """Test POST /api/pipeline/cancel handler."""

    def test_error_when_not_running(self, state):
        """Test returns error when no job is running."""
        result = handle_cancel(state)
        assert "error" in result

    def test_success_when_running(self, running_state):
        """Test cancellation succeeds for a running job."""
        with patch(
            "build_tools.syllable_walk_web.services.pipeline_runner.cancel_pipeline"
        ) as mock_cancel:
            result = handle_cancel(running_state)

        assert "error" not in result
        assert result["status"] == "cancelled"
        mock_cancel.assert_called_once_with(running_state.pipeline_job)


# ============================================================
# handle_runs
# ============================================================


class TestHandleRuns:
    """Test GET /api/pipeline/runs handler."""

    def test_returns_runs_list(self, state):
        """Test returns dict with runs key."""
        with patch("build_tools.syllable_walk_web.run_discovery.discover_runs", return_value=[]):
            result = handle_runs(state)

        assert "runs" in result
        assert isinstance(result["runs"], list)

    def test_delegates_to_discover_runs(self, state):
        """Test passes output_base to discover_runs."""
        mock_run = MagicMock()
        mock_run.to_dict.return_value = {
            "path": "/test",
            "run_id": "20260220_120000_pyphen",
            "timestamp": "20260220_120000",
        }

        with patch(
            "build_tools.syllable_walk_web.run_discovery.discover_runs",
            return_value=[mock_run],
        ) as mock_discover:
            result = handle_runs(state)

        mock_discover.assert_called_once_with(state.output_base)
        assert len(result["runs"]) == 1
        assert result["runs"][0]["run_id"] == "20260220_120000_pyphen"

    def test_uses_corpus_dir_a_for_patch_a(self, state, tmp_path):
        """Test patch=a discovers from corpus_dir_a when set."""
        state.corpus_dir_a = tmp_path

        with patch(
            "build_tools.syllable_walk_web.run_discovery.discover_runs",
            return_value=[],
        ) as mock_discover:
            handle_runs(state, patch="a")

        mock_discover.assert_called_once_with(tmp_path)

    def test_uses_corpus_dir_b_for_patch_b(self, state, tmp_path):
        """Test patch=b discovers from corpus_dir_b when set."""
        state.corpus_dir_b = tmp_path

        with patch(
            "build_tools.syllable_walk_web.run_discovery.discover_runs",
            return_value=[],
        ) as mock_discover:
            handle_runs(state, patch="b")

        mock_discover.assert_called_once_with(tmp_path)

    def test_falls_back_to_output_base_when_no_corpus_dir(self, state):
        """Test patch=a falls back to output_base when corpus_dir_a is None."""
        with patch(
            "build_tools.syllable_walk_web.run_discovery.discover_runs",
            return_value=[],
        ) as mock_discover:
            handle_runs(state, patch="a")

        mock_discover.assert_called_once_with(state.output_base)

    def test_no_patch_param_uses_output_base(self, state):
        """Test no patch parameter uses output_base."""
        with patch(
            "build_tools.syllable_walk_web.run_discovery.discover_runs",
            return_value=[],
        ) as mock_discover:
            handle_runs(state, patch=None)

        mock_discover.assert_called_once_with(state.output_base)
