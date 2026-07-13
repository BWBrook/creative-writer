"""Story progress and manuscript statistics."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import (
    ensure_directory,
    load_chapter_document,
    load_yaml_model,
    split_front_matter,
)
from creative_writer.models import StoryConfig

WORD_PATTERN = re.compile(r"\b\w+(?:[’'-]\w+)*\b", re.UNICODE)
IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]+\)")
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")


@dataclass(slots=True)
class ChapterStatistics:
    """Word-count statistics for one manuscript chapter."""

    index: int
    title: str
    manuscript_path: Path
    words: int
    characters: int


@dataclass(slots=True)
class CategoryStatistics:
    """Aggregated statistics for a class of Markdown files."""

    label: str
    file_count: int
    words: int


@dataclass(slots=True)
class StoryStatisticsResult:
    """Rendered manuscript statistics for one story."""

    story_slug: str
    story_title: str
    report_path: Path
    generated_at: datetime
    manuscript_total_words: int
    total_story_markdown_words: int
    supporting_markdown_words: int
    average_chapter_words: int
    estimated_reading_minutes: int
    chapter_count: int
    drafted_chapters: int
    chapter_stats: list[ChapterStatistics] = field(default_factory=list)
    category_stats: list[CategoryStatistics] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _display_title_from_stem(path: Path) -> str:
    stem = path.stem.replace("_", "-")
    words = [part for part in stem.split("-") if part]
    return " ".join(word.capitalize() for word in words) or path.stem


def _strip_optional_front_matter(text: str, path: Path) -> str:
    if text.startswith("---"):
        try:
            _, body = split_front_matter(text, path)
        except CreativeWriterError:
            return text
        return body
    return text


def _markdown_to_countable_text(text: str, path: Path) -> str:
    body = _strip_optional_front_matter(text, path)
    body = IMAGE_PATTERN.sub(r"\1", body)
    body = LINK_PATTERN.sub(r"\1", body)
    body = INLINE_CODE_PATTERN.sub(r"\1", body)
    body = HTML_TAG_PATTERN.sub(" ", body)
    body = body.replace("#", " ")
    body = body.replace("*", " ")
    body = body.replace("_", " ")
    body = body.replace(">", " ")
    return body


def count_markdown_words(path: Path) -> int:
    """Count words in a Markdown file, excluding YAML front matter."""

    text = path.read_text(encoding="utf-8")
    return count_markdown_words_from_text(text, path)


def count_markdown_words_from_text(text: str, path: Path) -> int:
    """Count words in Markdown text for an already-loaded file body."""

    countable = _markdown_to_countable_text(text, path)
    return len(WORD_PATTERN.findall(countable))


def _reading_minutes(words: int) -> int:
    if words <= 0:
        return 0
    return max(1, (words + 249) // 250)


def _supporting_markdown_categories(story_dir: Path) -> list[CategoryStatistics]:
    buckets: dict[str, list[Path]] = {
        "Outline": [],
        "Style guide": [],
        "World notes": [],
        "Chapter stubs": [],
        "Scene cards": [],
        "Other markdown": [],
    }

    for path in sorted(story_dir.rglob("*.md")):
        relative = path.relative_to(story_dir)
        if relative.parts[0] in {"manuscript", "original"}:
            continue
        if relative == Path("outline.md"):
            buckets["Outline"].append(path)
        elif relative == Path("style-guide.md"):
            buckets["Style guide"].append(path)
        elif relative == Path("world.md"):
            buckets["World notes"].append(path)
        elif relative.parts[0] == "chapter-stubs":
            buckets["Chapter stubs"].append(path)
        elif relative.parts[0] == "scene-cards":
            buckets["Scene cards"].append(path)
        else:
            buckets["Other markdown"].append(path)

    category_stats: list[CategoryStatistics] = []
    for label, paths in buckets.items():
        if not paths:
            continue
        category_stats.append(
            CategoryStatistics(
                label=label,
                file_count=len(paths),
                words=sum(count_markdown_words(path) for path in paths),
            )
        )

    return category_stats


def _collect_chapter_stats(
    story_dir: Path,
    story: StoryConfig | None,
    notes: list[str],
) -> list[ChapterStatistics]:
    chapter_stats: list[ChapterStatistics] = []

    if story:
        for index, chapter_name in enumerate(story.chapters, start=1):
            stub_path = story_dir / chapter_name
            try:
                chapter = load_chapter_document(story_dir, stub_path)
                title = chapter.front_matter.title
                manuscript_path = chapter.manuscript_path
                words = count_markdown_words_from_text(
                    chapter.manuscript_body,
                    manuscript_path,
                )
                characters = len(chapter.manuscript_body)
            except CreativeWriterError as exc:
                notes.append(f"{stub_path}: {exc}")
                fallback_path = story_dir / "manuscript" / Path(chapter_name).name
                if not fallback_path.exists():
                    continue
                title = _display_title_from_stem(fallback_path)
                manuscript_path = fallback_path
                text = fallback_path.read_text(encoding="utf-8")
                words = count_markdown_words_from_text(text, fallback_path)
                characters = len(text)

            chapter_stats.append(
                ChapterStatistics(
                    index=index,
                    title=title,
                    manuscript_path=manuscript_path,
                    words=words,
                    characters=characters,
                )
            )

        return chapter_stats

    manuscript_dir = story_dir / "manuscript"
    for index, manuscript_path in enumerate(sorted(manuscript_dir.glob("*.md")), start=1):
        text = manuscript_path.read_text(encoding="utf-8")
        chapter_stats.append(
            ChapterStatistics(
                index=index,
                title=_display_title_from_stem(manuscript_path),
                manuscript_path=manuscript_path,
                words=count_markdown_words_from_text(text, manuscript_path),
                characters=len(text),
            )
        )

    return chapter_stats


def _render_statistics_report(
    story_dir: Path,
    result: StoryStatisticsResult,
) -> str:
    lines = [
        f"# Manuscript Statistics: {result.story_title}",
        "",
        f"- Story slug: `{result.story_slug}`",
        f"- Generated (UTC): `{result.generated_at.isoformat()}`",
        f"- Story path: `{story_dir}`",
        f"- Chapters counted: {result.chapter_count}",
        f"- Chapters with manuscript words: {result.drafted_chapters}",
        f"- Total manuscript words: {result.manuscript_total_words:,}",
        f"- Average words per chapter: {result.average_chapter_words:,}",
        f"- Estimated reading time: {result.estimated_reading_minutes} minute(s)",
        f"- Supporting Markdown words: {result.supporting_markdown_words:,}",
        f"- Total story Markdown words: {result.total_story_markdown_words:,}",
        "",
        "## Chapter Breakdown",
        "",
        "| # | Chapter | Words | Characters | File |",
        "|---|---|---:|---:|---|",
    ]

    if result.chapter_stats:
        for chapter in result.chapter_stats:
            relative = chapter.manuscript_path.relative_to(story_dir)
            lines.append(
                f"| {chapter.index} | {chapter.title} | {chapter.words:,} | "
                f"{chapter.characters:,} | `{relative}` |"
            )
    else:
        lines.append("| - | No chapters found | 0 | 0 | - |")

    lines.extend(["", "## Supporting Markdown", ""])
    if result.category_stats:
        lines.append("| Category | Files | Words |")
        lines.append("|---|---:|---:|")
        for category in result.category_stats:
            lines.append(
                f"| {category.label} | {category.file_count} | {category.words:,} |"
            )
    else:
        lines.append("- No supporting Markdown files were found.")

    lines.extend(["", "## Notes", ""])
    if result.notes:
        for note in result.notes:
            lines.append(f"- {note}")
    else:
        lines.append("- None.")

    return "\n".join(lines) + "\n"


def generate_story_statistics(root: Path, story_slug: str) -> StoryStatisticsResult:
    """Generate a manuscript statistics report for one story."""

    story_dir = root / "stories" / story_slug
    if not story_dir.exists():
        raise CreativeWriterError(f"Story directory does not exist: {story_dir}")

    notes: list[str] = []
    story_title = _display_title_from_stem(Path(story_slug))
    story: StoryConfig | None = None

    story_path = story_dir / "story.yml"
    if story_path.exists():
        try:
            story = load_yaml_model(story_path, StoryConfig)
            story_title = story.title
        except CreativeWriterError as exc:
            notes.append(str(exc))
    else:
        notes.append(f"{story_path}: story.yml is missing; chapter order fell back to manuscript/*.md.")

    chapter_stats = _collect_chapter_stats(story_dir, story, notes)
    manuscript_total_words = sum(chapter.words for chapter in chapter_stats)
    supporting_categories = _supporting_markdown_categories(story_dir)
    supporting_words = sum(category.words for category in supporting_categories)
    total_story_markdown_words = manuscript_total_words + supporting_words

    report_dir = root / "build" / story_slug / "reports"
    ensure_directory(report_dir)
    report_path = report_dir / "ms-statistics.md"

    result = StoryStatisticsResult(
        story_slug=story_slug,
        story_title=story_title,
        report_path=report_path,
        generated_at=datetime.now(timezone.utc),
        manuscript_total_words=manuscript_total_words,
        total_story_markdown_words=total_story_markdown_words,
        supporting_markdown_words=supporting_words,
        average_chapter_words=(
            manuscript_total_words // len(chapter_stats) if chapter_stats else 0
        ),
        estimated_reading_minutes=_reading_minutes(manuscript_total_words),
        chapter_count=len(chapter_stats),
        drafted_chapters=sum(1 for chapter in chapter_stats if chapter.words > 0),
        chapter_stats=chapter_stats,
        category_stats=supporting_categories,
        notes=notes,
    )

    report_path.write_text(
        _render_statistics_report(story_dir, result),
        encoding="utf-8",
    )
    return result
