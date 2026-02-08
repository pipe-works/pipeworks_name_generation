"""Route handlers for user favorites CRUD and export/import."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol


class _FavoritesHandler(Protocol):
    """Structural protocol for favorites endpoint handler behavior."""

    favorites_db_path: Path

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None: ...

    def _read_json_body(self) -> dict[str, Any]: ...

    def _ensure_favorites_schema(self, conn: Any) -> None: ...


class _OptionalIntParser(Protocol):
    """Callable signature for optional int parsing."""

    def __call__(
        self,
        query: dict[str, list[str]],
        key: str,
        *,
        default: int,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int: ...


class _UpdateFavoriteFn(Protocol):
    """Callable signature for favorite updates."""

    def __call__(
        self,
        conn: Any,
        *,
        favorite_id: int,
        note_md: str | None,
        gender: str | None,
        tags: Iterable[str],
    ) -> dict[str, Any] | None: ...


class FavoritesError(ValueError):
    """Raised when favorites input validation fails."""


def _coerce_optional_int(value: Any, *, field: str) -> int | None:
    """Convert a payload value into an optional int."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise FavoritesError(f"{field} must be an integer.") from exc


def _parse_tags(raw: Any) -> list[str]:
    """Parse tags supplied as a list or comma-delimited string."""
    if raw is None:
        return []
    if isinstance(raw, str):
        return [tag.strip() for tag in raw.split(",") if tag.strip()]
    if isinstance(raw, list):
        return [str(tag).strip() for tag in raw if str(tag).strip()]
    raise FavoritesError("tags must be a list or comma-separated string.")


def _coerce_gender(value: Any) -> str | None:
    """Normalize optional gender input."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise FavoritesError("gender must be a string.")
    cleaned = value.strip().lower()
    if cleaned in {"male", "female"}:
        return cleaned
    raise FavoritesError("gender must be 'male' or 'female'.")


def _coerce_entry(
    entry: Any,
    *,
    default_tags: list[str],
    default_note: str | None,
    default_gender: str | None,
) -> dict[str, Any]:
    """Normalize one favorites entry payload."""
    if not isinstance(entry, dict):
        raise FavoritesError("Each favorite entry must be an object.")

    name = str(entry.get("name", "")).strip()
    if not name:
        raise FavoritesError("Favorite name is required.")

    source = str(entry.get("source", "")).strip()
    if not source:
        raise FavoritesError("Favorite source is required.")

    metadata = entry.get("metadata")
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise FavoritesError("metadata must be an object.")

    tags = _parse_tags(entry.get("tags", default_tags))
    note_md = entry.get("note_md", default_note)
    note_value = str(note_md) if note_md is not None else None

    gender = _coerce_gender(entry.get("gender"))
    if gender is None:
        gender = default_gender

    return {
        "name": name,
        "name_class": entry.get("name_class"),
        "package_id": _coerce_optional_int(entry.get("package_id"), field="package_id"),
        "package_name": entry.get("package_name"),
        "syllable_key": entry.get("syllable_key"),
        "render_style": entry.get("render_style"),
        "output_format": entry.get("output_format"),
        "seed": _coerce_optional_int(entry.get("seed"), field="seed"),
        "gender": gender,
        "source": source,
        "note_md": note_value,
        "metadata": metadata,
        "tags": tags,
    }


def get_favorites(
    handler: _FavoritesHandler,
    query: dict[str, list[str]],
    *,
    parse_optional_int: _OptionalIntParser,
    connect_database: Callable[[Path], Any],
    initialize_schema: Callable[[Any], None],
    list_favorites: Callable[..., tuple[list[dict[str, Any]], int]],
) -> None:
    """Return favorites list with pagination and filters."""
    try:
        limit = parse_optional_int(query, "limit", default=20, minimum=1)
        offset = parse_optional_int(query, "offset", default=0, minimum=0)
        tag = (query.get("tag") or [""])[0].strip() or None
        name_class = (query.get("class") or [""])[0].strip() or None
        name_query = (query.get("q") or [""])[0].strip() or None
        package_id_raw = parse_optional_int(query, "package_id", default=0, minimum=1)
        package_id = package_id_raw or None

        with connect_database(handler.favorites_db_path) as conn:
            initialize_schema(conn)
            favorites, total = list_favorites(
                conn,
                limit=limit or 20,
                offset=offset or 0,
                name_query=name_query,
                tag=tag,
                name_class=name_class,
                package_id=package_id,
            )
    except FavoritesError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    except Exception as exc:  # pragma: no cover - defensive error response
        handler._send_json({"error": f"Failed to load favorites: {exc}"}, status=500)
        return

    handler._send_json(
        {
            "favorites": favorites,
            "offset": offset or 0,
            "limit": limit or 20,
            "total": total,
        }
    )


def get_favorite_tags(
    handler: _FavoritesHandler,
    *,
    connect_database: Callable[[Path], Any],
    initialize_schema: Callable[[Any], None],
    list_tags: Callable[[Any], list[str]],
) -> None:
    """Return all tags used by favorites."""
    try:
        with connect_database(handler.favorites_db_path) as conn:
            initialize_schema(conn)
            tags = list_tags(conn)
    except Exception as exc:  # pragma: no cover - defensive error response
        handler._send_json({"error": f"Failed to load tags: {exc}"}, status=500)
        return

    handler._send_json({"tags": tags})


def post_favorites(
    handler: _FavoritesHandler,
    *,
    connect_database: Callable[[Path], Any],
    initialize_schema: Callable[[Any], None],
    insert_favorites: Callable[[Any, list[dict[str, Any]]], list[dict[str, Any]]],
) -> None:
    """Insert one or more favorites into the user database."""
    try:
        payload = handler._read_json_body()
        raw_entries = payload.get("entries")
        if not isinstance(raw_entries, list) or not raw_entries:
            raise FavoritesError("entries must be a non-empty list.")

        default_tags = _parse_tags(payload.get("tags"))
        default_note = payload.get("note_md")
        default_gender = _coerce_gender(payload.get("gender"))
        entries = [
            _coerce_entry(
                entry,
                default_tags=default_tags,
                default_note=default_note,
                default_gender=default_gender,
            )
            for entry in raw_entries
        ]

        with connect_database(handler.favorites_db_path) as conn:
            initialize_schema(conn)
            inserted = insert_favorites(conn, entries)
    except FavoritesError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    except Exception as exc:  # pragma: no cover - defensive error response
        handler._send_json({"error": f"Failed to save favorites: {exc}"}, status=500)
        return

    handler._send_json({"count": len(inserted), "favorites": inserted})


def post_favorites_update(
    handler: _FavoritesHandler,
    *,
    connect_database: Callable[[Path], Any],
    initialize_schema: Callable[[Any], None],
    update_favorite: _UpdateFavoriteFn,
) -> None:
    """Update a favorite note/tags."""
    try:
        payload = handler._read_json_body()
        favorite_id = _coerce_optional_int(payload.get("favorite_id"), field="favorite_id")
        if favorite_id is None:
            raise FavoritesError("favorite_id is required.")
        tags = _parse_tags(payload.get("tags"))
        note_md = payload.get("note_md")
        gender = _coerce_gender(payload.get("gender"))
        note_value = str(note_md) if note_md is not None else None

        with connect_database(handler.favorites_db_path) as conn:
            initialize_schema(conn)
            updated = update_favorite(
                conn,
                favorite_id=favorite_id,
                note_md=note_value,
                gender=gender,
                tags=tags,
            )
    except FavoritesError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    except Exception as exc:  # pragma: no cover - defensive error response
        handler._send_json({"error": f"Failed to update favorite: {exc}"}, status=500)
        return

    if updated is None:
        handler._send_json({"error": "Favorite not found."}, status=404)
        return
    handler._send_json({"favorite": updated})


def post_favorites_delete(
    handler: _FavoritesHandler,
    *,
    connect_database: Callable[[Path], Any],
    initialize_schema: Callable[[Any], None],
    delete_favorite: Callable[[Any, int], bool],
) -> None:
    """Delete a favorite by id."""
    try:
        payload = handler._read_json_body()
        favorite_id = _coerce_optional_int(payload.get("favorite_id"), field="favorite_id")
        if favorite_id is None:
            raise FavoritesError("favorite_id is required.")

        with connect_database(handler.favorites_db_path) as conn:
            initialize_schema(conn)
            deleted = delete_favorite(conn, favorite_id)
    except FavoritesError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    except Exception as exc:  # pragma: no cover - defensive error response
        handler._send_json({"error": f"Failed to delete favorite: {exc}"}, status=500)
        return

    if not deleted:
        handler._send_json({"error": "Favorite not found."}, status=404)
        return
    handler._send_json({"deleted": True})


def get_favorites_export(
    handler: _FavoritesHandler,
    *,
    connect_database: Callable[[Path], Any],
    initialize_schema: Callable[[Any], None],
    export_favorites: Callable[[Any], dict[str, Any]],
) -> None:
    """Return JSON export payload for favorites."""
    try:
        with connect_database(handler.favorites_db_path) as conn:
            initialize_schema(conn)
            payload = export_favorites(conn)
    except Exception as exc:  # pragma: no cover - defensive error response
        handler._send_json({"error": f"Failed to export favorites: {exc}"}, status=500)
        return

    handler._send_json(payload)


def post_favorites_export(
    handler: _FavoritesHandler,
    *,
    connect_database: Callable[[Path], Any],
    initialize_schema: Callable[[Any], None],
    export_favorites: Callable[[Any], dict[str, Any]],
) -> None:
    """Write favorites export payload to a JSON file."""
    try:
        payload = handler._read_json_body()
        output_path_raw = str(payload.get("output_path", "")).strip()
        if not output_path_raw:
            raise FavoritesError("output_path is required.")

        output_path = Path(output_path_raw).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with connect_database(handler.favorites_db_path) as conn:
            initialize_schema(conn)
            export_payload = export_favorites(conn)

        output_path.write_text(json.dumps(export_payload, indent=2), encoding="utf-8")
    except FavoritesError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    except Exception as exc:  # pragma: no cover - defensive error response
        handler._send_json({"error": f"Failed to export favorites: {exc}"}, status=500)
        return

    handler._send_json({"path": str(output_path)})


def post_favorites_import(
    handler: _FavoritesHandler,
    *,
    connect_database: Callable[[Path], Any],
    initialize_schema: Callable[[Any], None],
    insert_favorites: Callable[[Any, list[dict[str, Any]]], list[dict[str, Any]]],
) -> None:
    """Import favorites from a JSON file path."""
    try:
        payload = handler._read_json_body()
        import_path_raw = str(payload.get("import_path", "")).strip()
        if not import_path_raw:
            raise FavoritesError("import_path is required.")

        import_path = Path(import_path_raw).expanduser()
        if not import_path.exists():
            raise FavoritesError("Import file not found.")

        data = json.loads(import_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise FavoritesError("Import payload must be a JSON object.")

        raw_entries = data.get("favorites")
        if not isinstance(raw_entries, list) or not raw_entries:
            raise FavoritesError("Import file contains no favorites.")

        entries = [
            _coerce_entry(
                entry,
                default_tags=_parse_tags(entry.get("tags")),
                default_note=entry.get("note_md"),
                default_gender=_coerce_gender(entry.get("gender")),
            )
            for entry in raw_entries
        ]

        with connect_database(handler.favorites_db_path) as conn:
            initialize_schema(conn)
            inserted = insert_favorites(conn, entries)
    except FavoritesError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    except json.JSONDecodeError as exc:
        handler._send_json({"error": f"Invalid JSON: {exc}"}, status=400)
        return
    except Exception as exc:  # pragma: no cover - defensive error response
        handler._send_json({"error": f"Failed to import favorites: {exc}"}, status=500)
        return

    handler._send_json({"count": len(inserted)})


__all__ = [
    "get_favorites",
    "get_favorite_tags",
    "post_favorites",
    "post_favorites_update",
    "post_favorites_delete",
    "get_favorites_export",
    "post_favorites_export",
    "post_favorites_import",
]
