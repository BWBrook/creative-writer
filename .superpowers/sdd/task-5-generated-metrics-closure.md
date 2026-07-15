# Wells Phase 2B Task 5 Generated-Metrics Closure

## Outcome

Closed the narrow generated-development-metrics and registry-orchestration
gaps in Task 5. The implementation is in the subsequent closure commit; no
new commit hash is asserted here.

The change is limited to:

- `src/creative_writer/source_analysis.py`
- `src/creative_writer/source_analysis_models.py`
- `src/creative_writer/source_evidence.py`
- `tests/test_source_analysis.py`
- `tests/test_source_analysis_models.py`
- `.superpowers/sdd/task-5-strict-metrics-schema.md`
- `.superpowers/sdd/task-5-closure-fixes.md`
- `.superpowers/sdd/task-5-generated-metrics-closure.md`

No source/manuscript, real holdout, Phase 2C, Permian, or interpretive files
were changed.

## Implementation notes

- Every `develop` run passes explicit current provenance, expected witness
  identities, and independently measured metric records into generated JSON
  validation. Top-level and nested provenance paths/hashes, exact enabled
  measurements, schema/version, witness uniqueness/set membership, identity
  grammar, and exact metric record types/values are checked before profile
  equality work.
- Every generated witness record and the complete development-metrics document
  now pass independent strict Pydantic schemas; candidate heuristics and all
  nested metric containers have explicit contracts.
- The writer return is schema-validated before identity construction, while
  the on-disk JSON uses a duplicate-key rejecting decoder and is schema-
  validated independently before exact comparisons.
- The empty protocol quantitative profile returns only after the generated
  JSON gate succeeds. CSV, metric-reference, and profile-value equality checks
  remain conditional for the genuinely empty protocol template.
- Generated-record comparison is type-exact, so malformed containers such as
  `total_words: []` cannot pass through Python scalar coercion or profile
  exemption paths. Failures still flow through `_post_metric_call`, which
  writes one atomic diagnostics update before raising `CreativeWriterError`.
- The retained `SourcesRegistry` remains the authority input to evidence
  validation. The orchestration companion confirms that a physically
  inconsistent registry is rejected by source-admission/corpus safeguards
  before evidence validation can construct an authority surface from stale
  admission or passage-index identities.
- Pipeline mutations cover the four forbidden locator forms and preserve the
  canonical observation/profile heading while introducing a trailing-space
  duplicate.

## TDD evidence

The retained mutation selector was freshly re-run after the strict schema
closure:

```text
uv run pytest tests/test_source_analysis.py -k 'generated_metrics_mutations_with_empty_protocol_profile or each_forbidden_locator_form or registry_identity_absent_from_retained_registry_at_pipeline_gate' -q
11 passed, 138 deselected
```

The new strict-schema regressions were run RED before the production changes
(`5 failed, 144 deselected`) and then GREEN (`5 passed, 144 deselected`).

The retained malformed-metrics test matrix was preserved, and the broader
closure slice passed:

```text
uv run pytest tests/test_source_analysis.py -k 'develop and (malformed_generated_metrics or empty_protocol_profile or generated_metrics_mutations or each_forbidden_locator_form or registry_identity_absent_from_retained_registry_at_pipeline_gate or trailing_space_duplicate)' -q
14 passed, 125 deselected
```

## Verification

Final verification was run after the documentation edits:

```text
uv run pytest tests/test_source_analysis.py tests/test_source_analysis_models.py -q
204 passed

uv run pytest -q
378 passed in 53.86s

uv run python -m compileall -q src tests
passed (exit 0)

git diff --check
passed (exit 0)
```

## Remaining caveats

Leakage detection remains mechanical: short, edited, paraphrased, or
semantically derived holdout prose remains a human-review risk by design. The
`validate` stage and later candidate-frozen/validated outcome workflow remain
outside Task 5 scope.
