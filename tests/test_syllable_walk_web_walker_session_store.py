"""Tests for walker dual-patch session store service."""

from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import patch

from build_tools.syllable_walk_web.services import walker_run_state_store, walker_session_store
from build_tools.syllable_walk_web.state import ServerState


def _prepare_patch_with_run_state(
    *,
    output_base: Path,
    patch_key: str,
    run_id: str,
    manifest_hash: str,
    reach_hash: str,
    walk_label: str,
) -> ServerState:
    """Build state with one patch configured and persisted run-state."""

    state = ServerState(output_base=output_base)
    run_dir = output_base / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    patch_state = state.patch_a if patch_key == "a" else state.patch_b
    patch_state.run_id = run_id
    patch_state.corpus_dir = run_dir
    patch_state.manifest_ipc_output_hash = manifest_hash
    patch_state.reach_cache_ipc_output_hash = reach_hash

    saved = walker_run_state_store.save_run_state(
        state=state,
        patch=patch_key,
        artifact_kind="walks",
        artifact_payload={"walks": [{"formatted": walk_label}]},
    )
    assert saved.status == "saved"
    return state


def test_save_session_skips_when_no_verifiable_patches(tmp_path: Path) -> None:
    """Session save should skip when neither patch has verifiable run context."""

    state = ServerState(output_base=tmp_path / "output")
    result = walker_session_store.save_session(state=state)
    assert result.status == "skipped"
    assert result.reason == "no-verifiable-patches"
    assert result.session_path is None


def test_save_session_writes_payload_for_single_patch(tmp_path: Path) -> None:
    """Saving one loaded patch should create a valid session payload on disk."""

    output_base = tmp_path / "output"
    state = _prepare_patch_with_run_state(
        output_base=output_base,
        patch_key="a",
        run_id="20260222_155258_nltk",
        manifest_hash="a" * 64,
        reach_hash="b" * 64,
        walk_label="ka·ri",
    )

    result = walker_session_store.save_session(state=state, label=" Session A ")
    assert result.status == "saved"
    assert result.session_path is not None and result.session_path.exists()
    assert result.patch_a_status == "saved"
    assert result.patch_b_status == "skipped"

    payload = json.loads(result.session_path.read_text(encoding="utf-8"))
    assert payload["label"] == "Session A"
    assert payload["patch_a"]["patch"] == "a"
    assert payload["patch_a"]["run_id"] == "20260222_155258_nltk"
    assert payload["patch_b"] is None
    assert payload["ipc"]["input_hash"] == result.ipc_input_hash
    assert payload["ipc"]["output_hash"] == result.ipc_output_hash


def test_save_session_writes_payload_for_both_patches(tmp_path: Path) -> None:
    """Session payload should include both patch references when available."""

    output_base = tmp_path / "output"
    state = _prepare_patch_with_run_state(
        output_base=output_base,
        patch_key="a",
        run_id="20260222_155258_nltk",
        manifest_hash="a" * 64,
        reach_hash="b" * 64,
        walk_label="ka·ri",
    )
    state_b = _prepare_patch_with_run_state(
        output_base=output_base,
        patch_key="b",
        run_id="20260222_160001_pyphen",
        manifest_hash="c" * 64,
        reach_hash="d" * 64,
        walk_label="do·re",
    )
    state.patch_b = state_b.patch_b

    result = walker_session_store.save_session(state=state)
    assert result.status == "saved"
    assert result.session_path is not None

    payload = json.loads(result.session_path.read_text(encoding="utf-8"))
    assert payload["patch_a"] is not None
    assert payload["patch_b"] is not None
    assert payload["patch_b"]["patch"] == "b"
    assert payload["patch_b"]["run_id"] == "20260222_160001_pyphen"


def test_resolve_pipeworks_ipc_version_uses_unknown_when_metadata_missing() -> None:
    """Version lookup should degrade to explicit unknown marker."""

    with patch.object(
        walker_session_store,
        "version",
        side_effect=PackageNotFoundError("pipeworks-ipc"),
    ):
        assert walker_session_store._resolve_pipeworks_ipc_version() == "unknown"


def test_verify_session_reports_missing_and_parse_errors(tmp_path: Path) -> None:
    """Verifier should return clear statuses for absent/malformed files."""

    output_base = tmp_path / "output"
    path = (tmp_path / "sessions" / "missing.json").resolve()
    missing = walker_session_store.verify_session(session_path=path, output_base=output_base)
    assert missing.status == "missing"

    malformed = path.with_name("bad.json")
    malformed.parent.mkdir(parents=True, exist_ok=True)
    malformed.write_text("{bad", encoding="utf-8")
    parse_error = walker_session_store.verify_session(
        session_path=malformed,
        output_base=output_base,
    )
    assert parse_error.status == "error"
    assert parse_error.reason == "session-parse-error"


def test_verify_session_rejects_invalid_session_shape(tmp_path: Path) -> None:
    """Verifier should reject invalid top-level shape fields."""

    output_base = tmp_path / "output"
    session_path = (tmp_path / "sessions" / "s1.json").resolve()
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(
        json.dumps({"schema_version": 1, "session_kind": "bad"}),
        encoding="utf-8",
    )
    result = walker_session_store.verify_session(session_path=session_path, output_base=output_base)
    assert result.status == "mismatch"
    assert result.reason in {"session-id-missing", "session-kind-mismatch"}


def test_verify_session_rejects_invalid_patch_ref_and_no_patches(tmp_path: Path) -> None:
    """Verifier should reject malformed patch refs and empty patch sessions."""

    output_base = tmp_path / "output"
    session_path = (tmp_path / "sessions" / "s2.json").resolve()
    session_path.parent.mkdir(parents=True, exist_ok=True)
    base_payload = {
        "schema_version": 1,
        "session_kind": "walker_patch_session",
        "session_id": "s2",
        "created_at_utc": "2026-02-23T00:00:00Z",
        "label": None,
        "patch_a": None,
        "patch_b": None,
        "ipc": {
            "version": 1,
            "library": "pipeworks-ipc",
            "library_ref": "pipeworks-ipc-vx",
            "input_hash": "a" * 64,
            "output_hash": "b" * 64,
            "input_payload": {},
            "output_payload": {},
        },
    }
    session_path.write_text(json.dumps(base_payload), encoding="utf-8")
    no_patches = walker_session_store.verify_session(
        session_path=session_path, output_base=output_base
    )
    assert no_patches.status == "mismatch"
    assert no_patches.reason == "session-no-patches"

    base_payload["patch_a"] = {"patch": "a"}  # invalid ref
    session_path.write_text(json.dumps(base_payload), encoding="utf-8")
    invalid_patch = walker_session_store.verify_session(
        session_path=session_path,
        output_base=output_base,
    )
    assert invalid_patch.status == "mismatch"
    assert invalid_patch.reason == "session-patch-a-invalid"


def test_verify_session_detects_ipc_hash_drift(tmp_path: Path) -> None:
    """Verifier should reject input/output hash mismatches."""

    output_base = tmp_path / "output"
    state = _prepare_patch_with_run_state(
        output_base=output_base,
        patch_key="a",
        run_id="20260222_155258_nltk",
        manifest_hash="a" * 64,
        reach_hash="b" * 64,
        walk_label="ka·ri",
    )
    save_result = walker_session_store.save_session(state=state)
    assert save_result.session_path is not None

    payload = json.loads(save_result.session_path.read_text(encoding="utf-8"))
    payload["ipc"]["input_hash"] = "f" * 64
    save_result.session_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    input_mismatch = walker_session_store.verify_session(
        session_path=save_result.session_path,
        output_base=output_base,
    )
    assert input_mismatch.status == "mismatch"
    assert input_mismatch.reason == "session-input-hash-mismatch"

    payload = json.loads(save_result.session_path.read_text(encoding="utf-8"))
    payload["ipc"]["input_hash"] = save_result.ipc_input_hash
    payload["ipc"]["output_hash"] = "e" * 64
    save_result.session_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    output_mismatch = walker_session_store.verify_session(
        session_path=save_result.session_path,
        output_base=output_base,
    )
    assert output_mismatch.status == "mismatch"
    assert output_mismatch.reason == "session-output-hash-mismatch"


def test_verify_session_detects_linked_run_state_mismatch(tmp_path: Path) -> None:
    """Verifier should reject session when linked run-state hash drifts."""

    output_base = tmp_path / "output"
    state = _prepare_patch_with_run_state(
        output_base=output_base,
        patch_key="a",
        run_id="20260222_155258_nltk",
        manifest_hash="a" * 64,
        reach_hash="b" * 64,
        walk_label="ka·ri",
    )
    save_result = walker_session_store.save_session(state=state)
    assert save_result.session_path is not None

    payload = json.loads(save_result.session_path.read_text(encoding="utf-8"))
    payload["patch_a"]["run_state_ipc_output_hash"] = "f" * 64
    session_input = {
        "session_id": payload["session_id"],
        "label": payload.get("label"),
        "lineage": payload.get("lineage"),
        "patch_a": payload.get("patch_a"),
        "patch_b": payload.get("patch_b"),
    }
    session_output = {
        "patch_a": payload.get("patch_a"),
        "patch_b": payload.get("patch_b"),
    }
    payload["ipc"]["input_payload"] = session_input
    payload["ipc"]["output_payload"] = session_output
    payload["ipc"]["input_hash"] = walker_session_store.compute_payload_hash(session_input)
    payload["ipc"]["output_hash"] = walker_session_store.compute_output_hash(
        walker_session_store._json_dumps_canonical(session_output)
    )
    save_result.session_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    verification = walker_session_store.verify_session(
        session_path=save_result.session_path,
        output_base=output_base,
    )
    assert verification.status == "mismatch"
    assert verification.reason == "session-a-run-state-output-hash-mismatch"


def test_save_session_repair_creates_new_revision_and_keeps_original(tmp_path: Path) -> None:
    """Repair saves should create a new immutable revision without overwrite."""

    output_base = tmp_path / "output"
    state = _prepare_patch_with_run_state(
        output_base=output_base,
        patch_key="a",
        run_id="20260222_155258_nltk",
        manifest_hash="a" * 64,
        reach_hash="b" * 64,
        walk_label="ka·ri",
    )
    original = walker_session_store.save_session(
        state=state, session_id="session_orig", label="Original"
    )
    assert original.status == "saved"
    assert original.session_id == "session_orig"
    assert original.session_path is not None and original.session_path.exists()
    original_payload = json.loads(original.session_path.read_text(encoding="utf-8"))
    assert original_payload["lineage"]["revision"] == 0
    assert original_payload["lineage"]["parent_session_id"] is None

    repaired = walker_session_store.save_session(
        state=state,
        label="Repaired",
        repair_from_session_id="session_orig",
    )
    assert repaired.status == "saved"
    assert repaired.session_id is not None
    assert repaired.session_id != "session_orig"
    assert repaired.session_path is not None and repaired.session_path.exists()
    assert repaired.parent_session_id == "session_orig"
    assert repaired.root_session_id == "session_orig"
    assert repaired.revision == 1

    repaired_payload = json.loads(repaired.session_path.read_text(encoding="utf-8"))
    assert repaired_payload["lineage"]["root_session_id"] == "session_orig"
    assert repaired_payload["lineage"]["parent_session_id"] == "session_orig"
    assert repaired_payload["lineage"]["revision"] == 1
    assert original.session_path.exists()
    assert json.loads(original.session_path.read_text(encoding="utf-8")) == original_payload


def test_save_session_rejects_existing_explicit_session_id(tmp_path: Path) -> None:
    """Explicit session IDs should be immutable and cannot be overwritten."""

    output_base = tmp_path / "output"
    state = _prepare_patch_with_run_state(
        output_base=output_base,
        patch_key="a",
        run_id="20260222_155258_nltk",
        manifest_hash="a" * 64,
        reach_hash="b" * 64,
        walk_label="ka·ri",
    )
    first = walker_session_store.save_session(state=state, session_id="session_same")
    assert first.status == "saved"

    second = walker_session_store.save_session(state=state, session_id="session_same")
    assert second.status == "mismatch"
    assert second.reason == "session-id-already-exists"


def test_load_session_returns_verified_payload(tmp_path: Path) -> None:
    """Load should return payload when session verification passes."""

    output_base = tmp_path / "output"
    state = _prepare_patch_with_run_state(
        output_base=output_base,
        patch_key="a",
        run_id="20260222_155258_nltk",
        manifest_hash="a" * 64,
        reach_hash="b" * 64,
        walk_label="ka·ri",
    )
    save_result = walker_session_store.save_session(state=state, label="S1")
    assert save_result.session_id is not None

    loaded = walker_session_store.load_session(
        session_id=save_result.session_id,
        output_base=output_base,
    )
    assert loaded.status == "verified"
    assert loaded.payload is not None
    assert loaded.payload["session_id"] == save_result.session_id


def test_load_session_returns_non_verified_for_missing_session(tmp_path: Path) -> None:
    """Load should return missing status for unknown session ids."""

    output_base = tmp_path / "output"
    result = walker_session_store.load_session(session_id="missing", output_base=output_base)
    assert result.status == "missing"
    assert result.reason == "session-missing"
    assert result.payload is None


def test_list_sessions_returns_sorted_entries_with_verification(tmp_path: Path) -> None:
    """List should return newest-first entries with verification metadata."""

    output_base = tmp_path / "output"
    state1 = _prepare_patch_with_run_state(
        output_base=output_base,
        patch_key="a",
        run_id="20260222_155258_nltk",
        manifest_hash="a" * 64,
        reach_hash="b" * 64,
        walk_label="ka·ri",
    )
    save1 = walker_session_store.save_session(state=state1, session_id="session_001", label="Old")
    assert save1.session_path is not None
    payload1 = json.loads(save1.session_path.read_text(encoding="utf-8"))
    payload1["created_at_utc"] = "2026-02-22T10:00:00Z"
    save1.session_path.write_text(json.dumps(payload1, indent=2), encoding="utf-8")

    state2 = _prepare_patch_with_run_state(
        output_base=output_base,
        patch_key="b",
        run_id="20260222_160001_pyphen",
        manifest_hash="c" * 64,
        reach_hash="d" * 64,
        walk_label="do·re",
    )
    save2 = walker_session_store.save_session(state=state2, session_id="session_002", label="New")
    assert save2.session_path is not None
    payload2 = json.loads(save2.session_path.read_text(encoding="utf-8"))
    payload2["created_at_utc"] = "2026-02-22T11:00:00Z"
    save2.session_path.write_text(json.dumps(payload2, indent=2), encoding="utf-8")

    entries = walker_session_store.list_sessions(output_base=output_base)
    assert [entry.session_id for entry in entries] == ["session_002", "session_001"]
    assert entries[0].verification_status == "verified"
    assert entries[0].label == "New"
    assert entries[0].root_session_id == "session_002"
    assert entries[0].revision == 0
    assert entries[1].verification_status == "verified"


def test_list_sessions_ignores_non_json_and_invalid_objects(tmp_path: Path) -> None:
    """List should ignore non-parseable and missing-id artifacts."""

    output_base = tmp_path / "output"
    sessions_base = walker_session_store.resolve_sessions_base(output_base=output_base)
    sessions_base.mkdir(parents=True, exist_ok=True)
    (sessions_base / "bad.json").write_text("{bad", encoding="utf-8")
    (sessions_base / "noid.json").write_text(json.dumps({"created_at_utc": "x"}), encoding="utf-8")

    entries = walker_session_store.list_sessions(output_base=output_base)
    assert entries == []


def test_read_json_object_and_coerce_patch_ref_guard_paths(tmp_path: Path) -> None:
    """Low-level helpers should reject malformed JSON and malformed patch refs."""

    path = tmp_path / "not_object.json"
    path.write_text(json.dumps(["not", "object"]), encoding="utf-8")
    assert walker_session_store._read_json_object(path) is None

    assert walker_session_store._coerce_patch_ref(raw="bad", expected_patch="a") is None

    base = {
        "patch": "a",
        "run_id": "20260222_155258_nltk",
        "manifest_ipc_output_hash": "a" * 64,
        "run_state_relative_path": walker_session_store.SESSION_RUN_STATE_RELATIVE_PATH,
        "run_state_ipc_output_hash": "b" * 64,
    }
    bad_patch = dict(base)
    bad_patch["patch"] = "b"
    assert walker_session_store._coerce_patch_ref(bad_patch, expected_patch="a") is None

    bad_run_id = dict(base)
    bad_run_id["run_id"] = ""
    assert walker_session_store._coerce_patch_ref(bad_run_id, expected_patch="a") is None

    bad_relative = dict(base)
    bad_relative["run_state_relative_path"] = "ipc/other.json"
    assert walker_session_store._coerce_patch_ref(bad_relative, expected_patch="a") is None

    bad_hashes = dict(base)
    bad_hashes["manifest_ipc_output_hash"] = "not-a-hash"
    assert walker_session_store._coerce_patch_ref(bad_hashes, expected_patch="a") is None


def test_build_patch_reference_guard_paths(tmp_path: Path) -> None:
    """Patch reference builder should expose deterministic guard reasons."""

    state = ServerState(output_base=tmp_path / "output")

    invalid_patch = walker_session_store._build_patch_reference(
        patch_key="z",
        patch_state=state.patch_a,
    )
    assert invalid_patch.status == "error"
    assert invalid_patch.reason == "invalid-patch:z"

    state.patch_a.run_id = "run_1"
    state.patch_a.manifest_ipc_output_hash = "a" * 64
    run_dir_missing = walker_session_store._build_patch_reference(
        patch_key="a",
        patch_state=state.patch_a,
    )
    assert run_dir_missing.status == "skipped"
    assert run_dir_missing.reason == "patch-a-run-dir-missing"

    state.patch_a.corpus_dir = state.output_base / "run_1"
    state.patch_a.corpus_dir.mkdir(parents=True, exist_ok=True)
    state.patch_a.manifest_ipc_output_hash = "bad"
    manifest_missing = walker_session_store._build_patch_reference(
        patch_key="a",
        patch_state=state.patch_a,
    )
    assert manifest_missing.status == "skipped"
    assert manifest_missing.reason == "patch-a-manifest-hash-missing"

    state.patch_a.manifest_ipc_output_hash = "a" * 64
    with patch.object(
        walker_session_store,
        "verify_run_state",
        return_value=walker_run_state_store.RunStateVerificationResult(
            status="missing",
            reason="run-state-missing",
            run_state_path=state.patch_a.corpus_dir
            / "ipc"
            / walker_run_state_store.RUN_STATE_FILENAME,
            run_state_ipc_input_hash=None,
            run_state_ipc_output_hash=None,
        ),
    ):
        run_state_missing = walker_session_store._build_patch_reference(
            patch_key="a",
            patch_state=state.patch_a,
        )
    assert run_state_missing.status == "missing"
    assert run_state_missing.reason == "patch-a-run-state-run-state-missing"

    with patch.object(
        walker_session_store,
        "verify_run_state",
        return_value=walker_run_state_store.RunStateVerificationResult(
            status="verified",
            reason="verified",
            run_state_path=state.patch_a.corpus_dir
            / "ipc"
            / walker_run_state_store.RUN_STATE_FILENAME,
            run_state_ipc_input_hash="c" * 64,
            run_state_ipc_output_hash=None,
        ),
    ):
        output_hash_missing = walker_session_store._build_patch_reference(
            patch_key="a",
            patch_state=state.patch_a,
        )
    assert output_hash_missing.status == "mismatch"
    assert output_hash_missing.reason == "patch-a-run-state-output-hash-missing"


def test_verify_session_rejects_schema_and_session_id(tmp_path: Path) -> None:
    """Verifier should reject schema drift and missing session identifiers."""

    output_base = tmp_path / "output"
    state = _prepare_patch_with_run_state(
        output_base=output_base,
        patch_key="a",
        run_id="20260222_155258_nltk",
        manifest_hash="a" * 64,
        reach_hash="b" * 64,
        walk_label="ka·ri",
    )
    saved = walker_session_store.save_session(state=state, session_id="session_schema")
    assert saved.session_path is not None

    payload = json.loads(saved.session_path.read_text(encoding="utf-8"))
    payload["schema_version"] = 99
    saved.session_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    schema_mismatch = walker_session_store.verify_session(
        session_path=saved.session_path,
        output_base=output_base,
    )
    assert schema_mismatch.status == "mismatch"
    assert schema_mismatch.reason == "session-schema-version-mismatch"

    payload["schema_version"] = walker_session_store.SESSION_SCHEMA_VERSION
    payload["session_id"] = ""
    saved.session_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    session_id_missing = walker_session_store.verify_session(
        session_path=saved.session_path,
        output_base=output_base,
    )
    assert session_id_missing.status == "mismatch"
    assert session_id_missing.reason == "session-id-missing"


def test_verify_session_rejects_patch_b_and_ipc_shape_variants(tmp_path: Path) -> None:
    """Verifier should reject malformed patch-b refs and malformed IPC blocks."""

    output_base = tmp_path / "output"
    state = _prepare_patch_with_run_state(
        output_base=output_base,
        patch_key="a",
        run_id="20260222_155258_nltk",
        manifest_hash="a" * 64,
        reach_hash="b" * 64,
        walk_label="ka·ri",
    )
    saved = walker_session_store.save_session(state=state, session_id="session_shapes")
    assert saved.session_path is not None

    payload = json.loads(saved.session_path.read_text(encoding="utf-8"))

    payload_patch_b = dict(payload)
    payload_patch_b["patch_b"] = {"patch": "b"}
    saved.session_path.write_text(json.dumps(payload_patch_b, indent=2), encoding="utf-8")
    patch_b_invalid = walker_session_store.verify_session(
        session_path=saved.session_path,
        output_base=output_base,
    )
    assert patch_b_invalid.status == "mismatch"
    assert patch_b_invalid.reason == "session-patch-b-invalid"

    payload_ipc_missing = dict(payload)
    payload_ipc_missing["ipc"] = None
    saved.session_path.write_text(json.dumps(payload_ipc_missing, indent=2), encoding="utf-8")
    ipc_missing = walker_session_store.verify_session(
        session_path=saved.session_path,
        output_base=output_base,
    )
    assert ipc_missing.status == "mismatch"
    assert ipc_missing.reason == "session-ipc-block-missing"

    payload_hash_invalid = dict(payload)
    payload_hash_invalid["ipc"] = dict(payload["ipc"])
    payload_hash_invalid["ipc"]["input_hash"] = "bad"
    saved.session_path.write_text(json.dumps(payload_hash_invalid, indent=2), encoding="utf-8")
    hash_invalid = walker_session_store.verify_session(
        session_path=saved.session_path,
        output_base=output_base,
    )
    assert hash_invalid.status == "mismatch"
    assert hash_invalid.reason == "session-ipc-hash-invalid"

    payload_block_invalid = dict(payload)
    payload_block_invalid["ipc"] = dict(payload["ipc"])
    payload_block_invalid["ipc"]["input_payload"] = ["bad"]
    saved.session_path.write_text(json.dumps(payload_block_invalid, indent=2), encoding="utf-8")
    block_invalid = walker_session_store.verify_session(
        session_path=saved.session_path,
        output_base=output_base,
    )
    assert block_invalid.status == "mismatch"
    assert block_invalid.reason == "session-ipc-payload-invalid"


def test_verify_session_rejects_invalid_lineage_shape(tmp_path: Path) -> None:
    """Verifier should reject malformed lineage metadata when present."""

    output_base = tmp_path / "output"
    state = _prepare_patch_with_run_state(
        output_base=output_base,
        patch_key="a",
        run_id="20260222_155258_nltk",
        manifest_hash="a" * 64,
        reach_hash="b" * 64,
        walk_label="ka·ri",
    )
    saved = walker_session_store.save_session(state=state, session_id="session_lineage")
    assert saved.session_path is not None

    payload = json.loads(saved.session_path.read_text(encoding="utf-8"))
    payload["lineage"] = {"root_session_id": "", "parent_session_id": None, "revision": 0}
    saved.session_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    verification = walker_session_store.verify_session(
        session_path=saved.session_path,
        output_base=output_base,
    )
    assert verification.status == "mismatch"
    assert verification.reason == "session-lineage-invalid"


def test_verify_session_rejects_input_output_payload_drift(tmp_path: Path) -> None:
    """Verifier should reject IPC payload drift before hash comparisons."""

    output_base = tmp_path / "output"
    state = _prepare_patch_with_run_state(
        output_base=output_base,
        patch_key="a",
        run_id="20260222_155258_nltk",
        manifest_hash="a" * 64,
        reach_hash="b" * 64,
        walk_label="ka·ri",
    )
    saved = walker_session_store.save_session(state=state, session_id="session_payload_drift")
    assert saved.session_path is not None

    payload = json.loads(saved.session_path.read_text(encoding="utf-8"))

    payload_input = dict(payload)
    payload_input["ipc"] = dict(payload["ipc"])
    payload_input["ipc"]["input_payload"] = dict(payload["ipc"]["input_payload"])
    payload_input["ipc"]["input_payload"]["session_id"] = "different"
    saved.session_path.write_text(json.dumps(payload_input, indent=2), encoding="utf-8")
    input_payload_mismatch = walker_session_store.verify_session(
        session_path=saved.session_path,
        output_base=output_base,
    )
    assert input_payload_mismatch.status == "mismatch"
    assert input_payload_mismatch.reason == "session-ipc-input-payload-mismatch"

    payload_output = dict(payload)
    payload_output["ipc"] = dict(payload["ipc"])
    payload_output["ipc"]["output_payload"] = dict(payload["ipc"]["output_payload"])
    payload_output["ipc"]["output_payload"]["patch_a"] = None
    saved.session_path.write_text(json.dumps(payload_output, indent=2), encoding="utf-8")
    output_payload_mismatch = walker_session_store.verify_session(
        session_path=saved.session_path,
        output_base=output_base,
    )
    assert output_payload_mismatch.status == "mismatch"
    assert output_payload_mismatch.reason == "session-ipc-output-payload-mismatch"


def test_verify_session_detects_linked_run_state_missing(tmp_path: Path) -> None:
    """Verifier should propagate linked run-state verification failures."""

    output_base = tmp_path / "output"
    state = _prepare_patch_with_run_state(
        output_base=output_base,
        patch_key="a",
        run_id="20260222_155258_nltk",
        manifest_hash="a" * 64,
        reach_hash="b" * 64,
        walk_label="ka·ri",
    )
    saved = walker_session_store.save_session(state=state, session_id="session_missing_run_state")
    assert saved.session_path is not None

    run_state_path = (
        output_base / "20260222_155258_nltk" / "ipc" / walker_run_state_store.RUN_STATE_FILENAME
    )
    run_state_path.unlink()

    verification = walker_session_store.verify_session(
        session_path=saved.session_path,
        output_base=output_base,
    )
    assert verification.status == "missing"
    assert verification.reason == "session-a-run-state-run-state-missing"


def test_load_session_handles_post_verify_parse_error(tmp_path: Path) -> None:
    """Load should return parse error when payload cannot be read after verify."""

    output_base = tmp_path / "output"
    sessions_base = tmp_path / "sessions"
    sessions_base.mkdir(parents=True, exist_ok=True)
    session_path = sessions_base / "session_parse_error.json"
    session_path.write_text("{bad", encoding="utf-8")

    with patch.object(
        walker_session_store,
        "verify_session",
        return_value=walker_session_store.SessionVerificationResult(
            status="verified",
            reason="verified",
            session_path=session_path,
            session_id="session_parse_error",
            ipc_input_hash="a" * 64,
            ipc_output_hash="b" * 64,
        ),
    ):
        loaded = walker_session_store.load_session(
            session_id="session_parse_error",
            output_base=output_base,
            configured_sessions_base=sessions_base,
        )

    assert loaded.status == "error"
    assert loaded.reason == "session-parse-error"
    assert loaded.payload is None


def test_list_sessions_returns_empty_when_sessions_base_absent(tmp_path: Path) -> None:
    """List should return empty results when sessions base path does not exist."""

    output_base = tmp_path / "output"
    configured_sessions_base = tmp_path / "missing_sessions"
    entries = walker_session_store.list_sessions(
        output_base=output_base,
        configured_sessions_base=configured_sessions_base,
    )
    assert entries == []


def test_coerce_lineage_rejects_invalid_parent_or_revision() -> None:
    """Lineage coercion should reject blank parent IDs and negative revisions."""

    assert walker_session_store._coerce_lineage(["bad"]) is None
    assert (
        walker_session_store._coerce_lineage(
            {"root_session_id": "session_root", "parent_session_id": " ", "revision": 0}
        )
        is None
    )
    assert (
        walker_session_store._coerce_lineage(
            {"root_session_id": "session_root", "parent_session_id": None, "revision": -1}
        )
        is None
    )


def test_save_session_rejects_mutually_exclusive_session_id_and_repair_source(
    tmp_path: Path,
) -> None:
    """Save should reject providing both explicit session id and repair source."""

    state = ServerState(output_base=tmp_path / "output")
    result = walker_session_store.save_session(
        state=state,
        session_id="session_explicit",
        repair_from_session_id="session_parent",
    )
    assert result.status == "error"
    assert result.reason == "session-id-and-repair-source-are-mutually-exclusive"


def test_save_session_repair_rejects_missing_parent_session(tmp_path: Path) -> None:
    """Repair saves should fail fast when parent session payload is absent/invalid."""

    state = ServerState(output_base=tmp_path / "output")
    result = walker_session_store.save_session(
        state=state,
        repair_from_session_id="session_missing_parent",
    )
    assert result.status == "missing"
    assert result.reason == "repair-source-session-missing-or-invalid"


def test_save_session_repair_falls_back_to_default_lineage_for_invalid_parent_lineage(
    tmp_path: Path,
) -> None:
    """Repair saves should recover lineage when parent payload lineage is malformed."""

    output_base = tmp_path / "output"
    state = _prepare_patch_with_run_state(
        output_base=output_base,
        patch_key="a",
        run_id="20260222_155258_nltk",
        manifest_hash="a" * 64,
        reach_hash="b" * 64,
        walk_label="ka·ri",
    )
    sessions_base = (tmp_path / "sessions").resolve()
    sessions_base.mkdir(parents=True, exist_ok=True)
    parent_path = sessions_base / "session_parent.json"
    parent_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "session_kind": "walker_patch_session",
                "session_id": "session_parent",
                "created_at_utc": "2026-02-23T00:00:00Z",
                "label": None,
                "patch_a": None,
                "patch_b": None,
                "lineage": {"root_session_id": "", "parent_session_id": None, "revision": 0},
                "ipc": {
                    "version": 1,
                    "library": "pipeworks-ipc",
                    "library_ref": "pipeworks-ipc-vx",
                    "input_hash": "a" * 64,
                    "output_hash": "b" * 64,
                    "input_payload": {},
                    "output_payload": {},
                },
            }
        ),
        encoding="utf-8",
    )
    state.sessions_base = sessions_base

    repaired = walker_session_store.save_session(
        state=state,
        repair_from_session_id="session_parent",
    )
    assert repaired.status == "saved"
    assert repaired.session_path is not None

    repaired_payload = json.loads(repaired.session_path.read_text(encoding="utf-8"))
    assert repaired_payload["lineage"]["root_session_id"] == "session_parent"
    assert repaired_payload["lineage"]["parent_session_id"] == "session_parent"
    assert repaired_payload["lineage"]["revision"] == 1
