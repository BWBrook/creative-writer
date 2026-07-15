# Task 6 final-audit repair brief

## Context

This is a bounded repair of Phase 2B Task 6. Read first:

- `.superpowers/sdd/task-6-remediation-contract.md`
- `docs/superpowers/specs/2026-07-15-wells-phase-2b-detailed-analysis-design.md`
- `docs/superpowers/plans/2026-07-15-wells-phase-2b-detailed-analysis.md`

The current implementation is at commit `9c8decd`. Preserve the physical
development/held-out/control partition design. Do not run the real corpus,
create the real `holdouts.yml`, interpret source prose, implement Phase 2C, or
plan the Permian story.

Use strict test-driven development: add a focused regression test, run it and
record the expected failure, implement the smallest coherent repair, and run
the focused test again. Finish with the complete test suite, compile check, and
`git diff --check`.

## Required repairs

### 1. Freeze candidate-time methodology and manifest

Extend the strict validation record so a candidate freeze records exact
SHA-256 values for the candidate-commit `analysis.yml` and `holdouts.yml`, in
addition to profile and ledger. At `candidate_frozen` and later:

- read all four candidate files from verified Git blob IDs;
- hash each blob before parsing it;
- require each clean `HEAD` blob ID to equal its candidate blob ID;
- use the candidate manifest as the authority for corpus-lock and partition
  bytes;
- reject a post-freeze analysis/manifest or partition-membership swap even when
  witness counts remain unchanged.

Check a recorded ledger hash before parsing its body.

### 2. Resolve the managed current pointer safely

Permit only the managed `validation/current` symlink with exact relative target
`generations/<64-lowercase-hex>`. Require real, nonsymlinked `validation/` and
`validation/generations/` directories and a real generation directory. Verify
its generation manifest before returning any file. Reject absolute targets,
other relative shapes, symlinked parents, and symlinked generation paths. A
second identical run through `run_source_analysis` must succeed and reuse the
generation.

### 3. Gate control authorization by lifecycle step

`authorize_control_access` must reject `candidate_frozen`, including a
zero-claim candidate. Only `heldout_assessed` and `complete` may mint
`VerifiedControlAccess`, after complete held-out treatment validation.

### 4. Enforce structural YAML leakage paths

Use the composed YAML node graph and track the path of every occurrence. A Tier
4 witness ID is permitted only at
`claims[i].validation_expectation.control_targets[j].witness_id`. YAML aliases
must be rechecked at every occurrence so an allowed anchor cannot legalize a
disallowed alias. Retain the existing generic frozen-output leakage checks.

### 5. Validate final period-control notes

Define and enforce this Markdown grammar:

- first heading: `# Period Controls`;
- one ``## Claim `<claim-id>` `` for every claim with control comparisons;
- under it, one ``### Comparison `<comparison-id>` `` for each comparison
  belonging to that claim;
- every comparison subsection has non-whitespace prose before the next
  heading;
- exact sets only: reject duplicate, missing, extra, misassociated, malformed,
  or empty sections.

Read final tracked bytes from verified `HEAD` blobs.

### 6. Make publication commit semantics truthful

Reject symlinked publication parents before writing. Complete every fallible
integrity check before the atomic `current` swap. Treat `os.replace` of
`current` as the commit point. If only the parent fsync fails afterward, raise
a dedicated committed-state exception whose message states that `current`
advanced and durability is uncertain; do not claim rollback. Pre-swap failures
remove staging and preserve the old pointer. Identical reruns verify and reuse
the generation.

### 7. Complete the negative/recovery matrix

Add production-path tests, not helper-only tests, for:

- second identical `run_source_analysis` invocation;
- stale staging cleanup;
- pre-pointer failures at publication boundaries;
- post-swap fsync failure and pointer state;
- concurrent pinned readers observing only old or new complete generations;
- real capability authorization, including zero-claim premature control;
- full committed `candidate_frozen -> heldout_assessed -> complete` lifecycle;
- malformed, short, uppercase, noncommit, equal, unreachable, descendant
  candidate commits;
- missing, symlink, gitlink, dirty, staged, and drifted candidate files;
- invalid target, reviewer, and transition links;
- candidate manifest/config drift and YAML anchor/alias escape;
- period-control missing/extra/empty/misassociated sections.

Prefer parametrized tests and existing fixtures to avoid repetitive setup.

## Owned files

- `src/creative_writer/source_validation.py`
- `src/creative_writer/source_analysis_common.py`
- `src/creative_writer/source_analysis_models.py`
- `src/creative_writer/source_evidence.py`
- `tests/test_source_validation.py`
- `tests/test_source_analysis.py`
- `tests/test_source_analysis_models.py`
- other directly related test helpers when necessary
- `.superpowers/sdd/task-6-final-audit-fixes.md`

Do not edit real generated source-study artifacts or story prose.

## Report contract

Write `.superpowers/sdd/task-6-final-audit-fixes.md` containing:

- status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`;
- commits created;
- each regression test's RED command and expected failure;
- focused GREEN commands and results;
- full verification commands and exact summaries;
- any residual concerns.

Return only status, commit IDs, a one-line full-test summary, and concerns.
