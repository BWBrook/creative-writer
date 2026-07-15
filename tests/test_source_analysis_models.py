from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import unicodedata
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from creative_writer.files import load_yaml_model
from creative_writer.source_analysis_models import (
    AnalysisConfig,
    AnalyticalDimension,
    EvidenceLedger,
    EvidenceClaim,
    HoldoutManifest,
    PassageRecord,
    WitnessDescriptor,
    QuantitativeProfile,
    ValidationRecord,
    _heading_slug,
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
        "composition_window": {"start": 1897, "end": 1899},
        "study_status": "protocol",
        "admission_registry": {"path": "source-study/admission.yml", "sha256": HASH},
        "source_registry": {"path": "original/sources.yml", "sha256": HASH},
        "authority_policy_version": "phase-2a-v1",
        "authority_tiers": [
            {
                "tier": tier,
                "jurisdiction": f"Tier {tier} jurisdiction.",
                "analytical_roles": [f"tier {tier} role"],
                "evidence_rule": f"Tier {tier} evidence rule.",
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
    text = "The sky was clear."
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "witness_id": "selected-short-fiction/the-star",
        "witness_ordinal": 1,
        "source_id": "selected-short-fiction",
        "selection_id": "the-star",
        "source_fingerprint": HASH,
        "heading_path": ["The Star"],
        "heading_label": "The Star",
        "block_type": "paragraph",
        "source_ordinal": 1,
        "heading_ordinal": 1,
        "normalized_text": text,
        "original_text": text,
        "word_count": 4,
        "direct_dialogue": "none",
        "content_hash": content_hash,
        "passage_id": f"selected-short-fiction/the-star:the-star:1:{content_hash[:12]}",
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


def _holdout_manifest() -> dict[str, object]:
    return {
        "schema_version": 1,
        "partition_seed": "wells-phase-2b-v1",
        "algorithm_version": "tertile-hash-v1",
        "tool_version": "creative-writer 1",
        "created_at": datetime(2026, 7, 15, 10, tzinfo=timezone.utc),
        "registry_hashes": {"original/sources.yml": HASH},
        "source_fingerprints": {
            "selected-short-fiction/the-star": HASH,
            "the-time-machine": HASH,
        },
        "whole_work_holdouts": ["selected-short-fiction/the-star"],
        "witnesses": [
            {
                "witness_id": "selected-short-fiction/the-star",
                "development_windows": [],
                "holdout_windows": [
                    {"id": "star-holdout", "passage_ids": ["star:1"]}
                ],
            },
            {
                "witness_id": "the-time-machine",
                "development_windows": [
                    {"id": "tm-dev-1", "passage_ids": ["tm:1"]}
                ],
                "holdout_windows": [
                    {"id": "tm-holdout-1", "passage_ids": ["tm:2"]}
                ],
            },
        ],
    }


def test_complete_yaml_fixtures_parse(tmp_path: Path) -> None:
    fixtures = [
        ("analysis.yml", _analysis_config(), AnalysisConfig),
        (
            "holdouts.yml",
            _holdout_manifest(),
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


def test_analysis_fixture_uses_canonical_composition_window() -> None:
    config = load_yaml_model(
        Path("stories/time-expedition/source-study/analysis.yml"), AnalysisConfig
    )

    assert config.composition_window.start == 1897
    assert config.composition_window.end == 1899


def test_analysis_requires_authority_tiers() -> None:
    payload = _analysis_config()
    payload.pop("authority_tiers")

    with pytest.raises(ValidationError, match="authority_tiers"):
        AnalysisConfig.model_validate(payload)


def test_analysis_rejects_duplicate_authority_tiers() -> None:
    payload = _analysis_config()
    tiers = payload["authority_tiers"]
    assert isinstance(tiers, list)
    tiers[1]["tier"] = tiers[0]["tier"]

    with pytest.raises(ValidationError, match="authority tier values must be unique"):
        AnalysisConfig.model_validate(payload)


def test_analysis_fixture_matches_admission_roles_by_authority_tier() -> None:
    admission = yaml.safe_load(
        Path("stories/time-expedition/source-study/admission.yml").read_text(
            encoding="utf-8"
        )
    )
    config = load_yaml_model(
        Path("stories/time-expedition/source-study/analysis.yml"), AnalysisConfig
    )

    expected: dict[int, list[str]] = {tier: [] for tier in range(1, 6)}
    for source in admission["sources"]:
        tier = source["authority"]["tier"]
        roles = [*source.get("analytical_roles", [])]
        roles.extend(
            role
            for selection in source.get("selections", [])
            for role in selection.get("analytical_roles", [])
        )
        for role in roles:
            if role not in expected[tier]:
                expected[tier].append(role)

    actual = {policy.tier: set(policy.analytical_roles) for policy in config.authority_tiers}

    assert actual == {tier: set(roles) for tier, roles in expected.items()}


def test_analysis_fixture_declares_all_approved_core_measurements() -> None:
    config = load_yaml_model(
        Path("stories/time-expedition/source-study/analysis.yml"), AnalysisConfig
    )
    approved = {
        "total_words",
        "total_passages",
        "total_sentences",
        "total_sections",
        "sentence_length_distribution",
        "passage_length_distribution",
        "paragraph_length_distribution",
        "dialogue_proportion",
        "dialogue_run_lengths",
        "punctuation_frequencies",
        "speech_attribution_verbs",
        "reporting_verbs",
        "first_person_pronoun_frequencies",
        "third_person_pronoun_frequencies",
        "demonstrative_frequencies",
        "modal_frequencies",
        "epistemic_frequencies",
        "function_word_frequencies",
        "function_word_sequence_frequencies",
        "paragraph_openings",
        "paragraph_transitions",
        "moving_window_lexical_concentration",
        "block_proportions",
        "section_level_variation",
    }

    assert set(config.enabled_measurements) == approved


def test_analysis_fixture_declares_pronoun_lexicons() -> None:
    config = load_yaml_model(
        Path("stories/time-expedition/source-study/analysis.yml"), AnalysisConfig
    )

    assert set(config.lexicons) >= {
        "first_person_pronouns",
        "third_person_pronouns",
        "demonstratives",
    }
    for name in ("first_person_pronouns", "third_person_pronouns", "demonstratives"):
        assert config.lexicons[name]


def test_analysis_rejects_generated_path_outside_build() -> None:
    payload = _analysis_config()
    generated_paths = payload["generated_paths"]
    assert isinstance(generated_paths, dict)
    generated_paths["passage_index"] = "outputs/passage-index.jsonl"

    with pytest.raises(ValidationError, match="generated paths must begin with build/"):
        AnalysisConfig.model_validate(payload)


def test_analytical_dimension_rejects_invented_dimension_id() -> None:
    dimension = _dimensions()[0]
    dimension["id"] = "invented-dimension"

    with pytest.raises(ValidationError, match="id"):
        AnalyticalDimension.model_validate(dimension)


def test_evidence_claim_rejects_invented_dimension_id() -> None:
    payload = _ledger()["claims"][0]
    payload["dimension"] = "invented-dimension"

    with pytest.raises(ValidationError, match="dimension"):
        EvidenceClaim.model_validate(payload)


def test_partition_rejects_string_holdout_fraction() -> None:
    payload = _analysis_config()
    partition = payload["partition"]
    assert isinstance(partition, dict)
    partition["holdout_fraction"] = "0.2"

    with pytest.raises(ValidationError, match="holdout_fraction"):
        AnalysisConfig.model_validate(payload)


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


def test_passage_rejects_malformed_hash() -> None:
    payload = _passage()
    payload["source_fingerprint"] = "not-a-sha256"

    with pytest.raises(ValidationError, match="source_fingerprint"):
        PassageRecord.model_validate(payload)


@pytest.mark.parametrize("heading", ["!!!", "漢字"])
def test_heading_slug_uses_deterministic_hash_for_non_slug_headings(heading: str) -> None:
    normalized_heading = unicodedata.normalize("NFC", heading)
    expected_slug = f"heading-{hashlib.sha256(normalized_heading.encode('utf-8')).hexdigest()[:12]}"

    assert _heading_slug(heading) == expected_slug
    assert _heading_slug("Untitled") == "untitled"

    payload = _passage()
    payload["heading_path"] = [heading]
    payload["heading_label"] = heading
    payload["passage_id"] = (
        f"selected-short-fiction/the-star:{expected_slug}:1:{payload['content_hash'][:12]}"
    )
    record = PassageRecord.model_validate(payload)
    assert record.passage_id == payload["passage_id"]

    payload["passage_id"] = (
        f"selected-short-fiction/the-star:untitled:1:{payload['content_hash'][:12]}"
    )
    with pytest.raises(ValidationError, match="passage ID"):
        PassageRecord.model_validate(payload)


def test_witness_descriptor_requires_one_based_global_ordinal() -> None:
    with pytest.raises(ValidationError, match="witness_ordinal"):
        WitnessDescriptor.model_validate(
            {
                "witness_id": "the-time-machine",
                "source_id": "the-time-machine",
                "source_fingerprint": HASH,
            }
        )
    with pytest.raises(ValidationError, match="witness_ordinal"):
        WitnessDescriptor.model_validate(
            {
                "witness_id": "the-time-machine",
                "witness_ordinal": 0,
                "source_id": "the-time-machine",
                "source_fingerprint": HASH,
            }
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("heading_label", "Wrong heading"),
        ("normalized_text", "Tampered text."),
        ("word_count", 99),
        ("content_hash", "b" * 64),
        ("passage_id", "tampered"),
    ],
)
def test_passage_rejects_integrity_tampering(field: str, value: object) -> None:
    payload = _passage()
    payload[field] = value

    with pytest.raises(ValidationError):
        PassageRecord.model_validate(payload)


def test_passage_rejects_empty_text() -> None:
    payload = _passage()
    payload["normalized_text"] = ""

    with pytest.raises(ValidationError, match="normalized_text"):
        PassageRecord.model_validate(payload)


def test_passage_rejects_selection_mismatch() -> None:
    payload = _passage()
    payload["selection_id"] = "different-selection"

    with pytest.raises(ValidationError, match="mismatched selection identity"):
        PassageRecord.model_validate(payload)


def test_ledger_rejects_duplicate_claim_ids() -> None:
    payload = _ledger()
    claims = payload["claims"]
    assert isinstance(claims, list)
    claims.append(dict(claims[0]))

    with pytest.raises(ValidationError, match="claim IDs must be unique"):
        EvidenceLedger.model_validate(payload)


def test_ledger_rejects_forbidden_extra_field() -> None:
    payload = _ledger()
    claims = payload["claims"]
    assert isinstance(claims, list)
    claims[0]["operational_use"] = "none"

    with pytest.raises(ValidationError, match="operational_use"):
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


def test_holdout_manifest_accepts_whole_work_and_partitioned_witnesses() -> None:
    manifest = HoldoutManifest.model_validate(_holdout_manifest())

    whole_work = next(
        item for item in manifest.witnesses if item.witness_id == "selected-short-fiction/the-star"
    )
    partitioned = next(item for item in manifest.witnesses if item.witness_id == "the-time-machine")
    assert whole_work.development_windows == []
    assert whole_work.holdout_windows
    assert partitioned.development_windows
    assert partitioned.holdout_windows


def test_holdout_manifest_rejects_undeclared_whole_work_witness() -> None:
    payload = _holdout_manifest()
    witnesses = payload["witnesses"]
    assert isinstance(witnesses, list)
    witnesses.pop(0)

    with pytest.raises(ValidationError, match="whole-work holdouts must be represented"):
        HoldoutManifest.model_validate(payload)


def test_holdout_manifest_rejects_development_windows_for_whole_work() -> None:
    payload = _holdout_manifest()
    witnesses = payload["witnesses"]
    assert isinstance(witnesses, list)
    whole_work = witnesses[0]
    assert isinstance(whole_work, dict)
    whole_work["development_windows"] = [
        {"id": "star-dev", "passage_ids": ["star:development"]}
    ]

    with pytest.raises(ValidationError, match="whole-work witnesses must not have development windows"):
        HoldoutManifest.model_validate(payload)


def test_holdout_manifest_rejects_non_whole_work_without_development_windows() -> None:
    payload = _holdout_manifest()
    witnesses = payload["witnesses"]
    assert isinstance(witnesses, list)
    partitioned = witnesses[1]
    assert isinstance(partitioned, dict)
    partitioned["development_windows"] = []

    with pytest.raises(ValidationError, match="non-whole-work witnesses require development windows"):
        HoldoutManifest.model_validate(payload)


def test_holdout_manifest_rejects_non_whole_work_without_holdout_windows() -> None:
    payload = _holdout_manifest()
    witnesses = payload["witnesses"]
    assert isinstance(witnesses, list)
    partitioned = witnesses[1]
    assert isinstance(partitioned, dict)
    partitioned["holdout_windows"] = []

    with pytest.raises(ValidationError, match="holdout_windows"):
        HoldoutManifest.model_validate(payload)


def test_development_validation_allows_absent_candidate_hashes() -> None:
    payload = _validation()
    payload["stage"] = "development"

    record = ValidationRecord.model_validate(payload)

    assert record.stage == "development"
    assert record.candidate_commit is None


def test_candidate_frozen_validation_requires_candidate_hashes() -> None:
    payload = _validation()
    payload["stage"] = "candidate_frozen"

    with pytest.raises(ValidationError, match="candidate freeze hashes"):
        ValidationRecord.model_validate(payload)


def test_candidate_frozen_validation_accepts_candidate_hashes_without_final_hash() -> None:
    payload = _validation()
    payload.update(
        {
            "stage": "candidate_frozen",
            "candidate_commit": COMMIT,
            "candidate_profile_sha256": HASH,
            "candidate_ledger_sha256": HASH,
        }
    )

    record = ValidationRecord.model_validate(payload)

    assert record.final_profile_sha256 is None


def test_validation_rejects_final_profile_hash_before_validated() -> None:
    payload = _validation()
    payload.update(
        {
            "stage": "candidate_frozen",
            "candidate_commit": COMMIT,
            "candidate_profile_sha256": HASH,
            "candidate_ledger_sha256": HASH,
            "final_profile_sha256": HASH,
        }
    )

    with pytest.raises(ValidationError, match="final profile hash must be absent before validation"):
        ValidationRecord.model_validate(payload)


def test_validated_validation_requires_final_profile_hash() -> None:
    payload = _validation()
    payload.update(
        {
            "stage": "validated",
            "candidate_commit": COMMIT,
            "candidate_profile_sha256": HASH,
            "candidate_ledger_sha256": HASH,
        }
    )

    with pytest.raises(ValidationError, match="final profile hash is required"):
        ValidationRecord.model_validate(payload)


def test_validated_validation_accepts_complete_hash_lifecycle() -> None:
    payload = _validation()
    payload.update(
        {
            "stage": "validated",
            "candidate_commit": COMMIT,
            "candidate_profile_sha256": HASH,
            "candidate_ledger_sha256": HASH,
            "final_profile_sha256": HASH,
        }
    )

    record = ValidationRecord.model_validate(payload)

    assert record.stage == "validated"
    assert record.final_profile_sha256 == HASH
