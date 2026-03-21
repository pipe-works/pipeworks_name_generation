Closeout and Archive Plan
=========================

This legacy repository is in transition/meta-only state.

Final architecture ownership:

1. ``pipeworks-namegen-lexicon`` owns the lexicon pipeline and lexicon web UI.
2. ``pipeworks-namegen-core`` owns deterministic generation primitives.
3. ``pipeworks-namegen-api`` owns production runtime and deployment templates.

Hard cutover policy:

1. No long-term legacy compatibility support remains in this repository.
2. Production runtime consumers should use ``pipeworks-namegen-api``.

Cross-repo maintenance cadence:

1. API contract checks run on API PRs.
2. Mud server integration checks run at least weekly and before releases.
3. Deterministic baseline checks run before core/api releases.

Archive runbook:

1. Confirm tracker Phase 8 completion and migration log completeness.
2. Confirm no production deployment points to this repository runtime.
3. Archive this repository in GitHub and retain history/tags.

The detailed closeout record is maintained in ``CLOSEOUT.md`` at repository root.
