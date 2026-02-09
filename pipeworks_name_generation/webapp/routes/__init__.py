"""Route handler modules for the webapp HTTP server."""

from . import database, database_admin, favorites, generation, help, imports, static

__all__ = [
    "static",
    "generation",
    "database",
    "database_admin",
    "imports",
    "favorites",
    "help",
]
