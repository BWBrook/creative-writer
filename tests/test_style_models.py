from __future__ import annotations

from copy import deepcopy
import datetime
from typing import Any

import pytest
from pydantic import ValidationError

from creative_writer.style_models import (
    StyleLintReport,
    StyleProfile,
    StyleReferencePacket,
    StyleReviewFrontMatter,
)

SHA256_A = "a" * 64
SHA256_B = "b" * 64
SHA256_C = "c" * 64


def artifact(path: str, sha256: str = SHA256_A) -> dict[str, str]:
    return {"path": path, "sha256": sha256}


def manual_rule(
    *,
    rule_id: str = "practice-mediated-testimony",
    family: str = "practice",
) -> dict[str, Any]:
    return {
        "id": rule_id,
        "name": "Mediated testimony",
        "family": family,
        "advisory": "review",
        "claim_ids": ["mediated-testimony-frame"] if family == "practice" else [],
        "roles": ["frame"],
        "scope": "story",
        "evaluation_mode": "manual_question",
        "review_question": "Does the evidence reach the reader through testimony?",
        "source_passage_ids": ["the-time-machine:ii:101:b859a93fec21"],
        "variation_passage_ids": [],
        "control_passage_ids": (
            ["the-beetle:book-i:54:8440a05cc8de"]
            if family == "anti_drift"
            else []
        ),
        "packet_ids": ["frame-and-testimony"],
        "interpretation_limits": "This is an editorial question, not a verdict.",
    }


def valid_style_profile_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "profile_id": "wells-1895-1899",
        "version": "1.0.0",
        "title": "Late-1890s Wells operational style profile",
        "provenance": {
            "study_id": "time-expedition-wells-phase-2b",
            "analysis": artifact(
                "stories/time-expedition/source-study/analysis.yml", SHA256_A
            ),
            "source_registry": artifact(
                "stories/time-expedition/original/sources.yml", SHA256_B
            ),
            "holdout_manifest": artifact(
                "stories/time-expedition/source-study/holdouts.yml", SHA256_C
            ),
            "evidence_ledger": artifact(
                "stories/time-expedition/source-study/evidence-ledger.yml", SHA256_A
            ),
            "validation_record": artifact(
                "stories/time-expedition/source-study/validation.md", SHA256_B
            ),
            "passage_indexes": {
                "development": artifact(
                    "build/time-expedition/source-study/indexes/development.jsonl",
                    SHA256_A,
                ),
                "heldout_wells": artifact(
                    "build/time-expedition/source-study/indexes/heldout-wells.jsonl",
                    SHA256_B,
                ),
                "tier4_controls": artifact(
                    "build/time-expedition/source-study/indexes/tier4-controls.jsonl",
                    SHA256_C,
                ),
            },
            "approved_review_run_id": "final-audit-rereview",
        },
        "eligible_claim_statuses": ["validated", "qualified"],
        "default_packet_ids": ["frame-and-testimony"],
        "change_basis": "Initial operationalisation of approved evidence.",
        "profile_review_refs": [
            "source-study/validation.md#final-audit-rereview",
        ],
        "roles": [
            {
                "id": "frame",
                "label": "Frame",
                "description": "The chain through which testimony reaches the reader.",
                "phase_2b_roles": ["frame architecture", "testimony"],
            },
            {
                "id": "scientific-inference",
                "label": "Scientific inference",
                "description": "Observation moving into provisional explanation.",
                "phase_2b_roles": ["speculative method"],
            },
        ],
        "rules": [
            manual_rule(),
            {
                "id": "locator-qualified-inference",
                "name": "Qualified inference locator",
                "family": "practice",
                "advisory": "notice",
                "claim_ids": ["qualified-speculative-inference"],
                "roles": ["scientific-inference"],
                "scope": "passage",
                "evaluation_mode": "locator",
                "review_question": "Do qualifying terms mark genuine uncertainty?",
                "signal": {
                    "kind": "lexicon_locator",
                    "terms": ["perhaps", "probably"],
                    "max_examples": 8,
                },
                "source_passage_ids": ["the-time-machine:iv:147:5a08c0c8cfcb"],
                "variation_passage_ids": [],
                "control_passage_ids": [],
                "packet_ids": ["observation-and-exposition"],
                "interpretation_limits": "The signal locates terms; it does not judge them.",
            },
            {
                "id": "diagnostic-uniform-cadence",
                "name": "Uniform cadence diagnostic",
                "family": "diagnostic",
                "advisory": "review",
                "claim_ids": [],
                "roles": ["frame"],
                "scope": "chapter",
                "evaluation_mode": "contextual_diagnostic",
                "review_question": "Is unusually even cadence intentional?",
                "signal": {
                    "kind": "sentence_profile",
                    "speech_attribution_verbs": ["said", "asked"],
                    "minimum_sentences": 20,
                },
                "tolerance": {
                    "metric": "sentence_length_cv",
                    "minimum_sample_size": 20,
                    "review_below": 0.28,
                    "reference_witness_ids": ["the-time-machine"],
                    "rationale": "A broad review threshold, not a target cadence.",
                },
                "source_passage_ids": [],
                "variation_passage_ids": [],
                "control_passage_ids": [],
                "packet_ids": [],
                "interpretation_limits": "This diagnostic is not a Wells requirement.",
            },
            manual_rule(
                rule_id="anti-drift-neighbouring-adventure-voice",
                family="anti_drift",
            ),
        ],
    }


def valid_reference_packet_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": "frame-and-testimony",
        "title": "Frame and testimony",
        "purpose": "Compare mediation, testimony, and authentic variation.",
        "profile_id": "wells-1895-1899",
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
                "permitted_use": "Study the evidentiary sequence.",
                "selection_note": "A compact example of mediated testimony.",
                "context_radius": 2,
            }
        ],
        "prohibited_uses": ["Do not copy local wording."],
        "anti_copying_guidance": (
            "Study narrative method and cadence without borrowing phrases."
        ),
    }


def valid_style_lint_report_payload() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "story_slug": "time-expedition",
        "story_title": "The Last Week of the Permian",
        "scope": "story",
        "chapter_selector": None,
        "profile_id": "wells-1895-1899",
        "profile_version": "1.0.0",
        "profile_sha256": SHA256_A,
        "evidence_ledger_sha256": SHA256_B,
        "validation_record_sha256": SHA256_C,
        "packet_manifest_sha256s": {"frame-and-testimony": SHA256_A},
        "chapters": [
            {
                "stub": "stories/time-expedition/chapter-stubs/01-permian.md",
                "manuscript": "stories/time-expedition/manuscript/01-permian.md",
                "title": "The Last Week of the Permian",
                "summary": "A recovered account of the expedition.",
                "roles": ["frame"],
                "packet_ids": ["frame-and-testimony"],
                "word_count": 4200,
            }
        ],
        "role_caveat": (
            "Chapter-level role assignment is coarse and does not classify "
            "every paragraph."
        ),
        "findings": [
            {
                "id": "finding-001",
                "category": "wells_practice",
                "manuscript": "stories/time-expedition/manuscript/01-permian.md",
                "line_start": 12,
                "line_end": 14,
                "observed_signal": "The account shifts from observation to inference.",
                "rule_id": "practice-qualified-inference",
                "rule_family": "practice",
                "advisory": "review",
                "roles": ["scientific-inference"],
                "scope": "passage",
                "claim_ids": ["qualified-speculative-inference"],
                "claim_statuses": {
                    "qualified-speculative-inference": "qualified",
                },
                "claim_jurisdictions": [
                    {
                        "scope": "role_specific",
                        "roles": ["speculative method"],
                        "eligible_witness_ids": ["the-time-machine"],
                    }
                ],
                "source_passage_ids": [
                    "the-time-machine:iv:147:5a08c0c8cfcb"
                ],
                "editorial_question": "Is the inference adequately qualified?",
                "limitations": "The finding prompts review and makes no verdict.",
            }
        ],
        "practice_questions": [
            {
                "rule_id": "practice-qualified-inference",
                "advisory": "review",
                "roles": ["scientific-inference"],
                "claim_ids": ["qualified-speculative-inference"],
                "claim_statuses": {
                    "qualified-speculative-inference": "qualified",
                },
                "claim_jurisdictions": [
                    {
                        "scope": "role_specific",
                        "roles": ["speculative method"],
                        "eligible_witness_ids": ["the-time-machine"],
                    }
                ],
                "question": "Does inference proceed from observed particulars?",
                "source_passage_ids": [
                    "the-time-machine:iv:147:5a08c0c8cfcb"
                ],
                "interpretation_limits": "This remains a manual editorial question.",
            }
        ],
        "diagnostics": [
            {
                "rule_id": "diagnostic-uniform-cadence",
                "manuscript": "stories/time-expedition/manuscript/01-permian.md",
                "manuscripts": [
                    "stories/time-expedition/manuscript/01-permian.md"
                ],
                "roles": ["frame"],
                "measurements": {
                    "sentence_length_cv": 0.31,
                    "note": "Broad contextual measure",
                    "unavailable_measure": None,
                },
                "sample_size": 42,
                "tolerance_note": "Above the broad review-below threshold.",
                "triggered": False,
                "limitations": "Sentence splitting is approximate.",
            }
        ],
        "generic_ai": {
            "status": "complete",
            "scanner": "creative-writer ai-audit",
            "group_names": ["contrastive_parallelism"],
            "finding_ids": [],
            "caution": "Generic AI signals are not positive Wells evidence.",
            "notice": None,
        },
        "limitations": ["No finding is an authorship or authenticity verdict."],
        "next_steps": ["Review findings against manuscript context."],
        "partial": False,
    }


def valid_style_review_payload() -> dict[str, Any]:
    return {
        "review_id": "chapter-one-first-pass",
        "date": datetime.date(2026, 7, 31),
        "scope": "chapter",
        "manuscripts": ["manuscript/01-last-week-of-the-permian.md"],
        "profile_id": "wells-1895-1899",
        "profile_version": "1.0.0",
        "lint_report": {
            "path": (
                "build/time-expedition/style/chapters/"
                "01-last-week-of-the-permian-lint-report.json"
            ),
            "sha256": SHA256_A,
        },
        "reference_packets": ["frame-and-testimony"],
        "reviewer_id": "codex",
        "reviewer_role": "ai",
        "outcome": "qualified",
    }


def test_style_profile_parses_complete_valid_payload() -> None:
    profile = StyleProfile.model_validate(valid_style_profile_payload())

    assert profile.profile_id == "wells-1895-1899"
    assert profile.provenance.passage_indexes.heldout_wells.sha256 == SHA256_B
    assert profile.rules[1].signal.kind == "lexicon_locator"
    assert profile.rules[2].tolerance.review_below == 0.28


def test_reference_packet_parses_complete_valid_payload() -> None:
    packet = StyleReferencePacket.model_validate(valid_reference_packet_payload())

    assert packet.id == "frame-and-testimony"
    assert packet.entries[0].context_radius == 2


def test_style_lint_report_preserves_advisory_contract_without_score() -> None:
    report = StyleLintReport.model_validate(valid_style_lint_report_payload())

    assert report.findings[0].advisory == "review"
    assert report.findings[0].claim_statuses == {
        "qualified-speculative-inference": "qualified"
    }
    assert report.practice_questions[0].claim_statuses == {
        "qualified-speculative-inference": "qualified"
    }
    assert report.generic_ai.status == "complete"
    assert "score" not in report.model_dump()


def test_style_review_accepts_ai_chapter_decision() -> None:
    payload = valid_style_review_payload()
    payload["outcome"] = "accepted"

    review = StyleReviewFrontMatter.model_validate(payload)

    assert review.scope == "chapter"
    assert review.reviewer_role == "ai"
    assert review.outcome == "accepted"
    assert review.date == datetime.date(2026, 7, 31)


def test_style_review_accepts_human_story_milestone() -> None:
    payload = valid_style_review_payload()
    payload.update(scope="story", reviewer_id="barry", reviewer_role="human")
    payload["outcome"] = "accepted"

    review = StyleReviewFrontMatter.model_validate(payload)

    assert review.scope == "story"
    assert review.reviewer_role == "human"
    assert review.outcome == "accepted"


@pytest.mark.parametrize("scope", ["story", "anthology"])
def test_style_review_milestone_acceptance_requires_human_reviewer(
    scope: str,
) -> None:
    payload = valid_style_review_payload()
    payload.update(scope=scope, reviewer_role="ai", outcome="accepted")

    with pytest.raises(ValidationError, match="human"):
        StyleReviewFrontMatter.model_validate(payload)


def test_style_review_rejects_unknown_outcome() -> None:
    payload = valid_style_review_payload()
    payload["outcome"] = "approved"

    with pytest.raises(ValidationError):
        StyleReviewFrontMatter.model_validate(payload)


@pytest.mark.parametrize(
    "manuscript",
    [
        "../manuscript/chapter.md",
        "manuscript/../chapter.md",
        "drafts/chapter.md",
        "manuscript/chapter.txt",
    ],
)
def test_style_review_requires_canonical_markdown_below_manuscript(
    manuscript: str,
) -> None:
    payload = valid_style_review_payload()
    payload["manuscripts"] = [manuscript]

    with pytest.raises(ValidationError, match="manuscript"):
        StyleReviewFrontMatter.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "duplicate"),
    [
        ("manuscripts", "manuscript/01-last-week-of-the-permian.md"),
        ("reference_packets", "frame-and-testimony"),
    ],
)
def test_style_review_rejects_duplicate_reference_lists(
    field: str,
    duplicate: str,
) -> None:
    payload = valid_style_review_payload()
    payload[field].append(duplicate)

    with pytest.raises(ValidationError, match="unique"):
        StyleReviewFrontMatter.model_validate(payload)


def test_style_review_requires_canonical_lint_report_path() -> None:
    payload = valid_style_review_payload()
    payload["lint_report"]["path"] = "build/../lint-report.json"

    with pytest.raises(ValidationError, match="relative POSIX"):
        StyleReviewFrontMatter.model_validate(payload)


def test_style_review_front_matter_is_strict() -> None:
    payload = valid_style_review_payload()
    payload["authenticity_score"] = 91

    with pytest.raises(ValidationError):
        StyleReviewFrontMatter.model_validate(payload)


@pytest.mark.parametrize("section", ["findings", "practice_questions"])
@pytest.mark.parametrize("mutation", ["missing", "additional"])
def test_style_report_claim_status_keys_exactly_match_claim_ids(
    section: str,
    mutation: str,
) -> None:
    payload = valid_style_lint_report_payload()
    claim_statuses = payload[section][0]["claim_statuses"]
    if mutation == "missing":
        claim_statuses.clear()
    else:
        claim_statuses["unrelated-claim"] = "validated"

    with pytest.raises(
        ValidationError,
        match="claim status keys must exactly match claim IDs",
    ):
        StyleLintReport.model_validate(payload)


@pytest.mark.parametrize("section", ["findings", "practice_questions"])
@pytest.mark.parametrize("mutation", ["missing", "additional", "claimless"])
def test_style_report_requires_exactly_one_jurisdiction_per_claim(
    section: str,
    mutation: str,
) -> None:
    payload = valid_style_lint_report_payload()
    record = payload[section][0]
    if mutation == "missing":
        record["claim_jurisdictions"] = []
    elif mutation == "additional":
        record["claim_jurisdictions"].append(
            deepcopy(record["claim_jurisdictions"][0])
        )
    else:
        record["claim_ids"] = []
        record["claim_statuses"] = {}

    with pytest.raises(
        ValidationError,
        match="exactly one claim jurisdiction per claim ID",
    ):
        StyleLintReport.model_validate(payload)


@pytest.mark.parametrize(
    ("factory", "schema_version"),
    [
        (valid_style_profile_payload, 2),
        (valid_reference_packet_payload, 2),
        (valid_style_lint_report_payload, 2),
    ],
)
def test_style_schemas_reject_unknown_versions(factory, schema_version: int) -> None:
    payload = factory()
    payload["schema_version"] = schema_version

    with pytest.raises(ValidationError):
        if factory is valid_style_profile_payload:
            StyleProfile.model_validate(payload)
        elif factory is valid_reference_packet_payload:
            StyleReferencePacket.model_validate(payload)
        else:
            StyleLintReport.model_validate(payload)


def test_style_profile_rejects_duplicate_role_ids() -> None:
    payload = valid_style_profile_payload()
    payload["roles"].append(deepcopy(payload["roles"][0]))

    with pytest.raises(ValidationError, match="role IDs must be unique"):
        StyleProfile.model_validate(payload)


def test_style_profile_rejects_duplicate_rule_ids() -> None:
    payload = valid_style_profile_payload()
    payload["rules"].append(deepcopy(payload["rules"][0]))

    with pytest.raises(ValidationError, match="rule IDs must be unique"):
        StyleProfile.model_validate(payload)


def test_reference_packet_rejects_duplicate_entry_ids() -> None:
    payload = valid_reference_packet_payload()
    payload["entries"].append(deepcopy(payload["entries"][0]))

    with pytest.raises(ValidationError, match="entry IDs must be unique"):
        StyleReferencePacket.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("family", "prescription"),
        ("advisory", "error"),
        ("scope", "sentence"),
        ("evaluation_mode", "rewrite"),
    ],
)
def test_style_profile_rejects_unknown_rule_enums(field: str, value: str) -> None:
    payload = valid_style_profile_payload()
    payload["rules"][0][field] = value

    with pytest.raises(ValidationError):
        StyleProfile.model_validate(payload)


def test_reference_packet_rejects_unknown_entry_kind() -> None:
    payload = valid_reference_packet_payload()
    payload["entries"][0]["kind"] = "model_text"

    with pytest.raises(ValidationError):
        StyleReferencePacket.model_validate(payload)


@pytest.mark.parametrize(
    ("factory", "field"),
    [
        (valid_style_profile_payload, "version"),
        (valid_reference_packet_payload, "profile_version"),
        (valid_style_lint_report_payload, "profile_version"),
    ],
)
def test_style_schemas_reject_malformed_semantic_versions(factory, field: str) -> None:
    payload = factory()
    payload[field] = "1.0"

    with pytest.raises(ValidationError):
        if factory is valid_style_profile_payload:
            StyleProfile.model_validate(payload)
        elif factory is valid_reference_packet_payload:
            StyleReferencePacket.model_validate(payload)
        else:
            StyleLintReport.model_validate(payload)


def test_style_profile_rejects_malformed_hash() -> None:
    payload = valid_style_profile_payload()
    payload["provenance"]["evidence_ledger"]["sha256"] = "not-a-sha256"

    with pytest.raises(ValidationError):
        StyleProfile.model_validate(payload)


def test_style_profile_rejects_empty_required_text() -> None:
    payload = valid_style_profile_payload()
    payload["change_basis"] = "   "

    with pytest.raises(ValidationError):
        StyleProfile.model_validate(payload)


def test_style_profile_rejects_duplicate_id_list_members() -> None:
    payload = valid_style_profile_payload()
    payload["rules"][0]["roles"].append("frame")

    with pytest.raises(ValidationError, match="rule roles must be unique"):
        StyleProfile.model_validate(payload)


def test_style_profile_rejects_noncanonical_provenance_path() -> None:
    payload = valid_style_profile_payload()
    payload["provenance"]["analysis"]["path"] = "../analysis.yml"

    with pytest.raises(ValidationError, match="relative POSIX"):
        StyleProfile.model_validate(payload)


def test_style_profile_rejects_manual_rule_with_signal() -> None:
    payload = valid_style_profile_payload()
    payload["rules"][0]["signal"] = {
        "kind": "lexicon_locator",
        "terms": ["perhaps"],
    }

    with pytest.raises(
        ValidationError, match="manual questions cannot declare a signal"
    ):
        StyleProfile.model_validate(payload)


def test_style_profile_rejects_locator_without_signal() -> None:
    payload = valid_style_profile_payload()
    del payload["rules"][1]["signal"]

    with pytest.raises(
        ValidationError, match="locator and contextual rules require a signal"
    ):
        StyleProfile.model_validate(payload)


def test_style_profile_rejects_practice_rule_without_claim() -> None:
    payload = valid_style_profile_payload()
    payload["rules"][0]["claim_ids"] = []

    with pytest.raises(
        ValidationError, match="practice rules require at least one Phase 2B claim"
    ):
        StyleProfile.model_validate(payload)


def test_style_profile_rejects_controls_on_non_anti_drift_rule() -> None:
    payload = valid_style_profile_payload()
    payload["rules"][0]["control_passage_ids"] = [
        "the-beetle:book-i:54:8440a05cc8de"
    ]

    with pytest.raises(
        ValidationError, match="Tier 4 controls belong only to anti-drift rules"
    ):
        StyleProfile.model_validate(payload)


def test_style_profile_rejects_tolerance_without_numeric_bound() -> None:
    payload = valid_style_profile_payload()
    del payload["rules"][2]["tolerance"]["review_below"]

    with pytest.raises(ValidationError, match="at least one numeric bound"):
        StyleProfile.model_validate(payload)


@pytest.mark.parametrize("field", ["review_below", "review_above"])
@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf")],
    ids=["nan", "positive-infinity", "negative-infinity"],
)
def test_style_profile_rejects_non_finite_tolerance_bounds(
    field: str, value: float
) -> None:
    payload = valid_style_profile_payload()
    payload["rules"][2]["tolerance"][field] = value

    with pytest.raises(ValidationError, match="tolerance bounds must be finite"):
        StyleProfile.model_validate(payload)


@pytest.mark.parametrize(
    "signal",
    [
        {"kind": "dialogue_profile", "minimum_words": 200},
        {
            "kind": "repeated_ngram",
            "ngram_size": 3,
            "minimum_occurrences": 3,
            "minimum_words": 300,
            "stop_words": ["the", "and"],
        },
        {
            "kind": "paragraph_opening",
            "prefix_words": 3,
            "minimum_occurrences": 3,
            "minimum_paragraphs": 8,
        },
    ],
)
def test_style_profile_accepts_each_remaining_signal_kind(
    signal: dict[str, Any],
) -> None:
    payload = valid_style_profile_payload()
    payload["rules"][2]["signal"] = signal

    profile = StyleProfile.model_validate(payload)

    assert profile.rules[2].signal.kind == signal["kind"]


def test_reference_packet_rejects_positive_tier_four_entry() -> None:
    payload = valid_reference_packet_payload()
    payload["entries"][0]["authority_tier"] = 4

    with pytest.raises(ValidationError, match="Tier 4"):
        StyleReferencePacket.model_validate(payload)


def test_style_lint_report_rejects_score_field() -> None:
    payload = valid_style_lint_report_payload()
    payload["score"] = 87

    with pytest.raises(ValidationError):
        StyleLintReport.model_validate(payload)


def test_style_lint_report_rejects_reversed_finding_line_range() -> None:
    payload = valid_style_lint_report_payload()
    payload["findings"][0]["line_start"] = 20
    payload["findings"][0]["line_end"] = 10

    with pytest.raises(
        ValidationError,
        match="line_end must be greater than or equal to line_start",
    ):
        StyleLintReport.model_validate(payload)


@pytest.mark.parametrize(
    ("status", "partial"),
    [
        ("complete", True),
        ("disabled", True),
        ("unavailable", False),
    ],
)
def test_style_lint_report_rejects_inconsistent_partial_state(
    status: str, partial: bool
) -> None:
    payload = valid_style_lint_report_payload()
    payload["generic_ai"]["status"] = status
    payload["partial"] = partial

    with pytest.raises(ValidationError, match="partial"):
        StyleLintReport.model_validate(payload)


def test_style_lint_report_accepts_unavailable_ai_as_partial() -> None:
    payload = valid_style_lint_report_payload()
    payload["generic_ai"]["status"] = "unavailable"
    payload["generic_ai"]["scanner"] = None
    payload["generic_ai"]["notice"] = "The external scanner is unavailable."
    payload["partial"] = True

    report = StyleLintReport.model_validate(payload)

    assert report.partial is True


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf")],
    ids=["nan", "positive-infinity", "negative-infinity"],
)
def test_style_lint_report_rejects_non_finite_diagnostic_measurements(
    value: float,
) -> None:
    payload = valid_style_lint_report_payload()
    payload["diagnostics"][0]["measurements"]["sentence_length_cv"] = value

    with pytest.raises(
        ValidationError, match="diagnostic float measurements must be finite"
    ):
        StyleLintReport.model_validate(payload)


def test_style_lint_report_accepts_story_diagnostic_provenance() -> None:
    payload = valid_style_lint_report_payload()
    diagnostic = payload["diagnostics"][0]
    diagnostic["manuscript"] = None

    report = StyleLintReport.model_validate(payload)

    assert report.diagnostics[0].manuscript is None
    assert report.diagnostics[0].manuscripts == [
        "stories/time-expedition/manuscript/01-permian.md"
    ]


@pytest.mark.parametrize(
    ("manuscript", "manuscripts"),
    [
        (
            "stories/time-expedition/manuscript/01-permian.md",
            [],
        ),
        (
            "stories/time-expedition/manuscript/01-permian.md",
            [
                "stories/time-expedition/manuscript/01-permian.md",
                "stories/time-expedition/manuscript/01-permian.md",
            ],
        ),
        (
            "stories/time-expedition/manuscript/01-permian.md",
            ["stories/time-expedition/manuscript/02-return.md"],
        ),
        (
            None,
            ["../manuscript.md"],
        ),
    ],
    ids=[
        "empty",
        "duplicate",
        "chapter-mismatch",
        "noncanonical",
    ],
)
def test_style_lint_report_rejects_invalid_diagnostic_provenance(
    manuscript: str | None,
    manuscripts: list[str],
) -> None:
    payload = valid_style_lint_report_payload()
    diagnostic = payload["diagnostics"][0]
    diagnostic["manuscript"] = manuscript
    diagnostic["manuscripts"] = manuscripts

    with pytest.raises(ValidationError):
        StyleLintReport.model_validate(payload)


def test_style_lint_report_rejects_noncanonical_manuscript_path() -> None:
    payload = valid_style_lint_report_payload()
    payload["findings"][0]["manuscript"] = "../manuscript.md"

    with pytest.raises(ValidationError, match="relative POSIX"):
        StyleLintReport.model_validate(payload)
