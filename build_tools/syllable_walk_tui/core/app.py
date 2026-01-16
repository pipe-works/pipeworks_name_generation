"""
Main Textual application for Syllable Walker TUI.

This module contains the primary App class, modal screens, and layout widgets
for the interactive terminal interface.

Architecture:
- Main view: Side-by-side patch configuration (always visible)
- Modal screens: Blended Walk (v) and Analysis (a) views
- Keyboard-first navigation with configurable keybindings
"""

from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Footer, Header, Label

from build_tools.syllable_walk.profiles import WALK_PROFILES
from build_tools.syllable_walk_tui.controls import (
    CorpusBrowserScreen,
    FloatSlider,
    IntSpinner,
    ProfileOption,
    SeedInput,
)
from build_tools.syllable_walk_tui.core.state import AppState
from build_tools.syllable_walk_tui.modules.analyzer import AnalysisScreen, StatsPanel
from build_tools.syllable_walk_tui.modules.blender import BlendedWalkScreen
from build_tools.syllable_walk_tui.modules.oscillator import OscillatorPanel, PatchState
from build_tools.syllable_walk_tui.services import (
    get_corpus_info,
    load_annotated_data,
    load_corpus_data,
    load_keybindings,
    validate_corpus_directory,
)

# BlendedWalkScreen moved to modules.blender.screen.BlendedWalkScreen
# AnalysisScreen moved to modules.analyzer.screen.AnalysisScreen
# StatsPanel moved to modules.analyzer.panel.StatsPanel
# PatchPanel moved to modules.oscillator.panel.OscillatorPanel


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
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("question_mark", "help", "Help", priority=True),
        Binding("f1", "help", "Help", priority=True),
        Binding("v", "view_blended", "Blended", priority=True),
        Binding("a", "view_analysis", "Analysis", priority=True),
        Binding("1", "select_corpus_a", "Corpus A", priority=True),
        Binding("2", "select_corpus_b", "Corpus B", priority=True),
    ]

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        layout: horizontal;
        width: 100%;
        height: 1fr;
    }

    .column {
        width: 1fr;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    .patch-panel {
        width: 35%;
    }

    .stats-panel {
        width: 30%;
    }

    .patch-header {
        text-style: bold;
        color: $accent;
    }

    .stats-header {
        text-style: bold;
        color: $accent;
    }

    .section-header {
        text-style: bold;
        margin-top: 1;
    }

    .divider {
        color: $primary-darken-2;
    }

    .spacer {
        height: 1;
    }

    .button-label {
        text-align: center;
    }

    .output-placeholder {
        color: $text-muted;
        text-style: italic;
    }

    .corpus-status {
        color: $text-muted;
        text-style: italic;
        margin-bottom: 1;
    }

    .corpus-status-valid {
        color: $success;
        text-style: none;
        margin-bottom: 1;
    }
    """

    def __init__(self):
        """Initialize application with default state."""
        super().__init__()
        self.state = AppState()
        self.keybindings = load_keybindings()
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

        # Main view: Three-column layout (always visible)
        # Pass initial seed values from PatchState so they display immediately
        with Horizontal(id="main-container"):
            with VerticalScroll(classes="column patch-panel"):
                yield OscillatorPanel("A", initial_seed=self.state.patch_a.seed, id="patch-a")
            with VerticalScroll(classes="column stats-panel"):
                yield StatsPanel(id="stats")
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
        self.push_screen(AnalysisScreen())

    def _get_initial_browse_dir(self, patch_name: str) -> Path:
        """
        Get smart initial directory for corpus browser.

        Priority order:
        1. Patch's current corpus_dir (if already set)
        2. Last browsed directory (if set)
        3. _working/output/ (if exists)
        4. Home directory (fallback)

        Args:
            patch_name: "A" or "B"

        Returns:
            Path to start browsing from
        """
        patch = self.state.patch_a if patch_name == "A" else self.state.patch_b

        # 1. Use patch's current corpus_dir if set
        if patch.corpus_dir and patch.corpus_dir.exists():
            return patch.corpus_dir

        # 2. Use last browsed directory if set
        if self.state.last_browse_dir and self.state.last_browse_dir.exists():
            return self.state.last_browse_dir

        # 3. Try _working/output/ if it exists
        project_root = Path(__file__).parent.parent.parent
        working_output = project_root / "_working" / "output"
        if working_output.exists() and working_output.is_dir():
            return working_output

        # 4. Fall back to home directory
        return Path.home()

    @work
    async def _select_corpus_for_patch(self, patch_name: str) -> None:
        """
        Open directory browser and handle corpus selection for a patch.

        Args:
            patch_name: "A" or "B"
        """
        try:
            # Get smart initial directory
            initial_dir = self._get_initial_browse_dir(patch_name)

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
    # Parameter Change Handlers - Wire widgets to PatchState
    # =========================================================================

    def _switch_to_custom_mode(self, patch_name: str, patch: "PatchState") -> None:
        """
        Switch patch to custom mode when user manually adjusts profile parameters.

        This is called when the user manually changes max_flips, temperature, or
        frequency_weight - the three parameters that define walk profiles. When
        manually adjusted, the patch switches from a named profile to "custom" mode.

        Args:
            patch_name: "A" or "B"
            patch: PatchState instance to update

        Note:
            Only switches to custom if currently using a named profile.
            If already in custom mode, does nothing.
        """
        # Only switch if we're currently using a named profile (not already custom)
        if patch.current_profile == "custom":
            return

        # Update state to custom mode
        old_profile = patch.current_profile
        patch.current_profile = "custom"

        # Update ProfileOption widgets: deselect old, select custom
        try:
            # Deselect the previously selected profile
            old_option = self.query_one(f"#profile-{old_profile}-{patch_name}", ProfileOption)
            old_option.set_selected(False)

            # Select the custom option
            custom_option = self.query_one(f"#profile-custom-{patch_name}", ProfileOption)
            custom_option.set_selected(True)
        except Exception as e:  # nosec B110 - Safe widget query failure
            # Widget not found or update failed - log but don't crash
            print(f"Warning: Could not update profile selection to custom: {e}")

    @on(IntSpinner.Changed)
    def on_int_spinner_changed(self, event: IntSpinner.Changed) -> None:
        """Handle integer spinner value changes and update patch state."""
        # Use widget_id from the message
        widget_id = event.widget_id
        if not widget_id:
            return

        # Parse widget ID to determine patch and parameter
        # Format: "<param>-<patch>" e.g., "min-length-A"
        parts = widget_id.rsplit("-", 1)
        if len(parts) != 2:
            return

        param_name, patch_name = parts
        patch = self.state.patch_a if patch_name == "A" else self.state.patch_b

        # Update the appropriate parameter in patch state
        if param_name == "min-length":
            patch.min_length = event.value
        elif param_name == "max-length":
            patch.max_length = event.value
        elif param_name == "walk-length":
            patch.walk_length = event.value
        elif param_name == "max-flips":
            patch.max_flips = event.value
            # Max flips is a profile parameter - switch to custom mode
            # UNLESS we're updating from a profile change (prevents feedback loop)
            if self._updating_from_profile:
                # Decrement counter - this is one of the expected profile updates
                self._pending_profile_updates -= 1
                if self._pending_profile_updates <= 0:
                    self._updating_from_profile = False
                    self._pending_profile_updates = 0
            elif not self._updating_from_profile:
                self._switch_to_custom_mode(patch_name, patch)
        elif param_name == "neighbors":
            patch.neighbor_limit = event.value

    @on(FloatSlider.Changed)
    def on_float_slider_changed(self, event: FloatSlider.Changed) -> None:
        """Handle float slider value changes and update patch state."""
        # Use widget_id from the message
        widget_id = event.widget_id
        if not widget_id:
            return

        # Parse widget ID to determine patch and parameter
        parts = widget_id.rsplit("-", 1)
        if len(parts) != 2:
            return

        param_name, patch_name = parts
        patch = self.state.patch_a if patch_name == "A" else self.state.patch_b

        # Update the appropriate parameter in patch state
        if param_name == "temperature":
            patch.temperature = event.value
            # Temperature is a profile parameter - switch to custom mode
            # UNLESS we're updating from a profile change (prevents feedback loop)
            if self._updating_from_profile:
                # Decrement counter - this is one of the expected profile updates
                self._pending_profile_updates -= 1
                if self._pending_profile_updates <= 0:
                    self._updating_from_profile = False
                    self._pending_profile_updates = 0
            elif not self._updating_from_profile:
                self._switch_to_custom_mode(patch_name, patch)
        elif param_name == "freq-weight":
            patch.frequency_weight = event.value
            # Frequency weight is a profile parameter - switch to custom mode
            # UNLESS we're updating from a profile change (prevents feedback loop)
            if self._updating_from_profile:
                # Decrement counter - this is one of the expected profile updates
                self._pending_profile_updates -= 1
                if self._pending_profile_updates <= 0:
                    self._updating_from_profile = False
                    self._pending_profile_updates = 0
            elif not self._updating_from_profile:
                self._switch_to_custom_mode(patch_name, patch)

    @on(SeedInput.Changed)
    def on_seed_changed(self, event: SeedInput.Changed) -> None:
        """Handle seed input changes and update patch state."""
        # Use widget_id from the message
        widget_id = event.widget_id
        if not widget_id:
            return

        # Parse widget ID to determine patch
        # Format: "seed-<patch>" e.g., "seed-A"
        parts = widget_id.rsplit("-", 1)
        if len(parts) != 2 or parts[0] != "seed":
            return

        patch_name = parts[1]
        patch = self.state.patch_a if patch_name == "A" else self.state.patch_b

        # Update seed in patch state with new value
        patch.seed = event.value
        patch.rng = __import__("random").Random(event.value)

    @on(ProfileOption.Selected)
    def on_profile_selected(self, event: ProfileOption.Selected) -> None:
        """Handle profile option selection (radio button click)."""
        # Parse widget ID to determine patch
        # Format: "profile-<profile_name>-<patch>" e.g., "profile-clerical-A"
        widget_id = event.widget_id
        if not widget_id:
            return

        parts = widget_id.rsplit("-", 1)
        if len(parts) != 2:
            return

        patch_name = parts[1]
        profile_name = event.profile_name
        patch = self.state.patch_a if patch_name == "A" else self.state.patch_b

        # Deselect all other profile options for this patch
        for profile_key in ["clerical", "dialect", "goblin", "ritual", "custom"]:
            try:
                option = self.query_one(f"#profile-{profile_key}-{patch_name}", ProfileOption)
                should_select = profile_key == profile_name
                option.set_selected(should_select)
            except Exception:  # nosec B110, B112 - Widget query can fail safely
                # Widget not found during initialization, ignore
                pass

        # Update current profile in state
        patch.current_profile = profile_name

        # If "custom" selected, don't update parameters - user will set them manually
        if profile_name == "custom":
            return

        # Load profile parameters and update all controls
        profile = WALK_PROFILES.get(profile_name)
        if not profile:
            # Unknown profile, ignore
            return

        # Update patch state with profile parameters
        patch.max_flips = profile.max_flips
        patch.temperature = profile.temperature
        patch.frequency_weight = profile.frequency_weight

        # CRITICAL: Set flag and counter to prevent auto-switch to custom during profile update
        # When we update parameter widgets below, they'll trigger Changed events.
        # We expect 3 Changed events (max_flips, temperature, freq_weight)
        # Each handler will decrement the counter and clear the flag when it reaches 0
        self._updating_from_profile = True
        self._pending_profile_updates = 3  # Expecting 3 parameter changes

        try:
            # Update all parameter widget displays to match profile
            # These will trigger Changed events, but handlers will skip custom switch
            # Update Max Flips
            max_flips_widget = self.query_one(f"#max-flips-{patch_name}", IntSpinner)
            max_flips_widget.set_value(profile.max_flips)

            # Update Temperature
            temperature_widget = self.query_one(f"#temperature-{patch_name}", FloatSlider)
            temperature_widget.set_value(profile.temperature)

            # Update Frequency Weight
            freq_weight_widget = self.query_one(f"#freq-weight-{patch_name}", FloatSlider)
            freq_weight_widget.set_value(profile.frequency_weight)

        except Exception as e:  # nosec B110 - Safe widget query failure
            # Widget not found or update failed - log but don't crash
            print(f"Warning: Could not update parameter widgets for profile: {e}")
            # Reset flag and counter on error to avoid getting stuck
            self._updating_from_profile = False
            self._pending_profile_updates = 0
