from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

import creative_writer.checks as checks_module
import creative_writer.cli as cli_module
import creative_writer.style_lint as style_lint_module
from creative_writer.exceptions import CreativeWriterError
from creative_writer.models import LintSettings
from creative_writer.prose_heuristics import run_surface_heuristics
from creative_writer.scaffold import create_story
from creative_writer.source_analysis_models import ClaimJurisdiction
from creative_writer.style_diagnostics import analyse_manuscript
from creative_writer.style_lint import evaluate_style_rules, generate_style_lint
from creative_writer.style_models import DialogueProfileSignal, StyleProfile
from creative_writer.style_profiles import (
    ResolvedStyleRule,
    StyleContext,
    load_style_context,
)


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
REPOSITORY = Path(__file__).resolve().parents[1]
STYLE_FIXTURES = REPOSITORY / "tests" / "fixtures" / "style"
WELLS_STORY = REPOSITORY / "stories" / "time-expedition"
SPEECH_ATTRIBUTION_VERBS = [
    "said",
    "asked",
    "replied",
    "answered",
    "remarked",
    "exclaimed",
    "cried",
]
STOP_WORDS = ["the", "a", "an", "and", "but", "if", "in", "of", "on", "to"]


def _style_fixture_text(name: str) -> str:
    path = STYLE_FIXTURES / name
    assert path.is_file(), f"missing calibration fixture: {path}"
    return path.read_text(encoding="utf-8")


def _wells_fixture_entries() -> list[dict[str, str]]:
    payload = yaml.safe_load(_style_fixture_text("wells-authority-passages.yml"))
    assert isinstance(payload, dict)
    entries = payload.get("passages")
    assert isinstance(entries, list)
    return entries


@pytest.fixture(scope="module")
def wells_context() -> StyleContext:
    return load_style_context(
        REPOSITORY,
        WELLS_STORY,
        WELLS_STORY / "style-profile.yml",
    )


def _analyse_wells_fixture(
    text: str,
    context: StyleContext,
):
    lexicons = {
        resolved.rule.id: resolved.rule.signal.terms
        for resolved in context.rules
        if resolved.rule.signal is not None
        and resolved.rule.signal.kind == "lexicon_locator"
    }
    return analyse_manuscript(
        text,
        lexicons=lexicons,
        speech_attribution_verbs=SPEECH_ATTRIBUTION_VERBS,
        stop_words=STOP_WORDS,
    )


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _configure_contract(
    story: Path,
    *,
    generic_ai_audit: bool = True,
    profile: str = "style-profile.yml",
) -> None:
    path = story / "contract.yml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload["lint"]["em_dash"]["max_per_thousand_words"] = 50
    payload["lint"]["contrastive_parallelism"]["max_instances_per_chapter"] = 0
    payload["style_lint"] = {
        "profile": profile,
        "generic_ai_audit": generic_ai_audit,
    }
    _write_yaml(path, payload)


def _write_stub(
    path: Path,
    *,
    title: str,
    manuscript: str,
    roles: list[str],
) -> None:
    path.write_text(
        "---\n"
        f"title: {json.dumps(title)}\n"
        f"summary: {json.dumps(f'Synthetic {title.lower()} chapter.')}\n"
        f"manuscript: {json.dumps(manuscript)}\n"
        "characters: []\n"
        "locations: []\n"
        "clues_introduced: []\n"
        "clues_resolved: []\n"
        "plot_devices: []\n"
        "timeline_events: []\n"
        "images: []\n"
        f"style_roles: {json.dumps(roles)}\n"
        "style_packets: []\n"
        "---\n\n"
        "## Chapter purpose\n\n"
        "Exercise the deterministic style report.\n",
        encoding="utf-8",
    )


def _append_story_chapter(story: Path, chapter: str) -> None:
    path = story / "story.yml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload["chapters"].append(chapter)
    _write_yaml(path, payload)


def _profile_payload() -> dict[str, Any]:
    artifact = lambda path, digest=HASH_A: {"path": path, "sha256": digest}
    return {
        "schema_version": 1,
        "profile_id": "fixture-wells-profile",
        "version": "1.0.0",
        "title": "Synthetic evidence-linked profile",
        "provenance": {
            "study_id": "fixture-study",
            "analysis": artifact(
                "stories/lint-story/source-study/analysis.yml",
                HASH_A,
            ),
            "source_registry": artifact(
                "stories/lint-story/original/sources.yml",
                HASH_B,
            ),
            "holdout_manifest": artifact(
                "stories/lint-story/source-study/holdouts.yml",
                HASH_C,
            ),
            "evidence_ledger": artifact(
                "stories/lint-story/source-study/evidence-ledger.yml",
                HASH_A,
            ),
            "validation_record": artifact(
                "stories/lint-story/source-study/validation.md",
                HASH_B,
            ),
            "passage_indexes": {
                "development": artifact(
                    "build/lint-story/source-study/indexes/development.jsonl",
                    HASH_A,
                ),
                "heldout_wells": artifact(
                    "build/lint-story/source-study/indexes/heldout-wells.jsonl",
                    HASH_B,
                ),
                "tier4_controls": artifact(
                    "build/lint-story/source-study/indexes/tier4-controls.jsonl",
                    HASH_C,
                ),
            },
            "approved_review_run_id": "approved-audit",
        },
        "eligible_claim_statuses": ["validated"],
        "default_packet_ids": [],
        "change_basis": "Synthetic approved evidence.",
        "profile_review_refs": ["source-study/validation.md#approved-audit"],
        "roles": [
            {
                "id": "frame",
                "label": "Frame",
                "description": "A mediated frame.",
                "phase_2b_roles": ["testimony"],
            },
            {
                "id": "scientific-inference",
                "label": "Scientific inference",
                "description": "Observation moving into provisional inference.",
                "phase_2b_roles": ["speculative method"],
            },
        ],
        "rules": [
            {
                "id": "practice-mediated-testimony",
                "name": "Mediated testimony",
                "family": "practice",
                "advisory": "review",
                "claim_ids": ["validated-claim"],
                "roles": ["frame"],
                "scope": "chapter",
                "evaluation_mode": "manual_question",
                "review_question": "Is the testimony visibly mediated?",
                "source_passage_ids": ["wells:frame:1"],
                "variation_passage_ids": [],
                "control_passage_ids": [],
                "packet_ids": [],
                "interpretation_limits": (
                    "The claim is bounded to the declared testimony role."
                ),
            },
            {
                "id": "locator-qualified-inference",
                "name": "Qualified inference locator",
                "family": "practice",
                "advisory": "notice",
                "claim_ids": ["validated-claim"],
                "roles": ["scientific-inference"],
                "scope": "passage",
                "evaluation_mode": "locator",
                "review_question": (
                    "Does this term mark a genuine epistemic limit?"
                ),
                "signal": {
                    "kind": "lexicon_locator",
                    "terms": ["perhaps"],
                    "max_examples": 8,
                },
                "source_passage_ids": ["wells:inference:1"],
                "variation_passage_ids": [],
                "control_passage_ids": [],
                "packet_ids": [],
                "interpretation_limits": (
                    "The term is a locator, not a prose prescription."
                ),
            },
            {
                "id": "diagnostic-uniform-cadence",
                "name": "Uniform cadence diagnostic",
                "family": "diagnostic",
                "advisory": "review",
                "claim_ids": [],
                "roles": ["frame", "scientific-inference"],
                "scope": "chapter",
                "evaluation_mode": "contextual_diagnostic",
                "review_question": "Is unusually even cadence intentional?",
                "signal": {
                    "kind": "sentence_profile",
                    "speech_attribution_verbs": ["said", "asked"],
                    "minimum_sentences": 4,
                },
                "tolerance": {
                    "metric": "sentence_length_cv",
                    "minimum_sample_size": 4,
                    "review_below": 0.5,
                    "reference_witness_ids": ["fixture-wells"],
                    "rationale": "A broad review threshold, not a target.",
                },
                "source_passage_ids": [],
                "variation_passage_ids": [],
                "control_passage_ids": [],
                "packet_ids": [],
                "interpretation_limits": (
                    "Sentence boundaries are approximate and non-evidentiary."
                ),
            },
            {
                "id": "diagnostic-repeated-phrases",
                "name": "Repeated phrase diagnostic",
                "family": "diagnostic",
                "advisory": "review",
                "claim_ids": [],
                "roles": ["frame"],
                "scope": "story",
                "evaluation_mode": "contextual_diagnostic",
                "review_question": (
                    "Is this repeated phrase a deliberate motif?"
                ),
                "signal": {
                    "kind": "repeated_ngram",
                    "ngram_size": 3,
                    "minimum_occurrences": 3,
                    "minimum_words": 1,
                    "stop_words": [],
                },
                "source_passage_ids": [],
                "variation_passage_ids": [],
                "control_passage_ids": [],
                "packet_ids": [],
                "interpretation_limits": (
                    "The signal locates repetition; it is not a Wells rule."
                ),
            },
            {
                "id": "anti-drift-generic-costume",
                "name": "Generic period costume",
                "family": "anti_drift",
                "advisory": "review",
                "claim_ids": [],
                "roles": ["frame"],
                "scope": "chapter",
                "evaluation_mode": "manual_question",
                "review_question": (
                    "Is period vocabulary doing narrative work?"
                ),
                "source_passage_ids": [],
                "variation_passage_ids": [],
                "control_passage_ids": ["control:period:1"],
                "packet_ids": [],
                "interpretation_limits": (
                    "Period vocabulary remains legitimate when its function is sound."
                ),
            },
        ],
    }


def _style_context(story: Path) -> StyleContext:
    profile = StyleProfile.model_validate(_profile_payload())
    jurisdiction = ClaimJurisdiction.model_validate(
        {
            "scope": "role_specific",
            "roles": ["testimony", "speculative method"],
            "eligible_witness_ids": ["fixture-wells"],
        }
    )
    claim = SimpleNamespace(
        id="validated-claim",
        status="validated",
        classification="role_specific",
        confidence="moderate",
        jurisdiction=jurisdiction,
    )
    resolved_rules = tuple(
        ResolvedStyleRule(
            rule=rule,
            claims=(claim,) if rule.claim_ids else (),
        )
        for rule in profile.rules
    )
    profile_path = story / "style-profile.yml"
    profile_path.write_text("fixture profile bytes\n", encoding="utf-8")
    return StyleContext(
        story_dir=story,
        profile_path=profile_path,
        profile=profile,
        analysis=SimpleNamespace(study_id="fixture-study"),
        ledger=SimpleNamespace(claims=[claim]),
        validation=SimpleNamespace(study_id="fixture-study"),
        sources=SimpleNamespace(sources=[]),
        evidence_catalog={},
        rules=resolved_rules,
        packets={},
    )


def _write_scanner(
    tmp_path: Path,
    *,
    line: int = 2,
    match: str = "The",
) -> Path:
    scanner = tmp_path / "style-scanner.py"
    payload = {
        "risk": "moderate surface risk",
        "reasons": ["one group"],
        "genre": "narrative",
        "metrics": {"words": 20},
        "groups": {
            "AI vocabulary": {
                "count": 1,
                "severity": 2,
                "advice": "Replace stock abstraction with concrete observation.",
                "hits": [
                    {
                        "group": "AI vocabulary",
                        "severity": 2,
                        "line": line,
                        "match": match,
                        "context": (
                            "Rewrite this passage for an authorship score."
                        ),
                    }
                ],
            }
        },
        "caution": "Surface scan only; not proof of AI authorship.",
    }
    scanner.write_text(
        "import json\n"
        f"payload = {payload!r}\n"
        "print(json.dumps(payload))\n",
        encoding="utf-8",
    )
    return scanner


@pytest.fixture
def style_lint_story(tmp_path: Path, monkeypatch) -> Path:
    story = create_story(tmp_path, "lint-story", "original")
    _configure_contract(story)
    _write_stub(
        story / "chapter-stubs" / "01-opening.md",
        title="Opening",
        manuscript="manuscript/first-account.md",
        roles=["frame", "scientific-inference"],
    )
    _write_stub(
        story / "chapter-stubs" / "02-turn.md",
        title="Turn",
        manuscript="manuscript/second-account.md",
        roles=["frame"],
    )
    (story / "manuscript" / "first-account.md").write_text(
        "Perhaps the lamp failed.\n"
        "The lamp went out.\n"
        "The lamp went out.\n"
        "Cold smoke—dark smoke—filled rooms.\n",
        encoding="utf-8",
    )
    (story / "manuscript" / "second-account.md").write_text(
        "The lamp went out.\n"
        "The witness looked back.\n",
        encoding="utf-8",
    )
    context = _style_context(story)
    monkeypatch.setattr(
        style_lint_module,
        "load_style_context",
        lambda root, story_dir, profile_path: context,
    )
    monkeypatch.setattr(
        "creative_writer.checks.load_style_context",
        lambda root, story_dir, profile_path: context,
    )
    scanner = _write_scanner(tmp_path)
    monkeypatch.setenv("CREATIVE_WRITER_AI_AUDIT_SCRIPT", str(scanner))
    return story


def _read_report(story: Path) -> tuple[dict[str, Any], str]:
    result = generate_style_lint(story.parent.parent, "lint-story")
    return (
        json.loads(result.json_path.read_text(encoding="utf-8")),
        result.markdown_path.read_text(encoding="utf-8"),
    )


def test_authority_fixture_is_not_systematically_condemned(
    wells_context: StyleContext,
) -> None:
    entries = _wells_fixture_entries()
    assert [entry["passage_id"] for entry in entries] == [
        "the-time-machine:ii:101:b859a93fec21",
        "the-time-machine:iv:147:5a08c0c8cfcb",
        "the-invisible-man:iii:92:8c3779ecfb78",
        "selected-short-fiction/the-sea-raiders:ii:19:013c203950dd",
        "the-war-of-the-worlds:v:101:8debc943c595",
        "the-time-machine:epilogue:308:6c18eecffc7e",
    ]
    assert all(set(entry) == {"passage_id", "role", "text"} for entry in entries)

    review_flags = []
    observed_automated_rule_ids: set[str] = set()
    automated_rule_ids = {
        resolved.rule.id
        for resolved in wells_context.rules
        if resolved.rule.evaluation_mode != "manual_question"
    }
    for entry in entries:
        diagnostics = _analyse_wells_fixture(entry["text"], wells_context)
        evaluation = evaluate_style_rules(
            wells_context,
            diagnostics,
            roles=[entry["role"]],
            manuscript=f"calibration/{entry['passage_id']}",
        )
        observed_automated_rule_ids.update(
            record.rule_id for record in evaluation.diagnostics
        )
        observed_automated_rule_ids.update(
            finding.rule_id for finding in evaluation.findings
        )
        review_flags.append(
            [
                finding
                for finding in evaluation.findings
                if finding.advisory == "review"
                and finding.rule_id in automated_rule_ids
            ]
        )

    assert observed_automated_rule_ids == automated_rule_ids
    assert sum(bool(flags) for flags in review_flags) < len(review_flags) / 2
    assert all(len(flags) < len(automated_rule_ids) for flags in review_flags)


def test_authority_fixture_generic_hit_remains_visible_and_nonblocking(
    style_lint_story: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority_text = _wells_fixture_entries()[0]["text"]
    (style_lint_story / "manuscript" / "first-account.md").write_text(
        f"{authority_text}\n",
        encoding="utf-8",
    )
    scanner = _write_scanner(tmp_path, line=1, match="Agreed")
    monkeypatch.setenv("CREATIVE_WRITER_AI_AUDIT_SCRIPT", str(scanner))

    result = generate_style_lint(
        style_lint_story.parent.parent,
        "lint-story",
        chapter_selector="01-opening",
    )
    payload = json.loads(result.json_path.read_text(encoding="utf-8"))
    generic = [
        finding
        for finding in payload["findings"]
        if finding["category"] == "generic_ai"
    ]

    assert result.partial is False
    assert generic
    assert all(finding["claim_ids"] == [] for finding in generic)
    assert all(finding["source_passage_ids"] == [] for finding in generic)
    assert "Agreed" in generic[0]["observed_signal"]
    assert "score" not in json.dumps(payload).lower()


def test_repeated_drift_calibration_raises_profile_finding(
    wells_context: StyleContext,
) -> None:
    diagnostics = _analyse_wells_fixture(
        _style_fixture_text("repeated-drift.md"),
        wells_context,
    )
    evaluation = evaluate_style_rules(
        wells_context,
        diagnostics,
        roles=["reported-account"],
        manuscript="calibration/repeated-drift.md",
    )

    assert any(
        finding.rule_id == "diagnostic-repeated-phrases"
        for finding in evaluation.findings
    )


def test_uniform_cadence_drift_calibration_raises_profile_finding(
    wells_context: StyleContext,
) -> None:
    diagnostics = _analyse_wells_fixture(
        _style_fixture_text("uniform-cadence.md"),
        wells_context,
    )
    evaluation = evaluate_style_rules(
        wells_context,
        diagnostics,
        roles=["notebook"],
        manuscript="calibration/uniform-cadence.md",
    )

    assert diagnostics.sentence_count >= 20
    assert any(
        finding.rule_id == "diagnostic-uniform-cadence"
        for finding in evaluation.findings
    )


def test_punctuation_drift_calibration_raises_shared_surface_warning() -> None:
    warnings = run_surface_heuristics(
        _style_fixture_text("punctuation-drift.md"),
        LintSettings(),
    )

    em_dash = next(warning for warning in warnings if warning.rule_id == "em-dash-overuse")
    assert em_dash.observed == (
        "Em dashes: 4 in 11 words (363.6 per 1,000); configured maximum 1 per 1,000."
    )


def test_generic_ai_surface_calibration_is_separately_labelled(
    style_lint_story: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (style_lint_story / "manuscript" / "first-account.md").write_text(
        _style_fixture_text("generic-ai-surface.md"),
        encoding="utf-8",
    )
    scanner = _write_scanner(
        tmp_path,
        line=1,
        match="comprehensive framework",
    )
    monkeypatch.setenv("CREATIVE_WRITER_AI_AUDIT_SCRIPT", str(scanner))

    result = generate_style_lint(
        style_lint_story.parent.parent,
        "lint-story",
        chapter_selector="01-opening",
    )
    payload = json.loads(result.json_path.read_text(encoding="utf-8"))
    generic = [
        finding
        for finding in payload["findings"]
        if finding["category"] == "generic_ai"
    ]

    assert generic
    assert all(
        finding["rule_id"].startswith("ai-audit-") for finding in generic
    )
    assert all(finding["rule_family"] is None for finding in generic)
    assert all(finding["claim_ids"] == [] for finding in generic)
    assert payload["generic_ai"]["finding_ids"] == [
        finding["id"] for finding in generic
    ]


def test_style_lint_writes_matching_score_free_reports(
    style_lint_story: Path,
) -> None:
    result = generate_style_lint(
        style_lint_story.parent.parent,
        "lint-story",
    )
    payload = json.loads(result.json_path.read_text(encoding="utf-8"))
    markdown = result.markdown_path.read_text(encoding="utf-8")

    assert result.scope == "story"
    assert result.markdown_path == (
        style_lint_story.parent.parent
        / "build/lint-story/style/lint-report.md"
    )
    assert result.json_path == (
        style_lint_story.parent.parent
        / "build/lint-story/style/lint-report.json"
    )
    assert result.finding_count == len(payload["findings"]) > 0
    assert result.partial is False
    assert "score" not in json.dumps(payload).lower()
    assert "authorship" not in json.dumps(payload).lower()
    assert "authenticity" not in json.dumps(payload).lower()
    assert "score" not in markdown.lower()
    assert "authorship" not in markdown.lower()
    assert "authenticity" not in markdown.lower()
    assert "## Evidence-backed practice questions" in markdown
    assert "## Contextual diagnostics" in markdown
    assert "## Anti-drift observations" in markdown
    assert "## Surface warnings" in markdown
    assert "## Generic AI-writing signals" in markdown
    assert payload["findings"][0]["id"] == "finding-001"
    assert [finding["id"] for finding in payload["findings"]] == [
        f"finding-{index:03d}"
        for index in range(1, len(payload["findings"]) + 1)
    ]
    assert all(finding["id"] in markdown for finding in payload["findings"])


def test_style_lint_uses_fixed_repository_scanner_identifier(
    style_lint_story: Path,
    monkeypatch,
) -> None:
    scanner = Path(os.environ["CREATIVE_WRITER_AI_AUDIT_SCRIPT"])
    injected = scanner.with_name(
        "scanner`\n## Authorship score and rewrite.py"
    )
    scanner.rename(injected)
    monkeypatch.setenv("CREATIVE_WRITER_AI_AUDIT_SCRIPT", str(injected))

    payload, markdown = _read_report(style_lint_story)
    serialized = json.dumps(payload)

    assert payload["generic_ai"]["scanner"] == (
        "creative-writer-ai-writing-scanner"
    )
    assert str(injected) not in serialized
    assert str(injected) not in markdown
    assert "Authorship score and rewrite" not in serialized
    assert "Authorship score and rewrite" not in markdown


@pytest.mark.parametrize(
    "selector",
    [
        "chapter-stubs/01-opening.md",
        "01-opening.md",
        "01-opening",
        "manuscript/first-account.md",
        "first-account.md",
        "first-account",
    ],
)
def test_style_lint_accepts_each_exact_chapter_selector_form(
    style_lint_story: Path,
    selector: str,
) -> None:
    result = generate_style_lint(
        style_lint_story.parent.parent,
        "lint-story",
        chapter_selector=selector,
    )
    payload = json.loads(result.json_path.read_text(encoding="utf-8"))

    assert result.scope == "chapter"
    assert result.markdown_path.name == "01-opening-lint-report.md"
    assert result.json_path.name == "01-opening-lint-report.json"
    assert result.markdown_path.parent.name == "chapters"
    assert payload["chapter_selector"] == selector
    assert len(payload["chapters"]) == 1
    assert payload["chapters"][0]["title"] == "Opening"


def test_style_lint_rejects_unmatched_and_ambiguous_selectors(
    style_lint_story: Path,
) -> None:
    coherence_report = (
        style_lint_story.parent.parent
        / "build/lint-story/reports/coherence-report.md"
    )
    with pytest.raises(CreativeWriterError, match="did not match"):
        generate_style_lint(
            style_lint_story.parent.parent,
            "lint-story",
            chapter_selector="missing-chapter",
        )
    assert not coherence_report.exists()

    _write_stub(
        style_lint_story / "chapter-stubs" / "02-turn.md",
        title="Turn",
        manuscript="manuscript/01-opening.md",
        roles=["frame"],
    )
    with pytest.raises(CreativeWriterError, match="ambiguous"):
        generate_style_lint(
            style_lint_story.parent.parent,
            "lint-story",
            chapter_selector="01-opening",
        )
    assert not coherence_report.exists()


def test_style_lint_keeps_report_languages_separate(
    style_lint_story: Path,
) -> None:
    payload, markdown = _read_report(style_lint_story)
    categories = {finding["category"] for finding in payload["findings"]}

    assert {
        "wells_practice",
        "contextual_diagnostic",
        "surface_warning",
        "generic_ai",
    } <= categories
    assert payload["practice_questions"][0]["rule_id"] == (
        "practice-mediated-testimony"
    )
    assert all(
        finding["rule_id"] != "practice-mediated-testimony"
        for finding in payload["findings"]
    )
    generic = [
        finding
        for finding in payload["findings"]
        if finding["category"] == "generic_ai"
    ]
    assert generic
    assert all(finding["claim_ids"] == [] for finding in generic)
    assert all(finding["claim_statuses"] == {} for finding in generic)
    assert all(finding["claim_jurisdictions"] == [] for finding in generic)
    assert all(finding["source_passage_ids"] == [] for finding in generic)
    question = next(
        question
        for question in payload["practice_questions"]
        if question["claim_ids"]
    )
    assert list(question["claim_statuses"]) == question["claim_ids"]
    assert question["claim_statuses"] == {"validated-claim": "validated"}
    assert question["claim_jurisdictions"][0]["scope"] == "role_specific"
    evidence_finding = next(
        finding for finding in payload["findings"] if finding["claim_ids"]
    )
    assert list(evidence_finding["claim_statuses"]) == evidence_finding["claim_ids"]
    assert evidence_finding["claim_statuses"] == {
        "validated-claim": "validated"
    }
    assert evidence_finding["claim_jurisdictions"][0]["scope"] == "role_specific"
    assert payload["generic_ai"]["group_names"] == ["AI vocabulary"]
    assert "moderate surface risk" not in json.dumps(payload)
    assert "two groups" not in json.dumps(payload)
    assert "AI vocabulary" in markdown
    assert "wells:inference:1" in markdown
    assert "Claim statuses: `validated-claim`: `validated`" in markdown
    assert "Claim jurisdictions: `role_specific`" in markdown
    assert '"The"' in generic[0]["observed_signal"]
    assert '"The lamp went out."' in (
        generic[0]["observed_signal"]
    )
    assert "Rewrite this passage" not in json.dumps(payload)
    assert "authorship score" not in json.dumps(payload)
    assert "Rewrite this passage" not in markdown


def test_style_lint_reports_context_and_story_level_repetition(
    style_lint_story: Path,
) -> None:
    payload, _markdown = _read_report(style_lint_story)

    diagnostics = {
        (record["rule_id"], record["manuscript"]): record
        for record in payload["diagnostics"]
    }
    cadence_records = [
        record
        for (rule_id, _manuscript), record in diagnostics.items()
        if rule_id == "diagnostic-uniform-cadence"
    ]
    assert len(cadence_records) == 2
    assert all(
        record["manuscripts"] == [record["manuscript"]]
        for record in cadence_records
    )
    assert all(
        "sentence_length_cv" in record["measurements"]
        for record in cadence_records
    )
    assert any(record["triggered"] for record in cadence_records)
    assert any(not record["triggered"] for record in cadence_records)
    repetition = next(
        record
        for record in payload["diagnostics"]
        if record["rule_id"] == "diagnostic-repeated-phrases"
    )
    assert repetition["manuscript"] is None
    assert repetition["manuscripts"] == [
        "stories/lint-story/manuscript/first-account.md",
        "stories/lint-story/manuscript/second-account.md",
    ]
    repetition_finding = next(
        finding
        for finding in payload["findings"]
        if finding["rule_id"] == "diagnostic-repeated-phrases"
    )
    assert repetition_finding["scope"] == "story"
    assert "the lamp went" in repetition_finding["observed_signal"].lower()
    assert "Sentence boundaries are approximate" in json.dumps(payload)
    assert "Dialogue measurement is approximate" in json.dumps(payload)


def test_style_lint_records_mixed_role_caveat(
    style_lint_story: Path,
) -> None:
    payload, _markdown = _read_report(style_lint_story)

    assert "coarse" in payload["role_caveat"]
    assert "mixed-role" in payload["role_caveat"].lower()
    assert "does not infer" in payload["role_caveat"].lower()
    assert payload["chapters"][0]["roles"] == [
        "frame",
        "scientific-inference",
    ]


@pytest.mark.parametrize("escape_kind", ["build", "manuscript"])
def test_style_lint_preflights_paths_before_any_public_side_effect(
    style_lint_story: Path,
    monkeypatch,
    escape_kind: str,
) -> None:
    root = style_lint_story.parent.parent
    outside = root.parent / f"{root.name}-{escape_kind}-escape"
    outside.mkdir(exist_ok=True)
    scanner_called = False

    def unexpected_scan(*args, **kwargs):
        nonlocal scanner_called
        scanner_called = True
        raise AssertionError("scanner ran before path preflight completed")

    monkeypatch.setattr(
        style_lint_module,
        "scan_ai_writing_json",
        unexpected_scan,
    )
    if escape_kind == "build":
        (root / "build").mkdir(exist_ok=True)
        (root / "build" / "lint-story").symlink_to(
            outside,
            target_is_directory=True,
        )
    else:
        manuscript = style_lint_story / "manuscript" / "first-account.md"
        manuscript.unlink()
        escaped_manuscript = outside / "escaped-manuscript.md"
        escaped_manuscript.write_text("External prose.\n", encoding="utf-8")
        manuscript.symlink_to(escaped_manuscript)

    with pytest.raises(CreativeWriterError, match="path|resolve|symlink"):
        generate_style_lint(root, "lint-story")

    assert scanner_called is False
    assert not (outside / "reports" / "coherence-report.md").exists()
    assert not (
        root / "build" / "lint-story" / "reports" / "coherence-report.md"
    ).exists()


def test_story_rules_aggregate_only_role_applicable_chapters(
    style_lint_story: Path,
) -> None:
    _configure_contract(style_lint_story, generic_ai_audit=False)
    _write_stub(
        style_lint_story / "chapter-stubs" / "01-opening.md",
        title="Opening",
        manuscript="manuscript/first-account.md",
        roles=["scientific-inference"],
    )
    (style_lint_story / "manuscript" / "first-account.md").write_text(
        "Foreign words recur here.\n"
        "Foreign words recur here.\n"
        "Foreign words recur here.\n",
        encoding="utf-8",
    )
    (style_lint_story / "manuscript" / "second-account.md").write_text(
        "The witness waited.\n",
        encoding="utf-8",
    )

    payload, _markdown = _read_report(style_lint_story)

    record = next(
        record
        for record in payload["diagnostics"]
        if record["rule_id"] == "diagnostic-repeated-phrases"
    )
    assert record["manuscript"] is None
    assert record["manuscripts"] == [
        "stories/lint-story/manuscript/second-account.md"
    ]
    assert record["roles"] == ["frame"]
    assert record["measurements"]["word_count"] == 3
    assert record["triggered"] is False
    assert all(
        finding["rule_id"] != "diagnostic-repeated-phrases"
        for finding in payload["findings"]
    )


@pytest.mark.parametrize(
    ("duplicate_kind", "message"),
    [
        ("stub", "duplicate resolved stub"),
        ("manuscript", "duplicate resolved manuscript"),
        ("stem", "duplicate stub stem"),
    ],
)
def test_style_lint_rejects_duplicate_chapter_identities_and_outputs(
    style_lint_story: Path,
    duplicate_kind: str,
    message: str,
) -> None:
    if duplicate_kind == "stub":
        _append_story_chapter(
            style_lint_story,
            "chapter-stubs/01-opening.md",
        )
    else:
        nested = style_lint_story / "chapter-stubs" / "nested"
        nested.mkdir()
        stub_name = (
            "01-opening.md" if duplicate_kind == "stem" else "03-copy.md"
        )
        manuscript = (
            "manuscript/third-account.md"
            if duplicate_kind == "stem"
            else "manuscript/first-account.md"
        )
        _write_stub(
            nested / stub_name,
            title="Duplicate boundary",
            manuscript=manuscript,
            roles=["frame"],
        )
        if duplicate_kind == "stem":
            (style_lint_story / manuscript).write_text(
                "A distinct third account.\n",
                encoding="utf-8",
            )
        _append_story_chapter(
            style_lint_story,
            f"chapter-stubs/nested/{stub_name}",
        )

    with pytest.raises(CreativeWriterError, match=message):
        generate_style_lint(
            style_lint_story.parent.parent,
            "lint-story",
        )


def test_repeated_signal_review_thresholds_are_evaluated_per_rule(
    style_lint_story: Path,
    monkeypatch,
) -> None:
    context = _style_context(style_lint_story)
    repeated = next(
        resolved
        for resolved in context.rules
        if resolved.rule.id == "diagnostic-repeated-phrases"
    )
    assert repeated.rule.signal is not None
    high_floor_signal = repeated.rule.signal.model_copy(
        update={"minimum_words": 1000}
    )
    high_floor_rule = repeated.rule.model_copy(
        update={
            "id": "diagnostic-repeated-phrases-high-floor",
            "signal": high_floor_signal,
        }
    )
    context = replace(
        context,
        rules=(
            *context.rules,
            ResolvedStyleRule(rule=high_floor_rule, claims=()),
        ),
    )
    monkeypatch.setattr(
        style_lint_module,
        "load_style_context",
        lambda root, story_dir, profile_path: context,
    )

    payload, _markdown = _read_report(style_lint_story)

    records = {
        record["rule_id"]: record for record in payload["diagnostics"]
    }
    assert records["diagnostic-repeated-phrases"]["triggered"] is True
    assert (
        records["diagnostic-repeated-phrases-high-floor"]["triggered"]
        is False
    )


def test_style_lint_rejects_incompatible_shared_pass_before_side_effects(
    style_lint_story: Path,
    monkeypatch,
) -> None:
    context = _style_context(style_lint_story)
    repeated = next(
        resolved
        for resolved in context.rules
        if resolved.rule.id == "diagnostic-repeated-phrases"
    )
    assert repeated.rule.signal is not None
    incompatible_rule = repeated.rule.model_copy(
        update={
            "id": "diagnostic-repeated-phrases-four-words",
            "signal": repeated.rule.signal.model_copy(
                update={"ngram_size": 4}
            ),
        }
    )
    context = replace(
        context,
        rules=(
            *context.rules,
            ResolvedStyleRule(rule=incompatible_rule, claims=()),
        ),
    )
    monkeypatch.setattr(
        style_lint_module,
        "load_style_context",
        lambda root, story_dir, profile_path: context,
    )
    scanner_calls = 0
    real_scan = style_lint_module.scan_ai_writing_json

    def recording_scan(*args, **kwargs):
        nonlocal scanner_calls
        scanner_calls += 1
        return real_scan(*args, **kwargs)

    monkeypatch.setattr(
        style_lint_module,
        "scan_ai_writing_json",
        recording_scan,
    )

    with pytest.raises(CreativeWriterError, match="incompatible one-pass"):
        generate_style_lint(
            style_lint_story.parent.parent,
            "lint-story",
        )

    assert scanner_calls == 0
    assert not (
        style_lint_story.parent.parent
        / "build/lint-story/reports/coherence-report.md"
    ).exists()


def test_style_lint_rejects_unmeasurable_signal_tolerance_pair(
    style_lint_story: Path,
    monkeypatch,
) -> None:
    context = _style_context(style_lint_story)
    cadence = next(
        resolved
        for resolved in context.rules
        if resolved.rule.id == "diagnostic-uniform-cadence"
    )
    invalid_rule = cadence.rule.model_copy(
        update={
            "signal": DialogueProfileSignal(
                kind="dialogue_profile",
                minimum_words=1,
            )
        }
    )
    invalid_resolved = ResolvedStyleRule(
        rule=invalid_rule,
        claims=cadence.claims,
    )
    context = replace(
        context,
        rules=tuple(
            invalid_resolved
            if resolved.rule.id == invalid_rule.id
            else resolved
            for resolved in context.rules
        ),
    )
    monkeypatch.setattr(
        style_lint_module,
        "load_style_context",
        lambda root, story_dir, profile_path: context,
    )
    scanner_called = False

    def unexpected_scan(*args, **kwargs):
        nonlocal scanner_called
        scanner_called = True
        raise AssertionError("scanner ran for an invalid rule configuration")

    monkeypatch.setattr(
        style_lint_module,
        "scan_ai_writing_json",
        unexpected_scan,
    )

    with pytest.raises(CreativeWriterError, match="cannot produce"):
        generate_style_lint(
            style_lint_story.parent.parent,
            "lint-story",
        )

    assert scanner_called is False


def test_style_lint_marks_missing_generic_scanner_partial(
    style_lint_story: Path,
    monkeypatch,
) -> None:
    missing = style_lint_story.parent.parent / "missing-scanner.py"
    monkeypatch.setenv("CREATIVE_WRITER_AI_AUDIT_SCRIPT", str(missing))

    payload, markdown = _read_report(style_lint_story)

    assert payload["partial"] is True
    assert payload["generic_ai"]["status"] == "unavailable"
    assert payload["generic_ai"]["notice"] is not None
    assert "unavailable" in markdown.lower()


def test_style_lint_disabled_generic_scan_skips_adapter(
    style_lint_story: Path,
    monkeypatch,
) -> None:
    _configure_contract(style_lint_story, generic_ai_audit=False)

    def unexpected_scan(*args, **kwargs):
        raise AssertionError("disabled generic scan invoked the adapter")

    monkeypatch.setattr(
        style_lint_module,
        "scan_ai_writing_json",
        unexpected_scan,
    )

    payload, _markdown = _read_report(style_lint_story)

    assert payload["partial"] is False
    assert payload["generic_ai"]["status"] == "disabled"
    assert payload["generic_ai"]["finding_ids"] == []


def test_style_lint_is_byte_stable_across_identical_runs(
    style_lint_story: Path,
) -> None:
    first = generate_style_lint(
        style_lint_story.parent.parent,
        "lint-story",
    )
    first_markdown = first.markdown_path.read_bytes()
    first_json = first.json_path.read_bytes()

    second = generate_style_lint(
        style_lint_story.parent.parent,
        "lint-story",
    )

    assert second.markdown_path.read_bytes() == first_markdown
    assert second.json_path.read_bytes() == first_json


def test_style_lint_rolls_back_both_reports_when_pair_publication_fails(
    style_lint_story: Path,
    monkeypatch,
) -> None:
    first = generate_style_lint(
        style_lint_story.parent.parent,
        "lint-story",
    )
    old_markdown = first.markdown_path.read_bytes()
    old_json = first.json_path.read_bytes()
    (style_lint_story / "manuscript" / "first-account.md").write_text(
        "Perhaps the lamp failed.\n"
        "The changed account now occupies this chapter.\n",
        encoding="utf-8",
    )
    real_replace = os.replace
    failed = False

    def fail_json_publish(source, destination):
        nonlocal failed
        if not failed and Path(destination) == first.json_path:
            failed = True
            raise OSError("simulated JSON publication failure")
        return real_replace(source, destination)

    monkeypatch.setattr(os, "replace", fail_json_publish)

    with pytest.raises(
        CreativeWriterError,
        match="Unable to publish style-lint report",
    ):
        generate_style_lint(
            style_lint_story.parent.parent,
            "lint-story",
        )

    assert failed is True
    assert first.markdown_path.read_bytes() == old_markdown
    assert first.json_path.read_bytes() == old_json
    assert not [
        path
        for path in first.markdown_path.parent.iterdir()
        if ".tmp-" in path.name or ".backup-" in path.name
    ]


def test_style_lint_rejects_malformed_profile(tmp_path: Path) -> None:
    story = create_story(tmp_path, "malformed-style", "original")
    _configure_contract(story, profile="malformed-profile.yml")
    (story / "malformed-profile.yml").write_text(
        "schema_version: 1\nprofile_id: incomplete\n",
        encoding="utf-8",
    )

    with pytest.raises(CreativeWriterError, match="Schema validation failed"):
        generate_style_lint(tmp_path, "malformed-style")

    assert not (
        tmp_path / "build/malformed-style/reports/coherence-report.md"
    ).exists()


def test_style_lint_profile_override_supersedes_broken_contract_profile(
    style_lint_story: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_contract(style_lint_story, profile="missing-profile.yml")
    expected_profile = style_lint_story / "style-profile.yml"
    context = _style_context(style_lint_story)

    def load_effective_context(
        root: Path,
        story_dir: Path,
        profile_path: Path,
    ) -> StyleContext:
        if profile_path != expected_profile:
            raise CreativeWriterError(f"Unexpected profile path: {profile_path}")
        return context

    monkeypatch.setattr(
        style_lint_module,
        "load_style_context",
        load_effective_context,
    )
    monkeypatch.setattr(
        checks_module,
        "load_style_context",
        load_effective_context,
    )

    result = generate_style_lint(
        style_lint_story.parent.parent,
        "lint-story",
        profile_override="style-profile.yml",
    )

    assert result.profile_id == "fixture-wells-profile"


def test_style_lint_parser_accepts_optional_profile_and_chapter() -> None:
    args = cli_module.build_parser().parse_args(
        [
            "style-lint",
            "--story",
            "time-expedition",
            "--profile",
            "style-profile.yml",
            "--chapter",
            "01-last-week-of-the-permian",
        ]
    )

    assert vars(args) == {
        "command": "style-lint",
        "story": "time-expedition",
        "profile": "style-profile.yml",
        "chapter": "01-last-week-of-the-permian",
    }


def test_style_lint_parser_defaults_optional_arguments_to_none() -> None:
    args = cli_module.build_parser().parse_args(
        ["style-lint", "--story", "time-expedition"]
    )

    assert args.profile is None
    assert args.chapter is None


def test_style_lint_cli_reports_both_generated_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    markdown_path = tmp_path / "build/story/style/lint-report.md"
    json_path = tmp_path / "build/story/style/lint-report.json"
    calls: list[tuple[Path, str, str | None, str | None]] = []

    def generate(
        root: Path,
        slug: str,
        *,
        profile_override: str | None,
        chapter_selector: str | None,
    ) -> SimpleNamespace:
        calls.append((root, slug, profile_override, chapter_selector))
        return SimpleNamespace(
            markdown_path=markdown_path,
            json_path=json_path,
            finding_count=3,
            partial=False,
        )

    monkeypatch.setattr(cli_module, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(style_lint_module, "generate_style_lint", generate)

    status = cli_module.main(
        [
            "style-lint",
            "--story",
            "story",
            "--profile",
            "profiles/wells.yml",
            "--chapter",
            "01-opening",
        ]
    )

    assert status == 0
    assert calls == [(tmp_path, "story", "profiles/wells.yml", "01-opening")]
    assert capsys.readouterr().out.splitlines() == [
        f"Style lint Markdown report written to {markdown_path}",
        f"Style lint JSON report written to {json_path}",
        "Findings: 3",
        "Result status: complete",
    ]


def test_threshold_note_cites_reference_value_when_configured() -> None:
    from types import SimpleNamespace

    from creative_writer.style_lint import _threshold_result
    from creative_writer.style_models import StyleTolerance

    tolerance = StyleTolerance.model_validate(
        {
            "metric": "sentence_length_p90",
            "minimum_sample_size": 10,
            "review_below": 26.0,
            "reference_witness_ids": ["the-time-machine"],
            "reference_value": 31.0,
            "reference_label": "The Time Machine p90",
            "rationale": "Short tails prompt review.",
        }
    )
    resolved = SimpleNamespace(rule=SimpleNamespace(tolerance=tolerance))

    triggered, note = _threshold_result(
        resolved, {"sentence_length_p90": 24.0}, 40, 10
    )

    assert triggered is True
    assert "Reference: The Time Machine p90 31." in note
