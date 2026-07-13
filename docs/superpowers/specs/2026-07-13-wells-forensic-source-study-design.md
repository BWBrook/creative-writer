# Wells Forensic Source Study Design

Date: 2026-07-13
Status: approved design, awaiting implementation plan

## Purpose

Build an anthology-wide, evidence-backed system for reconstructing H. G.
Wells's late-1890s fictional voice before planning or drafting any *Time
Expedition* story. The target is not modern prose decorated with Victorian
features. It is a meticulous public-domain pastiche that should plausibly read
as a recovered Wells manuscript.

The study will support every expedition in the anthology. Its first practical
application will eventually be *The Last Week of the Permian*, but Permian
research, story architecture, and manuscript prose are outside this pass.

## Recovered-Manuscript Premise

The governing conceit is that Wells composed a group of further Time
Traveller expeditions circa 1897-1899, left them unpublished, and that a later
editor has assembled the recovered papers into a complete work.

The eventual reader-facing edition will use restrained editorial apparatus:

- a short editorial preface may establish the recovery and assembly;
- clearly separated notes may explain genuine textual or assembly problems;
- the expedition narratives will remain uninterrupted by an intrusive modern
  editor;
- the supposed Wells manuscript and the later editorial voice will remain
  distinct;
- repository metadata and ordinary publication metadata will continue to
  identify the work truthfully as a pastiche, even when the in-book apparatus
  sustains the fictional archival conceit.

The study will analyse Wells as he wrote, not an idealised or sanitised
version of him. Authentic variation, occasional awkwardness, repetition,
period assumptions, and tonal unevenness are evidence. They must not be
removed merely because a modern editor would prefer smoother prose.

## Composition Window

The positive style target is Wells circa 1897-1899. Earlier material may be
used when it is directly formative or already canonical to the project.
Later Wells may be examined only as contrast unless a future design explicitly
changes the composition window.

This boundary governs:

- vocabulary and idiom;
- scientific concepts available to the narrator;
- syntax, punctuation, exposition, and dialogue habits;
- social assumptions and class register;
- the distinction between contemporary Wells and later adaptations or later
  developments in his own style.

## Source Authority Hierarchy

Every admitted source must declare an authority tier, permitted uses,
prohibited uses, and one or more analytical roles. No source becomes generally
authoritative merely because it is present in the corpus.

### Tier 1: Canonical Sovereign

*The Time Machine* is the sole story-world canon and primary style authority.
It alone governs:

- the Time Traveller and frame narrator;
- fictional continuity and the machine;
- frame architecture and the reported first-person account;
- the basic relationship among observation, inference, speculation, and
  testimony;
- the governing narrative mode of the new expeditions.

Where another source conflicts with *The Time Machine* inside these
jurisdictions, *The Time Machine* wins.

### Tier 2: Close Wells Witnesses

The following are Wells style witnesses with bounded roles and no authority
over *Time Expedition* continuity:

- *The Invisible Man*, already admitted, for sustained dialogue, social
  interaction, class register, comic friction, speech attribution,
  concealment, and crowd response;
- *The Island of Doctor Moreau* for retrospective first-person narration,
  scientific argument, moral pressure, observed horror, and dialogue under
  stress;
- *The War of the Worlds* for catastrophe, landscape, technical observation,
  public behaviour, episodic pressure, and movement from evidence to
  speculation;
- three to five Wells short stories first published between 1895 and 1899,
  selected during corpus admission for complementary analytical roles.

Each work remains separate in analysis. The study must not average them into
one undifferentiated Wells corpus.

### Tier 3: Wells Scientific and Nonfiction Witnesses

A small selection of Wells's period-relevant scientific or nonfiction prose
may inform:

- explanatory habits;
- scientific vocabulary and analogy;
- the intellectual limits of the imagined composition period;
- distinctions between Wells's fictional and expository voices.

These sources do not govern fictional voice, continuity, or scene design.

### Tier 4: Contemporary Controls

A small, date-matched selection of non-Wells authors will be used only as a
control corpus. Controls may identify:

- conventions shared across late-Victorian prose;
- period-valid vocabulary, manners, and dialogue forms;
- false Victorianism;
- drift toward a neighbouring author or generic adventure prose;
- features that are common to the period rather than distinctive to Wells.

Controls never prescribe the anthology's voice. They cannot justify a phrase
or technique merely because it is historically plausible.

### Tier 5: Excluded Influence

The following have no positive authority:

- film, television, game, audiobook, or illustrated adaptations;
- later inventions attached to *The Time Machine*;
- generic steampunk or reconstructed Victorian style;
- post-1899 Wells mannerisms unless used explicitly as negative contrast;
- non-Wells contemporary prose used as a blended style model.

## Corpus Admission

Corpus expansion begins with a bounded admission phase. *The Island of Doctor
Moreau* and *The War of the Worlds* are fixed additions. Other candidates must
be justified before acquisition or analysis.

The admission record for every source will include:

- title, author, and first-publication date;
- authority tier and analytical roles;
- permitted and prohibited uses;
- reason for inclusion and expected contribution;
- edition provenance and public-domain context;
- retained source path, extraction method, and SHA-256 fingerprint;
- textual limitations, editorial normalisation, or variant concerns.

The additional corpus is capped initially at:

- three to five Wells short stories;
- no more than three Wells nonfiction works or bounded selections;
- three to five non-Wells control authors, represented only as extensively as
  their assigned control role requires.

The complete admission record receives human review before detailed analysis.
This prevents convenient or accidental source selection from shaping the
conclusions after the fact.

## Study Artifacts

The evidence layer will live under:

```text
stories/time-expedition/source-study/
  README.md
  method.md
  findings/
    frame-and-narration.md
    observation-inference-and-speculation.md
    scientific-exposition.md
    dialogue-and-social-register.md
    syntax-rhythm-and-punctuation.md
    diction-and-figurative-language.md
    pacing-description-humour-and-endings.md
  evidence-ledger.yml
  quantitative-profile.yml
  period-controls.md
  editorial-principles.md
  verification-protocol.md
```

`original/sources.yml` remains the source and provenance registry. The study
will reference it rather than duplicate source metadata.

### Method

`method.md` will define the composition window, authority hierarchy, corpus
sampling, segmentation, measurement methods, source-location conventions,
held-out material, confidence language, and known limits.

### Findings

The findings documents will contain close reading supported by exact source
locations. They will discuss both representative and exceptional passages.
They must distinguish:

- Wells-wide tendencies from work-specific effects;
- narrative mode from dialogue or editorial frame;
- period convention from distinctive Wells usage;
- authorial practice from edition typography or conversion artefacts;
- strong tendencies from occasional options.

### Evidence Ledger

Each `evidence-ledger.yml` record will contain at least:

- a stable claim ID;
- analytical dimension;
- narrowly worded claim;
- jurisdiction and exclusions;
- supporting passages with source IDs and locators;
- counterexamples or variation notes;
- authority tier of each source;
- confidence;
- permitted operational use;
- prohibited overgeneralisation.

An operational claim requires multiple supporting examples and explicit
treatment of material counterexamples. Absolute claims such as "Wells
always" require exceptional evidence and should be rare.

### Quantitative Profile

`quantitative-profile.yml` will store descriptive per-work baselines rather
than one pooled target. Candidate measurements include:

- sentence and paragraph length distributions;
- direct-dialogue and reported-speech proportions;
- speech-attribution patterns;
- punctuation and parenthetical usage;
- lexical recurrence and vocabulary concentration;
- paragraph openings and transitions;
- figurative and rhetorical pattern frequencies;
- narration-to-exposition ratios where segmentation supports them.

Metrics are diagnostic alarms, not a recipe for generating prose. Matching
their averages does not establish authenticity, and authentic Wells passages
must not fail merely because they fall in the tails of his own distribution.

### Period Controls and Editorial Principles

`period-controls.md` will distinguish Wells from shared late-Victorian
practice and record recognisable drift toward control authors.

`editorial-principles.md` will define the restrained recovered-manuscript
apparatus, the modern editor's limited jurisdiction, and the boundary between
editorial reconstruction and the supposed Wells text.

### Operational Distillation

The existing `style-guide.md` and `style-card.md` remain provisional until the
study is complete. They will then become concise working distillations of the
evidence layer, not independent authorities. Every important operational rule
must trace back to the study.

## Forensic Method

The study will use the following sequence:

1. Acquire and fingerprint admitted editions.
2. Derive clean searchable text while retaining reliable source locators.
3. Segment each work by relevant narrative mode without destroying its
   chapter and scene context.
4. Calculate descriptive measurements independently for each work.
5. Close-read representative, extreme, and contradictory passages.
6. Compare Wells witnesses with *The Time Machine* inside their assigned
   jurisdictions.
7. Compare tentative findings against contemporary controls.
8. Record supported claims, counterexamples, confidence, and limits in the
   evidence ledger.
9. Reserve source passages from the initial close reading and use them as
   held-out validation material.
10. Distil the validated findings into operational guidance.

Held-out validation is not a claim that style can be reduced to a classifier.
It is a check against overfitting. The finished profile must accommodate
authentic, previously unexamined Wells variation without also accepting any
plausible late-Victorian paragraph as Wellsian.

## Recurring Authenticity Gates

The source study remains active throughout later planning and writing.

### Architecture Gate

Before outlining an expedition, compare its frame, account structure,
dramatic mechanism, epistemic progression, and ending logic directly with
*The Time Machine*.

### Reference Packet

Before drafting a major unit, assemble a small role-matched packet of Wells
passages relevant to the intended work: arrival, observation, scientific
inference, dialogue, danger, reflection, or another declared function. The
packet supplies evidence without encouraging phrase copying.

### Chapter Audit

After each chapter draft, run ordinary coherence and AI-writing checks,
descriptive style measurements, and close comparison with the active
reference packet. Findings must distinguish genuine mismatch from authentic
Wellsian variation.

### Story Audit

After structural revision, sweep the complete story against held-out Wells
passages and period controls. Check for cumulative modernisation, imported
voices, excessive smoothness or consistency, false Victorianism, and
cross-chapter drift.

### Anthology Audit

Before publication, compare expeditions with one another and with Wells. The
stories should plausibly share an author without becoming mechanically
identical.

### Verification Log

Each gate will record the passages and dimensions examined, findings,
decisions, revisions, and unresolved uncertainty. A later editor must be able
to reconstruct why a passage was accepted rather than relying on a vague
claim that it sounds right.

## Tooling and Data Flow

The pass may add modest deterministic tooling for extraction, segmentation,
measurement, locator validation, and report generation. It will not add an
embedded model API, a black-box Wells score, or automatic prose rewriting.

The data flow is:

```text
pinned editions
  -> reproducible clean text with locators
  -> per-work measurements and close reading
  -> evidence ledger plus counterexamples
  -> held-out and control validation
  -> operational style guide and verification protocol
  -> later reference packets and authenticity logs
```

Human judgement remains authoritative when evidence is mixed. The tooling
organises and tests claims; it does not decide literary authenticity by
threshold.

## Failure Handling

The following are blocking failures:

- a source download or retained archive fails integrity checks;
- a retained fingerprint changes without an explicit source-update decision;
- extraction is incomplete or includes excluded packaging matter;
- source locators do not resolve;
- an evidence-ledger record cites a missing source or passage;
- a lower-tier source is used outside its permitted jurisdiction;
- continuity is imported from a non-canonical source;
- editorial reconstruction is inserted into the Wells layer without being
  disclosed in the verification log.

The following are warnings requiring interpretation:

- a draft metric lies outside a Wells baseline;
- two Wells witnesses exhibit materially different tendencies;
- a supposedly Wellsian feature is common across period controls;
- a passage resembles a control author more strongly than the active Wells
  witnesses;
- a style claim is supported but has substantial counterexamples.

Conflicting evidence must remain visible. The system will narrow a rule's
jurisdiction or lower its confidence rather than force false consistency.

## Testing and Verification

Implementation tests will cover:

- source-record schemas, authority tiers, and permitted-use fields;
- archive fingerprints and reproducible extraction;
- exclusion of ebook packaging and source corpora from manuscript statistics;
- source-locator resolution;
- evidence-ledger schemas and referential integrity;
- metric calculations against small known fixtures;
- separate per-work reporting rather than accidental corpus pooling;
- held-out and period-control report generation;
- generation of the final study artifacts without manuscript prose.

Manual verification will inspect representative source passages, conversion
boundaries, counterexamples, control comparisons, and the traceability of
operational rules back to evidence.

## Completion Criteria

The source-study pass is complete when:

1. The admitted corpus has approved roles, provenance, fingerprints, and
   reproducible searchable text.
2. The seven close-reading findings documents are complete and source-linked.
3. The evidence ledger validates and records supporting passages,
   counterexamples, confidence, and jurisdiction.
4. The quantitative profile reports each work independently.
5. Period controls distinguish shared convention from Wells-specific
   tendencies without becoming positive style authorities.
6. Held-out validation demonstrates that the profile accommodates authentic
   Wells variation and exposes generic period imitation.
7. The operational style guide, style card, editorial principles, and
   verification protocol trace back to the evidence layer.
8. Existing story checks and the complete repository test suite pass.
9. No Permian story architecture or manuscript prose has been introduced.

## Deferred Work

This design explicitly defers:

- the human Q&A about *The Last Week of the Permian*;
- end-Permian scientific research and historical-knowledge translation;
- the expedition's dramatic mechanism, outline, scene cards, and ending;
- drafting or revising anthology prose;
- full editorial preface or textual notes;
- comparison of every surviving Wells edition or manuscript variant;
- model-based authorship attribution.
