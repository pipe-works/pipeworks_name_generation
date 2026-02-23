"""Typed payload contracts for Walker web API handlers.

These ``TypedDict`` models define the JSON boundary for request handlers in
``build_tools/syllable_walk_web/api``. They are intentionally lightweight:
runtime behavior remains unchanged, while handler signatures can now express
their response contracts explicitly.
"""

from __future__ import annotations

from typing import Any, Required, TypedDict


class ErrorResponse(TypedDict):
    """Standard error payload returned by Walker API handlers."""

    error: str


class ErrorWithLockResponse(ErrorResponse, total=False):
    """Error payload variant that includes lock conflict metadata."""

    lock_status: str
    lock: dict[str, Any] | None
    active_session_id: str


class SessionSavePatchStatus(TypedDict):
    """Per-patch status block used in save-session responses."""

    status: str | None
    reason: str | None


class SessionSaveResponse(TypedDict):
    """Successful ``/api/walker/save-session`` response payload."""

    status: str
    reason: str
    session_id: str | None
    session_path: str | None
    sessions_base: str
    patch_a: SessionSavePatchStatus
    patch_b: SessionSavePatchStatus
    ipc_input_hash: str | None
    ipc_output_hash: str | None
    root_session_id: str | None
    parent_session_id: str | None
    revision: int | None


class SessionListEntry(TypedDict):
    """One serialized entry returned by ``/api/walker/sessions``."""

    session_id: str
    created_at_utc: str | None
    label: str | None
    patch_a_run_id: str | None
    patch_b_run_id: str | None
    verification_status: str
    verification_reason: str
    session_path: str
    root_session_id: str | None
    parent_session_id: str | None
    revision: int | None
    lock_status: str | None
    lock: dict[str, Any] | None


class SessionsResponse(TypedDict):
    """Successful ``/api/walker/sessions`` response payload."""

    sessions: list[SessionListEntry]


class RestorePatchArtifactsResult(TypedDict, total=False):
    """Run-state restoration result for one patch during session load."""

    status: Required[str]
    reason: Required[str]
    restored: Required[bool]
    restored_kinds: Required[list[str]]
    run_state_ipc_input_hash: str | None
    run_state_ipc_output_hash: str | None


class SessionLoadPatchResult(TypedDict, total=False):
    """Per-patch block in ``/api/walker/load-session`` response payloads."""

    loaded: Required[bool]
    restored: Required[bool]
    verification_status: Required[str]
    verification_reason: Required[str]
    run_id: str | None
    restored_kinds: list[str]
    status: str | None
    source: str | None
    syllable_count: int | None
    run_state_ipc_input_hash: str | None
    run_state_ipc_output_hash: str | None


class SessionLockPayload(TypedDict):
    """Session lock status block returned by load-session endpoint."""

    status: str
    reason: str
    lock: dict[str, Any] | None


class SessionLoadResponse(TypedDict, total=False):
    """Successful or degraded ``/api/walker/load-session`` response payload."""

    status: Required[str]
    reason: Required[str]
    session_id: Required[str]
    ipc_input_hash: Required[str | None]
    ipc_output_hash: Required[str | None]
    patch_a: Required[SessionLoadPatchResult]
    patch_b: Required[SessionLoadPatchResult]
    recovered_from_stale_session: bool
    session_lock: SessionLockPayload


class RebuildReachCacheResponse(TypedDict):
    """Successful ``/api/walker/rebuild-reach-cache`` response payload."""

    patch: str
    run_id: str
    status: str
    ipc_input_hash: str | None
    ipc_output_hash: str | None
    verification_status: str | None
    verification_reason: str | None


class SessionLockStatusResponse(TypedDict):
    """Successful lock heartbeat/release response payload."""

    status: str
    reason: str
    lock: dict[str, Any] | None


class WalkResponse(TypedDict):
    """Successful ``/api/walker/walk`` response payload."""

    patch: str
    walks: list[dict[str, Any]]


class ReachSyllableRow(TypedDict):
    """One reachability row for ``/api/walker/reach-syllables``."""

    syllable: str
    frequency: int
    reachability: int


class ReachSyllablesResponse(TypedDict):
    """Successful ``/api/walker/reach-syllables`` response payload."""

    profile: str
    reach: int
    total: int
    unique_reachable: int
    syllables: list[ReachSyllableRow]


class CombineResponse(TypedDict):
    """Successful ``/api/walker/combine`` response payload."""

    patch: str
    generated: int
    unique: int
    duplicates: int
    syllables: int | list[int]
    source: str | None


class SelectResponse(TypedDict):
    """Successful ``/api/walker/select`` response payload."""

    patch: str
    name_class: str
    mode: str
    count: int
    requested: int
    names: list[str]


class ExportResponse(TypedDict):
    """Successful ``/api/walker/export`` response payload."""

    patch: str
    count: int
    names: list[str]


class AnalysisResponse(TypedDict):
    """Successful ``/api/walker/analysis/<patch>`` response payload."""

    patch: str
    analysis: dict[str, Any]
