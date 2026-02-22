"""Tests for syllable_walk_web session/IPC path helper utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from build_tools.syllable_walk_web.services import session_paths


def test_resolve_sessions_base_defaults_to_output_base_sessions(tmp_path: Path) -> None:
    """Without override, sessions base should be derived from output_base."""

    resolved = session_paths.resolve_sessions_base(output_base=tmp_path / "output")
    assert resolved == (tmp_path / "output" / "sessions").resolve()


def test_resolve_sessions_base_prefers_configured_override(tmp_path: Path) -> None:
    """Configured sessions base should override output_base-derived fallback."""

    override = tmp_path / "custom" / "sessions-root"
    resolved = session_paths.resolve_sessions_base(
        output_base=tmp_path / "output",
        configured_sessions_base=override,
    )
    assert resolved == override.resolve()


def test_run_ipc_dir_returns_run_local_ipc_directory(tmp_path: Path) -> None:
    """Run-local IPC directory should always be `<run_dir>/ipc`."""

    run_dir = tmp_path / "20260222_230000_nltk"
    assert session_paths.run_ipc_dir(run_dir) == run_dir / "ipc"


@pytest.mark.parametrize(
    ("patch", "kind", "expected"),
    [
        ("a", "walks", "patch_a_walks.v1.json"),
        ("A", "candidates", "patch_a_candidates.v1.json"),
        ("b", "selections", "patch_b_selections.v1.json"),
        ("b", "package", "patch_b_package.v1.json"),
    ],
)
def test_patch_output_sidecar_path_builds_canonical_filename(
    tmp_path: Path,
    patch: str,
    kind: str,
    expected: str,
) -> None:
    """Patch output sidecar filenames should follow canonical convention."""

    run_dir = tmp_path / "20260222_230000_nltk"
    path = session_paths.patch_output_sidecar_path(
        run_dir=run_dir,
        patch=patch,
        artifact_kind=kind,
    )
    assert path == run_dir / "ipc" / expected


def test_patch_output_sidecar_path_rejects_invalid_patch(tmp_path: Path) -> None:
    """Invalid patch keys should fail fast."""

    with pytest.raises(ValueError, match="Invalid patch key"):
        session_paths.patch_output_sidecar_path(
            run_dir=tmp_path,
            patch="c",
            artifact_kind="walks",
        )


def test_patch_output_sidecar_path_rejects_invalid_kind(tmp_path: Path) -> None:
    """Invalid artifact kinds should fail fast."""

    with pytest.raises(ValueError, match="Invalid patch output kind"):
        session_paths.patch_output_sidecar_path(
            run_dir=tmp_path,
            patch="a",
            artifact_kind="unknown",
        )


def test_patch_output_sidecar_path_rejects_invalid_schema_version(tmp_path: Path) -> None:
    """Schema versions lower than one are invalid."""

    with pytest.raises(ValueError, match="schema_version must be >= 1"):
        session_paths.patch_output_sidecar_path(
            run_dir=tmp_path,
            patch="a",
            artifact_kind="walks",
            schema_version=0,
        )


def test_session_file_path_uses_resolved_sessions_base(tmp_path: Path) -> None:
    """Session files should be placed under resolved sessions base."""

    path = session_paths.session_file_path(
        session_id="session_001",
        output_base=tmp_path / "output",
    )
    assert path == (tmp_path / "output" / "sessions" / "session_001.json").resolve()


def test_session_file_path_rejects_blank_session_id(tmp_path: Path) -> None:
    """Blank session identifiers should be rejected."""

    with pytest.raises(ValueError, match="session_id must not be blank"):
        session_paths.session_file_path(
            session_id="   ",
            output_base=tmp_path / "output",
        )
