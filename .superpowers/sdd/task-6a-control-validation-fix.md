# Task 6A control-validation fix

## 1. Completed action and changed files

Restored control-comparison partition validation for the staged
`heldout_assessed` pipeline.

Changed files:

- `src/creative_writer/source_analysis.py`
- `tests/test_source_analysis.py`
- `.superpowers/sdd/task-6a-control-validation-fix.md`

No real corpus, manuscript, source-study, holdout, control, or unrelated
artefact was opened or changed.

## 2. Implementation notes

- Preserved the existing held-out-only pre-open treatment gate.
- After the Tier 4 control partition is opened, `_validate_record_partitions`
  now validates the combined held-out and control records before metrics or
  validation outputs are built.
- Added a parameterized `heldout_assessed` pipeline matrix for invalid control
  passage, witness, role, tier/partition, and cross-witness passage references.
- Tests spy on the actual `_read_bound_partition` and assert the permitted
  sequence `heldout_wells`, `heldout_wells`, `tier4_controls`; seeded output
  sentinels prove invalid controls do not reach metrics/output generation.
- The complete validation path and its pre-open held-out gate were not changed.

## 3. Verification performed and results

RED before the source change:

```text
uv run pytest tests/test_source_analysis.py -q -k 'invalid_control_comparison_after_control_open'
5 failed, 178 deselected
Failure: malformed control comparisons completed without raising.
```

GREEN and required checks:

```text
uv run pytest tests/test_source_analysis.py -q -k 'invalid_control_comparison_after_control_open'
5 passed, 178 deselected

uv run pytest tests/test_source_analysis.py -q -k 'invalid_control_comparison_after_control_open or validate_heldout_assessed or present_wrong_partition_result_before_opening_controls or blocks_controls_until_every_non_rejected_claim_has_holdout_result or validate_frozen_pass'
10 passed, 173 deselected

uv run pytest tests/test_source_analysis.py -q
183 passed in 40.15s

uv run pytest -q
425 passed in 51.29s

uv run python -m compileall -q src tests
passed

git diff --check
passed
```

## 4. Remaining caveats, assumptions, or justified escalation

The fixture has one Tier 4 witness, so the cross-witness case uses a control
passage combined with a held-out witness passage and is rejected at the
partition-membership check before the later witness-mixing check. This keeps
the pipeline test within the existing fixture and proves the control reference
cannot cross the physical partition boundary.

No escalation is required for the assigned bounded fix.
