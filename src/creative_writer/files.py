"""Filesystem and parsing helpers."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from creative_writer.exceptions import CreativeWriterError
from creative_writer.models import ChapterDocument, ChapterFrontMatter

T = TypeVar("T", bound=BaseModel)


def repo_root(start: Path | None = None) -> Path:
    """Return the repository root by walking upward to pyproject.toml."""

    current = (start or Path.cwd()).resolve()
    for path in (current, *current.parents):
        if (path / "pyproject.toml").exists():
            return path
    raise CreativeWriterError("Could not locate repo root from current directory.")


def ensure_directory(path: Path) -> None:
    """Create a directory tree if it does not already exist."""

    path.mkdir(parents=True, exist_ok=True)


def load_yaml_model(path: Path, model_type: type[T]) -> T:
    """Load YAML content into a validated Pydantic model."""

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CreativeWriterError(f"Missing file: {path}") from exc
    except yaml.YAMLError as exc:
        raise CreativeWriterError(f"Invalid YAML in {path}: {exc}") from exc

    if raw is None:
        raw = {}

    if not isinstance(raw, dict):
        raise CreativeWriterError(
            f"YAML in {path} must parse to a mapping, not {type(raw).__name__}."
        )

    try:
        return model_type.model_validate(raw)
    except ValidationError as exc:
        raise CreativeWriterError(f"Schema validation failed for {path}:\n{exc}") from exc


def split_front_matter(text: str, path: Path) -> tuple[dict[str, Any], str]:
    """Split a Markdown document into YAML front matter and body."""

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise CreativeWriterError(f"{path} must start with YAML front matter.")

    closing_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        raise CreativeWriterError(f"{path} is missing the closing front matter fence.")

    front_matter_text = "".join(lines[1:closing_index])
    body = "".join(lines[closing_index + 1 :]).lstrip("\n")

    try:
        front_matter = yaml.safe_load(front_matter_text)
    except yaml.YAMLError as exc:
        raise CreativeWriterError(f"Invalid YAML front matter in {path}: {exc}") from exc

    if front_matter is None:
        front_matter = {}

    if not isinstance(front_matter, dict):
        raise CreativeWriterError(f"Front matter in {path} must parse to a mapping.")

    return front_matter, body


def load_chapter_document(story_dir: Path, stub_path: Path) -> ChapterDocument:
    """Load and validate one chapter stub plus its full manuscript file."""

    text = stub_path.read_text(encoding="utf-8")
    raw_front_matter, stub_body = split_front_matter(text, stub_path)

    try:
        front_matter = ChapterFrontMatter.model_validate(raw_front_matter)
    except ValidationError as exc:
        raise CreativeWriterError(
            f"Chapter front matter validation failed for {stub_path}:\n{exc}"
        ) from exc

    manuscript_path = story_dir / front_matter.manuscript
    try:
        manuscript_body = manuscript_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CreativeWriterError(
            f"Missing manuscript file for {stub_path}: {manuscript_path}"
        ) from exc

    return ChapterDocument(
        stub_path=stub_path,
        manuscript_path=manuscript_path,
        front_matter=front_matter,
        stub_body=stub_body,
        manuscript_body=manuscript_body,
    )


def write_text(path: Path, content: str) -> None:
    """Write text after ensuring the parent directory exists."""

    ensure_directory(path.parent)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
