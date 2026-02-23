"""Tests for walker run-state IPC store service."""

from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import patch

import pytest

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


def _save_valid_walk_state(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, str]]:
    """Create one valid saved run-state + sidecar and return key paths/refs."""

    state, run_dir = _configured_state_for_patch_a(tmp_path)
    result = walker_run_state_store.save_run_state(
        state=state,
        patch="a",
        artifact_kind="walks",
        artifact_payload={"walks": [{"formatted": "ka·ri"}]},
    )
    assert result.status == "saved"
    assert result.run_state_path is not None
    assert result.sidecar_path is not None

    run_state_payload = json.loads(result.run_state_path.read_text(encoding="utf-8"))
    sidecar_ref = run_state_payload["sidecars"]["patch_a_walks"]
    assert isinstance(sidecar_ref, dict)
    return run_dir, result.run_state_path, result.sidecar_path, sidecar_ref


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


def test_resolve_pipeworks_ipc_version_uses_unknown_when_metadata_missing() -> None:
    """Version lookup should degrade to explicit unknown marker."""

    with patch.object(
        walker_run_state_store,
        "version",
        side_effect=PackageNotFoundError("pipeworks-ipc"),
    ):
        assert walker_run_state_store._resolve_pipeworks_ipc_version() == "unknown"


def test_save_run_state_rejects_invalid_patch_and_artifact_kind(tmp_path: Path) -> None:
    """Invalid patch and sidecar kind should fail fast."""

    state, _run_dir = _configured_state_for_patch_a(tmp_path)
    invalid_patch = walker_run_state_store.save_run_state(
        state=state,
        patch="x",
        artifact_kind="walks",
        artifact_payload={"walks": []},
    )
    invalid_kind = walker_run_state_store.save_run_state(
        state=state,
        patch="a",
        artifact_kind="unknown",
        artifact_payload={"walks": []},
    )
    assert invalid_patch.status == "error"
    assert invalid_patch.reason == "invalid-patch:x"
    assert invalid_kind.status == "error"
    assert invalid_kind.reason == "invalid-artifact-kind:unknown"


def test_save_run_state_skips_when_run_dir_or_manifest_hash_missing(tmp_path: Path) -> None:
    """Save should skip when run dir/hash context is incomplete."""

    state = ServerState()
    state.patch_a.run_id = "20260222_155258_nltk"
    no_run_dir = walker_run_state_store.save_run_state(
        state=state,
        patch="a",
        artifact_kind="walks",
        artifact_payload={"walks": []},
    )
    state.patch_a.corpus_dir = tmp_path / "20260222_155258_nltk"
    state.patch_a.corpus_dir.mkdir(parents=True, exist_ok=True)
    no_manifest_hash = walker_run_state_store.save_run_state(
        state=state,
        patch="a",
        artifact_kind="walks",
        artifact_payload={"walks": []},
    )
    assert no_run_dir.status == "skipped"
    assert no_run_dir.reason == "patch-run-dir-missing"
    assert no_manifest_hash.status == "skipped"
    assert no_manifest_hash.reason == "manifest-output-hash-missing"


@pytest.mark.parametrize(
    "raw",
    [
        None,
        {},
        {
            "relative_path": 1,
            "artifact_kind": "walks",
            "patch": "a",
            "ipc_input_hash": "a" * 64,
            "ipc_output_hash": "b" * 64,
        },
        {
            "relative_path": "ipc/x.json",
            "artifact_kind": "bad",
            "patch": "a",
            "ipc_input_hash": "a" * 64,
            "ipc_output_hash": "b" * 64,
        },
        {
            "relative_path": "ipc/x.json",
            "artifact_kind": "walks",
            "patch": "x",
            "ipc_input_hash": "a" * 64,
            "ipc_output_hash": "b" * 64,
        },
        {
            "relative_path": "ipc/x.json",
            "artifact_kind": "walks",
            "patch": "a",
            "ipc_input_hash": "bad",
            "ipc_output_hash": "b" * 64,
        },
    ],
)
def test_coerce_sidecar_ref_rejects_invalid_shapes(raw: object) -> None:
    """Sidecar ref coercion should reject malformed values."""

    assert walker_run_state_store._coerce_sidecar_ref(raw) is None


def test_read_json_object_rejects_invalid_json_and_non_object(tmp_path: Path) -> None:
    """JSON loader helper should return None for parse/type errors."""

    bad = tmp_path / "bad.json"
    bad.write_text("{bad", encoding="utf-8")
    assert walker_run_state_store._read_json_object(bad) is None

    seq = tmp_path / "seq.json"
    seq.write_text("[]", encoding="utf-8")
    assert walker_run_state_store._read_json_object(seq) is None


def test_load_existing_sidecars_returns_empty_for_invalid_existing_payload(tmp_path: Path) -> None:
    """Existing run-state parser should tolerate malformed/foreign payloads."""

    run_dir = tmp_path / "20260222_155258_nltk"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_state_path = walker_run_state_store._run_state_path(run_dir)
    run_state_path.parent.mkdir(parents=True, exist_ok=True)

    run_state_path.write_text("{bad", encoding="utf-8")
    assert all(
        value is None
        for value in walker_run_state_store._load_existing_sidecars(run_dir, run_dir.name).values()
    )

    run_state_path.write_text(
        json.dumps({"run_id": "other", "sidecars": {}}),
        encoding="utf-8",
    )
    assert all(
        value is None
        for value in walker_run_state_store._load_existing_sidecars(run_dir, run_dir.name).values()
    )

    run_state_path.write_text(
        json.dumps({"run_id": run_dir.name, "sidecars": []}),
        encoding="utf-8",
    )
    assert all(
        value is None
        for value in walker_run_state_store._load_existing_sidecars(run_dir, run_dir.name).values()
    )


def test_verify_sidecar_payload_reports_path_and_file_errors(tmp_path: Path) -> None:
    """Sidecar verifier should fail on out-of-root and missing file paths."""

    run_dir, _run_state_path, _sidecar_path, sidecar_ref = _save_valid_walk_state(tmp_path)
    ref_outside = dict(sidecar_ref)
    ref_outside["relative_path"] = "../escape.json"
    status, reason = walker_run_state_store._verify_sidecar_payload(
        run_dir=run_dir,
        run_id=run_dir.name,
        slot="patch_a_walks",
        sidecar_ref=ref_outside,
    )
    assert status == "mismatch"
    assert reason.endswith("sidecar-path-outside-run-dir")

    ref_missing = dict(sidecar_ref)
    ref_missing["relative_path"] = "ipc/missing.v1.json"
    status, reason = walker_run_state_store._verify_sidecar_payload(
        run_dir=run_dir,
        run_id=run_dir.name,
        slot="patch_a_walks",
        sidecar_ref=ref_missing,
    )
    assert status == "missing"
    assert reason.endswith("sidecar-missing")


@pytest.mark.parametrize(
    ("mutator", "expected_reason"),
    [
        (lambda p: p.update({"schema_version": 99}), "sidecar-schema-version-mismatch"),
        (lambda p: p.update({"run_id": "other"}), "sidecar-run-id-mismatch"),
        (lambda p: p.update({"patch": "b"}), "sidecar-patch-mismatch"),
        (lambda p: p.update({"artifact_kind": "candidates"}), "sidecar-kind-mismatch"),
        (lambda p: p.update({"ipc": []}), "sidecar-ipc-block-missing"),
        (lambda p: p["ipc"].update({"input_hash": "bad"}), "sidecar-ipc-hash-invalid"),
        (lambda p: p["ipc"].update({"input_payload": []}), "sidecar-ipc-payload-invalid"),
        (lambda p: p["ipc"].update({"input_hash": "f" * 64}), "sidecar-input-hash-mismatch"),
        (lambda p: p["ipc"].update({"output_hash": "f" * 64}), "sidecar-output-hash-mismatch"),
        (lambda p: p.update({"payload": []}), "sidecar-payload-not-object"),
        (lambda p: p.update({"payload": {"tampered": True}}), "sidecar-payload-output-mismatch"),
    ],
)
def test_verify_sidecar_payload_reports_mismatch_reasons(
    tmp_path: Path,
    mutator,
    expected_reason: str,
) -> None:
    """Each sidecar payload corruption should map to a deterministic reason."""

    run_dir, _run_state_path, sidecar_path, sidecar_ref = _save_valid_walk_state(tmp_path)
    payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    mutator(payload)
    sidecar_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    status, reason = walker_run_state_store._verify_sidecar_payload(
        run_dir=run_dir,
        run_id=run_dir.name,
        slot="patch_a_walks",
        sidecar_ref=sidecar_ref,
    )
    assert status == "mismatch"
    assert reason.endswith(expected_reason)


def test_verify_sidecar_payload_reports_sidecar_ref_hash_mismatches(tmp_path: Path) -> None:
    """Sidecar ref hash drift should be detected even when sidecar file is valid."""

    run_dir, _run_state_path, _sidecar_path, sidecar_ref = _save_valid_walk_state(tmp_path)
    ref_in = dict(sidecar_ref)
    ref_in["ipc_input_hash"] = "f" * 64
    status, reason = walker_run_state_store._verify_sidecar_payload(
        run_dir=run_dir,
        run_id=run_dir.name,
        slot="patch_a_walks",
        sidecar_ref=ref_in,
    )
    assert status == "mismatch"
    assert reason.endswith("sidecar-ref-input-hash-mismatch")

    ref_out = dict(sidecar_ref)
    ref_out["ipc_output_hash"] = "f" * 64
    status, reason = walker_run_state_store._verify_sidecar_payload(
        run_dir=run_dir,
        run_id=run_dir.name,
        slot="patch_a_walks",
        sidecar_ref=ref_out,
    )
    assert status == "mismatch"
    assert reason.endswith("sidecar-ref-output-hash-mismatch")


def test_verify_run_state_reports_parse_error(tmp_path: Path) -> None:
    """Invalid JSON in run-state file should return parse error status."""

    run_dir = tmp_path / "20260222_155258_nltk"
    run_state_path = walker_run_state_store._run_state_path(run_dir)
    run_state_path.parent.mkdir(parents=True, exist_ok=True)
    run_state_path.write_text("{bad", encoding="utf-8")
    result = walker_run_state_store.verify_run_state(run_dir=run_dir, run_id=run_dir.name)
    assert result.status == "error"
    assert result.reason == "run-state-parse-error"


@pytest.mark.parametrize(
    ("mutator", "expected_reason"),
    [
        (lambda p: p.update({"schema_version": 99}), "run-state-schema-version-mismatch"),
        (lambda p: p.update({"state_kind": "other"}), "run-state-kind-mismatch"),
        (lambda p: p.update({"run_id": None}), "run-state-run-id-missing"),
        (
            lambda p: p.update({"manifest_ipc_output_hash": "bad"}),
            "run-state-manifest-hash-invalid",
        ),
        (
            lambda p: p.update({"reach_cache_ipc_output_hash": "bad"}),
            "run-state-reach-cache-hash-invalid",
        ),
        (lambda p: p.update({"sidecars": []}), "run-state-sidecars-missing"),
        (
            lambda p: p["sidecars"].pop("patch_a_walks"),
            "run-state-sidecar-slot-missing:patch_a_walks",
        ),
        (
            lambda p: p["sidecars"].update({"patch_a_walks": {"relative_path": "ipc/x.json"}}),
            "run-state-sidecar-ref-invalid:patch_a_walks",
        ),
        (lambda p: p.update({"ipc": []}), "run-state-ipc-block-missing"),
        (lambda p: p["ipc"].update({"input_hash": "bad"}), "run-state-ipc-hash-invalid"),
        (lambda p: p["ipc"].update({"input_payload": []}), "run-state-ipc-payload-invalid"),
        (
            lambda p: p["ipc"]["input_payload"].update({"run_id": "other"}),
            "run-state-ipc-input-payload-mismatch",
        ),
        (
            lambda p: p["ipc"]["output_payload"].update({"tampered": True}),
            "run-state-ipc-output-payload-mismatch",
        ),
        (lambda p: p["ipc"].update({"input_hash": "f" * 64}), "run-state-input-hash-mismatch"),
        (lambda p: p["ipc"].update({"output_hash": "f" * 64}), "run-state-output-hash-mismatch"),
    ],
)
def test_verify_run_state_reports_structural_and_hash_mismatches(
    tmp_path: Path,
    mutator,
    expected_reason: str,
) -> None:
    """Run-state verifier should emit deterministic mismatch reasons."""

    run_dir, run_state_path, _sidecar_path, _sidecar_ref = _save_valid_walk_state(tmp_path)
    payload = json.loads(run_state_path.read_text(encoding="utf-8"))
    mutator(payload)
    run_state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = walker_run_state_store.verify_run_state(run_dir=run_dir, run_id=run_dir.name)
    assert result.status == "mismatch"
    assert result.reason == expected_reason


def test_verify_run_state_reports_run_id_mismatch_when_expected_run_id_differs(
    tmp_path: Path,
) -> None:
    """Requested run id should be enforced when provided to verifier."""

    run_dir, _run_state_path, _sidecar_path, _sidecar_ref = _save_valid_walk_state(tmp_path)
    result = walker_run_state_store.verify_run_state(run_dir=run_dir, run_id="other_run")
    assert result.status == "mismatch"
    assert result.reason == "run-state-run-id-mismatch"


def test_load_run_state_returns_non_verified_status_without_payload(tmp_path: Path) -> None:
    """Load should mirror non-verified verification status for missing run-state."""

    run_dir = tmp_path / "20260222_155258_nltk"
    run_dir.mkdir(parents=True, exist_ok=True)
    result = walker_run_state_store.load_run_state(run_dir=run_dir, run_id=run_dir.name)
    assert result.status == "missing"
    assert result.payload is None


def test_load_run_state_returns_parse_error_when_verified_path_not_readable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Load should return parse error if verified file cannot be decoded."""

    run_dir = tmp_path / "20260222_155258_nltk"
    run_state_path = walker_run_state_store._run_state_path(run_dir)
    run_state_path.parent.mkdir(parents=True, exist_ok=True)
    run_state_path.write_text("{bad", encoding="utf-8")

    monkeypatch.setattr(
        walker_run_state_store,
        "verify_run_state",
        lambda **_: walker_run_state_store.RunStateVerificationResult(
            status="verified",
            reason="verified",
            run_state_path=run_state_path,
            run_state_ipc_input_hash="a" * 64,
            run_state_ipc_output_hash="b" * 64,
        ),
    )
    result = walker_run_state_store.load_run_state(run_dir=run_dir, run_id=run_dir.name)
    assert result.status == "error"
    assert result.reason == "run-state-parse-error"
