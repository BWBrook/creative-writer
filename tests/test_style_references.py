from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

import creative_writer.cli as cli_module
import creative_writer.style_references as style_references_module
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


def test_style_reference_rejects_symlinked_output_target(
    style_packet_story: StylePacketFixture,
) -> None:
    outside = style_packet_story.root / "unrelated.md"
    outside.write_text("must remain unchanged\n", encoding="utf-8")
    output_dir = (
        style_packet_story.root
        / "build"
        / "packet-story"
        / "style"
        / "reference-packets"
    )
    output_dir.mkdir(parents=True)
    (output_dir / "frame.md").symlink_to(outside)

    with pytest.raises(CreativeWriterError, match="symlink|redirects"):
        generate_style_reference(
            style_packet_story.root,
            "packet-story",
            "frame",
        )

    assert outside.read_text(encoding="utf-8") == "must remain unchanged\n"


def test_style_reference_replaces_hard_link_without_mutating_alias(
    style_packet_story: StylePacketFixture,
) -> None:
    alias = style_packet_story.root / "unrelated.md"
    alias.write_text("must remain unchanged\n", encoding="utf-8")
    output_dir = (
        style_packet_story.root
        / "build"
        / "packet-story"
        / "style"
        / "reference-packets"
    )
    output_dir.mkdir(parents=True)
    output_path = output_dir / "frame.md"
    os.link(alias, output_path)

    result = generate_style_reference(
        style_packet_story.root,
        "packet-story",
        "frame",
    )

    assert alias.read_text(encoding="utf-8") == "must remain unchanged\n"
    assert result.output_path.read_text(encoding="utf-8").startswith(
        "# Style Reference Packet:"
    )
    assert alias.stat().st_ino != result.output_path.stat().st_ino
    assert sorted(path.name for path in output_dir.iterdir()) == ["frame.md"]


def test_style_reference_staging_failure_preserves_previous_packet(
    style_packet_story: StylePacketFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = (
        style_packet_story.root
        / "build"
        / "packet-story"
        / "style"
        / "reference-packets"
    )
    output_dir.mkdir(parents=True)
    output_path = output_dir / "frame.md"
    output_path.write_text("previous good packet\n", encoding="utf-8")

    def fail_fsync(_file_descriptor: int) -> None:
        raise OSError("injected staging failure")

    monkeypatch.setattr(os, "fsync", fail_fsync)

    with pytest.raises(CreativeWriterError, match="injected staging failure"):
        generate_style_reference(
            style_packet_story.root,
            "packet-story",
            "frame",
        )

    assert output_path.read_text(encoding="utf-8") == "previous good packet\n"
    assert sorted(path.name for path in output_dir.iterdir()) == ["frame.md"]


def test_style_reference_staging_collision_preserves_unrelated_file(
    style_packet_story: StylePacketFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = (
        style_packet_story.root
        / "build"
        / "packet-story"
        / "style"
        / "reference-packets"
    )
    output_dir.mkdir(parents=True)
    staging_path = output_dir / ".frame.md.tmp-fixed-token"
    staging_path.write_text("unrelated staging collision\n", encoding="utf-8")
    monkeypatch.setattr(
        style_references_module.uuid,
        "uuid4",
        lambda: SimpleNamespace(hex="fixed-token"),
    )

    with pytest.raises(CreativeWriterError, match="File exists"):
        generate_style_reference(
            style_packet_story.root,
            "packet-story",
            "frame",
        )

    assert staging_path.read_text(encoding="utf-8") == (
        "unrelated staging collision\n"
    )
    assert not (output_dir / "frame.md").exists()


def test_style_reference_publish_failure_preserves_previous_packet(
    style_packet_story: StylePacketFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = (
        style_packet_story.root
        / "build"
        / "packet-story"
        / "style"
        / "reference-packets"
    )
    output_dir.mkdir(parents=True)
    output_path = output_dir / "frame.md"
    output_path.write_text("previous good packet\n", encoding="utf-8")

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("injected publish failure")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(CreativeWriterError, match="injected publish failure"):
        generate_style_reference(
            style_packet_story.root,
            "packet-story",
            "frame",
        )

    assert output_path.read_text(encoding="utf-8") == "previous good packet\n"
    assert sorted(path.name for path in output_dir.iterdir()) == ["frame.md"]


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
    rendered_entry_ids = re.findall(
        r"^### \d+\. [^:]+: `([^`]+)`$",
        body,
        flags=re.MULTILINE,
    )
    assert rendered_entry_ids == ["positive", "variation", "control"]


def test_tier_four_calibration_entries_are_never_positive_guidance(
    style_packet_story: StylePacketFixture,
) -> None:
    result = generate_style_reference(
        style_packet_story.root,
        "packet-story",
        "frame",
    )
    body = result.output_path.read_text(encoding="utf-8")
    positive_section, negative_section = body.split(
        "## Negative comparisons",
        maxsplit=1,
    )
    packet = style_packet_story.context.packets["frame"]
    tier_four_ids = {
        entry.passage_id
        for entry in packet.entries
        if entry.authority_tier == 4
    }
    control_texts = {
        record.original_text
        for record in parse_passage_partition(
            style_packet_story.index_bytes["tier4_controls"]
        )
        if record.passage_id in tier_four_ids
    }

    assert tier_four_ids
    assert all(
        entry.kind == "negative_control"
        for entry in packet.entries
        if entry.authority_tier == 4
    )
    assert all(text not in positive_section for text in control_texts)
    assert all(text in negative_section for text in control_texts)
    assert "never a positive Wells model" in negative_section


@pytest.mark.parametrize(
    "entry_ids",
    [
        ["control", "positive", "variation"],
        ["positive", "control", "variation"],
    ],
    ids=["leading-control", "interleaved-control"],
)
def test_style_reference_rejects_section_incompatible_manifest_order(
    style_packet_story: StylePacketFixture,
    entry_ids: list[str],
) -> None:
    manifest = style_packet_story.context.packets["frame"]
    entries = {entry.id: entry for entry in manifest.entries}
    manifest.entries = [entries[entry_id] for entry_id in entry_ids]

    with pytest.raises(
        CreativeWriterError,
        match="negative-control.*follow|section ordering",
    ):
        generate_style_reference(
            style_packet_story.root,
            "packet-story",
            "frame",
        )


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


def test_style_reference_stops_context_at_same_heading_source_ordinal_gaps(
    style_packet_story: StylePacketFixture,
) -> None:
    separated_before = _passage(
        witness_id="heldout-wells",
        source_id="heldout-wells",
        source_ordinal=5,
        heading="Testimony",
        heading_ordinal=1,
        normalized_text="Separated same-heading passage before.",
    )
    focal = _passage(
        witness_id="heldout-wells",
        source_id="heldout-wells",
        source_ordinal=11,
        heading="Testimony",
        heading_ordinal=2,
        normalized_text="Gap-bounded authentic variation focal.",
    )
    separated_after = _passage(
        witness_id="heldout-wells",
        source_id="heldout-wells",
        source_ordinal=17,
        heading="Testimony",
        heading_ordinal=3,
        normalized_text="Separated same-heading passage after.",
    )
    heldout_path = style_packet_story.index_paths["heldout_wells"]
    heldout_path.write_bytes(
        serialize_passage_partition(
            [separated_before, focal, separated_after]
        )
    )
    heldout_reference = (
        style_packet_story.context.profile.provenance.passage_indexes.heldout_wells
    )
    heldout_reference.sha256 = sha256_file(heldout_path)

    old_passage_id = style_packet_story.passage_ids["variation"]
    variation_entry = style_packet_story.context.packets["frame"].entries[1]
    variation_entry.passage_id = focal.passage_id
    old_evidence = style_packet_story.context.evidence_catalog.pop(old_passage_id)
    style_packet_story.context.evidence_catalog[focal.passage_id] = EvidencePassage(
        passage_id=focal.passage_id,
        witness_id=old_evidence.witness_id,
        source_id=old_evidence.source_id,
        selection_id=old_evidence.selection_id,
        authority_tier=old_evidence.authority_tier,
        claim_ids=old_evidence.claim_ids,
        evidence_kinds=old_evidence.evidence_kinds,
    )

    result = generate_style_reference(
        style_packet_story.root,
        "packet-story",
        "frame",
    )
    body = result.output_path.read_text(encoding="utf-8")

    assert "Gap-bounded authentic variation focal." in body
    assert "Separated same-heading passage before." not in body
    assert "Separated same-heading passage after." not in body


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


def test_style_reference_parser_accepts_optional_profile() -> None:
    args = cli_module.build_parser().parse_args(
        [
            "style-reference",
            "--story",
            "time-expedition",
            "--pack",
            "frame-and-testimony",
            "--profile",
            "style-profile.yml",
        ]
    )

    assert vars(args) == {
        "command": "style-reference",
        "story": "time-expedition",
        "pack": "frame-and-testimony",
        "profile": "style-profile.yml",
    }


def test_style_reference_parser_defaults_profile_to_none() -> None:
    args = cli_module.build_parser().parse_args(
        [
            "style-reference",
            "--story",
            "time-expedition",
            "--pack",
            "frame-and-testimony",
        ]
    )

    assert args.profile is None


def test_style_reference_cli_reports_output_and_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = (
        tmp_path
        / "build/story/style/reference-packets/frame-and-testimony.md"
    )
    calls: list[tuple[Path, str, str, str | None]] = []

    def generate(
        root: Path,
        slug: str,
        pack: str,
        profile_override: str | None = None,
    ) -> SimpleNamespace:
        calls.append((root, slug, pack, profile_override))
        return SimpleNamespace(
            output_path=output_path,
            entry_count=4,
        )

    monkeypatch.setattr(cli_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        style_references_module,
        "generate_style_reference",
        generate,
    )

    status = cli_module.main(
        [
            "style-reference",
            "--story",
            "story",
            "--pack",
            "frame-and-testimony",
            "--profile",
            "profiles/wells.yml",
        ]
    )

    assert status == 0
    assert calls == [
        (tmp_path, "story", "frame-and-testimony", "profiles/wells.yml")
    ]
    assert capsys.readouterr().out.splitlines() == [
        f"Style reference packet written to {output_path}",
        "Entries: 4",
    ]
