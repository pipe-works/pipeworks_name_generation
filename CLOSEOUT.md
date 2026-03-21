# Phase 8 Closeout and Archive Plan

This document records the final architecture decision, ongoing ownership model,
and archive action plan for the legacy `pipeworks_name_generation` repository.

## Final Architecture Decision

The migration is finalized as a three-repository model:

1. `pipeworks-namegen-lexicon`
   - Owns lexicon/corpus extraction, normalization, annotation, selection, and lexicon web UI.
2. `pipeworks-namegen-core`
   - Owns deterministic generation primitives and rendering helpers.
3. `pipeworks-namegen-api`
   - Owns production HTTP runtime (`/api/generate`) and deployment templates.

Hard cutover policy:

1. `pipeworks_name_generation` is not a production runtime owner.
2. Legacy compatibility maintenance is retired.
3. Runtime consumers should use `pipeworks-namegen-api` over HTTP.

## Maintenance Ownership and Cadence

### Ownership Matrix

1. API contract and runtime operations:
   - Repository: `pipeworks-namegen-api`
   - Owner focus: endpoint compatibility, deployment templates, runtime reliability.
2. Deterministic generation engine:
   - Repository: `pipeworks-namegen-core`
   - Owner focus: deterministic behavior, package API stability, renderer behavior.
3. Lexicon pipeline and lexicon web flows:
   - Repository: `pipeworks-namegen-lexicon`
   - Owner focus: reproducible lexicon outputs, pipeline reliability, web workflow continuity.
4. Game/service consumer integration:
   - Repository: `pipeworks_mud_server`
   - Owner focus: HTTP client resilience (timeouts/retries/errors) against API contract.

### Contract Check Cadence

1. Per PR in `pipeworks-namegen-api`:
   - Run API contract tests for `/api/generate` behavior.
2. Weekly cross-repo cadence:
   - Validate `pipeworks_mud_server` integration tests against current API baseline.
3. Pre-release cadence for `api` and `core`:
   - Run deterministic baseline checks and contract compatibility checks.
4. Release-note cadence:
   - Keep release-please/conventional commit summaries in each canonical repo.
   - Include cross-repo impact notes when API contract behavior or deterministic output semantics change.

## Archive Action Plan for `pipeworks_name_generation`

Archive can proceed once both are true:

1. Tracker Phase 8 is complete and accepted.
2. No active production dependency remains on this repository runtime surfaces.

Execution steps:

1. Confirm README and transition docs point to canonical repos.
2. Confirm tracker includes links to all migration PRs and merge commits.
3. Archive repository in GitHub (read-only state).
4. Retain tags/history for auditability.
5. Keep top-level README transition notice after archive.

## Canonical References

1. `https://github.com/pipe-works/pipeworks-namegen-lexicon`
2. `https://github.com/pipe-works/pipeworks-namegen-core`
3. `https://github.com/pipe-works/pipeworks-namegen-api`
4. `https://github.com/pipe-works/pipeworks_mud_server`
