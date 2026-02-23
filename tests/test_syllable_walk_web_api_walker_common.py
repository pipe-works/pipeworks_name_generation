"""Unit tests for shared walker API common helpers."""

from build_tools.syllable_walk_web.api.walker_common import (
    coerce_optional_constraint_int,
    compute_patch_comparison,
    is_sha256_hex,
    reach_cache_verification_from_read,
    resolve_patch_state,
)
from build_tools.syllable_walk_web.state import ServerState


def test_is_sha256_hex_accepts_only_canonical_lowercase_hashes() -> None:
    """Hash validator should accept lowercase 64-char hex and reject other forms."""

    assert is_sha256_hex("a" * 64) is True
    assert is_sha256_hex("A" * 64) is False
    assert is_sha256_hex("a" * 63) is False
    assert is_sha256_hex("g" * 64) is False
    assert is_sha256_hex(None) is False


def test_reach_cache_verification_mapping_matches_contract() -> None:
    """Reach-cache status mapping should preserve existing UI-facing semantics."""

    assert reach_cache_verification_from_read(
        cache_status=None,
        cache_message=None,
        input_hash=None,
        output_hash=None,
    ) == (None, None)
    assert reach_cache_verification_from_read(
        cache_status="hit",
        cache_message=None,
        input_hash="a" * 64,
        output_hash="b" * 64,
    ) == ("verified", "cache-hit-hashes-match")
    assert reach_cache_verification_from_read(
        cache_status="hit",
        cache_message=None,
        input_hash=None,
        output_hash="b" * 64,
    ) == ("error", "cache-hit-missing-hashes")
    assert reach_cache_verification_from_read(
        cache_status="invalid",
        cache_message="cache-corrupt",
        input_hash=None,
        output_hash=None,
    ) == ("mismatch", "cache-corrupt")
    assert reach_cache_verification_from_read(
        cache_status="miss",
        cache_message=None,
        input_hash=None,
        output_hash=None,
    ) == ("missing", "cache-miss")


def test_resolve_patch_state_accepts_a_and_b_only() -> None:
    """Patch resolver should normalize valid keys and reject invalid inputs."""

    state = ServerState()
    resolved_default = resolve_patch_state({}, state)
    assert resolved_default is not None
    patch_key_default, patch_default = resolved_default
    assert patch_key_default == "a"
    assert patch_default is state.patch_a

    resolved_b = resolve_patch_state({"patch": "B"}, state)
    assert resolved_b is not None
    patch_key_b, patch_b = resolved_b
    assert patch_key_b == "b"
    assert patch_b is state.patch_b

    assert resolve_patch_state({"patch": "c"}, state) is None
    assert resolve_patch_state({"patch": 123}, state) is None


def test_coerce_optional_constraint_int_handles_missing_null_and_invalid() -> None:
    """Constraint coercion should preserve default/null/invalid behavior."""

    value_missing, err_missing = coerce_optional_constraint_int(
        {},
        "neighbor_limit",
        default=10,
    )
    assert value_missing == 10
    assert err_missing is None

    value_null, err_null = coerce_optional_constraint_int(
        {"neighbor_limit": None},
        "neighbor_limit",
        default=10,
    )
    assert value_null is None
    assert err_null is None

    value_cast, err_cast = coerce_optional_constraint_int(
        {"neighbor_limit": "7"},
        "neighbor_limit",
        default=10,
    )
    assert value_cast == 7
    assert err_cast is None

    value_invalid, err_invalid = coerce_optional_constraint_int(
        {"neighbor_limit": "abc"},
        "neighbor_limit",
        default=10,
    )
    assert value_invalid is None
    assert err_invalid == "neighbor_limit must be an integer or null."


def test_compute_patch_comparison_reports_unknown_same_and_different() -> None:
    """Patch comparison should return canonical relation/policy/reason triples."""

    assert compute_patch_comparison(
        patch_a_manifest_hash=None,
        patch_b_manifest_hash="b" * 64,
    ) == {
        "corpus_hash_relation": "unknown",
        "policy": "none",
        "reason": "manifest-hash-unavailable",
    }

    assert compute_patch_comparison(
        patch_a_manifest_hash="a" * 64,
        patch_b_manifest_hash="a" * 64,
    ) == {
        "corpus_hash_relation": "same",
        "policy": "none",
        "reason": "patch-manifest-hashes-match",
    }

    assert compute_patch_comparison(
        patch_a_manifest_hash="a" * 64,
        patch_b_manifest_hash="b" * 64,
    ) == {
        "corpus_hash_relation": "different",
        "policy": "warn",
        "reason": "patch-manifest-hashes-differ",
    }
