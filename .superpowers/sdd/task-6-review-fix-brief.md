# Task 6 specialist-review repair brief

## Inputs

Read these first:

- `.superpowers/sdd/task-6-remediation-contract.md`
- `.superpowers/sdd/task-6-final-audit-fix-brief.md`
- `.superpowers/sdd/task-6-final-audit-fixes.md`

Base the repair on commit `6b05528`. Preserve all existing scope exclusions.
Use TDD for every behavioral repair and commit the result.

## Adjudicated contract point

The approved Phase 2B workflow revises the writer-facing `wells-profile.md` and
`evidence-ledger.yml` during final validation. Therefore:

- `analysis.yml` and `holdouts.yml` must remain byte-identical to their
  candidate-commit blobs at `candidate_frozen`, `heldout_assessed`, and
  `validated/complete`;
- candidate profile and ledger bytes must always be loaded and hash-verified
  from the candidate commit;
- writer-facing profile and ledger must equal the candidate blobs throughout
  `candidate_frozen`, but may differ at `validated/complete` only as strictly
  hash-checked final artifacts whose transitions are validated against the
  candidate objects.

Do not introduce duplicate frozen-profile/ledger files.

## Required fixes

1. Replace flattened YAML path strings with typed path segments. Permit a Tier
   4 witness only for the exact sequence:
   `claims`, list index, `validation_expectation`, `control_targets`, list
   index, `witness_id`. Reject a single dotted/bracketed mapping key that merely
   renders like that sequence. Continue traversing aliases at every occurrence.

2. Make `authorize_control_access` obtain the manifest from the pinned
   candidate Git object, not the current HEAD path. Keep the sealed frozen
   capability free of a control path or binding. It may carry only the
   candidate manifest object ID or sufficient candidate-commit identity to
   reread and reverify the candidate blob inside the authorizer.

3. In final validation, check `final_profile_sha256` and
   `final_ledger_sha256` immediately after reading their verified HEAD blobs,
   before decoding, YAML parsing, or semantic interpretation.

4. Add a real zero-claim production-capability test proving
   `authorize_control_access` fails at `candidate_frozen/frozen` before any
   control read.

5. Add one production-entrypoint test that creates separate Git commits and
   runs the complete sequence:
   `candidate_frozen/frozen -> candidate_frozen/heldout_assessed ->
   validated/complete`. It must exercise held-out-only publication, control
   authorization, final transition validation, and managed-generation reuse.

6. Add focused regressions for:

- the dotted/bracketed single-key YAML spoof;
- candidate-time analysis/manifest drift after freeze, including a
  same-count partition-membership swap;
- final-stage analysis/manifest drift rejection;
- legitimate final profile/ledger divergence with candidate bytes still used
  for transition comparison;
- final profile/ledger hash-before-parse ordering;
- candidate commit shape and trust cases still absent from production tests:
  malformed length, uppercase, noncommit, equal to HEAD, descendant/not an
  ancestor, missing candidate blob, symlink mode, gitlink mode, dirty/staged
  path, and clean HEAD drift;
- missing/extra/duplicate/misassociated/malformed/empty period-control sections;
- stale staging cleanup and symlinked `generations/` rejection;
- representative invalid target, reviewer, and transition links through the
  production validation entrypoint.

Use parametrization and fixture helpers to keep this matrix maintainable. Do
not add tests that merely repeat existing model validators without traversing
the production boundary.

7. Correct `.superpowers/sdd/task-6-final-audit-fixes.md` so it records every
commit and every regression's RED/GREEN evidence. Append this repair's exact
evidence rather than rewriting prior history.

## Verification

Run focused tests during RED/GREEN, then:

- `uv run pytest tests/test_source_validation.py tests/test_source_analysis.py tests/test_source_analysis_models.py -q`
- `uv run pytest -q`
- `uv run python -m compileall -q src tests`
- `git diff --check`

Write the result to `.superpowers/sdd/task-6-specialist-review-fixes.md` with
status, commits, exact RED/GREEN commands/results, full verification summaries,
and concerns. Return only status, commit IDs, one-line full-test result, and
concerns.
