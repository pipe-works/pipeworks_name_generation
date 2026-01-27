# pipeworks_name_generation

> A corpus linguistics toolkit for extracting, analyzing, and exploring phonetic patterns from any text source.

[![CI](https://github.com/pipe-works/pipeworks_name_generation/actions/workflows/ci.yml/badge.svg)](https://github.com/pipe-works/pipeworks_name_generation/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/pipe-works/pipeworks_name_generation/branch/main/graph/badge.svg)](https://codecov.io/gh/pipe-works/pipeworks_name_generation)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/pipe-works/pipeworks_name_generation)

`pipeworks_name_generation` is a standalone, GPL-3.0-or-later licensed toolkit for developers and world-builders who want to analyze phonetic patterns in text. It provides a comprehensive suite of corpus linguistics tools to extract, analyze, and explore syllabic structure from any text source.

The project also includes a lightweight, deterministic name generator as a **reference implementation**, demonstrating how to use the processed data to create pronounceable names suitable for games, simulations, and other generative systems.

---

## What Is This?

This project is fundamentally a **build tools ecosystem** for corpus linguistics. The core value lies in understanding and processing the linguistic ingredients that make names work, not in the act of assembling them.

**What you get:**

- Command-line tools for syllable extraction (Pyphen for 40+ languages, NLTK for English phonetics)
- Phonetic feature analysis and annotation
- Interactive exploration tools (syllable walker with TUI)
- Data provenance tracking via corpus database
- Analysis and visualization utilities (t-SNE, feature analysis, random sampling)

**Plus a reference implementation:**

- A lightweight, deterministic name generator showing how to consume the processed data
- Zero runtime dependencies
- Fully tested and documented

---

## Installation

**Note**: This package is not yet published to PyPI. Install from source:

### For Corpus Analysis (Primary Use Case)

If you want to extract, analyze, and explore syllable data from text:

```bash
git clone https://github.com/pipe-works/pipeworks_name_generation.git
cd pipeworks_name_generation
pip install -e ".[build-tools]"
```

This installs the full suite of command-line tools with all dependencies (pyphen, NLTK, scikit-learn, matplotlib, pandas, etc.).

### For Runtime Name Generation Only

If you only need the reference implementation generator (zero dependencies):

```bash
git clone https://github.com/pipe-works/pipeworks_name_generation.git
cd pipeworks_name_generation
pip install -e .
```

### From Git (Without Cloning)

```bash
# With build tools
pip install "pipeworks-name-generation[build-tools] @ git+https://github.com/pipe-works/pipeworks_name_generation.git@main"

# Without build tools (zero dependencies)
pip install "pipeworks-name-generation @ git+https://github.com/pipe-works/pipeworks_name_generation.git@main"
```

---

## Quick Start: Build Tools

The build tools are the core of this project. Here's a typical workflow for processing a text corpus:

### 1. Extract Syllables

Choose your extraction method:

```bash
# Option 1: Typographic hyphenation (Pyphen) - supports 40+ languages
python -m build_tools.pyphen_syllable_extractor --file input.txt --auto

# Option 2: Phonetic extraction (NLTK) - English only, uses CMU Pronouncing Dictionary
python -m build_tools.nltk_syllable_extractor --file input.txt
```

### 2. Normalize and Analyze

```bash
# Normalize extracted syllables (canonicalization and frequency analysis)
python -m build_tools.pyphen_syllable_normaliser --source _working/output/

# Annotate phonetic features (onsets, codas, clusters, etc.)
python -m build_tools.syllable_feature_annotator \
  --syllables _working/output/20260110_143022_pyphen/pyphen_syllables_unique.txt \
  --frequencies _working/output/20260110_143022_pyphen/pyphen_syllables_frequencies.json
```

### 3. Explore Interactively

```bash
# Launch interactive TUI for exploring syllable space
python -m build_tools.syllable_walker \
  --syllables _working/output/20260110_143022_pyphen/pyphen_syllables_unique.txt
```

### 4. Generate Name Candidates

```bash
# Combine syllables into name candidates
python -m build_tools.name_combiner \
  --run-dir _working/output/20260110_143022_pyphen/ \
  --syllables 2 --count 10000 --seed 42

# Select names by policy (first_name, last_name, place_name, etc.)
python -m build_tools.name_selector \
  --run-dir _working/output/20260110_143022_pyphen/ \
  --candidates candidates/pyphen_candidates_2syl.json \
  --name-class first_name --count 100
```

📖 **[Full Build Tools Documentation →](https://pipeworks-name-generation.readthedocs.io/en/latest/build_tools/index.html)**

---

## Reference Implementation: Name Generator

The included `NameGenerator` demonstrates how to consume processed syllable data at runtime. It's designed to be simple, deterministic, and dependency-free.

### Basic Usage

```python
from pipeworks_name_generation import NameGenerator

# Create a generator (uses 'simple' pattern with hardcoded dataset)
gen = NameGenerator(pattern="simple")

# Generate a name deterministically
name = gen.generate(seed=42)
print(name)  # "Kawyn"

# Same seed always produces the same name
assert gen.generate(seed=42) == name
```

### Design Philosophy

Names generated by this system are **structural**, not narrative.

They are designed to feel: plausible, consistent, and pronounceable.

...but not authoritative.

Meaning, history, and interpretation are applied later, elsewhere.

---

## The Build Tools Ecosystem

The project provides a comprehensive suite of command-line tools:

- **Pyphen Syllable Extractor** - Dictionary-based extraction using pyphen (40+ languages)
- **NLTK Syllable Extractor** - Phonetically-guided extraction using CMU Pronouncing Dictionary (English only)
- **Pyphen Syllable Normaliser** - 3-step pipeline for canonicalization and frequency analysis
- **NLTK Syllable Normaliser** - NLTK-specific normalization with fragment cleaning
- **Syllable Feature Annotator** - Phonetic feature detection (onsets, codas, clusters, vowels)
- **Syllable Walk TUI** - Interactive terminal UI for exploring phonetic feature space (Textual)
- **Syllable Walk Web** - Web-based syllable explorer with interactive visualization
- **Pipeline TUI** - Interactive terminal UI for running the full extraction pipeline
- **Name Combiner** - Generate name candidates from syllable pools
- **Name Selector** - Policy-based filtering (first_name, last_name, place_name, etc.)
- **Corpus Database** - Build provenance ledger for tracking extraction runs
- **Corpus DB Viewer** - Interactive terminal UI for viewing corpus database
- **Analysis Tools** - Feature analysis, t-SNE visualization, random sampling

Each tool is designed to be composable and produce structured output that feeds into the next stage of processing.

---

## Documentation

Complete documentation, including detailed usage guides and the full API reference, is
available at **[pipeworks-name-generation.readthedocs.io](https://pipeworks-name-generation.readthedocs.io/)**.

- **[Build Tools Guide](https://pipeworks-name-generation.readthedocs.io/en/latest/build_tools/index.html)**
  \- Detailed usage for all command-line tools.
- **[API Reference](https://pipeworks-name-generation.readthedocs.io/en/latest/autoapi/index.html)**
  \- Complete API documentation for all modules.
- **[Changelog](https://pipeworks-name-generation.readthedocs.io/en/latest/changelog.html)**
  \- Full release history and list of changes.

---

## Development

### Requirements

- Python 3.12 or higher

### Setup

```bash
git clone https://github.com/pipe-works/pipeworks_name_generation.git
cd pipeworks_name_generation
pip install -e ".[dev]"
pytest
```

## Project Status

**Status**: Alpha

The project is in active development. The build tools and underlying infrastructure are mature
and production-grade. The "Alpha" status reflects that the core `NameGenerator` API and its
pattern-loading capabilities are still evolving and subject to change before the 1.0.0-beta release.

- ✅ Comprehensive test coverage (>90%)
- ✅ Full CI/CD pipeline with automated checks
- ✅ Type-safe codebase with MyPy
- ✅ Automated documentation via Sphinx

## License

This project is licensed under the GPL-3.0-or-later. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
