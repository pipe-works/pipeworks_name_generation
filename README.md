# pipeworks_name_generation

> A corpus linguistics toolkit for procedural name generation, featuring dual syllable
> extraction pipelines, phonetic analysis, and interactive exploration tools.

[![CI](https://github.com/aa-parky/pipeworks_name_generation/actions/workflows/ci.yml/badge.svg)](https://github.com/aa-parky/pipeworks_name_generation/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/aa-parky/pipeworks_name_generation/branch/main/graph/badge.svg)](https://codecov.io/gh/aa-parky/pipeworks_name_generation)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/aa-parky/pipeworks_name_generation)

`pipeworks_name_generation` is a standalone, GPL-3 licensed toolkit for developers and
world-builders who want to generate names that *sound right* without being predictable. It
provides a powerful suite of corpus linguistics tools to extract, analyze, and explore phonetic
patterns from any text source.

The project also includes a lightweight, deterministic name generator as a reference
implementation, demonstrating how to use the processed data to create pronounceable, neutral
names suitable for games, simulations, and other generative systems.

---

## Project Philosophy: The Tools are the Magic

This project began with a simple goal: to create a better name generator. Existing solutions
often felt repetitive or statistically predictable. The journey to solve this led to a deeper
realization: the real magic isn't in the final act of assembling a name, but in understanding
the linguistic ingredients that make it work.

Therefore, the core of this project is the **build tools ecosystem**. This is a comprehensive
suite of command-line utilities for performing corpus linguistics, from syllable extraction and
normalization to phonetic feature analysis and interactive visualization. The name generator
itself is a deliberately simple consumer of the rich, structured data these tools produce.

This structure means the project's value lies in its ability to provide deep, reusable insights
into the phonetic and syllabic structure of any given text, which can then be used for a wide
variety of procedural generation tasks, including but not limited to name generation.

---

## Key Features

- **Comprehensive Build Tools**: A full suite for corpus linguistics and data preparation,
  forming the core of the project.
- **Dual Extraction Pipelines**: Process text using either typographic (Pyphen, 40+ languages)
  or phonetic (NLTK, English) syllable extraction.
- **Linguistically Plausible Generation**: Generate names based on real phonetic patterns,
  not just random strings.
- **Deterministic Runtime**: The lightweight generator is fully deterministic; the same seed
  will always produce the same name.
- **Zero Runtime Dependencies**: The core generator is a minimal, stable, and predictable
  library with no external dependencies.
- **Fully Documented & Tested**: High test coverage (>90%) and automated documentation ensure reliability and ease of use.

---

## Quick Start: The Name Generator

While the build tools are the project's core, the name generator provides a simple, immediate entry point.

### Installation

```bash
pip install pipeworks-name-generation
```

### Generate Your First Name

```python
from pipeworks_name_generation import NameGenerator

# Create a generator (the 'simple' pattern uses a small, hardcoded dataset)
gen = NameGenerator(pattern="simple")

# Generate a name deterministically
name = gen.generate(seed=42)
print(name)  # "Kawyn"

# Same seed = same name (always!)
assert gen.generate(seed=42) == name
```

---

## The Build Tools Ecosystem

The true power of the project lies in its command-line tools for corpus analysis.

- **Pyphen Syllable Extractor** - Dictionary-based extraction using pyphen (40+ languages).
- **NLTK Syllable Extractor** - Phonetically-guided extraction using CMU Pronouncing Dictionary (English only).
- **Pyphen Syllable Normaliser** - A 3-step pipeline for canonicalization and frequency analysis.
- **NLTK Syllable Normaliser** - NLTK-specific normalization with fragment cleaning.
- **Syllable Feature Annotator** - Phonetic feature detection (e.g., onsets, codas).
- **Syllable Walker** - Interactive exploration of the phonetic feature space.
- **Corpus Database** - A build provenance ledger for tracking extraction runs.
- **Analysis Tools** - Tools for feature analysis, t-SNE visualization, and random sampling.

**Example Workflow:**

```bash
# Option 1: Extract syllables with pyphen (typographic hyphenation, 40+ languages)
python -m build_tools.pyphen_syllable_extractor --file input.txt --auto

# Option 2: Extract syllables with NLTK (phonetic splits, English only)
python -m build_tools.nltk_syllable_extractor --file input.txt

# Normalize the extracted syllables (works with either extractor)
python -m build_tools.pyphen_syllable_normaliser --source _working/output/
```

📖 **[Full Build Tools Documentation →](https://pipeworks-name-generation.readthedocs.io/en/latest/build_tools/index.html)**

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

## Design Philosophy

Names generated by this system are **structural**, not narrative.

They are designed to feel: plausible, consistent, and pronounceable.

...but not authoritative.

Meaning, history, and interpretation are applied later, elsewhere.

---

## Development

### Requirements

- Python 3.12 or higher

### Setup

```bash
git clone https://github.com/aa-parky/pipeworks_name_generation.git
cd pipeworks_name_generation
pip install -e ".[dev]"
pytest
```

## Project Status

**Status**: Alpha

The project is in active development. The build tools and underlying infrastructure are mature
and production-grade. The "Alpha" status reflects that the core `NameGenerator` API and its
pattern-loading capabilities are still evolving and subject to change before the 0.5.0 release.

- ✅ Comprehensive test coverage (>90%)
- ✅ Full CI/CD pipeline with automated checks
- ✅ Type-safe codebase with MyPy
- ✅ Automated documentation via Sphinx

## License

This project is licensed under the GPL-3.0-or-later. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
