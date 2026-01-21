"""
Name Selector - Policy-Based Name Filtering and Ranking

Evaluates name candidates against name class policies to produce ranked,
admissible name lists. This is a **build-time tool only** - not used during
runtime name generation.

This module is the second stage of the Selection Policy Layer. It performs
policy evaluation on candidates produced by the name_combiner module.

Architectural Boundary:
    The selector is the governance layer. All admissibility decisions,
    scoring, and rejection logic live here. The combiner upstream is
    purely structural.

Features:
- Load name class policies from YAML configuration
- Evaluate candidates against 12-feature policies
- Hard mode (reject on discouraged) or soft mode (negative score)
- Ranked output by score
- Detailed evaluation metadata for debugging

Policy Logic:
- Preferred feature present: +1 score
- Tolerated feature present: 0 score
- Discouraged feature present: Reject (hard) or -10 (soft)

Usage:
    >>> from build_tools.name_selector import select_names, load_name_classes
    >>> policies = load_name_classes("data/name_classes.yml")
    >>> selected = select_names(candidates, policies["first_name"], count=100)
    >>> for name in selected[:5]:
    ...     print(f"{name['name']}: score={name['score']}")

CLI::

    python -m build_tools.name_selector \\
        --run-dir _working/output/20260110_115453_pyphen/ \\
        --candidates candidates/pyphen_candidates_2syl.json \\
        --name-class first_name \\
        --count 100
"""

from build_tools.name_selector.name_class import NameClassPolicy, load_name_classes
from build_tools.name_selector.policy import evaluate_candidate
from build_tools.name_selector.selector import select_names

__all__ = [
    "NameClassPolicy",
    "evaluate_candidate",
    "load_name_classes",
    "select_names",
]
