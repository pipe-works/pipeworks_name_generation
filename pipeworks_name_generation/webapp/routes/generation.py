"""Generation-related route handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol


class _GenerationHandler(Protocol):
    """Structural protocol for generation endpoint handler behavior."""

    db_path: Path

    def _read_json_body(self) -> dict[str, Any]: ...

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None: ...


def get_package_options(
    handler: _GenerationHandler,
    *,
    connect_database: Callable[..., Any],
    initialize_schema: Callable[..., None],
    list_generation_package_options: Callable[..., list[dict[str, Any]]],
) -> None:
    """Return package options grouped by generation class."""
    try:
        with connect_database(handler.db_path) as conn:
            initialize_schema(conn)
            name_classes = list_generation_package_options(conn)
        handler._send_json({"name_classes": name_classes})
    except Exception as exc:  # nosec B110 - converted into controlled API response
        handler._send_json(
            {"error": f"Failed to list generation package options: {exc}"},
            status=500,
        )


def get_package_syllables(
    handler: _GenerationHandler,
    query: dict[str, list[str]],
    *,
    parse_required_int: Callable[..., int],
    connect_database: Callable[..., Any],
    initialize_schema: Callable[..., None],
    list_generation_syllable_options: Callable[..., list[dict[str, str]]],
) -> None:
    """Return available syllable options for one class/package selection."""
    try:
        package_id = parse_required_int(query, "package_id", minimum=1)
        class_values = query.get("class_key", [])
        class_key = class_values[0].strip() if class_values else ""
        if not class_key:
            raise ValueError("Missing required query parameter: class_key")
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return

    try:
        with connect_database(handler.db_path) as conn:
            initialize_schema(conn)
            syllable_options = list_generation_syllable_options(
                conn,
                class_key=class_key,
                package_id=package_id,
            )
        handler._send_json(
            {
                "class_key": class_key,
                "package_id": package_id,
                "syllable_options": syllable_options,
            }
        )
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
    except Exception as exc:  # nosec B110 - converted into controlled API response
        handler._send_json(
            {"error": f"Failed to list generation syllable options: {exc}"},
            status=500,
        )


def get_selection_stats(
    handler: _GenerationHandler,
    query: dict[str, list[str]],
    *,
    parse_required_int: Callable[..., int],
    connect_database: Callable[..., Any],
    initialize_schema: Callable[..., None],
    get_generation_selection_stats: Callable[..., dict[str, int]],
) -> None:
    """Return max item and max unique counts for one selection scope."""
    try:
        package_id = parse_required_int(query, "package_id", minimum=1)
        class_values = query.get("class_key", [])
        class_key = class_values[0].strip() if class_values else ""
        if not class_key:
            raise ValueError("Missing required query parameter: class_key")

        syllable_values = query.get("syllable_key", [])
        syllable_key = syllable_values[0].strip() if syllable_values else ""
        if not syllable_key:
            raise ValueError("Missing required query parameter: syllable_key")
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return

    try:
        with connect_database(handler.db_path) as conn:
            initialize_schema(conn)
            stats = get_generation_selection_stats(
                conn,
                class_key=class_key,
                package_id=package_id,
                syllable_key=syllable_key,
            )
        handler._send_json(
            {
                "class_key": class_key,
                "package_id": package_id,
                "syllable_key": syllable_key,
                **stats,
            }
        )
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
    except Exception as exc:  # nosec B110 - converted into controlled API response
        handler._send_json(
            {"error": f"Failed to compute generation selection stats: {exc}"},
            status=500,
        )


def post_generate(
    handler: _GenerationHandler,
    *,
    coerce_generation_count: Callable[[Any], int],
    coerce_optional_seed: Callable[[Any], int | None],
    coerce_bool: Callable[[Any], bool],
    coerce_output_format: Callable[[Any], str],
    connect_database: Callable[..., Any],
    initialize_schema: Callable[..., None],
    collect_generation_source_values: Callable[..., list[str]],
    sample_generation_values: Callable[..., list[str]],
) -> None:
    """Generate names from SQLite tables for one selected class scope."""
    try:
        payload = handler._read_json_body()
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return

    class_key = str(payload.get("class_key", "")).strip()
    package_id_raw = payload.get("package_id")
    syllable_key = str(payload.get("syllable_key", "")).strip()
    if not class_key:
        handler._send_json({"error": "Field 'class_key' is required."}, status=400)
        return
    if package_id_raw is None or (isinstance(package_id_raw, str) and not package_id_raw.strip()):
        handler._send_json({"error": "Field 'package_id' is required."}, status=400)
        return
    if not syllable_key:
        handler._send_json({"error": "Field 'syllable_key' is required."}, status=400)
        return

    try:
        package_id = int(package_id_raw)
    except (TypeError, ValueError):
        handler._send_json({"error": "Field 'package_id' must be an integer."}, status=400)
        return
    if package_id < 1:
        handler._send_json({"error": "Field 'package_id' must be >= 1."}, status=400)
        return

    try:
        generation_count = coerce_generation_count(payload.get("generation_count", 20))
        seed = coerce_optional_seed(payload.get("seed"))
        unique_only = coerce_bool(payload.get("unique_only", False))
        output_format = coerce_output_format(payload.get("output_format", "json"))

        with connect_database(handler.db_path) as conn:
            initialize_schema(conn)
            source_values = collect_generation_source_values(
                conn,
                class_key=class_key,
                package_id=package_id,
                syllable_key=syllable_key,
            )
        names = sample_generation_values(
            source_values,
            count=generation_count,
            seed=seed,
            unique_only=unique_only,
        )
    except ValueError as exc:
        handler._send_json({"error": str(exc)}, status=400)
        return
    except Exception as exc:  # nosec B110 - converted into controlled API response
        handler._send_json({"error": f"Generation failed: {exc}"}, status=500)
        return

    response: dict[str, Any] = {
        "message": f"Generated {len(names)} name(s) from imported package data.",
        "source": "sqlite",
        "class_key": class_key,
        "package_id": package_id,
        "syllable_key": syllable_key,
        "generation_count": generation_count,
        "unique_only": unique_only,
        "output_format": output_format,
        "names": names,
    }
    if seed is not None:
        response["seed"] = seed
    if output_format == "txt":
        response["text"] = "\n".join(names)
    handler._send_json(response)


__all__ = [
    "get_package_options",
    "get_package_syllables",
    "get_selection_stats",
    "post_generate",
]
