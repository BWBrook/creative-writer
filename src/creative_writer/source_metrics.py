"""Transparent, standard-library metrics for the Phase 2B source study.

The sentence scanner is deliberately a Victorian-text approximation.  It is
fixture-tested for the observed title/initial forms, quotation closers,
lower-case speech attributions, ellipses, em dashes, contractions, and final
fragments, but it is not a general linguistic parser.  In particular,
initials that begin a sentence, deliberately lower-case prose after a full
stop, nested quotation marks, and editorially irregular punctuation can still
be misclassified.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import tempfile
import unicodedata
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from creative_writer.exceptions import CreativeWriterError
from creative_writer.source_analysis_models import (
    AnalysisConfig,
    MetricCandidateFlag,
    MetricDistribution,
    PassageRecord,
)


TOKEN_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)
_TERMINAL = ".?!…"
_CLOSERS = "\"'”’»’)]}"
_OPENING_QUOTES = "\"'“‘«"
_SUPPORTED_QUOTE_PAIRS = {"“": "”", "‘": "’", "«": "»"}
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


def _after_closers_and_attribution(text: str, index: int) -> tuple[int, str]:
    cursor = index
    while cursor < len(text) and text[cursor] in ",;:—–-" + _CLOSERS:
        cursor += 1
    cursor = _skip_after_terminal(text, cursor)
    return cursor, text[cursor:]


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


def sentence_token_lengths(text: str, speech_attribution_verbs: Sequence[str]) -> list[int]:
    return [len(tokenize(text[start:end])) for start, end in sentence_spans(text, speech_attribution_verbs)]


def _distribution(values: Sequence[int | float]) -> dict[str, int | float]:
    if not values:
        return {"count": 0, "minimum": None, "p10": None, "p25": None, "median": None,
                "p75": None, "p90": None, "maximum": None, "mean": None}
    ordered = sorted(float(value) for value in values)

    def percentile(probability: float) -> float:
        position = (len(ordered) - 1) * probability
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] + (ordered[upper] - ordered[lower]) * weight

    def integer_or_float(value: float) -> int | float:
        return int(value) if value.is_integer() else value

    return MetricDistribution.model_validate({
        "count": len(ordered),
        "minimum": integer_or_float(ordered[0]),
        "p10": integer_or_float(percentile(0.10)),
        "p25": integer_or_float(percentile(0.25)),
        "median": integer_or_float(percentile(0.50)),
        "p75": integer_or_float(percentile(0.75)),
        "p90": integer_or_float(percentile(0.90)),
        "maximum": integer_or_float(ordered[-1]),
        "mean": integer_or_float(sum(ordered) / len(ordered)),
    }).model_dump(mode="json")


def _quote_token_indexes(
    text: str, token_matches: Sequence[re.Match[str]]
) -> set[int] | None:
    stack: list[str] = []
    quoted: set[int] = set()
    cursor = 0

    def consume(start: int, end: int) -> bool:
        for position in range(start, end):
            character = text[position]
            if character in _SUPPORTED_QUOTE_PAIRS:
                stack.append(_SUPPORTED_QUOTE_PAIRS[character])
            elif character in _SUPPORTED_QUOTE_PAIRS.values():
                if not stack or character != stack[-1]:
                    return False
                stack.pop()
            elif character == '"':
                if stack and stack[-1] == '"':
                    stack.pop()
                else:
                    stack.append('"')
            elif character == "'" and not (
                position > 0
                and position + 1 < len(text)
                and text[position - 1].isalnum()
                and text[position + 1].isalnum()
            ):
                if stack and stack[-1] == "'":
                    stack.pop()
                else:
                    stack.append("'")
        return True

    for index, match in enumerate(token_matches):
        if not consume(cursor, match.start()):
            return None
        if stack:
            quoted.add(index)
        cursor = match.end()
    if not consume(cursor, len(text)) or stack:
        return None
    return quoted


def _dialogue_words(passage: PassageRecord, tokens: Sequence[str]) -> tuple[int, int]:
    if passage.direct_dialogue == "direct":
        return len(tokens), 0
    if passage.direct_dialogue == "none":
        return 0, 0
    if passage.direct_dialogue == "unknown":
        return 0, len(tokens)
    matches = list(TOKEN_RE.finditer(unicodedata.normalize("NFC", passage.normalized_text)))
    quoted = _quote_token_indexes(passage.normalized_text, matches)
    if quoted is None or not quoted:
        return 0, len(tokens)
    return len(quoted), 0


def _punctuation(passages: Sequence[PassageRecord]) -> dict[str, Any]:
    normalized_texts = [unicodedata.normalize("NFC", passage.normalized_text) for passage in passages]
    original = "".join(passage.original_text for passage in passages)
    ascii_ellipsis = sum(len(re.findall(r"\.\.\.", text)) for text in normalized_texts)
    normalized = "".join(normalized_texts)
    result: dict[str, Any] = {
        "periods_raw": normalized.count("."),
        "periods": normalized.count(".") - (ascii_ellipsis * 3),
        "question_marks": normalized.count("?"),
        "exclamation_marks": normalized.count("!"),
        "colons": normalized.count(":"),
        "semicolons": normalized.count(";"),
        "parentheses_open": normalized.count("("),
        "parentheses_close": normalized.count(")"),
        "hyphen": normalized.count("-"),
        "en_dash": normalized.count("–"),
        "em_dash": normalized.count("—"),
        "ellipsis_unicode": normalized.count("…"),
        "ellipsis_ascii": ascii_ellipsis,
        "double_quote_open": normalized.count("“"),
        "double_quote_close": normalized.count("”"),
        "single_quote_open": normalized.count("‘"),
        "single_quote_close": normalized.count("’"),
        "straight_double_quote": normalized.count('"'),
        "straight_single_quote": normalized.count("'"),
        "guillemet_open": normalized.count("«"),
        "guillemet_close": normalized.count("»"),
        "normalization_artifacts": {
            "bom": original.count("\ufeff"),
            "hair_space": original.count("\u200a"),
            "nbsp": original.count("\u00a0"),
        },
    }
    result["parentheses_total"] = result["parentheses_open"] + result["parentheses_close"]
    result["dash_total"] = result["hyphen"] + result["en_dash"] + result["em_dash"]
    result["ellipsis_total"] = result["ellipsis_unicode"] + result["ellipsis_ascii"]
    result["quote_counts_by_codepoint"] = {
        "U+2018": result["single_quote_open"],
        "U+2019": result["single_quote_close"],
        "U+201C": result["double_quote_open"],
        "U+201D": result["double_quote_close"],
        "U+0027": result["straight_single_quote"],
        "U+0022": result["straight_double_quote"],
        "U+00AB": result["guillemet_open"],
        "U+00BB": result["guillemet_close"],
    }
    denominator_words = sum(len(tokenize(text)) for text in normalized_texts)
    result["denominator_words"] = denominator_words
    result["per_1000_words"] = {
        key: value / denominator_words * 1000 if denominator_words else 0.0
        for key, value in result.items()
        if key != "denominator_words" and isinstance(value, (int, float))
    }
    return result


def _section_id(path: Sequence[str]) -> str:
    return " / ".join(path)


def _opening_category(passage: PassageRecord, config: AnalysisConfig) -> str:
    text = passage.normalized_text.lstrip()
    if text[:1] in _OPENING_QUOTES:
        return "dialogue"
    tokens = _casefold_tokens(text)
    if not tokens:
        return "other"
    token = tokens[0]
    if token in {term.casefold() for term in config.lexicons.get("transition_markers", [])}:
        return "transition"
    if token in {term.casefold() for term in config.lexicons.get("first_person_pronouns", [])}:
        return "first_person_pronoun"
    if token in {term.casefold() for term in config.lexicons.get("third_person_pronouns", [])}:
        return "third_person_pronoun"
    if token in {term.casefold() for term in config.lexicons.get("demonstratives", [])}:
        return "demonstrative"
    if token in {term.casefold() for term in config.lexicons.get("function_words", [])}:
        return "function_word"
    return "other"


def _concentration(section_passages: Sequence[PassageRecord]) -> dict[str, Any]:
    tokens = [token.casefold() for passage in section_passages for token in tokenize(passage.normalized_text)]
    count = len(tokens)
    if not count:
        return {
            "section_id": _section_id(section_passages[0].heading_path),
            "heading_path": list(section_passages[0].heading_path),
            "token_count": 0,
            "window_width": 0,
            "window_count": 0,
            "window_values": [],
            "mean": None,
            "minimum": None,
            "median": None,
            "maximum": None,
        }
    width = max(1, math.ceil(math.sqrt(count)))
    windows = [tokens[index : index + width] for index in range(count - width + 1)]
    values: list[float] = []
    for window in windows:
        frequencies = Counter(window)
        values.append(sum((frequency / width) ** 2 for frequency in frequencies.values()))
    summary = _distribution(values)
    return {
        "section_id": _section_id(section_passages[0].heading_path),
        "heading_path": list(section_passages[0].heading_path),
        "token_count": count,
        "window_width": width,
        "window_count": len(windows),
        "window_values": values,
        "mean": summary["mean"],
        "minimum": summary["minimum"],
        "median": summary["median"],
        "maximum": summary["maximum"],
    }


def _flag(
    passage: PassageRecord,
    metric: str,
    value: int | float,
    reason: str,
    kind: str,
) -> dict[str, Any]:
    return MetricCandidateFlag.model_validate({
        "kind": kind,
        "metric": metric,
        "value": value,
        "reason": reason,
        "passage_id": passage.passage_id,
        "section_id": _section_id(passage.heading_path),
        "sampling_aid": True,
        "interpretive_finding": False,
    }).model_dump(mode="json")


def _extreme_flags(
    passages: Sequence[PassageRecord], values: dict[str, list[tuple[PassageRecord, int]]]
) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    for metric, entries in values.items():
        if not entries:
            continue
        numeric = [value for _, value in entries]
        minimum, maximum = min(numeric), max(numeric)
        for passage, value in entries:
            if value == minimum:
                flags.append(_flag(passage, metric, value, "within-witness minimum", "length_extreme"))
            if value == maximum:
                flags.append(_flag(passage, metric, value, "within-witness maximum", "length_extreme"))
    return flags


@dataclass(slots=True)
class WitnessMetrics:
    """Auditable measurements for one witness, with no pooled target."""

    witness_id: str
    source_id: str
    selection_id: str | None
    witness_ordinal: int
    total_words: int
    total_passages: int
    total_sentences: int
    total_sections: int
    sentence_lengths: list[int]
    paragraph_lengths: list[int]
    passage_lengths: list[int]
    sentence_length_distribution: dict[str, Any]
    paragraph_length_distribution: dict[str, Any]
    passage_length_distribution: dict[str, Any]
    dialogue_proportion: dict[str, Any]
    dialogue_run_lengths: list[int]
    punctuation_frequencies: dict[str, Any]
    lexicon_frequencies: dict[str, dict[str, int]]
    normalized_frequencies: dict[str, dict[str, Any]]
    function_word_frequencies: dict[str, int]
    function_word_sequence_frequencies: dict[str, int]
    paragraph_openings: dict[str, int]
    paragraph_transitions: dict[str, int]
    moving_window_lexical_concentration: dict[str, Any]
    block_proportions: dict[str, Any]
    section_level_variation: dict[str, Any]
    section_metrics: list[dict[str, Any]]
    candidate_flags: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "witness_id": self.witness_id,
            "source_id": self.source_id,
            "selection_id": self.selection_id,
            "witness_ordinal": self.witness_ordinal,
            "total_words": self.total_words,
            "total_passages": self.total_passages,
            "total_sentences": self.total_sentences,
            "total_sections": self.total_sections,
            "sentence_length_distribution": self.sentence_length_distribution,
            "paragraph_length_distribution": self.paragraph_length_distribution,
            "passage_length_distribution": self.passage_length_distribution,
            "dialogue_proportion": self.dialogue_proportion,
            "dialogue_run_lengths": self.dialogue_run_lengths,
            "punctuation_frequencies": self.punctuation_frequencies,
            "speech_attribution_verbs": self.lexicon_frequencies.get("speech_attribution_verbs", {}),
            "reporting_verbs": self.lexicon_frequencies.get("reporting_verbs", {}),
            "first_person_pronoun_frequencies": self.lexicon_frequencies.get("first_person_pronouns", {}),
            "third_person_pronoun_frequencies": self.lexicon_frequencies.get("third_person_pronouns", {}),
            "demonstrative_frequencies": self.lexicon_frequencies.get("demonstratives", {}),
            "modal_frequencies": self.lexicon_frequencies.get("modal_verbs", {}),
            "epistemic_frequencies": self.lexicon_frequencies.get("epistemic_markers", {}),
            "lexicon_frequencies": self.lexicon_frequencies,
            "normalized_frequencies": self.normalized_frequencies,
            "function_word_frequencies": self.function_word_frequencies,
            "function_word_sequence_frequencies": self.function_word_sequence_frequencies,
            "paragraph_openings": self.paragraph_openings,
            "paragraph_transitions": self.paragraph_transitions,
            "moving_window_lexical_concentration": self.moving_window_lexical_concentration,
            "block_proportions": self.block_proportions,
            "section_level_variation": self.section_level_variation,
            "section_metrics": self.section_metrics,
            "candidate_flags": self.candidate_flags,
        }


def measure_witness(passages: Sequence[PassageRecord], config: AnalysisConfig) -> WitnessMetrics:
    """Measure one witness in reading order using only the declared lexicons."""

    if not passages:
        raise CreativeWriterError("cannot measure an empty witness")
    records = list(passages)
    witness_ids = {record.witness_id for record in records}
    if len(witness_ids) != 1:
        raise CreativeWriterError("measure_witness requires passages from exactly one witness")
    records.sort(key=lambda record: record.source_ordinal)
    first = records[0]
    tokens_by_passage = [tokenize(record.normalized_text) for record in records]
    folded_by_passage = [[token.casefold() for token in tokens] for tokens in tokens_by_passage]
    total_words = sum(len(tokens) for tokens in tokens_by_passage)
    attribution_verbs = config.lexicons.get("speech_attribution_verbs", [])
    sentence_lengths: list[int] = []
    sentence_entries: list[tuple[PassageRecord, int]] = []
    paragraph_entries: list[tuple[PassageRecord, int]] = []
    passage_entries: list[tuple[PassageRecord, int]] = []
    for record, tokens in zip(records, tokens_by_passage):
        lengths = sentence_token_lengths(record.normalized_text, attribution_verbs)
        sentence_lengths.extend(lengths)
        sentence_entries.extend((record, value) for value in lengths)
        length = len(tokens)
        passage_entries.append((record, length))
        if record.block_type == "paragraph":
            paragraph_entries.append((record, length))

    dialogue_words = 0
    unknown_words = 0
    unknown_passages = 0
    active_runs: list[int] = []
    current_run = 0
    current_section: tuple[str, ...] | None = None
    for record, tokens in zip(records, tokens_by_passage):
        words, unknown = _dialogue_words(record, tokens)
        dialogue_words += words
        unknown_words += unknown
        if unknown:
            unknown_passages += 1
        active = (
            record.block_type == "paragraph"
            and record.direct_dialogue in {"direct", "mixed"}
        )
        if record.heading_path != list(current_section or ()):
            if current_run:
                active_runs.append(current_run)
            current_run = 0
            current_section = tuple(record.heading_path)
        if active:
            current_run += 1
        elif current_run:
            active_runs.append(current_run)
            current_run = 0
    if current_run:
        active_runs.append(current_run)

    lexicon_frequencies: dict[str, dict[str, int]] = {}
    normalized_frequencies: dict[str, dict[str, Any]] = {}
    for name, terms in config.lexicons.items():
        counts = {term.casefold(): 0 for term in terms}
        for passage_tokens in folded_by_passage:
            local = Counter(passage_tokens)
            for term in counts:
                counts[term] += local.get(term, 0)
        lexicon_frequencies[name] = counts
        normalized_frequencies[name] = {
            "counts": counts,
            "denominator_words": total_words,
            "per_1000_words": {
                term: (count / total_words * 1000 if total_words else 0.0)
                for term, count in counts.items()
            },
        }
    function_words = {term.casefold() for term in config.lexicons.get("function_words", [])}
    function_word_frequencies = {
        term: lexicon_frequencies.get("function_words", {}).get(term, 0)
        for term in sorted(function_words)
    }
    bigrams: Counter[str] = Counter()
    for folded_tokens in folded_by_passage:
        for left, right in zip(folded_tokens, folded_tokens[1:]):
            if left in function_words and right in function_words:
                bigrams[f"{left} {right}"] += 1

    paragraph_openings: Counter[str] = Counter()
    paragraphs_by_section: dict[tuple[str, ...], list[PassageRecord]] = defaultdict(list)
    for record in records:
        if record.block_type == "paragraph":
            paragraph_openings[_opening_category(record, config)] += 1
            paragraphs_by_section[tuple(record.heading_path)].append(record)
    paragraph_transitions: Counter[str] = Counter()
    for section_records in paragraphs_by_section.values():
        for left, right in zip(section_records, section_records[1:]):
            paragraph_transitions[
                f"{_opening_category(left, config)}->{_opening_category(right, config)}"
            ] += 1

    section_groups: dict[tuple[str, ...], list[PassageRecord]] = defaultdict(list)
    for record in records:
        section_groups[tuple(record.heading_path)].append(record)
    section_metrics: list[dict[str, Any]] = []
    concentration_sections: list[dict[str, Any]] = []
    section_scalar_values: dict[str, list[int]] = defaultdict(list)
    for heading_path, section_records in section_groups.items():
        section_tokens = [tokenize(record.normalized_text) for record in section_records]
        section_word_count = sum(len(item) for item in section_tokens)
        section_sentences = sum(
            len(sentence_token_lengths(record.normalized_text, attribution_verbs))
            for record in section_records
        )
        section_dialogue = sum(
            _dialogue_words(record, tokens)[0]
            for record, tokens in zip(section_records, section_tokens)
        )
        section_punctuation = _punctuation(section_records)
        row: dict[str, Any] = {
            "section_id": _section_id(heading_path),
            "heading_path": list(heading_path),
            "total_words": section_word_count,
            "total_passages": len(section_records),
            "total_sentences": section_sentences,
            "dialogue_words": section_dialogue,
            "question_marks": section_punctuation["question_marks"],
            "exclamation_marks": section_punctuation["exclamation_marks"],
            "colons": section_punctuation["colons"],
            "semicolons": section_punctuation["semicolons"],
            "parentheses_total": section_punctuation["parentheses_total"],
            "ellipsis_total": section_punctuation["ellipsis_total"],
            "dash_total": section_punctuation["dash_total"],
            "lexicon_frequencies": {
                name: {
                    term: sum(Counter(tokens)[term] for tokens in (
                        [token.casefold() for token in tokenize(record.normalized_text)]
                        for record in section_records
                    ))
                    for term in terms
                }
                for name, terms in config.lexicons.items()
            },
        }
        section_metrics.append(row)
        concentration_sections.append(_concentration(section_records))
        for key in (
            "total_words", "total_passages", "total_sentences", "dialogue_words",
            "question_marks", "exclamation_marks", "colons", "semicolons",
            "parentheses_total", "ellipsis_total", "dash_total",
        ):
            section_scalar_values[key].append(row[key])
        for name, counts in row["lexicon_frequencies"].items():
            for term, count in counts.items():
                section_scalar_values[f"{name}:{term}"].append(count)
    section_level_variation: dict[str, Any] = {}
    for key, values in section_scalar_values.items():
        section_level_variation[key] = {
            "minimum": min(values),
            "maximum": max(values),
            "range": max(values) - min(values),
            "count": len(values),
        }

    block_counts = {"dialogue": 0, "narrative": 0, "quotation": 0, "verse": 0, "list": 0}
    for record in records:
        if record.block_type == "block_quote":
            category = "quotation"
        elif record.block_type == "verse":
            category = "verse"
        elif record.block_type == "list_item":
            category = "list"
        elif record.direct_dialogue in {"direct", "mixed"}:
            category = "dialogue"
        else:
            category = "narrative"
        block_counts[category] += 1
    block_denominator = len(records)
    block_proportions = {
        "counts": block_counts,
        "denominator_passages": block_denominator,
        "proportions": {
            category: count / block_denominator if block_denominator else 0.0
            for category, count in block_counts.items()
        },
    }

    flags = _extreme_flags(
        records,
        {
            "sentence_length": sentence_entries,
            "paragraph_length": paragraph_entries,
            "passage_length": passage_entries,
        },
    )
    for name, counts in lexicon_frequencies.items():
        if name == "function_words":
            continue
        rates = [
            (
                record,
                sum(
                    1
                    for token in folded
                    if token in counts
                ) / len(folded),
            )
            for record, folded in zip(records, folded_by_passage)
            if folded
        ]
        if not rates:
            continue
        maximum = max(value for _, value in rates)
        if maximum <= 0:
            continue
        for record, value in rates:
            if value == maximum:
                flags.append(_flag(record, name, value, "within-witness maximum marker rate", "marker_cluster"))

    def add_density_flags(
        metric: str,
        values: Sequence[tuple[PassageRecord, float]],
        reason: str,
        kind: str = "marker_cluster",
    ) -> None:
        if not values:
            return
        maximum = max(value for _, value in values)
        if maximum <= 0:
            return
        for record, value in values:
            if value == maximum:
                flags.append(_flag(record, metric, value, reason, kind))

    marker_terms = {
        *(
            term.casefold()
            for term in config.lexicons.get("modal_verbs", [])
        ),
        *(
            term.casefold()
            for term in config.lexicons.get("epistemic_markers", [])
        ),
    }
    add_density_flags(
        "modality_qualification_density",
        [
            (record, sum(token in marker_terms for token in folded) / len(folded))
            for record, folded in zip(records, folded_by_passage)
            if folded
        ],
        "within-witness maximum declared modality/qualification rate",
    )
    add_density_flags(
        "dialogue_density",
        [
            (record, _dialogue_words(record, tokens)[0] / len(tokens))
            for record, tokens in zip(records, tokens_by_passage)
            if tokens
        ],
        "within-witness maximum observable dialogue rate",
        kind="dialogue_cluster",
    )
    add_density_flags(
        "question_exclamation_density",
        [
            (
                record,
                (record.normalized_text.count("?") + record.normalized_text.count("!"))
                / len(tokens),
            )
            for record, tokens in zip(records, tokens_by_passage)
            if tokens
        ],
        "within-witness maximum question/exclamation rate",
        kind="punctuation_cluster",
    )
    add_density_flags(
        "parenthesis_density",
        [
            (
                record,
                (record.normalized_text.count("(") + record.normalized_text.count(")"))
                / len(tokens),
            )
            for record, tokens in zip(records, tokens_by_passage)
            if tokens
        ],
        "within-witness maximum parenthesis rate",
        kind="punctuation_cluster",
    )

    punctuation = _punctuation(records)
    return WitnessMetrics(
        witness_id=first.witness_id,
        source_id=first.source_id,
        selection_id=first.selection_id,
        witness_ordinal=first.witness_ordinal,
        total_words=total_words,
        total_passages=len(records),
        total_sentences=len(sentence_lengths),
        total_sections=len(section_groups),
        sentence_lengths=sentence_lengths,
        paragraph_lengths=[value for _, value in paragraph_entries],
        passage_lengths=[value for _, value in passage_entries],
        sentence_length_distribution=_distribution(sentence_lengths),
        paragraph_length_distribution=_distribution([value for _, value in paragraph_entries]),
        passage_length_distribution=_distribution([value for _, value in passage_entries]),
        dialogue_proportion={
            "dialogue_words": dialogue_words,
            "denominator_words": total_words,
            "proportion": dialogue_words / total_words if total_words else 0.0,
            "unknown_words": unknown_words,
            "unknown_passages": unknown_passages,
        },
        dialogue_run_lengths=active_runs,
        punctuation_frequencies=punctuation,
        lexicon_frequencies=lexicon_frequencies,
        normalized_frequencies=normalized_frequencies,
        function_word_frequencies=function_word_frequencies,
        function_word_sequence_frequencies=dict(sorted(bigrams.items())),
        paragraph_openings=dict(sorted(paragraph_openings.items())),
        paragraph_transitions=dict(sorted(paragraph_transitions.items())),
        moving_window_lexical_concentration={
            "sections": concentration_sections,
            "window_width_rule": "max(1, ceil(sqrt(section_token_count)))",
        },
        block_proportions=block_proportions,
        section_level_variation=section_level_variation,
        section_metrics=section_metrics,
        candidate_flags=flags,
    )


def _stage_artifact(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise CreativeWriterError(f"Unable to stage metric artifact {path}: {exc}") from exc
    assert temporary is not None
    return temporary


def _cleanup_artifact_paths(paths: Sequence[Path]) -> list[str]:
    failures: list[str] = []
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            failures.append(f"{path}: {exc}")
    return failures


def _commit_metric_artifacts(staged: Sequence[tuple[Path, Path]]) -> None:
    backups: dict[Path, Path] = {}
    installed: list[Path] = []
    restored: set[Path] = set()
    transaction_id = uuid.uuid4().hex
    original_failure: OSError | None = None
    recovery_errors: list[str] = []

    try:
        for target, temporary in staged:
            if target.exists():
                backup = target.parent / f".{target.name}.{transaction_id}.bak"
                os.replace(target, backup)
                backups[target] = backup
            os.replace(temporary, target)
            installed.append(target)
    except OSError as exc:
        original_failure = exc
        recovery_errors.extend(
            _cleanup_artifact_paths([target for target in reversed(installed)])
        )
        for target, backup in backups.items():
            if backup.exists():
                try:
                    os.replace(backup, target)
                except OSError as restore_error:
                    recovery_errors.append(
                        f"restoration of backup `{backup}` to `{target}` failed: "
                        f"{restore_error}; residual path: `{backup}`"
                    )
                else:
                    restored.add(target)
    finally:
        recovery_errors.extend(
            _cleanup_artifact_paths([temporary for _, temporary in staged])
        )
        for target, backup in backups.items():
            if original_failure is not None and target not in restored:
                if backup.exists():
                    recovery_errors.append(
                        f"residual un-restored backup `{backup}` remains; "
                        f"residual path: `{backup}`"
                    )
                continue
            recovery_errors.extend(_cleanup_artifact_paths([backup]))

    if original_failure is not None:
        detail = f"Unable to replace metric artifacts atomically: {original_failure}"
        if recovery_errors:
            detail += "\nRecovery errors:\n" + "\n".join(recovery_errors)
        raise CreativeWriterError(detail) from original_failure
    if recovery_errors:
        raise CreativeWriterError(
            "Metric artifacts installed, but cleanup failed:\n" + "\n".join(recovery_errors)
        )


def _metric_rows(
    metrics: WitnessMetrics,
    config: AnalysisConfig,
    provenance: dict[str, str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    identity = {
        "witness_id": metrics.witness_id,
        "source_id": metrics.source_id,
        "selection_id": metrics.selection_id or "",
        **provenance,
    }

    def add(metric: str, submetric: str, value: Any, passage_id: str = "", section_id: str = "") -> None:
        rows.append({
            **identity,
            "section_id": section_id,
            "metric": metric,
            "submetric": submetric,
            "value": json.dumps(value, ensure_ascii=False, sort_keys=True),
            "passage_id": passage_id,
            "notes": "sampling aid" if metric == "candidate_flags" else "",
        })

    scalar_names = {"total_words", "total_passages", "total_sentences", "total_sections"}
    distribution_names = {
        "sentence_length_distribution",
        "paragraph_length_distribution",
        "passage_length_distribution",
    }
    lexicon_names = {
        "speech_attribution_verbs": "speech_attribution_verbs",
        "reporting_verbs": "reporting_verbs",
        "first_person_pronoun_frequencies": "first_person_pronouns",
        "third_person_pronoun_frequencies": "third_person_pronouns",
        "demonstrative_frequencies": "demonstratives",
        "modal_frequencies": "modal_verbs",
        "epistemic_frequencies": "epistemic_markers",
    }
    mapping_values = {
        "function_word_frequencies": metrics.function_word_frequencies,
        "function_word_sequence_frequencies": metrics.function_word_sequence_frequencies,
        "paragraph_openings": metrics.paragraph_openings,
        "paragraph_transitions": metrics.paragraph_transitions,
    }
    for public_name in config.enabled_measurements:
        if public_name == "word_count":
            add(public_name, "value", metrics.total_words)
        elif public_name in scalar_names:
            add(public_name, "value", getattr(metrics, public_name))
        elif public_name in distribution_names:
            add(public_name, "summary", getattr(metrics, public_name))
        elif public_name in {
            "dialogue_proportion",
            "punctuation_frequencies",
            "block_proportions",
            "section_level_variation",
        }:
            add(public_name, "summary", getattr(metrics, public_name))
        elif public_name == "dialogue_run_lengths":
            add(public_name, "values", metrics.dialogue_run_lengths)
        elif public_name in lexicon_names:
            values = metrics.lexicon_frequencies[lexicon_names[public_name]]
            if values:
                for term, count in values.items():
                    add(public_name, term, count)
            else:
                add(public_name, "values", {})
        elif public_name == "moving_window_lexical_concentration":
            sections = metrics.moving_window_lexical_concentration["sections"]
            if sections:
                for section in sections:
                    add(public_name, "summary", section, section_id=section["section_id"])
            else:
                add(public_name, "values", [])
        elif public_name in mapping_values:
            values = mapping_values[public_name]
            if values:
                for key, value in sorted(values.items()):
                    add(public_name, key, value)
            else:
                add(public_name, "values", {})
        else:
            raise CreativeWriterError(f"Unsupported public measurement mapping: {public_name}")
    return rows


def measure_development(
    passages: Sequence[PassageRecord],
    config: AnalysisConfig,
    development_passage_ids: set[str] | Sequence[str],
    *,
    output_paths: dict[str, Path] | None = None,
    config_sha256: str = "",
    index_sha256: str = "",
    manifest_sha256: str = "",
    config_path: str = "",
    index_path: str = "",
    manifest_path: str = "",
) -> list[WitnessMetrics]:
    """Measure only supplied development IDs and write auditable artifacts."""

    allowed = set(development_passage_ids)
    selected = [passage for passage in passages if passage.passage_id in allowed]
    if len(selected) != len(allowed):
        missing = sorted(allowed - {passage.passage_id for passage in selected})
        raise CreativeWriterError("Development passage IDs are unresolved: " + ", ".join(missing))
    if not selected:
        raise CreativeWriterError("Development partition contains no passages")
    by_witness: dict[str, list[PassageRecord]] = defaultdict(list)
    for passage in selected:
        by_witness[passage.witness_id].append(passage)
    metrics = [
        measure_witness(by_witness[witness_id], config)
        for witness_id in sorted(by_witness, key=lambda item: min(p.witness_ordinal for p in by_witness[item]))
    ]
    if output_paths is None:
        return metrics
    provenance = {
        "study_id": config.study_id,
        "stage": "development",
        "config_sha256": config_sha256,
        "index_sha256": index_sha256,
        "manifest_sha256": manifest_sha256,
        "config_path": config_path,
        "index_path": index_path,
        "manifest_path": manifest_path,
    }
    document = {
        "schema_version": 1,
        "stage": "development",
        "study_id": config.study_id,
        "config_sha256": config_sha256,
        "index_sha256": index_sha256,
        "manifest_sha256": manifest_sha256,
        "provenance": provenance,
        "enabled_measurements": list(config.enabled_measurements),
        "candidate_heuristics": {
            "observation_to_explanation_movement": {
                "status": "deferred",
                "reason": "Deferred to human close reading because it cannot be measured from declared lexicons without interpretation.",
            }
        },
        "witnesses": [metric.to_dict() for metric in metrics],
    }
    rows = [
        row
        for metric in metrics
        for row in _metric_rows(metric, config, provenance)
    ]
    metric_order = {name: index for index, name in enumerate(config.enabled_measurements)}
    rows.sort(
        key=lambda row: (
            next(metric.witness_ordinal for metric in metrics if metric.witness_id == row["witness_id"]),
            metric_order[row["metric"]],
            row["submetric"],
            row["passage_id"],
        )
    )
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "study_id", "stage", "config_sha256", "index_sha256", "manifest_sha256",
            "config_path", "index_path", "manifest_path",
            "witness_id", "source_id", "selection_id", "section_id", "metric",
            "submetric", "value", "passage_id", "notes",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)
    report_lines = [
        "# Phase 2B development metrics",
        "",
        "> This is a deterministic descriptive measurement surface. It contains no pooled Wells target and no interpretive findings.",
        "",
        "## Method and limitations",
        "",
        "Sentence counts use an explicit left-to-right Victorian approximation with title/initial protection, quote closers, lower-case speech attribution, ellipses, and final-fragment handling. Initials at sentence starts, lower-case prose after full stops, nested quotations, and editorially irregular punctuation remain possible misclassification cases.",
        "",
        "Tokens use NFC-normalized text and `[^\\W_]+(?:['’][^\\W_]+)*`; sequences reset at passage boundaries. Punctuation is counted by exact code point. Dialogue is quoted-span based for mixed passages, all-token based for direct passages, and unknown passages remain in the denominator with zero numerator.",
        "",
        f"Study ID: `{config.study_id}`  ",
        "Stage: `development`  ",
        f"Configuration SHA-256: `{config_sha256}`  ",
        f"Passage-index SHA-256: `{index_sha256}`  ",
        f"Holdout-manifest SHA-256: `{manifest_sha256}`",
        f"Configuration path: `{config_path}`  ",
        f"Passage-index path: `{index_path}`  ",
        f"Holdout-manifest path: `{manifest_path}`",
        "",
        "Observation-to-explanation movement is deferred to human close reading because it cannot be measured from declared lexicons without interpretation.",
        "",
    ]
    for metric in metrics:
        report_lines.extend([
            f"## Witness: `{metric.witness_id}`",
            "",
            f"Source: `{metric.source_id}`; development words: **{metric.total_words}**; passages: **{metric.total_passages}**; sentence approximation: **{metric.total_sentences}**; sections: **{metric.total_sections}**.",
            "",
            "Candidate flags below are within-witness sampling aids only; they are not findings.",
            "",
        ])
        for flag in metric.candidate_flags:
            report_lines.append(
                f"- `{flag['kind']}` `{flag['metric']}` = `{flag['value']}` at `{flag['passage_id']}` ({flag['reason']})."
            )
        if not metric.candidate_flags:
            report_lines.append("- No candidate sampling flags.")
        report_lines.append("")
    payloads = [
        (
            output_paths["development_metrics"],
            (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=False) + "\n").encode("utf-8"),
        ),
        (output_paths["development_metrics_csv"], output.getvalue().encode("utf-8")),
        (output_paths["development_report"], ("\n".join(report_lines) + "\n").encode("utf-8")),
    ]
    staged: list[tuple[Path, Path]] = []
    try:
        for path, payload in payloads:
            staged.append((path, _stage_artifact(path, payload)))
        _commit_metric_artifacts(staged)
    except CreativeWriterError:
        _cleanup_artifact_paths([temporary for _, temporary in staged])
        raise
    return metrics


__all__ = [
    "WitnessMetrics",
    "measure_development",
    "measure_witness",
    "sentence_spans",
    "sentence_token_lengths",
    "tokenize",
]
