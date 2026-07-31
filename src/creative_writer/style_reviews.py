"""Tracked authenticity-review discovery and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import split_front_matter
from creative_writer.models import ReviewPackEntry
from creative_writer.style_models import StyleReviewFrontMatter
from creative_writer.style_profiles import StyleContext

IGNORED_STYLE_REVIEW_FILES = frozenset({"README.md", "_template.md"})


@dataclass(slots=True)
class StyleReviewDocument:
    path: Path
    front_matter: StyleReviewFrontMatter
    body: str


def style_review_paths(story_dir: Path) -> list[Path]:
    """Return real tracked style reviews in deterministic lexical order."""

    directory = story_dir / "style-reviews"
    if not directory.is_dir():
        return []
    return [
        path
        for path in sorted(directory.glob("*.md"))
        if path.name not in IGNORED_STYLE_REVIEW_FILES and path.is_file()
    ]


def load_style_review(path: Path) -> StyleReviewDocument:
    """Load one strict style review with a substantive Markdown body."""

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CreativeWriterError(
            f"Unable to read style review {path}: {exc}"
        ) from exc

    raw_front_matter, body = split_front_matter(text, path)
    try:
        front_matter = StyleReviewFrontMatter.model_validate(raw_front_matter)
    except ValidationError as exc:
        raise CreativeWriterError(
            f"Style review front matter validation failed for {path}:\n{exc}"
        ) from exc
    if not body.strip():
        raise CreativeWriterError(
            f"{path} must contain a non-empty Markdown body."
        )
    return StyleReviewDocument(
        path=path,
        front_matter=front_matter,
        body=body,
    )


def validate_style_reviews(
    story_dir: Path,
    context: StyleContext,
    manuscript_paths: set[str],
) -> list[str]:
    """Return path-preserving errors for invalid tracked style reviews."""

    errors: list[str] = []
    known_packets = set(context.packets)
    for path in style_review_paths(story_dir):
        try:
            document = load_style_review(path)
        except CreativeWriterError as exc:
            errors.append(f"{path}: {exc}")
            continue

        review = document.front_matter
        if review.profile_id != context.profile.profile_id:
            errors.append(
                f"{path}: profile ID `{review.profile_id}` does not match "
                f"active profile `{context.profile.profile_id}`"
            )
        if review.profile_version != context.profile.version:
            errors.append(
                f"{path}: profile version `{review.profile_version}` does not "
                f"match active profile version `{context.profile.version}`"
            )
        for packet_id in review.reference_packets:
            if packet_id not in known_packets:
                errors.append(
                    f"{path}: unknown style packet `{packet_id}`"
                )
        for manuscript in review.manuscripts:
            if manuscript not in manuscript_paths:
                errors.append(
                    f"{path}: unknown manuscript `{manuscript}`"
                )
    return errors


def validate_review_pack_style_context(
    entry: ReviewPackEntry,
    context: StyleContext,
    manuscript_paths: set[str],
) -> list[str]:
    """Cross-check optional calibration metadata against the active profile."""

    style = entry.style
    if style is None:
        return []

    prefix = f"Review-pack entry `{entry.id}`"
    errors: list[str] = []
    if style.profile_id != context.profile.profile_id:
        errors.append(
            f"{prefix} profile ID `{style.profile_id}` does not match active "
            f"profile `{context.profile.profile_id}`"
        )
    if style.profile_version != context.profile.version:
        errors.append(
            f"{prefix} profile version `{style.profile_version}` does not "
            f"match active profile version `{context.profile.version}`"
        )

    known_roles = {role.id for role in context.profile.roles}
    if style.narrative_role not in known_roles:
        errors.append(
            f"{prefix} uses unknown style role `{style.narrative_role}`"
        )

    known_claims = {
        claim_id
        for rule in context.profile.rules
        for claim_id in rule.claim_ids
    }
    for claim_id in style.claim_ids:
        if claim_id not in known_claims:
            errors.append(
                f"{prefix} uses unknown Phase 2B claim `{claim_id}`"
            )

    if entry.manuscript not in manuscript_paths:
        errors.append(
            f"{prefix} uses unknown configured manuscript "
            f"`{entry.manuscript}`"
        )
    return errors
