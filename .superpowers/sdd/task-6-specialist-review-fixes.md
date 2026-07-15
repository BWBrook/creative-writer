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
