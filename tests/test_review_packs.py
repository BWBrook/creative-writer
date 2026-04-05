from __future__ import annotations

from pathlib import Path

import pytest

from creative_writer.checks import check_story
from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import load_yaml_model
from creative_writer.models import ReviewPackManifest
from creative_writer.review_packs import generate_review_pack, validate_review_pack_manifest
from creative_writer.scaffold import create_story


def test_review_pack_manifest_parses_valid_yaml(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sample.yml"
    manifest_path.write_text(
        """title: "First pass"
purpose: "Ask for targeted human review."
entries:
  - id: opening-beat
    label: "Opening beat"
    manuscript: "manuscript/01-opening.md"
    start_line: 1
    end_line: 3
    kind: confidence
    question: "Is this working?"
    context: "Opening scene."
""",
        encoding="utf-8",
    )

    manifest = load_yaml_model(manifest_path, ReviewPackManifest)

    assert manifest.entries[0].kind == "confidence"
    assert manifest.entries[0].start_line == 1


def test_review_pack_manifest_rejects_invalid_kind(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sample.yml"
    manifest_path.write_text(
        """title: "First pass"
purpose: "Ask for targeted human review."
entries:
  - id: opening-beat
    label: "Opening beat"
    manuscript: "manuscript/01-opening.md"
    start_line: 1
    end_line: 3
    kind: praise
    question: "Is this working?"
""",
        encoding="utf-8",
    )

    with pytest.raises(CreativeWriterError):
        load_yaml_model(manifest_path, ReviewPackManifest)


def test_review_pack_manifest_rejects_invalid_manuscript_path(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sample.yml"
    manifest_path.write_text(
        """title: "First pass"
purpose: "Ask for targeted human review."
entries:
  - id: opening-beat
    label: "Opening beat"
    manuscript: "drafts/01-opening.md"
    start_line: 1
    end_line: 3
    kind: confidence
    question: "Is this working?"
""",
        encoding="utf-8",
    )

    with pytest.raises(CreativeWriterError):
        load_yaml_model(manifest_path, ReviewPackManifest)


def test_review_pack_manifest_rejects_invalid_line_ranges(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sample.yml"
    manifest_path.write_text(
        """title: "First pass"
purpose: "Ask for targeted human review."
entries:
  - id: opening-beat
    label: "Opening beat"
    manuscript: "manuscript/01-opening.md"
    start_line: 4
    end_line: 2
    kind: confidence
    question: "Is this working?"
""",
        encoding="utf-8",
    )

    with pytest.raises(CreativeWriterError):
        load_yaml_model(manifest_path, ReviewPackManifest)


def test_review_pack_validation_rejects_empty_excerpt(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "empty-excerpt", "original")
    (story_dir / "manuscript" / "01-opening.md").write_text("\n\n", encoding="utf-8")
    manifest_path = story_dir / "review-packs" / "empty.yml"
    manifest_path.write_text(
        """title: "Empty excerpt"
purpose: "Check empty excerpt handling."
entries:
  - id: blank-beat
    label: "Blank beat"
    manuscript: "manuscript/01-opening.md"
    start_line: 1
    end_line: 2
    kind: uncertainty
    question: "Is there anything here?"
""",
        encoding="utf-8",
    )

    with pytest.raises(CreativeWriterError):
        validate_review_pack_manifest(story_dir, manifest_path)


def test_generate_review_pack_creates_markdown_with_chapter_context(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "pack-gen", "original")
    (story_dir / "manuscript" / "01-opening.md").write_text(
        "First line.\nSecond line.\nThird line.\nFourth line.\n",
        encoding="utf-8",
    )
    manifest_path = story_dir / "review-packs" / "first-pass.yml"
    manifest_path.write_text(
        """title: "First pass"
purpose: "Ask for targeted human review."
entries:
  - id: opening-beat
    label: "Opening beat"
    manuscript: "manuscript/01-opening.md"
    start_line: 1
    end_line: 3
    kind: confidence
    question: "Is the opening doing the right kind of work?"
    context: "This is intended as a quiet but confident start."
""",
        encoding="utf-8",
    )

    result = generate_review_pack(tmp_path, "pack-gen", "first-pass")
    output = result.output_path.read_text(encoding="utf-8")

    assert result.output_path.exists()
    assert "Opening beat" in output
    assert "Kind: `confidence`" in output
    assert "Source: `manuscript/01-opening.md:1-3`" in output
    assert "Reviewer question: Is the opening doing the right kind of work?" in output
    assert "Chapter summary: Set up the story situation and introduce the first turn." in output
    assert "First line.\nSecond line.\nThird line." in output


def test_check_warns_when_excerpt_pack_mode_has_no_real_manifests(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "excerpt-mode", "original")
    (story_dir / "contract.yml").write_text(
        """human_role: "Read selectively."
ai_role: "Draft selectively."
authority_mode: direct_edit
review_mode: excerpt_pack
""",
        encoding="utf-8",
    )

    result = check_story(tmp_path, "excerpt-mode")

    assert result.ok
    assert any("excerpt_pack" in warning.message for warning in result.warnings)


def test_check_fails_when_review_pack_manifest_is_broken(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "broken-pack", "original")
    (story_dir / "review-packs" / "broken.yml").write_text(
        """title: "Broken pack"
purpose: "Break validation."
entries:
  - id: missing-manuscript
    label: "Missing manuscript"
    manuscript: "manuscript/not-there.md"
    start_line: 1
    end_line: 2
    kind: uncertainty
    question: "Does this fail?"
""",
        encoding="utf-8",
    )

    result = check_story(tmp_path, "broken-pack")

    assert not result.ok
    assert any("Review-pack manuscript does not exist" in error.message for error in result.errors)


def test_check_passes_with_valid_review_pack_manifest(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "valid-pack", "original")
    (story_dir / "contract.yml").write_text(
        """human_role: "Read selectively."
ai_role: "Draft selectively."
authority_mode: direct_edit
review_mode: excerpt_pack
""",
        encoding="utf-8",
    )
    (story_dir / "manuscript" / "01-opening.md").write_text(
        "First line.\nSecond line.\nThird line.\n",
        encoding="utf-8",
    )
    (story_dir / "review-packs" / "first-pass.yml").write_text(
        """title: "First pass"
purpose: "Ask for targeted human review."
entries:
  - id: opening-beat
    label: "Opening beat"
    manuscript: "manuscript/01-opening.md"
    start_line: 1
    end_line: 2
    kind: confidence
    question: "Is this working?"
""",
        encoding="utf-8",
    )

    result = check_story(tmp_path, "valid-pack")

    assert result.ok
    assert not result.warnings
