from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

from creative_writer.checks import check_story
from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import load_yaml_model
from creative_writer.models import ReviewPackManifest
from creative_writer.review_packs import (
    generate_review_pack,
    review_pack_manifest_paths,
    validate_review_pack_manifest,
)
from creative_writer.scaffold import create_story


REPOSITORY = Path(__file__).resolve().parents[1]
STYLE_FIXTURES = REPOSITORY / "tests" / "fixtures" / "style"


def _write_valid_review_pack_manifest(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """title: "Boundary test"
purpose: "Exercise story-local review-pack resolution."
entries:
  - id: opening-beat
    label: "Opening beat"
    manuscript: "manuscript/01-opening.md"
    start_line: 1
    end_line: 1
    kind: uncertainty
    question: "Should this passage receive review?"
""",
        encoding="utf-8",
    )


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


def test_review_pack_discovery_rejects_symlinked_directory(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "linked-pack-directory", "original")
    external_directory = tmp_path / "external-review-packs"
    external_directory.mkdir()
    _write_valid_review_pack_manifest(external_directory / "external.yml")
    review_directory = story_dir / "review-packs"
    shutil.rmtree(review_directory)
    review_directory.symlink_to(external_directory, target_is_directory=True)

    with pytest.raises(
        CreativeWriterError,
        match=r"review-packs.*directory.*symlink|redirects through a symlink",
    ):
        review_pack_manifest_paths(story_dir)


def test_review_pack_discovery_rejects_symlinked_manifest(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "linked-pack-manifest", "original")
    external_manifest = tmp_path / "external-review-pack.yml"
    _write_valid_review_pack_manifest(external_manifest)
    manifest_link = story_dir / "review-packs" / "external.yml"
    manifest_link.symlink_to(external_manifest)

    with pytest.raises(
        CreativeWriterError,
        match=r"external\.yml.*symlink|redirects through a symlink",
    ):
        review_pack_manifest_paths(story_dir)


def test_review_pack_validation_rejects_external_regular_manifest(
    tmp_path: Path,
) -> None:
    story_dir = create_story(tmp_path, "external-pack-manifest", "original")
    external_manifest = tmp_path / "external-review-pack.yml"
    _write_valid_review_pack_manifest(external_manifest)

    with pytest.raises(
        CreativeWriterError,
        match=r"external-review-pack\.yml.*outside.*review-packs|physically contained",
    ):
        validate_review_pack_manifest(story_dir, external_manifest)


def test_review_pack_discovery_keeps_real_manifests_and_ignores_template(
    tmp_path: Path,
) -> None:
    story_dir = create_story(tmp_path, "real-pack-manifest", "original")
    manifest_path = story_dir / "review-packs" / "first-pass.yml"
    _write_valid_review_pack_manifest(manifest_path)
    (story_dir / "review-packs" / "_template.yml").write_text(
        "template only\n",
        encoding="utf-8",
    )

    assert review_pack_manifest_paths(story_dir) == [manifest_path]


def test_generate_review_pack_rejects_absolute_manifest_name(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "absolute-pack-name", "original")
    (story_dir / "manuscript" / "01-opening.md").write_text(
        "Opening line.\n",
        encoding="utf-8",
    )
    external_manifest = tmp_path / "external-review-pack.yml"
    _write_valid_review_pack_manifest(external_manifest)

    with pytest.raises(CreativeWriterError, match="story-local YAML filename"):
        generate_review_pack(
            tmp_path,
            "absolute-pack-name",
            str(external_manifest),
        )


@pytest.mark.parametrize(
    ("pack_name", "manifest_relative"),
    [
        ("nested/pack", "review-packs/nested/pack.yml"),
        ("../outside", "outside.yml"),
        (r"..\outside", r"review-packs/..\outside.yml"),
        ("outside.md", "review-packs/outside.md.yml"),
    ],
)
def test_generate_review_pack_rejects_unsafe_manifest_names(
    tmp_path: Path,
    pack_name: str,
    manifest_relative: str,
) -> None:
    story_dir = create_story(tmp_path, "unsafe-pack-name", "original")
    (story_dir / "manuscript" / "01-opening.md").write_text(
        "Opening line.\n",
        encoding="utf-8",
    )
    _write_valid_review_pack_manifest(story_dir / manifest_relative)

    with pytest.raises(CreativeWriterError, match="story-local YAML filename"):
        generate_review_pack(tmp_path, "unsafe-pack-name", pack_name)


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


def test_review_pack_without_style_metadata_retains_exact_legacy_output(
    tmp_path: Path,
) -> None:
    story_dir = create_story(tmp_path, "legacy-pack", "original")
    (story_dir / "manuscript" / "01-opening.md").write_text(
        "First line.\nSecond line.\nThird line.\n",
        encoding="utf-8",
    )
    (story_dir / "review-packs" / "legacy.yml").write_text(
        """title: "Legacy pass"
purpose: "Preserve the existing review surface."
entries:
  - id: opening-beat
    label: "Opening beat"
    manuscript: "manuscript/01-opening.md"
    start_line: 1
    end_line: 2
    kind: confidence
    question: "Is this working?"
    context: "Opening scene."
""",
        encoding="utf-8",
    )

    result = generate_review_pack(tmp_path, "legacy-pack", "legacy")

    assert result.output_path.read_text(encoding="utf-8") == (
        "# Review Pack: Legacy pass\n"
        "\n"
        "- Story: `Legacy Pack`\n"
        "- Story slug: `legacy-pack`\n"
        "- Pack: `legacy`\n"
        "- Purpose: Preserve the existing review surface.\n"
        "- Entries: 1\n"
        "\n"
        "## 1. Opening beat\n"
        "\n"
        "- Kind: `confidence`\n"
        "- Source: `manuscript/01-opening.md:1-2`\n"
        "- Chapter: `Opening`\n"
        "- Chapter summary: Set up the story situation and introduce the first turn.\n"
        "- Context: Opening scene.\n"
        "- Reviewer question: Is this working?\n"
        "\n"
        "### Excerpt\n"
        "\n"
        "```text\n"
        "First line.\n"
        "Second line.\n"
        "```\n"
    )


def test_review_pack_renders_precise_style_calibration_before_excerpt(
    tmp_path: Path,
) -> None:
    story_dir = create_story(tmp_path, "style-pack", "original")
    (story_dir / "manuscript" / "01-opening.md").write_text(
        "First line.\nSecond line.\n",
        encoding="utf-8",
    )
    (story_dir / "review-packs" / "calibration.yml").write_text(
        """title: "Calibration pass"
purpose: "Ask for a bounded authenticity decision."
entries:
  - id: reported-distance
    label: "Reported distance"
    manuscript: "manuscript/01-opening.md"
    start_line: 1
    end_line: 2
    kind: uncertainty
    question: "Should this reported distance be retained?"
    style:
      finding_ids: [finding-003]
      profile_id: wells-1895-1899
      profile_version: 1.0.0
      claim_ids: [role-shaped-narrator-distance]
      narrative_role: reported-account
      ai_disposition: escalate
      ai_rationale: "The profile signal is mechanically true, but the source packet contains authentic role-specific variation that makes direct revision uncertain."
      decision_impact: "The ruling will guide narrator-distance choices across all reported-account chapters."
""",
        encoding="utf-8",
    )

    result = generate_review_pack(tmp_path, "style-pack", "calibration")
    output = result.output_path.read_text(encoding="utf-8")
    style_block = (
        "### Style calibration context\n"
        "\n"
        "- Profile: `wells-1895-1899` version `1.0.0`\n"
        "- Intended role: `reported-account`\n"
        "- Style findings: `finding-003`\n"
        "- Phase 2B claims: `role-shaped-narrator-distance`\n"
        "- AI disposition: `escalate`\n"
        "- AI rationale: The profile signal is mechanically true, but the source packet contains authentic role-specific variation that makes direct revision uncertain.\n"
        "- Decision impact: The ruling will guide narrator-distance choices across all reported-account chapters.\n"
    )

    assert style_block in output
    assert (
        "- Reviewer question: Should this reported distance be retained?"
        in output
    )
    assert output.index(style_block) < output.index("### Excerpt")


def test_synthetic_style_calibration_review_pack_compiles(
    tmp_path: Path,
) -> None:
    manuscript_fixture = STYLE_FIXTURES / "calibration-manuscript.md"
    manifest_fixture = STYLE_FIXTURES / "calibration-review-pack.yml"
    assert manuscript_fixture.is_file(), (
        f"missing calibration fixture: {manuscript_fixture}"
    )
    assert manifest_fixture.is_file(), (
        f"missing calibration fixture: {manifest_fixture}"
    )
    manuscript_text = manuscript_fixture.read_text(encoding="utf-8")
    manuscript_lines = manuscript_text.splitlines()
    assert len(manuscript_lines) == 9
    assert all(line.strip() for line in manuscript_lines)

    story_dir = create_story(tmp_path, "synthetic-calibration", "original")
    (story_dir / "manuscript" / "calibration-manuscript.md").write_text(
        manuscript_text,
        encoding="utf-8",
    )
    target_manifest = story_dir / "review-packs" / "calibration.yml"
    target_manifest.write_bytes(manifest_fixture.read_bytes())

    manifest = load_yaml_model(target_manifest, ReviewPackManifest)
    result = generate_review_pack(
        tmp_path,
        "synthetic-calibration",
        "calibration",
    )
    output = result.output_path.read_text(encoding="utf-8")
    expected_questions = [
        "Is the repeated phrase functioning as deliberate testimony structure, or should the profile continue to flag it as reusable cadence?",
        "Is the even notebook cadence an authentic documentary effect, or does it flatten the Time Traveller's reported voice?",
        "Does the generic scanner identify a real modern explanatory habit here, or is it colliding with legitimate period scientific exposition?",
    ]
    expected_roles = [
        "reported-account",
        "notebook",
        "scientific-exposition",
    ]
    expected_rule_ids = [
        "diagnostic-repeated-phrases",
        "diagnostic-uniform-cadence",
        "anti-drift-modern-hard-sf-explanation",
    ]

    assert result.entry_count == 3
    assert manifest.title == "Synthetic style calibration"
    assert manifest.purpose == (
        "Exercise the selective human escalation surface without using "
        "manuscript prose"
    )
    assert [entry.kind for entry in manifest.entries] == ["uncertainty"] * 3
    assert [entry.id for entry in manifest.entries] == [
        "repeated-phrase",
        "notebook-cadence",
        "modern-exposition",
    ]
    assert [
        (entry.start_line, entry.end_line) for entry in manifest.entries
    ] == [(1, 3), (4, 6), (7, 9)]
    assert [entry.question for entry in manifest.entries] == expected_questions
    assert all(entry.style is not None for entry in manifest.entries)
    styles = [entry.style for entry in manifest.entries if entry.style is not None]
    assert [style.finding_ids for style in styles] == [
        ["finding-001"],
        ["finding-002"],
        ["finding-003"],
    ]
    assert [style.narrative_role for style in styles] == expected_roles
    assert all(style.profile_id == "wells-1895-1899" for style in styles)
    assert all(style.profile_version == "1.0.0" for style in styles)
    assert all(style.ai_disposition == "escalate" for style in styles)
    assert all("packet" in style.ai_rationale.lower() for style in styles)
    assert all(
        "later Permian chapters" in style.decision_impact
        and rule_id in style.decision_impact
        for style, rule_id in zip(styles, expected_rule_ids, strict=True)
    )
    assert output.count("### Style calibration context") == 3
    assert output.count("- Reviewer question:") == 3
    assert all(question in output for question in expected_questions)


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


def test_make_review_pack_remains_unchanged_by_style_options() -> None:
    repository = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            "make",
            "-n",
            "review-pack",
            "STORY=time-expedition",
            "PACK=first-human-pass",
            "PROFILE=style-profile.yml",
            "CHAPTER=01-last-week-of-the-permian",
        ],
        cwd=repository,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == (
        'uv run creative-writer review-pack --story "time-expedition" '
        '--pack "first-human-pass"'
    )
