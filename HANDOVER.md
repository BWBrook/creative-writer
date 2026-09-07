# Handover to the next writing agent

Prepared 7 September 2026. Read this first, then inspect the live files and Git
state. This is a current orientation, not a transcript or an instruction to
replay earlier work. Barry requested it so a fresh task can start without the
accumulated assumptions of the long preceding conversation.

## The purpose and present focus

Creative Writer is a file-first Python workbench for collaborative human-AI
fiction: Markdown manuscripts, YAML planning, targeted review packs, advisory
checks, and EPUB/PDF output. The AI can lead drafting; Barry supplies premise,
scientific judgement, taste, and consequential creative decisions. Working
fiction is the product. The harness exists to help produce it.

The active project is `stories/time-expedition/`: a recovered anthology of
further journeys by Wells's Time Traveller. Its first expedition, *The Last
Week of the Permian*, is planned at roughly 18,000-22,000 words, with six
numbered chapters and an epilogue. Other story directories are separate work;
do not treat them as part of this tranche.

## What has been accomplished

- The general workbench, planning/coherence tools, review packs, and build
  workflow exist. No fresh scaffold or framework redesign is needed.
- A substantial Wells source study was completed and approved. Phase 2B
  retained six validated and four qualified claims, none strong-confidence;
  most describe practices shared with other period writers. Phase 2C supplies
  the operational style profile, six curated reference packets, advisory lint,
  and review records. It is ready to use, not a research phase to restart.
- The external Permian research report was reviewed and distilled into an
  approved canonical dossier. Detailed story, chapter, and scene architecture
  is committed. Exact period details are checked when a scene needs them.
- Chapter I now has a complete working draft (approximately 2,746 words by
  `wc -w`), a narrow period/canon brief, and a four-excerpt human calibration
  manifest. Chapters II-VI and the epilogue remain placeholders.

The closeout commit includes this handover, Chapter I, its period brief, and
its calibration manifest on `main`, following `afe334a` (chapter-reference
refresh) and `24bb39a` (Permian architecture). Barry authorized committing,
pushing, and clearing redundant branches and worktree residue. The primary
checkout remains `/Users/bwbrook/games/creative-writer`; a fresh checkout of
the resulting `main` also includes all substantive work. Verify live Git state
on arrival rather than relying on this dated note.

Chapter I is preserved for review, not certified as human-accepted. No
completed authenticity review is currently present in `style-reviews/`.

## Creative commitments to carry forward

The priority order is Wellsian authorship authenticity, late-1890s knowledge
and language, internal scientific coherence, then modern scientific
plausibility. Modern science stays backstage. Study narrative method rather
than borrowing distinctive source phrases or sentence skeletons.

*The Time Machine* alone governs canon. Other admitted Wells fiction and
nonfiction have bounded stylistic roles; neighbouring authors are comparative
or negative controls. Lint findings are questions for a reader, never an
authenticity score or a requirement to homogenise prose.

The anonymous narrator frames the testimony; Filby provokes and challenges;
the notebook compresses the baseline; the Traveller's Royal Society account
carries the developing crisis; an examination tests the surviving evidence.
Avoid narrating the same expedition twice through notebook and speech.

The title means about a week of the Traveller's accumulated experience at
four stations across roughly thirty months, not a seven-day global extinction.
Ancient Richmond is a bounded fictional reconstruction: arid northern tropical
high ground, river/plain, saline terminal waters, and a fissure refuge. Heat
and water stress accumulate into biological distress, displacement, then
extreme runoff and refuge failure. The scarred predator acts under ecological
pressure. The revolver buys time; lost evidence limits later claims.

The Society can provisionally accept the journey while disputing global cause
and extent. The Traveller cannot identify Siberia or demonstrate synchrony.
The temporal obstruction and terrestrial anchoring remain unexplained; the
epilogue implies renewed exploration without naming another destination.
Use the current narrative design for precise equipment and surviving exhibits.

## Next useful tranche

The immediate checkpoint is **Chapter I editorial calibration**, then drafting
the expedition using the settled architecture and the resulting feedback.
Read the chapter directly and inspect the four selected passages with Barry.
Judge voice, distinct speakers, the obstruction's intelligibility, and the
departure. Make a focused revision where it matters and record the resulting
judgement using the existing review workflow. Do not infer acceptance from
successful checks or retune thresholds merely to make findings disappear.

This is a recommendation for resuming work, not a new mandate to draft the
whole novella without the user's next instruction. Within an agreed writing
tranche, complete coherent work autonomously; reserve consultation for
consequential creative choices and useful reader judgement. Story/anthology
acceptance requires a human under the existing review contract. Publication,
Kindle sending, and other external actions require their own authorization.

## Small reading route

1. Read `stories/time-expedition/narrative-design.md` and `outline.md` for the
   current story contract; consult individual chapter stubs and scene cards
   only as you reach them.
2. Read `stories/time-expedition/style-guide.md`, then the relevant generated
   reference packets. `style-profile.yml` contains the machine-readable rules
   and provenance if a check needs diagnosis.
3. Read Chapter I, its `chapter-01-period-brief.md`, and the calibration
   manifest. Regenerate `build/time-expedition/reviews/chapter-01-calibration.md`
   with the command below for the selected excerpts.
4. Consult `research/last-week-of-the-permian/canonical-research-dossier.md`
   under the story for science and period boundaries. Its earlier provisional
   architecture choices are resolved by the current narrative design.

The old interview and `docs/superpowers/` plans are background, not a queue to
execute again. The README's old research-next wording has been updated, but
`story.yml` still says `planning` despite the Chapter I draft. Do not infer
progress from that metadata alone. Avoid bulk-loading the original corpus,
external research report, and historical audit artifacts unless needed.

## Skills and practical checks

Use [Twilight Laboratory](/Users/bwbrook/.codex/skills/twilight-laboratory/SKILL.md)
for coherent tranches, inherited decisions, and meaningful human involvement.
Use [Kill Your Darlings](/Users/bwbrook/.codex/skills/kill-your-darlings/SKILL.md)
to keep prose and tooling complexity tied to present value. Neither implies a
new audit, deletion campaign, or extra approval ladder. Use
[Audit AI Writing](/Users/bwbrook/.codex/skills/audit-ai-writing/SKILL.md) for
targeted prose triage when useful, subordinate to the Wells-specific brief.

Python is managed by `uv`; production code is in `src/creative_writer/` and
tests in `tests/`. Run from the repository root:

```sh
git status --short --branch
make check STORY=time-expedition
make style-lint STORY=time-expedition CHAPTER=01-the-obstruction
make review-pack STORY=time-expedition PACK=chapter-01-calibration
make style-reference STORY=time-expedition PACK=frame-and-testimony
```

At handover, coherence passed without blocking issues, chapter lint completed
with seven advisory findings, and the four-entry review pack regenerated
successfully. These establish workflow health, not literary quality. Generated
builds, caches, and ignored historical review scratch files were selected for
closeout cleanup; tracked research and review evidence is retained. `build/`
is disposable and ignored by Git. Review-pack excerpts use line ranges; update
them after revisions. Use `make test` for relevant harness changes; the full
suite and publication builds were not rerun for this documentation-only task.

Begin with the existing prose and Barry's next instruction. The research and
machinery have earned their place only insofar as they help us write the story.
