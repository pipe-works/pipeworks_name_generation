"""Route handler modules for the webapp HTTP server."""

from . import database, favorites, generation, help, imports, static

__all__ = ["static", "generation", "database", "imports", "favorites", "help"]
