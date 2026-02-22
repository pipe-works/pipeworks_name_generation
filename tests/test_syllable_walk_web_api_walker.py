"""Tests for the walker API handlers.

This module tests all eight walker API handlers:
- handle_load_corpus: corpus loading and walker init
- handle_walk: walk generation
- handle_stats: dual-patch state reporting
- handle_combine: candidate generation
- handle_select: name selection
- handle_export: name export
- handle_package: ZIP archive building
- handle_analysis: corpus metrics
"""

from unittest.mock import MagicMock, patch

import pytest

from build_tools.syllable_walk_web.api.walker import (
    handle_analysis,
    handle_combine,
    handle_export,
    handle_load_corpus,
    handle_package,
    handle_reach_syllables,
    handle_select,
    handle_stats,
    handle_walk,
)
from build_tools.syllable_walk_web.state import ServerState

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

        with (
            patch(
                "build_tools.syllable_walk_web.run_discovery.get_run_by_id",
                return_value=mock_run,
            ),
            patch(
                "build_tools.syllable_walk.db.load_syllables",
                return_value=(sample_annotated_data, "from test"),
            ),
            patch("build_tools.syllable_walk.walker.SyllableWalker"),
        ):
            result = handle_load_corpus({"patch": "a", "run_id": "test_run"}, state)

        assert "error" not in result
        assert result["status"] == "loading"
        assert result["syllable_count"] == 2
        assert state.patch_a.syllable_count == 2

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

    def test_success_generates_walks(self, loaded_state):
        """Test successful walk generation."""
        mock_walks = [
            {"formatted": "ka·ri", "syllables": ["ka", "ri"], "steps": []},
        ]
        with patch(
            "build_tools.syllable_walk_web.services.walk_generator.generate_walks",
            return_value=mock_walks,
        ):
            result = handle_walk({"patch": "a", "count": 1}, loaded_state)

        assert "error" not in result
        assert result["patch"] == "a"
        assert len(result["walks"]) == 1
        assert loaded_state.patch_a.walks == mock_walks

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

    def test_loaded_state(self, loaded_state):
        """Test stats reflect loaded corpus."""
        result = handle_stats(loaded_state)
        assert result["patch_a"]["corpus"] == "20260220_120000_pyphen"
        assert result["patch_a"]["walker_ready"] is True
        assert result["patch_a"]["syllable_count"] == 2
        assert result["patch_a"]["loader_status"] == "ready"
        assert result["patch_a"]["loading_error"] is None

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

    def test_success_generates_candidates(self, loaded_state):
        """Test successful candidate generation."""
        mock_candidates = [
            {"name": "Kari", "syllables": ["ka", "ri"], "features": {}},
            {"name": "Kari", "syllables": ["ka", "ri"], "features": {}},
            {"name": "Rika", "syllables": ["ri", "ka"], "features": {}},
        ]
        with patch(
            "build_tools.name_combiner.combiner.combine_syllables",
            return_value=mock_candidates,
        ):
            result = handle_combine({"patch": "a", "count": 3, "syllables": 2}, loaded_state)

        assert "error" not in result
        assert result["generated"] == 3
        assert result["unique"] == 2
        assert result["duplicates"] == 1

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
        ):
            result = handle_select(
                {"patch": "a", "name_class": "first_name"},
                state_with_candidates,
            )

        assert "error" not in result
        assert result["count"] == 1
        assert "Kari" in result["names"]

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
        with patch(
            "build_tools.syllable_walk_web.services.packager.build_package",
            return_value=(b"PK\x03\x04content", None),
        ):
            zip_bytes, filename, error = handle_package(
                {"name": "test-pkg", "version": "1.0"}, state
            )

        assert error is None
        assert filename == "test-pkg-1.0.zip"
        assert zip_bytes.startswith(b"PK")

    def test_returns_error_from_packager(self, state):
        """Test error from packager is propagated."""
        with patch(
            "build_tools.syllable_walk_web.services.packager.build_package",
            return_value=(b"", "Nothing to package."),
        ):
            zip_bytes, filename, error = handle_package({}, state)

        assert error == "Nothing to package."


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
