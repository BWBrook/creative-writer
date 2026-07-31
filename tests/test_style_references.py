from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from creative_writer.exceptions import CreativeWriterError
from creative_writer.source_analysis_common import sha256_file
from creative_writer.source_analysis_models import PassageRecord
from creative_writer.source_passages import (
    parse_passage_partition,
    serialize_passage_partition,
)
from creative_writer.style_models import StyleProfile, StyleReferencePacket
from creative_writer.style_profiles import EvidencePassage, StyleContext
from creative_writer.style_references import (
    generate_style_reference,
    style_reference_manifest_paths,
)


PROFILE_HASH = "a" * 64
SOURCE_FINGERPRINT = "b" * 64


@dataclass(slots=True)
class StylePacketFixture:
    root: Path
    story_dir: Path
    context: StyleContext
    index_paths: dict[str, Path]
    index_bytes: dict[str, bytes]
    passage_ids: dict[str, str]


def _passage(
    *,
    witness_id: str,
    source_id: str,
    source_ordinal: int,
    heading: str,
    heading_ordinal: int,
    normalized_text: str,
    original_text: str | None = None,
    selection_id: str | None = None,
    witness_ordinal: int = 1,
) -> PassageRecord:
    content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    passage_id = (
        f"{witness_id}:{heading.lower().replace(' ', '-')}:"
        f"{source_ordinal}:{content_hash[:12]}"
    )
    return PassageRecord.model_validate(
        {
            "witness_id": witness_id,
            "witness_ordinal": witness_ordinal,
            "source_id": source_id,
            "selection_id": selection_id,
            "source_fingerprint": SOURCE_FINGERPRINT,
            "heading_path": [heading],
            "heading_label": heading,
            "block_type": "paragraph",
            "source_ordinal": source_ordinal,
            "heading_ordinal": heading_ordinal,
            "normalized_text": normalized_text,
            "original_text": original_text or normalized_text,
            "word_count": len(normalized_text.split()),
            "direct_dialogue": "none",
            "content_hash": content_hash,
            "passage_id": passage_id,
        }
    )


def _artifact(path: str, digest: str = PROFILE_HASH) -> dict[str, str]:
    return {"path": path, "sha256": digest}


def _profile(
    index_paths: dict[str, Path],
    index_bytes: dict[str, bytes],
) -> StyleProfile:
    return StyleProfile.model_validate(
        {
            "schema_version": 1,
            "profile_id": "fixture-wells-profile",
            "version": "1.0.0",
            "title": "Fixture Wells profile",
            "provenance": {
                "study_id": "fixture-wells-phase-2b",
                "analysis": _artifact(
                    "stories/packet-story/source-study/analysis.yml"
                ),
                "source_registry": _artifact(
                    "stories/packet-story/original/sources.yml"
                ),
                "holdout_manifest": _artifact(
                    "stories/packet-story/source-study/holdouts.yml"
                ),
                "evidence_ledger": _artifact(
                    "stories/packet-story/source-study/evidence-ledger.yml"
                ),
                "validation_record": _artifact(
                    "stories/packet-story/source-study/validation.md"
                ),
                "passage_indexes": {
                    name: _artifact(
                        index_paths[name].relative_to(
                            index_paths[name].parents[4]
                        ).as_posix(),
                        hashlib.sha256(index_bytes[name]).hexdigest(),
                    )
                    for name in (
                        "development",
                        "heldout_wells",
                        "tier4_controls",
                    )
                },
                "approved_review_run_id": "approved-whole-study",
            },
            "eligible_claim_statuses": ["validated", "qualified"],
            "default_packet_ids": ["frame"],
            "change_basis": "Approved fixture evidence.",
            "profile_review_refs": [
                "source-study/validation.md#approved-whole-study"
            ],
            "roles": [
                {
                    "id": "frame",
                    "label": "Frame and testimony",
                    "description": "Visible framing of extraordinary testimony.",
                    "phase_2b_roles": ["testimony"],
                }
            ],
            "rules": [],
        }
    )


def _packet(passage_ids: dict[str, str]) -> StyleReferencePacket:
    return StyleReferencePacket.model_validate(
        {
            "schema_version": 1,
            "id": "frame",
            "title": "Frame and testimony",
            "purpose": "Study mediated testimony without copying local prose.",
            "profile_id": "fixture-wells-profile",
            "profile_version": "1.0.0",
            "roles": ["frame"],
            "claim_ids": ["mediated-testimony"],
            "context_radius": 1,
            "entries": [
                {
                    "id": "positive",
                    "passage_id": passage_ids["positive"],
                    "kind": "positive_example",
                    "claim_ids": ["mediated-testimony"],
                    "authority_tier": 2,
                    "permitted_use": "Study evidentiary mediation.",
                    "selection_note": "Approved development evidence.",
                    "context_radius": 0,
                },
                {
                    "id": "variation",
                    "passage_id": passage_ids["variation"],
                    "kind": "authentic_variation",
                    "claim_ids": ["mediated-testimony"],
                    "authority_tier": 1,
                    "permitted_use": "Compare authentic variation.",
                    "selection_note": "Approved held-out evidence.",
                },
                {
                    "id": "control",
                    "passage_id": passage_ids["control"],
                    "kind": "negative_control",
                    "claim_ids": ["mediated-testimony"],
                    "authority_tier": 4,
                    "permitted_use": "Use only for negative comparison.",
                    "selection_note": "Approved Tier 4 control.",
                },
            ],
            "prohibited_uses": [
                "Do not copy phrases.",
                "Do not treat Tier 4 controls as Wells evidence.",
            ],
            "anti_copying_guidance": (
                "Study relationships and narrative method, then draft in "
                "independent wording."
            ),
        }
    )


def _source(
    source_id: str,
    title: str,
    *,
    selection_id: str | None = None,
    selection_title: str | None = None,
) -> SimpleNamespace:
    selections: list[SimpleNamespace] = []
    if selection_id is not None:
        selections.append(
            SimpleNamespace(id=selection_id, title=selection_title)
        )
    return SimpleNamespace(
        id=source_id,
        work=SimpleNamespace(title=title),
        selections=selections,
    )


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


@pytest.fixture
def style_packet_story(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> StylePacketFixture:
    root = tmp_path
    story_dir = root / "stories" / "packet-story"
    profile_path = story_dir / "style-profile.yml"
    manifest_path = story_dir / "style-reference-packets" / "frame.yml"

    _write_yaml(
        story_dir / "contract.yml",
        {
            "human_role": "Author",
            "ai_role": "Advisory collaborator",
            "authority_mode": "review_first",
            "review_mode": "git_diff",
            "style_lint": {
                "profile": "style-profile.yml",
                "generic_ai_audit": False,
            },
        },
    )
    profile_path.write_text(
        "fixture profile loaded by test context\n",
        encoding="utf-8",
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        "fixture packet loaded by test context\n",
        encoding="utf-8",
    )

    development = [
        _passage(
            witness_id="selected-wells/story-a",
            source_id="selected-wells",
            selection_id="story-a",
            source_ordinal=1,
            heading="Chapter One",
            heading_ordinal=1,
            normalized_text="Development context before.",
        ),
        _passage(
            witness_id="selected-wells/story-a",
            source_id="selected-wells",
            selection_id="story-a",
            source_ordinal=2,
            heading="Chapter One",
            heading_ordinal=2,
            normalized_text="Positive focal normalized text.",
            original_text="Positive  focal line.\nSecond line stays verbatim.",
        ),
        _passage(
            witness_id="selected-wells/story-a",
            source_id="selected-wells",
            selection_id="story-a",
            source_ordinal=3,
            heading="Chapter One",
            heading_ordinal=3,
            normalized_text="Development context after.",
        ),
        _passage(
            witness_id="selected-wells/story-a",
            source_id="selected-wells",
            selection_id="story-a",
            source_ordinal=4,
            heading="Chapter Two",
            heading_ordinal=1,
            normalized_text="A different heading.",
        ),
    ]
    heldout = [
        _passage(
            witness_id="heldout-wells",
            source_id="heldout-wells",
            source_ordinal=1,
            heading="Testimony",
            heading_ordinal=1,
            normalized_text="Held-out context before.",
        ),
        _passage(
            witness_id="heldout-wells",
            source_id="heldout-wells",
            source_ordinal=2,
            heading="Testimony",
            heading_ordinal=2,
            normalized_text="Authentic variation focal.",
        ),
        _passage(
            witness_id="heldout-wells",
            source_id="heldout-wells",
            source_ordinal=3,
            heading="Afterword",
            heading_ordinal=1,
            normalized_text="Held-out next heading excluded.",
        ),
    ]
    controls = [
        _passage(
            witness_id="control-author",
            source_id="control-author",
            source_ordinal=1,
            heading="Adventure",
            heading_ordinal=1,
            normalized_text="Tier four control wording.",
        )
    ]
    index_records = {
        "development": development,
        "heldout_wells": heldout,
        "tier4_controls": controls,
    }
    index_bytes = {
        name: serialize_passage_partition(records)
        for name, records in index_records.items()
    }
    index_paths = {
        "development": (
            root
            / "build/packet-story/source-study/indexes/development.jsonl"
        ),
        "heldout_wells": (
            root
            / "build/packet-story/source-study/indexes/heldout-wells.jsonl"
        ),
        "tier4_controls": (
            root
            / "build/packet-story/source-study/indexes/tier4-controls.jsonl"
        ),
    }
    for name, path in index_paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(index_bytes[name])

    passage_ids = {
        "positive": development[1].passage_id,
        "variation": heldout[1].passage_id,
        "control": controls[0].passage_id,
    }
    profile = _profile(index_paths, index_bytes)
    packet = _packet(passage_ids)
    claim = SimpleNamespace(
        id="mediated-testimony",
        statement="Extraordinary testimony remains visibly mediated.",
        status="validated",
        classification="role_specific",
        confidence="moderate",
        jurisdiction=SimpleNamespace(
            scope="role_specific",
            roles=["testimony"],
            eligible_witness_ids=[
                "selected-wells/story-a",
                "heldout-wells",
            ],
        ),
        scope_and_limits="This applies only to bounded testimony roles.",
        prohibited_overgeneralisation=(
            "Do not turn a role-specific tendency into a universal rule."
        ),
    )
    evidence_catalog = {
        passage_ids["positive"]: EvidencePassage(
            passage_id=passage_ids["positive"],
            witness_id="selected-wells/story-a",
            source_id="selected-wells",
            selection_id="story-a",
            authority_tier=2,
            claim_ids=("mediated-testimony",),
            evidence_kinds=("support",),
        ),
        passage_ids["variation"]: EvidencePassage(
            passage_id=passage_ids["variation"],
            witness_id="heldout-wells",
            source_id="heldout-wells",
            selection_id=None,
            authority_tier=1,
            claim_ids=("mediated-testimony",),
            evidence_kinds=("validation",),
        ),
        passage_ids["control"]: EvidencePassage(
            passage_id=passage_ids["control"],
            witness_id="control-author",
            source_id="control-author",
            selection_id=None,
            authority_tier=4,
            claim_ids=("mediated-testimony",),
            evidence_kinds=("control",),
        ),
    }
    context = StyleContext(
        story_dir=story_dir,
        profile_path=profile_path,
        profile=profile,
        analysis=SimpleNamespace(study_id="fixture-wells-phase-2b"),
        ledger=SimpleNamespace(claims=[claim]),
        validation=SimpleNamespace(stage="validated"),
        sources=SimpleNamespace(
            sources=[
                _source(
                    "selected-wells",
                    "Selected Wells Collection",
                    selection_id="story-a",
                    selection_title="Selected Wells Story",
                ),
                _source("heldout-wells", "Held-Out Wells Novel"),
                _source("control-author", "Control Adventure"),
            ]
        ),
        evidence_catalog=evidence_catalog,
        rules=(),
        packets={"frame": packet},
    )
    monkeypatch.setattr(
        "creative_writer.style_references.load_style_context",
        lambda *_args, **_kwargs: context,
    )
    return StylePacketFixture(
        root=root,
        story_dir=story_dir,
        context=context,
        index_paths=index_paths,
        index_bytes=index_bytes,
        passage_ids=passage_ids,
    )


def test_style_reference_manifest_paths_are_sorted_and_ignore_template(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "style-reference-packets"
    directory.mkdir()
    for name in ("zeta.yml", "_template.yml", "alpha.yml", "notes.yaml"):
        (directory / name).write_text("fixture\n", encoding="utf-8")

    assert style_reference_manifest_paths(tmp_path) == [
        directory / "alpha.yml",
        directory / "zeta.yml",
    ]


@pytest.mark.parametrize(
    "pack",
    ["", "  ", "../frame", "nested/frame", "/tmp/frame", r"C:\tmp\frame"],
)
def test_style_reference_rejects_unsafe_pack_names(
    style_packet_story: StylePacketFixture,
    pack: str,
) -> None:
    with pytest.raises(CreativeWriterError, match="pack name|Pack name"):
        generate_style_reference(
            style_packet_story.root,
            "packet-story",
            pack,
        )


def test_style_reference_accepts_yml_suffix_and_reports_output_metadata(
    style_packet_story: StylePacketFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "creative_writer.style_references.run_source_analysis",
        lambda *_args, **_kwargs: pytest.fail(
            "verified indexes must not trigger preparation"
        ),
    )

    result = generate_style_reference(
        style_packet_story.root,
        "packet-story",
        "frame.yml",
    )

    assert result.story_slug == "packet-story"
    assert result.profile_id == "fixture-wells-profile"
    assert result.profile_version == "1.0.0"
    assert result.pack_name == "frame"
    assert result.manifest_path == (
        style_packet_story.story_dir
        / "style-reference-packets"
        / "frame.yml"
    )
    assert result.output_path == (
        style_packet_story.root
        / "build"
        / "packet-story"
        / "style"
        / "reference-packets"
        / "frame.md"
    )
    assert result.entry_count == 3
    assert result.source_indexes_prepared is False


def test_style_reference_compiles_manifest_order_and_negative_section(
    style_packet_story: StylePacketFixture,
) -> None:
    result = generate_style_reference(
        style_packet_story.root,
        "packet-story",
        "frame",
    )
    body = result.output_path.read_text(encoding="utf-8")

    assert body.index("Positive example") < body.index("Authentic variation")
    assert body.index("Authentic variation") < body.index(
        "## Negative comparisons"
    )
    assert "never a positive Wells model" in body
    positive_section, negative_section = body.split(
        "## Negative comparisons",
        maxsplit=1,
    )
    assert "Tier four control wording." not in positive_section
    assert "Tier four control wording." in negative_section


def test_style_reference_renders_provenance_claims_and_writer_guidance(
    style_packet_story: StylePacketFixture,
) -> None:
    result = generate_style_reference(
        style_packet_story.root,
        "packet-story",
        "frame",
    )
    body = result.output_path.read_text(encoding="utf-8")

    assert "# Style Reference Packet: Frame and testimony" in body
    assert "fixture-wells-profile" in body
    assert "fixture-wells-phase-2b" in body
    assert "approved-whole-study" in body
    assert "Study mediated testimony without copying local prose." in body
    assert "Frame and testimony (`frame`)" in body
    assert "mediated-testimony" in body
    assert "Final status: `validated`" in body
    assert "Classification: `role_specific`" in body
    assert "Confidence: `moderate`" in body
    assert "This applies only to bounded testimony roles." in body
    assert "Do not turn a role-specific tendency into a universal rule." in body
    assert "Do not copy phrases." in body
    assert "Do not treat Tier 4 controls as Wells evidence." in body
    assert (
        "Study relationships and narrative method, then draft in independent "
        "wording."
    ) in body


def test_style_reference_preserves_original_text_and_bounds_context_by_heading(
    style_packet_story: StylePacketFixture,
) -> None:
    result = generate_style_reference(
        style_packet_story.root,
        "packet-story",
        "frame",
    )
    body = result.output_path.read_text(encoding="utf-8")

    assert (
        "```text\nPositive  focal line.\nSecond line stays verbatim.\n```"
        in body
    )
    assert "Development context before." not in body
    assert "Development context after." not in body
    assert "Held-out context before." in body
    assert "Authentic variation focal." in body
    assert "Held-out next heading excluded." not in body


def test_style_reference_renders_source_identity_and_passage_metadata(
    style_packet_story: StylePacketFixture,
) -> None:
    result = generate_style_reference(
        style_packet_story.root,
        "packet-story",
        "frame",
    )
    body = result.output_path.read_text(encoding="utf-8")

    assert "Source title: Selected Wells Story" in body
    assert "Witness: `selected-wells/story-a`" in body
    assert "Authority tier: `2`" in body
    assert f"Stable passage ID: `{style_packet_story.passage_ids['positive']}`" in body
    assert "Heading path: `Chapter One`" in body
    assert "Selection rationale: Approved development evidence." in body
    assert "Permitted use: Study evidentiary mediation." in body


def test_style_reference_prepares_missing_indexes_exactly_once(
    style_packet_story: StylePacketFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for path in style_packet_story.index_paths.values():
        path.unlink()
    calls = 0

    def prepare(root: Path, slug: str, stage: str) -> None:
        nonlocal calls
        calls += 1
        assert root == style_packet_story.root
        assert slug == "packet-story"
        assert stage == "prepare"
        for name, path in style_packet_story.index_paths.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(style_packet_story.index_bytes[name])

    monkeypatch.setattr(
        "creative_writer.style_references.run_source_analysis",
        prepare,
    )

    result = generate_style_reference(
        style_packet_story.root,
        "packet-story",
        "frame",
    )

    assert calls == 1
    assert result.source_indexes_prepared is True


def test_style_reference_does_not_prepare_when_indexes_are_verified(
    style_packet_story: StylePacketFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "creative_writer.style_references.run_source_analysis",
        lambda *_args, **_kwargs: pytest.fail(
            "verified indexes must not be regenerated"
        ),
    )

    result = generate_style_reference(
        style_packet_story.root,
        "packet-story",
        "frame",
    )

    assert result.source_indexes_prepared is False


def test_style_reference_accepts_physical_partition_witness_ordinal_gaps(
    style_packet_story: StylePacketFixture,
) -> None:
    records = parse_passage_partition(
        style_packet_story.index_bytes["development"]
    )
    records.append(
        _passage(
            witness_id="later-wells",
            source_id="later-wells",
            witness_ordinal=3,
            source_ordinal=1,
            heading="Later Witness",
            heading_ordinal=1,
            normalized_text="A later global witness remains in this partition.",
        )
    )
    physical_partition = serialize_passage_partition(records)
    development_path = style_packet_story.index_paths["development"]
    development_path.write_bytes(physical_partition)
    style_packet_story.context.profile.provenance.passage_indexes.development.sha256 = (
        sha256_file(development_path)
    )

    result = generate_style_reference(
        style_packet_story.root,
        "packet-story",
        "frame",
    )

    assert result.entry_count == 3


def test_style_reference_blocks_stale_present_index_before_prepare(
    style_packet_story: StylePacketFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    style_packet_story.index_paths["development"].write_bytes(b"stale\n")
    style_packet_story.index_paths["heldout_wells"].unlink()
    monkeypatch.setattr(
        "creative_writer.style_references.run_source_analysis",
        lambda *_args, **_kwargs: pytest.fail(
            "stale present indexes must block before preparation"
        ),
    )

    with pytest.raises(
        CreativeWriterError,
        match="development.*SHA-256 mismatch",
    ):
        generate_style_reference(
            style_packet_story.root,
            "packet-story",
            "frame",
        )


def test_style_reference_verifies_indexes_created_by_prepare(
    style_packet_story: StylePacketFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    style_packet_story.index_paths["development"].unlink()

    def prepare(_root: Path, _slug: str, _stage: str) -> None:
        style_packet_story.index_paths["development"].write_bytes(b"wrong\n")

    monkeypatch.setattr(
        "creative_writer.style_references.run_source_analysis",
        prepare,
    )

    with pytest.raises(
        CreativeWriterError,
        match="development.*SHA-256 mismatch",
    ):
        generate_style_reference(
            style_packet_story.root,
            "packet-story",
            "frame",
        )


def test_style_reference_rejects_unknown_passage(
    style_packet_story: StylePacketFixture,
) -> None:
    style_packet_story.context.packets["frame"].entries[0].passage_id = (
        "selected-wells/story-a:missing:99:000000000000"
    )

    with pytest.raises(CreativeWriterError, match="Unknown passage ID"):
        generate_style_reference(
            style_packet_story.root,
            "packet-story",
            "frame",
        )


def test_style_reference_rejects_duplicate_passage_ids_across_partitions(
    style_packet_story: StylePacketFixture,
) -> None:
    duplicated = style_packet_story.index_bytes["development"]
    heldout_path = style_packet_story.index_paths["heldout_wells"]
    heldout_path.write_bytes(duplicated)
    heldout_reference = (
        style_packet_story.context.profile.provenance.passage_indexes.heldout_wells
    )
    heldout_reference.sha256 = sha256_file(heldout_path)

    with pytest.raises(
        CreativeWriterError,
        match="duplicate passage ID.*partitions",
    ):
        generate_style_reference(
            style_packet_story.root,
            "packet-story",
            "frame",
        )


def test_style_reference_uses_profile_override_without_contract(
    style_packet_story: StylePacketFixture,
) -> None:
    (style_packet_story.story_dir / "contract.yml").unlink()

    result = generate_style_reference(
        style_packet_story.root,
        "packet-story",
        "frame",
        profile_override="style-profile.yml",
    )

    assert result.profile_id == "fixture-wells-profile"


def test_style_reference_requires_configured_profile_or_override(
    style_packet_story: StylePacketFixture,
) -> None:
    (style_packet_story.story_dir / "contract.yml").unlink()

    with pytest.raises(CreativeWriterError, match="profile|contract"):
        generate_style_reference(
            style_packet_story.root,
            "packet-story",
            "frame",
        )
