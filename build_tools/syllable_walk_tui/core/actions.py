"""
Action implementations for Syllable Walker TUI.

Contains action logic extracted from the main App class.
The actual action_* methods remain on the App (Textual requirement),
but delegate complex logic here for testability and reuse.

This module provides:
- Patch validation helpers (validate_patch_ready)
- Database viewer opening (open_database_for_patch)
- Browse directory selection (get_initial_browse_dir)
- Metrics computation (compute_metrics_for_patch)
- Panel update helpers (update_combiner_panel, update_selector_panel)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from build_tools.syllable_walk_tui.core.app import SyllableWalkerApp
    from build_tools.syllable_walk_tui.modules.oscillator import PatchState


@dataclass
class PatchValidationResult:
    """Result of patch validation for generation readiness."""

    is_valid: bool
    patch: "PatchState | None" = None
    error_message: str | None = None


def compute_metrics_for_patch(patch: "PatchState"):
    """
    Compute corpus shape metrics for a patch.

    Args:
        patch: PatchState to compute metrics for

    Returns:
        CorpusShapeMetrics if patch has loaded data, None otherwise
    """
    from build_tools.syllable_walk_tui.services.metrics import compute_corpus_shape_metrics

    # Check if patch has required data
    if not patch.syllables or not patch.frequencies or not patch.annotated_data:
        return None

    try:
        return compute_corpus_shape_metrics(
            patch.syllables,
            patch.frequencies,
            patch.annotated_data,
        )
    except Exception:
        # Computation failed
        return None


def open_database_for_patch(
    app: "SyllableWalkerApp",
    patch_name: str,
) -> None:
    """
    Open database viewer for the specified patch.

    Args:
        app: Application instance for screen navigation and notifications
        patch_name: "A" or "B"
    """
    from build_tools.syllable_walk_tui.modules.database import DatabaseScreen

    patch = app.state.patch_a if patch_name == "A" else app.state.patch_b

    if patch.corpus_dir:
        db_path = patch.corpus_dir / "data" / "corpus.db"
        if db_path.exists():
            app.push_screen(DatabaseScreen(db_path=db_path, patch_name=patch_name))
        else:
            app.notify(
                f"No corpus.db found for Patch {patch_name}. "
                "The corpus may need to be rebuilt with the pipeline.",
                severity="warning",
            )
    else:
        app.notify(
            f"No corpus loaded for Patch {patch_name}. "
            f"Press {patch_name == 'A' and '1' or '2'} to select a corpus directory.",
            severity="warning",
        )


def get_initial_browse_dir(app: "SyllableWalkerApp", patch_name: str) -> Path:
    """
    Get smart initial directory for corpus browser.

    Priority order:
    1. Patch's current corpus_dir (if already set)
    2. Last browsed directory (if set)
    3. _working/output/ (if exists)
    4. Home directory (fallback)

    Args:
        app: Application instance for state access
        patch_name: "A" or "B"

    Returns:
        Path to start browsing from
    """
    patch = app.state.patch_a if patch_name == "A" else app.state.patch_b

    # 1. Use patch's current corpus_dir if set
    if patch.corpus_dir and patch.corpus_dir.exists():
        return patch.corpus_dir

    # 2. Use last browsed directory if set
    if app.state.last_browse_dir and app.state.last_browse_dir.exists():
        return app.state.last_browse_dir

    # 3. Try _working/output/ if it exists
    project_root = Path(__file__).parent.parent.parent
    working_output = project_root / "_working" / "output"
    if working_output.exists() and working_output.is_dir():
        return working_output

    # 4. Fall back to home directory
    return Path.home()


def validate_patch_ready(
    app: "SyllableWalkerApp",
    patch_name: str,
) -> PatchValidationResult:
    """
    Validate that a patch is ready for generation operations.

    Args:
        app: Application instance for state access and notifications
        patch_name: "A" or "B"

    Returns:
        PatchValidationResult with is_valid=True and patch if ready,
        or is_valid=False with error_message if not ready.
    """
    patch = app.state.patch_a if patch_name == "A" else app.state.patch_b

    if not patch.is_ready_for_generation():
        key_hint = 1 if patch_name == "A" else 2
        error_msg = f"Patch {patch_name}: Corpus not loaded. Press {key_hint} to select a corpus."
        app.notify(error_msg, severity="warning")
        return PatchValidationResult(is_valid=False, error_message=error_msg)

    return PatchValidationResult(is_valid=True, patch=patch)


def update_combiner_panel(
    app: "SyllableWalkerApp",
    patch_name: str,
    meta_output: dict,
) -> None:
    """
    Update the combiner panel with generation metadata.

    Args:
        app: Application instance for widget queries
        patch_name: "A" or "B"
        meta_output: Metadata dict from combiner result
    """
    from build_tools.syllable_walk_tui.modules.generator import CombinerPanel

    try:
        panel = app.query_one(f"#combiner-panel-{patch_name.lower()}", CombinerPanel)
        panel.update_output(meta_output)
    except Exception as e:
        print(f"Warning: Could not update combiner panel: {e}")


def update_selector_panel(
    app: "SyllableWalkerApp",
    patch_name: str,
    meta_output: dict,
    selected_names: list[str],
) -> None:
    """
    Update the selector panel with selection metadata.

    Args:
        app: Application instance for widget queries
        patch_name: "A" or "B"
        meta_output: Metadata dict from selector result
        selected_names: List of selected name strings
    """
    from build_tools.syllable_walk_tui.modules.generator import SelectorPanel

    try:
        panel = app.query_one(f"#selector-panel-{patch_name.lower()}", SelectorPanel)
        panel.update_output(meta_output, selected_names)
    except Exception as e:
        print(f"Warning: Could not update selector panel: {e}")
