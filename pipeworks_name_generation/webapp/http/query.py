"""Query-parameter parsing helpers for webapp HTTP routes."""

from __future__ import annotations


def _parse_required_int(
    query: dict[str, list[str]],
    key: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Parse a required integer query parameter."""
    values = query.get(key, [])
    if not values or not values[0].strip():
        raise ValueError(f"Missing required query parameter: {key}")
    return _coerce_int(values[0], key=key, minimum=minimum, maximum=maximum)


def _parse_optional_int(
    query: dict[str, list[str]],
    key: str,
    *,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Parse an optional integer query parameter."""
    values = query.get(key, [])
    if not values or not values[0].strip():
        return default
    return _coerce_int(values[0], key=key, minimum=minimum, maximum=maximum)


def _coerce_int(
    raw: str,
    *,
    key: str,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Convert string to bounded integer with useful error messages."""
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"Query parameter '{key}' must be an integer.") from exc

    if minimum is not None and value < minimum:
        raise ValueError(f"Query parameter '{key}' must be >= {minimum}.")
    if maximum is not None and value > maximum:
        raise ValueError(f"Query parameter '{key}' must be <= {maximum}.")
    return value


__all__ = ["_parse_required_int", "_parse_optional_int", "_coerce_int"]
