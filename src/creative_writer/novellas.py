"""Import/export helpers for the shared OneDrive Novellas folder."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from creative_writer.checks import check_story
from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory, write_text

NOVELLAS_ENV_VAR = "CREATIVE_WRITER_NOVELLAS_DIR"
DEFAULT_NOVELLAS_CANDIDATES = [
    Path(
        "~/Library/CloudStorage/OneDrive-UniversityofTasmania/Documents/Novellas"
    ).expanduser(),
    Path(
        "~/Library/Group Containers/UBF8T346G9.OneDriveStandaloneSuite/"
        "OneDrive - University of Tasmania.noindex/"
        "OneDrive - University of Tasmania/Documents/Novellas"
    ).expanduser(),
]
SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def resolve_novellas_dir() -> Path:
    """Resolve the shared Novellas folder, with env override support."""

    override = os.environ.get(NOVELLAS_ENV_VAR)
    if override:
        path = Path(override).expanduser().resolve()
        if not path.exists():
            raise CreativeWriterError(
                f"{NOVELLAS_ENV_VAR} points to a missing path: {path}"
            )
        return path

    for candidate in DEFAULT_NOVELLAS_CANDIDATES:
        if candidate.exists():
            return candidate.resolve()

    joined = "\n".join(f"- {candidate}" for candidate in DEFAULT_NOVELLAS_CANDIDATES)
    raise CreativeWriterError(
        "Could not locate the OneDrive Novellas folder.\n"
        f"Set {NOVELLAS_ENV_VAR} or ensure one of these paths exists:\n{joined}"
    )


def slugify_stem(name: str) -> str:
    """Convert a filename stem into a repo-friendly slug."""

    slug = SLUG_PATTERN.sub("-", name.lower()).strip("-")
    if not slug:
        raise CreativeWriterError(f"Could not derive a valid slug from '{name}'.")
    return slug


def title_from_stem(name: str) -> str:
    """Convert a slug-ish name to a title-cased filename."""

    return " ".join(part.capitalize() for part in slugify_stem(name).split("-"))


def ensure_ingested_readme(root: Path) -> None:
    """Create the ingested README if it does not already exist."""

    readme_path = root / "ingested" / "README.md"
    if readme_path.exists():
        return
    write_text(
        readme_path,
        """
        # Ingested Documents

        This directory holds Markdown files imported from the shared OneDrive
        `Documents/Novellas` folder.

        Imported media, when present, is extracted under `ingested/media/`.
        """,
    )


def import_novella(root: Path, source_name: str) -> Path:
    """Import a DOCX from the Novellas folder into `ingested/` as Markdown."""

    novellas_dir = resolve_novellas_dir()
    source_path = novellas_dir / source_name
    if not source_path.exists():
        raise CreativeWriterError(f"Source file does not exist: {source_path}")
    if source_path.suffix.lower() != ".docx":
        raise CreativeWriterError("Import currently supports .docx files only.")

    ensure_ingested_readme(root)
    ensure_directory(root / "ingested")

    slug = slugify_stem(source_path.stem)
    dest_path = root / "ingested" / f"{slug}.md"
    media_dir = root / "ingested" / "media" / slug

    command = [
        "pandoc",
        str(source_path),
        "--from=docx",
        "--to=gfm+yaml_metadata_block",
        "--wrap=none",
        "--extract-media",
        str(media_dir),
        "--output",
        str(dest_path),
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise CreativeWriterError("Pandoc is not installed or not on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or exc.stdout.strip() or "unknown Pandoc error"
        raise CreativeWriterError(
            f"Pandoc failed while importing {source_name}: {stderr}"
        ) from exc

    return dest_path


def export_novella(root: Path, input_path: str, output_name: str | None = None) -> Path:
    """Export a repo Markdown file to DOCX in the Novellas folder."""

    novellas_dir = resolve_novellas_dir()
    source_path = Path(input_path)
    if not source_path.is_absolute():
        source_path = root / source_path
    source_path = source_path.resolve()

    if not source_path.exists():
        raise CreativeWriterError(f"Markdown source does not exist: {source_path}")
    if source_path.suffix.lower() != ".md":
        raise CreativeWriterError("Export currently supports Markdown sources only.")

    destination_name = output_name or f"{title_from_stem(source_path.stem)}.docx"
    if not destination_name.lower().endswith(".docx"):
        destination_name = f"{destination_name}.docx"

    destination_path = novellas_dir / destination_name
    resource_path = os.pathsep.join([str(source_path.parent), str(root)])

    command = [
        "pandoc",
        str(source_path),
        "--from=gfm+yaml_metadata_block",
        "--resource-path",
        resource_path,
        "--output",
        str(destination_path),
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise CreativeWriterError("Pandoc is not installed or not on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or exc.stdout.strip() or "unknown Pandoc error"
        raise CreativeWriterError(
            f"Pandoc failed while exporting {source_path.name}: {stderr}"
        ) from exc

    return destination_path


def clear_ingested(root: Path, story_slug: str) -> list[Path]:
    """Clear a converted ingested source after sanity checks succeed."""

    ingested_markdown = root / "ingested" / f"{story_slug}.md"
    ingested_media_dir = root / "ingested" / "media" / story_slug
    story_dir = root / "stories" / story_slug

    if not ingested_markdown.exists() and not ingested_media_dir.exists():
        raise CreativeWriterError(
            f"No ingested source found for story slug '{story_slug}'."
        )
    if not story_dir.exists():
        raise CreativeWriterError(
            f"Cannot clear ingested material because story directory is missing: {story_dir}"
        )

    result = check_story(root, story_slug)
    if not result.ok:
        raise CreativeWriterError(
            f"Cannot clear ingested material for '{story_slug}' because story checks fail. "
            f"See {result.report_path}."
        )

    story_text_matches = list(story_dir.rglob("*.md")) + list(story_dir.rglob("*.yml"))
    offending_paths: list[Path] = []
    for path in story_text_matches:
        text = path.read_text(encoding="utf-8")
        if "ingested/" in text:
            offending_paths.append(path)

    if offending_paths:
        joined = "\n".join(f"- {path}" for path in offending_paths)
        raise CreativeWriterError(
            "Cannot clear ingested material because story files still reference "
            "`ingested/` paths:\n"
            f"{joined}"
        )

    if ingested_media_dir.exists():
        image_files = [path for path in ingested_media_dir.rglob("*") if path.is_file()]
        story_assets_dir = story_dir / "assets" / "images"
        story_asset_files = (
            [path for path in story_assets_dir.rglob("*") if path.is_file()]
            if story_assets_dir.exists()
            else []
        )
        story_asset_files = [
            path for path in story_asset_files if path.name.lower() != "readme.md"
        ]
        if image_files and not story_asset_files:
            raise CreativeWriterError(
                "Cannot clear ingested media because the imported source had extracted "
                "images but the story has no copied assets under assets/images/."
            )

    removed: list[Path] = []
    if ingested_markdown.exists():
        ingested_markdown.unlink()
        removed.append(ingested_markdown)
    if ingested_media_dir.exists():
        shutil.rmtree(ingested_media_dir)
        removed.append(ingested_media_dir)

    media_root = root / "ingested" / "media"
    if media_root.exists() and not any(media_root.iterdir()):
        media_root.rmdir()
        removed.append(media_root)

    return removed
