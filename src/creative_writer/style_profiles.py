"""Resolve advisory style profiles against approved Phase 2B evidence."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import load_yaml_model
from creative_writer.models import (
    ChapterDocument,
    RetainedSourceRecord,
    SourcesRegistry,
)
from creative_writer.source_analysis_common import safe_relative_path, sha256_file
from creative_writer.source_analysis_models import (
    AnalysisConfig,
    EvidenceClaim,
    EvidenceLedger,
    EvidenceReference,
    HoldoutManifest,
    ValidationRecord,
    load_validation_document,
)
from creative_writer.style_models import (
    StyleArtifactReference,
    StyleProfile,
    StyleReferencePacket,
    StyleRule,
)


CHAPTER_ROLE_CAVEAT = (
    "Chapter-level role assignment is coarse and does not classify every paragraph."
)


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


@dataclass(slots=True)
class _EvidenceAccumulator:
    passage_id: str
    witness_id: str
    source_id: str
    selection_id: str | None
    authority_tier: int
    claim_ids: list[str]
    evidence_kinds: list[str]


@dataclass(frozen=True, slots=True)
class _WitnessAuthority:
    witness_id: str
    source_id: str
    selection_id: str | None
    authority_tier: int
    analytical_roles: tuple[str, ...]


def _contained_profile_path(
    story_dir: Path,
    profile_path: Path,
    *,
    root: Path | None = None,
) -> Path:
    resolved_story = story_dir.resolve(strict=False)
    candidate = (
        profile_path
        if profile_path.is_absolute()
        else safe_relative_path(resolved_story, profile_path.as_posix())
    )
    resolved_candidate = candidate.resolve(strict=False)
    if resolved_candidate != candidate:
        raise CreativeWriterError(
            "Style profile path redirects through a symlink or is not canonical: "
            f"{profile_path} -> {resolved_candidate}"
        )
    if root is not None:
        resolved_root = root.resolve(strict=False)
        try:
            resolved_candidate.relative_to(resolved_root)
        except ValueError as exc:
            raise CreativeWriterError(
                f"Style profile path escapes repository root: {profile_path}"
            ) from exc
    try:
        resolved_candidate.relative_to(resolved_story)
    except ValueError as exc:
        raise CreativeWriterError(
            f"Style profile path escapes story directory: {profile_path}"
        ) from exc
    return resolved_candidate


def resolve_style_profile_path(
    story_dir: Path,
    configured_path: str | None,
    override: str | None,
) -> Path:
    """Resolve an explicit or configured profile without allowing traversal."""

    if override is not None:
        if not override.strip():
            raise CreativeWriterError("Style profile override must not be empty")
        candidate = Path(override)
        return _contained_profile_path(story_dir, candidate)

    if configured_path is None:
        raise CreativeWriterError(
            "Style analysis requires a configured profile or --profile override"
        )
    if not configured_path.strip() or Path(configured_path).is_absolute():
        raise CreativeWriterError(
            "configured style profile path must remain story-relative"
        )
    try:
        return _contained_profile_path(story_dir, Path(configured_path))
    except CreativeWriterError as exc:
        raise CreativeWriterError(
            "configured style profile path must remain story-relative: "
            f"{configured_path}"
        ) from exc


def _validated_root_and_story(root: Path, story_dir: Path) -> tuple[Path, Path]:
    resolved_root = root.resolve(strict=False)
    resolved_story = story_dir.resolve(strict=False)
    try:
        resolved_story.relative_to(resolved_root)
    except ValueError as exc:
        raise CreativeWriterError(
            f"story directory escapes repository root: {story_dir}"
        ) from exc
    return resolved_root, resolved_story


def _tracked_artifact_path(
    root: Path,
    story_dir: Path,
    label: str,
    reference: StyleArtifactReference,
) -> Path:
    path = safe_relative_path(root, reference.path)
    try:
        path.resolve(strict=False).relative_to(story_dir)
    except ValueError as exc:
        raise CreativeWriterError(
            f"{label} path escapes story directory: {reference.path}"
        ) from exc
    actual = sha256_file(path)
    if actual != reference.sha256:
        raise CreativeWriterError(
            f"{label} SHA-256 mismatch for {reference.path}: "
            f"expected {reference.sha256}, got {actual}"
        )
    return path


def _validate_study_lifecycle(
    profile: StyleProfile,
    analysis: AnalysisConfig,
    ledger: EvidenceLedger,
    validation: ValidationRecord,
) -> None:
    study_ids = {
        profile.provenance.study_id,
        analysis.study_id,
        ledger.study_id,
        validation.study_id,
    }
    if len(study_ids) != 1:
        raise CreativeWriterError(
            "Style profile provenance artifacts have mismatched study IDs"
        )
    if analysis.study_status not in {"candidate_frozen", "validated"}:
        raise CreativeWriterError(
            "Style profile analysis is not candidate-frozen or validated"
        )
    if ledger.stage != "validated":
        raise CreativeWriterError("Style profile evidence ledger is not validated")
    if validation.stage != "validated" or validation.validation_step != "complete":
        raise CreativeWriterError(
            "Style profile validation record is not complete and validated"
        )


def _validate_hash_lifecycle(
    profile: StyleProfile,
    analysis: AnalysisConfig,
    holdout: HoldoutManifest,
    validation: ValidationRecord,
) -> None:
    provenance = profile.provenance
    if analysis.source_registry.sha256 != provenance.source_registry.sha256:
        raise CreativeWriterError(
            "analysis source-registry SHA-256 does not match profile provenance"
        )
    registry_hash = holdout.registry_hashes.get(analysis.source_registry.path)
    if registry_hash != provenance.source_registry.sha256:
        raise CreativeWriterError(
            "holdout source-registry SHA-256 does not match profile provenance"
        )
    if validation.candidate_analysis_sha256 != provenance.analysis.sha256:
        raise CreativeWriterError(
            "validation candidate analysis SHA-256 does not match profile provenance"
        )
    if validation.candidate_manifest_sha256 != provenance.holdout_manifest.sha256:
        raise CreativeWriterError(
            "validation candidate holdout-manifest SHA-256 does not match "
            "profile provenance"
        )
    if validation.final_ledger_sha256 != provenance.evidence_ledger.sha256:
        raise CreativeWriterError(
            "validation final evidence-ledger SHA-256 does not match "
            "profile provenance"
        )


def _validate_index_bindings(
    root: Path,
    profile: StyleProfile,
    analysis: AnalysisConfig,
    holdout: HoldoutManifest,
) -> None:
    bindings = (
        (
            "development",
            profile.provenance.passage_indexes.development,
            holdout.development_passage_index,
            "development_passage_index",
        ),
        (
            "heldout_wells",
            profile.provenance.passage_indexes.heldout_wells,
            holdout.heldout_wells_passage_index,
            "heldout_wells_passage_index",
        ),
        (
            "tier4_controls",
            profile.provenance.passage_indexes.tier4_controls,
            holdout.tier4_control_passage_index,
            "tier4_control_passage_index",
        ),
    )
    for name, profile_binding, manifest_binding, generated_key in bindings:
        safe_relative_path(root, profile_binding.path)
        if (
            profile_binding.path != manifest_binding.path
            or profile_binding.path != analysis.generated_paths[generated_key]
        ):
            raise CreativeWriterError(
                f"{name} passage-index path does not match the approved "
                "analysis and holdout manifest"
            )
        if profile_binding.sha256 != manifest_binding.sha256:
            raise CreativeWriterError(
                f"{name} passage-index SHA-256 does not match the approved "
                "holdout manifest"
            )


def _source_map(sources: SourcesRegistry) -> dict[str, RetainedSourceRecord]:
    return {source.id: source for source in sources.sources}


def _resolve_witness(
    sources_by_id: dict[str, RetainedSourceRecord],
    witness_id: str,
) -> _WitnessAuthority:
    if "/" in witness_id:
        source_id, selection_id = witness_id.split("/", 1)
    else:
        source_id, selection_id = witness_id, None

    source = sources_by_id.get(source_id)
    if source is None:
        raise CreativeWriterError(
            f"Evidence witness {witness_id} has unknown source {source_id}"
        )
    selection_ids = {selection.id for selection in source.selections}
    if selection_id is not None and selection_id not in selection_ids:
        raise CreativeWriterError(
            f"Evidence witness {witness_id} has unknown selection {selection_id}"
        )
    if selection_id is None and source.selections:
        raise CreativeWriterError(
            f"Selected source {source_id} must use a <source-id>/<selection-id> "
            "witness ID"
        )
    return _WitnessAuthority(
        witness_id=witness_id,
        source_id=source_id,
        selection_id=selection_id,
        authority_tier=source.role.tier,
        analytical_roles=tuple(source.role.analytical_roles),
    )


def _validate_reference_authority(
    claim: EvidenceClaim,
    reference: EvidenceReference,
    sources_by_id: dict[str, RetainedSourceRecord],
) -> _WitnessAuthority:
    authority = _resolve_witness(sources_by_id, reference.witness_id)
    if (
        reference.source_id != authority.source_id
        or reference.selection_id != authority.selection_id
    ):
        raise CreativeWriterError(
            f"Evidence reference {reference.passage_id} has mismatched source identity"
        )
    if reference.authority_tier != authority.authority_tier:
        raise CreativeWriterError(
            f"Evidence reference authority tier for {reference.witness_id} "
            f"does not match source {authority.source_id}"
        )
    if reference.witness_id not in claim.jurisdiction.eligible_witness_ids:
        raise CreativeWriterError(
            f"Evidence reference {reference.passage_id} is outside claim "
            f"{claim.id} witness jurisdiction"
        )
    return authority


def _passage_memberships(
    holdout: HoldoutManifest,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    development_by_witness: dict[str, set[str]] = {}
    heldout_by_witness: dict[str, set[str]] = {}
    assignments: dict[str, list[tuple[str, str]]] = {}
    for witness in holdout.witnesses:
        development = development_by_witness.setdefault(witness.witness_id, set())
        for window in witness.development_windows:
            development.update(window.passage_ids)
            for passage_id in window.passage_ids:
                assignments.setdefault(passage_id, []).append(
                    ("development", witness.witness_id)
                )
        heldout_passages = heldout_by_witness.setdefault(witness.witness_id, set())
        for window in witness.holdout_windows:
            heldout_passages.update(window.passage_ids)
            for passage_id in window.passage_ids:
                assignments.setdefault(passage_id, []).append(
                    ("held-out", witness.witness_id)
                )

    for passage_id, passage_assignments in assignments.items():
        partitions = {partition for partition, _witness in passage_assignments}
        witnesses = {witness for _partition, witness in passage_assignments}
        if len(partitions) > 1:
            raise CreativeWriterError(
                f"Passage {passage_id} is assigned to both development and "
                "held-out partitions"
            )
        if len(witnesses) > 1:
            raise CreativeWriterError(
                f"Passage {passage_id} is assigned to multiple witnesses"
            )
        if len(passage_assignments) > 1:
            raise CreativeWriterError(
                f"Passage {passage_id} is assigned more than once"
            )
        witness_id = passage_assignments[0][1]
        if not passage_id.startswith(f"{witness_id}:"):
            raise CreativeWriterError(
                f"Passage {passage_id} does not belong to witness {witness_id}"
            )
    return development_by_witness, heldout_by_witness


def _add_evidence(
    catalog: dict[str, _EvidenceAccumulator],
    *,
    passage_id: str,
    authority: _WitnessAuthority,
    claim_id: str,
    evidence_kind: str,
) -> None:
    existing = catalog.get(passage_id)
    if existing is None:
        catalog[passage_id] = _EvidenceAccumulator(
            passage_id=passage_id,
            witness_id=authority.witness_id,
            source_id=authority.source_id,
            selection_id=authority.selection_id,
            authority_tier=authority.authority_tier,
            claim_ids=[claim_id],
            evidence_kinds=[evidence_kind],
        )
        return
    identity = (
        existing.witness_id,
        existing.source_id,
        existing.selection_id,
        existing.authority_tier,
    )
    incoming = (
        authority.witness_id,
        authority.source_id,
        authority.selection_id,
        authority.authority_tier,
    )
    if identity != incoming:
        raise CreativeWriterError(
            f"Evidence passage {passage_id} has inconsistent source authority"
        )
    if claim_id not in existing.claim_ids:
        existing.claim_ids.append(claim_id)
    if evidence_kind not in existing.evidence_kinds:
        existing.evidence_kinds.append(evidence_kind)


def _validate_result_target(
    claim: EvidenceClaim,
    target_id: str,
    witness_id: str,
    role: str,
    *,
    control: bool,
    record_id: str,
) -> None:
    targets = (
        claim.validation_expectation.control_targets
        if control
        else claim.validation_expectation.heldout_targets
    )
    target = next((item for item in targets if item.id == target_id), None)
    label = "Control comparison" if control else "Held-out result"
    if target is None:
        raise CreativeWriterError(
            f"{label} {record_id} references an unknown validation target"
        )
    if target.witness_id != witness_id or target.role != role:
        raise CreativeWriterError(
            f"{label} {record_id} does not match its declared validation target"
        )


def _validate_target_coverage(
    ledger: EvidenceLedger,
    validation: ValidationRecord,
) -> None:
    heldout_by_claim: dict[str, set[str]] = {}
    heldout_seen: set[tuple[str, str]] = set()
    for result in validation.heldout_claim_results:
        key = (result.claim_id, result.expectation_target_id)
        if key in heldout_seen:
            raise CreativeWriterError(
                f"held-out validation target {result.expectation_target_id} "
                f"for claim {result.claim_id} is covered more than once"
            )
        heldout_seen.add(key)
        heldout_by_claim.setdefault(result.claim_id, set()).add(
            result.expectation_target_id
        )
    controls_by_claim: dict[str, set[str]] = {}
    controls_seen: set[tuple[str, str]] = set()
    for comparison in validation.control_comparisons:
        key = (comparison.claim_id, comparison.expectation_target_id)
        if key in controls_seen:
            raise CreativeWriterError(
                f"control validation target {comparison.expectation_target_id} "
                f"for claim {comparison.claim_id} is covered more than once"
            )
        controls_seen.add(key)
        controls_by_claim.setdefault(comparison.claim_id, set()).add(
            comparison.expectation_target_id
        )

    for claim in ledger.claims:
        heldout_actual = heldout_by_claim.get(claim.id, set())
        control_actual = controls_by_claim.get(claim.id, set())
        if claim.status == "rejected":
            if heldout_actual or control_actual:
                raise CreativeWriterError(
                    f"Rejected claim {claim.id} must not have validation evidence"
                )
            continue
        heldout_expected = {
            target.id for target in claim.validation_expectation.heldout_targets
        }
        control_expected = {
            target.id for target in claim.validation_expectation.control_targets
        }
        if heldout_actual != heldout_expected:
            raise CreativeWriterError(
                f"Validation record has incomplete held-out target coverage "
                f"for claim {claim.id}"
            )
        if control_actual != control_expected:
            raise CreativeWriterError(
                f"Validation record has incomplete control target coverage "
                f"for claim {claim.id}"
            )


def _build_evidence_catalog(
    ledger: EvidenceLedger,
    validation: ValidationRecord,
    holdout: HoldoutManifest,
    sources: SourcesRegistry,
    eligible_claim_statuses: Sequence[str],
) -> dict[str, EvidencePassage]:
    claims_by_id = {claim.id: claim for claim in ledger.claims}
    eligible_claim_ids = {
        claim.id
        for claim in ledger.claims
        if claim.status in eligible_claim_statuses
    }
    sources_by_id = _source_map(sources)
    development_by_witness, heldout_by_witness = _passage_memberships(holdout)
    catalog: dict[str, _EvidenceAccumulator] = {}

    for claim in ledger.claims:
        for reference in claim.supporting_passages:
            authority = _validate_reference_authority(
                claim,
                reference,
                sources_by_id,
            )
            if authority.authority_tier == 4:
                raise CreativeWriterError(
                    f"Tier 4 passage {reference.passage_id} cannot support a claim"
                )
            if reference.passage_id not in development_by_witness.get(
                reference.witness_id,
                set(),
            ):
                raise CreativeWriterError(
                    f"Ledger passage {reference.passage_id} is outside the "
                    f"development partition for witness {reference.witness_id}"
                )
            if claim.id in eligible_claim_ids:
                _add_evidence(
                    catalog,
                    passage_id=reference.passage_id,
                    authority=authority,
                    claim_id=claim.id,
                    evidence_kind=reference.evidence_role,
                )
        for reference in claim.counterexample_passages:
            authority = _validate_reference_authority(
                claim,
                reference,
                sources_by_id,
            )
            if reference.passage_id not in development_by_witness.get(
                reference.witness_id,
                set(),
            ):
                raise CreativeWriterError(
                    f"Ledger passage {reference.passage_id} is outside the "
                    f"development partition for witness {reference.witness_id}"
                )
            if claim.id in eligible_claim_ids:
                _add_evidence(
                    catalog,
                    passage_id=reference.passage_id,
                    authority=authority,
                    claim_id=claim.id,
                    evidence_kind=reference.evidence_role,
                )

    heldout_witnesses = set(holdout.heldout_wells_passage_index.witness_ids)
    for result in validation.heldout_claim_results:
        claim = claims_by_id.get(result.claim_id)
        if claim is None:
            raise CreativeWriterError(
                f"Held-out result {result.id} references unknown claim "
                f"{result.claim_id}"
            )
        if result.role not in claim.jurisdiction.roles:
            raise CreativeWriterError(
                f"Held-out result {result.id} role {result.role} is outside "
                f"claim {claim.id} jurisdiction"
            )
        _validate_result_target(
            claim,
            result.expectation_target_id,
            result.witness_id,
            result.role,
            control=False,
            record_id=result.id,
        )
        authority = _resolve_witness(sources_by_id, result.witness_id)
        if authority.authority_tier == 4:
            raise CreativeWriterError(
                f"Held-out result {result.id} has Tier 4 authority"
            )
        if result.role not in authority.analytical_roles:
            raise CreativeWriterError(
                f"Held-out result {result.id} uses an undeclared source role"
            )
        if result.witness_id not in heldout_witnesses:
            raise CreativeWriterError(
                f"Held-out result {result.id} is outside the heldout_wells "
                "partition"
            )
        heldout_passages = heldout_by_witness.get(result.witness_id, set())
        for passage_id in result.passage_ids:
            if passage_id not in heldout_passages:
                raise CreativeWriterError(
                    f"Held-out result {result.id} references passage "
                    f"{passage_id} outside its holdout windows"
                )
            if claim.id in eligible_claim_ids:
                _add_evidence(
                    catalog,
                    passage_id=passage_id,
                    authority=authority,
                    claim_id=claim.id,
                    evidence_kind="validation",
                )

    control_witnesses = set(holdout.tier4_control_passage_index.witness_ids)
    for comparison in validation.control_comparisons:
        claim = claims_by_id.get(comparison.claim_id)
        if claim is None:
            raise CreativeWriterError(
                f"Control comparison {comparison.id} references unknown claim "
                f"{comparison.claim_id}"
            )
        _validate_result_target(
            claim,
            comparison.expectation_target_id,
            comparison.witness_id,
            comparison.role,
            control=True,
            record_id=comparison.id,
        )
        authority = _resolve_witness(sources_by_id, comparison.witness_id)
        if authority.authority_tier != 4:
            raise CreativeWriterError(
                f"Control comparison {comparison.id} is not Tier 4"
            )
        if comparison.role not in authority.analytical_roles:
            raise CreativeWriterError(
                f"Control comparison {comparison.id} uses an undeclared source role"
            )
        if comparison.witness_id not in control_witnesses:
            raise CreativeWriterError(
                f"Control comparison {comparison.id} is outside the "
                "tier4_controls partition"
            )
        for passage_id in comparison.passage_ids:
            if claim.id in eligible_claim_ids:
                _add_evidence(
                    catalog,
                    passage_id=passage_id,
                    authority=authority,
                    claim_id=claim.id,
                    evidence_kind="control",
                )

    _validate_target_coverage(ledger, validation)
    return {
        passage_id: EvidencePassage(
            passage_id=item.passage_id,
            witness_id=item.witness_id,
            source_id=item.source_id,
            selection_id=item.selection_id,
            authority_tier=item.authority_tier,
            claim_ids=tuple(item.claim_ids),
            evidence_kinds=tuple(item.evidence_kinds),
        )
        for passage_id, item in catalog.items()
    }


def _resolve_rules(
    profile: StyleProfile,
    ledger: EvidenceLedger,
) -> tuple[ResolvedStyleRule, ...]:
    claims_by_id = {claim.id: claim for claim in ledger.claims}
    roles_by_id = {role.id: role for role in profile.roles}
    resolved: list[ResolvedStyleRule] = []
    for rule in profile.rules:
        claims: list[EvidenceClaim] = []
        for claim_id in rule.claim_ids:
            claim = claims_by_id.get(claim_id)
            if claim is None:
                raise CreativeWriterError(
                    f"Rule {rule.id} uses unknown claim {claim_id}"
                )
            if claim.status not in profile.eligible_claim_statuses:
                raise CreativeWriterError(
                    f"Rule {rule.id} uses ineligible claim {claim.id}"
                )
            claims.append(claim)
        for role_id in rule.roles:
            role = roles_by_id.get(role_id)
            if role is None:
                raise CreativeWriterError(
                    f"Rule {rule.id} uses unknown role {role_id}"
                )
            for claim in claims:
                if not set(role.phase_2b_roles).intersection(
                    claim.jurisdiction.roles
                ):
                    raise CreativeWriterError(
                        f"Rule {rule.id} broadens {claim.id} beyond its "
                        "declared role jurisdiction"
                    )
        resolved.append(ResolvedStyleRule(rule=rule, claims=tuple(claims)))
    return tuple(resolved)


def _validate_approved_audit(
    profile: StyleProfile,
    ledger: EvidenceLedger,
    validation: ValidationRecord,
) -> None:
    run_id = profile.provenance.approved_review_run_id
    audit = next(
        (
            run
            for run in validation.review_run_provenance
            if run.run_id == run_id
        ),
        None,
    )
    if (
        audit is None
        or audit.stage != "whole_study_audit"
        or audit.outcome != "approved"
        or not audit.independent_of_candidate_authorship
    ):
        raise CreativeWriterError(
            f"Review run {run_id} must be an approved independent "
            "whole-study audit"
        )
    if set(audit.assigned_claim_ids) != {claim.id for claim in ledger.claims}:
        raise CreativeWriterError(
            "The approved whole-study audit must cover all ledger claims"
        )


def _validate_rule_evidence(
    rules: tuple[ResolvedStyleRule, ...],
    evidence_catalog: dict[str, EvidencePassage],
) -> None:
    for resolved in rules:
        rule = resolved.rule
        claim_ids = {claim.id for claim in resolved.claims}
        for passage_id in [
            *rule.source_passage_ids,
            *rule.variation_passage_ids,
        ]:
            passage = evidence_catalog.get(passage_id)
            if passage is None:
                raise CreativeWriterError(
                    f"Rule {rule.id} passage {passage_id} is not in the "
                    "approved evidence catalog"
                )
            if passage.authority_tier == 4:
                raise CreativeWriterError(
                    f"Tier 4 passage {passage_id} cannot be positive rule evidence"
                )
            if not claim_ids.intersection(passage.claim_ids):
                raise CreativeWriterError(
                    f"Rule {rule.id} passage {passage_id} is not evidence for "
                    "one of its declared claims"
                )
        for passage_id in rule.control_passage_ids:
            passage = evidence_catalog.get(passage_id)
            if passage is None:
                raise CreativeWriterError(
                    f"Rule {rule.id} control passage {passage_id} is not in "
                    "the approved evidence catalog"
                )
            if passage.authority_tier != 4:
                raise CreativeWriterError(
                    f"Rule {rule.id} negative control {passage_id} is not Tier 4"
                )


def _packet_ids(profile: StyleProfile) -> list[str]:
    packet_ids: list[str] = []
    for packet_id in profile.default_packet_ids:
        if packet_id not in packet_ids:
            packet_ids.append(packet_id)
    for rule in profile.rules:
        for packet_id in rule.packet_ids:
            if packet_id not in packet_ids:
                packet_ids.append(packet_id)
    return packet_ids


def _load_packets(
    story_dir: Path,
    profile: StyleProfile,
    rules: tuple[ResolvedStyleRule, ...],
    evidence_catalog: dict[str, EvidencePassage],
) -> dict[str, StyleReferencePacket]:
    profile_roles = {role.id for role in profile.roles}
    profile_claims = {
        claim.id for resolved in rules for claim in resolved.claims
    }
    packets: dict[str, StyleReferencePacket] = {}
    for packet_id in _packet_ids(profile):
        packet_path = safe_relative_path(
            story_dir,
            f"style-reference-packets/{packet_id}.yml",
        )
        if not packet_path.is_file():
            raise CreativeWriterError(
                f"Style profile references unknown packet {packet_id}"
            )
        packet = load_yaml_model(packet_path, StyleReferencePacket)
        if packet.id != packet_id:
            raise CreativeWriterError(
                f"Packet file {packet_path} declares ID {packet.id}, "
                f"expected {packet_id}"
            )
        if (
            packet.profile_id != profile.profile_id
            or packet.profile_version != profile.version
        ):
            raise CreativeWriterError(
                f"Packet {packet.id} does not match profile "
                f"{profile.profile_id} {profile.version}"
            )
        unknown_roles = set(packet.roles) - profile_roles
        if unknown_roles:
            raise CreativeWriterError(
                f"Packet {packet.id} uses unknown profile role(s): "
                f"{sorted(unknown_roles)}"
            )
        if not set(packet.claim_ids) <= profile_claims:
            raise CreativeWriterError(
                f"Packet {packet.id} claim IDs are outside the profile claims"
            )
        packet_claims = set(packet.claim_ids)
        for entry in packet.entries:
            entry_claims = set(entry.claim_ids)
            if not entry_claims <= packet_claims:
                raise CreativeWriterError(
                    f"Packet {packet.id} entry {entry.id} claim IDs are "
                    "outside the packet claim IDs"
                )
            if not entry_claims <= profile_claims:
                raise CreativeWriterError(
                    f"Packet {packet.id} entry {entry.id} claim IDs are "
                    "outside the profile claims"
                )
            passage = evidence_catalog.get(entry.passage_id)
            if passage is None:
                raise CreativeWriterError(
                    f"Packet {packet.id} entry {entry.id} passage is not in "
                    "the approved evidence catalog"
                )
            if not entry_claims.intersection(passage.claim_ids):
                raise CreativeWriterError(
                    f"Packet {packet.id} entry {entry.id} passage has no "
                    "declared claim relationship in the evidence catalog"
                )
            if entry.authority_tier != passage.authority_tier:
                raise CreativeWriterError(
                    f"Packet {packet.id} entry {entry.id} authority tier "
                    "does not match the evidence catalog"
                )
            if entry.kind == "negative_control" and entry.authority_tier != 4:
                raise CreativeWriterError(
                    f"Packet {packet.id} entry {entry.id} negative control "
                    "must be Tier 4"
                )
            if entry.authority_tier == 4 and entry.kind != "negative_control":
                raise CreativeWriterError(
                    f"Packet {packet.id} entry {entry.id} uses Tier 4 as "
                    "positive evidence"
                )
        packets[packet_id] = packet
    return packets


def _validate_source_registry_binding(
    root: Path,
    story_dir: Path,
    analysis: AnalysisConfig,
    source_path: Path,
) -> None:
    expected_story_path = safe_relative_path(
        story_dir,
        analysis.source_registry.path,
    )
    if expected_story_path != source_path:
        raise CreativeWriterError(
            "Profile source-registry path does not match analysis configuration"
        )
    try:
        source_path.relative_to(root)
    except ValueError as exc:
        raise CreativeWriterError(
            "Profile source-registry path escapes repository root"
        ) from exc


def load_style_context(
    root: Path,
    story_dir: Path,
    profile_path: Path,
) -> StyleContext:
    """Load one profile after validating its complete Phase 2B provenance."""

    resolved_root, resolved_story = _validated_root_and_story(root, story_dir)
    resolved_profile = _contained_profile_path(
        resolved_story,
        profile_path,
        root=resolved_root,
    )
    profile = load_yaml_model(resolved_profile, StyleProfile)
    provenance = profile.provenance

    analysis_path = _tracked_artifact_path(
        resolved_root,
        resolved_story,
        "analysis",
        provenance.analysis,
    )
    source_path = _tracked_artifact_path(
        resolved_root,
        resolved_story,
        "source-registry",
        provenance.source_registry,
    )
    holdout_path = _tracked_artifact_path(
        resolved_root,
        resolved_story,
        "holdout-manifest",
        provenance.holdout_manifest,
    )
    ledger_path = _tracked_artifact_path(
        resolved_root,
        resolved_story,
        "evidence-ledger",
        provenance.evidence_ledger,
    )
    validation_path = _tracked_artifact_path(
        resolved_root,
        resolved_story,
        "validation-record",
        provenance.validation_record,
    )

    analysis = load_yaml_model(analysis_path, AnalysisConfig)
    sources = load_yaml_model(source_path, SourcesRegistry)
    holdout = load_yaml_model(holdout_path, HoldoutManifest)
    ledger = load_yaml_model(ledger_path, EvidenceLedger)
    validation, _body = load_validation_document(validation_path)

    _validate_study_lifecycle(profile, analysis, ledger, validation)
    _validate_source_registry_binding(
        resolved_root,
        resolved_story,
        analysis,
        source_path,
    )
    _validate_hash_lifecycle(profile, analysis, holdout, validation)
    _validate_index_bindings(resolved_root, profile, analysis, holdout)
    rules = _resolve_rules(profile, ledger)
    _validate_approved_audit(profile, ledger, validation)
    evidence_catalog = _build_evidence_catalog(
        ledger,
        validation,
        holdout,
        sources,
        profile.eligible_claim_statuses,
    )
    _validate_rule_evidence(rules, evidence_catalog)
    packets = _load_packets(
        resolved_story,
        profile,
        rules,
        evidence_catalog,
    )
    return StyleContext(
        story_dir=resolved_story,
        profile_path=resolved_profile,
        profile=profile,
        analysis=analysis,
        ledger=ledger,
        validation=validation,
        sources=sources,
        evidence_catalog=evidence_catalog,
        rules=rules,
        packets=packets,
    )


def validate_chapter_style_metadata(
    context: StyleContext,
    chapters: Sequence[ChapterDocument],
) -> list[str]:
    """Return one path-preserving error per unknown chapter role or packet."""

    known_roles = {role.id for role in context.profile.roles}
    known_packets = set(context.packets)
    errors: list[str] = []
    for chapter in chapters:
        for role_id in chapter.front_matter.style_roles:
            if role_id not in known_roles:
                errors.append(
                    f"{chapter.stub_path}: unknown style role `{role_id}`"
                )
        for packet_id in chapter.front_matter.style_packets:
            if packet_id not in known_packets:
                errors.append(
                    f"{chapter.stub_path}: unknown style packet `{packet_id}`"
                )
    return errors
