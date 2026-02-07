"""
Tests for export helpers in syllable_walk_tui.services.exporter.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from build_tools.syllable_walk_tui.services.exporter import export_names_to_txt, export_sample_json


def test_export_sample_json_writes_lowercase_samples(tmp_path: Path) -> None:
    """export_sample_json should write lowercase samples to <name_class>.json."""
    selections_dir = tmp_path / "selections"
    names = ["Alma", "Belaro", "ALMA", "Cora"]

    output_path, error = export_sample_json(
        names=names,
        name_class="first_name",
        selections_dir=selections_dir,
        sample_size=2,
        seed=123,
    )

    assert error is None
    assert output_path.exists()
    assert output_path.name == "first_name_sample.json"

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["name_class"] == "first_name"
    assert payload["sample_count"] == 2
    assert all(name == name.lower() for name in payload["samples"])


def test_export_sample_json_errors_on_empty_names(tmp_path: Path) -> None:
    """export_sample_json should return an error when no names are provided."""
    selections_dir = tmp_path / "selections"

    output_path, error = export_sample_json(
        names=[],
        name_class="first_name",
        selections_dir=selections_dir,
    )

    assert error is not None
    assert output_path.name == "first_name_sample.json"


def test_export_names_to_txt_writes_lines(tmp_path: Path) -> None:
    """export_names_to_txt should write one name per line."""
    json_output_path = tmp_path / "names.json"
    txt_path, error = export_names_to_txt(["Alma", "Bera"], str(json_output_path))

    assert error is None
    assert txt_path.exists()
    assert txt_path.read_text(encoding="utf-8") == "Alma\nBera\n"


def test_export_names_to_txt_handles_oserror(tmp_path: Path) -> None:
    """export_names_to_txt should return filesystem errors from writes."""
    json_output_path = tmp_path / "names.json"
    with patch("builtins.open", side_effect=OSError("disk full")):
        txt_path, error = export_names_to_txt(["Alma"], str(json_output_path))

    assert txt_path.name == "names.txt"
    assert error is not None
    assert "File system error" in error


def test_export_sample_json_handles_mkdir_failure(tmp_path: Path) -> None:
    """export_sample_json should surface selections-dir creation errors."""
    selections_dir = tmp_path / "selections"
    with patch.object(Path, "mkdir", side_effect=OSError("no permission")):
        output_path, error = export_sample_json(
            names=["Alma"],
            name_class="first_name",
            selections_dir=selections_dir,
        )

    assert output_path.name == "first_name_sample.json"
    assert error is not None
    assert "Failed to create selections dir" in error


def test_export_sample_json_handles_write_failure(tmp_path: Path) -> None:
    """export_sample_json should surface file write errors."""
    selections_dir = tmp_path / "selections"
    with patch("builtins.open", side_effect=OSError("readonly fs")):
        output_path, error = export_sample_json(
            names=["Alma"],
            name_class="first_name",
            selections_dir=selections_dir,
        )

    assert output_path.name == "first_name_sample.json"
    assert error is not None
    assert "Failed to write sample JSON" in error
