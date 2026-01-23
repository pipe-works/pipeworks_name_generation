"""
Action implementations for Syllable Walker TUI.

Contains action logic extracted from the main App class.
The actual action_* methods remain on the App (Textual requirement),
but delegate complex logic here for testability and reuse.
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from build_tools.syllable_walk_tui.core.app import SyllableWalkerApp
    from build_tools.syllable_walk_tui.modules.oscillator import PatchState


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
