# Transition Map

This document records the legacy-to-canonical ownership split for the
`pipeworks_name_generation` migration.

## Canonical Repository Map

1. `pipeworks-namegen-lexicon`
   - Owns corpus/lexicon creation pipeline and lexicon web UI.
   - Receives all extraction/normalization/annotation/selection build-tool work.
2. `pipeworks-namegen-core`
   - Owns deterministic generation primitives and rendering helpers.
   - No HTTP server or deployment ownership.
3. `pipeworks-namegen-api`
   - Owns production HTTP runtime (`/api/generate`) and runtime deployment.
   - Canonical location for systemd/nginx/server.ini templates.

## Legacy Repo Scope (This Repository)

This repository is now transition/meta-only and should not be used as a
production runtime owner.

Retained purpose:

1. Migration history and auditability.
2. Pointer docs to canonical repos.
3. Closeout and archiving workflow.

## Hard Cutover Statement

Phase 7 policy is hard cutover:

1. Legacy compatibility wrappers are retired.
2. Production usage should not depend on legacy runtime surfaces.
3. Operational fallback after cutover should use versioned releases of the
   three canonical repos.

## Archive Intent

Once Phase 8 is complete and archive-readiness checklist items are satisfied,
this repository may be archived in GitHub while retaining history and tags.
