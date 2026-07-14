# Wells Phase 2A Reference Corpus Foundation Design

Date: 2026-07-14
Status: proposed design, awaiting human review

## Purpose

Complete the bounded reference corpus for the *Time Expedition* forensic
source study without beginning the detailed Wells analysis. This phase turns
the approved source candidates into a stable, reproducible evidence base and
then stops.

The result must make later analysis trustworthy in three ways:

- every positively admitted source has an explicit authority jurisdiction;
- every retained EPUB and derived text has verifiable provenance and identity;
- the corpus boundary is enforced by schema and validation rather than by
  editorial intention alone.

This is Phase 2A of the wider Wells study. Quantitative profiling, close
reading, evidence-ledger claims, operational style guidance, Permian story
design, and prose composition are all later phases.

## Expansion Boundary

The corpus closes at thirteen admission records:

- twelve admitted records with retained source artifacts;
- one excluded, unacquired diagnostic record;
- no records left in `approved` or `proposed` state.

The twelve retained records are:

| Tier | Source | Function |
|---:|---|---|
| 1 | H. G. Wells, *The Time Machine* | Sole continuity canon and primary style authority |
| 2 | H. G. Wells, *The Invisible Man* | Dialogue, social register, and comic friction |
| 2 | H. G. Wells, *The Island of Doctor Moreau* | Retrospective scientific adventure and moral pressure |
| 2 | H. G. Wells, *The War of the Worlds* | Catastrophe, landscape observation, and public behaviour |
| 2 | H. G. Wells, four selected short stories | Short-form architecture and bounded role-specific evidence |
| 3 | H. G. Wells, *Certain Personal Matters* | Period nonfiction, explanation, humour, and idiom |
| 3 | H. G. Wells, *Text Book of Biology, Part 1* | Scientific vocabulary, classification, and instructional exposition |
| 4 | Grant Allen, *The British Barbarians* | Scientific-romance and time-visitor control |
| 4 | Arthur Conan Doyle, *A Desert Drama* | Date-matched adventure and ensemble-dialogue control |
| 4 | Rudyard Kipling, *The Day's Work* | Technical-work and professional-register control |
| 4 | Richard Marsh, *The Beetle* | Sensational-fiction and horror-escalation control |
| 4 | H. Rider Haggard, *King Solomon's Mines* | Adventure architecture and motivation control |

The thirteenth record is Arthur Conan Doyle's *The Lost World* (1912). It is
recorded as Tier 5, `status: excluded`, and `style_authority: none`. It will
not be downloaded, retained, converted, or analysed in Phase 2A. Its only
declared future use is as a post-window diagnostic for detecting anachronistic
adventure architecture or drift toward a later lost-world idiom.

No further Wells work, nonfiction source, control author, or adventure novel
is added in this phase. In particular, *She*, Stevenson's adventure fiction,
Conrad's `Youth`, and other plausible period witnesses remain outside the core
corpus. A later expansion will require a new design decision with a specific
unmet analytical need; convenience or thematic resemblance will not be
sufficient.

## Authority Boundary

*The Time Machine* remains the sole Tier 1 source. Nothing in this expansion
changes its jurisdiction over continuity, the Time Traveller, the machine,
the frame, or the governing reported-account mode.

The Wells additions retain the bounded Tier 2 and Tier 3 roles already
approved in `source-study/admission.yml`. They do not become continuity
sources and do not override *The Time Machine*.

All five Tier 4 authors remain negative or comparative controls. Their works
may expose period conventions, generic adventure machinery, neighbouring
voices, and false Victorianism. They may never prescribe Wellsian style,
authorise phrase borrowing, supply *Time Expedition* continuity, or justify a
feature merely because it is historically plausible.

*King Solomon's Mines* has an especially narrow jurisdiction:

- permitted: adventure motivation, expedition assembly, discovery sequence,
  danger escalation, journey architecture, and period framing of mysterious
  travel;
- prohibited: style prescription, phrase borrowing, characters, places,
  incidents, lost-world content, imperial assumptions, racial ideology, and
  any override of a Wells source.

The source is studied as historical evidence, not cleansed or rewritten, but
its presence cannot smuggle its assumptions or inventions into the anthology.

*The Lost World* has no positive authority. Its post-1899 date is the reason
for exclusion, not a defect to be worked around. Recording it without
acquiring it makes the temporal boundary explicit while preserving a named
future diagnostic.

## Admission State Transition

The seven currently proposed records are human-approved by the decision that
authorised this phase. During implementation they move directly from
`proposed` to `admitted` once their retained artifacts, provenance records,
and validation checks are complete.

Two records are added:

- `king-solomons-mines`: Tier 4 and admitted only after successful retention;
- `the-lost-world`: Tier 5 and excluded from its first committed state.

The source endpoints and planned artifact paths for these additions are fixed:

| ID | Edition metadata | Planned path |
|---|---|---|
| `king-solomons-mines` | Standard Ebooks, `https://standardebooks.org/ebooks/h-rider-haggard/king-solomons-mines`, compatible EPUB at `https://standardebooks.org/ebooks/h-rider-haggard/king-solomons-mines/downloads/h-rider-haggard_king-solomons-mines.epub?source=download` | `original/h-rider-haggard_king-solomons-mines.epub` |
| `the-lost-world` | Project Gutenberg ebook 139, `https://www.gutenberg.org/ebooks/139`; metadata reference only | `original/arthur-conan-doyle_the-lost-world.epub`, which must remain absent |

The admission registry is not allowed to claim a source is admitted before
the corresponding retained record and files are present. Implementation may
use an intermediate local `approved` state while acquiring files, but the
committed completion state is exactly twelve admitted, zero approved, zero
proposed, and one excluded.

`original/sources.yml` contains exactly the twelve admitted records. It must
not contain *The Lost World* or any other excluded, proposed, or approved
source.

## Retained Source Layout

Each full-work source retains:

```text
stories/time-expedition/original/
  <source-name>.epub
  text/<source-id>.md
```

The selected Wells short fiction uses one retained omnibus EPUB but four
separate derived witnesses:

```text
stories/time-expedition/original/
  h-g-wells_short-fiction.epub
  text/selected-short-fiction/
    the-plattner-story.md
    the-sea-raiders.md
    the-crystal-egg.md
    the-star.md
```

There is no aggregate Markdown conversion of the omnibus. Unselected stories
are therefore unavailable to later text analysis through the retained
derived-text interface.

The four admissible archive members are fixed as:

| Selection ID | EPUB member |
|---|---|
| `the-plattner-story` | `epub/text/the-plattner-story.xhtml` |
| `the-sea-raiders` | `epub/text/the-sea-raiders.xhtml` |
| `the-crystal-egg` | `epub/text/the-crystal-egg.xhtml` |
| `the-star` | `epub/text/the-star.xhtml` |

No other literary member from the omnibus may be converted into the retained
corpus during this phase.

## Registry Model

The retained-source schema gains a `RetainedSourceSelection` model with:

- `id`;
- `title`;
- `first_published`;
- `input`, naming one EPUB archive member;
- `markdown`, naming one story-local derived Markdown path;
- `markdown_sha256`, fingerprinting that derived witness.

`RetainedSourceRecord` gains a `selections` list.
`RetainedSourceFiles.markdown` and `RetainedSourceFiles.markdown_sha256`
become a paired optional value so a record can use one of two mutually
exclusive shapes:

1. a full-work record has one `files.markdown` path, its
   `files.markdown_sha256`, and no retained selections;
2. a bounded omnibus record has no `files.markdown` path and one or more
   retained selections, each with its own Markdown SHA-256.

A record with neither shape or both shapes is invalid. Selection IDs must be
unique within a retained record. Selection Markdown paths must also be unique.

For an admitted source with planned selections, validation requires exact
parity between `admission.yml` and `original/sources.yml` for selection ID,
title, and first-publication year. Missing, extra, renamed, or duplicated
selections are blocking errors. An admitted source without planned selections
must use the full-work shape.

The existing record-level derivation metadata remains the common conversion
method for all selections. Each selection's `input` provides the
selection-specific source member.

## Acquisition and Provenance

Implementation acquires eight approved EPUBs: the seven existing proposed
artifacts plus *King Solomon's Mines*. Each download is made afresh into a
temporary location rather than written directly over a retained source.

Before retention, each candidate must pass:

- successful HTTP retrieval from the admission record's declared URL;
- ZIP integrity;
- exact EPUB `mimetype` validation;
- valid `META-INF/container.xml`;
- presence of every package document referenced by the container;
- presence of every declared derivation input member;
- SHA-256 calculation;
- extraction of available release or revision metadata;
- inspection of provenance and rights metadata;
- deterministic Pandoc conversion of only the declared literary inputs.

The newly observed SHA-256 is committed to `original/sources.yml`. A later
download mismatch is not accepted silently: it requires an explicit source
update decision, metadata review, regenerated derived text, and a committed
fingerprint change.

For Standard Ebooks, the retained record identifies the upstream release and
revision exposed by the downloaded artifact. For Project Gutenberg, the
record identifies the ebook number and the available release or update marker
without inventing a source-control revision.

Every record includes the same provenance fields already used by the four
retained Wells anchors: publisher, homepage, download URL, retrieval date,
derivation command, transcription basis, page-scan basis where known, public
domain context, editorial normalisation, textual limitations, variant
concerns, and rights statement. Unknown scan provenance is recorded honestly
as unavailable in the retained edition metadata rather than guessed.

## Derived Text Rules

Pandoc remains the derivation engine. Conversion uses `gfm-raw_html`, no line
wrapping, and the existing packaging-link filter where applicable. Input
members are passed explicitly in reading order; whole-EPUB conversion is not
used.

Derived text validation requires:

- a regular UTF-8 Markdown file under `original/text/`;
- non-empty literary content;
- no links to endnotes, imprint, colophon, uncopyright, or other excluded
  packaging documents;
- no path escape or absolute path;
- a matching Markdown SHA-256 fingerprint for every full work and retained
  selection;
- for retained selections, an `input` member that exists in the retained EPUB;
- no extra retained selection beyond the four admitted Wells stories.

The Markdown SHA-256 values protect the exact analytical witnesses, not only
the archives from which they were derived. Existing full-work records are
backfilled with the fingerprints of their current canonical Markdown during
this phase.

## Admission Report

`make source-admission STORY=time-expedition` keeps its public command
contract and expands its report to show:

- the final status counts of twelve admitted and one excluded;
- the Tier 4 negative-control restriction;
- the Tier 5 exclusion and post-window diagnostic restriction;
- each retained EPUB path and SHA-256;
- the derived Markdown path and SHA-256 for a full-work record;
- each selected subwork's source member, Markdown path, and Markdown SHA-256;
- blocking parity, path, archive, source-member, content, and fingerprint
  errors;
- any warnings that do not compromise corpus identity.

The report must make the absence of a retained *Lost World* artifact visible
as intentional, not as a missing-file defect. Conversely, the presence of an
artifact for any non-admitted source remains a blocking error.

## Repository Boundaries

Reference sources remain under `stories/time-expedition/original/` and are not
manuscript chapters. Existing story statistics, EPUB/PDF builds, review packs,
AI-writing audits, and Kindle output must continue to exclude this corpus.

No new top-level publication command is required. The existing
`source-admission` command is the corpus trust surface.

Generated admission reports remain under `build/` and are not committed.
EPUB source artifacts and their canonical derived Markdown are committed
because their fingerprints and exact contents define the reproducible study
corpus.

## Testing and Verification

Schema tests will cover:

- valid full-work and omnibus retained-record shapes;
- rejection of records with both or neither Markdown shape;
- duplicate retained selection IDs or Markdown paths;
- invalid selection paths and malformed SHA-256 values;
- missing or mismatched full-work Markdown fingerprints;
- Tier 5 records remaining excluded and absent from retained sources.

Admission checks will cover:

- exact admission-to-retention selection parity;
- missing, extra, or changed retained selections;
- a selection input absent from its EPUB;
- missing, empty, non-UTF-8, or path-escaping selection Markdown;
- selection Markdown fingerprint mismatch;
- excluded packaging links in selection Markdown;
- ordinary full-work validation remaining backward compatible;
- an excluded source requiring no retained artifact;
- an artifact appearing for an excluded source being rejected.

Corpus verification will then run:

1. structural EPUB inspection and SHA-256 verification for all twelve
   retained artifacts;
2. source-member and derived-file verification for all four Wells selections;
3. `make source-admission STORY=time-expedition`;
4. `make check STORY=time-expedition`;
5. `make stats STORY=time-expedition` to confirm source text remains excluded;
6. the complete automated test suite;
7. `git diff --check` and a final worktree review.

Manual verification will inspect the beginning and end of each new derived
text, chapter or story ordering, packaging removal, provenance fields, the
four selected-story boundaries, and the generated admission report.

## Phase 2A Completion Gate

Phase 2A is complete only when:

1. the admission registry contains exactly twelve admitted sources and one
   excluded diagnostic;
2. `original/sources.yml` and the retained files contain exactly the twelve
   admitted source artifacts;
3. all eight newly approved EPUBs have verified integrity, provenance, and
   committed fingerprints;
4. all derived texts are present, readable, bounded, and reproducible;
5. the four Wells short stories are independently addressable and no
   unselected story is admitted through the derived-text interface;
6. the admission report passes with no blocking issue;
7. story checks, statistics exclusion checks, and the complete test suite
   pass;
8. the completed corpus foundation is committed and pushed to the GitHub
   remote.

At that point work stops and is reported for human review before the detailed
Wells study begins.

## Explicitly Deferred

Phase 2A must not create or perform:

- quantitative prose measurements or a Wells baseline;
- close reading or passage annotation;
- findings documents or evidence-ledger claims;
- period-control comparisons beyond assigning and enforcing their roles;
- held-out sampling or authenticity scoring;
- revision of `style-guide.md`, `style-card.md`, or manuscript prose;
- reference packets or chapter authenticity audits;
- research into the end-Permian world;
- *The Last Week of the Permian* Q&A, architecture, outline, scene cards, or
  drafting;
- anthology-spine development;
- acquisition or analysis of *The Lost World*.

The next phase begins only after the human has reviewed the completed corpus
and explicitly authorised detailed Wells analysis.
