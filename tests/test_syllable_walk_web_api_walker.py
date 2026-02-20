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
        assert loaded_state.patch_a.selected_names == []


# ============================================================
# handle_walk
# ============================================================


class TestHandleWalk:
    """Test POST /api/walker/walk handler."""

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

    def test_loaded_state(self, loaded_state):
        """Test stats reflect loaded corpus."""
        result = handle_stats(loaded_state)
        assert result["patch_a"]["corpus"] == "20260220_120000_pyphen"
        assert result["patch_a"]["walker_ready"] is True
        assert result["patch_a"]["syllable_count"] == 2


# ============================================================
# handle_combine
# ============================================================


class TestHandleCombine:
    """Test POST /api/walker/combine handler."""

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


# ============================================================
# handle_select
# ============================================================


class TestHandleSelect:
    """Test POST /api/walker/select handler."""

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


# ============================================================
# handle_export
# ============================================================


class TestHandleExport:
    """Test POST /api/walker/export handler."""

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
