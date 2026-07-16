# Phase 2B Task 7 report

Status: complete

Implementation commit: `97a7693` (`Implement Phase 2B source-analysis CLI`)

## RED evidence

Before wiring the interface, the new CLI tests failed as expected:

- `uv run pytest tests/test_source_analysis.py -k 'source_analysis_cli' -q`
- Result: 10 failed, 1 passed, 220 deselected.
- Failures were the absent `source-analysis` parser command and absent CLI
  dispatch hook; the existing unsupported-stage test still passed.

## GREEN evidence

After adding the parser, dispatch, output reporting, Make target, and tests:

- `uv run pytest tests/test_source_analysis.py -k 'source_analysis_cli' -q`
- Result: 11 passed, 220 deselected.

The synthetic Git-backed test exercised public `cli.main` through prepare,
develop, candidate-frozen held-out-only validation, held-out-assessed control
validation, and complete final validation. It confirmed generation reporting,
held-out/control separation, final report compilation, and the Phase 2C stop
boundary.

## Verification

- `uv run pytest tests/test_source_analysis.py -q`: 231 passed in 73.35s.
- `uv run creative-writer source-analysis --help`: exit 0; showed required
  `--story` and `{prepare,develop,validate}` stage choices.
- `make -n source-analysis STORY=time-expedition STAGE=prepare`: exit 0;
  expanded to `uv run creative-writer source-analysis --story
  "time-expedition" --stage "prepare"`.
- `uv run pytest -q`: 485 passed in 80.96s.
- `uv run python -m compileall -q src tests`: exit 0.
- `git diff --check`: exit 0 before implementation commit.

## Concerns and scope boundary

No blocking concerns. Per the task contract, the real `time-expedition`
prepare stage was not run, no real holdouts were created, no source prose was
interpreted, and no Phase 2C or Permian work was entered. The report is
committed separately from the implementation.

## Blocking-review lifecycle correction (2026-07-16)

Status: complete

Implementation commit: `4c7e57a` (`Fix held-out control authorization lifecycle`)

### RED evidence

- `uv run pytest tests/test_source_analysis.py -k 'public_cli_heldout_assessed or premature_final_records' -q`
- Result before the production change: 4 failed, 226 deselected in 3.80s.
- The public CLI failed the held-out-only `heldout_assessed` record by demanding
  control target results, and the three premature final-record variants were
  not rejected before partition access.

### GREEN and regression evidence

- The same focused command: 4 passed, 226 deselected in 3.15s.
- `uv run pytest tests/test_source_analysis.py -k 'frozen_pass or heldout_assessed or source_analysis_cli_runs_complete or full_committed_validation_lifecycle or compiles_qualified_final or complete_validation_rerun' -q`:
  11 passed, 219 deselected in 11.53s.
- `uv run pytest tests/test_source_analysis.py tests/test_source_validation.py -q`:
  241 passed in 74.69s.
- `uv run pytest -q`: 484 passed in 87.71s.
- `uv run creative-writer source-analysis --help`: exit 0; retained required
  `--story` and `{prepare,develop,validate}` stage choices.
- `make -n source-analysis STORY=time-expedition STAGE=prepare`: exit 0;
  expanded to `uv run creative-writer source-analysis --story
  "time-expedition" --stage "prepare"`.
- `uv run python -m compileall -q src tests`: exit 0.
- `git diff --check`: exit 0 before the implementation commit.

The corrected public lifecycle now commits exact held-out results with empty
control comparisons, reviewer records, and transitions; the
`heldout_assessed` invocation alone opens Tier 4 and publishes the
control-inclusive packet; final records are authored afterward and required
only by `validated/complete`.

No blocking concerns remain. The real corpus and deferred Phase 2C/Permian
scope were not opened or run.
