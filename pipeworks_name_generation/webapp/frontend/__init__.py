"""Frontend asset access helpers used by the webapp handler."""

from .assets import get_index_html, get_static_binary_asset, get_static_text_asset

__all__ = ["get_index_html", "get_static_text_asset", "get_static_binary_asset"]
