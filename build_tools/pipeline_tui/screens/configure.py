"""
Configure tab panel for Pipeline TUI.

This module provides the ConfigurePanel widget which displays all configuration
options for the syllable extraction pipeline. It allows users to:

- Select source and output directories
- Choose extractor type (pyphen or NLTK)
- Configure language (for pyphen)
- Set syllable length constraints
- Toggle pipeline stages (normalize, annotate)

**Design Principles:**

- Uses shared tui_common controls for consistent UX
- Posts messages for state changes (handled by parent app)
- Clear visual grouping of related options
- Keyboard-navigable (Tab between controls, Enter/Space to activate)

**Message Flow:**

The panel posts custom messages when configuration changes. The parent app
handles these messages and updates the central PipelineState.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual import on
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Input, Label

from build_tools.pipeline_tui.core.state import ExtractorType
from build_tools.tui_common.controls import IntSpinner, RadioOption

if TYPE_CHECKING:
    from textual.app import ComposeResult


# =============================================================================
# Common Languages for Quick Selection
# =============================================================================

# Most commonly used languages for the language selector
# "auto" is the default - uses langdetect for automatic language detection
# Full list available in pyphen_syllable_extractor.languages
COMMON_LANGUAGES = [
    ("auto", "Auto-detect"),
    ("en_US", "English (US)"),
    ("en_GB", "English (UK)"),
    ("de_DE", "German"),
    ("fr", "French"),
    ("es", "Spanish"),
    ("it_IT", "Italian"),
    ("pt_BR", "Portuguese (Brazil)"),
    ("nl_NL", "Dutch"),
]


# =============================================================================
# ConfigurePanel Widget
# =============================================================================


class ConfigurePanel(VerticalScroll):
    """
    Configuration panel for pipeline settings.

    This widget contains all the configuration controls for setting up
    a syllable extraction pipeline run. It is designed to be composed
    within a TabPane in the main application.

    **Layout Structure:**

    .. code-block:: text

        ┌─────────────────────────────────────────────────────────┐
        │ DIRECTORIES                                              │
        │   Source: /path/to/source               [Browse]         │
        │   Output: /path/to/output               [Browse]         │
        ├─────────────────────────────────────────────────────────┤
        │ EXTRACTOR                                                │
        │   [x] Pyphen: Multi-language typographic hyphenation     │
        │   [ ] NLTK: English-only phonetic splitting              │
        ├─────────────────────────────────────────────────────────┤
        │ LANGUAGE (Pyphen only)                                   │
        │   [x] English (US)  [ ] German  [ ] French  [ ] Other    │
        │   Custom: [________]                                     │
        ├─────────────────────────────────────────────────────────┤
        │ CONSTRAINTS                                              │
        │   Min Length: [2]                                        │
        │   Max Length: [8]                                        │
        │   File Pattern: [*.txt]                                  │
        ├─────────────────────────────────────────────────────────┤
        │ PIPELINE STAGES                                          │
        │   [x] Run Normalization: Clean and deduplicate syllables │
        │   [x] Run Annotation: Add phonetic features              │
        └─────────────────────────────────────────────────────────┘

    Attributes:
        source_path: Currently selected source directory
        output_dir: Currently selected output directory
        extractor_type: Selected extractor (PYPHEN or NLTK)
        language: Language code for pyphen (e.g., "en_US")
        min_syllable_length: Minimum syllable length filter
        max_syllable_length: Maximum syllable length filter
        file_pattern: Glob pattern for input files
        run_normalize: Whether to run normalization step
        run_annotate: Whether to run annotation step

    Messages:
        - :class:`SourceSelected`: Posted when source directory changes
        - :class:`OutputSelected`: Posted when output directory changes
        - :class:`ExtractorChanged`: Posted when extractor type changes
        - :class:`LanguageChanged`: Posted when language changes
        - :class:`ConstraintsChanged`: Posted when length constraints change
        - :class:`PipelineStagesChanged`: Posted when stage toggles change
    """

    # -------------------------------------------------------------------------
    # Custom Messages for Configuration Changes
    # -------------------------------------------------------------------------

    class SourceSelected(Message):
        """Posted when the source directory is selected via browse button."""

        def __init__(self) -> None:
            """Initialize the SourceSelected message."""
            super().__init__()

    class OutputSelected(Message):
        """Posted when the output directory is selected via browse button."""

        def __init__(self) -> None:
            """Initialize the OutputSelected message."""
            super().__init__()

    class ExtractorChanged(Message):
        """
        Posted when the extractor type changes.

        Attributes:
            extractor_type: The newly selected extractor type
        """

        def __init__(self, extractor_type: ExtractorType) -> None:
            """
            Initialize the ExtractorChanged message.

            Args:
                extractor_type: The newly selected extractor type
            """
            super().__init__()
            self.extractor_type = extractor_type

    class LanguageChanged(Message):
        """
        Posted when the language selection changes.

        Attributes:
            language: The newly selected language code (e.g., "en_US")
        """

        def __init__(self, language: str) -> None:
            """
            Initialize the LanguageChanged message.

            Args:
                language: The language code
            """
            super().__init__()
            self.language = language

    class ConstraintsChanged(Message):
        """
        Posted when syllable length constraints change.

        Attributes:
            min_length: The new minimum syllable length
            max_length: The new maximum syllable length
            file_pattern: The file glob pattern
        """

        def __init__(self, min_length: int, max_length: int, file_pattern: str) -> None:
            """
            Initialize the ConstraintsChanged message.

            Args:
                min_length: Minimum syllable length
                max_length: Maximum syllable length
                file_pattern: File glob pattern
            """
            super().__init__()
            self.min_length = min_length
            self.max_length = max_length
            self.file_pattern = file_pattern

    class PipelineStagesChanged(Message):
        """
        Posted when pipeline stage toggles change.

        Attributes:
            run_normalize: Whether to run normalization
            run_annotate: Whether to run annotation
        """

        def __init__(self, run_normalize: bool, run_annotate: bool) -> None:
            """
            Initialize the PipelineStagesChanged message.

            Args:
                run_normalize: Whether normalization is enabled
                run_annotate: Whether annotation is enabled
            """
            super().__init__()
            self.run_normalize = run_normalize
            self.run_annotate = run_annotate

    # -------------------------------------------------------------------------
    # Default CSS Styling
    # -------------------------------------------------------------------------

    DEFAULT_CSS = """
    ConfigurePanel {
        width: 1fr;
        height: 1fr;
        padding: 1 2;
    }

    /* Section containers */
    .config-section {
        width: 100%;
        height: auto;
        margin-bottom: 1;
        padding: 0 1;
        border: solid $primary-darken-2;
    }

    .section-header {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    /* Directory selection row */
    .dir-row {
        height: 3;
        width: 100%;
        margin-bottom: 0;
    }

    .dir-label {
        width: 10;
        height: 3;
        content-align: center middle;
        text-align: right;
        padding-right: 1;
    }

    .dir-path {
        width: 1fr;
        height: 3;
        background: $boost;
        padding: 1;
        content-align: left middle;
        color: $text;
    }

    .dir-path-empty {
        color: $text-muted;
        text-style: italic;
    }

    .dir-button {
        width: 12;
        height: 3;
        margin-left: 1;
    }

    /* Extractor options */
    .extractor-option {
        height: auto;
        padding: 0 1;
    }

    /* Language selector */
    .language-row {
        height: auto;
        width: 100%;
    }

    .language-grid {
        width: 100%;
        height: auto;
    }

    .language-option {
        width: auto;
        margin-right: 2;
    }

    .custom-language-row {
        height: 3;
        margin-top: 1;
    }

    .custom-language-label {
        width: 10;
        height: 3;
        content-align: center middle;
        text-align: right;
        padding-right: 1;
    }

    .custom-language-input {
        width: 15;
        height: 3;
    }

    /* Language section disabled state */
    .language-section-disabled {
        opacity: 0.5;
    }

    .language-section-disabled .language-option {
        color: $text-muted;
    }

    /* Constraints section */
    .constraints-row {
        height: auto;
        width: 100%;
    }

    .pattern-row {
        height: 3;
        margin-top: 1;
    }

    .pattern-label {
        width: 15;
        height: 3;
        content-align: center middle;
        text-align: right;
        padding-right: 1;
    }

    .pattern-input {
        width: 15;
        height: 3;
    }

    /* Pipeline stages */
    .stage-option {
        height: auto;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        source_path: Path | None = None,
        output_dir: Path | None = None,
        extractor_type: ExtractorType = ExtractorType.PYPHEN,
        language: str = "auto",
        min_syllable_length: int = 2,
        max_syllable_length: int = 8,
        file_pattern: str = "*.txt",
        run_normalize: bool = True,
        run_annotate: bool = True,
        *args,
        **kwargs,
    ) -> None:
        """
        Initialize the ConfigurePanel with current configuration.

        Args:
            source_path: Current source directory path
            output_dir: Current output directory path
            extractor_type: Current extractor type selection
            language: Current language code for pyphen
            min_syllable_length: Current minimum syllable length
            max_syllable_length: Current maximum syllable length
            file_pattern: Current file glob pattern
            run_normalize: Whether normalization is enabled
            run_annotate: Whether annotation is enabled
            *args: Additional positional arguments passed to Static
            **kwargs: Additional keyword arguments passed to Static
        """
        super().__init__(*args, **kwargs)

        # Store initial configuration values
        self.source_path = source_path
        self.output_dir = output_dir
        self.extractor_type = extractor_type
        self.language = language
        self.min_syllable_length = min_syllable_length
        self.max_syllable_length = max_syllable_length
        self.file_pattern = file_pattern
        self.run_normalize = run_normalize
        self.run_annotate = run_annotate

    def compose(self) -> ComposeResult:
        """
        Compose the configuration panel layout.

        Creates a vertically scrollable panel with grouped configuration
        sections for directories, extractor, language, constraints, and
        pipeline stages.

        Yields:
            Configuration section widgets
        """
        # -----------------------------------------------------------------
        # DIRECTORIES Section
        # -----------------------------------------------------------------
        with Container(classes="config-section", id="directories-section"):
            yield Label("DIRECTORIES", classes="section-header")

            # Source directory row
            with Horizontal(classes="dir-row"):
                yield Label("Source:", classes="dir-label")
                source_text = str(self.source_path) if self.source_path else "Not selected"
                source_classes = "dir-path" if self.source_path else "dir-path dir-path-empty"
                yield Label(source_text, classes=source_classes, id="source-path-display")
                yield Button("Browse", classes="dir-button", id="source-browse-btn")

            # Output directory row
            with Horizontal(classes="dir-row"):
                yield Label("Output:", classes="dir-label")
                output_text = str(self.output_dir) if self.output_dir else "Not selected"
                output_classes = "dir-path" if self.output_dir else "dir-path dir-path-empty"
                yield Label(output_text, classes=output_classes, id="output-path-display")
                yield Button("Browse", classes="dir-button", id="output-browse-btn")

        # -----------------------------------------------------------------
        # EXTRACTOR Section
        # -----------------------------------------------------------------
        with Container(classes="config-section", id="extractor-section"):
            yield Label("EXTRACTOR", classes="section-header")

            # Extractor type options using RadioOption
            yield RadioOption(
                option_name="pyphen",
                description="Multi-language typographic hyphenation (40+ languages)",
                is_selected=(self.extractor_type == ExtractorType.PYPHEN),
                classes="extractor-option",
                id="extractor-pyphen",
            )
            yield RadioOption(
                option_name="nltk",
                description="English-only phonetic splitting (CMUDict)",
                is_selected=(self.extractor_type == ExtractorType.NLTK),
                classes="extractor-option",
                id="extractor-nltk",
            )

        # -----------------------------------------------------------------
        # LANGUAGE Section (Pyphen only)
        # -----------------------------------------------------------------
        # Determine if language section should be disabled (NLTK selected)
        lang_disabled = self.extractor_type == ExtractorType.NLTK
        lang_section_classes = (
            "config-section language-section-disabled" if lang_disabled else "config-section"
        )

        with Container(classes=lang_section_classes, id="language-section"):
            yield Label("LANGUAGE (Pyphen only)", classes="section-header")

            # Common language quick-select options
            with Horizontal(classes="language-grid"):
                # Create radio options for common languages
                for code, name in COMMON_LANGUAGES[:4]:  # First 4 common languages
                    yield RadioOption(
                        option_name=code,
                        description=name,
                        is_selected=(self.language == code),
                        classes="language-option",
                        id=f"lang-{code.replace('_', '-').lower()}",
                    )

            # Custom language input for languages not in quick-select
            with Horizontal(classes="custom-language-row"):
                yield Label("Custom:", classes="custom-language-label")
                # Show current language if not in common list
                initial_custom = ""
                if self.language not in [code for code, _ in COMMON_LANGUAGES[:4]]:
                    initial_custom = self.language
                yield Input(
                    placeholder="e.g., pt_BR",
                    value=initial_custom,
                    classes="custom-language-input",
                    id="custom-language-input",
                )

        # -----------------------------------------------------------------
        # CONSTRAINTS Section
        # -----------------------------------------------------------------
        with Container(classes="config-section", id="constraints-section"):
            yield Label("CONSTRAINTS", classes="section-header")

            # Min/Max syllable length spinners
            with Vertical(classes="constraints-row"):
                yield IntSpinner(
                    label="Min Length",
                    value=self.min_syllable_length,
                    min_val=1,
                    max_val=10,
                    id="min-length-spinner",
                )
                yield IntSpinner(
                    label="Max Length",
                    value=self.max_syllable_length,
                    min_val=1,
                    max_val=20,
                    id="max-length-spinner",
                )

            # File pattern input
            with Horizontal(classes="pattern-row"):
                yield Label("File Pattern:", classes="pattern-label")
                yield Input(
                    value=self.file_pattern,
                    placeholder="*.txt",
                    classes="pattern-input",
                    id="file-pattern-input",
                )

        # -----------------------------------------------------------------
        # PIPELINE STAGES Section
        # -----------------------------------------------------------------
        with Container(classes="config-section", id="stages-section"):
            yield Label("PIPELINE STAGES", classes="section-header")

            yield RadioOption(
                option_name="normalize",
                description="Clean and deduplicate syllables after extraction",
                is_selected=self.run_normalize,
                classes="stage-option",
                id="stage-normalize",
            )
            yield RadioOption(
                option_name="annotate",
                description="Add phonetic feature annotations",
                is_selected=self.run_annotate,
                classes="stage-option",
                id="stage-annotate",
            )

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    @on(Button.Pressed, "#source-browse-btn")
    def on_source_browse_pressed(self, event: Button.Pressed) -> None:
        """
        Handle source browse button press.

        Posts SourceSelected message to trigger directory browser in parent app.
        The parent app handles the actual directory selection modal.

        Args:
            event: Button press event
        """
        event.stop()  # Prevent event from bubbling
        self.post_message(self.SourceSelected())

    @on(Button.Pressed, "#output-browse-btn")
    def on_output_browse_pressed(self, event: Button.Pressed) -> None:
        """
        Handle output browse button press.

        Posts OutputSelected message to trigger directory browser in parent app.

        Args:
            event: Button press event
        """
        event.stop()
        self.post_message(self.OutputSelected())

    @on(RadioOption.Selected)
    def on_radio_option_selected(self, event: RadioOption.Selected) -> None:
        """
        Handle radio option selection events.

        Routes the selection to appropriate handler based on widget ID:
        - extractor-*: Update extractor type
        - lang-*: Update language selection
        - stage-*: Toggle pipeline stage

        Args:
            event: Radio option selected event
        """
        widget_id = event.widget_id or ""

        # Handle extractor type selection
        if widget_id.startswith("extractor-"):
            self._handle_extractor_selection(event.option_name)

        # Handle language selection
        elif widget_id.startswith("lang-"):
            self._handle_language_selection(event.option_name)

        # Handle pipeline stage toggles
        elif widget_id.startswith("stage-"):
            self._handle_stage_toggle(event.option_name)

    def _handle_extractor_selection(self, option_name: str) -> None:
        """
        Handle extractor type selection change.

        Updates internal state, toggles radio button display, and
        enables/disables the language section based on extractor type.

        Args:
            option_name: Selected extractor name ("pyphen" or "nltk")
        """
        # Determine new extractor type
        new_type = ExtractorType.PYPHEN if option_name == "pyphen" else ExtractorType.NLTK

        # Update radio button states
        try:
            pyphen_opt = self.query_one("#extractor-pyphen", RadioOption)
            nltk_opt = self.query_one("#extractor-nltk", RadioOption)
            pyphen_opt.set_selected(new_type == ExtractorType.PYPHEN)
            nltk_opt.set_selected(new_type == ExtractorType.NLTK)
        except Exception:  # nosec B110 - Widget may not exist
            pass

        # Update language section enabled state
        try:
            lang_section = self.query_one("#language-section", Container)
            if new_type == ExtractorType.NLTK:
                lang_section.add_class("language-section-disabled")
            else:
                lang_section.remove_class("language-section-disabled")
        except Exception:  # nosec B110 - Widget may not exist
            pass

        # Update internal state and post message
        self.extractor_type = new_type
        self.post_message(self.ExtractorChanged(new_type))

    def _handle_language_selection(self, language_code: str) -> None:
        """
        Handle language selection change from quick-select options.

        Updates radio button states and posts language change message.

        Args:
            language_code: Selected language code (e.g., "en_US")
        """
        # Update radio button states for all language options
        for code, _ in COMMON_LANGUAGES[:4]:
            try:
                opt_id = f"#lang-{code.replace('_', '-').lower()}"
                opt = self.query_one(opt_id, RadioOption)
                opt.set_selected(code == language_code)
            except Exception:  # nosec B110 - Widget may not exist
                pass

        # Clear custom input when selecting a quick-select option
        try:
            custom_input = self.query_one("#custom-language-input", Input)
            custom_input.value = ""
        except Exception:  # nosec B110 - Widget may not exist
            pass

        # Update internal state and post message
        self.language = language_code
        self.post_message(self.LanguageChanged(language_code))

    def _handle_stage_toggle(self, stage_name: str) -> None:
        """
        Handle pipeline stage toggle.

        Unlike extractor/language, stages are independent toggles (checkboxes),
        not mutually exclusive radio buttons. Clicking toggles the state.

        Args:
            stage_name: Stage name ("normalize" or "annotate")
        """
        # Toggle the appropriate stage
        if stage_name == "normalize":
            self.run_normalize = not self.run_normalize
            try:
                opt = self.query_one("#stage-normalize", RadioOption)
                opt.set_selected(self.run_normalize)
            except Exception:  # nosec B110 - Widget may not exist
                pass

        elif stage_name == "annotate":
            self.run_annotate = not self.run_annotate
            try:
                opt = self.query_one("#stage-annotate", RadioOption)
                opt.set_selected(self.run_annotate)
            except Exception:  # nosec B110 - Widget may not exist
                pass

        # Post stage change message
        self.post_message(self.PipelineStagesChanged(self.run_normalize, self.run_annotate))

    @on(Input.Changed)
    def on_input_changed(self, event: Input.Changed) -> None:
        """
        Handle input field changes.

        Routes input changes to appropriate handler based on widget ID:
        - custom-language-input: Update language setting
        - file-pattern-input: Update file pattern

        Args:
            event: Input change event
        """
        # Get the input widget ID from the event
        input_id = event.input.id if event.input else None

        if input_id == "custom-language-input":
            self._handle_custom_language_input(event.value)
        elif input_id == "file-pattern-input":
            self._handle_file_pattern_input(event.value)

    def _handle_custom_language_input(self, value: str) -> None:
        """
        Handle custom language input changes.

        When user types in custom language field, deselects quick-select
        options and updates the language setting.

        Args:
            value: New input value
        """
        custom_lang = value.strip()

        if custom_lang:
            # Deselect all quick-select language options
            for code, _ in COMMON_LANGUAGES[:4]:
                try:
                    opt_id = f"#lang-{code.replace('_', '-').lower()}"
                    opt = self.query_one(opt_id, RadioOption)
                    opt.set_selected(False)
                except Exception:  # nosec B110 - Widget may not exist
                    pass

            # Update language and post message
            self.language = custom_lang
            self.post_message(self.LanguageChanged(custom_lang))

    def _handle_file_pattern_input(self, value: str) -> None:
        """
        Handle file pattern input changes.

        Posts constraints changed message with updated pattern.

        Args:
            value: New input value
        """
        self.file_pattern = value.strip() or "*.txt"
        self.post_message(
            self.ConstraintsChanged(
                self.min_syllable_length,
                self.max_syllable_length,
                self.file_pattern,
            )
        )

    @on(IntSpinner.Changed)
    def on_spinner_changed(self, event: IntSpinner.Changed) -> None:
        """
        Handle IntSpinner value changes.

        Routes spinner changes to update constraints based on widget_id.

        Args:
            event: Spinner change event
        """
        widget_id = event.widget_id

        if widget_id == "min-length-spinner":
            self.min_syllable_length = event.value
            self.post_message(
                self.ConstraintsChanged(
                    self.min_syllable_length,
                    self.max_syllable_length,
                    self.file_pattern,
                )
            )
        elif widget_id == "max-length-spinner":
            self.max_syllable_length = event.value
            self.post_message(
                self.ConstraintsChanged(
                    self.min_syllable_length,
                    self.max_syllable_length,
                    self.file_pattern,
                )
            )

    # -------------------------------------------------------------------------
    # Public Methods for External Updates
    # -------------------------------------------------------------------------

    def update_source_path(self, path: Path | None) -> None:
        """
        Update the displayed source path.

        Called by parent app after directory selection.

        Args:
            path: New source path, or None if cleared
        """
        self.source_path = path
        try:
            display = self.query_one("#source-path-display", Label)
            if path:
                display.update(str(path))
                display.remove_class("dir-path-empty")
            else:
                display.update("Not selected")
                display.add_class("dir-path-empty")
        except Exception:  # nosec B110 - Widget may not exist
            pass

    def update_output_path(self, path: Path | None) -> None:
        """
        Update the displayed output path.

        Called by parent app after directory selection.

        Args:
            path: New output path, or None if cleared
        """
        self.output_dir = path
        try:
            display = self.query_one("#output-path-display", Label)
            if path:
                display.update(str(path))
                display.remove_class("dir-path-empty")
            else:
                display.update("Not selected")
                display.add_class("dir-path-empty")
        except Exception:  # nosec B110 - Widget may not exist
            pass
