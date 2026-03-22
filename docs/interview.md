# Creative Writer Project Interview

This document records the scoped interview for the repository. We will work
through one question at a time, refine the answer until it feels complete, and
only then move on.

## Workflow

For each question:

1. Record the current question.
2. Capture the user's narrated answer.
3. Refine and summarize the answer.
4. Note any decisions, open points, or assumptions.
5. Move to the next question only when both parties are satisfied.

## Question 1

### Prompt

What kind of fiction do you most want this repository to support first?

Some useful angles, if helpful:

- novel, novella, short story, linked stories, or series;
- likely genres or genre mixtures;
- tonal preferences;
- whether the early target is exploratory writing or a concrete project.

### User answer

The preferred starting forms and modes are:

- hard science fiction;
- low-magic fantasy;
- historical drama;
- adventure fiction in the spirit of mid-20th century writers such as Hammond
  Innes.
- pastiches set in favored fictional worlds, typically using original
  characters rather than the principal characters from the source material.

Stylistically, the user prefers prose closer to Hemingway and Borges than to
florid or ornamental writing. The general inclination is toward gritty realism,
economy of language, and restraint in descriptive excess.

At the same time, the repository itself should not be narrowly tied to these
preferences. The tooling, conventions, and guardrails should remain flexible
enough to support a wide range of fictional forms and styles.

The user also wants the repository to support two distinct classes of work:

- original fiction with no inherited setting constraints;
- personal-use pastiche that may raise licensing or derivative-work questions.

These pastiche works are intended only for private enjoyment and sharing among
friends and colleagues, not for commercial sale. The repository should make it
easy to keep such works clearly separated from original-fiction projects.

### Working synthesis

The first-wave design target should assume serious, plot-driven fiction with a
lean prose style, strong structure, and an emphasis on realism, causality, and
narrative economy. The most natural early test cases are likely to come from
hard science fiction, low-magic fantasy, historical drama, and adventure
fiction.

However, these genre and style preferences should shape example usage and
defaults rather than become hard constraints in the tooling. The repository
should be architected as a flexible fiction-workbench, not a genre-specific
story generator.

It should also treat "original fiction" and "pastiche / licensed-world
derivative work" as separate organizational modes, so that planning,
manuscripts, exports, and any future publishing-oriented workflows can remain
cleanly partitioned.

### Decisions

- Early examples and validation cases can reasonably draw from hard science
  fiction, low-magic fantasy, historical drama, and adventure fiction.
- The repository should support both original fiction and personal-use
  pastiche.
- Default assumptions should favor lean, restrained, non-florid prose.
- Tooling should remain genre-agnostic and adaptable despite the initial
  stylistic center of gravity.
- The project structure should make it straightforward to separate works that
  may carry licensing or derivative-setting concerns from fully original work.

### Open points

- Whether one of these genres should be chosen as the first concrete project
  test case.
- How strongly the repository should encode stylistic guidance versus leaving it
  entirely project-specific.
- Whether the separation between original and pastiche work should be enforced
  only by folder/project conventions or also by explicit metadata.

### Status

Settled on 2026-03-22.

## Question 2

### Prompt

What role do you most want the AI agent to play in the early life of this
repository?

Some useful angles, if helpful:

- co-author versus assistant;
- brainstormer versus outliner versus scene drafter;
- editor, critic, continuity checker, or prose polisher;
- whether you want the AI to take initiative or remain tightly directed.

### User answer

The repository should support multiple styles of AI involvement, ranging from
very light-touch use to heavy AI authorship. At the light end, this could mean
AI-assisted or fully automated tooling such as linting, structural checks, or
other workflow support with minimal creative intervention in the prose itself.

At the opposite end, the repository should also support workflows in which the
AI acts as the primary author.

The user's own preferred mode often leans toward that latter model: the AI may
be the dominant drafting voice, while the user contributes sparks, prompts,
critical commentary, structural feedback, added detail, and suggestions.
However, that balance is intentionally variable. In some projects the user may
arrive with only a germ of an idea; in others the user may already have a
well-developed concept that the AI then expands or executes. The exact balance
of initiative should therefore be configurable per story rather than assumed in
advance.

The aim is not merely to use AI as a copy assistant, but to generate new
fiction through a flexible human-AI collaboration in which the proportion of
creative labor can vary widely.

The motivation for building the repository as a harness, rather than relying on
one-shot chat writing, is to improve quality and control. The repository should
make room for planning, revision, narrative steering, and iterative critique so
that recurring quirks of direct AI story generation can be managed more
deliberately.

The user suggests that each story may need an explicit "golden contract" or
creative agreement that states the intended role of the human and the AI for
that project. This contract could capture whether a given work is effectively
90% AI and 10% human, 50/50, or primarily human-authored with AI in a support
role.

The repository itself should remain independent of any one story. A likely
shape is that the repo provides the tooling and conventions, while individual
stories live in their own structured subdirectories. As stories are attempted,
the repository should be refined in response to real pressure points, edge
cases, and failure modes encountered in practice.

### Working synthesis

The system should be designed around a spectrum of AI roles rather than a
single authoring philosophy. It should be equally capable of supporting:

- tooling-first workflows with little or no creative text generation;
- collaborative workflows with alternating human and AI contribution;
- AI-led writing workflows in which the human acts as curator, director,
  critic, and narrative co-designer.

For this user, the early design target should still include the third mode, but
without freezing the human into a single role such as sole idea-originator. The
important requirement is adjustable collaboration: each story should be able to
declare its own human/AI division of labor.

In practical terms, the AI should not just generate text; it should be able to
participate in a disciplined writing loop involving outlines, draft passes,
feedback, revision, and continuity-aware refinement.

This points toward a per-story contract artifact or metadata layer that defines
the expected relationship between human and AI for that work. The repository
itself should function as a reusable fiction-development framework, with
individual stories serving both as outputs and as testbeds that drive the
tooling's iterative improvement.

### Decisions

- The repository should support a spectrum of AI involvement levels, from
  tooling-only assistance to AI-primary authorship.
- Early design should prioritize adjustable human-AI collaboration, including
  AI-led drafting with human guidance, commentary, and revision.
- The repository should likely include a per-story "golden contract" that
  defines the human/AI creative split and working relationship.
- The workflow should explicitly address weaknesses of one-shot AI writing by
  enabling planning, iterative drafting, critique, and revision.
- The repository should be story-agnostic at the top level, with individual
  stories developed in their own structured directories.
- Story development should be used to iteratively refine and improve the
  repository itself.

### Open points

- What minimum fields a per-story creative contract should contain.
- How much independent initiative the AI should take without being explicitly
  prompted at each step.
- How visible and reviewable AI interventions should be in manuscript and
  planning files.

### Status

Settled on 2026-03-22.

## Question 3

### Prompt

What should count as the canonical source of truth for a story project inside
this repository?

Some useful angles, if helpful:

- plain text, Markdown, YAML, JSON, or some mixture;
- whether manuscripts, outlines, character notes, and contracts should all live
  as versioned files in git;
- whether generated outputs such as PDF or EPUB should be treated as build
  artifacts rather than primary sources;
- how much structure you want in the underlying files versus keeping them as
  free-form prose.

### User answer

The preferred canonical formats are Markdown and YAML, used according to their
strengths.

- Markdown should be the primary format for most narrative and human-facing
  documents.
- YAML should be used for structured specifications such as contracts, linting
  settings, and other machine-readable parameters.

Final deliverables will typically be generated as EPUB or PDF.

Everything that constitutes primary source material should be tracked in git and
versioned. Generated outputs such as EPUB and PDF do not need to be versioned,
because they can be rebuilt from the tracked source files.

YAML structures should likely be templated so that contracts and other control
documents are clear, consistent, and reproducible. By contrast, the principal
Markdown files should remain more flexible, since their structure may vary with
the style and intent of a given narrative project.

### Working synthesis

The repository should adopt a two-layer source-of-truth model:

- Markdown as the main human-readable and authorial medium for story text,
  notes, plans, and other narrative-facing documents;
- YAML as the structured configuration layer for contracts, rules, metadata, and
  other settings that benefit from validation or templating.

Build outputs such as PDF and EPUB should be treated as derived artifacts, not
canonical sources. They should be reproducible from the git-tracked Markdown and
YAML inputs.

This suggests a design in which the tooling strongly supports structured YAML
templates while allowing the manuscript-facing Markdown to stay comparatively
open and expressive.

The provisional implementation stack should be:

- Python for the main tooling and workflow logic;
- Make as a thin task runner and command surface;
- Pandoc and Quarto for document rendering and output generation;
- Unix shell tools used opportunistically for small glue tasks.

TypeScript or other tooling can be deferred unless and until the project grows
toward web-based or more interactive interfaces.

### Decisions

- Canonical source files should primarily be Markdown and YAML.
- Markdown should be the default format for narrative and other human-facing
  documents.
- YAML should be the default format for structured specifications and
  machine-readable settings.
- PDF and EPUB should be treated as generated outputs rather than versioned
  source artifacts.
- Primary source materials should be tracked in git; generated deliverables need
  not be.
- YAML-based control files should likely use templates or defined schemas.
- Python should be the primary implementation language for the tooling layer.
- Make should provide a light command interface rather than hold the core logic.
- Pandoc and Quarto should be the initial document build stack.
- More elaborate implementation layers such as TypeScript can be deferred unless
  future needs justify them.

### Open points

- Which specific document types should be standardized as YAML from the start.
- How much structure to impose on Markdown documents beyond lightweight
  conventions.
- Whether generated outputs should be excluded globally via `.gitignore` or
  stored in a conventional build directory.

### Status

Settled on 2026-03-22.

## Question 4

### Prompt

If we only build one genuinely useful `v0.1` capability first, what should it
be?

Some useful angles, if helpful:

- compile a story project to EPUB/PDF;
- scaffold a new story directory with contracts and templates;
- maintain character or world sheets;
- run linting or continuity checks;
- manage outlines, scene cards, or chapter plans;
- something else that would immediately make the repository feel worthwhile.

### User answer

The most valuable early capability would likely address one of the main
weaknesses of one-shot AI narrative generation: maintaining story coherence
across many moving parts.

This includes keeping track of things such as:

- characters and their motivations;
- plot devices;
- clues;
- other structural or narrative elements that must remain internally
  consistent.

The user sees strong value in a repository that treats this coherence-tracking
problem as a first-class concern. In effect, the system should help the AI and
human maintain the sort of notes, planning structures, references, and
cross-checks that a careful human writer would normally use to keep a story
internally sound.

### Working synthesis

The leading `v0.1` candidate is not merely "document compilation" or
"scaffolding," but a coherence-support workflow for story development.

The core idea would be to give each story a structured way to record and review
the narrative facts that matter for consistency, such as characters,
motivations, clues, plot devices, and other dependencies. Tooling could then
help the human and AI consult, maintain, and eventually check these records
while drafting and revising.

This reflects a clear design priority: the repository should improve on
one-shot AI writing by strengthening memory, continuity, and structural
awareness.

### Decisions

- A coherence-tracking capability is currently the strongest candidate for the
  first useful `v0.1` feature.
- Early repository value should come from helping maintain internal narrative
  consistency rather than only from compilation or formatting.

### Open points

- What specific coherence entities should be tracked first: characters,
  motivations, clues, plot devices, timeline elements, locations, or something
  else.
- Whether `v0.1` should focus only on structured note-keeping or also include
  automated checks and warnings.
- How tightly the coherence layer should be coupled to the drafting workflow.

### Status

Settled on 2026-03-22.

## Question 5

### Prompt

Which supporting artifacts matter most from the start for each story project?

Some useful angles, if helpful:

- chapter files;
- scene cards;
- outline or structural plan;
- character bible;
- world notes;
- timeline;
- unresolved threads;
- plot devices or clue registry;
- style guide;
- anything else you see as essential.

### User answer

Many supporting artifacts could be useful for a given narrative, but they do
not all need to be mandatory. The user distinguishes between a small core set
of canonical artifacts and a wider set of optional artifacts that should be
available as templates.

The most essential, near-universal artifacts are:

- a style guide for voice, tone, and prose constraints;
- a story contract describing the human/AI creative relationship for that
  project;
- a high-level outline or synopsis, understood also as a structural plan and
  narrative arc.

Other artifacts such as a character bible, scene cards, a world file, and a
timeline of events may be very important for particular projects, but should be
optional rather than required in every case.

The repository should therefore provide a framework of templates and expected
artifact types without imposing a rigid rule that every story, whether a brief
vignette or a novella, must fill out all of them. The aim is to create enough
scaffolding that the human and AI know what kinds of materials can support a
coherent narrative, while preserving flexibility and proportionality.

### Working synthesis

Each story project should begin with a minimal canonical support set, likely:

- a story contract;
- a style guide;
- a high-level outline or synopsis.

Around that core, the repository should offer optional artifact templates for
deeper narrative management, including characters, scene cards, worldbuilding,
timeline tracking, and related support documents.

This implies a tiered story-structure model:

- a small mandatory core suitable even for short works;
- an expandable optional layer that can be adopted as complexity increases.

That approach keeps the framework useful for both lightweight and substantial
projects while still giving the tooling enough structure to support coherence.

### Decisions

- Story projects should likely have a small canonical set of core artifacts.
- The strongest candidates for that core are: story contract, style guide, and
  high-level outline or synopsis.
- Additional artifacts should be available as templates rather than universally
  required.
- The framework should scale from very short works to longer forms without
  forcing unnecessary documentation overhead.

### Open points

- Whether the high-level outline and structural plan should be one artifact or
  two distinct documents.
- Whether any artifact besides the contract, style guide, and outline should be
  mandatory by default.
- How the repository should signal optional templates to users without making
  the story scaffold feel bloated.

### Status

Settled on 2026-03-22.

## Question 6

### Prompt

How structured do you want the system to feel in day-to-day use?

Some useful angles, if helpful:

- very loose and writer-friendly;
- moderately scaffolded with recommended conventions;
- strongly opinionated with required templates and checks;
- whether you want the framework to guide behavior gently or enforce it
  explicitly.

### User answer

The desired feel is moderately scaffolded.

The system should leave enough flexibility for the author, whether AI, human,
or both, to shape the story without being throttled by the tooling. At the same
time, templates, checks, and other framework elements should be taken
seriously, because they exist to support coherent and reproducible fiction
development.

The fundamental purpose of the repository is to provide tooling and guardrails
that enable more satisfying, coherent AI-written narratives than would emerge
from unconstrained zero-shot chatbot generation. That implies a framework that
guides and disciplines the writing process, but does not rigidly over-determine
it.

Possible tools within this scaffold include lint-like checks for common AI
writing quirks, such as overuse of em dashes, contrastive parallelism, and
other stylistic habits that may weaken prose quality or violate a project's
agreed style. The user does not imagine these checks as purely heuristic or
algorithmic; rather, they may combine conventional lint-style pattern detection
with model-assisted review in which an AI evaluates its own draft more
intelligently and proposes revisions.

### Working synthesis

The repository should aim for a middle path between free-form writing space and
hard procedural enforcement.

In practice, that means:

- core conventions and templates should exist and matter;
- checks and guardrails should help shape behavior and catch weaknesses;
- writers should still retain freedom to adapt the process to the needs of a
  specific story.

This suggests a design philosophy of "structured by default, flexible by
exception": the framework should gently but meaningfully steer work toward good
practice, without turning story development into bureaucratic compliance.

Importantly, the guardrail layer may be hybrid in nature:

- deterministic where simple stylistic or structural checks are useful;
- model-assisted where subtler judgments about contract compliance, prose
  quality, or AI-specific writing habits are needed.

### Decisions

- The repository should be moderately scaffolded rather than either extremely
  loose or heavily prescriptive.
- Templates and checks should be meaningful parts of the workflow, not merely
  decorative suggestions.
- The framework should guide disciplined narrative development while preserving
  creative flexibility.
- The checking layer can legitimately mix rule-based linting with AI-assisted
  self-review and revision support.

### Open points

- Which elements should be advisory versus enforced.
- Whether enforcement should increase only for certain workflows such as build,
  lint, or release steps.
- How much friction is acceptable when a story intentionally departs from the
  default scaffold.
- Which AI-writing quirks and contract violations should be targeted first by
  the lint/review system.

### Status

Settled on 2026-03-22.

## Question 7

### Prompt

How should AI edits and revisions be handled in the normal workflow?

Some useful angles, if helpful:

- should the AI edit manuscript files directly;
- should it propose patches for review first;
- should it write suggestions into separate review notes;
- how much traceability or auditability you want for AI-originated changes;
- whether this should differ between exploratory drafting and later-stage
  revision.

### User answer

This behavior should be governed by configurable settings rather than fixed as a
single universal workflow. The author should be able to define the degree of AI
primacy over manuscript editing, likely via YAML configuration.

For the user's own purposes, the expected default would often be to allow the
AI to edit manuscript files directly. However, other authors may want a higher
degree of review control, so the repository should support more conservative
options as well.

Useful tooling in this area would include the ability to extract human-friendly
diffs from AI edits. These could range from:

- precise change displays, analogous to tracked changes, perhaps via temporary
  DOCX output or other review-friendly representations;
- intelligent summaries generated by the AI that describe what changed and why,
  rather than only exposing the raw textual diff.

Different authors should be able to choose among these review modes according to
their preferences. These capabilities are not necessarily the highest-priority
implementation targets, but they are seen as valuable tools to develop over
time.

### Working synthesis

AI revision behavior should be configurable rather than hard-coded.

The likely model is a settings-driven continuum, ranging from:

- direct AI edits to manuscript files with minimal intervention;
- AI-generated change proposals or patch-style review;
- auxiliary review outputs that help a human inspect or understand what changed.

For this user, direct AI editing is likely to be the normal mode. However, the
repository should be architected so that more cautious, review-heavy workflows
are equally possible.

This suggests that edit handling should separate two concerns:

- authority: whether the AI may directly alter source files;
- visibility: how those alterations are surfaced to a human, from exact diffs
  to higher-level summaries.

### Decisions

- AI edit authority should be configurable, likely through YAML settings or
  per-story metadata.
- Direct AI editing of manuscript files should be supported as a first-class
  workflow.
- The framework should eventually support multiple review modes for AI changes,
  including precise diffs and higher-level summaries.
- Different authors should be able to choose different levels of AI control and
  change visibility.

### Open points

- Whether edit authority should be configured globally, per story, or per phase
  of writing.
- What the initial review output should be for `v0.1`: plain git diff, rendered
  review artifact, AI-generated summary, or some combination.
- Whether exploratory drafting and late-stage revision should default to
  different review behaviors.

### Status

Settled on 2026-03-22.

## Question 8

### Prompt

What concrete outcome would make you say, a month from now, that this
repository is already worth having?

Some useful angles, if helpful:

- a specific workflow that works end-to-end;
- one story project successfully scaffolded and developed;
- a coherence-checking loop that catches real problems;
- a reliable build process to EPUB/PDF;
- a feeling that the repo is already better than ordinary chat-based writing;
- any other practical milestone that would feel like real value.

### User answer

The primary success criterion is that the workflow should feel meaningfully
better than ordinary chat-based writing.

The user notes that ad hoc story generation in a chat app is easy, but has
clear limitations:

- the output is trapped in the chat interface rather than available as a proper
  artifact such as an EPUB for Kindle reading;
- the resulting length, form, or structure may not match the user's intent;
- the story may lack coherence because it has not been carefully planned,
  tracked, or revised.

If, a month from now, the user is regularly using this repository to generate
new short narrative fiction, that would itself demonstrate the repository's
value.

The expected proof will likely come not from one large work, but from a set of
short and varied test pieces or demonstration narratives. These can be used to
probe different approaches to style, form, workflow, and structure. The near-
term focus is therefore on shorter works, possibly including multi-chapter
pieces, rather than immediately attempting long novella-scale projects.

The broader aim is to improve the resilience, robustness, and practical
usefulness of the repository in supporting high-quality AI-written prose.

### Working synthesis

The repository will be worth having if it becomes a superior working environment
for generating and refining short fiction compared with a normal chatbot
interface.

In concrete terms, the one-month milestone is likely:

- the user is regularly using the repo rather than chat alone;
- the repo can support several short test narratives end-to-end;
- those stories can be shaped, tracked, and exported in ways that feel more
  controlled and satisfying than one-shot generation;
- the process is already surfacing lessons that make the framework stronger.

This suggests an early product strategy centered on many small proof pieces
rather than one ambitious long-form project. The immediate goal is practical
habitability and narrative quality, not breadth of features for their own sake.

### Decisions

- The most important early outcome is a workflow that is clearly better than
  chat-based writing for the user.
- Success should be measured by regular real use, not merely by technical
  completion of tooling.
- Early validation should come from multiple short and varied story projects.
- Near-term focus should remain on short fiction and short multi-chapter pieces
  rather than larger long-form works.

### Open points

- What minimum end-to-end workflow must exist before the repository feels ready
  for regular use.
- How many short test pieces would be enough to count as meaningful proof.
- Which dimensions of "better than chat" should be prioritized first:
  coherence, exportability, controllability, revision quality, or something
  else.

### Status

Settled on 2026-03-22.

## Question 9

### Prompt

Do you already have a specific story idea or test-case premise you’d like to
use as the first narrative project in this repository?

Some useful angles, if helpful:

- a one-sentence premise is enough;
- it can be original fiction or private-use pastiche;
- it can be chosen for convenience as a test case rather than because it is
  your most important story;
- if you do not yet have one, we can decide whether the repo should generate
  candidate premises later.

### User answer

Yes. The first narrative test case should be a short story set on Mars in the
year 2044.

Premise:

The first substantial human colony has recently been established after being
constructed by robot engineers that arrived during the previous decade. While
exploring nearby landforms, the first human colonists discover a cave. Inside
it, they find evidence that some intelligence has been there before them.

### Working synthesis

The initial story test case should be an original near-future Mars story with a
colonial-exploration frame and a buried mystery at its center.

This is a strong early fit for the repository because it naturally invites:

- hard-science-fiction worldbuilding;
- structured tracking of setting facts, logistics, and technology;
- mystery-oriented clue management;
- coherence checks around exploration, discovery, and interpretation.

It also provides a manageable scale for an early short-fiction workflow while
still being rich enough to stress-test the repository's planning and narrative
support systems.

### Decisions

- The first concrete narrative project should be a short story set on Mars in
  2044.
- The premise should involve a newly established human colony, prior robotic
  construction, and the discovery of possible prior intelligence in a cave.
- This project can serve as the initial real-world testbed for the repository.

### Open points

- Who the viewpoint character or characters should be.
- Whether the discovered intelligence is alien, human, artificial, ambiguous,
  or something else.
- What tone the story should strike: wonder, dread, procedural realism,
  adventure, or some mixture.
- Whether this story should be used only as a test case or also developed into a
  more polished finished piece.

### Status

Settled on 2026-03-22.

## Initial interview status

The first scoping pass is now complete for Questions 1 through 9.

Current result:

- the repository vision is materially clearer;
- the initial implementation stack is provisionally chosen;
- the first `v0.1` value target is centered on narrative coherence support;
- the first concrete story test case has been selected.

The current first test case should be treated as an initial proving ground, not
as the sole narrative mode the repository must support. Additional short and
varied test stories will likely be needed to pressure-test the framework across
different styles, structures, and collaboration modes.
