"""Phase 2B source-analysis preparation and deterministic partitioning."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

import yaml
from pydantic import ValidationError

from creative_writer import __version__
from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory, load_yaml_model
from creative_writer.source_analysis_common import (
    canonical_json_bytes,
    safe_relative_path,
    sha256_bytes,
    sha256_file,
)
from creative_writer.models import (
    RetainedSourceRecord,
    SourceStudyAdmission,
    SourcesRegistry,
)
from creative_writer.source_admission import check_source_admission
from creative_writer.source_analysis_models import (
    AnalysisConfig,
    CorpusLock,
    EvidenceLedger,
    EvidenceClaim,
    HoldoutManifest,
    HoldoutWindow,
    PassageRecord,
    PassageIndexBinding,
    QuantitativeProfile,
    ControlComparison,
    HeldoutClaimResult,
    ReviewerRecord,
    ValidationMetricPartition,
    ValidationMetricProvenance,
    ValidationMetricWitness,
    ValidationMetricsDocument,
    ValidationRecord,
    WitnessMetricRecord,
    WitnessDescriptor,
    WitnessHoldouts,
    load_validation_document,
)
from creative_writer.source_passages import (
    context_window,
    parse_markdown_witness,
    parse_passage_partition,
    partition_windows,
    read_passage_index,
    serialize_passage_partition,
    serialize_passage_index,
)
from creative_writer.source_metrics import measure_development, measure_validation_partition
from creative_writer.source_evidence import (
    ValidationIssue,
    ValidationResult,
    collect_evidence_issues,
    collect_leakage_issues,
    collect_observation_issues,
    collect_profile_issues,
    collect_quantitative_profile_issues,
    raise_for_issues,
    validate_evidence_ledger,
    validate_observation_dossiers,
    validate_profile_claim_links,
)
TOOL_VERSION = f"creative-writer {__version__}"
ALGORITHM_VERSION = "tertile-hash-v1"
GENERATED_FILENAMES = {
    "corpus_lock": "corpus-lock.json",
    "development_passage_index": "indexes/development.jsonl",
    "heldout_wells_passage_index": "indexes/heldout-wells.jsonl",
    "tier4_control_passage_index": "indexes/tier4-controls.jsonl",
    "development_metrics": "development-metrics.json",
    "development_metrics_csv": "development-metrics.csv",
    "development_report": "development-report.md",
    "validation_metrics": "validation/current/validation-metrics.json",
    "validation_packet": "validation/current/validation-packet.md",
    "analysis_report": "validation/current/analysis-report.md",
}
CANONICAL_EVIDENCE_FILENAMES = (
    "evidence-ledger.yml",
    "quantitative-profile.yml",
    "wells-profile.md",
    "period-controls.md",
    "validation.md",
)
CANONICAL_PROTOCOL_VALIDATION_BODY = (
    "# Validation Record\n\n"
    "## Protocol state\n\n"
    "The strict YAML front matter records the adopted protocol state. Freeze hashes,\n"
    "holdout results, control comparisons, reviewer findings, claim transitions,\n"
    "and the final profile fingerprint will be recorded only after their respective\n"
    "stages have occurred.\n"
)
PROTOCOL_VALIDATION_SUMMARIES = {
    "holdout_summary": "Held-out material has not been opened at protocol stage.",
    "control_summary": "Tier 4 controls remain quarantined at protocol stage.",
    "reviewer_summary": "Independent review has not begun at protocol stage.",
    "unresolved_uncertainty": "No reviewed claim outcomes exist at protocol stage.",
}


@dataclass(frozen=True, slots=True)
class _ExpandedWitness:
    descriptor: WitnessDescriptor
    markdown_path: Path
    markdown_path_relative: str
    source: RetainedSourceRecord


@dataclass(frozen=True, slots=True)
class SourceAnalysisResult:
    stage: str
    story_slug: str
    witness_count: int
    passage_count: int
    generated_paths: dict[str, Path]
    holdout_path: Path
    holdout_manifest_created: bool

    @property
    def holdout_manifest_verified(self) -> bool:
        return not self.holdout_manifest_created


@dataclass(frozen=True, slots=True)
class _ValidationPreflight:
    config: AnalysisConfig
    validation: ValidationRecord
    candidate_ledger: EvidenceLedger
    candidate_profile_bytes: bytes
    candidate_ledger_bytes: bytes
    candidate_profile_path: Path
    candidate_ledger_path: Path


@dataclass(frozen=True, slots=True)
class _ValidationCorpus:
    lock: CorpusLock
    manifest: HoldoutManifest
    passages: list[PassageRecord]
    heldout_ids: set[str]
    control_ids: set[str]
    witness_tiers: dict[str, int]
    witness_roles: dict[str, list[str]]
    registry: SourcesRegistry


@dataclass(frozen=True, slots=True)
class _ForbiddenPassageLocator:
    """ID-only leakage locator; develop never loads forbidden passage text."""

    passage_id: str
    normalized_text: str = ""


def _sha256(path: Path) -> str:
    return sha256_file(path)


def _window_hash(seed: str, source_id: str, first_passage_id: str) -> str:
    value = f"{seed}:{source_id}:{first_passage_id}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return canonical_json_bytes(payload)


def _story_path(root: Path, slug: str) -> Path:
    return root.resolve(strict=False) / "stories" / slug


def _relative_to_root(path: Path, root: Path) -> str:
    """Return a relative POSIX path across macOS /var and /private/var aliases."""

    return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()


def _normalize_markdown_body(body: str) -> str:
    normalized = body.replace("\r\n", "\n").replace("\r", "\n")
    return normalized if normalized.endswith("\n") else normalized + "\n"


def _registry_path(story_dir: Path, relative: str) -> Path:
    try:
        return safe_relative_path(story_dir, relative)
    except CreativeWriterError as exc:
        raise CreativeWriterError(f"Registry path escapes story directory: {relative}") from exc


def _verify_registry_hash(path: Path, expected: str, label: str) -> None:
    actual = _sha256(path)
    if actual != expected:
        raise CreativeWriterError(
            f"{label} SHA-256 mismatch for {path}: expected {expected}, got {actual}"
        )


def _validate_analysis_authority(
    config: AnalysisConfig, admission: SourceStudyAdmission
) -> None:
    if (
        config.composition_window.start != admission.composition_window.start
        or config.composition_window.end != admission.composition_window.end
    ):
        raise CreativeWriterError(
            "Analysis composition window does not match source admission "
            f"({config.composition_window.start}-{config.composition_window.end} vs "
            f"{admission.composition_window.start}-{admission.composition_window.end})"
        )

    admission_roles: dict[int, set[str]] = {tier: set() for tier in range(1, 6)}
    for source in admission.sources:
        admission_roles[source.authority.tier].update(source.analytical_roles)
        for selection in source.selections:
            admission_roles[source.authority.tier].update(selection.analytical_roles)
    configured_roles = {
        policy.tier: set(policy.analytical_roles) for policy in config.authority_tiers
    }
    if configured_roles != admission_roles:
        differences = [
            f"Tier {tier}: expected {sorted(admission_roles[tier])}, "
            f"configured {sorted(configured_roles[tier])}"
            for tier in range(1, 6)
            if configured_roles[tier] != admission_roles[tier]
        ]
        raise CreativeWriterError(
            "Configured authority tier roles do not match admission source and "
            "selection roles: " + "; ".join(differences)
        )


def _validate_expected_corpus(
    config: AnalysisConfig,
    admission: SourceStudyAdmission,
    registry: SourcesRegistry,
    witnesses: list[_ExpandedWitness],
) -> None:
    expected = config.expected_corpus
    actual_counts = {
        "admission_records": len(admission.sources),
        "retained_sources": len(registry.sources),
        "retained_epubs": len(registry.sources),
        "retained_markdown": len(witnesses),
        "full_work_witnesses": sum(
            item.descriptor.selection_id is None for item in witnesses
        ),
        "selected_witnesses": sum(
            item.descriptor.selection_id is not None for item in witnesses
        ),
    }
    for key, actual in actual_counts.items():
        expected_value = getattr(expected, key)
        if actual != expected_value:
            raise CreativeWriterError(
                f"Expected corpus {key}={expected_value}, got {actual}"
            )

    actual_witness_ids = [item.descriptor.witness_id for item in witnesses]
    if actual_witness_ids != expected.witness_ids:
        raise CreativeWriterError(
            "Expected corpus witness IDs/order do not match: "
            f"expected {expected.witness_ids}, got {actual_witness_ids}"
        )

    actual_excluded_ids = [
        source.id
        for source in admission.sources
        if source.status == "excluded" and source.authority.tier == 5
    ]
    if actual_excluded_ids != expected.excluded_tier5_ids:
        raise CreativeWriterError(
            "Expected corpus excluded Tier 5 IDs do not match: "
            f"expected {expected.excluded_tier5_ids}, got {actual_excluded_ids}"
        )
    if list(config.partition.whole_work_holdouts) != expected.whole_work_holdouts:
        raise CreativeWriterError(
            "Expected corpus whole_work_holdouts do not match the partition: "
            f"expected {expected.whole_work_holdouts}, "
            f"configured {config.partition.whole_work_holdouts}"
        )


def _resolve_generated_paths(
    root: Path, slug: str, config: AnalysisConfig
) -> dict[str, Path]:
    resolved_root = root.resolve(strict=False)
    resolved: dict[str, Path] = {}
    for key, relative in config.generated_paths.items():
        expected_relative = f"build/{slug}/source-study/{GENERATED_FILENAMES[key]}"
        if relative != expected_relative:
            raise CreativeWriterError(
                f"Configured generated path for {key} is `{relative}`; "
                f"expected `{expected_relative}`"
            )
        exact_target = resolved_root / expected_relative
        try:
            exact_target.relative_to(resolved_root)
        except ValueError as exc:
            raise CreativeWriterError(
                f"Generated path for {key} escapes repository root: {relative}"
            ) from exc
        target = exact_target.resolve(strict=False)
        try:
            target.relative_to(resolved_root)
        except ValueError as exc:
            raise CreativeWriterError(
                f"Generated path for {key} escapes repository root through a "
                f"symlink: {relative} -> {target}"
            ) from exc
        if target != exact_target:
            raise CreativeWriterError(
                f"Generated path for {key} redirects through a symlink: "
                f"{relative} -> {target}; expected lexical target {exact_target}"
            )
        resolved[key] = exact_target
    return resolved


def _expanded_witnesses(
    *, story_dir: Path, registry: SourcesRegistry
) -> tuple[list[_ExpandedWitness], dict[str, int]]:
    expanded: list[_ExpandedWitness] = []
    source_tiers: dict[str, int] = {}
    ordinal = 0
    for source in registry.sources:
        source_tiers[source.id] = source.role.tier
        if source.files.markdown is not None:
            assert source.files.markdown_sha256 is not None
            ordinal += 1
            markdown_relative = f"original/{source.files.markdown}"
            markdown_path = story_dir / "original" / source.files.markdown
            if _sha256(markdown_path) != source.files.markdown_sha256:
                raise CreativeWriterError(
                    f"Markdown source fingerprint drift for witness `{source.id}`: "
                    f"{markdown_path}"
                )
            expanded.append(
                _ExpandedWitness(
                    descriptor=WitnessDescriptor(
                        witness_id=source.id,
                        witness_ordinal=ordinal,
                        source_id=source.id,
                        selection_id=None,
                        source_fingerprint=source.files.markdown_sha256,
                    ),
                    markdown_path=markdown_path,
                    markdown_path_relative=markdown_relative,
                    source=source,
                )
            )
            continue

        for selection in source.selections:
            ordinal += 1
            witness_id = f"{source.id}/{selection.id}"
            source_tiers[witness_id] = source.role.tier
            markdown_relative = f"original/{selection.markdown}"
            markdown_path = story_dir / "original" / selection.markdown
            if _sha256(markdown_path) != selection.markdown_sha256:
                raise CreativeWriterError(
                    f"Markdown source fingerprint drift for witness `{witness_id}`: "
                    f"{markdown_path}"
                )
            expanded.append(
                _ExpandedWitness(
                    descriptor=WitnessDescriptor(
                        witness_id=witness_id,
                        witness_ordinal=ordinal,
                        source_id=source.id,
                        selection_id=selection.id,
                        source_fingerprint=selection.markdown_sha256,
                    ),
                    markdown_path=markdown_path,
                    markdown_path_relative=markdown_relative,
                    source=source,
                )
            )
    if not expanded:
        raise CreativeWriterError("The retained corpus expands to no witnesses")
    return expanded, source_tiers


def build_corpus_lock(
    *,
    slug: str,
    config: AnalysisConfig,
    admission: SourceStudyAdmission,
    registry: SourcesRegistry,
    witnesses: list[_ExpandedWitness],
    registry_hashes: dict[str, str],
) -> CorpusLock:
    """Build and strictly validate the timestamp-free corpus authority lock."""

    sources = []
    for source in registry.sources:
        sources.append(
            {
                "id": source.id,
                "tier": source.role.tier,
                "analytical_roles": list(source.role.analytical_roles),
                "permitted_uses": list(source.role.permitted_uses),
                "prohibited_uses": list(source.role.prohibited_uses),
                "epub_path": f"original/{source.files.epub}",
                "epub_sha256": source.files.epub_sha256,
            }
        )
    excluded = [
        source.id
        for source in admission.sources
        if source.status == "excluded" and source.authority.tier == 5
    ]
    full_work_count = sum(1 for item in witnesses if item.descriptor.selection_id is None)
    selected_count = len(witnesses) - full_work_count
    lock = CorpusLock.model_validate(
        {
            "schema_version": 1,
            "analysis": {
                "study_id": config.study_id,
                "story_slug": slug,
                "composition_window": config.composition_window.model_dump(mode="json"),
                "authority_policy_version": config.authority_policy_version,
            },
            "registry_hashes": registry_hashes,
            "sources": sources,
            "witnesses": [
                {
                    "witness_id": item.descriptor.witness_id,
                    "witness_ordinal": item.descriptor.witness_ordinal,
                    "source_id": item.descriptor.source_id,
                    "selection_id": item.descriptor.selection_id,
                    "markdown_path": item.markdown_path_relative,
                    "markdown_sha256": item.descriptor.source_fingerprint,
                }
                for item in witnesses
            ],
            "excluded_tier5_ids": excluded,
            "counts": {
                "admission_records": len(admission.sources),
                "retained_sources": len(registry.sources),
                "retained_epubs": len(registry.sources),
                "retained_markdown": len(witnesses),
                "full_work_witnesses": full_work_count,
                "selected_short_fiction_witnesses": selected_count,
                "witnesses": len(witnesses),
                "excluded_tier5_records": len(excluded),
            },
        }
    )
    return lock


def _select_window_indexes(
    *,
    windows: list[list[PassageRecord]],
    seed: str,
    source_id: str,
    holdout_count: int,
) -> set[int]:
    ranked: list[tuple[str, int, int]] = []
    for index, window in enumerate(windows, start=1):
        ranked.append(
            (
                _window_hash(seed, source_id, window[0].passage_id),
                index,
                min(2, math.floor(3 * (index - 1) / len(windows))),
            )
        )
    ranked.sort(key=lambda item: (item[0], item[1]))
    thirds = {item[2] for item in ranked}
    selected: set[int] = set()
    if holdout_count >= 3 and thirds == {0, 1, 2}:
        for tertile in range(3):
            selected.add(min(item for item in ranked if item[2] == tertile)[1])
    for _, index, _ in ranked:
        if len(selected) >= holdout_count:
            break
        selected.add(index)
    return selected


def select_holdouts(
    passages: list[PassageRecord],
    config: AnalysisConfig,
    witness_tiers: dict[str, int],
) -> list[WitnessHoldouts]:
    """Select deterministic, heading-bounded holdout windows in reading order."""

    by_witness: dict[str, list[PassageRecord]] = {}
    for passage in passages:
        by_witness.setdefault(passage.witness_id, []).append(passage)
    result: list[WitnessHoldouts] = []
    if config.partition.algorithm_version != ALGORITHM_VERSION:
        raise CreativeWriterError(
            f"Unsupported holdout algorithm `{config.partition.algorithm_version}`; "
            f"expected `{ALGORITHM_VERSION}`"
        )
    whole_work = set(config.partition.whole_work_holdouts)
    for witness_id, witness_passages in by_witness.items():
        tier = witness_tiers.get(witness_id)
        if tier is None and "/" in witness_id:
            tier = witness_tiers.get(witness_id.split("/", 1)[0])
        if tier is None:
            raise CreativeWriterError(f"No authority tier is declared for witness `{witness_id}`")
        if tier == 4:
            continue
        if tier not in {1, 2, 3}:
            raise CreativeWriterError(f"Unsupported analysis tier {tier} for witness `{witness_id}`")
        windows = partition_windows(
            witness_passages, config.partition.max_blocks_per_window
        )
        if not windows:
            raise CreativeWriterError(f"Witness `{witness_id}` has no partition windows")
        if witness_id in whole_work:
            holdout_indexes = set(range(1, len(windows) + 1))
        else:
            if len(windows) < 2:
                raise CreativeWriterError(
                    f"Wells witness `{witness_id}` must have at least two partition windows"
                )
            holdout_count = max(1, math.floor(0.2 * len(windows) + 0.5))
            source_id = witness_passages[0].source_id
            holdout_indexes = _select_window_indexes(
                windows=windows,
                seed=config.partition.seed,
                source_id=source_id,
                holdout_count=holdout_count,
            )
        witness_ordinal = witness_passages[0].witness_ordinal
        window_records = [
            HoldoutWindow(
                id=f"w{witness_ordinal:02d}-window-{index:04d}",
                passage_ids=[passage.passage_id for passage in window],
            )
            for index, window in enumerate(windows, start=1)
        ]
        result.append(
            WitnessHoldouts(
                witness_id=witness_id,
                development_windows=[
                    window for index, window in enumerate(window_records, start=1)
                    if index not in holdout_indexes
                ],
                holdout_windows=[
                    window for index, window in enumerate(window_records, start=1)
                    if index in holdout_indexes
                ],
            )
        )
    result.sort(key=lambda item: next(p.witness_ordinal for p in passages if p.witness_id == item.witness_id))
    return result


def _partition_passages(
    passages: list[PassageRecord],
    config: AnalysisConfig,
    source_tiers: dict[str, int],
) -> tuple[dict[str, list[PassageRecord]], list[WitnessHoldouts]]:
    """Partition the one parsed corpus into three disjoint physical sets."""

    holdout_witnesses = select_holdouts(passages, config, source_tiers)
    by_id = {passage.passage_id: passage for passage in passages}
    development_ids = {
        passage_id
        for witness in holdout_witnesses
        for window in witness.development_windows
        for passage_id in window.passage_ids
    }
    heldout_ids = {
        passage_id
        for witness in holdout_witnesses
        for window in witness.holdout_windows
        for passage_id in window.passage_ids
    }
    control_witnesses: list[WitnessHoldouts] = []
    control_ids: set[str] = set()
    for witness_id, witness_passages in sorted(
        ((witness_id, [p for p in passages if p.witness_id == witness_id]) for witness_id in {
            passage.witness_id for passage in passages
            if source_tiers.get(passage.source_id) == 4
        }),
        key=lambda item: by_id[item[1][0].passage_id].witness_ordinal,
    ):
        control_ids.update(passage.passage_id for passage in witness_passages)
        control_witnesses.append(
            WitnessHoldouts(
                witness_id=witness_id,
                development_windows=[],
                holdout_windows=[
                    HoldoutWindow(
                        id=f"w{witness_passages[0].witness_ordinal:02d}-window-0001",
                        passage_ids=[p.passage_id for p in witness_passages],
                    )
                ],
            )
        )

    all_ids = set(by_id)
    if development_ids & heldout_ids or development_ids & control_ids or heldout_ids & control_ids:
        raise CreativeWriterError("Physical passage partitions are not pairwise disjoint")
    if development_ids | heldout_ids | control_ids != all_ids:
        missing = sorted(all_ids - (development_ids | heldout_ids | control_ids))
        extra = sorted((development_ids | heldout_ids | control_ids) - all_ids)
        raise CreativeWriterError(
            f"Physical passage partitions do not equal the retained corpus; missing={missing}, extra={extra}"
        )
    for partition_name, ids in (("development", development_ids), ("heldout_wells", heldout_ids)):
        if any(source_tiers.get(by_id[passage_id].source_id) not in {1, 2, 3} for passage_id in ids):
            raise CreativeWriterError(f"{partition_name} partition can contain only retained Tier 1-3 passages")
    if any(source_tiers.get(by_id[passage_id].source_id) != 4 for passage_id in control_ids):
        raise CreativeWriterError("Tier 4 control partition must contain every and only Tier 4 passage")

    witnesses = sorted(
        [*holdout_witnesses, *control_witnesses],
        key=lambda item: by_id[item.holdout_windows[0].passage_ids[0]].witness_ordinal,
    )
    return (
        {
            "development": [by_id[passage_id] for passage_id in sorted(development_ids, key=lambda item: (by_id[item].witness_ordinal, by_id[item].source_ordinal))],
            "heldout_wells": [by_id[passage_id] for passage_id in sorted(heldout_ids, key=lambda item: (by_id[item].witness_ordinal, by_id[item].source_ordinal))],
            "tier4_controls": [by_id[passage_id] for passage_id in sorted(control_ids, key=lambda item: (by_id[item].witness_ordinal, by_id[item].source_ordinal))],
        },
        witnesses,
    )


def _build_holdout_manifest(
    *,
    config: AnalysisConfig,
    registry_hashes: dict[str, str],
    registry: SourcesRegistry,
    witnesses: list[_ExpandedWitness],
    passages: list[PassageRecord],
    source_tiers: dict[str, int],
    partitions: dict[str, list[PassageRecord]],
    corpus_lock_bytes: bytes,
    created_at: datetime,
) -> HoldoutManifest:
    source_fingerprints: dict[str, str] = {}
    for source in registry.sources:
        source_fingerprints[f"source/{source.id}/epub"] = source.files.epub_sha256
    for witness in witnesses:
        source_fingerprints[
            f"witness/{witness.descriptor.witness_id}/markdown"
        ] = witness.descriptor.source_fingerprint
    return HoldoutManifest.model_validate(
        {
            "schema_version": 2,
            "partition_seed": config.partition.seed,
            "algorithm_version": config.partition.algorithm_version,
            "tool_version": TOOL_VERSION,
            "created_at": created_at,
            "registry_hashes": registry_hashes,
            "corpus_lock": {
                "path": config.generated_paths["corpus_lock"],
                "sha256": sha256_bytes(corpus_lock_bytes),
            },
            "development_passage_index": _index_binding(
                config.generated_paths["development_passage_index"],
                "development",
                partitions["development"],
            ),
            "heldout_wells_passage_index": _index_binding(
                config.generated_paths["heldout_wells_passage_index"],
                "heldout_wells",
                partitions["heldout_wells"],
            ),
            "tier4_control_passage_index": _index_binding(
                config.generated_paths["tier4_control_passage_index"],
                "tier4_controls",
                partitions["tier4_controls"],
            ),
            "source_fingerprints": source_fingerprints,
            "whole_work_holdouts": list(config.partition.whole_work_holdouts),
            "witnesses": [item.model_dump(mode="json") for item in _partition_passages(passages, config, source_tiers)[1]],
        }
    )


def _index_binding(
    path: str, partition: str, records: list[PassageRecord]
) -> dict[str, object]:
    witness_ids: list[str] = []
    for record in records:
        if record.witness_id not in witness_ids:
            witness_ids.append(record.witness_id)
    return {
        "path": path,
        "sha256": sha256_bytes(serialize_passage_partition(records)),
        "partition": partition,
        "passage_count": len(records),
        "witness_ids": witness_ids,
    }


def _validate_existing_json(path: Path, expected: CorpusLock, label: str) -> None:
    if not path.exists():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        actual = CorpusLock.model_validate(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as exc:
        raise CreativeWriterError(f"Existing {label} is invalid: {path}: {exc}") from exc
    if actual.model_dump(mode="json") != expected.model_dump(mode="json"):
        raise CreativeWriterError(f"Existing {label} differs from the current corpus")


def _load_existing_manifest(path: Path) -> HoldoutManifest | None:
    if not path.exists():
        return None
    try:
        return load_yaml_model(path, HoldoutManifest)
    except CreativeWriterError as exc:
        raise CreativeWriterError(f"Existing holdout manifest is invalid: {path}: {exc}") from exc


def _cleanup_paths(paths: list[tuple[Path, str]]) -> list[str]:
    failures: list[str] = []
    for path, label in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            failures.append(
                f"{label} `{path}` failed: {exc}; residual path: `{path}`"
            )
    return failures


def _validate_manifest_passages(manifest: HoldoutManifest, passage_ids: set[str]) -> None:
    for witness in manifest.witnesses:
        for window in [*witness.development_windows, *witness.holdout_windows]:
            for passage_id in window.passage_ids:
                if passage_id not in passage_ids:
                    raise CreativeWriterError(
                        f"Existing holdout manifest has unresolved passage ID `{passage_id}` "
                        f"for witness `{witness.witness_id}`"
                    )


def _parse_retained_witnesses(witnesses: list[_ExpandedWitness]) -> list[PassageRecord]:
    """Reparse and validate every current retained witness in reading order."""

    passages: list[PassageRecord] = []
    seen_passage_ids: set[str] = set()
    for witness in witnesses:
        try:
            parsed = parse_markdown_witness(witness.markdown_path, witness.descriptor)
        except CreativeWriterError as exc:
            raise CreativeWriterError(
                f"Pandoc parsing failed for witness `{witness.descriptor.witness_id}` "
                f"({witness.markdown_path}): {exc}"
            ) from exc
        if not parsed:
            raise CreativeWriterError(
                f"Pandoc produced an empty passage index for witness "
                f"`{witness.descriptor.witness_id}`"
            )
        for passage in parsed:
            if passage.passage_id in seen_passage_ids:
                raise CreativeWriterError(
                    f"Duplicate passage ID `{passage.passage_id}` for witness "
                    f"`{witness.descriptor.witness_id}`"
                )
            if (
                passage.witness_id != witness.descriptor.witness_id
                or passage.witness_ordinal != witness.descriptor.witness_ordinal
                or passage.source_fingerprint != witness.descriptor.source_fingerprint
            ):
                raise CreativeWriterError(
                    f"Stale or unresolved passage identity for witness "
                    f"`{witness.descriptor.witness_id}`: {passage.passage_id}"
                )
            seen_passage_ids.add(passage.passage_id)
            passages.append(passage)
    if not passages:
        raise CreativeWriterError("The passage index is empty")
    return passages


def _stage_file(path: Path, payload: bytes) -> Path:
    temporary_path: Path | None = None
    try:
        ensure_directory(path.parent)
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        cleanup_errors = (
            _cleanup_paths([(temporary_path, "temporary cleanup")])
            if temporary_path is not None
            else []
        )
        detail = f"Unable to stage generated artifact {path}: {exc}"
        if cleanup_errors:
            detail += "\nCleanup errors:\n" + "\n".join(
                f"- {error}" for error in cleanup_errors
            )
        raise CreativeWriterError(detail) from exc
    assert temporary_path is not None
    return temporary_path


def _commit_staged(staged: list[tuple[Path, Path]]) -> None:
    backups: dict[Path, Path] = {}
    installed: list[Path] = []
    restored: set[Path] = set()
    transaction_id = uuid.uuid4().hex
    original_failure: OSError | None = None
    recovery_errors: list[str] = []

    try:
        for target, temporary in staged:
            if target.exists():
                backup = target.parent / f".{target.name}.{transaction_id}.bak"
                os.replace(target, backup)
                backups[target] = backup
            os.replace(temporary, target)
            installed.append(target)
    except OSError as exc:
        original_failure = exc
        recovery_errors.extend(
            _cleanup_paths(
                [(target, "removal during rollback") for target in reversed(installed)]
            )
        )
        for target, backup in backups.items():
            if backup.exists():
                try:
                    os.replace(backup, target)
                except OSError as restore_error:
                    recovery_errors.append(
                        f"restoration of backup `{backup}` to `{target}` failed: "
                        f"{restore_error}; residual path: `{backup}`"
                    )
                else:
                    restored.add(target)
    finally:
        recovery_errors.extend(
            _cleanup_paths(
                [(temporary, "temporary cleanup") for _, temporary in staged]
            )
        )
        for target, backup in backups.items():
            if original_failure is not None and target not in restored:
                if backup.exists():
                    recovery_errors.append(
                        f"residual un-restored backup `{backup}` remains; "
                        f"residual path: `{backup}`"
                    )
                continue
            recovery_errors.extend(_cleanup_paths([(backup, "backup cleanup")]))

    if original_failure is not None:
        detail = (
            "Unable to replace generated artifacts atomically: "
            f"{original_failure}"
        )
        if recovery_errors:
            detail += "\nRecovery errors:\n" + "\n".join(
                f"- {error}" for error in recovery_errors
            )
        raise CreativeWriterError(detail) from original_failure
    if recovery_errors:
        raise CreativeWriterError(
            "Generated artifacts installed, but cleanup left residual paths or "
            "errors:\n" + "\n".join(f"- {error}" for error in recovery_errors)
        ) from OSError(recovery_errors[0])


def _prepare(root: Path, slug: str) -> SourceAnalysisResult:
    admission_result = check_source_admission(root, slug)
    if not admission_result.ok:
        details = "\n".join(f"- {error}" for error in admission_result.errors)
        raise CreativeWriterError(f"Source admission failed for `{slug}`:\n{details}")

    story_dir = _story_path(root, slug)
    analysis_path = story_dir / "source-study" / "analysis.yml"
    config = load_yaml_model(analysis_path, AnalysisConfig)
    generated_paths = _resolve_generated_paths(root, slug, config)
    admission_path = _registry_path(story_dir, config.admission_registry.path)
    source_path = _registry_path(story_dir, config.source_registry.path)
    _verify_registry_hash(
        admission_path, config.admission_registry.sha256, "Admission registry"
    )
    _verify_registry_hash(source_path, config.source_registry.sha256, "Source registry")
    admission = load_yaml_model(admission_path, SourceStudyAdmission)
    registry = load_yaml_model(source_path, SourcesRegistry)
    _validate_analysis_authority(config, admission)
    witnesses, source_tiers = _expanded_witnesses(story_dir=story_dir, registry=registry)
    _validate_expected_corpus(config, admission, registry, witnesses)
    registry_hashes = {
        config.admission_registry.path: config.admission_registry.sha256,
        config.source_registry.path: config.source_registry.sha256,
    }
    lock = build_corpus_lock(
        slug=slug,
        config=config,
        admission=admission,
        registry=registry,
        witnesses=witnesses,
        registry_hashes=registry_hashes,
    )

    passages = _parse_retained_witnesses(witnesses)
    partitions, _ = _partition_passages(passages, config, source_tiers)
    partition_payloads = {
        name: serialize_passage_partition(records)
        for name, records in partitions.items()
    }
    lock_payload = _canonical_json(lock.model_dump(mode="json"))
    expected_manifest = _build_holdout_manifest(
        config=config,
        registry_hashes=registry_hashes,
        registry=registry,
        witnesses=witnesses,
        passages=passages,
        source_tiers=source_tiers,
        partitions=partitions,
        corpus_lock_bytes=lock_payload,
        created_at=datetime.now(timezone.utc),
    )

    lock_path = generated_paths["corpus_lock"]
    index_paths = {
        "development": generated_paths["development_passage_index"],
        "heldout_wells": generated_paths["heldout_wells_passage_index"],
        "tier4_controls": generated_paths["tier4_control_passage_index"],
    }
    holdout_path = story_dir / "source-study" / "holdouts.yml"
    _validate_existing_json(lock_path, lock, "corpus lock")
    for partition, index_path in index_paths.items():
        if index_path.exists():
            try:
                existing_index = index_path.read_bytes()
            except OSError as exc:
                raise CreativeWriterError(f"Unable to read existing passage index {index_path}: {exc}") from exc
            if existing_index != partition_payloads[partition]:
                raise CreativeWriterError(
                    f"Existing {partition} passage index differs from the current corpus"
                )
    existing_manifest = _load_existing_manifest(holdout_path)
    if existing_manifest is not None:
        _validate_manifest_passages(existing_manifest, {passage.passage_id for passage in passages})
        expected_manifest = _build_holdout_manifest(
            config=config,
            registry_hashes=registry_hashes,
            registry=registry,
            witnesses=witnesses,
            passages=passages,
            source_tiers=source_tiers,
            partitions=partitions,
            corpus_lock_bytes=lock_payload,
            created_at=existing_manifest.created_at,
        )
        if existing_manifest.model_dump(mode="json") != expected_manifest.model_dump(mode="json"):
            raise CreativeWriterError("Existing holdout manifest differs from the current partition")
        manifest_created = False
    else:
        manifest_created = True

    manifest_payload = yaml.safe_dump(
        expected_manifest.model_dump(),
        sort_keys=False,
        allow_unicode=True,
    ).encode("utf-8")
    staged: list[tuple[Path, Path]] = []
    try:
        staged.append((lock_path, _stage_file(lock_path, lock_payload)))
        staged.extend(
            (index_paths[partition], _stage_file(index_paths[partition], payload))
            for partition, payload in partition_payloads.items()
        )
        if manifest_created:
            staged.append((holdout_path, _stage_file(holdout_path, manifest_payload)))
        _commit_staged(staged)
    except (CreativeWriterError, OSError) as exc:
        cleanup_errors = _cleanup_paths(
            [(temporary, "outer temporary cleanup") for _, temporary in staged]
        )
        if cleanup_errors:
            detail = str(exc) + "\nOuter cleanup errors:\n" + "\n".join(
                f"- {error}" for error in cleanup_errors
            )
            raise CreativeWriterError(detail) from exc
        if isinstance(exc, OSError):
            raise CreativeWriterError(
                f"Unable to prepare source analysis for `{slug}`: {exc}"
            ) from exc
        raise

    return SourceAnalysisResult(
        stage="prepare",
        story_slug=slug,
        witness_count=len(witnesses),
        passage_count=len(passages),
        generated_paths=generated_paths,
        holdout_path=holdout_path,
        holdout_manifest_created=manifest_created,
    )


def _require_committed_holdout(root: Path, holdout_path: Path) -> None:
    """Require the partition lock to exist in Git before development opens."""

    relative = _relative_to_root(holdout_path, root)
    try:
        listed = subprocess.run(
            ["git", "ls-files", "--error-unmatch", relative],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", relative],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise CreativeWriterError(
            f"Unable to verify that holdout manifest is tracked/committed: {exc}"
        ) from exc
    if listed.returncode != 0 or listed.stdout.strip() != relative:
        raise CreativeWriterError(
            f"Development requires holdout manifest `{relative}` to be tracked/committed"
        )
    if status.returncode != 0:
        detail = status.stderr.strip() or "git status failed"
        raise CreativeWriterError(f"Unable to verify committed holdout manifest: {detail}")
    if status.stdout.strip():
        raise CreativeWriterError(
            f"Development requires holdout manifest `{relative}` to be committed; working-tree changes remain"
        )


def _load_optional_yaml_model(path: Path, model: type[Any]) -> Any | None:
    if not path.exists():
        return None
    return load_yaml_model(path, model)


def _read_bound_partition(
    path: Path,
    binding: PassageIndexBinding,
    *,
    expected_path: str,
    expected_partition: str,
) -> list[PassageRecord]:
    """Read exactly one physical index and verify its manifest binding."""

    if binding.path != expected_path or binding.partition != expected_partition:
        raise CreativeWriterError(
            f"Manifest binding for {expected_partition} does not match configured path or partition"
        )
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise CreativeWriterError(f"Unable to read {expected_partition} passage index {path}: {exc}") from exc
    if sha256_bytes(data) != binding.sha256:
        raise CreativeWriterError(f"{expected_partition} passage index SHA-256 does not match manifest binding")
    records = parse_passage_partition(data)
    if len(records) != binding.passage_count:
        raise CreativeWriterError(f"{expected_partition} passage count does not match manifest binding")
    actual_witness_ids: list[str] = []
    for record in records:
        if record.witness_id not in actual_witness_ids:
            actual_witness_ids.append(record.witness_id)
    if actual_witness_ids != binding.witness_ids:
        raise CreativeWriterError(f"{expected_partition} witness IDs do not match manifest binding")
    return records


def _manifest_partition_ids(
    manifest: HoldoutManifest, partition: str
) -> set[str]:
    ids: set[str] = set()
    for witness in manifest.witnesses:
        windows = (
            witness.development_windows
            if partition == "development"
            else witness.holdout_windows
        )
        for window in windows:
            ids.update(window.passage_ids)
    return ids


def _validate_lock_registry_metadata(
    config: AnalysisConfig,
    lock: CorpusLock,
    admission: SourceStudyAdmission,
    registry: SourcesRegistry,
    *,
    slug: str,
) -> dict[str, int]:
    """Validate registry/lock metadata without touching retained Markdown."""

    if lock.analysis.study_id != config.study_id or lock.analysis.story_slug != slug:
        raise CreativeWriterError("Committed corpus lock identity does not match analysis.yml")
    expected_registry_hashes = {
        config.admission_registry.path: config.admission_registry.sha256,
        config.source_registry.path: config.source_registry.sha256,
    }
    if lock.registry_hashes != expected_registry_hashes:
        raise CreativeWriterError("Committed corpus lock registry hashes do not match analysis.yml")
    _validate_analysis_authority(config, admission)
    source_tiers = {source.id: source.role.tier for source in registry.sources}
    registry_ids = [source.id for source in registry.sources]
    lock_ids = [source.id for source in lock.sources]
    if lock_ids != registry_ids:
        raise CreativeWriterError("Committed corpus lock source IDs do not match the source registry")
    for source in lock.sources:
        if source_tiers.get(source.id) != source.tier:
            raise CreativeWriterError(f"Committed corpus lock tier differs for `{source.id}`")
    expected_witness_ids = config.expected_corpus.witness_ids
    actual_witness_ids = [witness.witness_id for witness in lock.witnesses]
    if actual_witness_ids != expected_witness_ids:
        raise CreativeWriterError("Committed corpus lock witness IDs do not match analysis.yml")
    for witness in lock.witnesses:
        if witness.source_id not in source_tiers:
            raise CreativeWriterError(f"Committed corpus lock has unknown source `{witness.source_id}`")
    return source_tiers


def _load_development_partition(
    root: Path, slug: str, config: AnalysisConfig
) -> tuple[CorpusLock, HoldoutManifest, list[PassageRecord], dict[str, int], SourceStudyAdmission, SourcesRegistry]:
    story_dir = _story_path(root, slug)
    generated_paths = _resolve_generated_paths(root, slug, config)
    holdout_path = story_dir / "source-study" / "holdouts.yml"
    _require_committed_holdout(root, holdout_path)
    lock_path = generated_paths["corpus_lock"]
    development_path = generated_paths["development_passage_index"]
    if not lock_path.exists() or not development_path.exists() or not holdout_path.exists():
        raise CreativeWriterError(
            "Development requires the prepared corpus lock, development passage index, and holdout manifest"
        )
    try:
        lock_bytes = lock_path.read_bytes()
        lock = CorpusLock.model_validate(json.loads(lock_bytes.decode("utf-8")))
        manifest = _load_existing_manifest(holdout_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError, CreativeWriterError) as exc:
        raise CreativeWriterError(f"Committed corpus lock/manifest could not be loaded: {exc}") from exc
    if manifest is None:
        raise CreativeWriterError(f"Missing committed holdout manifest: {holdout_path}")
    if manifest.schema_version != 2:
        raise CreativeWriterError("Development requires a schema-v2 holdout manifest")
    if manifest.corpus_lock.path != _relative_to_root(lock_path, root):
        raise CreativeWriterError("Corpus-lock manifest binding path does not match configured path")
    if manifest.corpus_lock.sha256 != sha256_bytes(lock_bytes):
        raise CreativeWriterError("Corpus-lock manifest binding hash does not match corpus-lock bytes")
    expected_registry_hashes = {
        config.admission_registry.path: config.admission_registry.sha256,
        config.source_registry.path: config.source_registry.sha256,
    }
    if manifest.registry_hashes != expected_registry_hashes:
        raise CreativeWriterError("Committed holdout manifest registry hashes do not match analysis.yml")
    if (
        manifest.partition_seed != config.partition.seed
        or manifest.algorithm_version != config.partition.algorithm_version
        or manifest.whole_work_holdouts != list(config.partition.whole_work_holdouts)
    ):
        raise CreativeWriterError("Committed holdout manifest differs from the configured partition")
    expected_index_paths = {
        "development": _relative_to_root(generated_paths["development_passage_index"], root),
        "heldout_wells": _relative_to_root(generated_paths["heldout_wells_passage_index"], root),
        "tier4_controls": _relative_to_root(generated_paths["tier4_control_passage_index"], root),
    }
    if any(
        binding.path != expected_index_paths[partition]
        for partition, binding in {
            "development": manifest.development_passage_index,
            "heldout_wells": manifest.heldout_wells_passage_index,
            "tier4_controls": manifest.tier4_control_passage_index,
        }.items()
    ):
        raise CreativeWriterError("Committed holdout manifest index paths do not match analysis.yml")
    admission_path = _registry_path(story_dir, config.admission_registry.path)
    source_path = _registry_path(story_dir, config.source_registry.path)
    _verify_registry_hash(admission_path, config.admission_registry.sha256, "Admission registry")
    _verify_registry_hash(source_path, config.source_registry.sha256, "Source registry")
    admission = load_yaml_model(admission_path, SourceStudyAdmission)
    registry = load_yaml_model(source_path, SourcesRegistry)
    source_tiers = _validate_lock_registry_metadata(config, lock, admission, registry, slug=slug)
    records = _read_bound_partition(
        development_path,
        manifest.development_passage_index,
        expected_path=_relative_to_root(development_path, root),
        expected_partition="development",
    )
    expected_ids = _manifest_partition_ids(manifest, "development")
    actual_ids = {record.passage_id for record in records}
    if actual_ids != expected_ids:
        raise CreativeWriterError("Development index membership differs from manifest development windows")
    for record in records:
        if source_tiers.get(record.source_id) not in {1, 2, 3}:
            raise CreativeWriterError("Development index contains a non-Wells retained passage")
    return lock, manifest, records, source_tiers, admission, registry


_FULL_COMMIT_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


def _git_bytes(root: Path, arguments: list[str]) -> bytes:
    """Run a non-interactive Git object query without a shell or filters."""

    environment = os.environ.copy()
    environment.update(
        {
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PAGER": "cat",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_EXTERNAL_DIFF": "",
        }
    )
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            shell=False,
        )
    except OSError as exc:
        raise CreativeWriterError(f"Unable to run Git preflight: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise CreativeWriterError(
            f"Git preflight command failed (`git {' '.join(arguments)}`): "
            + (detail or f"exit status {result.returncode}")
        )
    return result.stdout


def _git_stdout(root: Path, arguments: list[str]) -> str:
    return _git_bytes(root, arguments).decode("utf-8", errors="strict")


def _candidate_git_blob(root: Path, commit: str, relative: str) -> bytes:
    tree = _git_bytes(root, ["ls-tree", "-z", "--full-tree", commit, "--", relative])
    entries = tree.split(b"\0") if tree else []
    matching = [entry for entry in entries if entry]
    if len(matching) != 1:
        raise CreativeWriterError(
            f"Candidate commit `{commit}` does not contain exactly one tracked entry for `{relative}`"
        )
    header, path_bytes = matching[0].split(b"\t", 1)
    mode, object_type, object_id = header.decode("ascii").split(" ")
    if path_bytes.decode("utf-8") != relative:
        raise CreativeWriterError(f"Candidate Git path mismatch for `{relative}`")
    if mode in {"120000", "160000"} or object_type != "blob":
        raise CreativeWriterError(
            f"Candidate file `{relative}` is not a regular Git blob (mode {mode}, type {object_type})"
        )
    if not re.fullmatch(r"[0-9a-f]{40,64}", object_id):
        raise CreativeWriterError(f"Candidate Git object ID is malformed for `{relative}`")
    return _git_bytes(
        root,
        [
            "show",
            "--no-ext-diff",
            "--no-textconv",
            "--format=",
            f"{commit}:{relative}",
        ],
    )


def _verify_candidate_commit(root: Path, commit: str) -> None:
    if not _FULL_COMMIT_RE.fullmatch(commit):
        raise CreativeWriterError(
            "candidate_commit must be a full lowercase 40- or 64-hex Git object"
        )
    try:
        resolved = _git_stdout(root, ["rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}"])
        head = _git_stdout(root, ["rev-parse", "--verify", "--quiet", "HEAD"]).strip()
    except CreativeWriterError as exc:
        raise CreativeWriterError(f"Candidate commit cannot be resolved: {commit}") from exc
    resolved = resolved.strip()
    if resolved != commit:
        raise CreativeWriterError(
            f"Candidate commit must resolve as the supplied full object: {commit}"
        )
    if resolved == head:
        raise CreativeWriterError("Candidate commit must be older than and not equal to HEAD")
    ancestry = _git_bytes(root, ["merge-base", "--is-ancestor", commit, "HEAD"])
    del ancestry


def _verify_current_candidate_file(root: Path, path: Path, relative: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise CreativeWriterError(f"Candidate file must be a clean regular file: {relative}")
    tracked = _git_stdout(root, ["ls-files", "--error-unmatch", "--", relative]).strip()
    if tracked != relative:
        raise CreativeWriterError(f"Candidate file is not tracked: {relative}")
    status = _git_stdout(root, ["status", "--porcelain=v1", "--untracked-files=all", "--", relative])
    if status.strip():
        raise CreativeWriterError(f"Candidate file is dirty in the working tree: {relative}")


def _preflight_validation(root: Path, slug: str) -> _ValidationPreflight:
    """Read only analysis.yml and validation.md until candidate Git checks pass."""

    story_dir = _story_path(root, slug)
    source_study = story_dir / "source-study"
    analysis_path = source_study / "analysis.yml"
    validation_path = source_study / "validation.md"
    config = load_yaml_model(analysis_path, AnalysisConfig)
    if config.study_status not in {"candidate_frozen", "validated"}:
        raise CreativeWriterError(
            "Validation requires analysis.yml study_status candidate_frozen or validated"
        )
    validation, _ = load_validation_document(validation_path)
    if validation.stage != config.study_status:
        raise CreativeWriterError(
            f"Validation record stage `{validation.stage}` does not match config status `{config.study_status}`"
        )
    if not validation.candidate_commit:
        raise CreativeWriterError("Validation record is missing candidate_commit")
    _verify_candidate_commit(root, validation.candidate_commit)

    candidate_profile_path = source_study / "wells-profile.md"
    candidate_ledger_path = source_study / "evidence-ledger.yml"
    profile_relative = _relative_to_root(candidate_profile_path, root)
    ledger_relative = _relative_to_root(candidate_ledger_path, root)
    _verify_current_candidate_file(root, candidate_profile_path, profile_relative)
    _verify_current_candidate_file(root, candidate_ledger_path, ledger_relative)
    candidate_profile_bytes = _candidate_git_blob(root, validation.candidate_commit, profile_relative)
    candidate_ledger_bytes = _candidate_git_blob(root, validation.candidate_commit, ledger_relative)
    try:
        current_profile_bytes = candidate_profile_path.read_bytes()
        current_ledger_bytes = candidate_ledger_path.read_bytes()
    except OSError as exc:
        raise CreativeWriterError(f"Unable to read clean candidate files: {exc}") from exc
    if config.study_status == "candidate_frozen" and (
        current_profile_bytes != candidate_profile_bytes
        or current_ledger_bytes != candidate_ledger_bytes
    ):
        raise CreativeWriterError("Current candidate profile or ledger bytes drift from the frozen Git commit")
    profile_hash = hashlib.sha256(candidate_profile_bytes).hexdigest()
    ledger_hash = hashlib.sha256(candidate_ledger_bytes).hexdigest()
    if profile_hash != validation.candidate_profile_sha256:
        raise CreativeWriterError(
            f"Candidate profile SHA-256 mismatch: expected {validation.candidate_profile_sha256}, got {profile_hash}"
        )
    if ledger_hash != validation.candidate_ledger_sha256:
        raise CreativeWriterError(
            f"Candidate ledger SHA-256 mismatch: expected {validation.candidate_ledger_sha256}, got {ledger_hash}"
        )
    try:
        raw_ledger = yaml.safe_load(candidate_ledger_bytes.decode("utf-8"))
        candidate_ledger = EvidenceLedger.model_validate(raw_ledger)
    except (UnicodeError, yaml.YAMLError, ValidationError, TypeError) as exc:
        raise CreativeWriterError(f"Frozen candidate ledger is not valid structured YAML: {exc}") from exc
    if candidate_ledger.study_id != config.study_id:
        raise CreativeWriterError("Frozen candidate ledger study identity does not match analysis.yml")
    if candidate_ledger.stage != "development":
        raise CreativeWriterError("Frozen candidate ledger must remain at development stage")
    return _ValidationPreflight(
        config=config,
        validation=validation,
        candidate_ledger=candidate_ledger,
        candidate_profile_bytes=candidate_profile_bytes,
        candidate_ledger_bytes=candidate_ledger_bytes,
        candidate_profile_path=candidate_profile_path,
        candidate_ledger_path=candidate_ledger_path,
    )


def _load_validation_corpus(
    root: Path, slug: str, config: AnalysisConfig, *, include_controls: bool
) -> _ValidationCorpus:
    """Load held-out Wells, then controls only when the caller is authorized."""

    story_dir = _story_path(root, slug)
    generated_paths = _resolve_generated_paths(root, slug, config)
    lock_path = generated_paths["corpus_lock"]
    manifest_path = story_dir / "source-study" / "holdouts.yml"
    try:
        lock_bytes = lock_path.read_bytes()
        lock = CorpusLock.model_validate(json.loads(lock_bytes.decode("utf-8")))
        manifest = _load_existing_manifest(manifest_path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError, CreativeWriterError) as exc:
        raise CreativeWriterError(f"Validation corpus lock/manifest could not be loaded: {exc}") from exc
    if manifest is None:
        raise CreativeWriterError(f"Missing committed holdout manifest: {manifest_path}")
    if manifest.schema_version != 2:
        raise CreativeWriterError("Validation requires a schema-v2 holdout manifest")
    if manifest.corpus_lock.path != _relative_to_root(lock_path, root) or manifest.corpus_lock.sha256 != sha256_bytes(lock_bytes):
        raise CreativeWriterError("Corpus-lock manifest binding does not match corpus-lock bytes")
    expected_registry_hashes = {
        config.admission_registry.path: config.admission_registry.sha256,
        config.source_registry.path: config.source_registry.sha256,
    }
    if lock.registry_hashes != expected_registry_hashes or manifest.registry_hashes != expected_registry_hashes:
        raise CreativeWriterError("Committed corpus registry hashes do not match analysis.yml")
    if (
        manifest.partition_seed != config.partition.seed
        or manifest.algorithm_version != config.partition.algorithm_version
        or manifest.whole_work_holdouts != list(config.partition.whole_work_holdouts)
    ):
        raise CreativeWriterError("Committed holdout manifest differs from the configured partition")

    expected_index_paths = {
        "development": _relative_to_root(generated_paths["development_passage_index"], root),
        "heldout_wells": _relative_to_root(generated_paths["heldout_wells_passage_index"], root),
        "tier4_controls": _relative_to_root(generated_paths["tier4_control_passage_index"], root),
    }
    if any(
        binding.path != expected_index_paths[partition]
        for partition, binding in {
            "development": manifest.development_passage_index,
            "heldout_wells": manifest.heldout_wells_passage_index,
            "tier4_controls": manifest.tier4_control_passage_index,
        }.items()
    ):
        raise CreativeWriterError("Committed holdout manifest index paths do not match analysis.yml")

    admission_path = _registry_path(story_dir, config.admission_registry.path)
    source_path = _registry_path(story_dir, config.source_registry.path)
    _verify_registry_hash(admission_path, config.admission_registry.sha256, "Admission registry")
    _verify_registry_hash(source_path, config.source_registry.sha256, "Source registry")
    admission = load_yaml_model(admission_path, SourceStudyAdmission)
    registry = load_yaml_model(source_path, SourcesRegistry)
    source_tiers = _validate_lock_registry_metadata(config, lock, admission, registry, slug=slug)
    source_roles = {
        source.id: list(source.role.analytical_roles) for source in registry.sources
    }
    lock_tiers = {
        witness.witness_id: source_tiers.get(witness.source_id, 0)
        for witness in lock.witnesses
    }
    heldout_witness_ids = set(manifest.heldout_wells_passage_index.witness_ids)
    heldout_ids = {
        passage_id
        for witness in manifest.witnesses
        if witness.witness_id in heldout_witness_ids
        for window in witness.holdout_windows
        for passage_id in window.passage_ids
    }
    heldout_path = generated_paths["heldout_wells_passage_index"]
    heldout_records = _read_bound_partition(
        heldout_path,
        manifest.heldout_wells_passage_index,
        expected_path=_relative_to_root(heldout_path, root),
        expected_partition="heldout_wells",
    )
    if {record.passage_id for record in heldout_records} != heldout_ids:
        raise CreativeWriterError("Held-out Wells index membership differs from manifest")
    if any(source_tiers.get(record.source_id) not in {1, 2, 3} for record in heldout_records):
        raise CreativeWriterError("Held-out Wells index contains a non-Wells passage")
    control_ids: set[str] = set()
    control_records: list[PassageRecord] = []
    if include_controls:
        control_witness_ids = set(manifest.tier4_control_passage_index.witness_ids)
        control_ids = {
            passage_id
            for witness in manifest.witnesses
            if witness.witness_id in control_witness_ids
            for window in witness.holdout_windows
            for passage_id in window.passage_ids
        }
        control_path = generated_paths["tier4_control_passage_index"]
        control_records = _read_bound_partition(
            control_path,
            manifest.tier4_control_passage_index,
            expected_path=_relative_to_root(control_path, root),
            expected_partition="tier4_controls",
        )
        if {record.passage_id for record in control_records} != control_ids:
            raise CreativeWriterError("Tier 4 control index membership differs from manifest")
        if any(source_tiers.get(record.source_id) != 4 for record in control_records):
            raise CreativeWriterError("Tier 4 control index contains a non-control passage")
    selected = [*heldout_records, *control_records]
    if not selected:
        raise CreativeWriterError("Validation corpus contains no permitted passages")
    return _ValidationCorpus(
        lock=lock,
        manifest=manifest,
        passages=selected,
        heldout_ids=heldout_ids,
        control_ids=control_ids,
        witness_tiers=lock_tiers,
        witness_roles={
            witness_id: source_roles.get(
                next(
                    item.source_id for item in lock.witnesses if item.witness_id == witness_id
                ),
                [],
            )
            for witness_id in lock_tiers
        },
        registry=registry,
    )


def _require_validation_treatment(
    record: ValidationRecord,
    claims: list[EvidenceClaim],
    *,
    require_controls: bool,
    require_reviewers: bool,
) -> None:
    non_rejected = {claim.id for claim in claims if claim.status != "rejected"}
    candidate_ids = {claim.id for claim in claims}
    for item in [
        *record.heldout_claim_results,
        *record.control_comparisons,
        *record.reviewer_records,
    ]:
        if item.claim_id not in candidate_ids:
            raise CreativeWriterError(
                f"Validation record references undeclared claim `{item.claim_id}`"
            )
    heldout_claims = {item.claim_id for item in record.heldout_claim_results}
    if missing := sorted(non_rejected - heldout_claims):
        raise CreativeWriterError(
            "Missing held-out claim results for: " + ", ".join(missing)
        )
    if require_controls:
        controls = {item.claim_id for item in record.control_comparisons}
        if missing := sorted(non_rejected - controls):
            raise CreativeWriterError(
                "Missing control comparisons for: " + ", ".join(missing)
            )
    if require_reviewers:
        reviewers = {item.claim_id for item in record.reviewer_records}
        if missing := sorted(non_rejected - reviewers):
            raise CreativeWriterError(
                "Missing reviewer records for: " + ", ".join(missing)
            )


def _validation_metric_partition(
    partition: str,
    passages: list[PassageRecord],
    ids: set[str],
    config: AnalysisConfig,
    corpus: _ValidationCorpus,
) -> ValidationMetricPartition:
    metrics = measure_validation_partition(passages, config, ids)
    witnesses: list[ValidationMetricWitness] = []
    for metric in metrics:
        payload = WitnessMetricRecord.model_validate(metric.to_dict())
        witnesses.append(
            ValidationMetricWitness(
                witness_id=metric.witness_id,
                source_id=metric.source_id,
                selection_id=metric.selection_id,
                authority_tier=corpus.witness_tiers[metric.witness_id],
                roles=corpus.witness_roles[metric.witness_id],
                metrics=payload,
            )
        )
    return ValidationMetricPartition(partition=partition, witnesses=witnesses)


def _validate_record_partitions(
    record: ValidationRecord,
    corpus: _ValidationCorpus,
    *,
    candidate_claim_ids: set[str] | None = None,
    include_controls: bool = True,
) -> None:
    """Validate authored validation references against already-open partitions."""

    by_id = {passage.passage_id: passage for passage in corpus.passages}
    heldout_witness_ids = {
        passage.witness_id for passage in corpus.passages if passage.passage_id in corpus.heldout_ids
    }
    for result in record.heldout_claim_results:
        if candidate_claim_ids is not None and result.claim_id not in candidate_claim_ids:
            raise CreativeWriterError(
                f"Held-out result `{result.id}` references undeclared claim `{result.claim_id}`"
            )
        if result.witness_id not in heldout_witness_ids:
            raise CreativeWriterError(f"Held-out result `{result.id}` is outside the heldout_wells partition")
        if any(passage_id not in corpus.heldout_ids for passage_id in result.passage_ids):
            raise CreativeWriterError(f"Held-out result `{result.id}` references a non-held-out passage")
        passages = [by_id.get(passage_id) for passage_id in result.passage_ids]
        if any(passage is None for passage in passages):
            raise CreativeWriterError(f"Held-out result `{result.id}` references an unresolved passage")
        if any(passage.witness_id != result.witness_id for passage in passages if passage is not None):
            raise CreativeWriterError(f"Held-out result `{result.id}` mixes witness passage IDs")
        if corpus.witness_tiers.get(result.witness_id) != result.authority_tier:
            raise CreativeWriterError(f"Held-out result `{result.id}` has the wrong authority tier")
        if result.role not in corpus.witness_roles.get(result.witness_id, []):
            raise CreativeWriterError(f"Held-out result `{result.id}` has an undeclared witness role")

    if not include_controls:
        return

    control_witness_ids = {
        passage.witness_id for passage in corpus.passages if passage.passage_id in corpus.control_ids
    }
    for comparison in record.control_comparisons:
        if candidate_claim_ids is not None and comparison.claim_id not in candidate_claim_ids:
            raise CreativeWriterError(
                f"Control comparison `{comparison.id}` references undeclared claim `{comparison.claim_id}`"
            )
        if comparison.witness_id not in control_witness_ids:
            raise CreativeWriterError(f"Control comparison `{comparison.id}` is outside the tier4_controls partition")
        if any(passage_id not in corpus.control_ids for passage_id in comparison.passage_ids):
            raise CreativeWriterError(f"Control comparison `{comparison.id}` references a non-control passage")
        passages = [by_id.get(passage_id) for passage_id in comparison.passage_ids]
        if any(passage is None for passage in passages):
            raise CreativeWriterError(f"Control comparison `{comparison.id}` references an unresolved passage")
        if any(passage.witness_id != comparison.witness_id for passage in passages if passage is not None):
            raise CreativeWriterError(f"Control comparison `{comparison.id}` mixes witness passage IDs")
        if comparison.role not in corpus.witness_roles.get(comparison.witness_id, []):
            raise CreativeWriterError(f"Control comparison `{comparison.id}` has an undeclared witness role")


def _validation_packet(
    corpus: _ValidationCorpus, *, include_controls: bool, context_radius: int
) -> str:
    lines = [
        "# Phase 2B validation packet",
        "",
        "Contexts are restricted to passage IDs in the current validation partition.",
        "",
    ]
    partitions = [("heldout_wells", corpus.heldout_ids)]
    if include_controls:
        partitions.append(("tier4_controls", corpus.control_ids))
    by_id = {passage.passage_id: passage for passage in corpus.passages}
    for partition, ids in partitions:
        lines.extend([f"## {partition}", ""])
        partition_passages = [passage for passage in corpus.passages if passage.passage_id in ids]
        for focal in partition_passages:
            context = context_window(partition_passages, focal.passage_id, context_radius)
            tier = corpus.witness_tiers[focal.witness_id]
            roles = ", ".join(corpus.witness_roles[focal.witness_id])
            label = "negative/comparative control" if partition == "tier4_controls" else "held-out Wells"
            lines.extend(
                [
                    f"### {label}: `{focal.passage_id}`",
                    "",
                    f"- Witness: `{focal.witness_id}`",
                    f"- Authority tier: `{tier}`",
                    f"- Role: `{roles}`",
                    f"- Source: `{focal.source_id}`",
                    f"- Passage ID: `{focal.passage_id}`",
                    "- Context:",
                ]
            )
            for item in context:
                if item.passage_id not in ids:
                    raise CreativeWriterError("Validation context crossed the current partition boundary")
                lines.append(f"  - `{item.passage_id}`: {item.normalized_text}")
            lines.append("")
    del by_id
    return "\n".join(lines).rstrip() + "\n"


def _validation_report(
    *,
    config: AnalysisConfig,
    preflight: _ValidationPreflight,
    corpus: _ValidationCorpus,
    metrics: ValidationMetricsDocument,
    final: bool,
    report_ledger: EvidenceLedger | None = None,
) -> str:
    lines = [
        "# Phase 2B analysis report",
        "",
        "This report separates deterministic measurements from authored candidate claims and human validation records.",
        "",
        "## Deterministic measurements",
        "",
        f"- Study: `{config.study_id}`",
        f"- Validation step: `{preflight.validation.validation_step}`",
        "- Measurements are reported independently by witness; no pooled target is calculated.",
    ]
    for partition in (metrics.heldout_wells, metrics.tier4_controls):
        if partition is None:
            continue
        lines.extend(["", f"### Partition: `{partition.partition}`", ""])
        for witness in partition.witnesses:
            lines.append(
                f"- Witness `{witness.witness_id}` (source `{witness.source_id}`, tier `{witness.authority_tier}`): "
                f"{witness.metrics.total_words} words across {witness.metrics.total_passages} passages."
            )
    lines.extend(["", "## Authored candidate claims", ""])
    authored_ledger = report_ledger or preflight.candidate_ledger
    for claim in authored_ledger.claims:
        lines.append(f"- `{claim.id}`: {claim.statement} ({claim.status}, {claim.confidence}).")
    lines.extend(["", "## Held-out results", ""])
    if preflight.validation.heldout_claim_results:
        for result in preflight.validation.heldout_claim_results:
            lines.append(f"- `{result.id}` for `{result.claim_id}` at `{result.witness_id}`: {result.assessment}. {result.observed_tendency}")
    else:
        lines.append("- No authored held-out claim results have been recorded yet.")
    lines.extend(["", "## Controls", ""])
    if metrics.tier4_controls is None:
        lines.append("Control material remains unopened until held-out claim assessments are recorded.")
    elif preflight.validation.control_comparisons:
        for comparison in preflight.validation.control_comparisons:
            lines.append(f"- `{comparison.id}` for `{comparison.claim_id}` at `{comparison.witness_id}`: {comparison.result}. {comparison.comparison}")
    else:
        lines.append("No authored control comparisons have been recorded yet.")
    lines.extend(["", "## Reviewer records", ""])
    if preflight.validation.reviewer_records:
        for reviewer in preflight.validation.reviewer_records:
            lines.append(f"- `{reviewer.id}` for `{reviewer.claim_id}` by `{reviewer.reviewer_id}`: {reviewer.outcome}. {reviewer.notes}")
    else:
        lines.append("Independent reviewer records are not yet complete.")
    lines.extend(["", "## Rejected claims", ""])
    rejected = [claim for claim in authored_ledger.claims if claim.status == "rejected"]
    if rejected:
        lines.extend(f"- `{claim.id}` remains retained as rejected." for claim in rejected)
    else:
        lines.append("- None in the frozen candidate ledger.")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "These descriptive measurements provide no inferential test, authorship attribution, or pooled aggregate judgement.",
            "",
            "## Phase 2C stop boundary",
            "",
            "This output does not authorise style guidance, style-card changes, story planning, or manuscript changes. Phase 2C requires separate design approval after human Phase 2B approval.",
        ]
    )
    if final:
        lines.extend(["", "## Final compiled status", "", "The final report includes the recorded claim transitions and retained rejected claims."])
    return "\n".join(lines).rstrip() + "\n"


def _write_validation_outputs(
    generated_paths: dict[str, Path],
    *,
    metrics: ValidationMetricsDocument,
    packet: str,
    report: str,
) -> None:
    payloads = [
        (
            generated_paths["validation_metrics"],
            (json.dumps(metrics.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        ),
        (generated_paths["validation_packet"], packet.encode("utf-8")),
        (generated_paths["analysis_report"], report.encode("utf-8")),
    ]
    staged: list[tuple[Path, Path]] = []
    try:
        for target, payload in payloads:
            staged.append((target, _stage_file(target, payload)))
        _commit_staged(staged)
    except (CreativeWriterError, OSError):
        _cleanup_paths([(temporary, "validation temporary cleanup") for _, temporary in staged])
        raise


def _tracked_regular_artifact(root: Path, path: Path) -> None:
    relative = _relative_to_root(path, root)
    if path.is_symlink() or not path.is_file():
        raise CreativeWriterError(f"Required tracked artifact is not a regular file: {relative}")
    tracked = _git_stdout(root, ["ls-files", "--error-unmatch", "--", relative]).strip()
    if tracked != relative:
        raise CreativeWriterError(f"Required tracked artifact is not tracked: {relative}")


def _validate_final_claims(
    *,
    candidate: EvidenceLedger,
    final: EvidenceLedger,
    validation: ValidationRecord,
) -> None:
    candidate_by_id = {claim.id: claim for claim in candidate.claims}
    final_by_id = {claim.id: claim for claim in final.claims}
    if set(candidate_by_id) != set(final_by_id):
        missing = sorted(set(candidate_by_id) - set(final_by_id))
        added = sorted(set(final_by_id) - set(candidate_by_id))
        raise CreativeWriterError(
            "Final ledger must preserve exact candidate claim IDs; "
            f"missing={missing}, added={added}"
        )
    immutable_fields = {
        "id",
        "dimension",
        "statement",
        "mode",
        "supporting_passages",
        "counterexample_passages",
        "counterexample_search",
        "control_results",
        "validation_expectation",
        "prohibited_overgeneralisation",
        "notes",
    }
    for claim_id, original in candidate_by_id.items():
        current = final_by_id[claim_id]
        for field in immutable_fields:
            if getattr(original, field) != getattr(current, field):
                raise CreativeWriterError(
                    f"Final claim `{claim_id}` changed undeclared development field `{field}`"
                )
        if current.status == "candidate":
            raise CreativeWriterError(f"Final claim `{claim_id}` cannot remain candidate")

    transitions = {transition.claim_id: transition for transition in validation.claim_transitions}
    if set(transitions) != set(candidate_by_id):
        raise CreativeWriterError("Final validation requires exactly one transition for every candidate claim")
    heldout_by_id = {item.id: item for item in validation.heldout_claim_results}
    control_by_id = {item.id: item for item in validation.control_comparisons}
    reviewer_by_id = {item.id: item for item in validation.reviewer_records}
    allowed_statuses = {
        "candidate": {"validated", "qualified", "rejected"},
        "qualified": {"validated", "qualified", "rejected"},
        "rejected": {"rejected"},
    }
    for claim_id, original in candidate_by_id.items():
        current = final_by_id[claim_id]
        transition = transitions[claim_id]
        if (
            transition.from_status != original.status
            or transition.from_confidence != original.confidence
            or transition.to_status != current.status
            or transition.to_confidence != current.confidence
        ):
            raise CreativeWriterError(
                f"Claim transition for `{claim_id}` does not match candidate/final status and confidence"
            )
        if original.status not in allowed_statuses or current.status not in allowed_statuses[original.status]:
            raise CreativeWriterError(
                f"Illegal claim transition `{original.status}` -> `{current.status}` for `{claim_id}`"
            )
        if original.status != "rejected":
            heldout_ids = [item.id for item in validation.heldout_claim_results if item.claim_id == claim_id]
            control_ids = [item.id for item in validation.control_comparisons if item.claim_id == claim_id]
            reviewer_ids = [item.id for item in validation.reviewer_records if item.claim_id == claim_id]
            if not heldout_ids or not control_ids or not reviewer_ids:
                raise CreativeWriterError(
                    f"Non-rejected claim `{claim_id}` lacks held-out, control, or reviewer treatment"
                )
            if set(transition.heldout_result_ids) != set(heldout_ids):
                raise CreativeWriterError(f"Claim `{claim_id}` transition does not reference all held-out results")
            if set(transition.control_comparison_ids) != set(control_ids):
                raise CreativeWriterError(f"Claim `{claim_id}` transition does not reference all control comparisons")
            if set(transition.reviewer_record_ids) != set(reviewer_ids):
                raise CreativeWriterError(f"Claim `{claim_id}` transition does not reference all reviewer records")
            for result_id in transition.heldout_result_ids:
                if heldout_by_id.get(result_id) is None or heldout_by_id[result_id].claim_id != claim_id:
                    raise CreativeWriterError(f"Claim `{claim_id}` transition references a different held-out claim")
            for comparison_id in transition.control_comparison_ids:
                if control_by_id.get(comparison_id) is None or control_by_id[comparison_id].claim_id != claim_id:
                    raise CreativeWriterError(f"Claim `{claim_id}` transition references a different control claim")
            for reviewer_id in transition.reviewer_record_ids:
                if reviewer_by_id.get(reviewer_id) is None or reviewer_by_id[reviewer_id].claim_id != claim_id:
                    raise CreativeWriterError(f"Claim `{claim_id}` transition references a different reviewer claim")
        elif current.status != "rejected":
            raise CreativeWriterError(f"Rejected claim `{claim_id}` may not be resurrected")
    if set(heldout_by_id) != {item.id for item in validation.heldout_claim_results}:
        raise CreativeWriterError("Held-out result IDs are not unique")
    if set(control_by_id) != {item.id for item in validation.control_comparisons}:
        raise CreativeWriterError("Control comparison IDs are not unique")
    if set(reviewer_by_id) != {item.id for item in validation.reviewer_records}:
        raise CreativeWriterError("Reviewer record IDs are not unique")


def _build_validation_metrics(
    config: AnalysisConfig,
    validation: ValidationRecord,
    generated_paths: dict[str, Path],
    corpus: _ValidationCorpus,
) -> ValidationMetricsDocument:
    # The generated path is rooted at build/<slug>/source-study.  Derive the
    # repository root without consulting any additional source artefact.
    build_root = generated_paths["validation_metrics"].parents[5]
    slug = generated_paths["validation_metrics"].parents[3].name
    config_path = build_root / "stories" / slug / "source-study" / "analysis.yml"
    manifest_path = config_path.parent / "holdouts.yml"
    return ValidationMetricsDocument(
        schema_version=1,
        stage=config.study_status,
        validation_step=validation.validation_step,
        study_id=config.study_id,
        provenance=ValidationMetricProvenance(
            study_id=config.study_id,
            tool_version=TOOL_VERSION,
            stage=config.study_status,
            validation_step=validation.validation_step,
            config_sha256=_sha256(config_path),
            index_sha256=_sha256(generated_paths["heldout_wells_passage_index"]),
            manifest_sha256=_sha256(manifest_path),
            candidate_commit=validation.candidate_commit,
            candidate_profile_sha256=validation.candidate_profile_sha256,
            candidate_ledger_sha256=validation.candidate_ledger_sha256,
            config_path=_relative_to_root(config_path, build_root),
            index_path=_relative_to_root(generated_paths["heldout_wells_passage_index"], build_root),
            manifest_path=_relative_to_root(manifest_path, build_root),
        ),
        enabled_measurements=list(config.enabled_measurements),
        heldout_wells=_validation_metric_partition(
            "heldout_wells", corpus.passages, corpus.heldout_ids, config, corpus
        ),
        tier4_controls=(
            _validation_metric_partition(
                "tier4_controls", corpus.passages, corpus.control_ids, config, corpus
            )
            if validation.validation_step in {"heldout_assessed", "complete"}
            else None
        ),
    )


def _validate(root: Path, slug: str) -> SourceAnalysisResult:
    preflight = _preflight_validation(root, slug)
    config = preflight.config
    validation = preflight.validation
    generated_paths = _resolve_generated_paths(root, slug, config)
    candidate_claims = preflight.candidate_ledger.claims
    if config.study_status == "candidate_frozen" and validation.validation_step == "frozen":
        if validation.heldout_claim_results or validation.control_comparisons or validation.reviewer_records:
            raise CreativeWriterError("frozen validation step cannot contain held-out, control, or reviewer records")
        corpus = _load_validation_corpus(root, slug, config, include_controls=False)
        metrics = _build_validation_metrics(config, validation, generated_paths, corpus)
        _write_validation_outputs(
            generated_paths,
            metrics=metrics,
            packet=_validation_packet(corpus, include_controls=False, context_radius=config.passage_rules.context_radius),
            report=_validation_report(config=config, preflight=preflight, corpus=corpus, metrics=metrics, final=False),
        )
        return SourceAnalysisResult("validate", slug, len(metrics.heldout_wells.witnesses), len(corpus.heldout_ids), generated_paths, _story_path(root, slug) / "source-study" / "holdouts.yml", False)

    if config.study_status == "candidate_frozen" and validation.validation_step == "heldout_assessed":
        _require_validation_treatment(validation, candidate_claims, require_controls=False, require_reviewers=False)
        corpus = _load_validation_corpus(root, slug, config, include_controls=False)
        _validate_record_partitions(
            validation,
            corpus,
            candidate_claim_ids={claim.id for claim in candidate_claims},
            include_controls=False,
        )
        corpus = _load_validation_corpus(root, slug, config, include_controls=True)
        _validate_record_partitions(
            validation,
            corpus,
            candidate_claim_ids={claim.id for claim in candidate_claims},
        )
        metrics = _build_validation_metrics(config, validation, generated_paths, corpus)
        _write_validation_outputs(
            generated_paths,
            metrics=metrics,
            packet=_validation_packet(corpus, include_controls=True, context_radius=config.passage_rules.context_radius),
            report=_validation_report(config=config, preflight=preflight, corpus=corpus, metrics=metrics, final=False),
        )
        return SourceAnalysisResult("validate", slug, len(metrics.heldout_wells.witnesses) + len(metrics.tier4_controls.witnesses if metrics.tier4_controls else []), len(corpus.passages), generated_paths, _story_path(root, slug) / "source-study" / "holdouts.yml", False)

    if config.study_status != "validated" or validation.validation_step != "complete":
        raise CreativeWriterError("Validation record must use frozen, heldout_assessed, or complete step for its configured stage")
    _require_validation_treatment(validation, candidate_claims, require_controls=True, require_reviewers=True)
    heldout_corpus = _load_validation_corpus(root, slug, config, include_controls=False)
    _validate_record_partitions(
        validation,
        heldout_corpus,
        candidate_claim_ids={claim.id for claim in candidate_claims},
        include_controls=False,
    )
    corpus = _load_validation_corpus(root, slug, config, include_controls=True)
    _validate_record_partitions(
        validation,
        corpus,
        candidate_claim_ids={claim.id for claim in candidate_claims},
    )
    story_dir = _story_path(root, slug)
    final_profile_path = story_dir / "source-study" / "wells-profile.md"
    final_ledger_path = story_dir / "source-study" / "evidence-ledger.yml"
    period_controls_path = story_dir / "source-study" / "period-controls.md"
    _tracked_regular_artifact(root, story_dir / "source-study" / "validation.md")
    _tracked_regular_artifact(root, period_controls_path)
    try:
        final_ledger = load_yaml_model(final_ledger_path, EvidenceLedger)
        final_profile_bytes = final_profile_path.read_bytes()
        final_ledger_bytes = final_ledger_path.read_bytes()
    except OSError as exc:
        raise CreativeWriterError(f"Unable to read final validation artifacts: {exc}") from exc
    if final_ledger.stage != "validated" or final_ledger.study_id != config.study_id:
        raise CreativeWriterError("Final evidence ledger must be validated and match the study")
    if hashlib.sha256(final_profile_bytes).hexdigest() != validation.final_profile_sha256:
        raise CreativeWriterError("Final profile SHA-256 does not match validation.md")
    if hashlib.sha256(final_ledger_bytes).hexdigest() != validation.final_ledger_sha256:
        raise CreativeWriterError("Final ledger SHA-256 does not match validation.md")
    _validate_final_claims(candidate=preflight.candidate_ledger, final=final_ledger, validation=validation)
    metrics = _build_validation_metrics(config, validation, generated_paths, corpus)
    _write_validation_outputs(
        generated_paths,
        metrics=metrics,
        packet=_validation_packet(corpus, include_controls=True, context_radius=config.passage_rules.context_radius),
            report=_validation_report(config=config, preflight=preflight, corpus=corpus, metrics=metrics, final=True, report_ledger=final_ledger),
    )
    return SourceAnalysisResult("validate", slug, len(corpus.witness_tiers), len(corpus.passages), generated_paths, story_dir / "source-study" / "holdouts.yml", False)


def _tracked_evidence_paths(story_dir: Path) -> list[Path]:
    source_study = story_dir / "source-study"
    paths = [
        source_study / "quantitative-profile.yml",
        source_study / "evidence-ledger.yml",
        source_study / "wells-profile.md",
        source_study / "period-controls.md",
        source_study / "validation.md",
    ]
    observation_dir = source_study / "observations"
    if observation_dir.exists():
        paths.extend(sorted(observation_dir.rglob("*.md")))
    return [path for path in paths if path.exists()]


def _expected_observation_paths(story_dir: Path, registry: SourcesRegistry) -> list[Path]:
    """Derive one dossier path per retained Tier 1-3 source, without role constants."""

    return [
        story_dir / "source-study" / "observations" / f"{source.id}.md"
        for source in registry.sources
        if source.role.tier in {1, 2, 3}
    ]


def _write_development_diagnostics(
    path: Path,
    validation: ValidationResult | None = None,
    *,
    errors: int | None = None,
    warnings: int | None = None,
) -> None:
    """Atomically replace a report with counts only, preserving it on failure."""

    if validation is not None:
        errors = len(validation.errors)
        warnings = len(validation.warnings)
    if errors is None or warnings is None:
        raise CreativeWriterError("Development diagnostics require error and warning counts")
    temporary_path: Path | None = None
    try:
        original = path.read_bytes()
        current = original.decode("utf-8")
        authored = current.split("\n## Evidence validation diagnostics", 1)[0].rstrip()
        payload = (
            authored
            + "\n\n## Evidence validation diagnostics\n\n"
            + f"- Blocking errors: **{errors}**\n"
            + f"- Warnings: **{warnings}**\n"
        ).encode("utf-8")
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            rollback_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb", dir=path.parent, prefix=f".{path.name}.rollback.", suffix=".tmp", delete=False
                ) as handle:
                    rollback_path = Path(handle.name)
                    handle.write(original)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(rollback_path, path)
                rollback_path = None
            finally:
                if rollback_path is not None:
                    rollback_path.unlink(missing_ok=True)
            raise
    except (OSError, UnicodeError) as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise CreativeWriterError(f"Unable to atomically write development diagnostics to {path}: {exc}") from exc


def _append_development_diagnostics(path: Path, validation: ValidationResult) -> None:
    """Compatibility wrapper for callers of the original private helper."""

    _write_development_diagnostics(path, validation)


def _post_metric_call(path: Path, report: Path, operation: Any) -> Any:
    """Run evidence IO/grammar work and record one atomic diagnostic on failure."""

    try:
        return operation()
    except (
        CreativeWriterError,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        RecursionError,
        TypeError,
        ValueError,
        ValidationError,
    ) as exc:
        diagnostic = ValidationResult(
            errors=[
                ValidationIssue(
                    "error",
                    str(path),
                    message=f"Post-metric evidence validation failed: {exc}",
                )
            ]
        )
        _write_development_diagnostics(report, diagnostic)
        if isinstance(exc, CreativeWriterError):
            raise
        raise CreativeWriterError(f"Post-metric evidence validation failed: {exc}") from exc


def _validate_returned_metric_records(metrics: object) -> list[dict[str, object]]:
    """Independently validate the metric writer return before comparisons."""

    if not isinstance(metrics, list):
        raise TypeError("measure_development must return a list of witness metrics")
    records: list[dict[str, object]] = []
    for ordinal, metric in enumerate(metrics, start=1):
        if isinstance(metric, dict):
            payload = metric
        else:
            serializer = getattr(metric, "to_dict", None)
            if not callable(serializer):
                raise TypeError(f"returned witness metric {ordinal} has no to_dict serializer")
            payload = serializer()
        if not isinstance(payload, dict):
            raise TypeError(f"returned witness metric {ordinal} serialized payload must be an object")
        try:
            WitnessMetricRecord.model_validate(payload)
        except (ValidationError, TypeError, ValueError, RecursionError):
            raise
        records.append(payload)
    if not records:
        raise ValueError("measure_development returned no witness metrics")
    return records


def _validate_development_dossier_set(
    story_dir: Path,
    registry: SourcesRegistry,
) -> tuple[list[Path], ValidationResult]:
    expected = _expected_observation_paths(story_dir, registry)
    observation_dir = story_dir / "source-study" / "observations"
    actual = sorted(observation_dir.rglob("*.md")) if observation_dir.exists() else []
    expected_set = set(expected)
    actual_set = set(actual)
    result = ValidationResult()
    for path in sorted(expected_set - actual_set):
        result.errors.append(ValidationIssue("error", str(path), message="Required retained Tier 1-3 observation dossier is missing"))
    for path in sorted(actual_set - expected_set):
        result.errors.append(ValidationIssue("error", str(path), message="Observation dossier is not derived from a retained Tier 1-3 source ID"))
    return expected, result.sorted()


def _validate_artifact_lifecycle(
    config: AnalysisConfig,
    *,
    ledger: EvidenceLedger | None,
    quantitative_profile: QuantitativeProfile | None,
    validation_record: ValidationRecord | None,
    validation_body: str | None,
    ledger_path: Path,
    quantitative_path: Path,
    validation_path: Path,
) -> ValidationResult:
    result = ValidationResult()
    order = {"protocol": 0, "development": 1, "candidate_frozen": 2, "validated": 3}
    configured = config.study_status
    if ledger is not None:
        if ledger.study_id != config.study_id:
            result.errors.append(ValidationIssue("error", str(ledger_path), locator=ledger.study_id, message="Evidence ledger study identity does not match analysis configuration"))
        if order[ledger.stage] > order[configured]:
            result.errors.append(ValidationIssue("error", str(ledger_path), message="Evidence ledger stage leads configured analysis stage"))
        if ledger.stage == "protocol" and ledger.claims:
            result.errors.append(ValidationIssue("error", str(ledger_path), message="Populated protocol evidence ledger is not an empty template"))
        if configured == "candidate_frozen" and ledger.stage != "development":
            result.errors.append(ValidationIssue("error", str(ledger_path), message="Candidate-frozen analysis requires the frozen evidence ledger to remain at development stage"))
        if configured == "validated" and ledger.stage != "validated":
            result.errors.append(ValidationIssue("error", str(ledger_path), message="Validated analysis requires a validated evidence ledger"))
    if quantitative_profile is not None:
        if quantitative_profile.study_id != config.study_id:
            result.errors.append(ValidationIssue("error", str(quantitative_path), locator=quantitative_profile.study_id, message="Quantitative profile study identity does not match analysis configuration"))
        if order[quantitative_profile.stage] > order[configured]:
            result.errors.append(ValidationIssue("error", str(quantitative_path), message="Quantitative profile stage leads configured analysis stage"))
        if quantitative_profile.stage == "protocol" and (
            quantitative_profile.generated_metrics or quantitative_profile.witnesses
        ):
            result.errors.append(ValidationIssue("error", str(quantitative_path), message="Populated protocol quantitative profile is not an empty template"))
    if validation_record is not None:
        if validation_record.study_id != config.study_id:
            result.errors.append(ValidationIssue("error", str(validation_path), locator=validation_record.study_id, message="Validation record study identity does not match analysis configuration"))
        if order[validation_record.stage] > order[configured]:
            result.errors.append(ValidationIssue("error", str(validation_path), message="Validation artifact stage leads configured analysis stage"))
        if validation_record.stage == "protocol" and validation_record.claim_transitions:
            result.errors.append(ValidationIssue("error", str(validation_path), message="Populated protocol validation record is not an empty template"))
        if validation_record.stage == "protocol":
            for field, expected in PROTOCOL_VALIDATION_SUMMARIES.items():
                if getattr(validation_record, field) != expected:
                    result.errors.append(ValidationIssue("error", str(validation_path), locator=field, message="Protocol validation record must retain the exact current placeholder value"))
            if any(
                getattr(validation_record, field) is not None
                for field in (
                    "candidate_commit",
                    "candidate_profile_sha256",
                    "candidate_ledger_sha256",
                    "final_profile_sha256",
                )
            ):
                result.errors.append(ValidationIssue("error", str(validation_path), message="Protocol validation record must not contain hashes"))
            if validation_body is None or _normalize_markdown_body(validation_body) != _normalize_markdown_body(CANONICAL_PROTOCOL_VALIDATION_BODY):
                result.errors.append(ValidationIssue("error", str(validation_path), message="Protocol validation Markdown body must match the canonical protocol body"))
        if configured in {"protocol", "development"} and validation_record.stage != "protocol":
            result.errors.append(ValidationIssue("error", str(validation_path), message="Protocol/development analysis requires a protocol validation record"))
        if configured == "candidate_frozen" and validation_record.stage != "candidate_frozen":
            result.errors.append(ValidationIssue("error", str(validation_path), message="Candidate-frozen analysis requires a candidate_frozen validation record"))
        if configured == "validated" and validation_record.stage != "validated":
            result.errors.append(ValidationIssue("error", str(validation_path), message="Validated analysis requires a validated validation record"))
    return result.sorted()


def _develop(root: Path, slug: str) -> SourceAnalysisResult:
    story_dir = _story_path(root, slug)
    analysis_path = story_dir / "source-study" / "analysis.yml"
    config = load_yaml_model(analysis_path, AnalysisConfig)
    if config.study_status not in {"protocol", "development"}:
        raise CreativeWriterError("The develop command is available only for config status protocol or development")
    generated_paths = _resolve_generated_paths(root, slug, config)
    holdout_path = story_dir / "source-study" / "holdouts.yml"
    lock, manifest, passages, source_tiers, admission, registry = _load_development_partition(
        root, slug, config
    )
    development_ids = {passage.passage_id for passage in passages}
    current_by_id = {passage.passage_id: passage for passage in passages}
    if not development_ids:
        raise CreativeWriterError("Holdout manifest contains no development passages")
    index_path = generated_paths["development_passage_index"]
    expected_metric_provenance = {
        "study_id": config.study_id,
        "stage": "development",
        "config_sha256": _sha256(analysis_path),
        "index_sha256": _sha256(index_path),
        "manifest_sha256": _sha256(holdout_path),
        "config_path": _relative_to_root(analysis_path, root),
        "index_path": _relative_to_root(index_path, root),
        "manifest_path": _relative_to_root(holdout_path, root),
    }
    development_report = generated_paths["development_report"]
    metrics = measure_development(
        passages,
        config,
        development_ids,
        output_paths=generated_paths,
        config_sha256=expected_metric_provenance["config_sha256"],
        index_sha256=expected_metric_provenance["index_sha256"],
        manifest_sha256=expected_metric_provenance["manifest_sha256"],
        config_path=expected_metric_provenance["config_path"],
        index_path=expected_metric_provenance["index_path"],
        manifest_path=expected_metric_provenance["manifest_path"],
    )
    returned_metric_records = _post_metric_call(
        generated_paths["development_metrics"],
        development_report,
        lambda: _validate_returned_metric_records(metrics),
    )

    evidence_result = ValidationResult()
    ledger_path = story_dir / "source-study" / "evidence-ledger.yml"
    profile_path = story_dir / "source-study" / "wells-profile.md"
    quantitative_path = story_dir / "source-study" / "quantitative-profile.yml"
    validation_path = story_dir / "source-study" / "validation.md"
    required_evidence_paths = [story_dir / "source-study" / name for name in CANONICAL_EVIDENCE_FILENAMES]
    for path in required_evidence_paths:
        if not path.exists():
            evidence_result.errors.append(ValidationIssue("error", str(path), message="Required canonical evidence artifact is missing"))
    if evidence_result.errors:
        _write_development_diagnostics(development_report, evidence_result)
        raise_for_issues(evidence_result, "Development source-analysis validation")

    ledger = _post_metric_call(
        ledger_path,
        development_report,
        lambda: _load_optional_yaml_model(ledger_path, EvidenceLedger),
    )
    quantitative_profile = _post_metric_call(
        quantitative_path,
        development_report,
        lambda: _load_optional_yaml_model(quantitative_path, QuantitativeProfile),
    )
    validation_record, validation_body = _post_metric_call(
        validation_path,
        development_report,
        lambda: load_validation_document(validation_path),
    )
    evidence_result.extend(
        _validate_artifact_lifecycle(
            config,
            ledger=ledger,
            quantitative_profile=quantitative_profile,
            validation_record=validation_record,
            validation_body=validation_body,
            ledger_path=ledger_path,
            quantitative_path=quantitative_path,
            validation_path=validation_path,
        )
    )
    if ledger is not None:
        evidence_result.extend(
            collect_evidence_issues(
                ledger,
                passages,
                config=config,
                stage="development",
                admission=admission,
                registry=registry,
                manifest=manifest,
                development_passage_ids=development_ids,
                file=ledger_path,
            )
        )

    if ledger is not None:
        evidence_result.extend(
            _post_metric_call(
                profile_path,
                development_report,
                lambda: collect_profile_issues(
                    profile_path,
                    ledger,
                    config,
                    stage="development",
                ),
            )
        )

    observation_paths = sorted((story_dir / "source-study" / "observations").rglob("*.md"))
    if observation_paths:
        evidence_result.extend(
            _post_metric_call(
                observation_paths[0],
                development_report,
                lambda: collect_observation_issues(
                    observation_paths,
                    passages,
                    config,
                    stage="development",
                    development_passage_ids=development_ids,
                    manifest=manifest,
                    claim_ids={claim.id for claim in ledger.claims} if ledger is not None else None,
                    admission=admission,
                    registry=registry,
                ),
            )
        )

    if quantitative_profile is not None:
        forbidden_witness_ids = {
            witness_id
            for witness_id, tier in source_tiers.items()
            if tier == 4
        }
        forbidden_witness_ids.update(
            witness.witness_id
            for witness in manifest.witnesses
            if not witness.development_windows
        )
        def validate_current_quantitative_profile() -> ValidationResult:
            result = collect_quantitative_profile_issues(
                quantitative_profile,
                root=root,
                metrics_path=generated_paths["development_metrics"],
                config=config,
                passages=passages,
                development_witness_ids={current_by_id[passage_id].witness_id for passage_id in development_ids},
                forbidden_witness_ids=forbidden_witness_ids,
                metrics_csv_path=generated_paths["development_metrics_csv"],
                expected_provenance=expected_metric_provenance,
                expected_witness_identities={
                    (
                        record["witness_id"],
                        record["source_id"],
                        record["selection_id"],
                    )
                    for record in returned_metric_records
                },
                expected_metric_records=returned_metric_records,
            )
            return raise_for_issues(result, "Quantitative profile validation")

        evidence_result.extend(
            _post_metric_call(
                quantitative_path,
                development_report,
                validate_current_quantitative_profile,
            )
        )

    _, dossier_result = _validate_development_dossier_set(story_dir, registry)
    evidence_result.extend(dossier_result)

    forbidden_witness_ids = {
        witness_id
        for witness_id, tier in source_tiers.items()
        if tier == 4
    }
    forbidden_witness_ids.update(
        witness.witness_id
        for witness in manifest.witnesses
        if not witness.development_windows
    )
    manifest_holdout_ids = {
        passage_id
        for witness in manifest.witnesses
        for window in witness.holdout_windows
        for passage_id in window.passage_ids
    }
    forbidden_passages = [
        _ForbiddenPassageLocator(passage_id)
        for passage_id in sorted(manifest_holdout_ids)
    ]
    evidence_result.extend(
        _post_metric_call(
            story_dir / "source-study",
            development_report,
            lambda: collect_leakage_issues(
                _tracked_evidence_paths(story_dir),
                forbidden_witness_ids=forbidden_witness_ids,
                forbidden_passages=forbidden_passages,
            ),
        )
    )
    evidence_result.extend(
        _post_metric_call(
            development_report,
            development_report,
            lambda: collect_leakage_issues(
                [
                    generated_paths["development_metrics"],
                    generated_paths["development_metrics_csv"],
                    generated_paths["development_report"],
                ],
                forbidden_witness_ids=forbidden_witness_ids,
                forbidden_passages=forbidden_passages,
            ),
        )
    )
    _write_development_diagnostics(generated_paths["development_report"], evidence_result)
    raise_for_issues(evidence_result, "Development source-analysis validation")
    return SourceAnalysisResult(
        stage="develop",
        story_slug=slug,
        witness_count=len(metrics),
        passage_count=len(development_ids),
        generated_paths=generated_paths,
        holdout_path=holdout_path,
        holdout_manifest_created=False,
    )


def run_source_analysis(root: Path, slug: str, stage: str) -> SourceAnalysisResult:
    """Run one staged source-analysis operation."""

    if stage == "prepare":
        return _prepare(root, slug)
    if stage == "develop":
        return _develop(root, slug)
    if stage != "validate":
        raise CreativeWriterError(
            f"Source analysis stage `{stage}` is not implemented; prepare and develop are available"
        )
    return _validate(root, slug)
