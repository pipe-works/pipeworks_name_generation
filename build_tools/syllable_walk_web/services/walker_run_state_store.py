"""Run-local IPC store for walker Patch A/B output state.

This service implements Phase 1 of the Patch A/B IPC session-load plan:

- write deterministic patch-output sidecars under ``<run_dir>/ipc/``
- maintain ``walker_run_state.v1.json`` as the authoritative per-run index
- verify stored IPC hashes for run-state + referenced sidecars
- load only verified run-state payloads

The API layer calls this service after successful mutable operations
(``walk``, ``combine``, ``select``, ``package``). Persistence failures are
reported to callers via result status but should not crash request handling.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from pipeworks_ipc.hashing import compute_output_hash, compute_payload_hash

from build_tools.syllable_walk_web.services.session_paths import (
    PATCH_KEYS,
    PATCH_OUTPUT_KINDS,
    patch_output_sidecar_path,
    run_ipc_dir,
)
from build_tools.syllable_walk_web.state import ServerState

RUN_STATE_FILENAME = "walker_run_state.v1.json"
SCHEMA_VERSION = 1
SIDE_CAR_SCHEMA_VERSION = 1
IPC_LIBRARY = "pipeworks-ipc"
RUN_STATE_KIND = "walker_run_state"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class RunStateSaveResult:
    """Outcome of one save operation for a patch-output artifact."""

    status: str
    reason: str
    run_state_path: Path | None = None
    sidecar_path: Path | None = None
    run_state_ipc_input_hash: str | None = None
    run_state_ipc_output_hash: str | None = None
    sidecar_ipc_input_hash: str | None = None
    sidecar_ipc_output_hash: str | None = None


@dataclass(frozen=True)
class RunStateVerificationResult:
    """Outcome of validating one run-state payload + referenced sidecars."""

    status: str
    reason: str
    run_state_path: Path
    run_state_ipc_input_hash: str | None = None
    run_state_ipc_output_hash: str | None = None


@dataclass(frozen=True)
class RunStateLoadResult:
    """Outcome of loading one run-state payload."""

    status: str
    reason: str
    run_state_path: Path
    payload: dict[str, Any] | None = None
    run_state_ipc_input_hash: str | None = None
    run_state_ipc_output_hash: str | None = None


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


def _run_state_path(run_dir: Path) -> Path:
    """Return canonical run-state path for one run directory."""

    return run_ipc_dir(run_dir) / RUN_STATE_FILENAME


def _all_sidecar_slots() -> tuple[str, ...]:
    """Return canonical ordered sidecar slot names for run-state payloads."""

    slots: list[str] = []
    for patch in PATCH_KEYS:
        for kind in PATCH_OUTPUT_KINDS:
            slots.append(f"patch_{patch}_{kind}")
    return tuple(slots)


def _empty_sidecars() -> dict[str, dict[str, str] | None]:
    """Return empty sidecar slot mapping with all canonical keys present."""

    return {slot: None for slot in _all_sidecar_slots()}


def _coerce_sidecar_ref(raw: Any) -> dict[str, str] | None:
    """Validate/coerce one sidecar-ref object from a JSON payload."""

    if not isinstance(raw, dict):
        return None
    required = {"relative_path", "artifact_kind", "patch", "ipc_input_hash", "ipc_output_hash"}
    if not required.issubset(raw.keys()):
        return None

    relative_path = raw.get("relative_path")
    artifact_kind = raw.get("artifact_kind")
    patch = raw.get("patch")
    ipc_input_hash = raw.get("ipc_input_hash")
    ipc_output_hash = raw.get("ipc_output_hash")

    if not isinstance(relative_path, str):
        return None
    if artifact_kind not in PATCH_OUTPUT_KINDS:
        return None
    if patch not in PATCH_KEYS:
        return None
    if not _is_sha256_hex(ipc_input_hash) or not _is_sha256_hex(ipc_output_hash):
        return None

    return {
        "relative_path": relative_path,
        "artifact_kind": str(artifact_kind),
        "patch": str(patch),
        "ipc_input_hash": str(ipc_input_hash),
        "ipc_output_hash": str(ipc_output_hash),
    }


def _read_json_object(path: Path) -> dict[str, Any] | None:
    """Read JSON object from ``path``; return ``None`` for parse/type errors."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _load_existing_sidecars(run_dir: Path, run_id: str) -> dict[str, dict[str, str] | None]:
    """Load existing run-state sidecar slots for one run, if valid."""

    sidecars = _empty_sidecars()
    path = _run_state_path(run_dir)
    if not path.exists():
        return sidecars

    payload = _read_json_object(path)
    if payload is None:
        return sidecars
    if payload.get("run_id") != run_id:
        return sidecars

    raw_sidecars = payload.get("sidecars")
    if not isinstance(raw_sidecars, dict):
        return sidecars

    for slot in sidecars:
        value = raw_sidecars.get(slot)
        if value is None:
            sidecars[slot] = None
            continue
        coerced = _coerce_sidecar_ref(value)
        if coerced is not None:
            sidecars[slot] = coerced

    return sidecars


def _build_sidecar_input_payload(
    *,
    run_id: str,
    patch: str,
    artifact_kind: str,
    manifest_ipc_output_hash: str,
    reach_cache_ipc_output_hash: str | None,
) -> dict[str, Any]:
    """Build canonical sidecar IPC input payload."""

    return {
        "run_id": run_id,
        "patch": patch,
        "artifact_kind": artifact_kind,
        "manifest_ipc_output_hash": manifest_ipc_output_hash,
        "reach_cache_ipc_output_hash": reach_cache_ipc_output_hash,
    }


def _normalized_sidecars(sidecars: dict[str, dict[str, str] | None]) -> dict[str, Any]:
    """Normalize sidecar slots for deterministic run-state hashing."""

    normalized: dict[str, Any] = {}
    for slot in _all_sidecar_slots():
        ref = sidecars.get(slot)
        if ref is None:
            normalized[slot] = None
            continue
        normalized[slot] = {
            "relative_path": ref["relative_path"],
            "artifact_kind": ref["artifact_kind"],
            "patch": ref["patch"],
            "ipc_input_hash": ref["ipc_input_hash"],
            "ipc_output_hash": ref["ipc_output_hash"],
        }
    return normalized


def _build_run_state_input_payload(
    *,
    run_id: str,
    manifest_ipc_output_hash: str,
    reach_cache_ipc_output_hash: str | None,
    sidecars: dict[str, dict[str, str] | None],
) -> dict[str, Any]:
    """Build canonical run-state IPC input payload."""

    return {
        "run_id": run_id,
        "manifest_ipc_output_hash": manifest_ipc_output_hash,
        "reach_cache_ipc_output_hash": reach_cache_ipc_output_hash,
        "sidecars": _normalized_sidecars(sidecars),
    }


def _build_run_state_output_payload(
    *,
    sidecars: dict[str, dict[str, str] | None],
) -> dict[str, Any]:
    """Build canonical run-state IPC output payload."""

    return {
        "sidecars": _normalized_sidecars(sidecars),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON payload with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _verify_sidecar_payload(
    *,
    run_dir: Path,
    run_id: str,
    slot: str,
    sidecar_ref: dict[str, str],
) -> tuple[str, str]:
    """Verify one sidecar payload referenced from run-state."""

    rel = sidecar_ref["relative_path"]
    sidecar_path = (run_dir / rel).resolve()
    if not str(sidecar_path).startswith(str(run_dir.resolve())):
        return "mismatch", f"{slot}:sidecar-path-outside-run-dir"
    if not sidecar_path.exists():
        return "missing", f"{slot}:sidecar-missing"

    payload = _read_json_object(sidecar_path)
    if payload is None:
        return "error", f"{slot}:sidecar-parse-error"

    if payload.get("schema_version") != SIDE_CAR_SCHEMA_VERSION:
        return "mismatch", f"{slot}:sidecar-schema-version-mismatch"
    if payload.get("run_id") != run_id:
        return "mismatch", f"{slot}:sidecar-run-id-mismatch"
    if payload.get("patch") != sidecar_ref["patch"]:
        return "mismatch", f"{slot}:sidecar-patch-mismatch"
    if payload.get("artifact_kind") != sidecar_ref["artifact_kind"]:
        return "mismatch", f"{slot}:sidecar-kind-mismatch"

    ipc = payload.get("ipc")
    if not isinstance(ipc, dict):
        return "mismatch", f"{slot}:sidecar-ipc-block-missing"

    stored_in = ipc.get("input_hash")
    stored_out = ipc.get("output_hash")
    input_payload = ipc.get("input_payload")
    output_payload = ipc.get("output_payload")
    if not _is_sha256_hex(stored_in) or not _is_sha256_hex(stored_out):
        return "mismatch", f"{slot}:sidecar-ipc-hash-invalid"
    if not isinstance(input_payload, dict) or not isinstance(output_payload, dict):
        return "mismatch", f"{slot}:sidecar-ipc-payload-invalid"

    expected_in = compute_payload_hash(input_payload)
    expected_out = compute_output_hash(_json_dumps_canonical(output_payload))
    if expected_in != stored_in:
        return "mismatch", f"{slot}:sidecar-input-hash-mismatch"
    if expected_out != stored_out:
        return "mismatch", f"{slot}:sidecar-output-hash-mismatch"

    if stored_in != sidecar_ref["ipc_input_hash"]:
        return "mismatch", f"{slot}:sidecar-ref-input-hash-mismatch"
    if stored_out != sidecar_ref["ipc_output_hash"]:
        return "mismatch", f"{slot}:sidecar-ref-output-hash-mismatch"

    payload_block = payload.get("payload")
    if not isinstance(payload_block, dict):
        return "mismatch", f"{slot}:sidecar-payload-not-object"
    if payload_block != output_payload:
        return "mismatch", f"{slot}:sidecar-payload-output-mismatch"

    return "verified", f"{slot}:sidecar-verified"


def save_run_state(
    *,
    state: ServerState,
    patch: str,
    artifact_kind: str,
    artifact_payload: dict[str, Any],
) -> RunStateSaveResult:
    """Save one patch artifact sidecar and update run-state index for the run.

    Args:
        state: Server global state with patch A/B contexts.
        patch: Patch key (``"a"`` or ``"b"``).
        artifact_kind: Sidecar kind (``walks``/``candidates``/``selections``/``package``).
        artifact_payload: Object payload to persist in sidecar and hash.

    Returns:
        ``RunStateSaveResult`` with ``status`` in ``saved|skipped|error``.
    """

    patch_key = patch.lower()
    if patch_key not in PATCH_KEYS:
        return RunStateSaveResult(status="error", reason=f"invalid-patch:{patch}")
    if artifact_kind not in PATCH_OUTPUT_KINDS:
        return RunStateSaveResult(status="error", reason=f"invalid-artifact-kind:{artifact_kind}")
    if not isinstance(artifact_payload, dict):
        return RunStateSaveResult(status="error", reason="artifact-payload-not-object")

    patch_state = state.patch_a if patch_key == "a" else state.patch_b
    run_id = patch_state.run_id
    run_dir = patch_state.corpus_dir

    if not isinstance(run_id, str) or not run_id.strip():
        return RunStateSaveResult(status="skipped", reason="patch-run-id-missing")
    if not isinstance(run_dir, Path):
        return RunStateSaveResult(status="skipped", reason="patch-run-dir-missing")
    manifest_output_hash = patch_state.manifest_ipc_output_hash
    if not _is_sha256_hex(manifest_output_hash):
        return RunStateSaveResult(status="skipped", reason="manifest-output-hash-missing")

    reach_output_hash: str | None = None
    if _is_sha256_hex(patch_state.reach_cache_ipc_output_hash):
        reach_output_hash = str(patch_state.reach_cache_ipc_output_hash)

    sidecar_path = patch_output_sidecar_path(
        run_dir=run_dir,
        patch=patch_key,
        artifact_kind=artifact_kind,
        schema_version=SIDE_CAR_SCHEMA_VERSION,
    )
    created_at_utc = _utc_now_iso()

    sidecar_input_payload = _build_sidecar_input_payload(
        run_id=run_id,
        patch=patch_key,
        artifact_kind=artifact_kind,
        manifest_ipc_output_hash=str(manifest_output_hash),
        reach_cache_ipc_output_hash=reach_output_hash,
    )
    sidecar_output_payload = artifact_payload
    sidecar_input_hash = compute_payload_hash(sidecar_input_payload)
    sidecar_output_hash = compute_output_hash(_json_dumps_canonical(sidecar_output_payload))

    sidecar_payload = {
        "schema_version": SIDE_CAR_SCHEMA_VERSION,
        "artifact_kind": artifact_kind,
        "patch": patch_key,
        "run_id": run_id,
        "created_at_utc": created_at_utc,
        "ipc": {
            "version": SCHEMA_VERSION,
            "library": IPC_LIBRARY,
            "library_ref": f"pipeworks-ipc-v{_resolve_pipeworks_ipc_version()}",
            "input_hash": sidecar_input_hash,
            "output_hash": sidecar_output_hash,
            "input_payload": sidecar_input_payload,
            "output_payload": sidecar_output_payload,
        },
        "payload": artifact_payload,
    }
    _write_json(sidecar_path, sidecar_payload)

    sidecars = _load_existing_sidecars(run_dir, run_id)
    slot = f"patch_{patch_key}_{artifact_kind}"
    sidecars[slot] = {
        "relative_path": sidecar_path.relative_to(run_dir).as_posix(),
        "artifact_kind": artifact_kind,
        "patch": patch_key,
        "ipc_input_hash": sidecar_input_hash,
        "ipc_output_hash": sidecar_output_hash,
    }

    run_state_input_payload = _build_run_state_input_payload(
        run_id=run_id,
        manifest_ipc_output_hash=str(manifest_output_hash),
        reach_cache_ipc_output_hash=reach_output_hash,
        sidecars=sidecars,
    )
    run_state_output_payload = _build_run_state_output_payload(sidecars=sidecars)
    run_state_input_hash = compute_payload_hash(run_state_input_payload)
    run_state_output_hash = compute_output_hash(_json_dumps_canonical(run_state_output_payload))

    run_state_payload = {
        "schema_version": SCHEMA_VERSION,
        "state_kind": RUN_STATE_KIND,
        "run_id": run_id,
        "created_at_utc": created_at_utc,
        "manifest_ipc_output_hash": manifest_output_hash,
        "reach_cache_ipc_output_hash": reach_output_hash,
        "sidecars": _normalized_sidecars(sidecars),
        "ipc": {
            "version": SCHEMA_VERSION,
            "library": IPC_LIBRARY,
            "library_ref": f"pipeworks-ipc-v{_resolve_pipeworks_ipc_version()}",
            "input_hash": run_state_input_hash,
            "output_hash": run_state_output_hash,
            "input_payload": run_state_input_payload,
            "output_payload": run_state_output_payload,
        },
    }
    run_state_path = _run_state_path(run_dir)
    _write_json(run_state_path, run_state_payload)

    return RunStateSaveResult(
        status="saved",
        reason="saved",
        run_state_path=run_state_path,
        sidecar_path=sidecar_path,
        run_state_ipc_input_hash=run_state_input_hash,
        run_state_ipc_output_hash=run_state_output_hash,
        sidecar_ipc_input_hash=sidecar_input_hash,
        sidecar_ipc_output_hash=sidecar_output_hash,
    )


def verify_run_state(
    *,
    run_dir: Path,
    run_id: str | None = None,
    manifest_ipc_output_hash: str | None = None,
) -> RunStateVerificationResult:
    """Verify run-state payload and referenced sidecars for one run directory."""

    run_state_path = _run_state_path(run_dir)
    if not run_state_path.exists():
        return RunStateVerificationResult(
            status="missing",
            reason="run-state-missing",
            run_state_path=run_state_path,
        )

    payload = _read_json_object(run_state_path)
    if payload is None:
        return RunStateVerificationResult(
            status="error",
            reason="run-state-parse-error",
            run_state_path=run_state_path,
        )

    if payload.get("schema_version") != SCHEMA_VERSION:
        return RunStateVerificationResult(
            status="mismatch",
            reason="run-state-schema-version-mismatch",
            run_state_path=run_state_path,
        )
    if payload.get("state_kind") != RUN_STATE_KIND:
        return RunStateVerificationResult(
            status="mismatch",
            reason="run-state-kind-mismatch",
            run_state_path=run_state_path,
        )

    stored_run_id = payload.get("run_id")
    if not isinstance(stored_run_id, str) or not stored_run_id.strip():
        return RunStateVerificationResult(
            status="mismatch",
            reason="run-state-run-id-missing",
            run_state_path=run_state_path,
        )
    if run_id is not None and stored_run_id != run_id:
        return RunStateVerificationResult(
            status="mismatch",
            reason="run-state-run-id-mismatch",
            run_state_path=run_state_path,
        )

    stored_manifest_hash = payload.get("manifest_ipc_output_hash")
    if not _is_sha256_hex(stored_manifest_hash):
        return RunStateVerificationResult(
            status="mismatch",
            reason="run-state-manifest-hash-invalid",
            run_state_path=run_state_path,
        )
    if (
        manifest_ipc_output_hash is not None
        and _is_sha256_hex(manifest_ipc_output_hash)
        and stored_manifest_hash != manifest_ipc_output_hash
    ):
        return RunStateVerificationResult(
            status="mismatch",
            reason="run-state-manifest-hash-mismatch",
            run_state_path=run_state_path,
        )

    stored_reach_hash = payload.get("reach_cache_ipc_output_hash")
    if stored_reach_hash is not None and not _is_sha256_hex(stored_reach_hash):
        return RunStateVerificationResult(
            status="mismatch",
            reason="run-state-reach-cache-hash-invalid",
            run_state_path=run_state_path,
        )

    raw_sidecars = payload.get("sidecars")
    if not isinstance(raw_sidecars, dict):
        return RunStateVerificationResult(
            status="mismatch",
            reason="run-state-sidecars-missing",
            run_state_path=run_state_path,
        )

    sidecars = _empty_sidecars()
    for slot in _all_sidecar_slots():
        if slot not in raw_sidecars:
            return RunStateVerificationResult(
                status="mismatch",
                reason=f"run-state-sidecar-slot-missing:{slot}",
                run_state_path=run_state_path,
            )
        raw_value = raw_sidecars[slot]
        if raw_value is None:
            sidecars[slot] = None
            continue
        coerced = _coerce_sidecar_ref(raw_value)
        if coerced is None:
            return RunStateVerificationResult(
                status="mismatch",
                reason=f"run-state-sidecar-ref-invalid:{slot}",
                run_state_path=run_state_path,
            )
        sidecars[slot] = coerced

    ipc = payload.get("ipc")
    if not isinstance(ipc, dict):
        return RunStateVerificationResult(
            status="mismatch",
            reason="run-state-ipc-block-missing",
            run_state_path=run_state_path,
        )

    stored_in = ipc.get("input_hash")
    stored_out = ipc.get("output_hash")
    input_payload = ipc.get("input_payload")
    output_payload = ipc.get("output_payload")
    if not _is_sha256_hex(stored_in) or not _is_sha256_hex(stored_out):
        return RunStateVerificationResult(
            status="mismatch",
            reason="run-state-ipc-hash-invalid",
            run_state_path=run_state_path,
        )
    if not isinstance(input_payload, dict) or not isinstance(output_payload, dict):
        return RunStateVerificationResult(
            status="mismatch",
            reason="run-state-ipc-payload-invalid",
            run_state_path=run_state_path,
        )

    expected_input_payload = _build_run_state_input_payload(
        run_id=stored_run_id,
        manifest_ipc_output_hash=str(stored_manifest_hash),
        reach_cache_ipc_output_hash=(
            str(stored_reach_hash) if _is_sha256_hex(stored_reach_hash) else None
        ),
        sidecars=sidecars,
    )
    expected_output_payload = _build_run_state_output_payload(sidecars=sidecars)
    if input_payload != expected_input_payload:
        return RunStateVerificationResult(
            status="mismatch",
            reason="run-state-ipc-input-payload-mismatch",
            run_state_path=run_state_path,
        )
    if output_payload != expected_output_payload:
        return RunStateVerificationResult(
            status="mismatch",
            reason="run-state-ipc-output-payload-mismatch",
            run_state_path=run_state_path,
        )

    expected_input_hash = compute_payload_hash(expected_input_payload)
    expected_output_hash = compute_output_hash(_json_dumps_canonical(expected_output_payload))
    if stored_in != expected_input_hash:
        return RunStateVerificationResult(
            status="mismatch",
            reason="run-state-input-hash-mismatch",
            run_state_path=run_state_path,
            run_state_ipc_input_hash=str(stored_in),
            run_state_ipc_output_hash=str(stored_out),
        )
    if stored_out != expected_output_hash:
        return RunStateVerificationResult(
            status="mismatch",
            reason="run-state-output-hash-mismatch",
            run_state_path=run_state_path,
            run_state_ipc_input_hash=str(stored_in),
            run_state_ipc_output_hash=str(stored_out),
        )

    for slot in _all_sidecar_slots():
        ref = sidecars[slot]
        if ref is None:
            continue
        sidecar_status, sidecar_reason = _verify_sidecar_payload(
            run_dir=run_dir,
            run_id=stored_run_id,
            slot=slot,
            sidecar_ref=ref,
        )
        if sidecar_status != "verified":
            return RunStateVerificationResult(
                status=sidecar_status,
                reason=sidecar_reason,
                run_state_path=run_state_path,
                run_state_ipc_input_hash=str(stored_in),
                run_state_ipc_output_hash=str(stored_out),
            )

    return RunStateVerificationResult(
        status="verified",
        reason="verified",
        run_state_path=run_state_path,
        run_state_ipc_input_hash=str(stored_in),
        run_state_ipc_output_hash=str(stored_out),
    )


def load_run_state(
    *,
    run_dir: Path,
    run_id: str | None = None,
    manifest_ipc_output_hash: str | None = None,
) -> RunStateLoadResult:
    """Load run-state payload for one run directory when verification succeeds."""

    verification = verify_run_state(
        run_dir=run_dir,
        run_id=run_id,
        manifest_ipc_output_hash=manifest_ipc_output_hash,
    )
    if verification.status != "verified":
        return RunStateLoadResult(
            status=verification.status,
            reason=verification.reason,
            run_state_path=verification.run_state_path,
            payload=None,
            run_state_ipc_input_hash=verification.run_state_ipc_input_hash,
            run_state_ipc_output_hash=verification.run_state_ipc_output_hash,
        )

    payload = _read_json_object(verification.run_state_path)
    if payload is None:
        return RunStateLoadResult(
            status="error",
            reason="run-state-parse-error",
            run_state_path=verification.run_state_path,
            payload=None,
            run_state_ipc_input_hash=verification.run_state_ipc_input_hash,
            run_state_ipc_output_hash=verification.run_state_ipc_output_hash,
        )

    return RunStateLoadResult(
        status="verified",
        reason="verified",
        run_state_path=verification.run_state_path,
        payload=payload,
        run_state_ipc_input_hash=verification.run_state_ipc_input_hash,
        run_state_ipc_output_hash=verification.run_state_ipc_output_hash,
    )
