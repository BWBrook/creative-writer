"""AI-writing surface audit integration."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from creative_writer.checks import check_story
from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory

AI_AUDIT_SCRIPT_ENV = "CREATIVE_WRITER_AI_AUDIT_SCRIPT"
DEFAULT_AI_AUDIT_SCRIPT = (
    Path.home() / ".codex" / "skills" / "audit-ai-writing" / "scripts" / "audit_ai_writing.py"
)


@dataclass(slots=True)
class AIWritingAuditResult:
    """Rendered AI-writing audit report for one story."""

    story_slug: str
    story_title: str
    report_path: Path
    generated_at: datetime
    chapter_count: int
    script_path: Path


class AIWritingHit(BaseModel):
    """One location-aware hit from the external surface scanner."""

    model_config = ConfigDict(extra="allow")

    group: str
    severity: int
    line: int = Field(ge=1)
    match: str
    context: str


class AIWritingGroup(BaseModel):
    """One scanner group, retaining its original identity and advice."""

    model_config = ConfigDict(extra="allow")

    count: int = Field(ge=0)
    severity: int = Field(ge=0)
    advice: str
    hits: list[AIWritingHit] = Field(default_factory=list)


class _AIWritingPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    groups: dict[str, AIWritingGroup]
    caution: str


@dataclass(slots=True)
class AIWritingJSONResult:
    """Structured scanner result for the separately labelled style report."""

    status: Literal["complete", "unavailable"]
    script_path: Path | None
    groups: dict[str, AIWritingGroup]
    caution: str
    notice: str | None


def _configured_script_path() -> Path:
    configured = os.environ.get(AI_AUDIT_SCRIPT_ENV)
    return (
        Path(configured).expanduser()
        if configured
        else DEFAULT_AI_AUDIT_SCRIPT
    )


def _resolve_script_path() -> Path:
    script_path = _configured_script_path()
    if not script_path.exists():
        raise CreativeWriterError(
            "AI-writing audit script not found. Set "
            f"{AI_AUDIT_SCRIPT_ENV} or install the audit-ai-writing skill. "
            f"Looked for: {script_path}"
        )
    return script_path


def scan_ai_writing_json(
    path: Path,
    genre: str = "narrative",
    *,
    unavailable_is_error: bool = True,
) -> AIWritingJSONResult:
    """Run the scanner's structured mode without importing aggregate risk."""

    try:
        script_path = _resolve_script_path()
    except CreativeWriterError:
        if unavailable_is_error:
            raise
        missing_path = _configured_script_path()
        return AIWritingJSONResult(
            status="unavailable",
            script_path=None,
            groups={},
            caution="The optional generic surface scan did not run.",
            notice=f"Generic AI-writing scanner unavailable: {missing_path}",
        )

    command = [
        sys.executable,
        str(script_path),
        "--genre",
        genre,
        "--json",
        str(path),
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or exc.stdout.strip() or "unknown audit error"
        raise CreativeWriterError(
            f"AI-writing JSON scan failed for {path}: {stderr}"
        ) from exc
    except OSError as exc:
        raise CreativeWriterError(
            f"Unable to execute AI-writing JSON scan for {path}: {exc}"
        ) from exc

    try:
        payload = _AIWritingPayload.model_validate_json(completed.stdout)
    except ValidationError as exc:
        raise CreativeWriterError(
            f"AI-writing JSON scan returned malformed JSON for {path}: {exc}"
        ) from exc

    return AIWritingJSONResult(
        status="complete",
        script_path=script_path,
        groups=payload.groups,
        caution=payload.caution,
        notice=None,
    )


def generate_ai_writing_audit(
    root: Path,
    slug: str,
    genre: str = "narrative",
) -> AIWritingAuditResult:
    """Run the audit-ai-writing scanner over a story manuscript."""

    script_path = _resolve_script_path()
    result = check_story(root, slug)
    if not result.ok or not result.story:
        raise CreativeWriterError(
            f"Cannot audit {slug}. Fix blocking issues first. See {result.report_path}."
        )

    report_dir = root / "build" / slug / "reports"
    ensure_directory(report_dir)
    report_path = report_dir / "ai-writing-audit.md"
    generated_at = datetime.now(timezone.utc)

    lines = [
        f"# AI Writing Audit: {result.story.title}",
        "",
        f"- Story slug: `{slug}`",
        f"- Generated (UTC): `{generated_at.isoformat()}`",
        f"- Genre: `{genre}`",
        f"- Scanner: `{script_path}`",
        f"- Chapters scanned: {len(result.chapters)}",
        "",
        "This report is a triage aid, not an authorship detector. Use it to guide",
        "manual revision against `audit-ai-writing`, especially for stock cadence,",
        "over-neat rhetorical turns, and abstract narrative closure.",
        "",
    ]

    for chapter in result.chapters:
        relative_path = chapter.manuscript_path.relative_to(root / "stories" / slug)
        command = [
            sys.executable,
            str(script_path),
            "--genre",
            genre,
            str(chapter.manuscript_path),
        ]
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() or exc.stdout.strip() or "unknown audit error"
            raise CreativeWriterError(
                f"AI-writing audit failed for {relative_path}: {stderr}"
            ) from exc

        lines.extend(
            [
                f"## {chapter.front_matter.title}",
                "",
                f"- Source: `{relative_path.as_posix()}`",
                "",
                "```text",
                completed.stdout.strip(),
                "```",
                "",
            ]
        )

    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return AIWritingAuditResult(
        story_slug=slug,
        story_title=result.story.title,
        report_path=report_path,
        generated_at=generated_at,
        chapter_count=len(result.chapters),
        script_path=script_path,
    )
