# Wells Phase 2B Task 3 Report: Corpus Lock, Holdouts, and Prepare

## Outcome

Implemented the Phase 2B Task 3 `prepare` orchestration without modifying the
CLI, Makefile, source registries, retained witnesses, study protocol/evidence
files, styles, plans, or manuscripts. The real tracked `holdouts.yml` was not
created because the task scope explicitly reserves it for Task 8; temporary
synthetic fixtures and a temporary copy of the real corpus were used instead.

Implementation and test commit:

`3c570f1` (`feat: prepare deterministic source analysis corpus`)

This report is committed separately after the implementation/tests commit.

## TDD record

### RED

I added `tests/test_source_analysis.py` before creating
`src/creative_writer/source_analysis.py`. The mandated focused command failed
at collection with the expected missing-interface error:

```text
uv run pytest tests/test_source_analysis.py -k 'prepare or holdout or corpus_lock' -q
ModuleNotFoundError: No module named 'creative_writer.source_analysis'
```

### GREEN

The focused suite reached 16 passing tests after the implementation. It covers
the synthetic real-Pandoc corpus, exact lock fields and counts, selection
expansion/order, hash ranking, round-half-up counts, tertile coverage, tie
order, whole-work holdout, Tier 4 quarantine, deterministic rerun behavior,
registry/source drift, duplicate/unresolved passages, empty output, and atomic
preservation.

## Files changed

### `src/creative_writer/source_analysis.py`

- Added `run_source_analysis(root, slug, stage)` with `prepare` support and
  clear unsupported-stage errors for `develop` and `validate`.
- Runs source admission first, then strictly loads `analysis.yml` and verifies
  both declared registry SHA-256 values before Pandoc parsing.
- Expands retained full works and selected short-fiction selections in
  registry order and assigns contiguous global witness ordinals.
- Builds a timestamp-free, strictly validated corpus lock containing study
  identity, registry fingerprints, authority/usage fields, EPUB and Markdown
  fingerprints, witness identities, Tier 5 exclusions, and exact counts.
- Selects heading-bounded windows deterministically with the prescribed
  SHA-256 key, round-half-up holdout count, tertile coverage, tie order, and
  globally unique window IDs; Tier 4 remains in the index/lock but receives no
  partition record.
- Creates or semantically verifies `holdouts.yml`, preserving a valid existing
  file and its original UTC timestamp.
- Validates all payloads before output and stages/replaces generated artifacts
  transactionally with rollback on replacement failure.

### `src/creative_writer/source_analysis_models.py`

Added strict corpus-lock models for analysis identity, retained source
fingerprints, expanded witness fingerprints, exact count summaries, and the
timestamp-free lock document.

### `src/creative_writer/source_passages.py`

Added deterministic validated passage-index serialization so orchestration can
fully validate the JSONL payload before atomic output while preserving the
existing writer/reader behavior.

### `tests/test_source_analysis.py`

Added a synthetic Phase 2A-compatible two-Wells/one-control fixture with real
Pandoc parsing and focused failure-preservation tests.

## Verification

Focused tests:

```text
uv run pytest tests/test_source_analysis.py -q
16 passed
```

Related source-analysis/model/passage/admission tests:

```text
uv run pytest tests/test_source_analysis_models.py tests/test_source_passages.py \
  tests/test_source_admission.py tests/test_source_analysis.py -q
133 passed
```

Full suite and mechanical checks:

```text
uv run pytest -q
217 passed in 15.03s
python3 -m compileall -q src tests
git diff --check
```

A temporary copy of the real `time-expedition` corpus completed `prepare`
through Pandoc with:

```text
witnesses=15
passages=12541
admission_records=13
retained_sources=12
retained_epubs=12
retained_markdown=15
holdout source fingerprints=27
```

The temporary copy's second `prepare` returned `holdout_manifest_created=False`
and `holdout_manifest_verified=True`. No generated artifact or tracked file was
written in the real checkout.

## Implementation decisions

1. `holdouts.yml` uses `source/<source-id>/epub` and
   `witness/<witness-id>/markdown` keys so EPUB and expanded Markdown
   fingerprints cannot collide.
2. The corpus lock stores retained sources in declared registry order and
   witnesses in expanded reading order. Its JSON has no timestamp.
3. Existing generated lock/index bytes are compared with the newly validated
   payload before any replacement. Existing holdouts are model-compared using
   their original `created_at` and are never rewritten when valid.
4. The passage serializer is shared with the existing index writer so Task 3's
   pre-output validation does not create a second JSONL encoding.
5. The package version (`creative-writer 0.1.0`) is recorded as the tool
   version for newly created holdout manifests.

## Self-review against the brief

- [x] Admission is the first `prepare` operation and blocks all analysis
  outputs on errors.
- [x] Strict analysis configuration and both registry hashes are checked before
  retained Markdown parsing.
- [x] Full-work and selected-short-fiction witness expansion preserves registry
  and selection order with contiguous global ordinals.
- [x] Corpus lock includes authority/usage fields, all retained EPUB and
  expanded Markdown fingerprints, Tier 5 exclusions, and exact counts without
  a timestamp.
- [x] Holdout fingerprint keys, whole-work holdout, deterministic within-work
  partitioning, Tier 4 quarantine, window IDs, and rerun immutability are
  implemented and tested.
- [x] Duplicate, stale/unresolved, empty, drift, changed-manifest, and output
  replacement failures are blocking and preserve existing artifacts.
- [x] Focused, related, full-suite, compileall, diff-check, and temporary real
  corpus smoke verification passed.
- [x] Implementation/tests and this report are separate commits.

## Concerns and assumptions

The real tracked `holdouts.yml` remains absent by deliberate scope: Task 8 owns
that generated repository artifact. The implementation was therefore verified
against a full temporary copy of the real corpus plus the synthetic fixture;
the final Task 8 run will create the tracked manifest through this same API.

## Review-closure addendum

The Phase 2B Task 3 review findings are fixed in implementation/config/tests
commit `f0ff5ea` (`fix: close Phase 2B Task 3 review findings`). The report is
being committed separately from that implementation commit.

### Scope

The closure commit changes only:

- `src/creative_writer/source_analysis.py`
- `src/creative_writer/source_analysis_models.py`
- `tests/test_source_analysis.py`
- `tests/test_source_analysis_models.py`
- `stories/time-expedition/source-study/analysis.yml`

`source_passages.py`, source/admission registries, CLI/Make files, evidence,
style, planning, and manuscript files were not changed.

### Findings fixed

- Added strict story-local `expected_corpus` authority with exact counts,
  ordered witness identities, excluded Tier 5 identities, and whole-work
  holdouts. The real Time Expedition configuration declares 13/12/12/15/11/4,
  all 15 witnesses in registry/selection order, `the-lost-world`, and
  `selected-short-fiction/the-star`.
- `prepare` now checks composition-window parity, derives exact per-tier role
  unions from admission source and selection roles, validates the configured
  corpus topology before parsing, and retains source-admission's per-source
  tier/permitted/prohibited jurisdiction gate.
- Generated paths have an exact eight-key schema and story-slug shape. Runtime
  resolution uses `strict=False`, rejects symlink escapes, and stages only the
  exact corpus-lock and passage-index targets during `prepare`.
- `_commit_staged` now reports the original replacement failure together with
  every removal, restoration, temporary-cleanup, and residual-backup error. An
  un-restored backup is never deleted, and successful installs surface cleanup
  failures.
- Holdout selection tests now distinguish parent `source_id` hashing from a
  selected witness ID, exercise exactly eight windows with two held out, and
  use the corrected “partition windows” error wording.
- `HoldoutManifest.created_at` requires an aware UTC timestamp with offset zero.
  Existing-manifest reuse reconstructs and validates the complete payload with
  the committed timestamp rather than using `model_copy`.

### TDD and verification

RED was recorded after adding the focused regressions and before implementing
the fixes:

```text
uv run pytest tests/test_source_analysis.py -k 'prepare or holdout or corpus_lock' -q
22 failed, 1 passed, 8 deselected
```

The failures were in the newly exercised expected-corpus/path/runtime and
transaction boundaries against the pre-fix implementation.

Focused GREEN:

```text
uv run pytest tests/test_source_analysis_models.py tests/test_source_analysis.py -q
80 passed
```

Related source suites:

```text
uv run pytest tests/test_source_passages.py tests/test_source_admission.py -q
79 passed
```

Full suite and mechanical checks:

```text
uv run pytest -q
239 passed in 13.63s
python3 -m compileall -q src tests
git diff --check
```

A complete temporary copy of the real corpus completed `prepare` twice through
Pandoc. The first run produced 15 witnesses and 12,541 passages and created
the temporary manifest; the second returned
`holdout_manifest_created=False` and `holdout_manifest_verified=True`. The
real checkout still has no `stories/time-expedition/source-study/holdouts.yml`.
