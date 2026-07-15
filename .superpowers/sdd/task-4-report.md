# Phase 2B Task 4 report

## Completed action

Implemented transparent per-witness metrics and the `develop` stage for the
Phase 2B source-analysis pipeline. The implementation commit is:

`0ab290e` — `Implement Phase 2B Task 4 source metrics`

The report is intentionally committed separately from the implementation.

## RED/GREEN evidence

- RED: `uv run pytest tests/test_source_metrics.py tests/test_source_analysis.py -q`
  failed during collection with the expected missing-module error:
  `ModuleNotFoundError: No module named 'creative_writer.source_metrics'`.
- Focused GREEN: `uv run pytest tests/test_source_metrics.py tests/test_source_analysis.py -q`
  passed, `40 passed`.
- Full GREEN: `uv run pytest -q` passed, `248 passed`.
- `git diff --check` passed before the implementation commit.

## Changed files

- `src/creative_writer/source_metrics.py`
  - NFC tokenization with the approved apostrophe-preserving regex;
  - explicit Victorian sentence scanner;
  - exact-code-point punctuation and normalization-artifact audit counts;
  - dialogue proportions and runs;
  - all declared lexicon counts, normalized rates, function-word bigrams,
    paragraph categories, moving-window concentration, block proportions,
    section variation, and within-witness candidate flags;
  - deterministic JSON, long-form CSV, and per-witness Markdown rendering.
- `src/creative_writer/source_analysis.py`
  - committed-holdout verification and development-only partition measurement;
  - corpus-lock and manifest revalidation;
  - output hash metadata and Tier 4/development leakage blocking.
- `src/creative_writer/source_analysis_models.py`
  - strict distribution and candidate-flag schemas.
- `tests/test_source_metrics.py`
  - hand-countable Victorian punctuation, sentence, dialogue, lexicon,
    distribution, block, concentration, variation, and flag fixtures.
- `tests/test_source_analysis.py`
  - synthetic Git-backed development chronology and held-out/control absence
    regression.

## Exact limitations and residual risks

- Sentence counts are approximations. The scanner protects the adopted titles
  and initials, quote closers, lower-case speech attributions, ellipses,
  em-dash interruptions, and final fragments, but initials at sentence starts,
  deliberately lower-case prose after full stops, nested quotations, and
  editorially irregular punctuation may still be classified incorrectly.
- Dialogue is observable only from block labels and quote spans. Unpaired
  quotes, quoted thoughts, nested quotations, and paragraphs containing
  several speakers remain uncertain. `unknown` contributes zero dialogue words
  while remaining in the denominator. Direct blocks use all metric tokens as
  prescribed.
- Punctuation is counted by exact code point. ASCII `...` is one ellipsis event
  and its three periods are excluded from the non-ellipsis period subtotal;
  BOM, hair-space, and NBSP counts are audited from original text rather than
  treated as punctuation.
- Moving-window concentration uses the adopted `ceil(sqrt(N))` width and can
  be unstable in very short sections or across orthographic variants. It is a
  diagnostic index, not an author score.
- Candidate flags are within-witness sampling aids only. They retain passage
  IDs and section context and do not assert literary findings.
- `develop` refuses to run until `holdouts.yml` is tracked and committed,
  verifies the corpus lock and semantic partition, measures only development
  passage IDs, and omits whole-work Wells holdouts and Tier 4 controls from all
  three generated outputs. The real story-local holdout file was not created;
  Task 8 owns that lock.
- The implementation does not run the real Wells development stage in this
  task because the required committed real holdout manifest is intentionally
  deferred to Task 8.
