"""Tests for the walker API handlers.

This module tests walker API handlers:
- handle_load_corpus: corpus loading and walker init
- handle_walk: walk generation
- handle_stats: dual-patch state reporting
- handle_save_session / handle_sessions / handle_load_session: session IPC APIs
- handle_combine: candidate generation
- handle_select: name selection
- handle_export: name export
- handle_package: ZIP archive building
- handle_analysis: corpus metrics
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from build_tools.syllable_walk.reach import ReachResult
from build_tools.syllable_walk_web.api.walker import (
    _clear_active_session_context,
    _reach_cache_verification_from_read,
    _read_json_object,
    _restore_patch_artifacts_from_run_state,
    handle_analysis,
    handle_combine,
    handle_export,
    handle_load_corpus,
    handle_load_session,
    handle_package,
    handle_reach_syllables,
    handle_rebuild_reach_cache,
    handle_save_session,
    handle_select,
    handle_session_lock_heartbeat,
    handle_session_lock_release,
    handle_sessions,
    handle_stats,
    handle_walk,
)
from build_tools.syllable_walk_web.services.pipeline_manifest import (
    ManifestIPCVerificationResult,
)
from build_tools.syllable_walk_web.services.profile_reaches_cache import CacheReadResult
from build_tools.syllable_walk_web.state import ServerState

# ============================================================
# _reach_cache_verification_from_read
# ============================================================


class TestReachCacheVerificationMapping:
    """Unit tests for cache-status to verification-status mapping."""

    def test_none_status_returns_unset(self):
        """None cache status should keep verification state unset."""

        status, reason = _reach_cache_verification_from_read(
            cache_status=None,
            cache_message=None,
            input_hash=None,
            output_hash=None,
        )
        assert status is None
        assert reason is None

    @pytest.mark.parametrize(
        ("cache_status", "cache_message", "expected_status", "expected_reason"),
        [
            ("invalid", None, "mismatch", "cache-invalid"),
            ("invalid", "ipc-tampered", "mismatch", "ipc-tampered"),
            ("error", None, "error", "cache-read-error"),
            ("error", "io-failure", "error", "io-failure"),
            ("none", None, "missing", "manifest-ipc-missing"),
            ("miss", None, "missing", "cache-miss"),
            ("unexpected", None, "error", "cache-status-unknown"),
        ],
    )
    def test_non_hit_statuses_map_to_expected_reason(
        self, cache_status, cache_message, expected_status, expected_reason
    ):
        """Each non-hit cache status should map to deterministic UI semantics."""

        status, reason = _reach_cache_verification_from_read(
            cache_status=cache_status,
            cache_message=cache_message,
            input_hash=None,
            output_hash=None,
        )
        assert status == expected_status
        assert reason == expected_reason

    def test_hit_with_missing_hashes_maps_to_error(self):
        """Hit without canonical hashes should be flagged as verification error."""

        status, reason = _reach_cache_verification_from_read(
            cache_status="hit",
            cache_message=None,
            input_hash=None,
            output_hash="b" * 64,
        )
        assert status == "error"
        assert reason == "cache-hit-missing-hashes"


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def state():
    """Fresh ServerState with no data loaded."""
    return ServerState()


@pytest.fixture
def sample_annotated_data():
    """Minimal annotated syllable records for testing."""
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
            "syllable": "ri",
            "frequency": 80,
            "features": {
                "starts_with_vowel": False,
                "starts_with_cluster": False,
                "starts_with_heavy_cluster": False,
                "contains_plosive": False,
                "contains_fricative": False,
                "contains_liquid": True,
                "contains_nasal": False,
                "short_vowel": False,
                "long_vowel": True,
                "ends_with_vowel": True,
                "ends_with_nasal": False,
                "ends_with_stop": False,
            },
        },
    ]


@pytest.fixture
def loaded_state(state, sample_annotated_data):
    """ServerState with patch_a loaded and walker ready."""
    state.patch_a.run_id = "20260220_120000_pyphen"
    state.patch_a.corpus_type = "pyphen"
    state.patch_a.syllable_count = 2
    state.patch_a.annotated_data = sample_annotated_data
    state.patch_a.frequencies = {"ka": 100, "ri": 80}
    state.patch_a.walker = MagicMock()
    state.patch_a.walker_ready = True
    return state


@pytest.fixture
def state_with_candidates(loaded_state):
    """State with candidates generated."""
    loaded_state.patch_a.candidates = [
        {"name": "Kari", "syllables": ["ka", "ri"], "features": {}},
        {"name": "Rika", "syllables": ["ri", "ka"], "features": {}},
    ]
    return loaded_state


@pytest.fixture
def state_with_selections(state_with_candidates):
    """State with names selected."""
    state_with_candidates.patch_a.selected_names = [
        {"name": "Kari", "syllables": ["ka", "ri"], "features": {}, "score": 1.0},
    ]
    return state_with_candidates


# ============================================================
# handle_load_corpus
# ============================================================


class TestHandleLoadCorpus:
    """Test POST /api/walker/load-corpus handler."""

    def test_error_when_missing_run_id(self, state):
        """Test returns error if run_id not provided."""
        result = handle_load_corpus({"patch": "a"}, state)
        assert "error" in result

    def test_error_when_invalid_patch(self, state):
        """Test returns error for invalid patch key."""
        result = handle_load_corpus({"patch": "c", "run_id": "test"}, state)
        assert "error" in result

    def test_load_corpus_rejects_when_active_session_lock_owned_elsewhere(self, state):
        """Load corpus should fail when active session lock is held by another holder."""

        state.active_session_id = "session_locked"
        state.active_session_lock_holder_id = "holder_owner"
        with patch(
            "build_tools.syllable_walk_web.services.walker_session_lock.acquire_session_lock",
            return_value={
                "status": "locked",
                "reason": "session lock held by another holder",
                "lock": {"holder_id": "holder_owner"},
            },
        ):
            result = handle_load_corpus(
                {"patch": "a", "run_id": "run_a", "lock_holder_id": "holder_other"},
                state,
            )
        assert "error" in result
        assert result["lock_status"] == "locked"

    def test_error_when_run_not_found(self, state):
        """Test returns error when run_id doesn't match any discovered run."""
        with patch(
            "build_tools.syllable_walk_web.run_discovery.get_run_by_id",
            return_value=None,
        ):
            result = handle_load_corpus({"patch": "a", "run_id": "nonexistent"}, state)
        assert "error" in result

    def test_error_when_corpus_load_fails(self, state):
        """Test returns error when corpus loading raises an exception."""
        mock_run = MagicMock()
        mock_run.corpus_db_path = None
        mock_run.annotated_json_path = None

        with (
            patch(
                "build_tools.syllable_walk_web.run_discovery.get_run_by_id",
                return_value=mock_run,
            ),
            patch(
                "build_tools.syllable_walk.db.load_syllables",
                side_effect=RuntimeError("DB error"),
            ),
        ):
            result = handle_load_corpus({"patch": "a", "run_id": "test_run"}, state)
        assert "error" in result

    def test_success_loads_corpus(self, state, sample_annotated_data):
        """Test successful corpus loading updates patch state."""
        mock_run = MagicMock()
        mock_run.corpus_db_path = None
        mock_run.annotated_json_path = None
        mock_run.extractor_type = "pyphen"
        mock_run.path = "/test/path"
        mock_run.ipc_input_hash = "a" * 64
        mock_run.ipc_output_hash = "b" * 64

        with (
            patch(
                "build_tools.syllable_walk_web.run_discovery.get_run_by_id",
                return_value=mock_run,
            ),
            patch(
                "build_tools.syllable_walk.db.load_syllables",
                return_value=(sample_annotated_data, "from test"),
            ),
            patch(
                "build_tools.syllable_walk_web.services.pipeline_manifest.verify_manifest_ipc_file",
                return_value=ManifestIPCVerificationResult(
                    status="verified",
                    reason="hashes-match",
                    input_hash="a" * 64,
                    output_hash="b" * 64,
                ),
            ),
            patch("build_tools.syllable_walk.walker.SyllableWalker"),
        ):
            result = handle_load_corpus({"patch": "a", "run_id": "test_run"}, state)

        assert "error" not in result
        assert result["status"] == "loading"
        assert result["syllable_count"] == 2
        assert state.patch_a.syllable_count == 2
        assert state.patch_a.manifest_ipc_input_hash == "a" * 64
        assert state.patch_a.manifest_ipc_output_hash == "b" * 64
        assert state.patch_a.manifest_ipc_verification_status == "verified"
        assert state.patch_a.manifest_ipc_verification_reason == "hashes-match"

    def test_resets_old_state(self, loaded_state):
        """Test loading a new corpus resets walks/candidates/selections."""
        loaded_state.patch_a.walks = [{"old": True}]
        loaded_state.patch_a.candidates = [{"old": True}]
        loaded_state.patch_a.selected_names = [{"name": "Old"}]

        mock_run = MagicMock()
        mock_run.corpus_db_path = None
        mock_run.annotated_json_path = None
        mock_run.extractor_type = "pyphen"
        mock_run.path = "/new/path"

        with (
            patch(
                "build_tools.syllable_walk_web.run_discovery.get_run_by_id",
                return_value=mock_run,
            ),
            patch(
                "build_tools.syllable_walk.db.load_syllables",
                return_value=([{"syllable": "ta", "frequency": 50}], "test"),
            ),
            patch("build_tools.syllable_walk.walker.SyllableWalker"),
        ):
            handle_load_corpus({"patch": "a", "run_id": "new_run"}, loaded_state)

        assert loaded_state.patch_a.walks == []
        assert loaded_state.patch_a.candidates is None
        assert loaded_state.patch_a.selected_names == []

    def test_manual_load_releases_active_session_context_for_same_holder(self, state):
        """Manual corpus load should release/clear active session lock context."""

        state.active_session_id = "session_active"
        state.active_session_lock_holder_id = "holder_self"
        mock_run = MagicMock()
        mock_run.corpus_db_path = None
        mock_run.annotated_json_path = None
        mock_run.extractor_type = "pyphen"
        mock_run.path = "/new/path"

        class _ThreadNoStart:
            def __init__(self, target, daemon):
                self._target = target
                self._daemon = daemon

            def start(self):
                return None

        with (
            patch(
                "build_tools.syllable_walk_web.run_discovery.get_run_by_id",
                return_value=mock_run,
            ),
            patch(
                "build_tools.syllable_walk_web.services.corpus_loader.load_corpus",
                return_value=([{"syllable": "ta", "frequency": 50}], "test"),
            ),
            patch("build_tools.syllable_walk_web.api.walker.threading.Thread", _ThreadNoStart),
            patch(
                "build_tools.syllable_walk_web.services.walker_session_lock.release_session_lock"
            ) as mock_release,
        ):
            result = handle_load_corpus(
                {
                    "patch": "a",
                    "run_id": "new_run",
                    "lock_holder_id": "holder_self",
                },
                state,
            )

        assert "error" not in result
        mock_release.assert_called_once()
        assert state.active_session_id is None
        assert state.active_session_lock_holder_id is None

    def test_uses_corpus_dir_a_for_patch_a(self, state, tmp_path):
        """Test patch a discovers from corpus_dir_a when set."""

        state.corpus_dir_a = tmp_path

        with patch(
            "build_tools.syllable_walk_web.run_discovery.get_run_by_id",
            return_value=None,
        ) as mock_get_run:
            handle_load_corpus({"patch": "a", "run_id": "some_run"}, state)

        mock_get_run.assert_called_once_with("some_run", base_path=tmp_path)

    def test_uses_corpus_dir_b_for_patch_b(self, state, tmp_path):
        """Test patch b discovers from corpus_dir_b when set."""
        state.corpus_dir_b = tmp_path

        with patch(
            "build_tools.syllable_walk_web.run_discovery.get_run_by_id",
            return_value=None,
        ) as mock_get_run:
            handle_load_corpus({"patch": "b", "run_id": "some_run"}, state)

        mock_get_run.assert_called_once_with("some_run", base_path=tmp_path)

    def test_falls_back_to_output_base(self, state):
        """Test uses output_base when no corpus_dir configured."""
        with patch(
            "build_tools.syllable_walk_web.run_discovery.get_run_by_id",
            return_value=None,
        ) as mock_get_run:
            handle_load_corpus({"patch": "a", "run_id": "some_run"}, state)

        mock_get_run.assert_called_once_with("some_run", base_path=state.output_base)

    def test_load_generation_increments_with_each_request(self, state):
        """Each new corpus load should advance the patch generation token.

        The generation counter provides ordering for background loader
        threads. The newest request owns ``active_load_generation`` until
        its thread finishes.
        """
        run = MagicMock()
        run.corpus_db_path = None
        run.annotated_json_path = None
        run.extractor_type = "pyphen"
        run.path = "/test/path"
        run.ipc_input_hash = "a" * 64
        run.ipc_output_hash = "b" * 64

        created_targets = []

        class _ThreadNoStart:
            def __init__(self, target, daemon):
                self._target = target
                self._daemon = daemon
                created_targets.append(target)

            def start(self):
                # Deliberately no-op so tests can inspect state before
                # any background work mutates it.
                return None

        with (
            patch(
                "build_tools.syllable_walk_web.run_discovery.get_run_by_id",
                side_effect=[run, run],
            ),
            patch(
                "build_tools.syllable_walk_web.services.corpus_loader.load_corpus",
                side_effect=[
                    ([{"syllable": "ka", "frequency": 10}], "first"),
                    ([{"syllable": "ri", "frequency": 12}], "second"),
                ],
            ),
            patch("build_tools.syllable_walk_web.api.walker.threading.Thread", _ThreadNoStart),
        ):
            handle_load_corpus({"patch": "a", "run_id": "run_1"}, state)
            handle_load_corpus({"patch": "a", "run_id": "run_2"}, state)

        assert state.patch_a.load_generation == 2
        assert state.patch_a.active_load_generation == 2
        assert len(created_targets) == 2

    def test_stale_loader_thread_cannot_overwrite_newer_load(self, state):
        """Out-of-order completion must not let stale threads clobber state.

        This test queues two loads, executes the older thread first, and
        verifies it cannot update walker/readiness fields. Only the latest
        generation is allowed to publish results.
        """
        run_1 = MagicMock()
        run_1.corpus_db_path = None
        run_1.annotated_json_path = None
        run_1.extractor_type = "pyphen"
        run_1.path = "/run/one"

        run_2 = MagicMock()
        run_2.corpus_db_path = None
        run_2.annotated_json_path = None
        run_2.extractor_type = "nltk"
        run_2.path = "/run/two"

        created_targets = []

        class _ThreadNoStart:
            def __init__(self, target, daemon):
                self._target = target
                self._daemon = daemon
                created_targets.append(target)

            def start(self):
                return None

        def _from_data(data, max_neighbor_distance, progress_callback):
            marker = data[0]["syllable"]
            progress_callback(f"building-{marker}")
            return f"walker-{marker}"

        def _compute_reaches(walker, progress_callback):
            progress_callback(f"reaches-{walker}")
            return {"dialect": f"reach-{walker}"}

        with (
            patch(
                "build_tools.syllable_walk_web.run_discovery.get_run_by_id",
                side_effect=[run_1, run_2],
            ),
            patch(
                "build_tools.syllable_walk_web.services.corpus_loader.load_corpus",
                side_effect=[
                    ([{"syllable": "aa", "frequency": 1}], "first"),
                    ([{"syllable": "bb", "frequency": 2}], "second"),
                ],
            ),
            patch("build_tools.syllable_walk_web.api.walker.threading.Thread", _ThreadNoStart),
            patch(
                "build_tools.syllable_walk.walker.SyllableWalker.from_data",
                side_effect=_from_data,
            ),
            patch(
                "build_tools.syllable_walk.reach.compute_all_reaches",
                side_effect=_compute_reaches,
            ),
        ):
            handle_load_corpus({"patch": "a", "run_id": "run_1"}, state)
            handle_load_corpus({"patch": "a", "run_id": "run_2"}, state)

            # Run the stale worker after the second request has already
            # advanced generation ownership.
            created_targets[0]()
            assert state.patch_a.walker is None
            assert state.patch_a.profile_reaches is None
            assert state.patch_a.walker_ready is False
            assert state.patch_a.loading_stage == "Loading corpus data"
            assert state.patch_a.active_load_generation == 2

            # Now complete the current generation loader.
            created_targets[1]()

        assert state.patch_a.walker == "walker-bb"
        assert state.patch_a.profile_reaches == {"dialect": "reach-walker-bb"}
        assert state.patch_a.walker_ready is True
        assert state.patch_a.loading_stage is None
        assert state.patch_a.active_load_generation is None

    def test_loader_exception_clears_active_generation(self, state):
        """Current generation failures should clear loading state cleanly."""
        run = MagicMock()
        run.corpus_db_path = None
        run.annotated_json_path = None
        run.extractor_type = "pyphen"
        run.path = "/test/path"

        class _ThreadInline:
            def __init__(self, target, daemon):
                self._target = target
                self._daemon = daemon

            def start(self):
                self._target()

        with (
            patch(
                "build_tools.syllable_walk_web.run_discovery.get_run_by_id",
                return_value=run,
            ),
            patch(
                "build_tools.syllable_walk_web.services.corpus_loader.load_corpus",
                return_value=([{"syllable": "ka", "frequency": 10}], "test"),
            ),
            patch("build_tools.syllable_walk_web.api.walker.threading.Thread", _ThreadInline),
            patch(
                "build_tools.syllable_walk.walker.SyllableWalker.from_data",
                side_effect=RuntimeError("boom"),
            ),
        ):
            result = handle_load_corpus({"patch": "a", "run_id": "run_1"}, state)

        assert result["status"] == "loading"
        assert state.patch_a.load_generation == 1
        assert state.patch_a.active_load_generation is None
        assert state.patch_a.walker_ready is False
        assert state.patch_a.loading_stage is None
        assert state.patch_a.loading_error == "Walker initialisation failed: boom"

    def test_new_load_clears_previous_loading_error(self, state):
        """A new load request should clear stale terminal error state."""
        state.patch_a.loading_error = "Walker initialisation failed: old"
        run = MagicMock()
        run.corpus_db_path = None
        run.annotated_json_path = None
        run.extractor_type = "pyphen"
        run.path = "/test/path"

        class _ThreadNoStart:
            def __init__(self, target, daemon):
                self._target = target
                self._daemon = daemon

            def start(self):
                return None

        with (
            patch(
                "build_tools.syllable_walk_web.run_discovery.get_run_by_id",
                return_value=run,
            ),
            patch(
                "build_tools.syllable_walk_web.services.corpus_loader.load_corpus",
                return_value=([{"syllable": "ka", "frequency": 10}], "test"),
            ),
            patch("build_tools.syllable_walk_web.api.walker.threading.Thread", _ThreadNoStart),
        ):
            handle_load_corpus({"patch": "a", "run_id": "run_1"}, state)

        assert state.patch_a.loading_error is None

    def test_rejects_non_string_patch(self, state):
        """Non-string patch key should fail validation via _resolve_patch_state."""
        result = handle_load_corpus({"patch": 123, "run_id": "run_1"}, state)
        assert "error" in result
        assert "Invalid patch" in result["error"]

    def test_stale_generation_after_from_data_is_ignored(self, state):
        """If generation changes after walker build, thread exits without publish."""
        run = MagicMock()
        run.corpus_db_path = None
        run.annotated_json_path = None
        run.extractor_type = "pyphen"
        run.path = "/test/path"

        class _ThreadInline:
            def __init__(self, target, daemon):
                self._target = target
                self._daemon = daemon

            def start(self):
                self._target()

        def _from_data(*args, **kwargs):
            # Simulate another load claiming generation ownership after build.
            state.patch_a.active_load_generation = 999
            return "walker-a"

        with (
            patch(
                "build_tools.syllable_walk_web.run_discovery.get_run_by_id",
                return_value=run,
            ),
            patch(
                "build_tools.syllable_walk_web.services.corpus_loader.load_corpus",
                return_value=([{"syllable": "ka", "frequency": 10}], "test"),
            ),
            patch("build_tools.syllable_walk_web.api.walker.threading.Thread", _ThreadInline),
            patch(
                "build_tools.syllable_walk.walker.SyllableWalker.from_data",
                side_effect=_from_data,
            ),
            patch("build_tools.syllable_walk.reach.compute_all_reaches") as mock_reaches,
        ):
            handle_load_corpus({"patch": "a", "run_id": "run_1"}, state)

        assert state.patch_a.walker is None
        assert state.patch_a.profile_reaches is None
        assert state.patch_a.walker_ready is False
        mock_reaches.assert_not_called()

    def test_stale_generation_after_reach_compute_is_ignored(self, state):
        """If generation changes after reach compute, results are not published."""
        run = MagicMock()
        run.corpus_db_path = None
        run.annotated_json_path = None
        run.extractor_type = "pyphen"
        run.path = "/test/path"

        class _ThreadInline:
            def __init__(self, target, daemon):
                self._target = target
                self._daemon = daemon

            def start(self):
                self._target()

        def _compute_reaches(*args, **kwargs):
            # Simulate newer load taking ownership right before publish.
            state.patch_a.active_load_generation = 999
            return {"dialect": "reach-a"}

        with (
            patch(
                "build_tools.syllable_walk_web.run_discovery.get_run_by_id",
                return_value=run,
            ),
            patch(
                "build_tools.syllable_walk_web.services.corpus_loader.load_corpus",
                return_value=([{"syllable": "ka", "frequency": 10}], "test"),
            ),
            patch("build_tools.syllable_walk_web.api.walker.threading.Thread", _ThreadInline),
            patch(
                "build_tools.syllable_walk.walker.SyllableWalker.from_data",
                return_value="walker-a",
            ),
            patch(
                "build_tools.syllable_walk.reach.compute_all_reaches",
                side_effect=_compute_reaches,
            ),
        ):
            handle_load_corpus({"patch": "a", "run_id": "run_1"}, state)

        assert state.patch_a.walker is None
        assert state.patch_a.profile_reaches is None
        assert state.patch_a.walker_ready is False

    def test_load_uses_profile_reach_cache_when_available(self, state):
        """Cache hit should skip compute_all_reaches and publish cached values."""

        run = MagicMock()
        run.corpus_db_path = None
        run.annotated_json_path = None
        run.extractor_type = "pyphen"
        run.path = "/test/path"

        cached_reaches = {
            "dialect": ReachResult(
                profile_name="dialect",
                reach=7,
                total=100,
                threshold=0.001,
                max_flips=2,
                temperature=0.7,
                frequency_weight=0.0,
                computation_ms=4.2,
                unique_reachable=12,
                reachable_indices=((0, 4),),
            ),
        }

        class _ThreadInline:
            def __init__(self, target, daemon):
                self._target = target
                self._daemon = daemon

            def start(self):
                self._target()

        with (
            patch(
                "build_tools.syllable_walk_web.run_discovery.get_run_by_id",
                return_value=run,
            ),
            patch(
                "build_tools.syllable_walk_web.services.corpus_loader.load_corpus",
                return_value=([{"syllable": "ka", "frequency": 10}], "test"),
            ),
            patch("build_tools.syllable_walk_web.api.walker.threading.Thread", _ThreadInline),
            patch(
                "build_tools.syllable_walk.walker.SyllableWalker.from_data",
                return_value="walker-a",
            ),
            patch(
                "build_tools.syllable_walk_web.services.profile_reaches_cache.load_cached_profile_reaches",
                return_value=CacheReadResult(
                    status="hit",
                    profile_reaches=cached_reaches,
                    ipc_input_hash="c" * 64,
                    ipc_output_hash="d" * 64,
                ),
            ) as mock_cache_load,
            patch("build_tools.syllable_walk.reach.compute_all_reaches") as mock_compute_reaches,
            patch(
                "build_tools.syllable_walk_web.services.profile_reaches_cache.write_cached_profile_reaches",
                return_value=True,
            ) as mock_cache_write,
        ):
            handle_load_corpus({"patch": "a", "run_id": "run_1"}, state)

        mock_cache_load.assert_called_once()
        mock_compute_reaches.assert_not_called()
        mock_cache_write.assert_not_called()
        assert state.patch_a.walker == "walker-a"
        assert state.patch_a.profile_reaches == cached_reaches
        assert state.patch_a.reach_cache_status == "hit"
        assert state.patch_a.reach_cache_ipc_input_hash == "c" * 64
        assert state.patch_a.reach_cache_ipc_output_hash == "d" * 64
        assert state.patch_a.reach_cache_ipc_verification_status == "verified"
        assert state.patch_a.reach_cache_ipc_verification_reason == "cache-hit-hashes-match"
        assert state.patch_a.walker_ready is True

    def test_load_computes_and_writes_cache_when_missing(self, state):
        """Cache miss should compute reaches and persist a new cache artifact."""

        run = MagicMock()
        run.corpus_db_path = None
        run.annotated_json_path = None
        run.extractor_type = "pyphen"
        run.path = "/test/path"
        run.ipc_input_hash = "a" * 64
        run.ipc_output_hash = "b" * 64

        computed_reaches = {
            "dialect": ReachResult(
                profile_name="dialect",
                reach=8,
                total=100,
                threshold=0.001,
                max_flips=2,
                temperature=0.7,
                frequency_weight=0.0,
                computation_ms=4.2,
                unique_reachable=14,
                reachable_indices=((0, 5),),
            ),
        }

        class _ThreadInline:
            def __init__(self, target, daemon):
                self._target = target
                self._daemon = daemon

            def start(self):
                self._target()

        with (
            patch(
                "build_tools.syllable_walk_web.run_discovery.get_run_by_id",
                return_value=run,
            ),
            patch(
                "build_tools.syllable_walk_web.services.corpus_loader.load_corpus",
                return_value=([{"syllable": "ka", "frequency": 10}], "test"),
            ),
            patch("build_tools.syllable_walk_web.api.walker.threading.Thread", _ThreadInline),
            patch(
                "build_tools.syllable_walk.walker.SyllableWalker.from_data",
                return_value="walker-a",
            ),
            patch(
                "build_tools.syllable_walk_web.services.profile_reaches_cache.load_cached_profile_reaches",
                return_value=CacheReadResult(status="miss"),
            ),
            patch(
                "build_tools.syllable_walk.reach.compute_all_reaches",
                return_value=computed_reaches,
            ) as mock_compute_reaches,
            patch(
                "build_tools.syllable_walk_web.services.profile_reaches_cache.write_cached_profile_reaches",
                return_value=True,
            ) as mock_cache_write,
            patch(
                "build_tools.syllable_walk_web.services.profile_reaches_cache.read_cached_profile_reach_hashes",
                return_value=("e" * 64, "f" * 64),
            ),
        ):
            handle_load_corpus({"patch": "a", "run_id": "run_1"}, state)

        mock_compute_reaches.assert_called_once()
        mock_cache_write.assert_called_once()
        assert state.patch_a.profile_reaches == computed_reaches
        assert state.patch_a.reach_cache_status == "miss"
        assert state.patch_a.reach_cache_ipc_input_hash == "e" * 64
        assert state.patch_a.reach_cache_ipc_output_hash == "f" * 64
        assert state.patch_a.reach_cache_ipc_verification_status == "verified"
        assert state.patch_a.reach_cache_ipc_verification_reason == "cache-written-after-miss"
        assert state.patch_a.walker_ready is True


# ============================================================
# handle_walk
# ============================================================


class TestHandleWalk:
    """Test POST /api/walker/walk handler."""

    def test_error_when_patch_invalid(self, loaded_state):
        """Test returns error when patch is not 'a' or 'b'."""
        result = handle_walk({"patch": "c"}, loaded_state)
        assert "error" in result

    def test_error_when_walker_not_ready(self, state):
        """Test returns error when no corpus loaded."""
        result = handle_walk({"patch": "a"}, state)
        assert "error" in result

    def test_walk_rejects_when_active_session_lock_owned_by_other_holder(self, loaded_state):
        """Mutating walk action should fail when active session lock is not owned."""

        loaded_state.active_session_id = "session_1"
        loaded_state.active_session_lock_holder_id = "holder_owner"
        with patch(
            "build_tools.syllable_walk_web.services.walker_session_lock.acquire_session_lock",
            return_value={
                "status": "locked",
                "reason": "session lock held by another holder",
                "lock": {"holder_id": "holder_owner"},
            },
        ):
            result = handle_walk(
                {"patch": "a", "count": 1, "lock_holder_id": "holder_other"},
                loaded_state,
            )
        assert "error" in result
        assert result["lock_status"] == "locked"

    def test_success_generates_walks(self, loaded_state):
        """Test successful walk generation."""
        mock_walks = [
            {"formatted": "ka·ri", "syllables": ["ka", "ri"], "steps": []},
        ]
        with (
            patch(
                "build_tools.syllable_walk_web.services.walk_generator.generate_walks",
                return_value=mock_walks,
            ),
            patch(
                "build_tools.syllable_walk_web.services.walker_run_state_store.save_run_state",
            ) as mock_save,
        ):
            result = handle_walk({"patch": "a", "count": 1}, loaded_state)

        assert "error" not in result
        assert result["patch"] == "a"
        assert len(result["walks"]) == 1
        assert loaded_state.patch_a.walks == mock_walks
        mock_save.assert_called_once()
        assert mock_save.call_args.kwargs["patch"] == "a"
        assert mock_save.call_args.kwargs["artifact_kind"] == "walks"

    def test_walk_succeeds_when_sidecar_persist_raises(self, loaded_state):
        """Sidecar persistence failures should not fail walk API responses."""

        mock_walks = [{"formatted": "ka·ri", "syllables": ["ka", "ri"], "steps": []}]
        with (
            patch(
                "build_tools.syllable_walk_web.services.walk_generator.generate_walks",
                return_value=mock_walks,
            ),
            patch(
                "build_tools.syllable_walk_web.services.walker_run_state_store.save_run_state",
                side_effect=RuntimeError("io-error"),
            ),
        ):
            result = handle_walk({"patch": "a", "count": 1}, loaded_state)

        assert "error" not in result
        assert result["patch"] == "a"
        assert result["walks"] == mock_walks

    def test_walk_forwards_neighbor_and_length_constraints(self, loaded_state):
        """Walk handler passes min/max length and neighbor cap to service."""
        mock_walks = [{"formatted": "ka·ri", "syllables": ["ka", "ri"], "steps": []}]
        with patch(
            "build_tools.syllable_walk_web.services.walk_generator.generate_walks",
            return_value=mock_walks,
        ) as mock_generate:
            result = handle_walk(
                {
                    "patch": "a",
                    "count": 1,
                    "steps": 3,
                    "neighbor_limit": 9,
                    "min_length": 2,
                    "max_length": 6,
                },
                loaded_state,
            )

        assert "error" not in result
        _, kwargs = mock_generate.call_args
        assert kwargs["neighbor_limit"] == 9
        assert kwargs["min_length"] == 2
        assert kwargs["max_length"] == 6

    def test_walk_allows_null_optional_constraints(self, loaded_state):
        """Null min/max/neighbor values disable optional runtime constraints."""
        mock_walks = [{"formatted": "ka·ri", "syllables": ["ka", "ri"], "steps": []}]
        with patch(
            "build_tools.syllable_walk_web.services.walk_generator.generate_walks",
            return_value=mock_walks,
        ) as mock_generate:
            result = handle_walk(
                {
                    "patch": "a",
                    "count": 1,
                    "neighbor_limit": None,
                    "min_length": None,
                    "max_length": None,
                },
                loaded_state,
            )

        assert "error" not in result
        _, kwargs = mock_generate.call_args
        assert kwargs["neighbor_limit"] is None
        assert kwargs["min_length"] is None
        assert kwargs["max_length"] is None

    def test_walk_rejects_min_length_greater_than_max_length(self, loaded_state):
        """API validation rejects impossible length constraints."""
        result = handle_walk(
            {
                "patch": "a",
                "min_length": 7,
                "max_length": 3,
            },
            loaded_state,
        )
        assert "error" in result
        assert "min_length must be <= max_length" in result["error"]

    def test_walk_rejects_non_numeric_parameters(self, loaded_state):
        """Non-numeric numeric fields should return validation error."""
        result = handle_walk({"patch": "a", "count": "not-an-int"}, loaded_state)
        assert "error" in result
        assert "expected numeric values" in result["error"]

    def test_walk_rejects_invalid_seed(self, loaded_state):
        """Seed must be integer or null."""
        result = handle_walk({"patch": "a", "seed": "bad-seed"}, loaded_state)
        assert "error" in result
        assert "Invalid seed" in result["error"]

    @pytest.mark.parametrize("field_name", ["neighbor_limit", "min_length", "max_length"])
    def test_walk_rejects_non_numeric_optional_constraint(self, loaded_state, field_name):
        """Optional constraints must be integer or null when provided."""
        body = {"patch": "a", field_name: "not-an-int"}
        result = handle_walk(body, loaded_state)
        assert "error" in result
        assert f"{field_name} must be an integer or null" in result["error"]

    @pytest.mark.parametrize(
        ("payload", "expected"),
        [
            ({"count": 0}, "count must be >= 1"),
            ({"steps": -1}, "steps must be >= 0"),
            ({"max_flips": 0}, "max_flips must be >= 1"),
            ({"neighbor_limit": 0}, "neighbor_limit must be >= 1"),
            ({"min_length": 0}, "min_length must be >= 1"),
            ({"max_length": 0}, "max_length must be >= 1"),
            ({"temperature": 0}, "temperature must be > 0"),
        ],
    )
    def test_walk_rejects_invalid_ranges(self, loaded_state, payload, expected):
        """Each API numeric bound violation should return a clear error."""
        body = {"patch": "a"}
        body.update(payload)
        result = handle_walk(body, loaded_state)
        assert "error" in result
        assert expected in result["error"]

    def test_walk_failure_returns_error(self, loaded_state):
        """Test walk generation exception returns error."""
        with patch(
            "build_tools.syllable_walk_web.services.walk_generator.generate_walks",
            side_effect=RuntimeError("Walker error"),
        ):
            result = handle_walk({"patch": "a"}, loaded_state)

        assert "error" in result


# ============================================================
# handle_stats
# ============================================================


class TestHandleStats:
    """Test GET /api/walker/stats handler."""

    def test_empty_state(self, state):
        """Test stats for empty patches."""
        result = handle_stats(state)
        assert "patch_a" in result
        assert "patch_b" in result
        assert result["patch_a"]["corpus"] is None
        assert result["patch_a"]["walker_ready"] is False
        assert result["patch_a"]["loader_status"] == "idle"
        assert result["patch_a"]["loading_error"] is None
        assert result["patch_a"]["reach_cache_status"] is None
        assert result["patch_a"]["manifest_ipc_input_hash"] is None
        assert result["patch_a"]["manifest_ipc_output_hash"] is None
        assert result["patch_a"]["manifest_ipc_verification_status"] is None
        assert result["patch_a"]["manifest_ipc_verification_reason"] is None
        assert result["patch_a"]["reach_cache_ipc_input_hash"] is None
        assert result["patch_a"]["reach_cache_ipc_output_hash"] is None
        assert result["patch_a"]["reach_cache_ipc_verification_status"] is None
        assert result["patch_a"]["reach_cache_ipc_verification_reason"] is None

    def test_loaded_state(self, loaded_state):
        """Test stats reflect loaded corpus."""
        result = handle_stats(loaded_state)
        assert result["patch_a"]["corpus"] == "20260220_120000_pyphen"
        assert result["patch_a"]["walker_ready"] is True
        assert result["patch_a"]["syllable_count"] == 2
        assert result["patch_a"]["loader_status"] == "ready"
        assert result["patch_a"]["loading_error"] is None
        assert result["patch_a"]["reach_cache_status"] is None
        assert result["patch_a"]["manifest_ipc_input_hash"] is None
        assert result["patch_a"]["manifest_ipc_output_hash"] is None
        assert result["patch_a"]["manifest_ipc_verification_status"] is None
        assert result["patch_a"]["manifest_ipc_verification_reason"] is None
        assert result["patch_a"]["reach_cache_ipc_input_hash"] is None
        assert result["patch_a"]["reach_cache_ipc_output_hash"] is None
        assert result["patch_a"]["reach_cache_ipc_verification_status"] is None
        assert result["patch_a"]["reach_cache_ipc_verification_reason"] is None

    def test_stats_include_reach_cache_status(self, state):
        """Stats payload should expose cache read status for UI diagnostics."""

        state.patch_a.run_id = "run_cache"
        state.patch_a.manifest_ipc_input_hash = "a" * 64
        state.patch_a.manifest_ipc_output_hash = "b" * 64
        state.patch_a.manifest_ipc_verification_status = "verified"
        state.patch_a.manifest_ipc_verification_reason = "hashes-match"
        state.patch_a.reach_cache_status = "hit"
        state.patch_a.reach_cache_ipc_input_hash = "c" * 64
        state.patch_a.reach_cache_ipc_output_hash = "d" * 64
        state.patch_a.reach_cache_ipc_verification_status = "verified"
        state.patch_a.reach_cache_ipc_verification_reason = "cache-hit-hashes-match"

        result = handle_stats(state)
        assert result["patch_a"]["reach_cache_status"] == "hit"
        assert result["patch_a"]["manifest_ipc_input_hash"] == "a" * 64
        assert result["patch_a"]["manifest_ipc_output_hash"] == "b" * 64
        assert result["patch_a"]["manifest_ipc_verification_status"] == "verified"
        assert result["patch_a"]["manifest_ipc_verification_reason"] == "hashes-match"
        assert result["patch_a"]["reach_cache_ipc_input_hash"] == "c" * 64
        assert result["patch_a"]["reach_cache_ipc_output_hash"] == "d" * 64
        assert result["patch_a"]["reach_cache_ipc_verification_status"] == "verified"
        assert result["patch_a"]["reach_cache_ipc_verification_reason"] == "cache-hit-hashes-match"

    def test_stats_loading_and_error_states(self, state):
        """Stats surface loading and error states for UI polling logic."""
        state.patch_a.run_id = "run_loading"
        state.patch_a.active_load_generation = 3
        state.patch_a.loading_stage = "Building neighbour graph"

        loading_result = handle_stats(state)
        assert loading_result["patch_a"]["loader_status"] == "loading"
        assert loading_result["patch_a"]["loading_error"] is None

        state.patch_a.active_load_generation = None
        state.patch_a.loading_stage = None
        state.patch_a.loading_error = "Walker initialisation failed: graph"

        error_result = handle_stats(state)
        assert error_result["patch_a"]["loader_status"] == "error"
        assert error_result["patch_a"]["loading_error"] == "Walker initialisation failed: graph"

    def test_stats_idle_with_run_loaded_but_not_initialising(self, state):
        """run_id without active generation should report idle."""
        state.patch_a.run_id = "20260222_000000_pyphen"
        state.patch_a.walker_ready = False
        state.patch_a.active_load_generation = None
        state.patch_a.loading_error = None
        state.patch_a.loading_stage = None
        result = handle_stats(state)
        assert result["patch_a"]["loader_status"] == "idle"

    def test_stats_include_reaches_when_computed(self, loaded_state):
        """Stats response includes reaches once profile_reaches is populated.

        After the background walker init computes reaches, the stats
        endpoint should include a 'reaches' dict with all four profiles.
        """
        from build_tools.syllable_walk.reach import ReachResult

        # Simulate what _init_walker does after computing reaches.
        loaded_state.patch_a.profile_reaches = {
            "clerical": ReachResult(
                profile_name="clerical",
                reach=10,
                total=100,
                threshold=0.001,
                max_flips=1,
                temperature=0.3,
                frequency_weight=1.0,
                computation_ms=5.0,
                unique_reachable=42,
            ),
            "dialect": ReachResult(
                profile_name="dialect",
                reach=25,
                total=100,
                threshold=0.001,
                max_flips=2,
                temperature=0.7,
                frequency_weight=0.0,
                computation_ms=6.0,
                unique_reachable=75,
            ),
        }

        result = handle_stats(loaded_state)
        patch_a = result["patch_a"]

        assert "reaches" in patch_a
        assert "clerical" in patch_a["reaches"]
        assert "dialect" in patch_a["reaches"]
        assert patch_a["reaches"]["clerical"]["reach"] == 10
        assert patch_a["reaches"]["clerical"]["total"] == 100
        assert patch_a["reaches"]["clerical"]["threshold"] == 0.001
        assert patch_a["reaches"]["clerical"]["computation_ms"] == 5.0
        assert patch_a["reaches"]["clerical"]["unique_reachable"] == 42
        assert patch_a["reaches"]["dialect"]["unique_reachable"] == 75

    def test_stats_no_reaches_before_computed(self, state):
        """Stats response should not include reaches when profile_reaches is None.

        Before the walker finishes loading, profile_reaches is None,
        and the stats response should not contain a 'reaches' key.
        """
        result = handle_stats(state)
        assert "reaches" not in result["patch_a"]
        assert "reaches" not in result["patch_b"]

    def test_stats_reaches_absent_for_unloaded_patch(self, loaded_state):
        """Patch B should have no reaches when only Patch A is loaded."""
        from build_tools.syllable_walk.reach import ReachResult

        loaded_state.patch_a.profile_reaches = {
            "ritual": ReachResult(
                profile_name="ritual",
                reach=80,
                total=100,
                threshold=0.001,
                max_flips=3,
                temperature=2.5,
                frequency_weight=-1.0,
                computation_ms=8.0,
            ),
        }

        result = handle_stats(loaded_state)
        assert "reaches" in result["patch_a"]
        assert "reaches" not in result["patch_b"]

    def test_stats_include_patch_comparison_same_hash(self, loaded_state):
        """Stats should report same corpus relation when hashes match."""

        loaded_state.patch_a.manifest_ipc_output_hash = "a" * 64
        loaded_state.patch_b.manifest_ipc_output_hash = "a" * 64
        result = handle_stats(loaded_state)
        comparison = result["patch_comparison"]
        assert comparison["corpus_hash_relation"] == "same"
        assert comparison["policy"] == "none"

    def test_stats_include_patch_comparison_different_hash(self, loaded_state):
        """Stats should report warn policy when corpus hashes differ."""

        loaded_state.patch_a.manifest_ipc_output_hash = "a" * 64
        loaded_state.patch_b.manifest_ipc_output_hash = "b" * 64
        result = handle_stats(loaded_state)
        comparison = result["patch_comparison"]
        assert comparison["corpus_hash_relation"] == "different"
        assert comparison["policy"] == "warn"


# ============================================================
# session endpoints
# ============================================================


class TestSessionEndpoints:
    """Test session save/list/load API handlers."""

    def test_save_session_rejects_invalid_label_type(self, state):
        """Save endpoint should reject non-string labels."""

        result = handle_save_session({"label": 123}, state)
        assert "error" in result
        assert "label must be a string" in result["error"]

    def test_save_session_rejects_invalid_session_id_type(self, state):
        """Save endpoint should reject non-string session IDs."""

        result = handle_save_session({"session_id": 123}, state)
        assert "error" in result
        assert "session_id must be a string" in result["error"]

    def test_save_session_rejects_invalid_repair_source_type(self, state):
        """Save endpoint should reject non-string repair source session IDs."""

        result = handle_save_session({"repair_from_session_id": 123}, state)
        assert "error" in result
        assert "repair_from_session_id must be a string" in result["error"]

    def test_save_session_success(self, state):
        """Save endpoint should map service result into API response shape."""

        with patch(
            "build_tools.syllable_walk_web.services.walker_session_store.save_session",
            return_value=SimpleNamespace(
                status="saved",
                reason="saved",
                session_id="session_1",
                session_path=Path("/tmp/sessions/session_1.json"),
                patch_a_status="saved",
                patch_a_reason="saved",
                patch_b_status="skipped",
                patch_b_reason="patch-b-run-id-missing",
                ipc_input_hash="a" * 64,
                ipc_output_hash="b" * 64,
                root_session_id="session_1",
                parent_session_id=None,
                revision=0,
            ),
        ):
            result = handle_save_session({"label": "Snapshot"}, state)

        assert "error" not in result
        assert result["status"] == "saved"
        assert result["session_id"] == "session_1"
        assert result["patch_a"]["status"] == "saved"
        assert result["patch_b"]["status"] == "skipped"
        assert result["ipc_input_hash"] == "a" * 64
        assert result["root_session_id"] == "session_1"
        assert result["parent_session_id"] is None
        assert result["revision"] == 0

    def test_save_session_returns_error_when_service_raises(self, state):
        """Service exceptions should be mapped to API error payloads."""

        with patch(
            "build_tools.syllable_walk_web.services.walker_session_store.save_session",
            side_effect=RuntimeError("disk-full"),
        ):
            result = handle_save_session({"label": "Snapshot"}, state)
        assert "error" in result
        assert "Session save failed" in result["error"]

    def test_save_session_rejects_when_active_session_lock_owned_elsewhere(self, state):
        """Save session should fail when active session lock is held by another holder."""

        state.active_session_id = "session_locked"
        state.active_session_lock_holder_id = "holder_owner"
        with patch(
            "build_tools.syllable_walk_web.services.walker_session_lock.acquire_session_lock",
            return_value={
                "status": "locked",
                "reason": "session lock held by another holder",
                "lock": {"holder_id": "holder_owner"},
            },
        ):
            result = handle_save_session({"lock_holder_id": "holder_other"}, state)
        assert "error" in result
        assert result["lock_status"] == "locked"

    def test_sessions_list_success(self, state):
        """List endpoint should return serialized session entries."""

        with patch(
            "build_tools.syllable_walk_web.services.walker_session_store.list_sessions",
            return_value=[
                SimpleNamespace(
                    session_id="session_1",
                    created_at_utc="2026-02-23T12:00:00Z",
                    label="Snapshot",
                    patch_a_run_id="run_a",
                    patch_b_run_id=None,
                    verification_status="verified",
                    verification_reason="verified",
                    session_path=Path("/tmp/sessions/session_1.json"),
                    root_session_id="session_1",
                    parent_session_id=None,
                    revision=0,
                )
            ],
        ):
            result = handle_sessions(state)

        assert "error" not in result
        assert len(result["sessions"]) == 1
        assert result["sessions"][0]["session_id"] == "session_1"
        assert result["sessions"][0]["verification_status"] == "verified"
        assert result["sessions"][0]["root_session_id"] == "session_1"
        assert result["sessions"][0]["revision"] == 0
        assert result["sessions"][0]["lock_status"] == "unlocked"
        assert result["sessions"][0]["lock"] is None

    def test_sessions_list_includes_active_lock_metadata(self, state):
        """List endpoint should include lock metadata for currently locked sessions."""

        state.walker_session_locks["session_1"] = {
            "session_id": "session_1",
            "holder_id": "holder_abc",
            "acquired_at_utc": "2026-02-23T12:00:00Z",
            "refreshed_at_utc": "2026-02-23T12:00:10Z",
            "expires_at_utc": "2099-01-01T00:00:00Z",
            "expires_at_epoch": 4_070_908_800.0,
        }

        with patch(
            "build_tools.syllable_walk_web.services.walker_session_store.list_sessions",
            return_value=[
                SimpleNamespace(
                    session_id="session_1",
                    created_at_utc="2026-02-23T12:00:00Z",
                    label="Snapshot",
                    patch_a_run_id="run_a",
                    patch_b_run_id=None,
                    verification_status="verified",
                    verification_reason="verified",
                    session_path=Path("/tmp/sessions/session_1.json"),
                    root_session_id="session_1",
                    parent_session_id=None,
                    revision=0,
                )
            ],
        ):
            result = handle_sessions(state)

        assert result["sessions"][0]["lock_status"] == "locked"
        assert result["sessions"][0]["lock"]["holder_id"] == "holder_abc"

    def test_sessions_list_returns_error_when_service_raises(self, state):
        """List endpoint should return explicit service errors."""

        with patch(
            "build_tools.syllable_walk_web.services.walker_session_store.list_sessions",
            side_effect=RuntimeError("read-error"),
        ):
            result = handle_sessions(state)
        assert "error" in result
        assert "Session listing failed" in result["error"]

    def test_load_session_requires_session_id(self, state):
        """Load endpoint should reject missing/invalid session IDs."""

        result = handle_load_session({}, state)
        assert "error" in result
        assert "session_id" in result["error"]

    def test_load_session_returns_non_verified_status(self, state):
        """Load endpoint should return verification result without restoring."""

        with patch(
            "build_tools.syllable_walk_web.services.walker_session_store.load_session",
            return_value=SimpleNamespace(
                status="missing",
                reason="session-missing",
                session_id="session_404",
                payload=None,
                ipc_input_hash=None,
                ipc_output_hash=None,
            ),
        ):
            result = handle_load_session({"session_id": "session_404"}, state)

        assert "error" not in result
        assert result["status"] == "missing"
        assert result["patch_a"]["loaded"] is False
        assert result["patch_b"]["loaded"] is False

    def test_load_session_recovers_from_stale_run_state_hash_mismatch(self, state):
        """Hash-drift mismatch should recover via raw session payload when possible."""

        stale_payload = {
            "session_id": "session_ok",
            "patch_a": {"run_id": "run_a"},
            "patch_b": None,
        }
        with (
            patch(
                "build_tools.syllable_walk_web.services.walker_session_store.load_session",
                return_value=SimpleNamespace(
                    status="mismatch",
                    reason="session-a-run-state-output-hash-mismatch",
                    session_id="session_ok",
                    payload=None,
                    session_path=Path("/tmp/sessions/session_ok.json"),
                    ipc_input_hash="a" * 64,
                    ipc_output_hash="b" * 64,
                ),
            ),
            patch(
                "build_tools.syllable_walk_web.api.walker._read_json_object",
                return_value=stale_payload,
            ),
            patch(
                "build_tools.syllable_walk_web.api.walker.handle_load_corpus",
                return_value={
                    "status": "loading",
                    "source": "annotated_json",
                    "syllable_count": 12,
                },
            ),
            patch(
                "build_tools.syllable_walk_web.api.walker._restore_patch_artifacts_from_run_state",
                return_value={
                    "status": "verified",
                    "reason": "run-state-restored",
                    "restored": True,
                    "restored_kinds": ["walks"],
                    "run_state_ipc_input_hash": "c" * 64,
                    "run_state_ipc_output_hash": "d" * 64,
                },
            ),
        ):
            result = handle_load_session({"session_id": "session_ok"}, state)

        assert "error" not in result
        assert result["status"] == "mismatch"
        assert result["reason"] == "session-a-run-state-output-hash-mismatch"
        assert result["recovered_from_stale_session"] is True
        assert result["patch_a"]["loaded"] is True
        assert result["patch_a"]["restored"] is True
        assert result["patch_a"]["verification_status"] == "verified"
        assert result["patch_b"]["loaded"] is False

    def test_load_session_returns_error_when_service_raises(self, state):
        """Load endpoint should map service exceptions to API errors."""

        with patch(
            "build_tools.syllable_walk_web.services.walker_session_store.load_session",
            side_effect=RuntimeError("io-error"),
        ):
            result = handle_load_session({"session_id": "session_1"}, state)
        assert "error" in result
        assert "Session load failed" in result["error"]

    def test_load_session_handles_absent_patch_reference(self, state):
        """Verified session with absent patch ref should be marked missing."""

        payload = {"session_id": "session_ok", "patch_a": None, "patch_b": {"run_id": "run_b"}}
        with (
            patch(
                "build_tools.syllable_walk_web.services.walker_session_store.load_session",
                return_value=SimpleNamespace(
                    status="verified",
                    reason="verified",
                    session_id="session_ok",
                    payload=payload,
                    ipc_input_hash="a" * 64,
                    ipc_output_hash="b" * 64,
                ),
            ),
            patch(
                "build_tools.syllable_walk_web.api.walker.handle_load_corpus",
                return_value={
                    "status": "loading",
                    "source": "annotated_json",
                    "syllable_count": 12,
                },
            ),
        ):
            result = handle_load_session({"session_id": "session_ok"}, state)

        assert result["patch_a"]["verification_status"] == "missing"
        assert result["patch_b"]["loaded"] is True

    def test_load_session_handles_invalid_patch_reference_shape(self, state):
        """Verified session with non-object patch ref should be mismatch."""

        payload = {"session_id": "session_ok", "patch_a": "bad", "patch_b": {"run_id": "run_b"}}
        with (
            patch(
                "build_tools.syllable_walk_web.services.walker_session_store.load_session",
                return_value=SimpleNamespace(
                    status="verified",
                    reason="verified",
                    session_id="session_ok",
                    payload=payload,
                    ipc_input_hash="a" * 64,
                    ipc_output_hash="b" * 64,
                ),
            ),
            patch(
                "build_tools.syllable_walk_web.api.walker.handle_load_corpus",
                return_value={
                    "status": "loading",
                    "source": "annotated_json",
                    "syllable_count": 12,
                },
            ),
        ):
            result = handle_load_session({"session_id": "session_ok"}, state)

        assert result["patch_a"]["verification_status"] == "mismatch"
        assert result["patch_b"]["loaded"] is True

    def test_load_session_handles_missing_run_id_in_patch_reference(self, state):
        """Verified session with missing run_id should be mismatch."""

        payload = {"session_id": "session_ok", "patch_a": {}, "patch_b": {"run_id": "run_b"}}
        with (
            patch(
                "build_tools.syllable_walk_web.services.walker_session_store.load_session",
                return_value=SimpleNamespace(
                    status="verified",
                    reason="verified",
                    session_id="session_ok",
                    payload=payload,
                    ipc_input_hash="a" * 64,
                    ipc_output_hash="b" * 64,
                ),
            ),
            patch(
                "build_tools.syllable_walk_web.api.walker.handle_load_corpus",
                return_value={
                    "status": "loading",
                    "source": "annotated_json",
                    "syllable_count": 12,
                },
            ),
        ):
            result = handle_load_session({"session_id": "session_ok"}, state)

        assert result["patch_a"]["verification_status"] == "mismatch"
        assert result["patch_b"]["loaded"] is True

    def test_load_session_handles_patch_load_error(self, state):
        """Patch load errors should be surfaced for the affected patch."""

        payload = {
            "session_id": "session_ok",
            "patch_a": {"run_id": "run_a"},
            "patch_b": {"run_id": "run_b"},
        }
        with (
            patch(
                "build_tools.syllable_walk_web.services.walker_session_store.load_session",
                return_value=SimpleNamespace(
                    status="verified",
                    reason="verified",
                    session_id="session_ok",
                    payload=payload,
                    ipc_input_hash="a" * 64,
                    ipc_output_hash="b" * 64,
                ),
            ),
            patch(
                "build_tools.syllable_walk_web.api.walker.handle_load_corpus",
                side_effect=[
                    {"error": "Run not found"},
                    {"status": "loading", "source": "annotated_json", "syllable_count": 12},
                ],
            ),
        ):
            result = handle_load_session({"session_id": "session_ok"}, state)

        assert result["patch_a"]["loaded"] is False
        assert result["patch_a"]["verification_status"] == "error"
        assert result["patch_b"]["loaded"] is True

    def test_load_session_verified_starts_patch_loads(self, state):
        """Verified session should trigger patch-level corpus load requests."""

        payload = {
            "session_id": "session_ok",
            "patch_a": {"run_id": "run_a"},
            "patch_b": {"run_id": "run_b"},
        }
        with (
            patch(
                "build_tools.syllable_walk_web.services.walker_session_store.load_session",
                return_value=SimpleNamespace(
                    status="verified",
                    reason="verified",
                    session_id="session_ok",
                    payload=payload,
                    ipc_input_hash="a" * 64,
                    ipc_output_hash="b" * 64,
                ),
            ),
            patch(
                "build_tools.syllable_walk_web.api.walker.handle_load_corpus",
                side_effect=[
                    {"status": "loading", "source": "annotated_json", "syllable_count": 10},
                    {"status": "loading", "source": "annotated_json", "syllable_count": 12},
                ],
            ) as mock_load_corpus,
        ):
            result = handle_load_session({"session_id": "session_ok"}, state)

        assert "error" not in result
        assert result["status"] == "verified"
        assert result["patch_a"]["loaded"] is True
        assert result["patch_b"]["loaded"] is True
        assert mock_load_corpus.call_count == 2

    def test_load_session_restores_verified_patch_artifacts(self, state, tmp_path):
        """Verified run-state sidecars should restore patch outputs on load."""

        from build_tools.syllable_walk_web.services.walker_run_state_store import save_run_state

        run_id = "run_a"
        run_dir = tmp_path / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        persist_state = ServerState()
        persist_state.patch_a.run_id = run_id
        persist_state.patch_a.corpus_dir = run_dir
        persist_state.patch_a.manifest_ipc_output_hash = "a" * 64
        persist_state.patch_a.reach_cache_ipc_output_hash = "b" * 64

        expected_walks = [{"formatted": "ka·ri", "syllables": ["ka", "ri"], "steps": []}]
        expected_candidates = [{"name": "Kari", "syllables": ["ka", "ri"], "features": {}}]
        expected_selections = [{"name": "Kari", "syllables": ["ka", "ri"], "score": 1.0}]

        assert (
            save_run_state(
                state=persist_state,
                patch="a",
                artifact_kind="walks",
                artifact_payload={"walks": expected_walks, "params": {"count": 1, "steps": 1}},
            ).status
            == "saved"
        )
        assert (
            save_run_state(
                state=persist_state,
                patch="a",
                artifact_kind="candidates",
                artifact_payload={"candidates": expected_candidates, "params": {"count": 1}},
            ).status
            == "saved"
        )
        assert (
            save_run_state(
                state=persist_state,
                patch="a",
                artifact_kind="selections",
                artifact_payload={"selected_names": expected_selections, "params": {"count": 1}},
            ).status
            == "saved"
        )

        payload = {"session_id": "session_ok", "patch_a": {"run_id": run_id}, "patch_b": None}

        def _mock_load_corpus(body, server_state):
            patch_state = server_state.patch_a if body.get("patch") == "a" else server_state.patch_b
            patch_state.run_id = body.get("run_id")
            patch_state.corpus_dir = run_dir
            patch_state.manifest_ipc_output_hash = "a" * 64
            return {"status": "loading", "source": "annotated_json", "syllable_count": 12}

        with (
            patch(
                "build_tools.syllable_walk_web.services.walker_session_store.load_session",
                return_value=SimpleNamespace(
                    status="verified",
                    reason="verified",
                    session_id="session_ok",
                    payload=payload,
                    ipc_input_hash="c" * 64,
                    ipc_output_hash="d" * 64,
                ),
            ),
            patch(
                "build_tools.syllable_walk_web.api.walker.handle_load_corpus",
                side_effect=_mock_load_corpus,
            ),
        ):
            result = handle_load_session({"session_id": "session_ok"}, state)

        assert result["patch_a"]["loaded"] is True
        assert result["patch_a"]["restored"] is True
        assert result["patch_a"]["verification_status"] == "verified"
        assert result["patch_a"]["verification_reason"] == "run-state-restored"
        assert set(result["patch_a"]["restored_kinds"]) >= {"walks", "candidates", "selections"}
        assert state.patch_a.walks == expected_walks
        assert state.patch_a.candidates == expected_candidates
        assert state.patch_a.selected_names == expected_selections
        assert result["patch_b"]["loaded"] is False
        assert result["patch_b"]["verification_status"] == "missing"

    def test_load_session_marks_patch_mismatch_when_run_state_verification_fails(
        self, state, tmp_path
    ):
        """Load should not trust sidecars when run-state verification drifts."""

        from build_tools.syllable_walk_web.services.walker_run_state_store import save_run_state

        run_id = "run_a"
        run_dir = tmp_path / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        persist_state = ServerState()
        persist_state.patch_a.run_id = run_id
        persist_state.patch_a.corpus_dir = run_dir
        persist_state.patch_a.manifest_ipc_output_hash = "a" * 64

        assert (
            save_run_state(
                state=persist_state,
                patch="a",
                artifact_kind="walks",
                artifact_payload={"walks": [{"formatted": "ka·ri"}], "params": {"count": 1}},
            ).status
            == "saved"
        )

        payload = {"session_id": "session_ok", "patch_a": {"run_id": run_id}, "patch_b": None}

        def _mock_load_corpus(body, server_state):
            patch_state = server_state.patch_a if body.get("patch") == "a" else server_state.patch_b
            patch_state.run_id = body.get("run_id")
            patch_state.corpus_dir = run_dir
            # Deliberate hash drift against saved run-state.
            patch_state.manifest_ipc_output_hash = "f" * 64
            return {"status": "loading", "source": "annotated_json", "syllable_count": 12}

        with (
            patch(
                "build_tools.syllable_walk_web.services.walker_session_store.load_session",
                return_value=SimpleNamespace(
                    status="verified",
                    reason="verified",
                    session_id="session_ok",
                    payload=payload,
                    ipc_input_hash="c" * 64,
                    ipc_output_hash="d" * 64,
                ),
            ),
            patch(
                "build_tools.syllable_walk_web.api.walker.handle_load_corpus",
                side_effect=_mock_load_corpus,
            ),
        ):
            result = handle_load_session({"session_id": "session_ok"}, state)

        assert result["patch_a"]["loaded"] is True
        assert result["patch_a"]["restored"] is False
        assert result["patch_a"]["verification_status"] == "mismatch"
        assert result["patch_a"]["verification_reason"] == "run-state-manifest-hash-mismatch"
        assert result["patch_a"]["restored_kinds"] == []
        assert state.patch_a.walks == []
        assert state.patch_a.candidates is None
        assert state.patch_a.selected_names == []

    def test_load_session_returns_lock_conflict_when_held_elsewhere(self, state):
        """Load should return lock conflict when another holder owns session lock."""

        with patch(
            "build_tools.syllable_walk_web.services.walker_session_lock.acquire_session_lock",
            return_value={
                "status": "locked",
                "reason": "session lock held by another holder",
                "lock": {
                    "session_id": "session_ok",
                    "holder_id": "holder_other",
                    "acquired_at_utc": "2026-02-23T12:00:00Z",
                    "refreshed_at_utc": "2026-02-23T12:00:10Z",
                    "expires_at_utc": "2026-02-23T12:00:45Z",
                },
            },
        ):
            result = handle_load_session(
                {
                    "session_id": "session_ok",
                    "lock_holder_id": "holder_self",
                },
                state,
            )

        assert "error" in result
        assert result["lock_status"] == "locked"
        assert result["active_session_id"] == "session_ok"
        assert result["lock"]["holder_id"] == "holder_other"

    def test_session_lock_heartbeat_and_release_handlers(self, state):
        """Heartbeat and release endpoints should round-trip lock ownership."""

        from build_tools.syllable_walk_web.services.walker_session_lock import acquire_session_lock

        acquired = acquire_session_lock(
            state=state,
            session_id="session_ok",
            holder_id="holder_self",
        )
        assert acquired["status"] == "acquired"

        heartbeat = handle_session_lock_heartbeat(
            {"session_id": "session_ok", "lock_holder_id": "holder_self"},
            state,
        )
        assert "error" not in heartbeat
        assert heartbeat["status"] == "held"

        released = handle_session_lock_release(
            {"session_id": "session_ok", "lock_holder_id": "holder_self"},
            state,
        )
        assert "error" not in released
        assert released["status"] == "released"

    def test_load_session_rejects_blank_lock_holder_id(self, state):
        """Load should reject blank lock holder IDs before lock acquisition."""

        result = handle_load_session(
            {
                "session_id": "session_ok",
                "lock_holder_id": "   ",
            },
            state,
        )
        assert "error" in result
        assert "must not be blank" in result["error"]

    def test_load_session_returns_error_for_unexpected_lock_status(self, state):
        """Load should fail fast if lock service returns an unknown status."""

        with patch(
            "build_tools.syllable_walk_web.services.walker_session_lock.acquire_session_lock",
            return_value={"status": "error", "reason": "lock-store-unavailable"},
        ):
            result = handle_load_session(
                {"session_id": "session_ok", "lock_holder_id": "holder_self"},
                state,
            )
        assert "error" in result
        assert "Failed to acquire session lock" in result["error"]

    def test_load_session_releases_lock_when_payload_cannot_be_loaded(self, state):
        """Load should release provisional lock when verified payload is absent."""

        with (
            patch(
                "build_tools.syllable_walk_web.services.walker_session_lock.acquire_session_lock",
                return_value={
                    "status": "acquired",
                    "reason": "session lock acquired",
                    "lock": {"session_id": "session_ok", "holder_id": "holder_self"},
                },
            ),
            patch(
                "build_tools.syllable_walk_web.services.walker_session_store.load_session",
                return_value=SimpleNamespace(
                    status="missing",
                    reason="session-missing",
                    session_id="session_ok",
                    payload=None,
                    ipc_input_hash=None,
                    ipc_output_hash=None,
                ),
            ),
            patch(
                "build_tools.syllable_walk_web.services.walker_session_lock.release_session_lock"
            ) as mock_release,
        ):
            result = handle_load_session(
                {"session_id": "session_ok", "lock_holder_id": "holder_self"},
                state,
            )

        assert "error" not in result
        assert result["status"] == "missing"
        mock_release.assert_called_once()

    def test_session_lock_handlers_cover_error_and_missing_statuses(self, state):
        """Heartbeat/release handlers should map locked/error/missing service states."""

        with patch(
            "build_tools.syllable_walk_web.services.walker_session_lock.heartbeat_session_lock",
            return_value={
                "status": "locked",
                "reason": "session lock held by another holder",
                "lock": {"holder_id": "holder_other"},
            },
        ):
            heartbeat_locked = handle_session_lock_heartbeat(
                {"session_id": "session_ok", "lock_holder_id": "holder_self"},
                state,
            )
        assert "error" in heartbeat_locked
        assert heartbeat_locked["lock_status"] == "locked"

        with patch(
            "build_tools.syllable_walk_web.services.walker_session_lock.heartbeat_session_lock",
            return_value={"status": "missing", "reason": "session lock not found"},
        ):
            heartbeat_missing = handle_session_lock_heartbeat(
                {"session_id": "session_ok", "lock_holder_id": "holder_self"},
                state,
            )
        assert "error" not in heartbeat_missing
        assert heartbeat_missing["status"] == "missing"

        with patch(
            "build_tools.syllable_walk_web.services.walker_session_lock.release_session_lock",
            return_value={
                "status": "locked",
                "reason": "session lock held by another holder",
                "lock": {"holder_id": "holder_other"},
            },
        ):
            release_locked = handle_session_lock_release(
                {"session_id": "session_ok", "lock_holder_id": "holder_self"},
                state,
            )
        assert "error" in release_locked
        assert release_locked["lock_status"] == "locked"

    def test_session_lock_handlers_reject_invalid_holder_payloads(self, state):
        """Heartbeat/release should reject missing or invalid lock holder IDs."""

        heartbeat_bad = handle_session_lock_heartbeat(
            {"session_id": "session_ok", "lock_holder_id": 123},
            state,
        )
        assert "error" in heartbeat_bad
        assert "must be a string" in heartbeat_bad["error"]

        release_bad = handle_session_lock_release(
            {"session_id": "session_ok", "lock_holder_id": 123},
            state,
        )
        assert "error" in release_bad
        assert "must be a string" in release_bad["error"]


# ============================================================
# session restore helpers
# ============================================================


def _build_restore_patch_state(tmp_path: Path):
    """Create one patch state with minimal verified run context for restore tests."""

    state = ServerState()
    run_dir = tmp_path / "run_a"
    run_dir.mkdir(parents=True, exist_ok=True)
    patch = state.patch_a
    patch.run_id = "run_a"
    patch.corpus_dir = run_dir
    patch.manifest_ipc_output_hash = "a" * 64
    return patch, run_dir


class TestSessionRestoreHelpers:
    """Tests for private restore helpers used by session-load flow."""

    def test_clear_active_session_context_resets_state(self, state):
        """Clear helper should null active session tracking fields."""

        state.active_session_id = "session_1"
        state.active_session_lock_holder_id = "holder_1"
        _clear_active_session_context(state)
        assert state.active_session_id is None
        assert state.active_session_lock_holder_id is None

    def test_read_json_object_handles_parse_and_shape_errors(self, tmp_path):
        """JSON helper should return None on parse failures and non-object payloads."""

        bad_path = tmp_path / "bad.json"
        bad_path.write_text("{bad", encoding="utf-8")
        assert _read_json_object(bad_path) is None

        list_path = tmp_path / "list.json"
        list_path.write_text("[]", encoding="utf-8")
        assert _read_json_object(list_path) is None

        good_path = tmp_path / "good.json"
        good_path.write_text('{"ok": true}', encoding="utf-8")
        assert _read_json_object(good_path) == {"ok": True}

    def test_restore_patch_artifacts_skips_when_run_context_missing(self, tmp_path):
        """Restore should skip when patch state has no run id or no run dir."""

        patch_state, _ = _build_restore_patch_state(tmp_path)
        patch_state.run_id = None
        skipped_no_run = _restore_patch_artifacts_from_run_state(
            patch_key="a",
            patch=patch_state,
        )
        assert skipped_no_run["status"] == "skipped"
        assert skipped_no_run["reason"] == "run-state-context-missing:run-id"

        patch_state.run_id = "run_a"
        patch_state.corpus_dir = None
        skipped_no_dir = _restore_patch_artifacts_from_run_state(
            patch_key="a",
            patch=patch_state,
        )
        assert skipped_no_dir["status"] == "skipped"
        assert skipped_no_dir["reason"] == "run-state-context-missing:run-dir"

    def test_restore_patch_artifacts_propagates_unverified_run_state(self, tmp_path):
        """Restore should return upstream run-state verification result when not verified."""

        patch_state, _ = _build_restore_patch_state(tmp_path)
        with patch(
            "build_tools.syllable_walk_web.services.walker_run_state_store.load_run_state",
            return_value=SimpleNamespace(
                status="missing",
                reason="run-state-missing",
                payload=None,
                run_state_ipc_input_hash=None,
                run_state_ipc_output_hash=None,
            ),
        ):
            result = _restore_patch_artifacts_from_run_state(patch_key="a", patch=patch_state)

        assert result["status"] == "missing"
        assert result["reason"] == "run-state-missing"

    def test_restore_patch_artifacts_rejects_missing_sidecars_block(self, tmp_path):
        """Restore should reject run-state payloads without sidecar map."""

        patch_state, _ = _build_restore_patch_state(tmp_path)
        with patch(
            "build_tools.syllable_walk_web.services.walker_run_state_store.load_run_state",
            return_value=SimpleNamespace(
                status="verified",
                reason="verified",
                payload={},
                run_state_ipc_input_hash="b" * 64,
                run_state_ipc_output_hash="c" * 64,
            ),
        ):
            result = _restore_patch_artifacts_from_run_state(patch_key="a", patch=patch_state)

        assert result["status"] == "mismatch"
        assert result["reason"] == "run-state-sidecars-missing"

    @pytest.mark.parametrize(
        ("slot", "sidecar_ref", "sidecar_content", "expected_status", "expected_reason"),
        [
            (
                "patch_a_walks",
                "invalid",
                None,
                "mismatch",
                "run-state-sidecar-ref-invalid:patch_a_walks",
            ),
            (
                "patch_a_walks",
                {},
                None,
                "mismatch",
                "run-state-sidecar-relative-path-invalid:patch_a_walks",
            ),
            (
                "patch_a_walks",
                {"relative_path": "../outside.json"},
                None,
                "mismatch",
                "run-state-sidecar-path-outside-run-dir:patch_a_walks",
            ),
            (
                "patch_a_walks",
                {"relative_path": "ipc/missing_walks.json"},
                None,
                "missing",
                "run-state-sidecar-missing:patch_a_walks",
            ),
            (
                "patch_a_walks",
                {"relative_path": "ipc/walks_bad_parse.json"},
                "{bad",
                "error",
                "run-state-sidecar-parse-error:patch_a_walks",
            ),
            (
                "patch_a_walks",
                {"relative_path": "ipc/walks_bad_payload.json"},
                '{"payload": []}',
                "mismatch",
                "run-state-sidecar-payload-invalid:patch_a_walks",
            ),
            (
                "patch_a_walks",
                {"relative_path": "ipc/walks_invalid.json"},
                '{"payload": {"walks": "bad"}}',
                "mismatch",
                "run-state-sidecar-walks-invalid:patch_a_walks",
            ),
            (
                "patch_a_candidates",
                {"relative_path": "ipc/candidates_invalid.json"},
                '{"payload": {"candidates": "bad"}}',
                "mismatch",
                "run-state-sidecar-candidates-invalid:patch_a_candidates",
            ),
            (
                "patch_a_selections",
                {"relative_path": "ipc/selections_invalid.json"},
                '{"payload": {"selected_names": "bad"}}',
                "mismatch",
                "run-state-sidecar-selections-invalid:patch_a_selections",
            ),
            (
                "patch_a_package",
                {"relative_path": "ipc/package_invalid.json"},
                '{"payload": {"package": "bad"}}',
                "mismatch",
                "run-state-sidecar-package-invalid:patch_a_package",
            ),
        ],
    )
    def test_restore_patch_artifacts_validates_sidecar_shapes(
        self,
        tmp_path,
        slot,
        sidecar_ref,
        sidecar_content,
        expected_status,
        expected_reason,
    ):
        """Restore should reject malformed sidecar refs and payload blocks deterministically."""

        patch_state, run_dir = _build_restore_patch_state(tmp_path)
        if isinstance(sidecar_ref, dict) and isinstance(sidecar_ref.get("relative_path"), str):
            sidecar_path = run_dir / sidecar_ref["relative_path"]
            sidecar_path.parent.mkdir(parents=True, exist_ok=True)
            if sidecar_content is not None:
                sidecar_path.write_text(sidecar_content, encoding="utf-8")

        with patch(
            "build_tools.syllable_walk_web.services.walker_run_state_store.load_run_state",
            return_value=SimpleNamespace(
                status="verified",
                reason="verified",
                payload={"sidecars": {slot: sidecar_ref}},
                run_state_ipc_input_hash="d" * 64,
                run_state_ipc_output_hash="e" * 64,
            ),
        ):
            result = _restore_patch_artifacts_from_run_state(patch_key="a", patch=patch_state)

        assert result["status"] == expected_status
        assert result["reason"] == expected_reason

    def test_restore_patch_artifacts_accepts_valid_package_sidecar(self, tmp_path):
        """Restore should accept valid package sidecar metadata and mark package restored."""

        patch_state, run_dir = _build_restore_patch_state(tmp_path)
        sidecar_path = run_dir / "ipc" / "package.json"
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        sidecar_path.write_text(
            '{"payload": {"package": {"filename": "pkg.zip", "size_bytes": 10}}}',
            encoding="utf-8",
        )

        with patch(
            "build_tools.syllable_walk_web.services.walker_run_state_store.load_run_state",
            return_value=SimpleNamespace(
                status="verified",
                reason="verified",
                payload={"sidecars": {"patch_a_package": {"relative_path": "ipc/package.json"}}},
                run_state_ipc_input_hash="d" * 64,
                run_state_ipc_output_hash="e" * 64,
            ),
        ):
            result = _restore_patch_artifacts_from_run_state(patch_key="a", patch=patch_state)

        assert result["status"] == "verified"
        assert result["restored"] is True
        assert "package" in result["restored_kinds"]


# ============================================================
# handle_rebuild_reach_cache
# ============================================================


class TestHandleRebuildReachCache:
    """Test POST /api/walker/rebuild-reach-cache handler."""

    def test_error_when_patch_invalid(self, loaded_state):
        """Invalid patch values should return an error."""

        result = handle_rebuild_reach_cache({"patch": "x"}, loaded_state)
        assert "error" in result

    def test_rebuild_rejects_when_active_session_lock_owned_elsewhere(self, loaded_state):
        """Rebuild should fail when active session lock is held by another holder."""

        loaded_state.active_session_id = "session_locked"
        loaded_state.active_session_lock_holder_id = "holder_owner"
        with patch(
            "build_tools.syllable_walk_web.services.walker_session_lock.acquire_session_lock",
            return_value={
                "status": "locked",
                "reason": "session lock held by another holder",
                "lock": {"holder_id": "holder_owner"},
            },
        ):
            result = handle_rebuild_reach_cache(
                {"patch": "a", "lock_holder_id": "holder_other"},
                loaded_state,
            )
        assert "error" in result
        assert result["lock_status"] == "locked"

    def test_error_when_walker_not_ready(self, state):
        """Rebuild requires a loaded walker."""

        result = handle_rebuild_reach_cache({"patch": "a"}, state)
        assert "error" in result
        assert "Walker not ready" in result["error"]

    def test_error_when_run_id_mismatches_loaded_patch(self, loaded_state):
        """Explicit run_id must match current patch context when provided."""

        loaded_state.patch_a.run_id = "run_a"
        loaded_state.patch_a.corpus_dir = Path("/tmp/run_a")
        result = handle_rebuild_reach_cache({"patch": "a", "run_id": "run_b"}, loaded_state)
        assert "error" in result
        assert "run_id mismatch" in result["error"]

    def test_error_when_run_id_has_invalid_type(self, loaded_state):
        """run_id must be a non-empty string when provided."""

        result = handle_rebuild_reach_cache({"patch": "a", "run_id": 123}, loaded_state)
        assert "error" in result
        assert "run_id must be a non-empty string" in result["error"]

    def test_error_when_corpus_dir_missing(self, loaded_state):
        """A loaded walker still requires a run directory for cache writes."""

        loaded_state.patch_a.run_id = "run_a"
        loaded_state.patch_a.corpus_dir = None
        loaded_state.patch_a.walker = MagicMock()
        loaded_state.patch_a.walker_ready = True
        result = handle_rebuild_reach_cache({"patch": "a"}, loaded_state)
        assert "error" in result
        assert "Run directory missing" in result["error"]

    def test_error_when_run_id_missing(self, loaded_state):
        """A loaded walker with no run ID cannot rebuild cache deterministically."""

        loaded_state.patch_a.run_id = None
        loaded_state.patch_a.corpus_dir = Path("/tmp/run_a")
        loaded_state.patch_a.walker = MagicMock()
        loaded_state.patch_a.walker_ready = True
        result = handle_rebuild_reach_cache({"patch": "a"}, loaded_state)
        assert "error" in result
        assert "run_id missing" in result["error"]

    def test_error_when_reach_compute_fails(self, loaded_state):
        """Reach-compute exceptions should return an explicit API error."""

        loaded_state.patch_a.run_id = "run_a"
        loaded_state.patch_a.corpus_dir = Path("/tmp/run_a")
        loaded_state.patch_a.walker = MagicMock()
        loaded_state.patch_a.walker_ready = True
        with patch(
            "build_tools.syllable_walk.reach.compute_all_reaches",
            side_effect=RuntimeError("compute-failed"),
        ):
            result = handle_rebuild_reach_cache({"patch": "a"}, loaded_state)
        assert "error" in result
        assert "Failed to compute profile reaches" in result["error"]

    def test_error_when_reach_cache_write_fails(self, loaded_state):
        """Failed cache writes should return an explicit API error."""

        loaded_state.patch_a.run_id = "run_a"
        loaded_state.patch_a.corpus_dir = Path("/tmp/run_a")
        loaded_state.patch_a.walker = MagicMock()
        loaded_state.patch_a.walker_ready = True
        with (
            patch("build_tools.syllable_walk.reach.compute_all_reaches", return_value={}),
            patch(
                "build_tools.syllable_walk_web.services.profile_reaches_cache.write_cached_profile_reaches",
                return_value=False,
            ),
        ):
            result = handle_rebuild_reach_cache({"patch": "a"}, loaded_state)
        assert "error" in result
        assert "Failed to write reach cache artifact" in result["error"]

    def test_rebuild_sets_error_status_when_hashes_missing(self, loaded_state):
        """Rebuild should surface missing IPC hashes as verification error."""

        loaded_state.patch_a.run_id = "run_a"
        loaded_state.patch_a.corpus_dir = Path("/tmp/run_a")
        loaded_state.patch_a.walker = MagicMock()
        loaded_state.patch_a.walker_ready = True
        mock_reaches = {
            "clerical": ReachResult(
                profile_name="clerical",
                reach=1,
                total=1,
                threshold=0.001,
                max_flips=1,
                temperature=0.3,
                frequency_weight=1.0,
                computation_ms=1.0,
            ),
            "dialect": ReachResult(
                profile_name="dialect",
                reach=1,
                total=1,
                threshold=0.001,
                max_flips=2,
                temperature=0.7,
                frequency_weight=0.0,
                computation_ms=1.0,
            ),
            "goblin": ReachResult(
                profile_name="goblin",
                reach=1,
                total=1,
                threshold=0.001,
                max_flips=2,
                temperature=1.0,
                frequency_weight=0.5,
                computation_ms=1.0,
            ),
            "ritual": ReachResult(
                profile_name="ritual",
                reach=1,
                total=1,
                threshold=0.001,
                max_flips=3,
                temperature=2.5,
                frequency_weight=-1.0,
                computation_ms=1.0,
            ),
        }
        with (
            patch("build_tools.syllable_walk.reach.compute_all_reaches", return_value=mock_reaches),
            patch(
                "build_tools.syllable_walk_web.services.profile_reaches_cache.write_cached_profile_reaches",
                return_value=True,
            ),
            patch(
                "build_tools.syllable_walk_web.services.profile_reaches_cache.read_cached_profile_reach_hashes",
                return_value=(None, None),
            ),
        ):
            result = handle_rebuild_reach_cache({"patch": "a"}, loaded_state)
        assert result["verification_status"] == "error"
        assert result["verification_reason"] == "cache-rebuilt-hashes-missing"

    def test_success_rebuilds_reach_cache(self, loaded_state):
        """Rebuild should recompute reaches and refresh IPC hash fields."""

        loaded_state.patch_a.run_id = "run_a"
        loaded_state.patch_a.corpus_dir = Path("/tmp/run_a")
        loaded_state.patch_a.walker = MagicMock()
        loaded_state.patch_a.walker_ready = True

        mock_reaches = {
            "clerical": ReachResult(
                profile_name="clerical",
                reach=10,
                total=100,
                threshold=0.001,
                max_flips=1,
                temperature=0.3,
                frequency_weight=1.0,
                computation_ms=5.0,
            ),
            "dialect": ReachResult(
                profile_name="dialect",
                reach=20,
                total=100,
                threshold=0.001,
                max_flips=2,
                temperature=0.7,
                frequency_weight=0.0,
                computation_ms=6.0,
            ),
            "goblin": ReachResult(
                profile_name="goblin",
                reach=30,
                total=100,
                threshold=0.001,
                max_flips=2,
                temperature=1.0,
                frequency_weight=0.5,
                computation_ms=7.0,
            ),
            "ritual": ReachResult(
                profile_name="ritual",
                reach=40,
                total=100,
                threshold=0.001,
                max_flips=3,
                temperature=2.5,
                frequency_weight=-1.0,
                computation_ms=8.0,
            ),
        }

        with (
            patch(
                "build_tools.syllable_walk.reach.compute_all_reaches",
                return_value=mock_reaches,
            ),
            patch(
                "build_tools.syllable_walk_web.services.profile_reaches_cache.write_cached_profile_reaches",
                return_value=True,
            ),
            patch(
                "build_tools.syllable_walk_web.services.profile_reaches_cache.read_cached_profile_reach_hashes",
                return_value=("a" * 64, "b" * 64),
            ),
        ):
            result = handle_rebuild_reach_cache({"patch": "a"}, loaded_state)

        assert "error" not in result
        assert result["status"] == "rebuilt"
        assert result["verification_status"] == "verified"
        assert loaded_state.patch_a.reach_cache_ipc_input_hash == "a" * 64
        assert loaded_state.patch_a.reach_cache_ipc_output_hash == "b" * 64
        assert loaded_state.patch_a.profile_reaches == mock_reaches


# ============================================================
# handle_combine
# ============================================================


class TestHandleCombine:
    """Test POST /api/walker/combine handler."""

    def test_error_when_patch_invalid(self, loaded_state):
        """Test returns error when patch is not 'a' or 'b'."""
        result = handle_combine({"patch": "c"}, loaded_state)
        assert "error" in result

    def test_error_when_no_corpus(self, state):
        """Test returns error when no corpus loaded."""
        result = handle_combine({"patch": "a"}, state)
        assert "error" in result

    def test_combine_ignores_lock_when_active_holder_not_set(self, state):
        """Combine should proceed to normal validation when active holder is unset."""

        state.active_session_id = "session_locked"
        state.active_session_lock_holder_id = None
        result = handle_combine({"patch": "a"}, state)
        assert "error" in result
        assert "No corpus loaded" in result["error"]

    def test_combine_rejects_when_active_session_lock_owned_elsewhere(self, loaded_state):
        """Combine should fail when active session lock is held by another holder."""

        loaded_state.active_session_id = "session_locked"
        loaded_state.active_session_lock_holder_id = "holder_owner"
        with patch(
            "build_tools.syllable_walk_web.services.walker_session_lock.acquire_session_lock",
            return_value={
                "status": "locked",
                "reason": "session lock held by another holder",
                "lock": {"holder_id": "holder_owner"},
            },
        ):
            result = handle_combine(
                {"patch": "a", "lock_holder_id": "holder_other"},
                loaded_state,
            )

        assert "error" in result
        assert result["lock_status"] == "locked"

    def test_combine_returns_lock_error_for_invalid_or_failed_holder_validation(self, loaded_state):
        """Combine should surface lock-holder validation and service error states."""

        loaded_state.active_session_id = "session_locked"
        loaded_state.active_session_lock_holder_id = "holder_owner"

        missing_holder = handle_combine({"patch": "a"}, loaded_state)
        assert "error" in missing_holder
        assert missing_holder["lock_status"] == "locked"

        invalid_holder = handle_combine({"patch": "a", "lock_holder_id": 123}, loaded_state)
        assert "error" in invalid_holder
        assert invalid_holder["lock_status"] == "error"

        with patch(
            "build_tools.syllable_walk_web.services.walker_session_lock.acquire_session_lock",
            return_value={"status": "error", "reason": "store-failed"},
        ):
            failed_lock = handle_combine(
                {"patch": "a", "lock_holder_id": "holder_owner"},
                loaded_state,
            )
        assert "error" in failed_lock
        assert failed_lock["lock_status"] == "error"

    def test_success_generates_candidates(self, loaded_state):
        """Test successful candidate generation."""
        mock_candidates = [
            {"name": "Kari", "syllables": ["ka", "ri"], "features": {}},
            {"name": "Kari", "syllables": ["ka", "ri"], "features": {}},
            {"name": "Rika", "syllables": ["ri", "ka"], "features": {}},
        ]
        with (
            patch(
                "build_tools.name_combiner.combiner.combine_syllables",
                return_value=mock_candidates,
            ),
            patch(
                "build_tools.syllable_walk_web.services.walker_run_state_store.save_run_state",
            ) as mock_save,
        ):
            result = handle_combine({"patch": "a", "count": 3, "syllables": 2}, loaded_state)

        assert "error" not in result
        assert result["generated"] == 3
        assert result["unique"] == 2
        assert result["duplicates"] == 1
        mock_save.assert_called_once()
        assert mock_save.call_args.kwargs["patch"] == "a"
        assert mock_save.call_args.kwargs["artifact_kind"] == "candidates"

    def test_combiner_failure_returns_error(self, loaded_state):
        """Test combiner exception returns error."""
        with patch(
            "build_tools.name_combiner.combiner.combine_syllables",
            side_effect=RuntimeError("Combiner error"),
        ):
            result = handle_combine({"patch": "a"}, loaded_state)

        assert "error" in result

    def test_flat_profile_uses_existing_combiner(self, loaded_state):
        """Test profile=flat (or absent) uses the flat combiner path."""
        mock_candidates = [
            {"name": "Kari", "syllables": ["ka", "ri"], "features": {}},
        ]
        with patch(
            "build_tools.name_combiner.combiner.combine_syllables",
            return_value=mock_candidates,
        ) as mock_combine:
            result = handle_combine(
                {"patch": "a", "count": 1, "syllables": 2, "profile": "flat"}, loaded_state
            )

        assert "error" not in result
        assert result["generated"] == 1
        mock_combine.assert_called_once()

    def test_named_profile_uses_walk_generation(self, loaded_state):
        """Test profile=dialect uses walk-based generation via _combine_via_walks."""
        mock_walks = [
            {"syllables": ["ka", "ri"], "formatted": "ka·ri"},
            {"syllables": ["ri", "ka"], "formatted": "ri·ka"},
        ]
        with (
            patch(
                "build_tools.syllable_walk_web.services.walk_generator.generate_walks",
                return_value=mock_walks,
            ) as mock_gen,
            patch(
                "build_tools.name_combiner.aggregator.aggregate_features",
                return_value={},
            ),
        ):
            result = handle_combine(
                {"patch": "a", "count": 2, "syllables": 2, "profile": "dialect"}, loaded_state
            )

        assert "error" not in result
        assert result["generated"] == 2
        # Verify generate_walks was called with profile="dialect" and steps=1
        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args
        assert call_kwargs[1].get("profile") == "dialect" or (len(call_kwargs[0]) > 1 and False)

    def test_named_profile_with_one_syllable_still_uses_one_step(self, loaded_state):
        """Syllable count 1 should clamp to one walk step."""
        with (
            patch(
                "build_tools.syllable_walk_web.services.walk_generator.generate_walks",
                return_value=[{"syllables": ["ka"], "formatted": "ka"}],
            ) as mock_gen,
            patch(
                "build_tools.name_combiner.aggregator.aggregate_features",
                return_value={},
            ),
        ):
            result = handle_combine(
                {"patch": "a", "count": 1, "syllables": 1, "profile": "dialect"},
                loaded_state,
            )

        assert "error" not in result
        _, kwargs = mock_gen.call_args
        assert kwargs["steps"] == 1

    def test_custom_profile_sends_explicit_params(self, loaded_state):
        """Test profile=custom passes max_flips, temperature, frequency_weight."""
        mock_walks = [
            {"syllables": ["ka", "ri"], "formatted": "ka·ri"},
        ]
        with (
            patch(
                "build_tools.syllable_walk_web.services.walk_generator.generate_walks",
                return_value=mock_walks,
            ) as mock_gen,
            patch(
                "build_tools.name_combiner.aggregator.aggregate_features",
                return_value={},
            ),
        ):
            result = handle_combine(
                {
                    "patch": "a",
                    "count": 1,
                    "syllables": 2,
                    "profile": "custom",
                    "max_flips": 3,
                    "temperature": 1.5,
                    "frequency_weight": -0.5,
                },
                loaded_state,
            )

        assert "error" not in result
        assert result["generated"] == 1
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["max_flips"] == 3
        assert call_kwargs["temperature"] == 1.5
        assert call_kwargs["frequency_weight"] == -0.5

    def test_profile_requires_walker_ready(self, state, sample_annotated_data):
        """Test walk profile returns error when walker not ready."""
        # Corpus loaded but walker not ready
        state.patch_a.annotated_data = sample_annotated_data
        state.patch_a.walker_ready = False
        state.patch_a.walker = None

        result = handle_combine(
            {"patch": "a", "count": 1, "syllables": 2, "profile": "goblin"}, state
        )

        assert "error" in result
        assert "Walker not ready" in result["error"]


# ============================================================
# handle_reach_syllables
# ============================================================


class TestHandleReachSyllables:
    """Test POST /api/walker/reach-syllables handler."""

    def test_error_when_patch_invalid(self, loaded_state):
        """Test returns error when patch is not 'a' or 'b'."""
        result = handle_reach_syllables({"patch": "c", "profile": "dialect"}, loaded_state)
        assert "error" in result

    def test_error_when_no_corpus(self, state):
        """Test returns error when no corpus loaded (no reach data)."""
        result = handle_reach_syllables({"patch": "a", "profile": "dialect"}, state)
        assert "error" in result

    def test_error_when_invalid_profile(self, loaded_state):
        """Test returns error for unknown profile name."""
        # Set up mock reach data with known profiles
        mock_reach = MagicMock()
        mock_reach.reachable_indices = ((0, 5), (1, 3))
        loaded_state.patch_a.profile_reaches = {"dialect": mock_reach}

        result = handle_reach_syllables({"patch": "a", "profile": "nonexistent"}, loaded_state)
        assert "error" in result
        assert "Unknown profile" in result["error"]

    def test_success_returns_syllables(self, loaded_state):
        """Test successful response with syllable list sorted by reachability."""
        import numpy as np

        # Mock the walker with syllable data
        loaded_state.patch_a.walker.syllables = ["ka", "ri"]
        loaded_state.patch_a.walker.frequencies = np.array([100, 80])

        mock_reach = MagicMock()
        # (index, reachability_count) pairs sorted by count descending
        mock_reach.reachable_indices = ((0, 5), (1, 3))
        mock_reach.reach = 2
        mock_reach.total = 2
        mock_reach.unique_reachable = 2
        loaded_state.patch_a.profile_reaches = {"dialect": mock_reach}

        result = handle_reach_syllables({"patch": "a", "profile": "dialect"}, loaded_state)

        assert "error" not in result
        assert result["profile"] == "dialect"
        assert result["reach"] == 2
        assert result["total"] == 2
        assert result["unique_reachable"] == 2
        assert len(result["syllables"]) == 2
        # Sorted by reachability count descending (ka=5, ri=3)
        assert result["syllables"][0]["syllable"] == "ka"
        assert result["syllables"][1]["syllable"] == "ri"
        assert result["syllables"][0]["frequency"] == 100
        assert result["syllables"][1]["frequency"] == 80
        assert result["syllables"][0]["reachability"] == 5
        assert result["syllables"][1]["reachability"] == 3

    def test_slices_to_reach_count(self, loaded_state):
        """Test response is limited to top `reach` syllables, not full union."""
        import numpy as np

        loaded_state.patch_a.walker.syllables = ["ka", "ri", "bo"]
        loaded_state.patch_a.walker.frequencies = np.array([100, 80, 60])

        mock_reach = MagicMock()
        # 3 union-reachable syllables, but reach (mean per-node) is only 2
        mock_reach.reachable_indices = ((0, 5), (1, 3), (2, 1))
        mock_reach.reach = 2
        mock_reach.total = 3
        mock_reach.unique_reachable = 3
        loaded_state.patch_a.profile_reaches = {"dialect": mock_reach}

        result = handle_reach_syllables({"patch": "a", "profile": "dialect"}, loaded_state)

        assert len(result["syllables"]) == 2  # sliced to reach, not 3
        assert result["syllables"][0]["syllable"] == "ka"
        assert result["syllables"][1]["syllable"] == "ri"

    def test_error_when_walker_not_ready(self, state, sample_annotated_data):
        """Test returns error when walker is None."""
        mock_reach = MagicMock()
        mock_reach.reachable_indices = ((0, 5),)
        state.patch_a.profile_reaches = {"dialect": mock_reach}
        state.patch_a.walker = None

        result = handle_reach_syllables({"patch": "a", "profile": "dialect"}, state)
        assert "error" in result


# ============================================================
# handle_select
# ============================================================


class TestHandleSelect:
    """Test POST /api/walker/select handler."""

    def test_error_when_patch_invalid(self, state_with_candidates):
        """Test returns error when patch is not 'a' or 'b'."""
        result = handle_select({"patch": "c"}, state_with_candidates)
        assert "error" in result

    def test_error_when_no_candidates(self, loaded_state):
        """Test returns error when no candidates generated."""
        result = handle_select({"patch": "a"}, loaded_state)
        assert "error" in result

    def test_select_rejects_when_active_session_lock_owned_elsewhere(self, state_with_candidates):
        """Select should fail when active session lock is held by another holder."""

        state_with_candidates.active_session_id = "session_locked"
        state_with_candidates.active_session_lock_holder_id = "holder_owner"
        with patch(
            "build_tools.syllable_walk_web.services.walker_session_lock.acquire_session_lock",
            return_value={
                "status": "locked",
                "reason": "session lock held by another holder",
                "lock": {"holder_id": "holder_owner"},
            },
        ):
            result = handle_select(
                {"patch": "a", "lock_holder_id": "holder_other"},
                state_with_candidates,
            )

        assert "error" in result
        assert result["lock_status"] == "locked"

    def test_success_selects_names(self, state_with_candidates):
        """Test successful name selection."""
        mock_result = {
            "name_class": "first_name",
            "mode": "hard",
            "count": 1,
            "requested": 100,
            "selected": [{"name": "Kari", "syllables": ["ka", "ri"], "score": 1.0}],
        }
        with (
            patch(
                "build_tools.name_selector.selector.select_names",
                return_value=mock_result["selected"],
            ),
            patch(
                "build_tools.name_selector.name_class.load_name_classes",
                return_value={
                    "first_name": MagicMock(description="First names", syllable_range=(2, 3))
                },
            ),
            patch(
                "build_tools.syllable_walk_web.services.walker_run_state_store.save_run_state",
            ) as mock_save,
        ):
            result = handle_select(
                {"patch": "a", "name_class": "first_name"},
                state_with_candidates,
            )

        assert "error" not in result
        assert result["count"] == 1
        assert "Kari" in result["names"]
        mock_save.assert_called_once()
        assert mock_save.call_args.kwargs["patch"] == "a"
        assert mock_save.call_args.kwargs["artifact_kind"] == "selections"

    def test_unknown_name_class_returns_error(self, state_with_candidates):
        """Test unknown name class returns error from selector_runner."""
        with patch(
            "build_tools.name_selector.name_class.load_name_classes",
            return_value={},
        ):
            result = handle_select(
                {"patch": "a", "name_class": "nonexistent"},
                state_with_candidates,
            )

        assert "error" in result

    def test_selector_exception_returns_error(self, state_with_candidates):
        """Raised selector exceptions should be converted to API errors."""
        with patch(
            "build_tools.syllable_walk_web.services.selector_runner.run_selector",
            side_effect=RuntimeError("selector blew up"),
        ):
            result = handle_select(
                {"patch": "a", "name_class": "first_name"}, state_with_candidates
            )

        assert "error" in result
        assert "Selector failed" in result["error"]


# ============================================================
# handle_export
# ============================================================


class TestHandleExport:
    """Test POST /api/walker/export handler."""

    def test_error_when_patch_invalid(self, state_with_selections):
        """Test returns error when patch is not 'a' or 'b'."""
        result = handle_export({"patch": "c"}, state_with_selections)
        assert "error" in result

    def test_error_when_no_selections(self, loaded_state):
        """Test returns error when no names selected."""
        result = handle_export({"patch": "a"}, loaded_state)
        assert "error" in result

    def test_exports_names_from_dicts(self, state_with_selections):
        """Test export extracts names from dict selections."""
        result = handle_export({"patch": "a"}, state_with_selections)
        assert "error" not in result
        assert result["count"] == 1
        assert "Kari" in result["names"]

    def test_exports_names_from_strings(self, loaded_state):
        """Test export handles plain string selections."""
        loaded_state.patch_a.selected_names = ["Kari", "Rika"]
        result = handle_export({"patch": "a"}, loaded_state)
        assert result["names"] == ["Kari", "Rika"]

    def test_export_uses_correct_patch(self, state_with_selections):
        """Test export respects patch parameter."""
        result = handle_export({"patch": "a"}, state_with_selections)
        assert result["patch"] == "a"


# ============================================================
# handle_package
# ============================================================


class TestHandlePackage:
    """Test POST /api/walker/package handler."""

    def test_delegates_to_build_package(self, state):
        """Test package handler delegates to packager service."""
        state.patch_a.run_id = "20260222_155258_nltk"
        state.patch_a.walks = [{"formatted": "ka·ri", "syllables": ["ka", "ri"], "steps": []}]
        with (
            patch(
                "build_tools.syllable_walk_web.services.packager.build_package",
                return_value=(b"PK\x03\x04content", None),
            ),
            patch(
                "build_tools.syllable_walk_web.services.walker_run_state_store.save_run_state",
            ) as mock_save,
        ):
            zip_bytes, filename, error = handle_package(
                {"name": "test-pkg", "version": "1.0"}, state
            )

        assert error is None
        assert filename == "test-pkg-1.0.zip"
        assert zip_bytes.startswith(b"PK")
        assert mock_save.call_count == 1
        assert mock_save.call_args.kwargs["patch"] == "a"
        assert mock_save.call_args.kwargs["artifact_kind"] == "package"

    def test_returns_error_from_packager(self, state):
        """Test error from packager is propagated."""
        state.patch_a.run_id = "20260222_155258_nltk"
        state.patch_a.walks = [{"formatted": "ka·ri", "syllables": ["ka", "ri"], "steps": []}]
        with (
            patch(
                "build_tools.syllable_walk_web.services.packager.build_package",
                return_value=(b"", "Nothing to package."),
            ),
            patch(
                "build_tools.syllable_walk_web.services.walker_run_state_store.save_run_state",
            ) as mock_save,
        ):
            zip_bytes, filename, error = handle_package({}, state)

        assert error == "Nothing to package."
        mock_save.assert_not_called()

    def test_package_rejects_when_active_session_lock_owned_elsewhere(self, state):
        """Package should fail when active session lock is held by another holder."""

        state.active_session_id = "session_locked"
        state.active_session_lock_holder_id = "holder_owner"
        with patch(
            "build_tools.syllable_walk_web.services.walker_session_lock.acquire_session_lock",
            return_value={
                "status": "locked",
                "reason": "session lock held by another holder",
                "lock": {"holder_id": "holder_owner"},
            },
        ):
            zip_bytes, filename, error = handle_package(
                {"lock_holder_id": "holder_other"},
                state,
            )

        assert zip_bytes == b""
        assert filename == ""
        assert isinstance(error, str)
        assert "locked by another tab/window" in error


# ============================================================
# handle_analysis
# ============================================================


class TestHandleAnalysis:
    """Test GET /api/walker/analysis/<patch> handler."""

    def test_invalid_patch(self, state):
        """Test error for invalid patch key."""
        result = handle_analysis("x", state)
        assert "error" in result

    def test_no_corpus_loaded(self, state):
        """Test error when no corpus loaded for patch."""
        result = handle_analysis("a", state)
        assert "error" in result

    def test_success_returns_analysis(self, loaded_state):
        """Test successful analysis returns metrics."""
        mock_metrics = {"total": 2, "unique": 2, "hapax": 0}
        with patch(
            "build_tools.syllable_walk_web.services.metrics.compute_analysis",
            return_value=mock_metrics,
        ):
            result = handle_analysis("a", loaded_state)

        assert "error" not in result
        assert result["patch"] == "a"
        assert result["analysis"]["total"] == 2

    def test_analysis_failure_returns_error(self, loaded_state):
        """Test analysis exception returns error."""
        with patch(
            "build_tools.syllable_walk_web.services.metrics.compute_analysis",
            side_effect=RuntimeError("Metrics error"),
        ):
            result = handle_analysis("a", loaded_state)

        assert "error" in result
