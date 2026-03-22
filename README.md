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

## Story layout

Each story lives under `stories/<slug>/` and uses Markdown plus YAML:

- `story.yml`: build metadata and chapter order
- `contract.yml`: human/AI collaboration settings and lint thresholds
- `style-guide.md`: voice, tone, and prose constraints
- `outline.md`: synopsis plus structural plan
- `manuscript/`: chapter Markdown files with YAML front matter

Optional artifact templates are included for:

- `characters.yml`
- `clues.yml`
- `locations.yml`
- `timeline.yml`
- `world.md`
- `scene-cards/`

## Commands

```bash
make init-story STORY=my-story KIND=original
make check STORY=mars-2044-cave
make epub STORY=mars-2044-cave
make pdf STORY=mars-2044-cave
make test
```

Generated outputs and reports land under `build/` and are not tracked in git.
