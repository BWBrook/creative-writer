# Phase 2B Task 5 final hardening

## Completed action

Implemented the final bounded Phase 2B Task 5 hardening for chronology,
recursive evidence topology, identifier boundaries, Markdown grammar,
quantitative JSON validation, and eligible-witness authority. No source text,
manuscript, real holdout, Phase 2C/style guidance, Permian planning, or real
interpretive artifact was changed.

## Changed files

- `src/creative_writer/source_analysis.py`
- `src/creative_writer/source_evidence.py`
- `tests/test_source_analysis.py`
- `.superpowers/sdd/task-5-sol-max-fixes.md`

## Implementation notes

- Protocol and development configurations now require `validation.md` to
  remain at the sealed protocol stage. The existing exact summaries, empty
  transitions, null freeze/final hashes, and canonical body checks remain
  enforced. Candidate-frozen and validated lifecycle contracts were not
  changed.
- Observation dossier inventory, topology checks, observation validation, and
  leakage scanning now recurse through Markdown beneath `source-study/observations`.
  Registry-derived flat dossier paths remain the only expected paths; nested or
  extra Markdown is blocking and is still scanned for forbidden IDs and text.
- Forbidden witness and passage IDs now use only ASCII alphanumeric,
  underscore, and hyphen as continuation characters, so colon/slash locator
  punctuation is detected while identifier prefixes remain safe.
- Markdown ATX headings are normalized for trailing spaces during semantic
  parsing, then noncanonical spellings and duplicate profile dimensions are
  rejected deterministically across observation and profile record regions.
- Generated quantitative JSON is checked for the required object, witness-list,
  witness-record, and provenance containers before any `.get` access. The
  quantitative validator now runs through the atomic post-metric diagnostic
  wrapper, including malformed generated JSON failures.
- Every eligible claim witness must be retained and exercise at least one role
  declared by that claim's jurisdiction.

## TDD and verification evidence

Focused RED, before production edits:

```text
uv run pytest tests/test_source_analysis.py -k 'protocol_validation_seal or recursively_scans_nested or id_boundaries or observation_heading_trailing or profile_heading_trailing or malformed_generated_json or eligible_witness_must' -q
7 failed, 2 passed, 113 deselected in 3.65s
```

Focused GREEN after production edits:

```text
uv run pytest tests/test_source_analysis.py -k 'protocol_validation_seal or recursively_scans_nested or id_boundaries or observation_heading_trailing or profile_heading_trailing or malformed_generated_json or eligible_witness_must' -q
9 passed, 113 deselected in 3.46s
```

Requested verification:

```text
uv run pytest tests/test_source_analysis.py tests/test_source_analysis_models.py -q
175 passed in 31.93s

uv run pytest -q
349 passed in 42.00s

uv run python -m compileall -q src tests
passed (exit 0)

git diff --check
passed (exit 0)
```

## Remaining caveats

Leakage detection remains mechanical: short, edited, paraphrased, or
semantically derived holdout prose remains a human-review risk. The `validate`
stage and later candidate-frozen/validated outcome workflow remain outside
Task 5 scope.
