"""Shared stateless helper functions for walker API handlers.

This module contains request-coercion and comparison helpers that do not need
filesystem access or mutation side effects. It exists to reduce the size and
cognitive load of ``api/walker.py`` while preserving existing endpoint
contracts.
"""

from __future__ import annotations

import re
from typing import Any

from build_tools.syllable_walk_web.state import PatchState, ServerState

_MISSING = object()
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def is_sha256_hex(value: Any) -> bool:
    """Return ``True`` when value is a lowercase 64-character SHA-256 hash."""

    return isinstance(value, str) and _SHA256_RE.match(value) is not None


def reach_cache_verification_from_read(
    *,
    cache_status: str | None,
    cache_message: str | None,
    input_hash: str | None,
    output_hash: str | None,
) -> tuple[str | None, str | None]:
    """Map reach-cache read outcomes to verification status and reason.

    This preserves the user-facing semantics consumed by the Walker UI:
    - cache hit + valid hashes => ``verified``
    - cache hit + missing hashes => ``error``
    - invalid/miss/none/error map to deterministic reason strings
    """

    if cache_status is None:
        return None, None
    if cache_status == "hit":
        if is_sha256_hex(input_hash) and is_sha256_hex(output_hash):
            return "verified", "cache-hit-hashes-match"
        return "error", "cache-hit-missing-hashes"
    if cache_status == "invalid":
        return "mismatch", cache_message or "cache-invalid"
    if cache_status == "error":
        return "error", cache_message or "cache-read-error"
    if cache_status == "none":
        return "missing", "manifest-ipc-missing"
    if cache_status == "miss":
        return "missing", "cache-miss"
    return "error", "cache-status-unknown"


def resolve_patch_state(
    body: dict[str, Any],
    state: ServerState,
) -> tuple[str, PatchState] | None:
    """Resolve request ``patch`` to ``("a"|"b", PatchState)``.

    Args:
        body: Request payload that may include ``patch``.
        state: Global server state containing patch A and patch B.

    Returns:
        Tuple of ``(patch_key, patch_state)`` when valid; otherwise ``None``.
    """

    raw_patch = body.get("patch", "a")
    if not isinstance(raw_patch, str):
        return None

    patch_key = raw_patch.lower()
    if patch_key not in ("a", "b"):
        return None

    patch = state.patch_a if patch_key == "a" else state.patch_b
    return patch_key, patch


def coerce_optional_constraint_int(
    body: dict[str, Any],
    field_name: str,
    *,
    default: int,
) -> tuple[int | None, str | None]:
    """Coerce one optional integer constraint from request payload.

    Semantics:
    - Missing field: use provided ``default``.
    - Explicit ``null``: disable this constraint (return ``None``).
    - Provided value: coerce to ``int`` or return deterministic error.
    """

    raw = body.get(field_name, _MISSING)
    if raw is _MISSING:
        return default, None
    if raw is None:
        return None, None
    try:
        return int(raw), None
    except (TypeError, ValueError):
        return None, f"{field_name} must be an integer or null."


def compute_patch_comparison(
    *,
    patch_a_manifest_hash: str | None,
    patch_b_manifest_hash: str | None,
) -> dict[str, str]:
    """Compute Patch A/B manifest-hash relation and policy signal."""

    if not is_sha256_hex(patch_a_manifest_hash) or not is_sha256_hex(patch_b_manifest_hash):
        return {
            "corpus_hash_relation": "unknown",
            "policy": "none",
            "reason": "manifest-hash-unavailable",
        }
    if patch_a_manifest_hash == patch_b_manifest_hash:
        return {
            "corpus_hash_relation": "same",
            "policy": "none",
            "reason": "patch-manifest-hashes-match",
        }
    return {
        "corpus_hash_relation": "different",
        "policy": "warn",
        "reason": "patch-manifest-hashes-differ",
    }
