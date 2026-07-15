# Task 5 handler coverage closure

## Completed action

Added three genuine `run_source_analysis(..., "develop")` orchestration tests
covering post-metric failures from:

- truncated/invalid generated metrics JSON;
- a non-list `measure_development` return after plausible artifacts are written;
- an empty `measure_development` return after plausible artifacts are written.

The tests assert `CreativeWriterError`, deterministic atomic diagnostics in
`development-report.md`, and the absence of raw `JSONDecodeError`, `TypeError`,
or `ValueError` propagation.

## Changed files

- `tests/test_source_analysis.py`
- `.superpowers/sdd/task-5-handler-coverage.md`

No production files were changed.

## RED/coverage-only result

The three tests immediately passed on the existing handlers. This is a
coverage-only addition, not a fabricated RED/GREEN production fix: the current
`_post_metric_call` wrapper already converts these failure classes to
`CreativeWriterError` and atomically writes the diagnostics report.

## Verification

The exact coverage command passed immediately, confirming coverage-only status:

```text
uv run pytest tests/test_source_analysis.py -k 'run_source_analysis_converts_truncated_metrics_json_to_atomic_diagnostics or run_source_analysis_converts_non_list_metrics_return_to_atomic_diagnostics or run_source_analysis_converts_empty_metrics_return_to_atomic_diagnostics' -q
3 passed, 149 deselected in 1.63s
```

Source/model suite:

```text
uv run pytest tests/test_source_analysis.py tests/test_source_analysis_models.py -q
207 passed in 45.27s
```

Full suite:

```text
uv run pytest -q
381 passed in 56.67s
```

Additional checks:

```text
uv run python -m compileall -q src tests
exit 0

git diff --check
exit 0
```
