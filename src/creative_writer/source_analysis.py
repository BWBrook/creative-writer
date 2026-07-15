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
from typing import Any

import yaml
from pydantic import ValidationError

from creative_writer import __version__
from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory, load_yaml_model
from creative_writer.models import (
    RetainedSourceRecord,
    SourceStudyAdmission,
    SourcesRegistry,
)
from creative_writer.source_admission import check_source_admission
from creative_writer.source_analysis_models import (
    AnalysisConfig,
    CorpusLock,
    HoldoutManifest,
    HoldoutWindow,
    PassageRecord,
    WitnessDescriptor,
    WitnessHoldouts,
)
from creative_writer.source_passages import (
    parse_markdown_witness,
    partition_windows,
    serialize_passage_index,
)


TOOL_VERSION = f"creative-writer {__version__}"
ALGORITHM_VERSION = "tertile-hash-v1"
GENERATED_FILENAMES = {
    "corpus_lock": "corpus-lock.json",
    "passage_index": "passage-index.jsonl",
    "development_metrics": "development-metrics.json",
    "development_metrics_csv": "development-metrics.csv",
    "development_report": "development-report.md",
    "validation_metrics": "validation-metrics.json",
    "validation_packet": "validation-packet.md",
    "analysis_report": "analysis-report.md",
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise CreativeWriterError(f"Unable to hash {path}: {exc}") from exc
    return digest.hexdigest()


def _window_hash(seed: str, source_id: str, first_passage_id: str) -> str:
    value = f"{seed}:{source_id}:{first_passage_id}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _story_path(root: Path, slug: str) -> Path:
    return root / "stories" / slug


def _registry_path(story_dir: Path, relative: str) -> Path:
    candidate = story_dir / relative
    try:
        candidate.relative_to(story_dir)
    except ValueError as exc:
        raise CreativeWriterError(f"Registry path escapes story directory: {relative}") from exc
    return candidate


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


def _build_holdout_manifest(
    *,
    config: AnalysisConfig,
    registry_hashes: dict[str, str],
    registry: SourcesRegistry,
    witnesses: list[_ExpandedWitness],
    passages: list[PassageRecord],
    source_tiers: dict[str, int],
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
            "schema_version": 1,
            "partition_seed": config.partition.seed,
            "algorithm_version": config.partition.algorithm_version,
            "tool_version": TOOL_VERSION,
            "created_at": created_at,
            "registry_hashes": registry_hashes,
            "source_fingerprints": source_fingerprints,
            "whole_work_holdouts": list(config.partition.whole_work_holdouts),
            "witnesses": [
                item.model_dump(mode="json")
                for item in select_holdouts(passages, config, source_tiers)
            ],
        }
    )


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
    index_payload = serialize_passage_index(passages)
    expected_manifest = _build_holdout_manifest(
        config=config,
        registry_hashes=registry_hashes,
        registry=registry,
        witnesses=witnesses,
        passages=passages,
        source_tiers=source_tiers,
        created_at=datetime.now(timezone.utc),
    )

    lock_path = generated_paths["corpus_lock"]
    index_path = generated_paths["passage_index"]
    holdout_path = story_dir / "source-study" / "holdouts.yml"
    _validate_existing_json(lock_path, lock, "corpus lock")
    if index_path.exists():
        try:
            existing_index = index_path.read_bytes()
        except OSError as exc:
            raise CreativeWriterError(f"Unable to read existing passage index {index_path}: {exc}") from exc
        if existing_index != index_payload:
            raise CreativeWriterError("Existing passage index differs from the current corpus")
    existing_manifest = _load_existing_manifest(holdout_path)
    if existing_manifest is not None:
        _validate_manifest_passages(existing_manifest, seen_passage_ids)
        expected_manifest = _build_holdout_manifest(
            config=config,
            registry_hashes=registry_hashes,
            registry=registry,
            witnesses=witnesses,
            passages=passages,
            source_tiers=source_tiers,
            created_at=existing_manifest.created_at,
        )
        if existing_manifest.model_dump(mode="json") != expected_manifest.model_dump(mode="json"):
            raise CreativeWriterError("Existing holdout manifest differs from the current partition")
        manifest_created = False
    else:
        manifest_created = True

    lock_payload = _canonical_json(lock.model_dump(mode="json"))
    manifest_payload = yaml.safe_dump(
        expected_manifest.model_dump(),
        sort_keys=False,
        allow_unicode=True,
    ).encode("utf-8")
    staged: list[tuple[Path, Path]] = []
    try:
        staged.append((lock_path, _stage_file(lock_path, lock_payload)))
        staged.append((index_path, _stage_file(index_path, index_payload)))
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


def run_source_analysis(root: Path, slug: str, stage: str) -> SourceAnalysisResult:
    """Run one staged source-analysis operation."""

    if stage != "prepare":
        raise CreativeWriterError(
            f"Source analysis stage `{stage}` is not implemented; only `prepare` is available"
        )
    return _prepare(root, slug)
