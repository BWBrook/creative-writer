from __future__ import annotations

import csv
import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

import pytest
import yaml
import creative_writer.source_analysis as source_analysis

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import load_yaml_model
from creative_writer.models import SourceStudyAdmission, SourcesRegistry
from creative_writer.source_analysis import (
    _commit_staged,
    _expected_observation_paths,
    _resolve_generated_paths,
    _tracked_evidence_paths,
    _validate_development_dossier_set,
    run_source_analysis,
    select_holdouts,
    validate_evidence_ledger,
    validate_observation_dossiers,
    validate_profile_claim_links,
)
from creative_writer.source_analysis_models import (
    AnalysisConfig,
    EvidenceLedger,
    HoldoutManifest,
    MetricReference,
    PassageRecord,
    QuantitativeProfile,
    WitnessQuantitativeProfile,
    WitnessDescriptor,
)
from creative_writer.source_evidence import (
    ValidationIssue,
    collect_leakage_issues,
    validate_leakage,
    validate_quantitative_profile,
)
from creative_writer.source_passages import read_passage_index


HASH = "a" * 64
CANONICAL_PROTOCOL_VALIDATION_BODY = (
    "# Validation Record\n\n"
    "## Protocol state\n\n"
    "The strict YAML front matter records the adopted protocol state. Freeze hashes,\n"
    "holdout results, control comparisons, reviewer findings, claim transitions,\n"
    "and the final profile fingerprint will be recorded only after their respective\n"
    "stages have occurred.\n"
)


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
                "tier-four",
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
                    4: ["tier-four role"],
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
        _retained_source(story, "tier-four", 4),
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
        _source_admission("tier-four", 4),
        {
            "id": "the-lost-world",
            "status": "excluded",
            "authority": {"tier": 5, "story_world_canon": False, "style_authority": "none"},
            "work": {"title": "The Lost World", "author": "Arthur Conan Doyle", "first_published": 1912},
            "analytical_roles": ["later diagnostic"],
            "permitted_uses": ["none"],
            "prohibited_uses": ["all"],
            "rationale": "Excluded outside-window tier-four source.",
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
    observations = story / "source-study/observations"
    observations.mkdir(parents=True)
    for source_id in ("wells-alpha", "selected-short-fiction"):
        (observations / f"{source_id}.md").write_text(
            "# Observation Dossier\n\n## Observations\n\n"
            "No reviewed observations are recorded at protocol status.\n",
            encoding="utf-8",
        )
    source_study = story / "source-study"
    (source_study / "evidence-ledger.yml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "study_id": "fixture-wells-phase-2b",
                "stage": "protocol",
                "mode": "descriptive",
                "claims": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (source_study / "quantitative-profile.yml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "study_id": "fixture-wells-phase-2b",
                "stage": "protocol",
                "generated_metrics": [],
                "witnesses": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (source_study / "wells-profile.md").write_text(
        "# Profile\n\n"
        + "\n\n".join(
            f"### {index}. {dimension['label']}\n\nNo reviewed descriptive synthesis is recorded at protocol status."
            for index, dimension in enumerate(_dimensions(), 1)
        )
        + "\n",
        encoding="utf-8",
    )
    (source_study / "period-controls.md").write_text(
        "# Period controls\n\nProtocol placeholder.\n", encoding="utf-8"
    )
    validation = {
        "schema_version": 1,
        "study_id": "fixture-wells-phase-2b",
        "stage": "protocol",
        "candidate_commit": None,
        "candidate_profile_sha256": None,
        "candidate_ledger_sha256": None,
        "holdout_summary": "Held-out material has not been opened at protocol stage.",
        "control_summary": "Tier 4 controls remain quarantined at protocol stage.",
        "reviewer_summary": "Independent review has not begun at protocol stage.",
        "claim_transitions": [],
        "unresolved_uncertainty": "No reviewed claim outcomes exist at protocol stage.",
        "final_profile_sha256": None,
    }
    (source_study / "validation.md").write_text(
        "---\n"
        + yaml.safe_dump(validation, sort_keys=False)
        + "---\n\n"
        + CANONICAL_PROTOCOL_VALIDATION_BODY,
        encoding="utf-8",
    )
    return story


def _fixture(root: Path) -> tuple[Path, object]:
    story = _write_fixture(root)
    result = run_source_analysis(root, "fixture", "prepare")
    return story, result


def _commit_fixture_holdouts(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "fixture@example.test"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
    subprocess.run(
        ["git", "add", "stories/fixture/source-study/holdouts.yml"], cwd=root, check=True
    )
    subprocess.run(["git", "commit", "-qm", "lock fixture holdouts"], cwd=root, check=True)


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
        "tier-four",
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
        "tier-four",
    ]
    assert [item["witness_ordinal"] for item in witnesses] == list(range(1, 7))


def test_holdout_manifest_has_all_fingerprints_and_quarantines_controls(tmp_path: Path) -> None:
    story, result = _fixture(tmp_path)
    manifest = yaml.safe_load((story / "source-study/holdouts.yml").read_text(encoding="utf-8"))

    assert set(manifest["registry_hashes"]) == {"source-study/admission.yml", "original/sources.yml"}
    assert set(manifest["source_fingerprints"]) == {
        "source/wells-alpha/epub",
        "source/selected-short-fiction/epub",
        "source/tier-four/epub",
        "witness/wells-alpha/markdown",
        "witness/selected-short-fiction/the-plattner-story/markdown",
        "witness/selected-short-fiction/the-sea-raiders/markdown",
        "witness/selected-short-fiction/the-crystal-egg/markdown",
        "witness/selected-short-fiction/the-star/markdown",
        "witness/tier-four/markdown",
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
    assert all("tier-four" not in item["witness_id"] for item in manifest["witnesses"])
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
        assert "tier-four" not in text
    report = (tmp_path / "build/fixture/source-study/development-report.md").read_text(
        encoding="utf-8"
    )
    assert "approximation" in report.lower()
    assert "pooled wells target" in report.lower()
    assert "Evidence validation diagnostics" in report
    assert "Blocking errors: **0**" in report
    assert "Warnings: **0**" in report


@pytest.mark.parametrize(
    "relative_path",
    [
        "source-study/evidence-ledger.yml",
        "source-study/quantitative-profile.yml",
        "source-study/wells-profile.md",
        "source-study/period-controls.md",
        "source-study/validation.md",
    ],
)
def test_develop_requires_every_canonical_evidence_artifact(
    tmp_path: Path, relative_path: str
) -> None:
    story, _ = _fixture(tmp_path)
    (story / relative_path).unlink()
    _commit_fixture_holdouts(tmp_path)

    with pytest.raises(CreativeWriterError, match="required|missing|artifact"):
        run_source_analysis(tmp_path, "fixture", "develop")


@pytest.mark.parametrize("relative_path", ["source-study/quantitative-profile.yml", "source-study/validation.md"])
def test_develop_binds_each_structured_artifact_to_analysis_study_id(
    tmp_path: Path, relative_path: str
) -> None:
    story, _ = _fixture(tmp_path)
    path = story / relative_path
    if path.suffix == ".yml":
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        payload["study_id"] = "wrong-study"
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    else:
        text = path.read_text(encoding="utf-8").replace(
            "study_id: fixture-wells-phase-2b", "study_id: wrong-study"
        )
        path.write_text(text, encoding="utf-8")
    _commit_fixture_holdouts(tmp_path)

    with pytest.raises(CreativeWriterError, match="study identity|study_id"):
        run_source_analysis(tmp_path, "fixture", "develop")


def test_develop_rejects_populated_protocol_ledger(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    config = _config_for_selection()
    claim = _fixture_claim(
        claim_id="protocol-populated",
        jurisdiction={
            "scope": "role_specific",
            "roles": ["fixture role"],
            "eligible_witness_ids": ["wells-alpha"],
        },
        classification="role_specific",
        support=[],
        search=None,
        status="rejected",
    )
    (story / "source-study/evidence-ledger.yml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "study_id": config.study_id,
                "stage": "protocol",
                "mode": "descriptive",
                "claims": [claim],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    _commit_fixture_holdouts(tmp_path)

    with pytest.raises(CreativeWriterError, match="(?i)populated protocol"):
        run_source_analysis(tmp_path, "fixture", "develop")


def test_develop_rejects_populated_protocol_validation_record(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    validation_path = story / "source-study/validation.md"
    validation = yaml.safe_load(
        validation_path.read_text(encoding="utf-8").split("---", 2)[1]
    )
    validation["claim_transitions"] = [
        {
            "claim_id": "protocol-claim",
            "from_status": "candidate",
            "to_status": "qualified",
            "reason": "A populated protocol transition must not be accepted.",
        }
    ]
    validation_path.write_text(
        "---\n" + yaml.safe_dump(validation, sort_keys=False) + "---\n\nProtocol state.\n",
        encoding="utf-8",
    )
    _commit_fixture_holdouts(tmp_path)

    with pytest.raises(CreativeWriterError, match="(?i)populated protocol"):
        run_source_analysis(tmp_path, "fixture", "develop")


@pytest.mark.parametrize(
    "mutation",
    [
        "holdout_summary",
        "control_summary",
        "reviewer_summary",
        "unresolved_uncertainty",
        "body",
    ],
)
def test_develop_rejects_substantive_protocol_validation_mutations(
    tmp_path: Path, mutation: str
) -> None:
    story, _ = _fixture(tmp_path)
    validation_path = story / "source-study/validation.md"
    validation_text = validation_path.read_text(encoding="utf-8")
    if mutation == "body":
        validation_text = validation_text.replace(
            "The strict YAML front matter records the adopted protocol state.",
            "The study concludes that the source has a distinctive structure.",
        )
    else:
        validation = yaml.safe_load(validation_text.split("---", 2)[1])
        validation[mutation] = "A substantive conclusion has been reviewed."
        validation_text = (
            "---\n"
            + yaml.safe_dump(validation, sort_keys=False)
            + "---\n\n"
            + CANONICAL_PROTOCOL_VALIDATION_BODY
        )
    validation_path.write_text(validation_text, encoding="utf-8")
    _commit_fixture_holdouts(tmp_path)

    with pytest.raises(CreativeWriterError, match="(?i)protocol validation"):
        run_source_analysis(tmp_path, "fixture", "develop")


def test_develop_rejects_protocol_validation_body_that_changes_only_line_content(
    tmp_path: Path,
) -> None:
    story, _ = _fixture(tmp_path)
    validation_path = story / "source-study/validation.md"
    validation_path.write_text(
        validation_path.read_text(encoding="utf-8").replace(
            "and the final profile fingerprint will be recorded only after their respective\n",
            "and the final profile fingerprint will be recorded only after all stages.\n",
        ),
        encoding="utf-8",
    )
    _commit_fixture_holdouts(tmp_path)

    with pytest.raises(CreativeWriterError, match="(?i)protocol validation"):
        run_source_analysis(tmp_path, "fixture", "develop")


def test_develop_accepts_protocol_body_line_endings_and_missing_final_newline(
    tmp_path: Path,
) -> None:
    story, _ = _fixture(tmp_path)
    validation_path = story / "source-study/validation.md"
    validation_text = validation_path.read_text(encoding="utf-8")
    validation_path.write_bytes(validation_text.replace("\n", "\r\n").rstrip("\r\n").encode("utf-8"))
    _commit_fixture_holdouts(tmp_path)

    result = run_source_analysis(tmp_path, "fixture", "develop")

    assert result.stage == "develop"


@pytest.mark.parametrize(
    ("configured_status", "mutation"),
    [
        ("development", "stage"),
        ("development", "summary"),
        ("development", "body"),
    ],
)
def test_develop_keeps_protocol_validation_seal_for_protocol_and_development_config(
    tmp_path: Path, configured_status: str, mutation: str
) -> None:
    story, _ = _fixture(tmp_path)
    config_path = story / "source-study/analysis.yml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["study_status"] = configured_status
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    validation_path = story / "source-study/validation.md"
    validation_text = validation_path.read_text(encoding="utf-8")
    if mutation == "stage":
        validation_text = validation_text.replace("stage: protocol", "stage: development")
    elif mutation == "summary":
        validation_text = validation_text.replace(
            "holdout_summary: Held-out material has not been opened at protocol stage.",
            "holdout_summary: A substantive conclusion was reviewed.",
        )
    else:
        validation_text = validation_text.replace(
            "The strict YAML front matter records the adopted protocol state.",
            "The study concludes that the source has a distinctive structure.",
        )
    validation_path.write_text(validation_text, encoding="utf-8")
    _commit_fixture_holdouts(tmp_path)

    with pytest.raises(CreativeWriterError, match="(?i)protocol validation|protocol stage"):
        run_source_analysis(tmp_path, "fixture", "develop")


def test_develop_recursively_scans_nested_observation_markdown_for_topology_and_leakage(
    tmp_path: Path,
) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    holdout = next(
        item for item in index if item.witness_id == "selected-short-fiction/the-star"
    )
    nested = story / "source-study/observations/archive/rogue.md"
    nested.parent.mkdir(parents=True)
    nested.write_text(
        f"archive/{holdout.witness_id}.md\n{holdout.passage_id}\n",
        encoding="utf-8",
    )
    _commit_fixture_holdouts(tmp_path)

    with pytest.raises(CreativeWriterError, match="(?i)topology|forbidden|passage ID"):
        run_source_analysis(tmp_path, "fixture", "develop")

    report = tmp_path / "build/fixture/source-study/development-report.md"
    report_text = report.read_text(encoding="utf-8")
    assert "Evidence validation diagnostics" in report_text
    assert "Blocking errors: **" in report_text


def test_leakage_id_boundaries_accept_locator_punctuation_but_reject_prefixes(
    tmp_path: Path,
) -> None:
    text = "one two three four five six seven eight nine"
    digest = hashlib.sha256(text.encode()).hexdigest()
    passage = PassageRecord(
        witness_id="holdout",
        witness_ordinal=1,
        source_id="holdout",
        selection_id=None,
        source_fingerprint=HASH,
        heading_path=["Heading"],
        heading_label="Heading",
        block_type="paragraph",
        source_ordinal=1,
        heading_ordinal=1,
        normalized_text=text,
        original_text=text,
        word_count=9,
        direct_dialogue="none",
        content_hash=digest,
        passage_id=f"holdout:heading:1:{digest[:12]}",
    )
    cases = {
        "witness-colon.md": "ref:holdout",
        "witness-slash.md": "archive/holdout.md",
        "passage-colon.md": f"ref:{passage.passage_id}",
        "passage-slash.md": f"archive/{passage.passage_id}.md",
    }
    for filename, content in cases.items():
        path = tmp_path / filename
        path.write_text(content, encoding="utf-8")
        result = collect_leakage_issues(
            [path], forbidden_witness_ids={"holdout"}, forbidden_passages=[passage]
        )
        assert result.errors, filename

    safe = tmp_path / "prefix.md"
    safe.write_text("holdout-extra holdout_extra holdout2", encoding="utf-8")
    assert not collect_leakage_issues(
        [safe], forbidden_witness_ids={"holdout"}, forbidden_passages=[passage]
    ).errors


def test_observation_heading_trailing_space_is_noncanonical_not_missing(
    tmp_path: Path,
) -> None:
    story, _ = _fixture(tmp_path)
    path = story / "source-study/observations/wells-alpha.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("## Observations\n", "## Observations   \n"),
        encoding="utf-8",
    )

    with pytest.raises(CreativeWriterError, match="(?i)canonical.*heading"):
        validate_observation_dossiers([path], read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl"), _config_for_selection())


def test_profile_heading_trailing_space_duplicate_is_rejected_deterministically(
    tmp_path: Path,
) -> None:
    story, _ = _fixture(tmp_path)
    config = _config_for_selection()
    profile = story / "source-study/wells-profile.md"
    profile_text = profile.read_text(encoding="utf-8").replace(
        "### 2. narrator-distance\n",
        "### 1. frame-architecture   \n\n#### Finding 1\nRogue finding.\n\n### 2. narrator-distance\n",
    )
    profile.write_text(profile_text, encoding="utf-8")
    ledger = EvidenceLedger.model_validate(
        {"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": []}
    )

    with pytest.raises(CreativeWriterError, match="(?i)duplicate.*dimension|canonical.*heading"):
        validate_profile_claim_links(profile, ledger, config, stage="development")


def test_develop_malformed_generated_json_writes_deterministic_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    story, _ = _fixture(tmp_path)
    config_path = story / "source-study/analysis.yml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["study_status"] = "development"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    _commit_fixture_holdouts(tmp_path)
    run_source_analysis(tmp_path, "fixture", "develop")

    config_model = load_yaml_model(config_path, AnalysisConfig)
    metrics_path = tmp_path / "build/fixture/source-study/development-metrics.json"
    csv_path = tmp_path / "build/fixture/source-study/development-metrics.csv"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    profile = _complete_quantitative_profile(config_model, metrics, metrics_path, csv_path)
    profile_path = story / "source-study/quantitative-profile.yml"
    profile_path.write_text(yaml.safe_dump(profile.model_dump(mode="json"), sort_keys=False), encoding="utf-8")

    original_measure_development = source_analysis.measure_development

    def mutate_metrics(*args: object, **kwargs: object) -> object:
        result = original_measure_development(*args, **kwargs)
        output_paths = kwargs["output_paths"]
        assert isinstance(output_paths, dict)
        generated = output_paths["development_metrics"]
        assert isinstance(generated, Path)
        generated.write_text("[]\n", encoding="utf-8")
        return result

    monkeypatch.setattr(source_analysis, "measure_development", mutate_metrics)
    reports: list[str] = []
    for _ in range(2):
        with pytest.raises(CreativeWriterError, match="(?i)JSON object|generated metric"):
            run_source_analysis(tmp_path, "fixture", "develop")
        report = tmp_path / "build/fixture/source-study/development-report.md"
        report_text = report.read_text(encoding="utf-8")
        assert "Evidence validation diagnostics" in report_text
        assert "Blocking errors: **1**" in report_text
        reports.append(report_text)
    assert reports[0] == reports[1]


@pytest.mark.parametrize(
    "mutation",
    ["witness_id", "source_id", "selection_id", "provenance", "witness_record"],
)
def test_develop_malformed_generated_metrics_with_empty_protocol_profile_writes_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    story, _ = _fixture(tmp_path)
    _commit_fixture_holdouts(tmp_path)
    metrics_path = tmp_path / "build/fixture/source-study/development-metrics.json"
    original_measure_development = source_analysis.measure_development

    def mutate_metrics(*args: object, **kwargs: object) -> object:
        result = original_measure_development(*args, **kwargs)
        document = json.loads(metrics_path.read_text(encoding="utf-8"))
        if mutation == "witness_id":
            document["witnesses"][0]["witness_id"] = []
        elif mutation == "source_id":
            document["witnesses"][0]["source_id"] = {}
        elif mutation == "selection_id":
            document["witnesses"][1]["selection_id"] = None
        elif mutation == "provenance":
            document["provenance"] = "malformed"
        else:
            document["witnesses"][0] = []
        metrics_path.write_text(json.dumps(document) + "\n", encoding="utf-8")
        return result

    monkeypatch.setattr(source_analysis, "measure_development", mutate_metrics)
    with pytest.raises(CreativeWriterError, match="(?i)generated development metric JSON|identity|provenance"):
        run_source_analysis(tmp_path, "fixture", "develop")

    report = tmp_path / "build/fixture/source-study/development-report.md"
    report_text = report.read_text(encoding="utf-8")
    assert "Evidence validation diagnostics" in report_text
    assert "Blocking errors: **" in report_text
    assert "Warnings: **0**" in report_text


@pytest.mark.parametrize(
    "mutation",
    [
        "empty_witnesses",
        "duplicate_witness",
        "stale_config_hash",
        "enabled_measurements_empty",
        "total_words_list",
        "malformed_nested_identity",
    ],
)
def test_develop_generated_metrics_mutations_with_empty_protocol_profile_write_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    story, _ = _fixture(tmp_path)
    _commit_fixture_holdouts(tmp_path)
    metrics_path = tmp_path / "build/fixture/source-study/development-metrics.json"
    original_measure_development = source_analysis.measure_development

    def mutate_metrics(*args: object, **kwargs: object) -> object:
        result = original_measure_development(*args, **kwargs)
        document = json.loads(metrics_path.read_text(encoding="utf-8"))
        if mutation == "empty_witnesses":
            document["witnesses"] = []
        elif mutation == "duplicate_witness":
            document["witnesses"].append(dict(document["witnesses"][0]))
        elif mutation == "stale_config_hash":
            document["config_sha256"] = "b" * 64
            document["provenance"]["config_sha256"] = "b" * 64
        elif mutation == "enabled_measurements_empty":
            document["enabled_measurements"] = []
        elif mutation == "total_words_list":
            document["witnesses"][0]["total_words"] = []
        else:
            document["witnesses"][0]["source_id"] = {"nested": "wells-alpha"}
        metrics_path.write_text(json.dumps(document) + "\n", encoding="utf-8")
        return result

    monkeypatch.setattr(source_analysis, "measure_development", mutate_metrics)
    with pytest.raises(CreativeWriterError, match="(?i)generated development metric JSON|identity|provenance|witness records"):
        run_source_analysis(tmp_path, "fixture", "develop")

    report = tmp_path / "build/fixture/source-study/development-report.md"
    report_text = report.read_text(encoding="utf-8")
    assert "Evidence validation diagnostics" in report_text
    assert "Blocking errors: **" in report_text
    assert "Warnings: **0**" in report_text


@pytest.mark.parametrize(
    "locator_template",
    [
        "ref:{passage_id}",
        "archive/{witness_id}.md",
        "ref:{witness_id}",
        "archive/{passage_id}.md",
    ],
)
def test_develop_rejects_each_forbidden_locator_form(
    tmp_path: Path, locator_template: str
) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    holdout = next(item for item in index if item.witness_id.endswith("/the-star"))
    controls = story / "source-study/period-controls.md"
    controls.write_text(
        controls.read_text(encoding="utf-8")
        + "\nForbidden locator: "
        + locator_template.format(
            passage_id=holdout.passage_id, witness_id=holdout.witness_id
        )
        + "\n",
        encoding="utf-8",
    )
    _commit_fixture_holdouts(tmp_path)

    with pytest.raises(CreativeWriterError, match="(?i)witness ID|passage ID|forbidden"):
        run_source_analysis(tmp_path, "fixture", "develop")

    report = tmp_path / "build/fixture/source-study/development-report.md"
    report_text = report.read_text(encoding="utf-8")
    assert "Evidence validation diagnostics" in report_text
    assert "Blocking errors: **" in report_text


def test_develop_blocks_registry_identity_absent_from_retained_registry_at_pipeline_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    story, _ = _fixture(tmp_path)
    source_path = story / "original/sources.yml"
    source_document = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    source_document["sources"] = [
        source
        for source in source_document["sources"]
        if source["id"] != "selected-short-fiction"
    ]
    source_path.write_text(yaml.safe_dump(source_document, sort_keys=False), encoding="utf-8")
    config_path = story / "source-study/analysis.yml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["source_registry"]["sha256"] = _sha256(source_path)
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    _commit_fixture_holdouts(tmp_path)

    called = False
    original_collect = source_analysis.collect_evidence_issues

    def capture_call(*args: object, **kwargs: object):
        nonlocal called
        called = True
        return original_collect(*args, **kwargs)

    monkeypatch.setattr(source_analysis, "collect_evidence_issues", capture_call)
    with pytest.raises(CreativeWriterError, match="Source admission failed"):
        run_source_analysis(tmp_path, "fixture", "develop")
    assert called is False


def test_develop_empty_protocol_profile_still_rejects_non_object_generated_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    story, _ = _fixture(tmp_path)
    _commit_fixture_holdouts(tmp_path)
    metrics_path = tmp_path / "build/fixture/source-study/development-metrics.json"
    original_measure_development = source_analysis.measure_development

    def mutate_metrics(*args: object, **kwargs: object) -> object:
        result = original_measure_development(*args, **kwargs)
        metrics_path.write_text("[]\n", encoding="utf-8")
        return result

    monkeypatch.setattr(source_analysis, "measure_development", mutate_metrics)
    with pytest.raises(CreativeWriterError, match="(?i)JSON object|generated metric"):
        run_source_analysis(tmp_path, "fixture", "develop")

    report = tmp_path / "build/fixture/source-study/development-report.md"
    report_text = report.read_text(encoding="utf-8")
    assert "Evidence validation diagnostics" in report_text
    assert "Blocking errors: **" in report_text
    assert "Warnings: **0**" in report_text


def test_eligible_witness_must_exercise_a_declared_claim_role(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["wells-alpha role"]
    admission, registry = _fixture_authority(story)
    alpha = next(item for item in index if item.witness_id == "wells-alpha")
    claim = _fixture_claim(
        claim_id="inflated-eligibility",
        jurisdiction={
            "scope": "role_specific",
            "roles": ["wells-alpha role"],
            "eligible_witness_ids": ["wells-alpha", "selected-short-fiction/the-plattner-story"],
        },
        classification="role_specific",
        support=[_fixture_reference(alpha)],
        search={
            "witness_ids": ["wells-alpha"],
            "dimensions": ["frame-architecture"],
            "method": "manual_close_reading",
            "coverage": "targeted",
            "searched_passage_ids": [alpha.passage_id],
            "outcome": "no_material_counterexample",
            "notes": "The targeted search found no material counterexample.",
        },
    )
    ledger = EvidenceLedger.model_validate(
        {"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]}
    )

    with pytest.raises(CreativeWriterError, match="(?i)eligible witness.*declared.*role"):
        validate_evidence_ledger(ledger, index, config=config, admission=admission, registry=registry)


def test_eligible_witness_must_be_an_explicitly_retained_registry_identity(
    tmp_path: Path,
) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["selected-short-fiction role"]
    admission, registry = _fixture_authority(story)
    registry.sources[:] = [
        source for source in registry.sources if source.id != "selected-short-fiction"
    ]
    selected = next(item for item in index if item.witness_id.endswith("/the-plattner-story"))
    claim = _fixture_claim(
        claim_id="unretained-eligibility",
        jurisdiction={
            "scope": "role_specific",
            "roles": ["selected-short-fiction role"],
            "eligible_witness_ids": [selected.witness_id],
        },
        classification="role_specific",
        support=[_fixture_reference(selected, 2)],
        search={
            "witness_ids": [selected.witness_id],
            "dimensions": ["frame-architecture"],
            "method": "manual_close_reading",
            "coverage": "targeted",
            "searched_passage_ids": [selected.passage_id],
            "outcome": "no_material_counterexample",
            "notes": "The targeted search found no material counterexample.",
        },
    )
    ledger = EvidenceLedger.model_validate(
        {
            "schema_version": 1,
            "study_id": config.study_id,
            "stage": "development",
            "mode": "descriptive",
            "claims": [claim],
        }
    )

    with pytest.raises(CreativeWriterError, match="(?i)retained authority|eligible witness"):
        validate_evidence_ledger(
            ledger, index, config=config, admission=admission, registry=registry
        )


def test_develop_passes_expanded_retained_registry_to_evidence_validator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    story, _ = _fixture(tmp_path)
    _commit_fixture_holdouts(tmp_path)
    seen: dict[str, SourcesRegistry] = {}
    original_collect = source_analysis.collect_evidence_issues

    def capture_registry(*args: object, **kwargs: object):
        registry = kwargs["registry"]
        assert isinstance(registry, SourcesRegistry)
        seen["registry"] = registry
        return original_collect(*args, **kwargs)

    monkeypatch.setattr(source_analysis, "collect_evidence_issues", capture_registry)
    run_source_analysis(tmp_path, "fixture", "develop")

    assert "registry" in seen
    retained = seen["registry"]
    selected_source = next(item for item in retained.sources if item.id == "selected-short-fiction")
    assert {item.id for item in selected_source.selections} == {
        "the-plattner-story",
        "the-sea-raiders",
        "the-crystal-egg",
        "the-star",
    }


def test_develop_rejects_forbidden_locator_with_prefix_boundary_mutation(
    tmp_path: Path,
) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    holdout = next(item for item in index if item.witness_id.endswith("/the-star"))
    controls = story / "source-study/period-controls.md"
    controls.write_text(
        controls.read_text(encoding="utf-8")
        + f"\nArchive locator: archive/{holdout.witness_id}.md\n",
        encoding="utf-8",
    )
    _commit_fixture_holdouts(tmp_path)

    with pytest.raises(CreativeWriterError, match="(?i)witness ID|forbidden"):
        run_source_analysis(tmp_path, "fixture", "develop")

    report = tmp_path / "build/fixture/source-study/development-report.md"
    report_text = report.read_text(encoding="utf-8")
    assert "Evidence validation diagnostics" in report_text
    assert "Blocking errors: **" in report_text


def test_develop_rejects_observation_trailing_space_duplicate_end_to_end(
    tmp_path: Path,
) -> None:
    story, _ = _fixture(tmp_path)
    path = story / "source-study/observations/wells-alpha.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "## Observations\n", "## Observations\n\n## Observations   \n", 1
        ),
        encoding="utf-8",
    )
    _commit_fixture_holdouts(tmp_path)

    with pytest.raises(CreativeWriterError, match="(?i)canonical|exactly one|observation"):
        run_source_analysis(tmp_path, "fixture", "develop")

    report = tmp_path / "build/fixture/source-study/development-report.md"
    report_text = report.read_text(encoding="utf-8")
    assert "Evidence validation diagnostics" in report_text
    assert "Blocking errors: **" in report_text


def test_develop_rejects_profile_trailing_space_duplicate_end_to_end(
    tmp_path: Path,
) -> None:
    story, _ = _fixture(tmp_path)
    profile = story / "source-study/wells-profile.md"
    profile.write_text(
        profile.read_text(encoding="utf-8").replace(
            "### 2. narrator-distance\n",
            "### 1. frame-architecture   \n\n### 2. narrator-distance\n",
            1,
        ),
        encoding="utf-8",
    )
    _commit_fixture_holdouts(tmp_path)

    with pytest.raises(CreativeWriterError, match="(?i)duplicate|canonical|profile"):
        run_source_analysis(tmp_path, "fixture", "develop")

    report = tmp_path / "build/fixture/source-study/development-report.md"
    report_text = report.read_text(encoding="utf-8")
    assert "Evidence validation diagnostics" in report_text
    assert "Blocking errors: **" in report_text


def test_develop_writes_diagnostics_when_ledger_schema_read_fails_after_metrics(
    tmp_path: Path,
) -> None:
    story, _ = _fixture(tmp_path)
    (story / "source-study/evidence-ledger.yml").write_text(
        "schema_version: 1\nstudy_id: fixture-wells-phase-2b\nstage: protocol\nclaims: [\n",
        encoding="utf-8",
    )
    _commit_fixture_holdouts(tmp_path)

    with pytest.raises(CreativeWriterError, match="evidence-ledger|YAML|validation"):
        run_source_analysis(tmp_path, "fixture", "develop")
    report = tmp_path / "build/fixture/source-study/development-report.md"
    report_text = report.read_text(encoding="utf-8")
    assert "Evidence validation diagnostics" in report_text
    assert "Blocking errors: **1**" in report_text
    assert "locator" not in report_text


@pytest.mark.parametrize("failure", ["schema", "read"])
def test_develop_writes_diagnostics_when_validation_schema_or_read_fails_after_metrics(
    tmp_path: Path, failure: str
) -> None:
    story, _ = _fixture(tmp_path)
    validation_path = story / "source-study/validation.md"
    if failure == "schema":
        validation_path.write_text(
            "---\nschema_version: 1\nstudy_id: fixture-wells-phase-2b\nstage: protocol\n---\n\n"
            + CANONICAL_PROTOCOL_VALIDATION_BODY,
            encoding="utf-8",
        )
    else:
        validation_path.unlink()
        validation_path.mkdir()
    _commit_fixture_holdouts(tmp_path)

    with pytest.raises((CreativeWriterError, OSError), match="validation|ValidationRecord|read|directory"):
        run_source_analysis(tmp_path, "fixture", "develop")

    report = tmp_path / "build/fixture/source-study/development-report.md"
    report_text = report.read_text(encoding="utf-8")
    assert "Evidence validation diagnostics" in report_text
    assert "Blocking errors: **1**" in report_text
    assert "Warnings: **0**" in report_text
    assert "locator" not in report_text


@pytest.mark.parametrize("artifact", ["profile", "observation"])
def test_develop_writes_diagnostics_when_profile_or_observation_grammar_fails(
    tmp_path: Path, artifact: str
) -> None:
    story, _ = _fixture(tmp_path)
    if artifact == "profile":
        path = story / "source-study/wells-profile.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "No reviewed descriptive synthesis is recorded at protocol status.",
                "Rogue profile prose.",
                1,
            ),
            encoding="utf-8",
        )
    else:
        path = story / "source-study/observations/wells-alpha.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "No reviewed observations are recorded at protocol status.",
                "Rogue observation prose.",
                1,
            ),
            encoding="utf-8",
        )
    _commit_fixture_holdouts(tmp_path)

    with pytest.raises(CreativeWriterError, match="(?i)validation|profile|observation"):
        run_source_analysis(tmp_path, "fixture", "develop")

    report = tmp_path / "build/fixture/source-study/development-report.md"
    report_text = report.read_text(encoding="utf-8")
    assert "Evidence validation diagnostics" in report_text
    assert "Blocking errors: **1**" in report_text
    assert "Warnings: **0**" in report_text
    assert "locator" not in report_text


def test_develop_reparses_and_rejects_index_direct_dialogue_drift(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index_path = tmp_path / "build/fixture/source-study/passage-index.jsonl"
    lines = index_path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    first["direct_dialogue"] = "unknown" if first["direct_dialogue"] != "unknown" else "none"
    lines[0] = json.dumps(first, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

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

    with pytest.raises(CreativeWriterError, match="reparsed.*passage index|canonical.*differs"):
        run_source_analysis(tmp_path, "fixture", "develop")


def _observation_markdown(passage_id: str, *, comparison: str | None = None) -> str:
    comparison = comparison or passage_id
    return f"""# Observation Dossier: Wells Alpha

## Observations

### Observation 1

#### Passage
- `{passage_id}`

#### Observation
The passage contains a directly observable fixture event.

#### Inference
The event supports a bounded fixture inference.

#### Jurisdiction
- Dimension: `frame-architecture`
- Role: `fixture role`

#### Comparison
- related: `{comparison}` — The comparison preserves the same bounded context.

#### Limitation
This observation is local to the cited passage and witness.

#### Candidate claims
None.
"""


def test_observation_validator_enforces_exact_grammar_and_resolves_locators(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    first = next(item for item in index if item.witness_id == "wells-alpha")
    path = story / "source-study/observations/wells-alpha.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_observation_markdown(first.passage_id).replace("fixture role", "wells-alpha role"), encoding="utf-8")
    admission, registry = _fixture_authority(story)
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["wells-alpha role"]

    result = validate_observation_dossiers(
        [path],
        index,
        config,
        stage="development",
        admission=admission,
        registry=registry,
        development_passage_ids={first.passage_id},
    )

    assert not result.errors
    assert not result.warnings


def test_observation_validator_blocks_unknown_and_holdout_locators_with_diagnostics(
    tmp_path: Path,
) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    alpha = [item for item in index if item.witness_id == "wells-alpha"]
    path = story / "source-study/observations/wells-alpha.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _observation_markdown(
            alpha[-1].passage_id,
            comparison="wells-alpha:missing:1:" + "a" * 12,
        ),
        encoding="utf-8",
    )
    admission, registry = _fixture_authority(story)
    with pytest.raises(CreativeWriterError) as caught:
        validate_observation_dossiers(
            [path],
            index,
            _config_for_selection(),
            stage="development",
            development_passage_ids={item.passage_id for item in alpha[:-1]},
            admission=admission,
            registry=registry,
        )
    message = str(caught.value)
    assert "wells-alpha.md" in message
    assert "missing" in message
    assert "held-out" in message


def test_profile_validator_accepts_protocol_placeholder_and_warns_on_development_orphan(
    tmp_path: Path,
) -> None:
    story, _ = _fixture(tmp_path)
    config = _config_for_selection()
    profile = story / "source-study/wells-profile.md"
    profile.write_text(
        "# Profile\n\n"
        + "\n\n".join(
            f"### {i}. {dimension.label}\n\nProtocol placeholder."
            for i, dimension in enumerate(config.dimensions, 1)
        )
        + "\n",
        encoding="utf-8",
    )
    empty = EvidenceLedger.model_validate(
        {"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": []}
    )
    result = validate_profile_claim_links(profile, empty, config, stage="development")
    assert not result.errors


def test_profile_validator_accepts_contiguous_findings_and_links_existing_claims(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    config = _config_for_selection()
    ledger = EvidenceLedger.model_validate(
        {
            "schema_version": 1,
            "study_id": config.study_id,
            "stage": "development",
            "mode": "descriptive",
            "claims": [{
                "id": "frame-claim",
                "dimension": "frame-architecture",
                "statement": "A bounded frame is present.",
                "jurisdiction": {"scope": "role_specific", "roles": ["fixture role"], "eligible_witness_ids": ["wells-alpha"]},
                "classification": "role_specific",
                "status": "rejected",
                "confidence": "tentative",
                "supporting_passages": [],
                "counterexample_passages": [],
                "counterexample_search": None,
                "control_results": [],
                "scope_and_limits": "Fixture limit.",
                "validation_expectation": "Fixture expectation.",
                "prohibited_overgeneralisation": "Fixture prohibition.",
                "notes": "Fixture.",
            }],
        }
    )
    profile = story / "source-study/wells-profile.md"
    profile.write_text(_profile_with_fields(config, "frame-claim"), encoding="utf-8")
    assert validate_profile_claim_links(profile, ledger, config, stage="development").ok


def test_evidence_validator_aggregates_authority_and_locator_diagnostics(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    alpha = next(item for item in index if item.witness_id == "wells-alpha")
    ledger = {
        "schema_version": 1,
        "study_id": "fixture-wells-phase-2b",
        "stage": "development",
        "mode": "descriptive",
        "claims": [{
            "id": "bad-claim",
            "dimension": "frame-architecture",
            "statement": "This always holds.",
            "jurisdiction": {"scope": "cross_work", "roles": ["fixture role"], "eligible_witness_ids": ["wells-alpha"]},
            "classification": "wells_distinctive",
            "status": "candidate",
            "confidence": "tentative",
            "supporting_passages": [{
                "witness_id": "wells-alpha", "source_id": "wells-alpha", "selection_id": None,
                "passage_id": alpha.passage_id, "authority_tier": 1, "evidence_role": "support",
                "relevance_note": "support",
            }],
            "counterexample_passages": [],
            "counterexample_search": {
                "witness_ids": ["wells-alpha"], "dimensions": ["frame-architecture"],
                "method": "manual_close_reading", "coverage": "targeted",
                "searched_passage_ids": [alpha.passage_id], "outcome": "no_material_counterexample",
                "notes": "search",
            },
            "control_results": [],
            "scope_and_limits": "bounded scope",
            "validation_expectation": "unseen witness",
            "prohibited_overgeneralisation": "not universal",
            "notes": "fixture",
        }],
    }
    parsed = EvidenceLedger.model_validate(ledger)
    with pytest.raises(CreativeWriterError) as caught:
        validate_evidence_ledger(parsed, index, config=_config_for_selection(), stage="development")
    message = str(caught.value)
    assert "bad-claim" in message
    assert "at least two Wells witnesses" in message
    assert "fixture role" in message


def test_profile_and_observation_results_use_validation_issue_records() -> None:
    issue = ValidationIssue("warning", "file.md", "claim", "locator", "diagnostic")
    assert issue.severity == "warning"


def test_quantitative_profile_checks_current_metric_provenance_and_witness_set(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "stories/fixture/source-study/holdouts.yml"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "lock fixture holdouts"], cwd=tmp_path, check=True)
    run_source_analysis(tmp_path, "fixture", "develop")
    metrics_path = tmp_path / "build/fixture/source-study/development-metrics.json"
    config = _config_for_selection()
    config.study_status = "development"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    witnesses = [
        WitnessQuantitativeProfile(
            witness_id=item["witness_id"],
            source_id=item["source_id"],
            selection_id=item["selection_id"],
            values={"total_words": item["total_words"]},
            variation="Fixture variation.",
            limitations="Fixture limitation.",
            interpretive_relevance="Fixture relevance.",
        )
        for item in metrics["witnesses"]
    ]
    profile = QuantitativeProfile(
        schema_version=1,
        study_id=config.study_id,
        stage="development",
        generated_metrics=[
            MetricReference(
                id="development-metrics",
                path="build/fixture/source-study/development-metrics.json",
                sha256=_sha256(metrics_path),
            )
            ,
            MetricReference(
                id="development-metrics-csv",
                path="build/fixture/source-study/development-metrics.csv",
                sha256=_sha256(tmp_path / "build/fixture/source-study/development-metrics.csv"),
            )
        ],
        witnesses=witnesses,
    )
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    development_ids = {
        passage.passage_id
        for passage in index
        if passage.witness_id in {item.witness_id for item in witnesses}
    }
    validate_quantitative_profile(
        profile,
        root=tmp_path,
        metrics_path=metrics_path,
        metrics_csv_path=tmp_path / "build/fixture/source-study/development-metrics.csv",
        config=config,
        passages=index,
        development_witness_ids={item.witness_id for item in witnesses},
    )
    profile.generated_metrics[0].sha256 = "0" * 64
    with pytest.raises(CreativeWriterError, match="fingerprint is stale"):
        validate_quantitative_profile(
            profile,
            root=tmp_path,
            metrics_path=metrics_path,
            config=config,
            passages=index,
            development_witness_ids={item.witness_id for item in witnesses},
        )
    assert development_ids


def test_leakage_checker_uses_documented_minimum_token_rule(tmp_path: Path) -> None:
    text = "The quiet witness recorded eight ordinary words for the test."
    digest = hashlib.sha256(text.encode()).hexdigest()
    index = [PassageRecord(
        witness_id="forbidden",
        witness_ordinal=1,
        source_id="forbidden",
        selection_id=None,
        source_fingerprint=HASH,
        heading_path=["Heading"],
        heading_label="Heading",
        block_type="paragraph",
        source_ordinal=1,
        heading_ordinal=1,
        normalized_text=text,
        original_text=text,
        word_count=len(text.split()),
        direct_dialogue="none",
        content_hash=digest,
        passage_id=f"forbidden:heading:1:{digest[:12]}",
    )]
    path = tmp_path / "ledger.yml"
    path.write_text(text + "\n", encoding="utf-8")
    with pytest.raises(CreativeWriterError, match="full normalized"):
        validate_leakage(
            [path],
            forbidden_witness_ids={"forbidden"},
            forbidden_passages=index,
        )


def _fixture_authority(story: Path) -> tuple[SourceStudyAdmission, SourcesRegistry]:
    return (
        load_yaml_model(story / "source-study/admission.yml", SourceStudyAdmission),
        load_yaml_model(story / "original/sources.yml", SourcesRegistry),
    )


def _fixture_claim(
    *,
    claim_id: str,
    jurisdiction: dict[str, object],
    classification: str,
    support: list[dict[str, object]],
    search: dict[str, object] | None,
    status: str = "candidate",
) -> dict[str, object]:
    return {
        "id": claim_id,
        "dimension": "frame-architecture",
        "statement": "The bounded fixture account uses a declared frame.",
        "jurisdiction": jurisdiction,
        "classification": classification,
        "status": status,
        "confidence": "tentative",
        "supporting_passages": support,
        "counterexample_passages": [],
        "counterexample_search": search,
        "control_results": [],
        "scope_and_limits": "The claim is bounded to the declared jurisdiction.",
        "validation_expectation": "Presence in an unseen role-matched passage.",
        "prohibited_overgeneralisation": "It does not describe all prose.",
        "notes": "Fixture evidence.",
    }


def _fixture_reference(passage: PassageRecord, tier: int = 1) -> dict[str, object]:
    return {
        "witness_id": passage.witness_id,
        "source_id": passage.source_id,
        "selection_id": passage.selection_id,
        "passage_id": passage.passage_id,
        "authority_tier": tier,
        "evidence_role": "support",
        "relevance_note": "Fixture support.",
    }


def test_evidence_validator_accepts_role_specific_claim_and_documented_search(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    manifest = yaml.safe_load((story / "source-study/holdouts.yml").read_text(encoding="utf-8"))
    manifest_model = HoldoutManifest.model_validate(manifest)
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["wells-alpha role"]
    admission, registry = _fixture_authority(story)
    alpha = next(item for item in index if item.witness_id == "wells-alpha" and item.passage_id in {
        passage_id
        for witness in manifest_model.witnesses
        for window in witness.development_windows
        for passage_id in window.passage_ids
    })
    claim = _fixture_claim(
        claim_id="role-claim",
        jurisdiction={"scope": "role_specific", "roles": ["wells-alpha role"], "eligible_witness_ids": ["wells-alpha"]},
        classification="role_specific",
        support=[_fixture_reference(alpha)],
        search={
            "witness_ids": ["wells-alpha"], "dimensions": ["frame-architecture"],
            "method": "manual_close_reading", "coverage": "targeted",
            "searched_passage_ids": [alpha.passage_id], "outcome": "no_material_counterexample",
            "notes": "The targeted search found no material counterexample.",
        },
    )
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]})
    result = validate_evidence_ledger(
        ledger,
        index,
        config=config,
        admission=admission,
        registry=registry,
        manifest=manifest_model,
        development_passage_ids={
            passage_id
            for witness in manifest_model.witnesses
            for window in witness.development_windows
            for passage_id in window.passage_ids
        },
    )
    assert result.ok


def test_evidence_validator_accepts_time_machine_continuity_claim(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["continuity"]
    admission, registry = _fixture_authority(story)
    admission.sources[0].analytical_roles.append("continuity")
    time_machine = next(item for item in index if item.witness_id == "wells-alpha")
    claim = _fixture_claim(
        claim_id="continuity-claim",
        jurisdiction={"scope": "continuity", "roles": ["continuity"], "eligible_witness_ids": ["wells-alpha"]},
        classification="role_specific",
        support=[_fixture_reference(time_machine)],
        search={
            "witness_ids": ["wells-alpha"], "dimensions": ["frame-architecture"],
            "method": "manual_close_reading", "coverage": "targeted",
            "searched_passage_ids": [time_machine.passage_id], "outcome": "no_material_counterexample",
            "notes": "The targeted search found no material counterexample.",
        },
    )
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]})
    assert validate_evidence_ledger(ledger, index, config=config, admission=admission, registry=registry).ok


def test_evidence_validator_accepts_two_witness_cross_work_omnibus_disclosure(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["selected-short-fiction role"]
    admission, registry = _fixture_authority(story)
    first = next(item for item in index if item.witness_id.endswith("/the-plattner-story"))
    second = next(item for item in index if item.witness_id.endswith("/the-sea-raiders"))
    claim = _fixture_claim(
        claim_id="cross-work-claim",
        jurisdiction={"scope": "cross_work", "roles": ["selected-short-fiction role"], "eligible_witness_ids": [first.witness_id, second.witness_id]},
        classification="wells_distinctive",
        support=[_fixture_reference(first, 2), _fixture_reference(second, 2)],
        search={
            "witness_ids": [first.witness_id, second.witness_id], "dimensions": ["frame-architecture"],
            "method": "manual_close_reading", "coverage": "targeted",
            "searched_passage_ids": [first.passage_id, second.passage_id], "outcome": "no_material_counterexample",
            "notes": "The targeted search found no material counterexample.",
        },
    )
    claim["notes"] = "Omnibus dependence: selected stories share one retained edition."
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]})
    assert validate_evidence_ledger(ledger, index, config=config, admission=admission, registry=registry).ok


def test_rejected_claim_is_retained_without_support(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["wells-alpha role"]
    admission, registry = _fixture_authority(story)
    claim = _fixture_claim(
        claim_id="rejected-claim",
        jurisdiction={"scope": "role_specific", "roles": ["wells-alpha role"], "eligible_witness_ids": ["wells-alpha"]},
        classification="unsupported",
        support=[],
        search=None,
        status="rejected",
    )
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]})
    assert validate_evidence_ledger(ledger, index, config=config, admission=admission, registry=registry).ok


def test_populated_observation_validation_requires_admission_and_registry(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    focal = next(item for item in index if item.witness_id == "wells-alpha")
    path = story / "source-study/observations/wells-alpha.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_observation_markdown(focal.passage_id), encoding="utf-8")

    with pytest.raises(CreativeWriterError, match="admission.*registry"):
        validate_observation_dossiers(
            [path], index, _config_for_selection(), stage="development",
            development_passage_ids={focal.passage_id},
        )


def test_observation_focal_and_comparison_witnesses_must_have_dimension_role(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    focal = next(item for item in index if item.witness_id == "wells-alpha")
    comparison = next(item for item in index if item.witness_id.endswith("/the-plattner-story"))
    path = story / "source-study/observations/wells-alpha.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_observation_markdown(focal.passage_id, comparison=comparison.passage_id), encoding="utf-8")
    admission, registry = _fixture_authority(story)
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["fixture role"]

    with pytest.raises(CreativeWriterError, match="(?i)focal witness.*role"):
        validate_observation_dossiers(
            [path], index, config, stage="development",
            admission=admission, registry=registry,
            development_passage_ids={focal.passage_id, comparison.passage_id},
        )


def test_ledger_requires_each_support_witness_to_exercise_declared_role(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["selected-short-fiction role"]
    admission, registry = _fixture_authority(story)
    first = next(item for item in index if item.witness_id == "wells-alpha")
    second = next(item for item in index if item.witness_id.endswith("/the-plattner-story"))
    claim = _fixture_claim(
        claim_id="per-witness-role",
        jurisdiction={"scope": "cross_work", "roles": ["selected-short-fiction role"], "eligible_witness_ids": [first.witness_id, second.witness_id]},
        classification="wells_distinctive",
        support=[_fixture_reference(first), _fixture_reference(second, 2)],
        search={
            "witness_ids": [first.witness_id, second.witness_id], "dimensions": ["frame-architecture"],
            "method": "manual_close_reading", "coverage": "targeted",
            "searched_passage_ids": [first.passage_id, second.passage_id], "outcome": "no_material_counterexample",
            "notes": "The targeted search covered both witnesses.",
        },
    )
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]})

    with pytest.raises(CreativeWriterError, match="(?i)each supporting witness.*declared.*role"):
        validate_evidence_ledger(ledger, index, config=config, admission=admission, registry=registry, file=story / "source-study/evidence-ledger.yml")


def test_ledger_counterexample_witness_must_match_claim_dimension_role(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["wells-alpha role"]
    admission, registry = _fixture_authority(story)
    support = next(item for item in index if item.witness_id == "wells-alpha")
    contrary = next(item for item in index if item.witness_id.endswith("/the-plattner-story"))
    counterexample = _fixture_reference(contrary, 2)
    counterexample["evidence_role"] = "counterexample"
    claim = _fixture_claim(
        claim_id="counterexample-role",
        jurisdiction={"scope": "role_specific", "roles": ["wells-alpha role"], "eligible_witness_ids": ["wells-alpha"]},
        classification="role_specific", support=[_fixture_reference(support)], search=None,
    )
    claim["counterexample_passages"] = [counterexample]
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]})

    with pytest.raises(CreativeWriterError, match="(?i)counterexample.*declared jurisdiction role"):
        validate_evidence_ledger(ledger, index, config=config, admission=admission, registry=registry)


def test_counterexample_reference_must_use_claim_jurisdiction_role(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["wells-alpha role", "selected-short-fiction role"]
    admission, registry = _fixture_authority(story)
    support = next(item for item in index if item.witness_id == "wells-alpha")
    contrary = next(item for item in index if item.witness_id.endswith("/the-plattner-story"))
    counterexample = _fixture_reference(contrary, 2)
    counterexample["evidence_role"] = "counterexample"
    claim = _fixture_claim(
        claim_id="counterexample-jurisdiction-role",
        jurisdiction={
            "scope": "role_specific",
            "roles": ["wells-alpha role"],
            "eligible_witness_ids": [support.witness_id, contrary.witness_id],
        },
        classification="role_specific",
        support=[_fixture_reference(support)],
        search=None,
    )
    claim["counterexample_passages"] = [counterexample]
    ledger = EvidenceLedger.model_validate(
        {
            "schema_version": 1,
            "study_id": config.study_id,
            "stage": "development",
            "mode": "descriptive",
            "claims": [claim],
        }
    )

    with pytest.raises(CreativeWriterError, match="declared jurisdiction role"):
        validate_evidence_ledger(ledger, index, config=config, admission=admission, registry=registry)


def test_counterexample_search_must_use_claim_jurisdiction_role(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["wells-alpha role", "selected-short-fiction role"]
    admission, registry = _fixture_authority(story)
    support = next(item for item in index if item.witness_id == "wells-alpha")
    searched = next(item for item in index if item.witness_id.endswith("/the-plattner-story"))
    claim = _fixture_claim(
        claim_id="counterexample-search-jurisdiction-role",
        jurisdiction={
            "scope": "role_specific",
            "roles": ["wells-alpha role"],
            "eligible_witness_ids": [support.witness_id, searched.witness_id],
        },
        classification="role_specific",
        support=[_fixture_reference(support)],
        search={
            "witness_ids": [searched.witness_id],
            "dimensions": ["frame-architecture"],
            "method": "manual_close_reading",
            "coverage": "targeted",
            "searched_passage_ids": [searched.passage_id],
            "outcome": "no_material_counterexample",
            "notes": "The bounded search was performed.",
        },
    )
    ledger = EvidenceLedger.model_validate(
        {
            "schema_version": 1,
            "study_id": config.study_id,
            "stage": "development",
            "mode": "descriptive",
            "claims": [claim],
        }
    )

    with pytest.raises(CreativeWriterError, match="declared jurisdiction role"):
        validate_evidence_ledger(ledger, index, config=config, admission=admission, registry=registry)


def test_ledger_diagnostics_retain_file_path_for_identity_failures(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["wells-alpha role"]
    admission, registry = _fixture_authority(story)
    passage = next(item for item in index if item.witness_id == "wells-alpha")
    reference = _fixture_reference(passage)
    reference["passage_id"] = "wells-alpha:stale:1:" + "0" * 12
    claim = _fixture_claim(
        claim_id="stale-reference",
        jurisdiction={"scope": "role_specific", "roles": ["wells-alpha role"], "eligible_witness_ids": ["wells-alpha"]},
        classification="role_specific", support=[reference], search=None,
        status="rejected",
    )
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]})
    with pytest.raises(CreativeWriterError) as caught:
        validate_evidence_ledger(ledger, index, config=config, admission=admission, registry=registry, file=story / "source-study/evidence-ledger.yml")
    assert "evidence-ledger.yml" in str(caught.value)


def test_ledger_study_identity_must_match_configuration(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    config = _config_for_selection()
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": "other-study", "stage": "development", "mode": "descriptive", "claims": []})
    with pytest.raises(CreativeWriterError, match="study identity"):
        validate_evidence_ledger(ledger, index, config=config, file=story / "source-study/evidence-ledger.yml")


def test_omnibus_dependence_requires_content_after_prefix(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["selected-short-fiction role"]
    admission, registry = _fixture_authority(story)
    first = next(item for item in index if item.witness_id.endswith("/the-plattner-story"))
    second = next(item for item in index if item.witness_id.endswith("/the-sea-raiders"))
    claim = _fixture_claim(
        claim_id="empty-omnibus-note",
        jurisdiction={"scope": "cross_work", "roles": ["selected-short-fiction role"], "eligible_witness_ids": [first.witness_id, second.witness_id]},
        classification="wells_distinctive",
        support=[_fixture_reference(first, 2), _fixture_reference(second, 2)],
        search={
            "witness_ids": [first.witness_id, second.witness_id], "dimensions": ["frame-architecture"],
            "method": "manual_close_reading", "coverage": "targeted", "searched_passage_ids": [first.passage_id, second.passage_id],
            "outcome": "no_material_counterexample", "notes": "The targeted search covered both witnesses.",
        },
    )
    claim["notes"] = "Omnibus dependence:"
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]})
    with pytest.raises(CreativeWriterError, match="Omnibus dependence"):
        validate_evidence_ledger(ledger, index, config=config, admission=admission, registry=registry)


def test_observation_grammar_rejects_stray_prefix_and_unknown_heading(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    focal = next(item for item in index if item.witness_id == "wells-alpha")
    path = story / "source-study/observations/wells-alpha.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = _observation_markdown(focal.passage_id).replace(
        "### Observation 1", "Stray prefix.\n\n### Observation 1\n\n#### Unknown\nstray"
    )
    path.write_text(content, encoding="utf-8")
    with pytest.raises(CreativeWriterError, match="stray|ordered"):
        validate_observation_dossiers([path], index, _config_for_selection(), stage="development", development_passage_ids={focal.passage_id})


def test_observation_validator_rejects_duplicate_observations_sections(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    focal = next(item for item in index if item.witness_id == "wells-alpha")
    path = story / "source-study/observations/wells-alpha.md"
    path.write_text(
        _observation_markdown(focal.passage_id).replace("fixture role", "wells-alpha role")
        + "\n## Observations\n\nNo reviewed observations are recorded at protocol status.\n",
        encoding="utf-8",
    )
    admission, registry = _fixture_authority(story)
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["wells-alpha role"]

    with pytest.raises(CreativeWriterError, match="duplicate|exactly one"):
        validate_observation_dossiers(
            [path],
            index,
            config,
            stage="development",
            admission=admission,
            registry=registry,
            development_passage_ids={focal.passage_id},
        )


def test_observation_validator_rejects_unbackticked_claim_ids(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    focal = next(item for item in index if item.witness_id == "wells-alpha")
    path = story / "source-study/observations/wells-alpha.md"
    path.write_text(
        _observation_markdown(focal.passage_id)
        .replace("fixture role", "wells-alpha role")
        .replace("None.", "- claim-one"),
        encoding="utf-8",
    )
    admission, registry = _fixture_authority(story)
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["wells-alpha role"]

    with pytest.raises(CreativeWriterError, match="claim-ID bullets|backticked"):
        validate_observation_dossiers(
            [path],
            index,
            config,
            stage="development",
            admission=admission,
            registry=registry,
            development_passage_ids={focal.passage_id},
            claim_ids={"claim-one"},
        )


def test_observation_comparison_must_use_declared_role_not_dimension_role(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    focal = next(item for item in index if item.witness_id.endswith("/the-plattner-story"))
    comparison = next(item for item in index if item.witness_id == "wells-alpha")
    admission, registry = _fixture_authority(story)
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["fixture role", "wells-alpha role"]
    path = story / "source-study/observations/selected-short-fiction.md"
    path.write_text(
        _observation_markdown(focal.passage_id, comparison=comparison.passage_id),
        encoding="utf-8",
    )

    with pytest.raises(CreativeWriterError, match="declared jurisdiction role"):
        validate_observation_dossiers(
            [path],
            index,
            config,
            stage="development",
            admission=admission,
            registry=registry,
            development_passage_ids={focal.passage_id, comparison.passage_id},
        )


def test_observation_grammar_accepts_backticked_claim_ids_and_multiple_entries(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    first = next(item for item in index if item.witness_id == "wells-alpha")
    second = next(item for item in index if item.witness_id == "wells-alpha" and item.passage_id != first.passage_id)
    path = story / "source-study/observations/wells-alpha.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _observation_markdown(first.passage_id).replace("fixture role", "wells-alpha role").replace("None.", "- `claim-one`\n- `claim-two`")
    second_body = _observation_markdown(second.passage_id).replace("fixture role", "wells-alpha role").split("### Observation 1\n\n", 1)[1].replace("None.", "- `claim-three`")
    text = text.replace("\n\n", "\n\n", 1) + "\n### Observation 2\n\n" + second_body
    path.write_text(text, encoding="utf-8")
    admission, registry = _fixture_authority(story)
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["wells-alpha role"]
    result = validate_observation_dossiers([path], index, config, stage="development", admission=admission, registry=registry, development_passage_ids={first.passage_id, second.passage_id}, claim_ids={"claim-one", "claim-two", "claim-three"})
    assert result.ok


def _profile_with_fields(config: AnalysisConfig, claim_id: str, *, absolute: bool = False, deferred_control: bool = True) -> str:
    finding = "The finding is bounded and descriptive."
    if absolute:
        finding = "The finding always holds."
    field_values = {
        "Claim IDs": f"- `{claim_id}`",
        "Finding": finding,
        "Classification and confidence": "Classification: `role_specific`\nConfidence: `tentative`",
        "Jurisdiction": "The finding is limited to the configured dimension and witness role.",
        "Evidence": "Representative evidence is retained in the ledger.",
        "Variation and counterexamples": "Variation and counterexamples are recorded in the ledger.",
        "Quantitative context": "The current metric context is descriptive and per witness.",
        "Control distinction": "Deferred until validation." if deferred_control else "The control comparison remains distinct.",
        "Unresolved uncertainty": "The finding remains uncertain outside the declared scope.",
    }
    fields = "\n\n".join(f"##### {name}\n{value}" for name, value in field_values.items())
    sections = [f"### {i}. {dimension.label}\n\n" + (f"#### Finding 1\n\n{fields}" if i == 1 else "Protocol placeholder.") for i, dimension in enumerate(config.dimensions, 1)]
    return "# Profile\n\n" + "\n\n".join(sections) + "\n"


def test_profile_finding_requires_exact_ordered_fields_and_backticked_links(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    config = _config_for_selection()
    claim = _fixture_claim(
        claim_id="profile-claim",
        jurisdiction={"scope": "role_specific", "roles": ["wells-alpha role"], "eligible_witness_ids": ["wells-alpha"]},
        classification="role_specific", support=[], search=None, status="rejected",
    )
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]})
    profile = story / "source-study/wells-profile.md"
    profile.write_text(_profile_with_fields(config, "profile-claim"), encoding="utf-8")
    assert validate_profile_claim_links(profile, ledger, config, stage="development").ok


def test_profile_rejects_unbackticked_claim_ids(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    config = _config_for_selection()
    claim = _fixture_claim(
        claim_id="profile-unbackticked",
        jurisdiction={"scope": "role_specific", "roles": ["wells-alpha role"], "eligible_witness_ids": ["wells-alpha"]},
        classification="role_specific", support=[], search=None, status="rejected",
    )
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]})
    profile = story / "source-study/wells-profile.md"
    profile.write_text(_profile_with_fields(config, "profile-unbackticked").replace("- `profile-unbackticked`", "- profile-unbackticked"), encoding="utf-8")

    with pytest.raises(CreativeWriterError, match="claim-ID bullets|backticked"):
        validate_profile_claim_links(profile, ledger, config, stage="development")


def test_profile_rejects_stray_prose_inside_finding_record_region(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    config = _config_for_selection()
    claim = _fixture_claim(
        claim_id="profile-stray",
        jurisdiction={"scope": "role_specific", "roles": ["wells-alpha role"], "eligible_witness_ids": ["wells-alpha"]},
        classification="role_specific", support=[], search=None, status="rejected",
    )
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]})
    profile = story / "source-study/wells-profile.md"
    profile.write_text(_profile_with_fields(config, "profile-stray").replace("#### Finding 1\n\n", "Stray prose.\n\n#### Finding 1\n\n"), encoding="utf-8")

    with pytest.raises(CreativeWriterError, match="stray|record"):
        validate_profile_claim_links(profile, ledger, config, stage="development")


def test_profile_rejects_rogue_record_heading_and_prose_after_finding_start(
    tmp_path: Path,
) -> None:
    story, _ = _fixture(tmp_path)
    config = _config_for_selection()
    claim = _fixture_claim(
        claim_id="profile-rogue-record",
        jurisdiction={"scope": "role_specific", "roles": ["wells-alpha role"], "eligible_witness_ids": ["wells-alpha"]},
        classification="role_specific", support=[], search=None, status="rejected",
    )
    ledger = EvidenceLedger.model_validate(
        {
            "schema_version": 1,
            "study_id": config.study_id,
            "stage": "development",
            "mode": "descriptive",
            "claims": [claim],
        }
    )
    profile = story / "source-study/wells-profile.md"
    profile.write_text(
        _profile_with_fields(config, "profile-rogue-record").replace(
            "#### Finding 1\n\n",
            "#### Finding 1\n\n#### Rogue record heading\n\nArbitrary rogue record prose.\n\n",
        ),
        encoding="utf-8",
    )

    with pytest.raises(CreativeWriterError, match="(?i)heading|unparsed|stray|record"):
        validate_profile_claim_links(profile, ledger, config, stage="development")


def test_profile_requires_exact_protocol_sentinel_for_empty_dimension(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    config = _config_for_selection()
    profile = story / "source-study/wells-profile.md"
    profile.write_text(
        "# Profile\n\n"
        + "\n\n".join(
            f"### {index}. {dimension.label}\n\n"
            + ("" if index == 1 else "Protocol placeholder.")
            for index, dimension in enumerate(config.dimensions, 1)
        )
        + "\n",
        encoding="utf-8",
    )
    empty = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": []})

    with pytest.raises(CreativeWriterError, match="exact protocol placeholder"):
        validate_profile_claim_links(profile, empty, config, stage="development")


def test_profile_requires_classification_and_confidence_declarations(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    config = _config_for_selection()
    claim = _fixture_claim(
        claim_id="profile-missing-classification",
        jurisdiction={"scope": "role_specific", "roles": ["wells-alpha role"], "eligible_witness_ids": ["wells-alpha"]},
        classification="role_specific", support=[], search=None, status="rejected",
    )
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]})
    profile = story / "source-study/wells-profile.md"
    profile.write_text(
        _profile_with_fields(config, "profile-missing-classification").replace(
            "Classification: `role_specific`\nConfidence: `tentative`",
            "The classification and confidence are not declared.",
        ),
        encoding="utf-8",
    )

    with pytest.raises(CreativeWriterError, match="classification.*confidence|Classification"):
        validate_profile_claim_links(profile, ledger, config, stage="development")


def test_profile_classification_and_confidence_must_match_linked_claims(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    config = _config_for_selection()
    claim = _fixture_claim(
        claim_id="profile-mismatch",
        jurisdiction={"scope": "role_specific", "roles": ["wells-alpha role"], "eligible_witness_ids": ["wells-alpha"]},
        classification="role_specific", support=[], search=None, status="rejected",
    )
    claim["confidence"] = "moderate"
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]})
    profile = story / "source-study/wells-profile.md"
    profile.write_text(_profile_with_fields(config, "profile-mismatch"), encoding="utf-8")

    with pytest.raises(CreativeWriterError, match="(?i)do(?:es)? not match linked claim"):
        validate_profile_claim_links(profile, ledger, config, stage="development")


def test_profile_handles_disagreeing_linked_claims_deterministically(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    config = _config_for_selection()
    claims = [
        _fixture_claim(
            claim_id="claim-a",
            jurisdiction={"scope": "role_specific", "roles": ["wells-alpha role"], "eligible_witness_ids": ["wells-alpha"]},
            classification="role_specific", support=[], search=None, status="rejected",
        ),
        _fixture_claim(
            claim_id="claim-b",
            jurisdiction={"scope": "role_specific", "roles": ["wells-alpha role"], "eligible_witness_ids": ["wells-alpha"]},
            classification="unsupported", support=[], search=None, status="rejected",
        ),
    ]
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": claims})
    profile = story / "source-study/wells-profile.md"
    profile.write_text(_profile_with_fields(config, "claim-a").replace("- `claim-a`", "- `claim-a`\n- `claim-b`"), encoding="utf-8")

    with pytest.raises(CreativeWriterError, match="claim-a.*claim-b|disagree"):
        validate_profile_claim_links(profile, ledger, config, stage="development")


def test_profile_development_finding_blocks_absolute_wording(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    config = _config_for_selection()
    claim = _fixture_claim(
        claim_id="profile-absolute",
        jurisdiction={"scope": "role_specific", "roles": ["wells-alpha role"], "eligible_witness_ids": ["wells-alpha"]},
        classification="role_specific", support=[], search=None, status="rejected",
    )
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]})
    profile = story / "source-study/wells-profile.md"
    profile.write_text(_profile_with_fields(config, "profile-absolute", absolute=True), encoding="utf-8")
    with pytest.raises(CreativeWriterError, match="always/never/invariably"):
        validate_profile_claim_links(profile, ledger, config, stage="development")


def test_leakage_requires_full_passage_sequence_and_boundary_safe_ids(tmp_path: Path) -> None:
    text = "one two three four five six seven eight nine"
    digest = hashlib.sha256(text.encode()).hexdigest()
    passage = PassageRecord(
        witness_id="holdout", witness_ordinal=1, source_id="holdout", selection_id=None,
        source_fingerprint=HASH, heading_path=["Heading"], heading_label="Heading", block_type="paragraph",
        source_ordinal=1, heading_ordinal=1, normalized_text=text, original_text=text, word_count=9,
        direct_dialogue="none", content_hash=digest, passage_id=f"holdout:heading:1:{digest[:12]}",
    )
    partial = tmp_path / "partial.md"
    partial.write_text("zero " + " ".join(text.split()[:8]), encoding="utf-8")
    boundary = tmp_path / "boundary.md"
    boundary.write_text("holdout-extra", encoding="utf-8")
    assert not collect_leakage_issues([partial, boundary], forbidden_witness_ids={"holdout"}, forbidden_passages=[passage]).errors
    full = tmp_path / "full.md"
    full.write_text(text, encoding="utf-8")
    with pytest.raises(CreativeWriterError, match="full normalized"):
        validate_leakage([full], forbidden_witness_ids={"holdout"}, forbidden_passages=[passage])


def test_diagnostics_write_is_atomic_and_preserves_previous_report_on_replace_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report = tmp_path / "development-report.md"
    report.write_text("old report\n", encoding="utf-8")
    previous = report.read_bytes()
    monkeypatch.setattr("creative_writer.source_analysis.os.replace", lambda *_args: (_ for _ in ()).throw(OSError("forced replace failure")))
    with pytest.raises(CreativeWriterError, match="diagnostics"):
        source_analysis._write_development_diagnostics(report, errors=2, warnings=1)
    assert report.read_bytes() == previous


def test_develop_rejects_config_stage_outside_protocol_or_development(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    config_path = story / "source-study/analysis.yml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["study_status"] = "candidate_frozen"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    with pytest.raises(CreativeWriterError, match="develop.*protocol or development"):
        run_source_analysis(tmp_path, "fixture", "develop")


def _development_metric_fixture(tmp_path: Path) -> tuple[Path, AnalysisConfig, dict, Path, Path, list[PassageRecord]]:
    story, _ = _fixture(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "stories/fixture/source-study/holdouts.yml"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "lock fixture holdouts"], cwd=tmp_path, check=True)
    run_source_analysis(tmp_path, "fixture", "develop")
    config = _config_for_selection()
    config.study_status = "development"
    metrics_path = tmp_path / "build/fixture/source-study/development-metrics.json"
    csv_path = tmp_path / "build/fixture/source-study/development-metrics.csv"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    return story, config, metrics, metrics_path, csv_path, index


def _complete_quantitative_profile(config: AnalysisConfig, metrics: dict, metrics_path: Path, csv_path: Path) -> QuantitativeProfile:
    return QuantitativeProfile(
        schema_version=1,
        study_id=config.study_id,
        stage="development",
        generated_metrics=[
            MetricReference(id="development-metrics", path=config.generated_paths["development_metrics"], sha256=_sha256(metrics_path)),
            MetricReference(id="development-metrics-csv", path=config.generated_paths["development_metrics_csv"], sha256=_sha256(csv_path)),
        ],
        witnesses=[
            WitnessQuantitativeProfile(
                witness_id=item["witness_id"],
                source_id=item["source_id"],
                selection_id=item["selection_id"] or None,
                values={"total_words": item["total_words"]},
                variation="Fixture variation.",
                limitations="Fixture limitation.",
                interpretive_relevance="Fixture relevance.",
            )
            for item in metrics["witnesses"]
        ],
    )


def test_quantitative_profile_requires_exact_json_and_csv_references(tmp_path: Path) -> None:
    _story, config, metrics, metrics_path, csv_path, index = _development_metric_fixture(tmp_path)
    profile = _complete_quantitative_profile(config, metrics, metrics_path, csv_path)
    profile.generated_metrics.pop()
    with pytest.raises(CreativeWriterError, match="exactly.*JSON and CSV"):
        validate_quantitative_profile(profile, root=tmp_path, metrics_path=metrics_path, metrics_csv_path=csv_path, config=config, passages=index, development_witness_ids={item.witness_id for item in profile.witnesses})


def test_quantitative_profile_rejects_invented_empty_and_mismatched_values(tmp_path: Path) -> None:
    _story, config, metrics, metrics_path, csv_path, index = _development_metric_fixture(tmp_path)
    profile = _complete_quantitative_profile(config, metrics, metrics_path, csv_path)
    profile.witnesses[0].values = {"invented.metric": 1}
    with pytest.raises(CreativeWriterError, match="does not resolve"):
        validate_quantitative_profile(profile, root=tmp_path, metrics_path=metrics_path, metrics_csv_path=csv_path, config=config, passages=index, development_witness_ids={item.witness_id for item in profile.witnesses})
    profile.witnesses[0].values = {"total_words": None}
    with pytest.raises(CreativeWriterError, match="exactly equal|nonempty"):
        validate_quantitative_profile(profile, root=tmp_path, metrics_path=metrics_path, metrics_csv_path=csv_path, config=config, passages=index, development_witness_ids={item.witness_id for item in profile.witnesses})


def test_quantitative_profile_rejects_empty_or_stale_csv_provenance(tmp_path: Path) -> None:
    _story, config, metrics, metrics_path, csv_path, index = _development_metric_fixture(tmp_path)
    profile = _complete_quantitative_profile(config, metrics, metrics_path, csv_path)
    csv_path.write_text("study_id,stage\n", encoding="utf-8")
    profile.generated_metrics[1].sha256 = _sha256(csv_path)
    with pytest.raises(CreativeWriterError, match="data rows|provenance"):
        validate_quantitative_profile(profile, root=tmp_path, metrics_path=metrics_path, metrics_csv_path=csv_path, config=config, passages=index, development_witness_ids={item.witness_id for item in profile.witnesses})


def _rewrite_csv_rows(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = list(rows[0])
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(output.getvalue(), encoding="utf-8")


@pytest.mark.parametrize("mutation", ["duplicate", "remove", "extra", "mismatch"])
def test_quantitative_profile_requires_exact_csv_json_profile_identity_sets(
    tmp_path: Path, mutation: str
) -> None:
    _story, config, metrics, metrics_path, csv_path, index = _development_metric_fixture(tmp_path)
    profile = _complete_quantitative_profile(config, metrics, metrics_path, csv_path)
    if mutation == "duplicate":
        metrics["witnesses"].append(dict(metrics["witnesses"][0]))
        metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
        profile.generated_metrics[0].sha256 = _sha256(metrics_path)
    else:
        rows = list(csv.DictReader(io.StringIO(csv_path.read_text(encoding="utf-8"))))
        if mutation == "remove":
            removed = profile.witnesses.pop()
            rows = [row for row in rows if row["witness_id"] != removed.witness_id]
        elif mutation == "extra":
            extra = dict(rows[0])
            extra.update({"witness_id": "extra-witness", "source_id": "extra-witness", "selection_id": ""})
            rows.append(extra)
        else:
            rows = [
                {**row, "source_id": "mismatched-source"}
                if row["witness_id"] == profile.witnesses[0].witness_id
                else row
                for row in rows
            ]
        _rewrite_csv_rows(csv_path, rows)
        profile.generated_metrics[1].sha256 = _sha256(csv_path)

    with pytest.raises(CreativeWriterError, match="(?i)identity|unique|witness set"):
        validate_quantitative_profile(
            profile,
            root=tmp_path,
            metrics_path=metrics_path,
            metrics_csv_path=csv_path,
            config=config,
            passages=index,
            development_witness_ids={item.witness_id for item in profile.witnesses},
        )


def test_quantitative_profile_rejects_csv_path_outside_configured_generated_output(
    tmp_path: Path,
) -> None:
    _story, config, metrics, metrics_path, csv_path, index = _development_metric_fixture(tmp_path)
    profile = _complete_quantitative_profile(config, metrics, metrics_path, csv_path)
    alternate = tmp_path / "build/fixture/source-study/alternate.csv"
    alternate.write_bytes(csv_path.read_bytes())

    with pytest.raises(CreativeWriterError, match="(?i)CSV path|configured.*CSV|configured development"):
        validate_quantitative_profile(
            profile,
            root=tmp_path,
            metrics_path=metrics_path,
            metrics_csv_path=alternate,
            config=config,
            passages=index,
            development_witness_ids={item.witness_id for item in profile.witnesses},
        )


def test_populated_protocol_quantitative_profile_cannot_skip_current_output_checks(
    tmp_path: Path,
) -> None:
    story, config, metrics, metrics_path, csv_path, index = _development_metric_fixture(tmp_path)
    config.study_status = "protocol"
    profile = _complete_quantitative_profile(config, metrics, metrics_path, csv_path)
    profile.stage = "protocol"
    profile.witnesses[0].values = {"total_words": -1}
    profile.generated_metrics = []
    (story / "source-study/quantitative-profile.yml").write_text(
        yaml.safe_dump(profile.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
    )

    with pytest.raises(CreativeWriterError, match="witness set|exactly equal|current"):
        run_source_analysis(tmp_path, "fixture", "develop")


def test_leakage_scans_all_tracked_evidence_files_and_three_development_outputs(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    source_study = story / "source-study"
    tracked = [
        source_study / "quantitative-profile.yml",
        source_study / "evidence-ledger.yml",
        source_study / "wells-profile.md",
        source_study / "period-controls.md",
        source_study / "validation.md",
        source_study / "observations" / "wells-alpha.md",
        source_study / "observations" / "selected-short-fiction.md",
    ]
    for path in tracked:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("holdout", encoding="utf-8")
    assert set(tracked) <= set(_tracked_evidence_paths(story))
    outputs = [
        tmp_path / "build/fixture/source-study/development-metrics.json",
        tmp_path / "build/fixture/source-study/development-metrics.csv",
        tmp_path / "build/fixture/source-study/development-report.md",
    ]
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("holdout", encoding="utf-8")
    result = collect_leakage_issues(tracked + outputs, forbidden_witness_ids={"holdout"}, forbidden_passages=[])
    assert len(result.errors) == len(tracked) + len(outputs)


def test_leakage_rejects_a_within_work_holdout_passage_id_in_free_text(tmp_path: Path) -> None:
    text = "one two three four five six seven eight nine"
    digest = hashlib.sha256(text.encode()).hexdigest()
    passage = PassageRecord(
        witness_id="within-work",
        witness_ordinal=1,
        source_id="within-work",
        selection_id=None,
        source_fingerprint=HASH,
        heading_path=["Heading"],
        heading_label="Heading",
        block_type="paragraph",
        source_ordinal=1,
        heading_ordinal=1,
        normalized_text=text,
        original_text=text,
        word_count=9,
        direct_dialogue="none",
        content_hash=digest,
        passage_id=f"within-work:heading:1:{digest[:12]}",
    )
    path = tmp_path / "profile.md"
    path.write_text(f"Referenced locator: {passage.passage_id}\n", encoding="utf-8")

    with pytest.raises(CreativeWriterError, match="passage ID|forbidden"):
        validate_leakage([path], forbidden_witness_ids=set(), forbidden_passages=[passage])


def test_develop_pipeline_rejects_holdout_passage_id_in_tracked_artifact(
    tmp_path: Path,
) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    holdout = next(
        item for item in index if item.witness_id == "selected-short-fiction/the-star"
    )
    controls = story / "source-study/period-controls.md"
    controls.write_text(
        controls.read_text(encoding="utf-8")
        + f"\nTracked holdout locator: {holdout.passage_id}\n",
        encoding="utf-8",
    )
    _commit_fixture_holdouts(tmp_path)

    with pytest.raises(CreativeWriterError, match="(?i)passage ID|forbidden"):
        run_source_analysis(tmp_path, "fixture", "develop")

    report = tmp_path / "build/fixture/source-study/development-report.md"
    report_text = report.read_text(encoding="utf-8")
    assert "Evidence validation diagnostics" in report_text
    assert "Blocking errors: **2**" in report_text


def test_develop_pipeline_rejects_holdout_passage_id_in_generated_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    holdout = next(
        item for item in index if item.witness_id == "selected-short-fiction/the-star"
    )
    original_measure_development = source_analysis.measure_development

    def mutate_generated_report(*args: object, **kwargs: object) -> object:
        result = original_measure_development(*args, **kwargs)
        output_paths = kwargs["output_paths"]
        assert isinstance(output_paths, dict)
        report_path = output_paths["development_report"]
        assert isinstance(report_path, Path)
        report_path.write_text(
            report_path.read_text(encoding="utf-8")
            + f"\nGenerated holdout locator: {holdout.passage_id}\n",
            encoding="utf-8",
        )
        return result

    monkeypatch.setattr(source_analysis, "measure_development", mutate_generated_report)
    _commit_fixture_holdouts(tmp_path)

    with pytest.raises(CreativeWriterError, match="(?i)passage ID|forbidden"):
        run_source_analysis(tmp_path, "fixture", "develop")

    report = tmp_path / "build/fixture/source-study/development-report.md"
    report_text = report.read_text(encoding="utf-8")
    assert "Evidence validation diagnostics" in report_text
    assert "Blocking errors: **2**" in report_text


def test_develop_requires_exact_retained_tier_one_to_three_dossiers(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    admission, registry = _fixture_authority(story)
    expected = _expected_observation_paths(story, registry)
    (expected[0]).unlink()
    extra = story / "source-study/observations/not-retained.md"
    extra.write_text("# Extra\n", encoding="utf-8")
    paths, result = _validate_development_dossier_set(story, registry)
    assert set(paths) == set(expected)
    assert any("missing" in issue.message for issue in result.errors)
    assert any("not derived" in issue.message for issue in result.errors)
    assert admission.sources


def _validated_identity_failure(tmp_path: Path, update: dict[str, object], message: str) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["wells-alpha role"]
    admission, registry = _fixture_authority(story)
    passage = next(item for item in index if item.witness_id == "wells-alpha")
    claim = _fixture_claim(
        claim_id="identity-failure",
        jurisdiction={"scope": "role_specific", "roles": ["wells-alpha role"], "eligible_witness_ids": ["wells-alpha"]},
        classification="role_specific", support=[_fixture_reference(passage)], search=None, status="rejected",
    )
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]})
    ledger.claims[0].supporting_passages[0] = ledger.claims[0].supporting_passages[0].model_copy(update=update)
    with pytest.raises(CreativeWriterError, match=message):
        validate_evidence_ledger(ledger, index, config=config, admission=admission, registry=registry, file=story / "source-study/evidence-ledger.yml")


def test_ledger_rejects_source_identity_mismatch(tmp_path: Path) -> None:
    _validated_identity_failure(tmp_path, {"source_id": "other-source"}, "source/selection identity")


def test_ledger_rejects_selection_identity_mismatch(tmp_path: Path) -> None:
    _validated_identity_failure(tmp_path, {"selection_id": "selection-that-is-not-real"}, "source/selection identity")


def test_ledger_rejects_tier_mismatch(tmp_path: Path) -> None:
    _validated_identity_failure(tmp_path, {"authority_tier": 2}, "authority tier")


def test_ledger_rejects_fingerprint_mismatch(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["wells-alpha role"]
    admission, registry = _fixture_authority(story)
    passage = next(item for item in index if item.witness_id == "wells-alpha")
    passage.source_fingerprint = "b" * 64
    claim = _fixture_claim(
        claim_id="fingerprint-failure",
        jurisdiction={"scope": "role_specific", "roles": ["wells-alpha role"], "eligible_witness_ids": ["wells-alpha"]},
        classification="role_specific", support=[_fixture_reference(passage)], search=None, status="rejected",
    )
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]})
    with pytest.raises(CreativeWriterError, match="fingerprint"):
        validate_evidence_ledger(ledger, index, config=config, admission=admission, registry=registry)


def test_development_rejects_tier_four_control_and_tier_two_continuity(tmp_path: Path) -> None:
    story, _ = _fixture(tmp_path)
    index = read_passage_index(tmp_path / "build/fixture/source-study/passage-index.jsonl")
    config = _config_for_selection()
    config.dimensions[0].roles[:] = ["selected-short-fiction role"]
    admission, registry = _fixture_authority(story)
    control = next(item for item in index if item.witness_id == "tier-four")
    control_reference = _fixture_reference(control, 4)
    control_reference["evidence_role"] = "control"
    claim = _fixture_claim(
        claim_id="control-failure",
        jurisdiction={"scope": "role_specific", "roles": ["selected-short-fiction role"], "eligible_witness_ids": ["selected-short-fiction/the-plattner-story"]},
        classification="role_specific", support=[], search=None, status="rejected",
    )
    claim["counterexample_passages"] = [control_reference]
    ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [claim]})
    with pytest.raises(CreativeWriterError, match="Control and validation.*unavailable"):
        validate_evidence_ledger(ledger, index, config=config, stage="development", admission=admission, registry=registry)

    selected = next(item for item in index if item.witness_id.endswith("/the-plattner-story"))
    continuity = _fixture_claim(
        claim_id="tier-two-continuity",
        jurisdiction={"scope": "continuity", "roles": ["selected-short-fiction role"], "eligible_witness_ids": [selected.witness_id]},
        classification="role_specific", support=[_fixture_reference(selected, 2)], search=None,
    )
    continuity["counterexample_search"] = {
        "witness_ids": [selected.witness_id], "dimensions": ["frame-architecture"], "method": "manual_close_reading", "coverage": "targeted", "searched_passage_ids": [selected.passage_id], "outcome": "no_material_counterexample", "notes": "A bounded search was performed.",
    }
    continuity_ledger = EvidenceLedger.model_validate({"schema_version": 1, "study_id": config.study_id, "stage": "development", "mode": "descriptive", "claims": [continuity]})
    with pytest.raises(CreativeWriterError, match="continuity eligibility"):
        validate_evidence_ledger(continuity_ledger, index, config=config, admission=admission, registry=registry)


def test_generated_path_resolution_accepts_var_private_var_alias_without_escape(tmp_path: Path) -> None:
    config = _config_for_selection()
    alias_root = Path(str(tmp_path).replace("/private", "", 1))
    resolved = _resolve_generated_paths(alias_root, "fixture", config)
    assert resolved["development_report"].resolve(strict=False).is_relative_to(tmp_path.resolve(strict=False))
