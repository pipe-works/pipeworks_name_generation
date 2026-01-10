# Development Guide

This document covers setup, testing, code quality, and development workflows for the pipeworks_name_generation project.

## Setup

```bash
# Create virtual environment (Python 3.12+)
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt
pip install -e .
```

## Testing

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_minimal_generation.py

# Run specific test
pytest tests/test_minimal_generation.py::TestBasicGeneration::test_generator_creates_deterministic_names

# Run tests verbose
pytest -v

# Run tests with coverage report
pytest --cov=pipeworks_name_generation --cov-report=html
```

## Code Quality

```bash
# Lint with ruff
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Type checking with mypy
mypy pipeworks_name_generation/

# Format with black (line length: 100)
black pipeworks_name_generation/ tests/

# Run all code quality checks at once
pre-commit run --all-files
```

## Pre-commit Hooks

```bash
# Install pre-commit hooks (one-time setup)
pip install pre-commit
pre-commit install

# Run hooks manually on all files
pre-commit run --all-files

# Run hooks manually on staged files
pre-commit run

# Update hooks to latest versions
pre-commit autoupdate

# Skip hooks for a commit (use sparingly)
git commit --no-verify
```

## Running Examples

```bash
python examples/minimal_proof_of_concept.py
```

## Build Tool Commands

```bash
# Extract syllables from text (interactive mode)
python -m build_tools.pyphen_syllable_extractor

# Extract syllables in batch mode - single file
python -m build_tools.pyphen_syllable_extractor --file input.txt --lang en_US

# Extract syllables in batch mode - multiple files
python -m build_tools.pyphen_syllable_extractor --files file1.txt file2.txt file3.txt --auto

# Extract syllables in batch mode - directory scan
python -m build_tools.pyphen_syllable_extractor --source ~/documents/ --pattern "*.txt" --lang en_US

# Extract syllables in batch mode - recursive directory scan with auto-detection
python -m build_tools.pyphen_syllable_extractor --source ~/corpus/ --recursive --auto

# Extract syllables with custom parameters
python -m build_tools.pyphen_syllable_extractor --file input.txt --lang de_DE --min 3 --max 6 --output ~/results/

# Run syllable extraction example (programmatic)
python examples/syllable_extraction_example.py

# Test syllable extractor (all tests)
pytest tests/test_syllable_extractor.py tests/test_syllable_extractor_batch.py -v

# Test only batch processing
pytest tests/test_syllable_extractor_batch.py -v

# Normalize syllables through 3-step pipeline (build-time tool)
python -m build_tools.pyphen_syllable_normaliser --source data/corpus/ --output _working/normalized/

# Normalize syllables recursively with custom parameters
python -m build_tools.pyphen_syllable_normaliser \
  --source data/ \
  --recursive \
  --min 3 \
  --max 10 \
  --output results/ \
  --verbose

# Test syllable normaliser (40 tests)
pytest tests/test_syllable_normaliser.py -v
```

For detailed documentation on each build tool, see:

- [Syllable Extractor](build_tools/syllable_extractor.md)
- [Syllable Normaliser](build_tools/syllable_normaliser.md)
- [Feature Annotator](build_tools/feature_annotator.md)
- [Analysis Tools](build_tools/analysis_tools.md)

## Documentation

```bash
# Build documentation (fully automated from code docstrings)
cd docs
make html

# View documentation (macOS)
open build/html/index.html

# Clean and rebuild
make clean && make html

# Documentation is automatically generated from code using sphinx-autoapi
# No manual .rst files needed - just write good docstrings!
# The docs are also built automatically on ReadTheDocs when pushed to GitHub
```

## CLI Documentation Standards

**CRITICAL**: All CLI tools MUST document command-line arguments in code, not in README or manual docs.

### The Pattern: `create_argument_parser()`

Every CLI tool must use this pattern for sphinx-argparse compatibility:

```python
def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and return the argument parser for [tool name].

    This function creates the ArgumentParser with all CLI options but does not
    parse arguments. This separation allows Sphinx documentation tools to
    introspect the parser and auto-generate CLI documentation.

    Returns:
        Configured ArgumentParser ready to parse command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Clear description of what this tool does",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with default settings
  python -m build_tools.tool_name

  # Custom options
  python -m build_tools.tool_name --option value --other-option 42
        """,
    )

    parser.add_argument(
        "--option",
        type=str,
        default="default_value",
        help="Detailed help text. Default: default_value",
    )

    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Number of items to process (default: 100)",
    )

    return parser


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = create_argument_parser()
    return parser.parse_args(args)
```

### Required Elements

1. **Function must be named `create_argument_parser()`** (sphinx-argparse requirement)
2. **Must return `ArgumentParser` object, NOT `Namespace`** (sphinx needs the parser)
3. **Every argument must have detailed help text**
4. **Include default values in help text** (e.g., "Default: 100")
5. **Use `RawDescriptionHelpFormatter` for epilog examples**
6. **Add concrete usage examples in epilog**

### Good Help Text Examples

```python
# ✅ GOOD - Detailed, includes default
parser.add_argument(
    "--perplexity",
    type=int,
    default=30,
    help="t-SNE perplexity parameter balancing local vs global structure. "
         "Typical range: 5-50. Lower values emphasize local clusters, "
         "higher values preserve global structure (default: 30)",
)

# ✅ GOOD - Explains purpose clearly
parser.add_argument(
    "--output",
    type=Path,
    default=Path("_working/output/"),
    help="Output directory for generated files. Directory will be created "
         "if it doesn't exist (default: _working/output/)",
)

# ❌ BAD - Too brief, no default mentioned
parser.add_argument(
    "--perplexity",
    type=int,
    default=30,
    help="Perplexity parameter",
)

# ❌ BAD - No help text at all
parser.add_argument(
    "--output",
    type=Path,
    default=Path("_working/output/"),
)
```

### Integration with Sphinx

The pattern enables automatic CLI documentation via sphinx-argparse:

```rst
Command-Line Interface
----------------------

.. argparse::
   :module: build_tools.tool_name.cli
   :func: create_argument_parser
   :prog: python -m build_tools.tool_name
```

This automatically extracts and formats:

- All `--options` with help text
- Default values
- Argument types
- Required vs optional arguments
- Usage examples from epilog

### Why This Matters

**Single Source of Truth:**

- CLI options documented in code → automatically appear in Sphinx docs
- No manual synchronization between README and actual arguments
- No forgetting what `--options` exist

**User Benefits:**

- Users always see accurate, up-to-date CLI documentation
- Generated docs show all available options
- Help text explains purpose, not just syntax

**Developer Benefits:**

- Add new CLI option → documentation updates automatically
- Remove option → documentation updates automatically
- Change default → documentation updates automatically

### Existing Examples

See these files for reference implementations:

- `build_tools/syllable_extractor/cli.py` - Full example with batch/interactive modes
- `build_tools/syllable_normaliser/cli.py` - Comprehensive option set
- `build_tools/syllable_feature_annotator/cli.py` - Clean, minimal example
- `build_tools/syllable_analysis/tsne_visualizer.py` - Algorithm parameters example

## Project Configuration

- **Python Version**: 3.12+
- **License**: GPL-3.0-or-later (all contributions must remain GPL)
- **Line Length**: 100 characters (black/ruff)
- **Type Checking**: mypy enabled but lenient in Phase 1 (`disallow_untyped_defs = false`)
- **Test Framework**: pytest with coverage reporting
- **Pre-commit Hooks**: Enabled for automated code quality checks
- **CI/CD**: GitHub Actions for testing, linting, security, docs, and builds

See also: [CI/CD Documentation](ci_cd.md)
