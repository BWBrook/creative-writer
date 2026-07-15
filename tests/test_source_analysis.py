from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

import pytest
import yaml

from creative_writer.exceptions import CreativeWriterError
from creative_writer.source_analysis import _commit_staged, run_source_analysis, select_holdouts
from creative_writer.source_analysis_models import (
    AnalysisConfig,
    PassageRecord,
    WitnessDescriptor,
)
from creative_writer.source_passages import read_passage_index


HASH = "a" * 64


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_epub(path: Path, members: dict[str, str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument.org:xmlns:container" version="1.0">
  <rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>
""",
        )
        archive.writestr(
            "EPUB/package.opf",
            """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Fixture</dc:title></metadata>
  <manifest/><spine/>
</package>
""",
        )
        for member, content in (members or {}).items():
            archive.writestr(member, content)


def _dimensions() -> list[dict[str, object]]:
    ids = [
        "frame-architecture",
        "narrator-distance",
        "observation-inference",
        "scientific-exposition",
        "dialogue-social-friction",
        "syntax-rhythm",
        "diction-description",
        "suspense-scene-pressure",
        "humour-irony",
        "transitions-ending-logic",
    ]
    return [
        {
            "id": item,
            "label": item,
            "roles": ["fixture role"],
            "description": "Fixture dimension.",
        }
        for item in ids
    ]


def _analysis_config(admission_hash: str, source_hash: str, *, seed: str = "fixture-seed") -> dict[str, object]:
    return {
        "schema_version": 1,
        "study_id": "fixture-wells-phase-2b",
        "composition_window": {"start": 1897, "end": 1899},
        "study_status": "protocol",
        "admission_registry": {"path": "source-study/admission.yml", "sha256": admission_hash},
        "source_registry": {"path": "original/sources.yml", "sha256": source_hash},
        "authority_policy_version": "fixture-v1",
        "expected_corpus": {
            "admission_records": 4,
            "retained_sources": 3,
            "retained_epubs": 3,
            "retained_markdown": 6,
            "full_work_witnesses": 2,
            "selected_witnesses": 4,
            "witness_ids": [
                "wells-alpha",
                "selected-short-fiction/the-plattner-story",
                "selected-short-fiction/the-sea-raiders",
                "selected-short-fiction/the-crystal-egg",
                "selected-short-fiction/the-star",
                "control",
            ],
            "excluded_tier5_ids": ["the-lost-world"],
            "whole_work_holdouts": ["selected-short-fiction/the-star"],
        },
        "authority_tiers": [
            {
                "tier": tier,
                "jurisdiction": f"Tier {tier} jurisdiction.",
                "analytical_roles": {
                    1: ["wells-alpha role"],
                    2: ["selected-short-fiction role", "fixture role"],
                    3: [],
                    4: ["control role"],
                    5: ["later diagnostic"],
                }[tier],
                "evidence_rule": f"Tier {tier} rule.",
            }
            for tier in range(1, 6)
        ],
        "passage_rules": {
            "input_format": "gfm",
            "heading_context": True,
            "substantive_block_types": ["paragraph", "block_quote", "verse", "list_item"],
            "passage_id_template": "<witness-id>:<heading-slug>:<source-ordinal>:<hash12>",
            "context_radius": 2,
        },
        "partition": {
            "seed": seed,
            "algorithm_version": "tertile-hash-v1",
            "holdout_fraction": 0.2,
            "max_blocks_per_window": 5,
            "whole_work_holdouts": ["selected-short-fiction/the-star"],
        },
        "enabled_measurements": ["word_count"],
        "lexicons": {"reporting_verbs": ["said"]},
        "dimensions": _dimensions(),
        "confidence_levels": ["tentative", "moderate", "strong"],
        "claim_statuses": ["candidate", "qualified", "rejected", "validated"],
        "claim_classifications": [
            "wells_distinctive",
            "wells_characteristic_but_shared",
            "role_specific",
            "period_general",
            "unsupported",
        ],
        "evidence_roles": ["support", "counterexample", "variation", "control", "validation"],
        "generated_paths": {
            "corpus_lock": "build/fixture/source-study/corpus-lock.json",
            "passage_index": "build/fixture/source-study/passage-index.jsonl",
            "development_metrics": "build/fixture/source-study/development-metrics.json",
            "development_metrics_csv": "build/fixture/source-study/development-metrics.csv",
            "development_report": "build/fixture/source-study/development-report.md",
            "validation_metrics": "build/fixture/source-study/validation-metrics.json",
            "validation_packet": "build/fixture/source-study/validation-packet.md",
            "analysis_report": "build/fixture/source-study/analysis-report.md",
        },
    }


def _source_admission(source_id: str, tier: int, *, selections: list[dict[str, object]] | None = None) -> dict[str, object]:
    style = {1: "primary", 2: "bounded", 4: "control"}[tier]
    roles = [f"{source_id} role"]
    return {
        "id": source_id,
        "status": "admitted",
        "authority": {"tier": tier, "story_world_canon": tier == 1, "style_authority": style},
        "work": {
            "title": source_id.title(),
            "author": "Fixture Author",
            "first_published": None if selections else 1898,
        },
        "analytical_roles": roles,
        "permitted_uses": [f"{source_id} permitted"],
        "prohibited_uses": [f"{source_id} prohibited"],
        "rationale": "Synthetic Phase 2A-compatible fixture source.",
        "edition": {
            "publisher": "Fixture Press",
            "homepage": f"https://example.test/{source_id}",
            "download_url": f"https://example.test/{source_id}.epub",
            "artifact_format": "standard-ebooks-compatible-epub",
            "planned_path": f"original/{source_id}.epub",
            "public_domain_context": "Synthetic fixture.",
            "textual_limitations": "Synthetic fixture.",
            "editorial_normalisation": "Synthetic fixture.",
            "variant_concerns": "Synthetic fixture.",
        },
        "selections": selections or [],
    }


def _retained_source(
    story: Path,
    source_id: str,
    tier: int,
    *,
    selection_ids: list[str] | None = None,
) -> dict[str, object]:
    original = story / "original"
    epub = original / f"{source_id}.epub"
    members = {
        f"EPUB/{selection_id}.xhtml": f"<html><body><p>{selection_id}</p></body></html>"
        for selection_id in (selection_ids or [])
    }
    _write_epub(epub, members)
    record: dict[str, object] = {
        "id": source_id,
        "role": {
            "tier": tier,
            "story_world_canon": tier == 1,
            "style_authority": {1: "primary", 2: "bounded", 4: "control"}[tier],
            "primary_style_anchor": tier == 1,
            "secondary_style_anchor": tier == 2,
            "focus": "Synthetic fixture source.",
            "analytical_roles": [f"{source_id} role"],
            "permitted_uses": [f"{source_id} permitted"],
            "prohibited_uses": [f"{source_id} prohibited"],
        },
        "work": {
            "title": source_id.title(),
            "author": "Fixture Author",
            "first_published": None if selection_ids else 1898,
        },
        "edition": {
            "publisher": "Fixture Press",
            "homepage": f"https://example.test/{source_id}",
            "download_url": f"https://example.test/{source_id}.epub",
            "upstream_release": "fixture-release",
            "upstream_revision": "fixture-revision",
        },
        "retrieved": "2026-07-15",
        "files": {"epub": f"{source_id}.epub", "epub_sha256": _sha256(epub)},
        "derivation": {
            "tool": "Pandoc 3.10",
            "input": "fixture",
            "writer": "gfm",
            "wrap": "none",
            "filter": "fixture",
        },
        "provenance": {"transcription": "fixture", "page_scans": "fixture"},
        "rights": {"source_text": "fixture", "edition_contributions": "fixture"},
    }
    if selection_ids:
        selections = []
        for selection_id in selection_ids:
            markdown = original / "text" / "selected-short-fiction" / f"{selection_id}.md"
            markdown.parent.mkdir(parents=True, exist_ok=True)
            markdown.write_text(
                "# First\n\n"
                + "\n\n".join(f"{selection_id} first block {i}." for i in range(1, 7))
                + "\n\n# Second\n\n"
                + "\n\n".join(f"{selection_id} second block {i}." for i in range(1, 3))
                + "\n",
                encoding="utf-8",
            )
            selections.append(
                {
                    "id": selection_id,
                    "title": selection_id.replace("-", " ").title(),
                    "first_published": 1897,
                    "input": f"EPUB/{selection_id}.xhtml",
                    "markdown": f"text/selected-short-fiction/{selection_id}.md",
                    "markdown_sha256": _sha256(markdown),
                }
            )
        record["selections"] = selections
    else:
        markdown = original / "text" / f"{source_id}.md"
        markdown.parent.mkdir(parents=True, exist_ok=True)
        markdown.write_text(
            "# First\n\n" + "\n\n".join(f"{source_id} first block {i}." for i in range(1, 7))
            + "\n\n# Second\n\n"
            + "\n\n".join(f"{source_id} second block {i}." for i in range(1, 3))
            + "\n",
            encoding="utf-8",
        )
        record["files"]["markdown"] = f"text/{source_id}.md"  # type: ignore[index]
        record["files"]["markdown_sha256"] = _sha256(markdown)  # type: ignore[index]
    return record


def _write_fixture(root: Path) -> Path:
    story = root / "stories" / "fixture"
    (story / "source-study").mkdir(parents=True)
    sources = [
        _retained_source(story, "wells-alpha", 1),
        _retained_source(
            story,
            "selected-short-fiction",
            2,
            selection_ids=["the-plattner-story", "the-sea-raiders", "the-crystal-egg", "the-star"],
        ),
        _retained_source(story, "control", 4),
    ]
    admission_sources = [
        _source_admission("wells-alpha", 1),
        _source_admission(
            "selected-short-fiction",
            2,
            selections=[
                {"id": item, "title": item.replace("-", " ").title(), "first_published": 1897, "analytical_roles": ["fixture role"]}
                for item in ["the-plattner-story", "the-sea-raiders", "the-crystal-egg", "the-star"]
            ],
        ),
        _source_admission("control", 4),
        {
            "id": "the-lost-world",
            "status": "excluded",
            "authority": {"tier": 5, "story_world_canon": False, "style_authority": "none"},
            "work": {"title": "The Lost World", "author": "Arthur Conan Doyle", "first_published": 1912},
            "analytical_roles": ["later diagnostic"],
            "permitted_uses": ["none"],
            "prohibited_uses": ["all"],
            "rationale": "Excluded outside-window control.",
            "edition": {
                "publisher": "Fixture Press",
                "homepage": "https://example.test/lost-world",
                "download_url": "https://example.test/lost-world.epub",
                "artifact_format": "project-gutenberg-epub",
                "planned_path": "original/the-lost-world.epub",
                "public_domain_context": "fixture",
                "textual_limitations": "fixture",
                "editorial_normalisation": "fixture",
                "variant_concerns": "fixture",
            },
            "selections": [],
        },
    ]
    admission = {
        "composition_window": {"start": 1897, "end": 1899},
        "editorial_mode": "restrained_apparatus",
        "sources": admission_sources,
    }
    source_path = story / "original" / "sources.yml"
    source_path.write_text(yaml.safe_dump({"sources": sources}, sort_keys=False), encoding="utf-8")
    admission_path = story / "source-study" / "admission.yml"
    admission_path.write_text(yaml.safe_dump(admission, sort_keys=False), encoding="utf-8")
    config = _analysis_config(_sha256(admission_path), _sha256(source_path))
    (story / "source-study" / "analysis.yml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
    )
    return story


def _fixture(root: Path) -> tuple[Path, object]:
    story = _write_fixture(root)
    result = run_source_analysis(root, "fixture", "prepare")
    return story, result


def _passage(
    witness_id: str,
    ordinal: int,
    index: int,
    *,
    source_id: str | None = None,
    heading: str | None = None,
) -> PassageRecord:
    source_id = source_id or witness_id
    heading = heading or f"Heading {index}"
    text = f"Passage {index}."
    digest = hashlib.sha256(text.encode()).hexdigest()
    return PassageRecord(
        witness_id=witness_id,
        witness_ordinal=ordinal,
        source_id=source_id,
        selection_id=None,
        source_fingerprint=HASH,
        heading_path=[heading],
        heading_label=heading,
        block_type="paragraph",
        source_ordinal=index,
        heading_ordinal=1,
        normalized_text=text,
        original_text=text,
        word_count=2,
        direct_dialogue="none",
        content_hash=digest,
        passage_id=f"{witness_id}:{heading.lower().replace(' ', '-')}:" \
        f"{index}:{digest[:12]}",
    )


def _config_for_selection() -> AnalysisConfig:
    raw = _analysis_config(HASH, HASH)
    return AnalysisConfig.model_validate(raw)


def test_prepare_builds_exact_lock_and_expands_selected_selections_in_order(tmp_path: Path) -> None:
    story, result = _fixture(tmp_path)

    assert result.stage == "prepare"
    assert result.story_slug == "fixture"
    assert result.witness_count == 6
    assert result.passage_count == 48
    assert result.holdout_manifest_created is True
    assert result.holdout_manifest_verified is False

    lock_path = tmp_path / "build/fixture/source-study/corpus-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    assert "created_at" not in json.dumps(lock)
    assert lock["analysis"] == {
        "study_id": "fixture-wells-phase-2b",
        "story_slug": "fixture",
        "composition_window": {"start": 1897, "end": 1899},
        "authority_policy_version": "fixture-v1",
    }
    assert lock["registry_hashes"] == {
        "source-study/admission.yml": _sha256(story / "source-study/admission.yml"),
        "original/sources.yml": _sha256(story / "original/sources.yml"),
    }
    assert [item["id"] for item in lock["sources"]] == [
        "wells-alpha",
        "selected-short-fiction",
        "control",
    ]
    assert lock["sources"][1]["tier"] == 2
    assert lock["sources"][1]["analytical_roles"] == ["selected-short-fiction role"]
    assert lock["sources"][1]["epub_path"] == "original/selected-short-fiction.epub"
    assert lock["excluded_tier5_ids"] == ["the-lost-world"]
    assert lock["counts"] == {
        "admission_records": 4,
        "retained_sources": 3,
        "retained_epubs": 3,
            "retained_markdown": 6,
            "full_work_witnesses": 2,
            "selected_short_fiction_witnesses": 4,
            "witnesses": 6,
        "excluded_tier5_records": 1,
    }
    witnesses = lock["witnesses"]
    assert [item["witness_id"] for item in witnesses] == [
        "wells-alpha",
        "selected-short-fiction/the-plattner-story",
        "selected-short-fiction/the-sea-raiders",
        "selected-short-fiction/the-crystal-egg",
        "selected-short-fiction/the-star",
        "control",
    ]
    assert [item["witness_ordinal"] for item in witnesses] == list(range(1, 7))


def test_holdout_manifest_has_all_fingerprints_and_quarantines_controls(tmp_path: Path) -> None:
    story, result = _fixture(tmp_path)
    manifest = yaml.safe_load((story / "source-study/holdouts.yml").read_text(encoding="utf-8"))

    assert set(manifest["registry_hashes"]) == {"source-study/admission.yml", "original/sources.yml"}
    assert set(manifest["source_fingerprints"]) == {
        "source/wells-alpha/epub",
        "source/selected-short-fiction/epub",
        "source/control/epub",
        "witness/wells-alpha/markdown",
        "witness/selected-short-fiction/the-plattner-story/markdown",
        "witness/selected-short-fiction/the-sea-raiders/markdown",
        "witness/selected-short-fiction/the-crystal-egg/markdown",
        "witness/selected-short-fiction/the-star/markdown",
        "witness/control/markdown",
    }
    assert manifest["whole_work_holdouts"] == ["selected-short-fiction/the-star"]
    assert {item["witness_id"] for item in manifest["witnesses"]} == {
        "wells-alpha",
        "selected-short-fiction/the-plattner-story",
        "selected-short-fiction/the-sea-raiders",
        "selected-short-fiction/the-crystal-egg",
        "selected-short-fiction/the-star",
    }
    star = next(item for item in manifest["witnesses"] if item["witness_id"].endswith("/the-star"))
    assert star["development_windows"] == []
    assert len(star["holdout_windows"]) == 3
    assert all(item["id"].startswith("w0") for item in star["holdout_windows"])
    assert all(item["id"].startswith("w0") for item in manifest["witnesses"][0]["development_windows"])
    assert all("control" not in item["witness_id"] for item in manifest["witnesses"])
    assert result.holdout_path == story / "source-study/holdouts.yml"


def test_holdout_count_uses_round_half_up_and_hash_selection() -> None:
    config = _config_for_selection()
    passages = [
        _passage("wells-alpha", 1, index, heading=f"Heading {(index - 1) // 5}")
        for index in range(1, 41)
    ]
    partitions = select_holdouts(passages, config, {"wells-alpha": 1})
    assert len(partitions) == 1
    assert len(partitions[0].development_windows + partitions[0].holdout_windows) == 8
    assert len(partitions[0].holdout_windows) == 2
    expected = sorted(
        passages[::5],
        key=lambda item: hashlib.sha256(
            f"fixture-seed:wells-alpha:{item.passage_id}".encode()
        ).hexdigest(),
    )[0].passage_id
    assert expected in {
        passage_id
        for window in partitions[0].holdout_windows
        for passage_id in window.passage_ids
    }


def test_holdout_tertile_coverage_and_tie_order(monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config_for_selection()
    passages = [_passage("wells-alpha", 1, index) for index in range(1, 16)]
    ranks = {item.passage_id: f"{index:064x}" for index, item in enumerate(passages, start=1)}
    monkeypatch.setattr(
        "creative_writer.source_analysis._window_hash",
        lambda seed, source_id, first_passage_id: ranks[first_passage_id],
    )
    partitions = select_holdouts(passages, config, {"wells-alpha": 1})
    selected = {
        passage_id
        for window in partitions[0].holdout_windows
        for passage_id in window.passage_ids
    }
    assert selected == {passages[0].passage_id, passages[5].passage_id, passages[10].passage_id}

    monkeypatch.setattr(
        "creative_writer.source_analysis._window_hash",
        lambda seed, source_id, first_passage_id: "0" * 64,
    )
    tied = select_holdouts(passages[:5], config, {"wells-alpha": 1})
    assert tied[0].holdout_windows[0].passage_ids == [passages[0].passage_id]


def test_selected_short_fiction_hash_uses_parent_source_id() -> None:
    config = _config_for_selection()
    witness_id = "selected-short-fiction/the-plattner-story"
    passages = []
    for index in range(1, 11):
        text = f"Selected passage {index}."
        digest = hashlib.sha256(text.encode()).hexdigest()
        passages.append(
            PassageRecord(
                witness_id=witness_id,
                witness_ordinal=2,
                source_id="selected-short-fiction",
                selection_id="the-plattner-story",
                source_fingerprint=HASH,
                heading_path=["Selected"],
                heading_label="Selected",
                block_type="paragraph",
                source_ordinal=index,
                heading_ordinal=index,
                normalized_text=text,
                original_text=text,
                word_count=3,
                direct_dialogue="none",
                content_hash=digest,
                passage_id=f"{witness_id}:selected:{index}:{digest[:12]}",
            )
        )

    partitions = select_holdouts(passages, config, {"selected-short-fiction": 2})
    selected = {
        passage_id
        for window in partitions[0].holdout_windows
        for passage_id in window.passage_ids
    }
    window_starts = [passages[0], passages[5]]
    parent_rank = sorted(
        window_starts,
        key=lambda item: hashlib.sha256(
            f"fixture-seed:selected-short-fiction:{item.passage_id}".encode()
        ).hexdigest(),
    )[0].passage_id
    witness_rank = sorted(
        window_starts,
        key=lambda item: hashlib.sha256(
            f"fixture-seed:{witness_id}:{item.passage_id}".encode()
        ).hexdigest(),
    )[0].passage_id

    assert parent_rank != witness_rank
    assert parent_rank in selected
    assert witness_rank not in selected


@pytest.mark.parametrize(
    ("mutation", "needle"),
    [
        ("composition", "composition window"),
        ("roles", "authority tier"),
        ("whole_work", "whole_work_holdouts"),
        ("topology", "witness IDs"),
        ("excluded", "excluded Tier 5"),
        ("counts", "retained_sources"),
        ("order", "witness IDs"),
    ],
)
def test_prepare_rejects_wrong_story_local_corpus_authority(
    tmp_path: Path, mutation: str, needle: str
) -> None:
    story = _write_fixture(tmp_path)
    config_path = story / "source-study/analysis.yml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if mutation == "composition":
        config["composition_window"]["start"] = 1898
    elif mutation == "roles":
        config["authority_tiers"][0]["analytical_roles"] = ["wrong role"]
    elif mutation == "whole_work":
        config["partition"]["whole_work_holdouts"] = ["wells-alpha"]
    elif mutation == "topology":
        config["expected_corpus"]["witness_ids"][-1] = "missing-witness"
    elif mutation == "excluded":
        config["expected_corpus"]["excluded_tier5_ids"] = ["wrong-exclusion"]
    elif mutation == "counts":
        config["expected_corpus"]["retained_sources"] = 2
    elif mutation == "order":
        config["expected_corpus"]["witness_ids"] = list(
            reversed(config["expected_corpus"]["witness_ids"])
        )
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(CreativeWriterError, match=needle):
        run_source_analysis(tmp_path, "fixture", "prepare")


def test_prepare_rejects_cross_story_generated_path(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    config_path = story / "source-study/analysis.yml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["generated_paths"]["corpus_lock"] = "build/other/source-study/corpus-lock.json"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(CreativeWriterError, match="generated path.*corpus_lock"):
        run_source_analysis(tmp_path, "fixture", "prepare")


def test_prepare_rejects_generated_path_symlink_escape(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    generated_dir = tmp_path / "build" / "fixture"
    generated_dir.mkdir(parents=True)
    (generated_dir / "source-study").symlink_to(outside, target_is_directory=True)

    with pytest.raises(CreativeWriterError, match="symlink|escapes repository root"):
        run_source_analysis(tmp_path, "fixture", "prepare")


def test_prepare_rejects_cross_story_generated_path_symlink_before_output(
    tmp_path: Path,
) -> None:
    _write_fixture(tmp_path)
    other_source_study = tmp_path / "build/other/source-study"
    other_source_study.mkdir(parents=True)
    other_target = other_source_study / "corpus-lock.json"
    other_target.write_bytes(b"untouched")
    generated_dir = tmp_path / "build/fixture"
    generated_dir.mkdir(parents=True)
    (generated_dir / "source-study").symlink_to(
        other_source_study, target_is_directory=True
    )

    with pytest.raises(CreativeWriterError, match="symlink|lexical target"):
        run_source_analysis(tmp_path, "fixture", "prepare")

    assert other_target.read_bytes() == b"untouched"
    assert not (tmp_path / "stories/fixture/source-study/holdouts.yml").exists()


def test_holdout_partition_error_names_partition_windows() -> None:
    config = _config_for_selection()
    passages = [_passage("wells-alpha", 1, 1)]

    with pytest.raises(CreativeWriterError, match="at least two partition windows"):
        select_holdouts(passages, config, {"wells-alpha": 1})


def test_prepare_rerun_is_byte_stable_and_verifies_existing_manifest(tmp_path: Path) -> None:
    story, first = _fixture(tmp_path)
    paths = [
        tmp_path / "build/fixture/source-study/corpus-lock.json",
        tmp_path / "build/fixture/source-study/passage-index.jsonl",
        story / "source-study/holdouts.yml",
    ]
    before = {path: path.read_bytes() for path in paths}

    second = run_source_analysis(tmp_path, "fixture", "prepare")

    assert second.holdout_manifest_created is False
    assert second.holdout_manifest_verified is True
    assert {path: path.read_bytes() for path in paths} == before
    assert first.witness_count == second.witness_count


@pytest.mark.parametrize("stage", ["validate"])
def test_unsupported_stages_raise_clear_error(tmp_path: Path, stage: str) -> None:
    with pytest.raises(CreativeWriterError, match=f"stage.*{stage}.*not implemented"):
        run_source_analysis(tmp_path, "fixture", stage)


def test_prepare_blocks_before_analysis_outputs_when_admission_fails(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    admission = story / "source-study/admission.yml"
    admission.write_text(admission.read_text(encoding="utf-8").replace("wells-alpha role", "drifted role"), encoding="utf-8")

    with pytest.raises(CreativeWriterError, match="Source admission failed"):
        run_source_analysis(tmp_path, "fixture", "prepare")
    assert not (tmp_path / "build/fixture/source-study/corpus-lock.json").exists()
    assert not (tmp_path / "build/fixture/source-study/passage-index.jsonl").exists()
    assert not (story / "source-study/holdouts.yml").exists()


def test_prepare_blocks_registry_hash_drift_before_parsing(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    config_path = story / "source-study/analysis.yml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["source_registry"]["sha256"] = "0" * 64
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(CreativeWriterError, match="(?i)source registry.*SHA-256 mismatch"):
        run_source_analysis(tmp_path, "fixture", "prepare")


def test_prepare_blocks_existing_holdout_drift_and_preserves_bytes(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    holdouts = story / "source-study/holdouts.yml"
    before = holdouts.read_bytes()
    payload = yaml.safe_load(before)
    payload["partition_seed"] = "changed-seed"
    holdouts.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    changed = holdouts.read_bytes()

    with pytest.raises(CreativeWriterError, match="holdout manifest differs"):
        run_source_analysis(tmp_path, "fixture", "prepare")
    assert holdouts.read_bytes() == changed
    assert holdouts.read_bytes() != before


def test_prepare_rejects_empty_index_and_preserves_existing_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    story, _ = _fixture(tmp_path)
    paths = [
        tmp_path / "build/fixture/source-study/corpus-lock.json",
        tmp_path / "build/fixture/source-study/passage-index.jsonl",
        story / "source-study/holdouts.yml",
    ]
    before = {path: path.read_bytes() for path in paths}
    monkeypatch.setattr("creative_writer.source_analysis.parse_markdown_witness", lambda *args, **kwargs: [])

    with pytest.raises(CreativeWriterError, match="no substantive passages|empty passage index"):
        run_source_analysis(tmp_path, "fixture", "prepare")
    assert {path: path.read_bytes() for path in paths} == before


def test_prepare_rejects_duplicate_passages_before_replacing_existing_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    story, _ = _fixture(tmp_path)
    paths = [
        tmp_path / "build/fixture/source-study/corpus-lock.json",
        tmp_path / "build/fixture/source-study/passage-index.jsonl",
        story / "source-study/holdouts.yml",
    ]
    before = {path: path.read_bytes() for path in paths}
    import creative_writer.source_analysis as source_analysis
    from creative_writer.source_passages import parse_markdown_witness as parse_original

    def duplicate_first(*args: object, **kwargs: object) -> list[PassageRecord]:
        parsed = parse_original(*args, **kwargs)
        return [*parsed, parsed[0]]

    monkeypatch.setattr(source_analysis, "parse_markdown_witness", duplicate_first)
    with pytest.raises(CreativeWriterError, match="Duplicate passage ID"):
        run_source_analysis(tmp_path, "fixture", "prepare")
    assert {path: path.read_bytes() for path in paths} == before


def test_prepare_blocks_markdown_fingerprint_drift_and_preserves_existing_artifacts(
    tmp_path: Path,
) -> None:
    story, _ = _fixture(tmp_path)
    paths = [
        tmp_path / "build/fixture/source-study/corpus-lock.json",
        tmp_path / "build/fixture/source-study/passage-index.jsonl",
        story / "source-study/holdouts.yml",
    ]
    before = {path: path.read_bytes() for path in paths}
    markdown = story / "original/text/wells-alpha.md"
    markdown.write_text(markdown.read_text(encoding="utf-8") + "Drift.\n", encoding="utf-8")

    with pytest.raises(CreativeWriterError, match="Source admission failed"):
        run_source_analysis(tmp_path, "fixture", "prepare")
    assert {path: path.read_bytes() for path in paths} == before


def test_prepare_rollback_preserves_existing_artifacts_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    story, _ = _fixture(tmp_path)
    paths = [
        tmp_path / "build/fixture/source-study/corpus-lock.json",
        tmp_path / "build/fixture/source-study/passage-index.jsonl",
        story / "source-study/holdouts.yml",
    ]
    before = {path: path.read_bytes() for path in paths}
    import creative_writer.source_analysis as source_analysis

    real_replace = source_analysis.os.replace
    calls = 0

    def fail_during_install(source: str | bytes | Path, target: str | bytes | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic replace failure")
        real_replace(source, target)

    monkeypatch.setattr(source_analysis.os, "replace", fail_during_install)
    with pytest.raises(CreativeWriterError, match="atomically"):
        run_source_analysis(tmp_path, "fixture", "prepare")
    assert {path: path.read_bytes() for path in paths} == before


def test_first_install_rollback_removes_completed_artifact_and_temps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_fixture(tmp_path)
    import creative_writer.source_analysis as source_analysis

    real_replace = source_analysis.os.replace
    calls = 0

    def fail_after_first_install(source: str | bytes | Path, target: str | bytes | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("first-install failure")
        real_replace(source, target)

    monkeypatch.setattr(source_analysis.os, "replace", fail_after_first_install)
    with pytest.raises(CreativeWriterError, match="first-install failure"):
        run_source_analysis(tmp_path, "fixture", "prepare")

    assert not list((tmp_path / "build/fixture/source-study").glob("corpus-lock.json"))
    assert not list((tmp_path / "build/fixture/source-study").glob(".*.tmp"))
    assert not (tmp_path / "stories/fixture/source-study/holdouts.yml").exists()


def test_rerun_late_failure_restores_all_existing_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    story, _ = _fixture(tmp_path)
    paths = [
        tmp_path / "build/fixture/source-study/corpus-lock.json",
        tmp_path / "build/fixture/source-study/passage-index.jsonl",
        story / "source-study/holdouts.yml",
    ]
    before = {path: path.read_bytes() for path in paths}
    import creative_writer.source_analysis as source_analysis

    real_replace = source_analysis.os.replace
    calls = 0

    def fail_late(source: str | bytes | Path, target: str | bytes | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 4:
            raise OSError("late rerun failure")
        real_replace(source, target)

    monkeypatch.setattr(source_analysis.os, "replace", fail_late)
    with pytest.raises(CreativeWriterError, match="late rerun failure"):
        run_source_analysis(tmp_path, "fixture", "prepare")

    assert {path: path.read_bytes() for path in paths} == before


def test_rollback_reports_forced_restoration_failure_and_keeps_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    story, _ = _fixture(tmp_path)
    target = tmp_path / "build/fixture/source-study/corpus-lock.json"
    before = target.read_bytes()
    import creative_writer.source_analysis as source_analysis

    real_replace = source_analysis.os.replace
    calls = 0
    def fail_restore(source: str | bytes | Path, target_path: str | bytes | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 4:
            raise OSError("install failure before restore")
        if calls == 5:
            raise OSError("forced restoration failure")
        real_replace(source, target_path)

    monkeypatch.setattr(source_analysis.os, "replace", fail_restore)
    with pytest.raises(CreativeWriterError, match="forced restoration failure") as caught:
        run_source_analysis(tmp_path, "fixture", "prepare")

    assert "residual" in str(caught.value)
    backups = list(target.parent.glob(f".{target.name}.*.bak"))
    assert backups
    assert not target.exists()
    assert backups[0].read_bytes() == before


def test_cleanup_failure_reports_residual_temp_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target.txt"
    temporary = tmp_path / "temporary.tmp"
    target.write_bytes(b"old")
    temporary.write_bytes(b"new")
    import creative_writer.source_analysis as source_analysis

    real_unlink = Path.unlink

    def fail_temp_cleanup(path: Path, missing_ok: bool = False) -> None:
        if path == temporary:
            raise OSError("temporary cleanup failure")
        real_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fail_temp_cleanup)
    with pytest.raises(CreativeWriterError, match="temporary cleanup failure") as caught:
        _commit_staged([(target, temporary)])

    assert str(temporary) in str(caught.value)
    assert target.read_bytes() == b"new"


def test_prepare_preserves_install_and_cleanup_failures_without_raw_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_fixture(tmp_path)
    import creative_writer.source_analysis as source_analysis

    real_replace = source_analysis.os.replace
    real_unlink = Path.unlink
    replace_calls = 0
    cleanup_target: Path | None = None

    def fail_during_install(
        source: str | bytes | Path, target: str | bytes | Path
    ) -> None:
        nonlocal cleanup_target, replace_calls
        replace_calls += 1
        if replace_calls == 2:
            cleanup_target = Path(source)
            raise OSError("forced install failure")
        real_replace(source, target)

    def fail_temp_cleanup(path: Path, missing_ok: bool = False) -> None:
        if cleanup_target is not None and path == cleanup_target:
            raise OSError("forced temp-cleanup failure")
        real_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(source_analysis.os, "replace", fail_during_install)
    monkeypatch.setattr(Path, "unlink", fail_temp_cleanup)

    with pytest.raises(CreativeWriterError) as caught:
        run_source_analysis(tmp_path, "fixture", "prepare")

    message = str(caught.value)
    assert "forced install failure" in message
    assert "forced temp-cleanup failure" in message
    assert cleanup_target is not None
    assert str(cleanup_target) in message
    assert not isinstance(caught.value, OSError)


def test_prepare_rejects_unresolved_committed_passage_and_preserves_manifest(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    holdouts = story / "source-study/holdouts.yml"
    payload = yaml.safe_load(holdouts.read_text(encoding="utf-8"))
    payload["witnesses"][0]["holdout_windows"][0]["passage_ids"][0] = "wells-alpha:missing:1:" + "a" * 12
    holdouts.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    changed = holdouts.read_bytes()

    with pytest.raises(CreativeWriterError, match="unresolved passage ID"):
        run_source_analysis(tmp_path, "fixture", "prepare")
    assert holdouts.read_bytes() == changed


def test_partition_window_ids_are_global_by_witness_ordinal_and_reading_order(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    manifest = yaml.safe_load((story / "source-study/holdouts.yml").read_text(encoding="utf-8"))
    ids = [
        window["id"]
        for witness in manifest["witnesses"]
        for window in [*witness["development_windows"], *witness["holdout_windows"]]
    ]
    assert len(ids) == len(set(ids))
    assert all(len(item.split("-")) == 3 for item in ids)
    for witness in manifest["witnesses"]:
        windows = [*witness["development_windows"], *witness["holdout_windows"]]
        assert [passage for window in windows for passage in window["passage_ids"]] == [
            passage
            for window in sorted(windows, key=lambda item: item["id"])
            for passage in window["passage_ids"]
        ] if not witness["development_windows"] else [
            passage
            for window in sorted(witness["development_windows"], key=lambda item: item["id"])
            for passage in window["passage_ids"]
        ] + [
            passage
            for window in sorted(witness["holdout_windows"], key=lambda item: item["id"])
            for passage in window["passage_ids"]
        ]


def test_develop_requires_committed_holdouts_and_writes_development_only_outputs(
    tmp_path: Path,
) -> None:
    story, _ = _fixture(tmp_path)
    with pytest.raises(CreativeWriterError, match="holdout manifest.*tracked|committed"):
        run_source_analysis(tmp_path, "fixture", "develop")

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "fixture@example.test"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "add", "stories/fixture/source-study/holdouts.yml"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(["git", "commit", "-qm", "lock fixture holdouts"], cwd=tmp_path, check=True)

    result = run_source_analysis(tmp_path, "fixture", "develop")
    assert result.stage == "develop"
    metrics = json.loads(
        (tmp_path / "build/fixture/source-study/development-metrics.json").read_text(
            encoding="utf-8"
        )
    )
    assert metrics["stage"] == "development"
    assert metrics["config_sha256"]
    assert metrics["index_sha256"]
    assert metrics["manifest_sha256"]
    assert [item["witness_id"] for item in metrics["witnesses"]] == [
        "wells-alpha",
        "selected-short-fiction/the-plattner-story",
        "selected-short-fiction/the-sea-raiders",
        "selected-short-fiction/the-crystal-egg",
    ]
    for output_name in (
        "development-metrics.json",
        "development-metrics.csv",
        "development-report.md",
    ):
        text = (tmp_path / "build/fixture/source-study" / output_name).read_text(
            encoding="utf-8"
        )
        assert "selected-short-fiction/the-star" not in text
        assert "control" not in text
    report = (tmp_path / "build/fixture/source-study/development-report.md").read_text(
        encoding="utf-8"
    )
    assert "approximation" in report.lower()
    assert "pooled wells target" in report.lower()
