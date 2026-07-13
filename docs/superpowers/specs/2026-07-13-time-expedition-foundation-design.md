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

The eventual manuscript is a growing anthology. Additional expeditions will
be added to the same chapter sequence unless experience later shows that the
anthology has outgrown the existing story boundary.

## Canonical Source Anchor

The source material will be stored under the story rather than in a global
library:

```text
stories/time-expedition/original/
  README.md
  source.yml
  h-g-wells_the-time-machine.epub
  text/
    the-time-machine.md
```

The compatible EPUB published by Standard Ebooks will be retained unchanged
as the archival source. The edition homepage is:

`https://standardebooks.org/ebooks/h-g-wells/the-time-machine`

The compatible EPUB download is:

`https://standardebooks.org/ebooks/h-g-wells/the-time-machine/dist/h-g-wells_the-time-machine.epub`

`source.yml` will record:

- work title and author;
- upstream edition homepage and exact download URL;
- retrieval date;
- local EPUB filename;
- SHA-256 checksum of the downloaded file;
- the public-domain and edition-provenance context;
- the command used to derive the working Markdown.

The checksum pins the exact comparative anchor even if the upstream EPUB is
later corrected or regenerated. The provenance note will distinguish Wells's
public-domain text from Standard Ebooks production contributions and will not
present itself as legal advice.

Pandoc will derive `original/text/the-time-machine.md` from that exact EPUB.
The Markdown is working material for search, quotation checks, structural
analysis, and later style study. It is not a replacement authority for the
retained EPUB. The derived file will preserve chapter headings and the full
prose but may omit ebook-only presentation elements such as cover art and
navigation pages.

`original/README.md` will explain the relationship between the archival EPUB,
derived Markdown, and new anthology material. It will also state that later
film, television, game, audiobook, and illustrated-edition inventions are not
canonical sources for this project.

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
structure remains unresolved. The manuscript file will contain only front
matter, a title, and a drafting note. No narrative prose will be written in
this pass.

The planning files will record only the decisions already made:

- *Time Expedition* is an anthology of further journeys by Wells's Time
  Traveller;
- Expedition I is *The Last Week of the Permian*;
- Wells's novella is the sole canonical literary anchor at this stage;
- meticulous source analysis must precede imitation and drafting;
- detailed Permian science, hazards, plot turns, reveal structure, and ending
  logic remain for a later planning phase.

`characters.yml` will contain canonical entries for the Time Traveller and the
unnamed frame narrator. Other character, clue, location, timeline, and plot
device registries will remain empty until the detailed design phase.

`style-card.md` and `style-guide.md` will identify the intended Wells pastiche
and the comparative source, but they will not pretend that the close style
study has already been performed. The later style phase must examine at least
the frame narrator, reported first-person tale, diction, syntax, scientific
exposition, humour, speculative reasoning, descriptive selection, and
rhetorical habits of the anchored text.

## Collaboration Contract

The initial contract will keep AI direct editing available while recognising
that substantive drafting has not begun. The human supplies premise, taste,
scientific judgement, and critical calibration. The AI organises the source,
builds planning artifacts, performs the later comparative analysis, and may
draft or revise prose once the style and narrative plans are approved.

The existing lint thresholds and review mechanisms will be retained. No new
model integration or review command is required for this pass.

## Failure Handling

The EPUB download will first land in a temporary local path. It will be moved
into `original/` only after a successful transfer and ZIP integrity check, so
an interrupted request cannot masquerade as a valid source.

Markdown derivation must fail visibly if Pandoc cannot parse the EPUB. The
derived file must be non-empty and contain representative beginning and ending
text from Wells's work. The recorded checksum must be recomputed from the
final retained EPUB.

## Verification

Implementation is complete when all of the following hold:

1. The expected story scaffold and `original/` tree exist.
2. The retained EPUB passes a ZIP archive integrity check.
3. Its SHA-256 checksum matches `source.yml`.
4. Pandoc successfully produces non-empty Markdown with chapter structure.
5. A manual spot-check confirms that the derived text begins and ends at the
   correct points in Wells's work and does not include unrelated material.
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
