"""
Name combiner execution service.

Mirrors the CLI behavior of build_tools.name_combiner.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from build_tools.name_combiner.combiner import combine_syllables

if TYPE_CHECKING:
    from build_tools.syllable_walk_tui.modules.generator import CombinerState
    from build_tools.syllable_walk_tui.modules.oscillator import PatchState


@dataclass
class CombinerResult:
    """Result from combiner execution."""

    candidates: list[dict]
    output_path: Path
    meta_output: dict
    error: str | None = None


def run_combiner(
    patch: "PatchState",
    combiner_state: "CombinerState",
) -> CombinerResult:
    """
    Run name_combiner for a patch (mirrors CLI behavior exactly).

    This function mirrors the CLI:
        python -m build_tools.name_combiner \\
            --run-dir <patch.corpus_dir> \\
            --syllables <syllables> \\
            --count <count> \\
            --seed <seed> \\
            --frequency-weight <frequency_weight>

    Output is written to: <run-dir>/candidates/{prefix}_candidates_{N}syl.json

    Args:
        patch: PatchState with corpus data
        combiner_state: CombinerState with generation parameters

    Returns:
        CombinerResult with generated candidates and metadata

    Note:
        Caller is responsible for validating patch state before calling.
    """
    # Extract values for clarity
    run_dir = patch.corpus_dir
    prefix = patch.corpus_type.lower() if patch.corpus_type else "nltk"
    comb = combiner_state

    # Validate required data
    if not run_dir:
        return CombinerResult(
            candidates=[],
            output_path=Path(),
            meta_output={},
            error="No corpus directory set",
        )

    if not patch.annotated_data:
        return CombinerResult(
            candidates=[],
            output_path=Path(),
            meta_output={},
            error="Annotated data not loaded",
        )

    try:
        # === Generate candidates (mirrors CLI main()) ===
        candidates = combine_syllables(
            annotated_data=patch.annotated_data,
            syllable_count=comb.syllables,
            count=comb.count,
            seed=comb.seed,
            frequency_weight=comb.frequency_weight,
        )

        # === Prepare output directory (mirrors CLI) ===
        candidates_dir = run_dir / "candidates"
        candidates_dir.mkdir(parents=True, exist_ok=True)

        output_filename = f"{prefix}_candidates_{comb.syllables}syl.json"
        output_path = candidates_dir / output_filename

        # === Build output structure (mirrors CLI) ===
        output = {
            "metadata": {
                "source_run": run_dir.name,
                "source_annotated": f"{prefix}_syllables_annotated.json",
                "syllable_count": comb.syllables,
                "total_candidates": len(candidates),
                "seed": comb.seed,
                "frequency_weight": comb.frequency_weight,
                "aggregation_rule": "majority",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "candidates": candidates,
        }

        # === Write output (mirrors CLI) ===
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)

        # === Build meta file (mirrors CLI exactly) ===
        unique_names = len(set(c["name"] for c in candidates))
        unique_percentage = unique_names / len(candidates) * 100 if candidates else 0

        meta_output = {
            "tool": "name_combiner",
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "arguments": {
                "run_dir": str(run_dir),
                "syllables": comb.syllables,
                "count": comb.count,
                "seed": comb.seed,
                "frequency_weight": comb.frequency_weight,
            },
            "output": {
                "candidates_file": str(output_path),
                "candidates_generated": len(candidates),
                "unique_names": unique_names,
                "unique_percentage": round(unique_percentage, 2),
            },
        }

        # === Write meta file ===
        meta_path = candidates_dir / f"{prefix}_combiner_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_output, f, indent=2)

        return CombinerResult(
            candidates=candidates,
            output_path=output_path,
            meta_output=meta_output,
            error=None,
        )

    except Exception as e:
        return CombinerResult(
            candidates=[],
            output_path=Path(),
            meta_output={},
            error=str(e),
        )
