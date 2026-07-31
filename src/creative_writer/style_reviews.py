"""Tracked authenticity-review discovery and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import split_front_matter
from creative_writer.models import ReviewPackEntry
from creative_writer.source_analysis_common import validate_relative_path
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
    if directory.is_symlink():
        raise CreativeWriterError(
            f"{directory}: style-reviews directory must not be a symlink"
        )
    if not directory.is_dir():
        return []

    paths: list[Path] = []
    for path in sorted(directory.glob("*.md")):
        if path.name in IGNORED_STYLE_REVIEW_FILES:
            continue
        if path.is_symlink():
            raise CreativeWriterError(
                f"{path}: style review file must not be a symlink"
            )
        if path.is_file():
            paths.append(path)
    return paths


def load_style_review(path: Path) -> StyleReviewDocument:
    """Load one strict style review with a substantive Markdown body."""

    if path.parent.is_symlink():
        raise CreativeWriterError(
            f"{path.parent}: style-reviews directory must not be a symlink"
        )
    if path.is_symlink():
        raise CreativeWriterError(
            f"{path}: style review file must not be a symlink"
        )
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


def _configured_manuscript_errors(
    story_dir: Path,
    manuscript_paths: set[str],
) -> list[str]:
    errors: list[str] = []
    try:
        real_story_dir = story_dir.resolve(strict=True)
    except OSError as exc:
        return [f"{story_dir}: unable to resolve story directory: {exc}"]

    manuscript_dir = real_story_dir / "manuscript"
    try:
        real_manuscript_dir = manuscript_dir.resolve(strict=True)
    except OSError as exc:
        return [
            f"{manuscript_dir}: unable to resolve story manuscript "
            f"directory: {exc}"
        ]
    if real_manuscript_dir != manuscript_dir:
        return [
            f"{manuscript_dir}: story manuscript directory must not be a "
            "symlink"
        ]

    for relative in sorted(manuscript_paths):
        manuscript = real_story_dir / relative
        try:
            validate_relative_path(relative)
        except CreativeWriterError as exc:
            errors.append(
                f"{manuscript}: configured manuscript path is not canonical: "
                f"{exc}"
            )
            continue
        if not relative.startswith("manuscript/") or not relative.endswith(".md"):
            errors.append(
                f"{manuscript}: configured manuscript must be below "
                "manuscript/ and end in .md"
            )
            continue
        try:
            resolved = manuscript.resolve(strict=True)
        except OSError as exc:
            errors.append(
                f"{manuscript}: unable to resolve configured manuscript: {exc}"
            )
            continue
        try:
            resolved.relative_to(real_manuscript_dir)
        except ValueError:
            errors.append(
                f"{manuscript}: configured manuscript resolves outside the "
                f"story manuscript directory: {resolved}"
            )
            continue
        if not resolved.is_file():
            errors.append(
                f"{manuscript}: configured manuscript is not a regular file"
            )
    return errors


def validate_style_reviews(
    story_dir: Path,
    context: StyleContext,
    manuscript_paths: set[str],
) -> list[str]:
    """Return path-preserving errors for invalid tracked style reviews."""

    errors = _configured_manuscript_errors(story_dir, manuscript_paths)
    known_packets = set(context.packets)
    try:
        paths = style_review_paths(story_dir)
    except CreativeWriterError as exc:
        errors.append(str(exc))
        return errors

    review_ids: dict[str, Path] = {}
    for path in paths:
        try:
            document = load_style_review(path)
        except CreativeWriterError as exc:
            errors.append(f"{path}: {exc}")
            continue

        review = document.front_matter
        first_path = review_ids.get(review.review_id)
        if first_path is None:
            review_ids[review.review_id] = path
        else:
            errors.append(
                f"{path}: duplicate review_id `{review.review_id}`; "
                f"first declared in {first_path}"
            )
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
