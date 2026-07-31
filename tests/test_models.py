from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import load_yaml_model
from creative_writer.models import (
    ChapterFrontMatter,
    ContractConfig,
    PlotDevicesRegistry,
    ReviewPackManifest,
)


def old_contract_payload() -> dict[str, object]:
    return {
        "human_role": "Author and final decision-maker.",
        "ai_role": "Drafting and editorial collaborator.",
        "authority_mode": "review_first",
        "review_mode": "git_diff",
    }


def old_chapter_payload() -> dict[str, object]:
    return {
        "title": "The first chapter",
        "summary": "The expedition begins.",
        "manuscript": "manuscript/01-first-chapter.md",
    }


def old_review_pack_payload() -> dict[str, object]:
    return {
        "title": "First review",
        "purpose": "Resolve one consequential uncertainty.",
        "entries": [
            {
                "id": "opening-frame",
                "label": "Opening frame",
                "manuscript": "manuscript/01-first-chapter.md",
                "start_line": 1,
                "end_line": 8,
                "kind": "uncertainty",
                "question": "Is the evidentiary frame legible?",
            }
        ],
    }


def test_plot_devices_registry_parses_valid_yaml(tmp_path: Path) -> None:
    registry_path = tmp_path / "plot_devices.yml"
    registry_path.write_text(
        """plot_devices:
  - id: test-device
    name: "Test device"
    narrative_role: "Creates structural pressure."
    description: "Used for schema validation."
    status: active
""",
        encoding="utf-8",
    )

    registry = load_yaml_model(registry_path, PlotDevicesRegistry)

    assert registry.plot_devices[0].id == "test-device"
    assert registry.plot_devices[0].status == "active"


def test_plot_devices_registry_rejects_invalid_status(tmp_path: Path) -> None:
    registry_path = tmp_path / "plot_devices.yml"
    registry_path.write_text(
        """plot_devices:
  - id: test-device
    name: "Test device"
    narrative_role: "Creates structural pressure."
    description: "Used for schema validation."
    status: pending
""",
        encoding="utf-8",
    )

    with pytest.raises(CreativeWriterError):
        load_yaml_model(registry_path, PlotDevicesRegistry)


def test_plot_devices_registry_rejects_invalid_id(tmp_path: Path) -> None:
    registry_path = tmp_path / "plot_devices.yml"
    registry_path.write_text(
        """plot_devices:
  - id: "Bad Device"
    name: "Bad device"
    narrative_role: "Creates structural pressure."
    description: "Used for schema validation."
    status: active
""",
        encoding="utf-8",
    )

    with pytest.raises(CreativeWriterError):
        load_yaml_model(registry_path, PlotDevicesRegistry)


def test_old_contract_still_parses_without_style_lint() -> None:
    contract = ContractConfig.model_validate(old_contract_payload())

    assert contract.style_lint is None
    assert contract.lint.em_dash.enabled is True


def test_contract_accepts_optional_style_lint_settings() -> None:
    payload = old_contract_payload()
    payload["style_lint"] = {
        "profile": "style-reference/style-profile.yml",
        "generic_ai_audit": False,
    }

    contract = ContractConfig.model_validate(payload)

    assert contract.style_lint is not None
    assert contract.style_lint.profile == "style-reference/style-profile.yml"
    assert contract.style_lint.generic_ai_audit is False


@pytest.mark.parametrize(
    "profile",
    [
        "/absolute/style-profile.yml",
        "../style-profile.yml",
        "style-reference\\style-profile.yml",
        "style-reference//style-profile.yml",
        "style-profile.json",
    ],
)
def test_contract_rejects_invalid_style_lint_profile_path(profile: str) -> None:
    payload = old_contract_payload()
    payload["style_lint"] = {"profile": profile}

    with pytest.raises(
        ValidationError, match="style-lint profile must be a story-relative YAML path"
    ):
        ContractConfig.model_validate(payload)


def test_old_chapter_stub_still_parses_without_style_metadata() -> None:
    chapter = ChapterFrontMatter.model_validate(old_chapter_payload())

    assert chapter.style_roles == []
    assert chapter.style_packets == []


def test_chapter_stub_accepts_optional_style_roles_and_packets() -> None:
    payload = old_chapter_payload()
    payload["style_roles"] = [" frame ", "scientific-inference"]
    payload["style_packets"] = [" frame-and-testimony "]

    chapter = ChapterFrontMatter.model_validate(payload)

    assert chapter.style_roles == ["frame", "scientific-inference"]
    assert chapter.style_packets == ["frame-and-testimony"]


@pytest.mark.parametrize("field", ["style_roles", "style_packets"])
def test_chapter_stub_rejects_empty_style_metadata_members(field: str) -> None:
    payload = old_chapter_payload()
    payload[field] = [" "]

    with pytest.raises(ValidationError, match="values must be non-empty strings"):
        ChapterFrontMatter.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "member"),
    [
        ("style_roles", "frame"),
        ("style_packets", "frame-and-testimony"),
    ],
)
def test_chapter_stub_rejects_duplicate_style_metadata_after_normalization(
    field: str, member: str
) -> None:
    payload = old_chapter_payload()
    payload[field] = [member, f" {member} "]

    with pytest.raises(ValidationError, match=rf"{field} must be unique"):
        ChapterFrontMatter.model_validate(payload)


def test_old_review_pack_manifest_still_parses_without_style_context() -> None:
    manifest = ReviewPackManifest.model_validate(old_review_pack_payload())

    assert manifest.entries[0].style is None


def test_review_pack_entry_accepts_optional_style_context() -> None:
    payload = old_review_pack_payload()
    payload["entries"][0]["style"] = {
        "finding_ids": ["finding-001"],
        "profile_id": "wells-1895-1899",
        "profile_version": "1.0.0",
        "claim_ids": ["qualified-speculative-inference"],
        "narrative_role": "scientific-inference",
        "ai_disposition": "escalate",
        "ai_rationale": "The passage is consequential and context-sensitive.",
        "decision_impact": "The answer will calibrate later inference passages.",
    }

    manifest = ReviewPackManifest.model_validate(payload)

    assert manifest.entries[0].style is not None
    assert manifest.entries[0].style.ai_disposition == "escalate"


@pytest.mark.parametrize(
    ("field", "member"),
    [
        ("finding_ids", "finding-001"),
        ("claim_ids", "qualified-speculative-inference"),
    ],
)
def test_review_pack_style_context_rejects_duplicate_id_members(
    field: str, member: str
) -> None:
    payload = old_review_pack_payload()
    style = {
        "finding_ids": [],
        "profile_id": "wells-1895-1899",
        "profile_version": "1.0.0",
        "claim_ids": [],
        "narrative_role": "scientific-inference",
        "ai_disposition": "monitor",
        "ai_rationale": "The local signal may be harmless.",
        "decision_impact": "The answer will guide later review.",
    }
    style[field] = [member, member]
    payload["entries"][0]["style"] = style

    with pytest.raises(ValidationError, match=rf"{field} must be unique"):
        ReviewPackManifest.model_validate(payload)


def test_review_pack_style_context_rejects_malformed_profile_version() -> None:
    payload = old_review_pack_payload()
    payload["entries"][0]["style"] = {
        "profile_id": "wells-1895-1899",
        "profile_version": "1.0",
        "narrative_role": "scientific-inference",
        "ai_disposition": "monitor",
        "ai_rationale": "The local signal may be harmless.",
        "decision_impact": "The answer will guide later review.",
    }

    with pytest.raises(ValidationError):
        ReviewPackManifest.model_validate(payload)
