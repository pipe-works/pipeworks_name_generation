"""Tests for the pipeline runner service.

This module tests pipeline execution orchestration:
- _log: log line formatting
- get_status: status dict construction
- cancel_pipeline: cancellation logic
- start_pipeline: background thread launch
- _run_stage: subprocess execution with cancellation
- _parse_run_directory: stdout parsing and fallback heuristics
"""

import json
import re
from unittest.mock import MagicMock, patch

import pytest

from build_tools.syllable_walk_web.services.pipeline_runner import (
    _log,
    _parse_run_directory,
    _run_stage,
    cancel_pipeline,
    get_status,
    start_pipeline,
)
from build_tools.syllable_walk_web.state import PipelineJobState

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def job():
    """Fresh idle pipeline job."""
    return PipelineJobState()


@pytest.fixture
def running_job():
    """Pipeline job in running state."""
    j = PipelineJobState()
    j.status = "running"
    j.job_id = "20260220_120000"
    return j


# ============================================================
# _log
# ============================================================


class TestLog:
    """Test log line appending."""

    def test_appends_log_line(self, job):
        """Test _log appends a dict with cls and text."""
        _log(job, "info", "test message")
        assert len(job.log_lines) == 1
        assert job.log_lines[0]["text"] == "test message"
        assert job.log_lines[0]["cls"] == "log-line--info"

    def test_multiple_logs(self, job):
        """Test multiple log entries accumulate."""
        _log(job, "info", "first")
        _log(job, "error", "second")
        assert len(job.log_lines) == 2
        assert job.log_lines[1]["cls"] == "log-line--error"


# ============================================================
# get_status
# ============================================================


class TestGetStatus:
    """Test pipeline status reporting."""

    def test_idle_status(self, job):
        """Test status dict for idle job."""
        status = get_status(job)
        assert status["status"] == "idle"
        assert status["job_id"] is None
        assert status["progress_percent"] == 0
        assert status["log_lines"] == []

    def test_running_status(self, running_job):
        """Test status dict for running job."""
        running_job.current_stage = "extract"
        running_job.progress_percent = 25
        _log(running_job, "info", "extracting")

        status = get_status(running_job)
        assert status["status"] == "running"
        assert status["current_stage"] == "extract"
        assert status["progress_percent"] == 25
        assert len(status["log_lines"]) == 1
        assert status["log_offset"] == 1


# ============================================================
# cancel_pipeline
# ============================================================


class TestCancelPipeline:
    """Test pipeline cancellation."""

    def test_cancel_idle_does_nothing(self, job):
        """Test cancelling an idle job is a no-op."""
        cancel_pipeline(job)
        assert job.status == "idle"

    def test_cancel_running_sets_cancelled(self, running_job):
        """Test cancelling a running job sets status to cancelled."""
        cancel_pipeline(running_job)
        assert running_job.status == "cancelled"

    def test_cancel_terminates_process(self, running_job):
        """Test cancellation terminates the subprocess."""
        mock_proc = MagicMock()
        running_job.process = mock_proc
        cancel_pipeline(running_job)
        mock_proc.terminate.assert_called_once()

    def test_cancel_handles_oserror(self, running_job):
        """Test cancellation handles OSError from terminate gracefully."""
        mock_proc = MagicMock()
        mock_proc.terminate.side_effect = OSError("already dead")
        running_job.process = mock_proc
        cancel_pipeline(running_job)
        assert running_job.status == "cancelled"


# ============================================================
# start_pipeline
# ============================================================


class TestStartPipeline:
    """Test pipeline background thread launch."""

    def test_sets_initial_state(self, job):
        """Test start_pipeline sets job state correctly."""
        with patch("build_tools.syllable_walk_web.services.pipeline_runner._run_pipeline"):
            start_pipeline(
                job,
                source_path="/test",
                output_dir="/output",
                extractor="pyphen",
            )

        assert job.status == "running"
        assert job.job_id is not None
        assert job.progress_percent == 0
        assert job.config["extractor"] == "pyphen"

    def test_resets_previous_state(self, running_job):
        """Test start_pipeline clears error and log from previous run."""
        running_job.error_message = "old error"
        running_job.log_lines = [{"text": "old log"}]
        running_job.status = "failed"

        with patch("build_tools.syllable_walk_web.services.pipeline_runner._run_pipeline"):
            start_pipeline(
                running_job,
                source_path="/test",
                output_dir="/output",
            )

        assert running_job.error_message is None
        assert running_job.log_lines == []


# ============================================================
# _run_stage
# ============================================================


class TestRunStage:
    """Test individual subprocess stage execution."""

    def test_success(self, job):
        """Test successful stage execution."""
        mock_proc = MagicMock()
        mock_proc.stdout = iter(["output line 1\n", "output line 2\n"])
        mock_proc.returncode = 0
        mock_proc.wait.return_value = 0

        with patch("subprocess.Popen", return_value=mock_proc):
            ok, stdout = _run_stage(job, ["echo", "test"], "extract")

        assert ok is True
        assert "output line 1" in stdout

    def test_failure_nonzero_exit(self, job):
        """Test stage failure on non-zero exit code."""
        mock_proc = MagicMock()
        mock_proc.stdout = iter(["error output\n"])
        mock_proc.returncode = 1
        mock_proc.wait.return_value = 1

        with patch("subprocess.Popen", return_value=mock_proc):
            ok, stdout = _run_stage(job, ["false"], "extract")

        assert ok is False

    def test_cancellation_mid_stream(self, job):
        """Test stage terminates on cancellation."""
        mock_proc = MagicMock()

        # After first line, simulate cancellation
        def stdout_iter():
            yield "line 1\n"
            job.status = "cancelled"
            yield "line 2\n"

        mock_proc.stdout = stdout_iter()
        mock_proc.returncode = 0

        with patch("subprocess.Popen", return_value=mock_proc):
            ok, stdout = _run_stage(job, ["cmd"], "extract")

        assert ok is False
        mock_proc.terminate.assert_called_once()

    def test_exception_handling(self, job):
        """Test stage handles exceptions gracefully."""
        with patch("subprocess.Popen", side_effect=OSError("no such cmd")):
            ok, stdout = _run_stage(job, ["nonexistent"], "extract")

        assert ok is False
        assert stdout == ""

    def test_skips_blank_output_lines(self, job):
        """Blank subprocess output lines should be ignored in captured stdout."""
        mock_proc = MagicMock()
        mock_proc.stdout = iter(["\n", "   \n", "payload\n"])
        mock_proc.returncode = 0
        mock_proc.wait.return_value = 0

        with patch("subprocess.Popen", return_value=mock_proc):
            ok, stdout = _run_stage(job, ["echo", "payload"], "extract")

        assert ok is True
        assert stdout == "payload"


# ============================================================
# _parse_run_directory
# ============================================================


class TestParseRunDirectory:
    """Test run directory path extraction from stdout."""

    def test_parses_run_directory_label(self, tmp_path):
        """Test parsing 'Run Directory: /path' from stdout."""
        run_dir = tmp_path / "20260220_120000_pyphen"
        run_dir.mkdir()

        stdout = f"Run Directory: {run_dir}\nDone."
        result = _parse_run_directory(stdout, str(tmp_path), "pyphen")
        assert result == run_dir

    def test_parses_output_label(self, tmp_path):
        """Test parsing 'Output: /path' from stdout."""
        run_dir = tmp_path / "20260220_120000_pyphen"
        run_dir.mkdir()

        stdout = f"Output: {run_dir}"
        result = _parse_run_directory(stdout, str(tmp_path), "pyphen")
        assert result == run_dir

    def test_parses_created_label(self, tmp_path):
        """Test parsing 'Created /path' from stdout."""
        run_dir = tmp_path / "20260220_120000_pyphen"
        run_dir.mkdir()

        stdout = f"Created {run_dir}"
        result = _parse_run_directory(stdout, str(tmp_path), "pyphen")
        assert result == run_dir

    def test_suffix_fallback(self, tmp_path):
        """Test fallback to directory with _extractor suffix."""
        # Stdout mentions a base path, but actual dir has _pyphen suffix
        base_dir = tmp_path / "20260220_120000"
        suffixed_dir = tmp_path / "20260220_120000_pyphen"
        suffixed_dir.mkdir()

        stdout = f"Run Directory: {base_dir}"
        result = _parse_run_directory(stdout, str(tmp_path), "pyphen")
        assert result == suffixed_dir

    def test_directory_scan_fallback(self, tmp_path):
        """Test fallback to most recent timestamped directory."""
        # Create dirs — the newer one should be found
        old = tmp_path / "20260101_000000_pyphen"
        old.mkdir()
        new = tmp_path / "20260220_120000_pyphen"
        new.mkdir()

        # No valid path in stdout
        stdout = "No directory mentioned\n"
        result = _parse_run_directory(stdout, str(tmp_path), "pyphen")
        assert result == new

    def test_returns_none_when_nothing_found(self, tmp_path):
        """Test returns None when no matching directory exists."""
        stdout = "No output"
        result = _parse_run_directory(stdout, str(tmp_path), "pyphen")
        assert result is None

    def test_ignores_wrong_extractor(self, tmp_path):
        """Test directory scan ignores dirs with wrong extractor name."""
        nltk_dir = tmp_path / "20260220_120000_nltk"
        nltk_dir.mkdir()

        stdout = "No output"
        result = _parse_run_directory(stdout, str(tmp_path), "pyphen")
        assert result is None

    def test_returns_none_when_output_parent_does_not_exist(self, tmp_path):
        """Fallback scan should return None when output parent path does not exist."""
        missing_parent = tmp_path / "does-not-exist"
        result = _parse_run_directory("No output", str(missing_parent), "pyphen")
        assert result is None


# ============================================================
# _run_pipeline (integration-style)
# ============================================================


class TestRunPipeline:
    """Test the full _run_pipeline orchestration function."""

    def test_extraction_only(self, job, tmp_path):
        """Test pipeline with extraction stage only (no normalize/annotate)."""
        from build_tools.syllable_walk_web.services.pipeline_runner import _run_pipeline

        run_dir = tmp_path / "20260220_120000_pyphen"
        run_dir.mkdir()
        data_dir = run_dir / "data"
        data_dir.mkdir()
        (data_dir / "corpus.db").write_text("placeholder", encoding="utf-8")

        job.status = "running"
        job.config = {
            "extractor": "pyphen",
            "language": "auto",
            "source_path": str(tmp_path / "source"),
            "output_dir": str(tmp_path),
            "min_syllable_length": "2",
            "max_syllable_length": "8",
            "file_pattern": "*.txt",
            "run_normalize": False,
            "run_annotate": False,
        }

        # Mock subprocess.Popen so extraction "succeeds" and prints run dir
        mock_proc = MagicMock()
        mock_proc.stdout = iter([f"Run Directory: {run_dir}\n"])
        mock_proc.returncode = 0
        mock_proc.wait.return_value = 0

        with patch("subprocess.Popen", return_value=mock_proc):
            _run_pipeline(job)

        assert job.status == "completed"
        assert job.progress_percent == 100
        assert job.output_path == run_dir
        assert any("[output]    corpus.db" in line["text"] for line in job.log_lines)
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "completed"
        assert manifest["run_id"] == run_dir.name
        assert [s["name"] for s in manifest["stages"]] == ["extract"]
        assert _SHA256_RE.match(manifest["ipc"]["input_hash"])
        assert _SHA256_RE.match(manifest["ipc"]["output_hash"])

    def test_extraction_failure(self, job, tmp_path):
        """Test pipeline fails if extraction stage fails."""
        from build_tools.syllable_walk_web.services.pipeline_runner import _run_pipeline

        job.status = "running"
        job.config = {
            "extractor": "pyphen",
            "language": "auto",
            "source_path": str(tmp_path),
            "output_dir": str(tmp_path),
            "min_syllable_length": "2",
            "max_syllable_length": "8",
            "file_pattern": "*.txt",
            "run_normalize": True,
            "run_annotate": True,
        }

        mock_proc = MagicMock()
        mock_proc.stdout = iter(["error\n"])
        mock_proc.returncode = 1
        mock_proc.wait.return_value = 1

        with patch("subprocess.Popen", return_value=mock_proc):
            _run_pipeline(job)

        assert job.status == "failed"
        assert job.error_message is not None

    def test_manifest_written_on_extraction_failure_when_run_dir_is_known(self, job, tmp_path):
        """Extraction failure should still persist manifest when run directory can be inferred."""
        from build_tools.syllable_walk_web.services.pipeline_runner import _run_pipeline

        run_dir = tmp_path / "20260220_130000_pyphen"
        run_dir.mkdir()
        (run_dir / "data").mkdir()

        job.status = "running"
        job.config = {
            "extractor": "pyphen",
            "language": "auto",
            "source_path": str(tmp_path),
            "output_dir": str(tmp_path),
            "min_syllable_length": "2",
            "max_syllable_length": "8",
            "file_pattern": "*.txt",
            "run_normalize": True,
            "run_annotate": True,
        }

        mock_proc = MagicMock()
        mock_proc.stdout = iter([f"Run Directory: {run_dir}\n", "extract failed\n"])
        mock_proc.returncode = 1
        mock_proc.wait.return_value = 1

        with patch("subprocess.Popen", return_value=mock_proc):
            _run_pipeline(job)

        assert job.status == "failed"
        assert job.error_message == "Extraction failed"
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "failed"
        stage_by_name = {stage["name"]: stage for stage in manifest["stages"]}
        assert stage_by_name["extract"]["status"] == "failed"

    def test_cancellation_during_extraction(self, job, tmp_path):
        """Test pipeline handles cancellation during extraction."""
        from build_tools.syllable_walk_web.services.pipeline_runner import _run_pipeline

        job.status = "running"
        job.config = {
            "extractor": "pyphen",
            "language": "auto",
            "source_path": str(tmp_path),
            "output_dir": str(tmp_path),
            "min_syllable_length": "2",
            "max_syllable_length": "8",
            "file_pattern": "*.txt",
            "run_normalize": True,
            "run_annotate": True,
        }

        # Simulate cancellation mid-extraction
        def stdout_with_cancel():
            yield "processing...\n"
            job.status = "cancelled"
            yield "more output\n"

        mock_proc = MagicMock()
        mock_proc.stdout = stdout_with_cancel()
        mock_proc.returncode = 0

        with patch("subprocess.Popen", return_value=mock_proc):
            _run_pipeline(job)

        assert job.status == "cancelled"

    def test_manifest_written_on_extraction_cancellation_when_run_dir_is_known(self, job, tmp_path):
        """Cancellation should persist a cancelled manifest when run directory is discoverable."""
        from build_tools.syllable_walk_web.services.pipeline_runner import _run_pipeline

        run_dir = tmp_path / "20260220_130001_pyphen"
        run_dir.mkdir()
        (run_dir / "data").mkdir()

        job.status = "running"
        job.config = {
            "extractor": "pyphen",
            "language": "auto",
            "source_path": str(tmp_path),
            "output_dir": str(tmp_path),
            "min_syllable_length": "2",
            "max_syllable_length": "8",
            "file_pattern": "*.txt",
            "run_normalize": True,
            "run_annotate": True,
        }

        def stdout_with_cancel():
            yield "processing...\n"
            job.status = "cancelled"
            yield "more output\n"

        mock_proc = MagicMock()
        mock_proc.stdout = stdout_with_cancel()
        mock_proc.returncode = 0

        with patch("subprocess.Popen", return_value=mock_proc):
            _run_pipeline(job)

        assert job.status == "cancelled"
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "cancelled"
        stage_by_name = {stage["name"]: stage for stage in manifest["stages"]}
        assert stage_by_name["extract"]["status"] == "cancelled"

    def test_no_run_directory_found(self, job, tmp_path):
        """Test pipeline fails when run directory can't be determined."""
        from build_tools.syllable_walk_web.services.pipeline_runner import _run_pipeline

        job.status = "running"
        job.config = {
            "extractor": "pyphen",
            "language": "auto",
            "source_path": str(tmp_path),
            "output_dir": str(tmp_path),
            "min_syllable_length": "2",
            "max_syllable_length": "8",
            "file_pattern": "*.txt",
            "run_normalize": False,
            "run_annotate": False,
        }

        # Extraction succeeds but doesn't print a directory path
        mock_proc = MagicMock()
        mock_proc.stdout = iter(["no path here\n"])
        mock_proc.returncode = 0
        mock_proc.wait.return_value = 0

        with patch("subprocess.Popen", return_value=mock_proc):
            _run_pipeline(job)

        assert job.status == "failed"
        assert "Could not determine" in job.error_message

    def test_full_pipeline_all_stages(self, job, tmp_path):
        """Test full pipeline with all four stages succeeding."""
        from build_tools.syllable_walk_web.services.pipeline_runner import _run_pipeline

        run_dir = tmp_path / "20260220_120000_pyphen"
        run_dir.mkdir()
        # Create required normaliser output files
        (run_dir / "pyphen_syllables_unique.txt").write_text("ka\nri\n")
        (run_dir / "pyphen_syllables_frequencies.json").write_text('{"ka": 100}')
        data_dir = run_dir / "data"
        data_dir.mkdir()

        job.status = "running"
        job.config = {
            "extractor": "pyphen",
            "language": "auto",
            "source_path": str(tmp_path / "source"),
            "output_dir": str(tmp_path),
            "min_syllable_length": "2",
            "max_syllable_length": "8",
            "file_pattern": "*.txt",
            "run_normalize": True,
            "run_annotate": True,
        }

        call_count = 0

        def make_proc(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            proc = MagicMock()
            if call_count == 1:
                # Extraction: print run directory
                proc.stdout = iter([f"Run Directory: {run_dir}\n"])
            else:
                # Other stages: just succeed
                proc.stdout = iter(["ok\n"])
            proc.returncode = 0
            proc.wait.return_value = 0
            return proc

        with patch("subprocess.Popen", side_effect=make_proc):
            _run_pipeline(job)

        assert job.status == "completed"
        assert job.progress_percent == 100
        # 4 stages: extract, normalize, annotate, database
        assert call_count == 4
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "completed"
        assert [s["name"] for s in manifest["stages"]] == [
            "extract",
            "normalize",
            "annotate",
            "database",
        ]
        assert all(s["status"] == "completed" for s in manifest["stages"])
        assert _SHA256_RE.match(manifest["ipc"]["input_hash"])
        assert _SHA256_RE.match(manifest["ipc"]["output_hash"])

    def test_manifest_written_on_normalization_failure(self, job, tmp_path):
        """Test manifest captures failed terminal state when normalize stage fails."""
        from build_tools.syllable_walk_web.services.pipeline_runner import _run_pipeline

        run_dir = tmp_path / "20260220_120000_pyphen"
        run_dir.mkdir()
        data_dir = run_dir / "data"
        data_dir.mkdir()

        job.status = "running"
        job.config = {
            "extractor": "pyphen",
            "language": "auto",
            "source_path": str(tmp_path / "source"),
            "output_dir": str(tmp_path),
            "min_syllable_length": "2",
            "max_syllable_length": "8",
            "file_pattern": "*.txt",
            "run_normalize": True,
            "run_annotate": False,
        }

        call_count = 0

        def make_proc(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            proc = MagicMock()
            if call_count == 1:
                proc.stdout = iter([f"Run Directory: {run_dir}\n"])
                proc.returncode = 0
                proc.wait.return_value = 0
            else:
                proc.stdout = iter(["normalize failed\n"])
                proc.returncode = 1
                proc.wait.return_value = 1
            return proc

        with patch("subprocess.Popen", side_effect=make_proc):
            _run_pipeline(job)

        assert job.status == "failed"
        assert job.error_message == "Normalization failed"
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "failed"
        assert any(err["message"] == "Normalization failed" for err in manifest["errors"])
        stage_by_name = {stage["name"]: stage for stage in manifest["stages"]}
        assert stage_by_name["extract"]["status"] == "completed"
        assert stage_by_name["normalize"]["status"] == "failed"
        assert _SHA256_RE.match(manifest["ipc"]["input_hash"])
        assert _SHA256_RE.match(manifest["ipc"]["output_hash"])

    def test_extraction_uses_file_mode_and_explicit_language(self, job, tmp_path):
        """Extraction command should use --file and --lang for file inputs in pyphen mode."""
        from build_tools.syllable_walk_web.services.pipeline_runner import _run_pipeline

        run_dir = tmp_path / "20260222_150000_pyphen"
        run_dir.mkdir()
        source_file = tmp_path / "source.txt"
        source_file.write_text("alpha beta", encoding="utf-8")

        job.status = "running"
        job.config = {
            "extractor": "pyphen",
            "language": "en_GB",
            "source_path": str(source_file),
            "output_dir": str(tmp_path),
            "min_syllable_length": "2",
            "max_syllable_length": "8",
            "file_pattern": "*.txt",
            "run_normalize": False,
            "run_annotate": False,
        }

        with patch(
            "build_tools.syllable_walk_web.services.pipeline_runner._run_stage",
            return_value=(True, f"Run Directory: {run_dir}\n"),
        ) as run_stage_mock:
            _run_pipeline(job)

        assert job.status == "completed"
        extract_cmd = run_stage_mock.call_args_list[0].args[1]
        assert "--file" in extract_cmd
        assert str(source_file) in extract_cmd
        assert "--lang" in extract_cmd
        assert "en_GB" in extract_cmd

    def test_manifest_written_on_annotation_input_file_gap(self, job, tmp_path):
        """Manifest should capture a failed annotate stage when normalize outputs are missing."""
        from build_tools.syllable_walk_web.services.pipeline_runner import _run_pipeline

        run_dir = tmp_path / "20260222_151000_pyphen"
        run_dir.mkdir()
        (run_dir / "data").mkdir()

        job.status = "running"
        job.config = {
            "extractor": "pyphen",
            "language": "auto",
            "source_path": str(tmp_path / "source"),
            "output_dir": str(tmp_path),
            "min_syllable_length": "2",
            "max_syllable_length": "8",
            "file_pattern": "*.txt",
            "run_normalize": True,
            "run_annotate": True,
        }

        call_count = 0

        def make_proc(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            proc = MagicMock()
            if call_count == 1:
                proc.stdout = iter([f"Run Directory: {run_dir}\n"])
            else:
                proc.stdout = iter(["normalize ok\n"])
            proc.returncode = 0
            proc.wait.return_value = 0
            return proc

        with patch("subprocess.Popen", side_effect=make_proc):
            _run_pipeline(job)

        assert job.status == "failed"
        assert "Missing input files for annotation" in (job.error_message or "")
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "failed"
        stage_by_name = {stage["name"]: stage for stage in manifest["stages"]}
        assert stage_by_name["extract"]["status"] == "completed"
        assert stage_by_name["normalize"]["status"] == "completed"
        assert stage_by_name["annotate"]["status"] == "failed"
        assert "database" not in stage_by_name

    def test_manifest_written_on_annotation_subprocess_failure(self, job, tmp_path):
        """Manifest should capture annotate subprocess failure and terminal failed state."""
        from build_tools.syllable_walk_web.services.pipeline_runner import _run_pipeline

        run_dir = tmp_path / "20260222_152000_pyphen"
        run_dir.mkdir()
        (run_dir / "pyphen_syllables_unique.txt").write_text("ka\nri\n", encoding="utf-8")
        (run_dir / "pyphen_syllables_frequencies.json").write_text('{"ka": 1}', encoding="utf-8")
        (run_dir / "data").mkdir()

        job.status = "running"
        job.config = {
            "extractor": "pyphen",
            "language": "auto",
            "source_path": str(tmp_path / "source"),
            "output_dir": str(tmp_path),
            "min_syllable_length": "2",
            "max_syllable_length": "8",
            "file_pattern": "*.txt",
            "run_normalize": True,
            "run_annotate": True,
        }

        call_count = 0

        def make_proc(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            proc = MagicMock()
            if call_count == 1:
                proc.stdout = iter([f"Run Directory: {run_dir}\n"])
                proc.returncode = 0
                proc.wait.return_value = 0
            elif call_count == 2:
                proc.stdout = iter(["normalize ok\n"])
                proc.returncode = 0
                proc.wait.return_value = 0
            else:
                proc.stdout = iter(["annotate failed\n"])
                proc.returncode = 1
                proc.wait.return_value = 1
            return proc

        with patch("subprocess.Popen", side_effect=make_proc):
            _run_pipeline(job)

        assert job.status == "failed"
        assert job.error_message == "Annotation failed"
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "failed"
        stage_by_name = {stage["name"]: stage for stage in manifest["stages"]}
        assert stage_by_name["annotate"]["status"] == "failed"
        assert "database" not in stage_by_name

    def test_manifest_written_on_database_subprocess_failure(self, job, tmp_path):
        """Manifest should capture database subprocess failure with completed prior stages."""
        from build_tools.syllable_walk_web.services.pipeline_runner import _run_pipeline

        run_dir = tmp_path / "20260222_153000_pyphen"
        run_dir.mkdir()
        (run_dir / "pyphen_syllables_unique.txt").write_text("ka\nri\n", encoding="utf-8")
        (run_dir / "pyphen_syllables_frequencies.json").write_text('{"ka": 1}', encoding="utf-8")
        (run_dir / "data").mkdir()

        job.status = "running"
        job.config = {
            "extractor": "pyphen",
            "language": "auto",
            "source_path": str(tmp_path / "source"),
            "output_dir": str(tmp_path),
            "min_syllable_length": "2",
            "max_syllable_length": "8",
            "file_pattern": "*.txt",
            "run_normalize": True,
            "run_annotate": True,
        }

        call_count = 0

        def make_proc(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            proc = MagicMock()
            if call_count == 1:
                proc.stdout = iter([f"Run Directory: {run_dir}\n"])
                proc.returncode = 0
                proc.wait.return_value = 0
            elif call_count in (2, 3):
                proc.stdout = iter(["ok\n"])
                proc.returncode = 0
                proc.wait.return_value = 0
            else:
                proc.stdout = iter(["db failed\n"])
                proc.returncode = 1
                proc.wait.return_value = 1
            return proc

        with patch("subprocess.Popen", side_effect=make_proc):
            _run_pipeline(job)

        assert job.status == "failed"
        assert job.error_message == "Database build failed"
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "failed"
        stage_by_name = {stage["name"]: stage for stage in manifest["stages"]}
        assert stage_by_name["extract"]["status"] == "completed"
        assert stage_by_name["normalize"]["status"] == "completed"
        assert stage_by_name["annotate"]["status"] == "completed"
        assert stage_by_name["database"]["status"] == "failed"
