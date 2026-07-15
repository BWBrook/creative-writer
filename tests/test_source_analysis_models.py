from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
    ClaimJurisdiction,
    CounterexampleSearch,
    EvidenceLedger,
    EvidenceClaim,
    GeneratedDevelopmentMetrics,
    HoldoutManifest,
    PassageRecord,
    WitnessDescriptor,
    WitnessMetricRecord,
    QuantitativeProfile,
    ValidationRecord,
    _heading_slug,
    parse_validation_document,
)


HASH = "a" * 64
COMMIT = "b" * 40


def _metric_record_payload() -> dict[str, object]:
    distribution = {
        "count": 1,
        "minimum": 2,
        "p10": 2,
        "p25": 2,
        "median": 2,
        "p75": 2,
        "p90": 2,
        "maximum": 2,
        "mean": 2,
    }
    return {
        "witness_id": "wells-alpha",
        "source_id": "wells-alpha",
        "selection_id": None,
        "witness_ordinal": 1,
        "total_words": 2,
        "total_passages": 1,
        "total_sentences": 1,
        "total_sections": 1,
        "sentence_length_distribution": distribution,
        "paragraph_length_distribution": distribution,
        "passage_length_distribution": distribution,
        "dialogue_proportion": {
            "dialogue_words": 0,
            "denominator_words": 2,
            "proportion": 0.0,
            "unknown_words": 0,
            "unknown_passages": 0,
        },
        "dialogue_run_lengths": [],
        "punctuation_frequencies": {
            "periods_raw": 1,
            "periods": 1,
            "question_marks": 0,
            "exclamation_marks": 0,
            "colons": 0,
            "semicolons": 0,
            "parentheses_open": 0,
            "parentheses_close": 0,
            "hyphen": 0,
            "en_dash": 0,
            "em_dash": 0,
            "ellipsis_unicode": 0,
            "ellipsis_ascii": 0,
            "double_quote_open": 0,
            "double_quote_close": 0,
            "single_quote_open": 0,
            "single_quote_close": 0,
            "straight_double_quote": 0,
            "straight_single_quote": 0,
            "guillemet_open": 0,
            "guillemet_close": 0,
            "normalization_artifacts": {"bom": 0, "hair_space": 0, "nbsp": 0},
            "parentheses_total": 0,
            "dash_total": 0,
            "ellipsis_total": 0,
            "quote_counts_by_codepoint": {
                "U+2018": 0,
                "U+2019": 0,
                "U+201C": 0,
                "U+201D": 0,
                "U+0027": 0,
                "U+0022": 0,
                "U+00AB": 0,
                "U+00BB": 0,
            },
            "denominator_words": 2,
            "per_1000_words": {"periods_raw": 500.0},
        },
        "speech_attribution_verbs": {"said": 0},
        "reporting_verbs": {"reported": 0},
        "first_person_pronoun_frequencies": {"i": 0},
        "third_person_pronoun_frequencies": {"he": 0},
        "demonstrative_frequencies": {"this": 0},
        "modal_frequencies": {"could": 0},
        "epistemic_frequencies": {"perhaps": 0},
        "lexicon_frequencies": {"function_words": {"the": 1}},
        "normalized_frequencies": {
            "function_words": {
                "counts": {"the": 1},
                "denominator_words": 2,
                "per_1000_words": {"the": 500.0},
            }
        },
        "function_word_frequencies": {"the": 1},
        "function_word_sequence_frequencies": {},
        "paragraph_openings": {"other": 1},
        "paragraph_transitions": {},
        "moving_window_lexical_concentration": {
            "sections": [{
                "section_id": "Chapter One",
                "heading_path": ["Chapter One"],
                "token_count": 2,
                "window_width": 2,
                "window_count": 1,
                "window_values": [1.0],
                "mean": 1.0,
                "minimum": 1.0,
                "median": 1.0,
                "maximum": 1.0,
            }],
            "window_width_rule": "max(1, ceil(sqrt(section_token_count)))",
        },
        "block_proportions": {
            "counts": {"dialogue": 0, "narrative": 1, "quotation": 0, "verse": 0, "list": 0},
            "denominator_passages": 1,
            "proportions": {"dialogue": 0.0, "narrative": 1.0, "quotation": 0.0, "verse": 0.0, "list": 0.0},
        },
        "section_level_variation": {
            "total_words": {"minimum": 2, "maximum": 2, "range": 0, "count": 1}
        },
        "section_metrics": [{
            "section_id": "Chapter One",
            "heading_path": ["Chapter One"],
            "total_words": 2,
            "total_passages": 1,
            "total_sentences": 1,
            "dialogue_words": 0,
            "question_marks": 0,
            "exclamation_marks": 0,
            "colons": 0,
            "semicolons": 0,
            "parentheses_total": 0,
            "ellipsis_total": 0,
            "dash_total": 0,
            "lexicon_frequencies": {"function_words": {"the": 1}},
        }],
        "candidate_flags": [],
    }


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
        "expected_corpus": {
            "admission_records": 13,
            "retained_sources": 12,
            "retained_epubs": 12,
            "retained_markdown": 15,
            "full_work_witnesses": 11,
            "selected_witnesses": 4,
            "witness_ids": [
                "the-time-machine",
                "the-invisible-man",
                "the-island-of-doctor-moreau",
                "the-war-of-the-worlds",
                "certain-personal-matters",
                "text-book-of-biology-part-1",
                "the-first-witness",
                "the-second-witness",
                "the-third-witness",
                "the-fourth-witness",
                "the-fifth-witness",
                "selected-short-fiction/the-plattner-story",
                "selected-short-fiction/the-sea-raiders",
                "selected-short-fiction/the-crystal-egg",
                "selected-short-fiction/the-star",
            ],
            "excluded_tier5_ids": ["the-lost-world"],
            "whole_work_holdouts": ["selected-short-fiction/the-star"],
        },
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
        "generated_paths": {
            "corpus_lock": "build/time-expedition/source-study/corpus-lock.json",
            "passage_index": "build/time-expedition/source-study/passage-index.jsonl",
            "development_metrics": "build/time-expedition/source-study/development-metrics.json",
            "development_metrics_csv": "build/time-expedition/source-study/development-metrics.csv",
            "development_report": "build/time-expedition/source-study/development-report.md",
            "validation_metrics": "build/time-expedition/source-study/validation-metrics.json",
            "validation_packet": "build/time-expedition/source-study/validation-packet.md",
            "analysis_report": "build/time-expedition/source-study/analysis-report.md",
        },
    }


def test_generated_metric_witness_schema_is_strict_for_emitted_scalar_fields() -> None:
    payload = _metric_record_payload()
    WitnessMetricRecord.model_validate(payload)

    for field, value in {
        "total_words": [],
        "total_passages": True,
        "witness_ordinal": "1",
        "source_id": [],
    }.items():
        mutated = {**payload, field: value}
        with pytest.raises(ValidationError):
            WitnessMetricRecord.model_validate(mutated)


def test_generated_metric_document_schemas_candidate_heuristics_and_extras() -> None:
    record = _metric_record_payload()
    document = {
        "schema_version": 1,
        "stage": "development",
        "study_id": "time-expedition-wells-phase-2b",
        "config_sha256": HASH,
        "index_sha256": HASH,
        "manifest_sha256": HASH,
        "provenance": {
            "study_id": "time-expedition-wells-phase-2b",
            "stage": "development",
            "config_sha256": HASH,
            "index_sha256": HASH,
            "manifest_sha256": HASH,
            "config_path": "stories/fixture/source-study/analysis.yml",
            "index_path": "build/fixture/source-study/passage-index.jsonl",
            "manifest_path": "stories/fixture/source-study/holdouts.yml",
        },
        "enabled_measurements": ["word_count"],
        "candidate_heuristics": {
            "observation_to_explanation_movement": {
                "status": "deferred",
                "reason": "Deferred to human close reading because it cannot be measured from declared lexicons without interpretation.",
            }
        },
        "witnesses": [record],
    }
    GeneratedDevelopmentMetrics.model_validate(document)

    nested_mutation = {**document, "candidate_heuristics": {"observation_to_explanation_movement": []}}
    with pytest.raises(ValidationError):
        GeneratedDevelopmentMetrics.model_validate(nested_mutation)

    extra_mutation = {**document, "unexpected": True}
    with pytest.raises(ValidationError):
        GeneratedDevelopmentMetrics.model_validate(extra_mutation)


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
                "jurisdiction": {
                    "scope": "continuity",
                    "roles": ["declared role"],
                    "eligible_witness_ids": ["the-time-machine"],
                },
                "classification": "role_specific",
                "status": "candidate",
                "confidence": "tentative",
                "supporting_passages": [_reference()],
                "counterexample_passages": [],
                "counterexample_search": {
                    "witness_ids": ["the-time-machine"],
                    "dimensions": ["frame-architecture"],
                    "method": "manual_close_reading",
                    "coverage": "targeted",
                    "searched_passage_ids": ["the-time-machine:chapter-one:1:" + HASH[:12]],
                    "outcome": "no_material_counterexample",
                    "notes": "Searched the declared frame passages; no material counterexample was reviewed at protocol stage.",
                },
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


def test_analysis_fixture_declares_exact_time_expedition_corpus_authority() -> None:
    config = load_yaml_model(
        Path("stories/time-expedition/source-study/analysis.yml"), AnalysisConfig
    )

    assert config.expected_corpus.model_dump() == {
        "admission_records": 13,
        "retained_sources": 12,
        "retained_epubs": 12,
        "retained_markdown": 15,
        "full_work_witnesses": 11,
        "selected_witnesses": 4,
        "witness_ids": [
            "the-time-machine",
            "selected-short-fiction/the-plattner-story",
            "selected-short-fiction/the-sea-raiders",
            "selected-short-fiction/the-crystal-egg",
            "selected-short-fiction/the-star",
            "certain-personal-matters",
            "text-book-of-biology-part-1",
            "the-british-barbarians",
            "a-desert-drama",
            "the-days-work",
            "the-beetle",
            "king-solomons-mines",
            "the-invisible-man",
            "the-island-of-doctor-moreau",
            "the-war-of-the-worlds",
        ],
        "excluded_tier5_ids": ["the-lost-world"],
        "whole_work_holdouts": ["selected-short-fiction/the-star"],
    }


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


def test_expected_corpus_requires_consistent_nonempty_identity_lists() -> None:
    payload = _analysis_config()
    expected = payload["expected_corpus"]
    assert isinstance(expected, dict)
    expected["selected_witnesses"] = 2

    with pytest.raises(ValidationError, match="selected_witnesses|witness_ids"):
        AnalysisConfig.model_validate(payload)


def test_expected_corpus_rejects_duplicate_witness_ids() -> None:
    payload = _analysis_config()
    expected = payload["expected_corpus"]
    assert isinstance(expected, dict)
    expected["witness_ids"] = ["the-time-machine", "the-time-machine"]

    with pytest.raises(ValidationError, match="witness IDs must be unique"):
        AnalysisConfig.model_validate(payload)


def test_expected_corpus_requires_all_known_generated_paths() -> None:
    payload = _analysis_config()
    generated_paths = payload["generated_paths"]
    assert isinstance(generated_paths, dict)
    generated_paths.pop("analysis_report")

    with pytest.raises(ValidationError, match="generated paths must declare exactly"):
        AnalysisConfig.model_validate(payload)


@pytest.mark.parametrize(
    "created_at",
    [
        datetime(2026, 7, 15, 10),
        datetime(2026, 7, 15, 10, tzinfo=timezone(timedelta(hours=10))),
    ],
)
def test_holdout_manifest_rejects_naive_and_non_utc_created_at(created_at: datetime) -> None:
    payload = _holdout_manifest()
    payload["created_at"] = created_at

    with pytest.raises(ValidationError, match="UTC"):
        HoldoutManifest.model_validate(payload)


def test_holdout_manifest_preserves_valid_z_utc_timestamp() -> None:
    payload = _holdout_manifest()
    parsed = yaml.safe_load("created_at: 2026-07-15T10:00:00Z\n")
    payload["created_at"] = parsed["created_at"]

    manifest = HoldoutManifest.model_validate(payload)

    assert manifest.created_at == parsed["created_at"]
    assert manifest.created_at.tzinfo is not None
    assert manifest.created_at.utcoffset() == timedelta(0)


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


def test_claim_jurisdiction_and_counterexample_search_are_structured() -> None:
    payload = _ledger()["claims"][0]
    assert isinstance(payload, list) is False
    claim = EvidenceLedger.model_validate(_ledger()).claims[0]

    assert isinstance(claim.jurisdiction, ClaimJurisdiction)
    assert isinstance(claim.counterexample_search, CounterexampleSearch)
    assert claim.jurisdiction.scope == "continuity"
    assert claim.counterexample_search.outcome == "no_material_counterexample"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("roles", ["declared role", "declared role"], "roles must be unique"),
        (
            "eligible_witness_ids",
            ["the-time-machine", "the-time-machine"],
            "eligible_witness_ids must be unique",
        ),
    ],
)
def test_claim_jurisdiction_rejects_duplicate_members(
    field: str, value: list[str], message: str
) -> None:
    payload = {
        "scope": "continuity",
        "roles": ["declared role"],
        "eligible_witness_ids": ["the-time-machine"],
    }
    payload[field] = value
    with pytest.raises(ValidationError, match=message):
        ClaimJurisdiction.model_validate(payload)


def test_counterexample_search_rejects_duplicate_dimensions_and_passages() -> None:
    payload = {
        "witness_ids": ["the-time-machine"],
        "dimensions": ["frame-architecture"],
        "method": "manual_close_reading",
        "coverage": "targeted",
        "searched_passage_ids": ["the-time-machine:chapter-one:1:" + HASH[:12]],
        "outcome": "no_material_counterexample",
        "notes": "A documented search.",
    }
    payload["dimensions"] = ["frame-architecture", "frame-architecture"]
    with pytest.raises(ValidationError, match="dimensions must be unique"):
        CounterexampleSearch.model_validate(payload)

    payload["dimensions"] = ["frame-architecture"]
    payload["searched_passage_ids"] = ["p", "p"]
    with pytest.raises(ValidationError, match="searched_passage_ids must be unique"):
        CounterexampleSearch.model_validate(payload)


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
