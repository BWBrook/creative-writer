# Wells Phase 2B Detailed Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a reproducible, source-linked, held-out, independently reviewed descriptive profile of H. G. Wells's fictional practice circa 1895-1899, while stopping before any operational pastiche guidance, style linter, Permian planning, or manuscript prose.

**Architecture:** Add a story-local analysis contract and evidence schemas, parse the fingerprinted Phase 2A Markdown witnesses through Pandoc JSON into stable passage records, commit a deterministic Wells holdout partition before analysis, and expose staged `prepare`, `develop`, and `validate` orchestration. Deterministic metrics and authority/leakage checks support, but never replace, source-level close reading. Candidate claims and profile are committed and fingerprinted before held-out Wells passages and Tier 4 controls can enter validation.

**Tech Stack:** Python 3.12, Pydantic 2, PyYAML, pytest, Pandoc JSON AST, GNU Make, Git, Markdown, YAML, JSON, JSON Lines, CSV.

## Global Constraints

- Phase 2B remains descriptive. It must not edit `style-guide.md`, `style-card.md`, any manuscript prose, any chapter stub, or any Permian/anthology plan.
- The author-specific and generic style-linter work is Phase 2C. No Wells-compliance score, AI-writing score, imitation threshold, phrase bank, or writing prescription is implemented here.
- The admitted corpus remains exactly thirteen admission records, twelve retained EPUBs, fifteen Markdown witnesses, four selected short stories, and one excluded/unacquired Tier 5 source.
- *The Time Machine* remains the sole Tier 1 continuity authority. Tier 2 and Tier 3 sources remain bounded by their declared analytical roles. Tier 4 sources are negative/comparative controls only and may never support a positive Wells claim.
- `selected-short-fiction/the-star` is the whole-work holdout. Every other Wells witness receives deterministic within-work holdouts before detailed analysis.
- Passage IDs are `<witness-id>:<heading-slug>:<source-ordinal>:<hash12>` and remain the canonical evidence locators; line numbers are advisory only.
- The passage parser reads retained Markdown through Pandoc JSON AST and never rewrites source witnesses.
- All metrics are reported per witness and, where useful, per section. No output may expose only a pooled Wells average.
- Interpretive observations and claims are human/agent authored. Commands generate indexes, measurements, audit packets, validation checks, and compiled reports but do not invent literary findings.
- Candidate observations and evidence may not reference held-out Wells passages or Tier 4 passages. Tier 4 passages use only the `control` evidence role; held-out passages use only `validation` after candidate freeze.
- Development claims use only `candidate`, `qualified`, or `rejected` status and `tentative` or `moderate` confidence. `validated` status and `strong` confidence are unavailable until validation.
- Every non-rejected claim needs material variation/counterevidence or a documented counterexample search. Cross-work claims need at least two Wells witnesses unless explicitly source-, role-, or continuity-specific.
- Candidate `wells-profile.md` and `evidence-ledger.yml` are committed and SHA-256 fingerprinted in `validation.md` before `validate` opens held-out Wells or Tier 4 material.
- Rejected claims remain in the final ledger. There is no aggregate authenticity score and no conventional significance testing over passage windows.
- Generated outputs remain under ignored `build/time-expedition/source-study/`; tracked Markdown/YAML is canonical.
- Use test-driven development for code behavior: add a focused failing test, confirm the expected RED result, add the minimum implementation, confirm GREEN, then refactor.
- Each implementation task receives a fresh worker and task-scoped review. A fresh final reviewer audits the complete Phase 2B change before completion.

---

## File Map

- `src/creative_writer/source_analysis_models.py`: analysis contract, passage, partition, metric-profile, evidence-ledger, and validation schemas.
- `src/creative_writer/source_passages.py`: Pandoc JSON parsing, text extraction, stable passage IDs, section context, passage windows, and JSONL persistence.
- `src/creative_writer/source_metrics.py`: documented tokenisation, sentence approximation, per-witness/section metrics, candidate sampling flags, and CSV/JSON/report rendering.
- `src/creative_writer/source_analysis.py`: staged orchestration, corpus lock, deterministic partitioning, authority/leakage checks, freeze verification, validation packets, and compiled reports.
- `src/creative_writer/cli.py`: `source-analysis --story --stage` interface.
- `Makefile`: `source-analysis STORY=<slug> STAGE=<prepare|develop|validate>` interface.
- `tests/test_source_analysis_models.py`: schema and state-invariant tests.
- `tests/test_source_passages.py`: AST, locator, context, and window tests.
- `tests/test_source_metrics.py`: deterministic measurement tests.
- `tests/test_source_analysis.py`: staged pipeline, partition, authority, leakage, freeze, and report tests.
- `stories/time-expedition/source-study/analysis.yml`: Wells study contract and declared lexicons/dimensions.
- `stories/time-expedition/source-study/analysis-plan.md`: concise adopted execution protocol.
- `stories/time-expedition/source-study/holdouts.yml`: immutable generated Wells partition.
- `stories/time-expedition/source-study/quantitative-profile.yml`: reviewed per-witness descriptive baselines.
- `stories/time-expedition/source-study/evidence-ledger.yml`: canonical claims and evidence references.
- `stories/time-expedition/source-study/wells-profile.md`: dimension-organised descriptive synthesis.
- `stories/time-expedition/source-study/period-controls.md`: claim-organised negative-control findings.
- `stories/time-expedition/source-study/validation.md`: freeze hashes, held-out results, reviewer findings, transitions, and final fingerprint.
- `stories/time-expedition/source-study/observations/*.md`: seven source-level development dossiers.
- `stories/time-expedition/source-study/README.md`: phase state and artifact guide.
- `stories/time-expedition/source-study/method.md`: implemented method and authority boundary.
- `README.md`: public command documentation.

---

### Task 1: Define Analysis Schemas and the Story-Local Protocol

**Files:**
- Create: `src/creative_writer/source_analysis_models.py`
- Create: `tests/test_source_analysis_models.py`
- Create: `stories/time-expedition/source-study/analysis.yml`
- Create: `stories/time-expedition/source-study/analysis-plan.md`
- Create: `stories/time-expedition/source-study/quantitative-profile.yml`
- Create: `stories/time-expedition/source-study/evidence-ledger.yml`
- Create: `stories/time-expedition/source-study/wells-profile.md`
- Create: `stories/time-expedition/source-study/period-controls.md`
- Create: `stories/time-expedition/source-study/validation.md`
- Create: `stories/time-expedition/source-study/observations/the-time-machine.md`
- Create: `stories/time-expedition/source-study/observations/selected-short-fiction.md`
- Create: `stories/time-expedition/source-study/observations/the-invisible-man.md`
- Create: `stories/time-expedition/source-study/observations/the-island-of-doctor-moreau.md`
- Create: `stories/time-expedition/source-study/observations/the-war-of-the-worlds.md`
- Create: `stories/time-expedition/source-study/observations/certain-personal-matters.md`
- Create: `stories/time-expedition/source-study/observations/text-book-of-biology-part-1.md`

**Interfaces:**
- `AnalysisConfig`: schema version `1`; study ID; composition window; study status (`protocol`, `development`, `candidate_frozen`, `validated`); admission/source registry paths and SHA-256 values; authority-policy version; passage/parser rules; partition seed, algorithm version, `0.2` fraction, five-block windows, and whole-work holdouts; enabled measurements; declared lexicons; ten analytical dimensions; confidence/status/classification vocabularies; generated paths.
- `PassageRecord`: witness/source/selection identity; source fingerprint; heading path/label; block type; source and heading ordinals; normalized and original text; word count; direct-dialogue classification; content hash; passage ID.
- `HoldoutManifest`: schema version; seed/algorithm/tool version; creation timestamp; registry hashes; source fingerprints; whole-work holdouts; and per-witness development/holdout windows with passage IDs.
- `QuantitativeProfile`: generated metric references plus reviewed per-witness values, variation, limitations, and interpretive relevance.
- `EvidenceLedger`: exact design fields, descriptive mode only, fixed classifications/statuses/confidences/evidence roles, and explicit operational use `none` by omission rather than an operational instruction field.
- `ValidationRecord`: candidate commit/hash fields, holdout/control/reviewer summaries, claim transitions, unresolved uncertainty, final profile hash, and stage.

- [ ] Write parsing tests for complete valid `analysis.yml`, holdout, quantitative-profile, evidence-ledger, and validation fixtures.
- [ ] Write focused invalid-shape tests for unknown enum values, duplicate dimension/claim IDs, malformed SHA-256 values, empty required text, mismatched selection identity, and development-stage `validated`/`strong` claims.
- [ ] Run `uv run pytest tests/test_source_analysis_models.py -q` and confirm RED because the models do not exist.
- [ ] Implement strict Pydantic models with `extra="forbid"`, reusable slug/path/hash types, uniqueness validators, and clear error messages.
- [ ] Run `uv run pytest tests/test_source_analysis_models.py -q` and confirm GREEN.
- [ ] Populate `analysis.yml` with the actual Phase 2A registry hashes, exact Wells/Tier 4 dimensions and roles, transparent lexicons, parser/partition constants, and generated paths.
- [ ] Add concise tracked protocol and evidence-surface files. Before evidence work, dossiers and synthesis files may contain only adopted method/headings and explicit phase-state notes, never fabricated findings or `TBD` placeholders.
- [ ] Validate every YAML file through the new models and run `git diff --check`.
- [ ] Commit the schema and protocol foundation.

### Task 2: Build the Pandoc Passage Index

**Files:**
- Create: `src/creative_writer/source_passages.py`
- Create: `tests/test_source_passages.py`
- Modify: `src/creative_writer/source_analysis_models.py`

**Interfaces:**
- `parse_markdown_witness(path, witness, pandoc="pandoc") -> list[PassageRecord]` invokes `pandoc --from=gfm --to=json` and raises `CreativeWriterError` on a missing executable, non-zero exit, malformed AST, or empty substantive result.
- `write_passage_index(path, passages)` emits deterministic UTF-8 JSON Lines sorted by registry/witness/source ordinal.
- `read_passage_index(path) -> list[PassageRecord]` validates every record and rejects duplicate passage IDs.
- `context_window(passages, passage_id, radius=2)` returns the focal passage and at most two substantive neighbours each side without crossing heading-path boundaries.
- `partition_windows(passages, max_blocks=5)` returns non-overlapping, heading-bounded windows in reading order.

- [ ] Add AST fixtures covering headings, paragraphs, block quotations, verse, nested lists, images, empty blocks, inline emphasis/quotes/notes, and Unicode punctuation.
- [ ] Add RED tests proving substantive block extraction, heading-path tracking, one-based ordinals, normalized/original text distinction, dialogue classification, stable ID format, `hash12`, duplicate rejection, two-sided context, and five-block heading-bounded windows.
- [ ] Run `uv run pytest tests/test_source_passages.py -q` and confirm the expected import/behavior failures.
- [ ] Implement a small recursive Pandoc inline/block text extractor; do not add a Markdown parser dependency or rewrite retained text.
- [ ] Generate IDs exactly as `<witness-id>:<heading-slug>:<source-ordinal>:<hash12>`, using `untitled` only when no heading exists and preserving witness IDs that contain `/`.
- [ ] Run `uv run pytest tests/test_source_passages.py -q` and confirm GREEN, then run `uv run pytest tests/test_source_models.py tests/test_source_admission.py -q` for regression coverage.
- [ ] Commit the passage-index implementation.

### Task 3: Implement Corpus Lock, Deterministic Holdouts, and `prepare`

**Files:**
- Create: `src/creative_writer/source_analysis.py`
- Create: `tests/test_source_analysis.py`
- Modify: `src/creative_writer/source_analysis_models.py`
- Modify: `src/creative_writer/source_passages.py`

**Interfaces:**
- `run_source_analysis(root, slug, stage) -> SourceAnalysisResult` is the orchestration entry point.
- `prepare` first calls `check_source_admission`; no analysis artifact is written when admission fails.
- `build_corpus_lock(...)` records exact registry hashes, every retained EPUB/Markdown fingerprint, witness identities, tiers, roles, and declared uses in `build/<slug>/source-study/corpus-lock.json`.
- `select_holdouts(...)` holds out all `selected-short-fiction/the-star`; partitions every other Wells witness into heading-bounded windows of up to five blocks; uses `max(1, floor((0.2 * n) + 0.5))`; hashes `<seed>:<source-id>:<first-passage-id>`; applies the specified tertile-coverage rule; resolves ties by source order; and excludes Tier 4 from development.
- First `prepare` writes tracked `holdouts.yml`. Later runs validate the existing manifest's semantic partition and preserve its original creation timestamp; any difference blocks rather than silently rewriting it.

- [ ] Create a synthetic two-Wells/one-control corpus fixture reusing the Phase 2A registries and real Pandoc parsing.
- [ ] Add RED tests for exact corpus-lock contents, four short selections as independent witnesses, whole-work holdout, round-half-up holdout counts, deterministic hash rank, tertile coverage, heading boundaries, Tier 4 quarantine, source-order tie resolution, and immutability on rerun.
- [ ] Add blocking tests for failed admission, registry hash drift, source fingerprint drift, duplicate/unresolved passages, empty index, changed seed/algorithm, and altered committed holdout membership.
- [ ] Run `uv run pytest tests/test_source_analysis.py -k 'prepare or holdout or corpus_lock' -q` and confirm RED.
- [ ] Implement `prepare`, writing `corpus-lock.json`, `passage-index.jsonl`, and tracked `holdouts.yml` only after all inputs validate.
- [ ] Ensure errors leave existing tracked holdouts untouched and provide exact source/witness context.
- [ ] Run the focused tests GREEN, then `uv run pytest tests/test_source_analysis_models.py tests/test_source_passages.py tests/test_source_analysis.py -q`.
- [ ] Commit the prepare-stage implementation.

### Task 4: Implement Transparent Per-Witness Metrics and `develop`

**Files:**
- Create: `src/creative_writer/source_metrics.py`
- Create: `tests/test_source_metrics.py`
- Modify: `src/creative_writer/source_analysis.py`
- Modify: `src/creative_writer/source_analysis_models.py`
- Modify: `tests/test_source_analysis.py`

**Interfaces:**
- `measure_witness(passages, config) -> WitnessMetrics` returns raw denominators, normalized frequencies, distributions, block proportions, section metrics, and flagged passage IDs for one witness.
- `measure_development(...)` receives only development passage IDs and writes `development-metrics.json`, `development-metrics.csv`, and `development-report.md` with each witness visible.
- Sentence segmentation and tokenization are documented approximations with fixtures for abbreviations, initials, Victorian quotation punctuation, ellipses, em dashes, contractions, and paragraph-final dialogue.
- Distribution output includes minimum, p10, p25, median, p75, p90, maximum, mean, and count without external numerical dependencies.
- Metrics cover every item named in the approved design and use only lexicons declared in `analysis.yml`.
- Candidate flags identify within-witness extremes and declared marker clusters only; they are labelled sampling aids, not findings.

- [ ] Add RED unit tests with hand-countable passages for word/sentence/section totals, distribution interpolation, normalized punctuation, dialogue proportion/run lengths, reporting verbs, pronoun/modal/epistemic/function-word lexicons, function-word bigrams, paragraph openings/transitions, moving-window lexical concentration, block proportions, per-section variation, and candidate flags.
- [ ] Add a regression test proving two witnesses remain separately visible and no pooled-only target is emitted.
- [ ] Run `uv run pytest tests/test_source_metrics.py -q` and confirm RED.
- [ ] Implement deterministic standard-library measurement helpers and concise documented limitations.
- [ ] Extend `develop` to verify the corpus lock and holdout manifest before measuring only development passages.
- [ ] Add pipeline tests proving held-out Wells and every Tier 4 passage ID are absent from development JSON, CSV, contexts, and report text.
- [ ] Run `uv run pytest tests/test_source_metrics.py tests/test_source_analysis.py -q` GREEN.
- [ ] Commit the metric/develop foundation.

### Task 5: Enforce Observation, Evidence, Authority, and Leakage Rules

**Files:**
- Modify: `src/creative_writer/source_analysis.py`
- Modify: `src/creative_writer/source_analysis_models.py`
- Modify: `tests/test_source_analysis.py`

**Interfaces:**
- `validate_observation_dossiers(...)` extracts declared passage IDs from the seven tracked dossiers, resolves every locator, and blocks held-out/control references during development.
- Observation entries use the fixed headings `Passage`, `Observation`, `Inference`, `Jurisdiction`, `Comparison`, `Limitation`, and `Candidate claims`; prose remains human-authored.
- `validate_evidence_ledger(...)` resolves all references against the passage index and registries; verifies source/selection/tier identity; enforces evidence-role, authority, continuity, stage, scope, counterexample, and cross-work-support rules; and reports every blocking issue together.
- `validate_profile_claim_links(...)` requires every material `wells-profile.md` finding section to declare one or more existing claim IDs and prevents orphaned non-rejected claims from disappearing from synthesis.

- [ ] Add RED tests for unknown/stale passage IDs, fingerprint mismatch, incorrect source/selection/tier metadata, Tier 4 support, Tier 2/3 continuity, role-jurisdiction violation, development holdout use, invalid evidence roles, premature `strong`/`validated`, missing scope/limits/counterexample treatment, absolute wording, and insufficient cross-work support.
- [ ] Add passing tests for a one-witness role-specific claim, a Time Machine continuity claim, a two-witness cross-work claim, documented no-counterexample search, rejected claim retention, and omnibus-dependence disclosure.
- [ ] Add dossier and profile-link tests, including multiple findings/claims and clear file/claim diagnostics.
- [ ] Run `uv run pytest tests/test_source_analysis.py -k 'authority or leakage or evidence or observation or profile' -q` and confirm RED.
- [ ] Implement the validators without model-generated interpretation or hidden source-role constants.
- [ ] Extend `develop` to validate tracked dossiers, quantitative-profile metric references, ledger claims, and candidate profile links after generating metrics; write a development report that separates deterministic results from authored interpretation.
- [ ] Run focused tests and the full source-analysis test set GREEN.
- [ ] Commit the evidence and authority gate.

### Task 6: Implement Candidate Freeze and Staged Validation

**Files:**
- Modify: `src/creative_writer/source_analysis.py`
- Modify: `src/creative_writer/source_analysis_models.py`
- Modify: `src/creative_writer/source_metrics.py`
- Modify: `tests/test_source_analysis.py`

**Interfaces:**
- `validate` refuses to open holdouts or controls unless `analysis.yml` has `study_status: candidate_frozen` or `validated` and `validation.md` records a reachable candidate Git commit plus exact SHA-256 hashes for the candidate `wells-profile.md` and `evidence-ledger.yml` at that commit.
- At `candidate_frozen`, `validate` verifies the freeze, measures held-out Wells and Tier 4 witnesses separately, and writes `validation-metrics.json`, `validation-packet.md`, and a provisional `analysis-report.md`; it does not promote claims automatically.
- At `validated`, `validate` additionally requires permitted final claim transitions, control and reviewer treatment for every non-rejected candidate claim, a current final profile hash, and complete tracked `period-controls.md`/`validation.md`; it then writes the final compiled report.
- Validation packets include witness/tier/role labels and context windows. Control evidence is clearly quarantined as negative/comparative material; no aggregate authenticity score is present.

- [ ] Add RED tests for missing/unreachable commit, changed profile/ledger hash, candidate files absent from the recorded commit, premature holdout/control output, missing claim expectation, illegal claim deletion, invalid status/confidence transition, unaddressed control comparison, missing reviewer result, and stale final profile hash.
- [ ] Add passing tests for candidate freeze, held-out/control packet generation, `validated`/`qualified`/`rejected` outcomes, retained rejected claims, and final compiled report.
- [ ] Run `uv run pytest tests/test_source_analysis.py -k 'freeze or validate or transition or compiled' -q` and confirm RED.
- [ ] Implement Git-object reads with non-interactive `git show <commit>:<path>` and SHA-256 verification; never mutate candidate evidence during validation.
- [ ] Generate separate source-wise effect summaries and limitations without significance tests or a composite score.
- [ ] Run focused tests and all source-analysis tests GREEN.
- [ ] Commit the freeze/validation implementation.

### Task 7: Wire the Public Interface and Synthetic End-to-End Test

**Files:**
- Modify: `src/creative_writer/cli.py`
- Modify: `Makefile`
- Modify: `README.md`
- Modify: `tests/test_source_analysis.py`
- Modify: `stories/time-expedition/source-study/README.md`
- Modify: `stories/time-expedition/source-study/method.md`

**Interfaces:**
- CLI: `creative-writer source-analysis --story <slug> --stage prepare|develop|validate`.
- Make: `make source-analysis STORY=<slug> STAGE=<prepare|develop|validate>`.
- CLI returns `0` only when the requested stage completes without blocking issues; errors use the existing `CreativeWriterError` path and non-zero exit.

- [ ] Add RED parser and command tests for all three stages, invalid stage handling, output-path messages, and non-zero blocking failures.
- [ ] Add a synthetic Git-backed mini-corpus scenario that runs `prepare`, commits holdouts, runs `develop`, commits/fingerprints a candidate, runs candidate validation, records final outcomes, and runs final validation.
- [ ] Confirm RED before wiring the parser/Make target.
- [ ] Implement CLI/Make integration and concise command documentation, including the candidate-freeze sequence and explicit Phase 2C stop boundary.
- [ ] Run `uv run pytest tests/test_source_analysis.py -q`, `uv run creative-writer source-analysis --help`, and `make -n source-analysis STORY=time-expedition STAGE=prepare` GREEN.
- [ ] Run `uv run pytest -q` for repository regression coverage.
- [ ] Commit the complete tooling interface.

### Task 8: Lock the Real Corpus and Holdout Partition Before Close Reading

**Files:**
- Modify: `stories/time-expedition/source-study/holdouts.yml` (created by command)
- Modify: `stories/time-expedition/source-study/README.md`
- Modify: `stories/time-expedition/source-study/method.md`
- Generated only: `build/time-expedition/source-study/corpus-lock.json`
- Generated only: `build/time-expedition/source-study/passage-index.jsonl`

- [ ] Run `make source-admission STORY=time-expedition` and confirm the Phase 2A boundary passes unchanged.
- [ ] Run `make source-analysis STORY=time-expedition STAGE=prepare` once to create the real corpus lock, passage index, and tracked holdout manifest.
- [ ] Audit exact witness counts, whole-work holdout identity, within-work holdout counts, tertile coverage, source fingerprints, and absence of Tier 4 development windows.
- [ ] Run the same prepare command again and prove byte-stable tracked `holdouts.yml` plus semantic verification of generated outputs.
- [ ] Review the protocol and partition with a fresh agent before any detailed Wells reading begins; fix blocking defects and rerun.
- [ ] Update phase-state prose to record that the protocol and holdout partition are locked while detailed evidence remains unstarted.
- [ ] Run `git diff --check`, source-admission, prepare, and focused tests.
- [ ] Commit the real holdout manifest separately. This commit must predate every substantive observation, quantitative interpretation, and candidate claim.

### Task 9: Generate and Review the Development Quantitative Profile

**Files:**
- Modify: `stories/time-expedition/source-study/quantitative-profile.yml`
- Generated only: `build/time-expedition/source-study/development-metrics.json`
- Generated only: `build/time-expedition/source-study/development-metrics.csv`
- Generated only: `build/time-expedition/source-study/development-report.md`

- [ ] Set `study_status: development` only after the holdout-lock commit exists.
- [ ] Run `make source-analysis STORY=time-expedition STAGE=develop` to generate development-only per-witness measurements and sampling aids.
- [ ] Audit denominators, source separation, sentence approximation, dialogue classification, extreme flags, and absence of every held-out/control passage ID from outputs.
- [ ] Populate `quantitative-profile.yml` only with reviewed metric IDs, per-witness values, variation, measurement limits, and candidate interpretive relevance; preserve the four short stories as separate witnesses.
- [ ] Have a fresh reviewer challenge false precision, pooled generalisation, unsupported metric interpretation, and source-role confusion.
- [ ] Revise the quantitative profile and rerun `develop` until it validates cleanly.
- [ ] Commit the reviewed quantitative profile and generated-method documentation; keep build outputs ignored.

### Task 10: Author Source-Level Development Observations and Candidate Claims

**Files:**
- Modify: all seven `stories/time-expedition/source-study/observations/*.md` dossiers
- Modify: `stories/time-expedition/source-study/evidence-ledger.yml`

- [ ] Close-read only development passages, using generated metric flags as sampling aids and direct source inspection for representative, extreme, and resistant examples.
- [ ] Populate each applicable dossier with `Passage`, `Observation`, `Inference`, `Jurisdiction`, `Comparison`, `Limitation`, and `Candidate claims`; keep the four selected stories in distinct sections and preserve source-level differences.
- [ ] Cover all ten analytical dimensions across the dossier set without forcing every dimension onto every source.
- [ ] Build a restrained candidate ledger. Every claim must be descriptive, narrowly scoped, resolvable, authority-valid, counterexample-aware, and equipped with a predeclared validation expectation.
- [ ] Run `make source-analysis STORY=time-expedition STAGE=develop` repeatedly; treat every stale locator, holdout/control leak, jurisdiction error, unsupported cross-work claim, or missing limitation as blocking.
- [ ] Dispatch separate fresh reviewers for Tier 1 continuity/frame evidence, Tier 2 fictional evidence, Tier 3 nonfiction evidence, and cross-work claim logic. Reviewers may inspect development passages but not held-out or Tier 4 texts.
- [ ] Resolve all Critical/Important findings, preserve recorded counterexamples, and retain rejected candidate claims rather than deleting analytical history.
- [ ] Commit the reviewed observation dossiers and candidate ledger.

### Task 11: Synthesize and Freeze the Candidate Wells Profile

**Files:**
- Modify: `stories/time-expedition/source-study/wells-profile.md`
- Modify: `stories/time-expedition/source-study/evidence-ledger.yml`
- Modify: `stories/time-expedition/source-study/validation.md`
- Modify: `stories/time-expedition/source-study/analysis.yml`

- [ ] Write `wells-profile.md` by analytical dimension from validated development metrics, dossiers, and ledger claims. Each finding declares claim IDs, classification/confidence, jurisdiction, evidence, variation, quantitative context, uncertainty, and no operational instruction.
- [ ] Run `develop` and audit every profile-to-ledger link, every orphaned non-rejected claim, and every phrase that slips from description into prescription.
- [ ] Obtain an independent candidate-profile review focused on claim discrimination, variation, authority, overgeneralisation, and the Phase 2C boundary.
- [ ] Resolve blocking findings and rerun all development gates.
- [ ] Commit the candidate `wells-profile.md` and `evidence-ledger.yml`; record that commit ID and the exact committed SHA-256 values in `validation.md` in a later commit.
- [ ] Set `study_status: candidate_frozen`, verify the recorded Git objects and hashes, and commit the freeze record separately. Do not amend either commit.

### Task 12: Validate Against Held-Out Wells and Tier 4 Controls

**Files:**
- Modify: `stories/time-expedition/source-study/evidence-ledger.yml`
- Modify: `stories/time-expedition/source-study/wells-profile.md`
- Modify: `stories/time-expedition/source-study/period-controls.md`
- Modify: `stories/time-expedition/source-study/validation.md`
- Modify: `stories/time-expedition/source-study/analysis.yml`
- Generated only: `build/time-expedition/source-study/validation-metrics.json`
- Generated only: `build/time-expedition/source-study/validation-packet.md`
- Generated only: `build/time-expedition/source-study/analysis-report.md`

- [ ] Run candidate-frozen `make source-analysis STORY=time-expedition STAGE=validate` to open and measure held-out Wells passages and quarantined Tier 4 controls.
- [ ] Assess each predeclared expectation against source-wise directions and context, explicitly allowing authentic variation; do not use significance tests or an authorship verdict.
- [ ] Populate `period-controls.md` by Wells claim, with the authorising control role, similarities/differences, cited control passages, corrected classification, and prohibited inference.
- [ ] Give a fresh independent reviewer the frozen candidate profile/ledger, authority policy, generated measurements, and anonymised validation packets where practical. Record review method, findings, uncertainty, and any inability to discriminate.
- [ ] Transition every candidate claim to `validated`, `qualified`, or `rejected`; retain rejected claims and record the reason. Adjust confidence/classification/jurisdiction only where validation evidence supports it.
- [ ] Reconcile the final descriptive profile with claim outcomes, preserving variation and adding control distinctions without writing Phase 2C instructions.
- [ ] Record claim transitions, held-out results, controls, reviewer findings, unresolved uncertainty, and current final profile hash in `validation.md`; set `study_status: validated`.
- [ ] Run final `validate` to compile `analysis-report.md` and block any incomplete transition, stale hash, authority error, or missing control/reviewer treatment.
- [ ] Review the final report for traceability, source separation, descriptive-only language, and explicit stop point.
- [ ] Commit the validated evidence layer.

### Task 13: Complete Repository Verification, Adversarial Review, and Handoff

**Files:**
- Modify if required by review: Phase 2B code, tests, and source-study artifacts only
- Modify: `stories/time-expedition/source-study/README.md`
- Modify: `stories/time-expedition/source-study/method.md`
- Modify: `README.md`

- [ ] Run `uv run pytest -q`.
- [ ] Run `make source-admission STORY=time-expedition`.
- [ ] Run `make source-analysis STORY=time-expedition STAGE=prepare`, then `develop`, then final `validate`.
- [ ] Run `git diff --check`, confirm `git status --short`, and confirm generated `build/` artifacts remain ignored.
- [ ] Search for forbidden scope drift in changed files: style-card edits, linter implementation, Permian planning, manuscript changes, prescriptions, phrase banks, aggregate authenticity scores, and untracked source changes.
- [ ] Dispatch a fresh high-capability whole-change reviewer with the approved design, this plan, complete diff, test reports, and current final analysis report. Require findings ordered by severity and explicit checks of holdout chronology, leakage, authority, evidence traceability, and Phase 2C separation.
- [ ] Dispatch one fix worker for all Critical/Important findings, rerun covering tests and commands, and obtain a clean re-review.
- [ ] Update source-study docs to mark Phase 2B technically complete but awaiting Barry's substantive approval before Phase 2C.
- [ ] Commit final review fixes and documentation without amending prior freeze/holdout chronology.
- [ ] Push `main` to `origin` only after all verification succeeds.

---

## Completion Evidence

Phase 2B is implemented only when all of the following are simultaneously true:

- the approved corpus and every fingerprint still pass Phase 2A admission;
- the tracked holdout manifest predates detailed analysis and verifies byte-for-byte on rerun;
- the passage index resolves every tracked evidence locator;
- development outputs contain neither held-out Wells nor Tier 4 positive evidence;
- deterministic metrics remain per witness and retain documented limits;
- all ten dimensions are represented in source-level observations and descriptive synthesis;
- every material profile finding maps to a valid ledger claim with variation/counterexample treatment;
- the candidate commit and hashes predate validation outputs and claim promotions;
- every candidate claim has a recorded held-out/control/reviewer outcome;
- the final profile remains descriptive and leaves operational guidance and linting to Phase 2C;
- the full test suite and all three real staged commands pass;
- a fresh adversarial reviewer reports no unresolved Critical or Important finding;
- `main` is committed and pushed, while the generated build tree remains ignored.
