# Creative Writer

A file-first workbench for writing fiction with an AI collaborator. Stories are
Markdown and YAML under `stories/<slug>/`; the tooling checks them for
continuity, reviews their prose against declared evidence, and builds EPUB and
PDF output. The harness exists to help write the story, not the other way
round.

## Current work

The active project is `stories/time-expedition/`, a recovered anthology of
further journeys by H. G. Wells's Time Traveller. Its first expedition, *The
Last Week of the Permian*, is complete in first draft: six numbered chapters
and an epilogue, revised after collaborator critique and ready for Barry's
full read. Fable passed the epilogue's Wells-1895 calibration; Astra completed
his four local repairs without reopening the settled passages. The chapter
review packs and continuity briefs record the decisions. Story acceptance
remains with Barry. The story contract is in `narrative-design.md` and
`outline.md`; the Permian science and its Victorian translation are in
`research/last-week-of-the-permian/`.

Drafting alternates between two AI collaborators, each acting as critic on the
other's chapter, with Barry as the final human reader. Review judgements live
in review-pack manifests, commit messages, and the conversation that produced
them; there is no separate review-record format.

The other three story directories are earlier or separate work and are not
part of this tranche.

## Story layout

- `story.yml`: title, kind, status, language, and chapter order
- `contract.yml`: human/AI roles, lint thresholds, and the optional style profile
- `style-card.md`: the inherited style family; `style-guide.md`: story-specific guidance
- `outline.md`, `narrative-design.md`, `world.md`: the story contract
- `characters.yml`, `clues.yml`, `plot_devices.yml`, `locations.yml`, `timeline.yml`: registries that chapter stubs reference by ID
- `chapter-stubs/`: one planning file per chapter with YAML front matter
- `scene-cards/<chapter>/`: scene-level planning
- `manuscript/`: the prose
- `review-packs/`: manifests that select line ranges for targeted human review
- `assets/images/`: embedded images

New stories are scaffolded from `templates/story/`; style cards live in
`templates/style-cards/`.

## Commands

```bash
make init-story STORY=my-story KIND=original [STYLE_CARD=<card-key-or-path>]
make style-cards
make check STORY=<slug>
make stats STORY=<slug>
make review-pack STORY=<slug> PACK=<name>
make style-lint STORY=<slug> [CHAPTER=<chapter>] [PROFILE=<path>]
make style-reference STORY=<slug> PACK=<name> [PROFILE=<path>]
make ai-audit STORY=<slug>
make epub STORY=<slug>
make pdf STORY=<slug>
make test
```

Every target wraps `uv run creative-writer <command>`; `creative-writer --help`
lists the full CLI. Generated reports and builds land under `build/` and are
not tracked.

`check` validates the story files, cross-references every ID a chapter stub
uses against the registries, and, when a style profile is configured, validates
the profile's provenance and packet manifests. It writes
`build/<slug>/reports/coherence-report.md` and fails only on blocking problems;
the em-dash and contrastive-parallelism thresholds in `contract.yml` produce
warnings.

`stats` writes per-chapter word counts, totals, and reading time to
`build/<slug>/reports/ms-statistics.md`.

`review-pack` renders a manifest from `stories/<slug>/review-packs/<pack>.yml`
to `build/<slug>/reviews/<pack>.md`: each entry is an inclusive line range,
labelled `confidence` or `uncertainty`, with one question for the reader. Line
ranges must be refreshed after a revision.

`ai-audit` runs the external `audit-ai-writing` scanner over the manuscript and
writes `build/<slug>/reports/ai-writing-audit.md`. The scanner is read from
`~/.codex/skills/audit-ai-writing/scripts/audit_ai_writing.py` unless
`CREATIVE_WRITER_AI_AUDIT_SCRIPT` says otherwise. Treat its hits as prompts;
on Chapter I of the Wells pastiche every hit was a false positive.

## Style lint

A story opts into evidence-linked style review through `contract.yml`:

```yaml
style_lint:
  profile: style-profile.yml
  generic_ai_audit: true
```

The profile binds rules to a closed source study by SHA-256. For
`time-expedition` that study is the Wells Phase 2B evidence layer under
`source-study/`: an evidence ledger of six validated and four qualified claims,
a validation record, and three hash-pinned passage indexes over the admitted
corpus in `original/`. The code that produced the study was retired once the
study closed and is in Git history before commit `099ae07`.

`style-lint` writes `build/<slug>/style/lint-report.md` and `.json`, or a
per-chapter pair under `build/<slug>/style/chapters/` when `CHAPTER` is given.
The Markdown report lists findings first, each with its manuscript excerpt and
one editorial question, then the practice questions for the chapter's declared
roles, the contextual diagnostics with their measurements, the anti-drift
questions, and an appendix of rule limits and source passages. Where a
diagnostic tolerance carries a reference value, the note cites it — for
example, the sentence-length p90 measured against *The Time Machine*'s Phase
2B value. Findings are advisory prompts, never a score or an authorship
verdict, and never change the prose.

`style-reference` compiles one manifest from `style-reference-packets/` into
`build/<slug>/style/reference-packets/<pack>.md`, with the focal passage, its
context, and its selection provenance. Reference text is for studying method,
evidentiary sequence, and cadence; do not borrow distinctive phrases, sentence
skeletons, or images.

Findings do not mutate the profile. A profile change increments its version and
records its basis in `change_basis` and the commit.

## Novellas and Kindle

The repo can round-trip DOCX with the OneDrive-synced `Documents/Novellas`
folder and email a built EPUB to a Send-to-Kindle address:

```bash
make novellas-path
make import-novella FILE="Title.docx"
make export-novella INPUT="stories/<slug>/manuscript/01-chapter.md" OUTPUT="Title Chapter 1.docx"
make clear-ingested STORY=<slug>
make kindle-preflight STORY=<slug>
make kindle STORY=<slug>
make kindle-store-password
```

Imports land under `ingested/`; set `CREATIVE_WRITER_NOVELLAS_DIR` if the sync
path differs. Kindle delivery reads the untracked `.creative-writer.local.yml`
(copy `config/kindle.example.yml`), resolves the SMTP password from the
environment or macOS Keychain, and `kindle-preflight` verifies everything
without sending mail.

## Development

Python is managed by `uv`; source is in `src/creative_writer/`, tests in
`tests/`. `make test` runs the suite (about 300 tests, under half a minute).
