# Wells Phase 2C Style Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a thin, evidence-linked Wells style workflow that compiles curated source packets, produces score-free advisory manuscript reports, preserves AI and human judgement, and leaves manuscript prose untouched.

**Architecture:** Add strict story-local style schemas over the approved Phase 2B evidence layer, then resolve them into a provenance-checked `StyleContext`. A small diagnostics engine analyses manuscript text, a report orchestrator separates Wells questions, contextual signals, surface warnings, and generic AI-writing signals, and existing review packs carry selected human calibration cases. `make check` validates configuration and tracked decisions only; explicit `style-reference` and `style-lint` commands generate disposable outputs under `build/`.

**Tech Stack:** Python 3.12, Pydantic 2, PyYAML, pytest, Pandoc-backed Phase 2B passage indexes, GNU Make, Markdown, YAML, JSON, SHA-256.

## Global Constraints

- Treat all manuscript style findings as advisory. Only malformed configuration, stale provenance, invalid references, unreadable inputs, or execution/report failures return non-zero.
- Do not produce a Wells score, authenticity score, authorship verdict, automatic rewrite, automatic role classifier, or automatic profile mutation.
- Keep `make check` separate from manuscript style analysis. It validates a configured profile, packet manifests, chapter metadata, review-pack style metadata, and authenticity reviews.
- Keep `make ai-audit` available and backward-compatible. Generic AI-writing signals remain a separately labelled editorial surface, never positive Wells evidence.
- Consume only Phase 2B claims whose final status is `validated` or `qualified`. Preserve their classification, confidence, jurisdiction, counterexamples, controls, limitations, and prohibited overgeneralisations.
- Tier 4 sources may appear only as negative or comparative controls. They may never become positive examples or Wells prescriptions.
- Use explicit chapter metadata for narrative roles and packet selection. Do not infer roles.
- Compile reference packets from manifest-selected stable passage IDs. Do not add similarity search or automatic source selection.
- Whole-story lint is the default. Chapter selection is optional and writes a distinct report pair.
- Markdown and JSON reports must contain the same findings, use deterministic ordering, and contain no aggregate score.
- The external AI-writing scanner being absent is a visible, non-blocking partial-result state. A present scanner that exits non-zero or emits malformed JSON is an execution error.
- Existing em-dash and contrastive-parallelism warnings remain unchanged in `make check` and also appear in the style report's separate surface-warning section.
- Existing review-pack manifests remain valid. Style calibration metadata is optional.
- Chapter reviews may be accepted by an AI reviewer with rationale. Story and anthology acceptance requires a human reviewer.
- Phase 2C changes no manuscript prose and performs no Permian scientific or historical research.
- Generated files stay below ignored `build/`. Tracked Markdown and YAML remain canonical.
- Use test-driven development for each behavior: write a focused failing test, confirm RED, implement the smallest coherent change, confirm GREEN, then commit.
- Complete one focused end-to-end self-review and repair pass. Stop after the completion criteria pass; calibration against actual Permian prose belongs to the next iteration.

---

## File Map

- `src/creative_writer/style_models.py`: strict profile, packet, report, finding, AI-triage, and authenticity-review schemas.
- `src/creative_writer/style_profiles.py`: profile-path resolution, Phase 2B provenance checks, evidence catalog construction, packet/profile validation, and chapter metadata validation.
- `src/creative_writer/style_references.py`: source-index preparation, packet resolution, bounded context extraction, and Markdown rendering.
- `src/creative_writer/style_diagnostics.py`: transparent manuscript units and deterministic sentence, paragraph, dialogue, locator, repetition, opening, and cadence diagnostics.
- `src/creative_writer/prose_heuristics.py`: shared em-dash and contrastive-parallelism warning logic used by both `check` and `style-lint`.
- `src/creative_writer/style_lint.py`: whole-story/chapter orchestration plus deterministic Markdown/JSON report rendering.
- `src/creative_writer/style_reviews.py`: tracked authenticity-review discovery and validation.
- `src/creative_writer/models.py`: optional contract configuration, chapter roles/packets, and review-pack calibration metadata.
- `src/creative_writer/ai_audit.py`: structured JSON scanner adapter while preserving the existing Markdown command.
- `src/creative_writer/checks.py`: configured-style validation integration only, with no style-analysis execution.
- `src/creative_writer/review_packs.py`: optional style-calibration rendering.
- `src/creative_writer/cli.py`: `style-lint` and `style-reference` command interfaces.
- `Makefile`: thin `style-lint` and `style-reference` targets.
- `tests/test_style_models.py`: strict schema invariants.
- `tests/test_style_profiles.py`: provenance, authority, role, claim, packet, and review validation.
- `tests/test_style_references.py`: packet compilation and context behavior.
- `tests/test_style_diagnostics.py`: hand-countable diagnostics.
- `tests/test_style_lint.py`: report separation, exit behavior, scanner integration, CLI scope, and determinism.
- `tests/test_style_reviews.py`: authenticity-review gates.
- `tests/fixtures/style/`: small authentic-source and synthetic-drift calibration fixtures.
- `stories/time-expedition/style-profile.yml`: Wells profile version `1.0.0`.
- `stories/time-expedition/style-reference-packets/*.yml`: six curated packet manifests.
- `stories/time-expedition/style-reviews/`: review guide and reusable tracked template.
- `stories/time-expedition/style-guide.md`: full evidence-linked operational guidance.
- `stories/time-expedition/style-card.md`: concise drafting-desk guidance.
- `stories/time-expedition/contract.yml`: profile activation.
- `stories/time-expedition/chapter-stubs/01-last-week-of-the-permian.md`: explicit roles and default packets only.
- `README.md`: public commands, artifact roles, exit semantics, and stop boundary.

---

### Task 1: Define the Style Data Contracts

**Files:**
- Create: `src/creative_writer/style_models.py`
- Create: `tests/test_style_models.py`
- Modify: `src/creative_writer/models.py`
- Modify: `tests/test_models.py`

**Interfaces:**
- Consumes: `StrictModel`, `Slug`, `SHA256`, `NonEmptyText`, and `RelativePath` from `creative_writer.source_analysis_models`.
- Produces: `StyleProfile`, `StyleReferencePacket`, `StylePacketEntry`, `StyleLintReport`, `StyleFinding`, `StylePracticeQuestion`, `StyleDiagnosticRecord`, `StyleLintSettings`, optional `ChapterFrontMatter.style_roles`, optional `ChapterFrontMatter.style_packets`, and optional `ReviewPackEntry.style`.

The contract additions in `models.py` are:

```python
class StyleLintSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: NonEmptyStr
    generic_ai_audit: bool = True

    @field_validator("profile")
    @classmethod
    def validate_profile(cls, value: str) -> str:
        if not _is_canonical_relative_posix_path(value) or not value.endswith((".yml", ".yaml")):
            raise ValueError("style-lint profile must be a story-relative YAML path")
        return value


class ReviewPackStyleContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_ids: list[Slug] = Field(default_factory=list)
    profile_id: Slug
    profile_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    claim_ids: list[Slug] = Field(default_factory=list)
    narrative_role: Slug
    ai_disposition: Literal["dismiss", "revise", "monitor", "escalate"]
    ai_rationale: NonEmptyStr
    decision_impact: NonEmptyStr
```

`ContractConfig` gains `style_lint: StyleLintSettings | None = None`.
`ChapterFrontMatter` gains `style_roles: list[str]` and
`style_packets: list[str]`, both defaulting to empty lists and using the
existing non-empty-string list validator. `ReviewPackEntry` gains
`style: ReviewPackStyleContext | None = None`.

The strict style schema uses these exact value sets:

```python
StyleRuleFamily = Literal["practice", "diagnostic", "anti_drift"]
StyleAdvisoryLevel = Literal["notice", "review"]
StyleScope = Literal["passage", "chapter", "story"]
StyleEvaluationMode = Literal["manual_question", "locator", "contextual_diagnostic"]
StyleSignalKind = Literal[
    "lexicon_locator",
    "sentence_profile",
    "dialogue_profile",
    "repeated_ngram",
    "paragraph_opening",
]
StylePacketEntryKind = Literal[
    "positive_example",
    "authentic_variation",
    "counterexample",
    "negative_control",
]
StyleFindingCategory = Literal[
    "wells_practice",
    "contextual_diagnostic",
    "anti_drift",
    "surface_warning",
    "generic_ai",
]
StyleReviewScope = Literal["chapter", "story", "anthology"]
StyleReviewOutcome = Literal["accepted", "qualified", "revise"]
StyleReviewerRole = Literal["ai", "human"]
```

`StyleProfile` has exactly these top-level fields:

```python
class StyleProfile(StrictModel):
    schema_version: Literal[1]
    profile_id: Slug
    version: str
    title: NonEmptyText
    provenance: StyleProvenance
    eligible_claim_statuses: list[Literal["validated", "qualified"]]
    default_packet_ids: list[Slug]
    change_basis: NonEmptyText
    profile_review_refs: list[NonEmptyText]
    roles: list[StyleNarrativeRole]
    rules: list[StyleRule]
```

`StyleProvenance` contains `study_id`, `analysis`, `source_registry`,
`holdout_manifest`, `evidence_ledger`, `validation_record`, three named
`passage_indexes`, and `approved_review_run_id`. Every artifact record
contains a canonical repository-relative path and SHA-256. The index names
are exactly `development`, `heldout_wells`, and `tier4_controls`.

`StyleNarrativeRole` contains `id`, `label`, `description`, and one or more
`phase_2b_roles`. `StyleRule` contains `id`, `name`, `family`, `advisory`,
`claim_ids`, `roles`, `scope`, `evaluation_mode`, `review_question`, optional
`signal`, optional `tolerance`, `source_passage_ids`,
`variation_passage_ids`, `control_passage_ids`, `packet_ids`, and
`interpretation_limits`.

`StyleSignal` is a discriminated union keyed by `kind`:

```python
class LexiconLocatorSignal(StrictModel):
    kind: Literal["lexicon_locator"]
    terms: list[NonEmptyText] = Field(min_length=1)
    max_examples: StrictInt = Field(default=8, ge=1, le=20)


class SentenceProfileSignal(StrictModel):
    kind: Literal["sentence_profile"]
    speech_attribution_verbs: list[NonEmptyText] = Field(min_length=1)
    minimum_sentences: StrictInt = Field(default=12, ge=1)


class DialogueProfileSignal(StrictModel):
    kind: Literal["dialogue_profile"]
    minimum_words: StrictInt = Field(default=200, ge=1)


class RepeatedNgramSignal(StrictModel):
    kind: Literal["repeated_ngram"]
    ngram_size: StrictInt = Field(default=3, ge=3, le=6)
    minimum_occurrences: StrictInt = Field(default=3, ge=2)
    minimum_words: StrictInt = Field(default=300, ge=1)
    stop_words: list[NonEmptyText] = Field(default_factory=list)


class ParagraphOpeningSignal(StrictModel):
    kind: Literal["paragraph_opening"]
    prefix_words: StrictInt = Field(default=3, ge=1, le=6)
    minimum_occurrences: StrictInt = Field(default=3, ge=2)
    minimum_paragraphs: StrictInt = Field(default=8, ge=2)
```

`StyleTolerance` contains `metric`, `minimum_sample_size`, optional
`review_below`, optional `review_above`, `reference_witness_ids`, and
`rationale`; at least one numeric bound is required. Supported metrics are
`sentence_length_median`, `sentence_length_p90`,
`sentence_length_cv`, `paragraph_length_median`, and
`dialogue_proportion`.

`StyleReferencePacket` contains `schema_version`, `id`, `title`, `purpose`,
`profile_id`, `profile_version`, `roles`, `claim_ids`, `context_radius`,
ordered `entries`, `prohibited_uses`, and `anti_copying_guidance`. Each entry
contains `id`, `passage_id`, `kind`, `claim_ids`, `authority_tier`,
`permitted_use`, `selection_note`, and an optional context-radius override.

`StyleLintReport` and `StyleFinding` preserve all fields required by the
approved report contract. A finding contains `id`, `category`,
`manuscript`, `line_start`, `line_end`, `observed_signal`, `rule_id`,
`rule_family`, `advisory`, `roles`, `scope`, `claim_ids`,
`claim_jurisdictions`, `source_passage_ids`, `editorial_question`, and
`limitations`. The report contains profile provenance, scope, chapter
inventory, role caveats, findings, practice questions, diagnostics, generic
AI status, limitations, and next steps; it has no score field.
The generic AI section uses status `complete`, `unavailable`, or `disabled`;
only `unavailable` makes the otherwise successful report partial.

Use these report support models:

```python
class StyleFinding(StrictModel):
    id: Slug
    category: StyleFindingCategory
    manuscript: RelativePath
    line_start: StrictInt = Field(ge=1)
    line_end: StrictInt = Field(ge=1)
    observed_signal: NonEmptyText
    rule_id: NonEmptyText
    rule_family: StyleRuleFamily | None
    advisory: StyleAdvisoryLevel
    roles: list[Slug]
    scope: StyleScope
    claim_ids: list[Slug]
    claim_jurisdictions: list[ClaimJurisdiction]
    source_passage_ids: list[NonEmptyText]
    editorial_question: NonEmptyText
    limitations: NonEmptyText


class StyleChapterInventory(StrictModel):
    stub: RelativePath
    manuscript: RelativePath
    title: NonEmptyText
    summary: NonEmptyText
    roles: list[Slug]
    packet_ids: list[Slug]
    word_count: StrictInt = Field(ge=0)


class StylePracticeQuestion(StrictModel):
    rule_id: Slug
    advisory: StyleAdvisoryLevel
    roles: list[Slug]
    claim_ids: list[Slug]
    question: NonEmptyText
    source_passage_ids: list[NonEmptyText]
    interpretation_limits: NonEmptyText


class StyleDiagnosticRecord(StrictModel):
    rule_id: Slug
    manuscript: RelativePath
    roles: list[Slug]
    measurements: dict[NonEmptyText, StrictInt | StrictFloat | NonEmptyText | None]
    sample_size: StrictInt = Field(ge=0)
    tolerance_note: NonEmptyText
    triggered: StrictBool
    limitations: NonEmptyText


class GenericAIReportSection(StrictModel):
    status: Literal["complete", "unavailable", "disabled"]
    scanner: NonEmptyText | None
    group_names: list[NonEmptyText]
    finding_ids: list[Slug]
    caution: NonEmptyText
    notice: NonEmptyText | None


class StyleLintReport(StrictModel):
    schema_version: Literal[1]
    story_slug: Slug
    story_title: NonEmptyText
    scope: Literal["story", "chapter"]
    chapter_selector: NonEmptyText | None
    profile_id: Slug
    profile_version: str
    profile_sha256: SHA256
    evidence_ledger_sha256: SHA256
    validation_record_sha256: SHA256
    packet_manifest_sha256s: dict[Slug, SHA256]
    chapters: list[StyleChapterInventory] = Field(min_length=1)
    role_caveat: NonEmptyText
    findings: list[StyleFinding]
    practice_questions: list[StylePracticeQuestion]
    diagnostics: list[StyleDiagnosticRecord]
    generic_ai: GenericAIReportSection
    limitations: list[NonEmptyText] = Field(min_length=1)
    next_steps: list[NonEmptyText] = Field(min_length=1)
    partial: StrictBool
```

- [ ] **Step 1: Write strict schema tests**

Add tests that parse one complete valid profile and packet, then reject:
unknown schema versions, duplicate role/rule/entry IDs, unknown enums,
malformed semantic versions, malformed hashes, empty required text,
duplicate list members, a manual rule with a signal, a locator without a
signal, a tolerance without either bound, and a Tier 4 packet entry not
labelled `negative_control`.

```python
def test_style_profile_rejects_duplicate_rule_ids() -> None:
    payload = valid_style_profile_payload()
    payload["rules"].append(payload["rules"][0])
    with pytest.raises(ValidationError, match="rule IDs must be unique"):
        StyleProfile.model_validate(payload)


def test_reference_packet_rejects_positive_tier_four_entry() -> None:
    payload = valid_reference_packet_payload()
    payload["entries"][0]["authority_tier"] = 4
    with pytest.raises(ValidationError, match="Tier 4"):
        StyleReferencePacket.model_validate(payload)
```

Add model regression tests proving an old contract, chapter stub, and
review-pack manifest still parse, plus focused tests for the three new
optional fields.

- [ ] **Step 2: Run the schema tests and confirm RED**

Run:

```bash
uv run pytest tests/test_style_models.py tests/test_models.py -q
```

Expected: collection fails because `creative_writer.style_models` and the
new optional models/fields do not exist.

- [ ] **Step 3: Implement the strict models and validators**

Create the types above with `extra="forbid"` and deterministic uniqueness
validators. Enforce:

```python
if self.evaluation_mode == "manual_question" and self.signal is not None:
    raise ValueError("manual questions cannot declare a signal")
if self.evaluation_mode != "manual_question" and self.signal is None:
    raise ValueError("locator and contextual rules require a signal")
if self.family == "practice" and not self.claim_ids:
    raise ValueError("practice rules require at least one Phase 2B claim")
if self.family != "anti_drift" and self.control_passage_ids:
    raise ValueError("Tier 4 controls belong only to anti-drift rules")
```

Validate all semantic-version fields with
`r"^\d+\.\d+\.\d+$"`, canonical relative paths with
`validate_relative_path`, and every ID list for uniqueness.

- [ ] **Step 4: Run the schema tests and confirm GREEN**

Run:

```bash
uv run pytest tests/test_style_models.py tests/test_models.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit the schema foundation**

```bash
git add src/creative_writer/style_models.py src/creative_writer/models.py tests/test_style_models.py tests/test_models.py
git commit -m "Add style workflow schemas"
```

---

### Task 2: Resolve Profiles Against the Approved Phase 2B Evidence

**Files:**
- Create: `src/creative_writer/style_profiles.py`
- Create: `tests/test_style_profiles.py`

**Interfaces:**
- Consumes: `StyleProfile`, `StyleReferencePacket`, `EvidenceLedger`,
  `ValidationRecord`, `AnalysisConfig`, `HoldoutManifest`, `SourcesRegistry`,
  `ChapterDocument`, `load_yaml_model`, `load_validation_document`,
  `safe_relative_path`, and `sha256_file`.
- Produces:

```python
@dataclass(frozen=True, slots=True)
class EvidencePassage:
    passage_id: str
    witness_id: str
    source_id: str
    selection_id: str | None
    authority_tier: int
    claim_ids: tuple[str, ...]
    evidence_kinds: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResolvedStyleRule:
    rule: StyleRule
    claims: tuple[EvidenceClaim, ...]


@dataclass(frozen=True, slots=True)
class StyleContext:
    story_dir: Path
    profile_path: Path
    profile: StyleProfile
    analysis: AnalysisConfig
    ledger: EvidenceLedger
    validation: ValidationRecord
    sources: SourcesRegistry
    evidence_catalog: dict[str, EvidencePassage]
    rules: tuple[ResolvedStyleRule, ...]
    packets: dict[str, StyleReferencePacket]
```

Functions:

```text
resolve_style_profile_path(story_dir: Path, configured_path: str | None, override: str | None) -> Path
load_style_context(root: Path, story_dir: Path, profile_path: Path) -> StyleContext
validate_chapter_style_metadata(context: StyleContext, chapters: Sequence[ChapterDocument]) -> list[str]
```

Profile overrides resolve relative to the story directory unless absolute.
The configured contract path must remain story-relative. The loader compares
the actual SHA-256 of every tracked provenance artifact to the profile,
requires matching study IDs, a validated ledger, a complete validated
validation record, and the named `whole_study_audit` review run with
`outcome: approved`.

The evidence catalog is built only from:

- ledger supporting and counterexample references;
- validation held-out claim results;
- validation Tier 4 control comparisons.

It records the claim relationship and authority tier for each passage. It
does not treat every passage in the corpus as approved style evidence.

- [ ] **Step 1: Write profile-resolution and provenance tests**

Use a compact story fixture with one validated claim, one held-out result,
one Tier 4 control, and one approved whole-study review. Add tests for:

```python
def test_profile_loads_and_inherits_claim_state(style_story: Path) -> None:
    context = load_style_context(style_story.parent.parent, style_story, style_story / "style-profile.yml")
    resolved = context.rules[0]
    assert resolved.claims[0].status == "validated"
    assert resolved.claims[0].confidence == "moderate"


def test_profile_rejects_stale_ledger_hash(style_story: Path) -> None:
    path = style_story / "source-study" / "evidence-ledger.yml"
    path.write_text(path.read_text() + "\n", encoding="utf-8")
    with pytest.raises(CreativeWriterError, match="evidence-ledger.*SHA-256"):
        load_style_context(style_story.parent.parent, style_story, style_story / "style-profile.yml")
```

Also reject a missing/rejected claim, a qualified claim when only validated
is eligible, mismatched claim jurisdiction, a role whose `phase_2b_roles`
does not intersect its claim's jurisdiction, Tier 4 positive evidence,
Tier 1-3 material declared as a negative control, an unknown packet ID,
an unapproved whole-study review, a changed source tier, and a path escaping
the story or repository root.

- [ ] **Step 2: Run the profile tests and confirm RED**

Run:

```bash
uv run pytest tests/test_style_profiles.py -q
```

Expected: collection fails because `creative_writer.style_profiles` does not
exist.

- [ ] **Step 3: Implement profile loading and evidence-catalog construction**

Implement profile resolution without importing `style_lint` or `checks`.
Hydrate claims from the ledger rather than duplicating claim state in
`style-profile.yml`.

Use this authority logic:

```python
for rule in profile.rules:
    claims = tuple(claims_by_id[claim_id] for claim_id in rule.claim_ids)
    for claim in claims:
        if claim.status not in profile.eligible_claim_statuses:
            raise CreativeWriterError(f"Rule {rule.id} uses ineligible claim {claim.id}")
        for role_id in rule.roles:
            role = roles_by_id[role_id]
            if not set(role.phase_2b_roles).intersection(claim.jurisdiction.roles):
                raise CreativeWriterError(
                    f"Rule {rule.id} broadens {claim.id} beyond its declared role jurisdiction"
                )
```

Resolve source IDs and tiers through `SourcesRegistry`, including selected
short-fiction witness IDs of the form `<source-id>/<selection-id>`. Require
packet entry claim IDs to be subsets of the packet claim IDs and profile
claims. Require each packet passage to occur in the evidence catalog for at
least one declared claim.

- [ ] **Step 4: Implement chapter role and packet validation**

Return one clear error string per unknown role or packet, preserving chapter
stub paths at the caller. Mixed-role chapters pass and receive this fixed
report caveat:

```text
Chapter-level role assignment is coarse and does not classify every paragraph.
```

- [ ] **Step 5: Run focused and source-schema regression tests**

Run:

```bash
uv run pytest tests/test_style_profiles.py tests/test_source_analysis_models.py tests/test_source_models.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit the provenance resolver**

```bash
git add src/creative_writer/style_profiles.py tests/test_style_profiles.py
git commit -m "Validate style profiles against source evidence"
```

---

### Task 3: Compile Curated Style Reference Packets

**Files:**
- Create: `src/creative_writer/style_references.py`
- Create: `tests/test_style_references.py`

**Interfaces:**
- Consumes: `StyleContext`, `read_passage_index`, `context_window`,
  `run_source_analysis(root, slug, "prepare")`, and the three provenance
  index paths/hashes.
- Produces:

```python
@dataclass(slots=True)
class ResolvedStylePacketEntry:
    manifest_entry: StylePacketEntry
    focal: PassageRecord
    context: list[PassageRecord]
    source_title: str
    witness_id: str
    authority_tier: int


@dataclass(slots=True)
class StyleReferenceResult:
    story_slug: str
    profile_id: str
    profile_version: str
    pack_name: str
    manifest_path: Path
    output_path: Path
    entry_count: int
    source_indexes_prepared: bool
```

Functions:

```text
style_reference_manifest_paths(story_dir: Path) -> list[Path]
generate_style_reference(root: Path, slug: str, pack: str, profile_override: str | None = None) -> StyleReferenceResult
```

If any required passage index is absent, `generate_style_reference` runs
`run_source_analysis(root, slug, "prepare")` once, then reads all three
indexes. Existing indexes are not regenerated. Every loaded index must match
the SHA-256 recorded by the profile. A present but stale index blocks rather
than being silently replaced.

The renderer preserves manifest order and emits:

1. profile and Phase 2B provenance;
2. packet purpose and intended roles;
3. eligible claims with final status/classification/confidence and limits;
4. positive examples and authentic variation;
5. a separately labelled negative-control section;
6. source title, witness, tier, stable passage ID, heading path, and bounded
   context for every entry;
7. selection rationale and permitted use;
8. prohibited uses and anti-copying guidance.

- [ ] **Step 1: Write packet-compilation tests**

Create three tiny canonical JSONL indexes containing positive, held-out, and
control passages. Test exact manifest order, radius `0`, radius `1` bounded
by heading, unknown passage failure, stale index hash failure, Tier 4
segregation, and output metadata.

```python
def test_style_reference_compiles_manifest_order_and_negative_section(style_packet_story: Path) -> None:
    result = generate_style_reference(style_packet_story.parent.parent, "packet-story", "frame")
    body = result.output_path.read_text(encoding="utf-8")
    assert body.index("Positive example") < body.index("Authentic variation")
    assert "## Negative comparisons" in body
    assert "never a positive Wells model" in body
```

Monkeypatch `run_source_analysis` and prove it is called exactly once when
indexes are missing and not called when all verified indexes exist.

- [ ] **Step 2: Run packet tests and confirm RED**

Run:

```bash
uv run pytest tests/test_style_references.py -q
```

Expected: collection fails because `creative_writer.style_references` does
not exist.

- [ ] **Step 3: Implement index preparation and packet resolution**

Resolve pack names with or without `.yml`; reject empty names, absolute
paths, and path traversal. Merge index records by passage ID and reject
duplicates across partitions. Use the manifest entry's radius when present,
otherwise the packet radius.

```python
radius = entry.context_radius
if radius is None:
    radius = manifest.context_radius
resolved_context = context_window(indexes[partition], entry.passage_id, radius)
```

Do not normalize or paraphrase source excerpts. Render `original_text`
verbatim inside fenced `text` blocks.

- [ ] **Step 4: Run packet and passage-index tests**

Run:

```bash
uv run pytest tests/test_style_references.py tests/test_source_passages.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit the reference compiler**

```bash
git add src/creative_writer/style_references.py tests/test_style_references.py
git commit -m "Compile evidence-linked style reference packets"
```

---

### Task 4: Build Transparent Manuscript Diagnostics and Shared Surface Heuristics

**Files:**
- Create: `src/creative_writer/style_diagnostics.py`
- Create: `src/creative_writer/prose_heuristics.py`
- Create: `tests/test_style_diagnostics.py`
- Modify: `src/creative_writer/checks.py`
- Modify: `tests/test_checks.py`

**Interfaces:**
- Consumes: `sentence_spans` and `tokenize` from
  `creative_writer.source_metrics`, plus existing contract lint thresholds.
- Produces:

```python
@dataclass(frozen=True, slots=True)
class TextLocation:
    line_start: int
    line_end: int


@dataclass(frozen=True, slots=True)
class LocatedSignal:
    location: TextLocation
    observed: str


@dataclass(slots=True)
class ManuscriptDiagnostics:
    word_count: int
    paragraph_count: int
    sentence_count: int
    sentence_lengths: list[int]
    paragraph_lengths: list[int]
    sentence_length_cv: float | None
    dialogue_word_proportion: float | None
    punctuation_counts: dict[str, int]
    lexicon_hits: dict[str, list[LocatedSignal]]
    repeated_ngrams: list[LocatedSignal]
    repeated_openings: list[LocatedSignal]


@dataclass(frozen=True, slots=True)
class SurfaceHeuristicWarning:
    rule_id: Literal["em-dash-overuse", "contrastive-parallelism"]
    observed: str
    line_start: int
    line_end: int
```

Functions:

```text
analyse_manuscript(text: str, *, lexicons: Mapping[str, Sequence[str]], speech_attribution_verbs: Sequence[str], stop_words: Sequence[str] = (), repeated_ngram_size: int = 3, repeated_ngram_minimum: int = 3, opening_prefix_words: int = 3, opening_minimum: int = 3) -> ManuscriptDiagnostics
run_surface_heuristics(text: str, lint: LintSettings) -> list[SurfaceHeuristicWarning]
```

HTML comments, fenced code blocks, headings, and image-only lines are excluded
from prose measurements while preserving source line numbers. Dialogue
proportion remains a transparent approximation: count words between matched
curly or straight double quotes and divide by analysed words. The report must
state that nested quotations and attribution boundaries are imperfect.

- [ ] **Step 1: Write hand-countable diagnostic tests**

Cover:

- paragraph and sentence counts;
- median, p90, and coefficient of variation inputs;
- straight and curly quoted dialogue;
- epistemic locators with exact line numbers;
- repeated three-word sequences at three occurrences;
- repeated three-word paragraph openings at three occurrences;
- HTML comments and headings excluded without shifting line locations;
- em-dash and contrastive warnings with exact configured thresholds.

```python
def test_repeated_ngram_reports_first_and_last_lines() -> None:
    text = "The lamp went out.\\n\\nThe lamp went out again.\\n\\nThe lamp went out at dawn.\\n"
    result = analyse_manuscript(
        text,
        lexicons={},
        speech_attribution_verbs=["said"],
        repeated_ngram_size=3,
        repeated_ngram_minimum=3,
    )
    assert result.repeated_ngrams[0].location == TextLocation(1, 5)
    assert "the lamp went" in result.repeated_ngrams[0].observed
```

- [ ] **Step 2: Run diagnostic tests and confirm RED**

Run:

```bash
uv run pytest tests/test_style_diagnostics.py tests/test_checks.py -q
```

Expected: the new modules are missing and the existing check path has not
been refactored.

- [ ] **Step 3: Implement diagnostics without external NLP dependencies**

Use the existing Victorian-aware sentence approximation. Compute coefficient
of variation only when at least two non-empty sentence lengths exist:

```python
mean = statistics.fmean(lengths)
cv = statistics.pstdev(lengths) / mean if len(lengths) >= 2 and mean else None
```

Normalize repetition matching with Unicode NFC, case-folding, and lexical
tokens; do not stem words or substitute synonyms. Ignore n-grams composed
only of the caller-supplied stop-list. The Wells profile supplies exactly
`the, a, an, and, but, if, in, of, on, to`; the engine itself contains no
Wells lexicon.

- [ ] **Step 4: Move existing prose heuristics behind the shared function**

Replace the duplicated counting block in `check_story` with
`run_surface_heuristics`. Preserve the current warning text:

```text
Em dash count <n> exceeds configured limit <limit>.
Contrastive parallelism count <n> exceeds configured limit <limit>.
```

The shared result also retains line locations for `style-lint`.

- [ ] **Step 5: Run diagnostic and check regressions**

Run:

```bash
uv run pytest tests/test_style_diagnostics.py tests/test_checks.py -q
```

Expected: all tests pass and existing check warnings are byte-for-byte
compatible.

- [ ] **Step 6: Commit the diagnostic layer**

```bash
git add src/creative_writer/style_diagnostics.py src/creative_writer/prose_heuristics.py src/creative_writer/checks.py tests/test_style_diagnostics.py tests/test_checks.py
git commit -m "Add transparent manuscript style diagnostics"
```

---

### Task 5: Generate Separated, Score-Free Style-Lint Reports

**Files:**
- Create: `src/creative_writer/style_lint.py`
- Create: `tests/test_style_lint.py`
- Modify: `src/creative_writer/ai_audit.py`
- Modify: `tests/test_ai_audit.py`

**Interfaces:**
- Consumes: `check_story`, `StyleContext`, `analyse_manuscript`,
  `run_surface_heuristics`, and the external scanner's `--json` mode.
- Produces:

```python
class AIWritingHit(BaseModel):
    model_config = ConfigDict(extra="allow")

    group: str
    severity: int
    line: int = Field(ge=1)
    match: str
    context: str


class AIWritingGroup(BaseModel):
    model_config = ConfigDict(extra="allow")

    count: int = Field(ge=0)
    severity: int = Field(ge=0)
    advice: str
    hits: list[AIWritingHit] = Field(default_factory=list)


@dataclass(slots=True)
class AIWritingJSONResult:
    status: Literal["complete", "unavailable"]
    script_path: Path | None
    groups: dict[str, AIWritingGroup]
    caution: str
    notice: str | None
```

```python
@dataclass(slots=True)
class StyleLintResult:
    story_slug: str
    scope: Literal["story", "chapter"]
    profile_id: str
    profile_version: str
    markdown_path: Path
    json_path: Path
    finding_count: int
    partial: bool


@dataclass(slots=True)
class StyleRuleEvaluation:
    questions: list[StylePracticeQuestion]
    diagnostics: list[StyleDiagnosticRecord]
    findings: list[StyleFinding]
```

Functions:

```text
scan_ai_writing_json(path: Path, genre: str = "narrative", *, unavailable_is_error: bool = True) -> AIWritingJSONResult
evaluate_style_rules(context: StyleContext, diagnostics: ManuscriptDiagnostics, *, roles: Sequence[str], manuscript: str) -> StyleRuleEvaluation
generate_style_lint(root: Path, slug: str, *, profile_override: str | None = None, chapter_selector: str | None = None) -> StyleLintResult
```

Chapter selectors match exactly one of: configured stub path, stub filename,
stub stem, manuscript path, manuscript filename, or manuscript stem.
Ambiguous or unmatched selectors raise `CreativeWriterError`.

Whole-story output is:

```text
build/<slug>/style/lint-report.md
build/<slug>/style/lint-report.json
```

Chapter output is:

```text
build/<slug>/style/chapters/<stub-stem>-lint-report.md
build/<slug>/style/chapters/<stub-stem>-lint-report.json
```

Manual practice and anti-drift rules become review questions, not failures.
Locator rules create notice-level findings only when the located signal is
present. Contextual diagnostics always report their measurements; they create
a finding only when an explicit tolerance or repetition/opening threshold is
crossed.

Findings are sorted by category rank, story chapter order, line, and rule ID,
then assigned `finding-001`, `finding-002`, and so forth. Markdown and JSON
are rendered from the same `StyleLintReport` object. JSON uses
`json.dumps(report.model_dump(mode="json"), ensure_ascii=False,
sort_keys=True, indent=2)`.

- [ ] **Step 1: Add a structured scanner-adapter test**

Create a fake executable Python scanner that returns:

```json
{
  "risk": "moderate surface risk",
  "reasons": ["two groups"],
  "genre": "narrative",
  "metrics": {"words": 20},
  "groups": {
    "AI vocabulary": {
      "count": 1,
      "severity": 2,
      "advice": "Replace the stock abstraction with concrete observation.",
      "hits": [
        {"group": "AI vocabulary", "severity": 2, "line": 3, "match": "shaped", "context": "answer-shaped"}
      ]
    }
  },
  "caution": "Surface scan only; not proof of AI authorship."
}
```

Assert the adapter invokes `--genre narrative --json`, preserves group
identity/advice/hits, omits the scanner's aggregate risk from the returned
style-report data, returns `unavailable` only when the script is absent and
`unavailable_is_error=False`, and raises on non-zero or malformed JSON.
Keep the existing Markdown audit test unchanged and passing.

- [ ] **Step 2: Write style-lint report tests**

Create a two-chapter synthetic story/profile with one manual practice rule,
one epistemic locator, one low-CV sentence tolerance, one repeated-ngram
rule, and enabled surface/generic checks. Assert:

```python
def test_style_lint_writes_matching_score_free_reports(style_lint_story: Path) -> None:
    result = generate_style_lint(style_lint_story.parent.parent, "lint-story")
    payload = json.loads(result.json_path.read_text(encoding="utf-8"))
    markdown = result.markdown_path.read_text(encoding="utf-8")
    assert "score" not in json.dumps(payload).lower()
    assert "## Evidence-backed practice questions" in markdown
    assert "## Contextual diagnostics" in markdown
    assert "## Surface warnings" in markdown
    assert "## Generic AI-writing signals" in markdown
    assert payload["findings"][0]["id"] == "finding-001"
```

Add tests for whole-story output, each accepted chapter-selector form,
ambiguous selection, a distinct chapter output path, findings returning
success, malformed profile failure, generic scanner partial status,
`generic_ai_audit: false` skipping scanner invocation with status `disabled`,
stable bytes across two identical runs, mixed-role caveat, story-level
repetition, and no score/authorship language.

- [ ] **Step 3: Run adapter and lint tests and confirm RED**

Run:

```bash
uv run pytest tests/test_ai_audit.py tests/test_style_lint.py -q
```

Expected: structured scanner and style-lint interfaces do not exist.

- [ ] **Step 4: Implement the structured scanner adapter**

Keep `generate_ai_writing_audit` on its existing Markdown scanner path.
Add a separate JSON invocation:

```python
command = [
    sys.executable,
    str(script_path),
    "--genre",
    genre,
    "--json",
    str(path),
]
```

Validate the minimum external shape with permissive `extra="allow"` Pydantic
models so additive scanner fields do not break the repository. Do not copy
`risk` or `reasons` into `StyleLintReport`.

- [ ] **Step 5: Implement rule evaluation and report rendering**

For each selected chapter:

1. analyse prose once;
2. render all applicable manual questions;
3. evaluate profile locator/contextual rules;
4. convert shared surface warnings into `surface_warning` findings;
5. convert each generic scanner hit into a `generic_ai` finding;
6. retain source passage IDs, claim state/jurisdiction, questions, and limits;
7. assemble story-level repetition/uniformity findings after chapter analysis.

Use profile order for questions and deterministic finding order for IDs.
Generic AI findings use rule IDs of the form
`ai-audit-<slugified-group-name>`. They carry no Phase 2B claims or source
examples.

- [ ] **Step 6: Run lint tests and focused regressions**

Run:

```bash
uv run pytest tests/test_ai_audit.py tests/test_style_lint.py tests/test_style_diagnostics.py tests/test_checks.py -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit the report engine**

```bash
git add src/creative_writer/style_lint.py src/creative_writer/ai_audit.py tests/test_style_lint.py tests/test_ai_audit.py
git commit -m "Generate evidence-linked style lint reports"
```

---

### Task 6: Validate Configured Style Artifacts and Wire Public Commands

**Files:**
- Modify: `src/creative_writer/checks.py`
- Modify: `src/creative_writer/cli.py`
- Modify: `Makefile`
- Modify: `README.md`
- Modify: `tests/test_checks.py`
- Modify: `tests/test_style_lint.py`
- Modify: `tests/test_style_references.py`
- Modify: `tests/test_review_packs.py`

**Interfaces:**
- Consumes: `ContractConfig.style_lint`, `load_style_context`,
  `validate_chapter_style_metadata`, `generate_style_lint`, and
  `generate_style_reference`.
- Produces:

```text
creative-writer style-lint --story <slug> [--profile <path>] [--chapter <chapter>]
creative-writer style-reference --story <slug> --pack <name> [--profile <path>]
make style-lint STORY=<slug> [PROFILE=<path>] [CHAPTER=<chapter>]
make style-reference STORY=<slug> PACK=<name> [PROFILE=<path>]
```

If a story has no `contract.yml` style profile, `make check` keeps current
behavior. `style-lint` and `style-reference` require either a configured
profile or `--profile`. `make check` loads and validates all real
`style-reference-packets/*.yml`, excluding `README.md` and `_template.yml`,
but does not read manuscript prose for style signals or invoke the external
scanner.

- [ ] **Step 1: Add check-integration tests**

Add tests proving:

- no configured style profile preserves existing behavior;
- a configured valid profile passes;
- a missing profile, stale provenance, unknown chapter role, unknown chapter
  packet, and broken packet manifest each create a blocking error;
- `check` never calls `generate_style_lint` or `scan_ai_writing_json`;
- mixed roles pass and do not become warnings.

```python
def test_check_does_not_execute_style_analysis(configured_style_story: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "creative_writer.style_lint.generate_style_lint",
        lambda *args, **kwargs: pytest.fail("style lint must remain explicit"),
    )
    assert check_story(configured_style_story.parent.parent, "configured-style").ok
```

- [ ] **Step 2: Add parser and Make-interface tests**

Test `build_parser()` for both new commands and all optional arguments.
Use `make -n` assertions for absent and present `PROFILE`/`CHAPTER` variables.
The expected expanded commands are:

```text
uv run creative-writer style-lint --story "time-expedition"
uv run creative-writer style-lint --story "time-expedition" --profile "style-profile.yml" --chapter "01-last-week-of-the-permian"
uv run creative-writer style-reference --story "time-expedition" --pack "frame-and-testimony" --profile "style-profile.yml"
```

- [ ] **Step 3: Run command/check tests and confirm RED**

Run:

```bash
uv run pytest tests/test_checks.py tests/test_style_lint.py tests/test_style_references.py -q
```

Expected: check integration and command parser assertions fail.

- [ ] **Step 4: Integrate style validation into `check_story`**

After chapters and review packs are loaded, resolve the configured profile
once. Catch `CreativeWriterError` and add a blocking check message at the
profile or manifest path. Validate chapter role/packet IDs and all packet
manifests. Do not require generated passage indexes during `check`; profile
and packet focal references are validated against the tracked evidence
catalog.

- [ ] **Step 5: Add CLI and Make targets**

Add optional argument variables without emitting empty flags:

```make
STYLE_PROFILE_ARG :=
ifneq ($(strip $(PROFILE)),)
STYLE_PROFILE_ARG := --profile "$(PROFILE)"
endif

STYLE_CHAPTER_ARG :=
ifneq ($(strip $(CHAPTER)),)
STYLE_CHAPTER_ARG := --chapter "$(CHAPTER)"
endif

style-lint:
	uv run creative-writer style-lint --story "$(STORY)" $(STYLE_PROFILE_ARG) $(STYLE_CHAPTER_ARG)

style-reference:
	uv run creative-writer style-reference --story "$(STORY)" --pack "$(PACK)" $(STYLE_PROFILE_ARG)
```

CLI success messages report both generated paths for lint, and packet output,
entry count, and whether indexes were prepared for reference compilation.
All `CreativeWriterError` failures use the existing non-zero path.

- [ ] **Step 6: Document the public workflow**

Update `README.md` with:

- optional `contract.yml` configuration;
- both CLI and Make forms;
- whole-story versus chapter output paths;
- the six separated report surfaces;
- advisory versus blocking semantics;
- the missing-scanner partial state;
- reference packet provenance and anti-copying boundary;
- the explicit statement that `make check` validates but does not run
  manuscript style analysis.

- [ ] **Step 7: Run focused command and regression tests**

Run:

```bash
uv run pytest tests/test_checks.py tests/test_style_lint.py tests/test_style_references.py tests/test_ai_audit.py -q
uv run creative-writer style-lint --help
uv run creative-writer style-reference --help
make -n style-lint STORY=time-expedition PROFILE=style-profile.yml CHAPTER=01-last-week-of-the-permian
make -n style-reference STORY=time-expedition PACK=frame-and-testimony PROFILE=style-profile.yml
```

Expected: tests pass, both help commands exit `0`, and Make prints the exact
expected commands.

- [ ] **Step 8: Commit the public interface**

```bash
git add src/creative_writer/checks.py src/creative_writer/cli.py Makefile README.md tests/test_checks.py tests/test_style_lint.py tests/test_style_references.py
git commit -m "Wire style lint and reference commands"
```

---

### Task 7: Preserve AI Triage, Human Calibration, and Authenticity Decisions

**Files:**
- Create: `src/creative_writer/style_reviews.py`
- Create: `tests/test_style_reviews.py`
- Modify: `src/creative_writer/style_models.py`
- Modify: `tests/test_style_models.py`
- Modify: `src/creative_writer/review_packs.py`
- Modify: `src/creative_writer/checks.py`
- Modify: `tests/test_review_packs.py`
- Modify: `tests/test_checks.py`

**Interfaces:**
- Consumes: `ReviewPackEntry.style`, `StyleContext`, `split_front_matter`, and
  configured chapter manuscript paths.
- Produces:

```python
@dataclass(slots=True)
class StyleReviewDocument:
    path: Path
    front_matter: StyleReviewFrontMatter
    body: str
```

Functions:

```text
style_review_paths(story_dir: Path) -> list[Path]
load_style_review(path: Path) -> StyleReviewDocument
validate_style_reviews(story_dir: Path, context: StyleContext, manuscript_paths: set[str]) -> list[str]
```

`StyleReviewFrontMatter` has:

```yaml
review_id: chapter-one-first-pass
date: 2026-07-31
scope: chapter
manuscripts:
  - manuscript/01-last-week-of-the-permian.md
profile_id: wells-1895-1899
profile_version: 1.0.0
lint_report:
  path: build/time-expedition/style/chapters/01-last-week-of-the-permian-lint-report.json
  sha256: 64-lowercase-hex-digits
reference_packets:
  - traveller-account
reviewer_id: codex
reviewer_role: ai
outcome: qualified
```

The report path is a stable repository-relative reference and need not still
exist under ignored `build/`; its fingerprint remains required. An AI may use
`accepted`, `qualified`, or `revise` only for `scope: chapter`. A story or
anthology review with `outcome: accepted` requires `reviewer_role: human`.

Add these exact strict models to `style_models.py`:

```python
class StyleLintReportReference(StrictModel):
    path: RelativePath
    sha256: SHA256


class StyleReviewFrontMatter(StrictModel):
    review_id: Slug
    date: datetime.date
    scope: StyleReviewScope
    manuscripts: list[RelativePath] = Field(min_length=1)
    profile_id: Slug
    profile_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    lint_report: StyleLintReportReference
    reference_packets: list[Slug] = Field(default_factory=list)
    reviewer_id: NonEmptyText
    reviewer_role: StyleReviewerRole
    outcome: StyleReviewOutcome

    @model_validator(mode="after")
    def enforce_human_milestone_acceptance(self) -> "StyleReviewFrontMatter":
        if self.scope in {"story", "anthology"} and self.outcome == "accepted":
            if self.reviewer_role != "human":
                raise ValueError("story and anthology acceptance requires a human reviewer")
        return self
```

Validate each manuscript as a canonical path below `manuscript/` ending in
`.md`, and validate list uniqueness.

- [ ] **Step 1: Write review and calibration metadata tests**

Test:

- valid AI chapter review;
- valid human story review;
- AI story acceptance rejected;
- invalid outcome rejected;
- unknown profile version, packet ID, or manuscript rejected;
- empty Markdown body rejected;
- `_template.md` and `README.md` ignored;
- old review packs still render unchanged;
- style calibration metadata renders finding IDs, role, claims, AI
  disposition/rationale, decision impact, and the precise human question.

```python
def test_story_acceptance_requires_human_reviewer(tmp_path: Path) -> None:
    payload = valid_style_review_payload()
    payload.update(scope="story", reviewer_role="ai", outcome="accepted")
    with pytest.raises(ValidationError, match="human"):
        StyleReviewFrontMatter.model_validate(payload)
```

- [ ] **Step 2: Run review tests and confirm RED**

Run:

```bash
uv run pytest tests/test_style_reviews.py tests/test_review_packs.py tests/test_checks.py -q
```

Expected: authenticity-review module and style calibration rendering are
missing.

- [ ] **Step 3: Implement tracked authenticity-review validation**

Discover `style-reviews/*.md` in lexical order, excluding `README.md` and
`_template.md`. Parse strict front matter, require a non-empty body, then
cross-check profile ID/version, packet IDs, and manuscript paths against the
active `StyleContext`.

- [ ] **Step 4: Render optional review-pack style context**

When `entry.style` is present, add this writer-facing block before the
excerpt:

```markdown
### Style calibration context

- Profile: `wells-1895-1899` version `1.0.0`
- Intended role: `reported-account`
- Style findings: `finding-003`
- Phase 2B claims: `role-shaped-narrator-distance`
- AI disposition: `escalate`
- AI rationale: The profile signal is mechanically true, but the source packet contains authentic role-specific variation that makes direct revision uncertain.
- Decision impact: The ruling will guide narrator-distance choices across all reported-account chapters.
```

Do not alter output for entries without style metadata.

- [ ] **Step 5: Integrate review validation into `make check`**

When a profile is configured, validate all present authenticity reviews and
all style-bearing review-pack entries. A style-bearing review entry without
an active profile is a blocking error because its profile, roles, and claims
cannot be resolved.

- [ ] **Step 6: Run review and regression tests**

Run:

```bash
uv run pytest tests/test_style_reviews.py tests/test_review_packs.py tests/test_checks.py -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit the decision-record workflow**

```bash
git add src/creative_writer/style_reviews.py src/creative_writer/style_models.py src/creative_writer/review_packs.py src/creative_writer/checks.py tests/test_style_reviews.py tests/test_style_models.py tests/test_review_packs.py tests/test_checks.py
git commit -m "Track style calibration and authenticity reviews"
```

---

### Task 8: Author the Wells `1.0.0` Profile, Six Packets, and Writer Guidance

**Files:**
- Create: `stories/time-expedition/style-profile.yml`
- Create: `stories/time-expedition/style-reference-packets/README.md`
- Create: `stories/time-expedition/style-reference-packets/frame-and-testimony.yml`
- Create: `stories/time-expedition/style-reference-packets/traveller-account.yml`
- Create: `stories/time-expedition/style-reference-packets/observation-and-exposition.yml`
- Create: `stories/time-expedition/style-reference-packets/dialogue-and-social-friction.yml`
- Create: `stories/time-expedition/style-reference-packets/danger-and-action.yml`
- Create: `stories/time-expedition/style-reference-packets/reflection-and-closure.yml`
- Create: `stories/time-expedition/style-reviews/README.md`
- Create: `stories/time-expedition/style-reviews/_template.md`
- Modify: `stories/time-expedition/style-guide.md`
- Modify: `stories/time-expedition/style-card.md`
- Modify: `stories/time-expedition/contract.yml`
- Modify: `stories/time-expedition/chapter-stubs/01-last-week-of-the-permian.md`
- Modify: `stories/time-expedition/source-study/README.md`

**Interfaces:**
- Consumes: the approved Phase 2B ledger, validation record, source registry,
  indexes, profile/packet schemas, and public commands.
- Produces: the first complete operational profile and its writer-facing
  artifacts. It does not change
  `stories/time-expedition/manuscript/01-last-week-of-the-permian.md`.

Use this exact profile identity and provenance:

```yaml
schema_version: 1
profile_id: wells-1895-1899
version: 1.0.0
title: "Late-1890s H. G. Wells operational style profile"
eligible_claim_statuses: [validated, qualified]
provenance:
  study_id: time-expedition-wells-phase-2b
  analysis:
    path: stories/time-expedition/source-study/analysis.yml
    sha256: a1b6c8a50e1527b587fa3861413cc78d87f02f9d2773768859ac629ba5258a6f
  source_registry:
    path: stories/time-expedition/original/sources.yml
    sha256: a5ae71f7f2437e3309ab7ff638388c7623214fd095544ff6470cdb7ad34e9677
  holdout_manifest:
    path: stories/time-expedition/source-study/holdouts.yml
    sha256: 7ff1aaa6c96209ce8a22511840018d6e21580658d1421d4a8e76baef21690d67
  evidence_ledger:
    path: stories/time-expedition/source-study/evidence-ledger.yml
    sha256: c9d01946ca8c68492369a9962c1953ffb1c83948d61863c152fc8514d51b54e1
  validation_record:
    path: stories/time-expedition/source-study/validation.md
    sha256: 39582142777a486157b2249e1f317710099dc2ef8f4e047080cdd53875bd23e4
  passage_indexes:
    development:
      path: build/time-expedition/source-study/indexes/development.jsonl
      sha256: 76131fb52a054567695800cf2028f956679cf1f1723bc80a471f7252d181a3c8
    heldout_wells:
      path: build/time-expedition/source-study/indexes/heldout-wells.jsonl
      sha256: c503a29906aa6fbdbd4847daed698de405d936e9513f6dba020dbde16e74ed6d
    tier4_controls:
      path: build/time-expedition/source-study/indexes/tier4-controls.jsonl
      sha256: 8534aba41eb247f00ebb579cfcc8b8635e66c5e0a339792a76d712cddf45b936
  approved_review_run_id: final-audit-rereview
```

Set:

```yaml
default_packet_ids:
  - frame-and-testimony
  - traveller-account
  - observation-and-exposition
  - dialogue-and-social-friction
  - danger-and-action
  - reflection-and-closure
change_basis: "Initial operationalisation of the human-approved Phase 2B Wells evidence layer and the approved Phase 2C design dated 2026-07-31."
profile_review_refs:
  - "source-study/validation.md#final-audit-rereview"
  - "docs/superpowers/specs/2026-07-31-wells-phase-2c-operational-style-design.md"
```

Define these role mappings:

| Profile role | Phase 2B roles |
| --- | --- |
| `frame` | `frame architecture`, `testimony` |
| `reported-account` | `reported first-person account`, `retrospective first-person narration` |
| `notebook` | `testimony`, `reported first-person account` |
| `scientific-inference` | `speculative method`, `evidence-to-speculation movement`, `landscape observation`, `microscopic observation` |
| `scientific-exposition` | `speculative method`, `scientific argument`, `instructional exposition`, `comparison and classification`, `biological terminology` |
| `social-dialogue` | `social register`, `sustained dialogue`, `dialogue under stress`, `comic friction`, `humour` |
| `danger-action` | `biological danger`, `catastrophe`, `landscape observation`, `biological terminology` |
| `reflection-closure` | `frame architecture`, `short-form architecture` |

Operationalise the ten approved claims with these rule IDs and modes:

| Rule ID | Claim | Mode | Roles |
| --- | --- | --- | --- |
| `practice-mediated-testimony` | `mediated-testimony-frame` | `manual_question` | `frame`, `notebook` |
| `practice-role-shaped-distance` | `role-shaped-narrator-distance` | `manual_question` | `reported-account`, `notebook` |
| `practice-qualified-inference` | `qualified-speculative-inference` | `manual_question` | `scientific-inference` |
| `locator-qualified-inference` | `qualified-speculative-inference` | `locator` with `perhaps`, `probably`, `possibly`, `apparently`, `evidently`, `seemed`, `suppose`, `conjecture` | `scientific-inference` |
| `practice-qualified-exposition` | `qualified-scientific-exposition` | `manual_question` | `scientific-exposition` |
| `practice-dialogue-pressure` | `dialogue-pressure-varies-by-context` | `manual_question` | `social-dialogue` |
| `diagnostic-dialogue-context` | `dialogue-pressure-varies-by-context` | `contextual_diagnostic` | `social-dialogue` |
| `diagnostic-role-shaped-syntax` | `role-shaped-syntax` | `contextual_diagnostic` | `reported-account`, `notebook`, `social-dialogue` |
| `practice-selective-description` | `selective-observed-description` | `manual_question` | `scientific-inference`, `scientific-exposition`, `danger-action` |
| `practice-danger-through-observation` | `danger-through-observation` | `manual_question` | `danger-action` |
| `practice-humour-social-friction` | `humour-through-social-friction` | `manual_question` | `social-dialogue` |
| `practice-evidentiary-closure` | `short-form-evidentiary-closure` | `manual_question` | `frame`, `reflection-closure` |

Use these exact advisory levels, scopes, and editorial questions:

| Rule ID | Advisory / scope | Editorial question |
| --- | --- | --- |
| `practice-mediated-testimony` | `review` / `story` | Does the extraordinary claim reach the reader through a legible chain of witnessing, telling, record, or contest rather than unmediated authorial assertion? |
| `practice-role-shaped-distance` | `review` / `chapter` | Does narrator distance suit the current role, and are shifts between remembered experience, present telling, and reflective hindsight legible? |
| `practice-qualified-inference` | `review` / `passage` | Does inference proceed from observed particulars through provisional explanation, with uncertainty or correction where the evidence demands it? |
| `locator-qualified-inference` | `notice` / `passage` | Where do qualifying terms occur, and do they mark genuine epistemic limits rather than habitual hedging? |
| `practice-qualified-exposition` | `review` / `passage` | Does explanation answer pressure created by scene or evidence, use analogy and classification selectively, and avoid halting the narrative? |
| `practice-dialogue-pressure` | `review` / `chapter` | Is dialogue pressure suited to social and occupational context, with disagreement enacted through role and status rather than interchangeable exposition? |
| `diagnostic-dialogue-context` | `notice` / `chapter` | What does the approximate quoted-speech proportion reveal about this chapter's declared role, once parser limitations and authentic variation are considered? |
| `diagnostic-role-shaped-syntax` | `notice` / `chapter` | Do the sentence and paragraph distributions suit the declared role without being treated as a target cadence? |
| `practice-selective-description` | `review` / `passage` | Are observed details selected for inference or pressure, or has description become a comprehensive inventory? |
| `practice-danger-through-observation` | `review` / `passage` | Does danger first emerge through observation and altered interpretation before action accelerates? |
| `practice-humour-social-friction` | `review` / `passage` | Does humour arise from social friction, misunderstanding, or status rather than inserted quips? |
| `practice-evidentiary-closure` | `review` / `story` | Does the ending leave a final evidentiary fact, residue, or altered uncertainty rather than explain the theme or seal emotional acceptance? |

Add claimless contextual diagnostics:

- `diagnostic-repeated-phrases`: three-word n-grams, review at three
  occurrences after 300 words, using the profile stop-list `the, a, an, and,
  but, if, in, of, on, to`;
- `diagnostic-repeated-openings`: three-word openings, review at three
  occurrences after eight paragraphs;
- `diagnostic-uniform-cadence`: sentence-length CV review below `0.28` after
  twenty sentences.

Both sentence-profile rules use the speech-attribution lexicon `said, asked,
replied, answered, remarked, exclaimed, cried`. The role-shaped syntax rule
reports sentence and paragraph distributions with `minimum_sentences: 12`
and no automatic tolerance. The uniform-cadence rule uses
`minimum_sentences: 20` and the explicit CV tolerance above. The dialogue
context rule uses `minimum_words: 200` and reports its transparent quotation
approximation without an automatic high/low threshold.

Add three manual anti-drift rules:

- `anti-drift-generic-victorian-costume`;
- `anti-drift-neighbouring-adventure-voice`;
- `anti-drift-modern-hard-sf-explanation`.

Each asks a concrete question and states that period vocabulary, adventure
energy, or technical explanation is not itself a defect. The generic
AI-writing scanner remains outside these rules.

Use these exact claimless questions:

| Rule ID | Advisory / scope | Editorial question |
| --- | --- | --- |
| `diagnostic-repeated-phrases` | `review` / `story` | Is this repeated phrase a deliberate motif or an unnoticed reusable sentence component? |
| `diagnostic-repeated-openings` | `review` / `chapter` | Do the recurring paragraph openings create purposeful structure, or do they flatten the prose into a repeated launch pattern? |
| `diagnostic-uniform-cadence` | `review` / `chapter` | Is the unusually even sentence cadence an intentional role effect, or has local syntactic variation collapsed? |
| `anti-drift-generic-victorian-costume` | `review` / `passage` | Would this passage still feel period-authentic without its antique diction and social furniture, or is costume substituting for narrative method? |
| `anti-drift-neighbouring-adventure-voice` | `review` / `chapter` | Has the expedition borrowed heroic certainty, motivation, or cadence from a control author rather than using that source only to test period convention? |
| `anti-drift-modern-hard-sf-explanation` | `review` / `passage` | Does this explanation rely on modern knowledge or confidence unavailable to a late-1890s speculative narrator, instead of period-bounded observation and conjecture? |

For every claim-backed rule, set `interpretation_limits` to the linked
claim's exact `scope_and_limits`, followed by `Prohibited
overgeneralisation:` and the claim's exact
`prohibited_overgeneralisation`. Claimless diagnostics state that the signal
is a locator, not a Wells requirement. Anti-drift rules state that period
vocabulary, adventure energy, and technical detail remain legitimate when
their narrative function is sound.

Use these exact focal passage selections with context radius `1`:

| Packet | Positive/variation passages | Negative control |
| --- | --- | --- |
| `frame-and-testimony` | `the-time-machine:ii:101:b859a93fec21`; `selected-short-fiction/the-plattner-story:the-plattner-story:1:725f01ec6e50`; `the-time-machine:ii:79:3f712a420f66` | `the-beetle:book-i-the-house-with-the-open-window:54:8440a05cc8de` |
| `traveller-account` | `the-time-machine:ix:247:7c7656f6a229`; `the-time-machine:iii:102:301f3d1a7670`; `the-time-machine:xii:276:23b26487ff8e`; `the-island-of-doctor-moreau:i:2:522a64e3a5eb` | none |
| `observation-and-exposition` | `the-time-machine:iv:147:5a08c0c8cfcb`; `the-time-machine:v:165:29fe69fce8b4`; `the-war-of-the-worlds:v:101:8debc943c595`; `text-book-of-biology-part-1:note-on-making-comparisons:527:75c6e3818b0d` | `the-days-work:the-bridge-builders:72:c8e7cc2f7612` |
| `dialogue-and-social-friction` | `the-invisible-man:iii:92:8c3779ecfb78`; `the-invisible-man:iv:156:bea3b86ad1a8`; `the-invisible-man:vii:223:04a2271ebbf5`; `the-island-of-doctor-moreau:v:115:8ddf9cdc824d` | `the-british-barbarians:ii:130:dc2c2c7ed9db` |
| `danger-and-action` | `selected-short-fiction/the-sea-raiders:ii:19:013c203950dd`; `the-war-of-the-worlds:v:98:0fa76c4fe402`; `selected-short-fiction/the-sea-raiders:i:11:e706bbe4a853`; `the-war-of-the-worlds:xi:243:e7d3b67be077` | `a-desert-drama:stoppa-backa-cried-the-native-pilot-to-the-european-engineer:217:c5a008af45d1` |
| `reflection-and-closure` | `the-time-machine:epilogue:308:6c18eecffc7e`; `selected-short-fiction/the-crystal-egg:the-crystal-egg:51:025f5af2df0e`; `the-time-machine:xii:279:e22b90a63db0`; `selected-short-fiction/the-star:the-star:39:de14ba922638` | `king-solomons-mines:xx:1521:b6ceb2d61e7f` |

The `traveller-account` packet uses authentic Wells variation instead of a
Tier 4 control because its purpose is to compare role-shaped distance within
Wells, not contrast expedition voice with a neighbouring author.

Assign packet entry kinds and claims exactly as follows:

| Passage ID | Kind | Claim IDs |
| --- | --- | --- |
| `the-time-machine:ii:101:b859a93fec21` | `positive_example` | `mediated-testimony-frame` |
| `selected-short-fiction/the-plattner-story:the-plattner-story:1:725f01ec6e50` | `positive_example` | `mediated-testimony-frame` |
| `the-time-machine:ii:79:3f712a420f66` | `authentic_variation` | `mediated-testimony-frame` |
| `the-beetle:book-i-the-house-with-the-open-window:54:8440a05cc8de` | `negative_control` | `mediated-testimony-frame` |
| `the-time-machine:ix:247:7c7656f6a229` | `positive_example` | `role-shaped-narrator-distance` |
| `the-time-machine:iii:102:301f3d1a7670` | `positive_example` | `role-shaped-syntax` |
| `the-time-machine:xii:276:23b26487ff8e` | `positive_example` | `role-shaped-narrator-distance` |
| `the-island-of-doctor-moreau:i:2:522a64e3a5eb` | `authentic_variation` | `role-shaped-narrator-distance` |
| `the-time-machine:iv:147:5a08c0c8cfcb` | `positive_example` | `qualified-speculative-inference` |
| `the-time-machine:v:165:29fe69fce8b4` | `positive_example` | `qualified-scientific-exposition` |
| `the-war-of-the-worlds:v:101:8debc943c595` | `positive_example` | `selective-observed-description` |
| `text-book-of-biology-part-1:note-on-making-comparisons:527:75c6e3818b0d` | `authentic_variation` | `qualified-scientific-exposition` |
| `the-days-work:the-bridge-builders:72:c8e7cc2f7612` | `negative_control` | `qualified-scientific-exposition` |
| `the-invisible-man:iii:92:8c3779ecfb78` | `positive_example` | `dialogue-pressure-varies-by-context` |
| `the-invisible-man:iv:156:bea3b86ad1a8` | `positive_example` | `humour-through-social-friction` |
| `the-invisible-man:vii:223:04a2271ebbf5` | `positive_example` | `dialogue-pressure-varies-by-context`, `role-shaped-syntax` |
| `the-island-of-doctor-moreau:v:115:8ddf9cdc824d` | `authentic_variation` | `dialogue-pressure-varies-by-context` |
| `the-british-barbarians:ii:130:dc2c2c7ed9db` | `negative_control` | `humour-through-social-friction` |
| `selected-short-fiction/the-sea-raiders:ii:19:013c203950dd` | `positive_example` | `danger-through-observation` |
| `the-war-of-the-worlds:v:98:0fa76c4fe402` | `positive_example` | `danger-through-observation` |
| `selected-short-fiction/the-sea-raiders:i:11:e706bbe4a853` | `authentic_variation` | `danger-through-observation` |
| `the-war-of-the-worlds:xi:243:e7d3b67be077` | `positive_example` | `danger-through-observation` |
| `a-desert-drama:stoppa-backa-cried-the-native-pilot-to-the-european-engineer:217:c5a008af45d1` | `negative_control` | `danger-through-observation` |
| `the-time-machine:epilogue:308:6c18eecffc7e` | `positive_example` | `short-form-evidentiary-closure` |
| `selected-short-fiction/the-crystal-egg:the-crystal-egg:51:025f5af2df0e` | `positive_example` | `short-form-evidentiary-closure` |
| `the-time-machine:xii:279:e22b90a63db0` | `authentic_variation` | `short-form-evidentiary-closure` |
| `selected-short-fiction/the-star:the-star:39:de14ba922638` | `positive_example` | `short-form-evidentiary-closure` |
| `king-solomons-mines:xx:1521:b6ceb2d61e7f` | `negative_control` | `short-form-evidentiary-closure` |

- [ ] **Step 1: Add the profile and six manifests**

For each claim-backed rule, derive `source_passage_ids`,
`variation_passage_ids`, and `packet_ids` from every packet-table entry whose
claim list contains that rule's claim. Do not copy negative controls into a
claim-backed rule. Set the anti-drift control bindings to:

- `anti-drift-generic-victorian-costume`: the Beetle and British Barbarians
  control locators in the packet table;
- `anti-drift-neighbouring-adventure-voice`: the Days Work, Desert Drama, and
  King Solomon's Mines control locators;
- `anti-drift-modern-hard-sf-explanation`: no source locator, because Phase 2B
  admitted no modern hard-SF control.

Claimless diagnostics have no source, variation, control, claim, or packet
bindings. Packet entries declare the exact claims, tiers, permitted uses,
selection reasons, prohibited uses, and this anti-copying instruction:

```text
Study narrative method, evidentiary sequence, role, and cadence. Do not borrow distinctive phrases, sentence skeletons, images, or local wording.
```

- [ ] **Step 2: Activate the profile and declare the expedition roles**

Append to `contract.yml`:

```yaml
style_lint:
  profile: style-profile.yml
  generic_ai_audit: true
```

Add all eight profile role IDs and all six packet IDs to the sole current
chapter stub. Do not alter its planning body or manuscript target.

- [ ] **Step 3: Replace provisional writer guidance**

Write `style-guide.md` with:

- source hierarchy and recovered-manuscript objective;
- one section per profile role;
- evidence-backed practices keyed to rule and claim IDs;
- shared-period and qualified-claim cautions;
- authentic variation and counterexamples;
- generic Victorian, neighbouring-author, modern hard-SF, and AI-surface
  drift risks;
- packet commands and anti-copying use;
- chapter, story, and anthology review gates;
- AI triage dispositions and selective human escalation;
- profile-change discipline.

Write `style-card.md` as a concise desk reference with source hierarchy,
role reminders, observation-inference discipline, high-risk drift patterns,
the two commands, and links to the full guide/profile. It must contain no
phrase bank or imitation prompt.

- [ ] **Step 4: Add authenticity-review guidance and template**

The template contains the exact front matter from Task 7 with a valid
64-character example hash and these body headings:

```markdown
## Important findings
## Dispositions and rationale
## Accepted intentional variations
## Revisions requested or completed
## Human calibration decisions
## Unresolved uncertainty
## Proposed profile changes
```

The README states that present reviews validate, absent milestone reviews do
not block builds, AI can close chapter reviews, and human approval closes
story/anthology acceptance.

- [ ] **Step 5: Validate the real profile and compile all packets**

Run:

```bash
make check STORY=time-expedition
make style-reference STORY=time-expedition PACK=frame-and-testimony
make style-reference STORY=time-expedition PACK=traveller-account
make style-reference STORY=time-expedition PACK=observation-and-exposition
make style-reference STORY=time-expedition PACK=dialogue-and-social-friction
make style-reference STORY=time-expedition PACK=danger-and-action
make style-reference STORY=time-expedition PACK=reflection-and-closure
```

Expected: check passes; six packets land under
`build/time-expedition/style/reference-packets/`; every Tier 4 excerpt appears
only in `Negative comparisons`.

- [ ] **Step 6: Verify the manuscript is unchanged**

Run:

```bash
git diff --exit-code -- stories/time-expedition/manuscript/
```

Expected: exit `0` with no output.

- [ ] **Step 7: Commit the Wells operational profile**

```bash
git add stories/time-expedition/style-profile.yml stories/time-expedition/style-reference-packets stories/time-expedition/style-reviews stories/time-expedition/style-guide.md stories/time-expedition/style-card.md stories/time-expedition/contract.yml stories/time-expedition/chapter-stubs/01-last-week-of-the-permian.md stories/time-expedition/source-study/README.md
git commit -m "Add Wells operational style profile"
```

---

### Task 9: Calibrate, Verify End to End, and Stop at the Phase 2C Boundary

**Files:**
- Create: `tests/fixtures/style/wells-authority-passages.yml`
- Create: `tests/fixtures/style/repeated-drift.md`
- Create: `tests/fixtures/style/uniform-cadence.md`
- Create: `tests/fixtures/style/punctuation-drift.md`
- Create: `tests/fixtures/style/generic-ai-surface.md`
- Create: `tests/fixtures/style/calibration-manuscript.md`
- Create: `tests/fixtures/style/calibration-review-pack.yml`
- Modify: `tests/test_style_lint.py`
- Modify: `tests/test_style_references.py`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-07-31-wells-phase-2c-operational-style-design.md`

**Interfaces:**
- Consumes: the complete profile engine, real Wells profile, six packet
  manifests, retained source witnesses, and approved completion criteria.
- Produces: calibration evidence that catches obvious synthetic drift without
  routinely condemning the authority corpus, plus a verified Phase 2C v1
  handoff.

The authentic fixture contains the exact `original_text` and locator for
these six passages, copied verbatim from the verified Phase 2B indexes:

```text
the-time-machine:ii:101:b859a93fec21
the-time-machine:iv:147:5a08c0c8cfcb
the-invisible-man:iii:92:8c3779ecfb78
selected-short-fiction/the-sea-raiders:ii:19:013c203950dd
the-war-of-the-worlds:v:101:8debc943c595
the-time-machine:epilogue:308:6c18eecffc7e
```

The fixture records `passage_id`, `role`, and `text` for each entry. It is a
small public-domain calibration sample, not a new evidence layer or training
set.

`calibration-manuscript.md` contains nine non-empty lines grouped into three
three-line excerpts: a repeated-phrase edge case, a deliberately even
notebook cadence, and a generic-AI-surface edge case. The calibration manifest
is titled `Synthetic style calibration`, has purpose `Exercise the selective
human escalation surface without using manuscript prose`, and contains
`uncertainty` entries `repeated-phrase`, `notebook-cadence`, and
`modern-exposition`. It uses inclusive ranges `1-3`, `4-6`, and `7-9`, profile
`wells-1895-1899` version `1.0.0`, roles `reported-account`, `notebook`, and
`scientific-exposition`, finding IDs `finding-001` through `finding-003`, and
`ai_disposition: escalate` for all three. Its precise questions are:

1. Is the repeated phrase functioning as deliberate testimony structure, or
   should the profile continue to flag it as reusable cadence?
2. Is the even notebook cadence an authentic documentary effect, or does it
   flatten the Time Traveller's reported voice?
3. Does the generic scanner identify a real modern explanatory habit here,
   or is it colliding with legitimate period scientific exposition?

Each entry's `decision_impact` names the affected profile rule and says the
answer will guide later Permian chapters; each `ai_rationale` explains why the
source packet leaves the case genuinely ambiguous.

- [ ] **Step 1: Add calibration tests and confirm their intent**

Add tests proving:

- all profile-owned automated diagnostics can run over the six authentic
  passages;
- no authentic passage receives every contextual review signal;
- fewer than half of the authentic passages receive a review-level
  profile-owned automated finding;
- generic AI scanner hits, when supplied by a fake scanner, remain visible
  but do not fail the authentic fixture;
- repeated drift raises `diagnostic-repeated-phrases`;
- uniform cadence raises `diagnostic-uniform-cadence`;
- four em dashes above a configured limit of two raise the shared surface
  warning;
- fake generic AI JSON raises a separately labelled generic finding;
- a three-entry synthetic calibration manifest compiles through
  `generate_review_pack` with finding IDs, AI dispositions, rationales,
  decision impacts, and one precise question per entry;
- no Tier 4 packet entry is rendered as positive guidance.

```python
def test_authority_fixture_is_not_systematically_condemned(
    wells_context,
    wells_fixture_entries,
) -> None:
    review_flags = []
    automated_rule_ids = {
        rule.rule.id
        for rule in wells_context.rules
        if rule.rule.evaluation_mode != "manual_question"
    }
    for entry in wells_fixture_entries:
        diagnostics = analyse_manuscript(
            entry["text"],
            lexicons={},
            speech_attribution_verbs=["said", "asked", "replied", "answered", "remarked", "exclaimed", "cried"],
            stop_words=["the", "a", "an", "and", "but", "if", "in", "of", "on", "to"],
        )
        evaluation = evaluate_style_rules(
            wells_context,
            diagnostics,
            roles=[entry["role"]],
            manuscript=f"calibration/{entry['passage_id']}",
        )
        review_flags.append([
            finding
            for finding in evaluation.findings
            if finding.advisory == "review" and finding.rule_id in automated_rule_ids
        ])
    assert sum(bool(flags) for flags in review_flags) < len(review_flags) / 2
    assert all(len(flags) < len(automated_rule_ids) for flags in review_flags)
```

- [ ] **Step 2: Run calibration tests and make one focused repair**

Run:

```bash
uv run pytest tests/test_style_lint.py tests/test_style_references.py tests/test_review_packs.py -k "calibration or authority or drift or tier_four" -q
```

Expected: tests pass. If an authentic fixture is systematically flagged,
adjust only the responsible transparent tolerance or parser defect, document
the reason in the profile's `change_basis`, increment the profile patch
version to `1.0.1`, and update matching packet/review references. Do not tune
unrelated rules or perform a second polish loop.

- [ ] **Step 3: Run real whole-story and chapter smoke tests**

Run:

```bash
make check STORY=time-expedition
make style-lint STORY=time-expedition
make style-lint STORY=time-expedition CHAPTER=01-last-week-of-the-permian
```

Expected:

- coherence check passes;
- whole-story Markdown/JSON appear under
  `build/time-expedition/style/`;
- chapter Markdown/JSON appear under
  `build/time-expedition/style/chapters/`;
- the placeholder manuscript may produce a visible generic
  placeholder/instruction warning, but style-lint exits `0`;
- both reports identify the profile/version, roles, claim provenance,
  partial scanner state if applicable, and no score.

- [ ] **Step 4: Run complete repository verification**

Run:

```bash
uv run pytest -q
make check STORY=time-expedition
git diff --check
git status --short
```

Expected: full suite passes, story check passes, no whitespace errors, and
only intentional Phase 2C files are dirty.

- [ ] **Step 5: Verify all six packet outputs and report invariants**

Run:

```bash
jq -e 'has("score") | not' build/time-expedition/style/lint-report.json
jq -e 'all(.findings[]; has("score") | not)' build/time-expedition/style/lint-report.json
rg -n "Tier 4|Negative comparisons|Do not borrow" build/time-expedition/style/reference-packets
```

Expected: both `jq` checks return `true`; the `rg` command shows every
negative-control label and anti-copying warning.

- [ ] **Step 6: Record completion and the next boundary**

Update the design status to `implemented` only after all completion criteria
pass. Update `README.md` to state that Phase 2C v1 is operational, the first
substantive Permian chapter is the next calibration event, and the immediate
next project tranche is the dual-layer Permian research dossier. Do not add
research findings or manuscript prose.

- [ ] **Step 7: Commit the calibrated Phase 2C release**

```bash
git add tests/fixtures/style tests/test_style_lint.py tests/test_style_references.py tests/test_review_packs.py README.md docs/superpowers/specs/2026-07-31-wells-phase-2c-operational-style-design.md
git commit -m "Calibrate and verify Wells style workflow"
```

---

## Completion Gate

Phase 2C v1 is ready for user assessment when:

- `make check STORY=time-expedition` passes without running manuscript style
  analysis;
- all six reference packets compile from provenance-verified passage indexes;
- whole-story and chapter-targeted lint reports are deterministic, score-free,
  and advisory;
- all ten Phase 2B claims have bounded operational treatment;
- generic AI signals are optional, separate, and non-authoritative;
- review-pack calibration metadata and tracked authenticity reviews validate;
- the authority-corpus fixture is not systematically condemned;
- the full pytest suite passes;
- no manuscript prose or Permian research artifact changed;
- one focused repair pass found no remaining material defect.

At that point, stop and report completed work, material residual limitations,
and the highest-value next tranche. Do not begin repeated threshold tuning
until a substantive Permian draft supplies real evidence.
