"""Tests for manifest-driven run discovery in syllable_walk_web."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from build_tools.syllable_walk_web.run_discovery import (
    RunInfo,
    _build_output_tree_lines,
    _build_stage_statuses,
    _discover_selections,
    _extract_artifact_paths,
    _format_display_name,
    _format_processing_time,
    _load_manifest,
    _manifest_has_required_keys,
    _parse_timestamp,
    discover_runs,
    get_run_by_id,
    get_selection_data,
)


def _write_manifest(run_dir: Path, payload: dict) -> None:
    """Write a manifest payload to one run directory."""
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _manifest_payload(run_id: str, extractor: str = "pyphen") -> dict:
    """Return a minimal valid v1 manifest payload for tests."""
    return {
        "manifest_version": 1,
        "run_id": run_id,
        "status": "completed",
        "created_at_utc": "2026-02-22T15:00:00Z",
        "completed_at_utc": "2026-02-22T15:00:03Z",
        "extractor": extractor,
        "language": "auto",
        "config": {
            "source_path": "/tmp/source.txt",
            "file_pattern": "*.txt",
            "min_syllable_length": 2,
            "max_syllable_length": 8,
            "run_normalize": True,
            "run_annotate": True,
        },
        "metrics": {
            "syllable_count_unique": 3,
            "files_processed": 1,
        },
        "stages": [
            {
                "name": "extract",
                "status": "completed",
                "started_at_utc": "2026-02-22T15:00:00Z",
                "ended_at_utc": "2026-02-22T15:00:01Z",
                "duration_seconds": 1.0,
            },
            {
                "name": "normalize",
                "status": "completed",
                "started_at_utc": "2026-02-22T15:00:01Z",
                "ended_at_utc": "2026-02-22T15:00:02Z",
                "duration_seconds": 1.0,
            },
            {
                "name": "annotate",
                "status": "completed",
                "started_at_utc": "2026-02-22T15:00:02Z",
                "ended_at_utc": "2026-02-22T15:00:03Z",
                "duration_seconds": 1.0,
            },
        ],
        "artifacts": [
            {"path": "data/corpus.db", "type": "sqlite", "size_bytes": 128},
            {
                "path": f"data/{extractor}_syllables_annotated.json",
                "type": "annotated_json",
                "size_bytes": 256,
            },
        ],
        "ipc": {
            "version": 1,
            "library": "pipeworks-ipc",
            "library_ref": "pipeworks-ipc-v0.1.1",
            "input_hash": "a" * 64,
            "output_hash": "b" * 64,
        },
        "errors": [],
    }


@pytest.fixture
def manifest_run(tmp_path: Path) -> Path:
    """Create one valid run directory with manifest and expected artifacts."""
    run_id = "20260222_150000_pyphen"
    run_dir = tmp_path / run_id
    payload = _manifest_payload(run_id, extractor="pyphen")
    _write_manifest(run_dir, payload)
    (run_dir / "data").mkdir(parents=True, exist_ok=True)
    (run_dir / "data" / "corpus.db").write_text("sqlite", encoding="utf-8")
    (run_dir / "data" / "pyphen_syllables_annotated.json").write_text("[]", encoding="utf-8")
    selections_dir = run_dir / "selections"
    selections_dir.mkdir()
    (selections_dir / "pyphen_first_name_2syl.json").write_text(
        '{"metadata":{},"selections":[]}', encoding="utf-8"
    )
    return run_dir


class TestRunInfo:
    """RunInfo serialization contract tests."""

    def test_to_dict_includes_manifest_fields(self, tmp_path: Path) -> None:
        """RunInfo.to_dict should include additive manifest and IPC fields."""
        run_info = RunInfo(
            path=tmp_path / "20260222_150000_pyphen",
            run_id="20260222_150000_pyphen",
            extractor_type="pyphen",
            timestamp="20260222_150000",
            display_name="run",
            corpus_db_path=None,
            annotated_json_path=None,
            syllable_count=3,
            status="completed",
            created_at_utc="2026-02-22T15:00:00Z",
            completed_at_utc="2026-02-22T15:00:03Z",
            stage_statuses={"extract": "completed"},
            ipc_input_hash="a" * 64,
            ipc_output_hash="b" * 64,
        )
        payload = run_info.to_dict()
        assert payload["run_id"] == "20260222_150000_pyphen"
        assert payload["status"] == "completed"
        assert payload["created_at_utc"] == "2026-02-22T15:00:00Z"
        assert payload["stage_statuses"]["extract"] == "completed"
        assert payload["ipc_input_hash"] == "a" * 64


def test_load_manifest_handles_missing_and_invalid(tmp_path: Path) -> None:
    """Manifest loader should return None for missing/corrupt files."""
    missing = tmp_path / "20260222_000000_pyphen"
    missing.mkdir()
    assert _load_manifest(missing) is None

    invalid = tmp_path / "20260222_000001_pyphen"
    invalid.mkdir()
    (invalid / "manifest.json").write_text("{oops", encoding="utf-8")
    assert _load_manifest(invalid) is None


def test_manifest_required_key_validation() -> None:
    """Manifest schema validator should reject partial payloads."""
    valid = _manifest_payload("20260222_160000_pyphen")
    assert _manifest_has_required_keys(valid) is True

    invalid = dict(valid)
    invalid.pop("metrics")
    assert _manifest_has_required_keys(invalid) is False


def test_manifest_required_key_validation_rejects_wrong_types() -> None:
    """Validator should reject manifests when typed sections have wrong shape."""
    valid = _manifest_payload("20260222_160100_pyphen")

    bad_config = dict(valid)
    bad_config["config"] = []
    assert _manifest_has_required_keys(bad_config) is False

    bad_metrics = dict(valid)
    bad_metrics["metrics"] = []
    assert _manifest_has_required_keys(bad_metrics) is False

    bad_stages = dict(valid)
    bad_stages["stages"] = {}
    assert _manifest_has_required_keys(bad_stages) is False

    bad_artifacts = dict(valid)
    bad_artifacts["artifacts"] = {}
    assert _manifest_has_required_keys(bad_artifacts) is False


def test_parse_timestamp_and_duration_helpers() -> None:
    """Timestamp and duration helpers should parse/format expected values."""
    assert _parse_timestamp("20260222_160000") is not None
    assert _parse_timestamp("bad") is None

    from_interval = _format_processing_time(_manifest_payload("20260222_160000_pyphen"))
    assert from_interval == "3.00s"

    no_interval = _manifest_payload("20260222_160001_pyphen")
    no_interval["completed_at_utc"] = None
    no_interval["stages"] = [
        {"name": "extract", "status": "completed", "duration_seconds": 1.5},
        {"name": "normalize", "status": "completed", "duration_seconds": 2.5},
    ]
    assert _format_processing_time(no_interval) == "4.00s"


def test_format_processing_time_returns_none_for_invalid_timestamps() -> None:
    """Duration helper should gracefully return None when timestamps are malformed."""
    payload = _manifest_payload("20260222_160002_pyphen")
    payload["created_at_utc"] = "bad-timestamp"
    payload["completed_at_utc"] = "also-bad"
    payload["stages"] = [{"name": "extract", "status": "completed", "duration_seconds": "n/a"}]
    assert _format_processing_time(payload) is None


def test_extract_artifact_paths_ignores_non_dict_and_non_string_entries() -> None:
    """Artifact path extraction should ignore invalid entries and keep canonical paths."""
    payload = {
        "artifacts": [
            "not-a-dict",
            {"path": 123},
            {"path": "data/corpus.db"},
            {"path": "data/pyphen_syllables_annotated.json"},
        ]
    }
    corpus_rel, annotated_rel = _extract_artifact_paths(payload)
    assert corpus_rel == "data/corpus.db"
    assert annotated_rel == "data/pyphen_syllables_annotated.json"


def test_build_stage_statuses_ignores_non_dict_stages() -> None:
    """Stage status map should skip malformed list entries."""
    payload = {
        "stages": [
            "bad-entry",
            {"name": "extract", "status": "completed"},
        ]
    }
    statuses = _build_stage_statuses(payload)
    assert statuses == {"extract": "completed"}


def test_build_output_tree_lines_annotates_known_artifacts() -> None:
    """Tree builder should include deterministic notes for key artifacts."""
    lines = _build_output_tree_lines(
        "20260222_170000_pyphen",
        [
            {"path": "data/corpus.db"},
            {"path": "data/pyphen_syllables_annotated.json"},
            {"path": "meta/source.txt"},
        ],
        1784,
    )
    assert lines[0] == "20260222_170000_pyphen/"
    assert any("data/corpus.db  1,784 syllables" in line for line in lines)
    assert any("annotated data" in line for line in lines)
    assert any("meta/source.txt" in line for line in lines)


def test_build_output_tree_lines_ignores_non_dict_artifacts() -> None:
    """Tree builder should skip malformed artifact entries without failing."""
    artifacts: list[object] = [
        "bad-entry",
        {"path": "data/corpus.db"},
    ]
    lines = _build_output_tree_lines(
        "20260222_170001_pyphen",
        cast(list[dict[str, Any]], artifacts),
        10,
    )
    assert lines[0] == "20260222_170001_pyphen/"
    assert any("data/corpus.db" in line for line in lines)


def test_format_display_name_with_and_without_selections() -> None:
    """Display name format should include selection suffix only when present."""
    assert (
        _format_display_name("20260222_170000_pyphen", "pyphen", 1000, 0)
        == "20260222_170000_pyphen (1,000 syllables)"
    )
    assert (
        _format_display_name("20260222_170000_pyphen", "pyphen", 1000, 2)
        == "20260222_170000_pyphen (1,000 syllables, 2 selections)"
    )


class TestDiscoverRuns:
    """Manifest-driven run discovery behavior tests."""

    def test_discover_runs_requires_manifest(self, tmp_path: Path) -> None:
        """Runs without manifest should be skipped entirely."""
        (tmp_path / "20260222_150000_pyphen").mkdir()
        runs = discover_runs(tmp_path)
        assert runs == []

    def test_discover_runs_skips_corrupt_and_partial_manifest(self, tmp_path: Path) -> None:
        """Corrupt or incomplete manifests should be ignored."""
        bad_json = tmp_path / "20260222_150001_pyphen"
        bad_json.mkdir()
        (bad_json / "manifest.json").write_text("{bad", encoding="utf-8")

        partial = tmp_path / "20260222_150002_pyphen"
        partial.mkdir()
        _write_manifest(partial, {"run_id": partial.name})

        runs = discover_runs(tmp_path)
        assert runs == []

    def test_discover_runs_reads_manifest_fields(self, manifest_run: Path, tmp_path: Path) -> None:
        """Discovery should populate history fields directly from manifest."""
        runs = discover_runs(tmp_path)
        assert len(runs) == 1
        run = runs[0]
        payload = run.to_dict()
        assert payload["run_id"] == manifest_run.name
        assert payload["status"] == "completed"
        assert payload["source_path"] == "/tmp/source.txt"
        assert payload["files_processed"] == 1
        assert payload["processing_time"] == "3.00s"
        assert payload["syllable_count"] == 3
        assert payload["stage_statuses"]["extract"] == "completed"
        assert payload["ipc_input_hash"] == "a" * 64
        assert payload["ipc_output_hash"] == "b" * 64
        assert payload["selection_count"] == 1
        assert payload["corpus_db_path"] is not None
        assert payload["annotated_json_path"] is not None

    def test_discover_runs_skips_run_id_mismatch(self, tmp_path: Path) -> None:
        """Manifest run_id must match directory name for strict contract mode."""
        run_dir = tmp_path / "20260222_150010_pyphen"
        payload = _manifest_payload("20260222_150011_pyphen")
        _write_manifest(run_dir, payload)
        runs = discover_runs(tmp_path)
        assert runs == []

    def test_discover_runs_sorts_by_timestamp_desc_then_name(self, tmp_path: Path) -> None:
        """Runs should keep deterministic newest-first ordering."""
        for run_id in (
            "20260222_090000_nltk",
            "20260222_090000_pyphen",
            "20260222_100000_pyphen",
        ):
            run_dir = tmp_path / run_id
            extractor = run_id.split("_", 2)[2]
            payload = _manifest_payload(run_id, extractor=extractor)
            _write_manifest(run_dir, payload)
            (run_dir / "data").mkdir(parents=True, exist_ok=True)

        names = [run.path.name for run in discover_runs(tmp_path)]
        assert names == [
            "20260222_100000_pyphen",
            "20260222_090000_nltk",
            "20260222_090000_pyphen",
        ]

    def test_discover_runs_default_base_path_branch(self, tmp_path: Path, monkeypatch) -> None:
        """discover_runs() should return empty when default _working/output is absent."""
        monkeypatch.chdir(tmp_path)
        assert discover_runs() == []

    def test_discover_runs_skips_non_dirs_and_non_matching_folder_names(
        self, tmp_path: Path
    ) -> None:
        """Discovery should ignore filesystem files and non-run folder names."""
        (tmp_path / "note.txt").write_text("x", encoding="utf-8")
        (tmp_path / "not_a_run").mkdir()

        run_id = "20260222_170010_pyphen"
        run_dir = tmp_path / run_id
        _write_manifest(run_dir, _manifest_payload(run_id))
        (run_dir / "data").mkdir(parents=True, exist_ok=True)

        runs = discover_runs(tmp_path)
        assert len(runs) == 1
        assert runs[0].path.name == run_id

    def test_discover_runs_skips_empty_extractor(self, tmp_path: Path) -> None:
        """Run should be skipped when manifest extractor is empty."""
        run_id = "20260222_170020_pyphen"
        run_dir = tmp_path / run_id
        payload = _manifest_payload(run_id)
        payload["extractor"] = ""
        _write_manifest(run_dir, payload)
        assert discover_runs(tmp_path) == []

    def test_discover_runs_normalises_optional_manifest_fields(self, tmp_path: Path) -> None:
        """Discovery should normalize optional fields with invalid types to safe defaults."""
        run_id = "20260222_170030_pyphen"
        run_dir = tmp_path / run_id
        payload = _manifest_payload(run_id)
        payload["metrics"]["syllable_count_unique"] = "3"
        payload["metrics"]["files_processed"] = "1"
        payload["config"]["source_path"] = {"not": "a-string"}
        payload["ipc"]["input_hash"] = 123
        payload["ipc"]["output_hash"] = ["abc"]
        _write_manifest(run_dir, payload)
        (run_dir / "data").mkdir(parents=True, exist_ok=True)

        runs = discover_runs(tmp_path)
        assert len(runs) == 1
        run = runs[0]
        assert run.syllable_count == 0
        assert run.source_path is None
        assert run.files_processed is None
        assert run.ipc_input_hash is None
        assert run.ipc_output_hash is None


class TestSelectionAndLookup:
    """Selection loading and run lookup behavior."""

    def test_get_selection_data_reads_json(self, manifest_run: Path) -> None:
        """Selection loader should deserialize valid JSON payload."""
        data = get_selection_data(manifest_run / "selections" / "pyphen_first_name_2syl.json")
        assert isinstance(data, dict)
        assert "metadata" in data
        assert "selections" in data

    def test_get_selection_data_raises_for_missing(self, tmp_path: Path) -> None:
        """Selection loader should raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            get_selection_data(tmp_path / "missing.json")

    def test_get_run_by_id_returns_run(self, manifest_run: Path, tmp_path: Path) -> None:
        """Run lookup should return the matching discovered run."""
        run = get_run_by_id(manifest_run.name, tmp_path)
        assert run is not None
        assert run.run_id == manifest_run.name
        assert run.path.name == manifest_run.name

    def test_get_run_by_id_returns_none_when_missing(
        self, manifest_run: Path, tmp_path: Path
    ) -> None:
        """Run lookup should return None when no run matches."""
        assert get_run_by_id("20260222_999999_pyphen", tmp_path) is None

    def test_discover_selections_skips_meta_json(self, tmp_path: Path) -> None:
        """Selection discovery should skip *_meta.json helper files."""
        run_dir = tmp_path / "20260222_180000_pyphen"
        selections_dir = run_dir / "selections"
        selections_dir.mkdir(parents=True, exist_ok=True)
        (selections_dir / "pyphen_first_name_2syl_meta.json").write_text("{}", encoding="utf-8")
        (selections_dir / "pyphen_first_name_2syl.json").write_text(
            '{"metadata":{},"selections":[]}', encoding="utf-8"
        )

        selections = _discover_selections(run_dir, "pyphen")
        assert list(selections.keys()) == ["first_name"]
