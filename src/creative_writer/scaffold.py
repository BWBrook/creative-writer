"""Story scaffolding logic."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory, write_text

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TEMPLATE_TOKEN_PATTERN = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")
STYLE_CARD_KEY_PATTERN = re.compile(r"[^a-z0-9]+")


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


def style_cards_dir(root: Path) -> Path:
    """Return the style-card template directory."""

    template_dir = root / "templates" / "style-cards"
    if template_dir.exists():
        return template_dir

    packaged_template_dir = (
        Path(__file__).resolve().parents[2] / "templates" / "style-cards"
    )
    if packaged_template_dir.exists():
        return packaged_template_dir

    raise CreativeWriterError(
        "Style-card template directory is missing. Looked in "
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


def _normalize_style_card_key(value: str) -> str:
    return STYLE_CARD_KEY_PATTERN.sub("_", value.strip().lower()).strip("_")


def available_style_cards(root: Path) -> dict[str, Path]:
    """Return built-in style cards keyed by a normalized identifier."""

    try:
        cards_dir = style_cards_dir(root)
    except CreativeWriterError:
        return {}
    cards: dict[str, Path] = {}
    for path in sorted(cards_dir.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        cards[_normalize_style_card_key(path.stem)] = path
    return cards


def _resolve_style_card(
    root: Path,
    style_card: str | None,
) -> tuple[Path | None, str | None]:
    if not style_card:
        return None, None

    cards = available_style_cards(root)
    normalized = _normalize_style_card_key(style_card)
    if normalized in cards:
        return cards[normalized], cards[normalized].stem

    style_card_path = Path(style_card).expanduser()
    if not style_card_path.is_absolute():
        style_card_path = (root / style_card_path).resolve()

    if not style_card_path.exists():
        available = ", ".join(sorted(cards))
        raise CreativeWriterError(
            f"Unknown style card '{style_card}'. "
            f"Use one of: {available} or provide a path to a Markdown file."
        )
    if style_card_path.suffix.lower() != ".md":
        raise CreativeWriterError("Style card files must be Markdown (.md).")

    return style_card_path, f"custom/{_normalize_style_card_key(style_card_path.stem)}"


def list_style_cards(root: Path) -> list[tuple[str, str]]:
    """Return built-in style-card identifiers with display titles."""

    cards: list[tuple[str, str]] = []
    for key, path in available_style_cards(root).items():
        first_line = path.read_text(encoding="utf-8").splitlines()[0].strip()
        if first_line.startswith("# Style Card: "):
            title = first_line.removeprefix("# Style Card: ").strip()
        else:
            title = path.stem.replace("_", " ").title()
        cards.append((key, title))
    return cards


def _write_style_card(
    story_dir: Path,
    story_title: str,
    style_card_path: Path | None,
) -> None:
    destination = story_dir / "style-card.md"
    if style_card_path is None:
        return

    content = style_card_path.read_text(encoding="utf-8").rstrip() + "\n"
    note = (
        f"\n<!-- Imported into {story_title} from "
        f"{style_card_path.name}. Adapt in style-guide.md as needed. -->\n"
    )
    destination.write_text(content + note, encoding="utf-8")


def _annotate_story_config(story_dir: Path, style_card_key: str | None) -> None:
    if style_card_key is None:
        return

    story_path = story_dir / "story.yml"
    raw = yaml.safe_load(story_path.read_text(encoding="utf-8")) or {}
    raw["style_card"] = style_card_key
    story_path.write_text(
        yaml.safe_dump(raw, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )


def create_story(
    root: Path,
    slug: str,
    kind: str,
    title: str | None = None,
    style_card: str | None = None,
) -> Path:
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

    style_card_path, style_card_key = _resolve_style_card(root, style_card)
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

    _write_style_card(story_dir, story_title, style_card_path)
    _annotate_story_config(story_dir, style_card_key)

    return story_dir
