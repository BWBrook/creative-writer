# Wells Phase 2B Task 2 Report: Pandoc Passage Index

## Outcome

Implemented the Task 2 Pandoc passage index without changing retained
Markdown, orchestration, CLI, Makefile, registries, study evidence or
artifacts, style files, story plans, or manuscript prose.

Implementation and test commit:

`e5f14cee2ffd8c37a7230a9e0566deb6495a9daa` (`feat: add Pandoc passage index`)

The report is intentionally committed separately after the implementation
commit, as required by the task brief.

## TDD record

### RED

I wrote `tests/test_source_passages.py` before adding the passage parser or
witness descriptor. The mandated focused command was run:

```text
uv run pytest tests/test_source_passages.py -q
```

Observed result: collection failed with the expected missing-interface error:

```text
ImportError: cannot import name 'WitnessDescriptor' from
'creative_writer.source_analysis_models'
```

This established that the new tests exercised code that did not yet exist.

### GREEN

After the minimal schema and parser implementation, the focused suite first
reached:

```text
10 passed in 0.35s
```

An explicit mixed-dialogue test was then added during review. The final
focused result was:

```text
uv run pytest tests/test_source_passages.py -q
11 passed in 0.91s
```

The related Task 1/source-admission regression set passed:

```text
uv run pytest tests/test_source_passages.py tests/test_source_analysis_models.py \
  tests/test_source_models.py tests/test_source_admission.py -q
118 passed in 1.10s
```

## Files changed

### `src/creative_writer/source_passages.py`

Added the deterministic passage-index implementation:

- invokes `pandoc --from=gfm --to=json` for each witness;
- converts Pandoc JSON AST blocks and inlines recursively into passage text;
- emits paragraphs, top-level block quotes, `LineBlock` verse, and recursive
  ordered/bullet-list items;
- excludes headings, images, horizontal rules, empty blocks, raw blocks,
  code blocks, tables, and other non-substantive apparatus;
- keeps a real heading-level stack, including malformed source-level jumps;
- assigns one-based substantive source and heading ordinals;
- preserves original AST-derived text separately from normalized analysis text;
- computes normalized UTF-8 SHA-256 content hashes and stable passage IDs;
- classifies direct, mixed, and absent dialogue quotes;
- writes deterministic UTF-8 JSON Lines and strictly reads/validates them;
- provides heading-bounded context and five-block partition windows.

### `src/creative_writer/source_analysis_models.py`

Added only `WitnessDescriptor`, a strict model containing:

- `witness_id`;
- `source_id`;
- optional `selection_id`;
- retained Markdown `source_fingerprint`.

The descriptor reuses the existing selection-identity rule, so
`selected-short-fiction/the-star` remains a slash-containing witness with
parent source `selected-short-fiction` and selection `the-star`.

### `tests/test_source_passages.py`

Added focused synthetic-AST and real-Pandoc tests covering:

- headings, paragraphs, emphasis, Pandoc quoted inlines, notes, Unicode
  punctuation, FEFF, NBSP, hair spaces, and meaningful line breaks;
- malformed heading jumps and heading-path/heading-ordinal tracking;
- image, separator, empty, code, raw, and table filtering;
- top-level block quotes versus nested child paragraphs;
- `LineBlock` verse and block-quote line breaks;
- ordered lists, bullet lists, and nested list items without parent-text
  duplication;
- Unicode and ASCII quote dialogue heuristics for direct, mixed, and none;
- stable slash-preserving passage IDs and `hash12` content identity;
- missing Pandoc, non-zero Pandoc, malformed-AST, and empty-index errors;
- deterministic JSONL round trips and duplicate passage-ID rejection;
- two-sided context bounded by exact witness and heading-path identity;
- non-overlapping five-block windows bounded by exact heading-path identity;
- real selected-short-fiction witness identity.

## Implementation decisions

### AST invocation and errors

The parser uses a subprocess argument vector with exactly the prescribed GFM
input and JSON output formats. Missing executables, invocation failures,
non-zero exit status, invalid UTF-8/JSON, structurally malformed ASTs, and no
substantive result become `CreativeWriterError` failures. No Markdown parser
dependency was added and no retained source is rewritten.

### Original and normalized text

Original passage text is assembled from AST text nodes. `Space` and
`SoftBreak` become ordinary spaces; Pandoc `LineBreak` becomes a newline;
quoted AST inlines receive their ASCII quote delimiters; emphasis, links, and
notes are recursively reduced to text. Image alt text and raw inline markup
are not analytical prose.

Normalized text applies the controller resolution exactly:

1. Unicode NFC normalization;
2. removal of U+FEFF;
3. mapping U+00A0 and U+200A to ASCII spaces;
4. collapse of horizontal whitespace;
5. per-line trimming while retaining line-break boundaries;
6. UTF-8 SHA-256 hashing of the resulting text.

The original text is not used to compute the content hash. Word counts use
non-whitespace runs in normalized text.

### Block extraction

Headers update context only. A top-level `BlockQuote` is emitted as one
`block_quote` record, so its child paragraphs are not emitted separately.
`LineBlock` is emitted as `verse`; line breaks inside a block quote do not
change its `block_quote` type. List containers are not records: each list item
is emitted as `list_item`, and nested list containers are recursively walked
after the parent while their text is excluded from the parent text.

Images, horizontal rules, whitespace-only blocks, raw/code/table blocks, and
headers do not consume source ordinals.

### Heading paths and ordinals

The stack truncates to `level - 1` before appending a heading label. It does
not insert synthetic levels when the source jumps from H1 to H4 or otherwise
malforms the hierarchy. Before any heading the path is `['Untitled']`.

The source ordinal increments only after a non-empty substantive passage is
created. The heading ordinal resets only when the exact heading path tuple
changes, and empty blocks do not alter either ordinal.

### Dialogue heuristic

The heuristic recognizes ASCII double/single opening quotes and common
Unicode opening quotation marks. A quote at the start of the stripped
passage is `direct`; the first quote after narrative text is `mixed`; no
opening quote is `none`. An empty structural text value is `unknown`, though
empty values are filtered before passage records are emitted. This keeps
`unknown` reserved for the structural-undecidable case rather than treating
ordinary non-dialogue prose as uncertain.

### IDs, JSONL, context, and windows

Passage IDs use the existing schema rule exactly:

```text
<witness-id>:<heading-slug>:<source-ordinal>:<hash12>
```

The full witness ID is preserved, including `/`. JSONL output is UTF-8,
non-ASCII preserving, compact, sorted by `(source_id, witness_id,
source_ordinal)`, and key-order deterministic. The source record has no
separate registry-position field, so source ID is the available registry
ordering key.

Context windows include the focal record and up to two neighbours on each
side, stopping at any exact heading-path or witness boundary. Partition
windows consume reading-order records in non-overlapping chunks of at most
five, starting a new window whenever the exact heading path or witness
changes.

## Verification and real-corpus checks

The complete repository suite passed:

```text
uv run pytest -q
166 passed in 10.73s
```

The real retained corpus was also parsed directly through the new API without
writing an index artifact. All 15 declared Markdown witnesses succeeded:

```text
the-time-machine                         308 passages
selected-short-fiction/the-plattner-story 45 passages
selected-short-fiction/the-sea-raiders    41 passages
selected-short-fiction/the-crystal-egg    54 passages
selected-short-fiction/the-star           40 passages
certain-personal-matters                 403 passages
text-book-of-biology-part-1              650 passages
the-british-barbarians                   434 passages
a-desert-drama                           934 passages
the-days-work                           2074 passages
the-beetle                              3237 passages
king-solomons-mines                     1525 passages
the-invisible-man                       1138 passages
the-island-of-doctor-moreau              746 passages
the-war-of-the-worlds                    912 passages
parsed_witnesses=15
```

The smoke parse used the registry-declared Markdown fingerprints and exercised
the selected-fiction slash identities. It wrote no corpus or generated
artifact.

Additional checks passed:

- `uv run python -m compileall -q src tests`;
- `git diff --check` before staging;
- staged `git diff --cached --check` before the implementation commit.

## Self-review against the brief

- [x] Parser interface invokes Pandoc GFM-to-JSON and raises project errors
  for missing executable, failed process, malformed AST, and empty result.
- [x] Deterministic JSONL writer and strict reader are implemented.
- [x] Duplicate passage IDs are rejected on read.
- [x] Context uses exact heading paths and does not cross witness/section
  boundaries.
- [x] Partition windows are non-overlapping, reading ordered, and capped at
  five blocks by default.
- [x] Synthetic AST fixtures cover the requested structural edge cases.
- [x] Real-Pandoc fixtures cover Unicode, malformed headings, empty blocks,
  selected-short-fiction IDs, context, and five-block windows.
- [x] Source and heading ordinals are one-based and count substantive records
  only.
- [x] FEFF/NBSP/hair-space normalization and original-text retention follow
  the controller resolutions.
- [x] No new dependency, orchestration, CLI, registry, retained Markdown,
  evidence/artifact, style, story-plan, or manuscript-prose change was made.
- [x] Implementation/tests and report are intended to be separate focused
  commits.

## Concerns and assumptions

1. The current `PassageRecord` schema has no explicit registry-position field.
   The deterministic writer therefore sorts by source ID, witness ID, and
   source ordinal. Future orchestration that has a formal registry-order
   requirement should either supply records in that order or add an explicitly
   approved ordering field rather than inferring it from filesystem paths.
2. Pandoc inline notes are reduced into the containing passage's extracted
   text; note markup itself is not retained. This follows the text-extraction
   boundary and keeps note content auditable without adding a new passage type.
3. The valid corpus contains no Pandoc `CodeBlock`, `Table`, `RawBlock`, or
   `LineBlock`; those behaviors are protected by synthetic AST tests. The
   parser still handles them deterministically as non-passage apparatus or
   verse according to the approved contract.
4. No passage index JSONL artifact was generated because Task 2's write scope
   excludes generated study artifacts and orchestration. The writer/reader
   round trip is tested in temporary paths only.

## Final review state

The implementation commit is complete and independently verified. The only
remaining action for this task is the separate commit containing this report.

## Phase 2B Task 2 review-fix addendum

This addendum records the complete review closure after the original Task 2
implementation. The original concern that ordering would fall back to source
and witness IDs is superseded: explicit global witness ordinals are now
required by both relevant schemas and are the only registry-order key used by
the index writer and reader.

### Findings and fixes

1. Heading context was made level-aware. The parser stores `(level, label)`
   entries, pops stored levels greater than or equal to each new header level,
   and appends the new header. A real Pandoc test covers H1 `A` to H4 `A`,
   sibling H4 `B`, H4 to H3, repeated H3, and repeated H5 transitions; stale
   siblings disappear from every resulting heading path.

2. `WitnessDescriptor` and `PassageRecord` now require strict one-based
   `witness_ordinal` values. Parsing propagates the descriptor value. Writer
   sorting uses `(witness_ordinal, source_ordinal)` only. Writer and reader
   validation enforce one ordinal per witness, one witness per ordinal, and a
   complete ordinal set contiguous from 1. Reader input must already be in
   the same reading order. Fixtures and tests now provide explicit ordinals.

3. Writers reject empty collections and duplicate passage IDs before creating
   a directory or temporary file. Readers reject zero-byte files and
   duplicates. Existing destination content is tested and preserved on
   pre-write validation failure.

4. `PassageRecord` validation now requires the final heading path label to
   equal `heading_label`, recomputes SHA-256 from `normalized_text`, checks
   `content_hash` and the passage ID against that digest, and recomputes
   `word_count`. Isolated read and write tampering tests cover each integrity
   field.

5. `partition_windows` now requires `type(max_blocks) is int` and the value
   to be in `1..5`; booleans, zero, and six are rejected.

6. Pandoc `Quoted` fixtures and extraction now use tagged enum values such as
   `{"t": "DoubleQuote"}` and `{"t": "SingleQuote"}`. A focused tagged-shape
   test confirms rendered delimiters while preserving literal GFM quote text.

7. Directory creation errors are converted to `CreativeWriterError`. Index
   output is written to a same-directory temporary file and installed with
   `os.replace`; all temporary paths are cleaned up on write or replacement
   failure. Focused failure tests confirm destination preservation without
   platform-specific assumptions.

### TDD evidence

#### RED

The focused review tests were added before the implementation fixes and run
with:

```text
uv run pytest tests/test_source_passages.py tests/test_source_analysis_models.py -q
```

Observed result: `32 failed, 40 passed`. The failures were the expected
missing witness-ordinal schema, tagged-quote handling, heading-stack
behavior, strict partition validation, index validation, integrity checks,
and atomic-write protections.

#### GREEN

After implementation, the focused command passed:

```text
72 passed in 1.22s
```

The focused source regression set passed:

```text
uv run pytest tests/test_source_passages.py tests/test_source_analysis_models.py \
  tests/test_source_models.py tests/test_source_admission.py -q
145 passed in 2.15s
```

### Full verification

The complete repository suite passed after the final implementation change:

```text
uv run pytest -q
193 passed in 11.37s
```

Compilation and whitespace checks passed:

```text
uv run python -m compileall -q src tests
git diff --check
git diff --cached --check
```

The real source registry was expanded in declared source order, with the
selected omnibus children expanded in declared selection order, into exactly
15 explicit global witness ordinals. All 15 witnesses parsed successfully,
producing 12,541 passages:

```text
parsed_witnesses=15
temporary_index_round_trip=ok
indexed_passages=12541
```

The temporary full index was written and read back successfully. The read
records matched the writer's `(witness_ordinal, source_ordinal)` order, had
ordinals 1 through 15 without gaps, and passed record-integrity validation.
No generated corpus artifact was retained.

### Updated self-review

- [x] Level-aware heading stack and focused real heading transition coverage.
- [x] Explicit one-based witness ordinal schema propagation and non-lexical
  writer/reader ordering.
- [x] Consistent witness/ordinal mappings and contiguous full-index ordinals.
- [x] Empty/duplicate rejection before write-side filesystem mutation and on
  read.
- [x] Heading, digest, passage-ID, and word-count integrity checks on read and
  write through the shared strict model.
- [x] Strict `partition_windows` bound and boolean rejection.
- [x] Pandoc tagged quote enums with literal GFM quote preservation.
- [x] CreativeWriterError-wrapped directory creation and atomic replacement
  with cleanup and destination preservation tests.
- [x] Only the four implementation/test files named by the task were changed
  in the implementation commit; no witnesses, registries, orchestration, CLI,
  story evidence, styles, plans, or manuscripts were touched.

Implementation/tests commit:

`a7382559c349b8115c99c31fa740111267cbc0a5`
