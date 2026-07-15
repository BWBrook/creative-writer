# Phase 2B Task 5 review fixes

## Completed action

Implementation commit `c40052e` fixes the Phase 2B Task 5 review findings within
the assigned source-analysis and evidence-validation surface. The report is
committed separately from the implementation.

## Changed files

- `src/creative_writer/source_evidence.py`
- `src/creative_writer/source_analysis.py`
- `tests/test_source_analysis.py`

`source_analysis_models.py` required no model-schema change: the reviewed
constraints are enforced at the evidence boundary without adding hidden source
roles or interpretation to the models.

## Implementation notes

- Populated observations now require admission and registry authority, verify
  focal and comparison witness roles against the configured dimension, accept
  exact backticked claim bullets, and reject stray prefixes or unknown fields.
- Ledger references preserve identity, source selection, tier, fingerprint,
  holdout, and evidence-role checks with the ledger path in every diagnostic.
  Supporting witnesses individually exercise declared jurisdiction roles and
  all declared roles must be exercised. Counterexample passages and searches
  are role-checked against the claim dimension. Ledger study identity and
  omnibus-dependence content are required.
- Leakage checks cover every tracked evidence artifact plus JSON, CSV, and
  development-report outputs. Witness IDs use boundary-safe matching. Passage
  leakage uses exact full normalized sequences for passages of at least eight
  tokens; partial, edited, or paraphrased text remains a human-review risk.
- Development quantitative profiles require exactly the configured JSON and
  CSV metric references, current hashes, current provenance, an exact witness
  set, nonempty scalar dotted paths, and values equal to the current JSON
  output. Empty protocol profiles remain valid.
- Profile findings use the exact ordered nine-field grammar, require meaningful
  prose and valid claim/dimension links, permit the pre-validation control
  sentinel only where specified, and reject absolute wording during
  development. Candidate and validated completeness checks remain enforced.
- Lifecycle checks compare artifact study identity and stage ordering, allow
  only empty protocol artifacts to lag development, require candidate-frozen
  and validated ledgers/validation records at their corresponding stages, and
  keep `develop` restricted to protocol/development configuration status.
- Diagnostics replace reports atomically using a same-directory temporary file,
  fsync, replace, directory fsync, and rollback handling. Failed validation
  writes counts only and does not expose locators.
- Development dossier topology is derived from retained Tier 1--3 registry
  source IDs, with exactly one dossier per source and no hidden Wells constants.
- Generated-path comparisons canonicalize macOS `/var` and `/private/var`
  aliases without weakening containment checks.

## TDD and verification evidence

The first focused review-regression run was intentionally RED: 12 failures
covered the missing authority arguments, exact metric references, dossier
topology, diagnostics helper, grammar/profile rules, and related review
requirements. The old positive fixtures were then updated only where the new
contract required admission/registry, matching roles, complete profile fields,
or the CSV metric reference.

Verified after implementation:

- `uv run pytest tests/test_source_analysis_models.py tests/test_source_analysis.py -q`
  — **124 passed**.
- Controller-confirmed focused review subset — **113 passed**.
- Controller-confirmed full `pytest` — **298 passed**.
- `uv run python -m compileall -q src tests` — passed.
- `git diff --check` — passed.

The implementation commit is `c40052e`. This report is committed separately
as `Document Task 5 review fixes`.

## Residual limits and scope

Leakage detection cannot prove that short, edited, paraphrased, or semantically
similar prose is not derived from a holdout; those cases remain human-review
risks by design. Task 6 validation, source prose, CLI changes, real holdout
content, and Phase 2C remain outside this Task 5 change.
