"""SQLite database access layer for the syllable walker web interface.

This module provides functions to query the corpus.db SQLite database
for syllable data, avoiding the need to load large JSON files into memory.

The database schema stores syllables with their 12 phonetic features and
frequency counts, with indexes optimized for common query patterns.

Functions:
    load_syllables_from_sqlite: Load all syllables with features
    get_syllable_count: Get total syllable count
    syllable_exists: Check if a syllable exists
    get_random_syllable: Get a random syllable
"""

from __future__ import annotations

import json
import random
import sqlite3
from pathlib import Path

# The 12 phonetic features in the database schema
FEATURE_COLUMNS = [
    "starts_with_vowel",
    "starts_with_cluster",
    "starts_with_heavy_cluster",
    "contains_plosive",
    "contains_fricative",
    "contains_liquid",
    "contains_nasal",
    "short_vowel",
    "long_vowel",
    "ends_with_vowel",
    "ends_with_nasal",
    "ends_with_stop",
]


def _get_connection(db_path: Path) -> sqlite3.Connection:
    """Get a read-only connection to the database.

    Args:
        db_path: Path to corpus.db

    Returns:
        SQLite connection with row_factory set to sqlite3.Row
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_syllables_from_sqlite(db_path: Path) -> list[dict]:
    """Load all syllables with features from the database.

    This is the primary data loading function for the web interface.
    Returns data in the same format as the annotated JSON files.

    Args:
        db_path: Path to corpus.db

    Returns:
        List of dicts with 'syllable', 'frequency', and 'features' keys

    Example:
        >>> syllables = load_syllables_from_sqlite(Path("corpus.db"))
        >>> syllables[0]
        {'syllable': 'ab', 'frequency': 1, 'features': {'starts_with_vowel': True, ...}}
    """
    conn = _get_connection(db_path)
    try:
        # FEATURE_COLUMNS is a constant defined in this module, not user input
        cursor = conn.execute(f"""
            SELECT syllable, frequency, {', '.join(FEATURE_COLUMNS)}
            FROM syllables
            ORDER BY frequency DESC
            """)  # nosec B608 - FEATURE_COLUMNS is a module constant

        results = []
        for row in cursor:
            features = {col: bool(row[col]) for col in FEATURE_COLUMNS}
            results.append(
                {
                    "syllable": row["syllable"],
                    "frequency": row["frequency"],
                    "features": features,
                }
            )

        return results
    finally:
        conn.close()


def get_syllable_count(db_path: Path) -> int:
    """Get the total number of syllables in the database.

    Args:
        db_path: Path to corpus.db

    Returns:
        Total syllable count
    """
    conn = _get_connection(db_path)
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM syllables")
        count: int = cursor.fetchone()[0]
        return count
    finally:
        conn.close()


def syllable_exists(db_path: Path, syllable: str) -> bool:
    """Check if a syllable exists in the database.

    Args:
        db_path: Path to corpus.db
        syllable: Syllable to check

    Returns:
        True if syllable exists, False otherwise
    """
    conn = _get_connection(db_path)
    try:
        cursor = conn.execute("SELECT 1 FROM syllables WHERE syllable = ? LIMIT 1", (syllable,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def get_syllable_data(db_path: Path, syllable: str) -> dict | None:
    """Get data for a specific syllable.

    Args:
        db_path: Path to corpus.db
        syllable: Syllable to look up

    Returns:
        Dict with syllable data, or None if not found
    """
    conn = _get_connection(db_path)
    try:
        # FEATURE_COLUMNS is a constant defined in this module, not user input
        cursor = conn.execute(
            f"""
            SELECT syllable, frequency, {', '.join(FEATURE_COLUMNS)}
            FROM syllables
            WHERE syllable = ?
            """,  # nosec B608 - FEATURE_COLUMNS is a module constant
            (syllable,),
        )
        row = cursor.fetchone()

        if row is None:
            return None

        features = {col: bool(row[col]) for col in FEATURE_COLUMNS}
        return {
            "syllable": row["syllable"],
            "frequency": row["frequency"],
            "features": features,
        }
    finally:
        conn.close()


def get_random_syllable(db_path: Path, seed: int | None = None) -> str:
    """Get a random syllable from the database.

    Uses frequency-weighted random selection if seed is provided for
    reproducibility.

    Args:
        db_path: Path to corpus.db
        seed: Optional random seed for reproducibility

    Returns:
        Random syllable string
    """
    conn = _get_connection(db_path)
    try:
        # Get all syllables with frequencies
        cursor = conn.execute("SELECT syllable, frequency FROM syllables")
        rows = cursor.fetchall()

        if not rows:
            raise ValueError("Database is empty")

        # Create RNG instance (deterministic if seed provided)
        rng = random.Random(seed)  # nosec B311 - deterministic generation

        # Frequency-weighted selection
        syllables = [row["syllable"] for row in rows]
        weights = [row["frequency"] for row in rows]

        result: str = rng.choices(syllables, weights=weights, k=1)[0]
        return result
    finally:
        conn.close()


def load_syllables_from_json(json_path: Path) -> list[dict]:
    """Load syllables from annotated JSON file (fallback when no DB).

    Args:
        json_path: Path to *_syllables_annotated.json

    Returns:
        List of dicts with syllable data
    """
    with open(json_path, encoding="utf-8") as f:
        data: list[dict] = json.load(f)
        return data


def load_syllables(
    db_path: Path | None = None, json_path: Path | None = None
) -> tuple[list[dict], str]:
    """Load syllables from database or JSON, with automatic fallback.

    Prefers SQLite database for performance, falls back to JSON if
    database is not available.

    Args:
        db_path: Path to corpus.db (optional)
        json_path: Path to annotated JSON (optional)

    Returns:
        Tuple of (syllables list, source description)

    Raises:
        ValueError: If neither db_path nor json_path is valid
    """
    # Try database first
    if db_path and db_path.exists():
        try:
            syllables = load_syllables_from_sqlite(db_path)
            return syllables, f"SQLite ({len(syllables):,} syllables)"
        except Exception:  # nosec B110 - intentional fallback to JSON
            pass  # Fall through to JSON

    # Try JSON fallback
    if json_path and json_path.exists():
        syllables = load_syllables_from_json(json_path)
        return syllables, f"JSON ({len(syllables):,} syllables)"

    raise ValueError("No valid data source (corpus.db or annotated JSON) found")
