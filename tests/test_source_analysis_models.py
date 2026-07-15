from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from creative_writer.files import load_yaml_model
from creative_writer.source_analysis_models import (
    AnalysisConfig,
    EvidenceLedger,
    HoldoutManifest,
    PassageRecord,
    QuantitativeProfile,
    ValidationRecord,
    parse_validation_document,
)


HASH = "a" * 64
COMMIT = "b" * 40


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
            "id": dimension_id,
            "label": f"Dimension {index}",
            "roles": ["declared role"],
            "description": "A declared analytical dimension.",
        }
        for index, dimension_id in enumerate(ids, start=1)
    ]


def _analysis_config() -> dict[str, object]:
    return {
        "schema_version": 1,
        "study_id": "time-expedition-wells-phase-2b",
        "composition_window": {"start": 1895, "end": 1899},
        "study_status": "protocol",
        "admission_registry": {"path": "source-study/admission.yml", "sha256": HASH},
        "source_registry": {"path": "original/sources.yml", "sha256": HASH},
        "authority_policy_version": "phase-2a-v1",
        "passage_rules": {
            "input_format": "gfm",
            "heading_context": True,
            "substantive_block_types": ["paragraph", "block_quote", "verse", "list_item"],
            "passage_id_template": "<witness-id>:<heading-slug>:<source-ordinal>:<hash12>",
            "context_radius": 2,
        },
        "partition": {
            "seed": "wells-phase-2b-v1",
            "algorithm_version": "tertile-hash-v1",
            "holdout_fraction": 0.2,
            "max_blocks_per_window": 5,
            "whole_work_holdouts": ["selected-short-fiction/the-star"],
        },
        "enabled_measurements": ["word_count"],
        "lexicons": {"reporting_verbs": ["said", "asked"]},
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
        "generated_paths": {"passage_index": "build/time-expedition/source-study/passage-index.jsonl"},
    }


def _passage() -> dict[str, object]:
    return {
        "witness_id": "selected-short-fiction/the-star",
        "source_id": "selected-short-fiction",
        "selection_id": "the-star",
        "source_fingerprint": HASH,
        "heading_path": ["The Star"],
        "heading_label": "The Star",
        "block_type": "paragraph",
        "source_ordinal": 1,
        "heading_ordinal": 1,
        "normalized_text": "The sky was clear.",
        "original_text": "The sky was clear.",
        "word_count": 4,
        "direct_dialogue": "none",
        "content_hash": HASH,
        "passage_id": f"selected-short-fiction/the-star:the-star:1:{HASH[:12]}",
    }


def _reference() -> dict[str, object]:
    return {
        "witness_id": "the-time-machine",
        "source_id": "the-time-machine",
        "selection_id": None,
        "passage_id": f"the-time-machine:chapter-one:1:{HASH[:12]}",
        "authority_tier": 1,
        "evidence_role": "support",
        "relevance_note": "Supports the declared continuity jurisdiction.",
    }


def _ledger() -> dict[str, object]:
    return {
        "schema_version": 1,
        "study_id": "time-expedition-wells-phase-2b",
        "stage": "development",
        "mode": "descriptive",
        "claims": [
            {
                "id": "claim-frame-1",
                "dimension": "frame-architecture",
                "statement": "The frame is a declared continuity jurisdiction.",
                "jurisdiction": "The Time Machine continuity and frame authority.",
                "classification": "role_specific",
                "status": "candidate",
                "confidence": "tentative",
                "supporting_passages": [_reference()],
                "counterexample_passages": [],
                "counterexample_search": "Searched the declared frame passages; no material counterexample was reviewed at protocol stage.",
                "control_results": [],
                "scope_and_limits": "This claim is limited to the declared source jurisdiction.",
                "validation_expectation": "Presence across an unseen role-matched passage set.",
                "prohibited_overgeneralisation": "It does not describe all Wells narration.",
                "notes": "Protocol fixture.",
            }
        ],
    }


def _validation() -> dict[str, object]:
    return {
        "schema_version": 1,
        "study_id": "time-expedition-wells-phase-2b",
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


def test_complete_yaml_fixtures_parse(tmp_path: Path) -> None:
    fixtures = [
        ("analysis.yml", _analysis_config(), AnalysisConfig),
        (
            "holdouts.yml",
            {
                "schema_version": 1,
                "partition_seed": "wells-phase-2b-v1",
                "algorithm_version": "tertile-hash-v1",
                "tool_version": "creative-writer 1",
                "created_at": "2026-07-15T10:00:00Z",
                "registry_hashes": {"original/sources.yml": HASH},
                "source_fingerprints": {"the-time-machine": HASH},
                "whole_work_holdouts": ["selected-short-fiction/the-star"],
                "witnesses": [
                    {
                        "witness_id": "the-time-machine",
                        "development_windows": [
                            {"id": "tm-dev-1", "passage_ids": [_reference()["passage_id"]]}
                        ],
                        "holdout_windows": [
                            {
                                "id": "tm-holdout-1",
                                "passage_ids": [
                                    "the-time-machine:chapter-one:2:cccccccccccc"
                                ],
                            }
                        ],
                    }
                ],
            },
            HoldoutManifest,
        ),
        (
            "quantitative-profile.yml",
            {
                "schema_version": 1,
                "study_id": "time-expedition-wells-phase-2b",
                "stage": "protocol",
                "generated_metrics": [
                    {"id": "word-count", "path": "build/metrics.json", "sha256": HASH}
                ],
                "witnesses": [
                    {
                        "witness_id": "the-time-machine",
                        "source_id": "the-time-machine",
                        "selection_id": None,
                        "values": {"word_count": 10},
                        "variation": "Reviewed variation is recorded per witness.",
                        "limitations": "Protocol fixture contains no substantive result.",
                        "interpretive_relevance": "Descriptive measurement only.",
                    }
                ],
            },
            QuantitativeProfile,
        ),
        ("evidence-ledger.yml", _ledger(), EvidenceLedger),
        ("validation.yml", _validation(), ValidationRecord),
    ]

    for filename, payload, model_type in fixtures:
        path = tmp_path / filename
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        parsed = load_yaml_model(path, model_type)
        assert parsed.schema_version == 1


def test_validation_document_requires_strict_front_matter_and_preserves_body() -> None:
    document = "---\n" + yaml.safe_dump(_validation(), sort_keys=False) + "---\n\n# Review surface\n\nProtocol state.\n"

    record, body = parse_validation_document(document, Path("validation.md"))

    assert isinstance(record, ValidationRecord)
    assert record.stage == "protocol"
    assert body == "# Review surface\n\nProtocol state.\n"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("study_status", "invented"),
        ("confidence_levels", ["tentative", "moderate", "strong", "unknown"]),
    ],
)
def test_analysis_rejects_unknown_enum_values(field: str, value: object) -> None:
    payload = _analysis_config()
    payload[field] = value

    with pytest.raises(ValidationError):
        AnalysisConfig.model_validate(payload)


def test_analysis_rejects_duplicate_dimension_ids() -> None:
    payload = _analysis_config()
    dimensions = payload["dimensions"]
    assert isinstance(dimensions, list)
    dimensions[1]["id"] = dimensions[0]["id"]

    with pytest.raises(ValidationError, match="dimension IDs must be unique"):
        AnalysisConfig.model_validate(payload)


def test_passage_rejects_malformed_hash_empty_text_and_selection_mismatch() -> None:
    payload = _passage()
    payload["source_fingerprint"] = "not-a-sha256"
    payload["normalized_text"] = ""
    payload["selection_id"] = "different-selection"

    with pytest.raises(ValidationError):
        PassageRecord.model_validate(payload)


def test_ledger_rejects_duplicate_claim_ids_and_operational_instruction_field() -> None:
    payload = _ledger()
    claims = payload["claims"]
    assert isinstance(claims, list)
    claims.append(dict(claims[0]))
    claims[1]["operational_use"] = "none"

    with pytest.raises(ValidationError):
        EvidenceLedger.model_validate(payload)


@pytest.mark.parametrize(
    ("status", "confidence"),
    [("validated", "moderate"), ("candidate", "strong")],
)
def test_development_ledger_rejects_premature_claim_state(status: str, confidence: str) -> None:
    payload = _ledger()
    payload["claims"][0]["status"] = status
    payload["claims"][0]["confidence"] = confidence

    with pytest.raises(ValidationError, match="validation stage"):
        EvidenceLedger.model_validate(payload)


def test_ledger_rejects_mismatched_selection_identity() -> None:
    payload = _ledger()
    reference = payload["claims"][0]["supporting_passages"][0]
    reference["witness_id"] = "selected-short-fiction/the-star"
    reference["source_id"] = "selected-short-fiction"
    reference["selection_id"] = "other-selection"

    with pytest.raises(ValidationError, match="selection identity"):
        EvidenceLedger.model_validate(payload)
