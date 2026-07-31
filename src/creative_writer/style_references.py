"""Compile provenance-verified, writer-facing style reference packets."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory, load_yaml_model
from creative_writer.models import ContractConfig
from creative_writer.source_analysis import run_source_analysis
from creative_writer.source_analysis_common import safe_relative_path, sha256_file
from creative_writer.source_analysis_models import EvidenceClaim, PassageRecord
from creative_writer.source_passages import (
    context_window,
    parse_passage_partition,
)
from creative_writer.style_models import (
    StyleArtifactReference,
    StylePacketEntry,
    StyleReferencePacket,
)
from creative_writer.style_profiles import (
    EvidencePassage,
    StyleContext,
    load_style_context,
    resolve_style_profile_path,
)


_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_IGNORED_MANIFESTS = frozenset({"_template.yml"})
_INDEX_NAMES = ("development", "heldout_wells", "tier4_controls")
_ENTRY_LABELS = {
    "positive_example": "Positive example",
    "authentic_variation": "Authentic variation",
    "counterexample": "Counterexample",
    "negative_control": "Negative control",
}
_PROVENANCE_ARTIFACTS = (
    ("Analysis", "analysis"),
    ("Source registry", "source_registry"),
    ("Holdout manifest", "holdout_manifest"),
    ("Evidence ledger", "evidence_ledger"),
    ("Validation record", "validation_record"),
)
_INDEX_LABELS = {
    "development": "Development",
    "heldout_wells": "Held-out Wells",
    "tier4_controls": "Tier 4 controls",
}


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


@dataclass(frozen=True, slots=True)
class _IndexBinding:
    name: str
    path: Path
    reference: StyleArtifactReference


def style_reference_manifest_paths(story_dir: Path) -> list[Path]:
    """Return real style-reference manifests in deterministic path order."""

    directory = story_dir / "style-reference-packets"
    if not directory.is_dir():
        return []
    return [
        path
        for path in sorted(directory.glob("*.yml"))
        if path.name not in _IGNORED_MANIFESTS and path.is_file()
    ]


def _validated_story_dir(root: Path, slug: str) -> tuple[Path, Path]:
    if not isinstance(slug, str) or _SLUG.fullmatch(slug) is None:
        raise CreativeWriterError("Story slug must be a canonical lowercase slug")
    resolved_root = root.resolve(strict=False)
    story_dir = safe_relative_path(resolved_root, f"stories/{slug}")
    if not story_dir.is_dir():
        raise CreativeWriterError(f"Story directory does not exist: {story_dir}")
    return resolved_root, story_dir


def _resolve_manifest_path(story_dir: Path, pack: str) -> tuple[str, Path]:
    if not isinstance(pack, str):
        raise CreativeWriterError(
            "Style-reference pack name must be a slug with optional .yml suffix"
        )
    value = pack.strip()
    if value.endswith(".yml"):
        value = value[:-4]
    if (
        not value
        or _SLUG.fullmatch(value) is None
        or "/" in pack
        or "\\" in pack
    ):
        raise CreativeWriterError(
            "Style-reference pack name must be a slug with optional .yml suffix"
        )
    manifest_path = safe_relative_path(
        story_dir,
        f"style-reference-packets/{value}.yml",
    )
    if not manifest_path.is_file():
        raise CreativeWriterError(
            f"Style-reference packet manifest does not exist: {manifest_path}"
        )
    return value, manifest_path


def _load_context(
    root: Path,
    story_dir: Path,
    profile_override: str | None,
) -> StyleContext:
    configured_profile: str | None = None
    if profile_override is None:
        contract_path = story_dir / "contract.yml"
        if contract_path.is_file():
            contract = load_yaml_model(contract_path, ContractConfig)
            if contract.style_lint is not None:
                configured_profile = contract.style_lint.profile
    profile_path = resolve_style_profile_path(
        story_dir,
        configured_profile,
        profile_override,
    )
    return load_style_context(root, story_dir, profile_path)


def _index_bindings(root: Path, context: StyleContext) -> list[_IndexBinding]:
    references = context.profile.provenance.passage_indexes
    return [
        _IndexBinding(
            name=name,
            path=safe_relative_path(root, getattr(references, name).path),
            reference=getattr(references, name),
        )
        for name in _INDEX_NAMES
    ]


def _verify_present_index(binding: _IndexBinding) -> None:
    if not binding.path.is_file():
        raise CreativeWriterError(
            f"{binding.name} passage index is not a regular file: {binding.path}"
        )
    actual = sha256_file(binding.path)
    if actual != binding.reference.sha256:
        raise CreativeWriterError(
            f"{binding.name} passage-index SHA-256 mismatch for "
            f"{binding.reference.path}: expected {binding.reference.sha256}, "
            f"got {actual}"
        )


def _prepare_missing_indexes(
    root: Path,
    slug: str,
    bindings: list[_IndexBinding],
) -> bool:
    missing: list[_IndexBinding] = []
    for binding in bindings:
        if binding.path.exists():
            _verify_present_index(binding)
        else:
            missing.append(binding)
    if not missing:
        return False

    run_source_analysis(root, slug, "prepare")
    for binding in bindings:
        if not binding.path.exists():
            raise CreativeWriterError(
                f"{binding.name} passage index is missing after "
                f"source-analysis prepare: {binding.path}"
            )
        _verify_present_index(binding)
    return True


def _read_verified_partition(binding: _IndexBinding) -> list[PassageRecord]:
    try:
        data = binding.path.read_bytes()
    except OSError as exc:
        raise CreativeWriterError(
            f"Unable to read {binding.name} passage index {binding.path}: {exc}"
        ) from exc
    actual = hashlib.sha256(data).hexdigest()
    if actual != binding.reference.sha256:
        raise CreativeWriterError(
            f"{binding.name} passage-index SHA-256 mismatch for "
            f"{binding.reference.path}: expected {binding.reference.sha256}, "
            f"got {actual}"
        )
    return parse_passage_partition(data)


def _load_indexes(
    bindings: list[_IndexBinding],
) -> tuple[
    dict[str, list[PassageRecord]],
    dict[str, tuple[str, PassageRecord]],
]:
    indexes: dict[str, list[PassageRecord]] = {}
    passages: dict[str, tuple[str, PassageRecord]] = {}
    for binding in bindings:
        records = _read_verified_partition(binding)
        indexes[binding.name] = records
        for record in records:
            existing = passages.get(record.passage_id)
            if existing is not None:
                raise CreativeWriterError(
                    f"duplicate passage ID across partitions: "
                    f"{record.passage_id} ({existing[0]} and {binding.name})"
                )
            passages[record.passage_id] = (binding.name, record)
    return indexes, passages


def _source_title(context: StyleContext, evidence: EvidencePassage) -> str:
    source = next(
        (
            candidate
            for candidate in context.sources.sources
            if candidate.id == evidence.source_id
        ),
        None,
    )
    if source is None:
        raise CreativeWriterError(
            f"Passage {evidence.passage_id} has unknown source "
            f"{evidence.source_id}"
        )
    if evidence.selection_id is None:
        return source.work.title
    selection = next(
        (
            candidate
            for candidate in source.selections
            if candidate.id == evidence.selection_id
        ),
        None,
    )
    if selection is None:
        raise CreativeWriterError(
            f"Passage {evidence.passage_id} has unknown source selection "
            f"{evidence.selection_id}"
        )
    return selection.title


def _validate_record_identity(
    entry: StylePacketEntry,
    partition: str,
    focal: PassageRecord,
    evidence: EvidencePassage,
) -> None:
    if (
        focal.witness_id != evidence.witness_id
        or focal.source_id != evidence.source_id
        or focal.selection_id != evidence.selection_id
    ):
        raise CreativeWriterError(
            f"Packet entry {entry.id} passage identity does not match the "
            "approved evidence catalog"
        )
    if entry.authority_tier != evidence.authority_tier:
        raise CreativeWriterError(
            f"Packet entry {entry.id} authority tier does not match the "
            "approved evidence catalog"
        )
    if evidence.authority_tier == 4:
        if partition != "tier4_controls" or entry.kind != "negative_control":
            raise CreativeWriterError(
                f"Tier 4 packet entry {entry.id} must remain a negative "
                "control in the tier4_controls partition"
            )
    elif partition == "tier4_controls" or entry.kind == "negative_control":
        raise CreativeWriterError(
            f"Packet entry {entry.id} has an invalid negative-control "
            "authority or partition"
        )


def _is_contiguous_context_pair(
    left: PassageRecord,
    right: PassageRecord,
) -> bool:
    return (
        left.witness_id == right.witness_id
        and left.heading_path == right.heading_path
        and left.source_ordinal + 1 == right.source_ordinal
    )


def _partition_context_window(
    passages: list[PassageRecord],
    passage_id: str,
    radius: int,
) -> list[PassageRecord]:
    focal = context_window(passages, passage_id, 0)[0]
    focal_index = next(
        index
        for index, passage in enumerate(passages)
        if passage.passage_id == focal.passage_id
    )
    start = focal_index
    while start > 0 and _is_contiguous_context_pair(
        passages[start - 1],
        passages[start],
    ):
        start -= 1
    end = focal_index
    while end + 1 < len(passages) and _is_contiguous_context_pair(
        passages[end],
        passages[end + 1],
    ):
        end += 1
    return context_window(passages[start : end + 1], passage_id, radius)


def _resolve_entries(
    context: StyleContext,
    manifest: StyleReferencePacket,
    indexes: dict[str, list[PassageRecord]],
    passages: dict[str, tuple[str, PassageRecord]],
) -> list[ResolvedStylePacketEntry]:
    resolved: list[ResolvedStylePacketEntry] = []
    for entry in manifest.entries:
        indexed = passages.get(entry.passage_id)
        if indexed is None:
            raise CreativeWriterError(f"Unknown passage ID: {entry.passage_id}")
        partition, focal = indexed
        evidence = context.evidence_catalog.get(entry.passage_id)
        if evidence is None:
            raise CreativeWriterError(
                f"Packet entry {entry.id} passage is not in the approved "
                "evidence catalog"
            )
        _validate_record_identity(entry, partition, focal, evidence)
        radius = (
            entry.context_radius
            if entry.context_radius is not None
            else manifest.context_radius
        )
        resolved.append(
            ResolvedStylePacketEntry(
                manifest_entry=entry,
                focal=focal,
                context=_partition_context_window(
                    indexes[partition],
                    entry.passage_id,
                    radius,
                ),
                source_title=_source_title(context, evidence),
                witness_id=evidence.witness_id,
                authority_tier=evidence.authority_tier,
            )
        )
    return resolved


def _validate_section_order(manifest: StyleReferencePacket) -> None:
    negative_section_started = False
    for entry in manifest.entries:
        if entry.kind == "negative_control" or entry.authority_tier == 4:
            negative_section_started = True
            continue
        if negative_section_started:
            raise CreativeWriterError(
                f"Packet {manifest.id} section ordering is invalid: "
                "negative-control entries must follow all non-control entries; "
                f"entry {entry.id} appears after the negative section began"
            )


def _claim_index(context: StyleContext) -> dict[str, EvidenceClaim]:
    return {claim.id: claim for claim in context.ledger.claims}


def _render_claim(lines: list[str], claim: EvidenceClaim) -> None:
    roles = ", ".join(f"`{role}`" for role in claim.jurisdiction.roles)
    witnesses = ", ".join(
        f"`{witness}`" for witness in claim.jurisdiction.eligible_witness_ids
    )
    lines.extend(
        [
            "",
            f"### `{claim.id}`",
            "",
            f"- Statement: {claim.statement}",
            f"- Final status: `{claim.status}`",
            f"- Classification: `{claim.classification}`",
            f"- Confidence: `{claim.confidence}`",
            f"- Jurisdiction: `{claim.jurisdiction.scope}`",
            f"- Jurisdiction roles: {roles}",
            f"- Eligible witnesses: {witnesses}",
            f"- Scope and limits: {claim.scope_and_limits}",
            (
                "- Prohibited overgeneralisation: "
                f"{claim.prohibited_overgeneralisation}"
            ),
        ]
    )


def _context_position(
    passage: PassageRecord,
    focal: PassageRecord,
) -> str:
    if passage.passage_id == focal.passage_id:
        return "Focal passage"
    if passage.source_ordinal < focal.source_ordinal:
        return "Context before"
    return "Context after"


def _render_entry(
    lines: list[str],
    ordinal: int,
    resolved: ResolvedStylePacketEntry,
) -> None:
    entry = resolved.manifest_entry
    heading_path = " / ".join(resolved.focal.heading_path)
    lines.extend(
        [
            "",
            f"### {ordinal}. {_ENTRY_LABELS[entry.kind]}: `{entry.id}`",
            "",
            f"- Source title: {resolved.source_title}",
            f"- Witness: `{resolved.witness_id}`",
            f"- Authority tier: `{resolved.authority_tier}`",
            f"- Stable passage ID: `{resolved.focal.passage_id}`",
            f"- Heading path: `{heading_path}`",
            f"- Selection rationale: {entry.selection_note}",
            f"- Permitted use: {entry.permitted_use}",
            f"- Claims: {', '.join(f'`{item}`' for item in entry.claim_ids)}",
            f"- Bounded context passages: {len(resolved.context)}",
            "",
            "#### Bounded context",
        ]
    )
    for passage in resolved.context:
        passage_heading = " / ".join(passage.heading_path)
        lines.extend(
            [
                "",
                f"##### {_context_position(passage, resolved.focal)}",
                "",
                f"- Stable passage ID: `{passage.passage_id}`",
                f"- Heading path: `{passage_heading}`",
                f"- Source ordinal: `{passage.source_ordinal}`",
                "",
                "```text",
                passage.original_text,
                "```",
            ]
        )


def _render_reference(
    slug: str,
    context: StyleContext,
    manifest: StyleReferencePacket,
    entries: list[ResolvedStylePacketEntry],
) -> str:
    profile = context.profile
    provenance = profile.provenance
    roles = {role.id: role for role in profile.roles}
    claims = _claim_index(context)
    lines = [
        f"# Style Reference Packet: {manifest.title}",
        "",
        "## Packet identity",
        "",
        f"- Story slug: `{slug}`",
        f"- Packet ID: `{manifest.id}`",
        f"- Profile: `{profile.profile_id}` version `{profile.version}`",
        f"- Profile title: {profile.title}",
        f"- Entries: {len(entries)}",
        "",
        "## Phase 2B provenance",
        "",
        f"- Study ID: `{provenance.study_id}`",
        f"- Approved review run: `{provenance.approved_review_run_id}`",
    ]
    for label, attribute in _PROVENANCE_ARTIFACTS:
        reference = getattr(provenance, attribute)
        lines.append(
            f"- {label}: `{reference.path}` (SHA-256 `{reference.sha256}`)"
        )
    lines.extend(["", "### Passage indexes", ""])
    for name in _INDEX_NAMES:
        reference = getattr(provenance.passage_indexes, name)
        lines.append(
            f"- {_INDEX_LABELS[name]}: `{reference.path}` "
            f"(SHA-256 `{reference.sha256}`)"
        )

    lines.extend(
        [
            "",
            "## Purpose and intended roles",
            "",
            manifest.purpose,
            "",
            "### Intended roles",
        ]
    )
    for role_id in manifest.roles:
        role = roles.get(role_id)
        if role is None:
            raise CreativeWriterError(
                f"Packet {manifest.id} uses unknown profile role {role_id}"
            )
        lines.extend(
            [
                "",
                f"- {role.label} (`{role.id}`): {role.description}",
            ]
        )

    lines.extend(["", "## Eligible Phase 2B claims"])
    for claim_id in manifest.claim_ids:
        claim = claims.get(claim_id)
        if claim is None:
            raise CreativeWriterError(
                f"Packet {manifest.id} uses unknown claim {claim_id}"
            )
        if claim.status not in profile.eligible_claim_statuses:
            raise CreativeWriterError(
                f"Packet {manifest.id} uses ineligible claim {claim_id}"
            )
        _render_claim(lines, claim)

    lines.extend(["", "## Positive examples and authentic variation"])
    positive = [
        (ordinal, entry)
        for ordinal, entry in enumerate(entries, start=1)
        if entry.manifest_entry.kind != "negative_control"
    ]
    if not positive:
        lines.extend(["", "No positive Wells evidence is selected in this packet."])
    for ordinal, entry in positive:
        _render_entry(lines, ordinal, entry)

    lines.extend(
        [
            "",
            "## Negative comparisons",
            "",
            (
                "Tier 4 material is comparative negative evidence only: it is "
                "never a positive Wells model or prescription."
            ),
        ]
    )
    negative = [
        (ordinal, entry)
        for ordinal, entry in enumerate(entries, start=1)
        if entry.manifest_entry.kind == "negative_control"
    ]
    if not negative:
        lines.extend(["", "No Tier 4 negative control is selected in this packet."])
    for ordinal, entry in negative:
        _render_entry(lines, ordinal, entry)

    lines.extend(["", "## Use boundaries", "", "### Prohibited uses", ""])
    lines.extend(f"- {item}" for item in manifest.prohibited_uses)
    lines.extend(
        [
            "",
            "### Anti-copying guidance",
            "",
            manifest.anti_copying_guidance,
        ]
    )
    return "\n".join(lines) + "\n"


def generate_style_reference(
    root: Path,
    slug: str,
    pack: str,
    profile_override: str | None = None,
) -> StyleReferenceResult:
    """Compile one curated style-reference packet as deterministic Markdown."""

    resolved_root, story_dir = _validated_story_dir(root, slug)
    pack_name, manifest_path = _resolve_manifest_path(story_dir, pack)
    context = _load_context(resolved_root, story_dir, profile_override)
    manifest = context.packets.get(pack_name)
    if manifest is None:
        raise CreativeWriterError(
            f"Style profile does not declare packet {pack_name}"
        )
    if manifest.id != pack_name:
        raise CreativeWriterError(
            f"Packet manifest {manifest_path} declares ID {manifest.id}, "
            f"expected {pack_name}"
        )
    _validate_section_order(manifest)

    bindings = _index_bindings(resolved_root, context)
    prepared = _prepare_missing_indexes(
        resolved_root,
        slug,
        bindings,
    )
    indexes, passages = _load_indexes(bindings)
    entries = _resolve_entries(
        context,
        manifest,
        indexes,
        passages,
    )

    output_dir = safe_relative_path(
        resolved_root,
        f"build/{slug}/style/reference-packets",
    )
    ensure_directory(output_dir)
    output_path = safe_relative_path(
        resolved_root,
        f"build/{slug}/style/reference-packets/{pack_name}.md",
    )
    try:
        output_path.write_text(
            _render_reference(slug, context, manifest, entries),
            encoding="utf-8",
        )
    except OSError as exc:
        raise CreativeWriterError(
            f"Unable to write style-reference packet {output_path}: {exc}"
        ) from exc

    return StyleReferenceResult(
        story_slug=slug,
        profile_id=context.profile.profile_id,
        profile_version=context.profile.version,
        pack_name=pack_name,
        manifest_path=manifest_path,
        output_path=output_path,
        entry_count=len(entries),
        source_indexes_prepared=prepared,
    )
