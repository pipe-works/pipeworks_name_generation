"""
Tests for the selection packaging service.

These tests validate scan behavior, include filters, and ZIP output content.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest.mock import patch

from build_tools.syllable_walk_tui.services.packager import (
    PackageOptions,
    _extract_extractor_type,
    _parse_selection_filename,
    build_package_metadata,
    collect_included_files,
    package_selections,
    scan_selections,
    write_metadata_json,
)


def _write_selection_files(run_dir: Path, prefix: str = "pyphen") -> Path:
    """
    Create a minimal selections directory with JSON, TXT, and meta files.

    Args:
        run_dir: Run directory to populate
        prefix: Prefix used in selection filenames

    Returns:
        Path to the selections directory
    """
    selections_dir = run_dir / "selections"
    selections_dir.mkdir(parents=True, exist_ok=True)

    # Create a small JSON selection file
    json_path = selections_dir / f"{prefix}_first_name_2syl.json"
    json_path.write_text(
        json.dumps({"metadata": {"name_class": "first_name"}, "selections": [{"name": "Alma"}]}),
        encoding="utf-8",
    )

    # Create matching TXT export
    txt_path = selections_dir / f"{prefix}_first_name_2syl.txt"
    txt_path.write_text("Alma\n", encoding="utf-8")

    # Add another JSON selection file for coverage
    json_path_two = selections_dir / f"{prefix}_last_name_3syl.json"
    json_path_two.write_text(
        json.dumps({"metadata": {"name_class": "last_name"}, "selections": [{"name": "Belaro"}]}),
        encoding="utf-8",
    )

    # Add selector meta file
    meta_path = selections_dir / f"{prefix}_selector_meta.json"
    meta_path.write_text(json.dumps({"tool": "name_selector"}), encoding="utf-8")

    return selections_dir


def test_scan_selections_accepts_run_dir(tmp_path: Path) -> None:
    """scan_selections should work when given a run directory."""
    run_dir = tmp_path / "20260130_185007_pyphen"
    _write_selection_files(run_dir)

    inventory, error = scan_selections(run_dir)

    assert error is None
    assert inventory is not None
    assert inventory.run_dir == run_dir
    assert inventory.selections_dir == run_dir / "selections"
    assert len(inventory.selection_json) == 2
    assert len(inventory.selection_txt) == 1
    assert len(inventory.meta_json) == 1


def test_scan_selections_accepts_selections_dir(tmp_path: Path) -> None:
    """scan_selections should normalize selections/ to the parent run dir."""
    run_dir = tmp_path / "20260130_185007_pyphen"
    selections_dir = _write_selection_files(run_dir)

    inventory, error = scan_selections(selections_dir)

    assert error is None
    assert inventory is not None
    assert inventory.run_dir == run_dir
    assert inventory.selections_dir == selections_dir


def test_package_selections_creates_zip_with_manifest(tmp_path: Path) -> None:
    """package_selections should produce a ZIP archive with manifest."""
    run_dir = tmp_path / "20260130_185007_pyphen"
    _write_selection_files(run_dir)
    output_dir = tmp_path / "packages"

    result = package_selections(PackageOptions(run_dir=run_dir, output_dir=output_dir))

    assert result.error is None
    assert result.package_path.exists()

    with zipfile.ZipFile(result.package_path) as archive:
        names = set(archive.namelist())
        assert "manifest.json" in names
        assert "selections/pyphen_first_name_2syl.json" in names
        assert "selections/pyphen_first_name_2syl.txt" in names
        assert "selections/pyphen_last_name_3syl.json" in names
        assert "selections/pyphen_selector_meta.json" in names

        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        assert manifest["run_name"] == run_dir.name
        assert "first_name" in manifest["selection_index"]
        assert "2syl" in manifest["selection_index"]["first_name"]


def test_package_selections_respects_include_flags(tmp_path: Path) -> None:
    """package_selections should omit files based on include flags."""
    run_dir = tmp_path / "20260130_185007_pyphen"
    _write_selection_files(run_dir)

    options = PackageOptions(
        run_dir=run_dir,
        include_txt=False,
        include_meta=False,
        include_manifest=False,
    )
    result = package_selections(options)

    assert result.error is None
    with zipfile.ZipFile(result.package_path) as archive:
        names = set(archive.namelist())
        assert "manifest.json" not in names
        assert all(name.endswith(".json") for name in names)
        assert "selections/pyphen_first_name_2syl.json" in names
        assert "selections/pyphen_last_name_3syl.json" in names


def test_package_selections_rejects_existing_package(tmp_path: Path) -> None:
    """package_selections should return an error if the ZIP already exists."""
    run_dir = tmp_path / "20260130_185007_pyphen"
    _write_selection_files(run_dir)
    output_dir = tmp_path / "packages"

    first = package_selections(PackageOptions(run_dir=run_dir, output_dir=output_dir))
    assert first.error is None

    second = package_selections(PackageOptions(run_dir=run_dir, output_dir=output_dir))
    assert second.error is not None
    assert "already exists" in second.error


def test_package_selections_accepts_selections_dir(tmp_path: Path) -> None:
    """package_selections should accept selections/ as the run_dir input."""
    run_dir = tmp_path / "20260130_185007_pyphen"
    selections_dir = _write_selection_files(run_dir)

    result = package_selections(PackageOptions(run_dir=selections_dir))

    assert result.error is None
    assert result.package_path.parent == run_dir / "packages"


def test_package_selections_no_files_returns_error(tmp_path: Path) -> None:
    """package_selections should return an error when nothing is included."""
    run_dir = tmp_path / "20260130_185007_pyphen"
    (run_dir / "selections").mkdir(parents=True, exist_ok=True)

    result = package_selections(PackageOptions(run_dir=run_dir))

    assert result.error is not None
    assert "No selection files" in result.error


def test_collect_included_files_respects_flags(tmp_path: Path) -> None:
    """collect_included_files should include only requested file types."""
    run_dir = tmp_path / "20260130_185007_pyphen"
    _write_selection_files(run_dir)

    included, error = collect_included_files(
        run_dir, include_json=True, include_txt=False, include_meta=False
    )

    assert error is None
    assert included
    assert all(path.suffix == ".json" for path in included)
    assert not any(path.name.endswith("_meta.json") for path in included)


def test_build_package_metadata_includes_fields(tmp_path: Path) -> None:
    """build_package_metadata should capture author inputs and file list."""
    run_dir = tmp_path / "20260130_185007_pyphen"
    _write_selection_files(run_dir)

    included, _ = collect_included_files(
        run_dir, include_json=True, include_txt=True, include_meta=True
    )
    metadata_inputs = {
        "created_at": "2026-02-07 12:00:00",
        "author": "Test Author",
        "version": "1.0.0",
        "common_name": "Goblin Latin Flora",
        "intended_use": ["first_name", "last_name"],
        "examples": {"first_name": ["alma", "belaro"], "last_name": ["sorin"]},
    }
    include_flags = {"json": True, "txt": True, "meta": True, "manifest": True}

    metadata = build_package_metadata(run_dir, metadata_inputs, included, include_flags)

    assert metadata["author"] == "Test Author"
    assert metadata["common_name"] == "Goblin Latin Flora"
    assert metadata["source_run"] == run_dir.name
    assert metadata["files_included"]


def test_write_metadata_json_creates_file(tmp_path: Path) -> None:
    """write_metadata_json should write metadata beside the package."""
    output_dir = tmp_path / "packages"
    metadata = {"author": "Tester"}

    path, error = write_metadata_json(output_dir, "sample_package.zip", metadata)

    assert error is None
    assert path.exists()
    assert path.name == "sample_package_metadata.json"


def test_extract_extractor_type_and_filename_parsing_edges() -> None:
    """Internal parsers should handle invalid names safely."""
    assert _extract_extractor_type(Path("badname")) is None
    assert _extract_extractor_type(Path("20260130_185007_my_tool")) == "my_tool"

    assert _parse_selection_filename("bad.json") == (None, None)
    assert _parse_selection_filename("pyphen_first_name_bad.json") == (None, None)
    assert _parse_selection_filename("pyphen_first_name_2syl.json") == ("first_name", "2syl")


def test_scan_and_collect_return_errors_for_missing_paths(tmp_path: Path) -> None:
    """Scan/collect should return descriptive errors when inputs are missing."""
    missing_run = tmp_path / "missing"
    inventory, scan_error = scan_selections(missing_run)
    included, collect_error = collect_included_files(
        missing_run, include_json=True, include_txt=True, include_meta=True
    )

    assert inventory is None
    assert scan_error is not None
    assert included == []
    assert collect_error is not None


def test_scan_selections_errors_when_selections_subdir_missing(tmp_path: Path) -> None:
    """scan_selections should error when run dir has no selections folder."""
    run_dir = tmp_path / "20260130_185007_pyphen"
    run_dir.mkdir(parents=True)

    inventory, error = scan_selections(run_dir)

    assert inventory is None
    assert error is not None
    assert "Selections directory not found" in error


def test_package_selections_appends_zip_suffix(tmp_path: Path) -> None:
    """Package name without .zip suffix should be normalized."""
    run_dir = tmp_path / "20260130_185007_pyphen"
    _write_selection_files(run_dir)

    result = package_selections(
        PackageOptions(
            run_dir=run_dir,
            output_dir=tmp_path / "packages",
            package_name="custom_name",
        )
    )

    assert result.error is None
    assert result.package_path.name == "custom_name.zip"


def test_write_metadata_json_returns_error_on_oserror(tmp_path: Path) -> None:
    """write_metadata_json should return an error tuple when writes fail."""
    output_dir = tmp_path / "packages"

    with patch("builtins.open", side_effect=OSError("read-only")):
        path, error = write_metadata_json(output_dir, "sample_package.zip", {"author": "x"})

    assert path.name == "sample_package_metadata.json"
    assert error is not None
