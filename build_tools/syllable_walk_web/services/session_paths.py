"""Path helpers for walker IPC session and patch-output artifacts.

This module centralises filesystem path conventions for upcoming Patch A/B
session persistence features. It intentionally contains no IO side effects:
callers decide when to create directories or write files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

PatchKey = Literal["a", "b"]
PatchOutputKind = Literal["walks", "candidates", "selections", "package"]

PATCH_KEYS: tuple[PatchKey, ...] = ("a", "b")
PATCH_OUTPUT_KINDS: tuple[PatchOutputKind, ...] = (
    "walks",
    "candidates",
    "selections",
    "package",
)


def resolve_sessions_base(
    *,
    output_base: Path,
    configured_sessions_base: Path | None = None,
) -> Path:
    """Resolve the directory used for persisted walker session files.

    Resolution policy:

    1. Use ``configured_sessions_base`` when provided.
    2. Otherwise derive ``<output_base>/sessions``.

    Args:
        output_base: Active output root configured for this server instance.
        configured_sessions_base: Optional explicit sessions directory override.

    Returns:
        Normalized absolute path for session file storage.
    """

    if configured_sessions_base is not None:
        return configured_sessions_base.expanduser().resolve()
    return (output_base / "sessions").expanduser().resolve()


def run_ipc_dir(run_dir: Path) -> Path:
    """Return the canonical IPC subdirectory for one run directory."""

    return run_dir / "ipc"


def patch_output_sidecar_path(
    *,
    run_dir: Path,
    patch: str,
    artifact_kind: str,
    schema_version: int = 1,
) -> Path:
    """Build the canonical path for one patch-output sidecar artifact.

    Example::
        ``<run_dir>/ipc/patch_a_walks.v1.json``
    """

    patch_key = patch.lower()
    if patch_key not in PATCH_KEYS:
        raise ValueError(f"Invalid patch key: {patch}")
    if artifact_kind not in PATCH_OUTPUT_KINDS:
        raise ValueError(f"Invalid patch output kind: {artifact_kind}")
    if schema_version < 1:
        raise ValueError("schema_version must be >= 1")

    return run_ipc_dir(run_dir) / f"patch_{patch_key}_{artifact_kind}.v{schema_version}.json"


def session_file_path(
    *,
    session_id: str,
    output_base: Path,
    configured_sessions_base: Path | None = None,
) -> Path:
    """Build the canonical filename for one saved dual-patch session.

    Args:
        session_id: Opaque session identifier.
        output_base: Active output root configured for this server instance.
        configured_sessions_base: Optional explicit sessions directory override.

    Returns:
        Absolute path to ``<sessions_base>/<session_id>.json``.
    """

    cleaned = session_id.strip()
    if not cleaned:
        raise ValueError("session_id must not be blank")

    sessions_base = resolve_sessions_base(
        output_base=output_base,
        configured_sessions_base=configured_sessions_base,
    )
    return sessions_base / f"{cleaned}.json"
