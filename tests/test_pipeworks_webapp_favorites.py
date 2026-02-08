"""Tests for favorites persistence and route handlers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipeworks_name_generation.webapp.db import connect_database
from pipeworks_name_generation.webapp.favorites import (
    delete_favorite,
    export_favorites,
    insert_favorites,
    list_favorites,
    list_tags,
    update_favorite,
)
from pipeworks_name_generation.webapp.favorites.schema import initialize_favorites_schema
from pipeworks_name_generation.webapp.http import _parse_optional_int
from pipeworks_name_generation.webapp.routes import favorites as favorites_routes


class _FavoritesHandlerStub:
    """Minimal handler stub for testing favorites routes."""

    def __init__(self, favorites_db_path: Path, body: dict[str, Any] | None = None) -> None:
        self.favorites_db_path = favorites_db_path
        self._body = body or {}
        self.payload: dict[str, Any] | None = None
        self.status: int | None = None

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def _read_json_body(self) -> dict[str, Any]:
        return self._body

    def _ensure_favorites_schema(self, conn: Any) -> None:
        initialize_favorites_schema(conn)


def _sample_entry(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "name_class": "first_name",
        "package_id": 12,
        "package_name": "Goblin Flower",
        "syllable_key": "2syl",
        "render_style": "title",
        "output_format": "json",
        "seed": 101,
        "gender": "female",
        "source": "preview",
        "metadata": {"source": "preview", "selection": {"package_id": 12}},
    }


def test_favorites_repositories_round_trip(tmp_path: Path) -> None:
    """Favorites repositories should insert, update, export, and delete."""
    db_path = tmp_path / "favorites.sqlite3"
    with connect_database(db_path) as conn:
        initialize_favorites_schema(conn)
        inserted = insert_favorites(conn, [_sample_entry("Aldra")])
        assert inserted[0]["name"] == "Aldra"
        favorites, total = list_favorites(conn, limit=10, offset=0)
        assert total == 1
        assert favorites[0]["name"] == "Aldra"

        updated = update_favorite(
            conn,
            favorite_id=inserted[0]["id"],
            note_md="note",
            gender="female",
            tags=["goblin"],
        )
        assert updated is not None
        assert updated["note_md"] == "note"
        assert updated["tags"] == ["goblin"]
        assert updated["gender"] == "female"
        assert list_tags(conn) == ["goblin"]

        export_payload = export_favorites(conn)
        assert export_payload["schema_version"] == 1
        assert export_payload["favorites"][0]["name"] == "Aldra"

        deleted = delete_favorite(conn, inserted[0]["id"])
        assert deleted is True


def test_favorites_routes_round_trip(tmp_path: Path) -> None:
    """Favorites routes should support CRUD and import/export."""
    db_path = tmp_path / "favorites.sqlite3"

    handler = _FavoritesHandlerStub(
        db_path,
        body={
            "entries": [_sample_entry("Bran")],
            "tags": ["test"],
            "note_md": "note",
            "gender": "male",
        },
    )
    favorites_routes.post_favorites(
        handler,
        connect_database=connect_database,
        initialize_schema=initialize_favorites_schema,
        insert_favorites=insert_favorites,
    )
    assert handler.status == 200
    assert handler.payload and handler.payload["count"] == 1
    favorite_id = handler.payload["favorites"][0]["id"]

    list_handler = _FavoritesHandlerStub(db_path)
    favorites_routes.get_favorites(
        list_handler,
        {},
        parse_optional_int=_parse_optional_int,
        connect_database=connect_database,
        initialize_schema=initialize_favorites_schema,
        list_favorites=list_favorites,
    )
    assert list_handler.payload
    assert list_handler.payload["total"] == 1

    update_handler = _FavoritesHandlerStub(
        db_path,
        body={
            "favorite_id": favorite_id,
            "tags": "alpha, beta",
            "note_md": "rev",
            "gender": "female",
        },
    )
    favorites_routes.post_favorites_update(
        update_handler,
        connect_database=connect_database,
        initialize_schema=initialize_favorites_schema,
        update_favorite=update_favorite,
    )
    assert update_handler.payload
    assert update_handler.payload["favorite"]["note_md"] == "rev"
    assert update_handler.payload["favorite"]["gender"] == "female"

    tags_handler = _FavoritesHandlerStub(db_path)
    favorites_routes.get_favorite_tags(
        tags_handler,
        connect_database=connect_database,
        initialize_schema=initialize_favorites_schema,
        list_tags=list_tags,
    )
    assert tags_handler.payload
    assert "alpha" in tags_handler.payload["tags"]

    export_handler = _FavoritesHandlerStub(db_path)
    favorites_routes.get_favorites_export(
        export_handler,
        connect_database=connect_database,
        initialize_schema=initialize_favorites_schema,
        export_favorites=export_favorites,
    )
    export_payload = export_handler.payload or {}
    assert export_payload.get("favorites")

    export_path = tmp_path / "favorites_export.json"
    write_handler = _FavoritesHandlerStub(db_path, body={"output_path": str(export_path)})
    favorites_routes.post_favorites_export(
        write_handler,
        connect_database=connect_database,
        initialize_schema=initialize_favorites_schema,
        export_favorites=export_favorites,
    )
    assert export_path.exists()

    imported_payload = json.loads(export_path.read_text(encoding="utf-8"))
    assert imported_payload["favorites"]

    import_handler = _FavoritesHandlerStub(db_path, body={"import_path": str(export_path)})
    favorites_routes.post_favorites_import(
        import_handler,
        connect_database=connect_database,
        initialize_schema=initialize_favorites_schema,
        insert_favorites=insert_favorites,
    )
    assert import_handler.payload
    assert import_handler.payload["count"] >= 1

    delete_handler = _FavoritesHandlerStub(db_path, body={"favorite_id": favorite_id})
    favorites_routes.post_favorites_delete(
        delete_handler,
        connect_database=connect_database,
        initialize_schema=initialize_favorites_schema,
        delete_favorite=delete_favorite,
    )
    assert delete_handler.payload == {"deleted": True}

    missing_handler = _FavoritesHandlerStub(db_path, body={"favorite_id": 9999})
    favorites_routes.post_favorites_delete(
        missing_handler,
        connect_database=connect_database,
        initialize_schema=initialize_favorites_schema,
        delete_favorite=delete_favorite,
    )
    assert missing_handler.status == 404


def test_favorites_routes_validate_payloads(tmp_path: Path) -> None:
    """Favorites routes should reject invalid payloads."""
    db_path = tmp_path / "favorites.sqlite3"

    handler = _FavoritesHandlerStub(db_path, body={"entries": []})
    favorites_routes.post_favorites(
        handler,
        connect_database=connect_database,
        initialize_schema=initialize_favorites_schema,
        insert_favorites=insert_favorites,
    )
    assert handler.status == 400

    update_handler = _FavoritesHandlerStub(db_path, body={"tags": "x"})
    favorites_routes.post_favorites_update(
        update_handler,
        connect_database=connect_database,
        initialize_schema=initialize_favorites_schema,
        update_favorite=update_favorite,
    )
    assert update_handler.status == 400

    import_handler = _FavoritesHandlerStub(db_path, body={"import_path": ""})
    favorites_routes.post_favorites_import(
        import_handler,
        connect_database=connect_database,
        initialize_schema=initialize_favorites_schema,
        insert_favorites=insert_favorites,
    )
    assert import_handler.status == 400

    gender_handler = _FavoritesHandlerStub(
        db_path, body={"entries": [_sample_entry("Ada")], "gender": "unknown"}
    )
    favorites_routes.post_favorites(
        gender_handler,
        connect_database=connect_database,
        initialize_schema=initialize_favorites_schema,
        insert_favorites=insert_favorites,
    )
    assert gender_handler.status == 400
