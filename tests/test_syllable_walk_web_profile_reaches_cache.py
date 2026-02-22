"""Tests for walker profile-reach IPC cache service."""

from __future__ import annotations

import json
from pathlib import Path

from build_tools.syllable_walk.reach import ReachResult
from build_tools.syllable_walk_web.services import profile_reaches_cache


class _FakeWalker:
    """Minimal walker-like object exposing cache-keyed graph settings."""

    max_neighbor_distance = 3
    inertia_cost = 0.5
    feature_costs = {
        "contains_fricative": 0.7,
        "contains_liquid": 0.3,
        "contains_nasal": 0.3,
    }


def _write_manifest(
    run_dir: Path,
    *,
    manifest_version: int = 1,
    ipc_input_hash: str = "a" * 64,
    ipc_output_hash: str = "b" * 64,
) -> None:
    """Write minimal manifest with IPC fields used by cache service."""

    payload = {
        "manifest_version": manifest_version,
        "ipc": {
            "input_hash": ipc_input_hash,
            "output_hash": ipc_output_hash,
        },
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")


def _make_profile_result(name: str, n: int) -> ReachResult:
    """Build deterministic ReachResult sample for one profile."""

    return ReachResult(
        profile_name=name,
        reach=10 + n,
        total=100,
        threshold=0.001,
        max_flips=1 + (n % 3),
        temperature=0.3 + n,
        frequency_weight=float(-n),
        computation_ms=1.5 + n,
        unique_reachable=20 + n,
        reachable_indices=((n, 5 + n), (n + 1, 3 + n)),
    )


def _all_profile_reaches() -> dict[str, ReachResult]:
    """Build full named-profile reach mapping required by cache schema."""

    names = ["clerical", "dialect", "goblin", "ritual"]
    return {name: _make_profile_result(name, idx) for idx, name in enumerate(names)}


def test_cache_path_uses_run_local_ipc_directory(tmp_path: Path) -> None:
    """Cache should live under run-local ipc/ folder."""

    run_dir = tmp_path / "20260222_155258_nltk"
    assert profile_reaches_cache.cache_path(run_dir) == (
        run_dir / "ipc" / "walker_profile_reaches.v1.json"
    )


def test_load_returns_none_status_when_manifest_ipc_missing(tmp_path: Path) -> None:
    """Cache loading is ineligible without valid manifest IPC metadata."""

    run_dir = tmp_path / "20260222_155258_nltk"
    run_dir.mkdir(parents=True)

    result = profile_reaches_cache.load_cached_profile_reaches(
        run_dir=run_dir,
        run_id=run_dir.name,
        walker=_FakeWalker(),
    )

    assert result.status == "none"
    assert result.profile_reaches is None
    assert result.ipc_input_hash is None
    assert result.ipc_output_hash is None


def test_load_returns_miss_when_cache_file_absent(tmp_path: Path) -> None:
    """With valid manifest metadata but no cache file, status should be miss."""

    run_dir = tmp_path / "20260222_155258_nltk"
    _write_manifest(run_dir)

    result = profile_reaches_cache.load_cached_profile_reaches(
        run_dir=run_dir,
        run_id=run_dir.name,
        walker=_FakeWalker(),
    )

    assert result.status == "miss"
    assert result.profile_reaches is None
    assert result.ipc_input_hash is None
    assert result.ipc_output_hash is None


def test_write_returns_false_when_manifest_ipc_invalid(tmp_path: Path) -> None:
    """Write should fail cleanly when manifest hashes are unavailable."""

    run_dir = tmp_path / "20260222_155258_nltk"
    run_dir.mkdir(parents=True)
    # Missing output hash shape makes manifest ineligible.
    (run_dir / "manifest.json").write_text(
        '{"manifest_version":1,"ipc":{"input_hash":"abc"}}',
        encoding="utf-8",
    )

    ok = profile_reaches_cache.write_cached_profile_reaches(
        run_dir=run_dir,
        run_id=run_dir.name,
        walker=_FakeWalker(),
        profile_reaches=_all_profile_reaches(),
    )

    assert ok is False


def test_write_then_load_returns_hit(tmp_path: Path) -> None:
    """Round-trip write/read should produce a cache hit with parsed reaches."""

    run_dir = tmp_path / "20260222_155258_nltk"
    _write_manifest(run_dir)

    wrote = profile_reaches_cache.write_cached_profile_reaches(
        run_dir=run_dir,
        run_id=run_dir.name,
        walker=_FakeWalker(),
        profile_reaches=_all_profile_reaches(),
    )
    assert wrote is True
    assert profile_reaches_cache.cache_path(run_dir).exists()

    result = profile_reaches_cache.load_cached_profile_reaches(
        run_dir=run_dir,
        run_id=run_dir.name,
        walker=_FakeWalker(),
    )

    assert result.status == "hit"
    assert result.profile_reaches is not None
    assert isinstance(result.ipc_input_hash, str)
    assert len(result.ipc_input_hash) == 64
    assert isinstance(result.ipc_output_hash, str)
    assert len(result.ipc_output_hash) == 64
    assert set(result.profile_reaches.keys()) == {"clerical", "dialect", "goblin", "ritual"}
    assert result.profile_reaches["dialect"].profile_name == "dialect"


def test_read_cached_profile_reach_hashes_returns_none_when_missing(tmp_path: Path) -> None:
    """Hash helper should return empty tuple for missing cache file."""

    run_dir = tmp_path / "20260222_155258_nltk"
    run_dir.mkdir(parents=True)
    assert profile_reaches_cache.read_cached_profile_reach_hashes(run_dir) == (None, None)


def test_read_cached_profile_reach_hashes_returns_hashes_after_write(tmp_path: Path) -> None:
    """Hash helper should expose IPC hashes from the written cache payload."""

    run_dir = tmp_path / "20260222_155258_nltk"
    _write_manifest(run_dir)
    assert profile_reaches_cache.write_cached_profile_reaches(
        run_dir=run_dir,
        run_id=run_dir.name,
        walker=_FakeWalker(),
        profile_reaches=_all_profile_reaches(),
    )

    in_hash, out_hash = profile_reaches_cache.read_cached_profile_reach_hashes(run_dir)
    assert isinstance(in_hash, str) and len(in_hash) == 64
    assert isinstance(out_hash, str) and len(out_hash) == 64


def test_read_cached_profile_reach_hashes_returns_none_for_malformed_json(tmp_path: Path) -> None:
    """Malformed cache JSON should be tolerated and reported as empty hashes."""

    run_dir = tmp_path / "20260222_155258_nltk"
    cache_file = profile_reaches_cache.cache_path(run_dir)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("{bad-json", encoding="utf-8")

    assert profile_reaches_cache.read_cached_profile_reach_hashes(run_dir) == (None, None)


def test_read_cached_profile_reach_hashes_returns_none_when_payload_not_object(
    tmp_path: Path,
) -> None:
    """Non-object cache payload should return empty hash tuple."""

    run_dir = tmp_path / "20260222_155258_nltk"
    cache_file = profile_reaches_cache.cache_path(run_dir)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("[]", encoding="utf-8")

    assert profile_reaches_cache.read_cached_profile_reach_hashes(run_dir) == (None, None)


def test_read_cached_profile_reach_hashes_returns_none_when_ipc_block_missing(
    tmp_path: Path,
) -> None:
    """Cache payload without dict-valued ipc block should return empty hashes."""

    run_dir = tmp_path / "20260222_155258_nltk"
    cache_file = profile_reaches_cache.cache_path(run_dir)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"ipc": []}), encoding="utf-8")

    assert profile_reaches_cache.read_cached_profile_reach_hashes(run_dir) == (None, None)


def test_load_returns_invalid_when_manifest_output_hash_changes(tmp_path: Path) -> None:
    """Manifest IPC output hash drift should invalidate existing cache."""

    run_dir = tmp_path / "20260222_155258_nltk"
    _write_manifest(run_dir, ipc_output_hash="b" * 64)
    assert profile_reaches_cache.write_cached_profile_reaches(
        run_dir=run_dir,
        run_id=run_dir.name,
        walker=_FakeWalker(),
        profile_reaches=_all_profile_reaches(),
    )

    # Simulate a changed pipeline output manifest hash for the same run.
    _write_manifest(run_dir, ipc_output_hash="c" * 64)

    result = profile_reaches_cache.load_cached_profile_reaches(
        run_dir=run_dir,
        run_id=run_dir.name,
        walker=_FakeWalker(),
    )

    assert result.status == "invalid"


def test_load_returns_invalid_when_cache_json_is_malformed(tmp_path: Path) -> None:
    """Malformed cache file should never crash load path."""

    run_dir = tmp_path / "20260222_155258_nltk"
    _write_manifest(run_dir)
    cache_file = profile_reaches_cache.cache_path(run_dir)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("{invalid-json", encoding="utf-8")

    result = profile_reaches_cache.load_cached_profile_reaches(
        run_dir=run_dir,
        run_id=run_dir.name,
        walker=_FakeWalker(),
    )

    assert result.status == "invalid"


def test_load_returns_invalid_when_cache_is_tampered(tmp_path: Path) -> None:
    """Tampering with IPC hashes should invalidate cache deterministically."""

    run_dir = tmp_path / "20260222_155258_nltk"
    _write_manifest(run_dir)
    assert profile_reaches_cache.write_cached_profile_reaches(
        run_dir=run_dir,
        run_id=run_dir.name,
        walker=_FakeWalker(),
        profile_reaches=_all_profile_reaches(),
    )

    cache_file = profile_reaches_cache.cache_path(run_dir)
    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    payload["ipc"]["input_hash"] = "d" * 64
    cache_file.write_text(json.dumps(payload), encoding="utf-8")

    result = profile_reaches_cache.load_cached_profile_reaches(
        run_dir=run_dir,
        run_id=run_dir.name,
        walker=_FakeWalker(),
    )

    assert result.status == "invalid"
