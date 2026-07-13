# Time Expedition Foundation Design

Date: 2026-07-13
Status: approved design, awaiting implementation

## Purpose

Establish `stories/time-expedition/` as a buildable, source-backed anthology
workspace for meticulous public-domain pastiches of H. G. Wells's *The Time
Machine*. The anthology's first expedition will be *The Last Week of the
Permian*, but detailed voice study, scientific research, plot architecture,
and prose drafting are outside this foundation pass.

## Story Boundary

`stories/time-expedition/` will be one normal Creative Writer story project,
not a series hub with nested projects. It will therefore work with the
existing `check`, build, statistics, review-pack, AI-audit, and Kindle
interfaces without changes to the CLI.

The project metadata will use:

- title: `Time Expedition`
- slug: `time-expedition`
- kind: `pastiche`
- status: `planning`

The eventual manuscript is a growing anthology. Each expedition will be a
standalone short story, shorter than *The Time Machine* but written in the
same carefully studied mode. Additional expeditions will be added to the same
chapter sequence unless experience later shows that the anthology has
outgrown the existing story boundary. A possible anthology spine is deferred;
the stories do not need a shared narrative arc at this stage.

## Canonical Reference Corpus

The source material will be stored under the story rather than in a global
library:

```text
stories/time-expedition/original/
  README.md
  sources.yml
  h-g-wells_the-time-machine.epub
  h-g-wells_the-invisible-man.epub
  text/
    the-time-machine.md
    the-invisible-man.md
```

The corpus has two explicitly different kinds of authority:

- *The Time Machine* is the sole story-world canon and the primary style
  anchor. It governs the Time Traveller, fictional continuity, framing
  architecture, and the voice of his reported account.
- *The Invisible Man* is a secondary style anchor for Wells's handling of
  sustained dialogue, social interaction, class register, comic friction,
  concealment, and crowd response. It does not add characters, events,
  technology, or world facts to *Time Expedition* continuity.

Compatible EPUBs published by Standard Ebooks will be retained unchanged. The
edition homepages are:

- `https://standardebooks.org/ebooks/h-g-wells/the-time-machine`
- `https://standardebooks.org/ebooks/h-g-wells/the-invisible-man`

The effective compatible EPUB downloads are:

- `https://standardebooks.org/ebooks/h-g-wells/the-time-machine/downloads/h-g-wells_the-time-machine.epub?source=download`
- `https://standardebooks.org/ebooks/h-g-wells/the-invisible-man/downloads/h-g-wells_the-invisible-man.epub?source=download`

`sources.yml` will record for each work:

- work title and author;
- its authority role in this project;
- upstream edition homepage and exact download URL;
- retrieval date;
- local EPUB filename;
- SHA-256 checksum of the downloaded file;
- the public-domain and edition-provenance context;
- the command used to derive the working Markdown.

The checksums pin the exact comparative corpus even if either upstream EPUB is
later corrected or regenerated. The provenance notes will distinguish Wells's
public-domain texts from Standard Ebooks production contributions and will
not present themselves as legal advice.

Pandoc will derive `original/text/the-time-machine.md` from that exact EPUB.
The derivation will select the twelve chapter XHTML files and the epilogue in
spine order, excluding the cover, imprint, colophon, endnotes, and uncopyright
pages. It will similarly derive `original/text/the-invisible-man.md` from that
book's twenty-eight chapter XHTML files and epilogue. The Markdown files are
working material for search, quotation checks, structural comparison, and the
later style study. They are not replacement authorities for the retained
EPUBs. The derived files will preserve chapter headings and the full literary
prose while omitting ebook-only presentation elements.

The `original/` subtree is reference material, not story planning or
manuscript prose. Manuscript statistics will therefore exclude Markdown below
`original/` so the Wells corpus cannot inflate draft-progress totals.

`original/README.md` will explain the relationship among the archival EPUBs,
derived Markdown, and new anthology material. It will state the authority
boundary between the two Wells works and exclude later film, television,
game, audiobook, and illustrated-edition inventions from project canon.

## Initial Story Scaffold

The story will use the repository's complete standard scaffold, including all
mandatory planning files and optional registries. The generic two-chapter
template will be replaced by one provisional chapter unit:

```text
chapter-stubs/01-last-week-of-the-permian.md
manuscript/01-last-week-of-the-permian.md
scene-cards/01-last-week-of-the-permian/
```

The stub summary will explicitly state that the expedition's internal chapter
structure remains unresolved. The manuscript file will contain only an HTML
drafting note, which the statistics layer does not count as prose; the stub
supplies the title during document assembly. No narrative prose will be
written in this pass.

The planning files will record only the decisions already made:

- *Time Expedition* is an anthology of further journeys by Wells's Time
  Traveller;
- Expedition I is *The Last Week of the Permian*;
- *The Time Machine* is the sole story-world canon and primary voice anchor;
- *The Invisible Man* is a secondary style anchor for dialogue and social
  scenes, not a continuity source;
- meticulous source analysis must precede imitation and drafting;
- detailed Permian science, hazards, plot turns, reveal structure, and ending
  logic remain for a later planning phase.

`characters.yml` will contain canonical entries for the Time Traveller and the
unnamed frame narrator. Other character, clue, location, timeline, and plot
device registries will remain empty until the detailed design phase.

`style-card.md` and `style-guide.md` will identify the intended Wells pastiche
and both reference roles, but they will not pretend that the close style study
has already been performed. The later style phase must examine at least the
frame narrator, reported first-person tale, diction, syntax, scientific
exposition, humour, speculative reasoning, descriptive selection, and
rhetorical habits of *The Time Machine*. It will use *The Invisible Man* to
analyse dialogue cadence, social register, interruption, comic friction,
speech attribution, and conversation-driven scene movement.

## Collaboration Contract

The initial contract will keep AI direct editing available while recognising
that substantive drafting has not begun. The human supplies premise, taste,
scientific judgement, and critical calibration. The AI organises the source,
builds planning artifacts, performs the later comparative analysis, and may
draft or revise prose once the style and narrative plans are approved.

The existing lint thresholds and review mechanisms will be retained. No new
model integration or review command is required for this pass.

## Failure Handling

Both EPUB downloads will first land in temporary local paths. They will be
moved into `original/` only after successful transfers and ZIP integrity
checks, so an interrupted request cannot masquerade as a valid source.

Markdown derivation must fail visibly if Pandoc cannot parse either EPUB. Each
derived file must be non-empty and contain representative beginning and ending
text from its Wells work. The recorded checksums must be recomputed from the
final retained EPUBs.

## Verification

Implementation is complete when all of the following hold:

1. The expected story scaffold and `original/` tree exist.
2. Both retained EPUBs pass ZIP archive integrity checks.
3. Their SHA-256 checksums match `sources.yml`.
4. Pandoc successfully produces both non-empty Markdown files with the
   expected chapter structures.
5. Manual spot-checks confirm that each derived text begins and ends at the
   correct points in its Wells work and does not include unrelated material.
6. `make check STORY=time-expedition` passes.
7. Existing repository tests continue to pass.

## Deferred Work

The following work is explicitly deferred:

- close stylistic analysis of Wells's prose;
- a high-resolution Wells style card;
- end-Permian scientific research and terminology policy;
- detailed narrative architecture and chapter decomposition;
- manuscript prose;
- automated source-corpus ingestion or comparison tooling;
- comparison of book, serial, or other public-domain textual variants.
