"""Frontend asset loading for the webapp shell.

The webapp serves one HTML page plus small static CSS/JS assets from package
files. Content is cached in-process so repeated requests avoid disk IO.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_FRONTEND_ROOT = Path(__file__).resolve().parent
_TEMPLATES_DIR = _FRONTEND_ROOT / "templates"
_STATIC_DIR = _FRONTEND_ROOT / "static"

_STATIC_CONTENT_TYPES: dict[str, str] = {
    "app.css": "text/css; charset=utf-8",
    "app.js": "application/javascript; charset=utf-8",
}


@lru_cache(maxsize=1)
def get_index_html() -> str:
    """Return the cached index HTML shell."""
    return (_TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")


@lru_cache(maxsize=8)
def _read_static_text(filename: str) -> str:
    """Read and cache one UTF-8 static text asset by filename."""
    return (_STATIC_DIR / filename).read_text(encoding="utf-8")


def get_static_text_asset(filename: str) -> tuple[str, str]:
    """Return ``(content, content_type)`` for known static text assets.

    Raises:
        FileNotFoundError: If the filename is not one of the supported static
            assets served by the webapp.
    """
    content_type = _STATIC_CONTENT_TYPES.get(filename)
    if content_type is None:
        raise FileNotFoundError(f"Unknown static asset: {filename}")
    return _read_static_text(filename), content_type


__all__ = ["get_index_html", "get_static_text_asset"]
