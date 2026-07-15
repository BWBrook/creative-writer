"""Small pure/shared primitives for the source-analysis artifact boundary."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from collections.abc import Mapping
import fcntl
from pathlib import Path
from typing import Any

from creative_writer.exceptions import CreativeWriterError


def canonical_json_bytes(payload: Any, *, indent: int | None = 2) -> bytes:
    """Return deterministic UTF-8 JSON bytes with an explicit final LF."""

    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=indent,
            separators=None if indent is not None else (",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact bytes."""

    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Hash a regular file without decoding or normalising its contents."""

    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise CreativeWriterError(f"Unable to hash {path}: {exc}") from exc
    return digest.hexdigest()


def validate_relative_path(value: str) -> str:
    """Validate canonical repository-relative POSIX path syntax."""

    if not isinstance(value, str) or not value or value.startswith("/"):
        raise CreativeWriterError("path must be a non-empty relative POSIX path")
    parts = value.split("/")
    if "\\" in value or any(part in {"", ".", ".."} for part in parts):
        raise CreativeWriterError("path must use canonical relative POSIX syntax")
    return value


def safe_relative_path(root: Path, relative: str) -> Path:
    """Resolve a repository-relative path and reject lexical/symlink escapes."""

    validate_relative_path(relative)
    resolved_root = root.resolve(strict=False)
    lexical = resolved_root / relative
    try:
        lexical.relative_to(resolved_root)
        resolved = lexical.resolve(strict=False)
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise CreativeWriterError(f"Path escapes repository root: {relative}") from exc
    if resolved != lexical:
        raise CreativeWriterError(
            f"Path redirects through a symlink: {relative} -> {resolved}"
        )
    return lexical


VALIDATION_PAYLOAD_NAMES = (
    "validation-metrics.json",
    "validation-packet.md",
    "analysis-report.md",
)
_GENERATION_ID_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class ValidationGenerationSnapshot:
    """A complete, already-pinned validation generation."""

    generation_id: str
    directory: Path
    paths: dict[str, Path]
    bytes: dict[str, bytes]
    manifest: dict[str, Any]


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _validation_manifest(payloads: Mapping[str, bytes]) -> tuple[bytes, str]:
    if set(payloads) != set(VALIDATION_PAYLOAD_NAMES):
        raise CreativeWriterError(
            "validation generation must contain exactly the three validation payloads"
        )
    manifest = {
        "schema_version": 1,
        "files": [
            {
                "path": name,
                "sha256": sha256_bytes(payloads[name]),
                "size": len(payloads[name]),
            }
            for name in VALIDATION_PAYLOAD_NAMES
        ],
    }
    manifest_bytes = canonical_json_bytes(manifest, indent=None)
    return manifest_bytes, sha256_bytes(manifest_bytes)


def _verify_generation_directory(
    directory: Path, generation_id: str
) -> ValidationGenerationSnapshot:
    if not _GENERATION_ID_RE.fullmatch(generation_id):
        raise CreativeWriterError("validation generation ID must be exactly 64 lowercase hex characters")
    if directory.is_symlink() or not directory.is_dir():
        raise CreativeWriterError("validation generation directory is not a regular directory")
    manifest_path = directory / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise CreativeWriterError("validation generation manifest is not a regular file")
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CreativeWriterError(f"invalid validation generation manifest: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise CreativeWriterError("validation generation manifest has an invalid schema")
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise CreativeWriterError("validation generation manifest files must be a list")
    if len(entries) != len(VALIDATION_PAYLOAD_NAMES):
        raise CreativeWriterError("validation generation manifest must list exactly three files")
    if any(not isinstance(entry, dict) for entry in entries):
        raise CreativeWriterError("validation generation manifest contains a non-object file entry")
    expected_manifest_bytes, expected_id = _validation_manifest(
        {
            name: (directory / name).read_bytes()
            for name in VALIDATION_PAYLOAD_NAMES
            if (directory / name).is_file() and not (directory / name).is_symlink()
        }
    ) if all(
        (directory / name).is_file() and not (directory / name).is_symlink()
        for name in VALIDATION_PAYLOAD_NAMES
    ) else (b"", "")
    if expected_id != generation_id or manifest_bytes != expected_manifest_bytes:
        raise CreativeWriterError("validation generation manifest does not match its generation ID")
    paths: dict[str, Path] = {}
    payload_bytes: dict[str, bytes] = {}
    for entry in entries:
        name = entry.get("path")
        if name not in VALIDATION_PAYLOAD_NAMES or name in paths:
            raise CreativeWriterError("validation generation manifest has invalid or duplicate file entries")
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise CreativeWriterError(f"validation generation payload is not a regular file: {name}")
        data = path.read_bytes()
        if entry.get("sha256") != sha256_bytes(data) or entry.get("size") != len(data):
            raise CreativeWriterError(f"validation generation payload hash/size mismatch: {name}")
        paths[name] = path
        payload_bytes[name] = data
    if set(paths) != set(VALIDATION_PAYLOAD_NAMES):
        raise CreativeWriterError("validation generation manifest is incomplete")
    return ValidationGenerationSnapshot(
        generation_id=generation_id,
        directory=directory,
        paths=paths,
        bytes=payload_bytes,
        manifest=manifest,
    )


def _managed_current_generation(validation_root: Path) -> ValidationGenerationSnapshot:
    current = validation_root / "current"
    if current.is_symlink():
        target = os.readlink(current)
    else:
        raise CreativeWriterError("validation/current is not a managed relative symlink")
    match = re.fullmatch(r"generations/([0-9a-f]{64})", target)
    if match is None:
        raise CreativeWriterError("validation/current target is not generations/<64hex>")
    generation_id = match.group(1)
    generations = validation_root / "generations"
    generation = generations / generation_id
    if generation.resolve(strict=False) != generation:
        raise CreativeWriterError("validation/current generation redirects through a symlink")
    return _verify_generation_directory(generation, generation_id)


def read_current_validation_generation(validation_root: Path) -> ValidationGenerationSnapshot:
    """Resolve and verify ``current`` once; callers use this pinned triple."""

    return _managed_current_generation(validation_root)


def publish_validation_generation(
    validation_root: Path, payloads: Mapping[str, bytes]
) -> ValidationGenerationSnapshot:
    """Publish three validation payloads with one relative symlink swap."""

    validation_root = Path(validation_root)
    generations = validation_root / "generations"
    lock_path = validation_root / ".publication.lock"
    validation_root.mkdir(parents=True, exist_ok=True)
    generations.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    staging: Path | None = None
    renamed = False
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        for stale in generations.glob(".staging-*"):
            if stale.is_dir() and not stale.is_symlink():
                shutil.rmtree(stale)
            elif stale.exists() or stale.is_symlink():
                stale.unlink()
        manifest_bytes, generation_id = _validation_manifest(payloads)
        final = generations / generation_id
        if final.exists() or final.is_symlink():
            existing = _verify_generation_directory(final, generation_id)
            current = validation_root / "current"
            if current.is_symlink() and os.readlink(current) == f"generations/{generation_id}":
                return existing
            # Reuse the complete immutable generation, but still publish it through
            # the same single managed pointer swap when it is not current.
            _fsync_directory(generations)
            tmp_link = validation_root / f".current-{uuid.uuid4().hex}"
            os.symlink(f"generations/{generation_id}", tmp_link)
            try:
                os.replace(tmp_link, current)
            finally:
                if tmp_link.is_symlink() or tmp_link.exists():
                    tmp_link.unlink(missing_ok=True)
            _fsync_directory(validation_root)
            return _verify_generation_directory(final, generation_id)
        staging = generations / f".staging-{uuid.uuid4().hex}"
        staging.mkdir()
        for name in VALIDATION_PAYLOAD_NAMES:
            path = staging / name
            with path.open("wb") as handle:
                handle.write(payloads[name])
                handle.flush()
                os.fsync(handle.fileno())
        manifest_path = staging / "manifest.json"
        with manifest_path.open("wb") as handle:
            handle.write(manifest_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_directory(staging)
        os.replace(staging, final)
        staging = None
        renamed = True
        _fsync_directory(generations)
        tmp_link = validation_root / f".current-{uuid.uuid4().hex}"
        os.symlink(f"generations/{generation_id}", tmp_link)
        try:
            os.replace(tmp_link, validation_root / "current")
        finally:
            if tmp_link.is_symlink() or tmp_link.exists():
                tmp_link.unlink(missing_ok=True)
        _fsync_directory(validation_root)
        return _verify_generation_directory(final, generation_id)
    except (CreativeWriterError, OSError) as exc:
        if staging is not None and (staging.exists() or staging.is_symlink()):
            if staging.is_dir() and not staging.is_symlink():
                shutil.rmtree(staging, ignore_errors=True)
            else:
                staging.unlink(missing_ok=True)
        if isinstance(exc, CreativeWriterError):
            raise
        raise CreativeWriterError(f"Unable to publish validation generation: {exc}") from exc
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)
