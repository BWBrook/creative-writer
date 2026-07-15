"""Strict schemas for the Phase 2B source-analysis evidence layer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Annotated, Literal

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
from creative_writer.models import CompositionWindow


Slug = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
SHA256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
GitHash = Annotated[str, Field(pattern=r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")]
NonEmptyText = Annotated[str, Field(min_length=1, pattern=r"(?s).*\S.*")]
RelativePath = Annotated[str, Field(min_length=1, pattern=r"^[^/].*")]
Stage = Literal["protocol", "development", "candidate_frozen", "validated"]

DIMENSION_IDS = {
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
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _validate_relative_path(value: str) -> str:
    if "\\" in value:
        raise ValueError("paths must use canonical relative POSIX syntax")
    parts = value.split("/")
    if not value or value.startswith("/") or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("path must be a non-empty canonical relative POSIX path")
    return value


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
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return slug or "untitled"


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
    context_radius: int = Field(ge=0, le=2)

    @field_validator("substantive_block_types")
    @classmethod
    def unique_block_types(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "substantive block types")


class PartitionRules(StrictModel):
    seed: NonEmptyText
    algorithm_version: NonEmptyText
    holdout_fraction: float
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
    analytical_roles: list[NonEmptyText] = Field(min_length=1)
    evidence_rule: NonEmptyText

    @field_validator("analytical_roles")
    @classmethod
    def unique_roles(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "analytical roles")


class AnalyticalDimension(StrictModel):
    id: Slug
    label: NonEmptyText
    roles: list[NonEmptyText] = Field(min_length=1)
    description: NonEmptyText

    @field_validator("roles")
    @classmethod
    def unique_roles(cls, value: list[str]) -> list[str]:
        return _validate_unique(value, "dimension roles")


class AnalysisConfig(StrictModel):
    schema_version: Literal[1]
    study_id: Slug
    composition_window: CompositionWindow
    study_status: Stage
    admission_registry: RegistryReference
    source_registry: RegistryReference
    authority_policy_version: NonEmptyText
    authority_tiers: list[AuthorityTierPolicy] = Field(default_factory=list)
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
        return {key: _validate_relative_path(path) for key, path in value.items()}

    @model_validator(mode="after")
    def validate_dimensions(self) -> "AnalysisConfig":
        ids = [dimension.id for dimension in self.dimensions]
        _validate_unique(ids, "dimension IDs")
        if len(self.dimensions) != 10:
            raise ValueError("analysis configuration must declare exactly ten dimensions")
        if set(ids) != DIMENSION_IDS:
            raise ValueError("analysis dimensions must use the adopted ten dimension IDs")
        return self


class PassageRecord(StrictModel):
    witness_id: NonEmptyText
    source_id: NonEmptyText
    selection_id: Slug | None = None
    source_fingerprint: SHA256
    heading_path: list[NonEmptyText] = Field(min_length=1)
    heading_label: NonEmptyText
    block_type: Literal["paragraph", "block_quote", "verse", "list_item"]
    source_ordinal: int = Field(ge=1)
    heading_ordinal: int = Field(ge=1)
    normalized_text: NonEmptyText
    original_text: NonEmptyText
    word_count: int = Field(ge=1)
    direct_dialogue: Literal["direct", "none", "mixed", "unknown"]
    content_hash: SHA256
    passage_id: NonEmptyText

    @model_validator(mode="after")
    def validate_identity_and_id(self) -> "PassageRecord":
        _validate_selection_identity(self.witness_id, self.source_id, self.selection_id)
        expected = (
            f"{self.witness_id}:{_heading_slug(self.heading_label)}:"
            f"{self.source_ordinal}:{self.content_hash[:12]}"
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
    development_windows: list[HoldoutWindow] = Field(min_length=1)
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


MetricValue = StrictInt | StrictFloat | StrictBool | StrictStr | None


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


class EvidenceClaim(StrictModel):
    id: Slug
    dimension: Slug
    statement: NonEmptyText
    mode: Literal["descriptive"] = "descriptive"
    jurisdiction: NonEmptyText
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
    counterexample_search: NonEmptyText | None = None
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
        elif not (
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
