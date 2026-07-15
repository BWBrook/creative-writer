# Task 5 closure fixes

## Completed action

Closed the remaining bounded Phase 2B Task 5 bypasses in commit `25c166d`:

- generated development metrics are validated fail-closed on every `develop`
  run, including an empty protocol quantitative-profile template;
- malformed metric containers, provenance, records, and identities produce
  deterministic `ValidationResult` diagnostics before any identity set or
  tuple operation;
- eligible claim witnesses must be explicit retained source or expanded
  selection identities from `SourcesRegistry` and must exercise a declared
  jurisdiction role;
- locator-boundary and trailing-space duplicate-heading behaviour is covered
  through `run_source_analysis` pipeline mutations.

## Changed files

- `src/creative_writer/source_analysis.py`
- `src/creative_writer/source_evidence.py`
- `tests/test_source_analysis.py`
- `.superpowers/sdd/task-5-closure-fixes.md`

No source text, manuscripts, real holdouts, Phase 2C/style artifacts, Permian
planning, or interpretive artifacts were changed.

## Implementation notes

- `develop` now routes quantitative validation through `_post_metric_call`
  unconditionally whenever the canonical quantitative profile is present.
- The generated JSON gate checks the object, scalar/provenance fields,
  schema/version containers, witness list and records, SHA-256 strings, and
  source/selection identity grammar before uniqueness comparisons or profile
  lookups. A selected witness with `selection_id: null` is rejected by the
  identity relationship; `null` remains valid only for a full-work witness.
- Authority indexing starts from retained registry source records and expands
  retained selections explicitly. Admission roles remain available as role
  declarations, but admission or passage-index presence cannot create
  retained authority.
- End-to-end tests mutate generated JSON with a protocol-empty profile,
  remove a retained source while leaving admission/index data present, add a
  forbidden locator with a path prefix, and introduce exact trailing-space
  duplicate observation/profile headings while retaining canonical headings.

## TDD and verification evidence

RED was observed before production edits:

```text
uv run pytest tests/test_source_analysis.py -k 'malformed_generated_metrics_with_empty_protocol_profile or empty_protocol_profile_still_rejects or explicitly_retained_registry_identity or passes_expanded_retained_registry or forbidden_locator_with_prefix_boundary or observation_trailing_space_duplicate_end_to_end or profile_trailing_space_duplicate_end_to_end' -q
8 failed, 3 passed, 122 deselected
```

After the minimal fixes, the targeted closure tests passed:

```text
11 passed, 122 deselected
```

Required verification:

```text
uv run pytest tests/test_source_analysis.py tests/test_source_analysis_models.py -q
186 passed in 39.41s

uv run pytest -q
360 passed in 49.68s

uv run python -m compileall -q src tests
passed (exit 0)

git diff --check
passed (exit 0)
```

## Self-review

- The empty protocol early return occurs only after generated JSON structure,
  provenance, scalar, and identity validation; populated profiles retain the
  existing CSV, fingerprint, value, and witness-set checks.
- Malformed JSON values are rejected before `set(...)` or tuple deduplication;
  the post-metric wrapper converts the raised validation failure into one
  atomic report diagnostic before `CreativeWriterError`.
- Retained authority is derived from the same full-work/selection expansion
  used by the analysis pipeline, while registry-derived fingerprints and
  admission-derived role declarations remain intact.
- Existing source-analysis model, evidence, leakage, observation, profile,
  and full-repository tests remain green.

## Remaining caveats

Leakage detection remains mechanical: short, edited, paraphrased, or
semantically derived holdout prose remains a human-review risk by design. The
`validate` stage and later candidate-frozen/validated outcome workflow remain
outside Task 5 scope.
