"""Generate deterministic, separated, advisory style-lint reports."""

from __future__ import annotations

import json
import math
import re
import statistics
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from creative_writer.ai_audit import scan_ai_writing_json
from creative_writer.checks import check_story
from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory
from creative_writer.models import ChapterDocument
from creative_writer.prose_heuristics import run_surface_heuristics
from creative_writer.source_analysis_common import safe_relative_path, sha256_file
from creative_writer.style_diagnostics import (
    ManuscriptDiagnostics,
    analyse_manuscript,
)
from creative_writer.style_models import (
    GenericAIReportSection,
    StyleChapterInventory,
    StyleDiagnosticRecord,
    StyleFinding,
    StyleLintReport,
    StylePracticeQuestion,
)
from creative_writer.style_profiles import (
    CHAPTER_ROLE_CAVEAT,
    ResolvedStyleRule,
    StyleContext,
    load_style_context,
    resolve_style_profile_path,
    validate_chapter_style_metadata,
)


_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_CATEGORY_RANK = {
    "wells_practice": 0,
    "contextual_diagnostic": 1,
    "anti_drift": 2,
    "surface_warning": 3,
    "generic_ai": 4,
}
_GENERIC_CAUTION = (
    "Generic AI-writing signals are separate editorial prompts and provide "
    "no positive Wells evidence."
)
_SENTENCE_CAVEAT = (
    "Sentence boundaries are approximate and inherit the project's "
    "Victorian-text scanner."
)
_DIALOGUE_CAVEAT = (
    "Dialogue measurement is approximate: only words inside matched straight "
    "or curly double quotes are counted, and nested quotations and attribution "
    "boundaries are not parsed linguistically."
)
_MIXED_ROLE_CAVEAT = (
    " Mixed-role chapters retain every declared role; the report does not "
    "infer which role applies to a particular passage."
)


@dataclass(slots=True)
class StyleLintResult:
    """Paths and summary state for one generated report pair."""

    story_slug: str
    scope: Literal["story", "chapter"]
    profile_id: str
    profile_version: str
    markdown_path: Path
    json_path: Path
    finding_count: int
    partial: bool


@dataclass(slots=True)
class StyleRuleEvaluation:
    """Questions, measurements, and findings from one diagnostic pass."""

    questions: list[StylePracticeQuestion]
    diagnostics: list[StyleDiagnosticRecord]
    findings: list[StyleFinding]


@dataclass(frozen=True, slots=True)
class _StorySegment:
    line_start: int
    line_end: int
    manuscript: str


@dataclass(frozen=True, slots=True)
class _StoryText:
    text: str
    segments: tuple[_StorySegment, ...]


def _unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _matching_roles(rule: ResolvedStyleRule, roles: Sequence[str]) -> list[str]:
    declared = set(roles)
    if not rule.rule.roles:
        return _unique(list(roles))
    return [role for role in rule.rule.roles if role in declared]


def _applies(rule: ResolvedStyleRule, roles: Sequence[str]) -> bool:
    return not rule.rule.roles or bool(_matching_roles(rule, roles))


def _applicable_rules(
    context: StyleContext,
    roles: Sequence[str],
    scopes: set[str],
) -> list[ResolvedStyleRule]:
    return [
        resolved
        for resolved in context.rules
        if resolved.rule.scope in scopes and _applies(resolved, roles)
    ]


def _single_signal_configuration(
    rules: Sequence[ResolvedStyleRule],
    kind: str,
) -> object | None:
    signals = [
        resolved.rule.signal
        for resolved in rules
        if resolved.rule.signal is not None
        and resolved.rule.signal.kind == kind
    ]
    if not signals:
        return None
    signatures = {repr(signal.model_dump(mode="json")) for signal in signals}
    if len(signatures) > 1:
        raise CreativeWriterError(
            f"Applicable {kind} rules require incompatible one-pass settings"
        )
    return signals[0]


def _analyse_for_rules(
    text: str,
    rules: Sequence[ResolvedStyleRule],
) -> ManuscriptDiagnostics:
    lexicons = {
        resolved.rule.id: resolved.rule.signal.terms
        for resolved in rules
        if resolved.rule.signal is not None
        and resolved.rule.signal.kind == "lexicon_locator"
    }
    speech_attribution_verbs = _unique(
        [
            verb
            for resolved in rules
            if resolved.rule.signal is not None
            and resolved.rule.signal.kind == "sentence_profile"
            for verb in resolved.rule.signal.speech_attribution_verbs
        ]
    )
    repeated = _single_signal_configuration(rules, "repeated_ngram")
    opening = _single_signal_configuration(rules, "paragraph_opening")

    return analyse_manuscript(
        text,
        lexicons=lexicons,
        speech_attribution_verbs=speech_attribution_verbs,
        stop_words=repeated.stop_words if repeated is not None else (),
        repeated_ngram_size=repeated.ngram_size if repeated is not None else 3,
        repeated_ngram_minimum=(
            repeated.minimum_occurrences if repeated is not None else 3
        ),
        opening_prefix_words=(
            opening.prefix_words if opening is not None else 3
        ),
        opening_minimum=(
            opening.minimum_occurrences if opening is not None else 3
        ),
    )


def _median(values: Sequence[int]) -> float | None:
    return float(statistics.median(values)) if values else None


def _p90(values: Sequence[int]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = 0.9 * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    fraction = position - lower
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction)


def _sentence_measurements(
    diagnostics: ManuscriptDiagnostics,
) -> dict[str, int | float | str | None]:
    return {
        "sentence_count": diagnostics.sentence_count,
        "paragraph_count": diagnostics.paragraph_count,
        "sentence_length_median": _median(diagnostics.sentence_lengths),
        "sentence_length_p90": _p90(diagnostics.sentence_lengths),
        "sentence_length_cv": diagnostics.sentence_length_cv,
        "paragraph_length_median": _median(diagnostics.paragraph_lengths),
    }


def _diagnostic_limit(resolved: ResolvedStyleRule, signal_kind: str) -> str:
    limits = [resolved.rule.interpretation_limits]
    if signal_kind == "sentence_profile":
        limits.append(_SENTENCE_CAVEAT)
    elif signal_kind == "dialogue_profile":
        limits.append(_DIALOGUE_CAVEAT)
    elif signal_kind == "repeated_ngram":
        limits.append(
            "Repeated phrases are lexical locators and require contextual review."
        )
    elif signal_kind == "paragraph_opening":
        limits.append(
            "Paragraph openings are compared after markup exclusions and "
            "require contextual review."
        )
    return " ".join(_unique(limits))


def _threshold_result(
    resolved: ResolvedStyleRule,
    measurements: dict[str, int | float | str | None],
    sample_size: int,
    signal_minimum: int,
) -> tuple[bool, str]:
    tolerance = resolved.rule.tolerance
    if tolerance is None:
        return (
            False,
            "Context only; no automatic review tolerance is configured.",
        )
    minimum = max(signal_minimum, tolerance.minimum_sample_size)
    if sample_size < minimum:
        return (
            False,
            f"Sample size {sample_size} is below the review minimum {minimum}.",
        )
    value = measurements.get(tolerance.metric)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return (
            False,
            f"{tolerance.metric} is unavailable for this manuscript.",
        )

    crossed: list[str] = []
    if tolerance.review_below is not None and value < tolerance.review_below:
        crossed.append(f"below {tolerance.review_below:g}")
    if tolerance.review_above is not None and value > tolerance.review_above:
        crossed.append(f"above {tolerance.review_above:g}")
    if crossed:
        return (
            True,
            f"{tolerance.metric} {value:g} is {' and '.join(crossed)} "
            f"with sample size {sample_size}. {tolerance.rationale}",
        )
    bounds: list[str] = []
    if tolerance.review_below is not None:
        bounds.append(f"review below {tolerance.review_below:g}")
    if tolerance.review_above is not None:
        bounds.append(f"review above {tolerance.review_above:g}")
    return (
        False,
        f"{tolerance.metric} {value:g} is within the configured context "
        f"({'; '.join(bounds)}), with sample size {sample_size}.",
    )


def _finding_category(resolved: ResolvedStyleRule) -> str:
    if resolved.rule.family == "practice":
        return "wells_practice"
    if resolved.rule.family == "anti_drift":
        return "anti_drift"
    return "contextual_diagnostic"


def _rule_passages(resolved: ResolvedStyleRule) -> list[str]:
    rule = resolved.rule
    return _unique(
        [
            *rule.source_passage_ids,
            *rule.variation_passage_ids,
            *rule.control_passage_ids,
        ]
    )


def _practice_question(
    resolved: ResolvedStyleRule,
    roles: Sequence[str],
) -> StylePracticeQuestion:
    return StylePracticeQuestion(
        rule_id=resolved.rule.id,
        advisory=resolved.rule.advisory,
        roles=_matching_roles(resolved, roles),
        claim_ids=[claim.id for claim in resolved.claims],
        question=resolved.rule.review_question,
        source_passage_ids=_rule_passages(resolved),
        interpretation_limits=resolved.rule.interpretation_limits,
    )


def _style_finding(
    resolved: ResolvedStyleRule,
    *,
    manuscript: str,
    roles: Sequence[str],
    line_start: int,
    line_end: int,
    observed: str,
    advisory: Literal["notice", "review"] | None = None,
    limitations: str | None = None,
) -> StyleFinding:
    return StyleFinding(
        id="pending",
        category=_finding_category(resolved),
        manuscript=manuscript,
        line_start=line_start,
        line_end=line_end,
        observed_signal=observed,
        rule_id=resolved.rule.id,
        rule_family=resolved.rule.family,
        advisory=advisory or resolved.rule.advisory,
        roles=_matching_roles(resolved, roles),
        scope=resolved.rule.scope,
        claim_ids=[claim.id for claim in resolved.claims],
        claim_jurisdictions=[
            claim.jurisdiction for claim in resolved.claims
        ],
        source_passage_ids=_rule_passages(resolved),
        editorial_question=resolved.rule.review_question,
        limitations=limitations or resolved.rule.interpretation_limits,
    )


def _evaluate_rules(
    rules: Sequence[ResolvedStyleRule],
    diagnostics: ManuscriptDiagnostics,
    *,
    roles: Sequence[str],
    manuscript: str,
) -> StyleRuleEvaluation:
    questions: list[StylePracticeQuestion] = []
    records: list[StyleDiagnosticRecord] = []
    findings: list[StyleFinding] = []

    for resolved in rules:
        rule = resolved.rule
        if rule.evaluation_mode == "manual_question":
            questions.append(_practice_question(resolved, roles))
            continue

        signal = rule.signal
        if signal is None:
            raise CreativeWriterError(f"Style rule {rule.id} has no signal")

        if rule.evaluation_mode == "locator":
            if signal.kind != "lexicon_locator":
                raise CreativeWriterError(
                    f"Locator rule {rule.id} must use a lexicon locator"
                )
            for hit in diagnostics.lexicon_hits.get(rule.id, [])[
                : signal.max_examples
            ]:
                findings.append(
                    _style_finding(
                        resolved,
                        manuscript=manuscript,
                        roles=roles,
                        line_start=hit.location.line_start,
                        line_end=hit.location.line_end,
                        observed=hit.observed,
                        advisory="notice",
                    )
                )
            continue

        limitations = _diagnostic_limit(resolved, signal.kind)
        if signal.kind == "sentence_profile":
            measurements = _sentence_measurements(diagnostics)
            sample_size = diagnostics.sentence_count
            triggered, tolerance_note = _threshold_result(
                resolved,
                measurements,
                sample_size,
                signal.minimum_sentences,
            )
            located_signals = []
        elif signal.kind == "dialogue_profile":
            measurements = {
                "word_count": diagnostics.word_count,
                "dialogue_proportion": diagnostics.dialogue_word_proportion,
            }
            sample_size = diagnostics.word_count
            triggered, tolerance_note = _threshold_result(
                resolved,
                measurements,
                sample_size,
                signal.minimum_words,
            )
            located_signals = []
        elif signal.kind == "repeated_ngram":
            located_signals = diagnostics.repeated_ngrams
            measurements = {
                "word_count": diagnostics.word_count,
                "repeated_ngram_count": len(located_signals),
                "repeated_ngrams": (
                    "; ".join(item.observed for item in located_signals)
                    or None
                ),
            }
            sample_size = diagnostics.word_count
            triggered = (
                sample_size >= signal.minimum_words and bool(located_signals)
            )
            tolerance_note = (
                f"Review begins at {signal.minimum_occurrences} occurrences "
                f"after {signal.minimum_words} words; observed "
                f"{len(located_signals)} repeated phrase signal(s) across "
                f"{sample_size} words."
            )
        elif signal.kind == "paragraph_opening":
            located_signals = diagnostics.repeated_openings
            measurements = {
                "paragraph_count": diagnostics.paragraph_count,
                "repeated_opening_count": len(located_signals),
                "repeated_openings": (
                    "; ".join(item.observed for item in located_signals)
                    or None
                ),
            }
            sample_size = diagnostics.paragraph_count
            triggered = (
                sample_size >= signal.minimum_paragraphs
                and bool(located_signals)
            )
            tolerance_note = (
                f"Review begins at {signal.minimum_occurrences} matching "
                f"openings after {signal.minimum_paragraphs} paragraphs; "
                f"observed {len(located_signals)} signal(s) across "
                f"{sample_size} paragraphs."
            )
        else:
            raise CreativeWriterError(
                f"Unsupported contextual diagnostic signal: {signal.kind}"
            )

        records.append(
            StyleDiagnosticRecord(
                rule_id=rule.id,
                manuscript=manuscript,
                roles=_matching_roles(resolved, roles),
                measurements=measurements,
                sample_size=sample_size,
                tolerance_note=tolerance_note,
                triggered=triggered,
                limitations=limitations,
            )
        )
        if not triggered:
            continue
        if located_signals:
            findings.extend(
                _style_finding(
                    resolved,
                    manuscript=manuscript,
                    roles=roles,
                    line_start=located.location.line_start,
                    line_end=located.location.line_end,
                    observed=located.observed,
                    limitations=limitations,
                )
                for located in located_signals
            )
        else:
            findings.append(
                _style_finding(
                    resolved,
                    manuscript=manuscript,
                    roles=roles,
                    line_start=1,
                    line_end=1,
                    observed=tolerance_note,
                    limitations=limitations,
                )
            )

    return StyleRuleEvaluation(
        questions=questions,
        diagnostics=records,
        findings=findings,
    )


def evaluate_style_rules(
    context: StyleContext,
    diagnostics: ManuscriptDiagnostics,
    *,
    roles: Sequence[str],
    manuscript: str,
) -> StyleRuleEvaluation:
    """Evaluate all profile rules applicable to explicitly declared roles."""

    rules = [
        resolved
        for resolved in context.rules
        if _applies(resolved, roles)
    ]
    return _evaluate_rules(
        rules,
        diagnostics,
        roles=roles,
        manuscript=manuscript,
    )


def _chapter_selector_values(
    story_dir: Path,
    chapter: ChapterDocument,
) -> set[str]:
    stub = chapter.stub_path.relative_to(story_dir)
    manuscript = chapter.manuscript_path.relative_to(story_dir)
    return {
        stub.as_posix(),
        stub.name,
        stub.stem,
        manuscript.as_posix(),
        manuscript.name,
        manuscript.stem,
    }


def _select_chapters(
    story_dir: Path,
    chapters: Sequence[ChapterDocument],
    selector: str | None,
) -> list[ChapterDocument]:
    if selector is None:
        return list(chapters)
    matches = [
        chapter
        for chapter in chapters
        if selector in _chapter_selector_values(story_dir, chapter)
    ]
    if not matches:
        raise CreativeWriterError(
            f"Chapter selector {selector!r} did not match a configured chapter"
        )
    if len(matches) > 1:
        matched = ", ".join(
            chapter.stub_path.relative_to(story_dir).as_posix()
            for chapter in matches
        )
        raise CreativeWriterError(
            f"Chapter selector {selector!r} is ambiguous: {matched}"
        )
    return matches


def _story_text(
    chapters: Sequence[ChapterDocument],
    manuscripts: dict[Path, str],
) -> _StoryText:
    text = ""
    segments: list[_StorySegment] = []
    for chapter in chapters:
        if text:
            text += "\n\n"
        line_start = text.count("\n") + 1
        body = chapter.manuscript_body
        text += body
        line_count = max(1, len(body.splitlines()))
        segments.append(
            _StorySegment(
                line_start=line_start,
                line_end=line_start + line_count - 1,
                manuscript=manuscripts[chapter.manuscript_path],
            )
        )
    return _StoryText(text=text, segments=tuple(segments))


def _story_location(
    story_text: _StoryText,
    line: int,
) -> tuple[str, int]:
    for segment in story_text.segments:
        if segment.line_start <= line <= segment.line_end:
            return segment.manuscript, line - segment.line_start + 1
    segment = story_text.segments[-1]
    return segment.manuscript, max(1, segment.line_end - segment.line_start + 1)


def _map_story_findings(
    evaluation: StyleRuleEvaluation,
    story_text: _StoryText,
) -> StyleRuleEvaluation:
    mapped: list[StyleFinding] = []
    for finding in evaluation.findings:
        manuscript, line_start = _story_location(
            story_text,
            finding.line_start,
        )
        end_manuscript, line_end = _story_location(
            story_text,
            finding.line_end,
        )
        limitations = finding.limitations
        if end_manuscript != manuscript:
            line_end = line_start
            limitations += (
                " The story-wide location is anchored to the first occurrence; "
                "later occurrences may be in other selected chapters."
            )
        mapped.append(
            finding.model_copy(
                update={
                    "manuscript": manuscript,
                    "line_start": line_start,
                    "line_end": line_end,
                    "limitations": limitations,
                }
            )
        )
    return StyleRuleEvaluation(
        questions=evaluation.questions,
        diagnostics=evaluation.diagnostics,
        findings=mapped,
    )


def _surface_finding(
    manuscript: str,
    roles: Sequence[str],
    warning,
) -> StyleFinding:
    questions = {
        "em-dash-overuse": (
            "Is this concentration of em dashes intentional, or would another "
            "sentence shape serve the passage better?"
        ),
        "contrastive-parallelism": (
            "Is this contrastive construction earning its emphasis, or has it "
            "become a repeated default?"
        ),
    }
    return StyleFinding(
        id="pending",
        category="surface_warning",
        manuscript=manuscript,
        line_start=warning.line_start,
        line_end=warning.line_end,
        observed_signal=warning.observed,
        rule_id=warning.rule_id,
        rule_family=None,
        advisory="review",
        roles=list(roles),
        scope="chapter",
        claim_ids=[],
        claim_jurisdictions=[],
        source_passage_ids=[],
        editorial_question=questions[warning.rule_id],
        limitations=(
            "Configured surface warning only; it is separate from Wells evidence."
        ),
    )


def _slugify_group(value: str) -> str:
    folded = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return re.sub(r"[^a-z0-9]+", "-", folded).strip("-") or "signal"


def _generic_finding(
    *,
    manuscript: str,
    roles: Sequence[str],
    group_name: str,
    group,
    hit,
) -> StyleFinding:
    return StyleFinding(
        id="pending",
        category="generic_ai",
        manuscript=manuscript,
        line_start=hit.line,
        line_end=hit.line,
        observed_signal=(
            f"{hit.group}: {hit.match} in context {hit.context}"
        ),
        rule_id=f"ai-audit-{_slugify_group(group_name)}",
        rule_family=None,
        advisory=(
            "review"
            if max(group.severity, hit.severity) >= 2
            else "notice"
        ),
        roles=list(roles),
        scope="passage",
        claim_ids=[],
        claim_jurisdictions=[],
        source_passage_ids=[],
        editorial_question=(
            f"{group.advice} Does this signal matter in the surrounding passage?"
        ),
        limitations=(
            "Generic AI-writing surface signal only; it carries no Phase 2B "
            "claim or source example."
        ),
    )


def _merge_questions(
    context: StyleContext,
    questions: Sequence[StylePracticeQuestion],
) -> list[StylePracticeQuestion]:
    role_order = [role.id for role in context.profile.roles]
    by_rule: dict[str, StylePracticeQuestion] = {}
    for question in questions:
        existing = by_rule.get(question.rule_id)
        if existing is None:
            by_rule[question.rule_id] = question
            continue
        roles = set(existing.roles).union(question.roles)
        by_rule[question.rule_id] = existing.model_copy(
            update={"roles": [role for role in role_order if role in roles]}
        )
    rule_order = {
        resolved.rule.id: index
        for index, resolved in enumerate(context.rules)
    }
    return sorted(
        by_rule.values(),
        key=lambda question: rule_order[question.rule_id],
    )


def _assign_finding_ids(
    findings: Sequence[StyleFinding],
    chapter_order: dict[str, int],
) -> list[StyleFinding]:
    ordered = sorted(
        findings,
        key=lambda finding: (
            _CATEGORY_RANK[finding.category],
            chapter_order.get(finding.manuscript, len(chapter_order)),
            finding.line_start,
            finding.rule_id,
        ),
    )
    return [
        finding.model_copy(update={"id": f"finding-{index:03d}"})
        for index, finding in enumerate(ordered, start=1)
    ]


def _render_question(question: StylePracticeQuestion) -> list[str]:
    claims = ", ".join(f"`{claim}`" for claim in question.claim_ids) or "None"
    sources = (
        ", ".join(f"`{source}`" for source in question.source_passage_ids)
        or "None"
    )
    roles = ", ".join(f"`{role}`" for role in question.roles) or "None"
    return [
        f"### `{question.rule_id}`",
        "",
        f"- Advisory: `{question.advisory}`",
        f"- Roles: {roles}",
        f"- Phase 2B claims: {claims}",
        f"- Source passages: {sources}",
        f"- Question: {question.question}",
        f"- Limits: {question.interpretation_limits}",
        "",
    ]


def _render_finding(finding: StyleFinding) -> list[str]:
    roles = ", ".join(f"`{role}`" for role in finding.roles) or "None"
    claims = ", ".join(f"`{claim}`" for claim in finding.claim_ids) or "None"
    sources = (
        ", ".join(f"`{source}`" for source in finding.source_passage_ids)
        or "None"
    )
    return [
        f"### `{finding.id}`",
        "",
        f"- Category: `{finding.category}`",
        f"- Rule: `{finding.rule_id}`",
        f"- Location: `{finding.manuscript}:{finding.line_start}`"
        + (
            f"-{finding.line_end}"
            if finding.line_end != finding.line_start
            else ""
        ),
        f"- Advisory: `{finding.advisory}`",
        f"- Roles: {roles}",
        f"- Phase 2B claims: {claims}",
        f"- Source passages: {sources}",
        f"- Observed: {finding.observed_signal}",
        f"- Editorial question: {finding.editorial_question}",
        f"- Limits: {finding.limitations}",
        "",
    ]


def _render_findings(
    findings: Sequence[StyleFinding],
    *,
    compact: bool = False,
) -> list[str]:
    if not findings:
        return ["- None.", ""]
    if compact:
        return [
            *[
                f"- `{finding.id}` | `{finding.category}` | "
                f"`{finding.manuscript}:{finding.line_start}` | "
                f"`{finding.rule_id}` | {finding.observed_signal}"
                for finding in findings
            ],
            "",
        ]
    lines: list[str] = []
    for finding in findings:
        lines.extend(_render_finding(finding))
    return lines


def _render_markdown(report: StyleLintReport) -> str:
    lines = [
        f"# Style Lint Report: {report.story_title}",
        "",
        f"- Story: `{report.story_slug}`",
        f"- Scope: `{report.scope}`",
        f"- Chapter selector: `{report.chapter_selector or 'all configured chapters'}`",
        f"- Profile: `{report.profile_id}` version `{report.profile_version}`",
        f"- Partial result: `{'yes' if report.partial else 'no'}`",
        "",
        "All findings are advisory review prompts. Manuscript prose was not changed.",
        "",
        "## Run scope and manuscript inventory",
        "",
        f"- Role caveat: {report.role_caveat}",
    ]
    for chapter in report.chapters:
        roles = ", ".join(f"`{role}`" for role in chapter.roles) or "None"
        packets = (
            ", ".join(f"`{packet}`" for packet in chapter.packet_ids)
            or "None"
        )
        lines.append(
            f"- `{chapter.stub}` -> `{chapter.manuscript}` | "
            f"{chapter.title} | roles: {roles} | packets: {packets} | "
            f"words: {chapter.word_count}"
        )

    lines.extend(
        [
            "",
            "## Profile and evidence provenance",
            "",
            f"- Profile SHA-256: `{report.profile_sha256}`",
            f"- Evidence ledger SHA-256: `{report.evidence_ledger_sha256}`",
            f"- Validation record SHA-256: `{report.validation_record_sha256}`",
        ]
    )
    if report.packet_manifest_sha256s:
        for packet_id, digest in sorted(report.packet_manifest_sha256s.items()):
            lines.append(f"- Packet `{packet_id}` SHA-256: `{digest}`")
    else:
        lines.append("- Packet manifests: None.")

    lines.extend(["", "## Finding inventory", ""])
    lines.extend(_render_findings(report.findings, compact=True))

    evidence_questions = [
        question for question in report.practice_questions if question.claim_ids
    ]
    lines.extend(["## Evidence-backed practice questions", ""])
    if evidence_questions:
        for question in evidence_questions:
            lines.extend(_render_question(question))
    else:
        lines.extend(["- None.", ""])
    lines.extend(
        _render_findings(
            [
                finding
                for finding in report.findings
                if finding.category == "wells_practice"
            ]
        )
    )

    lines.extend(["## Contextual diagnostics", ""])
    if report.diagnostics:
        for diagnostic in report.diagnostics:
            roles = (
                ", ".join(f"`{role}`" for role in diagnostic.roles)
                or "None"
            )
            lines.extend(
                [
                    f"### `{diagnostic.rule_id}` on `{diagnostic.manuscript}`",
                    "",
                    f"- Roles: {roles}",
                    f"- Sample size: {diagnostic.sample_size}",
                    f"- Review threshold crossed: "
                    f"`{'yes' if diagnostic.triggered else 'no'}`",
                ]
            )
            for metric, value in sorted(diagnostic.measurements.items()):
                lines.append(f"- `{metric}`: `{value}`")
            lines.extend(
                [
                    f"- Context: {diagnostic.tolerance_note}",
                    f"- Limits: {diagnostic.limitations}",
                    "",
                ]
            )
    else:
        lines.extend(["- None.", ""])
    contextual = [
        finding
        for finding in report.findings
        if finding.category == "contextual_diagnostic"
    ]
    lines.extend(["### Story-level observations", ""])
    lines.extend(
        _render_findings(
            [finding for finding in contextual if finding.scope == "story"]
        )
    )
    lines.extend(["### Chapter and passage observations", ""])
    lines.extend(
        _render_findings(
            [finding for finding in contextual if finding.scope != "story"]
        )
    )

    lines.extend(["## Anti-drift observations", ""])
    anti_drift_questions = [
        question
        for question in report.practice_questions
        if not question.claim_ids
    ]
    if anti_drift_questions:
        for question in anti_drift_questions:
            lines.extend(_render_question(question))
    else:
        lines.extend(["- None.", ""])
    lines.extend(
        _render_findings(
            [
                finding
                for finding in report.findings
                if finding.category == "anti_drift"
            ]
        )
    )

    lines.extend(["## Surface warnings", ""])
    lines.extend(
        _render_findings(
            [
                finding
                for finding in report.findings
                if finding.category == "surface_warning"
            ]
        )
    )

    lines.extend(
        [
            "## Generic AI-writing signals",
            "",
            f"- Status: `{report.generic_ai.status}`",
            f"- Scanner: `{report.generic_ai.scanner or 'not run'}`",
            "- Groups: "
            + (
                ", ".join(
                    f"`{group}`" for group in report.generic_ai.group_names
                )
                or "None"
            ),
            f"- Caution: {report.generic_ai.caution}",
        ]
    )
    if report.generic_ai.notice:
        lines.append(f"- Notice: {report.generic_ai.notice}")
    lines.append("")
    lines.extend(
        _render_findings(
            [
                finding
                for finding in report.findings
                if finding.category == "generic_ai"
            ]
        )
    )

    lines.extend(["## Limitations", ""])
    lines.extend(f"- {item}" for item in report.limitations)
    lines.extend(["", "## Next steps", ""])
    lines.extend(f"- {item}" for item in report.next_steps)
    return "\n".join(lines).rstrip() + "\n"


def _packet_hashes(
    story_dir: Path,
    context: StyleContext,
) -> dict[str, str]:
    return {
        packet_id: sha256_file(
            story_dir / "style-reference-packets" / f"{packet_id}.yml"
        )
        for packet_id in context.packets
    }


def generate_style_lint(
    root: Path,
    slug: str,
    *,
    profile_override: str | None = None,
    chapter_selector: str | None = None,
) -> StyleLintResult:
    """Generate one deterministic Markdown/JSON advisory report pair."""

    if not isinstance(slug, str) or _SLUG.fullmatch(slug) is None:
        raise CreativeWriterError("Story slug must be a canonical lowercase slug")
    resolved_root = root.resolve(strict=False)
    story_dir = safe_relative_path(resolved_root, f"stories/{slug}")
    checked = check_story(resolved_root, slug)
    if (
        not checked.ok
        or checked.story is None
        or checked.contract is None
        or not checked.chapters
    ):
        raise CreativeWriterError(
            f"Cannot style-lint {slug}. Fix blocking issues first. "
            f"See {checked.report_path}."
        )

    configured_profile = (
        checked.contract.style_lint.profile
        if checked.contract.style_lint is not None
        else None
    )
    profile_path = resolve_style_profile_path(
        story_dir,
        configured_profile,
        profile_override,
    )
    context = load_style_context(resolved_root, story_dir, profile_path)
    metadata_errors = validate_chapter_style_metadata(
        context,
        checked.chapters,
    )
    if metadata_errors:
        raise CreativeWriterError(
            "Invalid chapter style metadata:\n" + "\n".join(metadata_errors)
        )

    chapters = _select_chapters(
        story_dir,
        checked.chapters,
        chapter_selector,
    )
    scope: Literal["story", "chapter"] = (
        "chapter" if chapter_selector is not None else "story"
    )
    manuscripts = {
        chapter.manuscript_path: chapter.manuscript_path.relative_to(
            resolved_root
        ).as_posix()
        for chapter in chapters
    }
    stubs = {
        chapter.stub_path: chapter.stub_path.relative_to(
            resolved_root
        ).as_posix()
        for chapter in chapters
    }

    all_questions: list[StylePracticeQuestion] = []
    diagnostic_records: list[StyleDiagnosticRecord] = []
    findings: list[StyleFinding] = []
    inventories: list[StyleChapterInventory] = []

    generic_enabled = (
        checked.contract.style_lint is None
        or checked.contract.style_lint.generic_ai_audit
    )
    generic_status: Literal["complete", "unavailable", "disabled"] = (
        "complete" if generic_enabled else "disabled"
    )
    scanner_path: Path | None = None
    generic_groups: set[str] = set()
    generic_notice: str | None = (
        None
        if generic_enabled
        else "Generic AI-writing scan is disabled by story configuration."
    )

    for chapter in chapters:
        roles = chapter.front_matter.style_roles
        chapter_rules = _applicable_rules(
            context,
            roles,
            {"passage", "chapter"},
        )
        diagnostics = _analyse_for_rules(
            chapter.manuscript_body,
            chapter_rules,
        )
        evaluation = _evaluate_rules(
            chapter_rules,
            diagnostics,
            roles=roles,
            manuscript=manuscripts[chapter.manuscript_path],
        )
        all_questions.extend(evaluation.questions)
        diagnostic_records.extend(evaluation.diagnostics)
        findings.extend(evaluation.findings)
        findings.extend(
            _surface_finding(
                manuscripts[chapter.manuscript_path],
                roles,
                warning,
            )
            for warning in run_surface_heuristics(
                chapter.manuscript_body,
                checked.contract.lint,
            )
        )

        if generic_enabled and generic_status == "complete":
            scan = scan_ai_writing_json(
                chapter.manuscript_path,
                unavailable_is_error=False,
            )
            if scan.status == "unavailable":
                generic_status = "unavailable"
                generic_notice = scan.notice
            else:
                scanner_path = scan.script_path
                for group_name in sorted(scan.groups):
                    generic_groups.add(group_name)
                    group = scan.groups[group_name]
                    findings.extend(
                        _generic_finding(
                            manuscript=manuscripts[
                                chapter.manuscript_path
                            ],
                            roles=roles,
                            group_name=group_name,
                            group=group,
                            hit=hit,
                        )
                        for hit in group.hits
                    )

        inventories.append(
            StyleChapterInventory(
                stub=stubs[chapter.stub_path],
                manuscript=manuscripts[chapter.manuscript_path],
                title=chapter.front_matter.title,
                summary=chapter.front_matter.summary,
                roles=list(roles),
                packet_ids=list(chapter.front_matter.style_packets),
                word_count=diagnostics.word_count,
            )
        )

    union_roles = _unique(
        [
            role
            for chapter in chapters
            for role in chapter.front_matter.style_roles
        ]
    )
    story_rules = _applicable_rules(context, union_roles, {"story"})
    if story_rules:
        combined = _story_text(chapters, manuscripts)
        story_diagnostics = _analyse_for_rules(combined.text, story_rules)
        story_evaluation = _evaluate_rules(
            story_rules,
            story_diagnostics,
            roles=union_roles,
            manuscript=manuscripts[chapters[0].manuscript_path],
        )
        story_evaluation = _map_story_findings(
            story_evaluation,
            combined,
        )
        all_questions.extend(story_evaluation.questions)
        diagnostic_records.extend(story_evaluation.diagnostics)
        findings.extend(story_evaluation.findings)

    chapter_order = {
        manuscripts[chapter.manuscript_path]: index
        for index, chapter in enumerate(chapters)
    }
    findings = _assign_finding_ids(findings, chapter_order)
    questions = _merge_questions(context, all_questions)
    generic_section = GenericAIReportSection(
        status=generic_status,
        scanner=str(scanner_path) if scanner_path is not None else None,
        group_names=sorted(generic_groups),
        finding_ids=[
            finding.id
            for finding in findings
            if finding.category == "generic_ai"
        ],
        caution=_GENERIC_CAUTION,
        notice=generic_notice,
    )
    role_caveat = CHAPTER_ROLE_CAVEAT
    if any(len(chapter.front_matter.style_roles) > 1 for chapter in chapters):
        role_caveat += _MIXED_ROLE_CAVEAT

    report = StyleLintReport(
        schema_version=1,
        story_slug=slug,
        story_title=checked.story.title,
        scope=scope,
        chapter_selector=chapter_selector,
        profile_id=context.profile.profile_id,
        profile_version=context.profile.version,
        profile_sha256=sha256_file(context.profile_path),
        evidence_ledger_sha256=(
            context.profile.provenance.evidence_ledger.sha256
        ),
        validation_record_sha256=(
            context.profile.provenance.validation_record.sha256
        ),
        packet_manifest_sha256s=_packet_hashes(story_dir, context),
        chapters=inventories,
        role_caveat=role_caveat,
        findings=findings,
        practice_questions=questions,
        diagnostics=diagnostic_records,
        generic_ai=generic_section,
        limitations=[
            (
                "All findings are advisory prompts; absence of findings does "
                "not certify the prose."
            ),
            (
                "Narrative roles come only from chapter metadata and are not "
                "inferred at passage level."
            ),
            _SENTENCE_CAVEAT,
            _DIALOGUE_CAVEAT,
            (
                "Generic AI-writing signals remain separate from Phase 2B "
                "claims and source examples."
            ),
        ],
        next_steps=[
            "Review each finding in its complete manuscript context.",
            (
                "Compare evidence-backed questions with the cited reference "
                "packets before deciding whether revision is useful."
            ),
            (
                "Escalate only consequential or ambiguous passages for human "
                "calibration."
            ),
        ],
        partial=generic_status == "unavailable",
    )

    if scope == "story":
        output_dir = safe_relative_path(
            resolved_root,
            f"build/{slug}/style",
        )
        markdown_path = safe_relative_path(
            resolved_root,
            f"build/{slug}/style/lint-report.md",
        )
        json_path = safe_relative_path(
            resolved_root,
            f"build/{slug}/style/lint-report.json",
        )
    else:
        stem = chapters[0].stub_path.stem
        output_dir = safe_relative_path(
            resolved_root,
            f"build/{slug}/style/chapters",
        )
        markdown_path = safe_relative_path(
            resolved_root,
            f"build/{slug}/style/chapters/{stem}-lint-report.md",
        )
        json_path = safe_relative_path(
            resolved_root,
            f"build/{slug}/style/chapters/{stem}-lint-report.json",
        )
    try:
        ensure_directory(output_dir)
        markdown_path.write_text(_render_markdown(report), encoding="utf-8")
        json_path.write_text(
            json.dumps(
                report.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        raise CreativeWriterError(
            f"Unable to write style-lint report for {slug}: {exc}"
        ) from exc

    return StyleLintResult(
        story_slug=slug,
        scope=scope,
        profile_id=context.profile.profile_id,
        profile_version=context.profile.version,
        markdown_path=markdown_path,
        json_path=json_path,
        finding_count=len(findings),
        partial=report.partial,
    )
