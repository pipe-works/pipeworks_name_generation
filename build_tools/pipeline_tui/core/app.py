"""
Main application class for Pipeline TUI.

This module contains the PipelineTuiApp class which is the entry point
for the Textual application.

**Application Structure:**

The app uses a tabbed interface with three main screens:

1. **Configure** - Set up extraction parameters
2. **Monitor** - Watch job progress and logs
3. **History** - Browse previous pipeline runs

**Keybindings:**

- ``q`` / ``Ctrl+Q``: Quit application
- ``?`` / ``F1``: Show help
- ``1``: Switch to Configure tab
- ``2``: Switch to Monitor tab
- ``3``: Switch to History tab
- ``r``: Run pipeline (when configured)
- ``c``: Cancel running job
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import Footer, Header, Label, Static, TabbedContent, TabPane

from build_tools.pipeline_tui.core.state import ExtractorType, JobStatus, PipelineState
from build_tools.pipeline_tui.services.pipeline import PipelineExecutor

if TYPE_CHECKING:
    from build_tools.pipeline_tui.screens.configure import ConfigurePanel


class PipelineTuiApp(App):
    """
    Main application for Pipeline Build Tools TUI.

    A Textual application providing an interactive interface for
    running syllable extraction, normalization, and annotation pipelines.

    Attributes:
        state: Application state (config, job status, UI state)
        theme: Color theme name

    Keybindings:
        - ``q``: Quit application
        - ``?``: Show help screen
        - ``1``/``2``/``3``: Switch tabs
        - ``r``: Run pipeline
        - ``c``: Cancel job
        - ``s``: Select source directory
        - ``o``: Select output directory
    """

    # -------------------------------------------------------------------------
    # Application metadata
    # -------------------------------------------------------------------------
    TITLE = "Pipeline Build Tools"
    SUB_TITLE = "Syllable Extraction Pipeline Manager"

    # -------------------------------------------------------------------------
    # Global keybindings (priority=True ensures they work even with focused widgets)
    # -------------------------------------------------------------------------
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("question_mark", "help", "Help", priority=True),
        Binding("1", "tab_configure", "Configure", priority=True),
        Binding("2", "tab_monitor", "Monitor", priority=True),
        Binding("3", "tab_history", "History", priority=True),
        Binding("r", "run_pipeline", "Run", priority=True),
        Binding("c", "cancel_job", "Cancel", priority=True),
        Binding("d", "select_source", "Directory", priority=True),
        Binding("f", "select_files", "Select", priority=True),
        Binding("o", "select_output", "Output", priority=True),
    ]

    # -------------------------------------------------------------------------
    # Default CSS styling
    # -------------------------------------------------------------------------
    DEFAULT_CSS = """
    PipelineTuiApp {
        background: $surface;
    }

    #main-container {
        width: 100%;
        height: 100%;
    }

    .status-bar {
        height: 3;
        background: $panel;
        border: solid $primary;
        padding: 0 1;
    }

    .status-label {
        width: 1fr;
    }

    /* Ensure TabPane content fills available space */
    TabPane {
        height: 1fr;
        width: 1fr;
    }

    ContentSwitcher {
        height: 1fr;
        width: 1fr;
    }

    .placeholder-content {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        source_dir: Path | None = None,
        output_dir: Path | None = None,
        theme: str = "nord",
    ) -> None:
        """
        Initialize the Pipeline TUI application.

        Args:
            source_dir: Initial source directory (optional)
            output_dir: Initial output directory (optional)
            theme: Color theme name (default: "nord")
        """
        super().__init__()
        self.theme = theme

        # Initialize application state
        self.state = PipelineState()

        # Initialize pipeline executor
        self._executor = PipelineExecutor()

        # Apply initial directories if provided
        if source_dir:
            self.state.config.source_path = source_dir
            self.state.last_source_dir = source_dir
        if output_dir:
            self.state.config.output_dir = output_dir
            self.state.last_output_dir = output_dir

    def compose(self) -> ComposeResult:
        """
        Compose the application layout.

        Layout:
        - Header with title
        - Status bar showing current config summary
        - Tabbed content (Configure, Monitor, History)
        - Footer with keybinding hints

        Yields:
            Application widget tree
        """
        yield Header()

        with Container(id="main-container"):
            # Status bar showing current configuration
            with Horizontal(classes="status-bar"):
                yield Label(
                    self._get_status_text(),
                    classes="status-label",
                    id="status-label",
                )

            # Main tabbed interface
            with TabbedContent(initial="configure"):
                with TabPane("Configure", id="configure"):
                    yield from self._compose_configure_tab()

                with TabPane("Monitor", id="monitor"):
                    yield from self._compose_monitor_tab()

                with TabPane("History", id="history"):
                    yield from self._compose_history_tab()

        yield Footer()

    def _compose_configure_tab(self) -> ComposeResult:
        """
        Compose the Configure tab content.

        This tab contains the ConfigurePanel widget which provides:
        - Source/output directory selection
        - Extractor type selection (pyphen/NLTK)
        - Language selection for pyphen
        - Syllable length constraints
        - Pipeline stage toggles (normalize, annotate)

        Yields:
            ConfigurePanel widget initialized with current state
        """
        # Lazy import to avoid circular dependency
        from build_tools.pipeline_tui.screens.configure import ConfigurePanel

        # Create ConfigurePanel with current state values
        yield ConfigurePanel(
            source_path=self.state.config.source_path,
            output_dir=self.state.config.output_dir,
            extractor_type=self.state.config.extractor_type,
            language=self.state.config.language,
            min_syllable_length=self.state.config.min_syllable_length,
            max_syllable_length=self.state.config.max_syllable_length,
            file_pattern=self.state.config.file_pattern,
            run_normalize=self.state.run_normalize,
            run_annotate=self.state.run_annotate,
            id="configure-panel",
        )

    def _compose_monitor_tab(self) -> ComposeResult:
        """
        Compose the Monitor tab content.

        This tab will contain:
        - Job status indicator
        - Progress bar
        - Current stage display
        - Log output area
        - Cancel button

        Yields:
            Monitor tab widgets
        """
        # Placeholder - will be replaced with actual monitoring widgets
        yield Static(
            "Monitor Tab\n\n"
            "Job status and progress will be shown here\n"
            "when a pipeline job is running.\n\n"
            "(Full implementation coming soon)",
            classes="placeholder-content",
        )

    def _compose_history_tab(self) -> ComposeResult:
        """
        Compose the History tab content.

        This tab will contain:
        - List of previous pipeline runs from corpus_db
        - Run details panel
        - Output file browser
        - Re-run button

        Yields:
            History tab widgets
        """
        # Placeholder - will be replaced with history browser
        yield Static(
            "History Tab\n\n"
            "Previous pipeline runs will be listed here\n"
            "with details and output browsing.\n\n"
            "(Full implementation coming soon)",
            classes="placeholder-content",
        )

    def _get_status_text(self) -> str:
        """
        Generate status bar text from current state.

        Returns:
            Formatted status string showing config summary
        """
        config = self.state.config

        # Determine source display
        if config.selected_files:
            count = len(config.selected_files)
            source = f"{count} file{'s' if count != 1 else ''}"
        elif config.source_path:
            source = config.source_path.name
        else:
            source = "Not selected"

        extractor = config.extractor_type.name.lower()
        status = self.state.job.status.name.lower()

        return f"Source: {source} | Extractor: {extractor} | Status: {status}"

    def _update_status(self) -> None:
        """Update the status bar with current state."""
        try:
            status_label = self.query_one("#status-label", Label)
            status_label.update(self._get_status_text())
        except Exception:  # nosec B110 - Widget may not exist yet
            pass

    # -------------------------------------------------------------------------
    # Tab switching actions
    # -------------------------------------------------------------------------

    def action_tab_configure(self) -> None:
        """Switch to Configure tab."""
        tabbed = self.query_one(TabbedContent)
        tabbed.active = "configure"

    def action_tab_monitor(self) -> None:
        """Switch to Monitor tab."""
        tabbed = self.query_one(TabbedContent)
        tabbed.active = "monitor"

    def action_tab_history(self) -> None:
        """Switch to History tab."""
        tabbed = self.query_one(TabbedContent)
        tabbed.active = "history"

    # -------------------------------------------------------------------------
    # Pipeline actions
    # -------------------------------------------------------------------------

    @work
    async def action_select_source(self) -> None:
        """
        Open directory browser to select source.

        Uses shared DirectoryBrowserScreen with source validator.
        Runs as a worker to support push_screen_wait.
        """
        from build_tools.pipeline_tui.services.validators import validate_source_directory
        from build_tools.tui_common.controls import DirectoryBrowserScreen

        result = await self.push_screen_wait(
            DirectoryBrowserScreen(
                title="Select Source Directory",
                validator=validate_source_directory,
                initial_dir=self.state.last_source_dir,
                help_text="Select a directory containing .txt files for extraction.",
                root_dir=Path.home(),  # Allow navigating up to home
            )
        )

        if result:
            self.state.config.source_path = result
            self.state.config.selected_files = []  # Clear file selection when directory is set
            self.state.last_source_dir = result
            self._update_status()
            self.notify(f"Source selected: {result.name}")

            # Update the ConfigurePanel display
            try:
                from build_tools.pipeline_tui.screens.configure import ConfigurePanel

                panel = self.query_one("#configure-panel", ConfigurePanel)
                panel.update_source_path(result)
            except Exception:  # nosec B110 - Panel may not exist yet
                pass

    @work
    async def action_select_output(self) -> None:
        """
        Open directory browser to select output directory.

        Uses shared DirectoryBrowserScreen with output validator.
        Runs as a worker to support push_screen_wait.
        """
        from build_tools.pipeline_tui.services.validators import validate_output_directory
        from build_tools.tui_common.controls import DirectoryBrowserScreen

        result = await self.push_screen_wait(
            DirectoryBrowserScreen(
                title="Select Output Directory",
                validator=validate_output_directory,
                initial_dir=self.state.last_output_dir,
                help_text="Select output directory for pipeline results.",
                root_dir=Path.home(),  # Allow navigating up to home
            )
        )

        if result:
            self.state.config.output_dir = result
            self.state.last_output_dir = result
            self._update_status()
            self.notify(f"Output selected: {result.name}")

            # Update the ConfigurePanel display
            try:
                from build_tools.pipeline_tui.screens.configure import ConfigurePanel

                panel = self.query_one("#configure-panel", ConfigurePanel)
                panel.update_output_path(result)
            except Exception:  # nosec B110 - Panel may not exist yet
                pass

    @work
    async def action_select_files(self) -> None:
        """
        Open file selector to choose specific files.

        Uses FileSelectorScreen for selecting individual files.
        Runs as a worker to support push_screen_wait.
        """
        from build_tools.pipeline_tui.screens.file_selector import FileSelectorScreen

        # Determine initial directory
        initial_dir = self.state.last_source_dir
        if self.state.config.source_path and self.state.config.source_path.exists():
            initial_dir = self.state.config.source_path

        result = await self.push_screen_wait(
            FileSelectorScreen(
                initial_dir=initial_dir,
                file_pattern=self.state.config.file_pattern,
                title="Select Source Files",
                root_dir=Path.home(),  # Allow navigating up to home
            )
        )

        if result:
            # Store selected files in config
            self.state.config.selected_files = result
            # Update last_source_dir to the common parent if files are in same dir
            if result:
                self.state.last_source_dir = result[0].parent
            self._update_status()
            count = len(result)
            self.notify(f"Selected {count} file{'s' if count != 1 else ''}")

            # Update the ConfigurePanel display
            try:
                from build_tools.pipeline_tui.screens.configure import ConfigurePanel

                panel = self.query_one("#configure-panel", ConfigurePanel)
                panel.update_selected_files(result)
            except Exception:  # nosec B110 - Panel may not exist yet
                pass

    def action_run_pipeline(self) -> None:
        """
        Start pipeline execution.

        Validates configuration and starts the pipeline job.
        """
        # Check if a job is already running
        if self.state.job.status == JobStatus.RUNNING:
            self.notify("A job is already running", severity="warning")
            return

        is_valid, error = self.state.config.is_valid()
        if not is_valid:
            self.notify(f"Cannot run: {error}", severity="error")
            return

        # Switch to monitor tab
        self.action_tab_monitor()

        # Start the job
        self.state.start_job()
        self._update_status()
        self.notify("Pipeline job started")

        # Actually run the pipeline
        self._run_pipeline_async()

    def action_cancel_job(self) -> None:
        """Cancel the currently running job."""
        if self.state.job.status != JobStatus.RUNNING:
            self.notify("No job is running", severity="warning")
            return

        # Cancel the executor
        self._cancel_pipeline_async()
        self.notify("Cancelling job...")

    def action_help(self) -> None:
        """Show help screen."""
        # TODO: Implement help screen
        self.notify("Help screen coming soon")

    # -------------------------------------------------------------------------
    # ConfigurePanel Message Handlers
    # -------------------------------------------------------------------------
    # Note: Using Textual's auto-routing convention (on_<widget>_<message>)
    # instead of @on decorators to avoid circular import issues.

    def on_configure_panel_source_selected(self, event: "ConfigurePanel.SourceSelected") -> None:
        """
        Handle source directory selection request from ConfigurePanel.

        Triggers the directory browser modal via the existing action.
        The browse button in ConfigurePanel posts this message.

        Args:
            event: Source selected event
        """
        # Use the existing action which handles the directory browser
        self.action_select_source()

    def on_configure_panel_output_selected(self, event: "ConfigurePanel.OutputSelected") -> None:
        """
        Handle output directory selection request from ConfigurePanel.

        Triggers the directory browser modal via the existing action.

        Args:
            event: Output selected event
        """
        self.action_select_output()

    def on_configure_panel_files_selected(self, event: "ConfigurePanel.FilesSelected") -> None:
        """
        Handle file selection request from ConfigurePanel.

        Opens the file selector modal for choosing specific files.

        Args:
            event: Files selected event
        """
        self.action_select_files()

    def on_configure_panel_extractor_changed(
        self, event: "ConfigurePanel.ExtractorChanged"
    ) -> None:
        """
        Handle extractor type change from ConfigurePanel.

        Updates the application state with the new extractor type.
        NLTK is English-only, so language setting is ignored for NLTK.

        Args:
            event: Extractor changed event with new extractor type
        """
        self.state.config.extractor_type = event.extractor_type
        self._update_status()

        # Notify user of the change
        extractor_name = "pyphen" if event.extractor_type == ExtractorType.PYPHEN else "NLTK"
        self.notify(f"Extractor: {extractor_name}")

    def on_configure_panel_language_changed(self, event: "ConfigurePanel.LanguageChanged") -> None:
        """
        Handle language selection change from ConfigurePanel.

        Updates the application state with the new language code.
        Only applies to pyphen extractor.

        Args:
            event: Language changed event with new language code
        """
        self.state.config.language = event.language
        self.notify(f"Language: {event.language}")

    def on_configure_panel_constraints_changed(
        self, event: "ConfigurePanel.ConstraintsChanged"
    ) -> None:
        """
        Handle constraints change from ConfigurePanel.

        Updates syllable length constraints and file pattern in state.

        Args:
            event: Constraints changed event with new values
        """
        self.state.config.min_syllable_length = event.min_length
        self.state.config.max_syllable_length = event.max_length
        self.state.config.file_pattern = event.file_pattern

    def on_configure_panel_pipeline_stages_changed(
        self, event: "ConfigurePanel.PipelineStagesChanged"
    ) -> None:
        """
        Handle pipeline stage toggle changes from ConfigurePanel.

        Updates which pipeline stages (normalize, annotate) will run.

        Args:
            event: Pipeline stages changed event with toggle states
        """
        self.state.run_normalize = event.run_normalize
        self.state.run_annotate = event.run_annotate

    # -------------------------------------------------------------------------
    # Pipeline Execution
    # -------------------------------------------------------------------------

    @work
    async def _run_pipeline_async(self) -> None:
        """
        Run the pipeline asynchronously.

        Executes extraction, normalization, and annotation stages
        via the PipelineExecutor. Updates job state and UI as it runs.
        """

        def on_progress(stage: str, pct: int, msg: str) -> None:
            """Handle progress updates from executor."""
            self.state.job.current_stage = stage
            self.state.job.progress_percent = pct
            self._update_status()

        def on_log(msg: str) -> None:
            """Handle log messages from executor."""
            self.state.job.add_log(msg)

        try:
            result = await self._executor.run_pipeline(
                config=self.state.config,
                run_normalize=self.state.run_normalize,
                run_annotate=self.state.run_annotate,
                on_progress=on_progress,
                on_log=on_log,
            )

            if result.cancelled:
                self.state.job.status = JobStatus.CANCELLED
                self.state.job.add_log("Pipeline cancelled by user")
                self.notify("Pipeline cancelled")
            elif result.success:
                if result.run_directory:
                    self.state.complete_job(result.run_directory)
                else:
                    self.state.complete_job(self.state.config.output_dir or Path.cwd())
                self.notify("Pipeline completed successfully", severity="information")
            else:
                # Find the error message from failed stages
                error_msg = "Unknown error"
                for stage_result in result.stages:
                    if not stage_result.success and stage_result.error_message:
                        error_msg = stage_result.error_message
                        break
                self.state.fail_job(error_msg)
                self.notify(f"Pipeline failed: {error_msg}", severity="error")

        except Exception as e:
            self.state.fail_job(str(e))
            self.notify(f"Pipeline error: {e}", severity="error")

        finally:
            self._update_status()

    @work
    async def _cancel_pipeline_async(self) -> None:
        """
        Cancel the running pipeline asynchronously.

        Signals the executor to terminate and updates job state.
        """
        try:
            await self._executor.cancel()
            self.state.job.status = JobStatus.CANCELLED
            self.state.job.add_log("Pipeline cancelled by user")
            self._update_status()
            self.notify("Job cancelled")
        except Exception as e:
            self.notify(f"Error cancelling: {e}", severity="error")
