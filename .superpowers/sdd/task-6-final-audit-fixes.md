# Task 6 final-audit fixes

Status: DONE

## Commits created

- Pending final commit ID for the verified source/test repair; the report-only follow-up will record the exact IDs.

## RED evidence

- `uv run pytest tests/test_source_analysis_models.py::test_candidate_frozen_validation_requires_candidate_analysis_and_manifest_hashes tests/test_source_validation.py::test_publication_rejects_symlinked_validation_root tests/test_source_validation.py::test_post_swap_parent_fsync_reports_committed_state_and_keeps_new_pointer -q`
  - Result: RED, `3 failed`.
  - Expected failures observed: the existing model accepted a candidate freeze without analysis/manifest hashes; publication followed a symlinked validation root; and post-swap fsync failure was reported only as `Unable to publish validation generation` rather than a committed-state error.

## Focused GREEN evidence

- The same three-test command passed: `3 passed`.
- `uv run pytest tests/test_source_analysis.py::test_yaml_alias_reuse_cannot_escape_the_exact_control_target_path tests/test_source_analysis.py::test_period_controls_require_exact_claim_and_comparison_sections tests/test_source_analysis.py::test_complete_validation_rerun_reuses_the_managed_generation tests/test_source_validation.py -q` passed after the focused repair; the rerun initially exposed and then verified the managed-pointer resolution fix.
- Scoped source-analysis verification: `uv run pytest tests/test_source_validation.py tests/test_source_analysis.py tests/test_source_analysis_models.py -q` -> `257 passed`.

## Full verification

- `uv run pytest -q` -> `438 passed in 56.03s`.
- `uv run python -m compileall -q src tests` -> exit `0`, no output.
- `git diff --check` -> exit `0`.

## Implementation notes

- Candidate freezes now pin and hash `analysis.yml`, `holdouts.yml`, profile, and ledger candidate blobs before parsing; candidate manifest bindings govern corpus-lock and partition access.
- Managed publication requires real directories and the exact relative `current` target, verifies the complete generation before the pointer swap, and reports post-swap parent-fsync failure as committed with uncertain durability.
- Tier 4 authorization is lifecycle-gated; YAML leakage follows composed-node paths including aliases; final period controls are validated from verified `HEAD` bytes.
- The frozen analysis configuration remains pinned while the validation record advances to `validated`, preserving exact candidate blob identity under the amended contract.

## Residual concerns

- None. No real corpus, holdouts, source-study generated artifacts, Wells prose, Phase 2C work, or Permian planning was run or changed.
