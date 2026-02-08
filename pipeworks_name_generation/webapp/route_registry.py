"""Route registry definitions for webapp HTTP dispatch.

The handler resolves request paths through these static mappings so route
registration is centralized and easy to scan or extend.
"""

from __future__ import annotations

# Map HTTP GET path -> endpoint adapter function name.
GET_ROUTE_METHODS: dict[str, str] = {
    "/": "get_root",
    "/static/app.css": "get_static_app_css",
    "/static/app.js": "get_static_app_js",
    "/static/api_builder_preview.js": "get_static_api_builder_preview_js",
    "/api/health": "get_health",
    "/api/generation/package-options": "get_generation_package_options",
    "/api/generation/package-syllables": "get_generation_package_syllables",
    "/api/generation/selection-stats": "get_generation_selection_stats",
    "/api/database/packages": "get_database_packages",
    "/api/database/package-tables": "get_database_package_tables",
    "/api/database/table-rows": "get_database_table_rows",
    "/api/help": "get_help",
    "/favicon.ico": "get_favicon",
}

# API-only route map (no UI or static asset endpoints).
API_GET_ROUTE_METHODS: dict[str, str] = {
    route: handler for route, handler in GET_ROUTE_METHODS.items() if route.startswith("/api/")
}

# Map HTTP POST path -> endpoint adapter function name.
POST_ROUTE_METHODS: dict[str, str] = {
    "/api/import": "post_import",
    "/api/generate": "post_generate",
}


def select_route_maps(serve_ui: bool) -> tuple[dict[str, str], dict[str, str]]:
    """Return the GET/POST route maps for the chosen server mode."""
    if serve_ui:
        return GET_ROUTE_METHODS, POST_ROUTE_METHODS
    return API_GET_ROUTE_METHODS, POST_ROUTE_METHODS


__all__ = [
    "GET_ROUTE_METHODS",
    "API_GET_ROUTE_METHODS",
    "POST_ROUTE_METHODS",
    "select_route_maps",
]
