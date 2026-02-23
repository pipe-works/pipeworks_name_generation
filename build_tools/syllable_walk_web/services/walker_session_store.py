"""Session IPC store for dual-patch walker restore metadata.

This service implements Phase 2 of the Patch A/B IPC session-load plan:

- write deterministic session artifacts under runtime-resolved ``sessions_base``
- verify session payload IPC integrity and linked run-state references
- list and load verified (or diagnosable) sessions for API integration
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from uuid import uuid4

from pipeworks_ipc.hashing import compute_output_hash, compute_payload_hash

from build_tools.syllable_walk_web.services.session_paths import (
    PATCH_KEYS,
    resolve_sessions_base,
    session_file_path,
)
from build_tools.syllable_walk_web.services.walker_run_state_store import (
    RUN_STATE_FILENAME,
    verify_run_state,
)
from build_tools.syllable_walk_web.state import PatchState, ServerState

SESSION_SCHEMA_VERSION = 1
SESSION_KIND = "walker_patch_session"
SESSION_RUN_STATE_RELATIVE_PATH = f"ipc/{RUN_STATE_FILENAME}"
IPC_LIBRARY = "pipeworks-ipc"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class SessionPatchReferenceResult:
    """Outcome of resolving one patch reference for session payload building."""

    status: str
    reason: str
    patch_ref: dict[str, Any] | None


@dataclass(frozen=True)
class SessionSaveResult:
    """Outcome of saving one dual-patch session payload."""

    status: str
    reason: str
    session_id: str | None = None
    session_path: Path | None = None
    patch_a_status: str | None = None
    patch_a_reason: str | None = None
    patch_b_status: str | None = None
    patch_b_reason: str | None = None
    ipc_input_hash: str | None = None
    ipc_output_hash: str | None = None
    root_session_id: str | None = None
    parent_session_id: str | None = None
    revision: int | None = None


@dataclass(frozen=True)
class SessionVerificationResult:
    """Outcome of validating one persisted session artifact."""

    status: str
    reason: str
    session_path: Path
    session_id: str | None = None
    ipc_input_hash: str | None = None
    ipc_output_hash: str | None = None


@dataclass(frozen=True)
class SessionLoadResult:
    """Outcome of loading one persisted session artifact."""

    status: str
    reason: str
    session_path: Path
    session_id: str | None = None
    payload: dict[str, Any] | None = None
    ipc_input_hash: str | None = None
    ipc_output_hash: str | None = None


@dataclass(frozen=True)
class SessionListEntry:
    """List item representing one persisted session artifact."""

    session_id: str
    created_at_utc: str | None
    label: str | None
    patch_a_run_id: str | None
    patch_b_run_id: str | None
    verification_status: str
    verification_reason: str
    session_path: Path
    root_session_id: str | None = None
    parent_session_id: str | None = None
    revision: int | None = None


def _utc_now_iso() -> str:
    """Return UTC timestamp in ``YYYY-MM-DDTHH:MM:SSZ`` format."""

    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _json_dumps_canonical(payload: dict[str, Any]) -> str:
    """Serialize JSON deterministically for stable hashing."""

    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _is_sha256_hex(value: Any) -> bool:
    """Return ``True`` when value is a canonical lowercase SHA-256 hash."""

    return isinstance(value, str) and _SHA256_RE.match(value) is not None


def _resolve_pipeworks_ipc_version() -> str:
    """Resolve installed ``pipeworks-ipc`` version for metadata fields."""

    try:
        return version("pipeworks-ipc")
    except PackageNotFoundError:
        return "unknown"


def _read_json_object(path: Path) -> dict[str, Any] | None:
    """Read JSON object from ``path``; return ``None`` for parse/type errors."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _new_session_id() -> str:
    """Generate opaque session id suitable for filename usage."""

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return f"session_{timestamp}_{uuid4().hex[:10]}"


def _normalize_label(label: str | None) -> str | None:
    """Normalize optional user label for session payloads."""

    if label is None:
        return None
    cleaned = str(label).strip()
    return cleaned or None


def _default_lineage(*, session_id: str) -> dict[str, Any]:
    """Build default lineage metadata for a first-generation session."""

    return {
        "root_session_id": session_id,
        "parent_session_id": None,
        "revision": 0,
    }


def _coerce_lineage(raw: Any) -> dict[str, Any] | None:
    """Validate/coerce session lineage metadata when present."""

    if not isinstance(raw, dict):
        return None
    root_session_id = raw.get("root_session_id")
    parent_session_id = raw.get("parent_session_id")
    revision = raw.get("revision")
    if not isinstance(root_session_id, str) or not root_session_id.strip():
        return None
    if parent_session_id is not None and (
        not isinstance(parent_session_id, str) or not parent_session_id.strip()
    ):
        return None
    if not isinstance(revision, int) or revision < 0:
        return None
    return {
        "root_session_id": root_session_id.strip(),
        "parent_session_id": (
            parent_session_id.strip() if isinstance(parent_session_id, str) else None
        ),
        "revision": revision,
    }


def _coerce_patch_ref(raw: Any, expected_patch: str) -> dict[str, str] | None:
    """Validate/coerce one persisted patch reference object."""

    if raw is None:
        return None
    if not isinstance(raw, dict):
        return None
    required = {
        "patch",
        "run_id",
        "manifest_ipc_output_hash",
        "run_state_relative_path",
        "run_state_ipc_output_hash",
    }
    if not required.issubset(raw.keys()):
        return None

    patch = raw.get("patch")
    run_id = raw.get("run_id")
    manifest_hash = raw.get("manifest_ipc_output_hash")
    run_state_rel = raw.get("run_state_relative_path")
    run_state_hash = raw.get("run_state_ipc_output_hash")
    if patch != expected_patch:
        return None
    if not isinstance(run_id, str) or not run_id.strip():
        return None
    if run_state_rel != SESSION_RUN_STATE_RELATIVE_PATH:
        return None
    if not _is_sha256_hex(manifest_hash) or not _is_sha256_hex(run_state_hash):
        return None

    return {
        "patch": patch,
        "run_id": run_id,
        "manifest_ipc_output_hash": str(manifest_hash),
        "run_state_relative_path": run_state_rel,
        "run_state_ipc_output_hash": str(run_state_hash),
    }


def _build_patch_reference(
    *, patch_key: str, patch_state: PatchState
) -> SessionPatchReferenceResult:
    """Build and verify one patch reference from in-memory patch state."""

    if patch_key not in PATCH_KEYS:
        return SessionPatchReferenceResult(
            status="error",
            reason=f"invalid-patch:{patch_key}",
            patch_ref=None,
        )

    run_id = patch_state.run_id
    run_dir = patch_state.corpus_dir
    manifest_hash = patch_state.manifest_ipc_output_hash

    if not isinstance(run_id, str) or not run_id.strip():
        return SessionPatchReferenceResult(
            status="skipped",
            reason=f"patch-{patch_key}-run-id-missing",
            patch_ref=None,
        )
    if not isinstance(run_dir, Path):
        return SessionPatchReferenceResult(
            status="skipped",
            reason=f"patch-{patch_key}-run-dir-missing",
            patch_ref=None,
        )
    if not _is_sha256_hex(manifest_hash):
        return SessionPatchReferenceResult(
            status="skipped",
            reason=f"patch-{patch_key}-manifest-hash-missing",
            patch_ref=None,
        )

    verification = verify_run_state(
        run_dir=run_dir,
        run_id=run_id,
        manifest_ipc_output_hash=str(manifest_hash),
    )
    if verification.status != "verified":
        return SessionPatchReferenceResult(
            status=verification.status,
            reason=f"patch-{patch_key}-run-state-{verification.reason}",
            patch_ref=None,
        )
    if not _is_sha256_hex(verification.run_state_ipc_output_hash):
        return SessionPatchReferenceResult(
            status="mismatch",
            reason=f"patch-{patch_key}-run-state-output-hash-missing",
            patch_ref=None,
        )

    return SessionPatchReferenceResult(
        status="saved",
        reason="saved",
        patch_ref={
            "patch": patch_key,
            "run_id": run_id,
            "manifest_ipc_output_hash": str(manifest_hash),
            "run_state_relative_path": SESSION_RUN_STATE_RELATIVE_PATH,
            "run_state_ipc_output_hash": str(verification.run_state_ipc_output_hash),
        },
    )


def _build_session_input_payload(
    *,
    session_id: str,
    label: str | None,
    patch_a: dict[str, Any] | None,
    patch_b: dict[str, Any] | None,
    lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build canonical session IPC input payload."""

    payload = {
        "session_id": session_id,
        "label": label,
        "patch_a": patch_a,
        "patch_b": patch_b,
    }
    if lineage is not None:
        payload["lineage"] = lineage
    return payload


def _build_session_output_payload(
    *,
    patch_a: dict[str, Any] | None,
    patch_b: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build canonical session IPC output payload."""

    return {
        "patch_a": patch_a,
        "patch_b": patch_b,
    }


def save_session(
    *,
    state: ServerState,
    label: str | None = None,
    session_id: str | None = None,
    repair_from_session_id: str | None = None,
) -> SessionSaveResult:
    """Persist one dual-patch session payload under resolved ``sessions_base``."""

    normalized_label = _normalize_label(label)
    cleaned_session_id = (
        session_id.strip() if isinstance(session_id, str) and session_id.strip() else None
    )
    cleaned_repair_source_id = (
        repair_from_session_id.strip()
        if isinstance(repair_from_session_id, str) and repair_from_session_id.strip()
        else None
    )
    if cleaned_session_id is not None and cleaned_repair_source_id is not None:
        return SessionSaveResult(
            status="error",
            reason="session-id-and-repair-source-are-mutually-exclusive",
        )

    lineage: dict[str, Any]
    if cleaned_repair_source_id is not None:
        parent_path = session_file_path(
            session_id=cleaned_repair_source_id,
            output_base=state.output_base,
            configured_sessions_base=state.sessions_base,
        )
        parent_payload = _read_json_object(parent_path)
        if parent_payload is None:
            return SessionSaveResult(
                status="missing",
                reason="repair-source-session-missing-or-invalid",
            )
        parent_session_id_raw = parent_payload.get("session_id")
        parent_session_id = (
            parent_session_id_raw.strip()
            if isinstance(parent_session_id_raw, str) and parent_session_id_raw.strip()
            else cleaned_repair_source_id
        )
        parent_lineage = _coerce_lineage(parent_payload.get("lineage"))
        if parent_lineage is None:
            parent_lineage = _default_lineage(session_id=parent_session_id)
        lineage = {
            "root_session_id": parent_lineage["root_session_id"],
            "parent_session_id": parent_session_id,
            "revision": int(parent_lineage["revision"]) + 1,
        }
        resolved_session_id = _new_session_id()
    else:
        resolved_session_id = cleaned_session_id or _new_session_id()
        path = session_file_path(
            session_id=resolved_session_id,
            output_base=state.output_base,
            configured_sessions_base=state.sessions_base,
        )
        if path.exists():
            return SessionSaveResult(
                status="mismatch",
                reason="session-id-already-exists",
                session_id=resolved_session_id,
            )
        lineage = _default_lineage(session_id=resolved_session_id)

    patch_a_result = _build_patch_reference(patch_key="a", patch_state=state.patch_a)
    patch_b_result = _build_patch_reference(patch_key="b", patch_state=state.patch_b)

    if patch_a_result.patch_ref is None and patch_b_result.patch_ref is None:
        return SessionSaveResult(
            status="skipped",
            reason="no-verifiable-patches",
            session_id=resolved_session_id,
            patch_a_status=patch_a_result.status,
            patch_a_reason=patch_a_result.reason,
            patch_b_status=patch_b_result.status,
            patch_b_reason=patch_b_result.reason,
            root_session_id=lineage["root_session_id"],
            parent_session_id=lineage["parent_session_id"],
            revision=lineage["revision"],
        )

    created_at_utc = _utc_now_iso()
    input_payload = _build_session_input_payload(
        session_id=resolved_session_id,
        label=normalized_label,
        patch_a=patch_a_result.patch_ref,
        patch_b=patch_b_result.patch_ref,
        lineage=lineage,
    )
    output_payload = _build_session_output_payload(
        patch_a=patch_a_result.patch_ref,
        patch_b=patch_b_result.patch_ref,
    )
    ipc_input_hash = compute_payload_hash(input_payload)
    ipc_output_hash = compute_output_hash(_json_dumps_canonical(output_payload))

    payload = {
        "schema_version": SESSION_SCHEMA_VERSION,
        "session_kind": SESSION_KIND,
        "session_id": resolved_session_id,
        "created_at_utc": created_at_utc,
        "label": normalized_label,
        "lineage": lineage,
        "patch_a": patch_a_result.patch_ref,
        "patch_b": patch_b_result.patch_ref,
        "ipc": {
            "version": SESSION_SCHEMA_VERSION,
            "library": IPC_LIBRARY,
            "library_ref": f"pipeworks-ipc-v{_resolve_pipeworks_ipc_version()}",
            "input_hash": ipc_input_hash,
            "output_hash": ipc_output_hash,
            "input_payload": input_payload,
            "output_payload": output_payload,
        },
    }

    path = session_file_path(
        session_id=resolved_session_id,
        output_base=state.output_base,
        configured_sessions_base=state.sessions_base,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return SessionSaveResult(
        status="saved",
        reason="saved",
        session_id=resolved_session_id,
        session_path=path,
        patch_a_status=patch_a_result.status,
        patch_a_reason=patch_a_result.reason,
        patch_b_status=patch_b_result.status,
        patch_b_reason=patch_b_result.reason,
        ipc_input_hash=ipc_input_hash,
        ipc_output_hash=ipc_output_hash,
        root_session_id=lineage["root_session_id"],
        parent_session_id=lineage["parent_session_id"],
        revision=lineage["revision"],
    )


def verify_session(*, session_path: Path, output_base: Path) -> SessionVerificationResult:
    """Verify persisted session payload + linked run-state references."""

    if not session_path.exists():
        return SessionVerificationResult(
            status="missing",
            reason="session-missing",
            session_path=session_path,
        )

    payload = _read_json_object(session_path)
    if payload is None:
        return SessionVerificationResult(
            status="error",
            reason="session-parse-error",
            session_path=session_path,
        )

    if payload.get("schema_version") != SESSION_SCHEMA_VERSION:
        return SessionVerificationResult(
            status="mismatch",
            reason="session-schema-version-mismatch",
            session_path=session_path,
        )
    if payload.get("session_kind") != SESSION_KIND:
        return SessionVerificationResult(
            status="mismatch",
            reason="session-kind-mismatch",
            session_path=session_path,
        )

    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        return SessionVerificationResult(
            status="mismatch",
            reason="session-id-missing",
            session_path=session_path,
        )
    raw_lineage = payload.get("lineage", None)
    if raw_lineage is None:
        lineage = _default_lineage(session_id=session_id)
    else:
        coerced_lineage = _coerce_lineage(raw_lineage)
        if coerced_lineage is None:
            return SessionVerificationResult(
                status="mismatch",
                reason="session-lineage-invalid",
                session_path=session_path,
                session_id=session_id,
            )
        lineage = coerced_lineage

    patch_a = _coerce_patch_ref(payload.get("patch_a"), "a")
    patch_b = _coerce_patch_ref(payload.get("patch_b"), "b")
    raw_patch_a = payload.get("patch_a")
    raw_patch_b = payload.get("patch_b")
    if raw_patch_a is not None and patch_a is None:
        return SessionVerificationResult(
            status="mismatch",
            reason="session-patch-a-invalid",
            session_path=session_path,
            session_id=session_id,
        )
    if raw_patch_b is not None and patch_b is None:
        return SessionVerificationResult(
            status="mismatch",
            reason="session-patch-b-invalid",
            session_path=session_path,
            session_id=session_id,
        )
    if patch_a is None and patch_b is None:
        return SessionVerificationResult(
            status="mismatch",
            reason="session-no-patches",
            session_path=session_path,
            session_id=session_id,
        )

    ipc = payload.get("ipc")
    if not isinstance(ipc, dict):
        return SessionVerificationResult(
            status="mismatch",
            reason="session-ipc-block-missing",
            session_path=session_path,
            session_id=session_id,
        )
    stored_in = ipc.get("input_hash")
    stored_out = ipc.get("output_hash")
    input_payload = ipc.get("input_payload")
    output_payload = ipc.get("output_payload")
    if not _is_sha256_hex(stored_in) or not _is_sha256_hex(stored_out):
        return SessionVerificationResult(
            status="mismatch",
            reason="session-ipc-hash-invalid",
            session_path=session_path,
            session_id=session_id,
        )
    if not isinstance(input_payload, dict) or not isinstance(output_payload, dict):
        return SessionVerificationResult(
            status="mismatch",
            reason="session-ipc-payload-invalid",
            session_path=session_path,
            session_id=session_id,
        )

    normalized_label = _normalize_label(payload.get("label"))
    expected_input_payload = _build_session_input_payload(
        session_id=session_id,
        label=normalized_label,
        patch_a=patch_a,
        patch_b=patch_b,
        lineage=lineage if raw_lineage is not None else None,
    )
    expected_output_payload = _build_session_output_payload(
        patch_a=patch_a,
        patch_b=patch_b,
    )
    if input_payload != expected_input_payload:
        return SessionVerificationResult(
            status="mismatch",
            reason="session-ipc-input-payload-mismatch",
            session_path=session_path,
            session_id=session_id,
        )
    if output_payload != expected_output_payload:
        return SessionVerificationResult(
            status="mismatch",
            reason="session-ipc-output-payload-mismatch",
            session_path=session_path,
            session_id=session_id,
        )

    expected_input_hash = compute_payload_hash(expected_input_payload)
    expected_output_hash = compute_output_hash(_json_dumps_canonical(expected_output_payload))
    if stored_in != expected_input_hash:
        return SessionVerificationResult(
            status="mismatch",
            reason="session-input-hash-mismatch",
            session_path=session_path,
            session_id=session_id,
            ipc_input_hash=str(stored_in),
            ipc_output_hash=str(stored_out),
        )
    if stored_out != expected_output_hash:
        return SessionVerificationResult(
            status="mismatch",
            reason="session-output-hash-mismatch",
            session_path=session_path,
            session_id=session_id,
            ipc_input_hash=str(stored_in),
            ipc_output_hash=str(stored_out),
        )

    for patch_ref in (patch_a, patch_b):
        if patch_ref is None:
            continue
        run_dir = output_base / patch_ref["run_id"]
        run_state_verification = verify_run_state(
            run_dir=run_dir,
            run_id=patch_ref["run_id"],
            manifest_ipc_output_hash=patch_ref["manifest_ipc_output_hash"],
        )
        if run_state_verification.status != "verified":
            return SessionVerificationResult(
                status=run_state_verification.status,
                reason=f"session-{patch_ref['patch']}-run-state-{run_state_verification.reason}",
                session_path=session_path,
                session_id=session_id,
                ipc_input_hash=str(stored_in),
                ipc_output_hash=str(stored_out),
            )
        if (
            run_state_verification.run_state_ipc_output_hash
            != patch_ref["run_state_ipc_output_hash"]
        ):
            return SessionVerificationResult(
                status="mismatch",
                reason=f"session-{patch_ref['patch']}-run-state-output-hash-mismatch",
                session_path=session_path,
                session_id=session_id,
                ipc_input_hash=str(stored_in),
                ipc_output_hash=str(stored_out),
            )

    return SessionVerificationResult(
        status="verified",
        reason="verified",
        session_path=session_path,
        session_id=session_id,
        ipc_input_hash=str(stored_in),
        ipc_output_hash=str(stored_out),
    )


def load_session(
    *,
    session_id: str,
    output_base: Path,
    configured_sessions_base: Path | None = None,
) -> SessionLoadResult:
    """Load one session by id when verification succeeds."""

    path = session_file_path(
        session_id=session_id,
        output_base=output_base,
        configured_sessions_base=configured_sessions_base,
    )
    verification = verify_session(session_path=path, output_base=output_base)
    if verification.status != "verified":
        return SessionLoadResult(
            status=verification.status,
            reason=verification.reason,
            session_path=path,
            session_id=verification.session_id,
            payload=None,
            ipc_input_hash=verification.ipc_input_hash,
            ipc_output_hash=verification.ipc_output_hash,
        )

    payload = _read_json_object(path)
    if payload is None:
        return SessionLoadResult(
            status="error",
            reason="session-parse-error",
            session_path=path,
            session_id=verification.session_id,
            payload=None,
            ipc_input_hash=verification.ipc_input_hash,
            ipc_output_hash=verification.ipc_output_hash,
        )

    return SessionLoadResult(
        status="verified",
        reason="verified",
        session_path=path,
        session_id=verification.session_id,
        payload=payload,
        ipc_input_hash=verification.ipc_input_hash,
        ipc_output_hash=verification.ipc_output_hash,
    )


def list_sessions(
    *,
    output_base: Path,
    configured_sessions_base: Path | None = None,
) -> list[SessionListEntry]:
    """List persisted sessions in descending ``created_at_utc`` order."""

    sessions_base = resolve_sessions_base(
        output_base=output_base,
        configured_sessions_base=configured_sessions_base,
    )
    if not sessions_base.exists() or not sessions_base.is_dir():
        return []

    entries: list[SessionListEntry] = []
    for path in sessions_base.glob("*.json"):
        payload = _read_json_object(path)
        if payload is None:
            continue
        session_id = payload.get("session_id")
        if not isinstance(session_id, str) or not session_id.strip():
            continue

        verification = verify_session(session_path=path, output_base=output_base)
        patch_a = payload.get("patch_a")
        patch_b = payload.get("patch_b")
        raw_lineage = payload.get("lineage", None)
        lineage = _coerce_lineage(raw_lineage) if raw_lineage is not None else None
        patch_a_run_id = patch_a.get("run_id") if isinstance(patch_a, dict) else None
        patch_b_run_id = patch_b.get("run_id") if isinstance(patch_b, dict) else None
        created_at_utc = payload.get("created_at_utc")
        label = _normalize_label(payload.get("label"))

        entries.append(
            SessionListEntry(
                session_id=session_id,
                created_at_utc=str(created_at_utc) if isinstance(created_at_utc, str) else None,
                label=label,
                patch_a_run_id=str(patch_a_run_id) if isinstance(patch_a_run_id, str) else None,
                patch_b_run_id=str(patch_b_run_id) if isinstance(patch_b_run_id, str) else None,
                verification_status=verification.status,
                verification_reason=verification.reason,
                session_path=path,
                root_session_id=(
                    lineage["root_session_id"]
                    if isinstance(lineage, dict)
                    else (session_id if isinstance(session_id, str) else None)
                ),
                parent_session_id=(
                    lineage["parent_session_id"] if isinstance(lineage, dict) else None
                ),
                revision=(lineage["revision"] if isinstance(lineage, dict) else 0),
            )
        )

    entries.sort(key=lambda item: item.created_at_utc or "", reverse=True)
    return entries
