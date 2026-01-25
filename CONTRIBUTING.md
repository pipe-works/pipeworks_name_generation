# Contributing to Pipeworks Name Generation

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

Be respectful, constructive, and professional in all interactions.

## Getting Started

### Development Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/pipe-works/pipeworks_name_generation.git
   cd pipeworks_name_generation
   ```

2. **Set up Python environment** (Python 3.12+):

   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:

   ```bash
   pip install --upgrade pip
   pip install -r requirements-dev.txt
   pip install -e .
   ```

4. **Install pre-commit hooks**:

   ```bash
   pre-commit install
   ```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Your Changes

Follow these guidelines:

- **Code Style**: The project uses Black for formatting (line length: 100)
- **Linting**: Ruff for linting (automatically fixes many issues)
- **Type Hints**: mypy for type checking (lenient in Phase 1)
- **Determinism**: CRITICAL - maintain deterministic behavior in name generation

### 3. Write Tests

- All new features must include tests
- Bug fixes should include regression tests
- Tests must pass before submitting PR

```bash
# Run tests
pytest -v

# Run tests with coverage
pytest --cov=pipeworks_name_generation --cov-report=html
```

### 4. Run Pre-commit Hooks

```bash
# Run all hooks on all files
pre-commit run --all-files

# Or commit and hooks run automatically
git add .
git commit -m "Your commit message"
```

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Code Quality Standards

### Automated Checks

Pre-commit hooks automatically enforce:

- **Formatting**: Black, isort
- **Linting**: Ruff
- **Type Checking**: mypy
- **Security**: Bandit, Safety
- **Documentation**: markdownlint, codespell

### Manual Review Checklist

Before submitting a PR, verify:

- [ ] Code follows project conventions
- [ ] All tests pass
- [ ] New features have documentation
- [ ] Docstrings follow Google style
- [ ] Type hints are present (where reasonable)
- [ ] No unnecessary dependencies added
- [ ] Determinism is maintained (if touching generation code)

## Testing Requirements

### Critical Tests

The following test **must always pass**:

```python
# Determinism test
gen = NameGenerator(pattern="simple")
assert gen.generate(seed=42) == gen.generate(seed=42)

# Batch determinism test
batch1 = gen.generate_batch(count=5, base_seed=42)
batch2 = gen.generate_batch(count=5, base_seed=42)
assert batch1 == batch2
```

### Test Organization

```text
tests/
├── test_minimal_generation.py    # Core generation tests
├── test_syllable_extractor.py    # Build tool tests
└── test_*.py                      # Additional test modules
```

## Documentation

### Docstring Style

Use Google-style docstrings:

```python
def example_function(param1: str, param2: int) -> bool:
    """Brief description of function.

    Longer description if needed, explaining behavior,
    edge cases, and important notes.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When and why this is raised

    Example:
        >>> example_function("test", 42)
        True
    """
    pass
```

### Documentation Build

```bash
cd docs
make html
open build/html/index.html  # macOS
```

## Design Principles

### Core Requirements

1. **Determinism is Paramount**: Same seed must always produce same name
2. **Zero Runtime Dependencies**: No external libraries at runtime
3. **Build-time vs Runtime**: Heavy processing (NLP, corpus analysis) is build-time only
4. **Context-Free**: Names have no semantic meaning or cultural affiliation
5. **Lightweight**: Fast generation, minimal memory footprint

### Phase 1 Limitations

The project is currently in Phase 1 (Proof of Concept):

- Only "simple" pattern exists
- Syllables are hardcoded
- No YAML loading yet
- No phonotactic constraints yet
- No CLI yet

These are **not bugs** - they are intentional scope limitations.

## CI/CD Pipeline

### GitHub Actions

PRs and commits trigger automated checks:

1. **Code Quality**: Ruff, Black, mypy
2. **Tests**: Ubuntu, macOS, Windows with Python 3.12 and 3.13
3. **Security**: Bandit, Safety
4. **Documentation**: Sphinx build
5. **Package Build**: Distribution package validation

### Pre-commit.ci

The project uses pre-commit.ci for automated PR fixes:

- Runs on every PR
- Auto-fixes formatting issues
- Creates fix commits automatically

## Commit Messages

Use clear, descriptive commit messages:

```text
feat: Add phonotactic constraint validation
fix: Ensure deterministic syllable selection
docs: Update API documentation for NameGenerator
test: Add edge case tests for empty syllables
refactor: Simplify syllable selection logic
```

Prefixes:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `test:` - Test additions/changes
- `refactor:` - Code restructuring
- `perf:` - Performance improvements
- `chore:` - Maintenance tasks

## Questions?

- **Issues**: Open a GitHub issue
- **Discussions**: Use GitHub Discussions
- **Documentation**: Check CLAUDE.md for detailed development info

## License

By contributing, you agree that your contributions will be licensed under the GPL-3.0-or-later license.
