# AGENTS.md

## Repo Summary

- Primary focus is `build_tools/` (corpus analysis, extraction, selection, TUIs).
- Runtime generator in `pipeworks_name_generation/` is intentionally minimal.

## Non-Negotiables

- Determinism: use isolated RNGs (`random.Random(seed)`), avoid global state.
- Zero runtime deps: heavy NLP and analysis stay in build-time tools.
- Build outputs should be reproducible with fixed seeds.

## Development Workflow

- Python 3.12+
- Install deps:
  - `pip install -r requirements-dev.txt`
  - `pip install -e .`
- Pre-commit hooks:
  - `pre-commit install`
  - `pre-commit run --all-files`
- Tests:
  - `pytest -v`

## Docs

- Build Sphinx docs:
  - `make -C docs html`
  - Output: `docs/build/html/index.html`

## GitHub/PR Standards

- Follow `.github/PULL_REQUEST_TEMPLATE.md` checklist.
- Include tests for changes and run pre-commit before PR.
- Keep changes scoped and document any behavior changes.
- Release Please: use conventional commit prefixes (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`)
  and/or squash PRs with a conventional title so release-please can open a release PR.

## Useful Paths

- TUI: `build_tools/syllable_walk_tui/`
- Name classes: `data/name_classes.yml`
- Build tool docs: `docs/source/build_tools/`
- Tests: `tests/`
