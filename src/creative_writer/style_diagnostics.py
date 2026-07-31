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
_SETEXT_UNDERLINE_RE = re.compile(r"^[ \t]{0,3}(?:=+|-+)[ \t]*$")
_FENCE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
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


def _consume_bracketed(text: str, start: int) -> int | None:
    if start >= len(text) or text[start] != "[":
        return None
    depth = 1
    cursor = start + 1
    while cursor < len(text):
        character = text[cursor]
        if character == "\\" and cursor + 1 < len(text):
            cursor += 2
            continue
        if character == "[":
            depth += 1
        elif character == "]":
            depth -= 1
            if depth == 0:
                return cursor + 1
        cursor += 1
    return None


def _consume_angle_destination(text: str, start: int) -> int | None:
    if start >= len(text) or text[start] != "<":
        return None
    cursor = start + 1
    while cursor < len(text):
        character = text[cursor]
        if character == "\\" and cursor + 1 < len(text):
            cursor += 2
            continue
        if character == ">":
            return cursor + 1
        if character == "<":
            return None
        cursor += 1
    return None


def _consume_inline_bare_destination(text: str, start: int) -> int | None:
    depth = 0
    cursor = start
    while cursor < len(text):
        character = text[cursor]
        if character == "\\" and cursor + 1 < len(text):
            cursor += 2
            continue
        if character.isspace():
            return cursor if depth == 0 else None
        if ord(character) < 32 or character == "\x7f":
            return None
        if character == "(":
            depth += 1
        elif character == ")":
            if depth == 0:
                return cursor
            depth -= 1
        cursor += 1
    return None


def _consume_inline_title(text: str, start: int) -> int | None:
    delimiters = {'"': '"', "'": "'", "(": ")"}
    closer = delimiters.get(text[start]) if start < len(text) else None
    if closer is None:
        return None
    opener = text[start]
    cursor = start + 1
    while cursor < len(text):
        character = text[cursor]
        if character == "\\" and cursor + 1 < len(text):
            cursor += 2
            continue
        if character == closer:
            return cursor + 1
        if opener == "(" and character == "(":
            return None
        cursor += 1
    return None


def _consume_parenthesized(text: str, start: int) -> int | None:
    if start >= len(text) or text[start] != "(":
        return None
    cursor = start + 1
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    if cursor >= len(text):
        return None

    if text[cursor] == "<":
        destination_end = _consume_angle_destination(text, cursor)
    else:
        destination_end = _consume_inline_bare_destination(text, cursor)
    if destination_end is None:
        return None
    cursor = destination_end

    if cursor < len(text) and text[cursor] == ")":
        return cursor + 1
    if cursor >= len(text) or not text[cursor].isspace():
        return None
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    if cursor < len(text) and text[cursor] == ")":
        return cursor + 1

    title_end = _consume_inline_title(text, cursor)
    if title_end is None:
        return None
    cursor = title_end
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor + 1 if cursor < len(text) and text[cursor] == ")" else None


def _normalize_reference_label(label: str) -> str:
    return " ".join(unicodedata.normalize("NFC", label).casefold().split())


def _consume_markdown_image(
    text: str,
    start: int,
    reference_labels: set[str],
) -> int | None:
    if not text.startswith("![", start):
        return None
    alt_end = _consume_bracketed(text, start + 1)
    if alt_end is None:
        return None

    cursor = alt_end
    if cursor < len(text) and text[cursor] == "(":
        return _consume_parenthesized(text, cursor)

    alt = text[start + 2 : alt_end - 1]
    if cursor < len(text) and text[cursor] == "[":
        label_end = _consume_bracketed(text, cursor)
        if label_end is None:
            return None
        label = text[cursor + 1 : label_end - 1] or alt
        return (
            label_end
            if _normalize_reference_label(label) in reference_labels
            else None
        )

    return (
        cursor
        if _normalize_reference_label(alt) in reference_labels
        else None
    )


def _is_image_only(line: str, reference_labels: set[str]) -> bool:
    candidate = line.strip()
    if not candidate:
        return False

    cursor = 0
    found_image = False
    while cursor < len(candidate):
        if candidate[cursor].isspace():
            cursor += 1
            continue
        html_image = _HTML_IMAGE_RE.match(candidate, cursor)
        if html_image:
            cursor = html_image.end()
            found_image = True
            continue
        markdown_image_end = _consume_markdown_image(
            candidate,
            cursor,
            reference_labels,
        )
        if markdown_image_end is None:
            return False
        cursor = markdown_image_end
        found_image = True
    return found_image


def _consume_bare_destination(text: str, start: int) -> int | None:
    cursor = start
    depth = 0
    while cursor < len(text) and not text[cursor].isspace():
        character = text[cursor]
        if character == "\\" and cursor + 1 < len(text):
            cursor += 2
            continue
        if character == "(":
            depth += 1
        elif character == ")":
            if depth == 0:
                return None
            depth -= 1
        cursor += 1
    if cursor == start or depth:
        return None
    return cursor


def _reference_definition_label(line: str) -> str | None:
    indent = len(line) - len(line.lstrip(" \t"))
    if indent > 3:
        return None
    candidate = line[indent:]
    label_end = _consume_bracketed(candidate, 0)
    if label_end is None or label_end >= len(candidate):
        return None
    if candidate[label_end] != ":":
        return None

    cursor = label_end + 1
    while cursor < len(candidate) and candidate[cursor] in " \t":
        cursor += 1
    if cursor >= len(candidate):
        return None
    if candidate[cursor] == "<":
        destination_end = candidate.find(">", cursor + 1)
        if destination_end < 0:
            return None
        cursor = destination_end + 1
    else:
        destination_end = _consume_bare_destination(candidate, cursor)
        if destination_end is None:
            return None
        cursor = destination_end

    remainder = candidate[cursor:].strip()
    if remainder:
        delimiters = {'"': '"', "'": "'", "(": ")"}
        closer = delimiters.get(remainder[0])
        if closer is None or len(remainder) < 2 or remainder[-1] != closer:
            return None

    label = candidate[1 : label_end - 1]
    normalized = _normalize_reference_label(label)
    return normalized or None


def _exclude_markdown_blocks(
    lines: list[tuple[int, str]],
) -> list[tuple[int, str]]:
    reference_definitions = {
        index: label
        for index, (_, line) in enumerate(lines)
        if (label := _reference_definition_label(line)) is not None
    }
    reference_labels = set(reference_definitions.values())

    filtered = list(lines)
    for index in reference_definitions:
        line_number, _ = filtered[index]
        filtered[index] = (line_number, "")

    for index, (line_number, line) in enumerate(filtered):
        if _ATX_HEADING_RE.match(line) or _is_image_only(
            line,
            reference_labels,
        ):
            filtered[index] = (line_number, "")

    for index, (line_number, line) in enumerate(filtered):
        if not _SETEXT_UNDERLINE_RE.match(line):
            continue
        previous = index - 1
        if previous < 0 or not filtered[previous][1].strip():
            continue
        filtered[index] = (line_number, "")
        while previous >= 0 and filtered[previous][1].strip():
            previous_line_number, _ = filtered[previous]
            filtered[previous] = (previous_line_number, "")
            previous -= 1

    return filtered


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

        lines.append((line_number, visible))

    return _exclude_markdown_blocks(lines)


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
        normalized_terms: list[tuple[str, ...]] = []
        seen_terms: set[tuple[str, ...]] = set()
        for declared_term in terms:
            term = tuple(
                token.casefold()
                for token in tokenize(declared_term)
            )
            if not term or term in seen_terms:
                continue
            seen_terms.add(term)
            normalized_terms.append(term)
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
