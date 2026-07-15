# Task 5 final re-review fixes

## Completed action

Implemented the bounded second Task 5 remediation for protocol validation,
profile grammar, quantitative CSV identity/provenance, passage-ID leakage
coverage, and post-metric diagnostics. No schema, source text, manuscript,
holdout, Phase 2C/style, Permian planning, or interpretive artifact was
changed.

## Changed files

- `src/creative_writer/source_analysis.py`
- `src/creative_writer/source_evidence.py`
- `tests/test_source_analysis.py`
- `.superpowers/sdd/task-5-final-rereview-fixes.md`

## Implementation notes

- Protocol-stage validation now requires the four exact placeholder summaries,
  absent freeze/final hashes, empty transitions, and the exact currently tracked
  protocol Markdown body. Body comparison normalizes only CRLF/CR line endings
  and a missing final newline. The parsed body is passed into lifecycle
  validation, and validation-document read failures use the atomic diagnostic
  path.
- Profile findings reject any nonblank pre-field content, unexpected headings,
  and rogue record prose anywhere inside a finding while retaining the exact
  protocol placeholder path.
- Quantitative validation canonicalizes JSON and CSV paths relative to the
  repository root, binds the supplied CSV path to the configured generated
  output, and compares unique `(witness_id, source_id, selection_id)` identity
  sets across CSV rows, JSON metrics, and quantitative-profile witnesses. It
  rejects duplicate JSON/profile identities and duplicate complete CSV rows,
  as well as missing, extra, or mismatched identities even after fingerprints
  are refreshed.
- Pipeline tests now mutate a tracked artifact and a generated artifact with a
  forbidden passage ID, and mutate validation read/schema plus observation and
  profile grammar inputs while asserting deterministic atomic diagnostics.
- Synthetic fixtures use a non-semantic Tier 4 ID (`tier-four`) so the exact
  canonical validation prose word “control” is not misclassified as a witness
  identifier by the mechanical leakage test.

## TDD and verification evidence

Focused adversarial tests were added before production edits and run RED:

```text
uv run pytest tests/test_source_analysis.py -k 'substantive_protocol_validation_mutations or protocol_validation_body_that_changes_only_line_content or rogue_record_heading or exact_csv_json_profile_identity_sets or csv_path_outside_configured or validation_schema_or_read_fails or profile_or_observation_grammar_fails or pipeline_rejects_holdout_passage_id' -q
13 failed, 5 passed, 94 deselected in 8.57s
```

The RED failures were the intended protocol lifecycle, rogue profile-heading,
CSV configured-path/identity, and diagnostics/leakage assertions. The passing
cases were coverage already satisfied by the existing implementation.

The same focused adversarial command after the production edits passed:

```text
18 passed, 95 deselected in 8.12s
```

Final verification:

```text
uv run pytest tests/test_source_analysis.py tests/test_source_analysis_models.py -q
166 passed in 28.95s

uv run pytest -q
340 passed in 38.14s

uv run python -m compileall -q src tests
passed (exit 0)

git diff --check
passed (exit 0)
```

## Remaining caveats

The canonical protocol body is intentionally pinned in the lifecycle gate to
the body currently tracked by `stories/time-expedition/source-study/validation.md`;
future intentional edits to that protocol artifact require a corresponding
gate/test update. Leakage detection remains mechanical: short, edited,
paraphrased, or semantically derived holdout prose remains a human-review risk.
The `validate` stage and final held-out/control outcome workflow remain outside
Task 5 scope.
