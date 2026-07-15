"""Phase 2B source-analysis preparation and deterministic partitioning."""

from __future__ import annotations

import hashlib
import json
import math
import os
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
from creative_writer.source_validation import (
    _load_development_partition,
    _load_optional_yaml_model,
    _load_validation_corpus,
    _read_bound_partition,
)
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
    generation_id: str | None = None

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
        from creative_writer import source_validation
        source_validation._read_bound_partition = _read_bound_partition
        return _develop(root, slug)
    if stage != "validate":
        raise CreativeWriterError(
            f"Source analysis stage `{stage}` is not implemented; prepare, develop, and validate are available"
        )
    from creative_writer import source_validation
    for name in ("_read_bound_partition", "_load_validation_corpus"):
        if name in globals():
            setattr(source_validation, name, globals()[name])
    return source_validation.run_validation(root, slug)
