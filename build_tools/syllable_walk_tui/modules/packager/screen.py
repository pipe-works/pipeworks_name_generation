"""
Package screen for Syllable Walker TUI.

This screen provides a two-column workflow:
- Left: editable metadata inputs that will be saved as JSON.
- Right: packaging workflow (select run dir, include options, build ZIP).
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Input, Label, Static, TextArea

from build_tools.name_selector.name_class import get_default_policy_path, load_name_classes
from build_tools.syllable_walk_tui.controls import DirectoryBrowserScreen
from build_tools.syllable_walk_tui.services.packager import (
    PackageOptions,
    build_package_metadata,
    collect_included_files,
    package_selections,
    scan_selections,
    write_metadata_json,
)


class PackageScreen(Screen):
    """
    Full-screen UI for packaging selection outputs.

    Users pick a run directory (``_working/<timestamp>_<extractor>``),
    choose which selection artifacts to include, and generate a ZIP
    archive that contains the selections plus an optional manifest.

    The left column captures author-facing metadata that will be saved
    as a JSON file alongside the package output.

    Keybindings:
        Esc/q: Close the screen
        b: Browse for a run directory
        p: Build package
    """

    BINDINGS = [
        ("escape", "close_screen", "Close"),
        ("q", "close_screen", "Close"),
        ("b", "browse_run_dir", "Browse"),
        ("p", "build_package", "Package"),
    ]

    DEFAULT_CSS = """
    PackageScreen {
        background: $surface;
        padding: 1;
    }

    #package-main {
        layout: horizontal;
        width: 100%;
        height: 1fr;
    }

    .package-column {
        width: 1fr;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    .panel-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .section-header {
        text-style: bold;
        margin-top: 1;
    }

    .row {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
    }

    .field-label {
        width: 14;
        text-align: right;
        padding-right: 1;
        color: $text-muted;
    }

    .input-wide {
        width: 1fr;
    }

    .intended-use-group {
        margin-bottom: 1;
    }

    .intended-use-option {
        margin-left: 1;
    }

    #meta-examples {
        height: 8;
        border: solid $primary;
    }

    #meta-files {
        height: 6;
        border: solid $primary;
        color: $text-muted;
        padding: 0 1;
    }

    #selection-summary {
        padding: 0 1;
        color: $text-muted;
        border: dashed $primary;
        height: auto;
    }

    #include-row Checkbox {
        margin-right: 2;
    }

    #button-row Button {
        margin-right: 1;
    }

    #package-status {
        padding: 0 1;
        height: auto;
        border: solid $primary;
        color: $text;
    }

    .status-error {
        color: $error;
    }

    .status-success {
        color: $success;
    }
    """

    def __init__(self, initial_run_dir: Path | None = None) -> None:
        """
        Initialize the package screen with optional initial run directory.

        Args:
            initial_run_dir: Pre-selected run directory, if available
        """
        super().__init__()
        # Track the current run directory in state for packaging actions
        self.run_dir: Path | None = initial_run_dir
        # Mirror include flags in state for easy access when building options
        self.include_json = True
        self.include_txt = True
        self.include_meta = True
        self.include_manifest = True
        # Cache name class options for the intended-use checkboxes
        self._name_class_options = self._load_name_class_options()
        # Track whether the package name should be auto-derived from common name
        self._auto_package_name = True

    def compose(self) -> ComposeResult:
        """Compose the package screen layout."""
        with Horizontal(id="package-main"):
            # -----------------------------------------------------------------
            # Left column: metadata editor panel
            # -----------------------------------------------------------------
            with VerticalScroll(classes="package-column", id="package-editor-column"):
                yield Label("PACKAGE EDITOR", classes="panel-title")
                yield Static(
                    "Provide author metadata to save with this package.",
                    classes="output-placeholder",
                )

                yield Label("Run Directory", classes="section-header")
                with Horizontal(classes="row"):
                    yield Label("Run Dir:", classes="field-label")
                    yield Input(
                        placeholder="_working/20260130_185007_pyphen",
                        id="run-dir-input",
                        classes="input-wide",
                    )
                    yield Button("Browse", id="browse-run-dir", variant="default")

                yield Label("Metadata", classes="section-header")

                # Date/time stamp (defaults to now but is editable)
                with Horizontal(classes="row"):
                    yield Label("Date/Time:", classes="field-label")
                    yield Input(id="meta-created", classes="input-wide")

                # Author name input
                with Horizontal(classes="row"):
                    yield Label("Author:", classes="field-label")
                    yield Input(placeholder="Author name", id="meta-author", classes="input-wide")

                # Version input
                with Horizontal(classes="row"):
                    yield Label("Version:", classes="field-label")
                    yield Input(placeholder="1.0.0", id="meta-version", classes="input-wide")

                # Human-friendly name input (defaults to run directory)
                with Horizontal(classes="row"):
                    yield Label("Common Name:", classes="field-label")
                    yield Input(id="meta-common-name", classes="input-wide")

                # Intended use checkboxes populated from name classes
                yield Label("Intended Use", classes="section-header")
                with Vertical(id="meta-intended-use", classes="intended-use-group"):
                    if self._name_class_options:
                        for index, (label, name_class) in enumerate(self._name_class_options):
                            yield Checkbox(
                                label,
                                value=index == 0,
                                id=self._intended_use_checkbox_id(name_class),
                                classes="intended-use-option",
                            )
                    else:
                        yield Static("No name classes available.", classes="output-placeholder")

                # Source is derived from the run directory and kept read-only
                with Horizontal(classes="row"):
                    yield Label("Source:", classes="field-label")
                    yield Input(id="meta-source", classes="input-wide", disabled=True)

                # Examples area for author-provided samples
                yield Label("Examples", classes="section-header")
                yield TextArea(
                    "",  # Start empty so authors can add examples
                    id="meta-examples",
                )

            # -----------------------------------------------------------------
            # Right column: packaging workflow panel
            # -----------------------------------------------------------------
            with VerticalScroll(classes="package-column", id="package-workflow-column"):
                yield Label("PACKAGE BUILDER", classes="panel-title")

                # Summary of discovered selection files
                yield Static("Select a run directory to view selections.", id="selection-summary")

                yield Label("Include", classes="section-header")
                with Horizontal(classes="row", id="include-row"):
                    yield Checkbox("JSON", value=True, id="include-json")
                    yield Checkbox("TXT", value=True, id="include-txt")
                    yield Checkbox("Meta", value=True, id="include-meta")
                    yield Checkbox("Manifest", value=True, id="include-manifest")

                # Included files list (auto-generated)
                yield Label("Files Included", classes="section-header")
                yield Static("Select a run directory to list files.", id="meta-files")

                yield Label("Output", classes="section-header")
                with Horizontal(classes="row"):
                    yield Label("Output Dir:", classes="field-label")
                    yield Input(
                        placeholder="defaults to <run_dir>/packages",
                        id="output-dir-input",
                        classes="input-wide",
                    )

                with Horizontal(classes="row"):
                    yield Label("Package Name:", classes="field-label")
                    yield Input(
                        placeholder="<run_dir>_selections.zip",
                        id="package-name-input",
                        classes="input-wide",
                    )

                # Action buttons row
                with Horizontal(classes="row", id="button-row"):
                    yield Button("Create Package", id="build-package", variant="primary")
                    yield Button("Close", id="close-package", variant="default")

                # Status output
                yield Static("", id="package-status")

    def on_mount(self) -> None:
        """Initialize inputs based on the current run directory state."""
        # Apply the default timestamp once when the screen mounts
        self._set_default_timestamp()
        # Apply a default version if the field is empty
        self._set_default_version()

        # If an initial run directory was supplied, populate dependent fields
        if self.run_dir:
            self._apply_run_dir_defaults(self.run_dir)
            self._refresh_selection_summary(self.run_dir)
            self._refresh_included_files(self.run_dir)
            self._set_source_fields(self.run_dir)
        # Ensure examples are populated for the initial intended use selection
        self._update_examples_from_intended_use()

    def action_close_screen(self) -> None:
        """Close this screen and return to the main view."""
        self.app.pop_screen()

    def action_browse_run_dir(self) -> None:
        """Keybinding action to browse for a run directory."""
        # Delegate to the async handler used by the browse button
        self._browse_for_run_dir()

    def action_build_package(self) -> None:
        """Keybinding action to build a package with the current settings."""
        # Delegate to the same handler used by the Create Package button
        self._build_package()

    @on(Button.Pressed, "#close-package")
    def on_close_pressed(self) -> None:
        """Handle Close button press."""
        self.action_close_screen()

    @on(Button.Pressed, "#browse-run-dir")
    def on_browse_pressed(self) -> None:
        """Handle Browse button press."""
        self._browse_for_run_dir()

    @work
    async def _browse_for_run_dir(self) -> None:
        """
        Open the directory browser to select a run directory.

        This uses a validator that ensures the selection contains
        a selections/ folder with at least one selection file.
        """
        # Build the initial directory for browsing
        initial_dir = self._get_default_working_dir()

        # Open the directory browser modal and await selection
        result = await self.app.push_screen_wait(
            DirectoryBrowserScreen(
                title="Select Run Directory",
                validator=self._validate_run_dir,
                initial_dir=initial_dir,
            )
        )

        if result:
            # Update the screen state and inputs with the chosen directory
            self._set_run_dir(result)

    @on(Input.Submitted, "#run-dir-input")
    def on_run_dir_submitted(self, event: Input.Submitted) -> None:
        """
        Handle manual run directory entry.

        This updates defaults and selection summary after the user
        confirms input with Enter.
        """
        run_dir = self._coerce_run_dir(self._normalize_path(event.value))
        if run_dir:
            self._set_run_dir(run_dir)
        else:
            self._update_status("Run directory is empty.", is_error=True)

    @on(Input.Submitted, "#output-dir-input")
    def on_output_dir_submitted(self, event: Input.Submitted) -> None:
        """Handle manual output directory entry."""
        output_dir = self._normalize_path(event.value)
        if output_dir is None:
            self._update_status("Output directory is empty.", is_error=True)

    @on(Input.Submitted, "#meta-common-name")
    def on_common_name_submitted(self, event: Input.Submitted) -> None:
        """Handle common name edits to keep the package name in sync."""
        self._handle_common_name_change(event.value)

    @on(Input.Changed, "#meta-common-name")
    def on_common_name_changed(self, event: Input.Changed) -> None:
        """Keep package name synced as the common name is edited."""
        # Update immediately so the package name stays aligned while typing
        self._handle_common_name_change(event.value)

    @on(Checkbox.Changed, ".intended-use-option")
    def on_intended_use_changed(self, event: Checkbox.Changed) -> None:
        """Refresh examples when intended-use selection changes."""
        self._update_examples_from_intended_use()

    @on(Input.Submitted, "#package-name-input")
    def on_package_name_submitted(self, event: Input.Submitted) -> None:
        """Handle manual package name entry."""
        if not event.value.strip():
            self._update_status("Package name is empty.", is_error=True)
            return
        # User has manually overridden the package name
        self._auto_package_name = False

    @on(Input.Changed, "#package-name-input")
    def on_package_name_changed(self, event: Input.Changed) -> None:
        """Track manual package name edits to disable auto-sync."""
        # Only disable auto-sync when the user diverges from derived value
        self._handle_package_name_change(event.value)

    @on(Checkbox.Changed)
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Update include flags when checkboxes change."""
        # Match checkbox IDs to local include flags for packaging
        include_changed = False
        if event.checkbox.id == "include-json":
            self.include_json = event.value
            include_changed = True
        elif event.checkbox.id == "include-txt":
            self.include_txt = event.value
            include_changed = True
        elif event.checkbox.id == "include-meta":
            self.include_meta = event.value
            include_changed = True
        elif event.checkbox.id == "include-manifest":
            self.include_manifest = event.value
            include_changed = True

        # Refresh the included files list when include options change
        if include_changed and self.run_dir:
            self._refresh_included_files(self.run_dir)

    @on(Button.Pressed, "#build-package")
    def on_build_package_pressed(self) -> None:
        """Handle Create Package button press."""
        self._build_package()

    def _build_package(self) -> None:
        """
        Execute packaging with the current UI settings.

        This validates inputs, calls the packaging service, writes
        the metadata JSON, and reports status back to the user.
        """
        run_dir = self._normalize_path(self._get_input_value("run-dir-input"))
        if not run_dir:
            self._update_status("Select a run directory before packaging.", is_error=True)
            return

        # Read optional output directory and package name
        output_dir = self._normalize_path(self._get_input_value("output-dir-input"))
        package_name = self._get_input_value("package-name-input").strip() or None

        # Default package name to the common name if none provided
        if not package_name:
            common_name = self._get_input_value("meta-common-name") or run_dir.name
            package_name = self._derive_package_name(common_name)

        # Assemble packaging options based on UI state
        options = PackageOptions(
            run_dir=run_dir,
            output_dir=output_dir,
            package_name=package_name,
            include_json=self.include_json,
            include_txt=self.include_txt,
            include_meta=self.include_meta,
            include_manifest=self.include_manifest,
        )

        # Run the packaging service
        result = package_selections(options)
        if result.error:
            self._update_status(result.error, is_error=True)
            return

        # Build metadata payload from the editor inputs
        metadata_inputs = self._collect_metadata_inputs()
        include_flags = {
            "json": self.include_json,
            "txt": self.include_txt,
            "meta": self.include_meta,
            "manifest": self.include_manifest,
        }
        metadata_payload = build_package_metadata(
            run_dir=run_dir,
            metadata_inputs=metadata_inputs,
            included_files=result.included_files,
            include_flags=include_flags,
        )

        # Write metadata JSON alongside the package
        metadata_path, meta_error = write_metadata_json(
            result.package_path.parent,
            result.package_path.name,
            metadata_payload,
        )

        if meta_error:
            self._update_status(f"Package created, metadata failed: {meta_error}", is_error=True)
            return

        self._update_status(
            f"Package created: {result.package_path} (metadata: {metadata_path.name})",
            is_error=False,
        )

    def _validate_run_dir(self, path: Path) -> tuple[bool, str, str]:
        """
        Directory browser validator for run directories.

        Args:
            path: Directory path to validate

        Returns:
            (is_valid, type_label, message)
        """
        inventory, error = scan_selections(path)
        if error or inventory is None:
            return (False, "", error or "Invalid run directory")

        # Build a concise message showing what was found
        json_count = len(inventory.selection_json)
        txt_count = len(inventory.selection_txt)
        meta_count = len(inventory.meta_json)
        message = f"{json_count} JSON, {txt_count} TXT, {meta_count} meta files"
        return (True, "run", message)

    def _set_run_dir(self, run_dir: Path) -> None:
        """
        Update run directory state and refresh dependent fields.

        Args:
            run_dir: Newly selected run directory
        """
        # Normalize any accidental selections/ paths to the parent run directory
        run_dir = self._coerce_run_dir(run_dir) or run_dir
        self.run_dir = run_dir
        # Reflect the run directory in the input field
        self._set_input_value("run-dir-input", str(run_dir))
        # Update default output directory and package name
        self._apply_run_dir_defaults(run_dir)
        # Refresh summary of available selection files
        self._refresh_selection_summary(run_dir)
        # Update source/common name fields and included files list
        self._set_source_fields(run_dir)
        self._refresh_included_files(run_dir)
        # Refresh examples based on the intended use selection
        self._update_examples_from_intended_use()

    def _apply_run_dir_defaults(self, run_dir: Path) -> None:
        """
        Apply default output directory and package name for a run directory.

        Args:
            run_dir: Run directory used to derive defaults
        """
        default_output_dir = run_dir / "packages"
        self._set_input_value("output-dir-input", str(default_output_dir))

    def _refresh_selection_summary(self, run_dir: Path) -> None:
        """
        Update the summary widget with discovered selection files.

        Args:
            run_dir: Run directory to scan
        """
        summary_widget = self.query_one("#selection-summary", Static)
        inventory, error = scan_selections(run_dir)
        if error or inventory is None:
            summary_widget.update(error or "No selections found.")
            return

        json_count = len(inventory.selection_json)
        txt_count = len(inventory.selection_txt)
        meta_count = len(inventory.meta_json)
        summary_widget.update(
            f"Found selections in {inventory.selections_dir} | "
            f"JSON: {json_count}, TXT: {txt_count}, Meta: {meta_count}"
        )

    def _refresh_included_files(self, run_dir: Path) -> None:
        """
        Update the included files list based on include toggles.

        Args:
            run_dir: Run directory to scan
        """
        list_widget = self.query_one("#meta-files", Static)
        included, error = collect_included_files(
            run_dir=run_dir,
            include_json=self.include_json,
            include_txt=self.include_txt,
            include_meta=self.include_meta,
        )
        if error:
            list_widget.update(error)
            return

        if not included:
            list_widget.update("No files match include settings.")
            return

        # Display each included file on its own line
        list_widget.update("\n".join(f"- {path.name}" for path in included))

    def _set_default_timestamp(self) -> None:
        """Set the metadata timestamp field to the current local time."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self._get_input_value("meta-created"):
            self._set_input_value("meta-created", timestamp)

    def _set_default_version(self) -> None:
        """Set the default version if the field is empty."""
        if not self._get_input_value("meta-version"):
            self._set_input_value("meta-version", "1.0.0")

    def _set_source_fields(self, run_dir: Path) -> None:
        """
        Populate source and common-name fields based on the run directory.

        Args:
            run_dir: Run directory selected for packaging
        """
        # Source is derived from the run directory name
        self._set_input_value("meta-source", run_dir.name)
        # Default common name to the run directory name if empty
        if not self._get_input_value("meta-common-name"):
            self._set_input_value("meta-common-name", run_dir.name)
            # Keep the package name aligned with the common name by default
            if self._auto_package_name:
                self._set_input_value(
                    "package-name-input",
                    self._derive_package_name(run_dir.name),
                )

    def _collect_metadata_inputs(self) -> dict:
        """
        Collect metadata fields from the left-column editor.

        Returns:
            Dictionary of metadata values keyed for build_package_metadata
        """
        return {
            "created_at": self._get_input_value("meta-created"),
            "author": self._get_input_value("meta-author"),
            "version": self._get_input_value("meta-version"),
            "common_name": self._get_input_value("meta-common-name"),
            "intended_use": self._get_intended_use_values(),
            "examples": self._collect_examples_payload(),
        }

    def _handle_common_name_change(self, raw_value: str) -> None:
        """
        Update the common name input and keep package name in sync.

        Args:
            raw_value: Raw text entered for the common name
        """
        common_name = raw_value.strip()
        if not common_name and self.run_dir:
            common_name = self.run_dir.name

        # Update the input to the normalized common name
        self._set_input_value("meta-common-name", common_name)

        # Only auto-update the package name if it hasn't been manually overridden
        if self._auto_package_name and common_name:
            self._set_input_value(
                "package-name-input",
                self._derive_package_name(common_name),
            )

    def _handle_package_name_change(self, raw_value: str) -> None:
        """
        Detect manual edits to the package name and disable auto-sync.

        Args:
            raw_value: Raw text entered for the package name
        """
        package_name = raw_value.strip()
        if not package_name:
            return

        common_name = self._get_input_value("meta-common-name") or ""
        derived_name = self._derive_package_name(common_name) if common_name else ""
        if package_name != derived_name:
            self._auto_package_name = False

    def _derive_package_name(self, common_name: str) -> str:
        """
        Derive a filesystem-safe package name from the common name.

        Args:
            common_name: Human-friendly package name from the editor

        Returns:
            Filename ending in _selections.zip
        """
        # Normalize whitespace and replace with underscores for stability
        slug = re.sub(r"\s+", "_", common_name.strip().lower())
        # Strip characters that are unsafe for filenames
        slug = re.sub(r"[^a-z0-9_\\-]+", "", slug)
        slug = slug or "package"
        return f"{slug}_selections.zip"

    def _load_name_class_options(self) -> list[tuple[str, str]]:
        """
        Load name class options for the intended-use checkboxes.

        Returns:
            List of (label, value) tuples for the checkbox group
        """
        try:
            policies = load_name_classes(get_default_policy_path())
            options: list[tuple[str, str]] = []
            for name in sorted(policies.keys()):
                label = name.replace("_", " ").title()
                options.append((label, name))
            return options
        except Exception:
            # Provide a minimal fallback so the checkbox group still renders
            return [
                ("First Name", "first_name"),
                ("Last Name", "last_name"),
                ("Place Name", "place_name"),
            ]

    def _update_examples_from_intended_use(self) -> None:
        """Initialize the examples field based on the current intended use selection."""
        name_classes = self._get_intended_use_values()
        self._set_examples_for_name_classes(name_classes)

    def _set_examples_for_name_classes(self, name_classes: list[str]) -> None:
        """
        Populate the examples field from sample JSON files for each name class.

        Args:
            name_classes: Selected name class identifiers
        """
        text_area = self.query_one("#meta-examples", TextArea)
        examples_payload = self._build_examples_payload(name_classes)
        text_area.text = self._format_examples_payload(examples_payload)

    def _load_examples_from_samples(self, name_class: str) -> list[str]:
        """
        Load examples from <run_dir>/selections/<name_class>_sample.json.

        Args:
            name_class: Selected name class identifier

        Returns:
            List of sample names (lowercase) or empty list if unavailable
        """
        if not self.run_dir:
            return []

        sample_path = self.run_dir / "selections" / f"{name_class}_sample.json"
        if not sample_path.exists():
            return []

        try:
            with open(sample_path, encoding="utf-8") as handle:
                payload = json.load(handle)
            samples = payload.get("samples", [])
            if isinstance(samples, list):
                return [str(item) for item in samples if str(item).strip()]
            return []
        except Exception:
            return []

    def _intended_use_checkbox_id(self, name_class: str) -> str:
        """
        Build a stable checkbox id for a name class.

        Args:
            name_class: Name class identifier

        Returns:
            Checkbox id string
        """
        return f"intended-use-{name_class}"

    def _get_intended_use_values(self) -> list[str]:
        """
        Collect selected intended-use name classes.

        Returns:
            List of selected name class identifiers
        """
        selected: list[str] = []
        for _, name_class in self._name_class_options:
            checkbox_id = self._intended_use_checkbox_id(name_class)
            matches = self.query(f"#{checkbox_id}")
            if not matches:
                continue
            checkbox = matches.first()
            if isinstance(checkbox, Checkbox) and checkbox.value:
                selected.append(name_class)
        return selected

    def _build_examples_payload(self, name_classes: list[str]) -> dict[str, list[str]]:
        """
        Build a class-keyed examples payload from sample JSON files.

        Args:
            name_classes: Selected name class identifiers

        Returns:
            Dictionary of name class -> list of samples
        """
        payload: dict[str, list[str]] = {}
        for name_class in name_classes:
            payload[name_class] = self._load_examples_from_samples(name_class)
        return payload

    def _format_examples_payload(self, payload: dict[str, list[str]]) -> str:
        """
        Format the examples payload for the editor text area.

        Args:
            payload: Examples dictionary keyed by name class

        Returns:
            Pretty JSON string for display/editing
        """
        if not payload:
            return ""
        return json.dumps(payload, indent=2)

    def _collect_examples_payload(self) -> dict[str, list[str]]:
        """
        Parse examples from the text area, falling back to samples when invalid.

        Returns:
            Examples dictionary keyed by name class
        """
        name_classes = self._get_intended_use_values()
        raw_text = self._get_text_area_value("meta-examples")
        if not raw_text.strip():
            # No edits yet, default to the current sample files
            return self._build_examples_payload(name_classes)

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            # Preserve the user's intended-use selections even on invalid JSON
            return self._build_examples_payload(name_classes)

        if not isinstance(parsed, dict):
            # Only dict payloads are accepted for class-keyed examples
            return self._build_examples_payload(name_classes)

        payload: dict[str, list[str]] = {}
        for name_class in name_classes:
            if name_class not in parsed:
                # Fill any missing classes with their sample defaults
                payload[name_class] = self._load_examples_from_samples(name_class)
                continue
            items = parsed.get(name_class)
            if isinstance(items, list):
                cleaned = [str(item) for item in items if str(item).strip()]
                payload[name_class] = cleaned
            else:
                # Fall back to sample data if the JSON entry isn't a list
                payload[name_class] = self._load_examples_from_samples(name_class)
        return payload

    def _update_status(self, message: str, is_error: bool) -> None:
        """
        Update the status message area with success or error text.

        Args:
            message: Message to display
            is_error: True for error styling, False for normal
        """
        status_widget = self.query_one("#package-status", Static)
        status_widget.update(message)
        status_widget.remove_class("status-error", "status-success")
        status_widget.add_class("status-error" if is_error else "status-success")

    def _get_default_working_dir(self) -> Path:
        """
        Determine a sensible default directory for browsing.

        Returns:
            Path to the _working directory if available, otherwise home
        """
        # Derive repository root based on the module location
        repo_root = Path(__file__).resolve().parents[4]
        working_dir = repo_root / "_working"
        if working_dir.exists():
            return working_dir
        return Path.home()

    def _get_input_value(self, widget_id: str) -> str:
        """
        Read the current value of a Textual Input widget.

        Args:
            widget_id: ID of the Input widget

        Returns:
            Input value as a string (empty if widget not found)
        """
        try:
            return self.query_one(f"#{widget_id}", Input).value
        except Exception:
            return ""

    def _set_input_value(self, widget_id: str, value: str) -> None:
        """
        Set the value of a Textual Input widget, ignoring errors.

        Args:
            widget_id: ID of the Input widget
            value: New value to set
        """
        try:
            widget = self.query_one(f"#{widget_id}", Input)
            widget.value = value
        except Exception:
            # Fail silently to avoid crashing the screen on missing widgets
            return

    def _get_text_area_value(self, widget_id: str) -> str:
        """
        Read the current content of a TextArea widget.

        Args:
            widget_id: ID of the TextArea widget

        Returns:
            Text content (empty string if unavailable)
        """
        try:
            text_area = self.query_one(f"#{widget_id}", TextArea)
            return text_area.text
        except Exception:
            return ""

    def _normalize_path(self, raw: str) -> Path | None:
        """
        Normalize a path string into a Path object.

        Args:
            raw: Raw string input from a widget

        Returns:
            Normalized Path or None if input is empty
        """
        raw = raw.strip()
        if not raw:
            return None
        return Path(raw).expanduser()

    def _coerce_run_dir(self, path: Path | None) -> Path | None:
        """
        Normalize a user-supplied path to a run directory.

        Users sometimes select the selections/ folder directly. In that case,
        return the parent run directory so defaults and packaging work as expected.

        Args:
            path: Candidate path from input or browser

        Returns:
            Run directory path, or None if input was None
        """
        if path is None:
            return None
        if path.name == "selections":
            return path.parent
        return path
