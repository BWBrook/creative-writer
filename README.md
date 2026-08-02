# Creative Writer

Tools and workflow for collaborative human-AI narrative writing.

This repository is being built iteratively. The initial focus is to:

- establish a shared workflow for scoping the project,
- record decisions in versioned documents,
- build small capabilities one at a time,
- test each capability against real writing work.

Current working document:

- [docs/interview.md](docs/interview.md)

## v0.1 foundation

The first implementation slice is a file-first story framework with:

- per-story scaffolding under `stories/<slug>/`,
- deterministic coherence and style checks,
- `EPUB` and `PDF` builds from Markdown sources,
- a seeded Mars 2044 test project.

The default story scaffold is now stored explicitly under
`templates/story/`, so the canonical framework is visible and easy to refine.

## Story layout

Each story lives under `stories/<slug>/` and uses Markdown plus YAML:

- `story.yml`: build metadata and chapter order
  - includes the story language used for `EPUB` metadata
- `style-card.md`: inherited style family copied from a built-in or custom card
- `contract.yml`: human/AI collaboration settings and lint thresholds
- `style-guide.md`: story-specific voice, tone, and prose constraints
- `outline.md`: synopsis plus structural plan
- `narrative-design.md`: story-engine decisions such as POV, dramatic question, ending logic, and reveal ladder
- `chapter-stubs/`: chapter-level planning files with YAML front matter
- `manuscript/`: full narrative chapter text
- `assets/images/`: embedded chapter images or other visual assets
- `scene-cards/<chapter>/`: optional scene planning linked from each chapter stub
- `review-packs/`: optional manifest-driven excerpt requests for targeted human feedback

Optional artifact templates are included for:

- `characters.yml`
- `clues.yml`
- `plot_devices.yml`
- `locations.yml`
- `timeline.yml`
- `world.md`
- `scene-cards/`
- `review-packs/`

## Commands

```bash
make init-story STORY=my-story KIND=original
make init-story STORY=my-story KIND=original STYLE_CARD=quiet_catastrophe_realism
make new-story STORY=my-story KIND=original
make style-cards
make check STORY=mars-2044-cave
make epub STORY=mars-2044-cave
make pdf STORY=mars-2044-cave
make stats STORY=mars-2044-cave
make ai-audit STORY=mars-2044-cave
make review-pack STORY=mars-2044-cave PACK=first-human-pass
make style-lint STORY=time-expedition
make style-lint STORY=time-expedition CHAPTER=01-the-obstruction
make style-reference STORY=time-expedition PACK=frame-and-testimony
make source-analysis STORY=time-expedition STAGE=prepare
make test
```

Phase 2B source analysis is staged explicitly:

```bash
creative-writer source-analysis --story <slug> --stage prepare
creative-writer source-analysis --story <slug> --stage develop
creative-writer source-analysis --story <slug> --stage validate
```

`prepare` creates or verifies the corpus lock and three physical passage
indexes; `develop` reads only the development index and is intentionally
limited to the pre-freeze `protocol`/`development` lifecycle; `validate`
reports the managed validation generation. The validation record advances in
order from `frozen` to `heldout_assessed` to `complete`, so held-out Wells
material is assessed before Tier 4 controls can be opened. The committed
`heldout_assessed` record contains held-out results only; its validation run
generates the control-inclusive packet used to author control comparisons,
reviewer records, and claim transitions for `complete`. Candidate
`analysis.yml` and `holdouts.yml` remain immutable for that validation run. At
`complete`, the writer-facing profile and evidence ledger may be the separately
hash-checked final versions required by the approved workflow. Phase 2B produces
descriptive evidence only and stops before Phase 2C style guidance, planning,
or manuscript changes.

The `time-expedition` Phase 2B study is technically complete and has passed its
independent acceptance re-review. Its final evidence layer contains six
validated and four qualified claims, with no rejected or strong-confidence
claims. The compiled report is available at
`build/time-expedition/source-study/validation/current/analysis-report.md`.
Barry gave substantive approval on 23 July 2026. Phase 2C v1 is now
operational: its provenance-locked Wells profile, six curated packets,
score-free advisory lint reports, and tracked calibration surfaces work end to
end. The first substantive Permian chapter is the next style-calibration event;
synthetic and placeholder prose will not be used for repeated threshold tuning.
The immediate next project tranche is the dual-layer Permian research dossier,
before detailed chapter and scene architecture or manuscript drafting.

For a simple script wrapper, you can also run:

```bash
scripts/new_story.sh my-story original "My Story Title" quiet_catastrophe_realism
```

`STYLE_CARD` can be either:

- a built-in card key from `templates/style-cards/`
- a path to a custom Markdown style card

When selected, the card is copied into the new story as `style-card.md`, and
the chosen source is recorded in `story.yml`.

Generated outputs and reports land under `build/` and are not tracked in git.

`make stats` writes a manuscript progress snapshot to
`build/<slug>/reports/ms-statistics.md`. The report includes:

- per-chapter manuscript word counts in story order,
- total manuscript words and average words per chapter,
- estimated reading time,
- a supporting-Markdown breakdown so you can see how much of the story exists as
  outline/stubs/scene cards versus full draft prose.

`make ai-audit` runs the local `audit-ai-writing` skill scanner over the
manuscript chapters and writes a triage report to
`build/<slug>/reports/ai-writing-audit.md`. Use it before or after revision
passes to catch stock AI surface tells such as abstract significance language,
over-neat parallelism, and repeated narrative closure habits. Set
`CREATIVE_WRITER_AI_AUDIT_SCRIPT` if the scanner script lives somewhere other
than the default Codex skill path.

`make check` writes a coherence report to
`build/<slug>/reports/coherence-report.md`. The report now includes:

- mandatory artifact presence, including `narrative-design.md`,
- registry counts for characters, clues, locations, timeline events, and plot devices,
- per-chapter counts for clues, plot devices, and real scene cards,
- a scene-card section that ignores `README.md` and `_template.md`,
- a plot-device section summarizing the tracked structural machinery of the story.

## Evidence-linked style workflow

A story can opt into evidence-linked style work through `contract.yml`:

```yaml
style_lint:
  profile: style-profile.yml
  generic_ai_audit: true
```

The profile path in `contract.yml` is story-relative. Stories without this
section retain the existing check, build, audit, and review-pack behaviour.
Either public style command can instead use `--profile`/`PROFILE` as a
story-local override:

```bash
creative-writer style-lint --story <slug>
creative-writer style-lint --story <slug> --profile <path> --chapter <chapter>
creative-writer style-reference --story <slug> --pack <name>
creative-writer style-reference --story <slug> --pack <name> --profile <path>

make style-lint STORY=<slug>
make style-lint STORY=<slug> PROFILE=<path> CHAPTER=<chapter>
make style-reference STORY=<slug> PACK=<name>
make style-reference STORY=<slug> PACK=<name> PROFILE=<path>
```

An explicit profile override fully replaces the `contract.yml` profile for
that command; the superseded profile is not validated. The Make targets reject
a blank `STORY` (and a blank `PACK` for `style-reference`) before invoking the
CLI.

`style-lint` requires a configured profile or an override. Its default
whole-story run writes matching advisory reports to
`build/<slug>/style/lint-report.md` and
`build/<slug>/style/lint-report.json`. A chapter selector writes a distinct
pair to `build/<slug>/style/chapters/<chapter>-lint-report.md` and
`build/<slug>/style/chapters/<chapter>-lint-report.json`. Selectors accept an
exact configured stub path, manuscript path, filename, or unambiguous stem.

The report keeps six reader-facing surfaces separate:

1. Run scope plus the declared chapter role and packet inventory.
2. Evidence-backed Wells practice questions and findings.
3. Contextual diagnostics, including story-level repetition and cadence observations.
4. Negative or comparative anti-drift observations and unresolved manual questions.
5. Existing em-dash and contrastive-parallelism surface warnings.
6. Generic AI-writing signals from the optional external scanner.

These are advisory review prompts, never an authenticity score, authorship
verdict, or automatic rewrite. A finding does not make the command fail.
Malformed configuration, missing or stale provenance, invalid claims or
source references, unknown chapter role or packet IDs, unreadable inputs, and
report execution failures are blocking errors. If the optional scanner is
unavailable, the other five surfaces still run and the successful report is
marked `partial`. A present scanner that fails or returns malformed data is an
execution error. Set `generic_ai_audit: false` to record that surface as
disabled instead of partial.

`style-reference` compiles one curated manifest to
`build/<slug>/style/reference-packets/<pack>.md`. This explicit command may
prepare missing, hash-pinned Phase 2B passage indexes; it reports whether it
did so. Compiled packets preserve profile, claim, passage, source, authority,
and selection provenance. Tier 4 material is confined to negative comparison.
Reference text is for studying narrative method, evidentiary sequence, role,
and cadence: do not borrow distinctive phrases, sentence skeletons, images,
or local wording.

When style lint is configured, `make check` validates the profile and its
tracked Phase 2B provenance, every real
`style-reference-packets/*.yml` manifest (excluding `_template.yml` and
`README.md`), and explicit chapter role/packet metadata. It neither requires
nor prepares generated passage indexes, and it never runs the Phase 2C
manuscript style engine or external scanner. The older contract-configured
em-dash and contrastive-parallelism warnings remain unchanged; run
`style-lint` explicitly for the six-surface manuscript report.

`make review-pack` reads a manifest from `stories/<slug>/review-packs/<pack>.yml`
and writes a readable Markdown packet to `build/<slug>/reviews/<pack>.md`. Each
entry selects an inclusive manuscript line range, labels it as `confidence` or
`uncertainty`, attaches a reviewer question, and includes optional context.

## Novellas pipeline

The repo also supports a two-way pipeline to the local OneDrive-synced
`Documents/Novellas` folder.

```bash
make novellas-path
make import-novella FILE="The New Grand Tour.docx"
make export-novella INPUT="stories/the-new-grand-tour/manuscript/01-california-to-orbit.md" OUTPUT="The New Grand Tour Chapter 1.docx"
make clear-ingested STORY=the-new-grand-tour
make kindle-preflight STORY=mars-2044-cave
make kindle STORY=mars-2044-cave
make kindle-store-password
```

Imported files land under `ingested/`. If the local OneDrive path ever differs
from this machine's default sync location, set `CREATIVE_WRITER_NOVELLAS_DIR`
to override discovery.

Once a story has been back-fitted into `stories/<slug>/`, `make clear-ingested`
can remove its staging import after verifying that:

- the story exists and passes `check`,
- no story files still reference `ingested/`,
- any extracted media has been copied into the story's own `assets/images/`.

## Kindle delivery

The repo can also email a built `EPUB` to a configured Send-to-Kindle address.

The delivery config is intentionally local-only:

- tracked example: `config/kindle.example.yml`
- untracked live config: `.creative-writer.local.yml`

Typical flow:

```bash
cp config/kindle.example.yml .creative-writer.local.yml
make kindle-store-password
make kindle-preflight STORY=mars-2044-cave
make kindle STORY=mars-2044-cave
```

`kindle-preflight` builds the `EPUB`, validates the local config, resolves the
SMTP credential from the environment or macOS Keychain, and writes a report to
`build/<slug>/reports/kindle-delivery.md` without sending mail.

By default, the SMTP layer expects:

- `smtp.gmail.com`
- port `465`
- `ssl`

If you prefer not to store the password in Keychain, set the environment
variable named by `smtp.password_env` instead.
