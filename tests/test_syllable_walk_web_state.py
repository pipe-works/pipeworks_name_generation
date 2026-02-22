"""Tests for syllable walker web state dataclasses.

This module tests the in-memory state models:
- PatchState defaults and field types
- PipelineJobState defaults and field types
- ServerState composition and independence
"""

from pathlib import Path

from build_tools.syllable_walk_web.state import (
    PatchState,
    PipelineJobState,
    ServerState,
)

# ============================================================
# PatchState Tests
# ============================================================


class TestPatchState:
    """Test PatchState dataclass."""

    def test_default_values(self):
        """Test all fields default to None/0/empty."""
        ps = PatchState()
        assert ps.run_id is None
        assert ps.corpus_type is None
        assert ps.corpus_dir is None
        assert ps.syllable_count == 0
        assert ps.walker is None
        assert ps.walker_ready is False
        assert ps.manifest_ipc_input_hash is None
        assert ps.manifest_ipc_output_hash is None
        assert ps.manifest_ipc_verification_status is None
        assert ps.manifest_ipc_verification_reason is None
        assert ps.reach_cache_status is None
        assert ps.reach_cache_ipc_input_hash is None
        assert ps.reach_cache_ipc_output_hash is None
        assert ps.reach_cache_ipc_verification_status is None
        assert ps.reach_cache_ipc_verification_reason is None
        assert ps.annotated_data is None
        assert ps.frequencies is None
        assert ps.walks == []
        assert ps.candidates is None
        assert ps.candidates_path is None
        assert ps.selections_path is None
        assert ps.selected_names == []

    def test_walks_default_factory(self):
        """Test that walks is a fresh list per instance (not shared)."""
        ps1 = PatchState()
        ps2 = PatchState()
        ps1.walks.append({"test": True})
        assert len(ps2.walks) == 0

    def test_selected_names_default_factory(self):
        """Test that selected_names is a fresh list per instance."""
        ps1 = PatchState()
        ps2 = PatchState()
        ps1.selected_names.append({"name": "Kira"})
        assert len(ps2.selected_names) == 0


# ============================================================
# PipelineJobState Tests
# ============================================================


class TestPipelineJobState:
    """Test PipelineJobState dataclass."""

    def test_default_values(self):
        """Test all fields default to idle/None/0/empty."""
        job = PipelineJobState()
        assert job.job_id is None
        assert job.status == "idle"
        assert job.config is None
        assert job.current_stage is None
        assert job.progress_percent == 0
        assert job.log_lines == []
        assert job.output_path is None
        assert job.error_message is None
        assert job.process is None

    def test_log_lines_default_factory(self):
        """Test that log_lines is a fresh list per instance."""
        j1 = PipelineJobState()
        j2 = PipelineJobState()
        j1.log_lines.append({"text": "hello"})
        assert len(j2.log_lines) == 0

    def test_status_is_mutable(self):
        """Test that status can be updated in-place."""
        job = PipelineJobState()
        job.status = "running"
        assert job.status == "running"


# ============================================================
# ServerState Tests
# ============================================================


class TestServerState:
    """Test ServerState dataclass."""

    def test_default_output_base(self):
        """Test default output_base is _working/output."""
        state = ServerState()
        assert state.output_base == Path("_working/output")
        assert state.sessions_base is None

    def test_custom_output_base(self):
        """Test output_base can be set at construction."""
        state = ServerState(output_base=Path("/tmp/custom"))
        assert state.output_base == Path("/tmp/custom")

    def test_custom_sessions_base(self):
        """Test sessions_base can be set independently at construction."""
        state = ServerState(
            output_base=Path("/tmp/custom"),
            sessions_base=Path("/tmp/sessions"),
        )
        assert state.output_base == Path("/tmp/custom")
        assert state.sessions_base == Path("/tmp/sessions")

    def test_patches_are_independent(self):
        """Test that patch_a and patch_b are separate instances."""
        state = ServerState()
        state.patch_a.run_id = "run-A"
        state.patch_b.run_id = "run-B"
        assert state.patch_a.run_id != state.patch_b.run_id

    def test_patches_are_not_shared_across_server_states(self):
        """Test that two ServerState instances don't share patches."""
        s1 = ServerState()
        s2 = ServerState()
        s1.patch_a.syllable_count = 999
        assert s2.patch_a.syllable_count == 0

    def test_pipeline_job_is_fresh(self):
        """Test that pipeline_job starts idle."""
        state = ServerState()
        assert state.pipeline_job.status == "idle"
        assert state.pipeline_job.job_id is None
