"""Repository helpers for user favorites stored in SQLite."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable


def _normalize_tags(raw_tags: Iterable[str]) -> list[str]:
    """Normalize user-provided tags into a unique, ordered list."""
    seen: set[str] = set()
    normalized: list[str] = []
    for tag in raw_tags:
        cleaned = str(tag).strip()
        if not cleaned:
            continue
        lowered = cleaned.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(cleaned)
    return normalized


def _ensure_tags(conn: Any, tags: Iterable[str]) -> list[int]:
    """Insert tags when missing and return their ids."""
    normalized = _normalize_tags(tags)
    if not normalized:
        return []

    for tag in normalized:
        conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))

    placeholders = ",".join(["?"] * len(normalized))
    rows = conn.execute(
        f"SELECT id, name FROM tags WHERE name IN ({placeholders})",  # nosec B608
        normalized,
    ).fetchall()
    id_by_name = {row["name"].casefold(): int(row["id"]) for row in rows}
    return [id_by_name[tag.casefold()] for tag in normalized if tag.casefold() in id_by_name]


def _serialize_metadata(metadata: dict[str, Any]) -> str:
    """Serialize metadata JSON with stable formatting."""
    return json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))


def _deserialize_metadata(payload: str) -> dict[str, Any]:
    """Parse metadata JSON, returning an empty object on failure."""
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def insert_favorites(conn: Any, entries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Insert favorites and return the inserted records.

    Each entry should include at minimum ``name``, ``source``, and ``metadata``.
    Optional fields are stored when present.
    """
    created_at = datetime.now(timezone.utc).isoformat()
    inserted: list[dict[str, Any]] = []

    for entry in entries:
        name = str(entry.get("name", "")).strip()
        source = str(entry.get("source", "")).strip()
        if not name:
            raise ValueError("Favorite name is required.")
        if not source:
            raise ValueError("Favorite source is required.")

        metadata = entry.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        tags = _normalize_tags(entry.get("tags", []))
        tag_ids = _ensure_tags(conn, tags)

        cursor = conn.execute(
            """
            INSERT INTO favorites (
                name,
                name_class,
                package_id,
                package_name,
                syllable_key,
                render_style,
                output_format,
                seed,
                gender,
                source,
                note_md,
                metadata_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                entry.get("name_class"),
                entry.get("package_id"),
                entry.get("package_name"),
                entry.get("syllable_key"),
                entry.get("render_style"),
                entry.get("output_format"),
                entry.get("seed"),
                entry.get("gender"),
                source,
                entry.get("note_md"),
                _serialize_metadata(metadata),
                created_at,
            ),
        )
        favorite_id = int(cursor.lastrowid)

        for tag_id in tag_ids:
            conn.execute(
                "INSERT OR IGNORE INTO favorite_tags (favorite_id, tag_id) VALUES (?, ?)",
                (favorite_id, tag_id),
            )

        inserted.append(
            {
                "id": favorite_id,
                "name": name,
                "name_class": entry.get("name_class"),
                "package_id": entry.get("package_id"),
                "package_name": entry.get("package_name"),
                "syllable_key": entry.get("syllable_key"),
                "render_style": entry.get("render_style"),
                "output_format": entry.get("output_format"),
                "seed": entry.get("seed"),
                "gender": entry.get("gender"),
                "source": source,
                "note_md": entry.get("note_md"),
                "metadata": metadata,
                "created_at": created_at,
                "tags": tags,
            }
        )

    conn.commit()
    return inserted


def list_favorites(
    conn: Any,
    *,
    limit: int,
    offset: int,
    name_query: str | None = None,
    tag: str | None = None,
    name_class: str | None = None,
    package_id: int | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Return favorites and total count for the given filters."""
    filters: list[str] = []
    params: list[Any] = []

    if name_query:
        filters.append("(f.name LIKE ? OR f.note_md LIKE ?)")
        like = f"%{name_query}%"
        params.extend([like, like])

    if name_class:
        filters.append("f.name_class = ?")
        params.append(name_class)

    if package_id is not None:
        filters.append("f.package_id = ?")
        params.append(package_id)

    if tag:
        filters.append(
            "EXISTS (SELECT 1 FROM favorite_tags ft2 "
            "JOIN tags t2 ON t2.id = ft2.tag_id "
            "WHERE ft2.favorite_id = f.id AND t2.name = ?)"
        )
        params.append(tag)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    count_row = conn.execute(
        f"SELECT COUNT(*) AS total FROM favorites f {where_clause}",  # nosec B608
        params,
    ).fetchone()
    total = int(count_row["total"]) if count_row else 0

    query = (
        "SELECT f.*, GROUP_CONCAT(t.name, '|') AS tags "
        "FROM favorites f "
        "LEFT JOIN favorite_tags ft ON ft.favorite_id = f.id "
        "LEFT JOIN tags t ON t.id = ft.tag_id "
        f"{where_clause} "  # nosec B608
        "GROUP BY f.id "
        "ORDER BY f.created_at DESC, f.id DESC "
        "LIMIT ? OFFSET ?"
    )
    rows = conn.execute(query, params + [limit, offset]).fetchall()

    favorites: list[dict[str, Any]] = []
    for row in rows:
        tags_raw = row["tags"] or ""
        tags = [tag for tag in tags_raw.split("|") if tag]
        favorites.append(
            {
                "id": int(row["id"]),
                "name": row["name"],
                "name_class": row["name_class"],
                "package_id": row["package_id"],
                "package_name": row["package_name"],
                "syllable_key": row["syllable_key"],
                "render_style": row["render_style"],
                "output_format": row["output_format"],
                "seed": row["seed"],
                "gender": row["gender"],
                "source": row["source"],
                "note_md": row["note_md"],
                "metadata": _deserialize_metadata(row["metadata_json"]),
                "created_at": row["created_at"],
                "tags": tags,
            }
        )

    return favorites, total


def list_tags(conn: Any) -> list[str]:
    """Return all tags sorted alphabetically."""
    rows = conn.execute("SELECT name FROM tags ORDER BY name ASC").fetchall()
    return [row["name"] for row in rows]


def update_favorite(
    conn: Any,
    *,
    favorite_id: int,
    note_md: str | None,
    gender: str | None,
    tags: Iterable[str],
) -> dict[str, Any] | None:
    """Update a favorite's note and tags."""
    conn.execute(
        "UPDATE favorites SET note_md = ?, gender = ? WHERE id = ?",
        (note_md, gender, favorite_id),
    )

    conn.execute("DELETE FROM favorite_tags WHERE favorite_id = ?", (favorite_id,))
    tag_ids = _ensure_tags(conn, tags)
    for tag_id in tag_ids:
        conn.execute(
            "INSERT OR IGNORE INTO favorite_tags (favorite_id, tag_id) VALUES (?, ?)",
            (favorite_id, tag_id),
        )

    row = conn.execute("SELECT * FROM favorites WHERE id = ?", (favorite_id,)).fetchone()
    if row is None:
        conn.commit()
        return None

    tags = list_tags_for_favorite(conn, favorite_id)
    conn.commit()
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "name_class": row["name_class"],
        "package_id": row["package_id"],
        "package_name": row["package_name"],
        "syllable_key": row["syllable_key"],
        "render_style": row["render_style"],
        "output_format": row["output_format"],
        "seed": row["seed"],
        "gender": row["gender"],
        "source": row["source"],
        "note_md": row["note_md"],
        "metadata": _deserialize_metadata(row["metadata_json"]),
        "created_at": row["created_at"],
        "tags": tags,
    }


def list_tags_for_favorite(conn: Any, favorite_id: int) -> list[str]:
    """Return tags associated with one favorite."""
    rows = conn.execute(
        """
        SELECT t.name
        FROM favorite_tags ft
        JOIN tags t ON t.id = ft.tag_id
        WHERE ft.favorite_id = ?
        ORDER BY t.name ASC
        """,
        (favorite_id,),
    ).fetchall()
    return [row["name"] for row in rows]


def delete_favorite(conn: Any, favorite_id: int) -> bool:
    """Delete one favorite by id."""
    cursor = conn.execute("DELETE FROM favorites WHERE id = ?", (favorite_id,))
    conn.commit()
    return bool(cursor.rowcount)


def export_favorites(conn: Any) -> dict[str, Any]:
    """Serialize all favorites for export."""
    rows = conn.execute("""
        SELECT f.*, GROUP_CONCAT(t.name, '|') AS tags
        FROM favorites f
        LEFT JOIN favorite_tags ft ON ft.favorite_id = f.id
        LEFT JOIN tags t ON t.id = ft.tag_id
        GROUP BY f.id
        ORDER BY f.created_at DESC, f.id DESC
        """).fetchall()

    favorites: list[dict[str, Any]] = []
    for row in rows:
        tags_raw = row["tags"] or ""
        tags = [tag for tag in tags_raw.split("|") if tag]
        favorites.append(
            {
                "id": int(row["id"]),
                "name": row["name"],
                "name_class": row["name_class"],
                "package_id": row["package_id"],
                "package_name": row["package_name"],
                "syllable_key": row["syllable_key"],
                "render_style": row["render_style"],
                "output_format": row["output_format"],
                "seed": row["seed"],
                "gender": row["gender"],
                "source": row["source"],
                "note_md": row["note_md"],
                "metadata": _deserialize_metadata(row["metadata_json"]),
                "created_at": row["created_at"],
                "tags": tags,
            }
        )

    return {
        "schema_version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "favorites": favorites,
    }


__all__ = [
    "insert_favorites",
    "list_favorites",
    "list_tags",
    "list_tags_for_favorite",
    "update_favorite",
    "delete_favorite",
    "export_favorites",
]
