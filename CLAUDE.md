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
# Extract syllables (choose one extractor)

# Option 1: pyphen (40+ languages, typographic hyphenation)
# Language auto-detected if langdetect installed, otherwise defaults to en_US
python -m build_tools.pyphen_syllable_extractor --file input.txt

# Option 2: NLTK (English only, phonetic splits with onset/coda)
python -m build_tools.nltk_syllable_extractor --file input.txt

# Normalize syllables (both use in-place processing)

# For pyphen extractor output:
python -m build_tools.pyphen_syllable_normaliser --run-dir _working/output/20260110_143022_pyphen/

# For NLTK extractor output (in-place processing with fragment cleaning):
python -m build_tools.nltk_syllable_normaliser --run-dir _working/output/20260110_095213_nltk/

# Annotate with features (source-agnostic, works with both normalisers)
python -m build_tools.syllable_feature_annotator \
  --syllables _working/output/20260110_143022_pyphen/pyphen_syllables_unique.txt \
  --frequencies _working/output/20260110_143022_pyphen/pyphen_syllables_frequencies.json
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
  extraction (pyphen, 40+ languages, typographic hyphenation)
- **[NLTK Syllable Extractor]** - Phonetically-guided syllable extraction (CMUDict + onset/coda,
  English only, phonetic splits)
- **[Syllable Normaliser](claude/build_tools/syllable_normaliser.md)** - 3-step normalization
  pipeline for pyphen extractor output (outputs: pyphen_* files)
- **[NLTK Syllable Normaliser]** - NLTK-specific normalization with fragment cleaning (in-place
  processing, outputs: nltk_* files)
- **[Feature Annotator](claude/build_tools/feature_annotator.md)** - Phonetic feature detection
- **[Corpus Database](claude/build_tools/corpus_db.md)** - Build provenance ledger for tracking
  extraction runs
- **[Analysis Tools](claude/build_tools/analysis_tools.md)** - Post-annotation analysis and
  visualization

## Build Pipeline Patterns

### Extraction + Normalization Workflows

The project supports two parallel syllable extraction pipelines with matching normalisers:

#### **Pyphen Pipeline (Multi-Language, Typographic)**

```bash
# 1. Extract with pyphen (typographic hyphenation)
# Language auto-detected if langdetect installed, otherwise defaults to en_US
python -m build_tools.pyphen_syllable_extractor \
  --source data/corpus/ \
  --output _working/output/

# Creates: _working/output/YYYYMMDD_HHMMSS_pyphen/syllables/*.txt

# 2. Normalize with pyphen normaliser (in-place)
python -m build_tools.pyphen_syllable_normaliser \
  --run-dir _working/output/YYYYMMDD_HHMMSS_pyphen/

# Creates (in-place): YYYYMMDD_HHMMSS_pyphen/pyphen_syllables_*.txt, pyphen_syllables_*.json
```

#### **NLTK Pipeline (English-Only, Phonetic)**

```bash
# 1. Extract with NLTK (phonetic splitting with onset/coda)
python -m build_tools.nltk_syllable_extractor \
  --source data/corpus/ \
  --pattern "*.txt" \
  --output _working/output/

# Creates: _working/output/YYYYMMDD_HHMMSS_nltk/syllables/*.txt

# 2. Normalize with NLTK normaliser (in-place with fragment cleaning)
python -m build_tools.nltk_syllable_normaliser \
  --run-dir _working/output/YYYYMMDD_HHMMSS_nltk/

# Creates (in-place): YYYYMMDD_HHMMSS_nltk/nltk_syllables_*.txt, nltk_syllables_*.json
```

### File Naming Conventions

All pipeline outputs use **prefixed naming** for clear provenance:

#### **Extractor Output Directories**

- Pyphen: `YYYYMMDD_HHMMSS_pyphen/` (typographic hyphenation)
- NLTK: `YYYYMMDD_HHMMSS_nltk/` (phonetic splitting)

#### **Normaliser Output Files**

**Pyphen Normaliser** (written in-place to run directory):

```text
pyphen_syllables_raw.txt              # Aggregated raw syllables
pyphen_syllables_canonicalised.txt    # Normalized (Unicode, diacritics, etc.)
pyphen_syllables_frequencies.json     # Frequency intelligence
pyphen_syllables_unique.txt           # Deduplicated inventory
pyphen_normalization_meta.txt         # Statistics report
```

**NLTK Normaliser** (written in-place to run directory):

```text
nltk_syllables_raw.txt                # Aggregated raw syllables
nltk_syllables_canonicalised.txt      # After fragment cleaning + normalization
nltk_syllables_frequencies.json       # Frequency intelligence
nltk_syllables_unique.txt             # Deduplicated inventory
nltk_normalization_meta.txt           # Statistics report
```

### Key Differences: Pyphen vs NLTK

| Feature | Pyphen Pipeline | NLTK Pipeline |
|---------|-----------------|---------------|
| **Language Support** | 40+ languages | English only (CMUDict) |
| **Splitting Method** | Typographic hyphenation | Phonetic (onset/coda) |
| **Syllable Quality** | Well-formed, formal | May have single-letter fragments |
| **Normaliser Preprocessing** | None | Fragment cleaning (merges single letters) |
| **Output Location** | In-place (run directory) | In-place (run directory) |
| **Output Prefix** | `pyphen_*` | `nltk_*` |
| **Typical Fragment Size** | 2-5+ characters | 1-5+ characters (before cleaning) |

### Fragment Cleaning (NLTK-Specific)

The NLTK normaliser includes a **fragment cleaning** preprocessing step to reconstruct
phonetically coherent syllables:

**Rules:**

1. Single vowels (a, e, i, o, u, y) merge with next fragment
2. Single consonants merge with next fragment
3. Multi-character fragments remain unchanged

**Example:**

```text
Before cleaning: ["i", "down", "the", "r", "a", "bbit", "h", "o", "le"]
After cleaning:  ["idown", "the", "ra", "bbit", "ho", "le"]
```

**Impact:** Typically reduces syllable count by ~9% by merging isolated single-letter fragments.

### When to Use Which Pipeline

**Use Pyphen Pipeline When:**

- You need multi-language support (40+ languages)
- You want formal, typographic syllable boundaries
- You prefer well-formed syllables without fragment issues
- You're working with non-English text

**Use NLTK Pipeline When:**

- You're working with English text only
- You want phonetically-guided syllable boundaries
- You prefer consonant cluster integrity (e.g., "An-drew" not "And-rew")
- You want syllables that feel more like spoken language

**Combining Both Pipelines:**

Both pipelines can be run in parallel for comparison or hybrid corpus building:

```bash
# Extract with both (pyphen will auto-detect language by default)
python -m build_tools.pyphen_syllable_extractor --file input.txt
python -m build_tools.nltk_syllable_extractor --file input.txt

# Normalize both (both use in-place processing now)
python -m build_tools.pyphen_syllable_normaliser --run-dir _working/output/20260110_143022_pyphen/
python -m build_tools.nltk_syllable_normaliser --run-dir _working/output/20260110_095213_nltk/

# Compare outputs (different prefixes make this clear)
diff _working/output/20260110_143022_pyphen/pyphen_syllables_unique.txt \
     _working/output/20260110_095213_nltk/nltk_syllables_unique.txt
```

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

### Documentation Content Rules

**Single Source of Truth:** Documentation should live where it's most naturally
maintained and automatically propagate where possible.

#### What Goes in Code Docstrings (Auto-Generated)

Module `__init__.py` docstrings should contain:

1. **Module Identity** (1-2 sentences)
   - What is this tool/module?
   - Build-time vs runtime designation

2. **Core Capabilities** (bullet points)
   - Key features list
   - Supported modes/workflows (high-level)

3. **Basic Usage Example** (3-10 lines)
   - Minimal working example showing primary use case

**Format:** Google-style docstrings

**Example:**

```python
"""
Syllable Extractor - Dictionary-Based Syllable Extraction

Dictionary-based hyphenation using pyphen (LibreOffice dictionaries).
This is a **build-time tool only** - not used during runtime name generation.

Features:
- Support for 40+ languages
- Automatic language detection (optional)
- Configurable syllable length constraints
- Deterministic extraction

Usage:
    >>> from build_tools.pyphen_syllable_extractor import SyllableExtractor
    >>> extractor = SyllableExtractor('en_US', min_syllable_length=2)
    >>> syllables = extractor.extract_syllables_from_text("Hello world")
"""
```

#### What Stays in RST Files (Manual)

RST files (`docs/source/build_tools/*.rst`) should contain:

1. **Auto-generated sections** (via directives)
   - `.. automodule::` for module overview
   - `.. argparse::` for CLI reference

2. **Detailed tutorials and examples**
   - Multi-scenario usage examples
   - Step-by-step workflows
   - Comparative examples ("when to use X vs Y")

3. **Reference specifications**
   - Output format specifications
   - File naming conventions
   - Data structure documentation

4. **Conceptual explanations**
   - "How it works" sections
   - Architecture/design rationale
   - Multi-paragraph explanations

5. **Warnings and important notes**
   - Caveats and gotchas
   - Performance considerations
   - Common pitfalls

#### Decision Matrix

When adding documentation, ask: **"Does this change when code capabilities change?"**

- **Yes** → Put in code docstring (will auto-propagate)
- **No** → Put in RST (stable reference/tutorial content)

### RST Template for Build Tools

All build tool documentation in `docs/source/build_tools/*.rst` must follow the standard template
located at `docs/source/_templates/build_tool_template.rst`.

#### Required Sections (in order)

1. **Overview** - `.. automodule:: :no-members:` (shows module docstring)
2. **Command-Line Interface** - `.. argparse::` directive (auto-generates CLI options)
3. **Output Format** - Manual description of output files, naming conventions, data structures
4. **Integration Guide** - How the tool fits in the pipeline, when to use it, example workflows
5. **Notes** - Important caveats, performance considerations, troubleshooting
6. **API Reference** - `.. automodule:: :members:` (full class/function documentation)

#### Optional Sections (for complex tools only)

- **Core Concepts** (after Overview) - For complex tools requiring conceptual explanation
  - Example: syllable_walk's phonetic distance, neighbor graphs
- **Advanced Topics** (before API Reference) - Performance benchmarks, algorithm details, troubleshooting
  - Example: syllable_walk's Web Interface, Performance, Algorithm Details

#### Template Files

- **Standard template**: `docs/source/_templates/build_tool_template.rst`
- **Complex template**: `docs/source/_templates/build_tool_template_complex.rst`

Use the complex template when your tool requires:

- Detailed conceptual explanations (Core Concepts section)
- Advanced features (Web interfaces, multiple modes)
- Performance benchmarks or algorithm details

#### Key Principles

1. **No duplicate content** - Code examples stay in `__init__.py` docstrings only
2. **No duplicate CLI examples** - argparse directive generates CLI usage automatically
3. **Consistent ordering** - All tools follow the same section structure
4. **Unique content only** - Manual RST should contain information NOT in code docstrings

#### Example Structure

```rst
===============
Tool Name
===============

.. currentmodule:: build_tools.tool_name

Overview
--------

.. automodule:: build_tools.tool_name
   :no-members:

Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.tool_name.cli
   :func: create_argument_parser
   :prog: python -m build_tools.tool_name

Output Format
-------------

[Manual content: file formats, naming conventions]

Integration Guide
-----------------

[Manual content: pipeline context, when to use]

Notes
-----

[Manual content: caveats, troubleshooting]

API Reference
-------------

.. automodule:: build_tools.tool_name
   :members:
   :undoc-members:
   :show-inheritance:
```

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

### Versioning and Changelog Governance

**Critical Rule**: Use [Conventional Commits](https://www.conventionalcommits.org/) for all commit messages.

#### Commit Message Format

```text
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Types:**

- `feat:` - New feature (triggers minor version bump in 0.x, major in 1.x+)
- `fix:` - Bug fix (triggers patch version bump)
- `docs:` - Documentation only changes
- `refactor:` - Code refactoring with no functionality change
- `chore:` - Maintenance tasks (hidden in changelog)

**Examples:**

```text
feat(build_tools): Add syllable walker for phonetic space exploration
fix(docs): Replace invalid JSON placeholder with valid example
docs: Add documentation content rules to CLAUDE.md
refactor: Move analysis tools to top-level build_tools/syllable_analysis
```

#### Automated Release Workflow

This project uses [release-please](https://github.com/googleapis/release-please) for automated versioning and
changelog generation:

1. **Commit using conventional commits** (as above)
2. **Push to main branch** - release-please bot monitors commits
3. **Release PR is auto-created/updated** - Accumulates changes, updates CHANGELOG.md, bumps version
4. **Manually review and merge the release PR** - This triggers:
   - Git tag creation
   - GitHub release publication
   - Version number update in `pyproject.toml`

**Important**: The release PR stays open and accumulates changes. You can push multiple commits before merging.
**No race conditions** - release only happens when YOU merge the PR.

#### Versioning Strategy (Semantic Versioning)

While in **0.x (Alpha):**

- `0.x.0` - New features, capabilities, or breaking changes
- `0.x.y` - Bug fixes, documentation, internal refactoring

**Current Status**: 0.2.0 (Alpha)

Move to **1.0.0 (Stable)** when:

- Phase 2+ generator is complete (YAML patterns, phonotactic constraints)
- CLI interface is stable
- API is considered production-ready
- External users exist

#### Changelog

CHANGELOG.md is **auto-generated** by release-please from conventional commit messages. Do not manually edit it -
all content comes from commit history.

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
