# Wells Phase 2B Detailed Forensic Analysis Design

Date: 2026-07-15
Status: proposed design, awaiting human review

## Purpose

Produce a validated, traceable description of H. G. Wells's fictional
practice circa 1895-1899 for the *Time Expedition* recovered-manuscript
anthology.

Phase 2A established a closed and fingerprinted reference corpus. Phase 2B
analyses that corpus. It will determine what Wells demonstrably does, where
his practice varies by work or narrative mode, which apparent features are
shared period conventions, and how confidently each conclusion can be held.

The result is an evidence layer, not a prose-generation recipe. Phase 2B ends
with a human-reviewed, validated descriptive profile. It does not revise the
operational style card, design *The Last Week of the Permian*, or draft
anthology prose.

## Relationship To Earlier Designs

This design refines two approved foundations:

- `2026-07-13-wells-forensic-source-study-design.md` defines the anthology-wide
  forensic study, authority hierarchy, recovered-manuscript premise, and broad
  analytical method.
- `2026-07-14-wells-phase-2-reference-corpus-design.md` defines and implements
  the closed Phase 2A corpus boundary.

The earlier forensic-study design described analysis and operational
distillation in one broad pass. The present design separates them:

- Phase 2B: deterministic measurement, close reading, evidence-ledger claims,
  period-control comparison, held-out validation, and a descriptive Wells
  profile;
- Phase 2C: translation of validated findings into the style guide, style
  card, reference-packet method, authenticity gates, and other operational
  writing guidance.

Where the earlier design's completion criteria include operational style
guidance, those criteria now belong to Phase 2C. This is a sequencing change,
not a rejection of the wider forensic-study design.

## Goal Statement

Phase 2B is complete when the repository contains a reproducible and
human-reviewed account of Wells's late-1890s practice that:

- preserves the authority jurisdiction of every source;
- keeps every work analytically separate;
- distinguishes observation from inference;
- supports every material claim with resolvable passage evidence;
- records counterexamples and variation rather than forcing consistency;
- tests candidate claims against untouched Wells passages and period controls;
- identifies claims as distinctive, shared, role-specific, period-general, or
  unsupported;
- stops before any finding becomes an instruction for writing pastiche.

## Non-Goals

Phase 2B will not:

- revise `style-guide.md` or `style-card.md`;
- produce an operational phrase bank, imitation prompt, or prose recipe;
- implement an author-specific style linter, drift score, or Wells-compliance
  threshold;
- plan the Permian expedition, anthology spine, frame scenes, or editorial
  preface;
- perform end-Permian scientific research;
- draft, rewrite, or audit anthology manuscript prose;
- acquire another source or silently change a retained edition;
- blend non-Wells prose into a composite Victorian voice;
- build a black-box Wells score or authorship classifier;
- embed a model API or automate interpretive literary judgement;
- treat metric matching as proof of authenticity;
- undertake exhaustive textual-variant scholarship across all historical
  editions.

## Governing Principles

### Evidence Before Prescription

Every Phase 2B claim is descriptive. It may state that Wells often moves from
concrete observation through qualified inference, but it may not instruct a
future writer to reproduce that movement. Operational consequences are
deferred until Phase 2C has reviewed the complete evidence layer.

### Separate Works Before Synthesis

All measurements and observations are first recorded per work. No pooled
"Wells average" may replace the source-level results. Synthesis may describe a
cross-work tendency only after showing its distribution and exceptions.

### Authority Is Jurisdictional

Source authority does not become broader during analysis. *The Time Machine*
alone governs continuity, the Time Traveller, the machine, frame structure,
and the reported-account mode. Other Wells works contribute only inside their
declared roles. Tier 4 controls can challenge a proposed distinction but can
never support a positive Wells claim.

### Variation Is Evidence

Awkwardness, repetition, unevenness, work-specific habits, and apparent
exceptions remain visible. The analysis narrows or qualifies a claim when
Wells varies; it does not smooth the evidence into an idealised style.

### Metrics Are Descriptive Instruments

Measurements identify patterns, extremes, and useful close-reading targets.
They do not settle literary interpretation, establish authorship, or define
hard pass/fail thresholds for later prose.

### Reproducibility Without False Precision

Deterministic tooling will index passages, calculate transparent measurements,
and validate references. Interpretive claims remain human- and agent-authored,
source-linked, and reviewable. Statistical significance tests are not used on
non-independent blocks of a small purposive corpus.

## Corpus And Authority Lock

Phase 2B begins by running the existing source-admission gate. Analysis is
blocked unless the corpus remains exactly:

- thirteen admission records;
- twelve admitted retained records;
- twelve retained EPUBs;
- fifteen retained Markdown witnesses;
- eleven full-work Markdown witnesses;
- four selected Wells short-fiction witnesses;
- one excluded and unacquired Tier 5 record, *The Lost World*.

The source IDs, roles, permitted uses, prohibited uses, edition fingerprints,
derived-text fingerprints, and selected-subwork identities in the Phase 2A
registries are immutable inputs to this phase.

For analysis, each full-work record has a `witness_id` equal to its source ID.
Each selected short story has a witness ID of
`selected-short-fiction/<selection-id>`. The four selections are therefore
measured and cited as four independent witnesses, never as one pooled omnibus.
Evidence references retain both the parent source ID and the selection ID.

Any source or derived-text fingerprint change invalidates all generated
indexes, metrics, passage partitions, and validation records. Such a change
requires a separate source-update decision and a complete regeneration of the
Phase 2B evidence layer.

No source may move tier, gain a new analytical role, or enter a new
jurisdiction as an incidental consequence of an interesting result.

## Analytical Roles

The study uses the Phase 2A authority map without modification:

- Tier 1 supplies continuity, frame, reported testimony, the Time Traveller,
  and primary voice evidence.
- Tier 2 supplies bounded fictional evidence for dialogue, social interaction,
  scientific argument, catastrophe, observation, moral pressure, short-form
  architecture, and related declared roles.
- Tier 3 supplies bounded evidence for nonfiction explanation, scientific
  vocabulary, classification, analogy, humour, and period idiom.
- Tier 4 supplies negative and comparative controls for period convention,
  generic adventure, sensationalism, neighbouring voices, and false
  Victorianism.
- Tier 5 supplies no positive evidence and remains physically absent.

The analysis report must display these roles wherever cross-source comparisons
are made. A numerical table without authority context is incomplete.

## Story-Local Artifact Layout

Phase 2B adds the following tracked evidence layer:

```text
stories/time-expedition/source-study/
  analysis-plan.md
  analysis.yml
  holdouts.yml
  quantitative-profile.yml
  evidence-ledger.yml
  wells-profile.md
  period-controls.md
  validation.md
  observations/
    the-time-machine.md
    selected-short-fiction.md
    the-invisible-man.md
    the-island-of-doctor-moreau.md
    the-war-of-the-worlds.md
    certain-personal-matters.md
    text-book-of-biology-part-1.md
```

The existing `source-study/README.md` and `source-study/method.md` are updated
to mark Phase 2B active and to point to the adopted story-local protocol. The
tracked `analysis-plan.md` is the concise execution protocol for this corpus;
the present repository-level design remains the fuller rationale.

The earlier broad design proposed seven dimension-based files under
`findings/`. Phase 2B replaces that layout with source-level observation
dossiers plus a dimension-based `wells-profile.md`. This keeps direct
observation separate from cross-work synthesis while retaining the earlier
finding areas inside the ten analytical dimensions below.

Tier 4 controls do not receive positive-style observation dossiers. Their
comparative findings live in `period-controls.md`, where their negative-only
jurisdiction is explicit.

Generated and reproducible artifacts remain ignored under:

```text
build/time-expedition/source-study/
  corpus-lock.json
  passage-index.jsonl
  development-metrics.json
  development-metrics.csv
  development-report.md
  validation-metrics.json
  validation-packet.md
  analysis-report.md
```

Tracked Markdown and YAML contain the adopted protocol and interpretive record.
Generated JSON, CSV, and Markdown contain mechanical indexes, calculations,
and compiled review surfaces that can always be recreated from the tracked
state.

## Analysis Configuration

`source-study/analysis.yml` is the machine-readable study contract. It records:

- schema version;
- study ID and composition window;
- corpus-registry paths and expected registry fingerprints;
- authority-policy version;
- passage-index rules;
- deterministic partition seed;
- holdout proportions and whole-work holdouts;
- enabled measurements and any declared lexicons;
- analytical dimensions;
- claim confidence levels and validation classifications;
- generated-output paths.

The configuration is story-local so another future source study can use the
same tooling without inheriting Wells-specific assumptions. Wells-specific
lexicons and dimensions are declared data rather than hidden code constants.

## Passage Index

### Parsing

The deterministic layer reads retained Markdown through Pandoc's JSON AST. It
never rewrites the retained witnesses. Headings establish structural context;
substantive paragraphs, block quotations, verse blocks, and list items become
indexable passage blocks. Images, empty blocks, and residual structural
apparatus do not become analytical passages.

The parser preserves:

- analytical witness ID;
- source ID and retained Markdown fingerprint;
- selection ID when the witness comes from the bounded omnibus;
- heading path and chapter or section label;
- block type;
- one-based block ordinal inside the source;
- one-based ordinal inside the current heading path;
- normalized analysis text;
- original text;
- word count;
- direct-dialogue classification where determinable;
- a content hash.

### Stable Passage IDs

Each passage receives an ID of the form:

```text
<witness-id>:<heading-slug>:<source-ordinal>:<hash12>
```

The ordinal makes the passage easy to locate in reading order. The truncated
content hash detects stale references if source text moves or changes. A
heading path and adjacent passage IDs are included in generated reports so a
short quotation never loses its narrative context.

Evidence records cite passage IDs, not raw Markdown line numbers. Human-facing
reports may show current line numbers as conveniences, but line numbers are
never the canonical locator.

### Context Windows

Close reading and validation operate on passage windows rather than isolated
sentences. A window contains a focal passage plus up to two substantive blocks
on either side, constrained by section boundaries. The focal passage remains
the cited evidence; neighbouring blocks provide context and are not silently
counted as additional support.

## Holdout Design

Held-out validation is an overfitting check, not an authorship experiment.
The partition is committed before quantitative profiling or close reading.

### Whole-Work Holdout

The complete retained witness for `selected-short-fiction/the-star` is held
out from development. Its short form, cosmic scale, observational movement,
and date make it a useful test of whether the profile can accommodate
authentic Wells material not used to construct candidate claims.

The source remains visible in the corpus registry but its passages cannot be
cited in candidate development claims.

### Within-Work Holdouts

Every other Wells witness is divided in reading order into non-overlapping
windows of up to five substantive blocks. A window never crosses a heading
boundary; a final window may contain fewer than five blocks. For a witness with
`n` eligible windows, the holdout count is
`max(1, floor((0.2 * n) + 0.5))`.

Selection is deterministic. Windows are ranked by SHA-256 of:

```text
<partition-seed>:<source-id>:<first-passage-id>
```

Each window is assigned to the first, middle, or final third by
`floor(3 * (window_index - 1) / n)`, capped at `2`. If the holdout count is at
least three and all thirds contain an eligible window, the lowest-hash window
from each third is selected first. Remaining places are filled by global hash
rank among unselected windows. If fewer than three places are available, or a
third has no eligible window, all places are filled by global hash rank. Hash
ties are resolved by source order.

### Control Quarantine

All Tier 4 control texts are quarantined during positive Wells-profile
development. They are opened only after candidate claims and development-set
measurements have been frozen. This prevents control authors from becoming
unacknowledged ingredients in the positive profile.

### Holdout Manifest

`holdouts.yml` records:

- partition seed and algorithm version;
- every retained source fingerprint;
- the complete whole-work holdout;
- development and holdout window IDs for every Wells witness;
- passage IDs in every window;
- generation timestamp and tool version.

Once committed, the manifest is immutable for Phase 2B. Regenerating a
different partition is a blocking error unless the design is explicitly
reopened.

### Leakage Gate

Before validation begins, the evidence ledger and observation dossiers may not
reference a held-out passage ID or a Tier 4 passage ID as positive evidence.
The checker reports leakage as a blocking error.

The source files necessarily remain accessible in the repository; the system
cannot make them cryptographically secret. The enforceable guarantee is that
tracked development claims, observations, and generated development reports
cannot contain held-out references or control-derived positive evidence.

## Deterministic Measurement Layer

### Measurement Policy

Measurements are reported per work and, where useful, per structural section.
Cross-work summaries show every component result and never expose only a pooled
number. Counts are normalized per 1,000 words where appropriate, accompanied
by raw counts and denominators.

The initial layer deliberately avoids dependency on a large statistical or
language model. Pandoc supplies structural parsing; documented Python logic
supplies tokenization and transparent heuristics. Sentence segmentation rules
are fixture-tested against representative Victorian punctuation and reported
as an acknowledged approximation.

### Core Measurements

The generated profile includes:

- total words, passages, sentences, and sections;
- sentence-length distribution, including median, quartiles, deciles, and
  tails;
- passage- and paragraph-length distributions;
- direct-dialogue proportion and dialogue-run lengths;
- question, exclamation, colon, semicolon, parenthesis, ellipsis, and dash
  frequencies;
- speech-attribution and reporting-verb frequencies from an explicit lexicon;
- first-person, third-person, demonstrative, modal, and epistemic-marker
  frequencies from declared lexicons;
- function-word frequencies and function-word sequence frequencies;
- paragraph-opening and transition categories;
- lexical concentration using length-aware moving-window measures;
- narrative, dialogue, quotation, verse, and list block proportions;
- chapter- or section-level variation for the same measurements.

No generated output exposes a ranked bank of reusable Wells phrases. Lexical
analysis reports normalized counts and short diagnostic contexts only when a
human needs to audit a measurement.

### Candidate Heuristics

Some dimensions cannot be measured without interpretation. The tooling may
flag candidates for close reading, including:

- dense modality or qualification;
- transitions from sensory observation to explanation;
- unusually long or short sentence and paragraph runs;
- dialogue-heavy social scenes;
- clusters of questions, exclamations, or parenthetical qualifications;
- extreme passages relative to the same work's distribution.

These flags are sampling aids. They do not become findings until a cited
close-reading record distinguishes observation from inference and considers
nearby context.

### Quantitative Profile

`quantitative-profile.yml` stores adopted descriptive baselines after review.
It references generated metric IDs and records per-witness values, variation,
measurement limitations, and candidate interpretive relevance. Each of the
four retained short stories remains a separate witness. The profile never
contains a single pooled target for Wells.

## Close-Reading Framework

Close reading proceeds only over development passages and uses the retained
authority map. Each observation dossier includes representative passages,
extreme passages identified by measurement, and passages that resist an
emerging account.

The required analytical dimensions are:

1. frame architecture and reported testimony;
2. narrator distance, focalisation, and mediation;
3. observation, inference, speculation, and self-correction;
4. scientific exposition, analogy, qualification, and uncertainty;
5. dialogue, speech attribution, class, and social friction;
6. syntax, rhythm, punctuation, and paragraph movement;
7. diction, figurative language, and descriptive selectivity;
8. suspense, revelation, danger, and scene pressure;
9. humour, irony, tonal shifts, and controlled awkwardness;
10. transitions, compression, reflection, and ending logic.

Each observation entry distinguishes:

- observation: what is directly present in the cited passage;
- inference: the proposed significance of that observation;
- jurisdiction: what source role allows the passage to support;
- comparison: related or contrary Wells passages;
- limitation: why the observation may be local rather than general;
- candidate claim IDs, if any.

The dossiers preserve work-level differences. They do not need to force every
dimension onto every source.

## Evidence Ledger

### Structure

`evidence-ledger.yml` is the canonical claim store. Its top-level `claims`
list contains records with:

- `id`;
- `dimension`;
- `statement`;
- `mode`, fixed to `descriptive` in Phase 2B;
- `jurisdiction`;
- `classification`;
- `status`;
- `confidence`;
- `supporting_passages`;
- `counterexample_passages`;
- `counterexample_search`;
- `control_results`;
- `scope_and_limits`;
- `validation_expectation`;
- `prohibited_overgeneralisation`;
- `notes`.

Permitted classifications are:

- `wells_distinctive`;
- `wells_characteristic_but_shared`;
- `role_specific`;
- `period_general`;
- `unsupported`.

Development statuses are `candidate`, `qualified`, and `rejected`. Validation
adds `validated`. Confidence values are `tentative`, `moderate`, and `strong`.
No development claim may be `strong` or `validated` before the validation
stage.

### Evidence References

Every passage reference records:

- analytical witness ID;
- source ID;
- selection ID when applicable;
- passage ID;
- authority tier;
- evidence role;
- a short relevance note.

Evidence roles are `support`, `counterexample`, `variation`, `control`, and
`validation`. Tier 4 passages may use only `control`. Held-out passages may use
only `validation` after the development profile is frozen.

### Claim Rules

A cross-work candidate claim requires support from at least two Wells
witnesses. The four selected short stories count as separate witnesses, but a
claim supported only by selections from the same omnibus must disclose that
edition-level dependence. A source-specific or role-specific claim may use one
witness only when its jurisdiction and scope explicitly say so. A continuity
claim may rely solely on *The Time Machine* because no other source has
continuity authority.

Every non-rejected claim must include either:

- at least one material counterexample or variation passage; or
- a documented counterexample search naming the sources, dimensions, and
  search method, with a statement that no material counterexample was found.

Absolute terms such as `always`, `never`, and `invariably` are rejected unless
the evidence covers every eligible passage and the claim is genuinely
exceptionless. The report treats such wording as presumptively erroneous.

A claim cannot be promoted merely because its metric is extreme. Quantitative
evidence and close-reading evidence must be linked but remain distinguishable.

The earlier broad design anticipated a `permitted operational use` field. In
Phase 2B all operational use is fixed to `none`; operational permissions are
assigned only by the separately approved Phase 2C design. The Phase 2B ledger
instead records classification, scope, limits, and prohibited
overgeneralisation so later distillation cannot outrun the evidence.

### Authority Validation

The checker blocks:

- Tier 4 evidence used as positive support;
- Tier 2 or Tier 3 evidence used for continuity;
- evidence outside a source's permitted analytical roles;
- references to an excluded or unretained source;
- unknown, stale, or fingerprint-mismatched passage IDs;
- held-out evidence cited during development;
- a `strong` or `validated` development claim;
- missing scope, limitation, or counterexample-search information.

## Candidate Synthesis

`wells-profile.md` is the human-readable descriptive synthesis. It is authored
from, and editorially reconciled with, the quantitative profile, observation
dossiers, and evidence ledger.

The profile is organised by analytical dimension rather than by source. Each
section includes:

- the narrowly worded descriptive finding;
- classification and confidence;
- jurisdiction;
- representative supporting evidence;
- material variation and counterexamples;
- quantitative context where relevant;
- distinction from period controls after validation;
- unresolved uncertainty.

The profile may say what a future operational phase will need to decide. It
may not contain imperatives, preferred phrasings, generation examples, target
thresholds, or direct instructions to imitate Wells.

Before validation, the candidate profile and evidence ledger are frozen by
recording their Git commit and SHA-256 fingerprints in `validation.md`.

## Validation

### Stage One: Held-Out Wells Material

The validation command unlocks the committed Wells holdouts only after the
candidate profile and ledger fingerprints are supplied. It generates metrics
and context packets for those passages without modifying development results.

Each candidate claim carries a predeclared validation expectation. An
expectation may be:

- directional quantitative replication;
- presence across an unseen role-matched passage set;
- accommodation of authentic variation without contradiction;
- absence from a source jurisdiction where it should not apply;
- qualitative confirmation by an independent reviewer.

The study reports source-wise directions and transparent effect sizes. It does
not convert passage windows into pseudo-independent samples for conventional
significance tests.

### Stage Two: Period Controls

After the Wells holdout assessment, all Tier 4 controls are measured and
examined within their declared negative roles. Candidate findings are then
classified as:

- plausibly Wells-distinctive within this corpus;
- characteristic of Wells but also present in neighbouring prose;
- specific to a Wells work or narrative role;
- general late-Victorian convention;
- unsupported or contradicted.

A shared control feature is not discarded automatically. Its classification
and operational limits are corrected so Phase 2C cannot mistake historical
plausibility for Wellsian distinctiveness.

### Stage Three: Independent Review

A fresh reviewer receives:

- the frozen candidate profile;
- evidence-ledger claims and locators;
- anonymised held-out and control passage packets where practical;
- generated measurements and limitations;
- the authority policy.

The reviewer checks claim discrimination, scope, counterexamples, authority
leakage, and fit to unseen authentic Wells variation. Blind passage judgement
is supplementary evidence, not an authorship verdict.

### Validation Outcomes

Each candidate claim becomes one of:

- `validated` with retained or adjusted confidence;
- `qualified` with narrowed jurisdiction or classification;
- `rejected` with the failed expectation recorded.

Rejected claims remain in the ledger. They are not deleted from the historical
record of the analysis.

`validation.md` records the frozen input hashes, holdout results, control
comparisons, reviewer findings, claim transitions, unresolved uncertainty, and
final profile fingerprint.

## Period-Control Report

`period-controls.md` is organised by candidate Wells claim, not as five
positive author profiles. For each comparison it records:

- the Wells claim under test;
- the specific control role that authorises comparison;
- quantitative similarities or differences;
- cited control passages;
- whether the feature remains distinctive, shared, role-specific, or
  period-general;
- prohibited inferences.

The report does not describe how to write like Haggard, Doyle, Kipling, Marsh,
or Allen. It exists to prevent their practices from being mistaken for Wells.

## Public Command Interface

Phase 2B adds one staged command family:

```text
creative-writer source-analysis --story <slug> --stage prepare
creative-writer source-analysis --story <slug> --stage develop
creative-writer source-analysis --story <slug> --stage validate
```

The Make interface is:

```text
make source-analysis STORY=<slug> STAGE=prepare
make source-analysis STORY=<slug> STAGE=develop
make source-analysis STORY=<slug> STAGE=validate
```

`prepare` performs source admission, locks corpus fingerprints, generates the
passage index, and creates or verifies the holdout manifest.

`develop` verifies the lock and holdout manifest, generates development-only
metrics and sampling aids, validates tracked observations and candidate claims,
and writes the development report.

`validate` requires frozen candidate-profile and ledger fingerprints, opens
the held-out and control partitions, generates validation measurements and
packets, validates claim outcomes, and writes the compiled analysis report.

The command does not write interpretive observations or claims. Agents and
humans author those tracked files; the command validates and compiles them.

## Internal Components

Implementation should keep focused modules:

- `source_analysis_models.py` for analysis configuration, passage, holdout,
  metric-profile, evidence-ledger, and validation schemas;
- `source_passages.py` for Pandoc-AST parsing, passage IDs, heading paths, and
  context windows;
- `source_metrics.py` for transparent deterministic measurements;
- `source_analysis.py` for staged orchestration, authority checks, leakage
  checks, and report generation;
- existing `cli.py` and the `Makefile` for the public interface.

The design does not require these exact filenames if implementation uncovers a
clearer small-module boundary. It does require parsing, measurement, schemas,
and orchestration not to collapse into one monolithic module.

## Data Flow

```text
admitted source registries and fingerprinted Markdown
  -> corpus lock
  -> Pandoc passage index
  -> deterministic holdout manifest
  -> development-only per-work metrics
  -> source-linked close-reading observations
  -> candidate evidence ledger and descriptive profile
  -> frozen candidate fingerprints
  -> held-out Wells validation
  -> Tier 4 negative-control comparison
  -> independent review
  -> validated evidence ledger and Wells profile
  -> human Phase 2B completion gate
```

At no point does the data flow continue automatically into a style card or
story plan.

## Failure Handling

The following are blocking failures:

- source admission fails;
- a registry or retained-source fingerprint differs from the corpus lock;
- the physical corpus differs from the declared corpus;
- Pandoc parsing fails or produces an empty index;
- a passage ID is duplicated, stale, or unresolved;
- the holdout manifest differs from the committed partition;
- development outputs expose held-out or Tier 4 positive evidence;
- evidence uses a source outside its authority jurisdiction;
- a claim lacks required scope, limits, or counterexample treatment;
- a generated metric silently pools works;
- candidate profile fingerprints differ from those frozen for validation;
- a final claim outcome is absent from the validation record;
- Phase 2B modifies style guidance, story planning, or manuscript prose.

Warnings requiring interpretation include:

- sentence segmentation ambiguity;
- a measurement that is highly sensitive to quotation or verse handling;
- a large within-work difference;
- disagreement among Wells witnesses;
- a candidate feature common in controls;
- an authentic holdout passage outside a development range;
- an independent reviewer unable to discriminate a candidate tendency.

Warnings remain visible in reports. The system responds by qualifying claims,
not by suppressing inconvenient evidence.

## Testing Strategy

### Schema Tests

Tests cover valid and invalid analysis configuration, passage records,
holdout manifests, quantitative profiles, evidence-ledger claims, authority
references, classifications, confidence transitions, and validation records.

### Passage Tests

Small Markdown fixtures cover headings, paragraphs, dialogue, block quotes,
verse, lists, Victorian punctuation, empty blocks, stable passage IDs, context
windows, duplicate detection, and changed-content invalidation.

### Partition Tests

Tests prove deterministic holdout selection, whole-work quarantine, per-work
minimums, first/middle/final coverage, source-fingerprint binding, and
rejection of a regenerated partition with a changed seed or algorithm.

### Metric Tests

Known fixtures verify raw counts, denominators, normalization, sentence and
passage distributions, dialogue classification, punctuation, lexicons,
function words, lexical concentration, and strict separation among works.

### Authority And Leakage Tests

Tests reject Tier 4 positive support, noncanonical continuity, unpermitted
source roles, unknown passage IDs, held-out development evidence, premature
strong confidence, and final outcomes unsupported by validation records.

### Pipeline Tests

A synthetic mini-corpus exercises `prepare`, `develop`, and `validate`
end-to-end. Golden reports verify deterministic ordering and human-readable
output. A Time Expedition smoke test verifies exact Phase 2A corpus counts and
ensures source analysis remains excluded from manuscript statistics and builds.

### Historical Negative Tests

The two Phase 2A corpus-integrity defects remain protected: a truncated final
EPUB member and destructive removal of literary `pgmonospaced` blocks must
continue to fail their existing regressions.

### Repository Verification

Completion requires:

- `make source-admission STORY=time-expedition`;
- all three staged source-analysis commands in order;
- `make check STORY=time-expedition`;
- `make stats STORY=time-expedition` with source-study material excluded;
- the complete test suite;
- fingerprint, locator, holdout, authority, and claim-integrity audits;
- a changed-path audit proving no Phase 2C or manuscript artifact changed.

## Review Sequence

Phase 2B is too interpretive for a single final review. It uses staged gates:

1. protocol and holdout review before measurement;
2. deterministic tooling and generated-metric review;
3. per-work observation review before synthesis;
4. candidate evidence-ledger and profile review before holdouts open;
5. held-out and control validation review;
6. independent whole-study audit;
7. human review of the compiled analysis report.

The same agent should not author the candidate profile and serve as its only
independent validator.

## Human Review Surface

`build/time-expedition/source-study/analysis-report.md` is the principal human
handoff. It compiles:

- corpus and authority summary;
- analytical method and limitations;
- per-work quantitative baselines;
- close-reading findings by dimension;
- representative support and counterexamples;
- held-out results;
- period-control comparisons;
- claim classifications and confidence;
- rejected claims and unresolved questions;
- Phase 2C handoff recommendations without operational instructions.

The report links every material conclusion to the tracked evidence ledger and
passage index.

## Phase 2B Completion Criteria

Phase 2B is complete only when:

1. the Phase 2A corpus lock passes without change;
2. the passage index resolves every retained Wells and control witness;
3. the committed holdout manifest predates detailed analysis and validates;
4. all measurements are reproducible and reported per work;
5. all seven observation dossiers are complete and passage-linked;
6. the quantitative profile records values, variation, and limitations;
7. every material profile statement maps to a valid evidence-ledger claim;
8. every non-rejected claim records counterexamples or a documented search;
9. no development claim leaks held-out or positive Tier 4 evidence;
10. the candidate profile is frozen before validation;
11. held-out Wells and Tier 4 control results are recorded for every candidate
    claim;
12. rejected and qualified claims remain visible;
13. an independent reviewer approves the final evidence layer;
14. the generated analysis report is complete and human-readable;
15. all repository and corpus checks pass;
16. no style-card, Permian-planning, anthology-planning, or manuscript prose
    file has changed;
17. a human explicitly approves Phase 2B before Phase 2C begins.

## Phase 2C Handoff Boundary

Phase 2C may consume only validated or explicitly qualified claims from the
Phase 2B evidence ledger. It may not treat raw metrics, rejected hypotheses,
or Tier 4 control practices as positive writing guidance.

Phase 2C will decide how validated description becomes:

- operational style rules;
- anti-drift warnings;
- bounded tolerances rather than rigid averages;
- a reusable style-lint profile backed by evidence-ledger claim IDs;
- role-matched reference packets;
- chapter, story, and anthology authenticity gates;
- revisions to `style-guide.md` and `style-card.md`.

Features classified as `period_general` may inform historical plausibility but
cannot be labelled distinctively Wellsian. Features classified as
`unsupported` remain prohibited from operational use. Any ambiguity in the
handoff is resolved by narrowing the operational rule rather than widening the
evidence claim.

Phase 2C requires a separate design approval. Phase 2B completion does not
authorise it automatically.

### Deferred General Style-Linter Handoff

A general stylistic linter is a valuable Phase 2C application of the evidence
layer. It is deliberately deferred because an 1890s Wells profile must be
derived from validated findings, not encoded from prior impressions and then
used to confirm those impressions.

The repository already has two partial mechanisms:

- `make check` runs contract-configured em-dash and contrastive-parallelism
  heuristics as non-blocking style warnings;
- `make ai-audit` runs the local `audit-ai-writing` narrative scanner and
  generates a manual-review report.

Phase 2C should unify their useful ideas without making either mechanism a
style authority. The likely public interface is:

```text
creative-writer style-lint --story <slug> [--profile <profile-id>]
make style-lint STORY=<slug> [PROFILE=<profile-id>]
```

The final Phase 2C design should use composable profiles rather than a single
hard-coded Wells checker:

- a general manuscript-hygiene profile for tool residue, placeholders,
  malformed markup, and objective contract violations;
- an AI-surface-risk profile derived from the `audit-ai-writing` rubric,
  including stock vocabulary clusters, false balance, over-neat cadence,
  theme explanation, bodily-emotion shorthand, sealed-world symptoms, and
  other narrative signals;
- a story-selected authorial profile compiled only from validated Phase 2B
  claims and per-witness ranges;
- negative drift controls that can warn about generic Victorianism,
  neighbouring adventure prose, or resemblance to a Tier 4 control without
  treating that control as a positive writing model.

The linter should support three complementary rule families:

1. deterministic rules for exact residues, configured phrases, punctuation,
   repetition, and transparent counts;
2. distributional diagnostics comparing a draft with per-witness ranges and
   authentic Wells variation, never with one pooled target;
3. evidence-guided review prompts for phenomena that require interpretation,
   such as over-explained theme, implausibly smooth epistemic progression, or
   drift toward another author.

Style results should use distinct severities:

- `error` only for objective failures such as malformed configuration, tool
  residue explicitly prohibited by contract, or an unresolved source/profile
  reference;
- `warning` for strong rule clusters or material departure from a configured
  authorial profile;
- `advisory` for weak signals, authentic-tail observations, and passages that
  need human reading.

Authorial deviations and AI-surface signs are warnings or advisories by
default. They are not proof of AI authorship, bad prose, or inauthenticity. A
single word, em dash, sentence length, or rhetorical pattern must never be
treated as decisive. Reports should emphasise converging clusters and show the
surrounding passage.

Every Wells-specific lint rule should record:

- the Phase 2B evidence-ledger claim IDs from which it was derived;
- analytical dimension and jurisdiction;
- applicable narrative modes;
- measurement or heuristic definition;
- authentic Wells range and material counterexamples;
- warning threshold and reason for that threshold;
- known false-positive conditions;
- whether the feature is Wells-distinctive, shared, role-specific, or merely
  period-general;
- revision guidance that describes the mismatch without supplying imitation
  phrases.

The linter must preserve the distinction between absence and excess. For
example, a device frequent in one Wells witness may be optional rather than
required, while an excessive concentration may still indicate mechanical
imitation. Authentic passages in the tails of Wells's own distribution must
remain visible as counterexamples rather than being labelled failures.

AI-surface checks should retain the `audit-ai-writing` skill's governing
cautions:

- risk signals are not authorship detection;
- clusters matter more than isolated tokens;
- genre and intended voice change interpretation;
- revision should restore concrete intention rather than synonym-swap flagged
  words;
- fluent, polished, historically mannered prose is not suspicious merely for
  being fluent, polished, or mannered.

Calibration against the authentic target is mandatory. On 2026-07-15, the
current generic narrative scanner rated the retained *Time Machine* witness
`high surface risk`. Its reasons included 175 em dashes, 222 triad-like
sentences, 28 parallelism hits, and 13 Markdown headings. Those results do not
make Wells's prose machine-like. They demonstrate that raw generic risk labels
cannot be imported into an author-specific workflow.

Before a general AI-surface rule enters a story profile, Phase 2C must run it
over the canonical and bounded source witnesses and record its authentic
baseline, document-structure sensitivity, and known false positives. The
combined linter may then:

- preserve a modern residue rule when the pattern has no authentic target
  analogue;
- assess concentration or clustering relative to genuine per-witness ranges;
- restrict a rule to a narrative mode where it remains discriminating;
- downgrade it to a manual-review prompt;
- disable it for that authorial profile while retaining it in the general
  profile.

The external scanner's aggregate `risk` label must not become an input to a
Wells authenticity judgement. Its individual observations may contribute only
after this calibration and with their original caution intact.

The final report should separate rather than collapse:

- objective manuscript hygiene;
- general AI-surface risk;
- departure from the selected authorial profile;
- resemblance to negative controls;
- unresolved interpretive questions.

A single aggregate authenticity score is prohibited. Such a score would hide
authority, genre, uncertainty, and contradictory evidence. The report should
instead give passage-level findings, chapter summaries, cumulative drift
signals, evidence provenance, and explicit manual-review questions.

The Phase 2C design must decide whether to internalise a stable rule pack from
the external `audit-ai-writing` scanner or retain it through an adapter. Phase
2B imposes only two requirements on that decision: the repository must remain
usable without silently depending on mutable external rules, and the original
skill must remain available as the richer manual editorial workflow.

No linter work begins in Phase 2B. This section records the required handoff so
the measurements, evidence classifications, counterexamples, and validation
results produced now will support a general system later without biasing the
forensic analysis.

## Explicit Stop Point

After the validated profile and analysis report receive human approval, work
stops. The next action is to propose the Phase 2C operational-distillation
design. No Permian Q&A, scientific research, story architecture, frame scene,
or narrative prose begins as part of this goal.
