# Task 6A report: physical partitioning

## Completed action and changed files

Implemented Task 6A physical quarantine on current `main`.

Changed files:

- `src/creative_writer/source_analysis_common.py` (created)
- `src/creative_writer/source_analysis_models.py`
- `src/creative_writer/source_passages.py`
- `src/creative_writer/source_analysis.py`
- `tests/test_source_analysis.py`
- `tests/test_source_analysis_models.py`
- `tests/test_source_passages.py`
- `stories/time-expedition/source-study/analysis.yml`
- `.superpowers/sdd/task-6a-report.md` (created)

No real source-study prepare run was performed. No real `holdouts.yml`, source
interpretation, manuscript, Phase 2C/style, Permian, or other story edits were
made.

## Implementation notes

- `AnalysisConfig` and `HoldoutManifest` are schema v2 only. Configured passage
  indexes are physically separate under `indexes/`, and validation outputs
  resolve only through `validation/current/`.
- Added strict `ArtifactBinding` and `PassageIndexBinding` models. Manifest
  bindings record exact repository-relative paths, exact-byte SHA-256 values,
  positive counts, partition names, and ordered unique witness IDs.
- Added pure canonical partition serialization/parsing. It emits compact,
  sorted-key UTF-8 JSONL with one LF per record and rejects BOMs, blanks,
  non-canonical JSON, duplicate records, invalid PassageRecord identities, and
  non-increasing global ordinals.
- `prepare` parses retained Markdown once, partitions in memory, proves
  pairwise disjointness and exact union, assigns Tier 1-3 passages to
  development/held-out Wells, assigns every Tier 4 passage to controls, and
  publishes three deterministic bound indexes plus the v2 manifest.
- `develop` reads only the development index after checking the clean v2
  manifest, corpus-lock binding, registry metadata, and development binding.
  It does not call source admission, parse retained Markdown, or open held-out
  or control indexes. Free-text leakage scanning uses ID-only forbidden
  locators; structured locator checks remain active.
- Transitional validation opens the held-out Wells index separately and opens
  the Tier 4 control index only for `heldout_assessed`/`complete`. Frozen
  validation does not open, hash, or parse the control index, and its generated
  outputs contain no Tier 4 material.
- Task 6B capability extraction, final Git/target/reviewer hardening, and
  atomic generation publication remain intentionally out of scope.

## Verification performed and results

RED evidence before implementation:

```text
1 failed: canonical partition API absent
2 failed: v2 config rejected and v1 config incorrectly accepted
```

Focused GREEN evidence:

```text
uv run pytest tests/test_source_passages.py -k 'canonical_partition' -q
2 passed

uv run pytest tests/test_source_analysis_models.py -k 'schema_v2 or schema_v1 or v2_manifest' -q
3 passed

uv run pytest tests/test_source_analysis.py -k 'prepare_builds_exact or holdout_manifest_has_all or reads_only_development or frozen_pass_measures or v1_or_mixed' -q
6 passed

uv run pytest tests/test_source_analysis.py -k 'prepare or holdout or corpus_lock' -q
32 passed

uv run pytest tests/test_source_analysis.py -k 'develop and not validate' -q
64 passed

uv run pytest tests/test_source_analysis.py -k 'validate or freeze or compiled' -q
7 passed

uv run pytest tests/test_source_analysis.py -k 'authority or evidence or observation or profile or leakage or quantitative or metric' -q
84 passed

uv run pytest tests/test_source_analysis_models.py tests/test_source_passages.py -q
101 passed

uv run pytest tests/test_source_metrics.py -q
15 passed

uv run pytest tests/test_source_analysis.py -q
161 passed in 34.14s

uv run pytest -q
398 passed in 44.65s

uv run python -m compileall -q src tests
passed

git diff --check
passed

Final self-review also confirmed that the production read paths use only the
configured v2 physical indexes, and that no real source-study artifacts were
generated.
```

## Remaining caveats and assumptions

- Real corpus artifacts must not be generated in this remediation unit; the
  protocol-only real `analysis.yml` declaration was validated without running
  prepare or opening source/holdout/control prose.
- Task 6B remains responsible for sealed capability extraction, final Git,
  target/reviewer, and atomic publication hardening.
