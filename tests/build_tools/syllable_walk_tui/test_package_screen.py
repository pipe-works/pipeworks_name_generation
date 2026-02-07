"""
UI layout tests for the PackageScreen.

These tests ensure the two-column layout and core widgets exist.
"""

import json
from pathlib import Path

import pytest
from textual.containers import VerticalScroll
from textual.widgets import Input, Static, TextArea

from build_tools.syllable_walk_tui.core import SyllableWalkerApp
from build_tools.syllable_walk_tui.modules.packager import PackageScreen


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
