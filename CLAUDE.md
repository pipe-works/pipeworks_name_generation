# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`pipeworks_name_generation` is a phonetic name generator that produces pronounceable, neutral
names without imposing semantic meaning. The system is designed to be context-free,
deterministic, and lightweight.

**Critical Design Principle**: Determinism is paramount. The same seed must always produce
the same name. This is essential for games where entity IDs need to map to consistent names
across sessions.

## Quick Command Reference

### Setup and Testing

```bash
# Setup
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt && pip install -e .

# Run tests
pytest

# Code quality
ruff check . && black pipeworks_name_generation/ tests/ && mypy pipeworks_name_generation/
pre-commit run --all-files
```

### Build Tools

```bash
# Extract syllables
python -m build_tools.syllable_extractor --file input.txt --auto

# Normalize syllables
python -m build_tools.syllable_normaliser --source data/corpus/ --output _working/normalized/

# Annotate with features
python -m build_tools.syllable_feature_annotator
```

For detailed command options, see [Development Guide](claude/development.md).

## Documentation Structure

Detailed documentation is organized in the `claude/` directory:

### Core Documentation

- **[Architecture and Design](claude/architecture.md)** - System architecture, design philosophy,
  phases, testing requirements
- **[Development Guide](claude/development.md)** - Setup, testing, code quality, build tool
  commands
- **[CI/CD Pipeline](claude/ci_cd.md)** - GitHub Actions workflows, pre-commit hooks

### Build Tool Documentation

- **[Syllable Extractor](claude/build_tools/syllable_extractor.md)** - Dictionary-based syllable
  extraction (pyphen)
- **[Syllable Normaliser](claude/build_tools/syllable_normaliser.md)** - 3-step normalization
  pipeline
- **[Feature Annotator](claude/build_tools/feature_annotator.md)** - Phonetic feature detection
- **[Analysis Tools](claude/build_tools/analysis_tools.md)** - Post-annotation analysis and
  visualization

## Critical Implementation Rules

### Deterministic RNG

```python
# ALWAYS use Random(seed), NOT random.seed()
rng = random.Random(seed)  # Creates isolated RNG instance
# This avoids global state contamination
```

### CLI Argument Documentation

**CRITICAL**: All CLI tools must document command-line arguments in code, not in README.

When creating or modifying any CLI tool (anything that uses `argparse`):

1. **Use `create_argument_parser()` function pattern** (required for sphinx-argparse)
2. **Write detailed help text for EVERY argument**
3. **Include default values in help text**
4. **Add examples in epilog section**

```python
def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and return the argument parser for this tool.

    Returns:
        Configured ArgumentParser ready to parse command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Clear description of what this tool does",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Example 1
  python -m module.name --option value

  # Example 2
  python -m module.name --other-option value
        """,
    )

    parser.add_argument(
        "--option",
        type=str,
        default="default_value",
        help="Detailed help text explaining what this option does. Default: default_value",
    )

    return parser

def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = create_argument_parser()
    return parser.parse_args(args)
```

**Why this matters:**

- CLI options are automatically documented in Sphinx via sphinx-argparse
- Single source of truth prevents documentation drift
- Users can always find accurate `--option` information in generated docs
- No more forgetting what options exist or keeping README in sync

See [Development Guide - CLI Documentation Standards](claude/development.md#cli-documentation-standards) for details.

### CLI Documentation Synchronization

When modifying CLI tools (`build_tools/**/cli.py` or `__main__.py`):

1. **Update argparse help text first** - This is the source of truth
2. **Check corresponding RST file** in `docs/source/build_tools/*.rst`
3. **Pre-commit hook reminder** - A warning will display if CLI files change

The pre-commit hook checks:

- Any `cli.py` or `__main__.py` in `build_tools/` subdirectories
- Reminds to sync RST documentation
- **Does not fail** - just a friendly reminder

Example workflow:

```python
# 1. Update CLI (e.g., build_tools/syllable_extractor/cli.py)
parser.add_argument("--new-option", help="New feature description")

# 2. Git commit triggers hook:
# ⚠️  CLI files changed: build_tools/syllable_extractor/cli.py
#    → Remember to update docs/source/build_tools/syllable_extractor.rst

# 3. Update RST if needed (or not, if just refactoring)
```

**Philosophy**: Not all CLI changes require RST updates (internal refactors, bug fixes),
so this is a **reminder, not enforcement**.

### Testing Requirements

All changes must maintain determinism:

```python
gen = NameGenerator(pattern="simple")
assert gen.generate(seed=42) == gen.generate(seed=42)
```

## Current State (Phase 1)

The project is in **Phase 1** - a minimal working proof of concept:

- Only "simple" pattern exists
- Syllables hardcoded in `generator.py`
- No YAML loading, phonotactic constraints, or CLI yet
- Zero runtime dependencies (by design)

These are **intentional scope limitations**, not bugs.

## Design Philosophy

**What this system IS:**

- Phonetically-plausible name generator
- Deterministic and seedable
- Context-free and domain-agnostic

**What this system IS NOT:**

- A lore or narrative system
- Genre-specific (fantasy/sci-fi/etc.)
- Semantically aware
- Culturally affiliated

The generator produces **structural** names. Meaning and interpretation are applied by consuming applications.

## Project Configuration

- **Python**: 3.12+
- **License**: GPL-3.0-or-later
- **Line Length**: 100 characters (black/ruff)
- **Type Checking**: mypy enabled (lenient in Phase 1)
- **Testing**: pytest with coverage
- **CI/CD**: GitHub Actions + pre-commit hooks

For detailed configuration, see [Development Guide](claude/development.md) and [CI/CD Pipeline](claude/ci_cd.md).

## Directory Structure

```text
pipeworks_name_generation/    # Core library code
tests/                         # pytest test suite
examples/                      # Usage examples
data/                          # Pattern files (future: YAML configs)
build_tools/                   # Build-time corpus analysis tools
claude/                        # Claude Code documentation (this structure)
docs/                          # Sphinx documentation
_working/                      # Local scratch workspace (not committed)
```

## Adding New Features

When extending beyond Phase 1:

1. **Maintain determinism at all costs**
2. Keep runtime dependencies minimal
3. Reserve heavy processing (NLP, corpus analysis) for build-time tools
4. Pattern data goes in `data/` directory
5. Build tools go in `build_tools/` directory

See [Architecture and Design](claude/architecture.md) for detailed guidance.
