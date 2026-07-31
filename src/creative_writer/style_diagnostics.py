"""Deterministic, hand-checkable manuscript style diagnostics.

Sentence boundaries use the project's deliberately approximate Victorian-text
scanner. Dialogue is likewise approximate: words inside matched straight or
curly double quotes count as dialogue, while nested quotations and attribution
boundaries are not parsed linguistically.
"""

from __future__ import annotations

import re
import statistics
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from creative_writer.source_metrics import sentence_spans, tokenize


_ATX_HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}(?:[ \t]+|$)")
_FENCE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
_MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
_HTML_IMAGE_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_DIALOGUE_RE = re.compile(r'“([^”]*?)”|"([^"]*?)"', re.DOTALL)


@dataclass(frozen=True, slots=True)
class TextLocation:
    line_start: int
    line_end: int


@dataclass(frozen=True, slots=True)
class LocatedSignal:
    location: TextLocation
    observed: str


@dataclass(slots=True)
class ManuscriptDiagnostics:
    word_count: int
    paragraph_count: int
    sentence_count: int
    sentence_lengths: list[int]
    paragraph_lengths: list[int]
    sentence_length_cv: float | None
    dialogue_word_proportion: float | None
    punctuation_counts: dict[str, int]
    lexicon_hits: dict[str, list[LocatedSignal]]
    repeated_ngrams: list[LocatedSignal]
    repeated_openings: list[LocatedSignal]


@dataclass(frozen=True, slots=True)
class _LocatedToken:
    text: str
    folded: str
    line: int


@dataclass(frozen=True, slots=True)
class _Paragraph:
    text: str
    tokens: tuple[_LocatedToken, ...]


def _strip_html_comments(line: str, in_comment: bool) -> tuple[str, bool]:
    visible: list[str] = []
    cursor = 0
    while cursor < len(line):
        if in_comment:
            end = line.find("-->", cursor)
            if end < 0:
                return "".join(visible), True
            visible.append(" ")
            cursor = end + 3
            in_comment = False
            continue

        start = line.find("<!--", cursor)
        if start < 0:
            visible.append(line[cursor:])
            break
        visible.append(line[cursor:start])
        visible.append(" ")
        cursor = start + 4
        in_comment = True
    return "".join(visible), in_comment


def _is_image_only(line: str) -> bool:
    if not line.strip():
        return False
    without_images = _MARKDOWN_IMAGE_RE.sub("", line)
    without_images = _HTML_IMAGE_RE.sub("", without_images)
    return not without_images.strip()


def _prose_lines(text: str) -> list[tuple[int, str]]:
    normalized = unicodedata.normalize("NFC", text)
    lines: list[tuple[int, str]] = []
    in_comment = False
    fence_character: str | None = None
    fence_length = 0

    for line_number, raw_line in enumerate(normalized.splitlines(), start=1):
        if fence_character is not None:
            closing = re.match(
                rf"^[ \t]{{0,3}}{re.escape(fence_character)}"
                rf"{{{fence_length},}}[ \t]*$",
                raw_line,
            )
            if closing:
                fence_character = None
                fence_length = 0
            lines.append((line_number, ""))
            continue

        visible, in_comment = _strip_html_comments(raw_line, in_comment)
        fence = _FENCE_RE.match(visible)
        if fence:
            marker = fence.group(1)
            fence_character = marker[0]
            fence_length = len(marker)
            lines.append((line_number, ""))
            continue

        if _ATX_HEADING_RE.match(visible) or _is_image_only(visible):
            visible = ""
        lines.append((line_number, visible))

    return lines


def _paragraphs(lines: Sequence[tuple[int, str]]) -> list[_Paragraph]:
    paragraphs: list[_Paragraph] = []
    current: list[tuple[int, str]] = []

    def finish_paragraph() -> None:
        if not current:
            return
        located_tokens = tuple(
            _LocatedToken(token, token.casefold(), line_number)
            for line_number, line in current
            for token in tokenize(line)
        )
        if located_tokens:
            paragraphs.append(
                _Paragraph(
                    text="\n".join(line for _, line in current),
                    tokens=located_tokens,
                )
            )
        current.clear()

    for line_number, line in lines:
        if line.strip():
            current.append((line_number, line))
        else:
            finish_paragraph()
    finish_paragraph()
    return paragraphs


def _punctuation_counts(text: str) -> dict[str, int]:
    ascii_ellipsis = len(re.findall(r"\.\.\.", text))
    counts = {
        "periods_raw": text.count("."),
        "periods": text.count(".") - (ascii_ellipsis * 3),
        "question_marks": text.count("?"),
        "exclamation_marks": text.count("!"),
        "colons": text.count(":"),
        "semicolons": text.count(";"),
        "parentheses_open": text.count("("),
        "parentheses_close": text.count(")"),
        "hyphen": text.count("-"),
        "en_dash": text.count("–"),
        "em_dash": text.count("—"),
        "ellipsis_unicode": text.count("…"),
        "ellipsis_ascii": ascii_ellipsis,
        "double_quote_open": text.count("“"),
        "double_quote_close": text.count("”"),
        "single_quote_open": text.count("‘"),
        "single_quote_close": text.count("’"),
        "straight_double_quote": text.count('"'),
        "straight_single_quote": text.count("'"),
        "guillemet_open": text.count("«"),
        "guillemet_close": text.count("»"),
    }
    counts["parentheses_total"] = (
        counts["parentheses_open"] + counts["parentheses_close"]
    )
    counts["dash_total"] = counts["hyphen"] + counts["en_dash"] + counts["em_dash"]
    counts["ellipsis_total"] = (
        counts["ellipsis_unicode"] + counts["ellipsis_ascii"]
    )
    return counts


def _lexicon_hits(
    paragraphs: Sequence[_Paragraph],
    lexicons: Mapping[str, Sequence[str]],
) -> dict[str, list[LocatedSignal]]:
    results: dict[str, list[LocatedSignal]] = {}
    for name, terms in lexicons.items():
        normalized_terms = [
            tuple(token.casefold() for token in tokenize(term))
            for term in terms
        ]
        normalized_terms = [term for term in normalized_terms if term]
        hits: list[LocatedSignal] = []
        for paragraph in paragraphs:
            tokens = paragraph.tokens
            for start in range(len(tokens)):
                for term in normalized_terms:
                    end = start + len(term)
                    if end > len(tokens):
                        continue
                    if tuple(token.folded for token in tokens[start:end]) != term:
                        continue
                    observed = " ".join(token.text for token in tokens[start:end])
                    hits.append(
                        LocatedSignal(
                            TextLocation(tokens[start].line, tokens[end - 1].line),
                            observed,
                        )
                    )
        results[name] = hits
    return results


def _repeated_ngrams(
    paragraphs: Sequence[_Paragraph],
    *,
    size: int,
    minimum: int,
    stop_words: Sequence[str],
) -> list[LocatedSignal]:
    if size < 1 or minimum < 2:
        raise ValueError("repeated n-gram size must be positive and minimum at least 2")

    stops = {
        token.casefold()
        for term in stop_words
        for token in tokenize(term)
    }
    occurrences: defaultdict[
        tuple[str, ...], list[tuple[int, TextLocation]]
    ] = defaultdict(list)
    order = 0
    for paragraph in paragraphs:
        tokens = paragraph.tokens
        for start in range(len(tokens) - size + 1):
            selected = tokens[start : start + size]
            phrase = tuple(token.folded for token in selected)
            if stops and all(token in stops for token in phrase):
                order += 1
                continue
            occurrences[phrase].append(
                (
                    order,
                    TextLocation(selected[0].line, selected[-1].line),
                )
            )
            order += 1

    repeated = [
        (positions[0][0], phrase, positions)
        for phrase, positions in occurrences.items()
        if len(positions) >= minimum
    ]
    repeated.sort(key=lambda item: (item[0], item[1]))
    return [
        LocatedSignal(
            TextLocation(positions[0][1].line_start, positions[-1][1].line_end),
            f"{' '.join(phrase)} ({len(positions)} occurrences)",
        )
        for _, phrase, positions in repeated
    ]


def _repeated_openings(
    paragraphs: Sequence[_Paragraph],
    *,
    prefix_words: int,
    minimum: int,
) -> list[LocatedSignal]:
    if prefix_words < 1 or minimum < 2:
        raise ValueError(
            "paragraph opening prefix must be positive and minimum at least 2"
        )

    occurrences: defaultdict[
        tuple[str, ...], list[tuple[int, TextLocation]]
    ] = defaultdict(list)
    for paragraph_number, paragraph in enumerate(paragraphs):
        selected = paragraph.tokens[:prefix_words]
        if len(selected) < prefix_words:
            continue
        phrase = tuple(token.folded for token in selected)
        occurrences[phrase].append(
            (
                paragraph_number,
                TextLocation(selected[0].line, selected[-1].line),
            )
        )

    repeated = [
        (positions[0][0], phrase, positions)
        for phrase, positions in occurrences.items()
        if len(positions) >= minimum
    ]
    repeated.sort(key=lambda item: (item[0], item[1]))
    return [
        LocatedSignal(
            TextLocation(positions[0][1].line_start, positions[-1][1].line_end),
            f"{' '.join(phrase)} ({len(positions)} paragraph openings)",
        )
        for _, phrase, positions in repeated
    ]


def analyse_manuscript(
    text: str,
    *,
    lexicons: Mapping[str, Sequence[str]],
    speech_attribution_verbs: Sequence[str],
    stop_words: Sequence[str] = (),
    repeated_ngram_size: int = 3,
    repeated_ngram_minimum: int = 3,
    opening_prefix_words: int = 3,
    opening_minimum: int = 3,
) -> ManuscriptDiagnostics:
    """Measure prose while retaining original source-line locations."""

    lines = _prose_lines(text)
    paragraphs = _paragraphs(lines)
    paragraph_lengths = [len(paragraph.tokens) for paragraph in paragraphs]
    sentence_lengths = [
        length
        for paragraph in paragraphs
        for start, end in sentence_spans(
            paragraph.text,
            speech_attribution_verbs,
        )
        if (length := len(tokenize(paragraph.text[start:end])))
    ]
    mean = statistics.fmean(sentence_lengths) if sentence_lengths else 0.0
    sentence_length_cv = (
        statistics.pstdev(sentence_lengths) / mean
        if len(sentence_lengths) >= 2 and mean
        else None
    )
    word_count = sum(paragraph_lengths)
    dialogue_words = sum(
        len(tokenize(match.group(1) or match.group(2) or ""))
        for paragraph in paragraphs
        for match in _DIALOGUE_RE.finditer(paragraph.text)
    )
    prose_text = "\n".join(line for _, line in lines)

    return ManuscriptDiagnostics(
        word_count=word_count,
        paragraph_count=len(paragraphs),
        sentence_count=len(sentence_lengths),
        sentence_lengths=sentence_lengths,
        paragraph_lengths=paragraph_lengths,
        sentence_length_cv=sentence_length_cv,
        dialogue_word_proportion=(
            dialogue_words / word_count if word_count else None
        ),
        punctuation_counts=_punctuation_counts(prose_text),
        lexicon_hits=_lexicon_hits(paragraphs, lexicons),
        repeated_ngrams=_repeated_ngrams(
            paragraphs,
            size=repeated_ngram_size,
            minimum=repeated_ngram_minimum,
            stop_words=stop_words,
        ),
        repeated_openings=_repeated_openings(
            paragraphs,
            prefix_words=opening_prefix_words,
            minimum=opening_minimum,
        ),
    )
