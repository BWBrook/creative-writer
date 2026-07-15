# Wells Phase 2B Task 1 Report

## Status

Task 1 is implemented. The schema and tracked story-local protocol foundation
is committed in `1ce4c80` (`feat: add Wells Phase 2B schema foundation`). The
report is intentionally committed separately because the implementation commit
hash must be recorded inside this file without creating a self-referential
amendment.

## Files changed

Implementation commit `1ce4c80` changed only the requested files:

- `src/creative_writer/source_analysis_models.py`
- `tests/test_source_analysis_models.py`
- `stories/time-expedition/source-study/analysis.yml`
- `stories/time-expedition/source-study/analysis-plan.md`
- `stories/time-expedition/source-study/quantitative-profile.yml`
- `stories/time-expedition/source-study/evidence-ledger.yml`
- `stories/time-expedition/source-study/wells-profile.md`
- `stories/time-expedition/source-study/period-controls.md`
- `stories/time-expedition/source-study/validation.md`
- `stories/time-expedition/source-study/observations/the-time-machine.md`
- `stories/time-expedition/source-study/observations/selected-short-fiction.md`
- `stories/time-expedition/source-study/observations/the-invisible-man.md`
- `stories/time-expedition/source-study/observations/the-island-of-doctor-moreau.md`
- `stories/time-expedition/source-study/observations/the-war-of-the-worlds.md`
- `stories/time-expedition/source-study/observations/certain-personal-matters.md`
- `stories/time-expedition/source-study/observations/text-book-of-biology-part-1.md`

This report is the only additional allowed file.

## Schema decisions

- Added strict Pydantic 2 models with `extra="forbid"` for `AnalysisConfig`,
  `PassageRecord`, `HoldoutManifest`, `QuantitativeProfile`, `EvidenceLedger`,
  and `ValidationRecord`.
- Added reusable canonical relative-path, slug, SHA-256, Git-hash, and
  non-empty-text constraints.
- `AnalysisConfig` records the actual Phase 2A admission and source-registry
  SHA-256 values, the 1895-1899 composition window, protocol state, the
  adopted ten dimension IDs, authority tiers/roles, parser constants,
  deterministic partition constants, declared measurements/lexicons,
  vocabularies, and generated paths.
- Passage, witness, claim, and evidence-reference validators reject duplicate
  identifiers, malformed hashes, empty required text, mismatched selected-work
  identity, invalid passage IDs, overlapping development/holdout windows,
  invalid Tier 4 evidence roles, and incomplete non-rejected claims.
- Evidence claims are descriptive only. The schema deliberately has no
  `operational_use` field; development-stage ledgers reject `validated` claims
  and `strong` confidence.
- `validation.md` is parsed by `parse_validation_document`/
  `load_validation_document`: strict YAML front matter is validated as
  `ValidationRecord`, and a non-empty human-readable Markdown body is required.
- The tracked quantitative profile and evidence ledger begin with empty
  collections at protocol status. Markdown protocol surfaces contain adopted
  headings and phase-state notes only; they contain no findings, locators, or
  `TBD` markers.

## TDD evidence

RED command:

```text
uv run pytest tests/test_source_analysis_models.py -q
```

Expected RED output was observed before implementation:

```text
exit_code=2
ERROR collecting tests/test_source_analysis_models.py
ModuleNotFoundError: No module named 'creative_writer.source_analysis_models'
1 error in 0.11s
```

GREEN command:

```text
uv run pytest tests/test_source_analysis_models.py -q
```

Observed output after implementation:

```text
exit_code=0
..........                                                               [100%]
10 passed in 0.10s
```

## Additional verification

The story-local YAML and validation document were loaded through the new
models:

```text
analysis.yml: AnalysisConfig OK
quantitative-profile.yml: QuantitativeProfile OK
evidence-ledger.yml: EvidenceLedger OK
validation.md: ValidationRecord stage=protocol body_lines=8
```

The complete test suite was run:

```text
uv run pytest -q
........................................................................ [ 54%]
...........................................................              [100%]
131 passed in 9.77s
```

Staged `git diff --check` passed. The staged changed-path audit listed exactly
the 16 implementation/test/protocol files above; no existing source registry,
parser, orchestration, CLI, Makefile, guidance, planning, or manuscript file
changed.

## Self-review

- The schema boundary matches the brief: YAML for analysis, quantitative
  profile, and evidence ledger; strict front matter plus Markdown body for
  validation; Markdown for the plan, profile, controls, and dossiers.
- The actual registry fingerprints were computed from the current Phase 2A
  files and are recorded without changing those files.
- Protocol-state artifacts do not claim reviewed results or invent passage
  locators. The selected short-fiction witness identity remains explicit.
- The implementation is limited to the schema foundation; passage parsing,
  orchestration, command interfaces, and generated holdouts remain for later
  tasks.

## Concerns and boundary notes

- The approved design’s broader artifact layout names `holdouts.yml` and calls
  for updates to `source-study/README.md` and `source-study/method.md`, but the
  Task 1 file list explicitly excludes all three. They were therefore not
  changed; the `HoldoutManifest` model is present for the later prepare task.
- The current worktree was already three commits ahead of `origin/main`; no
  existing commits or unrelated changes were altered.
