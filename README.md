# pipeworks_name_generation

> A lightweight, phonetic name generator that produces names which *sound right*,
> without imposing what they *mean*.

[![CI](https://github.com/aa-parky/pipeworks_name_generation/actions/workflows/ci.yml/badge.svg)](https://github.com/aa-parky/pipeworks_name_generation/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/aa-parky/pipeworks_name_generation/branch/main/graph/badge.svg)](https://codecov.io/gh/aa-parky/pipeworks_name_generation)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/aa-parky/pipeworks_name_generation)

`pipeworks_name_generation` is a standalone, GPL-3 licensed name generation system based on phonetic and syllabic recombination.

It generates **pronounceable, neutral names** intended to act purely as labels.  
Any narrative, cultural, or semantic meaning is deliberately left to downstream systems.

This project is designed to stand on its own and can be used independently of Pipeworks in games, simulations, world-building tools, or other generative systems.

---

## Design Goals

- Generate names that are **linguistically plausible**, not random strings
- Avoid direct copying of real names or source material
- Support **deterministic generation** via seeding
- Remain **context-free** and reusable across domains
- Keep runtime dependencies lightweight, predictable, and stable
- Allow different consumers to apply their own meaning and interpretation

---

## Installation

### Requirements

- Python 3.12 or higher
- No runtime dependencies (by design)

### From Source

Clone the repository and install in development mode:

```bash
git clone https://github.com/aa-parky/pipeworks_name_generation.git
cd pipeworks_name_generation
pip install -e .
```

For development with testing and documentation tools:

```bash
pip install -e ".[dev]"
```

### From PyPI

> **Note:** Package not yet published to PyPI. Currently in Phase 1 (proof of concept).

Once published, installation will be:

```bash
pip install pipeworks-name-generation
```

### Verify Installation

Run the proof of concept example:

```bash
python examples/minimal_proof_of_concept.py
```

---

## Quick Start

```python
from pipeworks_name_generation import NameGenerator

# Create a generator
gen = NameGenerator(pattern="simple")

# Generate a name deterministically
name = gen.generate(seed=42)
print(name)  # "Kawyn"

# Same seed = same name (always!)
assert gen.generate(seed=42) == name

# Generate multiple unique names
names = gen.generate_batch(count=10, base_seed=1000, unique=True)
print(names)
# ['Borkragmar', 'Kragso', 'Thrakrain', 'Alisra', ...]
```

**Key Feature:** Determinism is guaranteed. The same seed will always produce the same name, making this ideal for games where entity IDs need consistent names across sessions.

---

## Documentation

Full documentation is available and includes:

- **Installation Guide** - Setup instructions
- **Quick Start** - Get started in 5 minutes
- **User Guide** - Comprehensive usage patterns and examples
- **API Reference** - Complete API documentation
- **Development Guide** - Contributing and development setup

### Building Documentation Locally

To build and view the documentation on your machine:

```bash
# Install documentation dependencies
pip install -e ".[docs]"

# Build the HTML documentation
cd docs
make html

# View the documentation
open build/html/index.html  # macOS
xdg-open build/html/index.html  # Linux
start build/html/index.html  # Windows
```

To clean and rebuild:

```bash
make clean && make html
```

### Online Documentation

> **Coming Soon:** Documentation will be automatically hosted on ReadTheDocs when the repository is public.

---

## Non-Goals

This project deliberately does **not**:

- Encode lore, narrative meaning, or symbolism
- Distinguish between characters, places, organisations, or objects
- Imply cultural, regional, or historical identity
- Enforce genre-specific naming conventions
- Perform runtime natural-language processing
- Act as a world-building or storytelling system

All such concerns are expected to be handled by consuming applications.

---

## Architecture Overview

At a high level, the system works as follows:

1. Phonetic or syllabic units are derived from language corpora  
   *(analysis and build-time only)*
2. These units are stored as neutral, reusable data
3. Names are generated by recombining units using weighted rules and constraints
4. The system emits pronounceable name strings, without semantic awareness

Natural language toolkits (such as NLTK) may be used during **analysis or build phases**,  
but are intentionally excluded from the runtime generation path.

This keeps generation fast, deterministic, and easy to embed.

---

## Usage

`pipeworks_name_generation` is intended to be consumed programmatically.

Typical use cases include:

- Character name generation
- Place and location naming
- Organisation or faction names
- Artefact or object labels
- Procedural or generative world systems

The generator itself does not distinguish between these uses.

---

## Design Philosophy

Names generated by this system are **structural**, not narrative.

They are designed to feel:

- plausible
- consistent
- pronounceable

…but not authoritative.

Meaning, history, and interpretation are applied later, elsewhere.

---

## Licence

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

You are free to use, modify, and distribute this software under the terms of the GPL.  
Improvements and derivative works must remain open under the same licence.

See the `LICENSE` file for full details.

---

## Status

This project is under active development.  
APIs and internal structures may change as the system stabilises.
