# Time Expedition Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a source-backed `Time Expedition` anthology workspace whose first planned short story is *The Last Week of the Permian*, anchored to pinned public-domain editions of H. G. Wells's *The Time Machine* and *The Invisible Man* with explicitly different authority roles.

**Architecture:** Keep `stories/time-expedition/` as one ordinary Creative Writer story so all existing commands continue to work. Store both immutable comparative sources and their derived working texts under `original/`, label *The Time Machine* as story-world canon plus primary style anchor and *The Invisible Man* as a secondary dialogue/social-style anchor, keep the first expedition as one provisional chapter unit with zero manuscript prose, and exclude the source corpus from manuscript-progress statistics.

**Tech Stack:** Python 3.12 with `uv`, Pytest, YAML, Markdown, GNU Make, Pandoc 3.10, `curl`, `unzip`, and macOS `shasum`.

## Global Constraints

- `stories/time-expedition/` is a growing anthology, not a nested series hub.
- Each expedition is a standalone short story, shorter than *The Time Machine* but ultimately written in a closely studied Wells mode.
- The first expedition is *The Last Week of the Permian*.
- Do not perform the Wells style study, Permian research, detailed narrative architecture, or prose drafting in this pass.
- Treat *The Time Machine* as the sole story-world canon and primary style anchor.
- Treat *The Invisible Man* as a secondary style anchor for dialogue and social scenes, never as fictional continuity.
- Exclude inventions from later adaptations.
- Retain both downloaded EPUBs byte-for-byte and pin each with SHA-256.
- Derive Markdown only from each book's numbered chapter XHTML files and epilogue, excluding ebook packaging pages.
- Keep the current CLI unchanged.
- Keep generated reports under ignored `build/`; track both EPUBs, provenance, derived Markdown, and story planning sources.

---

### Task 1: Exclude Reference Corpora from Manuscript Statistics

**Files:**

- Modify: `src/creative_writer/stats.py`
- Modify: `tests/test_stats.py`

**Interfaces:**

- Consumes: `generate_story_statistics(root: Path, story_slug: str) -> StoryStatisticsResult`
- Produces: `_supporting_markdown_categories()` behaviour that ignores every Markdown file whose first story-relative path component is `original`

- [ ] **Step 1: Add a failing statistics regression test**

Append this test to `tests/test_stats.py`:

```python
def test_generate_story_statistics_excludes_original_reference_markdown(
    tmp_path: Path,
) -> None:
    story_dir = create_story(tmp_path, "source-backed-story", "pastiche")
    baseline = generate_story_statistics(tmp_path, "source-backed-story")

    original_text_dir = story_dir / "original" / "text"
    original_text_dir.mkdir(parents=True)
    (story_dir / "original" / "README.md").write_text(
        "# Comparative source\n\nReference metadata only.\n",
        encoding="utf-8",
    )
    (original_text_dir / "source-novel.md").write_text(
        "This source corpus must not count as story planning prose.\n" * 100,
        encoding="utf-8",
    )

    result = generate_story_statistics(tmp_path, "source-backed-story")

    assert result.supporting_markdown_words == baseline.supporting_markdown_words
    assert result.total_story_markdown_words == baseline.total_story_markdown_words
```

- [ ] **Step 2: Run the focused test and confirm the regression is exposed**

Run:

```bash
uv run --group dev pytest tests/test_stats.py::test_generate_story_statistics_excludes_original_reference_markdown -v
```

Expected: `FAIL`; `supporting_markdown_words` is greater than the baseline because the current traversal places both source files in `Other markdown`.

- [ ] **Step 3: Implement the narrow exclusion rule**

In `_supporting_markdown_categories()` in `src/creative_writer/stats.py`, replace:

```python
        if relative.parts[0] == "manuscript":
            continue
```

with:

```python
        if relative.parts[0] in {"manuscript", "original"}:
            continue
```

- [ ] **Step 4: Run the focused and complete statistics tests**

Run:

```bash
uv run --group dev pytest tests/test_stats.py -v
```

Expected: all statistics tests pass, including the new source-corpus regression test.

- [ ] **Step 5: Run the full suite**

Run:

```bash
make test
```

Expected: all repository tests pass.

- [ ] **Step 6: Commit the statistics safeguard**

```bash
git add src/creative_writer/stats.py tests/test_stats.py
git commit -m "Exclude source corpora from story statistics"
```

---

### Task 2: Create the Time Expedition Anthology Scaffold

**Files:**

- Create: `stories/time-expedition/` from `templates/story/`
- Modify: `stories/time-expedition/story.yml`
- Modify: `stories/time-expedition/contract.yml`
- Modify: `stories/time-expedition/style-card.md`
- Modify: `stories/time-expedition/style-guide.md`
- Modify: `stories/time-expedition/outline.md`
- Modify: `stories/time-expedition/narrative-design.md`
- Modify: `stories/time-expedition/world.md`
- Modify: `stories/time-expedition/characters.yml`
- Modify: `stories/time-expedition/review-packs/_template.yml`
- Create: `stories/time-expedition/chapter-stubs/01-last-week-of-the-permian.md`
- Create: `stories/time-expedition/manuscript/01-last-week-of-the-permian.md`
- Create: `stories/time-expedition/scene-cards/01-last-week-of-the-permian/README.md`
- Delete: `stories/time-expedition/chapter-stubs/01-opening.md`
- Delete: `stories/time-expedition/chapter-stubs/02-turn.md`
- Delete: `stories/time-expedition/manuscript/01-opening.md`
- Delete: `stories/time-expedition/manuscript/02-turn.md`
- Delete: `stories/time-expedition/scene-cards/01-opening/README.md`
- Delete: `stories/time-expedition/scene-cards/02-turn/README.md`

**Interfaces:**

- Consumes: `make init-story STORY=<slug> KIND=pastiche` and the canonical `templates/story/` tree
- Produces: a valid story at `stories/time-expedition/` with one provisional expedition unit, complete mandatory artifacts, standard optional registries, and no manuscript prose

- [ ] **Step 1: Confirm the destination does not already exist**

Run:

```bash
test ! -e stories/time-expedition
```

Expected: exit status `0`. If it exists, stop and inspect it rather than overwriting it.

- [ ] **Step 2: Generate the standard pastiche scaffold**

Run:

```bash
make init-story STORY=time-expedition KIND=pastiche
```

Expected: the CLI reports creation of `stories/time-expedition` and the complete default scaffold is present.

- [ ] **Step 3: Replace generic chapter units with the provisional Permian expedition**

Delete the six generic chapter-specific files listed above with `apply_patch`. Create `chapter-stubs/01-last-week-of-the-permian.md` with:

```markdown
---
title: "The Last Week of the Permian"
summary: "Provisional container for Expedition I; its internal chapter and scene structure remains unresolved pending the Wells style study, Permian research, and detailed narrative design."
manuscript: "manuscript/01-last-week-of-the-permian.md"
scene_cards_dir: "scene-cards/01-last-week-of-the-permian"
characters:
  - time-traveller
  - frame-narrator
locations: []
clues_introduced: []
clues_resolved: []
plot_devices: []
timeline_events: []
images: []
---

## Expedition purpose

Establish the first standalone short story in the *Time Expedition* anthology.

## Known premise

The Time Traveller visits Earth during the final week of the Permian. The
reason for the journey, exact arrival conditions, scientific observations,
hazards, dramatic structure, and outcome remain uncommitted.

## Planning status

- Complete a close study of the anchored Wells text before prescribing voice.
- Research the end-Permian setting before fixing events or terminology.
- Expand this provisional unit into the required chapter and scene structure
  only after the style and narrative plans are approved.

## Continuity notes

- Wells's *The Time Machine* is the sole story-world canon.
- *The Invisible Man* may inform dialogue and social handling but contributes
  no story-world continuity.
- Do not import material invented by later adaptations.
- Each expedition must stand alone even if an anthology spine is added later.
```

Create `manuscript/01-last-week-of-the-permian.md` with this single HTML comment so statistics report zero prose words:

```markdown
<!-- Drafting note: narrative prose begins only after the Wells style study and the Permian narrative plan are approved. -->
```

Create `scene-cards/01-last-week-of-the-permian/README.md` with:

```markdown
# The Last Week of the Permian Scene Cards

No scene cards are committed yet. After the expedition architecture is
approved, copy or adapt [`../_template.md`](../_template.md) for each scene.
```

- [ ] **Step 4: Set story metadata and collaboration authority**

Replace `story.yml` with:

```yaml
title: "Time Expedition"
slug: "time-expedition"
kind: "pastiche"
status: "planning"
language: "en-AU"
target_outputs:
  - epub
  - pdf
chapters:
  - chapter-stubs/01-last-week-of-the-permian.md
```

Replace `contract.yml` with:

```yaml
human_role: "Supply premises, scientific judgement, taste, and critical calibration for the anthology and its individual expeditions."
ai_role: "Organise canonical sources and planning artifacts, perform the approved comparative style analysis, and draft or revise prose only after the relevant style and narrative plans are settled."
authority_mode: direct_edit
review_mode: git_diff
lint:
  em_dash:
    enabled: true
    max_per_chapter: 2
  contrastive_parallelism:
    enabled: true
    max_instances_per_chapter: 1
```

- [ ] **Step 5: Record the provisional voice boundary**

Replace `style-card.md` with:

```markdown
# Style Card: Wellsian Time Expedition (Provisional)

## Status

This file identifies the intended source tradition but is not yet a usable
voice prescription. Replace it with a high-resolution style card only after a
close comparative study of the two anchored source texts in their assigned
roles.

## Canonical anchor

- H. G. Wells, *The Time Machine* (1895): story-world canon and primary style
  anchor.
- H. G. Wells, *The Invisible Man* (1897): secondary style anchor for
  dialogue and social scenes only.
- Local archival EPUBs and derived texts: `original/`.
- Later adaptations are outside the project canon.

## Required future analysis

- the unnamed frame narrator and the reported first-person account;
- diction, syntax, cadence, and paragraph movement;
- scientific exposition and speculative inference;
- humour, scepticism, social observation, and rhetorical qualification;
- descriptive selection, action, suspense, and endings;
- dialogue cadence, social register, interruption, speech attribution, comic
  friction, and conversation-driven scene movement in *The Invisible Man*.

## Current constraint

Do not draft pastiche prose from general recollection or a generic idea of
"Victorian" style. The anchored texts and their authority roles must govern
the later style card.
```

Replace `style-guide.md` with:

```markdown
# Style Guide

## Status

Provisional until the Wells source study is complete.

## Intended form

- Each expedition is a standalone short story within the anthology.
- Each story should be shorter than *The Time Machine*.
- The final voice should read as a meticulous continuation of Wells's own
  narrative mode, not as modern prose with period decoration.

## Things to lean toward

- Source-led decisions supported by passages in both derived texts, with *The
  Time Machine* controlling any conflict between them.
- A coherent relationship between frame, traveller's account, observation,
  inference, and speculation.
- Scientific curiosity and disciplined selection of concrete detail.

## Things to avoid

- Material originating in film, television, game, audiobook, or illustrated
  adaptations.
- Continuity, Time Traveller characterisation, or frame architecture imported
  from *The Invisible Man*.
- Generic steampunk, generic Victorian diction, or modern cinematic action.
- Unexamined modern idiom and familiar AI-writing abstractions.
- Treating these provisional notes as a substitute for the later style study.
```

- [ ] **Step 6: Record only the approved anthology and Expedition I decisions**

Replace `outline.md` with:

```markdown
# Outline

## Anthology premise

*Time Expedition* is a growing anthology of further journeys by H. G. Wells's
Time Traveller. Each expedition is a standalone short story, shorter than the
original novella but ultimately written in the same carefully studied mode.

## Anthology structure

The stories do not currently require a shared narrative arc. A framing spine
may be designed later without being assumed here.

## Expedition sequence

1. *The Last Week of the Permian* - planning.

## Expedition I: known premise

The Time Traveller visits Earth during the final week of the Permian.

## Provisional chapter order

1. `01-last-week-of-the-permian.md` - temporary container for the entire first
   expedition until detailed architecture determines its real chapter units.

## Deferred design questions

- Why does the Time Traveller choose or reach this date?
- How does he understand a world for which Victorian science has incomplete
  concepts and evidence?
- Which environmental and biological changes occur within his visit?
- What immediate pressure makes the account a story rather than a travelogue?
- How is the account framed, reported, and concluded?
- What anthology spine, if any, should connect later expeditions?
```

Replace `narrative-design.md` with:

```markdown
# Narrative Design

## Narrative anchor

A growing anthology of standalone short expeditions by Wells's Time Traveller.
The first sends him to the final week of the Permian, but its story mechanism
is not yet fixed.

## POV and lens

- Primary viewpoint: unresolved pending close study of Wells's frame and
  reported first-person architecture.
- Narrative distance: unresolved.
- What this lens lets the story notice: to be derived from the source study
  and scientific design rather than assumed in advance.

## Dramatic question

Not fixed. Scientific research and narrative planning must establish the
immediate pressure of the Permian expedition.

## Thematic question

Not fixed. The story should earn its speculative concern from the encounter
between a late-Victorian mind and deep-time ecological catastrophe.

## Ending logic

- What must be resolved: deferred until the expedition mechanism is chosen.
- What should remain open: deferred.
- What final note or image should the story land on: deferred.

## Reveal structure and clue ladder

The reveal sequence will be designed after the scientific evidence, the Time
Traveller's available concepts, and the story's pressure are established.

## Drift risks and handoff notes

- Preserve each expedition as a standalone short story.
- Do not impose a shared anthology arc before the spine is deliberately designed.
- Avoid generic Victorian, steampunk, disaster-film, or modern hard-SF voices.
- Keep later-adaptation inventions outside the canon.
- Do not let present-day terminology bypass the Time Traveller's own process
  of observation, analogy, error, and inference.
```

Replace `world.md` with:

```markdown
# World Notes

## Canonical literary world

- H. G. Wells's *The Time Machine* is the sole story-world canon and primary
  style anchor.
- H. G. Wells's *The Invisible Man* is a secondary style anchor for dialogue
  and social scenes only.
- The retained Standard Ebooks EPUBs and derived Markdown live under `original/`.
- Later adaptation-specific characters, dialogue, machinery, and visual
  designs are not canonical here.

## Anthology scope

- Each expedition is a shorter standalone adventure of the Time Traveller.
- A possible anthology spine is uncommitted and need not create a narrative arc.

## Expedition I

- Working title: *The Last Week of the Permian*.
- Setting: Earth during the final week of the Permian.
- Detailed geography, chronology, atmosphere, fauna, flora, hazards, and
  Victorian terminology await the dedicated scientific planning phase.
```

- [ ] **Step 7: Seed only canonical characters and update the review manifest example**

Replace `characters.yml` with:

```yaml
characters:
  - id: time-traveller
    name: "The Time Traveller"
    role: "Inventor of the Time Machine and principal witness of the expeditions."
    motivation: "To investigate time directly and test speculative reasoning against observation."
  - id: frame-narrator
    name: "The unnamed frame narrator"
    role: "Member of the Time Traveller's circle who records and mediates his account."
    motivation: "To preserve the account while retaining a thoughtful measure of uncertainty."
```

Keep `clues.yml`, `locations.yml`, `timeline.yml`, and `plot_devices.yml` empty. Replace `review-packs/_template.yml` with:

```yaml
title: "First human pass"
purpose: "Select a few passages for targeted human feedback after prose drafting begins."
entries:
  - id: expedition-opening-example
    label: "Expedition opening"
    manuscript: "manuscript/01-last-week-of-the-permian.md"
    start_line: 1
    end_line: 1
    kind: confidence
    question: "Does this opening establish the intended Wellsian narrative mode?"
    context: "Replace this example range after the manuscript contains reviewable prose."
```

- [ ] **Step 8: Validate the story scaffold**

Run:

```bash
make check STORY=time-expedition
```

Expected: `PASS` with no blocking errors. The coherence report is written to `build/time-expedition/reports/coherence-report.md`, and the chapter summary shows two registered characters, no plot devices, and zero real scene cards.

- [ ] **Step 9: Confirm manuscript statistics remain at zero**

Run:

```bash
make stats STORY=time-expedition
rg -n "Total manuscript words: 0|Chapters with manuscript words: 0" build/time-expedition/reports/ms-statistics.md
```

Expected: both zero-value lines are present.

- [ ] **Step 10: Commit the anthology scaffold**

```bash
git add stories/time-expedition
git commit -m "Scaffold Time Expedition anthology"
```

---

### Task 3: Pin and Derive the Primary Wells Anchor

**Files:**

- Create: `stories/time-expedition/original/README.md`
- Create: `stories/time-expedition/original/sources.yml`
- Create: `stories/time-expedition/original/h-g-wells_the-time-machine.epub`
- Create: `stories/time-expedition/original/text/the-time-machine.md`

**Interfaces:**

- Consumes: the Standard Ebooks *Time Machine* compatible EPUB endpoint, `unzip`, and Pandoc's HTML reader plus `gfm-raw_html` writer
- Produces: the story-world canon and primary style anchor as an immutable EPUB pinned to SHA-256 `ab1e79b320d93de15df26bd1c39211dd2c09bc15138f85d8ff115f86338d1f91`, plus a clean thirteen-section Markdown corpus containing chapters I-XII and the epilogue

- [ ] **Step 1: Download to a temporary path and verify the artifact before installation**

Run in `zsh`:

```zsh
tmpdir=$(mktemp -d /tmp/time-expedition-source.XXXXXX)
curl --fail --location --retry 3 --silent --show-error \
  --output "$tmpdir/h-g-wells_the-time-machine.epub" \
  "https://standardebooks.org/ebooks/h-g-wells/the-time-machine/downloads/h-g-wells_the-time-machine.epub?source=download"
file "$tmpdir/h-g-wells_the-time-machine.epub"
unzip -t "$tmpdir/h-g-wells_the-time-machine.epub"
shasum -a 256 "$tmpdir/h-g-wells_the-time-machine.epub"
```

Expected:

- `file` identifies an `EPUB document`;
- `unzip` ends with `No errors detected in compressed data`;
- SHA-256 is `ab1e79b320d93de15df26bd1c39211dd2c09bc15138f85d8ff115f86338d1f91`.

If the checksum differs, stop. Reinspect the Standard Ebooks colophon and revision before deciding whether the upstream edition changed; do not silently install a different artifact under the recorded fingerprint.

- [ ] **Step 2: Install the verified EPUB and derive literary-text-only Markdown**

Continue in the same `zsh` shell:

```zsh
mkdir -p stories/time-expedition/original/text
mv "$tmpdir/h-g-wells_the-time-machine.epub" \
  stories/time-expedition/original/h-g-wells_the-time-machine.epub
unzip -q stories/time-expedition/original/h-g-wells_the-time-machine.epub \
  -d "$tmpdir/unpacked"
chapter_files=("$tmpdir"/unpacked/epub/text/chapter-{1..12}.xhtml)
pandoc "${chapter_files[@]}" \
  "$tmpdir/unpacked/epub/text/epilogue.xhtml" \
  --from=html \
  --to=gfm-raw_html \
  --wrap=none \
  --output=stories/time-expedition/original/text/the-time-machine.md
rm -rf "$tmpdir"
```

Expected: the retained EPUB exists under `original/`, and the Markdown file is approximately 181 KB with thirteen level-two headings.

- [ ] **Step 3: Add exact source provenance**

Create `original/sources.yml` with:

```yaml
sources:
  - id: "the-time-machine"
    role:
      story_world_canon: true
      primary_style_anchor: true
      secondary_style_anchor: false
      focus: "Time Traveller continuity, frame architecture, reported first-person voice, scientific exposition, and speculative method."
    work:
      title: "The Time Machine"
      author: "H. G. Wells"
      first_published: 1895
    edition:
      publisher: "Standard Ebooks"
      homepage: "https://standardebooks.org/ebooks/h-g-wells/the-time-machine"
      download_url: "https://standardebooks.org/ebooks/h-g-wells/the-time-machine/downloads/h-g-wells_the-time-machine.epub?source=download"
      upstream_release: "2026-06-30T02:48:51Z"
      upstream_revision: "5032b60"
    retrieved: "2026-07-13"
    files:
      epub: "h-g-wells_the-time-machine.epub"
      epub_sha256: "ab1e79b320d93de15df26bd1c39211dd2c09bc15138f85d8ff115f86338d1f91"
      markdown: "text/the-time-machine.md"
    derivation:
      tool: "Pandoc 3.10"
      input: "epub/text/chapter-1.xhtml through chapter-12.xhtml, then epub/text/epilogue.xhtml"
      writer: "gfm-raw_html"
      wrap: "none"
    provenance:
      transcription: "Project Gutenberg ebook 35, produced by Distributed Proofreaders"
      page_scans: "Google Books volume Y0pAAQAAIAAJ"
    rights:
      source_text: "Public-domain Wells text; users should verify the law applicable in their jurisdiction. This record is provenance, not legal advice."
      standard_ebooks_contributions: "Dedicated to the worldwide public domain under CC0 1.0 by Standard Ebooks contributors."
```

- [ ] **Step 4: Document authority, scope, and reproducibility**

Create `original/README.md` with:

````markdown
# Original Reference Corpus

This subtree retains the primary canonical and comparative sources for the
*Time Expedition* anthology. It is reference material, not anthology
manuscript or planning prose.

## Files

- `h-g-wells_the-time-machine.epub`: unchanged compatible EPUB downloaded
  from Standard Ebooks.
- `sources.yml`: authority roles, edition provenance, retrieval details,
  checksums, and derivation metadata.
- `text/the-time-machine.md`: working Markdown containing Wells's chapters
  I-XII and epilogue in source order.

At this intermediate commit, *The Time Machine* is the story-world canon and
primary style anchor. Task 4 installs the approved secondary dialogue and
social-style anchor.

The EPUB is the archival authority for this source. The Markdown exists for
search, structural comparison, quotation checks, and the later Wells style
study. Regenerate it from the pinned EPUB rather than editing it as though it
were anthology prose.

## Authority boundary

*The Time Machine* controls Time Traveller continuity, frame architecture,
reported voice, scientific exposition, and speculative method. Do not import
dialogue, characters, machine designs, visual motifs, or other inventions from
later film, television, game, audiobook, or illustrated adaptations.

## Reproduce the Time Machine Markdown

From the repository root in `zsh`:

```zsh
tmpdir=$(mktemp -d /tmp/time-expedition-extract.XXXXXX)
trap 'rm -rf "$tmpdir"' EXIT
unzip -q stories/time-expedition/original/h-g-wells_the-time-machine.epub \
  -d "$tmpdir/unpacked"
chapter_files=("$tmpdir"/unpacked/epub/text/chapter-{1..12}.xhtml)
pandoc "${chapter_files[@]}" \
  "$tmpdir/unpacked/epub/text/epilogue.xhtml" \
  --from=html \
  --to=gfm-raw_html \
  --wrap=none \
  --output=stories/time-expedition/original/text/the-time-machine.md
```

The extraction deliberately excludes the cover, imprint, endnotes, colophon,
and uncopyright pages. See `sources.yml` for the pinned artifact fingerprint
and upstream provenance. The rights note there records source context and is
not legal advice.
````

- [ ] **Step 5: Verify the retained source and derived text**

Run:

```bash
test "$(shasum -a 256 stories/time-expedition/original/h-g-wells_the-time-machine.epub | awk '{print $1}')" = "ab1e79b320d93de15df26bd1c39211dd2c09bc15138f85d8ff115f86338d1f91"
test "$(rg -c '^## (I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|Epilogue)$' stories/time-expedition/original/text/the-time-machine.md)" -eq 13
rg -q '^The Time Traveller \(for so it will be convenient to speak of him\) was expounding' stories/time-expedition/original/text/the-time-machine.md
rg -q 'two strange white flowers.*shrivelled now' stories/time-expedition/original/text/the-time-machine.md
! rg -q '^## (Imprint|Endnotes|Colophon|Uncopyright)$' stories/time-expedition/original/text/the-time-machine.md
test "$(wc -c < stories/time-expedition/original/text/the-time-machine.md)" -gt 180000
```

Expected: every command exits `0`; the text has exactly thirteen literary section headings, contains the opening and final evidentiary image, excludes packaging sections, and exceeds 180 KB.

- [ ] **Step 6: Run intermediate story verification**

Run:

```bash
make check STORY=time-expedition
make stats STORY=time-expedition
rg -n "Total manuscript words: 0|Chapters with manuscript words: 0" build/time-expedition/reports/ms-statistics.md
! rg -q "32,278|Original Reference Corpus" build/time-expedition/reports/ms-statistics.md
make test
git diff --check
```

Expected:

- story check passes with no blocking errors;
- manuscript statistics remain at zero and do not include the source novel;
- all repository tests pass;
- `git diff --check` reports no whitespace errors.

- [ ] **Step 7: Commit the primary anchor**

```bash
git add stories/time-expedition/original
git commit -m "Anchor Time Expedition to The Time Machine"
```

---

### Task 4: Add The Invisible Man as a Dialogue and Social-Style Comparator

**Files:**

- Create: `stories/time-expedition/original/h-g-wells_the-invisible-man.epub`
- Create: `stories/time-expedition/original/text/the-invisible-man.md`
- Modify: `stories/time-expedition/original/sources.yml`
- Modify: `stories/time-expedition/original/README.md`

**Interfaces:**

- Consumes: the Standard Ebooks *Invisible Man* compatible EPUB endpoint, `unzip`, and Pandoc's HTML reader plus `gfm-raw_html` writer
- Produces: a secondary style anchor, explicitly excluded from fictional continuity, pinned to SHA-256 `31e36b331983cb324629b21429c17c3408ec4801b324350fb7cc662e7ad94b71`, plus clean Markdown containing chapters I-XXVIII and the epilogue

- [ ] **Step 1: Download and verify The Invisible Man before installation**

Run in `zsh`:

```zsh
tmpdir=$(mktemp -d /tmp/invisible-man-source.XXXXXX)
curl --fail --location --retry 3 --silent --show-error \
  --output "$tmpdir/h-g-wells_the-invisible-man.epub" \
  "https://standardebooks.org/ebooks/h-g-wells/the-invisible-man/downloads/h-g-wells_the-invisible-man.epub?source=download"
file "$tmpdir/h-g-wells_the-invisible-man.epub"
unzip -t "$tmpdir/h-g-wells_the-invisible-man.epub"
shasum -a 256 "$tmpdir/h-g-wells_the-invisible-man.epub"
```

Expected:

- `file` identifies an `EPUB document`;
- `unzip` ends with `No errors detected in compressed data`;
- SHA-256 is `31e36b331983cb324629b21429c17c3408ec4801b324350fb7cc662e7ad94b71`.

If the checksum differs, stop and inspect the current Standard Ebooks colophon and revision before changing the recorded fingerprint.

- [ ] **Step 2: Install the EPUB and derive dialogue-ready Markdown**

Continue in the same `zsh` shell:

```zsh
mv "$tmpdir/h-g-wells_the-invisible-man.epub" \
  stories/time-expedition/original/h-g-wells_the-invisible-man.epub
unzip -q stories/time-expedition/original/h-g-wells_the-invisible-man.epub \
  -d "$tmpdir/unpacked"
chapter_files=("$tmpdir"/unpacked/epub/text/chapter-{1..28}.xhtml)
pandoc "${chapter_files[@]}" \
  "$tmpdir/unpacked/epub/text/epilogue.xhtml" \
  --from=html \
  --to=gfm-raw_html \
  --wrap=none \
  --output=stories/time-expedition/original/text/the-invisible-man.md
rm -rf "$tmpdir"
```

Expected: the retained EPUB exists under `original/`, and the Markdown is approximately 281 KB with twenty-nine level-two headings.

- [ ] **Step 3: Add the secondary source record to `sources.yml`**

Append this item under the existing `sources:` list:

```yaml
  - id: "the-invisible-man"
    role:
      story_world_canon: false
      primary_style_anchor: false
      secondary_style_anchor: true
      focus: "Sustained dialogue, social interaction, class register, comic friction, concealment, speech attribution, and crowd response."
    work:
      title: "The Invisible Man"
      author: "H. G. Wells"
      first_published: 1897
    edition:
      publisher: "Standard Ebooks"
      homepage: "https://standardebooks.org/ebooks/h-g-wells/the-invisible-man"
      download_url: "https://standardebooks.org/ebooks/h-g-wells/the-invisible-man/downloads/h-g-wells_the-invisible-man.epub?source=download"
      upstream_release: "2026-06-30T02:48:51Z"
      upstream_revision: "5d64618"
    retrieved: "2026-07-13"
    files:
      epub: "h-g-wells_the-invisible-man.epub"
      epub_sha256: "31e36b331983cb324629b21429c17c3408ec4801b324350fb7cc662e7ad94b71"
      markdown: "text/the-invisible-man.md"
    derivation:
      tool: "Pandoc 3.10"
      input: "epub/text/chapter-1.xhtml through chapter-28.xhtml, then epub/text/epilogue.xhtml"
      writer: "gfm-raw_html"
      wrap: "none"
    provenance:
      transcription: "Project Gutenberg ebook 5230, produced by Andrew Sly"
      page_scans: "Google Books volume vdAOAAAAIAAJ"
    rights:
      source_text: "Public-domain Wells text; users should verify the law applicable in their jurisdiction. This record is provenance, not legal advice."
      standard_ebooks_contributions: "Dedicated to the worldwide public domain under CC0 1.0 by Standard Ebooks contributors."
```

- [ ] **Step 4: Replace the intermediate corpus README with the final authority map**

Replace `original/README.md` with:

````markdown
# Original Reference Corpus

This subtree retains the canonical and comparative Wells sources for the
*Time Expedition* anthology. It is reference material, not anthology
manuscript or planning prose.

## Authority map

- *The Time Machine* is the sole story-world canon and primary style anchor.
  It governs the Time Traveller, fictional continuity, frame architecture,
  reported first-person voice, scientific exposition, and speculative method.
- *The Invisible Man* is a secondary style anchor for sustained dialogue,
  social interaction, class register, comic friction, concealment, speech
  attribution, and crowd response. It contributes no fictional continuity to
  *Time Expedition*.

Where the books differ, *The Time Machine* governs the new expeditions.

## Files

- `h-g-wells_the-time-machine.epub`: unchanged compatible Standard Ebooks EPUB.
- `h-g-wells_the-invisible-man.epub`: unchanged compatible Standard Ebooks EPUB.
- `sources.yml`: authority roles, provenance, retrieval details, checksums,
  and derivation metadata for both works.
- `text/the-time-machine.md`: chapters I-XII and epilogue in source order.
- `text/the-invisible-man.md`: chapters I-XXVIII and epilogue in source order.

The EPUBs are the archival authorities for this checkout. The Markdown exists
for search, structural comparison, quotation checks, and the later Wells style
study. Regenerate derived text from the pinned EPUBs rather than editing it as
anthology prose.

## Canon boundary

Do not import dialogue, characters, events, technology, machine designs,
visual motifs, or other inventions from later film, television, game,
audiobook, or illustrated adaptations. Do not treat *The Invisible Man* as
evidence for the fictional continuity or narrator architecture of *Time
Expedition*.

## Reproduce the Markdown

From the repository root in `zsh`:

```zsh
tmpdir=$(mktemp -d /tmp/time-expedition-extract.XXXXXX)
trap 'rm -rf "$tmpdir"' EXIT

unzip -q stories/time-expedition/original/h-g-wells_the-time-machine.epub \
  -d "$tmpdir/time-machine"
time_machine_chapters=("$tmpdir"/time-machine/epub/text/chapter-{1..12}.xhtml)
pandoc "${time_machine_chapters[@]}" \
  "$tmpdir/time-machine/epub/text/epilogue.xhtml" \
  --from=html --to=gfm-raw_html --wrap=none \
  --output=stories/time-expedition/original/text/the-time-machine.md

unzip -q stories/time-expedition/original/h-g-wells_the-invisible-man.epub \
  -d "$tmpdir/invisible-man"
invisible_man_chapters=("$tmpdir"/invisible-man/epub/text/chapter-{1..28}.xhtml)
pandoc "${invisible_man_chapters[@]}" \
  "$tmpdir/invisible-man/epub/text/epilogue.xhtml" \
  --from=html --to=gfm-raw_html --wrap=none \
  --output=stories/time-expedition/original/text/the-invisible-man.md
```

Both extractions deliberately exclude covers, imprints, colophons,
uncopyright pages, and other ebook packaging. See `sources.yml` for pinned
fingerprints and upstream provenance. The rights records there are not legal
advice.
````

- [ ] **Step 5: Verify the secondary source and authority metadata**

Run:

```bash
test "$(shasum -a 256 stories/time-expedition/original/h-g-wells_the-invisible-man.epub | awk '{print $1}')" = "31e36b331983cb324629b21429c17c3408ec4801b324350fb7cc662e7ad94b71"
test "$(rg -c '^## (I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX|XXI|XXII|XXIII|XXIV|XXV|XXVI|XXVII|XXVIII|Epilogue)$' stories/time-expedition/original/text/the-invisible-man.md)" -eq 29
rg -q '^The stranger came early in February' stories/time-expedition/original/text/the-invisible-man.md
rg -q 'So he lapses into a dream, the undying wonderful dream of his life' stories/time-expedition/original/text/the-invisible-man.md
! rg -q '^## (Imprint|Endnotes|Colophon|Uncopyright)$' stories/time-expedition/original/text/the-invisible-man.md
test "$(wc -c < stories/time-expedition/original/text/the-invisible-man.md)" -gt 280000
rg -q 'story_world_canon: true' stories/time-expedition/original/sources.yml
rg -q 'story_world_canon: false' stories/time-expedition/original/sources.yml
```

Expected: every command exits `0`; the comparator has exactly twenty-nine literary sections, the correct opening and epilogue ending, no packaging sections, and an explicit non-canon role.

- [ ] **Step 6: Run complete verification**

Run:

```bash
make check STORY=time-expedition
make stats STORY=time-expedition
rg -n "Total manuscript words: 0|Chapters with manuscript words: 0" build/time-expedition/reports/ms-statistics.md
! rg -q "32,278|48,405|Original Reference Corpus" build/time-expedition/reports/ms-statistics.md
make test
git diff --check
```

Expected:

- story check passes with no blocking errors;
- manuscript statistics remain at zero and exclude both source works;
- all repository tests pass;
- `git diff --check` reports no whitespace errors.

- [ ] **Step 7: Commit the complete reference corpus and planning records**

```bash
git add stories/time-expedition/original
git commit -m "Add Wells dialogue style comparator"
```

- [ ] **Step 8: Confirm the final local state**

Run:

```bash
git status --short
git log -6 --oneline --decorate
```

Expected: worktree clean; the four implementation commits and the design and planning commits are visible on `main`. Do not push unless the user requests it.
