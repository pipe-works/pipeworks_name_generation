"""Tests for the packager service.

This module tests ZIP archive building and disk persistence:
- build_package: empty state, walks only, candidates, selections, both patches
- ZIP contents verification (correct paths, valid JSON)
- _write_selections: JSON + TXT output
- _build_manifest: schema, timestamps, file counts
- _patch_summary: correct counts
- _persist_to_disk: directory creation, file writing, error handling
"""

import json
import zipfile
from io import BytesIO
from typing import Any
from unittest.mock import patch

import pytest

from build_tools.syllable_walk_web.services.packager import (
    _patch_summary,
    _persist_to_disk,
    _write_selections,
    build_package,
)
from build_tools.syllable_walk_web.state import PatchState, ServerState

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def state():
    """Fresh ServerState with no data."""
    return ServerState()


@pytest.fixture
def state_with_walks(state):
    """State with walks in patch A."""
    state.patch_a.run_id = "test_run"
    state.patch_a.corpus_type = "pyphen"
    state.patch_a.syllable_count = 10
    state.patch_a.walks = [
        {"formatted": "ka·ri", "syllables": ["ka", "ri"], "steps": []},
        {"formatted": "ta·mi", "syllables": ["ta", "mi"], "steps": []},
    ]
    return state


@pytest.fixture
def state_with_candidates(state_with_walks):
    """State with candidates in patch A."""
    state_with_walks.patch_a.candidates = [
        {"name": "Kari", "syllables": ["ka", "ri"], "features": {}},
        {"name": "Tami", "syllables": ["ta", "mi"], "features": {}},
    ]
    return state_with_walks


@pytest.fixture
def state_with_selections(state_with_candidates):
    """State with selections in patch A."""
    state_with_candidates.patch_a.selected_names = [
        {"name": "Kari", "syllables": ["ka", "ri"], "score": 1.0},
    ]
    return state_with_candidates


@pytest.fixture
def full_state(state_with_selections):
    """State with data in both patches."""
    s = state_with_selections
    s.patch_b.run_id = "test_run_b"
    s.patch_b.corpus_type = "nltk"
    s.patch_b.syllable_count = 5
    s.patch_b.walks = [{"formatted": "do·re", "syllables": ["do", "re"], "steps": []}]
    s.patch_b.candidates = [{"name": "Dore", "syllables": ["do", "re"], "features": {}}]
    s.patch_b.selected_names = [{"name": "Dore", "score": 0.9}]
    return s


# ============================================================
# build_package — empty state
# ============================================================


class TestBuildPackageEmpty:
    """Test build_package with no data."""

    def test_empty_state_returns_error(self, state):
        """Test empty state returns error message, not empty ZIP."""
        zip_bytes, error = build_package(state)
        assert error is not None
        assert "Nothing to package" in error
        assert zip_bytes == b""

    def test_empty_with_all_flags_false(self, state_with_walks):
        """Test all include flags false returns error."""
        zip_bytes, error = build_package(
            state_with_walks,
            include_walks_a=False,
            include_walks_b=False,
            include_candidates=False,
            include_selections=False,
        )
        assert error is not None


# ============================================================
# build_package — walks only
# ============================================================


class TestBuildPackageWalks:
    """Test build_package with walk data."""

    def test_walks_only(self, state_with_walks):
        """Test packaging walks produces valid ZIP."""
        zip_bytes, error = build_package(
            state_with_walks,
            include_candidates=False,
            include_selections=False,
        )
        assert error is None
        assert len(zip_bytes) > 0

        zf = zipfile.ZipFile(BytesIO(zip_bytes))
        names = zf.namelist()
        assert "patch_a/walks.json" in names
        assert "manifest.json" in names

    def test_walks_json_is_valid(self, state_with_walks):
        """Test walks.json inside ZIP contains valid data."""
        zip_bytes, _ = build_package(
            state_with_walks, include_candidates=False, include_selections=False
        )
        zf = zipfile.ZipFile(BytesIO(zip_bytes))
        data = json.loads(zf.read("patch_a/walks.json"))
        assert len(data) == 2
        assert data[0]["formatted"] == "ka·ri"


# ============================================================
# build_package — candidates
# ============================================================


class TestBuildPackageCandidates:
    """Test build_package with candidate data."""

    def test_candidates_included(self, state_with_candidates):
        """Test candidates are packaged when include_candidates=True."""
        zip_bytes, error = build_package(state_with_candidates, include_selections=False)
        assert error is None
        zf = zipfile.ZipFile(BytesIO(zip_bytes))
        assert "patch_a/candidates.json" in zf.namelist()


# ============================================================
# build_package — selections
# ============================================================


class TestBuildPackageSelections:
    """Test build_package with selection data."""

    def test_selections_json_and_txt(self, state_with_selections):
        """Test selections produce both JSON and TXT files."""
        zip_bytes, error = build_package(state_with_selections)
        assert error is None
        zf = zipfile.ZipFile(BytesIO(zip_bytes))
        names = zf.namelist()
        assert "patch_a/selections.json" in names
        assert "patch_a/selections.txt" in names

    def test_selections_txt_content(self, state_with_selections):
        """Test TXT file has one name per line."""
        zip_bytes, _ = build_package(state_with_selections)
        zf = zipfile.ZipFile(BytesIO(zip_bytes))
        txt = zf.read("patch_a/selections.txt").decode("utf-8")
        assert "Kari" in txt


# ============================================================
# build_package — both patches
# ============================================================


class TestBuildPackageBothPatches:
    """Test build_package with data in both patches."""

    def test_both_patches_included(self, full_state):
        """Test both patch A and B data are in the ZIP."""
        zip_bytes, error = build_package(full_state)
        assert error is None
        zf = zipfile.ZipFile(BytesIO(zip_bytes))
        names = zf.namelist()
        assert "patch_a/walks.json" in names
        assert "patch_b/walks.json" in names
        assert "patch_a/selections.json" in names
        assert "patch_b/selections.json" in names


# ============================================================
# build_package — manifest
# ============================================================


class TestBuildPackageManifest:
    """Test manifest.json inside the ZIP."""

    def test_manifest_has_required_fields(self, state_with_walks):
        """Test manifest contains all required metadata."""
        zip_bytes, _ = build_package(
            state_with_walks, include_candidates=False, include_selections=False
        )
        zf = zipfile.ZipFile(BytesIO(zip_bytes))
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["schema_version"] == 1
        assert "created_at" in manifest
        assert manifest["package_name"] == "corpus-package"
        assert manifest["version"] == "0.1.0"
        assert "patch_a" in manifest
        assert "patch_b" in manifest
        assert manifest["file_count"] >= 1

    def test_custom_name_and_version(self, state_with_walks):
        """Test custom name and version appear in manifest."""
        zip_bytes, _ = build_package(
            state_with_walks,
            name="my-corpus",
            version="2.0.0",
            include_candidates=False,
            include_selections=False,
        )
        zf = zipfile.ZipFile(BytesIO(zip_bytes))
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["package_name"] == "my-corpus"
        assert manifest["version"] == "2.0.0"


# ============================================================
# _patch_summary
# ============================================================


class TestPatchSummary:
    """Test _patch_summary helper."""

    def test_empty_patch(self):
        """Test summary for empty patch."""
        ps = PatchState()
        summary = _patch_summary(ps)
        assert summary["run_id"] is None
        assert summary["walk_count"] == 0
        assert summary["candidate_count"] == 0
        assert summary["selection_count"] == 0

    def test_populated_patch(self):
        """Test summary for populated patch."""
        ps = PatchState()
        ps.run_id = "test"
        ps.corpus_type = "pyphen"
        ps.syllable_count = 100
        ps.walks = [{"a": 1}, {"b": 2}]
        ps.candidates = [{"name": "X"}]
        ps.selected_names = [{"name": "Y"}, {"name": "Z"}]

        summary = _patch_summary(ps)
        assert summary["run_id"] == "test"
        assert summary["walk_count"] == 2
        assert summary["candidate_count"] == 1
        assert summary["selection_count"] == 2


# ============================================================
# _write_selections
# ============================================================


class TestWriteSelections:
    """Test selection writing into ZIP archives."""

    def test_writes_json_and_txt(self):
        """Test both JSON and TXT files are created."""
        from io import BytesIO

        buf = BytesIO()
        files: list[dict[str, Any]] = []
        ps = PatchState()
        ps.selected_names = [
            {"name": "Kari", "score": 1.0},
            {"name": "Rika", "score": 0.8},
        ]

        with zipfile.ZipFile(buf, "w") as zf:
            _write_selections(zf, "a", ps, files)

        zf = zipfile.ZipFile(BytesIO(buf.getvalue()))
        assert "patch_a/selections.json" in zf.namelist()
        assert "patch_a/selections.txt" in zf.namelist()
        assert len(files) == 2

    def test_txt_has_names_only(self):
        """Test TXT file contains only name strings."""
        buf = BytesIO()
        files: list[dict[str, Any]] = []
        ps = PatchState()
        ps.selected_names = [{"name": "Kari"}, {"name": "Rika"}]

        with zipfile.ZipFile(buf, "w") as zf:
            _write_selections(zf, "a", ps, files)

        zf = zipfile.ZipFile(BytesIO(buf.getvalue()))
        txt = zf.read("patch_a/selections.txt").decode("utf-8")
        lines = txt.strip().split("\n")
        assert lines == ["Kari", "Rika"]


# ============================================================
# _persist_to_disk
# ============================================================


class TestPersistToDisk:
    """Test disk persistence of ZIP and metadata."""

    def test_creates_packages_directory(self, tmp_path):
        """Test packages/ directory is created under output_base."""
        state = ServerState(output_base=tmp_path)
        _persist_to_disk(
            state=state,
            name="test",
            version="1.0",
            zip_bytes=b"PK\x03\x04",
            manifest={"created_at": "2026-02-20T00:00:00Z"},
            include_flags={"walks_a": True},
            files_included=[{"path": "test.json"}],
        )
        assert (tmp_path / "packages").is_dir()

    def test_writes_zip_file(self, tmp_path):
        """Test ZIP file is written to packages/."""
        state = ServerState(output_base=tmp_path)
        _persist_to_disk(
            state=state,
            name="test",
            version="1.0",
            zip_bytes=b"PK\x03\x04",
            manifest={"created_at": "2026-02-20T00:00:00Z"},
            include_flags={},
            files_included=[],
        )
        zips = list((tmp_path / "packages").glob("*.zip"))
        assert len(zips) == 1
        assert zips[0].read_bytes() == b"PK\x03\x04"

    def test_writes_metadata_json(self, tmp_path):
        """Test companion metadata JSON is written."""
        state = ServerState(output_base=tmp_path)
        _persist_to_disk(
            state=state,
            name="test",
            version="1.0",
            zip_bytes=b"PK\x03\x04",
            manifest={"created_at": "2026-02-20T00:00:00Z"},
            include_flags={"walks_a": True},
            files_included=[{"path": "walks.json"}],
        )
        meta_files = list((tmp_path / "packages").glob("*_metadata.json"))
        assert len(meta_files) == 1

        meta = json.loads(meta_files[0].read_text())
        assert meta["schema_version"] == 1
        assert meta["package_name"] == "test"
        assert meta["version"] == "1.0"
        assert meta["files_included"] == ["walks.json"]

    def test_handles_oserror_gracefully(self, tmp_path, capsys):
        """Test OSError during persistence is caught and logged."""
        state = ServerState(output_base=tmp_path / "nonexistent" / "deep")

        with patch("pathlib.Path.mkdir", side_effect=OSError("disk full")):
            # Should not raise
            _persist_to_disk(
                state=state,
                name="test",
                version="1.0",
                zip_bytes=b"PK",
                manifest={},
                include_flags={},
                files_included=[],
            )

        captured = capsys.readouterr()
        assert "warning" in captured.err.lower() or "failed" in captured.err.lower()
