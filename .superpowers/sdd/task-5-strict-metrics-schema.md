# Task 5 strict generated-metrics schema closure

## Completed action

Closed the remaining generated-development-metrics architecture gap with
independent strict Pydantic 2 schemas and fail-closed JSON decoding. The
change remains limited to the assigned source-analysis validation surface;
source text, manuscripts, real holdouts, Phase 2C, Permian, and interpretive
artifacts were not changed.

## Implementation notes

- `WitnessMetricRecord` explicitly contracts every field emitted by
  `WitnessMetrics.to_dict`, including nested distributions, punctuation,
  lexicon maps, section summaries, concentration windows, block proportions,
  and candidate flags. Numeric fields use strict numeric types and all models
  forbid extra fields.
- `GeneratedDevelopmentMetrics` explicitly contracts provenance, enabled
  measurements, and the candidate-heuristics object. The deferred
  observation-to-explanation movement has a fixed status and canonical reason.
- The writer return is serialized and schema-validated before any identity
  tuple/set construction. The on-disk document is parsed with a recursive
  duplicate-key rejecting decoder and independently schema-validated before
  exact provenance and current-output comparisons.
- JSON decoding, duplicate keys, Unicode/OSError, recursion, validation, and
  type failures become deterministic validation issues. `_post_metric_call`
  atomically replaces diagnostics before converting bounded failures to
  `CreativeWriterError`.

## TDD evidence

The new run-source-analysis regressions were observed RED before the strict
implementation:

```text
5 failed, 144 deselected
```

After implementation, the focused regressions passed:

```text
5 passed, 144 deselected
```

The model/source-analysis suites passed:

```text
204 passed
```

## Verification

The repository-wide suite passed:

```text
378 passed in 53.86s
```

Additional required compile and diff checks are recorded in the final task
handoff after the documentation edits.

## Remaining caveats

The schema validates the emitted metric contract and preserves the existing
exact-output/provenance gate; it does not change the scientific meaning or
interpretive status of any metric. Later validation and candidate-frozen or
validated workflows remain outside Task 5 scope.
