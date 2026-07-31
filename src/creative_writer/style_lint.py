"""Generate deterministic, separated, advisory style-lint reports."""

from __future__ import annotations

import json
import math
import os
import re
import statistics
import unicodedata
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from creative_writer.ai_audit import scan_ai_writing_json
from creative_writer.checks import check_story
from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import (
    ensure_directory,
    load_chapter_document,
    load_yaml_model,
    split_front_matter,
)
from creative_writer.models import (
    ChapterDocument,
    ChapterFrontMatter,
    ContractConfig,
    StoryConfig,
)
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
_GENERIC_SCANNER_ID = "creative-writer-ai-writing-scanner"
_GENERIC_UNAVAILABLE_NOTICE = (
    "The optional creative-writer AI-writing scanner is unavailable."
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


@dataclass(frozen=True, slots=True)
class _PreflightChapter:
    stub_path: Path
    manuscript_path: Path
    stub_stem: str
    document: ChapterDocument


@dataclass(frozen=True, slots=True)
class _ReportTarget:
    output_dir: Path
    markdown_path: Path
    json_path: Path


@dataclass(frozen=True, slots=True)
class _PreflightLayout:
    story_dir: Path
    story: StoryConfig
    contract: ContractConfig
    chapters: tuple[_PreflightChapter, ...]
    story_target: _ReportTarget
    chapter_targets: dict[str, _ReportTarget]


@dataclass(slots=True)
class _PublicationEntry:
    final_path: Path
    content: bytes
    temporary_path: Path
    backup_path: Path
    had_original: bool
    staged: bool = False
    backed_up: bool = False
    published: bool = False


def _unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _contained_path(root: Path, relative: str, label: str) -> Path:
    try:
        return safe_relative_path(root, relative)
    except CreativeWriterError as exc:
        raise CreativeWriterError(
            f"{label} path is not physically contained: {exc}"
        ) from exc


def _require_directory(path: Path, label: str) -> None:
    if not path.is_dir() or path.is_symlink():
        raise CreativeWriterError(f"{label} path is not a physical directory: {path}")


def _require_file(path: Path, label: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise CreativeWriterError(f"{label} path is not a physical file: {path}")


def _preflight_directory(path: Path, label: str) -> None:
    if path.exists() and (not path.is_dir() or path.is_symlink()):
        raise CreativeWriterError(
            f"{label} path cannot be used as a physical directory: {path}"
        )


def _preflight_file_target(path: Path, label: str) -> None:
    if path.exists() and (not path.is_file() or path.is_symlink()):
        raise CreativeWriterError(
            f"{label} path cannot be used as a report file: {path}"
        )


def _report_target(
    root: Path,
    *,
    output_relative: str,
    markdown_relative: str,
    json_relative: str,
    label: str,
) -> _ReportTarget:
    output_dir = _contained_path(root, output_relative, f"{label} directory")
    markdown_path = _contained_path(
        root,
        markdown_relative,
        f"{label} Markdown target",
    )
    json_path = _contained_path(
        root,
        json_relative,
        f"{label} JSON target",
    )
    _preflight_directory(output_dir, f"{label} directory")
    _preflight_file_target(markdown_path, f"{label} Markdown target")
    _preflight_file_target(json_path, f"{label} JSON target")
    return _ReportTarget(
        output_dir=output_dir,
        markdown_path=markdown_path,
        json_path=json_path,
    )


def _physical_file_identity(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_dev, stat.st_ino


def _collision_key(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def _preflight_layout(root: Path, slug: str) -> _PreflightLayout:
    story_dir = _contained_path(root, f"stories/{slug}", "story")
    _require_directory(story_dir, "story")

    story_path = _contained_path(root, f"stories/{slug}/story.yml", "story config")
    contract_path = _contained_path(
        root,
        f"stories/{slug}/contract.yml",
        "story contract",
    )
    _require_file(story_path, "story config")
    _require_file(contract_path, "story contract")
    try:
        story = load_yaml_model(story_path, StoryConfig)
    except CreativeWriterError as exc:
        if "chapters must be unique" in str(exc):
            raise CreativeWriterError(
                f"Story {slug} has duplicate resolved stub identity"
            ) from exc
        raise
    contract = load_yaml_model(contract_path, ContractConfig)
    if story.style_card is not None:
        style_card = _contained_path(story_dir, story.style_card, "style card")
        _require_file(style_card, "style card")

    chapters: list[_PreflightChapter] = []
    stub_identities: set[tuple[int, int]] = set()
    manuscript_identities: set[tuple[int, int]] = set()
    stem_keys: set[str] = set()
    for configured_stub in story.chapters:
        stub_path = _contained_path(
            story_dir,
            configured_stub,
            "chapter stub",
        )
        _require_file(stub_path, "chapter stub")
        stub_identity = _physical_file_identity(stub_path)
        if stub_identity in stub_identities:
            raise CreativeWriterError(
                f"Story {slug} has duplicate resolved stub identity: {stub_path}"
            )
        stub_identities.add(stub_identity)

        try:
            metadata, _body = split_front_matter(
                stub_path.read_text(encoding="utf-8"),
                stub_path,
            )
            front_matter = ChapterFrontMatter.model_validate(metadata)
        except UnicodeDecodeError as exc:
            raise CreativeWriterError(
                f"Chapter stub is not valid UTF-8: {stub_path}"
            ) from exc
        except OSError as exc:
            raise CreativeWriterError(
                f"Unable to read chapter stub {stub_path}: {exc}"
            ) from exc
        except ValidationError as exc:
            raise CreativeWriterError(
                f"Schema validation failed for {stub_path}: {exc}"
            ) from exc

        manuscript_path = _contained_path(
            story_dir,
            front_matter.manuscript,
            "chapter manuscript",
        )
        _require_file(manuscript_path, "chapter manuscript")
        manuscript_identity = _physical_file_identity(manuscript_path)
        if manuscript_identity in manuscript_identities:
            raise CreativeWriterError(
                "Story "
                f"{slug} has duplicate resolved manuscript identity: "
                f"{manuscript_path}"
            )
        manuscript_identities.add(manuscript_identity)

        stem_key = _collision_key(stub_path.stem)
        if stem_key in stem_keys:
            raise CreativeWriterError(
                f"Story {slug} has duplicate stub stem/output collision: "
                f"{stub_path.stem}"
            )
        stem_keys.add(stem_key)
        try:
            document = load_chapter_document(story_dir, stub_path)
        except UnicodeDecodeError as exc:
            raise CreativeWriterError(
                f"Chapter manuscript is not valid UTF-8: {manuscript_path}"
            ) from exc
        except OSError as exc:
            raise CreativeWriterError(
                f"Unable to load chapter document {stub_path}: {exc}"
            ) from exc
        if document.manuscript_path != manuscript_path:
            raise CreativeWriterError(
                f"Chapter manuscript path changed during preflight: {stub_path}"
            )
        chapters.append(
            _PreflightChapter(
                stub_path=stub_path,
                manuscript_path=manuscript_path,
                stub_stem=stub_path.stem,
                document=document,
            )
        )

    build_dir = _contained_path(root, "build", "build directory")
    story_build_dir = _contained_path(
        root,
        f"build/{slug}",
        "story build directory",
    )
    reports_dir = _contained_path(
        root,
        f"build/{slug}/reports",
        "story reports directory",
    )
    coherence_path = _contained_path(
        root,
        f"build/{slug}/reports/coherence-report.md",
        "coherence report target",
    )
    style_dir = _contained_path(
        root,
        f"build/{slug}/style",
        "style report directory",
    )
    chapter_style_dir = _contained_path(
        root,
        f"build/{slug}/style/chapters",
        "chapter style report directory",
    )
    for path, label in (
        (build_dir, "build directory"),
        (story_build_dir, "story build directory"),
        (reports_dir, "story reports directory"),
        (style_dir, "style report directory"),
        (chapter_style_dir, "chapter style report directory"),
    ):
        _preflight_directory(path, label)
    _preflight_file_target(coherence_path, "coherence report target")

    story_target = _report_target(
        root,
        output_relative=f"build/{slug}/style",
        markdown_relative=f"build/{slug}/style/lint-report.md",
        json_relative=f"build/{slug}/style/lint-report.json",
        label="story style report",
    )
    chapter_targets: dict[str, _ReportTarget] = {}
    output_keys: set[str] = set()
    for chapter in chapters:
        target = _report_target(
            root,
            output_relative=f"build/{slug}/style/chapters",
            markdown_relative=(
                f"build/{slug}/style/chapters/"
                f"{chapter.stub_stem}-lint-report.md"
            ),
            json_relative=(
                f"build/{slug}/style/chapters/"
                f"{chapter.stub_stem}-lint-report.json"
            ),
            label=f"chapter {chapter.stub_stem} style report",
        )
        for path in (target.markdown_path, target.json_path):
            key = _collision_key(path.as_posix())
            if key in output_keys:
                raise CreativeWriterError(
                    f"Story {slug} has a chapter report output collision: {path}"
                )
            output_keys.add(key)
        chapter_targets[chapter.stub_stem] = target

    return _PreflightLayout(
        story_dir=story_dir,
        story=story,
        contract=contract,
        chapters=tuple(chapters),
        story_target=story_target,
        chapter_targets=chapter_targets,
    )


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


def _story_rule_groups(
    context: StyleContext,
    chapters: Sequence[ChapterDocument],
) -> dict[tuple[int, ...], list[ResolvedStyleRule]]:
    groups: dict[tuple[int, ...], list[ResolvedStyleRule]] = {}
    for resolved in context.rules:
        if resolved.rule.scope != "story":
            continue
        applicable_indexes = tuple(
            index
            for index, chapter in enumerate(chapters)
            if _applies(resolved, chapter.front_matter.style_roles)
        )
        if applicable_indexes:
            groups.setdefault(applicable_indexes, []).append(resolved)
    return groups


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
    if kind == "repeated_ngram":
        signatures = {
            (
                signal.ngram_size,
                signal.minimum_occurrences,
                tuple(sorted(word.casefold() for word in signal.stop_words)),
            )
            for signal in signals
        }
    elif kind == "paragraph_opening":
        signatures = {
            (
                signal.prefix_words,
                signal.minimum_occurrences,
            )
            for signal in signals
        }
    else:
        signatures = {
            repr(signal.model_dump(mode="json")) for signal in signals
        }
    if len(signatures) > 1:
        raise CreativeWriterError(
            f"Applicable {kind} rules require incompatible one-pass settings"
        )
    return signals[0]


def _validate_shared_pass_compatibility(
    context: StyleContext,
    chapters: Sequence[ChapterDocument],
) -> None:
    rule_sets = [
        _applicable_rules(
            context,
            chapter.front_matter.style_roles,
            {"passage", "chapter"},
        )
        for chapter in chapters
    ]
    rule_sets.extend(_story_rule_groups(context, chapters).values())
    for rules in rule_sets:
        _single_signal_configuration(rules, "repeated_ngram")
        _single_signal_configuration(rules, "paragraph_opening")


def _validate_measurement_contract(
    rules: Sequence[ResolvedStyleRule],
) -> None:
    metrics_by_signal = {
        "sentence_profile": {
            "sentence_length_median",
            "sentence_length_p90",
            "sentence_length_cv",
            "paragraph_length_median",
        },
        "dialogue_profile": {"dialogue_proportion"},
    }
    for resolved in rules:
        rule = resolved.rule
        if rule.tolerance is None:
            continue
        if rule.signal is None:
            raise CreativeWriterError(
                f"Style rule {rule.id} has a tolerance but no signal"
            )
        available = metrics_by_signal.get(rule.signal.kind, set())
        if rule.tolerance.metric not in available:
            raise CreativeWriterError(
                f"Style rule {rule.id} signal {rule.signal.kind} cannot produce "
                f"configured measurement {rule.tolerance.metric}"
            )


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
    claims = list(resolved.claims)
    return StylePracticeQuestion(
        rule_id=resolved.rule.id,
        advisory=resolved.rule.advisory,
        roles=_matching_roles(resolved, roles),
        claim_ids=[claim.id for claim in claims],
        claim_statuses={claim.id: claim.status for claim in claims},
        claim_jurisdictions=[claim.jurisdiction for claim in claims],
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
    claims = list(resolved.claims)
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
        claim_ids=[claim.id for claim in claims],
        claim_statuses={claim.id: claim.status for claim in claims},
        claim_jurisdictions=[claim.jurisdiction for claim in claims],
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
    diagnostic_manuscripts: Sequence[str] | None = None,
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
                manuscript=(
                    manuscript
                    if diagnostic_manuscripts is None
                    else None
                ),
                manuscripts=(
                    [manuscript]
                    if diagnostic_manuscripts is None
                    else list(diagnostic_manuscripts)
                ),
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
        claim_statuses={},
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
            f"{hit.group} match "
            f"{json.dumps(hit.match, ensure_ascii=False)} in context "
            f"{json.dumps(hit.context, ensure_ascii=False)}"
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
        claim_statuses={},
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


def _markdown_safe(value: str) -> str:
    return re.sub(r"([\\`*_\[\]{}<>#|])", r"\\\1", value)


def _render_claim_statuses(
    claim_ids: Sequence[str],
    claim_statuses: dict[str, str],
) -> str:
    return (
        ", ".join(
            f"`{claim_id}`: `{claim_statuses[claim_id]}`"
            for claim_id in claim_ids
        )
        or "None"
    )


def _render_claim_jurisdictions(jurisdictions: Sequence[object]) -> str:
    rendered: list[str] = []
    for jurisdiction in jurisdictions:
        roles = (
            ", ".join(f"`{role}`" for role in jurisdiction.roles)
            or "None"
        )
        witnesses = (
            ", ".join(
                f"`{witness}`"
                for witness in jurisdiction.eligible_witness_ids
            )
            or "None"
        )
        rendered.append(
            f"`{jurisdiction.scope}` (roles: {roles}; "
            f"eligible witnesses: {witnesses})"
        )
    return "; ".join(rendered) or "None"


def _render_question(question: StylePracticeQuestion) -> list[str]:
    claims = ", ".join(f"`{claim}`" for claim in question.claim_ids) or "None"
    statuses = _render_claim_statuses(
        question.claim_ids,
        question.claim_statuses,
    )
    jurisdictions = _render_claim_jurisdictions(
        question.claim_jurisdictions
    )
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
        f"- Claim statuses: {statuses}",
        f"- Claim jurisdictions: {jurisdictions}",
        f"- Source passages: {sources}",
        f"- Question: {_markdown_safe(question.question)}",
        f"- Limits: {_markdown_safe(question.interpretation_limits)}",
        "",
    ]


def _render_finding(finding: StyleFinding) -> list[str]:
    roles = ", ".join(f"`{role}`" for role in finding.roles) or "None"
    claims = ", ".join(f"`{claim}`" for claim in finding.claim_ids) or "None"
    statuses = _render_claim_statuses(
        finding.claim_ids,
        finding.claim_statuses,
    )
    jurisdictions = _render_claim_jurisdictions(
        finding.claim_jurisdictions
    )
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
        f"- Claim statuses: {statuses}",
        f"- Claim jurisdictions: {jurisdictions}",
        f"- Source passages: {sources}",
        f"- Observed: {_markdown_safe(finding.observed_signal)}",
        f"- Editorial question: {_markdown_safe(finding.editorial_question)}",
        f"- Limits: {_markdown_safe(finding.limitations)}",
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
                f"`{finding.rule_id}` | "
                f"{_markdown_safe(finding.observed_signal)}"
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
            provenance = ", ".join(
                f"`{manuscript}`"
                for manuscript in diagnostic.manuscripts
            )
            heading = (
                f"on `{diagnostic.manuscript}`"
                if diagnostic.manuscript is not None
                else f"across {provenance}"
            )
            lines.extend(
                [
                    f"### `{diagnostic.rule_id}` {heading}",
                    "",
                    f"- Roles: {roles}",
                    f"- Manuscripts measured: {provenance}",
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


def _recheck_report_target(root: Path, target: _ReportTarget) -> None:
    for path, label in (
        (target.output_dir, "style report directory"),
        (target.markdown_path, "style report Markdown target"),
        (target.json_path, "style report JSON target"),
    ):
        relative = path.relative_to(root).as_posix()
        checked = _contained_path(root, relative, label)
        if checked != path:
            raise CreativeWriterError(
                f"{label} path changed after preflight: {path}"
            )
    _preflight_directory(target.output_dir, "style report directory")
    _preflight_file_target(
        target.markdown_path,
        "style report Markdown target",
    )
    _preflight_file_target(
        target.json_path,
        "style report JSON target",
    )


def _stage_report_entry(entry: _PublicationEntry) -> None:
    with entry.temporary_path.open("xb") as handle:
        entry.staged = True
        handle.write(entry.content)
        handle.flush()
        os.fsync(handle.fileno())


def _remove_if_present(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _rollback_report_entries(
    entries: Sequence[_PublicationEntry],
) -> list[str]:
    errors: list[str] = []
    for entry in reversed(entries):
        try:
            if entry.published:
                _remove_if_present(entry.final_path)
            if entry.backed_up and entry.backup_path.exists():
                os.replace(entry.backup_path, entry.final_path)
            elif not entry.had_original:
                _remove_if_present(entry.final_path)
        except OSError as exc:
            errors.append(f"{entry.final_path}: {exc}")
    return errors


def _cleanup_staged_temporaries(
    entries: Sequence[_PublicationEntry],
) -> list[str]:
    errors: list[str] = []
    for entry in entries:
        if not entry.staged:
            continue
        try:
            _remove_if_present(entry.temporary_path)
        except OSError as exc:
            errors.append(f"{entry.temporary_path}: {exc}")
    return errors


def _publish_report_pair(
    target: _ReportTarget,
    *,
    markdown_bytes: bytes,
    json_bytes: bytes,
) -> None:
    markdown_exists = target.markdown_path.exists()
    json_exists = target.json_path.exists()
    if markdown_exists != json_exists:
        raise CreativeWriterError(
            "Cannot publish style-lint report over an incomplete existing "
            "Markdown/JSON pair"
        )

    token = uuid.uuid4().hex
    entries = [
        _PublicationEntry(
            final_path=target.markdown_path,
            content=markdown_bytes,
            temporary_path=target.markdown_path.with_name(
                f".{target.markdown_path.name}.tmp-{token}"
            ),
            backup_path=target.markdown_path.with_name(
                f".{target.markdown_path.name}.backup-{token}"
            ),
            had_original=markdown_exists,
        ),
        _PublicationEntry(
            final_path=target.json_path,
            content=json_bytes,
            temporary_path=target.json_path.with_name(
                f".{target.json_path.name}.tmp-{token}"
            ),
            backup_path=target.json_path.with_name(
                f".{target.json_path.name}.backup-{token}"
            ),
            had_original=json_exists,
        ),
    ]
    for entry in entries:
        if entry.temporary_path.exists() or entry.backup_path.exists():
            raise CreativeWriterError(
                "Cannot publish style-lint report because a staging path "
                f"already exists: {entry.temporary_path}"
            )
    try:
        for entry in entries:
            _stage_report_entry(entry)
        if markdown_exists:
            for entry in entries:
                os.replace(entry.final_path, entry.backup_path)
                entry.backed_up = True
        for entry in entries:
            os.replace(entry.temporary_path, entry.final_path)
            entry.published = True
    except OSError as exc:
        rollback_errors = _rollback_report_entries(entries)
        cleanup_errors = _cleanup_staged_temporaries(entries)
        details = [
            (
                f"rollback errors: {'; '.join(rollback_errors)}"
                if rollback_errors
                else ""
            ),
            (
                f"temporary cleanup errors: {'; '.join(cleanup_errors)}"
                if cleanup_errors
                else ""
            ),
        ]
        detail = "; " + "; ".join(item for item in details if item) if any(
            details
        ) else ""
        raise CreativeWriterError(
            f"Unable to publish style-lint report pair: {exc}{detail}"
        ) from exc

    cleanup_errors = _cleanup_staged_temporaries(entries)
    for entry in entries:
        try:
            _remove_if_present(entry.backup_path)
        except OSError as exc:
            cleanup_errors.append(f"{entry.backup_path}: {exc}")
    if cleanup_errors:
        raise CreativeWriterError(
            "Style-lint report pair was published, but backup cleanup failed: "
            + "; ".join(cleanup_errors)
        )


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
    layout = _preflight_layout(resolved_root, slug)
    story_dir = layout.story_dir
    configured_profile = (
        layout.contract.style_lint.profile
        if layout.contract.style_lint is not None
        else None
    )
    profile_path = resolve_style_profile_path(
        story_dir,
        configured_profile,
        profile_override,
    )
    context = load_style_context(resolved_root, story_dir, profile_path)
    preflight_documents = [
        chapter.document for chapter in layout.chapters
    ]
    metadata_errors = validate_chapter_style_metadata(
        context,
        preflight_documents,
    )
    if metadata_errors:
        raise CreativeWriterError(
            "Invalid chapter style metadata:\n" + "\n".join(metadata_errors)
        )
    _validate_measurement_contract(context.rules)
    selected_preflight_documents = _select_chapters(
        story_dir,
        preflight_documents,
        chapter_selector,
    )
    _validate_shared_pass_compatibility(
        context,
        selected_preflight_documents,
    )
    profile_sha256 = sha256_file(context.profile_path)
    packet_manifest_sha256s = _packet_hashes(story_dir, context)

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
    if checked.story != layout.story or checked.contract != layout.contract:
        raise CreativeWriterError(
            "Story configuration changed after style-lint preflight"
        )
    if len(checked.chapters) != len(layout.chapters):
        raise CreativeWriterError(
            "Configured chapter inventory changed after path preflight"
        )
    for chapter, preflight_chapter in zip(
        checked.chapters,
        layout.chapters,
        strict=True,
    ):
        _require_file(chapter.stub_path, "chapter stub")
        _require_file(chapter.manuscript_path, "chapter manuscript")
        if (
            _physical_file_identity(chapter.stub_path)
            != _physical_file_identity(preflight_chapter.stub_path)
            or _physical_file_identity(chapter.manuscript_path)
            != _physical_file_identity(preflight_chapter.manuscript_path)
        ):
            raise CreativeWriterError(
                "Configured chapter paths changed after path preflight"
            )
    selected_stub_paths = [
        chapter.stub_path for chapter in selected_preflight_documents
    ]
    checked_by_stub = {
        chapter.stub_path: chapter for chapter in checked.chapters
    }
    try:
        chapters = [
            checked_by_stub[stub_path] for stub_path in selected_stub_paths
        ]
    except KeyError as exc:
        raise CreativeWriterError(
            "Selected chapter inventory changed after style-lint preflight"
        ) from exc
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
                generic_notice = _GENERIC_UNAVAILABLE_NOTICE
            else:
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

    for applicable_indexes, story_rules in _story_rule_groups(
        context,
        chapters,
    ).items():
        applicable_chapters = [
            chapters[index] for index in applicable_indexes
        ]
        applicable_roles = _unique(
            [
                role
                for chapter in applicable_chapters
                for role in chapter.front_matter.style_roles
            ]
        )
        combined = _story_text(applicable_chapters, manuscripts)
        story_diagnostics = _analyse_for_rules(
            combined.text,
            story_rules,
        )
        story_evaluation = _evaluate_rules(
            story_rules,
            story_diagnostics,
            roles=applicable_roles,
            manuscript=manuscripts[
                applicable_chapters[0].manuscript_path
            ],
            diagnostic_manuscripts=[
                manuscripts[chapter.manuscript_path]
                for chapter in applicable_chapters
            ],
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
        scanner=(
            _GENERIC_SCANNER_ID
            if generic_status == "complete"
            else None
        ),
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
        profile_sha256=profile_sha256,
        evidence_ledger_sha256=(
            context.profile.provenance.evidence_ledger.sha256
        ),
        validation_record_sha256=(
            context.profile.provenance.validation_record.sha256
        ),
        packet_manifest_sha256s=packet_manifest_sha256s,
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

    target = (
        layout.story_target
        if scope == "story"
        else layout.chapter_targets[chapters[0].stub_path.stem]
    )
    markdown_bytes = _render_markdown(report).encode("utf-8")
    json_bytes = json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    ).encode("utf-8")
    _recheck_report_target(resolved_root, target)
    try:
        ensure_directory(target.output_dir)
    except OSError as exc:
        raise CreativeWriterError(
            f"Unable to prepare style-lint report directory for {slug}: {exc}"
        ) from exc
    _recheck_report_target(resolved_root, target)
    _publish_report_pair(
        target,
        markdown_bytes=markdown_bytes,
        json_bytes=json_bytes,
    )

    return StyleLintResult(
        story_slug=slug,
        scope=scope,
        profile_id=context.profile.profile_id,
        profile_version=context.profile.version,
        markdown_path=target.markdown_path,
        json_path=target.json_path,
        finding_count=len(findings),
        partial=report.partial,
    )
