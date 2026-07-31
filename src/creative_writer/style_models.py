"""Strict schemas for the advisory Phase 2C style workflow."""

from __future__ import annotations

import math
from typing import Annotated, Literal

from pydantic import (
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

from creative_writer.exceptions import CreativeWriterError
from creative_writer.source_analysis_common import validate_relative_path
from creative_writer.source_analysis_models import (
    ClaimJurisdiction,
    NonEmptyText,
    RelativePath,
    SHA256,
    Slug,
    StrictModel,
)

SemanticVersion = Annotated[StrictStr, Field(pattern=r"^\d+\.\d+\.\d+$")]

StyleRuleFamily = Literal["practice", "diagnostic", "anti_drift"]
StyleAdvisoryLevel = Literal["notice", "review"]
StyleScope = Literal["passage", "chapter", "story"]
StyleEvaluationMode = Literal[
    "manual_question", "locator", "contextual_diagnostic"
]
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
StyleToleranceMetric = Literal[
    "sentence_length_median",
    "sentence_length_p90",
    "sentence_length_cv",
    "paragraph_length_median",
    "dialogue_proportion",
]


def _validate_canonical_relative_path(value: str) -> str:
    try:
        return validate_relative_path(value)
    except CreativeWriterError as exc:
        raise ValueError(str(exc)) from exc


def _validate_unique(values: list[str], label: str) -> list[str]:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")
    return values


class StyleArtifactReference(StrictModel):
    path: RelativePath
    sha256: SHA256

    _path = field_validator("path")(_validate_canonical_relative_path)


class StylePassageIndexes(StrictModel):
    development: StyleArtifactReference
    heldout_wells: StyleArtifactReference
    tier4_controls: StyleArtifactReference


class StyleProvenance(StrictModel):
    study_id: Slug
    analysis: StyleArtifactReference
    source_registry: StyleArtifactReference
    holdout_manifest: StyleArtifactReference
    evidence_ledger: StyleArtifactReference
    validation_record: StyleArtifactReference
    passage_indexes: StylePassageIndexes
    approved_review_run_id: Slug


class StyleNarrativeRole(StrictModel):
    id: Slug
    label: NonEmptyText
    description: NonEmptyText
    phase_2b_roles: list[NonEmptyText] = Field(min_length=1)

    @field_validator("phase_2b_roles")
    @classmethod
    def unique_phase_2b_roles(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "Phase 2B roles")


class LexiconLocatorSignal(StrictModel):
    kind: Literal["lexicon_locator"]
    terms: list[NonEmptyText] = Field(min_length=1)
    max_examples: StrictInt = Field(default=8, ge=1, le=20)

    @field_validator("terms")
    @classmethod
    def unique_terms(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "locator terms")


class SentenceProfileSignal(StrictModel):
    kind: Literal["sentence_profile"]
    speech_attribution_verbs: list[NonEmptyText] = Field(min_length=1)
    minimum_sentences: StrictInt = Field(default=12, ge=1)

    @field_validator("speech_attribution_verbs")
    @classmethod
    def unique_speech_attribution_verbs(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "speech-attribution verbs")


class DialogueProfileSignal(StrictModel):
    kind: Literal["dialogue_profile"]
    minimum_words: StrictInt = Field(default=200, ge=1)


class RepeatedNgramSignal(StrictModel):
    kind: Literal["repeated_ngram"]
    ngram_size: StrictInt = Field(default=3, ge=3, le=6)
    minimum_occurrences: StrictInt = Field(default=3, ge=2)
    minimum_words: StrictInt = Field(default=300, ge=1)
    stop_words: list[NonEmptyText] = Field(default_factory=list)

    @field_validator("stop_words")
    @classmethod
    def unique_stop_words(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "stop words")


class ParagraphOpeningSignal(StrictModel):
    kind: Literal["paragraph_opening"]
    prefix_words: StrictInt = Field(default=3, ge=1, le=6)
    minimum_occurrences: StrictInt = Field(default=3, ge=2)
    minimum_paragraphs: StrictInt = Field(default=8, ge=2)


StyleSignal = Annotated[
    LexiconLocatorSignal
    | SentenceProfileSignal
    | DialogueProfileSignal
    | RepeatedNgramSignal
    | ParagraphOpeningSignal,
    Field(discriminator="kind"),
]


class StyleTolerance(StrictModel):
    metric: StyleToleranceMetric
    minimum_sample_size: StrictInt = Field(ge=1)
    review_below: StrictFloat | None = None
    review_above: StrictFloat | None = None
    reference_witness_ids: list[NonEmptyText] = Field(min_length=1)
    rationale: NonEmptyText

    @field_validator("review_below", "review_above")
    @classmethod
    def require_finite_bounds(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("style tolerance bounds must be finite")
        return value

    @field_validator("reference_witness_ids")
    @classmethod
    def unique_reference_witness_ids(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "reference witness IDs")

    @model_validator(mode="after")
    def require_numeric_bound(self) -> "StyleTolerance":
        if self.review_below is None and self.review_above is None:
            raise ValueError("style tolerance requires at least one numeric bound")
        return self


class StyleRule(StrictModel):
    id: Slug
    name: NonEmptyText
    family: StyleRuleFamily
    advisory: StyleAdvisoryLevel
    claim_ids: list[Slug]
    roles: list[Slug]
    scope: StyleScope
    evaluation_mode: StyleEvaluationMode
    review_question: NonEmptyText
    signal: StyleSignal | None = None
    tolerance: StyleTolerance | None = None
    source_passage_ids: list[NonEmptyText]
    variation_passage_ids: list[NonEmptyText]
    control_passage_ids: list[NonEmptyText]
    packet_ids: list[Slug]
    interpretation_limits: NonEmptyText

    @field_validator(
        "claim_ids",
        "roles",
        "source_passage_ids",
        "variation_passage_ids",
        "control_passage_ids",
        "packet_ids",
    )
    @classmethod
    def unique_id_lists(cls, value: list[str], info) -> list[str]:
        labels = {
            "claim_ids": "rule claim IDs",
            "roles": "rule roles",
            "source_passage_ids": "source passage IDs",
            "variation_passage_ids": "variation passage IDs",
            "control_passage_ids": "control passage IDs",
            "packet_ids": "rule packet IDs",
        }
        return _validate_unique(value, labels[info.field_name])

    @model_validator(mode="after")
    def validate_rule_contract(self) -> "StyleRule":
        if self.evaluation_mode == "manual_question" and self.signal is not None:
            raise ValueError("manual questions cannot declare a signal")
        if self.evaluation_mode != "manual_question" and self.signal is None:
            raise ValueError("locator and contextual rules require a signal")
        if self.family == "practice" and not self.claim_ids:
            raise ValueError("practice rules require at least one Phase 2B claim")
        if self.family != "anti_drift" and self.control_passage_ids:
            raise ValueError("Tier 4 controls belong only to anti-drift rules")
        return self


class StyleProfile(StrictModel):
    schema_version: Literal[1]
    profile_id: Slug
    version: SemanticVersion
    title: NonEmptyText
    provenance: StyleProvenance
    eligible_claim_statuses: list[Literal["validated", "qualified"]]
    default_packet_ids: list[Slug]
    change_basis: NonEmptyText
    profile_review_refs: list[NonEmptyText]
    roles: list[StyleNarrativeRole]
    rules: list[StyleRule]

    @field_validator(
        "eligible_claim_statuses", "default_packet_ids", "profile_review_refs"
    )
    @classmethod
    def unique_profile_lists(cls, value: list[str], info) -> list[str]:
        labels = {
            "eligible_claim_statuses": "eligible claim statuses",
            "default_packet_ids": "default packet IDs",
            "profile_review_refs": "profile review references",
        }
        return _validate_unique(value, labels[info.field_name])

    @model_validator(mode="after")
    def unique_role_and_rule_ids(self) -> "StyleProfile":
        _validate_unique([role.id for role in self.roles], "role IDs")
        _validate_unique([rule.id for rule in self.rules], "rule IDs")
        return self


class StylePacketEntry(StrictModel):
    id: Slug
    passage_id: NonEmptyText
    kind: StylePacketEntryKind
    claim_ids: list[Slug]
    authority_tier: Literal[1, 2, 3, 4]
    permitted_use: NonEmptyText
    selection_note: NonEmptyText
    context_radius: StrictInt | None = Field(default=None, ge=0, le=2)

    @field_validator("claim_ids")
    @classmethod
    def unique_claim_ids(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "packet entry claim IDs")

    @model_validator(mode="after")
    def restrict_tier_four_use(self) -> "StylePacketEntry":
        if self.authority_tier == 4 and self.kind != "negative_control":
            raise ValueError("Tier 4 packet entries must be labelled negative_control")
        return self


class StyleReferencePacket(StrictModel):
    schema_version: Literal[1]
    id: Slug
    title: NonEmptyText
    purpose: NonEmptyText
    profile_id: Slug
    profile_version: SemanticVersion
    roles: list[Slug]
    claim_ids: list[Slug]
    context_radius: StrictInt = Field(ge=0, le=2)
    entries: list[StylePacketEntry]
    prohibited_uses: list[NonEmptyText]
    anti_copying_guidance: NonEmptyText

    @field_validator("roles", "claim_ids", "prohibited_uses")
    @classmethod
    def unique_packet_lists(cls, value: list[str], info) -> list[str]:
        labels = {
            "roles": "packet role IDs",
            "claim_ids": "packet claim IDs",
            "prohibited_uses": "prohibited uses",
        }
        return _validate_unique(value, labels[info.field_name])

    @model_validator(mode="after")
    def unique_entry_ids(self) -> "StyleReferencePacket":
        _validate_unique([entry.id for entry in self.entries], "entry IDs")
        return self


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
    claim_statuses: dict[Slug, Literal["validated", "qualified"]]
    claim_jurisdictions: list[ClaimJurisdiction]
    source_passage_ids: list[NonEmptyText]
    editorial_question: NonEmptyText
    limitations: NonEmptyText

    _manuscript = field_validator("manuscript")(
        _validate_canonical_relative_path
    )

    @field_validator("roles", "claim_ids", "source_passage_ids")
    @classmethod
    def unique_id_lists(cls, value: list[str], info) -> list[str]:
        labels = {
            "roles": "finding role IDs",
            "claim_ids": "finding claim IDs",
            "source_passage_ids": "finding source passage IDs",
        }
        return _validate_unique(value, labels[info.field_name])

    @model_validator(mode="after")
    def validate_finding_contract(self) -> "StyleFinding":
        if self.line_end < self.line_start:
            raise ValueError(
                "line_end must be greater than or equal to line_start"
            )
        if set(self.claim_statuses) != set(self.claim_ids):
            raise ValueError(
                "finding claim status keys must exactly match claim IDs"
            )
        return self


class StyleChapterInventory(StrictModel):
    stub: RelativePath
    manuscript: RelativePath
    title: NonEmptyText
    summary: NonEmptyText
    roles: list[Slug]
    packet_ids: list[Slug]
    word_count: StrictInt = Field(ge=0)

    _paths = field_validator("stub", "manuscript")(
        _validate_canonical_relative_path
    )

    @field_validator("roles", "packet_ids")
    @classmethod
    def unique_id_lists(cls, value: list[str], info) -> list[str]:
        label = "chapter role IDs" if info.field_name == "roles" else "chapter packet IDs"
        return _validate_unique(value, label)


class StylePracticeQuestion(StrictModel):
    rule_id: Slug
    advisory: StyleAdvisoryLevel
    roles: list[Slug]
    claim_ids: list[Slug]
    claim_statuses: dict[Slug, Literal["validated", "qualified"]]
    claim_jurisdictions: list[ClaimJurisdiction]
    question: NonEmptyText
    source_passage_ids: list[NonEmptyText]
    interpretation_limits: NonEmptyText

    @field_validator("roles", "claim_ids", "source_passage_ids")
    @classmethod
    def unique_id_lists(cls, value: list[str], info) -> list[str]:
        labels = {
            "roles": "practice-question role IDs",
            "claim_ids": "practice-question claim IDs",
            "source_passage_ids": "practice-question source passage IDs",
        }
        return _validate_unique(value, labels[info.field_name])

    @model_validator(mode="after")
    def validate_claim_statuses(self) -> "StylePracticeQuestion":
        if set(self.claim_statuses) != set(self.claim_ids):
            raise ValueError(
                "practice-question claim status keys must exactly match claim IDs"
            )
        return self


class StyleDiagnosticRecord(StrictModel):
    rule_id: Slug
    manuscript: RelativePath
    roles: list[Slug]
    measurements: dict[
        NonEmptyText, StrictInt | StrictFloat | NonEmptyText | None
    ]
    sample_size: StrictInt = Field(ge=0)
    tolerance_note: NonEmptyText
    triggered: StrictBool
    limitations: NonEmptyText

    _manuscript = field_validator("manuscript")(
        _validate_canonical_relative_path
    )

    @field_validator("measurements")
    @classmethod
    def require_finite_float_measurements(
        cls, value: dict[str, int | float | str | None]
    ) -> dict[str, int | float | str | None]:
        if any(
            isinstance(measurement, float) and not math.isfinite(measurement)
            for measurement in value.values()
        ):
            raise ValueError("diagnostic float measurements must be finite")
        return value

    @field_validator("roles")
    @classmethod
    def unique_roles(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "diagnostic role IDs")


class GenericAIReportSection(StrictModel):
    status: Literal["complete", "unavailable", "disabled"]
    scanner: NonEmptyText | None
    group_names: list[NonEmptyText]
    finding_ids: list[Slug]
    caution: NonEmptyText
    notice: NonEmptyText | None

    @field_validator("group_names", "finding_ids")
    @classmethod
    def unique_lists(cls, value: list[str], info) -> list[str]:
        label = (
            "generic AI group names"
            if info.field_name == "group_names"
            else "generic AI finding IDs"
        )
        return _validate_unique(value, label)


class StyleLintReport(StrictModel):
    schema_version: Literal[1]
    story_slug: Slug
    story_title: NonEmptyText
    scope: Literal["story", "chapter"]
    chapter_selector: NonEmptyText | None
    profile_id: Slug
    profile_version: SemanticVersion
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

    @field_validator("limitations", "next_steps")
    @classmethod
    def unique_guidance(cls, value: list[str], info) -> list[str]:
        label = "report limitations" if info.field_name == "limitations" else "next steps"
        return _validate_unique(value, label)

    @model_validator(mode="after")
    def validate_report_contract(self) -> "StyleLintReport":
        _validate_unique([finding.id for finding in self.findings], "finding IDs")
        expected_partial = self.generic_ai.status == "unavailable"
        if self.partial != expected_partial:
            raise ValueError(
                "partial must be true exactly when generic AI status is unavailable"
            )
        return self
