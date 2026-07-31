from __future__ import annotations

import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
import yaml

from creative_writer.exceptions import CreativeWriterError
from creative_writer.style_profiles import StyleContext
from creative_writer.style_reviews import (
    load_style_review,
    style_review_paths,
    validate_style_reviews,
)

SHA256 = "a" * 64


def valid_style_review_payload() -> dict[str, Any]:
    return {
        "review_id": "chapter-one-first-pass",
        "date": datetime.date(2026, 7, 31),
        "scope": "chapter",
        "manuscripts": ["manuscript/01-opening.md"],
        "profile_id": "wells-1895-1899",
        "profile_version": "1.0.0",
        "lint_report": {
            "path": (
                "build/time-expedition/style/chapters/"
                "01-opening-lint-report.json"
            ),
            "sha256": SHA256,
        },
        "reference_packets": ["traveller-account"],
        "reviewer_id": "codex",
        "reviewer_role": "ai",
        "outcome": "qualified",
    }


def _write_review(
    path: Path,
    payload: dict[str, Any] | None = None,
    *,
    body: str = "# Authenticity decision\n\nRetain the reported uncertainty.\n",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    front_matter = yaml.safe_dump(
        payload or valid_style_review_payload(),
        sort_keys=False,
        allow_unicode=True,
    )
    path.write_text(f"---\n{front_matter}---\n\n{body}", encoding="utf-8")


def _style_context() -> StyleContext:
    profile = SimpleNamespace(
        profile_id="wells-1895-1899",
        version="1.0.0",
    )
    return cast(
        StyleContext,
        SimpleNamespace(
            profile=profile,
            packets={"traveller-account": object()},
        ),
    )


def test_style_review_paths_are_lexical_and_ignore_guidance_files(
    tmp_path: Path,
) -> None:
    review_dir = tmp_path / "style-reviews"
    _write_review(review_dir / "z-last.md")
    _write_review(review_dir / "a-first.md")
    (review_dir / "README.md").write_text("Guidance only.\n", encoding="utf-8")
    (review_dir / "_template.md").write_text(
        "Template only.\n",
        encoding="utf-8",
    )
    (review_dir / "ignored.yml").write_text("not: markdown\n", encoding="utf-8")

    assert [path.name for path in style_review_paths(tmp_path)] == [
        "a-first.md",
        "z-last.md",
    ]


def test_load_style_review_preserves_valid_front_matter_and_body(
    tmp_path: Path,
) -> None:
    path = tmp_path / "style-reviews" / "chapter-one.md"
    _write_review(path)

    review = load_style_review(path)

    assert review.path == path
    assert review.front_matter.review_id == "chapter-one-first-pass"
    assert review.front_matter.reviewer_role == "ai"
    assert review.body == (
        "# Authenticity decision\n\nRetain the reported uncertainty.\n"
    )


def test_load_style_review_rejects_empty_markdown_body(tmp_path: Path) -> None:
    path = tmp_path / "style-reviews" / "empty.md"
    _write_review(path, body=" \n\t\n")

    with pytest.raises(CreativeWriterError, match="Markdown body"):
        load_style_review(path)


def test_validate_style_reviews_accepts_missing_fingerprinted_lint_report(
    tmp_path: Path,
) -> None:
    path = tmp_path / "style-reviews" / "chapter-one.md"
    _write_review(path)

    errors = validate_style_reviews(
        tmp_path,
        _style_context(),
        {"manuscript/01-opening.md"},
    )

    assert errors == []
    assert not (
        tmp_path
        / "build/time-expedition/style/chapters/01-opening-lint-report.json"
    ).exists()


def test_validate_style_reviews_accepts_human_story_review(
    tmp_path: Path,
) -> None:
    payload = valid_style_review_payload()
    payload.update(
        scope="story",
        reviewer_id="barry",
        reviewer_role="human",
        outcome="accepted",
    )
    _write_review(tmp_path / "style-reviews" / "story-review.md", payload)

    errors = validate_style_reviews(
        tmp_path,
        _style_context(),
        {"manuscript/01-opening.md"},
    )

    assert errors == []


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ({"profile_id": "unknown-profile"}, "profile ID"),
        ({"profile_version": "2.0.0"}, "profile version"),
        ({"reference_packets": ["unknown-packet"]}, "unknown style packet"),
        ({"manuscripts": ["manuscript/02-missing.md"]}, "unknown manuscript"),
    ],
)
def test_validate_style_reviews_rejects_unknown_context_references(
    tmp_path: Path,
    mutation: dict[str, Any],
    expected: str,
) -> None:
    payload = valid_style_review_payload()
    payload.update(mutation)
    path = tmp_path / "style-reviews" / "invalid-reference.md"
    _write_review(path, payload)

    errors = validate_style_reviews(
        tmp_path,
        _style_context(),
        {"manuscript/01-opening.md"},
    )

    assert len(errors) == 1
    assert str(path) in errors[0]
    assert expected in errors[0]


def test_validate_style_reviews_reports_invalid_review_without_stopping(
    tmp_path: Path,
) -> None:
    invalid = tmp_path / "style-reviews" / "a-invalid.md"
    invalid.parent.mkdir(parents=True)
    invalid.write_text("No front matter.\n", encoding="utf-8")
    valid = tmp_path / "style-reviews" / "b-valid.md"
    _write_review(valid)

    errors = validate_style_reviews(
        tmp_path,
        _style_context(),
        {"manuscript/01-opening.md"},
    )

    assert len(errors) == 1
    assert str(invalid) in errors[0]
