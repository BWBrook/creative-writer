"""Manifest-driven targeted review packs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory, load_chapter_document, load_yaml_model
from creative_writer.models import ReviewPackEntry, ReviewPackManifest, StoryConfig
from creative_writer.source_analysis_common import safe_relative_path

IGNORED_REVIEW_PACK_FILES = {"README.md", "_template.yml"}


@dataclass(slots=True)
class ResolvedReviewPackEntry:
    """A validated excerpt ready for rendering."""

    entry: ReviewPackEntry
    excerpt: str
    chapter_title: str | None
    chapter_summary: str | None


@dataclass(slots=True)
class ReviewPackResult:
    """Completed review-pack generation result."""

    story_slug: str
    story_title: str
    pack_name: str
    manifest_path: Path
    output_path: Path
    entry_count: int


def review_packs_dir(story_dir: Path) -> Path:
    """Return the story-local review-pack directory."""

    return story_dir / "review-packs"


def _contained_review_packs_dir(story_dir: Path) -> Path:
    expected = review_packs_dir(story_dir)
    try:
        directory = safe_relative_path(story_dir, "review-packs")
    except CreativeWriterError as exc:
        raise CreativeWriterError(
            f"{expected}: review-packs directory must be physically contained "
            f"and must not be a symlink: {exc}"
        ) from exc
    if directory.exists() and (not directory.is_dir() or directory.is_symlink()):
        raise CreativeWriterError(
            f"{directory}: review-packs directory must be a physical directory"
        )
    return directory


def _contained_review_pack_manifest(story_dir: Path, manifest_path: Path) -> Path:
    directory = _contained_review_packs_dir(story_dir)
    if manifest_path.suffix != ".yml":
        raise CreativeWriterError(
            f"{manifest_path}: review-pack manifest must end in .yml"
        )
    if manifest_path.is_symlink():
        raise CreativeWriterError(
            f"{manifest_path}: review-pack manifest must not be a symlink"
        )
    try:
        resolved_directory = directory.resolve(strict=True)
        resolved_manifest = manifest_path.resolve(strict=True)
    except OSError as exc:
        raise CreativeWriterError(
            f"{manifest_path}: unable to resolve review-pack manifest: {exc}"
        ) from exc
    if resolved_manifest.parent != resolved_directory:
        raise CreativeWriterError(
            f"{manifest_path}: review-pack manifest is outside the story "
            f"review-packs directory {directory}"
        )
    if not resolved_manifest.is_file():
        raise CreativeWriterError(
            f"{manifest_path}: review-pack manifest is not a regular file"
        )
    return manifest_path


def review_pack_manifest_paths(story_dir: Path) -> list[Path]:
    """Return real review-pack manifests for a story."""

    directory = _contained_review_packs_dir(story_dir)
    if not directory.exists():
        return []

    manifests: list[Path] = []
    for path in sorted(directory.glob("*.yml")):
        if path.name in IGNORED_REVIEW_PACK_FILES:
            continue
        manifests.append(_contained_review_pack_manifest(story_dir, path))
    return manifests


def _resolve_pack_manifest_path(story_dir: Path, pack: str) -> Path:
    error = (
        "Review-pack name must be a story-local YAML filename with an optional "
        ".yml suffix."
    )
    if not isinstance(pack, str):
        raise CreativeWriterError(error)
    pack_name = pack.strip()
    candidate = Path(pack_name)
    if (
        not pack_name
        or "\\" in pack_name
        or candidate.is_absolute()
        or len(candidate.parts) != 1
        or pack_name in {".", ".."}
    ):
        raise CreativeWriterError(error)
    if candidate.suffix:
        if candidate.suffix != ".yml":
            raise CreativeWriterError(error)
    elif "." in pack_name:
        raise CreativeWriterError(error)
    else:
        pack_name = f"{pack_name}.yml"

    manifest_path = _contained_review_packs_dir(story_dir) / pack_name
    return _contained_review_pack_manifest(story_dir, manifest_path)


def _chapter_index(story_dir: Path, story: StoryConfig) -> dict[str, tuple[str, str]]:
    index: dict[str, tuple[str, str]] = {}
    for chapter_name in story.chapters:
        chapter = load_chapter_document(story_dir, story_dir / chapter_name)
        index[chapter.front_matter.manuscript] = (
            chapter.front_matter.title,
            chapter.front_matter.summary,
        )
    return index


def _extract_excerpt(manuscript_path: Path, start_line: int, end_line: int) -> str:
    lines = manuscript_path.read_text(encoding="utf-8").splitlines()
    total_lines = len(lines)

    if start_line > total_lines:
        raise CreativeWriterError(
            f"{manuscript_path} does not contain line {start_line}; file has {total_lines} lines."
        )
    if end_line > total_lines:
        raise CreativeWriterError(
            f"{manuscript_path} does not contain line {end_line}; file has {total_lines} lines."
        )

    excerpt = "\n".join(lines[start_line - 1 : end_line]).strip("\n")
    if not excerpt.strip():
        raise CreativeWriterError(
            f"{manuscript_path}:{start_line}-{end_line} resolves to empty excerpt text."
        )
    return excerpt


def validate_review_pack_manifest(
    story_dir: Path,
    manifest_path: Path,
    chapter_index: dict[str, tuple[str, str]] | None = None,
) -> tuple[ReviewPackManifest, list[ResolvedReviewPackEntry]]:
    """Validate a review-pack manifest and resolve all excerpts."""

    manifest_path = _contained_review_pack_manifest(story_dir, manifest_path)
    manifest = load_yaml_model(manifest_path, ReviewPackManifest)
    resolved_entries: list[ResolvedReviewPackEntry] = []
    chapter_index = chapter_index or {}

    for entry in manifest.entries:
        manuscript_path = story_dir / entry.manuscript
        if not manuscript_path.exists():
            raise CreativeWriterError(
                f"Review-pack manuscript does not exist for {manifest_path}: {entry.manuscript}"
            )

        excerpt = _extract_excerpt(manuscript_path, entry.start_line, entry.end_line)
        chapter_title: str | None = None
        chapter_summary: str | None = None
        if entry.manuscript in chapter_index:
            chapter_title, chapter_summary = chapter_index[entry.manuscript]

        resolved_entries.append(
            ResolvedReviewPackEntry(
                entry=entry,
                excerpt=excerpt,
                chapter_title=chapter_title,
                chapter_summary=chapter_summary,
            )
        )

    return manifest, resolved_entries


def _render_review_pack(
    story: StoryConfig,
    pack_name: str,
    manifest: ReviewPackManifest,
    entries: list[ResolvedReviewPackEntry],
) -> str:
    lines = [
        f"# Review Pack: {manifest.title}",
        "",
        f"- Story: `{story.title}`",
        f"- Story slug: `{story.slug}`",
        f"- Pack: `{pack_name}`",
        f"- Purpose: {manifest.purpose}",
        f"- Entries: {len(entries)}",
    ]

    for index, resolved in enumerate(entries, start=1):
        entry = resolved.entry
        lines.extend(
            [
                "",
                f"## {index}. {entry.label}",
                "",
                f"- Kind: `{entry.kind}`",
                f"- Source: `{entry.manuscript}:{entry.start_line}-{entry.end_line}`",
            ]
        )
        if resolved.chapter_title:
            lines.append(f"- Chapter: `{resolved.chapter_title}`")
        if resolved.chapter_summary:
            lines.append(f"- Chapter summary: {resolved.chapter_summary}")
        if entry.context:
            lines.append(f"- Context: {entry.context}")
        lines.append(f"- Reviewer question: {entry.question}")
        if entry.style is not None:
            style = entry.style
            finding_ids = ", ".join(
                f"`{finding_id}`" for finding_id in style.finding_ids
            )
            claim_ids = ", ".join(
                f"`{claim_id}`" for claim_id in style.claim_ids
            )
            lines.extend(
                [
                    "",
                    "### Style calibration context",
                    "",
                    (
                        f"- Profile: `{style.profile_id}` version "
                        f"`{style.profile_version}`"
                    ),
                    f"- Intended role: `{style.narrative_role}`",
                    f"- Style findings: {finding_ids or 'None recorded.'}",
                    f"- Phase 2B claims: {claim_ids or 'None recorded.'}",
                    f"- AI disposition: `{style.ai_disposition}`",
                    f"- AI rationale: {style.ai_rationale}",
                    f"- Decision impact: {style.decision_impact}",
                ]
            )
        lines.extend(
            [
                "",
                "### Excerpt",
                "",
                "```text",
                resolved.excerpt,
                "```",
            ]
        )

    return "\n".join(lines) + "\n"


def generate_review_pack(root: Path, slug: str, pack: str) -> ReviewPackResult:
    """Generate one Markdown review pack from a story-local manifest."""

    story_dir = root / "stories" / slug
    if not story_dir.exists():
        raise CreativeWriterError(f"Story directory does not exist: {story_dir}")

    story = load_yaml_model(story_dir / "story.yml", StoryConfig)
    manifest_path = _resolve_pack_manifest_path(story_dir, pack)
    chapter_index = _chapter_index(story_dir, story)
    manifest, entries = validate_review_pack_manifest(
        story_dir, manifest_path, chapter_index
    )

    output_dir = root / "build" / slug / "reviews"
    ensure_directory(output_dir)
    pack_name = manifest_path.stem
    output_path = output_dir / f"{pack_name}.md"
    output_path.write_text(
        _render_review_pack(story, pack_name, manifest, entries),
        encoding="utf-8",
    )

    return ReviewPackResult(
        story_slug=slug,
        story_title=story.title,
        pack_name=pack_name,
        manifest_path=manifest_path,
        output_path=output_path,
        entry_count=len(entries),
    )
