"""Generation-domain helpers for the webapp API.

This module owns class/syllable mapping rules, package option discovery,
selection statistics, and deterministic sampling behavior used by
``/api/generate`` and related generation endpoints.
"""

from __future__ import annotations

import random
import re
import sqlite3
from pathlib import Path
from typing import Any, Sequence

from pipeworks_name_generation.webapp.constants import (
    GENERATION_CLASS_KEYS,
    GENERATION_CLASS_PATTERNS,
    GENERATION_NAME_CLASSES,
    GENERATION_SYLLABLE_LABELS,
)
from pipeworks_name_generation.webapp.storage import _quote_identifier


def _coerce_generation_count(raw_count: Any) -> int:
    """Parse and bound requested generation count for SQLite mode."""
    try:
        count = int(raw_count)
    except (TypeError, ValueError) as exc:
        raise ValueError("Field 'generation_count' must be an integer.") from exc
    if count < 1:
        raise ValueError("Field 'generation_count' must be >= 1.")
    if count > 100000:
        raise ValueError("Field 'generation_count' must be <= 100000.")
    return count


def _coerce_optional_seed(raw_seed: Any) -> int | None:
    """Parse optional seed value for local RNG-based sampling."""
    if raw_seed is None:
        return None
    if isinstance(raw_seed, str) and not raw_seed.strip():
        return None
    try:
        return int(raw_seed)
    except (TypeError, ValueError) as exc:
        raise ValueError("Field 'seed' must be an integer when provided.") from exc


def _coerce_bool(raw_value: Any) -> bool:
    """Parse loose bool payload values used by UI and API clients."""
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, int):
        return raw_value != 0
    if isinstance(raw_value, str):
        normalized = raw_value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", ""}:
            return False
    raise ValueError("Field 'unique_only' must be a boolean-compatible value.")


def _coerce_output_format(raw_format: Any) -> str:
    """Validate output format enum currently supported by the generate route."""
    normalized = str(raw_format).strip().lower() if raw_format is not None else "json"
    if normalized not in {"json", "txt"}:
        raise ValueError("Field 'output_format' must be one of: json, txt.")
    return normalized


def _read_all_values_from_table(conn: sqlite3.Connection, table_name: str) -> list[str]:
    """Read all values from one imported txt table preserving row order."""
    quoted = _quote_identifier(table_name)
    query = f"""
        SELECT value
        FROM {quoted}
        ORDER BY line_number, id
        """  # nosec B608
    rows = conn.execute(query).fetchall()
    return [str(row["value"]) for row in rows]


def _collect_generation_source_values(
    conn: sqlite3.Connection, *, class_key: str, package_id: int, syllable_key: str
) -> list[str]:
    """Collect candidate values from SQLite tables matching selection filters.

    Raises:
        ValueError: For unsupported selection keys or when no matching values
            exist for the requested selection.
    """
    matching_tables = _list_generation_matching_tables(
        conn,
        class_key=class_key,
        package_id=package_id,
        syllable_key=syllable_key,
    )
    if not matching_tables:
        raise ValueError("No imported tables match class/package/syllable selection.")

    values: list[str] = []
    for item in matching_tables:
        table_name = str(item["table_name"])
        values.extend(_read_all_values_from_table(conn, table_name))

    # Keep non-empty strings only; importer already trims values but this keeps
    # generation resilient to unexpected DB contents.
    normalized_values = [value.strip() for value in values if str(value).strip()]
    if not normalized_values:
        raise ValueError("No candidate values found for the selected generation scope.")
    return normalized_values


def _sample_generation_values(
    values: Sequence[str], *, count: int, seed: int | None, unique_only: bool
) -> list[str]:
    """Sample output names from candidate values using a local RNG instance.

    The RNG is per-request so seed usage never mutates global random state.
    """
    # Non-cryptographic sampling is intentional for deterministic API behavior.
    rng = random.Random(seed) if seed is not None else random.Random()  # nosec B311
    if unique_only:
        unique_values = list(dict.fromkeys(str(value) for value in values))
        if not unique_values:
            return []
        if count >= len(unique_values):
            shuffled = unique_values[:]
            rng.shuffle(shuffled)
            return shuffled
        return rng.sample(unique_values, k=count)

    if not values:
        return []
    return [str(rng.choice(values)) for _ in range(count)]


def _map_source_txt_name_to_generation_class(source_txt_name: str) -> str | None:
    """Map one imported txt filename to a canonical generation class key.

    The source filename stem is normalized to lowercase ``snake_case`` before
    matching against known pattern hints for each Generation tab class.

    Args:
        source_txt_name: Imported ``*.txt`` source filename.

    Returns:
        Canonical generation class key, or ``None`` when no mapping is known.
    """
    normalized = re.sub(r"[^a-z0-9]+", "_", Path(source_txt_name).stem.lower()).strip("_")
    for class_key, patterns in GENERATION_CLASS_PATTERNS.items():
        if any(pattern in normalized for pattern in patterns):
            return class_key
    return None


def _extract_syllable_option_from_source_txt_name(source_txt_name: str) -> str | None:
    """Extract normalized syllable option key from one source txt filename.

    Supported values are keys like ``2syl``, ``3syl``, ``4syl``, and ``all``
    derived from common source filename conventions (for example
    ``nltk_first_name_2syl.txt`` or ``nltk_first_name_all.txt``).

    Args:
        source_txt_name: Imported ``*.txt`` source filename.

    Returns:
        Normalized syllable option key, or ``None`` when no known mode exists.
    """
    normalized = re.sub(r"[^a-z0-9]+", "_", Path(source_txt_name).stem.lower()).strip("_")
    if "_all" in normalized or normalized.endswith("all"):
        return "all"

    match = re.search(r"_(\d+)syl(?:_|$)", normalized)
    if match:
        return f"{match.group(1)}syl"

    return None


def _syllable_option_sort_key(option_key: str) -> tuple[int, int, str]:
    """Return deterministic sort key for syllable option keys.

    Numeric options (for example ``2syl``) are sorted by number first, followed
    by non-numeric options such as ``all``.
    """
    if option_key == "all":
        return (1, 9999, option_key)

    match = re.fullmatch(r"(\d+)syl", option_key)
    if match:
        return (0, int(match.group(1)), option_key)

    return (2, 9999, option_key)


def _list_generation_syllable_options(
    conn: sqlite3.Connection, *, class_key: str, package_id: int
) -> list[dict[str, str]]:
    """List syllable options for one package within one generation class.

    Args:
        conn: Open SQLite connection.
        class_key: Canonical generation class key.
        package_id: Imported package id.

    Returns:
        Sorted syllable option dictionaries with ``key`` and ``label`` values.

    Raises:
        ValueError: If ``class_key`` is not one of the supported generation
            classes.
    """
    if class_key not in GENERATION_CLASS_KEYS:
        raise ValueError(f"Unsupported generation class_key: {class_key!r}")

    rows = conn.execute(
        """
        SELECT source_txt_name
        FROM package_tables
        WHERE package_id = ?
        ORDER BY source_txt_name COLLATE NOCASE
        """,
        (package_id,),
    ).fetchall()

    option_keys: set[str] = set()
    for row in rows:
        source_txt_name = str(row["source_txt_name"])
        mapped_class = _map_source_txt_name_to_generation_class(source_txt_name)
        if mapped_class != class_key:
            continue

        option_key = _extract_syllable_option_from_source_txt_name(source_txt_name)
        if option_key is None:
            continue
        option_keys.add(option_key)

    sorted_keys = sorted(option_keys, key=_syllable_option_sort_key)
    return [{"key": key, "label": GENERATION_SYLLABLE_LABELS.get(key, key)} for key in sorted_keys]


def _validate_generation_syllable_key(syllable_key: str) -> str:
    """Validate and normalize one generation syllable mode key.

    Accepted values are ``all`` or a numeric ``Nsyl`` shape (for example
    ``2syl``). Invalid values fail fast so API callers receive a clear,
    deterministic validation error.

    Args:
        syllable_key: Raw syllable key string from API query.

    Returns:
        Lower-cased, validated syllable key.

    Raises:
        ValueError: If the key does not match supported syllable modes.
    """
    normalized = syllable_key.strip().lower()
    if normalized == "all":
        return normalized
    if re.fullmatch(r"\d+syl", normalized):
        return normalized
    raise ValueError(f"Unsupported generation syllable_key: {syllable_key!r}")


def _list_generation_matching_tables(
    conn: sqlite3.Connection, *, class_key: str, package_id: int, syllable_key: str
) -> list[dict[str, Any]]:
    """List imported txt tables matching one generation class+syllable filter.

    The filter is based on each ``package_tables.source_txt_name`` value:
    filename patterns are mapped to canonical class keys and syllable keys, and
    only exact matches are returned.

    Args:
        conn: Open SQLite connection.
        class_key: Canonical generation class key.
        package_id: Imported package id.
        syllable_key: Validated syllable option key (for example ``2syl``).

    Returns:
        Matching table metadata dictionaries with ``table_name`` and
        ``row_count`` values.

    Raises:
        ValueError: If ``class_key`` or ``syllable_key`` is unsupported.
    """
    if class_key not in GENERATION_CLASS_KEYS:
        raise ValueError(f"Unsupported generation class_key: {class_key!r}")
    normalized_syllable_key = _validate_generation_syllable_key(syllable_key)

    rows = conn.execute(
        """
        SELECT source_txt_name, table_name, row_count
        FROM package_tables
        WHERE package_id = ?
        ORDER BY source_txt_name COLLATE NOCASE
        """,
        (package_id,),
    ).fetchall()

    matches: list[dict[str, Any]] = []
    for row in rows:
        source_txt_name = str(row["source_txt_name"])
        mapped_class = _map_source_txt_name_to_generation_class(source_txt_name)
        if mapped_class != class_key:
            continue

        mapped_syllable = _extract_syllable_option_from_source_txt_name(source_txt_name)
        if mapped_syllable != normalized_syllable_key:
            continue

        matches.append(
            {
                "source_txt_name": source_txt_name,
                "table_name": str(row["table_name"]),
                "row_count": int(row["row_count"]),
            }
        )

    return matches


def _count_distinct_values_across_tables(
    conn: sqlite3.Connection, table_names: Sequence[str]
) -> int:
    """Count distinct ``value`` strings across one or more imported txt tables.

    Args:
        conn: Open SQLite connection.
        table_names: Physical table names to include in the distinct count.

    Returns:
        Count of unique ``value`` strings across all listed tables.
    """
    if not table_names:
        return 0

    unique_values: set[str] = set()
    for table_name in table_names:
        quoted = _quote_identifier(table_name)
        query = f"SELECT value FROM {quoted}"  # nosec B608
        rows = conn.execute(query).fetchall()
        for row in rows:
            unique_values.add(str(row["value"]))
    return len(unique_values)


def _get_generation_selection_stats(
    conn: sqlite3.Connection, *, class_key: str, package_id: int, syllable_key: str
) -> dict[str, int]:
    """Compute size/uniqueness limits for one Generation card selection.

    Args:
        conn: Open SQLite connection.
        class_key: Canonical generation class key.
        package_id: Imported package id.
        syllable_key: Syllable mode key selected by the user.

    Returns:
        Dictionary with:
        - ``max_items``: Total available rows across matching table(s).
        - ``max_unique_combinations``: Distinct values across matching table(s).
    """
    matching_tables = _list_generation_matching_tables(
        conn,
        class_key=class_key,
        package_id=package_id,
        syllable_key=syllable_key,
    )
    if not matching_tables:
        return {"max_items": 0, "max_unique_combinations": 0}

    max_items = sum(int(item["row_count"]) for item in matching_tables)
    table_names = [str(item["table_name"]) for item in matching_tables]
    max_unique_combinations = _count_distinct_values_across_tables(conn, table_names)
    return {
        "max_items": max_items,
        "max_unique_combinations": max_unique_combinations,
    }


def _list_generation_package_options(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return per-class package options for Generation tab dropdown cards.

    The response is intentionally grouped by canonical generation class. Each
    class includes packages that currently have at least one imported txt source
    file mapping to that class.

    Args:
        conn: Open SQLite connection.

    Returns:
        List of class dictionaries with package option entries.
    """
    rows = conn.execute("""
        SELECT
            p.id AS package_id,
            p.package_name,
            t.source_txt_name
        FROM imported_packages AS p
        INNER JOIN package_tables AS t ON t.package_id = p.id
        ORDER BY p.package_name COLLATE NOCASE, p.id, t.source_txt_name COLLATE NOCASE
        """).fetchall()

    per_class: dict[str, dict[int, dict[str, Any]]] = {
        class_key: {} for class_key, _ in GENERATION_NAME_CLASSES
    }
    for row in rows:
        class_key = _map_source_txt_name_to_generation_class(str(row["source_txt_name"]))
        if class_key is None:
            continue

        package_id = int(row["package_id"])
        package_name = str(row["package_name"])
        source_txt_name = str(row["source_txt_name"])

        existing = per_class[class_key].get(package_id)
        if existing is None:
            per_class[class_key][package_id] = {
                "package_id": package_id,
                "package_name": package_name,
                "source_txt_names": [source_txt_name],
            }
            continue

        existing["source_txt_names"].append(source_txt_name)

    result: list[dict[str, Any]] = []
    for class_key, label in GENERATION_NAME_CLASSES:
        packages = list(per_class[class_key].values())
        packages.sort(key=lambda item: (str(item["package_name"]).lower(), int(item["package_id"])))
        for package in packages:
            deduped_sources = sorted({str(name) for name in package["source_txt_names"]})
            package["source_txt_names"] = deduped_sources
        result.append({"key": class_key, "label": label, "packages": packages})

    return result


__all__ = [
    "_coerce_generation_count",
    "_coerce_optional_seed",
    "_coerce_bool",
    "_coerce_output_format",
    "_read_all_values_from_table",
    "_collect_generation_source_values",
    "_sample_generation_values",
    "_map_source_txt_name_to_generation_class",
    "_extract_syllable_option_from_source_txt_name",
    "_syllable_option_sort_key",
    "_list_generation_syllable_options",
    "_validate_generation_syllable_key",
    "_list_generation_matching_tables",
    "_count_distinct_values_across_tables",
    "_get_generation_selection_stats",
    "_list_generation_package_options",
]
