"""Unit tests for HTTP query parsing helpers."""

from __future__ import annotations

import pytest

from pipeworks_name_generation.webapp.http import (
    _coerce_int,
    _parse_optional_int,
    _parse_required_int,
)


def test_parse_required_int_missing() -> None:
    """Missing required query param should raise a clear error."""
    with pytest.raises(ValueError, match="Missing required query parameter: foo"):
        _parse_required_int({}, "foo")


def test_parse_required_int_invalid() -> None:
    """Non-numeric required param should raise a clear error."""
    with pytest.raises(ValueError, match="must be an integer"):
        _parse_required_int({"limit": ["nope"]}, "limit")


def test_parse_required_int_bounds() -> None:
    """Bounds should be enforced for required params."""
    with pytest.raises(ValueError, match=">= 1"):
        _parse_required_int({"page": ["0"]}, "page", minimum=1)
    with pytest.raises(ValueError, match="<= 10"):
        _parse_required_int({"page": ["11"]}, "page", maximum=10)


def test_parse_required_int_ok() -> None:
    """Valid required param should parse correctly."""
    assert _parse_required_int({"page": ["3"]}, "page", minimum=1, maximum=10) == 3


def test_parse_optional_int_default() -> None:
    """Optional params should return defaults when missing or blank."""
    assert _parse_optional_int({}, "limit", default=25) == 25
    assert _parse_optional_int({"limit": [""]}, "limit", default=25) == 25


def test_parse_optional_int_bounds() -> None:
    """Optional params should enforce bounds when provided."""
    with pytest.raises(ValueError, match=">= 1"):
        _parse_optional_int({"limit": ["0"]}, "limit", default=25, minimum=1)
    with pytest.raises(ValueError, match="<= 50"):
        _parse_optional_int({"limit": ["99"]}, "limit", default=25, maximum=50)


def test_coerce_int_reports_key() -> None:
    """Coerce should reference the key in error messages."""
    with pytest.raises(ValueError, match="Query parameter 'size' must be an integer"):
        _coerce_int("bad", key="size")
