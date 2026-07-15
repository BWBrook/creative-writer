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
  SHA-256 values, the 1897-1899 composition window, protocol state, the
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

## Fix Review Findings

### Status

All six Task 1 review findings are fixed in implementation commit
`e68ee06c9d19bc6d62f9a1f6a25ecf8367be75d5`.

### Changes

- Set the story analysis configuration and test fixture composition window to
  the canonical admitted `1897-1899` window. The Phase 2A admission registry,
  including the 1895 `The Time Machine` authority witness, was not changed.
- Made whole-work holdouts explicit in `HoldoutManifest`: declared whole-work
  IDs must have witness records; those records have zero development windows
  and at least one holdout window; all other witnesses require both window
  types. Passage coverage remains an orchestration responsibility.
- Updated `ValidationRecord` lifecycle rules so development may omit candidate
  hashes, candidate-frozen and validated stages require candidate commit,
  profile, and ledger hashes, and the final profile hash is forbidden before
  validated and required at validated.
- Made the new schema boundary strict with `ConfigDict(strict=True)`, strict
  string/integer/float fields, and a strict composition-window model. YAML-native
  integers, floats, and PyYAML-loaded datetimes remain accepted; string
  `"0.2"` is rejected.
- Split the compound negative tests into isolated malformed-hash, empty-text,
  selection-mismatch, duplicate-claim-ID, and forbidden-extra-field tests, and
  added focused whole-work and validation-lifecycle positive/negative tests.

### TDD and verification

RED, before implementation:

```text
uv run pytest tests/test_source_analysis_models.py -q
Result: 9 failed, 16 passed.
Expected failures covered the 1895 fixture/config, universal development-window
requirement, string holdout-fraction coercion, development without candidate
hashes, whole-work topology, and pre-validation final hash.
```

GREEN focused suite:

```text
uv run pytest tests/test_source_analysis_models.py -q
Result: 26 passed in 0.10s.
```

Full regression suite:

```text
uv run pytest -q
Result: 147 passed in 7.88s.
```

YAML scalar-boundary smoke check:

```text
uv run python - <<'PY'
import yaml
from pathlib import Path
path = Path('stories/time-expedition/source-study/analysis.yml')
raw = yaml.safe_load(path.read_text())
print(type(raw['composition_window']['start']).__name__, raw['composition_window'])
print(type(raw['partition']['holdout_fraction']).__name__, raw['partition']['holdout_fraction'])
PY
Result: int {'start': 1897, 'end': 1899}
        float 0.2
```

Diff and scope checks:

```text
git diff --check
Result: passed.

Changed implementation paths in e68ee06:
src/creative_writer/source_analysis_models.py
tests/test_source_analysis_models.py
stories/time-expedition/source-study/analysis.yml
Result: no raw data or unrelated artefacts changed.
```

### Self-review

- The canonical window is applied only to the Phase 2B analysis config and
  fixture; the source-admission authority records remain intact.
- Whole-work and partitioned witness rules are enforced at the manifest level,
  with duplicate witness/window/passage checks retained and complete passage
  coverage deliberately deferred to orchestration.
- Lifecycle checks distinguish protocol/development from candidate freeze and
  final validation, including the previously missing final-hash guard.
- Strict validation is compatible with the repository's `yaml.safe_load` path:
  valid YAML-native numeric values and timestamp datetimes pass, while scalar
  strings are not silently coerced.
- The implementation diff is restricted to the three allowed files; this
  report is the only subsequent file change.

### Concerns

No unresolved concerns. The separate report commit hash is returned in the
handoff because recording a commit's own hash inside that same commit would be
self-referential.

## Remaining Review Findings

### Status

The remaining Task 1 review findings are fixed in implementation commit
`5958ce1294354e42e179f225f5c39f58b9d0cde7`.

### Changes

- Made `authority_tiers` required and enforced one policy for each tier 1
  through 5, with duplicate tier IDs rejected. The complete model fixture now
  declares all five policies.
- Derived the story-local per-tier role comparison from `admission.yml`, adding
  all selected-short-fiction roles to Tier 2 and `social register` to Tier 4.
  The repository test compares exact role sets after including source-level
  and selection-level roles.
- Expanded `enabled_measurements` to the approved core set: totals for words,
  passages, sentences, and sections; sentence, passage, and paragraph length
  distributions; dialogue proportion and runs; punctuation; speech/reporting
  verbs; pronoun, demonstrative, modal, and epistemic frequencies; function
  words and sequences; paragraph openings/transitions; moving-window lexical
  concentration; block proportions; and section-level variation.
- Declared explicit `first_person_pronouns`, `third_person_pronouns`, and
  `demonstratives` lexicons for later pronoun metrics.
- Required each generated path to pass canonical relative-POSIX validation and
  begin with `build/`, with an isolated rejection test.
- Defined the canonical `DimensionId` literal union and reused it for both
  `AnalyticalDimension.id` and `EvidenceClaim.dimension`, with isolated
  invented-dimension rejection tests.
- Corrected the superseded earlier report wording to `1897-1899`; the Phase 2A
  admission registry remains unchanged.

### TDD and verification

RED command, after adding the focused tests and before implementation:

```text
uv run pytest tests/test_source_analysis_models.py -q
Result: 8 failed, 26 passed in 0.24s.
Expected failures covered required/unique authority tiers, exact admission role
sets, the expanded measurement and lexicon declarations, the build-path rule,
and invented dimension IDs.
```

GREEN focused suite:

```text
uv run pytest tests/test_source_analysis_models.py -q
Result: 34 passed in 0.26s.
```

Full regression suite:

```text
uv run pytest -q
Result: 155 passed in 19.79s.
```

Independent admission-vs-analysis role comparison:

```text
uv run python - <<'PY'
# Loads admission.yml and analysis.yml, unions source and selection roles by
# tier, and compares each modelled tier as an exact set.
PY
Result: tiers [1, 2, 3, 4, 5];
        tier 1 expected=4 actual=4 exact=True;
        tier 2 expected=28 actual=28 exact=True;
        tier 3 expected=7 actual=7 exact=True;
        tier 4 expected=21 actual=21 exact=True;
        tier 5 expected=3 actual=3 exact=True.
```

Formatting and scope checks:

```text
git diff --check
Result: passed before the implementation commit.

Implementation commit paths:
src/creative_writer/source_analysis_models.py
tests/test_source_analysis_models.py
stories/time-expedition/source-study/analysis.yml
Result: no raw data or unrelated artefacts changed.
```

### Self-review

- The authority policy now cannot omit a tier, repeat a tier, or introduce a
  tier outside the prescribed 1-5 set.
- The repository role test derives expected values from the admission registry,
  so selection roles cannot silently disappear from `analysis.yml`.
- Measurement identifiers are explicit and unique, and the three pronoun
  lexicons are visible configuration rather than implementation constants.
- Generated paths validate canonical relative-POSIX syntax before the required
  `build/` prefix check.
- `DimensionId` is the single declared vocabulary used at both dimension
  declaration and evidence-claim boundaries.
- Only the three requested implementation/config/test files were included in
  the implementation commit; this report is being committed separately.

### Concerns

No unresolved concerns. The report commit hash is returned separately because
including it in this report would make the report commit self-referential.
