"""
UI layout tests for the PackageScreen.

These tests ensure the two-column layout and core widgets exist.
"""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from textual.containers import VerticalScroll
from textual.widgets import Input, Static, TextArea

from build_tools.syllable_walk_tui.core import SyllableWalkerApp
from build_tools.syllable_walk_tui.modules.packager import PackageScreen
from build_tools.syllable_walk_tui.services.packager import PackageResult, SelectionInventory


def _static_text(widget: Static) -> str:
    """Return plain string content from a Static widget."""
    return str(widget.render())


@pytest.mark.asyncio
async def test_package_screen_layout_has_editor_and_workflow_columns() -> None:
    """PackageScreen should render editor and workflow columns with key widgets."""
    app = SyllableWalkerApp()

    async with app.run_test() as pilot:
        screen = PackageScreen()
        app.push_screen(screen)
        # Allow Textual to mount the screen before querying widgets
        await pilot.pause()

        # Left column should exist and host the metadata editor
        screen.query_one("#package-editor-column", VerticalScroll)
        screen.query_one("#meta-created", Input)
        screen.query_one("#meta-author", Input)
        screen.query_one("#meta-version", Input)
        screen.query_one("#meta-common-name", Input)
        screen.query_one("#meta-intended-use")
        assert screen.query(".intended-use-option")
        screen.query_one("#meta-source", Input)
        screen.query_one("#meta-examples", TextArea)
        screen.query_one("#meta-files", Static)

        # Version should default to 1.0.0
        assert screen.query_one("#meta-version", Input).value == "1.0.0"

        # Right column should exist and host the workflow inputs
        screen.query_one("#package-workflow-column", VerticalScroll)
        screen.query_one("#run-dir-input", Input)


@pytest.mark.asyncio
async def test_common_name_updates_package_name() -> None:
    """Common name should drive the default package name."""
    app = SyllableWalkerApp()

    async with app.run_test() as pilot:
        screen = PackageScreen()
        app.push_screen(screen)
        await pilot.pause()

        # Simulate entering a common name
        screen._handle_common_name_change("Goblin Latin Flora")

        package_name = screen.query_one("#package-name-input", Input).value
        assert package_name == "goblin_latin_flora_selections.zip"


@pytest.mark.asyncio
async def test_manual_package_name_blocks_auto_sync() -> None:
    """Manual package name edits should prevent auto updates from common name."""
    app = SyllableWalkerApp()

    async with app.run_test() as pilot:
        screen = PackageScreen()
        app.push_screen(screen)
        await pilot.pause()

        # User overrides the package name
        screen._handle_package_name_change("custom_selections.zip")
        screen._set_input_value("package-name-input", "custom_selections.zip")

        # Common name edits should no longer overwrite the manual value
        screen._handle_common_name_change("Goblin Latin Flora")

        package_name = screen.query_one("#package-name-input", Input).value
        assert package_name == "custom_selections.zip"


@pytest.mark.asyncio
async def test_examples_update_from_sample_json(tmp_path: Path) -> None:
    """Examples field should load from <run_dir>/selections/<name_class>_sample.json."""
    run_dir = tmp_path / "20260130_185007_pyphen"
    selections_dir = run_dir / "selections"
    selections_dir.mkdir(parents=True)
    sample_path = selections_dir / "first_name_sample.json"
    sample_path.write_text('{"samples": ["Alma", "Bera"]}', encoding="utf-8")

    app = SyllableWalkerApp()

    async with app.run_test() as pilot:
        screen = PackageScreen(initial_run_dir=run_dir)
        app.push_screen(screen)
        await pilot.pause()

        # Force refresh to ensure sample file is read
        screen._set_examples_for_name_classes(["first_name"])

        examples_text = screen.query_one("#meta-examples", TextArea).text
        assert examples_text == json.dumps({"first_name": ["Alma", "Bera"]}, indent=2)


def test_load_examples_from_samples_handles_missing_and_invalid(tmp_path: Path) -> None:
    """Loading samples should safely handle missing and malformed inputs."""
    screen = PackageScreen()
    assert screen._load_examples_from_samples("first_name") == []

    run_dir = tmp_path / "20260130_185007_pyphen"
    selections_dir = run_dir / "selections"
    selections_dir.mkdir(parents=True)
    screen.run_dir = run_dir

    # Missing file
    assert screen._load_examples_from_samples("first_name") == []

    # Malformed payload
    (selections_dir / "first_name_sample.json").write_text("{bad json", encoding="utf-8")
    assert screen._load_examples_from_samples("first_name") == []

    # Non-list samples
    (selections_dir / "first_name_sample.json").write_text('{"samples": "bad"}', encoding="utf-8")
    assert screen._load_examples_from_samples("first_name") == []


def test_collect_examples_payload_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Examples payload parser should fall back to sample defaults on invalid editor data."""
    screen = PackageScreen()
    monkeypatch.setattr(screen, "_get_intended_use_values", lambda: ["first_name", "last_name"])
    monkeypatch.setattr(
        screen,
        "_build_examples_payload",
        lambda classes: {name: [f"{name}-sample"] for name in classes},
    )
    monkeypatch.setattr(
        screen,
        "_load_examples_from_samples",
        lambda name: [f"{name}-fallback"],
    )

    # Empty editor should use defaults
    monkeypatch.setattr(screen, "_get_text_area_value", lambda _: "")
    assert screen._collect_examples_payload() == {
        "first_name": ["first_name-sample"],
        "last_name": ["last_name-sample"],
    }

    # Invalid JSON should use defaults
    monkeypatch.setattr(screen, "_get_text_area_value", lambda _: "{broken")
    assert screen._collect_examples_payload() == {
        "first_name": ["first_name-sample"],
        "last_name": ["last_name-sample"],
    }

    # Non-dict JSON should use defaults
    monkeypatch.setattr(screen, "_get_text_area_value", lambda _: '["bad"]')
    assert screen._collect_examples_payload() == {
        "first_name": ["first_name-sample"],
        "last_name": ["last_name-sample"],
    }

    # Partial dict should fill missing/invalid classes from fallback
    monkeypatch.setattr(
        screen,
        "_get_text_area_value",
        lambda _: '{"first_name": ["one", "two"], "last_name": "bad"}',
    )
    assert screen._collect_examples_payload() == {
        "first_name": ["one", "two"],
        "last_name": ["last_name-fallback"],
    }


def test_load_name_class_options_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Name class options should fall back when policy loading fails."""
    import build_tools.syllable_walk_tui.modules.packager.screen as screen_module

    screen = PackageScreen()

    def _raise_load_error(_: Path) -> dict:
        raise ValueError

    monkeypatch.setattr(screen_module, "load_name_classes", _raise_load_error)
    options = screen._load_name_class_options()
    assert ("First Name", "first_name") in options
    assert ("Last Name", "last_name") in options


@pytest.mark.asyncio
async def test_run_dir_and_build_error_status_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Screen should set helpful status messages for validation and build failures."""
    import build_tools.syllable_walk_tui.modules.packager.screen as screen_module

    app = SyllableWalkerApp()
    run_dir = tmp_path / "20260130_185007_pyphen"
    run_dir.mkdir(parents=True)

    async with app.run_test() as pilot:
        screen = PackageScreen()
        app.push_screen(screen)
        await pilot.pause()

        # Empty run-dir input should block packaging
        screen._set_input_value("run-dir-input", "")
        screen._build_package()
        assert "Select a run directory before packaging." in _static_text(
            screen.query_one("#package-status", Static)
        )

        # Packaging service error should be surfaced
        screen._set_input_value("run-dir-input", str(run_dir))
        monkeypatch.setattr(
            screen_module,
            "package_selections",
            lambda _: PackageResult(
                package_path=Path(),
                included_files=[],
                manifest=None,
                error="package failed",
            ),
        )
        screen._build_package()
        assert "package failed" in _static_text(screen.query_one("#package-status", Static))


@pytest.mark.asyncio
async def test_build_success_and_metadata_write_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Build flow should report metadata write errors and success status."""
    import build_tools.syllable_walk_tui.modules.packager.screen as screen_module

    app = SyllableWalkerApp()
    run_dir = tmp_path / "20260130_185007_pyphen"
    pkg_dir = run_dir / "packages"
    pkg_dir.mkdir(parents=True)
    package_path = pkg_dir / "custom.zip"

    async with app.run_test() as pilot:
        screen = PackageScreen()
        app.push_screen(screen)
        await pilot.pause()

        screen._set_input_value("run-dir-input", str(run_dir))
        screen._set_input_value("meta-common-name", "Goblin Latin Flora")
        screen._set_input_value("package-name-input", "")

        monkeypatch.setattr(
            screen_module,
            "package_selections",
            lambda _: PackageResult(
                package_path=package_path, included_files=[package_path], manifest={}
            ),
        )
        monkeypatch.setattr(
            screen_module,
            "build_package_metadata",
            lambda **_: {"ok": True},
        )

        # First run: metadata write failure
        monkeypatch.setattr(
            screen_module,
            "write_metadata_json",
            lambda *args: (Path(args[0]) / "x.json", "meta write failed"),
        )
        screen._build_package()
        assert "metadata failed: meta write failed" in _static_text(
            screen.query_one("#package-status", Static)
        )

        # Second run: full success
        monkeypatch.setattr(
            screen_module,
            "write_metadata_json",
            lambda *args: (Path(args[0]) / "ok_metadata.json", None),
        )
        screen._build_package()
        assert "Package created:" in _static_text(screen.query_one("#package-status", Static))


@pytest.mark.asyncio
async def test_summary_and_included_file_refresh_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Summary and included-files widgets should handle error, empty, and success cases."""
    import build_tools.syllable_walk_tui.modules.packager.screen as screen_module

    app = SyllableWalkerApp()
    run_dir = tmp_path / "20260130_185007_pyphen"
    run_dir.mkdir(parents=True)

    async with app.run_test() as pilot:
        screen = PackageScreen()
        app.push_screen(screen)
        await pilot.pause()

        # Summary error branch
        monkeypatch.setattr(screen_module, "scan_selections", lambda _: (None, "scan error"))
        screen._refresh_selection_summary(run_dir)
        assert "scan error" in _static_text(screen.query_one("#selection-summary", Static))

        # Summary success branch
        inventory = SelectionInventory(
            run_dir=run_dir,
            selections_dir=run_dir / "selections",
            selection_json=[run_dir / "a.json"],
            selection_txt=[run_dir / "a.txt"],
            meta_json=[run_dir / "a_meta.json"],
        )
        monkeypatch.setattr(screen_module, "scan_selections", lambda _: (inventory, None))
        screen._refresh_selection_summary(run_dir)
        summary_text = _static_text(screen.query_one("#selection-summary", Static))
        assert "JSON: 1, TXT: 1, Meta: 1" in summary_text

        # Included files error
        monkeypatch.setattr(
            screen_module, "collect_included_files", lambda **_: ([], "collect error")
        )
        screen._refresh_included_files(run_dir)
        assert "collect error" in _static_text(screen.query_one("#meta-files", Static))

        # Included files empty
        monkeypatch.setattr(screen_module, "collect_included_files", lambda **_: ([], None))
        screen._refresh_included_files(run_dir)
        assert "No files match include settings." in _static_text(
            screen.query_one("#meta-files", Static)
        )

        # Included files success
        monkeypatch.setattr(
            screen_module,
            "collect_included_files",
            lambda **_: ([run_dir / "one.json", run_dir / "two.txt"], None),
        )
        screen._refresh_included_files(run_dir)
        included_text = _static_text(screen.query_one("#meta-files", Static))
        assert "- one.json" in included_text
        assert "- two.txt" in included_text


@pytest.mark.asyncio
async def test_checkbox_events_and_run_dir_submission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Checkbox handlers and run-dir submission should update state and trigger refreshes."""
    app = SyllableWalkerApp()
    run_dir = tmp_path / "20260130_185007_pyphen"
    (run_dir / "selections").mkdir(parents=True)

    async with app.run_test() as pilot:
        screen = PackageScreen()
        app.push_screen(screen)
        await pilot.pause()

        refreshed: list[Path] = []
        monkeypatch.setattr(
            screen,
            "_refresh_included_files",
            lambda run_dir: refreshed.append(run_dir),
        )

        screen.run_dir = run_dir
        screen.on_checkbox_changed(
            cast(Any, SimpleNamespace(checkbox=SimpleNamespace(id="include-json"), value=False))
        )
        assert screen.include_json is False
        assert refreshed[-1] == run_dir

        # Unknown checkbox should not trigger refresh
        count_before = len(refreshed)
        screen.on_checkbox_changed(
            cast(Any, SimpleNamespace(checkbox=SimpleNamespace(id="unknown"), value=True))
        )
        assert len(refreshed) == count_before

        # Run-dir submit should coerce selections/ to parent run dir
        screen.on_run_dir_submitted(cast(Any, SimpleNamespace(value=str(run_dir / "selections"))))
        assert screen.run_dir == run_dir


def test_small_helpers_and_path_normalization() -> None:
    """Small helper methods should handle missing widgets and path coercion."""
    screen = PackageScreen()

    assert screen._get_input_value("missing-input") == ""
    screen._set_input_value("missing-input", "value")
    assert screen._get_text_area_value("missing-text") == ""

    assert screen._normalize_path("   ") is None
    normalized = screen._normalize_path("~/tmp")
    assert normalized is not None

    assert screen._coerce_run_dir(None) is None
    assert screen._coerce_run_dir(Path("/tmp/run/selections")) == Path("/tmp/run")
