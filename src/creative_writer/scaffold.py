"""Story scaffolding logic."""

from __future__ import annotations

import re
from pathlib import Path

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory, write_text

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TEMPLATE_TOKEN_PATTERN = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")


def slug_to_title(slug: str) -> str:
    """Convert a slug into a simple title."""

    words = [piece for piece in slug.replace("_", "-").split("-") if piece]
    if not words:
        raise CreativeWriterError("Story slug must contain at least one word.")
    return " ".join(word.capitalize() for word in words)


def story_template_dir(root: Path) -> Path:
    """Return the canonical story template directory."""

    template_dir = root / "templates" / "story"
    if template_dir.exists():
        return template_dir

    packaged_template_dir = Path(__file__).resolve().parents[2] / "templates" / "story"
    if packaged_template_dir.exists():
        return packaged_template_dir

    raise CreativeWriterError(
        "Story template directory is missing. Looked in "
        f"{template_dir} and {packaged_template_dir}."
    )


def render_template_text(template_text: str, context: dict[str, str]) -> str:
    """Render `{{ token }}` placeholders in a template string."""

    def replace_token(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            raise CreativeWriterError(f"Unknown template token: {key}")
        return context[key]

    return TEMPLATE_TOKEN_PATTERN.sub(replace_token, template_text)


def create_story(root: Path, slug: str, kind: str, title: str | None = None) -> Path:
    """Create a new story directory from the canonical template."""

    if kind not in {"original", "pastiche"}:
        raise CreativeWriterError("KIND must be either 'original' or 'pastiche'.")
    if not SLUG_PATTERN.fullmatch(slug):
        raise CreativeWriterError(
            "Story slug must use lowercase letters, numbers, and single hyphens."
        )

    story_title = title or slug_to_title(slug)
    story_dir = root / "stories" / slug
    if story_dir.exists():
        raise CreativeWriterError(f"Story already exists: {story_dir}")

    context = {
        "story_slug": slug,
        "story_title": story_title,
        "story_kind": kind,
    }

    template_dir = story_template_dir(root)
    ensure_directory(story_dir)

    for template_path in sorted(template_dir.rglob("*")):
        relative_path = template_path.relative_to(template_dir)
        destination_path = story_dir / relative_path

        if template_path.is_dir():
            ensure_directory(destination_path)
            continue

        rendered = render_template_text(
            template_path.read_text(encoding="utf-8"),
            context,
        )
        write_text(destination_path, rendered)

    return story_dir
