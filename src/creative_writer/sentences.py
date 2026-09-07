"""Word tokenizer and sentence scanner for manuscript diagnostics.

The sentence scanner is a Victorian-text approximation. It handles the
observed title/initial forms, quotation closers, lower-case speech
attributions, ellipses, em dashes, contractions, and final fragments, but it
is not a general linguistic parser. Initials that begin a sentence,
deliberately lower-case prose after a full stop, nested quotation marks, and
editorially irregular punctuation can still be misclassified.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Sequence

TOKEN_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)
_TERMINAL = ".?!…"
_CLOSERS = "\"'”’»’)]}"
_SUPPORTED_QUOTE_CLOSERS = frozenset({"\"", "'", "”", "’", "»"})
_TITLES = {"mr", "mrs", "ms", "dr"}


def tokenize(text: str) -> list[str]:
    """Return NFC-normalized word tokens, retaining internal apostrophes."""

    return TOKEN_RE.findall(unicodedata.normalize("NFC", text))


def _casefold_tokens(text: str) -> list[str]:
    return [token.casefold() for token in tokenize(text)]


def _next_word(text: str, index: int) -> tuple[str, int] | None:
    match = TOKEN_RE.search(text, index)
    if match is None:
        return None
    return match.group(0), match.end()


def _previous_word(text: str, index: int) -> tuple[str, int, int] | None:
    matches = list(TOKEN_RE.finditer(text, 0, index))
    if not matches:
        return None
    match = matches[-1]
    return match.group(0), match.start(), match.end()


def _skip_after_terminal(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def _is_nonterminal_period(text: str, index: int, end: int) -> bool:
    """Recognise the fixed title/initial protection rules."""

    if end != index + 1 or text[index] != ".":
        return False
    previous = _previous_word(text, index)
    following = _next_word(text, end)
    if previous is None or following is None:
        return False
    word, start, _ = previous
    next_word, _ = following
    if word.casefold() in _TITLES:
        return True
    if len(word) <= 3 and word.isascii() and word.isupper():
        if len(next_word) <= 3 and next_word.isascii() and next_word.isupper():
            return True
        prefix = text[max(0, start - 3) : start]
        if re.search(r"[A-Z]\.$", prefix):
            return True
        if next_word[:1].isupper():
            return True
    return False


def _terminal_runs(text: str) -> Iterable[tuple[int, int, str]]:
    index = 0
    while index < len(text):
        character = text[index]
        if character not in _TERMINAL:
            index += 1
            continue
        start = index
        if character == "." and text[index : index + 3] == "...":
            index += 3
            kind = "ascii_ellipsis"
        else:
            index += 1
            kind = "ellipsis" if character == "…" else "terminal"
        while index < len(text) and text[index] in _TERMINAL:
            index += 1
        yield start, index, kind


def _is_quote_attribution(
    text: str,
    event_end: int,
    speech_attribution_verbs: set[str],
) -> bool:
    """Return whether a terminal immediately closes a quoted utterance."""

    if event_end >= len(text) or text[event_end] not in _SUPPORTED_QUOTE_CLOSERS:
        return False
    cursor = event_end + 1
    while cursor < len(text) and text[cursor] in _CLOSERS:
        cursor += 1
    while cursor < len(text) and text[cursor] in ",;:—–-":
        cursor += 1
        while cursor < len(text) and text[cursor] in _CLOSERS:
            cursor += 1
    cursor = _skip_after_terminal(text, cursor)
    next_word = _next_word(text, cursor)
    if next_word is None or not next_word[0][:1].islower():
        return False
    next_terminal = next(
        (start for start, _, _ in _terminal_runs(text) if start >= next_word[1]),
        len(text),
    )
    attribution_tokens = set(_casefold_tokens(text[cursor:next_terminal]))
    return bool(attribution_tokens & speech_attribution_verbs)


def sentence_spans(text: str, speech_attribution_verbs: Sequence[str]) -> list[tuple[int, int]]:
    """Return sentence-like spans using the adopted left-to-right scanner."""

    normalized = unicodedata.normalize("NFC", text)
    verbs = {term.casefold() for term in speech_attribution_verbs}
    spans: list[tuple[int, int]] = []
    start = 0
    for event_start, event_end, kind in _terminal_runs(normalized):
        if event_start < start or _is_nonterminal_period(normalized, event_start, event_end):
            continue
        cursor = event_end
        while cursor < len(normalized) and normalized[cursor] in _CLOSERS:
            cursor += 1
        after_cursor = cursor
        while after_cursor < len(normalized) and normalized[after_cursor] in ",;:—–-":
            after_cursor += 1
            while after_cursor < len(normalized) and normalized[after_cursor] in _CLOSERS:
                after_cursor += 1
        after_cursor = _skip_after_terminal(normalized, after_cursor)
        next_word = _next_word(normalized, after_cursor)
        if kind in {"ascii_ellipsis", "ellipsis"} and next_word is not None:
            if next_word[0][:1].islower():
                continue
        if _is_quote_attribution(normalized, event_end, verbs):
            continue
        boundary = max(cursor, event_end)
        while boundary < len(normalized) and normalized[boundary] in _CLOSERS:
            boundary += 1
        spans.append((start, boundary))
        start = boundary
    if normalized[start:].strip():
        spans.append((start, len(normalized)))
    return spans
