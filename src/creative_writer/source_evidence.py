"""Strict, source-linked validation for the Phase 2B evidence surface.

This module validates human-authored Markdown and YAML artifacts.  It does not
author observations, claims, or profile findings.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from creative_writer.exceptions import CreativeWriterError
from creative_writer.models import SourceStudyAdmission, SourcesRegistry
from creative_writer.source_analysis_models import (
    AnalysisConfig,
    EvidenceClaim,
    EvidenceLedger,
    PassageRecord,
    QuantitativeProfile,
)


PROTOCOL_OBSERVATION_SENTINEL = "No reviewed observations are recorded at protocol status."
PROTOCOL_PROFILE_SENTINEL = "No reviewed descriptive synthesis is recorded at protocol status."
# Exact normalized token sequences shorter than this are too likely to be
# ordinary Victorian phrasing to identify copied source prose mechanically.
FORBIDDEN_TEXT_MIN_TOKENS = 8
_TOKEN_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)
_PLACEHOLDER_RE = re.compile(r"\b(?:tbd|todo|placeholder|no reviewed|reserved for)\b", re.I)


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
    start = next((i for i, line in enumerate(lines) if line == heading), None)
    if start is None:
        return None
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return "\n".join(lines[start + 1 : end]).strip()


def _entry_blocks(section: str, heading_re: re.Pattern[str]) -> list[tuple[int, str, str]]:
    lines = section.splitlines()
    matches = [
        (i, match)
        for i, line in enumerate(lines)
        if (match := heading_re.fullmatch(line)) is not None
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
        match = re.fullmatch(r"- ([^\s`]+)", line)
        if not match:
            return None
        claims.append(match.group(1))
    return claims if claims else None


def _observation_entry_issues(
    path: Path,
    number: int,
    content: str,
    passages_by_id: dict[str, PassageRecord],
    config: AnalysisConfig,
    accessible_ids: set[str],
    claim_ids: set[str] | None,
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
    if len(jurisdiction_lines) != 2:
        issues.append(_error(path, "Jurisdiction must contain exactly Dimension and Role bullets", locator=f"Observation {number}"))
    else:
        dimension_match = re.fullmatch(r"- Dimension: `([^`]+)`", jurisdiction_lines[0])
        role_match = re.fullmatch(r"- Role: `([^`]+)`", jurisdiction_lines[1])
        if not dimension_match or not role_match:
            issues.append(_error(path, "Jurisdiction bullets must be exactly Dimension then Role", locator=f"Observation {number}"))
        else:
            dimension_id, role = dimension_match.group(1), role_match.group(1)
            dimension = next((item for item in config.dimensions if item.id == dimension_id), None)
            if dimension is None:
                issues.append(_error(path, "Unknown configured dimension", locator=dimension_id))
            elif role not in dimension.roles:
                issues.append(_error(path, "Jurisdiction role is not configured for the dimension", locator=role))

    comparisons = _parse_comparison(values["Comparison"])
    if comparisons is None:
        issues.append(_error(path, "Comparison must use related/contrary/variation locator bullets or ASCII None - <reason>", locator=f"Observation {number}"))
    else:
        for locator in comparisons:
            if locator not in passages_by_id:
                issues.append(_error(path, "Unknown or stale comparison locator", locator=locator))
            elif locator not in accessible_ids:
                issues.append(_error(path, "Development comparison cannot cite a held-out or inaccessible passage", locator=locator))
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
) -> ValidationResult:
    """Collect all observation grammar, locator, and development leakage issues."""

    result = ValidationResult()
    by_id, _ = _passage_maps(passages)
    accessible, _ = _accessible_ids(
        passages,
        stage=stage,
        development_passage_ids=development_passage_ids,
        manifest=manifest,
    )
    for path in sorted(paths, key=lambda item: item.as_posix()):
        text = _read(path)
        section = _extract_section(text, "## Observations")
        if section is None:
            result.errors.append(_error(path, "Missing exact ## Observations section"))
            continue
        entries = _entry_blocks(section, re.compile(r"^### Observation (\d+)$"))
        if not entries:
            if section.strip() != PROTOCOL_OBSERVATION_SENTINEL:
                result.errors.append(_error(path, "Observations must be the exact protocol sentinel or contiguous ### Observation N entries"))
            continue
        first_entry_line = entries[0][0]
        if any(line.strip() for line in section.splitlines()[:first_entry_line]):
            result.errors.append(_error(path, "Observation entries may not have unstructured prose before the first entry"))
        if any(
            line.startswith("### ") and not re.fullmatch(r"### Observation \d+", line)
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
    registry_by_source = {source.id: source for source in registry.sources} if registry else {}
    result: dict[str, _WitnessAuthority] = {}
    for passage in passages:
        retained = registry_by_source.get(passage.source_id)
        admitted = admission_by_source.get(passage.source_id)
        tier = retained.role.tier if retained else None
        roles = set(retained.role.analytical_roles) if retained else set()
        fingerprint: str | None = None
        if retained:
            if passage.selection_id is None:
                fingerprint = retained.files.markdown_sha256
            else:
                selection = next((item for item in retained.selections if item.id == passage.selection_id), None)
                fingerprint = selection.markdown_sha256 if selection else None
        if admitted:
            roles.update(admitted.analytical_roles)
            if passage.selection_id is not None:
                selection = next((item for item in admitted.selections if item.id == passage.selection_id), None)
                if selection:
                    roles.update(selection.analytical_roles)
        result[passage.witness_id] = _WitnessAuthority(
            passage.witness_id,
            passage.source_id,
            passage.selection_id,
            tier,
            frozenset(roles),
            fingerprint,
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
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    locator = reference.passage_id
    authority = authorities.get(reference.witness_id)
    passage = by_id.get(locator)
    if passage is None:
        issues.append(_error(None, f"Unknown or stale passage ID in {label}", claim=claim.id, locator=locator))
        return issues
    if passage.witness_id != reference.witness_id:
        issues.append(_error(None, "Reference witness_id does not match verified passage", claim=claim.id, locator=locator))
    if passage.source_id != reference.source_id or passage.selection_id != reference.selection_id:
        issues.append(_error(None, "Reference source/selection identity does not match verified passage", claim=claim.id, locator=locator))
    if authority is None:
        issues.append(_error(None, "Reference witness is absent from retained authority registries", claim=claim.id, locator=locator))
    else:
        if authority.tier is not None and reference.authority_tier != authority.tier:
            issues.append(_error(None, "Reference authority tier does not match retained registry", claim=claim.id, locator=locator))
        if authority.fingerprint is not None and passage.source_fingerprint != authority.fingerprint:
            issues.append(_error(None, "Verified passage fingerprint does not match retained registry", claim=claim.id, locator=locator))
    if stage == "development" and locator not in accessible_ids:
        issues.append(_error(None, "Development evidence cannot cite a held-out or inaccessible passage", claim=claim.id, locator=locator))
    tier = authority.tier if authority and authority.tier is not None else reference.authority_tier
    if tier == 4 and reference.evidence_role != "control":
        issues.append(_error(None, "Tier 4 evidence may use only the control role", claim=claim.id, locator=locator))
    if reference.evidence_role == "control" and tier != 4:
        issues.append(_error(None, "Control evidence must come from Tier 4", claim=claim.id, locator=locator))
    if stage == "development" and reference.evidence_role == "validation":
        issues.append(_error(None, "Validation evidence is unavailable during development", claim=claim.id, locator=locator))
    if stage == "development" and tier not in {1, 2, 3}:
        issues.append(_error(None, "Development evidence must use accessible Wells Tier 1-3 witnesses", claim=claim.id, locator=locator))
    if stage == "development" and reference.evidence_role in {"control", "validation"}:
        issues.append(_error(None, "Control and validation evidence roles are unavailable during development", claim=claim.id, locator=locator))
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
            result.errors.extend(_reference_issues(claim, reference, label="support", by_id=by_id, authorities=authorities, accessible_ids=accessible, stage=active_stage))
            support_witnesses.add(reference.witness_id)
            if reference.witness_id in authorities:
                support_authorities.append(authorities[reference.witness_id])
            if reference.evidence_role != "support":
                result.errors.append(_error(file, "Supporting passages must use evidence_role support", claim=claim.id, locator=reference.passage_id))
            if reference.witness_id not in eligible:
                result.errors.append(_error(file, "Support witness is outside claim eligible_witness_ids", claim=claim.id, locator=reference.witness_id))
        for reference in claim.counterexample_passages:
            result.errors.extend(_reference_issues(claim, reference, label="counterexample", by_id=by_id, authorities=authorities, accessible_ids=accessible, stage=active_stage))
            if reference.evidence_role not in {"counterexample", "variation"}:
                result.errors.append(_error(file, "Counterexample passages must use counterexample or variation evidence_role", claim=claim.id, locator=reference.passage_id))
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
            exercised_roles = set().union(*(authority.roles for authority in support_authorities)) if support_authorities else set()
            for role in jurisdiction.roles:
                if role not in exercised_roles:
                    result.errors.append(_error(file, "Every jurisdiction role must be exercised by supporting evidence", claim=claim.id, locator=role))
            if support_witnesses and not support_witnesses <= eligible:
                result.errors.append(_error(file, "All support must be inside eligible_witness_ids", claim=claim.id))
        omnibus_parents = {
            item.split("/", 1)[0]
            for item in support_witnesses
            if "/" in item
        }
        if claim.status != "rejected" and len(support_witnesses) >= 2 and len(omnibus_parents) == 1 and all("/" in item for item in support_witnesses):
            if not claim.notes.splitlines() or not any(line.startswith("Omnibus dependence:") for line in claim.notes.splitlines()):
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
        if (match := dimension_section_re.fullmatch(line)) is not None
    ]
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
    for _, (ordinal_text, _label), section_content in sections:
        ordinal = int(ordinal_text)
        findings = _entry_blocks(section_content, re.compile(r"^#### Finding (\d+)$"))
        if not findings:
            if section_content.strip() not in {"", PROTOCOL_PROFILE_SENTINEL, "Protocol placeholder."}:
                result.errors.append(_error(path, "Profile dimension must contain contiguous findings or the exact protocol placeholder", locator=f"dimension {ordinal}"))
            elif stage in {"candidate_frozen", "validated"}:
                result.errors.append(_error(path, "Candidate/final profile cannot retain protocol placeholders", locator=f"dimension {ordinal}"))
            continue
        numbers = [int(number) for _, number, _ in findings]
        if numbers != list(range(1, len(numbers) + 1)):
            result.errors.append(_error(path, "Profile finding ordinals must be contiguous from 1", locator=f"dimension {ordinal}"))
        for _, finding_number, finding_content in findings:
            fields = _entry_blocks(finding_content, re.compile(r"^##### (.+)$"))
            if [name for _, name, _ in fields] != ["Claim IDs", "Finding"]:
                result.errors.append(_error(path, "Each finding must declare Claim IDs before Finding", locator=f"dimension {ordinal} finding {finding_number}"))
                continue
            claim_lines = _nonblank_lines(dict((name, value) for _, name, value in fields)["Claim IDs"])
            if not claim_lines:
                result.errors.append(_error(path, "Finding Claim IDs must contain one or more nonempty bullets", locator=f"dimension {ordinal} finding {finding_number}"))
            for line in claim_lines:
                match = re.fullmatch(r"- ([^\s`]+)", line)
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
            finding_text = dict((name, value) for _, name, value in fields)["Finding"]
            if not _content_is_human(finding_text):
                result.errors.append(_error(path, "Finding must contain non-placeholder prose", locator=f"dimension {ordinal} finding {finding_number}"))
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


def _metric_ids(document: dict) -> set[str]:
    ids = {"development-metrics", "development-metrics.csv", "development-metrics.json"}
    ids.update(str(item) for item in document.get("enabled_measurements", []))
    return ids


def collect_quantitative_profile_issues(
    profile: QuantitativeProfile,
    *,
    root: Path,
    metrics_path: Path,
    config: AnalysisConfig,
    passages: Sequence[PassageRecord],
    development_witness_ids: set[str],
    forbidden_witness_ids: set[str] | None = None,
) -> ValidationResult:
    result = ValidationResult()
    forbidden_witness_ids = forbidden_witness_ids or set()
    stage_order = {"protocol": 0, "development": 1, "candidate_frozen": 2, "validated": 3}
    if stage_order[profile.stage] > stage_order[config.study_status]:
        result.errors.append(_error(metrics_path, "Quantitative profile stage cannot lead configured analysis stage"))
    try:
        import json

        document = json.loads(metrics_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        result.errors.append(_error(metrics_path, f"Unable to read generated metric JSON: {exc}"))
        return result.sorted()
    if document.get("stage") != "development":
        result.errors.append(_error(metrics_path, "Quantitative profile must reference current development metric output"))
    if document.get("study_id") != config.study_id or profile.study_id != config.study_id:
        result.errors.append(_error(metrics_path, "Quantitative metric study identity is stale"))
    metric_witnesses = {item.get("witness_id") for item in document.get("witnesses", [])}
    profile_witnesses = {item.witness_id for item in profile.witnesses}
    if profile.stage == "development" and profile_witnesses != development_witness_ids:
        result.errors.append(_error(metrics_path, "Development quantitative profile witness set must exactly equal current development metric witnesses"))
    if metric_witnesses != development_witness_ids:
        result.errors.append(_error(metrics_path, "Generated development metric witness set is not the current development witness set"))
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
        if passage and (passage.source_id != witness.source_id or passage.selection_id != witness.selection_id):
            result.errors.append(_error(metrics_path, "Quantitative profile witness identity does not match verified passage registry", locator=witness.witness_id))
    for reference in profile.generated_metrics:
        if reference.id not in _metric_ids(document):
            result.errors.append(_error(metrics_path, "Quantitative profile metric ID is not present in current development output", locator=reference.id))
        allowed_metric_paths = {
            config.generated_paths["development_metrics"],
            config.generated_paths["development_metrics_csv"],
        }
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
            if target.suffix == ".csv":
                try:
                    import csv

                    with target.open(newline="", encoding="utf-8") as handle:
                        rows = csv.DictReader(handle)
                        for row in rows:
                            if row.get("study_id") != config.study_id or row.get("stage") != "development":
                                result.errors.append(_error(metrics_path, "Current development CSV contains stale study or stage provenance", locator=reference.path))
                                break
                except (OSError, UnicodeError, csv.Error) as exc:
                    result.errors.append(_error(metrics_path, f"Unable to inspect current development CSV: {exc}", locator=reference.path))
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
    """Detect forbidden IDs and exact normalized copied text using an eight-token floor."""

    result = ValidationResult()
    forbidden_sequences: list[tuple[str, tuple[str, ...]]] = []
    for passage in forbidden_passages:
        tokens = tuple(token.casefold() for token in _TOKEN_RE.findall(unicodedata.normalize("NFC", passage.normalized_text)))
        if len(tokens) >= FORBIDDEN_TEXT_MIN_TOKENS:
            for start in range(len(tokens) - FORBIDDEN_TEXT_MIN_TOKENS + 1):
                forbidden_sequences.append((passage.passage_id, tokens[start : start + FORBIDDEN_TEXT_MIN_TOKENS]))
    for path in sorted(paths, key=lambda item: item.as_posix()):
        text = _read(path)
        for witness_id in sorted(forbidden_witness_ids):
            if witness_id in text:
                result.errors.append(_error(path, "Forbidden holdout or Tier 4 witness ID appears in tracked development content", locator=witness_id))
        tokens = tuple(token.casefold() for token in _TOKEN_RE.findall(unicodedata.normalize("NFC", text)))
        for locator, sequence in forbidden_sequences:
            if any(tokens[index : index + FORBIDDEN_TEXT_MIN_TOKENS] == sequence for index in range(len(tokens) - FORBIDDEN_TEXT_MIN_TOKENS + 1)):
                result.errors.append(_error(path, f"Exact normalized forbidden passage text copied using the minimum {FORBIDDEN_TEXT_MIN_TOKENS}-token rule", locator=locator))
    return result.sorted()


def validate_leakage(*args, **kwargs) -> ValidationResult:
    result = collect_leakage_issues(*args, **kwargs)
    return raise_for_issues(result, "Development leakage validation")


__all__ = [
    "FORBIDDEN_TEXT_MIN_TOKENS",
    "PROTOCOL_OBSERVATION_SENTINEL",
    "PROTOCOL_PROFILE_SENTINEL",
    "ValidationIssue",
    "ValidationResult",
    "collect_evidence_issues",
    "collect_leakage_issues",
    "collect_observation_issues",
    "collect_profile_issues",
    "collect_quantitative_profile_issues",
    "raise_for_issues",
    "validate_evidence_ledger",
    "validate_leakage",
    "validate_observation_dossiers",
    "validate_profile_claim_links",
    "validate_quantitative_profile",
]
