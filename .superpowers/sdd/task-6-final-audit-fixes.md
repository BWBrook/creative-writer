# Task 6 final-audit fixes

Status: DONE

## Commits created

- `3c45a09` — verified source/test implementation and regression coverage.
- `6b05528` — report-only commit recording the final-audit evidence.

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

## Specialist-review repair appended 2026-07-16

Status: DONE

### Commits

- `cc3abbb` — specialist-review source repairs and expanded production-boundary tests.
- The report-only commit containing this appended evidence is self-referential; its exact ID is returned in the task status alongside `cc3abbb`.

The adjudication/base commit `50ce74b` clarified the approved candidate/final artifact boundary but was not created by this repair.

### RED evidence

- `uv run pytest tests/test_source_analysis.py::test_yaml_dotted_bracketed_key_cannot_spoof_control_target_path tests/test_source_analysis.py::test_verified_freeze_exposes_no_manifest_or_control_path tests/test_source_analysis.py::test_control_authorization_rereads_pinned_candidate_manifest_after_head_drift tests/test_source_analysis.py::test_final_profile_and_ledger_hashes_precede_final_ledger_parse -q`
  - Result: RED, `5 failed in 3.54s`.
  - Expected failures observed: the dotted/bracketed single key was accepted; `VerifiedFreeze` exposed `manifest_path`; authorization adopted a drifted HEAD control binding; and malformed final-ledger bytes were decoded before both the profile-first and ledger hash mismatch checks.
- `uv run pytest tests/test_source_analysis.py::test_verified_freeze_exposes_no_manifest_or_control_path -q`
  - Result: RED, `1 failed in 0.94s`.
  - Expected failure observed after tightening the capability assertion: the frozen capability still carried Tier 4 witness metadata in `heldout_witnesses`.
- `uv run pytest tests/test_source_analysis.py -q -k 'zero_claim_frozen_production_capability or production_entrypoint_runs_full_committed_validation_lifecycle or final_profile_and_ledger_may_diverge or production_rejects_clean_head_analysis_or_manifest_drift or production_rejects_dirty_or_staged_candidate_path or candidate_commit_shape_and_ancestry or candidate_commit_equal_to_head or candidate_blob_tree_shape or period_control_section_matrix or production_validation_cleans_stale_staging or production_validation_rejects_symlinked_generations or invalid_target_reviewer_and_transition_links'`
  - Result before source changes: `28 passed, 191 deselected in 18.51s`; no RED was expected for these coverage-only cases because they codified already-implemented production behavior.
  - Coverage: zero-claim lifecycle gating, clean candidate/final config and manifest drift, Git trust shapes/path states, final profile/ledger divergence, period-control grammar, stale staging, symlinked `generations/`, and invalid target/reviewer/transition links.

### GREEN evidence

- The five-case RED command above passed: `5 passed in 2.97s`.
- The tightened frozen-capability test passed: `1 passed in 0.79s`.
- Expanded focused matrix: `uv run pytest tests/test_source_analysis.py -q -k 'yaml_dotted_bracketed_key or zero_claim_frozen_production_capability or verified_freeze_exposes_no_manifest or control_authorization_rereads_pinned or production_entrypoint_runs_full_committed_validation_lifecycle or final_profile_and_ledger_may_diverge or final_profile_and_ledger_hashes_precede or production_rejects_clean_head_analysis_or_manifest_drift or production_rejects_dirty_or_staged_candidate_path or candidate_commit_shape_and_ancestry or candidate_commit_equal_to_head or candidate_blob_tree_shape or period_control_section_matrix or production_validation_cleans_stale_staging or production_validation_rejects_symlinked_generations or invalid_target_reviewer_and_transition_links'` -> `33 passed, 186 deselected in 20.79s`.
- A scoped run then exposed a test-only stale module alias: `2 failed, 288 passed in 66.20s`. Replaying the leaking predecessor plus both direct-capability tests after resetting the alias passed: `3 passed in 1.64s`.

### Final verification

- `uv run pytest tests/test_source_validation.py tests/test_source_analysis.py tests/test_source_analysis_models.py -q` -> `290 passed in 66.29s`.
- `uv run pytest -q` -> `471 passed in 78.21s`.
- `uv run python -m compileall -q src tests` -> exit `0`, no output.
- `git diff --check` -> exit `0`, no output.

### Specialist-review regressions covered

- Typed YAML path segments reject flattened-key spoofing while aliases remain checked at each occurrence.
- The genuine frozen capability has no manifest/control path or control binding, contains held-out witness metadata only, rejects zero-claim frozen authorization, and rereads the hash-verified candidate manifest for later authorization.
- Final profile and ledger hashes are checked before decoding/parsing; legitimate final profile/ledger divergence still compares transitions against candidate blobs.
- Separate Git commits traverse frozen -> heldout_assessed -> complete, publish held-out-only first, authorize controls only after assessment, validate final links, and reuse the managed generation.
- Candidate and final analysis/manifest drift, same-count membership swaps, malformed/uppercase/noncommit/equal/nonancestor commits, missing/symlink/gitlink candidate entries, dirty/staged paths, and clean HEAD drift fail through the production entrypoint.
- Missing, extra, duplicate, misassociated, malformed, and empty period-control sections fail through production validation.
- Production stale-staging cleanup, symlinked `generations/` rejection, and representative invalid target/reviewer/transition links are covered.

### Residual concerns

- None. No real corpus, real holdouts, source-study generated artifacts, story prose, Wells interpretation, Phase 2C work, or Permian planning was run or changed.
