# pipeworks_name_generation (Legacy Transition Repository)

This repository is now in **transition/meta-only** state.

Production and active ownership has moved to three purpose-built repositories:

1. [`pipeworks-namegen-lexicon`](https://github.com/pipe-works/pipeworks-namegen-lexicon)
   - Lexicon/corpus extraction, normalization, annotation, selection pipeline.
   - Lexicon web UI ownership.
2. [`pipeworks-namegen-core`](https://github.com/pipe-works/pipeworks-namegen-core)
   - Deterministic generation primitives and rendering helpers.
3. [`pipeworks-namegen-api`](https://github.com/pipe-works/pipeworks-namegen-api)
   - Canonical production runtime and HTTP service boundary (`/api/generate`).
   - Deployment ownership (`systemd`, `nginx`, runtime templates under `deploy/`).

## Hard Cutover Policy

Phase 7 migration policy is a hard cutover:

1. No long-term legacy compatibility support in this repository.
2. No production deployment ownership remains here.
3. Consumers should integrate through `pipeworks-namegen-api`.

## Where To Go Now

1. Runtime deployment templates and operations docs:
   - [`pipeworks-namegen-api/deploy`](https://github.com/pipe-works/pipeworks-namegen-api/tree/main/deploy)
2. Lexicon pipeline tooling and web flows:
   - [`pipeworks-namegen-lexicon`](https://github.com/pipe-works/pipeworks-namegen-lexicon)
3. Deterministic core package:
   - [`pipeworks-namegen-core`](https://github.com/pipe-works/pipeworks-namegen-core)

## Transition Map

See [`TRANSITION.md`](TRANSITION.md) for migration mapping, ownership boundaries,
and archive-readiness context.

For Phase 8 closeout governance and archive execution steps, see
[`CLOSEOUT.md`](CLOSEOUT.md).

## Repository Status

This repository is retained only for:

1. Migration history and auditability.
2. Pointers to canonical repositories.
3. Final closeout/archival steps.
