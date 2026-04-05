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

Optional artifact templates are included for:

- `characters.yml`
- `clues.yml`
- `plot_devices.yml`
- `locations.yml`
- `timeline.yml`
- `world.md`
- `scene-cards/`

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
make test
```

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

`make check` writes a coherence report to
`build/<slug>/reports/coherence-report.md`. The report now includes:

- mandatory artifact presence, including `narrative-design.md`,
- registry counts for characters, clues, locations, timeline events, and plot devices,
- per-chapter counts for clues, plot devices, and real scene cards,
- a scene-card section that ignores `README.md` and `_template.md`,
- a plot-device section summarizing the tracked structural machinery of the story.

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
