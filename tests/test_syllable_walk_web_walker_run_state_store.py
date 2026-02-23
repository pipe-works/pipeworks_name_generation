"""Tests for walker run-state IPC store service."""

from __future__ import annotations

import json
from pathlib import Path

from build_tools.syllable_walk_web.services import walker_run_state_store
from build_tools.syllable_walk_web.state import ServerState


def _configured_state_for_patch_a(tmp_path: Path) -> tuple[ServerState, Path]:
    """Build server state with a fully configured Patch A run context."""

    run_dir = tmp_path / "20260222_155258_nltk"
    run_dir.mkdir(parents=True, exist_ok=True)

    state = ServerState()
    state.patch_a.run_id = run_dir.name
    state.patch_a.corpus_dir = run_dir
    state.patch_a.manifest_ipc_output_hash = "a" * 64
    state.patch_a.reach_cache_ipc_output_hash = "b" * 64
    return state, run_dir


def test_save_run_state_writes_sidecar_and_run_state(tmp_path: Path) -> None:
    """Saving one artifact should write sidecar + run-state payloads."""

    state, run_dir = _configured_state_for_patch_a(tmp_path)
    result = walker_run_state_store.save_run_state(
        state=state,
        patch="a",
        artifact_kind="walks",
        artifact_payload={
            "walks": [{"formatted": "ka·ri", "syllables": ["ka", "ri"], "steps": []}],
            "params": {"count": 1, "steps": 1},
        },
    )

    assert result.status == "saved"
    assert result.sidecar_path is not None and result.sidecar_path.exists()
    assert result.run_state_path is not None and result.run_state_path.exists()

    verification = walker_run_state_store.verify_run_state(
        run_dir=run_dir,
        run_id=run_dir.name,
        manifest_ipc_output_hash="a" * 64,
    )
    assert verification.status == "verified"

    loaded = walker_run_state_store.load_run_state(
        run_dir=run_dir,
        run_id=run_dir.name,
        manifest_ipc_output_hash="a" * 64,
    )
    assert loaded.status == "verified"
    assert loaded.payload is not None
    assert loaded.payload["run_id"] == run_dir.name
    assert loaded.payload["sidecars"]["patch_a_walks"] is not None
    assert loaded.payload["sidecars"]["patch_b_walks"] is None


def test_save_run_state_skips_when_patch_run_context_missing() -> None:
    """Save should be a no-op when patch run metadata is not loaded."""

    state = ServerState()
    result = walker_run_state_store.save_run_state(
        state=state,
        patch="a",
        artifact_kind="walks",
        artifact_payload={"walks": []},
    )
    assert result.status == "skipped"
    assert result.reason == "patch-run-id-missing"


def test_verify_run_state_reports_missing_when_payload_absent(tmp_path: Path) -> None:
    """Verification should report missing when run-state file does not exist."""

    run_dir = tmp_path / "20260222_155258_nltk"
    run_dir.mkdir(parents=True, exist_ok=True)
    verification = walker_run_state_store.verify_run_state(run_dir=run_dir, run_id=run_dir.name)
    assert verification.status == "missing"
    assert verification.reason == "run-state-missing"


def test_verify_run_state_detects_manifest_hash_mismatch(tmp_path: Path) -> None:
    """Verification should detect drift between expected and stored manifest hash."""

    state, run_dir = _configured_state_for_patch_a(tmp_path)
    save_result = walker_run_state_store.save_run_state(
        state=state,
        patch="a",
        artifact_kind="walks",
        artifact_payload={"walks": [{"formatted": "ka·ri"}]},
    )
    assert save_result.status == "saved"

    verification = walker_run_state_store.verify_run_state(
        run_dir=run_dir,
        run_id=run_dir.name,
        manifest_ipc_output_hash="f" * 64,
    )
    assert verification.status == "mismatch"
    assert verification.reason == "run-state-manifest-hash-mismatch"


def test_verify_run_state_detects_tampered_sidecar_payload(tmp_path: Path) -> None:
    """Tampering with sidecar IPC hashes should fail verification."""

    state, run_dir = _configured_state_for_patch_a(tmp_path)
    save_result = walker_run_state_store.save_run_state(
        state=state,
        patch="a",
        artifact_kind="walks",
        artifact_payload={"walks": [{"formatted": "ka·ri"}]},
    )
    assert save_result.status == "saved"
    assert save_result.sidecar_path is not None

    payload = json.loads(save_result.sidecar_path.read_text(encoding="utf-8"))
    payload["ipc"]["output_hash"] = "f" * 64
    save_result.sidecar_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    verification = walker_run_state_store.verify_run_state(
        run_dir=run_dir,
        run_id=run_dir.name,
        manifest_ipc_output_hash="a" * 64,
    )
    assert verification.status == "mismatch"
    assert "sidecar-output-hash-mismatch" in verification.reason


def test_save_run_state_preserves_existing_slots_for_same_run(tmp_path: Path) -> None:
    """Second artifact save should preserve first sidecar slot entries."""

    state, run_dir = _configured_state_for_patch_a(tmp_path)
    first = walker_run_state_store.save_run_state(
        state=state,
        patch="a",
        artifact_kind="walks",
        artifact_payload={"walks": [{"formatted": "ka·ri"}]},
    )
    assert first.status == "saved"

    second = walker_run_state_store.save_run_state(
        state=state,
        patch="a",
        artifact_kind="candidates",
        artifact_payload={"candidates": [{"name": "Kari"}]},
    )
    assert second.status == "saved"

    loaded = walker_run_state_store.load_run_state(
        run_dir=run_dir,
        run_id=run_dir.name,
        manifest_ipc_output_hash="a" * 64,
    )
    assert loaded.status == "verified"
    assert loaded.payload is not None
    sidecars = loaded.payload["sidecars"]
    assert sidecars["patch_a_walks"] is not None
    assert sidecars["patch_a_candidates"] is not None
    assert sidecars["patch_a_selections"] is None


def test_save_run_state_rejects_non_object_artifact_payload(tmp_path: Path) -> None:
    """Artifact payload must be JSON object for schema compatibility."""

    state, _run_dir = _configured_state_for_patch_a(tmp_path)
    result = walker_run_state_store.save_run_state(
        state=state,
        patch="a",
        artifact_kind="walks",
        artifact_payload=[],  # type: ignore[arg-type]
    )
    assert result.status == "error"
    assert result.reason == "artifact-payload-not-object"
