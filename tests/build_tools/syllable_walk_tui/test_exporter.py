"""
Tests for export helpers in syllable_walk_tui.services.exporter.
"""

from __future__ import annotations

import json
from pathlib import Path

from build_tools.syllable_walk_tui.services.exporter import export_sample_json


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
