# Wells Phase 2C Operational Style Design

Date: 2026-07-31
Status: approved

## Purpose

Translate the approved Phase 2B Wells evidence layer into a practical,
evidence-linked writing and review workflow for *Time Expedition*.

Phase 2C will provide:

- a concise operational Wells style profile;
- expanded writer-facing guidance;
- curated role-matched reference packets;
- a reusable but deliberately small style-lint engine;
- separated Wells, anti-drift, and generic AI-writing diagnostics;
- tracked authenticity reviews;
- an AI-triage workflow that reserves human attention for difficult cases.

The system will act as a set of soft guardrails. It will help an AI writer and
human collaborator notice likely drift, inspect relevant source evidence, and
record judgement. It will not certify authorship, score "Wellsness", rewrite
prose automatically, or block publication because a heuristic fired.

## Relationship To Earlier Work

### Phase 2B Handoff

Phase 2B produced a validated descriptive evidence layer with ten claims:

- six validated claims;
- four qualified claims;
- no rejected final claims;
- no strong-confidence claims.

All final claims remain bounded by their stated roles, sources,
counterexamples, controls, and prohibited overgeneralisations.

Phase 2C may consume only validated or explicitly qualified claims from
`source-study/evidence-ledger.yml`. It may not turn raw metrics, rejected
hypotheses, Tier 4 practices, or a remembered idea of Wells into positive
guidance.

Features classified as `wells_characteristic_but_shared` may support the
target practice while remaining explicitly non-distinctive. Features
classified as `role_specific` may be used only within that role. Tier 4
controls remain negative and comparative evidence.

### Permian Story Design

The approved design for *The Last Week of the Permian* supplies the first
concrete writing target. Its principal modes include:

- an anonymous outer frame;
- Filby's reading of an expedition notebook;
- the Time Traveller's reported first-person account;
- scientific observation and inference;
- occupational dialogue at the Royal Society;
- environmental danger and physical action;
- reflective and evidentiary closure.

Phase 2C must support those modes without drafting, revising, or researching
the Permian story.

### Existing Repository Tools

The repository already has two partial style mechanisms:

- `make check` runs contract-configured em-dash and
  contrastive-parallelism warnings;
- `make ai-audit` invokes the external `audit-ai-writing` narrative scanner.

Phase 2C may organise these signals within one review surface, but neither
mechanism becomes a Wells authority. Authentic Wells passages can contain
patterns that generic AI-writing heuristics flag. A heuristic that routinely
condemns its own authority corpus is defective.

## Governing Principles

### Evidence Before Prescription

Every Wells-specific rule must cite eligible Phase 2B claim IDs and preserve
their jurisdiction, variation, uncertainty, and prohibited
overgeneralisation.

### Soft Guardrails

Manuscript findings are advisory. The engine supplies locations, measurements,
evidence, and review questions. Editorial judgement determines whether a
passage is effective, authentically variable, intentionally divergent, or
genuinely drifting.

Only malformed configuration, invalid provenance, stale claim or passage
references, unreadable inputs, and execution failures return a blocking error.

### Separation Of Signals

The system distinguishes:

- evidence-backed Wells practice questions;
- contextual quantitative diagnostics;
- negative or comparative anti-drift observations;
- generic AI-writing surface warnings;
- manual authenticity questions.

These categories cannot be combined into an aggregate score.

### Explicit Roles

Style comparison requires an intended narrative role. The system uses
optional writer-declared role metadata and never infers role through an opaque
classifier.

### Judgement After Heuristics

Deterministic tools locate possible problems. The AI reviews all findings
against manuscript context and source evidence. Only ambiguous,
high-consequence cases reach the human collaborator.

### Thin Reusable Core

The engine is profile-driven, but Phase 2C implements only one complete
profile: late-1890s Wells for *Time Expedition*. Reusability means clean data
boundaries and schemas, not a plugin framework or a universal theory of style.

### Traceable Calibration

Profiles, packet manifests, and authenticity decisions are tracked. Generated
reports remain disposable. A profile change must name the review evidence
that motivated it; no human ruling changes the profile automatically.

## Selected Architecture

Phase 2C uses an evidence-linked profile engine with four components.

### Reusable Lint Engine

Generic Python code will:

- load and validate a selected profile;
- resolve evidence claims and source passage locators;
- read manuscript chapters;
- apply transparent surface diagnostics;
- assemble manual practice questions;
- integrate optional generic AI-audit JSON;
- render deterministic Markdown and JSON reports.

The engine contains no built-in Wells rules, phrase lists, or Victorian style
assumptions.

### Story-Local Wells Profile

`stories/time-expedition/style-profile.yml` will hold:

- profile identity and version;
- Phase 2B provenance;
- permitted claim states;
- declared narrative roles;
- evidence-linked operational rules;
- contextual diagnostic definitions;
- anti-drift rules;
- default reference packets;
- calibration and change notes.

### Writer-Facing Guidance

The provisional `style-guide.md` becomes the full operational guide.
`style-card.md` becomes a concise drafting companion. Both are distillations
of the profile and evidence layer rather than independent authorities.

### Review Surfaces

Tracked story-local artifacts hold:

- reference-packet manifests;
- authenticity-review templates and completed decisions;
- any calibration pack manifests created through the existing review-pack
  workflow.

Generated reports and compiled packets live under `build/`.

## Public Interfaces

### Style Lint

CLI:

```text
creative-writer style-lint --story <slug> [--profile <path>] [--chapter <chapter>]
```

Make:

```text
make style-lint STORY=<slug> [PROFILE=<path>] [CHAPTER=<chapter>]
```

The default scope is the complete manuscript. A chapter selector provides a
focused drafting pass without changing the default review unit.

### Style Reference Packet

CLI:

```text
creative-writer style-reference --story <slug> --pack <name> [--profile <path>]
```

Make:

```text
make style-reference STORY=<slug> PACK=<name> [PROFILE=<path>]
```

Packet selection remains deliberate and manifest-driven. The command does not
perform similarity search or choose source passages automatically.

### Routine Check

`make check STORY=<slug>` will validate a configured style profile, its
provenance, packet manifests, role metadata, and any tracked authenticity
reviews. It will not run manuscript style analysis.

A story without a configured profile continues to work normally.

### Existing AI Audit

`make ai-audit STORY=<slug>` remains available. `style-lint` can consume its
structured scanner output through the existing adapter while keeping the
generic findings separate.

## Contract Configuration

`contract.yml` gains an optional style-lint section:

```yaml
style_lint:
  profile: style-profile.yml
  generic_ai_audit: true
```

The profile path is relative to the story directory unless an explicit CLI
override is supplied.

If no style-lint section is present:

- `make check` has no style-profile requirement;
- `make style-lint` requires an explicit profile;
- existing lint and AI-audit behaviour remains unchanged.

The existing `lint` settings for em dashes and contrastive parallelism remain
valid. `style-lint` will include their results in its separated surface-warning
section while preserving their existing `make check` warning behaviour.

## Story-Local Artifact Layout

Phase 2C will add:

```text
stories/time-expedition/
  style-profile.yml
  style-guide.md
  style-card.md
  style-reference-packets/
    README.md
    frame-and-testimony.yml
    traveller-account.yml
    observation-and-exposition.yml
    dialogue-and-social-friction.yml
    danger-and-action.yml
    reflection-and-closure.yml
  style-reviews/
    README.md
    _template.md
```

`style-guide.md` and `style-card.md` already exist and will be replaced in
place rather than duplicated.

Generated outputs will use:

```text
build/<slug>/style/
  lint-report.md
  lint-report.json
  chapters/
    <chapter>-lint-report.md
    <chapter>-lint-report.json
  reference-packets/
    <pack>.md
```

Calibration packets continue to compile through the existing
`review-packs/` workflow and land under its established build path.

Generated style outputs remain ignored by Git.

## Profile Schema

### Profile Identity And Provenance

The profile records:

- `schema_version`;
- `profile_id`;
- `version`;
- `title`;
- evidence-ledger path;
- validation-record path;
- approved Phase 2B generation or fingerprints;
- eligible claim statuses;
- default packet IDs;
- change basis and profile-review references.

Profile loading fails if the expected evidence generation or tracked
fingerprints no longer match.

### Narrative Roles

The profile declares stable role IDs and writer-facing descriptions. The
initial Wells profile needs at least:

- `frame`;
- `reported-account`;
- `notebook`;
- `scientific-inference`;
- `scientific-exposition`;
- `social-dialogue`;
- `danger-action`;
- `reflection-closure`.

Roles organise rules and packet selection. They are not stylistic scores or
claims that a chapter has only one mode.

### Operational Rules

Each rule contains:

- stable rule ID and name;
- rule family;
- advisory level: `notice` or `review`;
- eligible Phase 2B claim IDs where the rule is Wells-specific;
- inherited claim status, classification, confidence, and jurisdiction;
- applicable narrative roles;
- applicable scope: passage, chapter, or story;
- evaluation mode;
- writer-facing review question;
- optional transparent signal definition;
- optional broad contextual tolerance;
- source examples and material counterexamples;
- relevant reference-packet IDs;
- explicit interpretation limits.

Evaluation modes are deliberately small:

- `manual_question`;
- `locator`;
- `contextual_diagnostic`.

No evaluation mode asserts authorship or produces an automatic rewrite.

### Rule Families

`practice` rules ask whether a source-backed narrative or rhetorical mechanism
is functioning.

`diagnostic` rules surface a marked and transparent quantitative departure
that may deserve inspection.

`anti_drift` rules identify resemblance to generic Victorianism, neighbouring
styles, modern hard-SF habits, or generic AI surfaces. Tier 4 controls may
support only this negative or comparative family.

### Quantitative Tolerances

Tolerances are broad diagnostic ranges rather than targets. They must:

- retain source, work, and role context;
- avoid pooled "Wells averages";
- expose sample size and known parser limitations;
- flag outliers for inspection rather than correction;
- permit authentic source tails and exceptions.

Metrics that do not measure a Phase 2B claim cannot be presented as tests of
that claim.

## Phase 2B Claim Operationalisation

Phase 2C treats the ten final claims as ten review dimensions, not ten
detectors.

| Claim | Final state | Initial operational treatment |
| --- | --- | --- |
| `mediated-testimony-frame` | validated, moderate, shared | Manual frame and evidence-chain practice question |
| `role-shaped-narrator-distance` | validated, moderate, shared | Manual role-specific distance question |
| `qualified-speculative-inference` | validated, moderate, shared | Manual practice question plus epistemic-marker locator |
| `qualified-scientific-exposition` | qualified, moderate, shared | Narrow manual exposition question with prominent variation |
| `dialogue-pressure-varies-by-context` | validated, moderate, shared | Manual dialogue-function question plus contextual turn diagnostics |
| `role-shaped-syntax` | validated, moderate, shared | Contextual sentence and paragraph diagnostics; no target cadence |
| `selective-observed-description` | qualified, tentative, shared | Manual selection-and-observation question only |
| `danger-through-observation` | qualified, tentative, shared | Manual danger-order question only |
| `humour-through-social-friction` | validated, moderate, shared | Manual social-friction question |
| `short-form-evidentiary-closure` | qualified, moderate, role-specific | Manual ending gate within eligible short-form roles |

The first profile may use mechanical assistance to:

- show sentence and paragraph distributions;
- show dialogue and punctuation context;
- locate epistemic markers;
- locate repeated phrases, paragraph openings, and vocabulary clusters;
- surface existing em-dash, contrastive-parallelism, and generic AI warnings.

These diagnostics locate material for review. They do not decide whether
mediation, humour, descriptive selection, danger pacing, or closure succeeds.

## Chapter Role Metadata

Chapter-stub front matter gains two optional fields:

```yaml
style_roles:
  - reported-account
  - scientific-inference
style_packets:
  - traveller-account
  - observation-and-exposition
```

Unknown role or packet IDs are blocking validation errors when a profile is
configured.

Several roles may be declared for one chapter. The report must state that
chapter-level role assignment is coarse and cannot classify every paragraph.
Stories without these fields receive profile-wide and generic diagnostics.

The approved profile and chapter CLI options support focused experiments.
Additional role or packet overrides, scene-level role metadata, and automatic
role classification are deferred.

## Reference Packet Manifests

Each packet manifest records:

- packet ID, title, and purpose;
- intended narrative roles;
- eligible Phase 2B claim IDs;
- selected source passage IDs;
- bounded context-window rules;
- material counterexamples or authentic variations;
- each source's authority tier and permitted use;
- prohibited uses and anti-copying guidance.

The initial packet set is:

1. `frame-and-testimony`
2. `traveller-account`
3. `observation-and-exposition`
4. `dialogue-and-social-friction`
5. `danger-and-action`
6. `reflection-and-closure`

Packets remain small enough for active comparison. The implementation plan
will choose the exact passage count from the eligible evidence, with a
preference for a few high-value passages plus variation rather than exhaustive
quotation.

A compiled packet includes:

- profile and evidence-generation provenance;
- role and purpose;
- readable source excerpts with stable locators;
- why each passage was selected;
- relevant claim summaries and limitations;
- counterexamples or authentic variation;
- guidance on what to observe structurally;
- a warning against phrase borrowing.

Tier 2 and Tier 3 passages appear only within their admitted roles. Tier 4
controls may appear in a separately labelled negative-comparison section and
never as positive models.

## Writer-Facing Guidance

### Full Style Guide

`style-guide.md` will explain:

- authority and source hierarchy;
- the recovered-manuscript objective;
- role-specific operational guidance;
- the distinction between Wells practice and shared period practice;
- authentic variation and counterexamples;
- generic Victorian, neighbouring-author, modern, and AI drift risks;
- reference-packet use;
- chapter, story, and anthology review gates;
- human escalation and profile-calibration policy.

Important guidance must cite profile rule IDs or Phase 2B claim IDs.

### Concise Style Card

`style-card.md` will provide a short drafting-desk reference:

- source hierarchy;
- role-specific reminders;
- high-value practices;
- high-risk drift patterns;
- the observation-inference discipline;
- the current packet and review commands;
- links to the full guide and profile.

The card cannot become an imitation prompt, phrase bank, or substitute for
source reading.

## Style-Lint Report Contract

### Output

A whole-story run writes:

```text
build/<slug>/style/lint-report.md
build/<slug>/style/lint-report.json
```

A chapter run writes a distinct pair below
`build/<slug>/style/chapters/`.

### Report Sections

The Markdown report contains:

- run scope and manuscript inventory;
- profile, evidence, and packet provenance;
- declared roles and role-assignment caveats;
- concise finding inventory without a score;
- evidence-backed practice questions;
- contextual quantitative diagnostics;
- anti-drift observations;
- generic AI-surface warnings in a separate section;
- story-level repetition and uniformity observations;
- manual questions not resolved by deterministic analysis;
- limitations, incomplete adapters, and next review steps.

### Finding Record

Each finding has:

- stable run-local finding ID;
- manuscript path and location;
- observed text or signal;
- rule ID and rule family;
- advisory level;
- applicable role and scope;
- claim IDs and jurisdiction;
- source examples or counterexamples;
- concrete editorial question;
- limitations relevant to interpretation.

The JSON preserves the same information for AI triage and calibration-pack
assembly.

### Exit Behaviour

A run with manuscript findings exits successfully.

A non-zero exit is reserved for:

- malformed profile or manifest data;
- invalid evidence or passage references;
- stale provenance;
- unreadable story or manuscript inputs;
- report-generation or execution failure.

If the external generic AI scanner is unavailable, Wells-profile analysis
continues. The report records that the generic section was not run. This
partial-result state is visible but non-blocking.

A report with no configured findings is not an authenticity certificate.

## AI Triage

The style-lint command performs no model calls.

After a run, the AI reviewer examines every finding against:

- the full manuscript context;
- the declared narrative role;
- the cited Phase 2B claim;
- source examples and counterexamples;
- the active reference packet;
- current story intent.

The AI assigns one provisional disposition:

- `dismiss`: mechanically true but editorially irrelevant;
- `revise`: a clear prose or drift problem that can be addressed directly;
- `monitor`: harmless locally but worth watching across the manuscript;
- `escalate`: ambiguous and consequential enough for human judgement.

The generated report is a starting surface, not the completed editorial
decision.

## Human Calibration Packs

Human attention is treated as a limited, high-value resource.

Only a passage whose decision could materially affect the manuscript, clarify
the profile, or establish a reusable taste judgement should be escalated.

Calibration packs reuse the existing `review-pack` workflow. Phase 2C extends
review entries with optional style metadata:

- style-lint finding IDs;
- profile ID and version;
- Phase 2B claim IDs;
- intended narrative role;
- AI provisional disposition and rationale;
- decision impact.

Existing review-pack manifests remain valid.

A human calibration pack should normally contain three to five passages. Each
entry presents:

- the excerpt and manuscript location;
- the intended role;
- triggered signals;
- relevant Wells evidence and authentic variation;
- the AI's current judgement;
- one precise human question;
- why the answer matters.

Human feedback never mutates the profile automatically.

## Authenticity Reviews

Tracked reviews live under `style-reviews/` as Markdown with YAML front
matter.

The front matter records:

- review ID and date;
- scope and reviewed manuscript paths;
- profile ID and version;
- lint-report fingerprint or stable reference;
- reference packets used;
- reviewer identity or role;
- outcome.

The Markdown body records:

- important findings;
- dispositions and rationale;
- accepted intentional variations;
- revisions requested or completed;
- human calibration decisions;
- unresolved uncertainty;
- any proposed profile change.

Permitted outcomes are:

- `accepted`;
- `qualified`;
- `revise`.

Chapter-level authenticity reviews may be completed by the AI with a tracked
rationale. Story-level and anthology-level authenticity acceptance requires
explicit human approval.

The absence of a milestone review does not block a build. Present reviews are
validated; expected review gates are documented and may produce reminders.

## Generic AI-Writing Integration

The existing scanner remains an editorial rubric, not an authorship detector.

Its findings appear in a separate report section and retain their original
pattern-group identity and advice. They cannot:

- support a positive Wells rule;
- overrule an authentic source example;
- contribute to a combined score;
- trigger an automatic rewrite;
- establish that prose was AI-generated.

Where a generic signal is common in the authority corpus, the Wells report
must expose that calibration context rather than present the signal as
inherently defective. Repeated or clustered use in a new manuscript may still
justify review.

## Calibration And Versioning

### Authority-Corpus Calibration

Automated diagnostics will be exercised against:

- eligible development Wells passages;
- held-out Wells passages;
- material counterexamples;
- Tier 4 controls in their negative-only role;
- synthetic drift fixtures.

Calibration asks whether a rule usefully locates review material. It does not
train an authorship classifier.

The authority corpus need not produce zero warnings. It must not be routinely
or uniformly condemned by the profile that cites it.

### Profile Changes

Every profile change increments its version and records:

- the changed rule or tolerance;
- the evidence or review record motivating the change;
- the expected editorial effect;
- whether earlier reports need reinterpretation.

One human ruling is evidence for calibration, not an automatic universal rule.

### First Real Draft

The first substantive Permian chapter is the next major calibration event.
Observed false positives, missed problems, and human edge-case decisions will
guide a later, bounded refinement pass.

## Validation And Test Plan

### Schema And Provenance

- valid profiles parse;
- unknown schema versions fail;
- missing or duplicate rule IDs fail;
- invalid advisory levels, scopes, roles, or evaluation modes fail;
- stale Phase 2B provenance fails;
- missing, rejected, or ineligible claim IDs fail;
- a rule cannot broaden a claim's declared jurisdiction;
- Tier 4 evidence cannot become positive guidance.

### Chapter Metadata

- valid optional roles and packet IDs pass;
- unknown configured roles or packets fail;
- stories without style metadata retain current behaviour;
- mixed-role chapters are reported with the required caveat.

### Reference Packets

- valid manifests compile in declared order;
- invalid passage IDs fail;
- source roles and authority tiers are displayed;
- context windows remain bounded;
- counterexamples and anti-copying guidance are rendered;
- Tier 4 passages appear only in negative sections.

### Style Lint

- whole-story and chapter-targeted runs write distinct Markdown and JSON;
- report metadata matches the selected profile and evidence generation;
- findings include locations, rule IDs, claim IDs, and editorial questions;
- manuscript findings return success;
- malformed inputs return failure;
- no aggregate authenticity score appears;
- contextual metrics are labelled as non-evidentiary where appropriate;
- generic AI findings remain in a separate section;
- unavailable generic scanner produces a visible partial-result notice.

### AI-Audit Compatibility

- existing `make ai-audit` behaviour and tests continue to pass;
- existing em-dash and contrastive-parallelism check warnings remain intact;
- older review-pack manifests remain valid after optional style fields are
  added.

### Authenticity Reviews

- valid review front matter parses;
- invalid outcomes or unknown profile versions fail;
- AI chapter reviews and human story reviews can be represented;
- profile-change proposals can cite calibration decisions.

### Calibration Fixtures

- selected authentic Wells fixtures exercise every automated diagnostic;
- authentic source variation remains visible;
- synthetic repetition, punctuation, uniformity, and generic AI fixtures
  raise the intended signals;
- control material is never promoted into positive Wells guidance;
- a calibration pack can be assembled from selected synthetic findings.

### Repository Verification

- `make check STORY=time-expedition` passes;
- `make style-reference STORY=time-expedition PACK=<name>` succeeds for all
  six initial packets;
- whole-story and chapter-targeted `make style-lint` smoke tests succeed;
- the complete repository test suite passes;
- no manuscript prose or Permian research artifact changes in Phase 2C.

## Completion Criteria

Phase 2C v1 is complete when:

1. The reusable profile loader and thin lint engine work end to end.
2. The Wells profile is provenance-locked to the approved Phase 2B layer.
3. All ten claims have an explicitly bounded operational treatment.
4. The six initial reference packets compile with valid locators and context.
5. `style-guide.md` and `style-card.md` trace important guidance to evidence.
6. Whole-story and chapter reports are deterministic, separated, and
   score-free.
7. Generic AI signals remain optional, separate, and visibly incomplete when
   unavailable.
8. The AI triage and human calibration workflow can be performed with existing
   review-pack infrastructure.
9. Authenticity review records validate and preserve decision rationale.
10. Authority-corpus calibration finds no systematic self-condemnation.
11. Existing commands and tests continue to pass.
12. One focused self-review and repair pass finds no material defect.

## Explicitly Deferred Work

Phase 2C v1 will not implement:

- an authorship classifier or Wells score;
- automatic role classification;
- semantic similarity or automatic passage selection;
- automatic prose rewriting;
- automatic profile learning or mutation;
- a profile plugin registry;
- another author profile;
- sophisticated cross-chapter drift modelling;
- scene-level style-role metadata;
- mandatory build-blocking authenticity gates;
- a complete anthology audit with only one expedition;
- manuscript prose changes;
- Permian scientific or historical research.

## Stopping Policy

The implementation will stop when the thin end-to-end workflow satisfies the
completion criteria and one focused repair pass has addressed material
defects.

It will not continue through repeated tuning rounds against synthetic data.
Fine-tuning that depends upon actual prose will wait for the first substantive
Permian chapter and selected human calibration judgements.

## Approved Next Sequence

After written approval of this design:

1. Produce a detailed Phase 2C implementation plan.
2. Implement Phase 2C v1 with tests and one focused repair pass.
3. Return for user assessment.
4. Begin the dual-layer Permian research dossier.
5. Convert the approved story design and research into detailed chapter and
   scene architecture.
6. Draft and calibrate against real manuscript prose.
