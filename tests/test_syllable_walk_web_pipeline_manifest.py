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
