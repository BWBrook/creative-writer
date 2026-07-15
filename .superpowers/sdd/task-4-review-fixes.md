# Phase 2B Task 4 review-fixes report

## Completed action

Fixed all assigned Phase 2B Task 4 review findings in implementation commit
`299e234` (`Fix Phase 2B Task 4 review findings`). The prior implementation
and report commits reviewed were `0ab290e` and `9f9337f`.

No real holdouts, story artifacts, Phase 2C work, or prose were changed.

## RED/GREEN evidence

- Pre-fix baseline: focused `uv run pytest tests/test_source_metrics.py tests/test_source_analysis.py -q` passed `40`; full `uv run pytest -q` passed `248`.
- Review RED: after adding the review regressions, the focused suite failed `6` tests, including index trust, non-quoted attribution, mixed-quote uncertainty, passage-boundary punctuation, candidate aids, and exact CSV mapping.
- Additional RED: the nested curly-outer/straight-inner quote regression failed with `0` dialogue words before the quote-stack correction.
- Focused GREEN: `uv run pytest tests/test_source_metrics.py tests/test_source_analysis.py -q` passed `48`.
- Full GREEN: `uv run pytest -q` passed `256`.
- `python3 -m compileall -q src tests` passed.
- `git diff --check` passed.

## Defects fixed

- `develop` reparses every retained witness, serializes the regenerated records
  canonically, rejects any byte drift against the build passage index, and uses
  the verified records downstream. The regression mutates only `direct_dialogue`.
- Sentence attribution suppression now requires a terminal immediately followed
  by a supported quotation closer and a lower-case adjacent clause containing a
  declared speech verb. Non-quoted lower-case continuation remains separate.
- Mixed passages with unmatched, mismatched, or stray closing quotations are
  explicitly unknown and contribute no dialogue words. Supported nested quote
  pairs remain measurable.
- Punctuation aggregation resets at passage boundaries. Exact components and
  derived families now include `denominator_words` and `per_1000_words` rates.
- CSV output maps the configured 24 public measurement names exactly, emits
  explicit empty mapping/sequence/transition rows, carries study/stage,
  config/index/manifest paths, and carries all three hashes on every row. JSON
  and Markdown include the same provenance and no pooled row.
- JSON, CSV, and Markdown are staged and installed as one rollback-capable
  transaction. The forced third-install failure regression confirms previous
  bytes survive and no temporary or backup files remain.
- Candidate flags now cover within-witness length extrema, declared
  modality/qualification density, observable dialogue density, and
  question/exclamation/parenthesis clusters. They are marked sampling aids and
  non-findings. Observation-to-explanation movement is explicitly deferred to
  human close reading because declared lexicons cannot measure it without
  interpretation.

## Changed files

- `src/creative_writer/source_metrics.py`
- `src/creative_writer/source_analysis.py`
- `tests/test_source_metrics.py`
- `tests/test_source_analysis.py`

The eight new review regressions were added alongside all prior hand fixtures.

## Residual risks and assumptions

- Sentence counts remain transparent approximations for initials at sentence
  starts, deliberately lower-case prose after full stops, and editorially
  irregular punctuation.
- Dialogue remains structural and quote-span based. Quoted thoughts, several
  speakers in one paragraph, and other interpretive cases can remain uncertain;
  direct parser labels still use the prescribed all-token rule.
- Candidate flags identify sampling aids only and do not establish literary
  findings. Observation-to-explanation movement requires human close reading.
- The real Wells `develop` stage remains gated by its committed story-local
  holdout manifest, as required by the existing workflow; the tests exercise
  the synthetic Git-backed development path.
