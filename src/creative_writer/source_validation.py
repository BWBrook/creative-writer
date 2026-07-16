"""Git-trusted staged validation, sealed quarantine access, and publication."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from creative_writer import __version__
from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory, load_yaml_model
from creative_writer.source_analysis_common import canonical_json_bytes, publish_validation_generation, read_current_validation_generation, safe_relative_path, sha256_bytes, sha256_file
from creative_writer.models import SourceStudyAdmission, SourcesRegistry
from creative_writer.source_analysis_models import AnalysisConfig, CorpusLock, EvidenceLedger, EvidenceClaim, HoldoutManifest, PassageIndexBinding, PassageRecord, QuantitativeProfile, ControlComparison, HeldoutClaimResult, ReviewerRecord, ValidationMetricPartition, ValidationMetricProvenance, ValidationMetricWitness, ValidationMetricsDocument, ValidationRecord, WitnessMetricRecord, WitnessDescriptor, WitnessHoldouts, load_validation_document, parse_validation_document
from creative_writer.source_passages import context_window, parse_passage_partition
from creative_writer.source_metrics import measure_validation_partition
from creative_writer.source_evidence import (
    ValidationIssue,
    ValidationResult,
    validate_period_controls,
    validate_profile_claim_links,
)

TOOL_VERSION = f"creative-writer {__version__}"
GENERATED_FILENAMES = {"corpus_lock": "corpus-lock.json", "development_passage_index": "indexes/development.jsonl", "heldout_wells_passage_index": "indexes/heldout-wells.jsonl", "tier4_control_passage_index": "indexes/tier4-controls.jsonl", "development_metrics": "development-metrics.json", "development_metrics_csv": "development-metrics.csv", "development_report": "development-report.md", "validation_metrics": "validation/current/validation-metrics.json", "validation_packet": "validation/current/validation-packet.md", "analysis_report": "validation/current/analysis-report.md"}
CANONICAL_PROTOCOL_VALIDATION_BODY = ("# Validation Record\\n\\n" "## Protocol state\\n\\n" "The strict YAML front matter records the adopted protocol state. Freeze hashes,\\n" "holdout results, control comparisons, reviewer findings, claim transitions,\\n" "and the final profile fingerprint will be recorded only after their respective\\n" "stages have occurred.\\n")
PROTOCOL_VALIDATION_SUMMARIES = {"holdout_summary": "Held-out material has not been opened at protocol stage.", "control_summary": "Tier 4 controls remain quarantined at protocol stage.", "reviewer_summary": "Independent review has not begun at protocol stage.", "unresolved_uncertainty": "No reviewed claim outcomes exist at protocol stage."}
_CAPABILITY_SEAL = object()

@dataclass(frozen=True, slots=True)
class VerifiedFreeze:
    _seal: object = field(repr=False, compare=False)
    root: Path
    slug: str
    config: AnalysisConfig
    validation: ValidationRecord
    candidate_ledger: EvidenceLedger
    candidate_profile_bytes: bytes
    candidate_ledger_bytes: bytes
    candidate_profile_path: Path
    candidate_ledger_path: Path
    heldout_index_path: Path
    heldout_index_binding: PassageIndexBinding
    heldout_witnesses: tuple[WitnessHoldouts, ...]
    lock: CorpusLock
    def __post_init__(self) -> None:
        if self._seal is not _CAPABILITY_SEAL:
            raise CreativeWriterError("VerifiedFreeze has an invalid capability seal")

@dataclass(frozen=True, slots=True)
class VerifiedControlAccess:
    _seal: object = field(repr=False, compare=False)
    freeze: VerifiedFreeze
    heldout: HeldoutCorpus
    control_witnesses: tuple[WitnessHoldouts, ...]
    control_index_path: Path
    control_index_binding: PassageIndexBinding
    def __post_init__(self) -> None:
        if self._seal is not _CAPABILITY_SEAL:
            raise CreativeWriterError("VerifiedControlAccess has an invalid capability seal")

@dataclass(frozen=True, slots=True)
class HeldoutCorpus:
    _seal: object = field(repr=False, compare=False)
    freeze: VerifiedFreeze
    records: tuple[PassageRecord, ...]
    ids: frozenset[str]
    witness_tiers: dict[str, int]
    witness_roles: dict[str, list[str]]
    registry: SourcesRegistry

    def __post_init__(self) -> None:
        if self._seal is not _CAPABILITY_SEAL:
            raise CreativeWriterError("HeldoutCorpus has an invalid capability seal")

@dataclass(frozen=True, slots=True)
class ControlCorpus:
    _seal: object = field(repr=False, compare=False)
    access: VerifiedControlAccess
    records: tuple[PassageRecord, ...]
    ids: frozenset[str]
    witness_tiers: dict[str, int]
    witness_roles: dict[str, list[str]]

    def __post_init__(self) -> None:
        if self._seal is not _CAPABILITY_SEAL:
            raise CreativeWriterError("ControlCorpus has an invalid capability seal")

@dataclass(frozen=True, slots=True)
class _ValidationPreflight:
    config: AnalysisConfig
    validation: ValidationRecord
    candidate_ledger: EvidenceLedger
    candidate_quantitative_profile: QuantitativeProfile
    candidate_profile_bytes: bytes
    candidate_ledger_bytes: bytes
    candidate_profile_path: Path
    candidate_ledger_path: Path
    root: Path
    slug: str
    manifest_path: Path
    lock_path: Path
    manifest: HoldoutManifest
    lock: CorpusLock

@dataclass(frozen=True, slots=True)
class _ValidationCorpus:
    lock: CorpusLock
    manifest: HoldoutManifest | None
    passages: list[PassageRecord]
    heldout_ids: set[str]
    control_ids: set[str]
    witness_tiers: dict[str, int]
    witness_roles: dict[str, list[str]]
    registry: SourcesRegistry

@dataclass(frozen=True, slots=True)
class _ForbiddenPassageLocator:
    passage_id: str
    normalized_text: str = ""

def _genuine(capability: object, expected: type[object]) -> bool:
    if type(capability) is not expected:
        return False
    try:
        return capability._seal is _CAPABILITY_SEAL  # type: ignore[attr-defined]
    except AttributeError:
        return False

def _sha256(path: Path) -> str:
    return sha256_file(path)

def _story_path(root: Path, slug: str) -> Path:
    return root.resolve(strict=False) / "stories" / slug

def _relative_to_root(path: Path, root: Path) -> str:
    return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()

def _normalize_markdown_body(body: str) -> str:
    normalized = body.replace("\\r\\n", "\\n").replace("\\r", "\\n")
    return normalized if normalized.endswith("\\n") else normalized + "\\n"

def _registry_path(story_dir: Path, relative: str) -> Path:
    try:
        return safe_relative_path(story_dir, relative)
    except CreativeWriterError as exc:
        raise CreativeWriterError(f"Registry path escapes story directory: {relative}") from exc

def _verify_registry_hash(path: Path, expected: str, label: str) -> None:
    actual = _sha256(path)
    if actual != expected:
        raise CreativeWriterError(f"{label} SHA-256 mismatch for {path}: expected {expected}, got {actual}")

def _head_model_bytes(root: Path, path: Path, label: str) -> bytes:
    """Read a tracked protocol model from its verified HEAD blob."""

    _mode, _object_id, data = _head_blob(root, _relative_to_root(path, root))
    if not data:
        raise CreativeWriterError(f"{label} HEAD blob is empty")
    return data

def _validate_analysis_authority(config: AnalysisConfig, admission: SourceStudyAdmission) -> None:
    if config.composition_window.start != admission.composition_window.start or config.composition_window.end != admission.composition_window.end:
        raise CreativeWriterError("Analysis composition window does not match source admission")
    admission_roles: dict[int, set[str]] = {tier: set() for tier in range(1, 6)}
    for source in admission.sources:
        admission_roles[source.authority.tier].update(source.analytical_roles)
        for selection in source.selections:
            admission_roles[source.authority.tier].update(selection.analytical_roles)
    configured_roles = {policy.tier: set(policy.analytical_roles) for policy in config.authority_tiers}
    if configured_roles != admission_roles:
        raise CreativeWriterError("Configured authority tier roles do not match admission source and selection roles")

def _resolve_generated_paths(root: Path, slug: str, config: AnalysisConfig) -> dict[str, Path]:
    resolved_root = root.resolve(strict=False)
    resolved: dict[str, Path] = {}
    for key, relative in config.generated_paths.items():
        expected_relative = f"build/{slug}/source-study/{GENERATED_FILENAMES[key]}"
        if relative != expected_relative:
            raise CreativeWriterError(f"Configured generated path for {key} has the wrong configured path")
        target = resolved_root / expected_relative
        current = target.parent
        managed_current = (
            key in {"validation_metrics", "validation_packet", "analysis_report"}
            and current.name == "current"
            and current.is_symlink()
            and current.parent.name == "validation"
            and current.parent.resolve(strict=False) == current.parent
            and re.fullmatch(r"generations/[0-9a-f]{64}", os.readlink(current)) is not None
        )
        if target.resolve(strict=False) != target and not managed_current:
            raise CreativeWriterError(f"Generated path redirects through a symlink: {relative}")
        resolved[key] = target
    return resolved

def _load_existing_manifest(path: Path) -> HoldoutManifest | None:
    if not path.exists():
        return None
    return load_yaml_model(path, HoldoutManifest)

def _read_bytes(path: Path, *, label: str) -> bytes:
    """Central filesystem byte reader for post-freeze partition access."""

    try:
        return path.read_bytes()
    except OSError as exc:
        raise CreativeWriterError(f"Unable to read {label} bytes from {path}: {exc}") from exc

def _require_committed_holdout(root: Path, holdout_path: Path) -> None:
    """Require the partition lock to exist in Git before development opens."""

    relative = _relative_to_root(holdout_path, root)
    try:
        listed = _git_stdout(root, ["ls-files", "--error-unmatch", "--", relative]).strip()
        status = _git_stdout(root, ["status", "--porcelain", "--", relative])
    except CreativeWriterError as exc:
        raise CreativeWriterError(
            f"Unable to verify that holdout manifest is tracked/committed: {exc}"
        ) from exc
    if listed != relative:
        raise CreativeWriterError(
            f"Development requires holdout manifest `{relative}` to be tracked/committed"
        )
    if status.strip():
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
    data = _read_bytes(path, label=f"{expected_partition} passage index")
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


def _git_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PAGER": "cat",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_EXTERNAL_DIFF": "",
        }
    )
    return environment


def _git_bytes(root: Path, arguments: list[str]) -> bytes:
    """Run a non-interactive Git object query without a shell or filters."""

    environment = _git_environment()
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


def _candidate_git_blob_record(root: Path, commit: str, relative: str) -> tuple[str, bytes]:
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
    if len(object_id) != _git_object_id_length(root) or not re.fullmatch(r"[0-9a-f]+", object_id):
        raise CreativeWriterError(f"Candidate Git object ID is malformed for `{relative}`")
    return object_id, _git_bytes(root, ["cat-file", "blob", object_id])


def _candidate_git_blob(root: Path, commit: str, relative: str) -> bytes:
    return _candidate_git_blob_record(root, commit, relative)[1]


def _verify_candidate_commit(root: Path, commit: str) -> None:
    object_format = _git_stdout(root, ["rev-parse", "--show-object-format"]).strip()
    expected_length = {"sha1": 40, "sha256": 64}.get(object_format)
    if expected_length is None:
        raise CreativeWriterError(f"Unsupported Git object format: {object_format}")
    if len(commit) != expected_length or not _FULL_COMMIT_RE.fullmatch(commit):
        raise CreativeWriterError(
            f"candidate_commit must be a full lowercase {expected_length}-hex Git commit"
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
    _git_bytes(root, ["merge-base", "--is-ancestor", commit, "HEAD"])


def _git_object_id_length(root: Path) -> int:
    object_format = _git_stdout(root, ["rev-parse", "--show-object-format"]).strip()
    expected_length = {"sha1": 40, "sha256": 64}.get(object_format)
    if expected_length is None:
        raise CreativeWriterError(f"Unsupported Git object format: {object_format}")
    return expected_length


def _stage_zero_blob(root: Path, relative: str) -> tuple[str, str]:
    output = _git_bytes(root, ["ls-files", "--stage", "-z", "--", relative])
    entries = [entry for entry in output.split(b"\0") if entry]
    if len(entries) != 1:
        raise CreativeWriterError(f"Path is missing, duplicated, or not tracked at stage 0: {relative}")
    header, path_bytes = entries[0].split(b"\t", 1)
    mode, object_id, stage = header.decode("ascii").split()
    if path_bytes.decode("utf-8") != relative or stage != "0" or mode not in {"100644", "100755"}:
        raise CreativeWriterError(f"Path is not a clean stage-0 regular blob: {relative}")
    if len(object_id) != _git_object_id_length(root) or not re.fullmatch(r"[0-9a-f]+", object_id):
        raise CreativeWriterError(f"Path has a malformed Git blob object ID: {relative}")
    return mode, object_id


def _head_blob(root: Path, relative: str) -> tuple[str, str, bytes]:
    _stage_zero_blob(root, relative)
    status = _git_stdout(root, ["status", "--porcelain=v1", "--untracked-files=all", "--", relative])
    if status.strip():
        raise CreativeWriterError(f"Tracked path is dirty or staged: {relative}")
    mode, object_id = _head_object_id(root, relative)
    return mode, object_id, _git_bytes(root, ["cat-file", "blob", object_id])


def _head_object_id(root: Path, relative: str) -> tuple[str, str]:
    tree = _git_bytes(root, ["ls-tree", "-z", "--full-tree", "HEAD", "--", relative])
    entries = [entry for entry in tree.split(b"\0") if entry]
    if len(entries) != 1:
        raise CreativeWriterError(f"HEAD does not contain exactly one regular blob for {relative}")
    header, path_bytes = entries[0].split(b"\t", 1)
    mode, object_type, object_id = header.decode("ascii").split()
    if path_bytes.decode("utf-8") != relative or mode not in {"100644", "100755"} or object_type != "blob":
        raise CreativeWriterError(f"HEAD path is not a regular blob: {relative}")
    if len(object_id) != _git_object_id_length(root) or not re.fullmatch(r"[0-9a-f]+", object_id):
        raise CreativeWriterError(f"HEAD path has a malformed Git blob object ID: {relative}")
    return mode, object_id


def _candidate_blob_object_id(root: Path, commit: str, relative: str) -> str:
    tree = _git_bytes(root, ["ls-tree", "-z", "--full-tree", commit, "--", relative])
    entries = [entry for entry in tree.split(b"\0") if entry]
    if len(entries) != 1:
        raise CreativeWriterError(f"Candidate commit does not contain exactly one entry for {relative}")
    header, path_bytes = entries[0].split(b"\t", 1)
    mode, object_type, object_id = header.decode("ascii").split(" ")
    if path_bytes.decode("utf-8") != relative or mode not in {"100644", "100755"} or object_type != "blob":
        raise CreativeWriterError(f"Candidate file is not a regular blob: {relative}")
    if len(object_id) != _git_object_id_length(root) or not re.fullmatch(r"[0-9a-f]+", object_id):
        raise CreativeWriterError(f"Candidate path has a malformed Git blob object ID: {relative}")
    return object_id


def _verify_current_candidate_file(root: Path, path: Path, relative: str, *, expected_object_id: str | None = None) -> tuple[str, str]:
    _mode, object_id = _stage_zero_blob(root, relative)
    status = _git_stdout(root, ["status", "--porcelain=v1", "--untracked-files=all", "--", relative])
    if status.strip():
        raise CreativeWriterError(f"Candidate file is dirty or staged: {relative}")
    _head_mode, head_object_id = _head_object_id(root, relative)
    if expected_object_id is not None and head_object_id != expected_object_id:
        raise CreativeWriterError(f"Current HEAD blob differs from candidate blob for {relative}")
    return object_id, head_object_id


def _preflight_validation(root: Path, slug: str) -> _ValidationPreflight:
    """Read trusted HEAD protocol files before any partition access."""

    story_dir = _story_path(root, slug)
    source_study = story_dir / "source-study"
    analysis_path = source_study / "analysis.yml"
    validation_path = source_study / "validation.md"
    analysis_relative = _relative_to_root(analysis_path, root)
    validation_relative = _relative_to_root(validation_path, root)
    if not (root / ".git").exists():
        raise CreativeWriterError(
            "Validation requires schema-v2 clean HEAD protocol blobs, candidate_frozen or validated status, and a reachable candidate commit; configured generated paths/known corpus-analysis keys were not checked"
        )
    try:
        _analysis_mode, _analysis_oid, analysis_bytes = _head_blob(root, analysis_relative)
        _validation_mode, _validation_oid, validation_bytes = _head_blob(root, validation_relative)
    except CreativeWriterError as exc:
        raise CreativeWriterError(
            f"Validation requires schema-v2 clean HEAD protocol blobs and configured generated paths/known corpus-analysis keys: {exc}"
        ) from exc
    try:
        validation, _ = parse_validation_document(
            validation_bytes.decode("utf-8"), validation_path
        )
    except (UnicodeError, yaml.YAMLError, ValidationError, CreativeWriterError) as exc:
        raise CreativeWriterError(f"Trusted validation protocol is invalid: {exc}") from exc
    if validation.stage not in {"candidate_frozen", "validated"}:
        raise CreativeWriterError("Validation requires a candidate_frozen or validated record")
    if not validation.candidate_commit:
        raise CreativeWriterError("Validation record is missing candidate_commit")
    _verify_candidate_commit(root, validation.candidate_commit)

    candidate_analysis_path = source_study / "analysis.yml"
    candidate_manifest_path = source_study / "holdouts.yml"
    candidate_profile_path = source_study / "wells-profile.md"
    candidate_ledger_path = source_study / "evidence-ledger.yml"
    candidate_quantitative_profile_path = source_study / "quantitative-profile.yml"
    candidate_paths = {
        "analysis": candidate_analysis_path,
        "manifest": candidate_manifest_path,
        "profile": candidate_profile_path,
        "ledger": candidate_ledger_path,
    }
    candidate_relative = {
        name: _relative_to_root(path, root) for name, path in candidate_paths.items()
    }
    candidate_blobs = {
        name: _candidate_git_blob_record(root, validation.candidate_commit, relative)
        for name, relative in candidate_relative.items()
    }
    quantitative_relative = _relative_to_root(candidate_quantitative_profile_path, root)
    quantitative_blob = _candidate_git_blob_record(
        root, validation.candidate_commit, quantitative_relative
    )
    recorded_hashes = {
        "analysis": validation.candidate_analysis_sha256,
        "manifest": validation.candidate_manifest_sha256,
        "profile": validation.candidate_profile_sha256,
        "ledger": validation.candidate_ledger_sha256,
    }
    for name, (_object_id, data) in candidate_blobs.items():
        actual_hash = sha256_bytes(data)
        if actual_hash != recorded_hashes[name]:
            raise CreativeWriterError(
                f"Candidate {name} SHA-256 mismatch: expected {recorded_hashes[name]}, got {actual_hash}"
            )

    # Hash checks above deliberately precede all current profile/ledger reads.
    for name, path in candidate_paths.items():
        _verify_current_candidate_file(
            root,
            path,
            candidate_relative[name],
            expected_object_id=candidate_blobs[name][0] if name in {"analysis", "manifest"} or validation.stage == "candidate_frozen" else None,
        )
    _verify_current_candidate_file(
        root,
        candidate_quantitative_profile_path,
        quantitative_relative,
    )

    try:
        config = AnalysisConfig.model_validate(
            yaml.safe_load(candidate_blobs["analysis"][1].decode("utf-8"))
        )
        manifest = HoldoutManifest.model_validate(
            yaml.safe_load(candidate_blobs["manifest"][1].decode("utf-8"))
        )
        candidate_profile_bytes = candidate_blobs["profile"][1]
        candidate_ledger_bytes = candidate_blobs["ledger"][1]
        raw_ledger = yaml.safe_load(candidate_ledger_bytes.decode("utf-8"))
        candidate_ledger = EvidenceLedger.model_validate(raw_ledger)
        candidate_quantitative_profile = QuantitativeProfile.model_validate(
            yaml.safe_load(quantitative_blob[1].decode("utf-8"))
        )
    except (UnicodeError, yaml.YAMLError, ValidationError, TypeError) as exc:
        raise CreativeWriterError(f"Frozen candidate files are not valid structured content: {exc}") from exc
    if config.study_status not in {"candidate_frozen", "validated"}:
        raise CreativeWriterError(
            "Validation requires analysis.yml study_status candidate_frozen or validated"
        )
    if not (
        validation.stage == config.study_status
        or (config.study_status == "candidate_frozen" and validation.stage == "validated")
    ):
        raise CreativeWriterError(
            f"Validation record stage `{validation.stage}` does not match config status `{config.study_status}`"
        )
    if candidate_ledger.study_id != config.study_id:
        raise CreativeWriterError("Frozen candidate ledger study identity does not match analysis.yml")
    if candidate_ledger.stage != "development":
        raise CreativeWriterError("Frozen candidate ledger must remain at development stage")

    profile_relative = _relative_to_root(candidate_profile_path, root)
    ledger_relative = _relative_to_root(candidate_ledger_path, root)
    if validation.stage == "candidate_frozen" and (
        _head_object_id(root, profile_relative)[1] != candidate_blobs["profile"][0]
        or _head_object_id(root, ledger_relative)[1] != candidate_blobs["ledger"][0]
    ):
        raise CreativeWriterError("Current candidate profile or ledger bytes drift from the frozen Git commit")
    generated_paths = _resolve_generated_paths(root, slug, config)
    lock_path = generated_paths["corpus_lock"]
    manifest_path = candidate_manifest_path
    try:
        # The lock is generated-only; the frozen manifest supplies its trusted
        # path and digest just as it does for the physical passage indexes.
        lock_bytes = _read_bytes(lock_path, label="corpus lock")
        lock = CorpusLock.model_validate(json.loads(lock_bytes.decode("utf-8")))
        manifest_bytes = candidate_blobs["manifest"][1]
    except (OSError, UnicodeError, json.JSONDecodeError, yaml.YAMLError, ValidationError, CreativeWriterError) as exc:
        raise CreativeWriterError(f"Validation corpus lock/manifest could not be loaded: {exc}") from exc
    expected_index_paths = {
        "development": _relative_to_root(generated_paths["development_passage_index"], root),
        "heldout_wells": _relative_to_root(generated_paths["heldout_wells_passage_index"], root),
        "tier4_controls": _relative_to_root(generated_paths["tier4_control_passage_index"], root),
    }
    bindings = {
        "development": manifest.development_passage_index,
        "heldout_wells": manifest.heldout_wells_passage_index,
        "tier4_controls": manifest.tier4_control_passage_index,
    }
    if manifest.corpus_lock.path != _relative_to_root(lock_path, root):
        raise CreativeWriterError("Corpus-lock manifest binding path does not match configured path")
    if manifest.corpus_lock.sha256 != sha256_bytes(lock_bytes):
        raise CreativeWriterError("Corpus-lock manifest binding hash does not match generated bytes")
    expected_registry_hashes = {
        config.admission_registry.path: config.admission_registry.sha256,
        config.source_registry.path: config.source_registry.sha256,
    }
    if manifest.registry_hashes != expected_registry_hashes or lock.registry_hashes != expected_registry_hashes:
        raise CreativeWriterError("Committed corpus registry hashes do not match analysis.yml")
    if (
        manifest.partition_seed != config.partition.seed
        or manifest.algorithm_version != config.partition.algorithm_version
        or manifest.whole_work_holdouts != list(config.partition.whole_work_holdouts)
    ):
        raise CreativeWriterError("Committed holdout manifest differs from the configured partition")
    if any(binding.path != expected_index_paths[partition] for partition, binding in bindings.items()):
        raise CreativeWriterError("Committed holdout manifest index paths do not match configured generated paths")
    return _ValidationPreflight(
        config=config,
        validation=validation,
        candidate_ledger=candidate_ledger,
        candidate_quantitative_profile=candidate_quantitative_profile,
        candidate_profile_bytes=candidate_profile_bytes,
        candidate_ledger_bytes=candidate_ledger_bytes,
        candidate_profile_path=candidate_profile_path,
        candidate_ledger_path=candidate_ledger_path,
        root=root,
        slug=slug,
        manifest_path=manifest_path,
        lock_path=lock_path,
        manifest=manifest,
        lock=lock,
    )


def _load_validation_corpus(
    root: Path, slug: str, config: AnalysisConfig, *, include_controls: bool
) -> _ValidationCorpus:
    """Compatibility shim using the same sealed path as the validation entry."""

    preflight = _preflight_validation(root, slug)
    if preflight.config != config:
        raise CreativeWriterError("Validation corpus configuration does not match trusted analysis.yml")
    freeze = _freeze_from_preflight(preflight)
    heldout = open_heldout_wells(freeze)
    controls: ControlCorpus | None = None
    if include_controls:
        controls = open_tier4_controls(authorize_control_access(freeze, heldout))
    return _corpus_from_capabilities(
        freeze,
        heldout,
        controls,
        manifest=preflight.manifest,
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


def _reject_premature_heldout_assessed_records(record: ValidationRecord) -> None:
    if record.validation_step != "heldout_assessed":
        return
    premature = [
        label
        for label, values in (
            ("control comparisons", record.control_comparisons),
            ("reviewer records", record.reviewer_records),
            ("claim transitions", record.claim_transitions),
        )
        if values
    ]
    if premature:
        raise CreativeWriterError(
            "heldout_assessed validation contains premature final records: "
            + ", ".join(premature)
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
    candidate_claims: list[EvidenceClaim] | None = None,
    include_controls: bool = True,
) -> None:
    """Validate exact target/result/reviewer bindings after partition access."""

    by_id = {passage.passage_id: passage for passage in corpus.passages}
    claims = {claim.id: claim for claim in (candidate_claims or [])}
    if not claims and candidate_claim_ids is not None:
        claims = {claim_id: None for claim_id in candidate_claim_ids}

    def target_sets(claim_id: str) -> tuple[set[str], set[str], bool]:
        claim = claims.get(claim_id)
        if claim is None:
            raise CreativeWriterError(f"Validation target registry lacks candidate claim `{claim_id}`")
        expectation = claim.validation_expectation
        return (
            {target.id for target in expectation.heldout_targets},
            {target.id for target in expectation.control_targets},
            False,
        )

    heldout_seen: dict[tuple[str, str], str] = {}
    for result in record.heldout_claim_results:
        if candidate_claim_ids is not None and result.claim_id not in candidate_claim_ids:
            raise CreativeWriterError(f"Held-out result `{result.id}` references undeclared claim `{result.claim_id}`")
        heldout_key = (result.claim_id, result.expectation_target_id)
        if heldout_key in heldout_seen:
            raise CreativeWriterError(f"Held-out expectation target `{result.expectation_target_id}` is covered more than once")
        heldout_seen[heldout_key] = result.id
        claim = claims.get(result.claim_id)
        heldout_targets, _control_targets, legacy = target_sets(result.claim_id)
        if not legacy and result.expectation_target_id not in heldout_targets:
            raise CreativeWriterError(f"Held-out result `{result.id}` references an unknown expectation target")
        target = next((item for item in getattr(getattr(claim, "validation_expectation", None), "heldout_targets", []) if item.id == result.expectation_target_id), None)
        if target is not None and (result.witness_id != target.witness_id or result.role != target.role):
            raise CreativeWriterError(f"Held-out result `{result.id}` does not match its expectation target witness or role")
        if result.witness_id not in {passage.witness_id for passage in corpus.passages if passage.passage_id in corpus.heldout_ids}:
            raise CreativeWriterError(f"Held-out result `{result.id}` is outside the heldout_wells partition")
        if any(passage_id not in corpus.heldout_ids for passage_id in result.passage_ids):
            raise CreativeWriterError(f"Held-out result `{result.id}` references a non-held-out passage")
        passages = [by_id.get(passage_id) for passage_id in result.passage_ids]
        if any(passage is None for passage in passages):
            raise CreativeWriterError(f"Held-out result `{result.id}` references an unresolved passage")
        if any(passage.witness_id != result.witness_id for passage in passages if passage is not None):
            raise CreativeWriterError(f"Held-out result `{result.id}` mixes witness passage IDs")
        if corpus.witness_tiers.get(result.witness_id) not in {1, 2, 3}:
            raise CreativeWriterError(f"Held-out result `{result.id}` has a non-Wells authority tier")
        if result.role not in corpus.witness_roles.get(result.witness_id, []):
            raise CreativeWriterError(f"Held-out result `{result.id}` has an undeclared witness role")

    if candidate_claim_ids is not None:
        for claim_id in candidate_claim_ids:
            claim = claims.get(claim_id)
            if claim is not None and claim.status == "rejected":
                if any(item.claim_id == claim_id for item in record.heldout_claim_results):
                    raise CreativeWriterError(f"Rejected claim `{claim_id}` must not receive held-out evidence")
                continue
            expected, _, legacy = target_sets(claim_id)
            actual = {item.expectation_target_id for item in record.heldout_claim_results if item.claim_id == claim_id}
            if not legacy and actual != expected:
                raise CreativeWriterError(f"Held-out result target set for `{claim_id}` is not exactly the declared target set")

    if not include_controls:
        return

    control_seen: dict[tuple[str, str], str] = {}
    control_witness_ids = {passage.witness_id for passage in corpus.passages if passage.passage_id in corpus.control_ids}
    for comparison in record.control_comparisons:
        if candidate_claim_ids is not None and comparison.claim_id not in candidate_claim_ids:
            raise CreativeWriterError(f"Control comparison `{comparison.id}` references undeclared claim `{comparison.claim_id}`")
        control_key = (comparison.claim_id, comparison.expectation_target_id)
        if control_key in control_seen:
            raise CreativeWriterError(f"Control expectation target `{comparison.expectation_target_id}` is covered more than once")
        control_seen[control_key] = comparison.id
        claim = claims.get(comparison.claim_id)
        _heldout_targets, control_targets, legacy = target_sets(comparison.claim_id)
        if not legacy and comparison.expectation_target_id not in control_targets:
            raise CreativeWriterError(f"Control comparison `{comparison.id}` references an unknown expectation target")
        if comparison.witness_id not in control_witness_ids:
            raise CreativeWriterError(f"Control comparison `{comparison.id}` is outside the tier4_controls partition")
        if any(passage_id not in corpus.control_ids for passage_id in comparison.passage_ids):
            raise CreativeWriterError(f"Control comparison `{comparison.id}` references a non-control passage")
        passages = [by_id.get(passage_id) for passage_id in comparison.passage_ids]
        if any(passage is None for passage in passages):
            raise CreativeWriterError(f"Control comparison `{comparison.id}` references an unresolved passage")
        if any(passage.witness_id != comparison.witness_id for passage in passages if passage is not None):
            raise CreativeWriterError(f"Control comparison `{comparison.id}` mixes witness passage IDs")
        if corpus.witness_tiers.get(comparison.witness_id) != 4:
            raise CreativeWriterError(f"Control comparison `{comparison.id}` is not Tier 4")
        if comparison.role not in corpus.witness_roles.get(comparison.witness_id, []):
            raise CreativeWriterError(f"Control comparison `{comparison.id}` has an undeclared witness role")
        target = next((item for item in getattr(getattr(claim, "validation_expectation", None), "control_targets", []) if item.id == comparison.expectation_target_id), None)
        if target is not None and (comparison.witness_id != target.witness_id or comparison.role != target.role):
            raise CreativeWriterError(f"Control comparison `{comparison.id}` does not match its expectation target witness or role")

    if candidate_claim_ids is not None:
        for claim_id in candidate_claim_ids:
            claim = claims.get(claim_id)
            if claim is not None and claim.status == "rejected":
                if any(item.claim_id == claim_id for item in record.control_comparisons):
                    raise CreativeWriterError(f"Rejected claim `{claim_id}` must not receive control evidence")
                continue
            _, expected, legacy = target_sets(claim_id)
            actual = {item.expectation_target_id for item in record.control_comparisons if item.claim_id == claim_id}
            if not legacy and actual != expected:
                raise CreativeWriterError(f"Control comparison target set for `{claim_id}` is not exactly the declared target set")

    reviewers_by_key: set[tuple[str, str]] = set()
    heldout_ids = {item.id for item in record.heldout_claim_results}
    control_ids = {item.id for item in record.control_comparisons}
    for reviewer in record.reviewer_records:
        key = (reviewer.claim_id, reviewer.reviewer_id)
        if key in reviewers_by_key:
            raise CreativeWriterError(f"Duplicate reviewer record for claim `{reviewer.claim_id}` and reviewer `{reviewer.reviewer_id}`")
        reviewers_by_key.add(key)
        if candidate_claim_ids is not None and reviewer.claim_id not in candidate_claim_ids:
            raise CreativeWriterError(f"Reviewer `{reviewer.id}` references undeclared claim `{reviewer.claim_id}`")
        expected_heldout = {item.id for item in record.heldout_claim_results if item.claim_id == reviewer.claim_id}
        expected_control = {item.id for item in record.control_comparisons if item.claim_id == reviewer.claim_id}
        if set(reviewer.heldout_result_ids) != expected_heldout or not set(reviewer.heldout_result_ids) <= heldout_ids:
            raise CreativeWriterError(f"Reviewer `{reviewer.id}` does not link the complete held-out result set")
        if set(reviewer.control_comparison_ids) != expected_control or not set(reviewer.control_comparison_ids) <= control_ids:
            raise CreativeWriterError(f"Reviewer `{reviewer.id}` does not link the complete control comparison set")


def _validate_review_provenance(
    record: ValidationRecord,
    candidate_claim_ids: set[str],
    *,
    require_complete: bool,
) -> None:
    """Validate the distributed review-run graph before final publication."""

    runs = {run.run_id: run for run in record.review_run_provenance}
    if not require_complete:
        if runs:
            raise CreativeWriterError(
                "Review provenance is not permitted before complete validation"
            )
        return
    if not runs:
        raise CreativeWriterError(
            "Complete validation requires review provenance runs"
        )

    heldout = {item.id: item for item in record.heldout_claim_results}
    controls = {item.id: item for item in record.control_comparisons}
    reviewers = {item.id: item for item in record.reviewer_records}
    record_claims = {
        **{item_id: item.claim_id for item_id, item in heldout.items()},
        **{item_id: item.claim_id for item_id, item in controls.items()},
        **{item_id: item.claim_id for item_id, item in reviewers.items()},
    }
    if len(record_claims) != len(heldout) + len(controls) + len(reviewers):
        raise CreativeWriterError("Review provenance record IDs must be unique across record types")

    produced_by: dict[str, str] = {}
    for run in record.review_run_provenance:
        assigned = set(run.assigned_claim_ids)
        unknown_claims = assigned - candidate_claim_ids
        if unknown_claims:
            raise CreativeWriterError(
                f"Review run `{run.run_id}` assigns undeclared claim(s): {sorted(unknown_claims)}"
            )
        for record_id in run.produced_record_ids:
            if record_id not in record_claims:
                raise CreativeWriterError(
                    f"Review run `{run.run_id}` links unknown record `{record_id}`"
                )
            if record_id in produced_by:
                raise CreativeWriterError(
                    f"Review record `{record_id}` is produced by more than one review run"
                )
            if record_claims[record_id] not in assigned:
                raise CreativeWriterError(
                    f"Review run `{run.run_id}` links record `{record_id}` for an unassigned claim"
                )
            produced_by[record_id] = run.run_id
            if record_id in heldout and run.stage != "heldout_review":
                raise CreativeWriterError(
                    f"Held-out result `{record_id}` is linked from a non-held-out review run"
                )
            if record_id in controls and run.stage != "control_review":
                raise CreativeWriterError(
                    f"Control comparison `{record_id}` is linked from a non-control review run"
                )
            if record_id in reviewers and run.stage != "claim_synthesis":
                raise CreativeWriterError(
                    f"Reviewer record `{record_id}` is linked from a non-synthesis review run"
                )

    missing_records = set(record_claims) - set(produced_by)
    if missing_records:
        raise CreativeWriterError(
            f"Complete validation has review records without provenance links: {sorted(missing_records)}"
        )
    if not any(
        run.stage == "whole_study_audit"
        and run.independent_of_candidate_authorship
        and set(run.assigned_claim_ids) == candidate_claim_ids
        for run in record.review_run_provenance
    ):
        raise CreativeWriterError(
            "Complete validation requires an independent whole-study audit "
            "covering all candidate claims"
        )

    for reviewer in record.reviewer_records:
        linked_runs = []
        for run_id in reviewer.review_run_ids:
            run = runs.get(run_id)
            if run is None:
                raise CreativeWriterError(
                    f"Reviewer record `{reviewer.id}` links unknown review provenance run `{run_id}`"
                )
            if reviewer.claim_id not in run.assigned_claim_ids:
                raise CreativeWriterError(
                    f"Reviewer record `{reviewer.id}` links review provenance run `{run_id}` for a different claim"
                )
            linked_runs.append(run)
        stages = {run.stage for run in linked_runs}
        if "claim_synthesis" not in stages:
            raise CreativeWriterError(
                f"Reviewer record `{reviewer.id}` must link a claim-synthesis run"
            )
        for result_id in reviewer.heldout_result_ids:
            run_id = produced_by.get(result_id)
            if run_id is None or not any(run.run_id == run_id for run in linked_runs):
                raise CreativeWriterError(
                    f"Reviewer record `{reviewer.id}` does not link the provenance run for held-out result `{result_id}`"
                )
        for comparison_id in reviewer.control_comparison_ids:
            run_id = produced_by.get(comparison_id)
            if run_id is None or not any(run.run_id == run_id for run in linked_runs):
                raise CreativeWriterError(
                    f"Reviewer record `{reviewer.id}` does not link the provenance run for control comparison `{comparison_id}`"
                )


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
    final_profile_text: str | None = None,
) -> str:
    ledger = report_ledger or preflight.candidate_ledger
    lines = [
        "# Phase 2B analysis report",
        "",
        "This report is a deterministic compilation of the trusted validation record, corpus bindings, quantitative profile, descriptive profile, evidence ledger, and review records.",
        "",
        "## Corpus and authority summary",
        "",
        f"- Study: `{config.study_id}`",
        f"- Validation step: `{preflight.validation.validation_step}`",
        f"- Composition window: `{config.composition_window.start}-{config.composition_window.end}`",
        f"- Corpus counts: {preflight.lock.counts.model_dump(mode='json')}",
        f"- Admission registry: `{config.admission_registry.path}` (`{config.admission_registry.sha256}`)",
        f"- Source registry: `{config.source_registry.path}` (`{config.source_registry.sha256}`)",
        f"- Authority policy: `{config.authority_policy_version}`",
        "- Authority tiers:",
    ]
    for policy in config.authority_tiers:
        if policy.tier == 4 and metrics.tier4_controls is None:
            continue
        roles = ", ".join(f"`{role}`" for role in policy.analytical_roles)
        lines.append(
            f"  - Tier {policy.tier}: {policy.jurisdiction} Roles: {roles or '`none declared`'}."
        )
    lines.extend(["- Partition bindings:"])
    for binding in (
        preflight.manifest.development_passage_index,
        preflight.manifest.heldout_wells_passage_index,
        preflight.manifest.tier4_control_passage_index,
    ):
        if binding.partition == "tier4_controls" and metrics.tier4_controls is None:
            continue
        lines.append(
            f"  - `{binding.partition}`: `{binding.path}` ({binding.passage_count} passages; "
            f"witnesses={binding.witness_ids}; SHA-256 `{binding.sha256}`)."
        )
    lines.extend(
        [
            "",
            "## Method and limitations",
            "",
            f"- Input format: `{config.passage_rules.input_format}`; context radius: `{config.passage_rules.context_radius}` substantive blocks.",
            f"- Partition algorithm: `{config.partition.algorithm_version}` with seed `{config.partition.seed}` and holdout fraction `{config.partition.holdout_fraction}`.",
            f"- Enabled measurements: {', '.join(f'`{item}`' for item in config.enabled_measurements)}.",
            "- Measurements remain per witness; no pooled Wells target, significance test, authorship verdict, or metric-to-authenticity rule is calculated.",
            f"- Validation summary: {preflight.validation.holdout_summary}",
            f"- Control summary: {preflight.validation.control_summary if metrics.tier4_controls is not None else 'Control material remains quarantined at this stage.'}",
            f"- Review summary: {preflight.validation.reviewer_summary}",
            "",
            "## Per-witness quantitative baselines",
            "",
        ]
    )
    if preflight.candidate_quantitative_profile.witnesses:
        for witness in preflight.candidate_quantitative_profile.witnesses:
            lines.append(
                f"### Witness `{witness.witness_id}` (source `{witness.source_id}`)"
            )
            lines.append(
                "- Values: "
                + "; ".join(
                    f"`{key}: {value}`" for key, value in sorted(witness.values.items())
                )
            )
            lines.extend(
                [
                    f"- Variation: {witness.variation}",
                    f"- Limitations: {witness.limitations}",
                    f"- Interpretive relevance: {witness.interpretive_relevance}",
                    "",
                ]
            )
    else:
        lines.append("- No candidate-frozen per-witness quantitative baselines were recorded.")

    if final and final_profile_text is not None:
        lines.extend(["", "## Final profile synthesis by dimension", ""])
        profile_lines = final_profile_text.splitlines()
        dimension_starts = [
            index for index, line in enumerate(profile_lines) if line.startswith("### ")
        ]
        for index, start in enumerate(dimension_starts):
            end = dimension_starts[index + 1] if index + 1 < len(dimension_starts) else len(profile_lines)
            lines.extend(profile_lines[start:end])
            lines.append("")

    lines.extend(
        [
            f"## {'Final descriptive claims' if final else 'Candidate descriptive claims'}",
            "",
        ]
    )
    for claim in ledger.claims:
        support = ", ".join(
            f"`{reference.passage_id}` ({reference.witness_id})"
            for reference in claim.supporting_passages
        ) or "none"
        counterexamples = ", ".join(
            f"`{reference.passage_id}` ({reference.witness_id})"
            for reference in claim.counterexample_passages
        ) or "none"
        search = claim.counterexample_search
        search_summary = (
            "not recorded"
            if search is None
            else (
                f"`{search.method}` / `{search.coverage}` / `{search.outcome}`; "
                f"witnesses={search.witness_ids}; passage locators={search.searched_passage_ids}; "
                f"notes={search.notes}"
            )
        )
        lines.extend(
            [
                f"### Claim `{claim.id}`",
                "",
                f"- Statement: {claim.statement}",
                f"- Status: `{claim.status}`; confidence: `{claim.confidence}`; classification: `{claim.classification}`.",
                f"- Jurisdiction: `{claim.jurisdiction.scope}`; roles={claim.jurisdiction.roles}; eligible witnesses={claim.jurisdiction.eligible_witness_ids}.",
                f"- Supporting passage locators: {support}.",
                f"- Counterexample/variation passage locators: {counterexamples}.",
                f"- Counterexample search: {search_summary}.",
                f"- Scope and limits: {claim.scope_and_limits}",
                "",
            ]
        )
    lines.extend(["", "## Held-out results", ""])
    if preflight.validation.heldout_claim_results:
        for result in preflight.validation.heldout_claim_results:
            lines.append(
                f"- `{result.id}` for claim `{result.claim_id}` at `{result.witness_id}`: "
                f"{result.assessment}; passage locators={result.passage_ids}. "
                f"{result.observed_tendency} Notes: {result.notes}"
            )
    else:
        lines.append("- Held-out results have not been recorded at this stage.")
    lines.extend(["", "## Control comparisons", ""])
    if metrics.tier4_controls is None:
        lines.append("- Control material remains quarantined until held-out assessment authorises access.")
    elif preflight.validation.control_comparisons:
        for comparison in preflight.validation.control_comparisons:
            lines.append(
                f"- `{comparison.id}` for claim `{comparison.claim_id}` at `{comparison.witness_id}`: "
                f"`{comparison.result}`; passage locators={comparison.passage_ids}. "
                f"{comparison.comparison} Notes: {comparison.notes}"
            )
    else:
        lines.append("- Tier 4 material is accessible at this validation step, but no control comparison has been recorded yet.")
    lines.extend(["", "## Review provenance and records", ""])
    if preflight.validation.review_run_provenance:
        for run in preflight.validation.review_run_provenance:
            lines.append(
                f"- Run `{run.run_id}` ({run.stage}) by `{run.reviewer_id}` / role `{run.role_id}`: "
                f"assigned claims={run.assigned_claim_ids}; method={run.method}; materials={run.materials_seen}; "
                f"independent_of_candidate_authorship={run.independent_of_candidate_authorship}; "
                f"anonymisation={run.anonymisation_status}; outcome={run.outcome}; "
                f"produced records={run.produced_record_ids or 'none'}; limitations={run.limitations}"
            )
        for reviewer in preflight.validation.reviewer_records:
            lines.append(
                f"- Reviewer record `{reviewer.id}` for claim `{reviewer.claim_id}` by `{reviewer.reviewer_id}`: "
                f"outcome=`{reviewer.outcome}`; review runs={reviewer.review_run_ids}; "
                f"held-out records={reviewer.heldout_result_ids}; controls={reviewer.control_comparison_ids}. {reviewer.notes}"
            )
    else:
        lines.append("- Review-run provenance is not yet present at this stage.")
    lines.extend(["", "## Claim transitions", ""])
    if preflight.validation.claim_transitions:
        for transition in preflight.validation.claim_transitions:
            lines.append(
                f"- `{transition.claim_id}`: `{transition.from_status}`/`{transition.from_confidence}` -> "
                f"`{transition.to_status}`/`{transition.to_confidence}`; reason: {transition.reason}; "
                f"held-out results={transition.heldout_result_ids}; controls={transition.control_comparison_ids}; "
                f"reviewers={transition.reviewer_record_ids}."
            )
    else:
        lines.append("- No final claim transitions have been recorded at this stage.")
    lines.extend(["", "## Candidate and final hashes", ""])
    lines.extend(
        [
            f"- Candidate commit: `{preflight.validation.candidate_commit}`",
            f"- Candidate analysis SHA-256: `{preflight.validation.candidate_analysis_sha256}`",
            f"- Candidate manifest SHA-256: `{preflight.validation.candidate_manifest_sha256}`",
            f"- Candidate profile SHA-256: `{preflight.validation.candidate_profile_sha256}`",
            f"- Candidate ledger SHA-256: `{preflight.validation.candidate_ledger_sha256}`",
            f"- Final profile SHA-256: `{preflight.validation.final_profile_sha256 or 'not recorded at this stage'}`",
            f"- Final ledger SHA-256: `{preflight.validation.final_ledger_sha256 or 'not recorded at this stage'}`",
        ]
    )
    lines.extend(["", "## Unresolved uncertainty and rejected claims", "", f"- {preflight.validation.unresolved_uncertainty}"])
    rejected = [claim for claim in ledger.claims if claim.status == "rejected"]
    if rejected:
        lines.extend(f"- Rejected claim retained: `{claim.id}` — {claim.notes}" for claim in rejected)
    else:
        lines.append("- No rejected claims are present in the report ledger.")
    lines.extend(
        [
            "",
            "## Phase 2C stop boundary",
            "",
            "This report remains descriptive. It does not authorise style guidance, style-card changes, writing instructions, phrase banks, linter implementation, story planning, or manuscript changes. Phase 2C requires separate design approval and explicit human approval of Phase 2B.",
        ]
    )
    if final:
        lines.extend(["", "## Final compiled status", "", "The final report includes the trusted final profile, validated ledger, recorded validation outcomes, review provenance, and retained rejected claims."])
    return "\n".join(lines).rstrip() + "\n"


def _corpus_from_capabilities(
    freeze: VerifiedFreeze,
    heldout: HeldoutCorpus,
    controls: ControlCorpus | None = None,
    *,
    manifest: HoldoutManifest | None = None,
) -> _ValidationCorpus:
    passages = list(heldout.records)
    heldout_ids = set(heldout.ids)
    control_ids: set[str] = set()
    witness_tiers = dict(heldout.witness_tiers)
    witness_roles = dict(heldout.witness_roles)
    if controls is not None:
        passages.extend(controls.records)
        control_ids = set(controls.ids)
        witness_tiers.update(controls.witness_tiers)
        witness_roles.update(controls.witness_roles)
    return _ValidationCorpus(
        lock=freeze.lock,
        manifest=manifest,
        passages=passages,
        heldout_ids=heldout_ids,
        control_ids=control_ids,
        witness_tiers=witness_tiers,
        witness_roles=witness_roles,
        registry=heldout.registry,
    )


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
        "jurisdiction",
        "supporting_passages",
        "counterexample_passages",
        "counterexample_search",
        "scope_and_limits",
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
        else:
            if current.status != "rejected":
                raise CreativeWriterError(f"Rejected claim `{claim_id}` may not be resurrected")
            if (
                transition.heldout_result_ids
                or transition.control_comparison_ids
                or transition.reviewer_record_ids
            ):
                raise CreativeWriterError(f"Rejected claim `{claim_id}` transition must not link validation evidence")
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
    _config_mode, _config_oid, config_bytes = _head_blob(
        build_root, _relative_to_root(config_path, build_root)
    )
    _manifest_mode, _manifest_oid, manifest_bytes = _head_blob(
        build_root, _relative_to_root(manifest_path, build_root)
    )
    return ValidationMetricsDocument(
        schema_version=1,
        stage=validation.stage,
        validation_step=validation.validation_step,
        study_id=config.study_id,
        provenance=ValidationMetricProvenance(
            study_id=config.study_id,
            tool_version=TOOL_VERSION,
            stage=validation.stage,
            validation_step=validation.validation_step,
            config_sha256=sha256_bytes(config_bytes),
            index_sha256=_sha256(generated_paths["heldout_wells_passage_index"]),
            manifest_sha256=sha256_bytes(manifest_bytes),
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
    freeze = _freeze_from_preflight(preflight)
    if validation.stage == "candidate_frozen" and validation.validation_step == "frozen":
        if validation.heldout_claim_results or validation.control_comparisons or validation.reviewer_records:
            raise CreativeWriterError("frozen validation step cannot contain held-out, control, or reviewer records")
        heldout = open_heldout_wells(freeze)
        corpus = _corpus_from_capabilities(freeze, heldout, manifest=preflight.manifest)
        metrics = _build_validation_metrics(config, validation, generated_paths, corpus)
        generation_id = _write_validation_outputs(
            generated_paths,
            metrics=metrics,
            packet=_validation_packet(corpus, include_controls=False, context_radius=config.passage_rules.context_radius),
            report=_validation_report(config=config, preflight=preflight, corpus=corpus, metrics=metrics, final=False),
        )
        return _make_result(root, slug, generated_paths=generated_paths, holdout_path=_story_path(root, slug) / "source-study" / "holdouts.yml", witness_count=len(metrics.heldout_wells.witnesses), passage_count=len(corpus.heldout_ids), generation_id=generation_id)

    if validation.stage == "candidate_frozen" and validation.validation_step == "heldout_assessed":
        _reject_premature_heldout_assessed_records(validation)
        _require_validation_treatment(validation, candidate_claims, require_controls=False, require_reviewers=False)
        heldout = open_heldout_wells(freeze)
        corpus = _corpus_from_capabilities(freeze, heldout, manifest=preflight.manifest)
        _validate_record_partitions(
            validation,
            corpus,
            candidate_claim_ids={claim.id for claim in candidate_claims},
            candidate_claims=candidate_claims,
            include_controls=False,
        )
        control_access = authorize_control_access(freeze, heldout)
        controls = open_tier4_controls(control_access)
        corpus = _corpus_from_capabilities(freeze, heldout, controls, manifest=preflight.manifest)
        metrics = _build_validation_metrics(config, validation, generated_paths, corpus)
        generation_id = _write_validation_outputs(
            generated_paths,
            metrics=metrics,
            packet=_validation_packet(corpus, include_controls=True, context_radius=config.passage_rules.context_radius),
            report=_validation_report(config=config, preflight=preflight, corpus=corpus, metrics=metrics, final=False),
        )
        return _make_result(root, slug, generated_paths=generated_paths, holdout_path=_story_path(root, slug) / "source-study" / "holdouts.yml", witness_count=len(metrics.heldout_wells.witnesses) + len(metrics.tier4_controls.witnesses if metrics.tier4_controls else []), passage_count=len(corpus.passages), generation_id=generation_id)

    if validation.stage != "validated" or validation.validation_step != "complete":
        raise CreativeWriterError("Validation record must use frozen, heldout_assessed, or complete step for its configured stage")
    _require_validation_treatment(validation, candidate_claims, require_controls=True, require_reviewers=True)
    heldout = open_heldout_wells(freeze)
    heldout_corpus = _corpus_from_capabilities(freeze, heldout, manifest=preflight.manifest)
    _validate_record_partitions(
        validation,
        heldout_corpus,
        candidate_claim_ids={claim.id for claim in candidate_claims},
        candidate_claims=candidate_claims,
        include_controls=False,
    )
    control_access = authorize_control_access(freeze, heldout)
    controls = open_tier4_controls(control_access)
    corpus = _corpus_from_capabilities(freeze, heldout, controls, manifest=preflight.manifest)
    _validate_record_partitions(
        validation,
        corpus,
        candidate_claim_ids={claim.id for claim in candidate_claims},
        candidate_claims=candidate_claims,
    )
    _validate_review_provenance(
        validation,
        {claim.id for claim in candidate_claims},
        require_complete=True,
    )
    story_dir = _story_path(root, slug)
    final_profile_path = story_dir / "source-study" / "wells-profile.md"
    final_ledger_path = story_dir / "source-study" / "evidence-ledger.yml"
    period_controls_path = story_dir / "source-study" / "period-controls.md"
    try:
        _profile_mode, _profile_oid, final_profile_bytes = _head_blob(
            root, _relative_to_root(final_profile_path, root)
        )
    except CreativeWriterError as exc:
        raise CreativeWriterError(
            f"Unable to read final profile from its trusted HEAD blob: {exc}"
        ) from exc
    if sha256_bytes(final_profile_bytes) != validation.final_profile_sha256:
        raise CreativeWriterError("Final profile SHA-256 does not match validation.md")
    try:
        final_profile_text = final_profile_bytes.decode("utf-8")
    except UnicodeError as exc:
        raise CreativeWriterError("Final profile artifact is not valid UTF-8") from exc
    try:
        _ledger_mode, _ledger_oid, final_ledger_bytes = _head_blob(
            root, _relative_to_root(final_ledger_path, root)
        )
    except CreativeWriterError as exc:
        raise CreativeWriterError(
            f"Unable to read final ledger from its trusted HEAD blob: {exc}"
        ) from exc
    if sha256_bytes(final_ledger_bytes) != validation.final_ledger_sha256:
        raise CreativeWriterError("Final ledger SHA-256 does not match validation.md")
    try:
        _validation_mode, _validation_oid, _trusted_validation_bytes = _head_blob(
            root, _relative_to_root(story_dir / "source-study" / "validation.md", root)
        )
        _controls_mode, _controls_oid, _trusted_controls_bytes = _head_blob(
            root, _relative_to_root(period_controls_path, root)
        )
        final_ledger = EvidenceLedger.model_validate(
            yaml.safe_load(final_ledger_bytes.decode("utf-8"))
        )
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError, CreativeWriterError) as exc:
        raise CreativeWriterError(f"Unable to read final validation artifacts from trusted HEAD blobs: {exc}") from exc
    if final_ledger.stage != "validated" or final_ledger.study_id != config.study_id:
        raise CreativeWriterError("Final evidence ledger must be validated and match the study")
    validate_profile_claim_links(
        final_profile_path,
        final_ledger,
        config,
        stage="validated",
        content=final_profile_text,
    )
    try:
        controls_text = _trusted_controls_bytes.decode("utf-8")
    except UnicodeError as exc:
        raise CreativeWriterError(
            f"Final period-controls artifact is not valid UTF-8: {exc}"
        ) from exc
    validate_period_controls(
        controls_text,
        validation.control_comparisons,
        file=period_controls_path,
    )
    _validate_final_claims(candidate=preflight.candidate_ledger, final=final_ledger, validation=validation)
    metrics = _build_validation_metrics(config, validation, generated_paths, corpus)
    generation_id = _write_validation_outputs(
        generated_paths,
        metrics=metrics,
        packet=_validation_packet(corpus, include_controls=True, context_radius=config.passage_rules.context_radius),
            report=_validation_report(
                config=config,
                preflight=preflight,
                corpus=corpus,
                metrics=metrics,
                final=True,
                report_ledger=final_ledger,
                final_profile_text=final_profile_text,
            ),
    )
    return _make_result(root, slug, generated_paths=generated_paths, holdout_path=story_dir / "source-study" / "holdouts.yml", witness_count=len(corpus.witness_tiers), passage_count=len(corpus.passages), generation_id=generation_id)



def _make_result(root: Path, slug: str, *, generated_paths: dict[str, Path], holdout_path: Path, witness_count: int, passage_count: int, generation_id: str | None = None) -> object:
    from creative_writer.source_analysis import SourceAnalysisResult
    return SourceAnalysisResult(stage="validate", story_slug=slug, witness_count=witness_count, passage_count=passage_count, generated_paths=generated_paths, holdout_path=holdout_path, holdout_manifest_created=False, generation_id=generation_id)

def _validation_payloads(metrics: ValidationMetricsDocument, packet: str, report: str) -> dict[str, bytes]:
    return {"validation-metrics.json": (json.dumps(metrics.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2) + "\n").encode("utf-8"), "validation-packet.md": packet.encode("utf-8"), "analysis-report.md": report.encode("utf-8")}

def _write_validation_outputs(generated_paths: dict[str, Path], *, metrics: ValidationMetricsDocument, packet: str, report: str) -> str:
    validation_root = generated_paths["validation_metrics"].parent.parent
    return publish_validation_generation(validation_root, _validation_payloads(metrics, packet, report)).generation_id

def _freeze_from_preflight(preflight: _ValidationPreflight) -> VerifiedFreeze:
    generated = _resolve_generated_paths(preflight.root, preflight.slug, preflight.config)
    heldout_binding = preflight.manifest.heldout_wells_passage_index
    heldout_witness_ids = set(heldout_binding.witness_ids)
    heldout_witnesses = tuple(
        witness
        for witness in preflight.manifest.witnesses
        if witness.witness_id in heldout_witness_ids
    )
    return VerifiedFreeze(_CAPABILITY_SEAL, preflight.root, preflight.slug, preflight.config, preflight.validation, preflight.candidate_ledger, preflight.candidate_profile_bytes, preflight.candidate_ledger_bytes, preflight.candidate_profile_path, preflight.candidate_ledger_path, generated["heldout_wells_passage_index"], heldout_binding, heldout_witnesses, preflight.lock)

def open_heldout_wells(capability: VerifiedFreeze) -> HeldoutCorpus:
    if not _genuine(capability, VerifiedFreeze):
        raise CreativeWriterError("held-out opening requires a genuine verified freeze")
    story_dir = _story_path(capability.root, capability.slug)
    admission_path = _registry_path(story_dir, capability.config.admission_registry.path)
    source_path = _registry_path(story_dir, capability.config.source_registry.path)
    admission_bytes = _head_model_bytes(capability.root, admission_path, "Admission registry")
    source_bytes = _head_model_bytes(capability.root, source_path, "Source registry")
    if sha256_bytes(admission_bytes) != capability.config.admission_registry.sha256:
        raise CreativeWriterError("Admission registry SHA-256 does not match analysis.yml")
    if sha256_bytes(source_bytes) != capability.config.source_registry.sha256:
        raise CreativeWriterError("Source registry SHA-256 does not match analysis.yml")
    admission = SourceStudyAdmission.model_validate(yaml.safe_load(admission_bytes.decode("utf-8")))
    registry = SourcesRegistry.model_validate(yaml.safe_load(source_bytes.decode("utf-8")))
    source_tiers = _validate_lock_registry_metadata(
        capability.config, capability.lock, admission, registry, slug=capability.slug
    )
    roles = {source.id: list(source.role.analytical_roles) for source in registry.sources}
    records = _read_bound_partition(capability.heldout_index_path, capability.heldout_index_binding, expected_path=_relative_to_root(capability.heldout_index_path, capability.root), expected_partition="heldout_wells")
    allowed_witnesses = set(capability.heldout_index_binding.witness_ids)
    ids = {
        passage_id
        for witness in capability.heldout_witnesses
        if witness.witness_id in allowed_witnesses
        for window in witness.holdout_windows
        for passage_id in window.passage_ids
    }
    if {record.passage_id for record in records} != ids:
        raise CreativeWriterError("Held-out Wells index membership differs from manifest")
    if any(source_tiers.get(record.source_id) not in {1, 2, 3} for record in records):
        raise CreativeWriterError("Held-out Wells index contains a non-Wells passage")
    witness_tiers = {
        witness.witness_id: source_tiers[witness.source_id]
        for witness in capability.lock.witnesses
    }
    witness_roles = {
        witness.witness_id: roles[witness.source_id]
        for witness in capability.lock.witnesses
    }
    return HeldoutCorpus(_CAPABILITY_SEAL, capability, tuple(records), frozenset(ids), witness_tiers, witness_roles, registry)

def authorize_control_access(capability: VerifiedFreeze, heldout: HeldoutCorpus) -> VerifiedControlAccess:
    if not _genuine(capability, VerifiedFreeze) or not _genuine(heldout, HeldoutCorpus) or heldout.freeze is not capability:
        raise CreativeWriterError("control authorization requires the genuine freeze and its held-out corpus")
    if capability.validation.validation_step not in {"heldout_assessed", "complete"}:
        raise CreativeWriterError(
            "Tier 4 control authorization is unavailable before complete held-out assessment"
        )
    _reject_premature_heldout_assessed_records(capability.validation)
    candidate_claim_ids = {claim.id for claim in capability.candidate_ledger.claims}
    _require_validation_treatment(
        capability.validation,
        capability.candidate_ledger.claims,
        require_controls=False,
        require_reviewers=False,
    )
    _validate_record_partitions(capability.validation, _ValidationCorpus(capability.lock, None, list(heldout.records), set(heldout.ids), set(), heldout.witness_tiers, heldout.witness_roles, heldout.registry), candidate_claim_ids=candidate_claim_ids, candidate_claims=capability.candidate_ledger.claims, include_controls=False)
    generated = _resolve_generated_paths(capability.root, capability.slug, capability.config)
    candidate_commit = capability.validation.candidate_commit
    if candidate_commit is None:
        raise CreativeWriterError("Verified freeze is missing its pinned candidate commit")
    manifest_path = _story_path(capability.root, capability.slug) / "source-study/holdouts.yml"
    _manifest_object_id, manifest_bytes = _candidate_git_blob_record(
        capability.root,
        candidate_commit,
        _relative_to_root(manifest_path, capability.root),
    )
    actual_manifest_hash = sha256_bytes(manifest_bytes)
    if actual_manifest_hash != capability.validation.candidate_manifest_sha256:
        raise CreativeWriterError(
            "Candidate manifest SHA-256 changed before control authorization"
        )
    try:
        manifest = HoldoutManifest.model_validate(
            yaml.safe_load(manifest_bytes.decode("utf-8"))
        )
    except (UnicodeError, yaml.YAMLError, ValidationError, TypeError) as exc:
        raise CreativeWriterError(
            f"Pinned candidate holdout manifest is invalid: {exc}"
        ) from exc
    if manifest.heldout_wells_passage_index != capability.heldout_index_binding:
        raise CreativeWriterError("Held-out binding changed before control authorization")
    control_binding = manifest.tier4_control_passage_index
    control_witness_ids = set(control_binding.witness_ids)
    control_witnesses = tuple(
        witness for witness in manifest.witnesses if witness.witness_id in control_witness_ids
    )
    return VerifiedControlAccess(
        _CAPABILITY_SEAL,
        capability,
        heldout,
        control_witnesses,
        generated["tier4_control_passage_index"],
        control_binding,
    )

def open_tier4_controls(capability: VerifiedControlAccess) -> ControlCorpus:
    if not _genuine(capability, VerifiedControlAccess):
        raise CreativeWriterError("Tier 4 controls require a genuine control-access capability")
    freeze = capability.freeze
    records = _read_bound_partition(capability.control_index_path, capability.control_index_binding, expected_path=_relative_to_root(capability.control_index_path, freeze.root), expected_partition="tier4_controls")
    allowed_witnesses = set(capability.control_index_binding.witness_ids)
    ids = {
        passage_id
        for witness in capability.control_witnesses
        if witness.witness_id in allowed_witnesses
        for window in witness.holdout_windows
        for passage_id in window.passage_ids
    }
    if {record.passage_id for record in records} != ids:
        raise CreativeWriterError("Tier 4 control index membership differs from manifest")
    source_tiers = {source.id: source.tier for source in freeze.lock.sources}
    roles = {source.id: list(source.analytical_roles) for source in freeze.lock.sources}
    if any(source_tiers.get(record.source_id) != 4 for record in records):
        raise CreativeWriterError("Tier 4 control index contains a non-control passage")
    witness_tiers = {
        witness.witness_id: source_tiers[witness.source_id]
        for witness in freeze.lock.witnesses
        if witness.source_id in source_tiers
    }
    witness_roles = {
        witness.witness_id: roles[witness.source_id]
        for witness in freeze.lock.witnesses
        if witness.source_id in roles
    }
    controls = ControlCorpus(_CAPABILITY_SEAL, capability, tuple(records), frozenset(ids), witness_tiers, witness_roles)
    if freeze.validation.validation_step == "complete":
        corpus = _corpus_from_capabilities(freeze, capability.heldout, controls)
        _validate_record_partitions(
            freeze.validation,
            corpus,
            candidate_claim_ids={claim.id for claim in freeze.candidate_ledger.claims},
            candidate_claims=freeze.candidate_ledger.claims,
        )
    return controls


def run_validation(root: Path, slug: str) -> object:
    return _validate(root, slug)

__all__ = ["ControlCorpus", "HeldoutCorpus", "VerifiedControlAccess", "VerifiedFreeze", "authorize_control_access", "open_heldout_wells", "open_tier4_controls", "publish_validation_generation", "read_current_validation_generation", "run_validation"]
