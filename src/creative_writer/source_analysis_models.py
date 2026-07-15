"""Strict schemas for the Phase 2B source-analysis evidence layer."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal, get_args

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    ValidationError,
    field_validator,
    model_validator,
)

from creative_writer.exceptions import CreativeWriterError
Slug = Annotated[StrictStr, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
SHA256 = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
GitHash = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")]
NonEmptyText = Annotated[StrictStr, Field(min_length=1, pattern=r"(?s).*\S.*")]
RelativePath = Annotated[StrictStr, Field(min_length=1, pattern=r"^[^/].*")]
Stage = Literal["protocol", "development", "candidate_frozen", "validated"]
DimensionId = Literal[
    "frame-architecture",
    "narrator-distance",
    "observation-inference",
    "scientific-exposition",
    "dialogue-social-friction",
    "syntax-rhythm",
    "diction-description",
    "suspense-scene-pressure",
    "humour-irony",
    "transitions-ending-logic",
]

DIMENSION_IDS = set(get_args(DimensionId))


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class StrictCompositionWindow(StrictModel):
    start: StrictInt = Field(ge=1800, le=2100)
    end: StrictInt = Field(ge=1800, le=2100)

    @model_validator(mode="after")
    def validate_order(self) -> "StrictCompositionWindow":
        if self.end < self.start:
            raise ValueError("composition window end must not precede start")
        return self


def _validate_relative_path(value: str) -> str:
    if "\\" in value:
        raise ValueError("paths must use canonical relative POSIX syntax")
    parts = value.split("/")
    if not value or value.startswith("/") or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("path must be a non-empty canonical relative POSIX path")
    return value


def _validate_generated_path(value: str) -> str:
    path = _validate_relative_path(value)
    if not path.startswith("build/"):
        raise ValueError("generated paths must begin with build/")
    return path


def _validate_text_list(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("values must be non-empty strings")
        cleaned.append(value.strip())
    return cleaned


def _validate_unique(values: list[str], label: str) -> list[str]:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")
    return values


def _validate_selection_identity(
    witness_id: str, source_id: str, selection_id: str | None
) -> None:
    if "/" in witness_id:
        expected_source, expected_selection = witness_id.split("/", 1)
        if source_id != expected_source or selection_id != expected_selection:
            raise ValueError("mismatched selection identity")
    elif source_id != witness_id or selection_id is not None:
        raise ValueError("mismatched selection identity")


def _heading_slug(label: str) -> str:
    normalized = unicodedata.normalize("NFC", label)
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    if slug:
        return slug
    if normalized == "Untitled":
        return "untitled"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    return f"heading-{digest}"


class RegistryReference(StrictModel):
    path: RelativePath
    sha256: SHA256

    _path = field_validator("path")(_validate_relative_path)


class PassageRules(StrictModel):
    input_format: Literal["gfm"]
    heading_context: StrictBool
    substantive_block_types: list[
        Literal["paragraph", "block_quote", "verse", "list_item"]
    ] = Field(min_length=1)
    passage_id_template: Literal[
        "<witness-id>:<heading-slug>:<source-ordinal>:<hash12>"
    ]
    context_radius: StrictInt = Field(ge=0, le=2)

    @field_validator("substantive_block_types")
    @classmethod
    def unique_block_types(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "substantive block types")


class WitnessDescriptor(StrictModel):
    """Identity and retained-text fingerprint supplied to the passage parser."""

    witness_id: NonEmptyText
    witness_ordinal: StrictInt = Field(ge=1)
    source_id: NonEmptyText
    selection_id: Slug | None = None
    source_fingerprint: SHA256

    @model_validator(mode="after")
    def validate_identity(self) -> "WitnessDescriptor":
        _validate_selection_identity(self.witness_id, self.source_id, self.selection_id)
        return self


class PartitionRules(StrictModel):
    seed: NonEmptyText
    algorithm_version: NonEmptyText
    holdout_fraction: StrictFloat
    max_blocks_per_window: Literal[5]
    whole_work_holdouts: list[NonEmptyText] = Field(min_length=1)

    @field_validator("holdout_fraction")
    @classmethod
    def prescribed_fraction(cls, value: float) -> float:
        if value != 0.2:
            raise ValueError("holdout fraction must be exactly 0.2")
        return value

    @field_validator("whole_work_holdouts")
    @classmethod
    def unique_whole_work_holdouts(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "whole-work holdouts")


class AuthorityTierPolicy(StrictModel):
    tier: Literal[1, 2, 3, 4, 5]
    jurisdiction: NonEmptyText
    analytical_roles: list[NonEmptyText] = Field(default_factory=list)
    evidence_rule: NonEmptyText

    @field_validator("analytical_roles")
    @classmethod
    def unique_roles(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "analytical roles")


class AnalyticalDimension(StrictModel):
    id: DimensionId
    label: NonEmptyText
    roles: list[NonEmptyText] = Field(min_length=1)
    description: NonEmptyText

    @field_validator("roles")
    @classmethod
    def unique_roles(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "dimension roles")


class ExpectedCorpus(StrictModel):
    """Story-local authority for the physical and analytical corpus topology."""

    admission_records: StrictInt = Field(ge=1)
    retained_sources: StrictInt = Field(ge=1)
    retained_epubs: StrictInt = Field(ge=1)
    retained_markdown: StrictInt = Field(ge=1)
    full_work_witnesses: StrictInt = Field(ge=1)
    selected_witnesses: StrictInt = Field(ge=1)
    witness_ids: list[NonEmptyText] = Field(min_length=1)
    excluded_tier5_ids: list[NonEmptyText] = Field(min_length=1)
    whole_work_holdouts: list[NonEmptyText] = Field(min_length=1)

    @field_validator("witness_ids")
    @classmethod
    def unique_witness_ids(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "expected witness IDs")

    @field_validator("excluded_tier5_ids")
    @classmethod
    def unique_excluded_ids(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "expected excluded Tier 5 IDs")

    @field_validator("whole_work_holdouts")
    @classmethod
    def unique_whole_work_ids(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "expected whole-work holdout IDs")

    @model_validator(mode="after")
    def validate_topology(self) -> "ExpectedCorpus":
        if self.retained_sources != self.retained_epubs:
            raise ValueError("retained_sources and retained_epubs counts must agree")
        if self.full_work_witnesses + self.selected_witnesses != self.retained_markdown:
            raise ValueError(
                "full_work_witnesses plus selected_witnesses must equal retained_markdown"
            )
        if len(self.witness_ids) != self.retained_markdown:
            raise ValueError("witness_ids count must equal retained_markdown")
        missing_holdouts = set(self.whole_work_holdouts) - set(self.witness_ids)
        if missing_holdouts:
            raise ValueError(
                "whole-work holdout IDs must be present in witness_ids: "
                + ", ".join(sorted(missing_holdouts))
            )
        return self


class AnalysisConfig(StrictModel):
    schema_version: Literal[1]
    study_id: Slug
    composition_window: StrictCompositionWindow
    study_status: Stage
    admission_registry: RegistryReference
    source_registry: RegistryReference
    authority_policy_version: NonEmptyText
    expected_corpus: ExpectedCorpus
    authority_tiers: list[AuthorityTierPolicy] = Field(min_length=5)
    passage_rules: PassageRules
    partition: PartitionRules
    enabled_measurements: list[NonEmptyText] = Field(min_length=1)
    lexicons: dict[NonEmptyText, list[NonEmptyText]] = Field(default_factory=dict)
    dimensions: list[AnalyticalDimension] = Field(min_length=1)
    confidence_levels: list[Literal["tentative", "moderate", "strong"]] = Field(
        min_length=1
    )
    claim_statuses: list[Literal["candidate", "qualified", "rejected", "validated"]] = Field(
        min_length=1
    )
    claim_classifications: list[
        Literal[
            "wells_distinctive",
            "wells_characteristic_but_shared",
            "role_specific",
            "period_general",
            "unsupported",
        ]
    ] = Field(min_length=1)
    evidence_roles: list[
        Literal["support", "counterexample", "variation", "control", "validation"]
    ] = Field(min_length=1)
    generated_paths: dict[NonEmptyText, RelativePath] = Field(min_length=1)

    @field_validator(
        "enabled_measurements",
        "confidence_levels",
        "claim_statuses",
        "claim_classifications",
        "evidence_roles",
    )
    @classmethod
    def unique_vocabularies(cls, value: list[str], info) -> list[str]:
        return _validate_unique(value, f"{info.field_name} values")

    @field_validator("lexicons")
    @classmethod
    def validate_lexicons(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        for name, terms in value.items():
            if not terms:
                raise ValueError(f"lexicon {name!r} must contain at least one term")
            _validate_unique(_validate_text_list(terms), f"lexicon {name}")
        return value

    @field_validator("generated_paths")
    @classmethod
    def validate_generated_paths(cls, value: dict[str, str]) -> dict[str, str]:
        expected_files = {
            "corpus_lock": "corpus-lock.json",
            "passage_index": "passage-index.jsonl",
            "development_metrics": "development-metrics.json",
            "development_metrics_csv": "development-metrics.csv",
            "development_report": "development-report.md",
            "validation_metrics": "validation-metrics.json",
            "validation_packet": "validation-packet.md",
            "analysis_report": "analysis-report.md",
        }
        if set(value) != set(expected_files):
            raise ValueError(
                "generated paths must declare exactly the known corpus-analysis keys"
            )
        validated: dict[str, str] = {}
        for key, path in value.items():
            path = _validate_generated_path(path)
            filename = expected_files[key]
            if not re.fullmatch(
                rf"build/[a-z0-9]+(?:-[a-z0-9]+)*/source-study/{re.escape(filename)}",
                path,
            ):
                raise ValueError(
                    f"generated path for {key} must be build/<slug>/source-study/{filename}"
                )
            validated[key] = path
        return validated

    @field_validator("authority_tiers")
    @classmethod
    def validate_authority_tiers(
        cls, value: list[AuthorityTierPolicy]
    ) -> list[AuthorityTierPolicy]:
        tier_values = [policy.tier for policy in value]
        _validate_unique(tier_values, "authority tier values")
        if set(tier_values) != {1, 2, 3, 4, 5}:
            raise ValueError(
                "authority tiers must declare exactly one policy for each tier 1, 2, 3, 4, and 5"
            )
        return value

    @model_validator(mode="after")
    def validate_dimensions(self) -> "AnalysisConfig":
        ids = [dimension.id for dimension in self.dimensions]
        _validate_unique(ids, "dimension IDs")
        if len(self.dimensions) != 10:
            raise ValueError("analysis configuration must declare exactly ten dimensions")
        if set(ids) != DIMENSION_IDS:
            raise ValueError("analysis dimensions must use the adopted ten dimension IDs")
        return self


class CorpusAnalysisIdentity(StrictModel):
    study_id: Slug
    story_slug: Slug
    composition_window: StrictCompositionWindow
    authority_policy_version: NonEmptyText


class CorpusSourceFingerprint(StrictModel):
    id: Slug
    tier: Literal[1, 2, 3, 4]
    analytical_roles: list[NonEmptyText] = Field(min_length=1)
    permitted_uses: list[NonEmptyText] = Field(min_length=1)
    prohibited_uses: list[NonEmptyText] = Field(min_length=1)
    epub_path: RelativePath
    epub_sha256: SHA256

    _path = field_validator("epub_path")(_validate_relative_path)


class CorpusWitnessFingerprint(StrictModel):
    witness_id: NonEmptyText
    witness_ordinal: StrictInt = Field(ge=1)
    source_id: Slug
    selection_id: Slug | None = None
    markdown_path: RelativePath
    markdown_sha256: SHA256

    _path = field_validator("markdown_path")(_validate_relative_path)

    @model_validator(mode="after")
    def validate_identity(self) -> "CorpusWitnessFingerprint":
        _validate_selection_identity(self.witness_id, self.source_id, self.selection_id)
        return self


class CorpusCounts(StrictModel):
    admission_records: StrictInt = Field(ge=0)
    retained_sources: StrictInt = Field(ge=0)
    retained_epubs: StrictInt = Field(ge=0)
    retained_markdown: StrictInt = Field(ge=0)
    full_work_witnesses: StrictInt = Field(ge=0)
    selected_short_fiction_witnesses: StrictInt = Field(ge=0)
    witnesses: StrictInt = Field(ge=0)
    excluded_tier5_records: StrictInt = Field(ge=0)


class CorpusLock(StrictModel):
    schema_version: Literal[1]
    analysis: CorpusAnalysisIdentity
    registry_hashes: dict[RelativePath, SHA256] = Field(min_length=2)
    sources: list[CorpusSourceFingerprint] = Field(min_length=1)
    witnesses: list[CorpusWitnessFingerprint] = Field(min_length=1)
    excluded_tier5_ids: list[NonEmptyText] = Field(min_length=1)
    counts: CorpusCounts

    @field_validator("registry_hashes")
    @classmethod
    def validate_registry_paths(cls, value: dict[str, str]) -> dict[str, str]:
        return {_validate_relative_path(path): digest for path, digest in value.items()}

    @field_validator("excluded_tier5_ids")
    @classmethod
    def unique_excluded_ids(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "excluded Tier 5 IDs")

    @field_validator("sources")
    @classmethod
    def unique_source_ids(cls, value: list[CorpusSourceFingerprint]) -> list[CorpusSourceFingerprint]:
        _validate_unique([item.id for item in value], "corpus source IDs")
        return value

    @field_validator("witnesses")
    @classmethod
    def unique_witness_ids(cls, value: list[CorpusWitnessFingerprint]) -> list[CorpusWitnessFingerprint]:
        _validate_unique([item.witness_id for item in value], "corpus witness IDs")
        ordinals = [item.witness_ordinal for item in value]
        if ordinals != list(range(1, len(ordinals) + 1)):
            raise ValueError("corpus witness ordinals must be contiguous from 1")
        return value


class PassageRecord(StrictModel):
    witness_id: NonEmptyText
    witness_ordinal: StrictInt = Field(ge=1)
    source_id: NonEmptyText
    selection_id: Slug | None = None
    source_fingerprint: SHA256
    heading_path: list[NonEmptyText] = Field(min_length=1)
    heading_label: NonEmptyText
    block_type: Literal["paragraph", "block_quote", "verse", "list_item"]
    source_ordinal: StrictInt = Field(ge=1)
    heading_ordinal: StrictInt = Field(ge=1)
    normalized_text: NonEmptyText
    original_text: NonEmptyText
    word_count: StrictInt = Field(ge=1)
    direct_dialogue: Literal["direct", "none", "mixed", "unknown"]
    content_hash: SHA256
    passage_id: NonEmptyText

    @model_validator(mode="after")
    def validate_identity_and_id(self) -> "PassageRecord":
        _validate_selection_identity(self.witness_id, self.source_id, self.selection_id)
        if self.heading_label != self.heading_path[-1]:
            raise ValueError("heading_label must equal the final heading_path label")
        expected_hash = hashlib.sha256(self.normalized_text.encode("utf-8")).hexdigest()
        if self.content_hash != expected_hash:
            raise ValueError("content_hash must be the SHA-256 hash of normalized_text")
        expected_word_count = len(re.findall(r"\S+", self.normalized_text))
        if self.word_count != expected_word_count:
            raise ValueError("word_count must match normalized_text")
        expected = (
            f"{self.witness_id}:{_heading_slug(self.heading_label)}:"
            f"{self.source_ordinal}:{expected_hash[:12]}"
        )
        if self.passage_id != expected:
            raise ValueError(f"passage ID must be {expected}")
        return self


class HoldoutWindow(StrictModel):
    id: Slug
    passage_ids: list[NonEmptyText] = Field(min_length=1)

    @field_validator("passage_ids")
    @classmethod
    def unique_passages(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "window passage IDs")


class WitnessHoldouts(StrictModel):
    witness_id: NonEmptyText
    development_windows: list[HoldoutWindow] = Field(default_factory=list)
    holdout_windows: list[HoldoutWindow] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_window_partition(self) -> "WitnessHoldouts":
        window_ids = [window.id for window in [*self.development_windows, *self.holdout_windows]]
        _validate_unique(window_ids, "window IDs")
        development = {
            passage_id
            for window in self.development_windows
            for passage_id in window.passage_ids
        }
        holdout = {
            passage_id
            for window in self.holdout_windows
            for passage_id in window.passage_ids
        }
        if development & holdout:
            raise ValueError("development and holdout windows must not overlap")
        return self


class HoldoutManifest(StrictModel):
    schema_version: Literal[1]
    partition_seed: NonEmptyText
    algorithm_version: NonEmptyText
    tool_version: NonEmptyText
    created_at: datetime
    registry_hashes: dict[RelativePath, SHA256] = Field(min_length=1)
    source_fingerprints: dict[NonEmptyText, SHA256] = Field(min_length=1)
    whole_work_holdouts: list[NonEmptyText] = Field(min_length=1)
    witnesses: list[WitnessHoldouts] = Field(min_length=1)

    @field_validator("created_at")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware UTC")
        if value.utcoffset() != timedelta(0):
            raise ValueError("created_at must use UTC offset zero")
        return value

    @field_validator("registry_hashes")
    @classmethod
    def validate_registry_paths(cls, value: dict[str, str]) -> dict[str, str]:
        return {_validate_relative_path(path): digest for path, digest in value.items()}

    @field_validator("whole_work_holdouts")
    @classmethod
    def unique_whole_work_holdouts(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "whole-work holdouts")

    @field_validator("witnesses")
    @classmethod
    def unique_witnesses(cls, value: list[WitnessHoldouts]) -> list[WitnessHoldouts]:
        _validate_unique([item.witness_id for item in value], "witness IDs")
        return value

    @model_validator(mode="after")
    def validate_whole_work_topology(self) -> "HoldoutManifest":
        declared_whole_work = set(self.whole_work_holdouts)
        witness_ids = {witness.witness_id for witness in self.witnesses}
        missing_witnesses = declared_whole_work - witness_ids
        if missing_witnesses:
            missing = ", ".join(sorted(missing_witnesses))
            raise ValueError(f"whole-work holdouts must be represented by witnesses: {missing}")

        for witness in self.witnesses:
            if witness.witness_id in declared_whole_work:
                if witness.development_windows:
                    raise ValueError(
                        "whole-work witnesses must not have development windows"
                    )
            elif not witness.development_windows:
                raise ValueError(
                    "non-whole-work witnesses require development windows"
                )
        return self


MetricValue = StrictInt | StrictFloat | StrictBool | StrictStr | None


class MetricDistribution(StrictModel):
    """Standard-library distribution summary emitted by source metrics."""

    count: StrictInt = Field(ge=0)
    minimum: StrictInt | StrictFloat | None
    p10: StrictInt | StrictFloat | None
    p25: StrictInt | StrictFloat | None
    median: StrictInt | StrictFloat | None
    p75: StrictInt | StrictFloat | None
    p90: StrictInt | StrictFloat | None
    maximum: StrictInt | StrictFloat | None
    mean: StrictInt | StrictFloat | None


class MetricCandidateFlag(StrictModel):
    """A within-witness sampling aid, never an interpretive finding."""

    kind: NonEmptyText
    metric: NonEmptyText
    value: StrictInt | StrictFloat
    reason: NonEmptyText
    passage_id: NonEmptyText
    section_id: NonEmptyText
    sampling_aid: StrictBool = True
    interpretive_finding: StrictBool = False


class MetricReference(StrictModel):
    id: Slug
    path: RelativePath
    sha256: SHA256

    _path = field_validator("path")(_validate_relative_path)


class WitnessQuantitativeProfile(StrictModel):
    witness_id: NonEmptyText
    source_id: NonEmptyText
    selection_id: Slug | None = None
    values: dict[NonEmptyText, MetricValue]
    variation: NonEmptyText
    limitations: NonEmptyText
    interpretive_relevance: NonEmptyText

    @model_validator(mode="after")
    def validate_identity(self) -> "WitnessQuantitativeProfile":
        _validate_selection_identity(self.witness_id, self.source_id, self.selection_id)
        return self


class QuantitativeProfile(StrictModel):
    schema_version: Literal[1]
    study_id: Slug
    stage: Stage
    generated_metrics: list[MetricReference] = Field(default_factory=list)
    witnesses: list[WitnessQuantitativeProfile] = Field(default_factory=list)

    @field_validator("witnesses")
    @classmethod
    def unique_witnesses(cls, value: list[WitnessQuantitativeProfile]) -> list[WitnessQuantitativeProfile]:
        _validate_unique([item.witness_id for item in value], "witness IDs")
        return value


class EvidenceReference(StrictModel):
    witness_id: NonEmptyText
    source_id: NonEmptyText
    selection_id: Slug | None = None
    passage_id: NonEmptyText
    authority_tier: Literal[1, 2, 3, 4]
    evidence_role: Literal["support", "counterexample", "variation", "control", "validation"]
    relevance_note: NonEmptyText

    @model_validator(mode="after")
    def validate_identity_and_role(self) -> "EvidenceReference":
        _validate_selection_identity(self.witness_id, self.source_id, self.selection_id)
        if self.authority_tier == 4 and self.evidence_role != "control":
            raise ValueError("Tier 4 evidence may use only the control role")
        if self.evidence_role == "control" and self.authority_tier != 4:
            raise ValueError("control evidence must come from Tier 4")
        return self


class ClaimJurisdiction(StrictModel):
    """The declared scope and source-role boundary of one evidence claim."""

    scope: Literal["cross_work", "source_specific", "role_specific", "continuity"]
    roles: list[NonEmptyText] = Field(min_length=1)
    eligible_witness_ids: list[NonEmptyText] = Field(min_length=1)

    @field_validator("roles", "eligible_witness_ids")
    @classmethod
    def unique_members(cls, value: list[str], info) -> list[str]:
        return _validate_unique(value, f"{info.field_name}")


class CounterexampleSearch(StrictModel):
    """A reproducible close-reading search used when no material variation is cited."""

    witness_ids: list[NonEmptyText] = Field(min_length=1)
    dimensions: list[DimensionId] = Field(min_length=1)
    method: Literal[
        "manual_close_reading",
        "metric_guided_close_reading",
        "exhaustive_close_reading",
    ]
    coverage: Literal["targeted", "all_eligible_passages"]
    searched_passage_ids: list[NonEmptyText] = Field(min_length=1)
    outcome: Literal["no_material_counterexample", "material_counterexample_found"]
    notes: NonEmptyText

    @field_validator("witness_ids", "dimensions", "searched_passage_ids")
    @classmethod
    def unique_members(cls, value: list[str], info) -> list[str]:
        return _validate_unique(value, f"{info.field_name}")


class EvidenceClaim(StrictModel):
    id: Slug
    dimension: DimensionId
    statement: NonEmptyText
    mode: Literal["descriptive"] = "descriptive"
    jurisdiction: ClaimJurisdiction
    classification: Literal[
        "wells_distinctive",
        "wells_characteristic_but_shared",
        "role_specific",
        "period_general",
        "unsupported",
    ]
    status: Literal["candidate", "qualified", "rejected", "validated"]
    confidence: Literal["tentative", "moderate", "strong"]
    supporting_passages: list[EvidenceReference] = Field(default_factory=list)
    counterexample_passages: list[EvidenceReference] = Field(default_factory=list)
    counterexample_search: CounterexampleSearch | None = None
    control_results: list[NonEmptyText] = Field(default_factory=list)
    scope_and_limits: NonEmptyText
    validation_expectation: NonEmptyText
    prohibited_overgeneralisation: NonEmptyText
    notes: NonEmptyText

    @model_validator(mode="after")
    def validate_evidence_completeness(self) -> "EvidenceClaim":
        if self.status != "rejected" and not self.supporting_passages:
            raise ValueError("non-rejected claims require supporting passages")
        if self.status != "rejected" and not (
            self.counterexample_passages or self.counterexample_search
        ):
            raise ValueError(
                "non-rejected claims require counterexample passages or a counterexample search"
            )
        return self


class EvidenceLedger(StrictModel):
    schema_version: Literal[1]
    study_id: Slug
    stage: Stage
    mode: Literal["descriptive"]
    claims: list[EvidenceClaim] = Field(default_factory=list)

    @field_validator("claims")
    @classmethod
    def unique_claims(cls, value: list[EvidenceClaim]) -> list[EvidenceClaim]:
        _validate_unique([claim.id for claim in value], "claim IDs")
        return value

    @model_validator(mode="after")
    def validate_stage_claims(self) -> "EvidenceLedger":
        if self.stage != "validated":
            for claim in self.claims:
                if claim.status == "validated" or claim.confidence == "strong":
                    raise ValueError(
                        "validated status and strong confidence require the validation stage"
                    )
        return self


class ClaimTransition(StrictModel):
    claim_id: Slug
    from_status: Literal["candidate", "qualified", "rejected", "validated"]
    to_status: Literal["candidate", "qualified", "rejected", "validated"]
    reason: NonEmptyText


class ValidationRecord(StrictModel):
    schema_version: Literal[1]
    study_id: Slug
    stage: Stage
    candidate_commit: GitHash | None = None
    candidate_profile_sha256: SHA256 | None = None
    candidate_ledger_sha256: SHA256 | None = None
    holdout_summary: NonEmptyText
    control_summary: NonEmptyText
    reviewer_summary: NonEmptyText
    claim_transitions: list[ClaimTransition] = Field(default_factory=list)
    unresolved_uncertainty: NonEmptyText
    final_profile_sha256: SHA256 | None = None

    @model_validator(mode="after")
    def validate_stage_hashes(self) -> "ValidationRecord":
        if self.stage != "validated" and self.final_profile_sha256 is not None:
            raise ValueError("final profile hash must be absent before validation")

        if self.stage == "protocol":
            if any(
                value is not None
                for value in (
                    self.candidate_commit,
                    self.candidate_profile_sha256,
                    self.candidate_ledger_sha256,
                    self.final_profile_sha256,
                )
            ):
                raise ValueError("protocol validation records cannot contain freeze hashes")
        elif self.stage in {"candidate_frozen", "validated"} and not (
            self.candidate_commit
            and self.candidate_profile_sha256
            and self.candidate_ledger_sha256
        ):
            raise ValueError("candidate freeze hashes are required after protocol stage")
        if self.stage == "validated" and not self.final_profile_sha256:
            raise ValueError("final profile hash is required at the validation stage")
        return self


def parse_validation_document(
    text: str, path: Path | str = Path("validation.md")
) -> tuple[ValidationRecord, str]:
    """Parse strict ValidationRecord front matter and return its Markdown body."""

    display_path = str(path)
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise CreativeWriterError(f"{display_path} must start with YAML front matter.")

    closing_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break
    if closing_index is None:
        raise CreativeWriterError(f"{display_path} is missing the closing front matter fence.")

    try:
        raw = yaml.safe_load("".join(lines[1:closing_index]))
    except yaml.YAMLError as exc:
        raise CreativeWriterError(f"Invalid YAML front matter in {display_path}: {exc}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise CreativeWriterError(f"Front matter in {display_path} must parse to a mapping.")
    try:
        record = ValidationRecord.model_validate(raw)
    except ValidationError as exc:
        raise CreativeWriterError(
            f"ValidationRecord front matter validation failed for {display_path}:\n{exc}"
        ) from exc

    body = "".join(lines[closing_index + 1 :]).lstrip("\n")
    if not body.strip():
        raise CreativeWriterError(f"{display_path} must contain a Markdown body.")
    return record, body


def load_validation_document(path: Path) -> tuple[ValidationRecord, str]:
    """Read and parse a tracked validation Markdown document."""

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CreativeWriterError(f"Unable to read validation document {path}: {exc}") from exc
    return parse_validation_document(text, path)
