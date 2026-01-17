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

from build_tools.pipeline_tui.core.state import PipelineState

if TYPE_CHECKING:
    pass


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
        Binding("s", "select_source", "Source", priority=True),
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

        This tab will contain:
        - Source selection
        - Output selection
        - Extractor type selection
        - Language selection
        - Syllable length constraints
        - Pipeline stage toggles

        Yields:
            Configure tab widgets
        """
        # Placeholder - will be replaced with actual controls
        yield Static(
            "Configure Tab\n\n"
            "Press [s] to select source directory\n"
            "Press [o] to select output directory\n"
            "Press [r] to run pipeline\n\n"
            "(Full implementation coming soon)",
            classes="placeholder-content",
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
        source = config.source_path.name if config.source_path else "Not selected"
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
            )
        )

        if result:
            self.state.config.source_path = result
            self.state.last_source_dir = result
            self._update_status()
            self.notify(f"Source selected: {result.name}")

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
            )
        )

        if result:
            self.state.config.output_dir = result
            self.state.last_output_dir = result
            self._update_status()
            self.notify(f"Output selected: {result.name}")

    def action_run_pipeline(self) -> None:
        """
        Start pipeline execution.

        Validates configuration and starts the pipeline job.
        """
        is_valid, error = self.state.config.is_valid()
        if not is_valid:
            self.notify(f"Cannot run: {error}", severity="error")
            return

        # Switch to monitor tab
        self.action_tab_monitor()

        # Start the job (actual execution will be implemented in services)
        self.state.start_job()
        self._update_status()
        self.notify("Pipeline job started")

        # TODO: Actually run the pipeline using services.pipeline

    def action_cancel_job(self) -> None:
        """Cancel the currently running job."""
        from build_tools.pipeline_tui.core.state import JobStatus

        if self.state.job.status != JobStatus.RUNNING:
            self.notify("No job is running", severity="warning")
            return

        # TODO: Actually cancel the job
        self.state.job.status = JobStatus.CANCELLED
        self._update_status()
        self.notify("Job cancelled")

    def action_help(self) -> None:
        """Show help screen."""
        # TODO: Implement help screen
        self.notify("Help screen coming soon")
