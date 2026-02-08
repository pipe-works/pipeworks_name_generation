"""Schema helpers for the user-specific favorites database."""

from __future__ import annotations

import sqlite3


def initialize_favorites_schema(conn: sqlite3.Connection) -> None:
    """Create tables used by the favorites user database.

    Args:
        conn: Open SQLite connection.
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            name_class TEXT,
            package_id INTEGER,
            package_name TEXT,
            syllable_key TEXT,
            render_style TEXT,
            output_format TEXT,
            seed INTEGER,
            gender TEXT,
            source TEXT NOT NULL,
            note_md TEXT,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_favorites_name
        ON favorites(name);

        CREATE INDEX IF NOT EXISTS idx_favorites_name_class
        ON favorites(name_class);

        CREATE INDEX IF NOT EXISTS idx_favorites_package
        ON favorites(package_id);

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE
        );

        CREATE TABLE IF NOT EXISTS favorite_tags (
            favorite_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            FOREIGN KEY(favorite_id) REFERENCES favorites(id) ON DELETE CASCADE,
            FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE,
            UNIQUE(favorite_id, tag_id)
        );

        CREATE INDEX IF NOT EXISTS idx_favorite_tags_favorite_id
        ON favorite_tags(favorite_id);

        CREATE INDEX IF NOT EXISTS idx_favorite_tags_tag_id
        ON favorite_tags(tag_id);
        """)
    # Keep schema migrations lightweight by adding missing columns when upgrading
    # older favorites databases in place.
    columns = {row[1] for row in conn.execute("PRAGMA table_info(favorites)").fetchall()}
    if "gender" not in columns:
        conn.execute("ALTER TABLE favorites ADD COLUMN gender TEXT")
    conn.commit()


__all__ = ["initialize_favorites_schema"]
