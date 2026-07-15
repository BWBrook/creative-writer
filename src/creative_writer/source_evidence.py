"""Strict, source-linked validation for the Phase 2B evidence surface.

This module validates human-authored Markdown and YAML artifacts.  It does not
author observations, claims, or profile findings.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from json import JSONDecodeError
from pathlib import Path
from typing import Iterable, Sequence

from pydantic import ValidationError
import yaml

from creative_writer.exceptions import CreativeWriterError
from creative_writer.models import SourceStudyAdmission, SourcesRegistry
from creative_writer.source_analysis_models import (
    AnalysisConfig,
    ControlComparison,
    EvidenceClaim,
    EvidenceLedger,
    GeneratedDevelopmentMetrics,
    PassageRecord,
    QuantitativeProfile,
    WitnessQuantitativeProfile,
    WitnessMetricRecord,
)


PROTOCOL_OBSERVATION_SENTINEL = "No reviewed observations are recorded at protocol status."
PROTOCOL_PROFILE_SENTINEL = "No reviewed descriptive synthesis is recorded at protocol status."
# Exact normalized passage sequences shorter than this are too likely to be
# ordinary Victorian phrasing to identify copied source prose mechanically.
# Partial or edited copies remain a human-review risk.
FORBIDDEN_TEXT_MIN_TOKENS = 8
_TOKEN_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)
_PLACEHOLDER_RE = re.compile(r"\b(?:tbd|todo|placeholder|no reviewed|reserved for)\b", re.I)
class DuplicateJSONKeyError(ValueError):
    """Raised when a JSON object repeats a key at any nesting level."""


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise DuplicateJSONKeyError(f"duplicate key: {key}")
        document[key] = value
    return document


def _json_values_equal_exact(actual: object, expected: object) -> bool:
    """Compare JSON values without Python's bool/int equality coercion."""

    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        if actual.keys() != expected.keys():
            return False
        return all(
            _json_values_equal_exact(actual[key], expected[key])
            for key in actual
        )
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(
            _json_values_equal_exact(item, expected_item)
            for item, expected_item in zip(actual, expected)
        )
    return actual == expected


def _normalized_heading(line: str) -> str:
    """Normalize only Markdown ATX trailing spaces for semantic matching."""

    return line.rstrip(" \t")


def _heading_match(line: str, pattern: re.Pattern[str]) -> re.Match[str] | None:
    return pattern.fullmatch(_normalized_heading(line))


def _is_atx_heading(line: str) -> bool:
    return bool(re.match(r"^#{1,6} ", _normalized_heading(line)))


def _noncanonical_heading(line: str) -> bool:
    return _is_atx_heading(line) and line != _normalized_heading(line)


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    severity: str
    file: str
    claim: str = ""
    locator: str = ""
    message: str = ""

    def sort_key(self) -> tuple[str, str, str, str, str]:
        return (self.severity, self.file, self.claim, self.locator, self.message)


@dataclass(slots=True)
class ValidationResult:
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def sorted(self) -> "ValidationResult":
        self.errors.sort(key=lambda issue: issue.sort_key())
        self.warnings.sort(key=lambda issue: issue.sort_key())
        return self

    def extend(self, other: "ValidationResult") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


def _display(path: Path | str | None) -> str:
    return str(path) if path is not None else "<evidence>"


def _error(
    file: Path | str | None,
    message: str,
    *,
    claim: str = "",
    locator: str = "",
) -> ValidationIssue:
    return ValidationIssue("error", _display(file), claim, locator, message)


def _warning(
    file: Path | str | None,
    message: str,
    *,
    claim: str = "",
    locator: str = "",
) -> ValidationIssue:
    return ValidationIssue("warning", _display(file), claim, locator, message)


def raise_for_issues(result: ValidationResult, label: str = "Evidence validation") -> ValidationResult:
    result.sorted()
    if result.errors:
        lines = [f"{label} failed with {len(result.errors)} error(s):"]
        for issue in result.errors:
            location = f"file={issue.file}"
            if issue.claim:
                location += f" claim={issue.claim}"
            if issue.locator:
                location += f" locator={issue.locator}"
            lines.append(f"- {location}: {issue.message}")
        if result.warnings:
            lines.append(f"Warnings: {len(result.warnings)}")
        raise CreativeWriterError("\n".join(lines))
    return result


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CreativeWriterError(f"Unable to read evidence file {path}: {exc}") from exc


def _canonical_root_path(root: Path, path: Path) -> Path:
    candidate = path if path.is_absolute() else root / path
    return candidate.resolve(strict=False)


def _profile_identity_tuple(item: WitnessQuantitativeProfile) -> tuple[str, str, str | None]:
    return (
        item.witness_id,
        item.source_id,
        item.selection_id,
    )


def _passage_maps(passages: Sequence[PassageRecord]) -> tuple[dict[str, PassageRecord], dict[str, list[PassageRecord]]]:
    by_id: dict[str, PassageRecord] = {}
    by_witness: dict[str, list[PassageRecord]] = {}
    for passage in passages:
        if passage.passage_id in by_id:
            raise CreativeWriterError(f"Duplicate verified passage ID `{passage.passage_id}`")
        by_id[passage.passage_id] = passage
        by_witness.setdefault(passage.witness_id, []).append(passage)
    for witness_passages in by_witness.values():
        witness_passages.sort(key=lambda item: item.source_ordinal)
    return by_id, by_witness


def _manifest_ids(manifest: object | None) -> tuple[set[str], set[str]]:
    if manifest is None:
        return set(), set()
    development: set[str] = set()
    holdout: set[str] = set()
    for witness in getattr(manifest, "witnesses", []):
        for window in getattr(witness, "development_windows", []):
            development.update(window.passage_ids)
        for window in getattr(witness, "holdout_windows", []):
            holdout.update(window.passage_ids)
    return development, holdout


def _accessible_ids(
    passages: Sequence[PassageRecord],
    *,
    stage: str,
    development_passage_ids: set[str] | None = None,
    manifest: object | None = None,
) -> tuple[set[str], set[str]]:
    all_ids = {passage.passage_id for passage in passages}
    manifest_development, manifest_holdout = _manifest_ids(manifest)
    if development_passage_ids is not None:
        development = set(development_passage_ids)
    elif manifest_development:
        development = manifest_development
    else:
        development = all_ids
    if stage == "development":
        return development & all_ids, manifest_holdout & all_ids
    return all_ids, manifest_holdout & all_ids


def _content_is_human(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped) and not _PLACEHOLDER_RE.search(stripped)


def _extract_section(text: str, heading: str) -> str | None:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if _normalized_heading(line) == heading), None)
    if start is None:
        return None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if _normalized_heading(lines[i]).startswith("## "):
            end = i
            break
    return "\n".join(lines[start + 1 : end]).strip()


def _entry_blocks(section: str, heading_re: re.Pattern[str]) -> list[tuple[int, str, str]]:
    lines = section.splitlines()
    matches = [
        (i, match)
        for i, line in enumerate(lines)
        if (match := _heading_match(line, heading_re)) is not None
    ]
    blocks: list[tuple[int, str, str]] = []
    for index, (line_number, match) in enumerate(matches):
        end = matches[index + 1][0] if index + 1 < len(matches) else len(lines)
        blocks.append((line_number, match.group(1), "\n".join(lines[line_number + 1 : end]).strip()))
    return blocks


def _nonblank_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _parse_locator_bullet(content: str) -> str | None:
    lines = _nonblank_lines(content)
    if len(lines) != 1:
        return None
    match = re.fullmatch(r"- `([^`]+)`", lines[0])
    return match.group(1) if match else None


def _parse_comparison(content: str) -> list[str] | None:
    lines = _nonblank_lines(content)
    if len(lines) == 1 and re.fullmatch(r"None - .+", lines[0]):
        return []
    locators: list[str] = []
    for line in lines:
        match = re.fullmatch(r"- (?:related|contrary|variation): `([^`]+)`(?: - | — ).+", line)
        if not match:
            return None
        locators.append(match.group(1))
    return locators if locators else None


def _parse_candidate_claims(content: str) -> list[str] | None:
    lines = _nonblank_lines(content)
    if lines == ["None."]:
        return []
    claims: list[str] = []
    for line in lines:
        match = re.fullmatch(r"- `([^`]+)`", line)
        if not match:
            return None
        claims.append(match.group(1))
    return claims if claims else None


_ALLOWED_CONTROL_WITNESS_PATH = re.compile(
    r"^claims\[\d+\]\.validation_expectation\.control_targets\[\d+\]\.witness_id$"
)


def _yaml_scalar_occurrences(text: str) -> list[tuple[str, str]]:
    """Return every composed YAML scalar and its document path."""

    root = yaml.compose(text)
    if root is None:
        return []
    occurrences: list[tuple[str, str]] = []

    def visit(node: object, path: str) -> None:
        node_id = getattr(node, "id", None)
        if node_id == "scalar":
            value = getattr(node, "value", None)
            if isinstance(value, str):
                occurrences.append((path, value))
            return
        if node_id == "sequence":
            for index, child in enumerate(getattr(node, "value", [])):
                visit(child, f"{path}[{index}]")
            return
        if node_id == "mapping":
            for key_node, value_node in getattr(node, "value", []):
                key = getattr(key_node, "value", None)
                key_path = f"{path}.{key}" if path else str(key)
                visit(key_node, f"{path}.<key>" if path else "<key>")
                visit(value_node, key_path)

    visit(root, "")
    return occurrences


def _observation_entry_issues(
    path: Path,
    number: int,
    content: str,
    passages_by_id: dict[str, PassageRecord],
    config: AnalysisConfig,
    accessible_ids: set[str],
    claim_ids: set[str] | None,
    authorities: dict[str, _WitnessAuthority],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    expected = [
        "Passage",
        "Observation",
        "Inference",
        "Jurisdiction",
        "Comparison",
        "Limitation",
        "Candidate claims",
    ]
    blocks = _entry_blocks(content, re.compile(r"^#### (.+)$"))
    for line in content.splitlines():
        if _heading_match(line, re.compile(r"^#### .+$")) and _noncanonical_heading(line):
            issues.append(_error(path, "Canonical heading spelling is required without trailing whitespace", locator=f"Observation {number}"))
    first_field_line = next(
        (index for index, line in enumerate(content.splitlines()) if _heading_match(line, re.compile(r"^#### .+$"))),
        None,
    )
    if first_field_line is not None and any(
        line.strip() for line in content.splitlines()[:first_field_line]
    ):
        issues.append(_error(path, "Observation entries may not have stray prose before the first expected field", locator=f"Observation {number}"))
    if any(
        re.match(r"^#{4,} ", _normalized_heading(line)) and not _heading_match(line, re.compile(r"^#### .+"))
        for line in content.splitlines()
    ):
        issues.append(_error(path, "Observation entry contains an unrecognised heading", locator=f"Observation {number}"))
    actual = [name for _, name, _ in blocks]
    if actual != expected:
        issues.append(_error(path, f"Observation {number} fields must be exactly ordered as {expected}"))
        return issues
    values = {name: value for _, name, value in blocks}
    focal_id = _parse_locator_bullet(values["Passage"])
    if focal_id is None:
        issues.append(_error(path, "Passage must contain exactly one bullet locator", locator=f"Observation {number}"))
    elif focal_id not in passages_by_id:
        issues.append(_error(path, "Unknown or stale passage locator", locator=focal_id))
    elif focal_id not in accessible_ids:
        issues.append(_error(path, "Development observation cannot cite a held-out or inaccessible passage", locator=focal_id))
    else:
        passage = passages_by_id[focal_id]
        if path.stem != passage.source_id:
            issues.append(_error(path, "Observation file stem must equal focal passage source_id", locator=focal_id))
    for field_name in ("Observation", "Inference", "Limitation"):
        if not _content_is_human(values[field_name]):
            issues.append(_error(path, f"{field_name} must contain non-placeholder human-authored prose", locator=f"Observation {number}"))

    jurisdiction_lines = _nonblank_lines(values["Jurisdiction"])
    dimension_id: str | None = None
    declared_role: str | None = None
    if len(jurisdiction_lines) != 2:
        issues.append(_error(path, "Jurisdiction must contain exactly Dimension and Role bullets", locator=f"Observation {number}"))
    else:
        dimension_match = re.fullmatch(r"- Dimension: `([^`]+)`", jurisdiction_lines[0])
        role_match = re.fullmatch(r"- Role: `([^`]+)`", jurisdiction_lines[1])
        if not dimension_match or not role_match:
            issues.append(_error(path, "Jurisdiction bullets must be exactly Dimension then Role", locator=f"Observation {number}"))
        else:
            dimension_id, declared_role = dimension_match.group(1), role_match.group(1)
            dimension = next((item for item in config.dimensions if item.id == dimension_id), None)
            if dimension is None:
                issues.append(_error(path, "Unknown configured dimension", locator=dimension_id))
            elif declared_role not in dimension.roles:
                issues.append(_error(path, "Jurisdiction role is not configured for the dimension", locator=declared_role))
            elif focal_id in passages_by_id:
                focal_authority = authorities.get(passages_by_id[focal_id].witness_id)
                if focal_authority is None or declared_role not in focal_authority.roles:
                    issues.append(_error(path, "Focal witness does not exercise the declared jurisdiction role", locator=focal_id))

    comparisons = _parse_comparison(values["Comparison"])
    if comparisons is None:
        issues.append(_error(path, "Comparison must use related/contrary/variation locator bullets or ASCII None - <reason>", locator=f"Observation {number}"))
    else:
        for locator in comparisons:
            if locator not in passages_by_id:
                issues.append(_error(path, "Unknown or stale comparison locator", locator=locator))
            elif locator not in accessible_ids:
                issues.append(_error(path, "Development comparison cannot cite a held-out or inaccessible passage", locator=locator))
            elif dimension_id is not None:
                dimension = next((item for item in config.dimensions if item.id == dimension_id), None)
                comparison_authority = authorities.get(passages_by_id[locator].witness_id)
                if dimension is not None and declared_role is not None and (
                    comparison_authority is None
                    or declared_role not in comparison_authority.roles
                ):
                    issues.append(_error(path, "Comparison witness does not exercise the declared jurisdiction role", locator=locator))
    claims = _parse_candidate_claims(values["Candidate claims"])
    if claims is None:
        issues.append(_error(path, "Candidate claims must contain claim-ID bullets or exact None.", locator=f"Observation {number}"))
    elif claim_ids is not None:
        for claim_id in claims:
            if claim_id not in claim_ids:
                issues.append(_error(path, "Unknown candidate claim ID", claim=claim_id, locator=f"Observation {number}"))
    return issues


def collect_observation_issues(
    paths: Sequence[Path],
    passages: Sequence[PassageRecord],
    config: AnalysisConfig,
    *,
    stage: str = "development",
    development_passage_ids: set[str] | None = None,
    manifest: object | None = None,
    claim_ids: set[str] | None = None,
    admission: SourceStudyAdmission | None = None,
    registry: SourcesRegistry | None = None,
) -> ValidationResult:
    """Collect all observation grammar, locator, and development leakage issues."""

    result = ValidationResult()
    by_id, _ = _passage_maps(passages)
    authorities = _authority_index(passages, admission, registry)
    accessible, _ = _accessible_ids(
        passages,
        stage=stage,
        development_passage_ids=development_passage_ids,
        manifest=manifest,
    )
    for path in sorted(paths, key=lambda item: item.as_posix()):
        text = _read(path)
        observation_headings = [
            line for line in text.splitlines()
            if _normalized_heading(line) == "## Observations"
        ]
        if len(observation_headings) > 1:
            result.errors.append(_error(path, "Tracked dossier must contain exactly one ## Observations section"))
        if any(_noncanonical_heading(line) for line in observation_headings):
            result.errors.append(_error(path, "Canonical heading spelling is required without trailing whitespace in the Observations section"))
        section = _extract_section(text, "## Observations")
        if section is None:
            result.errors.append(_error(path, "Missing exact ## Observations section"))
            continue
        entries = _entry_blocks(section, re.compile(r"^### Observation (\d+)$"))
        if any(
            _heading_match(line, re.compile(r"^### Observation \d+$")) and _noncanonical_heading(line)
            for line in section.splitlines()
        ):
            result.errors.append(_error(path, "Canonical heading spelling is required without trailing whitespace in observation entries"))
        if not entries:
            if section.strip() != PROTOCOL_OBSERVATION_SENTINEL:
                result.errors.append(_error(path, "Observations must be the exact protocol sentinel or contiguous ### Observation N entries"))
            continue
        first_entry_line = entries[0][0]
        if any(line.strip() for line in section.splitlines()[:first_entry_line]):
            result.errors.append(_error(path, "Observation entries may not have unstructured prose before the first entry"))
        if admission is None or registry is None:
            result.errors.append(_error(path, "Populated observation dossiers require admission and source registry authority"))
        if any(
            _normalized_heading(line).startswith("### ") and not _heading_match(line, re.compile(r"^### Observation \d+$"))
            for line in section.splitlines()
        ):
            result.errors.append(_error(path, "Observation section contains an unrecognised third-level heading"))
        numbers = [int(name) for _, name, _ in entries]
        if numbers != list(range(1, len(numbers) + 1)):
            result.errors.append(_error(path, "Observation ordinals must be contiguous from 1"))
        for _, number, content in entries:
            result.errors.extend(
                _observation_entry_issues(
                    path,
                    int(number),
                    content,
                    by_id,
                    config,
                    accessible,
                    claim_ids,
                    authorities,
                )
            )
    return result.sorted()


def validate_observation_dossiers(*args, **kwargs) -> ValidationResult:
    """Validate tracked observation dossiers and raise one aggregate diagnostic."""

    result = collect_observation_issues(*args, **kwargs)
    return raise_for_issues(result, "Observation dossier validation")


@dataclass(frozen=True, slots=True)
class _WitnessAuthority:
    witness_id: str
    source_id: str
    selection_id: str | None
    tier: int | None
    roles: frozenset[str]
    fingerprint: str | None


def _authority_index(
    passages: Sequence[PassageRecord],
    admission: SourceStudyAdmission | None,
    registry: SourcesRegistry | None,
) -> dict[str, _WitnessAuthority]:
    admission_by_source = {source.id: source for source in admission.sources} if admission else {}
    result: dict[str, _WitnessAuthority] = {}
    if registry is None:
        return result
    for retained in registry.sources:
        base_roles = set(retained.role.analytical_roles)
        if retained.files.markdown is not None:
            result[retained.id] = _WitnessAuthority(
                retained.id,
                retained.id,
                None,
                retained.role.tier,
                frozenset(base_roles),
                retained.files.markdown_sha256,
            )
        else:
            for selection in retained.selections:
                witness_id = f"{retained.id}/{selection.id}"
                result[witness_id] = _WitnessAuthority(
                    witness_id,
                    retained.id,
                    selection.id,
                    retained.role.tier,
                    frozenset(base_roles),
                    selection.markdown_sha256,
                )
    for witness_id, authority in list(result.items()):
        admitted = admission_by_source.get(authority.source_id)
        if admitted is None:
            continue
        roles = set(authority.roles)
        roles.update(admitted.analytical_roles)
        if authority.selection_id is not None:
            selection = next(
                (item for item in admitted.selections if item.id == authority.selection_id),
                None,
            )
            if selection is not None:
                roles.update(selection.analytical_roles)
        result[witness_id] = _WitnessAuthority(
            authority.witness_id,
            authority.source_id,
            authority.selection_id,
            authority.tier,
            frozenset(roles),
            authority.fingerprint,
        )
    return result


def _reference_issues(
    claim: EvidenceClaim,
    reference,
    *,
    label: str,
    by_id: dict[str, PassageRecord],
    authorities: dict[str, _WitnessAuthority],
    accessible_ids: set[str],
    stage: str,
    file: Path | str | None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    locator = reference.passage_id
    authority = authorities.get(reference.witness_id)
    passage = by_id.get(locator)
    if passage is None:
        issues.append(_error(file, f"Unknown or stale passage ID in {label}", claim=claim.id, locator=locator))
        return issues
    if passage.witness_id != reference.witness_id:
        issues.append(_error(file, "Reference witness_id does not match verified passage", claim=claim.id, locator=locator))
    if passage.source_id != reference.source_id or passage.selection_id != reference.selection_id:
        issues.append(_error(file, "Reference source/selection identity does not match verified passage", claim=claim.id, locator=locator))
    if authority is None:
        issues.append(_error(file, "Reference witness is absent from retained authority registries", claim=claim.id, locator=locator))
    else:
        if authority.tier is None:
            issues.append(_error(file, "Reference witness has no retained authority tier", claim=claim.id, locator=locator))
        elif reference.authority_tier != authority.tier:
            issues.append(_error(file, "Reference authority tier does not match retained registry", claim=claim.id, locator=locator))
        if authority.fingerprint is None:
            issues.append(_error(file, "Reference witness has no retained fingerprint", claim=claim.id, locator=locator))
        elif passage.source_fingerprint != authority.fingerprint:
            issues.append(_error(file, "Verified passage fingerprint does not match retained registry", claim=claim.id, locator=locator))
    if stage == "development" and locator not in accessible_ids:
        issues.append(_error(file, "Development evidence cannot cite a held-out or inaccessible passage", claim=claim.id, locator=locator))
    tier = authority.tier if authority and authority.tier is not None else reference.authority_tier
    if tier == 4 and reference.evidence_role != "control":
        issues.append(_error(file, "Tier 4 evidence may use only the control role", claim=claim.id, locator=locator))
    if reference.evidence_role == "control" and tier != 4:
        issues.append(_error(file, "Control evidence must come from Tier 4", claim=claim.id, locator=locator))
    if stage == "development" and reference.evidence_role == "validation":
        issues.append(_error(file, "Validation evidence is unavailable during development", claim=claim.id, locator=locator))
    if stage == "development" and tier not in {1, 2, 3}:
        issues.append(_error(file, "Development evidence must use accessible Wells Tier 1-3 witnesses", claim=claim.id, locator=locator))
    if stage == "development" and reference.evidence_role in {"control", "validation"}:
        issues.append(_error(file, "Control and validation evidence roles are unavailable during development", claim=claim.id, locator=locator))
    return issues


def _eligible_authorities(
    claim: EvidenceClaim,
    authorities: dict[str, _WitnessAuthority],
    *,
    file: Path | str | None = None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    jurisdiction = claim.jurisdiction
    for witness_id in jurisdiction.eligible_witness_ids:
        if witness_id not in authorities:
            issues.append(_error(file, "Eligible witness is absent from retained authority registries", claim=claim.id, locator=witness_id))
        elif not set(jurisdiction.roles).intersection(authorities[witness_id].roles):
            issues.append(_error(file, "Eligible witness does not exercise a declared jurisdiction role", claim=claim.id, locator=witness_id))
    return issues


def collect_evidence_issues(
    ledger: EvidenceLedger,
    passages: Sequence[PassageRecord],
    *,
    config: AnalysisConfig,
    stage: str | None = None,
    admission: SourceStudyAdmission | None = None,
    registry: SourcesRegistry | None = None,
    manifest: object | None = None,
    development_passage_ids: set[str] | None = None,
    file: Path | str | None = None,
) -> ValidationResult:
    """Collect all claim, reference, authority, scope, and search issues."""

    result = ValidationResult()
    active_stage = stage or ledger.stage
    by_id, by_witness = _passage_maps(passages)
    authorities = _authority_index(passages, admission, registry)
    accessible, holdout_ids = _accessible_ids(
        passages,
        stage=active_stage,
        development_passage_ids=development_passage_ids,
        manifest=manifest,
    )
    dimension_roles = {item.id: set(item.roles) for item in config.dimensions}
    if ledger.study_id != config.study_id:
        result.errors.append(_error(file, "Evidence ledger study identity does not match analysis configuration", locator=ledger.study_id))
    tier1_continuity = {
        witness_id
        for witness_id, authority in authorities.items()
        if authority.tier == 1 and "continuity" in authority.roles
    }

    for claim in ledger.claims:
        jurisdiction = claim.jurisdiction
        if claim.dimension not in dimension_roles:
            result.errors.append(_error(file, "Claim dimension is not configured", claim=claim.id))
        else:
            unknown_roles = set(jurisdiction.roles) - dimension_roles[claim.dimension]
            for role in sorted(unknown_roles):
                result.errors.append(_error(file, "Jurisdiction role is not configured for claim dimension", claim=claim.id, locator=role))
        result.errors.extend(_eligible_authorities(claim, authorities, file=file))
        eligible = set(jurisdiction.eligible_witness_ids)
        support_witnesses: set[str] = set()
        support_authorities: list[_WitnessAuthority] = []
        for reference in claim.supporting_passages:
            result.errors.extend(_reference_issues(claim, reference, label="support", by_id=by_id, authorities=authorities, accessible_ids=accessible, stage=active_stage, file=file))
            support_witnesses.add(reference.witness_id)
            if reference.witness_id in authorities:
                support_authorities.append(authorities[reference.witness_id])
            if reference.evidence_role != "support":
                result.errors.append(_error(file, "Supporting passages must use evidence_role support", claim=claim.id, locator=reference.passage_id))
            if reference.witness_id not in eligible:
                result.errors.append(_error(file, "Support witness is outside claim eligible_witness_ids", claim=claim.id, locator=reference.witness_id))
        for reference in claim.counterexample_passages:
            result.errors.extend(_reference_issues(claim, reference, label="counterexample", by_id=by_id, authorities=authorities, accessible_ids=accessible, stage=active_stage, file=file))
            if reference.evidence_role not in {"counterexample", "variation"}:
                result.errors.append(_error(file, "Counterexample passages must use counterexample or variation evidence_role", claim=claim.id, locator=reference.passage_id))
            if reference.witness_id not in eligible:
                result.errors.append(_error(file, "Counterexample witness is outside claim eligible_witness_ids", claim=claim.id, locator=reference.witness_id))
            if reference.witness_id in authorities and not set(jurisdiction.roles).intersection(authorities[reference.witness_id].roles):
                result.errors.append(_error(file, "Counterexample or variation witness does not exercise a declared jurisdiction role", claim=claim.id, locator=reference.witness_id))
        if claim.status != "rejected":
            if not claim.supporting_passages:
                result.errors.append(_error(file, "Non-rejected claims require support", claim=claim.id))
            if not claim.counterexample_passages and claim.counterexample_search is None:
                result.errors.append(_error(file, "Non-rejected claims require counterexample or structured search", claim=claim.id))
        if claim.status != "rejected" and jurisdiction.scope == "cross_work":
            wells_support = {item.witness_id for item in claim.supporting_passages if authorities.get(item.witness_id, _WitnessAuthority("", "", None, item.authority_tier, frozenset(), None)).tier in {1, 2, 3}}
            if len(wells_support) < 2:
                result.errors.append(_error(file, "cross_work claims require support from at least two Wells witnesses", claim=claim.id))
        if claim.status != "rejected" and jurisdiction.scope == "source_specific":
            if len(eligible) != 1:
                result.errors.append(_error(file, "source_specific claims require exactly one eligible witness", claim=claim.id))
            if claim.classification != "role_specific":
                result.errors.append(_error(file, "source_specific claims must use role_specific classification", claim=claim.id))
        if claim.status != "rejected" and jurisdiction.scope == "role_specific":
            if not eligible:
                result.errors.append(_error(file, "role_specific claims require one or more eligible witnesses", claim=claim.id))
            if claim.classification != "role_specific":
                result.errors.append(_error(file, "role_specific claims must use role_specific classification", claim=claim.id))
        if claim.status != "rejected" and jurisdiction.scope == "continuity":
            if eligible != tier1_continuity:
                result.errors.append(_error(file, "continuity eligibility must derive from the singleton Tier 1 continuity witness", claim=claim.id))
            if support_witnesses != tier1_continuity:
                result.errors.append(_error(file, "continuity support must use the singleton Tier 1 continuity witness", claim=claim.id))
            if claim.classification != "role_specific":
                result.errors.append(_error(file, "continuity claims must use role_specific classification", claim=claim.id))
        if claim.status != "rejected":
            exercised_roles = set().union(*(authority.roles & set(jurisdiction.roles) for authority in support_authorities)) if support_authorities else set()
            for role in jurisdiction.roles:
                if role not in exercised_roles:
                    result.errors.append(_error(file, "Every jurisdiction role must be exercised by supporting evidence", claim=claim.id, locator=role))
            for witness_id in support_witnesses:
                authority = authorities.get(witness_id)
                if authority is None or not set(jurisdiction.roles).intersection(authority.roles):
                    result.errors.append(_error(file, "Each supporting witness must exercise at least one declared jurisdiction role", claim=claim.id, locator=witness_id))
            if support_witnesses and not support_witnesses <= eligible:
                result.errors.append(_error(file, "All support must be inside eligible_witness_ids", claim=claim.id))
        omnibus_parents = {
            item.split("/", 1)[0]
            for item in support_witnesses
            if "/" in item
        }
        if claim.status != "rejected" and len(support_witnesses) >= 2 and len(omnibus_parents) == 1 and all("/" in item for item in support_witnesses):
            if not any(
                line.startswith("Omnibus dependence:") and line.partition(":")[2].strip()
                for line in claim.notes.splitlines()
            ):
                result.errors.append(_error(file, "Selections-only support must disclose Omnibus dependence: in notes", claim=claim.id))

        search = claim.counterexample_search
        if search is not None:
            if claim.dimension not in set(search.dimensions):
                result.errors.append(_error(file, "Counterexample search dimensions must include the claim dimension", claim=claim.id))
            if not set(search.witness_ids) <= eligible:
                result.errors.append(_error(file, "Counterexample search witnesses must be inside claim eligible_witness_ids", claim=claim.id))
            searched_witnesses: set[str] = set()
            for locator in search.searched_passage_ids:
                passage = by_id.get(locator)
                if passage is None:
                    result.errors.append(_error(file, "Counterexample search contains an unknown passage ID", claim=claim.id, locator=locator))
                    continue
                searched_witnesses.add(passage.witness_id)
                if passage.witness_id not in set(search.witness_ids):
                    result.errors.append(_error(file, "Searched passage does not belong to declared search witness_ids", claim=claim.id, locator=locator))
                if locator not in accessible:
                    result.errors.append(_error(file, "Counterexample search cannot use inaccessible or held-out passage", claim=claim.id, locator=locator))
            for witness_id in search.witness_ids:
                if witness_id not in authorities:
                    result.errors.append(_error(file, "Counterexample search witness is not retained", claim=claim.id, locator=witness_id))
                elif not set(jurisdiction.roles).intersection(authorities[witness_id].roles):
                    result.errors.append(_error(file, "Counterexample search witness does not exercise a declared jurisdiction role", claim=claim.id, locator=witness_id))
            if searched_witnesses != set(search.witness_ids):
                result.errors.append(_error(file, "Every counterexample-search witness must contribute a searched passage", claim=claim.id))
            if search.outcome == "material_counterexample_found" and not claim.counterexample_passages:
                result.errors.append(_error(file, "material_counterexample_found requires a counterexample reference", claim=claim.id))
            if search.coverage == "all_eligible_passages":
                if search.method != "exhaustive_close_reading":
                    result.errors.append(_error(file, "all_eligible_passages requires exhaustive_close_reading", claim=claim.id))
                expected = {locator for witness_id in eligible for locator in [item.passage_id for item in by_witness.get(witness_id, [])] if locator in accessible}
                if set(search.searched_passage_ids) != expected:
                    result.errors.append(_error(file, "all_eligible_passages search must equal the exact accessible eligible passage set", claim=claim.id))
        statement_words = {word.casefold() for word in re.findall(r"[A-Za-z]+", claim.statement)}
        if claim.status != "rejected" and statement_words & {"always", "never", "invariably"}:
            if active_stage != "validated":
                result.errors.append(_error(file, "Absolute statement words always/never/invariably are unavailable before validated exhaustive evidence", claim=claim.id))
            elif search is None or search.method != "exhaustive_close_reading" or search.coverage != "all_eligible_passages" or search.outcome != "no_material_counterexample" or claim.counterexample_passages:
                result.errors.append(_error(file, "Absolute wording requires validated exhaustive all-eligible no-counterexample evidence", claim=claim.id))
        if active_stage == "development" and (claim.status == "validated" or claim.confidence == "strong"):
            result.errors.append(_error(file, "validated status and strong confidence require the validation stage", claim=claim.id))
        if active_stage == "development" and holdout_ids & {reference.passage_id for reference in [*claim.supporting_passages, *claim.counterexample_passages]}:
            result.errors.append(_error(file, "Development claim references a holdout passage", claim=claim.id))
    return result.sorted()


def validate_evidence_ledger(*args, **kwargs) -> ValidationResult:
    """Validate the evidence ledger and raise one aggregate diagnostic."""

    result = collect_evidence_issues(*args, **kwargs)
    return raise_for_issues(result, "Evidence ledger validation")


def _profile_finding_issues(
    path: Path,
    content: str,
    *,
    config: AnalysisConfig,
    claims: dict[str, EvidenceClaim],
    stage: str,
) -> ValidationResult:
    result = ValidationResult()
    dimension_section_re = re.compile(r"^### (\d+)\. (.+)$")
    lines = content.splitlines()
    dimension_matches = [
        (index, match)
        for index, line in enumerate(lines)
        if (match := _heading_match(line, dimension_section_re)) is not None
    ]
    dimension_heading_numbers: list[int] = []
    for line in lines:
        match = _heading_match(line, dimension_section_re)
        if match is None:
            continue
        dimension_heading_numbers.append(int(match.group(1)))
        if _noncanonical_heading(line):
            result.errors.append(_error(path, "Canonical heading spelling is required without trailing whitespace in profile dimensions", locator=f"dimension {match.group(1)}"))
    for ordinal in sorted({number for number in dimension_heading_numbers if dimension_heading_numbers.count(number) > 1}):
        result.errors.append(_error(path, "Profile contains a duplicate dimension heading", locator=f"dimension {ordinal}"))
    sections = []
    for index, (line_number, match) in enumerate(dimension_matches):
        end = dimension_matches[index + 1][0] if index + 1 < len(dimension_matches) else len(lines)
        sections.append((line_number, (match.group(1), match.group(2)), "\n".join(lines[line_number + 1 : end]).strip()))
    expected = [(index, dimension.label) for index, dimension in enumerate(config.dimensions, 1)]
    actual = [(int(number), label) for _, (number, label), _ in sections]
    if actual != expected:
        result.errors.append(_error(path, "Profile dimensions must use each exact configured ordinal and label in order"))
        return result.sorted()
    linked: set[str] = set()
    expected_fields = [
        "Claim IDs",
        "Finding",
        "Classification and confidence",
        "Jurisdiction",
        "Evidence",
        "Variation and counterexamples",
        "Quantitative context",
        "Control distinction",
        "Unresolved uncertainty",
    ]
    for _, (ordinal_text, _label), section_content in sections:
        ordinal = int(ordinal_text)
        findings = _entry_blocks(section_content, re.compile(r"^#### Finding (\d+)$"))
        if not findings:
            if section_content.strip() not in {PROTOCOL_PROFILE_SENTINEL, "Protocol placeholder."}:
                result.errors.append(_error(path, "Profile dimension must contain contiguous findings or the exact protocol placeholder", locator=f"dimension {ordinal}"))
            elif stage in {"candidate_frozen", "validated"}:
                result.errors.append(_error(path, "Candidate/final profile cannot retain protocol placeholders", locator=f"dimension {ordinal}"))
            continue
        first_finding_line = findings[0][0]
        if any(line.strip() for line in section_content.splitlines()[:first_finding_line]):
            result.errors.append(_error(path, "Profile findings may not have stray prose before the first finding", locator=f"dimension {ordinal}"))
        numbers = [int(number) for _, number, _ in findings]
        if numbers != list(range(1, len(numbers) + 1)):
            result.errors.append(_error(path, "Profile finding ordinals must be contiguous from 1", locator=f"dimension {ordinal}"))
        for _, finding_number, finding_content in findings:
            finding_heading_re = re.compile(r"^#### Finding \d+$")
            for line in section_content.splitlines():
                if _heading_match(line, finding_heading_re) and _noncanonical_heading(line):
                    result.errors.append(_error(path, "Canonical heading spelling is required without trailing whitespace in profile findings", locator=f"dimension {ordinal} finding {finding_number}"))
            fields = _entry_blocks(finding_content, re.compile(r"^##### (.+)$"))
            for line in finding_content.splitlines():
                if _heading_match(line, re.compile(r"^##### .+$")) and _noncanonical_heading(line):
                    result.errors.append(_error(path, "Canonical heading spelling is required without trailing whitespace in profile fields", locator=f"dimension {ordinal} finding {finding_number}"))
            actual_fields = [name for _, name, _ in fields]
            expected_field_headings = {f"##### {name}" for name in expected_fields}
            first_expected_field = next(
                (
                    index
                    for index, line in enumerate(finding_content.splitlines())
                    if _normalized_heading(line) in expected_field_headings
                ),
                None,
            )
            if first_expected_field is None or any(
                line.strip()
                for line in finding_content.splitlines()[:first_expected_field]
            ):
                result.errors.append(_error(path, "Profile finding contains stray or unparsed content before the first expected field", locator=f"dimension {ordinal} finding {finding_number}"))
            if any(
                re.match(r"^#{1,6} ", _normalized_heading(line)) and _normalized_heading(line) not in expected_field_headings
                for line in finding_content.splitlines()
            ):
                result.errors.append(_error(path, "Profile finding contains an unexpected heading or unparsed record content", locator=f"dimension {ordinal} finding {finding_number}"))
            if actual_fields != expected_fields:
                result.errors.append(_error(path, f"Profile finding fields must be exactly ordered as {expected_fields}", locator=f"dimension {ordinal} finding {finding_number}"))
                continue
            values = dict((name, value) for _, name, value in fields)
            claim_lines = _nonblank_lines(values["Claim IDs"])
            if not claim_lines:
                result.errors.append(_error(path, "Finding Claim IDs must contain one or more nonempty bullets", locator=f"dimension {ordinal} finding {finding_number}"))
            linked_claims: list[EvidenceClaim] = []
            for line in claim_lines:
                match = re.fullmatch(r"- `([^`]+)`", line)
                if not match:
                    result.errors.append(_error(path, "Claim IDs must be nonempty claim-ID bullets", locator=f"dimension {ordinal} finding {finding_number}"))
                    continue
                claim_id = match.group(1)
                linked.add(claim_id)
                claim = claims.get(claim_id)
                if claim is None:
                    result.errors.append(_error(path, "Profile links an unknown claim ID", claim=claim_id, locator=f"dimension {ordinal}"))
                elif claim.dimension != config.dimensions[ordinal - 1].id:
                    result.errors.append(_error(path, "Profile claim link is mismatched to the configured dimension", claim=claim_id, locator=f"dimension {ordinal}"))
                else:
                    linked_claims.append(claim)
            for field_name, field_value in values.items():
                if field_name == "Control distinction" and field_value.strip() == "Deferred until validation." and stage != "validated":
                    continue
                if not _content_is_human(field_value):
                    result.errors.append(_error(path, f"{field_name} must contain non-placeholder prose", locator=f"dimension {ordinal} finding {finding_number}"))
            if stage == "validated" and values["Control distinction"].strip() == "Deferred until validation.":
                result.errors.append(_error(path, "Validated profile findings require a completed control distinction", locator=f"dimension {ordinal} finding {finding_number}"))
            classification_lines = _nonblank_lines(values["Classification and confidence"])
            classification_match = (
                re.fullmatch(r"Classification: `([^`]+)`", classification_lines[0])
                if len(classification_lines) == 2
                else None
            )
            confidence_match = (
                re.fullmatch(r"Confidence: `([^`]+)`", classification_lines[1])
                if len(classification_lines) == 2
                else None
            )
            if classification_match is None or confidence_match is None:
                result.errors.append(_error(path, "Profile finding must declare Classification and Confidence exactly", locator=f"dimension {ordinal} finding {finding_number}"))
            else:
                declared_classification = classification_match.group(1)
                declared_confidence = confidence_match.group(1)
                if declared_classification not in config.claim_classifications:
                    result.errors.append(_error(path, "Profile finding classification is not configured", locator=f"dimension {ordinal} finding {finding_number}"))
                if declared_confidence not in config.confidence_levels:
                    result.errors.append(_error(path, "Profile finding confidence is not configured", locator=f"dimension {ordinal} finding {finding_number}"))
                ordered_claims = sorted(linked_claims, key=lambda claim: claim.id)
                declared_pairs = {
                    (claim.classification, claim.confidence) for claim in ordered_claims
                }
                if len(declared_pairs) > 1:
                    details = ", ".join(
                        f"{claim.id}=({claim.classification},{claim.confidence})"
                        for claim in ordered_claims
                    )
                    result.errors.append(_error(path, f"Linked claims disagree deterministically: {details}", locator=f"dimension {ordinal} finding {finding_number}"))
                elif ordered_claims and declared_pairs != {(declared_classification, declared_confidence)}:
                    result.errors.append(_error(path, "Profile classification and confidence do not match linked claim", locator=f"dimension {ordinal} finding {finding_number}"))
            if stage == "development":
                words = {word.casefold() for word in re.findall(r"[A-Za-z]+", finding_content)}
                if words.intersection({"always", "never", "invariably"}):
                    result.errors.append(_error(path, "Absolute wording always/never/invariably is unavailable in development profile findings", locator=f"dimension {ordinal} finding {finding_number}"))
    orphans = sorted(claim_id for claim_id, claim in claims.items() if claim.status != "rejected" and claim_id not in linked)
    if orphans:
        issue_factory = _error if stage in {"candidate_frozen", "validated"} else _warning
        for claim_id in orphans:
            (result.errors if issue_factory is _error else result.warnings).append(issue_factory(path, "Non-rejected claim is orphaned from the profile", claim=claim_id))
    return result.sorted()


def collect_profile_issues(
    path: Path,
    ledger: EvidenceLedger,
    config: AnalysisConfig,
    *,
    stage: str | None = None,
) -> ValidationResult:
    text = _read(path)
    active_stage = stage or ledger.stage or config.study_status
    return _profile_finding_issues(path, text, config=config, claims={claim.id: claim for claim in ledger.claims}, stage=active_stage)


def validate_profile_claim_links(*args, **kwargs) -> ValidationResult:
    """Validate profile grammar and claim-to-dimension links."""

    result = collect_profile_issues(*args, **kwargs)
    return raise_for_issues(result, "Profile claim-link validation")


def collect_quantitative_profile_issues(
    profile: QuantitativeProfile,
    *,
    root: Path,
    metrics_path: Path,
    config: AnalysisConfig,
    passages: Sequence[PassageRecord],
    development_witness_ids: set[str],
    forbidden_witness_ids: set[str] | None = None,
    metrics_csv_path: Path | None = None,
    expected_provenance: dict[str, str] | None = None,
    expected_witness_identities: set[tuple[str, str, str | None]] | None = None,
    expected_metric_records: Sequence[dict[str, object]] | None = None,
) -> ValidationResult:
    result = ValidationResult()
    forbidden_witness_ids = forbidden_witness_ids or set()
    stage_order = {"protocol": 0, "development": 1, "candidate_frozen": 2, "validated": 3}
    if stage_order[profile.stage] > stage_order[config.study_status]:
        result.errors.append(_error(metrics_path, "Quantitative profile stage cannot lead configured analysis stage"))
    try:
        document = json.loads(
            metrics_path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
        )
        parsed_document = GeneratedDevelopmentMetrics.model_validate(document)
    except (
        OSError,
        UnicodeError,
        JSONDecodeError,
        DuplicateJSONKeyError,
        RecursionError,
        TypeError,
        ValueError,
        ValidationError,
    ) as exc:
        result.errors.append(
            _error(
                metrics_path,
                f"Generated development metric JSON object/schema validation failed: {exc}",
            )
        )
        return result.sorted()
    if document["enabled_measurements"] != list(config.enabled_measurements):
        result.errors.append(_error(metrics_path, "Generated development metric JSON enabled_measurements do not match the current analysis configuration", locator="enabled_measurements"))
    provenance = document.get("provenance")
    if expected_provenance is not None:
        for field, expected in expected_provenance.items():
            if field in document and document.get(field) != expected:
                result.errors.append(_error(metrics_path, "Generated development metric JSON contains stale top-level provenance", locator=field))
            if provenance.get(field) != expected:
                result.errors.append(_error(metrics_path, "Generated development metric JSON contains stale provenance", locator=field))
    metric_records = document.get("witnesses")

    metric_identities = [
        (item.witness_id, item.source_id, item.selection_id)
        for item in parsed_document.witnesses
    ]
    if expected_metric_records is not None:
        try:
            for record in expected_metric_records:
                WitnessMetricRecord.model_validate(record)
        except (ValidationError, TypeError, ValueError, RecursionError) as exc:
            result.errors.append(
                _error(
                    metrics_path,
                    f"Independently measured writer return failed generated metric witness schema validation: {exc}",
                    locator="returned witnesses",
                )
            )
            return result.sorted()
    if expected_metric_records is not None and not _json_values_equal_exact(
        metric_records, list(expected_metric_records)
    ):
        result.errors.append(_error(metrics_path, "Generated development metric witness records do not exactly match the independently measured current development output", locator="witnesses"))
    if result.errors:
        return result.sorted()
    if document.get("stage") != "development":
        result.errors.append(_error(metrics_path, "Quantitative profile must reference current development metric output"))
    if document.get("study_id") != config.study_id:
        result.errors.append(_error(metrics_path, "Quantitative metric study identity is stale"))
    if profile.study_id != config.study_id:
        result.errors.append(_error(metrics_path, "Quantitative profile study identity is stale"))
    metric_witness_ids = [item.witness_id for item in parsed_document.witnesses]
    if len(metric_witness_ids) != len(set(metric_witness_ids)):
        result.errors.append(_error(metrics_path, "Generated development metric witness IDs must be unique"))
    metric_witnesses = set(metric_witness_ids)
    if len(metric_identities) != len(set(metric_identities)):
        result.errors.append(_error(metrics_path, "Generated development metric witness identities must be unique"))
    if metric_witnesses != development_witness_ids:
        result.errors.append(_error(metrics_path, "Generated development metric witness set is not the current development witness set"))
    if expected_witness_identities is not None and set(metric_identities) != expected_witness_identities:
        result.errors.append(_error(metrics_path, "Generated development metric witness identity set does not match the independently expected development witness set"))
    if result.errors:
        return result.sorted()
    if profile.stage == "protocol" and not profile.generated_metrics and not profile.witnesses:
        return result.sorted()
    profile_witnesses = {item.witness_id for item in profile.witnesses}
    profile_identities = [_profile_identity_tuple(item) for item in profile.witnesses]
    if len(profile_identities) != len(set(profile_identities)):
        result.errors.append(_error(metrics_path, "Quantitative profile witness identities must be unique"))
    if profile_witnesses != development_witness_ids:
        result.errors.append(_error(metrics_path, "Quantitative profile witness set must exactly equal current development metric witnesses"))
    configured_json = config.generated_paths["development_metrics"]
    configured_csv = config.generated_paths["development_metrics_csv"]
    metrics_csv_path = metrics_csv_path or root / configured_csv
    if _canonical_root_path(root, metrics_path) != _canonical_root_path(root, Path(configured_json)):
        result.errors.append(_error(metrics_path, "Quantitative profile JSON path is not the configured development output", locator=str(metrics_path)))
    if _canonical_root_path(root, metrics_csv_path) != _canonical_root_path(root, Path(configured_csv)):
        result.errors.append(_error(metrics_csv_path, "Quantitative profile CSV path is not the configured development output", locator=str(metrics_csv_path)))
    expected_references = {
        "development-metrics": configured_json,
        "development-metrics-csv": configured_csv,
    }
    actual_references = {reference.id: reference.path for reference in profile.generated_metrics}
    if len(profile.generated_metrics) != 2 or actual_references != expected_references:
        result.errors.append(_error(metrics_path, "Populated quantitative profile must contain exactly the JSON and CSV metric references with configured IDs and paths"))
    passage_by_witness = {passage.witness_id: passage for passage in passages}
    for witness in profile.witnesses:
        if witness.witness_id in forbidden_witness_ids:
            result.errors.append(_error(metrics_path, "Quantitative profile references a forbidden holdout/control witness", locator=witness.witness_id))
        metric = next((item for item in document.get("witnesses", []) if item.get("witness_id") == witness.witness_id), None)
        if metric is None:
            result.errors.append(_error(metrics_path, "Quantitative profile witness is absent from generated metrics", locator=witness.witness_id))
            continue
        if metric.get("source_id") != witness.source_id or metric.get("selection_id") != witness.selection_id:
            result.errors.append(_error(metrics_path, "Quantitative profile witness identity does not match generated metrics", locator=witness.witness_id))
        passage = passage_by_witness.get(witness.witness_id)
        if passage is None:
            result.errors.append(_error(metrics_path, "Quantitative profile witness is absent from the verified passage registry", locator=witness.witness_id))
        elif passage.source_id != witness.source_id or passage.selection_id != witness.selection_id:
            result.errors.append(_error(metrics_path, "Quantitative profile witness identity does not match verified passage registry", locator=witness.witness_id))
        if not witness.values:
            result.errors.append(_error(metrics_path, "Quantitative profile witness values must be nonempty", locator=witness.witness_id))
        for metric_path, stored_value in witness.values.items():
            parts = metric_path.split(".")
            current: object = metric
            if not metric_path.strip() or any(not part for part in parts):
                result.errors.append(_error(metrics_path, "Quantitative profile metric paths must be nonempty dotted paths", locator=metric_path))
                continue
            try:
                for part in parts:
                    if not isinstance(current, dict) or part not in current:
                        raise KeyError(part)
                    current = current[part]
            except KeyError:
                result.errors.append(_error(metrics_path, "Quantitative profile metric path does not resolve in current witness output", locator=f"{witness.witness_id}:{metric_path}"))
                continue
            if current is None or isinstance(current, (dict, list)):
                result.errors.append(_error(metrics_path, "Quantitative profile values must resolve to nonempty scalar output values", locator=f"{witness.witness_id}:{metric_path}"))
            elif type(stored_value) is not type(current) or stored_value != current:
                result.errors.append(_error(metrics_path, "Quantitative profile stored value does not exactly equal current witness output", locator=f"{witness.witness_id}:{metric_path}"))
    for reference in profile.generated_metrics:
        allowed_metric_paths = {
            configured_json,
            configured_csv,
        }
        if reference.id not in {"development-metrics", "development-metrics-csv"}:
            result.errors.append(_error(metrics_path, "Quantitative profile metric ID is not one of the configured development references", locator=reference.id))
        if reference.path not in allowed_metric_paths:
            result.errors.append(_error(metrics_path, "Quantitative profile metric path is outside the configured development outputs", locator=reference.path))
        target = root / reference.path
        if not target.exists():
            result.errors.append(_error(metrics_path, "Quantitative profile metric path is missing", locator=reference.path))
        else:
            import hashlib

            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            if actual != reference.sha256:
                result.errors.append(_error(metrics_path, "Quantitative profile metric fingerprint is stale", locator=reference.path))
    try:
        with metrics_csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            required = {"study_id", "stage", "config_sha256", "index_sha256", "manifest_sha256", "config_path", "index_path", "manifest_path", "witness_id", "source_id", "selection_id"}
            if not reader.fieldnames or not required <= set(reader.fieldnames):
                result.errors.append(_error(metrics_csv_path, "Current development CSV has invalid provenance columns"))
            if not rows:
                result.errors.append(_error(metrics_csv_path, "Current development CSV must contain data rows"))
            csv_identities = [
                (row.get("witness_id"), row.get("source_id"), row.get("selection_id") or None)
                for row in rows
            ]
            if set(csv_identities) != set(metric_identities):
                result.errors.append(_error(metrics_csv_path, "Current development CSV identity set does not exactly match generated JSON metrics"))
            if set(csv_identities) != set(profile_identities):
                result.errors.append(_error(metrics_csv_path, "Current development CSV identity set does not exactly match the quantitative profile witnesses"))
            csv_row_keys = [
                tuple(row.get(field, "") for field in (
                    "witness_id", "source_id", "selection_id", "section_id",
                    "metric", "submetric", "value", "passage_id", "notes",
                ))
                for row in rows
            ]
            if len(csv_row_keys) != len(set(csv_row_keys)):
                result.errors.append(_error(metrics_csv_path, "Current development CSV contains duplicate metric rows"))
            for row in rows:
                if (
                    row.get("study_id") != config.study_id
                    or row.get("stage") != "development"
                    or any(row.get(key) != document.get(key, provenance.get(key, "")) for key in ("config_sha256", "index_sha256", "manifest_sha256"))
                    or any(row.get(key) != provenance.get(key, "") for key in ("config_path", "index_path", "manifest_path"))
                ):
                    result.errors.append(_error(metrics_csv_path, "Current development CSV contains stale or invalid provenance"))
                    break
    except (OSError, UnicodeError, csv.Error) as exc:
        result.errors.append(_error(metrics_csv_path, f"Unable to inspect current development CSV: {exc}"))
    return result.sorted()


def validate_quantitative_profile(*args, **kwargs) -> ValidationResult:
    result = collect_quantitative_profile_issues(*args, **kwargs)
    return raise_for_issues(result, "Quantitative profile validation")


def collect_leakage_issues(
    paths: Sequence[Path],
    *,
    forbidden_witness_ids: set[str],
    forbidden_passages: Sequence[PassageRecord],
) -> ValidationResult:
    """Detect forbidden IDs and exact full normalized passage copies.

    Sequences shorter than eight tokens, partial copies, and edited or
    paraphrased text remain human-review risks.
    """

    result = ValidationResult()
    forbidden_sequences: list[tuple[str, tuple[str, ...]]] = []
    for passage in forbidden_passages:
        tokens = tuple(token.casefold() for token in _TOKEN_RE.findall(unicodedata.normalize("NFC", passage.normalized_text)))
        if len(tokens) >= FORBIDDEN_TEXT_MIN_TOKENS:
            forbidden_sequences.append((passage.passage_id, tokens))
    for path in sorted(paths, key=lambda item: item.as_posix()):
        text = _read(path)
        yaml_occurrences: list[tuple[str, str]] = []
        if path.name.endswith((".yml", ".yaml")):
            try:
                yaml_occurrences = _yaml_scalar_occurrences(text)
            except yaml.YAMLError:
                yaml_occurrences = []
        for witness_id in sorted(forbidden_witness_ids):
            boundary = rf"(?<![A-Za-z0-9_-]){re.escape(witness_id)}(?![A-Za-z0-9_-])"
            occurrences = len(re.findall(boundary, text))
            allowed = [
                document_path
                for document_path, value in yaml_occurrences
                if value == witness_id and _ALLOWED_CONTROL_WITNESS_PATH.fullmatch(document_path)
            ]
            disallowed = [
                document_path
                for document_path, value in yaml_occurrences
                if value == witness_id and not _ALLOWED_CONTROL_WITNESS_PATH.fullmatch(document_path)
            ]
            if disallowed or occurrences != len(allowed):
                result.errors.append(_error(path, "Forbidden holdout or Tier 4 witness ID appears in tracked development content", locator=witness_id))
        for passage in forbidden_passages:
            boundary = rf"(?<![A-Za-z0-9_-]){re.escape(passage.passage_id)}(?![A-Za-z0-9_-])"
            if re.search(boundary, text):
                result.errors.append(_error(path, "Forbidden holdout passage ID appears in tracked development content", locator=passage.passage_id))
        tokens = tuple(token.casefold() for token in _TOKEN_RE.findall(unicodedata.normalize("NFC", text)))
        for locator, sequence in forbidden_sequences:
            if any(
                tokens[index : index + len(sequence)] == sequence
                for index in range(len(tokens) - len(sequence) + 1)
            ):
                result.errors.append(_error(path, "Exact full normalized forbidden passage text copied; partial or edited text remains a human-review risk", locator=locator))
    return result.sorted()


def validate_leakage(*args, **kwargs) -> ValidationResult:
    result = collect_leakage_issues(*args, **kwargs)
    return raise_for_issues(result, "Development leakage validation")


_PERIOD_ROOT_HEADING = "# Period Controls"
_PERIOD_CLAIM_HEADING = re.compile(r"^## Claim `([^`]+)`$")
_PERIOD_COMPARISON_HEADING = re.compile(r"^### Comparison `([^`]+)`$")


def collect_period_controls_issues(
    text: str,
    comparisons: Sequence[ControlComparison],
    *,
    file: Path | str = "period-controls.md",
) -> ValidationResult:
    """Validate the exact claim/comparison Markdown grammar for final controls."""

    result = ValidationResult()
    path = Path(file)
    lines = text.splitlines()
    if not lines or lines[0] != _PERIOD_ROOT_HEADING:
        result.errors.append(_error(path, "Period controls must begin with `# Period Controls`"))

    expected: dict[str, set[str]] = {}
    for comparison in comparisons:
        expected.setdefault(comparison.claim_id, set()).add(comparison.id)
    actual: dict[str, list[str]] = {}
    seen_claims: set[str] = set()
    seen_comparisons: set[str] = set()
    current_claim: str | None = None
    current_comparison: str | None = None
    comparison_body: list[str] = []

    def finish_comparison() -> None:
        nonlocal current_comparison, comparison_body
        if current_comparison is None:
            return
        if not "".join(comparison_body).strip():
            result.errors.append(
                _error(path, "Period-control comparison section must contain non-whitespace prose", locator=current_comparison)
            )
        current_comparison = None
        comparison_body = []

    for line in lines[1:] if lines else []:
        normalized = line
        claim_match = _PERIOD_CLAIM_HEADING.fullmatch(normalized)
        comparison_match = _PERIOD_COMPARISON_HEADING.fullmatch(normalized)
        if claim_match:
            finish_comparison()
            claim_id = claim_match.group(1)
            if claim_id in seen_claims:
                result.errors.append(_error(path, "Duplicate period-control claim section", locator=claim_id))
            seen_claims.add(claim_id)
            actual.setdefault(claim_id, [])
            current_claim = claim_id
            continue
        if comparison_match:
            finish_comparison()
            if current_claim is None:
                result.errors.append(_error(path, "Comparison section is not nested under a claim section"))
                current_comparison = comparison_match.group(1)
                comparison_body = []
                continue
            comparison_id = comparison_match.group(1)
            if comparison_id in seen_comparisons:
                result.errors.append(_error(path, "Duplicate period-control comparison section", locator=comparison_id))
            seen_comparisons.add(comparison_id)
            actual[current_claim].append(comparison_id)
            current_comparison = comparison_id
            comparison_body = []
            continue
        if normalized.startswith("#"):
            result.errors.append(_error(path, "Malformed or unexpected period-control heading", locator=normalized))
        if current_comparison is not None:
            comparison_body.append(line)

    finish_comparison()
    if set(actual) != set(expected):
        result.errors.append(
            _error(path, "Period-control claim sections do not exactly match claims with control comparisons")
        )
    for claim_id, expected_ids in expected.items():
        if set(actual.get(claim_id, [])) != expected_ids or len(actual.get(claim_id, [])) != len(expected_ids):
            result.errors.append(
                _error(path, "Period-control comparison sections do not exactly match the claim registry", locator=claim_id)
            )
    return result.sorted()


def validate_period_controls(*args, **kwargs) -> ValidationResult:
    return raise_for_issues(
        collect_period_controls_issues(*args, **kwargs),
        "Final period-control validation",
    )


__all__ = [
    "FORBIDDEN_TEXT_MIN_TOKENS",
    "PROTOCOL_OBSERVATION_SENTINEL",
    "PROTOCOL_PROFILE_SENTINEL",
    "ValidationIssue",
    "ValidationResult",
    "collect_evidence_issues",
    "collect_leakage_issues",
    "collect_period_controls_issues",
    "collect_observation_issues",
    "collect_profile_issues",
    "collect_quantitative_profile_issues",
    "raise_for_issues",
    "validate_evidence_ledger",
    "validate_leakage",
    "validate_period_controls",
    "validate_observation_dossiers",
    "validate_profile_claim_links",
    "validate_quantitative_profile",
]
