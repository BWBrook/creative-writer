# Wells Phase 2B Task 5 Generated-Metrics Closure

## Outcome

Closed the narrow generated-development-metrics and registry-orchestration
gaps in Task 5. The implementation is in the subsequent closure commit; no
new commit hash is asserted here.

The change is limited to:

- `src/creative_writer/source_analysis.py`
- `src/creative_writer/source_evidence.py`
- `tests/test_source_analysis.py`
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

The new mutation tests were run RED before the production changes:

```text
uv run pytest tests/test_source_analysis.py -k 'generated_metrics_mutations_with_empty_protocol_profile or each_forbidden_locator_form or registry_identity_absent_from_retained_registry_at_pipeline_gate' -q
6 failed, 5 passed, 128 deselected
```

After the implementation, the same focused command was GREEN:

```text
11 passed, 128 deselected
```

The retained prior malformed-metrics test matrix was preserved, and the
broader closure slice passed:

```text
uv run pytest tests/test_source_analysis.py -k 'develop and (malformed_generated_metrics or empty_protocol_profile or generated_metrics_mutations or each_forbidden_locator_form or registry_identity_absent_from_retained_registry_at_pipeline_gate or trailing_space_duplicate)' -q
14 passed, 125 deselected
```

## Verification

Final verification was run after the documentation edits:

```text
uv run pytest tests/test_source_analysis.py tests/test_source_analysis_models.py -q
197 passed in 41.32s

uv run pytest -q
371 passed in 51.65s

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
