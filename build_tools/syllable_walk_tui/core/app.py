"""
Main Textual application for Syllable Walker TUI.

This module contains the primary App class, modal screens, and layout widgets
for the interactive terminal interface.

Architecture:
- Main view: Side-by-side patch configuration (always visible)
- Modal screens: Blended Walk (v) and Analysis (a) views
- Keyboard-first navigation with configurable keybindings
"""

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Footer, Header, Label, Select

from build_tools.syllable_walk_tui.controls import (
    CorpusBrowserScreen,
    FloatSlider,
    IntSpinner,
    ProfileOption,
    SeedInput,
)
from build_tools.syllable_walk_tui.core import actions, handlers
from build_tools.syllable_walk_tui.core.state import AppState
from build_tools.syllable_walk_tui.modules.analyzer import AnalysisScreen
from build_tools.syllable_walk_tui.modules.blender import BlendedWalkScreen
from build_tools.syllable_walk_tui.modules.generator import CombinerPanel, SelectorPanel
from build_tools.syllable_walk_tui.modules.oscillator import OscillatorPanel
from build_tools.syllable_walk_tui.services import (
    get_corpus_info,
    load_annotated_data,
    load_corpus_data,
    load_keybindings,
    validate_corpus_directory,
)
from build_tools.syllable_walk_tui.services.combiner_runner import run_combiner
from build_tools.syllable_walk_tui.services.exporter import export_names_to_txt
from build_tools.syllable_walk_tui.services.generation import generate_walks_for_patch
from build_tools.syllable_walk_tui.services.selector_runner import run_selector


class SyllableWalkerApp(App):
    """
    Main Textual application for Syllable Walker TUI.

    Provides interactive interface for exploring phonetic space through
    side-by-side patch configuration and real-time generation.

    Default Keybindings:
        q, Ctrl+Q: Quit application
        ?, F1: Show help
        v: View blended walk (modal screen)
        a: View analysis (modal screen)
        1: Select corpus for Patch A
        2: Select corpus for Patch B

    Note:
        All keybindings are user-configurable via
        ~/.config/pipeworks_tui/keybindings.toml
    """

    # Class-level bindings with priority=True to work even with focused widgets
    # Using Binding class explicitly to enable priority (allows bindings to fire
    # even when child widgets like IntSpinner/FloatSlider/SeedInput have focus)
    # NOTE: Only ctrl+q quits the app globally. Screens can use 'q' to close themselves.
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("question_mark", "help", "Help", priority=True),
        Binding("f1", "help", "Help", priority=True),
        Binding("v", "view_blended", "Blended", priority=True),
        Binding("a", "view_analysis", "Analysis", priority=True),
        Binding("d", "view_database_a", "DB A", priority=True),
        Binding("D", "view_database_b", "DB B", priority=True),
        Binding("1", "select_corpus_a", "Corpus A", priority=True),
        Binding("2", "select_corpus_b", "Corpus B", priority=True),
    ]

    CSS_PATH = "styles.tcss"

    def __init__(self):
        """Initialize application with default state."""
        super().__init__()
        self.state = AppState()
        self.keybindings = load_keybindings()
        # Set theme (nord provides better contrast for highlighted areas)
        self.theme = "nord"
        # Note: Keybindings are now defined in BINDINGS class attribute
        # Config-based overrides can be added in future if needed

        # Flag to prevent auto-switch to custom when updating parameters from profile selection
        # (prevents feedback loop when profile changes trigger parameter widget updates)
        self._updating_from_profile = False
        # Counter to track pending parameter updates during profile change
        self._pending_profile_updates = 0

    def compose(self) -> ComposeResult:
        """Create application layout."""
        yield Header(show_clock=False)

        # Main view: Four-column layout
        # Column 1: Oscillator A (walk parameters)
        # Column 2: Combiner A + Selector A (name generation + selection)
        # Column 3: Combiner B + Selector B (name generation + selection)
        # Column 4: Oscillator B (walk parameters)
        with Horizontal(id="main-container"):
            with VerticalScroll(classes="column patch-panel"):
                yield OscillatorPanel("A", initial_seed=self.state.patch_a.seed, id="patch-a")
            with VerticalScroll(classes="column combiner-column"):
                yield CombinerPanel(patch_name="A", id="combiner-panel-a")
                yield SelectorPanel(patch_name="A", id="selector-panel-a")
            with VerticalScroll(classes="column combiner-column"):
                yield CombinerPanel(patch_name="B", id="combiner-panel-b")
                yield SelectorPanel(patch_name="B", id="selector-panel-b")
            with VerticalScroll(classes="column patch-panel"):
                yield OscillatorPanel("B", initial_seed=self.state.patch_b.seed, id="patch-b")

        yield Footer()

    def on_mount(self) -> None:
        """
        Handle app mount event.

        NOTE: Previously disabled focus on ALL container widgets, but this broke tab order.
        Now we only disable focus on the StatsPanel container since it has no focusable
        children and shouldn't be in the tab navigation path.
        """
        # Disable focus on StatsPanel's VerticalScroll container only
        # This prevents tab navigation from going through the empty stats panel
        # between Patch A and Patch B
        stats_containers = self.query(".stats-panel")
        for container in stats_containers:
            container.can_focus = False

    @on(Button.Pressed, "#select-corpus-A")
    def on_button_select_corpus_a(self) -> None:
        """Handle Patch A corpus selection button press."""
        self._select_corpus_for_patch("A")

    @on(Button.Pressed, "#select-corpus-B")
    def on_button_select_corpus_b(self) -> None:
        """Handle Patch B corpus selection button press."""
        self._select_corpus_for_patch("B")

    @on(Button.Pressed, "#generate-A")
    def on_button_generate_a(self) -> None:
        """Generate walks for patch A."""
        self._generate_walks_for_patch("A")

    @on(Button.Pressed, "#generate-B")
    def on_button_generate_b(self) -> None:
        """Generate walks for patch B."""
        self._generate_walks_for_patch("B")

    @on(Button.Pressed, "#generate-candidates-a")
    def on_button_generate_candidates_a(self) -> None:
        """Generate candidates for Patch A using name_combiner (mirrors CLI behavior)."""
        self._run_combiner("A")

    @on(Button.Pressed, "#generate-candidates-b")
    def on_button_generate_candidates_b(self) -> None:
        """Generate candidates for Patch B using name_combiner (mirrors CLI behavior)."""
        self._run_combiner("B")

    @on(Button.Pressed, "#select-names-a")
    def on_button_select_names_a(self) -> None:
        """Select names for Patch A using name_selector (mirrors CLI behavior)."""
        self._run_selector("A")

    @on(Button.Pressed, "#select-names-b")
    def on_button_select_names_b(self) -> None:
        """Select names for Patch B using name_selector (mirrors CLI behavior)."""
        self._run_selector("B")

    @on(Button.Pressed, "#export-txt-a")
    def on_button_export_txt_a(self) -> None:
        """Export selected names to TXT file for Patch A."""
        self._export_to_txt("A")

    @on(Button.Pressed, "#export-txt-b")
    def on_button_export_txt_b(self) -> None:
        """Export selected names to TXT file for Patch B."""
        self._export_to_txt("B")

    # ─────────────────────────────────────────────────────────────
    # Wrapper methods for actions module (preserves API for tests)
    # ─────────────────────────────────────────────────────────────

    def _get_initial_browse_dir(self, patch_name: str):
        """Get smart initial directory for corpus browser. Delegates to actions."""
        return actions.get_initial_browse_dir(self, patch_name)

    def _open_database_for_patch(self, patch_name: str) -> None:
        """Open database viewer for a patch. Delegates to actions."""
        actions.open_database_for_patch(self, patch_name)

    def _compute_metrics_for_patch(self, patch):
        """Compute corpus shape metrics for a patch. Delegates to actions."""
        return actions.compute_metrics_for_patch(patch)

    # ─────────────────────────────────────────────────────────────
    # Core workflow methods
    # ─────────────────────────────────────────────────────────────

    def _generate_walks_for_patch(self, patch_name: str) -> None:
        """
        Generate walks for a patch using SyllableWalker.

        Args:
            patch_name: "A" or "B"
        """
        patch = self.state.patch_a if patch_name == "A" else self.state.patch_b

        # Validate patch is ready
        if not patch.is_ready_for_generation():
            self.notify(f"Patch {patch_name}: Corpus not loaded", severity="warning")
            return

        # Notify user that generation is starting
        self.notify(
            f"Patch {patch_name}: Initializing walker...",
            timeout=2,
            severity="information",
        )

        # Delegate to service
        result = generate_walks_for_patch(patch)

        if result.error:
            self.notify(f"Patch {patch_name}: {result.error}", severity="error")
            return

        # Store in patch state
        patch.outputs = result.walks

        # Update walks output in oscillator panel
        try:
            output_label = self.query_one(f"#walks-output-{patch_name}", Label)
            output_label.update("\n".join(result.walks))
        except Exception:  # nosec B110 - Label may not exist in all layouts
            pass

        self.notify(
            f"Patch {patch_name}: Generated {len(result.walks)} walks",
            severity="information",
        )

    def _run_combiner(self, patch_name: str) -> None:
        """
        Run name_combiner for a specific patch (mirrors CLI behavior exactly).

        Args:
            patch_name: "A" or "B" - which patch to use for generation
        """
        # Get the combiner state for this patch (independent A/B)
        comb = self.state.combiner_a if patch_name == "A" else self.state.combiner_b
        patch = self.state.patch_a if patch_name == "A" else self.state.patch_b

        # Validate patch is ready
        if not patch.is_ready_for_generation():
            self.notify(
                f"Patch {patch_name}: Corpus not loaded. "
                f"Press {1 if patch_name == 'A' else 2} to select a corpus.",
                severity="warning",
            )
            return

        self.notify(
            f"Generating {comb.count:,} {comb.syllables}-syllable candidates...",
            timeout=2,
            severity="information",
        )

        # Delegate to service
        result = run_combiner(patch, comb)

        if result.error:
            self.notify(f"Combiner failed: {result.error}", severity="error")
            return

        # Update state
        comb.outputs = [c["name"] for c in result.candidates[:10]]  # Preview first 10
        comb.last_output_path = str(result.output_path)

        # Update panel output with full metadata
        try:
            panel = self.query_one(f"#combiner-panel-{patch_name.lower()}", CombinerPanel)
            panel.update_output(result.meta_output)
        except Exception as e:
            print(f"Warning: Could not update panel: {e}")

        self.notify(
            f"Generated {len(result.candidates):,} candidates → {result.output_path.name}",
            severity="information",
        )

    def _run_selector(self, patch_name: str) -> None:
        """
        Run name_selector for a specific patch (mirrors CLI behavior exactly).

        Args:
            patch_name: "A" or "B" - which patch to use for selection
        """
        # Get the selector and combiner states for this patch (independent A/B)
        selector = self.state.selector_a if patch_name == "A" else self.state.selector_b
        combiner = self.state.combiner_a if patch_name == "A" else self.state.combiner_b
        patch = self.state.patch_a if patch_name == "A" else self.state.patch_b

        # Validate patch is ready
        if not patch.is_ready_for_generation():
            self.notify(
                f"Patch {patch_name}: Corpus not loaded. "
                f"Press {1 if patch_name == 'A' else 2} to select a corpus.",
                severity="warning",
            )
            return

        self.notify(
            f"Selecting {selector.count} {selector.name_class} names...",
            timeout=2,
            severity="information",
        )

        # Delegate to service
        result = run_selector(patch, combiner, selector)

        if result.error:
            self.notify(f"Selector failed: {result.error}", severity="error")
            return

        # Update state
        selector.last_output_path = str(result.output_path)
        selector.last_candidates_path = combiner.last_output_path
        selector.outputs = result.selected_names

        # Update panel
        try:
            panel = self.query_one(f"#selector-panel-{patch_name.lower()}", SelectorPanel)
            panel.update_output(result.meta_output, selector.outputs)
        except Exception as e:
            print(f"Warning: Could not update selector panel: {e}")

        self.notify(
            f"Selected {len(result.selected):,} {selector.name_class} names → {result.output_path.name}",
            severity="information",
        )

    def _export_to_txt(self, patch_name: str) -> None:
        """
        Export selected names to a plain text file (one name per line).

        Args:
            patch_name: "A" or "B" - which patch's selections to export
        """
        selector = self.state.selector_a if patch_name == "A" else self.state.selector_b

        # Check if there are names to export
        if not selector.outputs:
            self.notify(
                f"Patch {patch_name}: No names to export. Run Select Names first.",
                severity="warning",
            )
            return

        # Check if we have the output path from the selector
        if not selector.last_output_path:
            self.notify(
                f"Patch {patch_name}: No selection output path. Run Select Names first.",
                severity="warning",
            )
            return

        # Delegate to service
        txt_path, error = export_names_to_txt(selector.outputs, selector.last_output_path)

        if error:
            self.notify(f"Export failed: {error}", severity="error")
        else:
            self.notify(
                f"Exported {len(selector.outputs):,} names → {txt_path.name}",
                severity="information",
            )

    def action_select_corpus_a(self) -> None:
        """Action: Open corpus selector for Patch A (keybinding: 1)."""
        self._select_corpus_for_patch("A")

    def action_select_corpus_b(self) -> None:
        """Action: Open corpus selector for Patch B (keybinding: 2)."""
        self._select_corpus_for_patch("B")

    def action_view_blended(self) -> None:
        """Action: Open blended walk modal screen (keybinding: v)."""
        self.push_screen(BlendedWalkScreen())

    def action_view_analysis(self) -> None:
        """Action: Open analysis modal screen (keybinding: a)."""
        # Compute metrics for loaded patches using actions module
        metrics_a = actions.compute_metrics_for_patch(self.state.patch_a)
        metrics_b = actions.compute_metrics_for_patch(self.state.patch_b)

        self.push_screen(
            AnalysisScreen(
                metrics_a=metrics_a,
                metrics_b=metrics_b,
                corpus_path_a=self.state.patch_a.corpus_dir,
                corpus_path_b=self.state.patch_b.corpus_dir,
                annotated_data_a=self.state.patch_a.annotated_data,
                annotated_data_b=self.state.patch_b.annotated_data,
            )
        )

    def action_view_database_a(self) -> None:
        """Action: Open database viewer for Patch A (keybinding: d)."""
        actions.open_database_for_patch(self, "A")

    def action_view_database_b(self) -> None:
        """Action: Open database viewer for Patch B (keybinding: D)."""
        actions.open_database_for_patch(self, "B")

    @work
    async def _select_corpus_for_patch(self, patch_name: str) -> None:
        """
        Open directory browser and handle corpus selection for a patch.

        Args:
            patch_name: "A" or "B"
        """
        try:
            # Get smart initial directory
            initial_dir = actions.get_initial_browse_dir(self, patch_name)

            # Open browser modal
            result = await self.push_screen_wait(CorpusBrowserScreen(initial_dir))

            if result:
                # Validate and store selection
                is_valid, corpus_type, error = validate_corpus_directory(result)

                if is_valid:
                    # Update patch state
                    patch = self.state.patch_a if patch_name == "A" else self.state.patch_b
                    patch.corpus_dir = result
                    patch.corpus_type = corpus_type

                    # === PHASE 1: Load quick metadata (FAST - synchronous) ===
                    # Load syllables list and frequencies (~50KB, <100ms)
                    # This is fast enough to do immediately without blocking
                    try:
                        syllables, frequencies = load_corpus_data(result)
                        patch.syllables = syllables
                        patch.frequencies = frequencies

                        # Remember this location for next time
                        self.state.last_browse_dir = result.parent

                        # Update UI to show quick metadata loaded
                        try:
                            status_label = self.query_one(f"#corpus-status-{patch_name}", Label)
                            corpus_info = get_corpus_info(result)

                            # Build detailed file list showing what was loaded
                            corpus_prefix = corpus_type.lower() if corpus_type else "nltk"
                            files_loaded = (
                                f"{corpus_info}\n"
                                f"─────────────────\n"
                                f"✓ {corpus_prefix}_syllables_unique.txt\n"
                                f"✓ {corpus_prefix}_syllables_frequencies.json\n"
                                f"⏳ {corpus_prefix}_syllables_annotated.json"
                            )
                            status_label.update(files_loaded)
                            status_label.remove_class("corpus-status")
                            status_label.add_class("corpus-status-valid")
                        except Exception as e:
                            # Log UI update errors but don't fail
                            print(f"Warning: Could not update status label: {e}")

                        # Update center panel corpus label with directory name and type
                        try:
                            corpus_label = self.query_one(f"#walks-corpus-{patch_name}", Label)
                            dir_name = result.name  # e.g., "20260110_115601_nltk"
                            corpus_label.update(f"{dir_name} ({corpus_type})")
                            corpus_label.remove_class("output-placeholder")
                        except Exception as e:
                            print(f"Warning: Could not update center corpus label: {e}")

                        # Notify user that quick metadata loaded successfully
                        self.notify(
                            f"Patch {patch_name}: Loaded {len(syllables):,} syllables "
                            f"from {corpus_type} corpus",
                            timeout=2,
                        )

                        # Set focus to the first profile option in this patch
                        # This makes tab navigation start from the patch that was just loaded
                        try:
                            first_profile = self.query_one(f"#profile-clerical-{patch_name}")
                            first_profile.focus()
                        except Exception:  # nosec B110 - Safe widget query, intentionally silent
                            # Widget not found during initialization, ignore gracefully
                            pass

                        # === PHASE 2: Kick off background loading (SLOW - async) ===
                        # Load annotated data with phonetic features (~15MB, 1-2 seconds)
                        # This runs in background to avoid freezing the UI
                        # The _load_annotated_data_background method will:
                        # - Set is_loading_annotated = True
                        # - Load data in background thread
                        # - Update UI when complete
                        # - Handle errors gracefully
                        self._load_annotated_data_background(patch_name)

                    except Exception as e:
                        # Failed to load quick metadata - this is a critical error
                        # Don't proceed to annotated data loading
                        self.notify(f"Error loading corpus data: {e}", severity="error", timeout=5)
                        # Reset patch state since loading failed
                        patch.corpus_dir = None
                        patch.corpus_type = None
                        patch.syllables = None
                        patch.frequencies = None
                        patch.annotated_data = None
                        patch.is_loading_annotated = False
                        patch.loading_error = str(e)

                else:
                    self.notify(f"Invalid corpus: {error}", severity="error", timeout=5)

        except Exception as e:
            # Catch any errors to prevent silent failures
            self.notify(f"Error selecting corpus: {e}", severity="error", timeout=5)
            import traceback

            traceback.print_exc()

    @work
    async def _load_annotated_data_background(self, patch_name: str) -> None:
        """
        Load annotated phonetic data in background worker (non-blocking).

        This method runs in a background thread to load the large annotated.json
        file (typically 10-15MB, 400k-600k lines) without freezing the UI.

        The loading process:
        1. Set patch loading state (is_loading_annotated = True)
        2. Update UI to show "Loading..." status
        3. Load annotated data file (1-2 seconds)
        4. Update patch state with loaded data
        5. Update UI to show "Ready" status
        6. Handle any errors and update UI accordingly

        Args:
            patch_name: "A" or "B" to identify which patch to load for

        Note:
            This method uses the @work decorator which automatically runs
            the code in a background worker thread, preventing UI freezing.
            UI updates are scheduled back to the main thread.
        """
        # Get the patch we're loading for
        patch = self.state.patch_a if patch_name == "A" else self.state.patch_b

        # Safety check: ensure corpus directory is set
        if not patch.corpus_dir:
            self.notify(
                f"Patch {patch_name}: Cannot load annotated data - no corpus selected",
                severity="error",
                timeout=5,
            )
            return

        try:
            # === STEP 1: Set loading state ===
            # Mark patch as loading (disables Generate button in UI)
            patch.is_loading_annotated = True
            patch.loading_error = None

            # === STEP 2: Update UI to show loading state ===
            # This tells the user that background loading is happening
            try:
                status_label = self.query_one(f"#corpus-status-{patch_name}", Label)
                corpus_info = get_corpus_info(patch.corpus_dir)

                # Show loading progress with file list
                corpus_prefix = patch.corpus_type.lower() if patch.corpus_type else "nltk"
                files_loading = (
                    f"{corpus_info}\n"
                    f"─────────────────\n"
                    f"✓ {corpus_prefix}_syllables_unique.txt\n"
                    f"✓ {corpus_prefix}_syllables_frequencies.json\n"
                    f"⏳ {corpus_prefix}_syllables_annotated.json (loading...)"
                )
                status_label.update(files_loading)
                status_label.remove_class("corpus-status")
                status_label.add_class("corpus-status-valid")
            except Exception as e:
                # Log UI update errors but don't fail the loading
                print(f"Warning: Could not update status label (loading): {e}")

            # Notify user that background loading started
            self.notify(
                f"Patch {patch_name}: Loading phonetic features...",
                timeout=2,
                severity="information",
            )

            # === STEP 3: Load annotated data (SLOW - 1-2 seconds) ===
            # This is the expensive operation that happens in the background
            # The @work decorator ensures this doesn't block the UI
            annotated_data, load_metadata = load_annotated_data(patch.corpus_dir)

            # === STEP 4: Update patch state with loaded data ===
            patch.annotated_data = annotated_data
            patch.is_loading_annotated = False

            # === STEP 5: Update UI to show ready state ===
            try:
                status_label = self.query_one(f"#corpus-status-{patch_name}", Label)
                corpus_info = get_corpus_info(patch.corpus_dir)
                syllable_count = len(annotated_data)

                # Build source indicator based on what was loaded
                source = load_metadata.get("source", "unknown")
                load_time = load_metadata.get("load_time_ms", "?")

                # Show only files that were actually loaded
                corpus_prefix = patch.corpus_type.lower() if patch.corpus_type else "nltk"

                if source == "sqlite":
                    # SQLite path: show corpus.db, JSON not loaded
                    files_ready = (
                        f"{corpus_info}\n"
                        f"─────────────────\n"
                        f"✓ {corpus_prefix}_syllables_unique.txt\n"
                        f"✓ {corpus_prefix}_syllables_frequencies.json\n"
                        f"✓ corpus.db ({load_time}ms, SQLite)\n"
                        f"─────────────────\n"
                        f"Ready: {syllable_count:,} syllables"
                    )
                else:
                    # JSON fallback path: show annotated.json, SQLite not present
                    file_name = load_metadata.get("file_name", "annotated.json")
                    files_ready = (
                        f"{corpus_info}\n"
                        f"─────────────────\n"
                        f"✓ {corpus_prefix}_syllables_unique.txt\n"
                        f"✓ {corpus_prefix}_syllables_frequencies.json\n"
                        f"✓ {file_name} ({load_time}ms, JSON)\n"
                        f"─────────────────\n"
                        f"Ready: {syllable_count:,} syllables"
                    )
                status_label.update(files_ready)
                status_label.remove_class("corpus-status")
                status_label.add_class("corpus-status-valid")
            except Exception as e:
                # Log UI update errors but don't fail the loading
                print(f"Warning: Could not update status label (complete): {e}")

            # Notify user that loading completed successfully
            if source == "sqlite":
                self.notify(
                    f"Patch {patch_name}: Loaded from SQLite ({len(annotated_data):,} syllables, {load_time}ms)",
                    timeout=3,
                    severity="information",
                )
            else:
                self.notify(
                    f"Patch {patch_name}: Loaded from JSON ({len(annotated_data):,} syllables, {load_time}ms)",
                    timeout=3,
                    severity="information",
                )

        except FileNotFoundError as e:
            # === ERROR HANDLING: Annotated file doesn't exist ===
            # This might happen if the corpus hasn't been processed with
            # syllable_feature_annotator yet
            patch.is_loading_annotated = False
            patch.loading_error = "Annotated data file not found"

            # Update UI to show error with file list
            try:
                status_label = self.query_one(f"#corpus-status-{patch_name}", Label)
                corpus_prefix = patch.corpus_type.lower() if patch.corpus_type else "nltk"
                files_error = (
                    f"{get_corpus_info(patch.corpus_dir)}\n"
                    f"─────────────────\n"
                    f"✓ {corpus_prefix}_syllables_unique.txt\n"
                    f"✓ {corpus_prefix}_syllables_frequencies.json\n"
                    f"✗ {corpus_prefix}_syllables_annotated.json\n"
                    f"─────────────────\n"
                    f"Run syllable_feature_annotator"
                )
                status_label.update(files_error)
                status_label.remove_class("corpus-status-valid")
                status_label.add_class("corpus-status")
            except Exception:  # nosec B110
                pass  # Ignore UI update errors

            self.notify(f"Patch {patch_name}: {str(e)}", severity="error", timeout=5)

        except Exception as e:
            # === ERROR HANDLING: Other errors ===
            patch.is_loading_annotated = False
            patch.loading_error = str(e)

            # Update UI to show error with file list
            try:
                status_label = self.query_one(f"#corpus-status-{patch_name}", Label)
                corpus_prefix = patch.corpus_type.lower() if patch.corpus_type else "nltk"
                files_error = (
                    f"{get_corpus_info(patch.corpus_dir)}\n"
                    f"─────────────────\n"
                    f"✓ {corpus_prefix}_syllables_unique.txt\n"
                    f"✓ {corpus_prefix}_syllables_frequencies.json\n"
                    f"✗ {corpus_prefix}_syllables_annotated.json\n"
                    f"─────────────────\n"
                    f"Error: {str(e)[:30]}..."
                )
                status_label.update(files_error)
                status_label.remove_class("corpus-status-valid")
                status_label.add_class("corpus-status")
            except Exception:  # nosec B110
                pass  # Ignore UI update errors

            self.notify(
                f"Patch {patch_name}: Error loading annotated data: {e}",
                severity="error",
                timeout=5,
            )
            import traceback

            traceback.print_exc()

    def action_help(self) -> None:
        """Show help information."""
        help_text = (
            "Syllable Walker TUI - Keybindings\n\n"
            "[q] Quit\n"
            "[?] Help\n\n"
            "Tabs:\n"
            "[p] Patch Config\n"
            "[b] Blended Walk\n"
            "[a] Analysis\n\n"
            "Corpus:\n"
            "[1] Select Corpus A\n"
            "[2] Select Corpus B\n\n"
            "Parameters:\n"
            "[TAB] Navigate controls\n"
            "[j/k or +/-] Adjust values\n"
        )
        self.notify(help_text, timeout=10)

    def action_quit(self) -> None:  # type: ignore[override]
        """Quit the application."""
        self.exit()

    # =========================================================================
    # Parameter Change Handlers - Delegate to handlers module
    # =========================================================================

    @on(IntSpinner.Changed)
    def on_int_spinner_changed(self, event: IntSpinner.Changed) -> None:
        """Handle integer spinner value changes."""
        if event.widget_id:
            handlers.handle_int_spinner_changed(self, event.widget_id, event.value)

    @on(FloatSlider.Changed)
    def on_float_slider_changed(self, event: FloatSlider.Changed) -> None:
        """Handle float slider value changes."""
        if event.widget_id:
            handlers.handle_float_slider_changed(self, event.widget_id, event.value)

    @on(SeedInput.Changed)
    def on_seed_changed(self, event: SeedInput.Changed) -> None:
        """Handle seed input changes."""
        if event.widget_id:
            handlers.handle_seed_changed(self, event.widget_id, event.value)

    @on(Select.Changed)
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle Select widget changes (e.g., name class dropdown)."""
        widget_id = str(event.control.id) if event.control.id else None
        if widget_id and widget_id.startswith("selector-name-class"):
            value = str(event.value) if event.value else "first_name"
            handlers.handle_selector_name_class_changed(self, widget_id, value)

    @on(ProfileOption.Selected)
    def on_profile_selected(self, event: ProfileOption.Selected) -> None:
        """Handle profile option selection (radio button click)."""
        if event.widget_id:
            handlers.handle_profile_selected(self, event.widget_id, event.profile_name)
