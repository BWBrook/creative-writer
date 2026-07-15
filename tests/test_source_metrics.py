from __future__ import annotations

import hashlib
import re
from pathlib import Path

from creative_writer.files import load_yaml_model
from creative_writer.source_analysis_models import AnalysisConfig, PassageRecord
from creative_writer.source_metrics import measure_witness


HASH = "a" * 64


def _config() -> AnalysisConfig:
    return load_yaml_model(
        Path("stories/time-expedition/source-study/analysis.yml"), AnalysisConfig
    )


def _passage(
    text: str,
    ordinal: int,
    *,
    heading: str = "I",
    block_type: str = "paragraph",
    dialogue: str = "none",
    witness_id: str = "fixture-a",
    witness_ordinal: int = 1,
    source_id: str | None = None,
) -> PassageRecord:
    source_id = source_id or witness_id
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return PassageRecord(
        witness_id=witness_id,
        witness_ordinal=witness_ordinal,
        source_id=source_id,
        selection_id=None,
        source_fingerprint=HASH,
        heading_path=[heading],
        heading_label=heading,
        block_type=block_type,
        source_ordinal=ordinal,
        heading_ordinal=ordinal,
        normalized_text=text,
        original_text=text,
        word_count=len(re.findall(r"\S+", text)),
        direct_dialogue=dialogue,
        content_hash=digest,
        passage_id=f"{witness_id}:{heading.lower()}:{ordinal}:{digest[:12]}",
    )


def test_victorian_fixture_counts_sentences_dialogue_punctuation_and_lexicons() -> None:
    passages = [
        _passage(
            'Mr. Wells said, “Wait... now.” Dr. H. G. Wells replied, “No!”',
            1,
            dialogue="mixed",
        ),
        _passage('“Go,” she said. “Yes.”', 2, dialogue="mixed"),
        _passage("I could see this; perhaps that was so.", 3),
    ]

    result = measure_witness(passages, _config())

    assert result.total_words == 23
    assert result.total_passages == 3
    assert result.total_sentences == 5
    assert result.total_sections == 1
    assert result.sentence_lengths == [5, 6, 3, 1, 8]
    assert result.paragraph_lengths == [11, 4, 8]
    assert result.dialogue_proportion["dialogue_words"] == 5
    assert result.dialogue_proportion["denominator_words"] == 23
    assert result.dialogue_run_lengths == [2]
    assert result.lexicon_frequencies["reporting_verbs"]["said"] == 2
    assert result.lexicon_frequencies["speech_attribution_verbs"]["replied"] == 1
    assert result.lexicon_frequencies["first_person_pronouns"]["i"] == 1
    assert result.lexicon_frequencies["third_person_pronouns"]["she"] == 1
    assert result.lexicon_frequencies["demonstratives"]["this"] == 1
    assert result.lexicon_frequencies["demonstratives"]["that"] == 1
    assert result.lexicon_frequencies["epistemic_markers"]["perhaps"] == 1
    assert result.paragraph_openings == {
        "other": 1,
        "dialogue": 1,
        "first_person_pronoun": 1,
    }
    assert result.paragraph_transitions == {
        "other->dialogue": 1,
        "dialogue->first_person_pronoun": 1,
    }
    assert result.punctuation_frequencies["periods_raw"] == 11
    assert result.punctuation_frequencies["periods"] == 8
    assert result.punctuation_frequencies["ellipsis_ascii"] == 1
    assert result.punctuation_frequencies["question_marks"] == 0
    assert result.punctuation_frequencies["exclamation_marks"] == 1
    assert result.punctuation_frequencies["semicolons"] == 1
    assert result.punctuation_frequencies["double_quote_open"] == 4
    assert result.punctuation_frequencies["double_quote_close"] == 4


def test_punctuation_variants_and_internal_ellipsis_are_exact_code_points() -> None:
    result = measure_witness(
        [_passage("Dash—one – two - three… end; (yes)!", 1)], _config()
    )

    assert result.total_words == 6
    assert result.total_sentences == 1
    assert result.punctuation_frequencies["em_dash"] == 1
    assert result.punctuation_frequencies["en_dash"] == 1
    assert result.punctuation_frequencies["hyphen"] == 1
    assert result.punctuation_frequencies["ellipsis_unicode"] == 1
    assert result.punctuation_frequencies["ellipsis_ascii"] == 0
    assert result.punctuation_frequencies["semicolons"] == 1
    assert result.punctuation_frequencies["parentheses_open"] == 1
    assert result.punctuation_frequencies["parentheses_close"] == 1
    assert result.punctuation_frequencies["exclamation_marks"] == 1


def test_declared_lexicons_and_function_word_bigrams_are_exact_casefolded_tokens() -> None:
    result = measure_witness(
        [_passage("I could see this and that, but if I would ask her in the room perhaps.", 1)],
        _config(),
    )

    assert result.total_words == 16
    assert result.lexicon_frequencies["first_person_pronouns"]["i"] == 2
    assert result.lexicon_frequencies["third_person_pronouns"]["her"] == 1
    assert result.lexicon_frequencies["demonstratives"]["this"] == 1
    assert result.lexicon_frequencies["demonstratives"]["that"] == 1
    assert result.lexicon_frequencies["modal_verbs"]["could"] == 1
    assert result.lexicon_frequencies["modal_verbs"]["would"] == 1
    assert result.lexicon_frequencies["epistemic_markers"]["perhaps"] == 1
    assert result.lexicon_frequencies["reporting_verbs"].get("ask", 0) == 0
    assert result.function_word_frequencies["and"] == 1
    assert result.function_word_frequencies["but"] == 1
    assert result.function_word_frequencies["if"] == 1
    assert result.function_word_frequencies["in"] == 1
    assert result.function_word_frequencies["the"] == 1
    assert result.function_word_sequence_frequencies == {"but if": 1, "in the": 1}


def test_distributions_use_linear_interpolation_and_section_variation_is_explicit() -> None:
    passages = [_passage("One.", 1), _passage("Two words here.", 2, heading="II")]
    result = measure_witness(passages, _config())

    assert result.paragraph_length_distribution == {
        "count": 2,
        "minimum": 1,
            "p10": 1.2,
            "p25": 1.5,
            "median": 2,
                "p75": 2.5,
                "p90": 2.8,
            "maximum": 3,
            "mean": 2,
    }
    assert result.sentence_length_distribution["count"] == 2
    assert result.section_level_variation["total_words"] == {
        "minimum": 1,
        "maximum": 3,
        "range": 2,
        "count": 2,
    }


def test_block_proportions_runs_concentration_and_candidate_flags_are_auditable() -> None:
    passages = [
        _passage('“Run.”', 1, dialogue="direct"),
        _passage("Rain fell.", 2),
        _passage("A quoted block.", 3, block_type="block_quote"),
        _passage("One line", 4, block_type="verse"),
        _passage("two words", 5, block_type="list_item"),
    ]
    result = measure_witness(passages, _config())

    assert result.block_proportions["counts"] == {
        "dialogue": 1,
        "narrative": 1,
        "quotation": 1,
        "verse": 1,
        "list": 1,
    }
    assert result.block_proportions["proportions"]["dialogue"] == 0.2
    assert result.dialogue_proportion["dialogue_words"] == 1
    assert result.dialogue_run_lengths == [1]
    concentration = measure_witness([_passage("red red blue green.", 1)], _config())
    assert concentration.moving_window_lexical_concentration["sections"][0]["window_width"] == 2
    assert result.candidate_flags
    assert all("passage_id" in flag for flag in result.candidate_flags)
    assert all(flag["sampling_aid"] is True for flag in result.candidate_flags)


def test_direct_passages_count_all_tokens_and_sequences_reset_at_boundaries() -> None:
    result = measure_witness(
        [
            _passage('“Run.” said he.', 1, dialogue="direct"),
            _passage("the river.", 2),
        ],
        _config(),
    )

    assert result.dialogue_proportion["dialogue_words"] == 3
    assert result.function_word_sequence_frequencies == {}


def test_two_witness_measurements_keep_section_variation_local() -> None:
    a = measure_witness(
        [
            _passage("One.", 1, heading="I", witness_id="fixture-a", witness_ordinal=1),
            _passage("Two.", 2, heading="I", witness_id="fixture-a", witness_ordinal=1),
            _passage("Three.", 3, heading="II", witness_id="fixture-a", witness_ordinal=1),
        ],
        _config(),
    )
    b = measure_witness(
        [_passage("Four words here.", 1, witness_id="fixture-b", witness_ordinal=2)],
        _config(),
    )

    assert (a.total_words, a.total_passages, a.total_sections) == (3, 3, 2)
    assert (b.total_words, b.total_passages, b.total_sections) == (3, 1, 1)
    assert a.section_level_variation["total_words"]["range"] == 1
    assert b.section_level_variation["total_words"]["range"] == 0
