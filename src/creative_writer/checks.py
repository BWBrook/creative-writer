"""Coherence and style checks for story projects."""

from __future__ import annotations

import re
from pathlib import Path

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory, load_chapter_document, load_yaml_model
from creative_writer.models import (
    CharactersRegistry,
    CheckMessage,
    CheckResult,
    CluesRegistry,
    ContractConfig,
    LocationsRegistry,
    StoryConfig,
    TimelineRegistry,
)

MANDATORY_ARTIFACTS = [
    "story.yml",
    "contract.yml",
    "style-guide.md",
    "outline.md",
    "manuscript",
]

CONTRASTIVE_PATTERN = re.compile(
    r"\b(?:not only\b[^.!?\n]{0,80}\bbut also|not\b[^.!?\n]{0,80}\bbut)\b",
    re.IGNORECASE,
)


def _add_error(result: CheckResult, location: Path | str, message: str) -> None:
    result.errors.append(CheckMessage("error", str(location), message))


def _add_warning(result: CheckResult, location: Path | str, message: str) -> None:
    result.warnings.append(CheckMessage("warning", str(location), message))


def _render_report(
    result: CheckResult,
    story_dir: Path,
    registry_counts: dict[str, int],
) -> str:
    status = "PASS"
    if result.errors:
        status = "FAIL"
    elif result.warnings:
        status = "WARN"

    lines = [
        f"# Coherence Report: {result.story_title or result.story_slug}",
        "",
        f"- Story slug: `{result.story_slug}`",
        f"- Status: **{status}**",
        f"- Blocking issues: {len(result.errors)}",
        f"- Warnings: {len(result.warnings)}",
        f"- Story path: `{story_dir}`",
        "",
        "## Mandatory artifacts",
        "",
    ]
    for artifact in MANDATORY_ARTIFACTS:
        target = story_dir / artifact
        lines.append(
            f"- `{artifact}`: {'present' if target.exists() else 'missing'}"
        )

    lines.extend(
        [
            "",
            "## Registries",
            "",
            f"- Characters tracked: {registry_counts['characters']}",
            f"- Clues tracked: {registry_counts['clues']}",
            f"- Locations tracked: {registry_counts['locations']}",
            f"- Timeline events tracked: {registry_counts['timeline']}",
            "",
            "## Chapters",
            "",
        ]
    )
    if result.chapters:
        for chapter in result.chapters:
            fm = chapter.front_matter
            lines.append(
                f"- `{chapter.path.name}`: {fm.title} | characters={len(fm.characters)} | "
                f"locations={len(fm.locations)} | clues introduced={len(fm.clues_introduced)} | "
                f"clues resolved={len(fm.clues_resolved)}"
            )
    else:
        lines.append("- No chapters were successfully parsed.")

    lines.extend(["", "## Blocking issues", ""])
    if result.errors:
        for item in result.errors:
            lines.append(f"- `{item.location}`: {item.message}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Warnings", ""])
    if result.warnings:
        for item in result.warnings:
            lines.append(f"- `{item.location}`: {item.message}")
    else:
        lines.append("- None.")

    return "\n".join(lines) + "\n"


def _load_registry_ids(
    story_dir: Path,
    filename: str,
    key: str,
    model_type: type,
    result: CheckResult,
) -> set[str]:
    path = story_dir / filename
    if not path.exists():
        return set()

    try:
        registry = load_yaml_model(path, model_type)
    except CreativeWriterError as exc:
        _add_error(result, path, str(exc))
        return set()

    return {item.id for item in getattr(registry, key)}


def check_story(root: Path, slug: str) -> CheckResult:
    """Run validation and style checks for one story."""

    story_dir = root / "stories" / slug
    result = CheckResult(story_slug=slug)
    report_dir = root / "build" / slug / "reports"
    ensure_directory(report_dir)
    result.report_path = report_dir / "coherence-report.md"

    if not story_dir.exists():
        _add_error(result, story_dir, "Story directory does not exist.")
        result.report_path.write_text(
            _render_report(
                result,
                story_dir,
                {"characters": 0, "clues": 0, "locations": 0, "timeline": 0},
            ),
            encoding="utf-8",
        )
        return result

    for artifact in MANDATORY_ARTIFACTS:
        target = story_dir / artifact
        if not target.exists():
            _add_error(result, target, "Missing mandatory artifact.")

    story_path = story_dir / "story.yml"
    contract_path = story_dir / "contract.yml"

    if story_path.exists():
        try:
            result.story = load_yaml_model(story_path, StoryConfig)
            result.story_title = result.story.title
        except CreativeWriterError as exc:
            _add_error(result, story_path, str(exc))

    if contract_path.exists():
        try:
            result.contract = load_yaml_model(contract_path, ContractConfig)
        except CreativeWriterError as exc:
            _add_error(result, contract_path, str(exc))

    registry_ids = {
        "characters": _load_registry_ids(
            story_dir, "characters.yml", "characters", CharactersRegistry, result
        ),
        "clues": _load_registry_ids(
            story_dir, "clues.yml", "clues", CluesRegistry, result
        ),
        "locations": _load_registry_ids(
            story_dir, "locations.yml", "locations", LocationsRegistry, result
        ),
        "timeline": _load_registry_ids(
            story_dir, "timeline.yml", "events", TimelineRegistry, result
        ),
    }

    if result.story:
        for chapter_name in result.story.chapters:
            chapter_path = story_dir / chapter_name
            if not chapter_path.exists():
                _add_error(result, chapter_path, "Listed chapter file does not exist.")
                continue

            try:
                chapter = load_chapter_document(chapter_path)
            except CreativeWriterError as exc:
                _add_error(result, chapter_path, str(exc))
                continue

            result.chapters.append(chapter)

            if registry_ids["characters"]:
                unknown = sorted(
                    set(chapter.front_matter.characters) - registry_ids["characters"]
                )
                if unknown:
                    _add_error(
                        result,
                        chapter_path,
                        f"Unknown characters referenced: {', '.join(unknown)}",
                    )

            if registry_ids["locations"]:
                unknown = sorted(
                    set(chapter.front_matter.locations) - registry_ids["locations"]
                )
                if unknown:
                    _add_error(
                        result,
                        chapter_path,
                        f"Unknown locations referenced: {', '.join(unknown)}",
                    )

            if registry_ids["clues"]:
                clue_refs = set(chapter.front_matter.clues_introduced).union(
                    chapter.front_matter.clues_resolved
                )
                unknown = sorted(clue_refs - registry_ids["clues"])
                if unknown:
                    _add_error(
                        result,
                        chapter_path,
                        f"Unknown clues referenced: {', '.join(unknown)}",
                    )

            if registry_ids["timeline"]:
                unknown = sorted(
                    set(chapter.front_matter.timeline_events) - registry_ids["timeline"]
                )
                if unknown:
                    _add_error(
                        result,
                        chapter_path,
                        f"Unknown timeline events referenced: {', '.join(unknown)}",
                    )

            if result.contract:
                em_dash_count = chapter.body.count("—")
                em_dash_lint = result.contract.lint.em_dash
                if em_dash_lint.enabled and em_dash_count > em_dash_lint.max_per_chapter:
                    _add_warning(
                        result,
                        chapter_path,
                        f"Em dash count {em_dash_count} exceeds configured limit "
                        f"{em_dash_lint.max_per_chapter}.",
                    )

                contrastive_lint = result.contract.lint.contrastive_parallelism
                contrastive_hits = len(CONTRASTIVE_PATTERN.findall(chapter.body))
                if (
                    contrastive_lint.enabled
                    and contrastive_hits
                    > contrastive_lint.max_instances_per_chapter
                ):
                    _add_warning(
                        result,
                        chapter_path,
                        f"Contrastive parallelism count {contrastive_hits} exceeds "
                        f"configured limit "
                        f"{contrastive_lint.max_instances_per_chapter}.",
                    )

    report_body = _render_report(
        result,
        story_dir,
        {
            "characters": len(registry_ids["characters"]),
            "clues": len(registry_ids["clues"]),
            "locations": len(registry_ids["locations"]),
            "timeline": len(registry_ids["timeline"]),
        },
    )
    result.report_path.write_text(report_body, encoding="utf-8")
    return result
