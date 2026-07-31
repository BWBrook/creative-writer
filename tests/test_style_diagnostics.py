from __future__ import annotations

import math
import statistics

import pytest

from creative_writer.models import LintSettings
from creative_writer.prose_heuristics import (
    SurfaceHeuristicWarning,
    run_surface_heuristics,
)
from creative_writer.style_diagnostics import (
    LocatedSignal,
    TextLocation,
    analyse_manuscript,
)


def test_counts_expose_hand_checkable_median_p90_and_cv_inputs() -> None:
    result = analyse_manuscript(
        "One.\n\nTwo words. Three more words.\n\nOne two three four.\n",
        lexicons={},
        speech_attribution_verbs=["said"],
    )

    assert result.word_count == 10
    assert result.paragraph_count == 3
    assert result.sentence_count == 4
    assert result.sentence_lengths == [1, 2, 3, 4]
    assert result.paragraph_lengths == [1, 5, 4]
    assert statistics.median(result.sentence_lengths) == 2.5
    assert (
        result.sentence_lengths[2]
        + 0.7 * (result.sentence_lengths[3] - result.sentence_lengths[2])
    ) == pytest.approx(3.7)
    assert result.sentence_length_cv == pytest.approx(1 / math.sqrt(5))
    assert result.punctuation_counts["periods_raw"] == 4
    assert result.punctuation_counts["periods"] == 4


def test_coefficient_of_variation_requires_two_nonempty_sentences() -> None:
    result = analyse_manuscript(
        "Only one sentence.",
        lexicons={},
        speech_attribution_verbs=["said"],
    )

    assert result.sentence_lengths == [3]
    assert result.sentence_length_cv is None


def test_dialogue_proportion_counts_matched_straight_and_curly_quotes() -> None:
    result = analyse_manuscript(
        '"Come now," he said.\n\n“Wait here,” she replied.\n\nNo speech here.\n',
        lexicons={},
        speech_attribution_verbs=["said", "replied"],
    )

    assert result.word_count == 11
    assert result.dialogue_word_proportion == pytest.approx(4 / 11)
    assert result.punctuation_counts["straight_double_quote"] == 2
    assert result.punctuation_counts["double_quote_open"] == 1
    assert result.punctuation_counts["double_quote_close"] == 1


def test_markup_exclusions_preserve_lexicon_source_lines() -> None:
    text = """# Heading with perhaps
<!--
perhaps hidden
-->
Plain words.
```python
print("perhaps")
```
![Perhaps](image.png)
Apparently this remains.
Perhaps this remains too.
"""

    result = analyse_manuscript(
        text,
        lexicons={"epistemic": ["perhaps", "apparently"]},
        speech_attribution_verbs=["said"],
    )

    assert result.word_count == 9
    assert result.paragraph_count == 2
    assert result.sentence_count == 3
    assert result.punctuation_counts["periods"] == 3
    assert result.punctuation_counts["straight_double_quote"] == 0
    assert result.lexicon_hits == {
        "epistemic": [
            LocatedSignal(TextLocation(10, 10), "Apparently"),
            LocatedSignal(TextLocation(11, 11), "Perhaps"),
        ]
    }


def test_commonmark_heading_and_image_variants_preserve_surrounding_prose() -> None:
    text = """Before remains.

Setext heading
continues here
-------------

![Reference hidden][plate]

![Balanced hidden](images/plate_(draft).png)

After remains.

[plate]: images/plate.png
"""

    result = analyse_manuscript(
        text,
        lexicons={
            "retained": ["before", "after"],
            "excluded": ["setext", "continues", "reference", "balanced"],
        },
        speech_attribution_verbs=["said"],
    )

    assert result.word_count == 4
    assert result.paragraph_count == 2
    assert result.sentence_count == 2
    assert result.paragraph_lengths == [2, 2]
    assert result.punctuation_counts["periods"] == 2
    assert result.lexicon_hits == {
        "retained": [
            LocatedSignal(TextLocation(1, 1), "Before"),
            LocatedSignal(TextLocation(11, 11), "After"),
        ],
        "excluded": [],
    }


def test_lexicon_matching_uses_unicode_nfc_and_casefolding() -> None:
    result = analyse_manuscript(
        "CAFE\u0301 evidence remained.\n",
        lexicons={"epistemic": ["café evidence"]},
        speech_attribution_verbs=["said"],
    )

    assert result.lexicon_hits["epistemic"] == [
        LocatedSignal(TextLocation(1, 1), "CAFÉ evidence")
    ]


def test_lexicon_terms_are_deduplicated_after_token_normalization() -> None:
    result = analyse_manuscript(
        "CAFÉ evidence remained.\n",
        lexicons={
            "epistemic": [
                "café evidence",
                "CAFE\u0301 EVIDENCE!",
                "café",
                "CAFÉ",
            ]
        },
        speech_attribution_verbs=["said"],
    )

    assert result.lexicon_hits["epistemic"] == [
        LocatedSignal(TextLocation(1, 1), "CAFÉ evidence"),
        LocatedSignal(TextLocation(1, 1), "CAFÉ"),
    ]


def test_repeated_ngram_reports_first_and_last_lines() -> None:
    text = (
        "The lamp went out.\n\n"
        "THE LAMP WENT out again.\n\n"
        "The lamp went out at dawn.\n"
    )
    result = analyse_manuscript(
        text,
        lexicons={},
        speech_attribution_verbs=["said"],
        repeated_ngram_size=3,
        repeated_ngram_minimum=3,
    )

    assert result.repeated_ngrams[0] == LocatedSignal(
        TextLocation(1, 5),
        "the lamp went (3 occurrences)",
    )


def test_repeated_ngram_ignores_sequences_made_only_of_stop_words() -> None:
    result = analyse_manuscript(
        "In the end.\n\nIN THE END.\n\nin the end.\n",
        lexicons={},
        speech_attribution_verbs=["said"],
        stop_words=["in", "the", "end"],
    )

    assert result.repeated_ngrams == []


def test_repeated_opening_reports_first_and_last_paragraph_lines() -> None:
    result = analyse_manuscript(
        "In that hour we entered.\n\n"
        "In that hour we stopped.\n\n"
        "In that hour we listened.\n",
        lexicons={},
        speech_attribution_verbs=["said"],
        opening_prefix_words=3,
        opening_minimum=3,
    )

    assert result.repeated_openings == [
        LocatedSignal(
            TextLocation(1, 5),
            "in that hour (3 paragraph openings)",
        )
    ]


def test_surface_heuristics_report_exact_thresholds_and_locations() -> None:
    lint = LintSettings.model_validate(
        {
            "em_dash": {"enabled": True, "max_per_chapter": 1},
            "contrastive_parallelism": {
                "enabled": True,
                "max_instances_per_chapter": 1,
            },
        }
    )
    text = (
        "One — here.\n"
        "Another — there.\n"
        "It was not only calm but also cold.\n"
        "It was not dark but dim.\n"
    )

    assert run_surface_heuristics(text, lint) == [
        SurfaceHeuristicWarning(
            rule_id="em-dash-overuse",
            observed="Em dash count 2 exceeds configured limit 1.",
            line_start=1,
            line_end=2,
        ),
        SurfaceHeuristicWarning(
            rule_id="contrastive-parallelism",
            observed=(
                "Contrastive parallelism count 2 exceeds configured limit 1."
            ),
            line_start=3,
            line_end=4,
        ),
    ]

    at_threshold = LintSettings.model_validate(
        {
            "em_dash": {"enabled": True, "max_per_chapter": 2},
            "contrastive_parallelism": {
                "enabled": True,
                "max_instances_per_chapter": 2,
            },
        }
    )
    assert run_surface_heuristics(text, at_threshold) == []
