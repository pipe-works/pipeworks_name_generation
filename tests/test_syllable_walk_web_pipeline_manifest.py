"""Tests for pipeline manifest helpers used by syllable_walk_web.

The manifest module is responsible for deterministic run metadata snapshots,
including stage telemetry and artifact/metric discovery from run directories.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from build_tools.syllable_walk_web.services import pipeline_manifest

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def test_create_manifest_includes_required_structure() -> None:
    """create_manifest should return schema v1 with stable required keys."""

    manifest = pipeline_manifest.create_manifest(
        run_id="20260222_123000_pyphen",
        extractor="pyphen",
        language="en_GB",
        source_path="/tmp/source.txt",
        file_pattern="*.txt",
        min_syllable_length=2,
        max_syllable_length=8,
        run_normalize=True,
        run_annotate=True,
        created_at_utc="2026-02-22T12:30:00Z",
    )

    assert manifest["manifest_version"] == 1
    assert manifest["run_id"] == "20260222_123000_pyphen"
    assert manifest["status"] == "running"
    assert manifest["extractor"] == "pyphen"
    assert manifest["config"]["source_path"] == "/tmp/source.txt"
    assert manifest["metrics"]["syllable_count_unique"] is None
    assert manifest["stages"] == []
    assert manifest["artifacts"] == []
    assert "ipc" in manifest
    assert manifest["ipc"]["library"] == "pipeworks-ipc"
    assert manifest["ipc"]["library_ref"].startswith("pipeworks-ipc-v")
    assert _SHA256_RE.match(manifest["ipc"]["input_hash"])
    assert manifest["ipc"]["output_hash"] is None
    assert manifest["ipc"]["output_payload"] is None
    assert manifest["errors"] == []


def test_upsert_stage_computes_duration_for_completed_stage() -> None:
    """upsert_stage should compute duration when both timestamps are present."""

    manifest = pipeline_manifest.create_manifest(
        run_id="20260222_123000_pyphen",
        extractor="pyphen",
        language="en_GB",
        source_path="/tmp/source.txt",
        file_pattern="*.txt",
        min_syllable_length=2,
        max_syllable_length=8,
        run_normalize=True,
        run_annotate=True,
        created_at_utc="2026-02-22T12:30:00Z",
    )
    pipeline_manifest.upsert_stage(
        manifest,
        name="extract",
        status="completed",
        started_at_utc="2026-02-22T12:30:00Z",
        ended_at_utc="2026-02-22T12:30:04Z",
    )

    assert len(manifest["stages"]) == 1
    stage = manifest["stages"][0]
    assert stage["name"] == "extract"
    assert stage["status"] == "completed"
    assert stage["duration_seconds"] == 4.0


def test_refresh_metrics_and_artifacts_prefers_db_and_counts_input_files(tmp_path: Path) -> None:
    """refresh_metrics_and_artifacts should fill deterministic artifacts and metrics."""

    run_dir = tmp_path / "20260222_123000_pyphen"
    data_dir = run_dir / "data"
    data_dir.mkdir(parents=True)

    # Create sqlite output as canonical syllable count source.
    db_path = data_dir / "corpus.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE syllables (syllable TEXT PRIMARY KEY)")
    conn.executemany("INSERT INTO syllables (syllable) VALUES (?)", [("ka",), ("ri",), ("na",)])
    conn.commit()
    conn.close()

    # Additional artifacts for classification checks.
    (data_dir / "pyphen_syllables_annotated.json").write_text("[]", encoding="utf-8")
    (run_dir / "pyphen_syllables_unique.txt").write_text("ka\nri\nna\n", encoding="utf-8")
    meta_dir = run_dir / "meta"
    meta_dir.mkdir()
    (meta_dir / "source.txt").write_text("Input File: /tmp/source.txt\n", encoding="utf-8")

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "a.txt").write_text("a", encoding="utf-8")
    (source_dir / "b.txt").write_text("b", encoding="utf-8")
    (source_dir / "ignore.md").write_text("x", encoding="utf-8")

    manifest = pipeline_manifest.create_manifest(
        run_id=run_dir.name,
        extractor="pyphen",
        language="en_GB",
        source_path=str(source_dir),
        file_pattern="*.txt",
        min_syllable_length=2,
        max_syllable_length=8,
        run_normalize=True,
        run_annotate=True,
        created_at_utc="2026-02-22T12:30:00Z",
    )
    pipeline_manifest.refresh_metrics_and_artifacts(
        manifest,
        run_directory=run_dir,
        source_path=str(source_dir),
        file_pattern="*.txt",
    )

    assert manifest["metrics"]["syllable_count_unique"] == 3
    assert manifest["metrics"]["files_processed"] == 2

    artifact_paths = [item["path"] for item in manifest["artifacts"]]
    assert artifact_paths == sorted(artifact_paths)
    assert any(
        item["path"] == "data/corpus.db" and item["type"] == "sqlite"
        for item in manifest["artifacts"]
    )
    assert any(
        item["path"] == "pyphen_syllables_unique.txt" and item["type"] == "syllables_unique"
        for item in manifest["artifacts"]
    )
    assert _SHA256_RE.match(manifest["ipc"]["input_hash"])
    assert _SHA256_RE.match(manifest["ipc"]["output_hash"])
    assert manifest["ipc"]["output_payload"]["metrics"]["syllable_count_unique"] == 3
    assert manifest["ipc"]["output_payload"]["metrics"]["files_processed"] == 2


def test_refresh_metrics_and_artifacts_keeps_deterministic_output_hash(tmp_path: Path) -> None:
    """Refreshing with unchanged files should keep the same output hash."""

    run_dir = tmp_path / "20260222_123000_nltk"
    data_dir = run_dir / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "nltk_syllables_annotated.json").write_text(
        '[{"syllable":"ka"},{"syllable":"ri"}]', encoding="utf-8"
    )
    (run_dir / "nltk_syllables_unique.txt").write_text("ka\nri\n", encoding="utf-8")

    manifest = pipeline_manifest.create_manifest(
        run_id=run_dir.name,
        extractor="nltk",
        language="auto",
        source_path=str(tmp_path / "source.txt"),
        file_pattern="*.txt",
        min_syllable_length=2,
        max_syllable_length=8,
        run_normalize=True,
        run_annotate=True,
        created_at_utc="2026-02-22T12:30:00Z",
    )
    (tmp_path / "source.txt").write_text("src", encoding="utf-8")

    pipeline_manifest.refresh_metrics_and_artifacts(
        manifest,
        run_directory=run_dir,
        source_path=str(tmp_path / "source.txt"),
        file_pattern="*.txt",
    )
    first_hash = manifest["ipc"]["output_hash"]

    pipeline_manifest.refresh_metrics_and_artifacts(
        manifest,
        run_directory=run_dir,
        source_path=str(tmp_path / "source.txt"),
        file_pattern="*.txt",
    )
    second_hash = manifest["ipc"]["output_hash"]

    assert first_hash == second_hash
    assert _SHA256_RE.match(first_hash)


def test_refresh_ipc_changes_input_hash_when_relevant_input_changes(tmp_path: Path) -> None:
    """Input hash should change when canonical configuration fields change."""

    run_dir = tmp_path / "20260222_123001_nltk"
    data_dir = run_dir / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "nltk_syllables_annotated.json").write_text("[]", encoding="utf-8")

    manifest = pipeline_manifest.create_manifest(
        run_id=run_dir.name,
        extractor="nltk",
        language="auto",
        source_path=str(tmp_path / "source-a.txt"),
        file_pattern="*.txt",
        min_syllable_length=2,
        max_syllable_length=8,
        run_normalize=True,
        run_annotate=True,
        created_at_utc="2026-02-22T12:30:00Z",
    )
    baseline = manifest["ipc"]["input_hash"]

    manifest["config"]["max_syllable_length"] = 9
    pipeline_manifest.refresh_ipc(manifest)
    updated = manifest["ipc"]["input_hash"]

    assert baseline != updated
    assert _SHA256_RE.match(updated)


def test_verify_manifest_ipc_returns_verified_for_consistent_manifest() -> None:
    """verify_manifest_ipc should report verified when hashes match payloads."""

    manifest = pipeline_manifest.create_manifest(
        run_id="20260222_123001_nltk",
        extractor="nltk",
        language="auto",
        source_path="/tmp/source.txt",
        file_pattern="*.txt",
        min_syllable_length=2,
        max_syllable_length=8,
        run_normalize=True,
        run_annotate=True,
        created_at_utc="2026-02-22T12:30:00Z",
    )
    pipeline_manifest.refresh_ipc(manifest)

    result = pipeline_manifest.verify_manifest_ipc(manifest)
    assert result.status == "verified"
    assert result.reason == "hashes-match"
    assert isinstance(result.input_hash, str) and _SHA256_RE.match(result.input_hash)
    assert isinstance(result.output_hash, str) and _SHA256_RE.match(result.output_hash)


def test_verify_manifest_ipc_returns_missing_when_ipc_block_absent() -> None:
    """verify_manifest_ipc should mark manifests without ipc block as missing."""

    manifest = {"manifest_version": 1, "run_id": "20260222_123001_nltk"}
    result = pipeline_manifest.verify_manifest_ipc(manifest)
    assert result.status == "missing"
    assert result.reason == "missing-ipc-block"


def test_verify_manifest_ipc_returns_missing_when_both_hashes_absent() -> None:
    """Missing input/output hashes should return a specific missing reason."""

    result = pipeline_manifest.verify_manifest_ipc({"ipc": {}})
    assert result.status == "missing"
    assert result.reason == "missing-input-output-hash"


def test_verify_manifest_ipc_returns_missing_when_input_hash_absent() -> None:
    """Missing input hash should preserve output hash and return missing reason."""

    manifest = {"ipc": {"output_hash": "b" * 64}}
    result = pipeline_manifest.verify_manifest_ipc(manifest)
    assert result.status == "missing"
    assert result.reason == "missing-input-hash"
    assert result.input_hash is None
    assert result.output_hash == "b" * 64


def test_verify_manifest_ipc_returns_missing_when_output_hash_absent() -> None:
    """Missing output hash should preserve input hash and return missing reason."""

    manifest = {"ipc": {"input_hash": "a" * 64}}
    result = pipeline_manifest.verify_manifest_ipc(manifest)
    assert result.status == "missing"
    assert result.reason == "missing-output-hash"
    assert result.input_hash == "a" * 64
    assert result.output_hash is None


def test_verify_manifest_ipc_returns_mismatch_when_fields_drift_without_refresh() -> None:
    """verify_manifest_ipc should detect config drift when hashes are stale."""

    manifest = pipeline_manifest.create_manifest(
        run_id="20260222_123002_pyphen",
        extractor="pyphen",
        language="en_GB",
        source_path="/tmp/source.txt",
        file_pattern="*.txt",
        min_syllable_length=2,
        max_syllable_length=8,
        run_normalize=True,
        run_annotate=True,
        created_at_utc="2026-02-22T12:30:00Z",
    )
    pipeline_manifest.refresh_ipc(manifest)
    manifest["config"]["max_syllable_length"] = 9

    result = pipeline_manifest.verify_manifest_ipc(manifest)
    assert result.status == "mismatch"
    assert result.reason in {"input-mismatch", "input-output-mismatch"}


def test_verify_manifest_ipc_returns_output_mismatch_when_only_output_hash_drifts() -> None:
    """Output-only drift should map to output-mismatch."""

    manifest = pipeline_manifest.create_manifest(
        run_id="20260222_123002_pyphen",
        extractor="pyphen",
        language="en_GB",
        source_path="/tmp/source.txt",
        file_pattern="*.txt",
        min_syllable_length=2,
        max_syllable_length=8,
        run_normalize=True,
        run_annotate=True,
        created_at_utc="2026-02-22T12:30:00Z",
    )
    pipeline_manifest.refresh_ipc(manifest)
    assert isinstance(manifest["ipc"]["output_hash"], str)
    manifest["ipc"]["output_hash"] = "f" * 64

    result = pipeline_manifest.verify_manifest_ipc(manifest)
    assert result.status == "mismatch"
    assert result.reason == "output-mismatch"


def test_verify_manifest_ipc_file_returns_missing_when_manifest_file_absent(
    tmp_path: Path,
) -> None:
    """verify_manifest_ipc_file should return missing when no manifest exists."""

    run_dir = tmp_path / "20260222_123003_nltk"
    run_dir.mkdir(parents=True)
    result = pipeline_manifest.verify_manifest_ipc_file(run_dir)
    assert result.status == "missing"
    assert result.reason == "manifest-missing"


def test_verify_manifest_ipc_file_returns_parse_error_on_invalid_json(tmp_path: Path) -> None:
    """verify_manifest_ipc_file should return parse error for malformed JSON."""

    run_dir = tmp_path / "20260222_123004_nltk"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text("{bad-json", encoding="utf-8")

    result = pipeline_manifest.verify_manifest_ipc_file(run_dir)
    assert result.status == "error"
    assert result.reason == "manifest-parse-error"


def test_verify_manifest_ipc_file_returns_error_for_non_object_payload(tmp_path: Path) -> None:
    """verify_manifest_ipc_file should reject non-object JSON payloads."""

    run_dir = tmp_path / "20260222_123005_nltk"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text("[]", encoding="utf-8")

    result = pipeline_manifest.verify_manifest_ipc_file(run_dir)
    assert result.status == "error"
    assert result.reason == "manifest-not-object"


def test_write_manifest_persists_json_with_trailing_newline(tmp_path: Path) -> None:
    """write_manifest should atomically persist a valid JSON document."""

    run_dir = tmp_path / "20260222_123000_nltk"
    manifest = pipeline_manifest.create_manifest(
        run_id=run_dir.name,
        extractor="nltk",
        language="auto",
        source_path=str(tmp_path / "source.txt"),
        file_pattern="*.txt",
        min_syllable_length=2,
        max_syllable_length=8,
        run_normalize=False,
        run_annotate=False,
        created_at_utc="2026-02-22T12:30:00Z",
    )
    pipeline_manifest.set_terminal_status(
        manifest,
        status="completed",
        completed_at_utc="2026-02-22T12:30:01Z",
    )

    path = pipeline_manifest.write_manifest(run_dir, manifest)
    raw = path.read_text(encoding="utf-8")
    loaded = json.loads(raw)

    assert path == run_dir / "manifest.json"
    assert raw.endswith("\n")
    assert loaded["run_id"] == run_dir.name
    assert loaded["status"] == "completed"


def test_resolve_pipeworks_ipc_version_returns_unknown_when_package_missing(monkeypatch) -> None:
    """Version resolution should gracefully fall back when metadata is unavailable."""

    def _raise_package_not_found(_: str) -> str:
        raise pipeline_manifest.PackageNotFoundError

    monkeypatch.setattr(pipeline_manifest, "version", _raise_package_not_found)
    assert pipeline_manifest._resolve_pipeworks_ipc_version() == "unknown"


def test_detect_syllable_count_falls_back_to_json_when_db_query_fails(tmp_path: Path) -> None:
    """DB query failures should not abort count detection if JSON output exists."""

    run_dir = tmp_path / "20260222_123500_pyphen"
    data_dir = run_dir / "data"
    data_dir.mkdir(parents=True)
    # Create an invalid sqlite file so sqlite3 raises before query completes.
    (data_dir / "corpus.db").write_text("not-a-sqlite-db", encoding="utf-8")
    (data_dir / "pyphen_syllables_annotated.json").write_text(
        '[{"syllable":"ka"},{"syllable":"ri"},{"syllable":"na"}]',
        encoding="utf-8",
    )

    assert pipeline_manifest._detect_syllable_count(run_dir) == 3


def test_detect_syllable_count_ignores_invalid_json_payload(tmp_path: Path) -> None:
    """Invalid JSON in annotated output should be ignored and return None when no fallback exists."""

    run_dir = tmp_path / "20260222_123600_pyphen"
    data_dir = run_dir / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "pyphen_syllables_annotated.json").write_text("{invalid", encoding="utf-8")

    assert pipeline_manifest._detect_syllable_count(run_dir) is None


def test_detect_files_processed_returns_none_when_source_is_missing() -> None:
    """File-count detection should return None when no source path is configured."""

    assert pipeline_manifest._detect_files_processed(None, "*.txt") is None


def test_artifact_type_defaults_to_file_for_unknown_paths() -> None:
    """Unknown artifact paths should use the generic file type."""

    assert pipeline_manifest._artifact_type("data/custom_payload.bin") == "file"
