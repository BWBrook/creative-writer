# Writer Feedback

This document records the lived experience of using the `creative-writer`
repository as a fiction workbench from the writer's side. It is intended for
builder agents improving the harness, not as a technical changelog.

Use each entry to capture what a writer was trying to do, where the process
fought back, why that mattered to the work, and what kind of remedy would make
the tool more habitable.

## 2026-04-04

### Entry 1: Narrative-design decisions have no obvious home

- Context: Reworking `stories/mars-2044-cave/` from a short demo scaffold into a
  7-12k story packet before drafting.
- Friction: The current core artifacts make room for premise, style, and
  chapter order, but there is no explicit place to record narrative anchor,
  thematic question, ending logic, or clue ladder. Those decisions can be bent
  into `outline.md`, but that is an improvised use rather than an intended one.
- Impact on writing: A second writer or agent can recover the broad plan, but
  not the real design logic quickly. That makes handoff slower and creates more
  room for drift during revision.
- Suggested fixes: Add a lightweight planning surface for narrative design, or
  expand the outline template so it explicitly invites POV choice, dramatic
  question, ending mode, and reveal structure.
- Template gaps: Missing optional artifact or template section for narrative
  anchor and clue progression.

### Entry 2: Scene cards exist, but feel vestigial

- Context: Deciding whether to use `scene-cards/` during pre-draft planning.
- Friction: The repo provides scene-card directories and links to them from
  chapter stubs, but it does not provide a real example scene card, a suggested
  heading structure, or any output that reflects scene-card use.
- Impact on writing: Scene cards feel like a ghost feature. A writer has to
  invent the format from scratch, which weakens the sense that the harness is
  actively helping with scene-level planning.
- Suggested fixes: Provide a minimal scene-card template and surface scene-card
  usage in the coherence report so the feature feels alive.
- Template gaps: Missing sample scene-card file and missing recommended
  headings.

### Entry 3: `plot_devices` is present without a supporting system

- Context: Planning the mystery machinery for the Mars story.
- Friction: Chapter front matter includes `plot_devices`, but the template has
  no story-level registry for them and the checks do not validate or summarise
  the entries.
- Impact on writing: The field promises structure and then leaves the writer to
  manage it alone. That lowers trust in the surrounding planning apparatus.
- Suggested fixes: Either add a real optional `plot_devices.yml` artifact with
  report support, or remove the field until it can carry actual weight.
- Template gaps: Missing registry and missing validation/reporting for plot
  devices.

### Entry 4: Writer review wants targeted excerpts, not whole-draft dumping

- Context: Planning the first human feedback pass on the Mars story draft.
- Friction: The current review model points toward file diffs or full-manuscript
  sharing, but neither is ideal for AI-first drafting when the human reader is
  being used as a scarce critical resource.
- Impact on writing: Whole-draft review creates diffuse feedback and encourages
  the human reader to spend effort on parts the writer does not need help with.
  The better workflow is to surface a few chosen passages: some to validate what
  is working, some to interrogate uncertainty.
- Suggested fixes: Add a review-oriented workflow or template for excerpt packs
  that lets the writer label each excerpt as "confidence" or "uncertainty" and
  attach a specific question.
- Template gaps: Missing review artifact for targeted excerpt feedback during
  drafting.
