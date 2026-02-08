"""Unit tests for file-backed frontend asset helpers."""

from __future__ import annotations

import pytest

from pipeworks_name_generation.webapp.frontend.assets import (
    get_index_html,
    get_static_text_asset,
)


def test_index_html_contains_core_shell_elements() -> None:
    """Index HTML loader should return the app shell markup."""
    html = get_index_html()
    assert "Pipeworks Name Generator" in html
    assert "/static/app.css" in html
    assert "/static/app.js" in html


def test_static_assets_load_known_files_and_reject_unknown() -> None:
    """Static asset loader should expose known files and fail for unknown names."""
    css_content, css_type = get_static_text_asset("app.css")
    assert "body" in css_content
    assert css_type == "text/css; charset=utf-8"

    js_content, js_type = get_static_text_asset("app.js")
    assert "function" in js_content
    assert js_type == "application/javascript; charset=utf-8"

    with pytest.raises(FileNotFoundError):
        get_static_text_asset("missing.css")
