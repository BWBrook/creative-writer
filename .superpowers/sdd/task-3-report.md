# Task 3 Report: Record the Exact Proposed Corpus

## Status

Implemented the exact Task 3 corpus proposal and migrated the two retained
source records to the strict authority schema. No proposed artifact was
downloaded, and no Moreau or War of the Worlds artifact was added.

## RED evidence

Added the real-story admission smoke test
`test_time_expedition_admission_passes` to `tests/test_source_admission.py`.

Command:

```text
uv run --group dev pytest tests/test_source_admission.py::test_time_expedition_admission_passes -v
```

Result before implementation: **FAIL**. The assertion failed because
`source-study/admission.yml` was missing, which was the expected precondition
failure from the brief.

## GREEN evidence

Focused test:

```text
uv run --group dev pytest tests/test_source_admission.py::test_time_expedition_admission_passes -v
```

Result: **1 passed**.

Admission command:

```text
make source-admission STORY=time-expedition
```

Result: exit `0`; report generated at
`build/time-expedition/reports/source-admission-report.md` with no blocking
issues.

The generated report records:

- Admitted: 2
- Approved, awaiting retention: 2
- Proposed: 7
- `the-time-machine`: admitted, Tier 1, primary
- `the-island-of-doctor-moreau`: approved, Tier 2, bounded
- `the-british-barbarians`: proposed, Tier 4, control

## Absence checks

The seven required proposed EPUB paths were each checked with `test ! -e`:

- `original/h-g-wells_short-fiction.epub`
- `original/h-g-wells_certain-personal-matters.epub`
- `original/h-g-wells_text-book-of-biology-part-1.epub`
- `original/grant-allen_the-british-barbarians.epub`
- `original/arthur-conan-doyle_a-desert-drama.epub`
- `original/rudyard-kipling_the-days-work.epub`
- `original/richard-marsh_the-beetle.epub`

Result: **all seven proposed artifacts absent**.

## Full-suite verification

Command:

```text
uv run --group dev pytest
```

Result: **56 passed in 10.05s**.

## Files changed

- `stories/time-expedition/source-study/README.md` — phase boundary and
  generated-review guidance.
- `stories/time-expedition/source-study/method.md` — settled forensic source
  study method and current prohibitions.
- `stories/time-expedition/source-study/admission.yml` — exact eleven-record
  anthology-wide admission proposal.
- `stories/time-expedition/original/sources.yml` — strict authority fields and
  rights-key migration for the two retained records.
- `tests/test_source_admission.py` — real-story admission smoke test.
- `.superpowers/sdd/task-3-report.md` — this report.

## Self-review

- `git diff --check` passed.
- The source admission report has the required 2/2/7 counts and no blocking
  issues.
- The retained records preserve existing work, edition, retrieval, file
  fingerprints, derivation, provenance, source-text rights, booleans, focus,
  revision IDs, and prose; only the specified schema fields were added or
  renamed.
- No manuscript prose was changed.
- No files outside the assigned source-study, retained registry, test, and
  required task-report scope were modified.

## Concerns

None. Task 4 remains responsible for acquiring the two approved Wells EPUBs;
the seven proposed artifacts remain blocked pending human review.
