"""AI-writing surface audit integration."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    ValidationError,
    field_validator,
    model_validator,
)

from creative_writer.checks import check_story
from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory

AI_AUDIT_SCRIPT_ENV = "CREATIVE_WRITER_AI_AUDIT_SCRIPT"
DEFAULT_AI_AUDIT_SCRIPT = (
    Path.home() / ".codex" / "skills" / "audit-ai-writing" / "scripts" / "audit_ai_writing.py"
)
_FORBIDDEN_EDITORIAL_CLAIM = re.compile(
    r"\b(?:"
    r"scores?|scoring|scorecards?|"
    r"authorship|authenticity|authored|"
    r"rewrites?|rewriting|rewritten"
    r")\b",
    re.IGNORECASE,
)
_MARKDOWN_STRUCTURE = re.compile(
    r"(?:^|\s)(?:#{1,6}\s|[-+*]\s|>\s|\d+\.\s)|[`<>\[\]]|\*\*|__"
)


def _safe_external_text(value: str, label: str) -> str:
    if not value or value != value.strip():
        raise ValueError(f"{label} must be non-empty without surrounding space")
    if "\n" in value or "\r" in value or not all(
        character.isprintable() for character in value
    ):
        raise ValueError(f"{label} must be single-line printable text")
    return value


def _safe_external_editorial_text(value: str, label: str) -> str:
    value = _safe_external_text(value, label)
    if _FORBIDDEN_EDITORIAL_CLAIM.search(value):
        raise ValueError(f"{label} contains a prohibited editorial claim")
    if _MARKDOWN_STRUCTURE.search(value):
        raise ValueError(f"{label} contains Markdown structure")
    return value


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

    model_config = ConfigDict(extra="allow", strict=True)

    group: StrictStr
    severity: StrictInt = Field(ge=0)
    line: StrictInt = Field(ge=1)
    match: StrictStr
    context: StrictStr

    @field_validator("group", "match", "context")
    @classmethod
    def safe_text(cls, value: str, info) -> str:
        return _safe_external_text(value, f"scanner hit {info.field_name}")


class AIWritingGroup(BaseModel):
    """One scanner group, retaining its original identity and advice."""

    model_config = ConfigDict(extra="allow", strict=True)

    count: StrictInt = Field(ge=0)
    severity: StrictInt = Field(ge=0)
    advice: StrictStr
    hits: list[AIWritingHit] = Field(default_factory=list)

    @field_validator("advice")
    @classmethod
    def safe_advice(cls, value: str) -> str:
        return _safe_external_editorial_text(value, "scanner group advice")


class _AIWritingPayload(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    groups: dict[str, AIWritingGroup]
    caution: StrictStr

    @field_validator("caution")
    @classmethod
    def safe_caution(cls, value: str) -> str:
        return _safe_external_text(value, "scanner caution")

    @model_validator(mode="after")
    def validate_group_contract(self) -> "_AIWritingPayload":
        for group_name, group in self.groups.items():
            _safe_external_editorial_text(group_name, "scanner group name")
            if group.count != len(group.hits):
                raise ValueError(
                    f"scanner group {group_name!r} count does not match hits"
                )
            if any(hit.group != group_name for hit in group.hits):
                raise ValueError(
                    f"scanner group {group_name!r} contains a mismatched hit group"
                )
        return self


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


def _decode_scanner_output(
    output: bytes | str | None,
    *,
    path: Path,
    stream: str,
) -> str:
    if output is None:
        return ""
    if isinstance(output, str):
        return output
    try:
        return output.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CreativeWriterError(
            f"AI-writing JSON scan returned invalid UTF-8 on {stream} for {path}"
        ) from exc


def _reject_nonstandard_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant {value}")


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

    try:
        manuscript_text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise CreativeWriterError(
            f"Scanned manuscript is not valid UTF-8: {path}"
        ) from exc
    except OSError as exc:
        raise CreativeWriterError(
            f"Unable to read scanned manuscript {path}: {exc}"
        ) from exc

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
            text=False,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (
            _decode_scanner_output(
                exc.stderr,
                path=path,
                stream="stderr",
            ).strip()
            or _decode_scanner_output(
                exc.stdout,
                path=path,
                stream="stdout",
            ).strip()
            or "unknown audit error"
        )
        raise CreativeWriterError(
            f"AI-writing JSON scan failed for {path}: {stderr}"
        ) from exc
    except OSError as exc:
        raise CreativeWriterError(
            f"Unable to execute AI-writing JSON scan for {path}: {exc}"
        ) from exc

    stdout = _decode_scanner_output(
        completed.stdout,
        path=path,
        stream="stdout",
    )
    try:
        decoded = json.loads(
            stdout,
            parse_constant=_reject_nonstandard_json_constant,
        )
        payload = _AIWritingPayload.model_validate(decoded)
        line_count = len(manuscript_text.splitlines())
        for group in payload.groups.values():
            for hit in group.hits:
                if hit.line > line_count:
                    raise ValueError(
                        f"scanner hit line {hit.line} exceeds {line_count} lines"
                    )
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
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
