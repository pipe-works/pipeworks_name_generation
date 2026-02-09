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
- CI must run on PRs targeting `main` or `develop`:
  - Workflow: `.github/workflows/ci.yml` (reusable workflow in `pipe-works/.github`).
  - Triggers: `pull_request` to `main`/`develop`, `push` to `main`/`develop`/`release-please--*`,
    plus `workflow_dispatch`/`workflow_call`.
  - If a PR shows "no checks", verify the base branch is `main`/`develop` and that Actions are enabled.

## Useful Paths

- TUI: `build_tools/syllable_walk_tui/`
- Name classes: `data/name_classes.yml`
- Build tool docs: `docs/source/build_tools/`
- Tests: `tests/`

## Code Map (High-Level)

- Runtime generator: `pipeworks_name_generation/generator.py` (minimal, hardcoded syllables, deterministic `random.Random(seed)`).
- Runtime rendering helpers: `pipeworks_name_generation/renderer.py` (render styles: raw/lower/upper/title/sentence).
- Web app (HTTP server + API): `pipeworks_name_generation/webapp/`:
  - Server entrypoint: `server.py` (UI + API).
  - API-only entrypoint: `api.py` (forces API-only routes).
  - DB layer: `db/` (SQLite schema + repositories + table store).
  - Favorites: `favorites/` (SQLite-backed favorites store).
  - Frontend assets: `frontend/` (HTML/CSS/JS).
- Build tools (primary focus): `build_tools/`:
  - Extraction: `pyphen_syllable_extractor/` (multi-language, typographic), `nltk_syllable_extractor/` (English phonetic).
  - Normalization: `pyphen_syllable_normaliser/`, `nltk_syllable_normaliser/` (in-place run-dir pipelines).
  - Annotation: `syllable_feature_annotator/` (12 feature detectors).
  - Analysis: `syllable_analysis/` (sampling, feature signatures, t-SNE, plotting).
  - Selection policy layer: `name_combiner/` (structural candidates) + `name_selector/` (policy evaluation).
  - Syllable walk explorer: `syllable_walk/` + `syllable_walk_tui/` + `syllable_walk_web/`.
  - Corpus ledger: `corpus_db/` (provenance DB; default `data/raw/syllable_extractor.db`).

## Build Pipeline (Common Flow)

- Extract syllables: `pyphen_syllable_extractor` or `nltk_syllable_extractor`.
- Normalize: `pyphen_syllable_normaliser` or `nltk_syllable_normaliser` (creates `*_syllables_*.{txt,json}`).
- Annotate features: `syllable_feature_annotator` (creates annotated JSON).
- Generate candidates: `name_combiner` (candidates JSON).
- Select names: `name_selector` (policy-based selections using `data/name_classes.yml`).

## Internal Docs

- Detailed guides live in `claude/` (architecture, build tools, development guide, CI/CD).
