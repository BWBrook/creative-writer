"""Pandoc-backed story assembly and rendering."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from creative_writer.checks import check_story
from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory


def _assemble_markdown(root: Path, slug: str) -> tuple[Path, str, str, set[str]]:
    result = check_story(root, slug)
    if not result.ok or not result.story:
        raise CreativeWriterError(
            f"Cannot build {slug}. Fix blocking issues first. "
            f"See {result.report_path}."
        )

    build_dir = root / "build" / slug
    ensure_directory(build_dir)
    assembled_path = build_dir / f"{slug}.assembled.md"

    lines = [
        "---",
        f'title: "{result.story.title}"',
        f'lang: "{result.story.language}"',
        "---",
        "",
    ]

    for chapter in result.chapters:
        lines.append(f"# {chapter.front_matter.title}")
        lines.append("")
        body = chapter.manuscript_body.strip()
        if body:
            lines.append(body)
        else:
            lines.append("_No chapter body yet._")
        lines.append("")

    assembled_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return (
        assembled_path,
        result.story.title,
        result.story.language,
        set(result.story.target_outputs),
    )


def build_story(root: Path, slug: str, target: str) -> Path:
    """Build a story to EPUB or PDF with Pandoc."""

    if target not in {"epub", "pdf"}:
        raise CreativeWriterError("Build target must be 'epub' or 'pdf'.")

    assembled_path, title, language, target_outputs = _assemble_markdown(root, slug)
    if target not in target_outputs:
        raise CreativeWriterError(
            f"{slug} does not declare '{target}' in story.yml target_outputs."
        )
    output_path = root / "build" / slug / f"{slug}.{target}"

    command = [
        "pandoc",
        str(assembled_path),
        "--standalone",
        "--toc",
        "--metadata",
        f"title={title}",
        "--metadata",
        f"lang={language}",
        "--resource-path",
        os.pathsep.join(
            [
                str(root / "stories" / slug),
                str(root / "stories" / slug / "manuscript"),
                str(root),
            ]
        ),
        "--output",
        str(output_path),
    ]
    if target == "pdf":
        command.extend(["--pdf-engine=xelatex"])

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise CreativeWriterError("Pandoc is not installed or not on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or exc.stdout.strip() or "unknown Pandoc error"
        raise CreativeWriterError(f"Pandoc failed while building {slug}: {stderr}") from exc

    return output_path
