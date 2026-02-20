"""
Corpus loading service for the web application.

Loads annotated syllables from SQLite or JSON for a given pipeline run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_corpus(
    corpus_db_path: Path | None = None,
    annotated_json_path: Path | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Load annotated syllables from a pipeline run.

    Delegates to ``build_tools.syllable_walk.db.load_syllables``, which
    prefers SQLite and falls back to JSON automatically.

    Args:
        corpus_db_path: Path to ``corpus.db`` (SQLite).
        annotated_json_path: Path to annotated JSON file.

    Returns:
        Tuple of (syllables_list, source_description).
        ``syllables_list`` contains dicts with keys:
        ``syllable`` (str), ``frequency`` (int), ``features`` (dict[str, bool]).
    """
    from build_tools.syllable_walk.db import load_syllables

    return load_syllables(db_path=corpus_db_path, json_path=annotated_json_path)
