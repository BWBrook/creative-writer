# Phase 2B Task 4 final-fixes re-review report

## Completed action

Closed the final Phase 2B Task 4 re-review findings in implementation commit
`e596b56` (`fix: preserve failed metric rollback backups`). The report is
committed separately from the implementation.

No real holdouts, story artifacts, prose, or Phase 2C work were changed.

## RED/GREEN evidence

- RED: the two new focused regressions failed as intended. The punctuation
  regression found the unwanted `denominator_words: 1000.0` entry in
  `per_1000_words`; the adversarial rollback regression found zero residual
  `.bak` files after a forced third-install failure followed by a forced
  restoration failure.
- Focused GREEN: `uv run pytest -q tests/test_source_metrics.py::test_punctuation_events_reset_at_passage_boundaries_and_report_rates tests/test_source_metrics.py::test_metric_rollback_keeps_backup_when_restoration_fails`
  passed, `2 passed`.
- Source-metrics/source-analysis GREEN:
  `uv run pytest -q tests/test_source_metrics.py tests/test_source_analysis.py`
  passed, `49 passed`.
- Full GREEN: `uv run pytest -q` passed, `257 passed`.
- `uv run python -m compileall -q src tests` passed.
- `git diff --check` and post-commit `git diff --check HEAD^ HEAD` passed.

## Defects closed

- Metric artifact rollback now preserves any backup whose restoration fails.
  The restoration error and exact residual backup path are aggregated into
  `CreativeWriterError`; backups successfully restored or superseded are the
  only backups eligible for cleanup. Recoverable artifacts are restored and
  staged temporary files are cleaned.
- Punctuation `per_1000_words` rates now exclude the numeric
  `denominator_words` metadata field while retaining every actual punctuation
  count and derived punctuation-family rate.

## Changed files in implementation commit `e596b56`

- `src/creative_writer/source_metrics.py`
  - excluded `denominator_words` from punctuation rates;
  - aligned metric-artifact rollback cleanup and residual reporting with the
    proven `source_analysis._commit_staged` semantics.
- `tests/test_source_metrics.py`
  - added the exact punctuation-rate regression;
  - added the adversarial third-install/restoration-failure regression.

## Residual approximation risks

- Sentence counts remain a transparent Victorian-text approximation. Initials
  at sentence starts, deliberately lower-case prose after full stops, nested
  quotations, and editorially irregular punctuation can still be
  misclassified.
- Dialogue remains structural and quote-span based. Quoted thoughts, several
  speakers in one paragraph, and unpaired or irregular quotes can remain
  uncertain; unknown passages contribute zero dialogue words while remaining
  in the denominator.
- Exact-code-point punctuation counts describe the supplied text and do not
  resolve editorial intent. ASCII ellipses, quote variants, dash variants,
  and normalization artifacts retain their declared approximation rules.
- Moving-window concentration and candidate flags are diagnostic sampling
  aids, not literary findings. Interpretation and observation-to-explanation
  movement remain deferred to human close reading.
- The real Wells `develop` stage remains gated by its committed story-local
  holdout manifest; this repair does not run or create real holdouts.
