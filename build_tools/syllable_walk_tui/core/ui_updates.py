"""
UI status update helpers for Syllable Walker TUI.

Contains functions for updating corpus status labels in the oscillator panels.
These are extracted from app.py to reduce complexity and enable testing.

The status label shows:
- Corpus directory info (timestamp, type)
- Files loaded/loading status
- Ready state with syllable count
- Error states with actionable messages
"""

from typing import TYPE_CHECKING

from textual.widgets import Label

if TYPE_CHECKING:
    from build_tools.syllable_walk_tui.core.app import SyllableWalkerApp


def _get_corpus_prefix(corpus_type: str | None) -> str:
    """Get the file prefix based on corpus type."""
    return corpus_type.lower() if corpus_type else "nltk"


def update_corpus_status_quick_load(
    app: "SyllableWalkerApp",
    patch_name: str,
    corpus_info: str,
    corpus_type: str | None,
) -> None:
    """
    Update status label after quick metadata loads (syllables + frequencies).

    Shows checkmarks for loaded files and a spinner for annotated data pending.

    Args:
        app: Application instance for widget queries
        patch_name: "A" or "B"
        corpus_info: Display string for corpus directory (e.g., "20260110_143022_pyphen")
        corpus_type: Corpus type (e.g., "pyphen", "nltk")
    """
    try:
        status_label = app.query_one(f"#corpus-status-{patch_name}", Label)
        corpus_prefix = _get_corpus_prefix(corpus_type)

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


def update_corpus_status_loading(
    app: "SyllableWalkerApp",
    patch_name: str,
    corpus_info: str,
    corpus_type: str | None,
) -> None:
    """
    Update status label to show annotated data is loading.

    Args:
        app: Application instance for widget queries
        patch_name: "A" or "B"
        corpus_info: Display string for corpus directory
        corpus_type: Corpus type (e.g., "pyphen", "nltk")
    """
    try:
        status_label = app.query_one(f"#corpus-status-{patch_name}", Label)
        corpus_prefix = _get_corpus_prefix(corpus_type)

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
        print(f"Warning: Could not update status label (loading): {e}")


def update_corpus_status_ready(
    app: "SyllableWalkerApp",
    patch_name: str,
    corpus_info: str,
    corpus_type: str | None,
    syllable_count: int,
    source: str,
    load_time: str | int,
    file_name: str | None = None,
) -> None:
    """
    Update status label to show corpus is ready.

    Args:
        app: Application instance for widget queries
        patch_name: "A" or "B"
        corpus_info: Display string for corpus directory
        corpus_type: Corpus type (e.g., "pyphen", "nltk")
        syllable_count: Number of syllables loaded
        source: Data source ("sqlite" or "json")
        load_time: Load time in milliseconds
        file_name: JSON filename if source is "json"
    """
    try:
        status_label = app.query_one(f"#corpus-status-{patch_name}", Label)
        corpus_prefix = _get_corpus_prefix(corpus_type)

        if source == "sqlite":
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
            display_name = file_name or "annotated.json"
            files_ready = (
                f"{corpus_info}\n"
                f"─────────────────\n"
                f"✓ {corpus_prefix}_syllables_unique.txt\n"
                f"✓ {corpus_prefix}_syllables_frequencies.json\n"
                f"✓ {display_name} ({load_time}ms, JSON)\n"
                f"─────────────────\n"
                f"Ready: {syllable_count:,} syllables"
            )
        status_label.update(files_ready)
        status_label.remove_class("corpus-status")
        status_label.add_class("corpus-status-valid")
    except Exception as e:
        print(f"Warning: Could not update status label (complete): {e}")


def update_corpus_status_error(
    app: "SyllableWalkerApp",
    patch_name: str,
    corpus_info: str,
    corpus_type: str | None,
    error_msg: str,
) -> None:
    """
    Update status label to show an error occurred.

    Args:
        app: Application instance for widget queries
        patch_name: "A" or "B"
        corpus_info: Display string for corpus directory
        corpus_type: Corpus type (e.g., "pyphen", "nltk")
        error_msg: Error message to display (truncated to 30 chars)
    """
    try:
        status_label = app.query_one(f"#corpus-status-{patch_name}", Label)
        corpus_prefix = _get_corpus_prefix(corpus_type)

        # Truncate long error messages
        display_error = error_msg[:30] + "..." if len(error_msg) > 30 else error_msg

        files_error = (
            f"{corpus_info}\n"
            f"─────────────────\n"
            f"✓ {corpus_prefix}_syllables_unique.txt\n"
            f"✓ {corpus_prefix}_syllables_frequencies.json\n"
            f"✗ {corpus_prefix}_syllables_annotated.json\n"
            f"─────────────────\n"
            f"Error: {display_error}"
        )
        status_label.update(files_error)
        status_label.remove_class("corpus-status-valid")
        status_label.add_class("corpus-status")
    except Exception:  # nosec B110
        pass  # Ignore UI update errors


def update_corpus_status_not_annotated(
    app: "SyllableWalkerApp",
    patch_name: str,
    corpus_info: str,
    corpus_type: str | None,
) -> None:
    """
    Update status label when annotated data file is not found.

    This indicates the user needs to run syllable_feature_annotator.

    Args:
        app: Application instance for widget queries
        patch_name: "A" or "B"
        corpus_info: Display string for corpus directory
        corpus_type: Corpus type (e.g., "pyphen", "nltk")
    """
    try:
        status_label = app.query_one(f"#corpus-status-{patch_name}", Label)
        corpus_prefix = _get_corpus_prefix(corpus_type)

        files_error = (
            f"{corpus_info}\n"
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


def update_center_corpus_label(
    app: "SyllableWalkerApp",
    patch_name: str,
    dir_name: str,
    corpus_type: str | None,
) -> None:
    """
    Update the center panel corpus label with directory name and type.

    Args:
        app: Application instance for widget queries
        patch_name: "A" or "B"
        dir_name: Directory name (e.g., "20260110_115601_nltk")
        corpus_type: Corpus type (e.g., "pyphen", "nltk")
    """
    try:
        corpus_label = app.query_one(f"#walks-corpus-{patch_name}", Label)
        corpus_label.update(f"{dir_name} ({corpus_type})")
        corpus_label.remove_class("output-placeholder")
    except Exception as e:
        print(f"Warning: Could not update center corpus label: {e}")
