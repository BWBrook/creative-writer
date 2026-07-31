from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

import pytest
import yaml

from creative_writer.checks import check_story
from creative_writer.scaffold import create_story
from creative_writer.source_analysis_common import sha256_file


STYLE_ARTIFACTS = (
    "source-study/analysis.yml",
    "original/sources.yml",
    "source-study/holdouts.yml",
    "source-study/evidence-ledger.yml",
    "source-study/validation.md",
)


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _set_chapter_style_metadata(
    story_dir: Path,
    *,
    roles: list[str],
    packets: list[str],
) -> None:
    path = story_dir / "chapter-stubs" / "01-opening.md"
    _opening, front_matter, body = path.read_text(encoding="utf-8").split("---", 2)
    payload = yaml.safe_load(front_matter)
    assert isinstance(payload, dict)
    payload["style_roles"] = roles
    payload["style_packets"] = packets
    rendered = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    path.write_text(f"---\n{rendered}---{body}", encoding="utf-8")


@pytest.fixture
def configured_style_story(tmp_path: Path) -> Path:
    story_dir = create_story(tmp_path, "configured-style", "original")
    repository = Path(__file__).resolve().parents[1]
    source_story = repository / "stories" / "time-expedition"
    for relative in STYLE_ARTIFACTS:
        destination = story_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_story / relative, destination)

    holdout = _read_yaml(story_dir / "source-study" / "holdouts.yml")
    story_prefix = "stories/configured-style"
    profile = {
        "schema_version": 1,
        "profile_id": "configured-style-profile",
        "version": "1.0.0",
        "title": "Configured style check fixture",
        "provenance": {
            "study_id": "time-expedition-wells-phase-2b",
            "analysis": {
                "path": f"{story_prefix}/source-study/analysis.yml",
                "sha256": sha256_file(story_dir / "source-study" / "analysis.yml"),
            },
            "source_registry": {
                "path": f"{story_prefix}/original/sources.yml",
                "sha256": sha256_file(story_dir / "original" / "sources.yml"),
            },
            "holdout_manifest": {
                "path": f"{story_prefix}/source-study/holdouts.yml",
                "sha256": sha256_file(story_dir / "source-study" / "holdouts.yml"),
            },
            "evidence_ledger": {
                "path": f"{story_prefix}/source-study/evidence-ledger.yml",
                "sha256": sha256_file(
                    story_dir / "source-study" / "evidence-ledger.yml"
                ),
            },
            "validation_record": {
                "path": f"{story_prefix}/source-study/validation.md",
                "sha256": sha256_file(story_dir / "source-study" / "validation.md"),
            },
            "passage_indexes": {
                "development": {
                    "path": holdout["development_passage_index"]["path"],
                    "sha256": holdout["development_passage_index"]["sha256"],
                },
                "heldout_wells": {
                    "path": holdout["heldout_wells_passage_index"]["path"],
                    "sha256": holdout["heldout_wells_passage_index"]["sha256"],
                },
                "tier4_controls": {
                    "path": holdout["tier4_control_passage_index"]["path"],
                    "sha256": holdout["tier4_control_passage_index"]["sha256"],
                },
            },
            "approved_review_run_id": "final-audit-rereview",
        },
        "eligible_claim_statuses": ["validated", "qualified"],
        "default_packet_ids": ["frame"],
        "change_basis": "Exercise configured check-time validation.",
        "profile_review_refs": [
            "source-study/validation.md#final-audit-rereview"
        ],
        "roles": [
            {
                "id": "frame",
                "label": "Frame",
                "description": "Visible testimony and evidentiary framing.",
                "phase_2b_roles": ["frame architecture", "testimony"],
            },
            {
                "id": "reported-account",
                "label": "Reported account",
                "description": "A second compatible chapter role.",
                "phase_2b_roles": ["testimony"],
            },
        ],
        "rules": [
            {
                "id": "practice-mediated-testimony",
                "name": "Mediated testimony",
                "family": "practice",
                "advisory": "review",
                "claim_ids": ["mediated-testimony-frame"],
                "roles": ["frame"],
                "scope": "story",
                "evaluation_mode": "manual_question",
                "review_question": "Is extraordinary testimony visibly mediated?",
                "source_passage_ids": [
                    "the-time-machine:ii:101:b859a93fec21"
                ],
                "variation_passage_ids": [],
                "control_passage_ids": [],
                "packet_ids": ["frame"],
                "interpretation_limits": "The approved claim remains bounded.",
            }
        ],
    }
    packet = {
        "schema_version": 1,
        "id": "frame",
        "title": "Frame and testimony",
        "purpose": "Exercise one approved source relationship.",
        "profile_id": "configured-style-profile",
        "profile_version": "1.0.0",
        "roles": ["frame"],
        "claim_ids": ["mediated-testimony-frame"],
        "context_radius": 1,
        "entries": [
            {
                "id": "time-machine-frame",
                "passage_id": "the-time-machine:ii:101:b859a93fec21",
                "kind": "positive_example",
                "claim_ids": ["mediated-testimony-frame"],
                "authority_tier": 1,
                "permitted_use": "Study evidentiary mediation.",
                "selection_note": "Approved ledger support.",
            }
        ],
        "prohibited_uses": ["Do not copy local wording."],
        "anti_copying_guidance": "Study method without borrowing phrases.",
    }
    _write_yaml(story_dir / "style-profile.yml", profile)
    _write_yaml(story_dir / "style-reference-packets" / "frame.yml", packet)

    contract = _read_yaml(story_dir / "contract.yml")
    contract["style_lint"] = {
        "profile": "style-profile.yml",
        "generic_ai_audit": True,
    }
    _write_yaml(story_dir / "contract.yml", contract)
    _set_chapter_style_metadata(
        story_dir,
        roles=["frame", "reported-account"],
        packets=["frame"],
    )
    return story_dir


def test_reference_integrity_fails_for_unknown_registry_entries(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "reference-test", "original")

    (story_dir / "characters.yml").write_text(
        "characters:\n  - id: hero\n    name: Hero\n",
        encoding="utf-8",
    )
    (story_dir / "chapter-stubs" / "01-opening.md").write_text(
        """---
title: "Opening"
summary: "Introduce the protagonist."
manuscript: "manuscript/01-opening.md"
scene_cards_dir: "scene-cards/01-opening"
characters:
  - stranger
locations: []
clues_introduced: []
clues_resolved: []
plot_devices: []
timeline_events: []
images: []
---

Stub text.
""",
        encoding="utf-8",
    )
    (story_dir / "manuscript" / "01-opening.md").write_text("Body text.\n", encoding="utf-8")

    result = check_story(tmp_path, "reference-test")

    assert not result.ok
    assert any("Unknown characters referenced" in error.message for error in result.errors)


def test_heuristics_warn_without_failing(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "warning-test", "original")

    (story_dir / "contract.yml").write_text(
        """human_role: "Guide the story."
ai_role: "Draft the prose."
authority_mode: direct_edit
review_mode: git_diff
lint:
  em_dash:
    enabled: true
    max_per_chapter: 0
  contrastive_parallelism:
    enabled: true
    max_instances_per_chapter: 0
""",
        encoding="utf-8",
    )
    (story_dir / "chapter-stubs" / "01-opening.md").write_text(
        """---
title: "Opening"
summary: "Generate warnings but no blocking errors."
manuscript: "manuscript/01-opening.md"
scene_cards_dir: "scene-cards/01-opening"
characters: []
locations: []
clues_introduced: []
clues_resolved: []
plot_devices: []
timeline_events: []
images: []
---
Stub text.
""",
        encoding="utf-8",
    )
    (story_dir / "manuscript" / "01-opening.md").write_text(
        "This line uses an em dash — once.\nIt was not quiet but tense.\n",
        encoding="utf-8",
    )

    result = check_story(tmp_path, "warning-test")

    assert result.ok
    assert len(result.warnings) == 2
    assert [warning.message for warning in result.warnings] == [
        "Em dash count 1 exceeds configured limit 0.",
        "Contrastive parallelism count 1 exceeds configured limit 0.",
    ]


def test_invalid_story_schema_is_blocking(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "schema-test", "original")
    (story_dir / "story.yml").write_text(
        """title: "Broken Story"
slug: "schema-test"
kind: "mystery"
status: planning
target_outputs:
  - epub
chapters:
  - chapter-stubs/01-opening.md
""",
        encoding="utf-8",
    )

    result = check_story(tmp_path, "schema-test")

    assert not result.ok
    assert any("Schema validation failed" in error.message for error in result.errors)


def test_missing_referenced_image_is_blocking(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "image-test", "original")

    (story_dir / "chapter-stubs" / "01-opening.md").write_text(
        """---
title: "Opening"
summary: "Check image handling."
manuscript: "manuscript/01-opening.md"
scene_cards_dir: "scene-cards/01-opening"
characters: []
locations: []
clues_introduced: []
clues_resolved: []
plot_devices: []
timeline_events: []
images:
  - assets/images/missing.jpeg
---

Stub text.
""",
        encoding="utf-8",
    )
    (story_dir / "manuscript" / "01-opening.md").write_text(
        "![Missing image](assets/images/missing.jpeg)\n",
        encoding="utf-8",
    )

    result = check_story(tmp_path, "image-test")

    assert not result.ok
    assert any("image" in error.message.lower() for error in result.errors)


def test_missing_narrative_design_is_blocking(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "missing-design", "original")
    (story_dir / "narrative-design.md").unlink()

    result = check_story(tmp_path, "missing-design")

    assert not result.ok
    assert any("narrative-design.md" in error.location for error in result.errors)


def test_empty_plot_devices_registry_is_allowed_without_references(tmp_path: Path) -> None:
    create_story(tmp_path, "no-plot-devices", "original")

    result = check_story(tmp_path, "no-plot-devices")

    assert result.ok


def test_plot_device_reference_requires_registry_entry(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "plot-device-fail", "original")

    (story_dir / "chapter-stubs" / "01-opening.md").write_text(
        """---
title: "Opening"
summary: "Introduce a plot device."
manuscript: "manuscript/01-opening.md"
scene_cards_dir: "scene-cards/01-opening"
characters: []
locations: []
clues_introduced: []
clues_resolved: []
plot_devices:
  - missing-device
timeline_events: []
images: []
---

Stub text.
""",
        encoding="utf-8",
    )
    (story_dir / "manuscript" / "01-opening.md").write_text("Body text.\n", encoding="utf-8")

    result = check_story(tmp_path, "plot-device-fail")

    assert not result.ok
    assert any("Unknown plot devices referenced" in error.message for error in result.errors)


def test_coherence_report_includes_scene_cards_and_plot_devices(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "report-test", "original")

    (story_dir / "plot_devices.yml").write_text(
        """plot_devices:
  - id: test-device
    name: "Test device"
    narrative_role: "Creates a structural turn."
    description: "Used to prove report coverage."
    status: active
""",
        encoding="utf-8",
    )
    (story_dir / "chapter-stubs" / "01-opening.md").write_text(
        """---
title: "Opening"
summary: "Generate a populated report."
manuscript: "manuscript/01-opening.md"
scene_cards_dir: "scene-cards/01-opening"
characters: []
locations: []
clues_introduced: []
clues_resolved: []
plot_devices:
  - test-device
timeline_events: []
images: []
---

Stub text.
""",
        encoding="utf-8",
    )
    (story_dir / "manuscript" / "01-opening.md").write_text("Body text.\n", encoding="utf-8")
    (story_dir / "scene-cards" / "01-opening" / "01-first-beat.md").write_text(
        "# First Beat\n",
        encoding="utf-8",
    )

    result = check_story(tmp_path, "report-test")
    report = result.report_path.read_text(encoding="utf-8")

    assert result.ok
    assert "## Scene cards" in report
    assert "## Plot devices" in report
    assert "Plot devices tracked: 1" in report
    assert "plot devices=1 | scene cards=1" in report
    assert "scene-cards/01-opening/01-first-beat.md" in report
    assert "_template.md" not in report


def test_check_without_configured_style_profile_keeps_existing_behavior(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_story(tmp_path, "plain-story", "original")

    monkeypatch.setattr(
        "creative_writer.checks.load_style_context",
        lambda *_args, **_kwargs: pytest.fail(
            "unconfigured stories must not load a style profile"
        ),
        raising=False,
    )

    result = check_story(tmp_path, "plain-story")

    assert result.ok
    assert not result.warnings


def test_check_passes_with_configured_profile_without_generated_indexes(
    configured_style_story: Path,
) -> None:
    root = configured_style_story.parent.parent
    index_dir = root / "build" / "time-expedition" / "source-study" / "indexes"

    result = check_story(root, "configured-style")

    assert result.ok, [error.message for error in result.errors]
    assert not index_dir.exists()


def test_check_reports_missing_configured_profile(
    configured_style_story: Path,
) -> None:
    profile_path = configured_style_story / "style-profile.yml"
    profile_path.unlink()

    result = check_story(configured_style_story.parent.parent, "configured-style")

    assert not result.ok
    assert any(
        error.location == str(profile_path) and "Missing file" in error.message
        for error in result.errors
    )


def test_check_reports_stale_style_provenance(
    configured_style_story: Path,
) -> None:
    ledger_path = configured_style_story / "source-study" / "evidence-ledger.yml"
    ledger_path.write_text(
        ledger_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    result = check_story(configured_style_story.parent.parent, "configured-style")

    assert not result.ok
    assert any(
        error.location == str(configured_style_story / "style-profile.yml")
        and "evidence-ledger SHA-256 mismatch" in error.message
        for error in result.errors
    )


@pytest.mark.parametrize(
    ("roles", "packets", "expected"),
    [
        (["unknown-role"], ["frame"], "unknown style role `unknown-role`"),
        (["frame"], ["unknown-packet"], "unknown style packet `unknown-packet`"),
    ],
)
def test_check_reports_unknown_chapter_style_metadata(
    configured_style_story: Path,
    roles: list[str],
    packets: list[str],
    expected: str,
) -> None:
    _set_chapter_style_metadata(
        configured_style_story,
        roles=roles,
        packets=packets,
    )

    result = check_story(configured_style_story.parent.parent, "configured-style")

    assert not result.ok
    assert any(expected in error.message for error in result.errors)


def test_check_reports_broken_declared_packet_manifest(
    configured_style_story: Path,
) -> None:
    manifest_path = (
        configured_style_story / "style-reference-packets" / "frame.yml"
    )
    manifest_path.write_text("schema_version: 1\nid: frame\n", encoding="utf-8")

    result = check_story(configured_style_story.parent.parent, "configured-style")

    assert not result.ok
    assert any(
        error.location == str(manifest_path)
        and "Schema validation failed" in error.message
        for error in result.errors
    )


def test_check_validates_every_real_packet_manifest(
    configured_style_story: Path,
) -> None:
    manifest_path = (
        configured_style_story / "style-reference-packets" / "orphan.yml"
    )
    payload = _read_yaml(
        configured_style_story / "style-reference-packets" / "frame.yml"
    )
    payload["id"] = "orphan"
    payload["title"] = "Undeclared real packet"
    _write_yaml(manifest_path, payload)

    result = check_story(configured_style_story.parent.parent, "configured-style")

    assert not result.ok
    assert any(
        error.location == str(manifest_path)
        and "not declared by the configured profile" in error.message
        for error in result.errors
    )


def test_check_ignores_packet_readme_and_template(
    configured_style_story: Path,
) -> None:
    packet_dir = configured_style_story / "style-reference-packets"
    (packet_dir / "README.md").write_text("Not a manifest.\n", encoding="utf-8")
    (packet_dir / "_template.yml").write_text(
        "schema_version: invalid\n",
        encoding="utf-8",
    )

    result = check_story(configured_style_story.parent.parent, "configured-style")

    assert result.ok, [error.message for error in result.errors]


def test_check_does_not_execute_style_analysis_or_external_scanner(
    configured_style_story: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "creative_writer.style_lint.generate_style_lint",
        lambda *_args, **_kwargs: pytest.fail("style lint must remain explicit"),
    )
    monkeypatch.setattr(
        "creative_writer.ai_audit.scan_ai_writing_json",
        lambda *_args, **_kwargs: pytest.fail("scanner must remain explicit"),
    )

    result = check_story(configured_style_story.parent.parent, "configured-style")

    assert result.ok, [error.message for error in result.errors]


def test_check_accepts_mixed_style_roles_without_warning(
    configured_style_story: Path,
) -> None:
    result = check_story(configured_style_story.parent.parent, "configured-style")

    assert result.ok, [error.message for error in result.errors]
    assert not result.warnings
