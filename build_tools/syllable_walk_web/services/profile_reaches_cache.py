"""IPC-backed cache for precomputed walker profile reaches.

This module provides a deterministic, run-directory-local cache for the
profile reach tables computed during ``/api/walker/load-corpus``.

Cache goals:
- Avoid recomputing profile reaches when corpus + walker settings are unchanged.
- Keep each run directory self-contained as the source of truth.
- Use pipeworks-ipc hashes so cache validity is explicit and auditable.

Cache file location:
``<run_dir>/ipc/walker_profile_reaches.v1.json``
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

from build_tools.syllable_walk.profiles import WALK_PROFILES
from build_tools.syllable_walk.reach import DEFAULT_REACH_THRESHOLD, ReachResult

CACHE_SCHEMA_VERSION = 1
CACHE_KIND = "walker_profile_reaches"
CACHE_FILENAME = "walker_profile_reaches.v1.json"
CACHE_SCHEMA_ID = "urn:pipeworks:schema:walker-profile-reaches-cache:v1"
MANIFEST_FILENAME = "manifest.json"
PROFILE_NAMES = ("clerical", "dialect", "goblin", "ritual")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class CacheReadResult:
    """Result of attempting to read and validate a profile-reach cache.

    Attributes:
        status: One of ``hit``, ``miss``, ``invalid``, ``error``, ``none``.
            ``none`` means cache is ineligible because required manifest IPC
            metadata is missing.
        profile_reaches: Populated only for ``status == \"hit\"``.
        message: Optional short diagnostic used for debugging and tests.
    """

    status: str
    profile_reaches: dict[str, ReachResult] | None = None
    message: str | None = None
    ipc_input_hash: str | None = None
    ipc_output_hash: str | None = None


@dataclass(frozen=True)
class ManifestIPCInfo:
    """Canonical IPC fields extracted from one run's ``manifest.json``."""

    manifest_version: int
    input_hash: str
    output_hash: str


def cache_path(run_dir: Path) -> Path:
    """Return canonical cache path for one run directory."""

    return run_dir / "ipc" / CACHE_FILENAME


def read_cached_profile_reach_hashes(run_dir: Path) -> tuple[str | None, str | None]:
    """Return cache IPC hashes from disk, if present and valid.

    This helper is intentionally lightweight and tolerant: malformed or missing
    cache files simply return ``(None, None)``.
    """

    path = cache_path(run_dir)
    if not path.exists():
        return None, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, None
    if not isinstance(payload, dict):
        return None, None
    ipc = payload.get("ipc")
    if not isinstance(ipc, dict):
        return None, None

    input_hash_raw = ipc.get("input_hash")
    output_hash_raw = ipc.get("output_hash")
    input_hash = str(input_hash_raw) if _is_sha256_hex(input_hash_raw) else None
    output_hash = str(output_hash_raw) if _is_sha256_hex(output_hash_raw) else None
    return input_hash, output_hash


def _utc_now_iso() -> str:
    """Return UTC ISO timestamp with second precision."""

    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_sha256_hex(value: Any) -> bool:
    """Return ``True`` when value is a 64-char lowercase SHA-256 hex string."""

    return isinstance(value, str) and _SHA256_RE.match(value) is not None


def _resolve_pipeworks_ipc_version() -> str:
    """Resolve installed ``pipeworks-ipc`` version for cache metadata."""

    try:
        return version("pipeworks-ipc")
    except PackageNotFoundError:
        return "unknown"


def _load_manifest_ipc_info(run_dir: Path) -> ManifestIPCInfo | None:
    """Read manifest IPC metadata required to key cache validity.

    Returns ``None`` when manifest file or required IPC hash fields are missing
    or malformed.
    """

    manifest_path = run_dir / MANIFEST_FILENAME
    if not manifest_path.exists():
        return None

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    manifest_version = payload.get("manifest_version")
    ipc = payload.get("ipc")
    if not isinstance(manifest_version, int) or not isinstance(ipc, dict):
        return None

    input_hash_raw = ipc.get("input_hash")
    output_hash_raw = ipc.get("output_hash")
    if not _is_sha256_hex(input_hash_raw) or not _is_sha256_hex(output_hash_raw):
        return None
    input_hash = str(input_hash_raw)
    output_hash = str(output_hash_raw)

    return ManifestIPCInfo(
        manifest_version=manifest_version,
        input_hash=input_hash,
        output_hash=output_hash,
    )


def _build_graph_settings(walker: Any) -> dict[str, Any]:
    """Build deterministic graph-setting payload from a walker instance."""

    feature_costs_raw = getattr(walker, "feature_costs", {}) or {}
    feature_costs: dict[str, float] = {}
    for key in sorted(feature_costs_raw):
        feature_costs[str(key)] = float(feature_costs_raw[key])

    return {
        "walker_impl": f"{walker.__class__.__module__}.{walker.__class__.__name__}",
        "max_neighbor_distance": int(getattr(walker, "max_neighbor_distance", 3)),
        "inertia_cost": float(getattr(walker, "inertia_cost", 0.5)),
        "feature_costs": feature_costs,
    }


def _build_reach_settings() -> dict[str, Any]:
    """Build deterministic reach-setting payload from named walk profiles."""

    profiles: dict[str, dict[str, Any]] = {}
    for name in PROFILE_NAMES:
        profile = WALK_PROFILES[name]
        profiles[name] = {
            "max_flips": int(profile.max_flips),
            "temperature": float(profile.temperature),
            "frequency_weight": float(profile.frequency_weight),
        }

    return {
        "threshold": float(DEFAULT_REACH_THRESHOLD),
        "profiles": profiles,
    }


def _build_input_payload(
    *,
    run_id: str,
    manifest_output_hash: str,
    graph_settings: dict[str, Any],
    reach_settings: dict[str, Any],
) -> dict[str, Any]:
    """Build canonical IPC input payload for cache-key hashing."""

    return {
        "run_id": run_id,
        "manifest_ipc_output_hash": manifest_output_hash,
        "graph_settings": graph_settings,
        "reach_settings": reach_settings,
    }


def _build_output_payload(profile_reaches: dict[str, ReachResult]) -> dict[str, Any]:
    """Build canonical IPC output payload from full reach results."""

    profiles: dict[str, dict[str, int]] = {}
    for name in PROFILE_NAMES:
        result = profile_reaches.get(name)
        if result is None:
            raise ValueError(f"Missing required profile reach: {name}")
        profiles[name] = {
            "reach": int(result.reach),
            "total": int(result.total),
            "unique_reachable": int(result.unique_reachable),
        }
    return {"profiles": profiles}


def _json_dumps_canonical(payload: dict[str, Any]) -> str:
    """Serialize JSON deterministically for stable hashing."""

    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _encode_profile_reaches(profile_reaches: dict[str, ReachResult]) -> dict[str, Any]:
    """Convert ReachResult objects to JSON-serializable records."""

    encoded: dict[str, Any] = {}
    for name in PROFILE_NAMES:
        result = profile_reaches.get(name)
        if result is None:
            raise ValueError(f"Missing required profile reach: {name}")

        reachable_indices = [
            [int(idx), int(count)] for idx, count in tuple(result.reachable_indices)
        ]
        encoded[name] = {
            "profile_name": str(result.profile_name),
            "reach": int(result.reach),
            "total": int(result.total),
            "threshold": float(result.threshold),
            "max_flips": int(result.max_flips),
            "temperature": float(result.temperature),
            "frequency_weight": float(result.frequency_weight),
            "computation_ms": float(result.computation_ms),
            "unique_reachable": int(result.unique_reachable),
            "reachable_indices": reachable_indices,
        }
    return encoded


def _decode_profile_reaches(payload: Any) -> dict[str, ReachResult] | None:
    """Convert cached JSON records back to ReachResult objects."""

    if not isinstance(payload, dict):
        return None
    if set(payload.keys()) != set(PROFILE_NAMES):
        return None

    decoded: dict[str, ReachResult] = {}
    for name in PROFILE_NAMES:
        record = payload.get(name)
        if not isinstance(record, dict):
            return None

        try:
            raw_entries = record.get("reachable_indices", [])
            if not isinstance(raw_entries, list):
                return None

            reachable_indices: list[tuple[int, int]] = []
            for entry in raw_entries:
                if (
                    not isinstance(entry, list)
                    or len(entry) != 2
                    or not isinstance(entry[0], int)
                    or not isinstance(entry[1], int)
                ):
                    return None
                reachable_indices.append((entry[0], entry[1]))

            decoded[name] = ReachResult(
                profile_name=str(record["profile_name"]),
                reach=int(record["reach"]),
                total=int(record["total"]),
                threshold=float(record["threshold"]),
                max_flips=int(record["max_flips"]),
                temperature=float(record["temperature"]),
                frequency_weight=float(record["frequency_weight"]),
                computation_ms=float(record["computation_ms"]),
                unique_reachable=int(record.get("unique_reachable", 0)),
                reachable_indices=tuple(reachable_indices),
            )
        except (KeyError, TypeError, ValueError):
            return None

    return decoded


def load_cached_profile_reaches(
    *,
    run_dir: Path,
    run_id: str,
    walker: Any,
) -> CacheReadResult:
    """Read and validate cached profile reaches for a run.

    Validation gates:
    - manifest IPC metadata is present (hash authority)
    - cache file exists and parses
    - cache input payload/hash matches current run + walker settings
    - cache output payload/hash is internally consistent
    """

    manifest_info = _load_manifest_ipc_info(run_dir)
    if manifest_info is None:
        return CacheReadResult(status="none", message="manifest-ipc-missing")

    path = cache_path(run_dir)
    if not path.exists():
        return CacheReadResult(status="miss", message="cache-file-missing")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return CacheReadResult(status="invalid", message="cache-json-invalid")

    if not isinstance(payload, dict):
        return CacheReadResult(status="invalid", message="cache-root-not-object")

    graph_settings = _build_graph_settings(walker)
    reach_settings = _build_reach_settings()
    expected_input_payload = _build_input_payload(
        run_id=run_id,
        manifest_output_hash=manifest_info.output_hash,
        graph_settings=graph_settings,
        reach_settings=reach_settings,
    )
    expected_input_hash = compute_payload_hash(expected_input_payload)

    try:
        if payload.get("schema_version") != CACHE_SCHEMA_VERSION:
            return CacheReadResult(status="invalid", message="schema-version-mismatch")
        if payload.get("cache_kind") != CACHE_KIND:
            return CacheReadResult(status="invalid", message="cache-kind-mismatch")
        if payload.get("run_id") != run_id:
            return CacheReadResult(status="invalid", message="run-id-mismatch")

        manifest_block = payload.get("manifest")
        if not isinstance(manifest_block, dict):
            return CacheReadResult(status="invalid", message="manifest-block-missing")
        if manifest_block.get("ipc_output_hash") != manifest_info.output_hash:
            return CacheReadResult(status="invalid", message="manifest-output-hash-mismatch")
        if manifest_block.get("ipc_input_hash") != manifest_info.input_hash:
            return CacheReadResult(status="invalid", message="manifest-input-hash-mismatch")

        ipc_block = payload.get("ipc")
        if not isinstance(ipc_block, dict):
            return CacheReadResult(status="invalid", message="ipc-block-missing")
        if ipc_block.get("input_payload") != expected_input_payload:
            return CacheReadResult(status="invalid", message="input-payload-mismatch")
        if ipc_block.get("input_hash") != expected_input_hash:
            return CacheReadResult(status="invalid", message="input-hash-mismatch")

        decoded_reaches = _decode_profile_reaches(payload.get("profile_reaches"))
        if decoded_reaches is None:
            return CacheReadResult(status="invalid", message="profile-reaches-invalid")

        expected_output_payload = _build_output_payload(decoded_reaches)
        if ipc_block.get("output_payload") != expected_output_payload:
            return CacheReadResult(status="invalid", message="output-payload-mismatch")

        expected_output_hash = compute_output_hash(_json_dumps_canonical(expected_output_payload))
        if ipc_block.get("output_hash") != expected_output_hash:
            return CacheReadResult(status="invalid", message="output-hash-mismatch")

        output_hash_raw = ipc_block.get("output_hash")
        output_hash = str(output_hash_raw) if _is_sha256_hex(output_hash_raw) else None
        return CacheReadResult(
            status="hit",
            profile_reaches=decoded_reaches,
            ipc_input_hash=expected_input_hash,
            ipc_output_hash=output_hash,
        )
    except Exception as exc:  # pragma: no cover - defensive catch-all
        return CacheReadResult(status="error", message=str(exc))


def write_cached_profile_reaches(
    *,
    run_dir: Path,
    run_id: str,
    walker: Any,
    profile_reaches: dict[str, ReachResult],
) -> bool:
    """Write deterministic profile-reach cache for a run.

    Returns ``True`` when written successfully, else ``False``.
    """

    manifest_info = _load_manifest_ipc_info(run_dir)
    if manifest_info is None:
        return False

    try:
        graph_settings = _build_graph_settings(walker)
        reach_settings = _build_reach_settings()
        input_payload = _build_input_payload(
            run_id=run_id,
            manifest_output_hash=manifest_info.output_hash,
            graph_settings=graph_settings,
            reach_settings=reach_settings,
        )
        output_payload = _build_output_payload(profile_reaches)

        ipc_input_hash = compute_payload_hash(input_payload)
        ipc_output_hash = compute_output_hash(_json_dumps_canonical(output_payload))

        payload: dict[str, Any] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": CACHE_SCHEMA_ID,
            "title": "Walker Profile Reaches Cache (v1)",
            "description": (
                "Run-directory IPC cache artifact for precomputed initial "
                "profile tables used by syllable_walk_web."
            ),
            "schema_version": CACHE_SCHEMA_VERSION,
            "cache_kind": CACHE_KIND,
            "run_id": run_id,
            "created_at_utc": _utc_now_iso(),
            "manifest": {
                "relative_path": MANIFEST_FILENAME,
                "manifest_version": manifest_info.manifest_version,
                "ipc_input_hash": manifest_info.input_hash,
                "ipc_output_hash": manifest_info.output_hash,
            },
            "graph_settings": graph_settings,
            "reach_settings": reach_settings,
            "ipc": {
                "version": 1,
                "library": "pipeworks-ipc",
                "library_ref": f"pipeworks-ipc-v{_resolve_pipeworks_ipc_version()}",
                "input_hash": ipc_input_hash,
                "output_hash": ipc_output_hash,
                "input_payload": input_payload,
                "output_payload": output_payload,
            },
            "profile_reaches": _encode_profile_reaches(profile_reaches),
        }

        target = cache_path(run_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp.replace(target)
        return True
    except (OSError, TypeError, ValueError):
        return False
