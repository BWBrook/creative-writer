"""Hashing and repository-relative path helpers shared by the style tools."""

from __future__ import annotations

import hashlib
from pathlib import Path

from creative_writer.exceptions import CreativeWriterError


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
