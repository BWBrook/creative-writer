from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

import pytest

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import load_yaml_model
from creative_writer.source_analysis_models import AnalysisConfig, PassageRecord
from creative_writer.source_metrics import measure_development, measure_witness, sentence_token_lengths


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


def test_nonquoted_lowercase_continuation_with_later_said_starts_a_new_sentence() -> None:
    assert sentence_token_lengths(
        "The rain stopped. and later he said hello.",
        _config().lexicons["speech_attribution_verbs"],
    ) == [3, 5]


def test_invalid_mixed_quotes_are_unknown_and_contribute_no_dialogue_words() -> None:
    for text in (
        "Narration “unclosed words.",
        "Narration “mismatched words’.",
        "Narration “quoted words” and stray close”.",
    ):
        result = measure_witness([_passage(text, 1, dialogue="mixed")], _config())
        assert result.dialogue_proportion["dialogue_words"] == 0
        assert result.dialogue_proportion["unknown_words"] == result.total_words
        assert result.dialogue_proportion["unknown_passages"] == 1


def test_supported_nested_quotes_remain_measureable_dialogue() -> None:
    result = measure_witness(
        [_passage('Narration “outer "inner" words”.', 1, dialogue="mixed")],
        _config(),
    )

    assert result.dialogue_proportion["dialogue_words"] == 3
    assert result.dialogue_proportion["unknown_words"] == 0


def test_punctuation_events_reset_at_passage_boundaries_and_report_rates() -> None:
    result = measure_witness(
        [_passage("Wait..", 1), _passage(". Next.", 2)],
        _config(),
    )

    punctuation = result.punctuation_frequencies
    assert punctuation["periods_raw"] == 4
    assert punctuation["periods"] == 4
    assert punctuation["ellipsis_ascii"] == 0
    assert punctuation["denominator_words"] == 2
    assert punctuation["per_1000_words"] == {
        "periods_raw": 2000.0,
        "periods": 2000.0,
        "question_marks": 0.0,
        "exclamation_marks": 0.0,
        "colons": 0.0,
        "semicolons": 0.0,
        "parentheses_open": 0.0,
        "parentheses_close": 0.0,
        "hyphen": 0.0,
        "en_dash": 0.0,
        "em_dash": 0.0,
        "ellipsis_unicode": 0.0,
        "ellipsis_ascii": 0.0,
        "double_quote_open": 0.0,
        "double_quote_close": 0.0,
        "single_quote_open": 0.0,
        "single_quote_close": 0.0,
        "straight_double_quote": 0.0,
        "straight_single_quote": 0.0,
        "guillemet_open": 0.0,
        "guillemet_close": 0.0,
        "parentheses_total": 0.0,
        "dash_total": 0.0,
        "ellipsis_total": 0.0,
    }
    assert "denominator_words" not in punctuation["per_1000_words"]
    assert result.total_sentences == 3


def test_candidate_flags_cover_declared_density_clusters_and_defer_interpretation() -> None:
    result = measure_witness(
        [
            _passage('“Could perhaps?” said he!', 1, dialogue="mixed"),
            _passage("Could perhaps? (Maybe)!", 2),
        ],
        _config(),
    )

    flag_metrics = {flag["metric"] for flag in result.candidate_flags}
    assert "modality_qualification_density" in flag_metrics
    assert "dialogue_density" in flag_metrics
    assert "question_exclamation_density" in flag_metrics
    assert "parenthesis_density" in flag_metrics
    assert all(flag["sampling_aid"] is True for flag in result.candidate_flags)
    assert all(flag["interpretive_finding"] is False for flag in result.candidate_flags)


def test_csv_maps_every_public_measurement_with_provenance_and_empty_rows(tmp_path: Path) -> None:
    config = _config()
    output_paths = {
        "development_metrics": tmp_path / "development-metrics.json",
        "development_metrics_csv": tmp_path / "development-metrics.csv",
        "development_report": tmp_path / "development-report.md",
    }
    passage = _passage("Plain narrative.", 1)
    measure_development(
        [passage],
        config,
        {passage.passage_id},
        output_paths=output_paths,
        config_sha256="config-hash",
        index_sha256="index-hash",
        manifest_sha256="manifest-hash",
        config_path="source-study/analysis.yml",
        index_path="build/fixture/source-study/passage-index.jsonl",
        manifest_path="source-study/holdouts.yml",
    )

    rows = list(csv.DictReader(output_paths["development_metrics_csv"].open(encoding="utf-8")))
    assert {row["metric"] for row in rows} == set(config.enabled_measurements)
    assert all(row["study_id"] == config.study_id for row in rows)
    assert all(row["stage"] == "development" for row in rows)
    assert all(row["config_sha256"] == "config-hash" for row in rows)
    assert all(row["index_sha256"] == "index-hash" for row in rows)
    assert all(row["manifest_sha256"] == "manifest-hash" for row in rows)
    assert all(row["config_path"] == "source-study/analysis.yml" for row in rows)
    assert all(row["index_path"] == "build/fixture/source-study/passage-index.jsonl" for row in rows)
    assert all(row["manifest_path"] == "source-study/holdouts.yml" for row in rows)
    assert any(
        row["metric"] == "function_word_sequence_frequencies"
        and json.loads(row["value"]) == {}
        for row in rows
    )
    assert any(
        row["metric"] == "paragraph_transitions" and json.loads(row["value"]) == {}
        for row in rows
    )

    document = json.loads(output_paths["development_metrics"].read_text(encoding="utf-8"))
    assert document["provenance"] == {
        "study_id": config.study_id,
        "stage": "development",
        "config_sha256": "config-hash",
        "index_sha256": "index-hash",
        "manifest_sha256": "manifest-hash",
        "config_path": "source-study/analysis.yml",
        "index_path": "build/fixture/source-study/passage-index.jsonl",
        "manifest_path": "source-study/holdouts.yml",
    }
    report = output_paths["development_report"].read_text(encoding="utf-8")
    assert f"Study ID: `{config.study_id}`" in report
    assert "Stage: `development`" in report
    assert "observation-to-explanation movement" in report.lower()
    assert "deferred to human close reading" in report.lower()


def test_metric_artifacts_roll_back_together_on_third_install_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config()
    output_paths = {
        "development_metrics": tmp_path / "development-metrics.json",
        "development_metrics_csv": tmp_path / "development-metrics.csv",
        "development_report": tmp_path / "development-report.md",
    }
    passage = _passage("Plain narrative.", 1)
    kwargs = {
        "output_paths": output_paths,
        "config_sha256": "config-hash",
        "index_sha256": "index-hash",
        "manifest_sha256": "manifest-hash",
        "config_path": "source-study/analysis.yml",
        "index_path": "build/fixture/source-study/passage-index.jsonl",
        "manifest_path": "source-study/holdouts.yml",
    }
    measure_development([passage], config, {passage.passage_id}, **kwargs)
    before = {path: path.read_bytes() for path in output_paths.values()}

    import creative_writer.source_metrics as source_metrics

    real_replace = source_metrics.os.replace
    failed = False

    def fail_report_install(source: str | Path, target: str | Path) -> None:
        nonlocal failed
        if Path(target).name == "development-report.md" and not failed:
            failed = True
            raise OSError("forced third-install failure")
        real_replace(source, target)

    monkeypatch.setattr(source_metrics.os, "replace", fail_report_install)
    changed_kwargs = {**kwargs, "config_sha256": "new-config-hash"}
    with pytest.raises(Exception, match="third-install failure"):
        measure_development([passage], config, {passage.passage_id}, **changed_kwargs)

    assert {path: path.read_bytes() for path in output_paths.values()} == before
    assert not list(tmp_path.glob(".*.tmp"))
    assert not list(tmp_path.glob(".*.bak"))


def test_metric_rollback_keeps_backup_when_restoration_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config()
    output_paths = {
        "development_metrics": tmp_path / "development-metrics.json",
        "development_metrics_csv": tmp_path / "development-metrics.csv",
        "development_report": tmp_path / "development-report.md",
    }
    passage = _passage("Plain narrative.", 1)
    kwargs = {
        "output_paths": output_paths,
        "config_sha256": "config-hash",
        "index_sha256": "index-hash",
        "manifest_sha256": "manifest-hash",
        "config_path": "source-study/analysis.yml",
        "index_path": "build/fixture/source-study/passage-index.jsonl",
        "manifest_path": "source-study/holdouts.yml",
    }
    measure_development([passage], config, {passage.passage_id}, **kwargs)
    before = {path: path.read_bytes() for path in output_paths.values()}

    import creative_writer.source_metrics as source_metrics

    real_replace = source_metrics.os.replace
    restore_failed = False

    def fail_install_and_restore(source: str | Path, target: str | Path) -> None:
        nonlocal restore_failed
        source_path = Path(source)
        target_path = Path(target)
        if (
            target_path == output_paths["development_report"]
            and source_path.name.endswith(".tmp")
        ):
            raise OSError("forced third-install failure")
        if (
            target_path == output_paths["development_metrics"]
            and source_path.name.startswith(".development-metrics.json.")
            and source_path.name.endswith(".bak")
            and not restore_failed
        ):
            restore_failed = True
            raise OSError("forced restoration failure")
        real_replace(source, target)

    monkeypatch.setattr(source_metrics.os, "replace", fail_install_and_restore)
    changed_kwargs = {**kwargs, "config_sha256": "new-config-hash"}
    with pytest.raises(CreativeWriterError) as caught:
        measure_development([passage], config, {passage.passage_id}, **changed_kwargs)

    residual_backups = list(tmp_path.glob(".development-metrics.json.*.bak"))
    assert len(residual_backups) == 1
    residual_backup = residual_backups[0]
    message = str(caught.value)
    assert "forced third-install failure" in message
    assert "forced restoration failure" in message
    assert str(residual_backup) in message
    assert not output_paths["development_metrics"].exists()
    assert output_paths["development_metrics_csv"].read_bytes() == before[
        output_paths["development_metrics_csv"]
    ]
    assert output_paths["development_report"].read_bytes() == before[
        output_paths["development_report"]
    ]
    assert not list(tmp_path.glob(".*.tmp"))
    assert not list(tmp_path.glob(".development-metrics.csv.*.bak"))
    assert not list(tmp_path.glob(".development-report.md.*.bak"))
