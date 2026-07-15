# Task 6 specialist-review fixes

Status: DONE

## Commits

- `cc3abbb` — specialist-review source repairs and expanded production-boundary tests.
- The report-only commit containing this evidence is self-referential; its exact ID is returned in the task status alongside `cc3abbb`.

Base/adjudication HEAD: `50ce74b`. Prior final-audit commits corrected in the appended history: `3c45a09`, `6b05528`.

## RED evidence

- `uv run pytest tests/test_source_analysis.py::test_yaml_dotted_bracketed_key_cannot_spoof_control_target_path tests/test_source_analysis.py::test_verified_freeze_exposes_no_manifest_or_control_path tests/test_source_analysis.py::test_control_authorization_rereads_pinned_candidate_manifest_after_head_drift tests/test_source_analysis.py::test_final_profile_and_ledger_hashes_precede_final_ledger_parse -q`
  - Result: `5 failed in 3.54s`.
  - Expected failures: flattened YAML key spoof accepted; frozen capability exposed a manifest path; authorizer used a drifted HEAD control binding; final malformed-ledger bytes were decoded before the profile-first and ledger hash checks.
- `uv run pytest tests/test_source_analysis.py::test_verified_freeze_exposes_no_manifest_or_control_path -q`
  - Result: `1 failed in 0.94s`.
  - Expected failure: `heldout_witnesses` still included the Tier 4 witness.
- `uv run pytest tests/test_source_analysis.py -q -k 'zero_claim_frozen_production_capability or production_entrypoint_runs_full_committed_validation_lifecycle or final_profile_and_ledger_may_diverge or production_rejects_clean_head_analysis_or_manifest_drift or production_rejects_dirty_or_staged_candidate_path or candidate_commit_shape_and_ancestry or candidate_commit_equal_to_head or candidate_blob_tree_shape or period_control_section_matrix or production_validation_cleans_stale_staging or production_validation_rejects_symlinked_generations or invalid_target_reviewer_and_transition_links'` -> `28 passed, 191 deselected in 18.51s` before source changes. These coverage-only tests intentionally codified existing production behavior and therefore required no source RED.

## Focused GREEN evidence

- The five-case RED command passed: `5 passed in 2.97s`.
- Tightened capability-surface test: `1 passed in 0.79s`.
- Expanded focused matrix: `uv run pytest tests/test_source_analysis.py -q -k 'yaml_dotted_bracketed_key or zero_claim_frozen_production_capability or verified_freeze_exposes_no_manifest or control_authorization_rereads_pinned or production_entrypoint_runs_full_committed_validation_lifecycle or final_profile_and_ledger_may_diverge or final_profile_and_ledger_hashes_precede or production_rejects_clean_head_analysis_or_manifest_drift or production_rejects_dirty_or_staged_candidate_path or candidate_commit_shape_and_ancestry or candidate_commit_equal_to_head or candidate_blob_tree_shape or period_control_section_matrix or production_validation_cleans_stale_staging or production_validation_rejects_symlinked_generations or invalid_target_reviewer_and_transition_links'` -> `33 passed, 186 deselected in 20.79s`.
- Test-isolation correction replay: `uv run pytest tests/test_source_analysis.py::test_validate_candidate_preflight_rejects_unreachable_commit_without_quarantine_read tests/test_source_analysis.py::test_zero_claim_frozen_production_capability_cannot_authorize_controls tests/test_source_analysis.py::test_control_authorization_rereads_pinned_candidate_manifest_after_head_drift -q` -> `3 passed in 1.64s`.

## Full verification

- `uv run pytest tests/test_source_validation.py tests/test_source_analysis.py tests/test_source_analysis_models.py -q` -> `290 passed in 66.29s`.
- `uv run pytest -q` -> `471 passed in 78.21s`.
- `uv run python -m compileall -q src tests` -> exit `0`, no output.
- `git diff --check` -> exit `0`, no output.

## Implementation summary

- YAML leakage traversal now uses typed mapping/list path segments, so a flattened dotted/bracketed key cannot impersonate the sole allowed control-target path; aliases are still visited at each occurrence.
- `VerifiedFreeze` carries only held-out witness metadata and no manifest/control path or control binding. Control authorization rereads and hash-verifies `holdouts.yml` from the pinned candidate Git commit.
- Final profile and ledger hashes are checked immediately after their verified HEAD blob reads and before final-ledger decoding or semantic validation.
- Production tests cover zero-claim premature authorization; the committed frozen -> heldout_assessed -> complete lifecycle; candidate/final config and same-count manifest drift; final candidate/final profile-ledger boundaries; Git commit/tree/worktree trust cases; the full period-control section matrix; stale staging and symlinked `generations/`; and representative target/reviewer/transition failures.

## Concerns

- None. The repair did not run or alter the real corpus, create real holdouts, touch real source-study/story artifacts, interpret Wells prose, implement Phase 2C, or plan the Permian story.

## Bounded TDD follow-up appended 2026-07-16

Status: DONE

### Commits

- `5d61e4f` — node-identity-aware Tier 4 leakage accounting and publication-boundary regressions.
- The report-only commit containing this appended evidence is self-referential; its exact ID is returned in the task status alongside `5d61e4f`.

### RED evidence

- `uv run pytest tests/test_source_analysis.py::test_yaml_alias_at_two_exact_control_target_paths_counts_one_lexical_scalar tests/test_source_analysis.py::test_yaml_alias_reuse_cannot_escape_the_exact_control_target_path tests/test_source_analysis.py::test_yaml_dotted_bracketed_key_cannot_spoof_control_target_path tests/test_source_validation.py::test_concurrent_readers_observe_only_complete_old_or_new_generations tests/test_source_validation.py::test_existing_generation_current_swap_failure_preserves_old_pointer_and_retries -q`
  - Result: `1 failed, 4 passed in 0.31s`.
  - Expected failure: one anchored Tier 4 witness scalar aliased at a second exact allowed control-target path was rejected because raw lexical occurrences were reconciled against path occurrences instead of unique composed scalar nodes.
  - Preservation and publication evidence already passed RED: an alias occurrence at a disallowed path and a dotted/bracketed key remained rejected; real concurrent publication exposed only complete snapshots; and injected `os.replace(temp_current, validation/current)` failure preserved the old pointer and allowed generation reuse.

### GREEN evidence

- The exact five-test RED command above passed: `5 passed in 0.17s`.
- YAML traversal continues to authorize every occurrence using its typed path, while raw-text reconciliation now counts each composed scalar node identity once.
- The concurrent readers and publisher are barrier-controlled, all thread futures are resolved in the test thread, and observations are asserted to equal the complete old or complete new byte mapping only.
- The direct pointer-swap failure test verifies old-current preservation, `.current-*` cleanup, retention of the complete new generation, and successful identical retry with the same generation ID.

### Final verification

- `uv run pytest tests/test_source_validation.py tests/test_source_analysis.py -q` -> `231 passed in 65.39s (0:01:05)`.
- `uv run pytest -q` -> `474 passed in 77.40s (0:01:17)`.
- `uv run python -m compileall -q src tests` -> exit `0`, no output.
- `git diff --check` -> exit `0`, no output.

### Follow-up concerns

- None. Only the three authorized source/test files and these two evidence reports were changed; no real corpus, holdouts, generated source-study/story artifacts, Wells prose, Phase 2C work, or Permian planning was touched or run.
