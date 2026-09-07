"""Shared, location-aware prose surface heuristics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from creative_writer.models import LintSettings


_CONTRASTIVE_PATTERN = re.compile(
    r"\b(?:not only\b[^.!?\n]{0,80}\bbut also|not\b[^.!?\n]{0,80}\bbut)\b",
    re.IGNORECASE,
)
_SENTENCE_END = re.compile(r"[.!?]+[\"'”’]*(?=\s|$)")
_WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*")
_MIRROR_MAX_WORDS = 6


@dataclass(frozen=True, slots=True)
class SurfaceHeuristicWarning:
    rule_id: Literal["em-dash-overuse", "contrastive-parallelism"]
    observed: str
    line_start: int
    line_end: int


def _line_number(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def _sentences(text: str) -> list[tuple[int, str]]:
    """Return (offset, sentence) pairs in reading order, paragraph by paragraph."""

    sentences: list[tuple[int, str]] = []
    for paragraph in re.finditer(r"[^\n]+(?:\n[^\n]+)*", text):
        body = paragraph.group(0)
        start = 0
        for end in _SENTENCE_END.finditer(body):
            piece = body[start : end.end()]
            if piece.strip():
                lead = len(piece) - len(piece.lstrip())
                sentences.append((paragraph.start() + start + lead, piece.strip()))
            start = end.end()
        tail = body[start:]
        if tail.strip():
            lead = len(tail) - len(tail.lstrip())
            sentences.append((paragraph.start() + start + lead, tail.strip()))
    return sentences


def _mirrored_pairs(text: str) -> list[tuple[int, int]]:
    """Locate adjacent short sentences that open with the same two words.

    Antiphonal pairs such as "It is lunacy." / "It is experiment." are the
    epigrammatic form of contrastive parallelism that a "not X but Y" search
    cannot see.
    """

    sentences = _sentences(text)
    pairs: list[tuple[int, int]] = []
    for (first_start, first), (second_start, second) in zip(sentences, sentences[1:]):
        first_words = [word.casefold() for word in _WORD.findall(first)]
        second_words = [word.casefold() for word in _WORD.findall(second)]
        if (
            2 <= len(first_words) <= _MIRROR_MAX_WORDS
            and 2 <= len(second_words) <= _MIRROR_MAX_WORDS
            and first_words[:2] == second_words[:2]
            and first_words != second_words
        ):
            pairs.append((first_start, second_start + len(second) - 1))
    return pairs


def run_surface_heuristics(
    text: str,
    lint: LintSettings,
) -> list[SurfaceHeuristicWarning]:
    """Return configured warnings in the legacy check order."""

    warnings: list[SurfaceHeuristicWarning] = []
    em_dash_positions = [
        position for position, character in enumerate(text) if character == "—"
    ]
    word_count = len(_WORD.findall(text))
    rate = len(em_dash_positions) * 1000 / word_count if word_count else 0.0
    em_dash_limit = lint.em_dash.max_per_thousand_words
    if lint.em_dash.enabled and em_dash_positions and rate > em_dash_limit:
        warnings.append(
            SurfaceHeuristicWarning(
                rule_id="em-dash-overuse",
                observed=(
                    f"Em dashes: {len(em_dash_positions)} in {word_count} words "
                    f"({rate:.1f} per 1,000); configured maximum "
                    f"{em_dash_limit:g} per 1,000."
                ),
                line_start=_line_number(text, em_dash_positions[0]),
                line_end=_line_number(text, em_dash_positions[-1]),
            )
        )

    spans = [
        (match.start(), match.end() - 1)
        for match in _CONTRASTIVE_PATTERN.finditer(text)
    ]
    spans.extend(_mirrored_pairs(text))
    spans.sort()
    contrastive_limit = lint.contrastive_parallelism.max_instances_per_chapter
    if lint.contrastive_parallelism.enabled and len(spans) > contrastive_limit:
        warnings.append(
            SurfaceHeuristicWarning(
                rule_id="contrastive-parallelism",
                observed=(
                    f"Contrastive parallelism count {len(spans)} "
                    f"exceeds configured limit {contrastive_limit}."
                ),
                line_start=_line_number(text, spans[0][0]),
                line_end=_line_number(text, spans[-1][1]),
            )
        )

    return warnings
