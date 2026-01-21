#!/usr/bin/env python3
"""
Pre-commit hook to check RST formatting in Python docstrings and argparse epilogs.

This hook checks for common RST formatting issues that cause documentation
to render incorrectly in Sphinx:

1. `Examples:` without `::` in argparse epilogs (should be `Examples::`)
2. `CLI:` without `::` in module docstrings (should be `CLI::`)
3. Other common label patterns that need `::` for code blocks

Usage:
    python scripts/check_rst_docstrings.py [files...]

Exit codes:
    0 - All files pass
    1 - Formatting issues found
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

# Patterns that should have `::` when followed by indented code blocks
# These are common labels used before code examples in docstrings
CODE_BLOCK_LABELS = [
    r"Examples?",
    r"CLI",
    r"Usage",
    r"Command[- ]?line(?: usage)?",
    r"Quick [Ss]tart",
]

# Compile the pattern to match labels that should have ::
# Matches: "Examples:" at end of line (code block header) but not:
# - "Examples::" (already correct)
# - "Examples: something" (inline example, not a code block)
MISSING_DOUBLE_COLON_PATTERN = re.compile(
    rf"^\s*({'|'.join(CODE_BLOCK_LABELS)}):(?!:)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


class Issue:
    """Represents a formatting issue found in a file."""

    def __init__(self, file: Path, line: int, label: str, context: str):
        self.file = file
        self.line = line
        self.label = label
        self.context = context

    def __str__(self) -> str:
        return (
            f"{self.file}:{self.line}: "
            f"'{self.label}:' should be '{self.label}::' for RST code block\n"
            f"    {self.context.strip()}"
        )


def extract_docstrings_and_epilogs(source: str) -> list[tuple[str, int, str]]:
    """
    Extract docstrings and argparse epilog strings from Python source.

    Returns:
        List of (content, line_number, type) tuples where type is 'docstring' or 'epilog'
    """
    results = []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return results

    # Extract module docstring
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        results.append((tree.body[0].value.value, tree.body[0].lineno, "docstring"))

    # Walk the AST to find:
    # 1. Function/class docstrings
    # 2. argparse epilog= keyword arguments
    for node in ast.walk(tree):
        # Check for function/class docstrings
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                results.append((node.body[0].value.value, node.body[0].lineno, "docstring"))

        # Check for epilog= in function calls (ArgumentParser)
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "epilog" and isinstance(keyword.value, ast.Constant):
                    if isinstance(keyword.value.value, str):
                        results.append((keyword.value.value, keyword.value.lineno, "epilog"))

    return results


def check_content(content: str, base_line: int, content_type: str) -> list[tuple[int, str, str]]:
    """
    Check content for missing :: after code block labels.

    Returns:
        List of (line_offset, label, context) tuples for each issue found
    """
    issues = []
    lines = content.split("\n")

    for i, line in enumerate(lines):
        match = MISSING_DOUBLE_COLON_PATTERN.search(line)
        if match:
            label = match.group(1)

            # Check if the next non-empty line indicates this is valid RST:
            # 1. Doctest (starts with >>>) - Sphinx handles these automatically
            # 2. RST directive (starts with ..) - explicit code-block or similar
            # 3. Line ends with :: - there's already a nested code block defined
            # 4. Bullet list (starts with - or *) - not a code block
            # 5. Label/definition (ends with :) - section heading, not code block
            skip_this = False
            for next_line in lines[i + 1 :]:
                stripped = next_line.strip()
                if stripped:  # Found non-empty line
                    if (
                        stripped.startswith(">>>")
                        or stripped.startswith("..")
                        or stripped.endswith("::")
                        or stripped.startswith("- ")
                        or stripped.startswith("* ")
                        or stripped.endswith(":")
                    ):
                        skip_this = True
                    break

            if not skip_this:
                # Get context (the matching line)
                context = line
                issues.append((i, label, context))

    return issues


def check_file(filepath: Path) -> list[Issue]:
    """Check a single Python file for RST formatting issues."""
    issues = []

    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
        return issues

    # Extract all docstrings and epilogs
    contents = extract_docstrings_and_epilogs(source)

    for content, line_no, content_type in contents:
        found_issues = check_content(content, line_no, content_type)
        for line_offset, label, context in found_issues:
            issues.append(
                Issue(
                    file=filepath,
                    line=line_no + line_offset,
                    label=label,
                    context=context,
                )
            )

    return issues


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print("Usage: check_rst_docstrings.py <file1.py> [file2.py ...]", file=sys.stderr)
        return 0

    all_issues: list[Issue] = []

    for filepath_str in argv:
        filepath = Path(filepath_str)
        if filepath.suffix == ".py" and filepath.exists():
            issues = check_file(filepath)
            all_issues.extend(issues)

    if all_issues:
        print("RST formatting issues found:\n", file=sys.stderr)
        for issue in all_issues:
            print(f"  {issue}\n", file=sys.stderr)
        print(
            f"Found {len(all_issues)} issue(s). "
            "Add '::' after labels to create proper RST code blocks.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
