"""
Name selector execution service.

Mirrors the CLI behavior of build_tools.name_selector.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from build_tools.name_selector.name_class import get_default_policy_path, load_name_classes
from build_tools.name_selector.selector import compute_selection_statistics, select_names

if TYPE_CHECKING:
    from build_tools.syllable_walk_tui.modules.generator import CombinerState, SelectorState
    from build_tools.syllable_walk_tui.modules.oscillator import PatchState


@dataclass
class SelectorResult:
    """Result from selector execution."""

    selected: list[dict]
    selected_names: list[str]
    output_path: Path
    meta_output: dict
    error: str | None = None


def run_selector(
    patch: "PatchState",
    combiner_state: "CombinerState",
    selector_state: "SelectorState",
) -> SelectorResult:
    """
    Run name_selector for a patch (mirrors CLI behavior exactly).

    This function mirrors the CLI:
        python -m build_tools.name_selector \\
            --run-dir <patch.corpus_dir> \\
            --candidates <from combiner output> \\
            --name-class <name_class> \\
            --count <count> \\
            --mode <mode>

    Output is written to: <run-dir>/selections/{prefix}_{name_class}_{N}syl.json

    Args:
        patch: PatchState with corpus data
        combiner_state: CombinerState for candidates path and seed
        selector_state: SelectorState with selection parameters

    Returns:
        SelectorResult with selected names and metadata

    Note:
        Caller is responsible for validating patch state and combiner output
        before calling.
    """
    # Extract values for clarity
    run_dir = patch.corpus_dir
    prefix = patch.corpus_type.lower() if patch.corpus_type else "nltk"
    selector = selector_state
    combiner = combiner_state

    # Validate required data
    if not run_dir:
        return SelectorResult(
            selected=[],
            selected_names=[],
            output_path=Path(),
            meta_output={},
            error="No corpus directory set",
        )

    if not combiner.last_output_path:
        return SelectorResult(
            selected=[],
            selected_names=[],
            output_path=Path(),
            meta_output={},
            error="No candidates generated. Run Generate Candidates first.",
        )

    candidates_path = Path(combiner.last_output_path)
    if not candidates_path.exists():
        return SelectorResult(
            selected=[],
            selected_names=[],
            output_path=Path(),
            meta_output={},
            error=f"Candidates file not found: {candidates_path.name}",
        )

    try:
        # Load candidates
        with open(candidates_path, encoding="utf-8") as f:
            candidates_data = json.load(f)
        candidates = candidates_data.get("candidates", [])

        if not candidates:
            return SelectorResult(
                selected=[],
                selected_names=[],
                output_path=Path(),
                meta_output={},
                error="No candidates in file",
            )

        # Load policy
        policy_path = get_default_policy_path()
        policies = load_name_classes(policy_path)

        if selector.name_class not in policies:
            return SelectorResult(
                selected=[],
                selected_names=[],
                output_path=Path(),
                meta_output={},
                error=f"Unknown name class: {selector.name_class}",
            )

        policy = policies[selector.name_class]

        # Compute statistics
        stats = compute_selection_statistics(
            candidates, policy, mode=selector.mode  # type: ignore[arg-type]
        )

        # Select names
        selected = select_names(
            candidates,
            policy,
            count=selector.count,
            mode=selector.mode,  # type: ignore[arg-type]
            order=selector.order,  # type: ignore[arg-type]
            seed=combiner.seed,
        )

        # Prepare output directory
        selections_dir = run_dir / "selections"
        selections_dir.mkdir(parents=True, exist_ok=True)

        # Extract syllable count from combiner state
        syllables = combiner.syllables

        output_filename = f"{prefix}_{selector.name_class}_{syllables}syl.json"
        output_path = selections_dir / output_filename

        # Build output structure
        output = {
            "metadata": {
                "source_candidates": candidates_path.name,
                "name_class": selector.name_class,
                "policy_description": policy.description,
                "policy_file": str(policy_path),
                "mode": selector.mode,
                "order": selector.order,
                "seed": combiner.seed,
                "total_evaluated": stats["total_evaluated"],
                "admitted": stats["admitted"],
                "rejected": stats["rejected"],
                "rejection_reasons": stats["rejection_reasons"],
                "score_distribution": stats["score_distribution"],
                "output_count": len(selected),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "selections": selected,
        }

        # Write output
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)

        # Build meta file
        meta_output = {
            "tool": "name_selector",
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "arguments": {
                "run_dir": str(run_dir),
                "candidates": str(candidates_path),
                "name_class": selector.name_class,
                "policy_file": str(policy_path),
                "count": selector.count,
                "mode": selector.mode,
                "order": selector.order,
                "seed": combiner.seed,
            },
            "input": {
                "candidates_file": str(candidates_path),
                "candidates_loaded": len(candidates),
                "policy_file": str(policy_path),
                "policy_name": selector.name_class,
                "policy_description": policy.description,
            },
            "output": {
                "selections_file": str(output_path),
                "selections_count": len(selected),
            },
            "statistics": {
                "total_evaluated": stats["total_evaluated"],
                "admitted": stats["admitted"],
                "admitted_percentage": (
                    round(stats["admitted"] / stats["total_evaluated"] * 100, 2)
                    if stats["total_evaluated"] > 0
                    else 0
                ),
                "rejected": stats["rejected"],
                "rejection_reasons": stats["rejection_reasons"],
                "score_distribution": stats["score_distribution"],
                "mode": selector.mode,
                "source_prefix": prefix,
                "syllable_count": syllables,
            },
        }

        # Write meta file
        meta_filename = f"{prefix}_selector_meta.json"
        meta_path = selections_dir / meta_filename
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_output, f, indent=2)

        # Extract names for convenience
        selected_names = [s["name"] for s in selected]

        return SelectorResult(
            selected=selected,
            selected_names=selected_names,
            output_path=output_path,
            meta_output=meta_output,
            error=None,
        )

    except Exception as e:
        return SelectorResult(
            selected=[],
            selected_names=[],
            output_path=Path(),
            meta_output={},
            error=str(e),
        )
