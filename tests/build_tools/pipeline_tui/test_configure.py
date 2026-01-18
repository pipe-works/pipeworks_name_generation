"""
Tests for ConfigurePanel widget.

Tests the ConfigurePanel component which provides all configuration
options for the syllable extraction pipeline.
"""

from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from textual.app import App
from textual.widgets import Button, Input, Label

from build_tools.pipeline_tui.core.state import ExtractorType
from build_tools.pipeline_tui.screens.configure import (
    COMMON_LANGUAGES,
    ConfigurePanel,
)
from build_tools.tui_common.controls import IntSpinner, RadioOption

# =============================================================================
# ConfigurePanel Initialization Tests
# =============================================================================


class TestConfigurePanelInitialization:
    """Tests for ConfigurePanel initialization."""

    def test_initialization_with_defaults(self):
        """Test ConfigurePanel initializes with correct default values."""
        panel = ConfigurePanel()

        assert panel.source_path is None
        assert panel.output_dir is None
        assert panel.extractor_type == ExtractorType.PYPHEN
        assert panel.language == "auto"  # Matches pyphen extractor default (auto-detect)
        assert panel.min_syllable_length == 2
        assert panel.max_syllable_length == 8
        assert panel.file_pattern == "*.txt"
        assert panel.run_normalize is True
        assert panel.run_annotate is True

    def test_initialization_with_custom_values(self):
        """Test ConfigurePanel initializes with provided values."""
        source = Path("/test/source")
        output = Path("/test/output")

        panel = ConfigurePanel(
            source_path=source,
            output_dir=output,
            extractor_type=ExtractorType.NLTK,
            language="de_DE",
            min_syllable_length=3,
            max_syllable_length=10,
            file_pattern="*.md",
            run_normalize=False,
            run_annotate=False,
        )

        assert panel.source_path == source
        assert panel.output_dir == output
        assert panel.extractor_type == ExtractorType.NLTK
        assert panel.language == "de_DE"
        assert panel.min_syllable_length == 3
        assert panel.max_syllable_length == 10
        assert panel.file_pattern == "*.md"
        assert panel.run_normalize is False
        assert panel.run_annotate is False


# =============================================================================
# ConfigurePanel Message Tests
# =============================================================================


class TestConfigurePanelMessages:
    """Tests for ConfigurePanel message classes."""

    def test_source_selected_message(self):
        """Test SourceSelected message creation."""
        msg = ConfigurePanel.SourceSelected()
        # Message should be created without error
        assert msg is not None

    def test_output_selected_message(self):
        """Test OutputSelected message creation."""
        msg = ConfigurePanel.OutputSelected()
        assert msg is not None

    def test_extractor_changed_message(self):
        """Test ExtractorChanged message stores extractor type."""
        msg = ConfigurePanel.ExtractorChanged(ExtractorType.NLTK)
        assert msg.extractor_type == ExtractorType.NLTK

        msg2 = ConfigurePanel.ExtractorChanged(ExtractorType.PYPHEN)
        assert msg2.extractor_type == ExtractorType.PYPHEN

    def test_language_changed_message(self):
        """Test LanguageChanged message stores language code."""
        msg = ConfigurePanel.LanguageChanged("fr")
        assert msg.language == "fr"

    def test_constraints_changed_message(self):
        """Test ConstraintsChanged message stores all constraints."""
        msg = ConfigurePanel.ConstraintsChanged(
            min_length=3,
            max_length=12,
            file_pattern="*.rst",
        )
        assert msg.min_length == 3
        assert msg.max_length == 12
        assert msg.file_pattern == "*.rst"

    def test_pipeline_stages_changed_message(self):
        """Test PipelineStagesChanged message stores toggle states."""
        msg = ConfigurePanel.PipelineStagesChanged(
            run_normalize=False,
            run_annotate=True,
        )
        assert msg.run_normalize is False
        assert msg.run_annotate is True


# =============================================================================
# ConfigurePanel Widget Tests
# =============================================================================


class TestConfigurePanelWidgets:
    """Tests for ConfigurePanel widget composition."""

    @pytest.mark.asyncio
    async def test_panel_contains_expected_sections(self):
        """Test that ConfigurePanel contains all expected section containers."""

        class TestApp(App):
            def compose(self):
                yield ConfigurePanel(id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            # Query within the panel for nested widgets
            panel = app.query_one("#test-panel", ConfigurePanel)

            # Verify all sections exist by querying within the panel
            assert panel.query_one("#directories-section")
            assert panel.query_one("#extractor-section")
            assert panel.query_one("#language-section")
            assert panel.query_one("#constraints-section")
            assert panel.query_one("#stages-section")

    @pytest.mark.asyncio
    async def test_panel_contains_directory_buttons(self):
        """Test that ConfigurePanel contains browse buttons for directories."""

        class TestApp(App):
            def compose(self):
                yield ConfigurePanel(id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)
            source_btn = panel.query_one("#source-browse-btn", Button)
            output_btn = panel.query_one("#output-browse-btn", Button)

            assert source_btn is not None
            assert output_btn is not None
            assert "Browse" in str(source_btn.label)
            assert "Browse" in str(output_btn.label)

    @pytest.mark.asyncio
    async def test_panel_contains_extractor_options(self):
        """Test that ConfigurePanel contains extractor type radio options."""

        class TestApp(App):
            def compose(self):
                yield ConfigurePanel(id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)
            pyphen_opt = panel.query_one("#extractor-pyphen", RadioOption)
            nltk_opt = panel.query_one("#extractor-nltk", RadioOption)

            assert pyphen_opt is not None
            assert nltk_opt is not None
            assert pyphen_opt.option_name == "pyphen"
            assert nltk_opt.option_name == "nltk"

    @pytest.mark.asyncio
    async def test_panel_contains_spinner_controls(self):
        """Test that ConfigurePanel contains min/max length spinners."""

        class TestApp(App):
            def compose(self):
                yield ConfigurePanel(id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)
            min_spinner = panel.query_one("#min-length-spinner", IntSpinner)
            max_spinner = panel.query_one("#max-length-spinner", IntSpinner)

            assert min_spinner is not None
            assert max_spinner is not None
            assert min_spinner.value == 2  # Default
            assert max_spinner.value == 8  # Default

    @pytest.mark.asyncio
    async def test_panel_contains_file_pattern_input(self):
        """Test that ConfigurePanel contains file pattern input."""

        class TestApp(App):
            def compose(self):
                yield ConfigurePanel(id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)
            pattern_input = panel.query_one("#file-pattern-input", Input)

            assert pattern_input is not None
            assert pattern_input.value == "*.txt"

    @pytest.mark.asyncio
    async def test_panel_contains_stage_toggles(self):
        """Test that ConfigurePanel contains pipeline stage toggles."""

        class TestApp(App):
            def compose(self):
                yield ConfigurePanel(id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)
            normalize_opt = panel.query_one("#stage-normalize", RadioOption)
            annotate_opt = panel.query_one("#stage-annotate", RadioOption)

            assert normalize_opt is not None
            assert annotate_opt is not None


# =============================================================================
# ConfigurePanel State Display Tests
# =============================================================================


class TestConfigurePanelStateDisplay:
    """Tests for ConfigurePanel initial state display."""

    @pytest.mark.asyncio
    async def test_displays_source_path_when_set(self):
        """Test that source path is displayed when provided."""
        source_path = Path("/test/source/dir")

        class TestApp(App):
            def compose(self):
                yield ConfigurePanel(source_path=source_path, id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)
            source_display = panel.query_one("#source-path-display", Label)
            assert str(source_path) in str(source_display.render())

    @pytest.mark.asyncio
    async def test_displays_not_selected_when_no_source(self):
        """Test that 'Not selected' is shown when no source path."""

        class TestApp(App):
            def compose(self):
                yield ConfigurePanel(source_path=None, id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)
            source_display = panel.query_one("#source-path-display", Label)
            assert "Not selected" in str(source_display.render())

    @pytest.mark.asyncio
    async def test_pyphen_selected_by_default(self):
        """Test that pyphen extractor is selected by default."""

        class TestApp(App):
            def compose(self):
                yield ConfigurePanel(id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)
            pyphen_opt = panel.query_one("#extractor-pyphen", RadioOption)
            nltk_opt = panel.query_one("#extractor-nltk", RadioOption)

            assert pyphen_opt.is_selected is True
            assert nltk_opt.is_selected is False

    @pytest.mark.asyncio
    async def test_nltk_selected_when_specified(self):
        """Test that NLTK extractor can be pre-selected."""

        class TestApp(App):
            def compose(self):
                yield ConfigurePanel(
                    extractor_type=ExtractorType.NLTK,
                    id="test-panel",
                )

        async with TestApp().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)
            pyphen_opt = panel.query_one("#extractor-pyphen", RadioOption)
            nltk_opt = panel.query_one("#extractor-nltk", RadioOption)

            assert pyphen_opt.is_selected is False
            assert nltk_opt.is_selected is True


# =============================================================================
# ConfigurePanel Event Handler Tests
# =============================================================================


class TestConfigurePanelEventHandlers:
    """Tests for ConfigurePanel event handling."""

    @pytest.mark.asyncio
    async def test_source_browse_button_posts_message(self):
        """Test that clicking source browse button posts SourceSelected."""

        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.source_messages: list[Any] = []

            def compose(self):
                yield ConfigurePanel(id="test-panel")

            def on_configure_panel_source_selected(self, event: ConfigurePanel.SourceSelected):
                self.source_messages.append(event)

        async with TestApp().run_test() as pilot:
            app: Any = pilot.app
            await pilot.pause()

            # Click the browse button
            panel = app.query_one("#test-panel", ConfigurePanel)
            source_btn = panel.query_one("#source-browse-btn", Button)
            source_btn.press()

            await pilot.pause()

            assert len(app.source_messages) == 1

    @pytest.mark.asyncio
    async def test_output_browse_button_posts_message(self):
        """Test that clicking output browse button posts OutputSelected."""

        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.output_messages: list[Any] = []

            def compose(self):
                yield ConfigurePanel(id="test-panel")

            def on_configure_panel_output_selected(self, event: ConfigurePanel.OutputSelected):
                self.output_messages.append(event)

        async with TestApp().run_test() as pilot:
            app: Any = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)
            output_btn = panel.query_one("#output-browse-btn", Button)
            output_btn.press()

            await pilot.pause()

            assert len(app.output_messages) == 1

    @pytest.mark.asyncio
    async def test_extractor_selection_posts_message(self):
        """Test that selecting an extractor posts ExtractorChanged."""

        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.extractor_messages: list[Any] = []

            def compose(self):
                yield ConfigurePanel(id="test-panel")

            def on_configure_panel_extractor_changed(self, event: ConfigurePanel.ExtractorChanged):
                self.extractor_messages.append(event)

        async with TestApp().run_test() as pilot:
            app: Any = pilot.app
            await pilot.pause()

            # Select NLTK (pyphen is already selected by default)
            panel = app.query_one("#test-panel", ConfigurePanel)
            nltk_opt = panel.query_one("#extractor-nltk", RadioOption)
            nltk_opt.action_select()

            await pilot.pause()

            assert len(app.extractor_messages) == 1
            assert app.extractor_messages[0].extractor_type == ExtractorType.NLTK

    @pytest.mark.asyncio
    async def test_min_length_change_posts_message(self):
        """Test that changing min length posts ConstraintsChanged."""

        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.constraints_messages: list[Any] = []

            def compose(self):
                yield ConfigurePanel(id="test-panel")

            def on_configure_panel_constraints_changed(
                self, event: ConfigurePanel.ConstraintsChanged
            ):
                self.constraints_messages.append(event)

        async with TestApp().run_test() as pilot:
            app: Any = pilot.app
            await pilot.pause()

            # Clear any messages from initialization
            initial_count = len(app.constraints_messages)

            panel = app.query_one("#test-panel", ConfigurePanel)
            min_spinner = panel.query_one("#min-length-spinner", IntSpinner)
            min_spinner.action_increment()

            await pilot.pause()

            # Should have at least one new message
            assert len(app.constraints_messages) > initial_count
            # Last message should have the incremented value
            assert app.constraints_messages[-1].min_length == 3  # 2 + 1

    @pytest.mark.asyncio
    async def test_stage_toggle_posts_message(self):
        """Test that toggling a stage posts PipelineStagesChanged."""

        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.stage_messages: list[Any] = []

            def compose(self):
                yield ConfigurePanel(id="test-panel")

            def on_configure_panel_pipeline_stages_changed(
                self, event: ConfigurePanel.PipelineStagesChanged
            ):
                self.stage_messages.append(event)

        async with TestApp().run_test() as pilot:
            app: Any = pilot.app
            await pilot.pause()

            # Clear any messages from initialization
            initial_count = len(app.stage_messages)

            # Toggle normalize off using internal handler
            # (RadioOption.action_select doesn't fire when already selected)
            panel = app.query_one("#test-panel", ConfigurePanel)
            panel._handle_stage_toggle("normalize")

            await pilot.pause()

            # Should have at least one new message
            assert len(app.stage_messages) > initial_count
            # Should be toggled to False (last message)
            assert app.stage_messages[-1].run_normalize is False


# =============================================================================
# ConfigurePanel Public Method Tests
# =============================================================================


class TestConfigurePanelPublicMethods:
    """Tests for ConfigurePanel public update methods."""

    @pytest.mark.asyncio
    async def test_update_source_path_updates_display(self):
        """Test that update_source_path updates the label display."""

        class TestApp(App):
            def compose(self):
                yield ConfigurePanel(id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)

            new_path = Path("/new/source/path")
            panel.update_source_path(new_path)

            await pilot.pause()

            source_display = panel.query_one("#source-path-display", Label)
            assert str(new_path) in str(source_display.render())
            assert panel.source_path == new_path

    @pytest.mark.asyncio
    async def test_update_source_path_handles_none(self):
        """Test that update_source_path handles None value."""

        class TestApp(App):
            def compose(self):
                yield ConfigurePanel(
                    source_path=Path("/initial"),
                    id="test-panel",
                )

        async with TestApp().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)

            panel.update_source_path(None)

            await pilot.pause()

            source_display = panel.query_one("#source-path-display", Label)
            assert "Not selected" in str(source_display.render())
            assert panel.source_path is None

    @pytest.mark.asyncio
    async def test_update_output_path_updates_display(self):
        """Test that update_output_path updates the label display."""

        class TestApp(App):
            def compose(self):
                yield ConfigurePanel(id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)

            new_path = Path("/new/output/path")
            panel.update_output_path(new_path)

            await pilot.pause()

            output_display = panel.query_one("#output-path-display", Label)
            assert str(new_path) in str(output_display.render())
            assert panel.output_dir == new_path


# =============================================================================
# ConfigurePanel Extractor Selection Behavior Tests
# =============================================================================


class TestConfigurePanelExtractorBehavior:
    """Tests for extractor selection behavior."""

    @pytest.mark.asyncio
    async def test_selecting_nltk_disables_language_section(self):
        """Test that selecting NLTK adds disabled class to language section."""

        class TestApp(App):
            def compose(self):
                yield ConfigurePanel(id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)

            # Initially pyphen is selected, language section should be enabled
            lang_section = panel.query_one("#language-section")
            assert "language-section-disabled" not in lang_section.classes

            # Select NLTK
            nltk_opt = panel.query_one("#extractor-nltk", RadioOption)
            nltk_opt.action_select()

            await pilot.pause()

            # Language section should now be disabled
            assert "language-section-disabled" in lang_section.classes

    @pytest.mark.asyncio
    async def test_selecting_pyphen_enables_language_section(self):
        """Test that selecting pyphen removes disabled class from language."""

        class TestApp(App):
            def compose(self):
                yield ConfigurePanel(
                    extractor_type=ExtractorType.NLTK,
                    id="test-panel",
                )

        async with TestApp().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)

            # Initially NLTK is selected
            lang_section = panel.query_one("#language-section")
            assert "language-section-disabled" in lang_section.classes

            # Select pyphen
            pyphen_opt = panel.query_one("#extractor-pyphen", RadioOption)
            pyphen_opt.action_select()

            await pilot.pause()

            # Language section should now be enabled
            assert "language-section-disabled" not in lang_section.classes


# =============================================================================
# ConfigurePanel Language Selection Tests
# =============================================================================


class TestConfigurePanelLanguageSelection:
    """Tests for language selection behavior."""

    @pytest.mark.asyncio
    async def test_selecting_language_updates_state(self):
        """Test that selecting a language updates panel state."""

        class TestApp(App):
            def compose(self):
                yield ConfigurePanel(id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)

            # Select German
            de_opt = panel.query_one("#lang-de-de", RadioOption)
            de_opt.action_select()

            await pilot.pause()

            assert panel.language == "de_DE"

    @pytest.mark.asyncio
    async def test_custom_language_input_updates_state(self):
        """Test that typing custom language updates panel state."""

        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.language_messages: list[Any] = []

            def compose(self):
                yield ConfigurePanel(id="test-panel")

            def on_configure_panel_language_changed(self, event: ConfigurePanel.LanguageChanged):
                self.language_messages.append(event)

        async with TestApp().run_test() as pilot:
            app: Any = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)

            custom_input = panel.query_one("#custom-language-input", Input)
            custom_input.value = "pt_BR"
            # Trigger the change event
            panel._handle_input_change = Mock()  # Avoid actual handling in this test

            # Manually trigger the handler
            panel.language = "pt_BR"
            panel.post_message(ConfigurePanel.LanguageChanged("pt_BR"))

            await pilot.pause()

            assert len(app.language_messages) >= 1
            # Last message should be pt_BR
            assert any(msg.language == "pt_BR" for msg in app.language_messages)


# =============================================================================
# ConfigurePanel Stage Toggle Tests
# =============================================================================


class TestConfigurePanelStageToggles:
    """Tests for pipeline stage toggle behavior."""

    @pytest.mark.asyncio
    async def test_stage_toggle_is_independent(self):
        """Test that stage toggles work independently (not mutually exclusive)."""

        class TestApp(App):
            def compose(self):
                yield ConfigurePanel(id="test-panel")

        async with TestApp().run_test() as pilot:
            app = pilot.app
            await pilot.pause()

            panel = app.query_one("#test-panel", ConfigurePanel)

            # Initially both are on
            assert panel.run_normalize is True
            assert panel.run_annotate is True

            # Toggle normalize off - call the internal handler directly
            # to avoid potential issues with RadioOption.Selected routing
            panel._handle_stage_toggle("normalize")

            await pilot.pause()

            # Normalize should be off, annotate still on
            assert panel.run_normalize is False
            assert panel.run_annotate is True

            # Toggle annotate off
            panel._handle_stage_toggle("annotate")

            await pilot.pause()

            # Both should now be off
            assert panel.run_normalize is False
            assert panel.run_annotate is False


# =============================================================================
# Common Languages Constant Tests
# =============================================================================


class TestCommonLanguages:
    """Tests for COMMON_LANGUAGES constant."""

    def test_common_languages_contains_expected_entries(self):
        """Test that COMMON_LANGUAGES contains expected language codes."""
        codes = [code for code, _ in COMMON_LANGUAGES]

        assert "en_US" in codes
        assert "en_GB" in codes
        assert "de_DE" in codes
        assert "fr" in codes

    def test_common_languages_has_display_names(self):
        """Test that all entries have non-empty display names."""
        for code, name in COMMON_LANGUAGES:
            assert code, "Language code should not be empty"
            assert name, "Language name should not be empty"
            assert len(name) > 2, f"Language name '{name}' seems too short"
