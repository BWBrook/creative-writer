from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

from creative_writer.exceptions import CreativeWriterError
from creative_writer.models import ChapterDocument, ChapterFrontMatter
from creative_writer.source_analysis_common import sha256_file
from creative_writer.style_profiles import (
    CHAPTER_ROLE_CAVEAT,
    load_style_context,
    resolve_style_profile_path,
    validate_chapter_style_metadata,
)


STUDY_ID = "fixture-wells-phase-2b"
COMMIT = "a" * 40
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
SUPPORT_PASSAGE = "selected-wells/story-a:chapter-one:1:aaaaaaaaaaaa"
HELDOUT_PASSAGE = "heldout-wells:chapter-two:2:bbbbbbbbbbbb"
CONTROL_PASSAGE = "control-author:chapter-three:3:cccccccccccc"


def _artifact(path: str, digest: str) -> dict[str, str]:
    return {"path": path, "sha256": digest}


def _dimensions() -> list[dict[str, Any]]:
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
            "id": dimension_id,
            "label": f"Dimension {index}",
            "roles": ["testimony"],
            "description": "A bounded fixture dimension.",
        }
        for index, dimension_id in enumerate(ids, start=1)
    ]


def _source_record(
    source_id: str,
    *,
    tier: int,
    style_authority: str,
    selection_id: str | None = None,
) -> dict[str, Any]:
    selected = selection_id is not None
    files: dict[str, Any] = {
        "epub": f"original/{source_id}.epub",
        "epub_sha256": HASH_A,
    }
    selections: list[dict[str, Any]] = []
    if selected:
        selections.append(
            {
                "id": selection_id,
                "title": "Story A",
                "first_published": 1897,
                "input": f"text/{selection_id}.xhtml",
                "markdown": f"text/{selection_id}.md",
                "markdown_sha256": HASH_B,
            }
        )
    else:
        files.update(
            {
                "markdown": f"original/{source_id}.md",
                "markdown_sha256": HASH_B,
            }
        )
    return {
        "id": source_id,
        "role": {
            "tier": tier,
            "story_world_canon": tier == 1,
            "style_authority": style_authority,
            "primary_style_anchor": style_authority == "primary",
            "secondary_style_anchor": style_authority in {"secondary", "bounded"},
            "focus": "Fixture authority boundary.",
            "analytical_roles": ["testimony", "adventure"],
            "permitted_uses": ["Bounded style analysis."],
            "prohibited_uses": ["No universal prescriptions."],
        },
        "work": {
            "title": source_id.replace("-", " ").title(),
            "author": "Fixture Author",
            "first_published": 1897,
        },
        "edition": {
            "publisher": "Fixture Press",
            "homepage": "https://example.test",
            "download_url": "https://example.test/source.epub",
            "upstream_release": "fixture-1",
            "upstream_revision": "fixture-revision",
        },
        "retrieved": "2026-07-31",
        "files": files,
        "selections": selections,
        "derivation": {
            "tool": "pandoc",
            "input": "epub",
            "writer": "gfm",
            "wrap": "none",
            "filter": "fixture",
        },
        "provenance": {
            "transcription": "Fixture transcription.",
            "page_scans": "No page scans used.",
        },
        "rights": {
            "source_text": "Public-domain fixture.",
            "edition_contributions": "Synthetic metadata.",
        },
    }


def _sources_payload() -> dict[str, Any]:
    return {
        "sources": [
            _source_record(
                "selected-wells",
                tier=2,
                style_authority="secondary",
                selection_id="story-a",
            ),
            _source_record(
                "heldout-wells",
                tier=1,
                style_authority="primary",
            ),
            _source_record(
                "control-author",
                tier=4,
                style_authority="control",
            ),
        ]
    }


def _generated_paths() -> dict[str, str]:
    prefix = "build/style-story/source-study"
    return {
        "corpus_lock": f"{prefix}/corpus-lock.json",
        "development_passage_index": f"{prefix}/indexes/development.jsonl",
        "heldout_wells_passage_index": f"{prefix}/indexes/heldout-wells.jsonl",
        "tier4_control_passage_index": f"{prefix}/indexes/tier4-controls.jsonl",
        "development_metrics": f"{prefix}/development-metrics.json",
        "development_metrics_csv": f"{prefix}/development-metrics.csv",
        "development_report": f"{prefix}/development-report.md",
        "validation_metrics": f"{prefix}/validation/current/validation-metrics.json",
        "validation_packet": f"{prefix}/validation/current/validation-packet.md",
        "analysis_report": f"{prefix}/validation/current/analysis-report.md",
    }


def _analysis_payload(source_hash: str) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "study_id": STUDY_ID,
        "composition_window": {"start": 1895, "end": 1899},
        "study_status": "validated",
        "admission_registry": {
            "path": "source-study/admission.yml",
            "sha256": HASH_A,
        },
        "source_registry": {
            "path": "original/sources.yml",
            "sha256": source_hash,
        },
        "authority_policy_version": "fixture-v1",
        "expected_corpus": {
            "admission_records": 4,
            "retained_sources": 3,
            "retained_epubs": 3,
            "retained_markdown": 3,
            "full_work_witnesses": 2,
            "selected_witnesses": 1,
            "witness_ids": [
                "selected-wells/story-a",
                "heldout-wells",
                "control-author",
            ],
            "excluded_tier5_ids": ["excluded-source"],
            "whole_work_holdouts": ["heldout-wells"],
        },
        "authority_tiers": [
            {
                "tier": tier,
                "jurisdiction": f"Tier {tier} fixture jurisdiction.",
                "analytical_roles": ["testimony"],
                "evidence_rule": f"Tier {tier} fixture evidence rule.",
            }
            for tier in range(1, 6)
        ],
        "passage_rules": {
            "input_format": "gfm",
            "heading_context": True,
            "substantive_block_types": [
                "paragraph",
                "block_quote",
                "verse",
                "list_item",
            ],
            "passage_id_template": (
                "<witness-id>:<heading-slug>:<source-ordinal>:<hash12>"
            ),
            "context_radius": 2,
        },
        "partition": {
            "seed": "fixture-seed",
            "algorithm_version": "tertile-hash-v1",
            "holdout_fraction": 0.2,
            "max_blocks_per_window": 5,
            "whole_work_holdouts": ["heldout-wells"],
        },
        "enabled_measurements": ["word_count"],
        "lexicons": {"reporting_verbs": ["said"]},
        "dimensions": _dimensions(),
        "confidence_levels": ["tentative", "moderate", "strong"],
        "claim_statuses": [
            "candidate",
            "qualified",
            "rejected",
            "validated",
        ],
        "claim_classifications": [
            "wells_distinctive",
            "wells_characteristic_but_shared",
            "role_specific",
            "period_general",
            "unsupported",
        ],
        "evidence_roles": [
            "support",
            "counterexample",
            "variation",
            "control",
            "validation",
        ],
        "generated_paths": _generated_paths(),
    }


def _holdout_payload(source_hash: str) -> dict[str, Any]:
    paths = _generated_paths()
    return {
        "schema_version": 2,
        "partition_seed": "fixture-seed",
        "algorithm_version": "tertile-hash-v1",
        "tool_version": "creative-writer fixture",
        "created_at": datetime(2026, 7, 31, tzinfo=timezone.utc),
        "registry_hashes": {"original/sources.yml": source_hash},
        "corpus_lock": {"path": paths["corpus_lock"], "sha256": HASH_A},
        "development_passage_index": {
            "path": paths["development_passage_index"],
            "sha256": HASH_A,
            "partition": "development",
            "passage_count": 1,
            "witness_ids": ["selected-wells/story-a"],
        },
        "heldout_wells_passage_index": {
            "path": paths["heldout_wells_passage_index"],
            "sha256": HASH_B,
            "partition": "heldout_wells",
            "passage_count": 3,
            "witness_ids": ["selected-wells/story-a", "heldout-wells"],
        },
        "tier4_control_passage_index": {
            "path": paths["tier4_control_passage_index"],
            "sha256": HASH_C,
            "partition": "tier4_controls",
            "passage_count": 1,
            "witness_ids": ["control-author"],
        },
        "source_fingerprints": {
            "selected-wells/story-a": HASH_A,
            "heldout-wells": HASH_B,
            "control-author": HASH_C,
        },
        "whole_work_holdouts": ["heldout-wells"],
        "witnesses": [
            {
                "witness_id": "selected-wells/story-a",
                "development_windows": [
                    {
                        "id": "selected-development",
                        "passage_ids": [SUPPORT_PASSAGE],
                    }
                ],
                "holdout_windows": [
                    {
                        "id": "selected-holdout",
                        "passage_ids": [
                            "selected-wells/story-a:chapter-four:4:dddddddddddd"
                        ],
                    }
                ],
            },
            {
                "witness_id": "heldout-wells",
                "development_windows": [],
                "holdout_windows": [
                    {
                        "id": "heldout-whole-work",
                        "passage_ids": [
                            HELDOUT_PASSAGE,
                            "heldout-wells:chapter-five:5:eeeeeeeeeeee",
                        ],
                    }
                ],
            },
        ],
    }


def _ledger_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "study_id": STUDY_ID,
        "stage": "validated",
        "mode": "descriptive",
        "claims": [
            {
                "id": "validated-claim",
                "dimension": "frame-architecture",
                "statement": "Testimony is visibly mediated in the bounded sample.",
                "jurisdiction": {
                    "scope": "role_specific",
                    "roles": ["testimony"],
                    "eligible_witness_ids": ["selected-wells/story-a"],
                },
                "classification": "role_specific",
                "status": "validated",
                "confidence": "moderate",
                "supporting_passages": [
                    {
                        "witness_id": "selected-wells/story-a",
                        "source_id": "selected-wells",
                        "selection_id": "story-a",
                        "passage_id": SUPPORT_PASSAGE,
                        "authority_tier": 2,
                        "evidence_role": "support",
                        "relevance_note": "A selected-witness support passage.",
                    }
                ],
                "counterexample_passages": [],
                "counterexample_search": {
                    "witness_ids": ["selected-wells/story-a"],
                    "dimensions": ["frame-architecture"],
                    "method": "manual_close_reading",
                    "coverage": "targeted",
                    "searched_passage_ids": [SUPPORT_PASSAGE],
                    "outcome": "no_material_counterexample",
                    "notes": "The fixture search found no material counterexample.",
                },
                "control_results": [
                    "The Tier 4 witness is a comparative control only."
                ],
                "scope_and_limits": "The claim is role- and sample-bounded.",
                "validation_expectation": {
                    "heldout_targets": [
                        {
                            "id": "heldout-testimony",
                            "witness_id": "heldout-wells",
                            "role": "testimony",
                        }
                    ],
                    "control_targets": [
                        {
                            "id": "control-adventure",
                            "witness_id": "control-author",
                            "role": "adventure",
                        }
                    ],
                    "heldout_tendency": "Mediation recurs in held-out testimony.",
                    "disconfirming_result": "Mediation is absent.",
                    "control_expectation": "The comparison remains negative only.",
                },
                "prohibited_overgeneralisation": "Do not universalise the claim.",
                "notes": "Synthetic profile-resolution fixture.",
            }
        ],
    }


def _validation_payload(
    analysis_hash: str,
    holdout_hash: str,
    ledger_hash: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "study_id": STUDY_ID,
        "stage": "validated",
        "validation_step": "complete",
        "candidate_commit": COMMIT,
        "candidate_analysis_sha256": analysis_hash,
        "candidate_manifest_sha256": holdout_hash,
        "candidate_profile_sha256": HASH_A,
        "candidate_ledger_sha256": HASH_B,
        "holdout_summary": "The declared held-out target was assessed.",
        "control_summary": "The Tier 4 comparison remained negative evidence.",
        "reviewer_summary": "The complete fixture evidence was approved.",
        "heldout_claim_results": [
            {
                "id": "heldout-result",
                "claim_id": "validated-claim",
                "expectation_target_id": "heldout-testimony",
                "witness_id": "heldout-wells",
                "role": "testimony",
                "passage_ids": [HELDOUT_PASSAGE],
                "assessment": "supports",
                "observed_tendency": "The bounded tendency recurs.",
                "notes": "Synthetic held-out result.",
            }
        ],
        "control_comparisons": [
            {
                "id": "control-result",
                "claim_id": "validated-claim",
                "expectation_target_id": "control-adventure",
                "witness_id": "control-author",
                "role": "adventure",
                "passage_ids": [CONTROL_PASSAGE],
                "comparison": "The control is comparative only.",
                "result": "not_shared",
                "notes": "Synthetic control result.",
            }
        ],
        "reviewer_records": [
            {
                "id": "reviewer-result",
                "claim_id": "validated-claim",
                "reviewer_id": "fixture-reviewer",
                "outcome": "approved",
                "heldout_result_ids": ["heldout-result"],
                "control_comparison_ids": ["control-result"],
                "review_run_ids": [
                    "heldout-review",
                    "control-review",
                    "claim-synthesis",
                ],
                "notes": "Synthetic reviewer synthesis.",
            }
        ],
        "review_run_provenance": [
            {
                "run_id": "heldout-review",
                "reviewer_id": "heldout-reader",
                "role_id": "heldout-reader",
                "stage": "heldout_review",
                "assigned_claim_ids": ["validated-claim"],
                "method": "Independent held-out reading.",
                "materials_seen": ["held-out packet"],
                "independent_of_candidate_authorship": True,
                "anonymisation_status": "not_anonymised",
                "outcome": "Assessment recorded.",
                "produced_record_ids": ["heldout-result"],
                "limitations": "Synthetic fixture.",
            },
            {
                "run_id": "control-review",
                "reviewer_id": "control-reader",
                "role_id": "control-reader",
                "stage": "control_review",
                "assigned_claim_ids": ["validated-claim"],
                "method": "Independent control reading.",
                "materials_seen": ["control packet"],
                "independent_of_candidate_authorship": True,
                "anonymisation_status": "not_anonymised",
                "outcome": "Comparison recorded.",
                "produced_record_ids": ["control-result"],
                "limitations": "Synthetic fixture.",
            },
            {
                "run_id": "claim-synthesis",
                "reviewer_id": "synthesis-reviewer",
                "role_id": "claim-synthesis",
                "stage": "claim_synthesis",
                "assigned_claim_ids": ["validated-claim"],
                "method": "Synthesis of recorded results.",
                "materials_seen": ["held-out result", "control result"],
                "independent_of_candidate_authorship": False,
                "anonymisation_status": "not_anonymised",
                "outcome": "Final state recorded.",
                "produced_record_ids": ["reviewer-result"],
                "limitations": "Synthetic fixture.",
            },
            {
                "run_id": "approved-whole-study",
                "reviewer_id": "independent-auditor",
                "role_id": "whole-study-auditor",
                "stage": "whole_study_audit",
                "assigned_claim_ids": ["validated-claim"],
                "method": "Independent whole-study audit.",
                "materials_seen": ["final evidence layer"],
                "independent_of_candidate_authorship": True,
                "anonymisation_status": "not_anonymised",
                "outcome": "approved",
                "produced_record_ids": [],
                "limitations": "Synthetic fixture.",
            },
        ],
        "claim_transitions": [
            {
                "claim_id": "validated-claim",
                "from_status": "candidate",
                "to_status": "validated",
                "from_confidence": "tentative",
                "to_confidence": "moderate",
                "reason": "Held-out and control review support the bounded claim.",
                "heldout_result_ids": ["heldout-result"],
                "control_comparison_ids": ["control-result"],
                "reviewer_record_ids": ["reviewer-result"],
            }
        ],
        "unresolved_uncertainty": "The fixture does not support generalisation.",
        "final_profile_sha256": HASH_C,
        "final_ledger_sha256": ledger_hash,
    }


def _profile_payload(
    analysis_hash: str,
    source_hash: str,
    holdout_hash: str,
    ledger_hash: str,
    validation_hash: str,
) -> dict[str, Any]:
    story_prefix = "stories/style-story"
    paths = _generated_paths()
    return {
        "schema_version": 1,
        "profile_id": "fixture-profile",
        "version": "1.0.0",
        "title": "Fixture evidence-linked profile",
        "provenance": {
            "study_id": STUDY_ID,
            "analysis": _artifact(
                f"{story_prefix}/source-study/analysis.yml",
                analysis_hash,
            ),
            "source_registry": _artifact(
                f"{story_prefix}/original/sources.yml",
                source_hash,
            ),
            "holdout_manifest": _artifact(
                f"{story_prefix}/source-study/holdouts.yml",
                holdout_hash,
            ),
            "evidence_ledger": _artifact(
                f"{story_prefix}/source-study/evidence-ledger.yml",
                ledger_hash,
            ),
            "validation_record": _artifact(
                f"{story_prefix}/source-study/validation.md",
                validation_hash,
            ),
            "passage_indexes": {
                "development": _artifact(
                    paths["development_passage_index"],
                    HASH_A,
                ),
                "heldout_wells": _artifact(
                    paths["heldout_wells_passage_index"],
                    HASH_B,
                ),
                "tier4_controls": _artifact(
                    paths["tier4_control_passage_index"],
                    HASH_C,
                ),
            },
            "approved_review_run_id": "approved-whole-study",
        },
        "eligible_claim_statuses": ["validated"],
        "default_packet_ids": ["test-packet"],
        "change_basis": "Approved fixture evidence.",
        "profile_review_refs": [
            "source-study/validation.md#approved-whole-study"
        ],
        "roles": [
            {
                "id": "frame",
                "label": "Frame",
                "description": "A testimony frame.",
                "phase_2b_roles": ["testimony"],
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
                "id": "practice-testimony",
                "name": "Visible testimony",
                "family": "practice",
                "advisory": "review",
                "claim_ids": ["validated-claim"],
                "roles": ["frame"],
                "scope": "chapter",
                "evaluation_mode": "manual_question",
                "review_question": "Is testimony visibly mediated?",
                "source_passage_ids": [SUPPORT_PASSAGE],
                "variation_passage_ids": [HELDOUT_PASSAGE],
                "control_passage_ids": [],
                "packet_ids": ["test-packet"],
                "interpretation_limits": "The claim remains sample-bounded.",
            }
        ],
    }


def _packet_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": "test-packet",
        "title": "Fixture testimony packet",
        "purpose": "Compare approved evidence without copying prose.",
        "profile_id": "fixture-profile",
        "profile_version": "1.0.0",
        "roles": ["frame"],
        "claim_ids": ["validated-claim"],
        "context_radius": 1,
        "entries": [
            {
                "id": "support-entry",
                "passage_id": SUPPORT_PASSAGE,
                "kind": "positive_example",
                "claim_ids": ["validated-claim"],
                "authority_tier": 2,
                "permitted_use": "Study mediation.",
                "selection_note": "Ledger support.",
            },
            {
                "id": "heldout-entry",
                "passage_id": HELDOUT_PASSAGE,
                "kind": "authentic_variation",
                "claim_ids": ["validated-claim"],
                "authority_tier": 1,
                "permitted_use": "Study held-out variation.",
                "selection_note": "Held-out validation evidence.",
            },
            {
                "id": "control-entry",
                "passage_id": CONTROL_PASSAGE,
                "kind": "negative_control",
                "claim_ids": ["validated-claim"],
                "authority_tier": 4,
                "permitted_use": "Test comparative drift only.",
                "selection_note": "Tier 4 negative control.",
            },
        ],
        "prohibited_uses": ["Do not treat controls as Wells evidence."],
        "anti_copying_guidance": "Study method without borrowing local wording.",
    }


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def _read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _write_validation(path: Path, payload: dict[str, Any]) -> None:
    front_matter = yaml.safe_dump(payload, sort_keys=False)
    path.write_text(
        f"---\n{front_matter}---\n\n# Validation\n\nApproved fixture evidence.\n",
        encoding="utf-8",
    )


def _read_validation(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    front_matter = text.split("---", 2)[1]
    payload = yaml.safe_load(front_matter)
    assert isinstance(payload, dict)
    return payload


@pytest.fixture
def style_story(tmp_path: Path) -> Path:
    story = tmp_path / "stories" / "style-story"
    source_path = story / "original" / "sources.yml"
    analysis_path = story / "source-study" / "analysis.yml"
    holdout_path = story / "source-study" / "holdouts.yml"
    ledger_path = story / "source-study" / "evidence-ledger.yml"
    validation_path = story / "source-study" / "validation.md"
    profile_path = story / "style-profile.yml"
    packet_path = story / "style-reference-packets" / "test-packet.yml"

    _write_yaml(source_path, _sources_payload())
    source_hash = sha256_file(source_path)
    _write_yaml(analysis_path, _analysis_payload(source_hash))
    analysis_hash = sha256_file(analysis_path)
    _write_yaml(holdout_path, _holdout_payload(source_hash))
    holdout_hash = sha256_file(holdout_path)
    _write_yaml(ledger_path, _ledger_payload())
    ledger_hash = sha256_file(ledger_path)
    _write_validation(
        validation_path,
        _validation_payload(analysis_hash, holdout_hash, ledger_hash),
    )
    validation_hash = sha256_file(validation_path)
    _write_yaml(
        profile_path,
        _profile_payload(
            analysis_hash,
            source_hash,
            holdout_hash,
            ledger_hash,
            validation_hash,
        ),
    )
    _write_yaml(packet_path, _packet_payload())
    return story


def _mutate_yaml(path: Path, mutation: Callable[[dict[str, Any]], None]) -> None:
    payload = _read_yaml(path)
    mutation(payload)
    _write_yaml(path, payload)


def _mutate_profile(
    story: Path,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    _mutate_yaml(story / "style-profile.yml", mutation)


def _mutate_packet(
    story: Path,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    _mutate_yaml(
        story / "style-reference-packets" / "test-packet.yml",
        mutation,
    )


def _reseal_validation(story: Path) -> None:
    validation_path = story / "source-study" / "validation.md"
    profile_path = story / "style-profile.yml"
    profile = _read_yaml(profile_path)
    profile["provenance"]["validation_record"]["sha256"] = sha256_file(
        validation_path
    )
    _write_yaml(profile_path, profile)


def _mutate_validation(
    story: Path,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    path = story / "source-study" / "validation.md"
    payload = _read_validation(path)
    mutation(payload)
    _write_validation(path, payload)
    _reseal_validation(story)


def _mutate_ledger_and_reseal(
    story: Path,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    ledger_path = story / "source-study" / "evidence-ledger.yml"
    validation_path = story / "source-study" / "validation.md"
    profile_path = story / "style-profile.yml"
    ledger = _read_yaml(ledger_path)
    mutation(ledger)
    _write_yaml(ledger_path, ledger)
    ledger_hash = sha256_file(ledger_path)

    validation = _read_validation(validation_path)
    validation["final_ledger_sha256"] = ledger_hash
    claim_ids = [claim["id"] for claim in ledger["claims"]]
    if claim_ids:
        for run in validation["review_run_provenance"]:
            if run["stage"] == "whole_study_audit":
                run["assigned_claim_ids"] = claim_ids
    _write_validation(validation_path, validation)

    profile = _read_yaml(profile_path)
    profile["provenance"]["evidence_ledger"]["sha256"] = ledger_hash
    profile["provenance"]["validation_record"]["sha256"] = sha256_file(
        validation_path
    )
    _write_yaml(profile_path, profile)


def _load(story: Path):
    return load_style_context(
        story.parent.parent,
        story,
        story / "style-profile.yml",
    )


def _chapter(story: Path, *, roles: list[str], packets: list[str]) -> ChapterDocument:
    front_matter = ChapterFrontMatter.model_validate(
        {
            "title": "Fixture chapter",
            "summary": "A chapter used to validate explicit style metadata.",
            "manuscript": "manuscript/01-fixture.md",
            "style_roles": roles,
            "style_packets": packets,
        }
    )
    return ChapterDocument(
        stub_path=story / "chapter-stubs" / "01-fixture.md",
        manuscript_path=story / "manuscript" / "01-fixture.md",
        front_matter=front_matter,
        stub_body="",
        manuscript_body="Fixture manuscript.",
    )


def test_profile_override_resolution_is_story_relative_unless_absolute(
    style_story: Path,
) -> None:
    relative = resolve_style_profile_path(
        style_story,
        configured_path=None,
        override="profiles/alternate.yml",
    )
    absolute_override = style_story / "style-profile.yml"

    assert relative == style_story / "profiles" / "alternate.yml"
    assert (
        resolve_style_profile_path(
            style_story,
            configured_path=None,
            override=str(absolute_override),
        )
        == absolute_override
    )


def test_configured_profile_path_must_remain_story_relative(
    style_story: Path,
) -> None:
    with pytest.raises(CreativeWriterError, match="configured.*story-relative"):
        resolve_style_profile_path(
            style_story,
            configured_path="../style-profile.yml",
            override=None,
        )


def test_relative_profile_override_cannot_escape_story(style_story: Path) -> None:
    with pytest.raises(CreativeWriterError, match="escapes|canonical"):
        resolve_style_profile_path(
            style_story,
            configured_path=None,
            override="../style-profile.yml",
        )


def test_profile_resolution_requires_configuration_or_override(
    style_story: Path,
) -> None:
    with pytest.raises(CreativeWriterError, match="requires.*profile"):
        resolve_style_profile_path(
            style_story,
            configured_path=None,
            override=None,
        )


def test_profile_loads_and_inherits_claim_state(style_story: Path) -> None:
    context = _load(style_story)

    resolved = context.rules[0]
    assert resolved.claims[0].status == "validated"
    assert resolved.claims[0].confidence == "moderate"
    assert context.evidence_catalog[SUPPORT_PASSAGE].source_id == "selected-wells"
    assert context.evidence_catalog[SUPPORT_PASSAGE].selection_id == "story-a"
    assert context.evidence_catalog[SUPPORT_PASSAGE].evidence_kinds == ("support",)
    assert context.evidence_catalog[HELDOUT_PASSAGE].evidence_kinds == (
        "validation",
    )
    assert context.evidence_catalog[CONTROL_PASSAGE].authority_tier == 4
    assert set(context.evidence_catalog) == {
        SUPPORT_PASSAGE,
        HELDOUT_PASSAGE,
        CONTROL_PASSAGE,
    }
    assert set(context.packets) == {"test-packet"}


def test_profile_load_does_not_require_generated_passage_indexes(
    style_story: Path,
) -> None:
    assert not (
        style_story.parent.parent
        / "build"
        / "style-story"
        / "source-study"
        / "indexes"
        / "development.jsonl"
    ).exists()

    assert _load(style_story).profile.profile_id == "fixture-profile"


def test_profile_rejects_stale_ledger_hash(style_story: Path) -> None:
    path = style_story / "source-study" / "evidence-ledger.yml"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(CreativeWriterError, match="evidence-ledger.*SHA-256"):
        _load(style_story)


def test_profile_rejects_mismatched_study_id(style_story: Path) -> None:
    _mutate_ledger_and_reseal(
        style_story,
        lambda payload: payload.__setitem__("study_id", "other-study"),
    )

    with pytest.raises(CreativeWriterError, match="study ID"):
        _load(style_story)


def test_profile_rejects_passage_index_binding_drift(style_story: Path) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["provenance"]["passage_indexes"]["development"]["sha256"] = (
            "f" * 64
        )

    _mutate_profile(style_story, mutate)

    with pytest.raises(CreativeWriterError, match="development.*SHA-256"):
        _load(style_story)


def test_profile_rejects_missing_claim(style_story: Path) -> None:
    _mutate_ledger_and_reseal(
        style_story,
        lambda payload: payload["claims"].clear(),
    )

    with pytest.raises(CreativeWriterError, match="unknown claim validated-claim"):
        _load(style_story)


def test_profile_rejects_rejected_claim(style_story: Path) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        claim = payload["claims"][0]
        claim["status"] = "rejected"
        claim["supporting_passages"] = []
        claim["counterexample_search"] = None

    _mutate_ledger_and_reseal(style_story, mutate)

    with pytest.raises(
        CreativeWriterError,
        match="Rule practice-testimony uses ineligible claim validated-claim",
    ):
        _load(style_story)


def test_profile_rejects_qualified_claim_when_only_validated_is_eligible(
    style_story: Path,
) -> None:
    _mutate_ledger_and_reseal(
        style_story,
        lambda payload: payload["claims"][0].__setitem__(
            "status",
            "qualified",
        ),
    )

    with pytest.raises(
        CreativeWriterError,
        match="Rule practice-testimony uses ineligible claim validated-claim",
    ):
        _load(style_story)


def test_profile_rejects_heldout_role_outside_claim_jurisdiction(
    style_story: Path,
) -> None:
    _mutate_validation(
        style_story,
        lambda payload: payload["heldout_claim_results"][0].__setitem__(
            "role",
            "unrelated-role",
        ),
    )

    with pytest.raises(CreativeWriterError, match="jurisdiction"):
        _load(style_story)


def test_profile_rejects_role_that_broadens_claim_jurisdiction(
    style_story: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["roles"][0]["phase_2b_roles"] = ["unrelated-role"]

    _mutate_profile(style_story, mutate)

    with pytest.raises(
        CreativeWriterError,
        match="Rule practice-testimony broadens validated-claim",
    ):
        _load(style_story)


def test_profile_rejects_unknown_rule_role(style_story: Path) -> None:
    _mutate_profile(
        style_story,
        lambda payload: payload["rules"][0].__setitem__(
            "roles",
            ["missing-role"],
        ),
    )

    with pytest.raises(CreativeWriterError, match="unknown role missing-role"):
        _load(style_story)


def test_profile_rejects_changed_source_tier(style_story: Path) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["claims"][0]["supporting_passages"][0]["authority_tier"] = 3

    _mutate_ledger_and_reseal(style_story, mutate)

    with pytest.raises(CreativeWriterError, match="authority tier.*selected-wells"):
        _load(style_story)


def test_profile_rejects_tier_four_positive_rule_evidence(
    style_story: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["rules"][0]["source_passage_ids"] = [CONTROL_PASSAGE]

    _mutate_profile(style_story, mutate)

    with pytest.raises(CreativeWriterError, match="Tier 4.*positive"):
        _load(style_story)


def test_profile_rejects_tier_one_to_three_negative_control(
    style_story: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["entries"][0]["kind"] = "negative_control"

    _mutate_packet(style_story, mutate)

    with pytest.raises(CreativeWriterError, match="negative control.*Tier 4"):
        _load(style_story)


def test_profile_rejects_unknown_packet_id(style_story: Path) -> None:
    _mutate_profile(
        style_story,
        lambda payload: payload.__setitem__(
            "default_packet_ids",
            ["missing-packet"],
        ),
    )

    with pytest.raises(CreativeWriterError, match="unknown packet missing-packet"):
        _load(style_story)


def test_profile_rejects_packet_entry_claim_outside_packet(
    style_story: Path,
) -> None:
    _mutate_packet(
        style_story,
        lambda payload: payload["entries"][0].__setitem__(
            "claim_ids",
            ["other-claim"],
        ),
    )

    with pytest.raises(CreativeWriterError, match="entry.*claim IDs.*packet"):
        _load(style_story)


def test_profile_rejects_packet_claim_outside_profile(style_story: Path) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["claim_ids"] = ["other-claim"]
        payload["entries"][0]["claim_ids"] = ["other-claim"]

    _mutate_packet(style_story, mutate)

    with pytest.raises(CreativeWriterError, match="packet.*claim.*profile"):
        _load(style_story)


def test_profile_rejects_packet_passage_outside_evidence_catalog(
    style_story: Path,
) -> None:
    _mutate_packet(
        style_story,
        lambda payload: payload["entries"][0].__setitem__(
            "passage_id",
            "selected-wells/story-a:unknown:99:ffffffffffff",
        ),
    )

    with pytest.raises(CreativeWriterError, match="evidence catalog"):
        _load(style_story)


def test_profile_rejects_unapproved_named_whole_study_review(
    style_story: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["review_run_provenance"][-1]["outcome"] = "changes_requested"

    _mutate_validation(style_story, mutate)

    with pytest.raises(CreativeWriterError, match="approved.*whole-study"):
        _load(style_story)


@pytest.mark.parametrize(
    ("record_key", "expected"),
    [
        ("heldout_claim_results", "held-out.*covered more than once"),
        ("control_comparisons", "control.*covered more than once"),
    ],
)
def test_profile_rejects_duplicate_validation_target_coverage(
    style_story: Path,
    record_key: str,
    expected: str,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        duplicate = deepcopy(payload[record_key][0])
        duplicate["id"] = f"duplicate-{duplicate['id']}"
        payload[record_key].append(duplicate)

    _mutate_validation(style_story, mutate)

    with pytest.raises(CreativeWriterError, match=expected):
        _load(style_story)


def test_profile_rejects_named_audit_without_full_claim_coverage(
    style_story: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["review_run_provenance"][-1]["assigned_claim_ids"] = [
            "other-claim"
        ]

    _mutate_validation(style_story, mutate)

    with pytest.raises(CreativeWriterError, match="all.*claims"):
        _load(style_story)


def test_profile_rejects_tracked_artifact_outside_story(style_story: Path) -> None:
    root = style_story.parent.parent
    source = style_story / "source-study" / "analysis.yml"
    outside = root / "outside-analysis.yml"
    outside.write_bytes(source.read_bytes())

    def mutate(payload: dict[str, Any]) -> None:
        payload["provenance"]["analysis"] = _artifact(
            "outside-analysis.yml",
            sha256_file(outside),
        )

    _mutate_profile(style_story, mutate)

    with pytest.raises(CreativeWriterError, match="analysis.*escapes story"):
        _load(style_story)


def test_profile_rejects_story_outside_repository_root(style_story: Path) -> None:
    with pytest.raises(CreativeWriterError, match="story.*repository root"):
        load_style_context(
            style_story / "nested-root",
            style_story,
            style_story / "style-profile.yml",
        )


def test_chapter_metadata_reports_each_unknown_id_with_stub_path(
    style_story: Path,
) -> None:
    context = _load(style_story)
    chapter = _chapter(
        style_story,
        roles=["unknown-role-one", "unknown-role-two"],
        packets=["unknown-packet"],
    )

    errors = validate_chapter_style_metadata(context, [chapter])

    assert len(errors) == 3
    assert all(str(chapter.stub_path) in error for error in errors)
    assert any("unknown-role-one" in error for error in errors)
    assert any("unknown-role-two" in error for error in errors)
    assert any("unknown-packet" in error for error in errors)


def test_mixed_role_chapter_metadata_passes_with_fixed_caveat(
    style_story: Path,
) -> None:
    context = _load(style_story)
    chapter = _chapter(
        style_story,
        roles=["frame", "reported-account"],
        packets=["test-packet"],
    )

    assert validate_chapter_style_metadata(context, [chapter]) == []
    assert CHAPTER_ROLE_CAVEAT == (
        "Chapter-level role assignment is coarse and does not classify every "
        "paragraph."
    )
