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
