from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
from pathlib import Path

import pytest

from creative_writer.exceptions import CreativeWriterError
from creative_writer.source_analysis_models import WitnessDescriptor
from creative_writer.source_passages import (
    context_window,
    parse_markdown_witness,
    partition_windows,
    read_passage_index,
    write_passage_index,
)


FINGERPRINT = "a" * 64


def _witness(witness_id: str = "the-time-machine", witness_ordinal: int = 1) -> WitnessDescriptor:
    if "/" in witness_id:
        source_id, selection_id = witness_id.split("/", 1)
    else:
        source_id, selection_id = witness_id, None
    return WitnessDescriptor(
        witness_id=witness_id,
        witness_ordinal=witness_ordinal,
        source_id=source_id,
        selection_id=selection_id,
        source_fingerprint=FINGERPRINT,
    )


def _stub_pandoc(monkeypatch: pytest.MonkeyPatch, payload: object, *, stderr: str = "", code: int = 0) -> None:
    def run(*args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            returncode=code,
            stdout=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            stderr=stderr.encode("utf-8"),
        )

    monkeypatch.setattr("creative_writer.source_passages.subprocess.run", run)


def _text(value: str) -> list[dict[str, object]]:
    return [{"t": "Str", "c": value}]


def _fixture_ast() -> dict[str, object]:
    nested_list = {
        "t": "BulletList",
        "c": [[{"t": "Plain", "c": _text("nested child")}]],
    }
    return {
        "pandoc-api-version": [1, 23, 1, 2],
        "meta": {},
        "blocks": [
            {"t": "Image", "c": [["", [], []], _text("cover"), ["cover.png", ""]]},
            {"t": "Para", "c": _text("Prelude")},
            {"t": "Header", "c": [1, ["top", [], []], _text("Top")]},
            {
                "t": "Para",
                "c": [
                    {"t": "Str", "c": "“Hello,”"},
                    {"t": "Space"},
                    {"t": "Emph", "c": _text("said")},
                    {"t": "Space"},
                    {"t": "Str", "c": "the"},
                    {"t": "Space"},
                    {"t": "Quoted", "c": [{"t": "DoubleQuote"}, _text("Traveller")]},
                    {"t": "Space"},
                    {
                        "t": "Note",
                        "c": [{"t": "Para", "c": _text("a note")}],
                    },
                ],
            },
            {"t": "Para", "c": [{"t": "Space"}]},
            {
                "t": "BlockQuote",
                "c": [
                    {
                        "t": "Para",
                        "c": [
                            {"t": "Str", "c": "“First line"},
                            {"t": "LineBreak"},
                            {"t": "Str", "c": "second line.”"},
                        ],
                    }
                ],
            },
            {
                "t": "LineBlock",
                "c": [_text("verse one"), _text("verse two")],
            },
            {"t": "Header", "c": [3, ["deep", [], []], _text("Deep") ]},
            {
                "t": "OrderedList",
                "c": [
                    ["1", "DefaultStyle", "1"],
                    [
                        [{"t": "Plain", "c": _text("parent")}, nested_list],
                        [{"t": "Plain", "c": _text("second") }],
                    ],
                ],
            },
            {"t": "HorizontalRule"},
            {"t": "CodeBlock", "c": [["", [], []], "not a passage"]},
            {"t": "RawBlock", "c": ["html", "<p>not a passage</p>"]},
            {"t": "Table", "c": []},
        ],
    }


def test_synthetic_ast_extracts_passages_and_heading_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    markdown = tmp_path / "fixture.md"
    markdown.write_text("ignored by fake Pandoc", encoding="utf-8")
    _stub_pandoc(monkeypatch, _fixture_ast())
    passages = parse_markdown_witness(markdown, _witness("selected-short-fiction/the-star"))

    assert [passage.original_text for passage in passages] == [
        "Prelude",
        '“Hello,” said the "Traveller" a note',
        "“First line\nsecond line.”",
        "verse one\nverse two",
        "parent",
        "nested child",
        "second",
    ]
    assert [passage.block_type for passage in passages] == [
        "paragraph",
        "paragraph",
        "block_quote",
        "verse",
        "list_item",
        "list_item",
        "list_item",
    ]
    assert passages[0].heading_path == ["Untitled"]
    assert passages[0].heading_label == "Untitled"
    assert passages[1].heading_path == ["Top"]
    assert passages[2].heading_path == ["Top"]
    assert passages[3].heading_path == ["Top"]
    assert passages[4].heading_path == ["Top", "Deep"]
    assert passages[4].heading_ordinal == 1
    assert passages[5].heading_ordinal == 2
    assert passages[6].heading_ordinal == 3
    assert [passage.source_ordinal for passage in passages] == list(range(1, 8))
    assert passages[0].passage_id.startswith(
        "selected-short-fiction/the-star:untitled:1:"
    )
    assert passages[1].direct_dialogue == "direct"
    assert passages[2].direct_dialogue == "direct"
    assert passages[3].direct_dialogue == "none"
    assert passages[1].word_count == 6


def test_real_pandoc_preserves_unicode_and_normalizes_analysis_text(tmp_path: Path) -> None:
    markdown = tmp_path / "unicode.md"
    markdown.write_text(
        "# Chapter\n\n"
        "“It’s naïve\ufeff—really.”\u00a0Word\u200a\ufeff—marking.  \n"
        "A second line.\n",
        encoding="utf-8",
    )

    passages = parse_markdown_witness(markdown, _witness())

    assert len(passages) == 1
    assert passages[0].original_text == "“It’s naïve\ufeff—really.”\u00a0Word\u200a\ufeff—marking.\nA second line."
    assert passages[0].normalized_text == "“It’s naïve—really.” Word —marking.\nA second line."
    assert passages[0].content_hash == hashlib.sha256(
        passages[0].normalized_text.encode("utf-8")
    ).hexdigest()
    assert passages[0].direct_dialogue == "direct"


def test_real_pandoc_handles_malformed_heading_jumps_and_empty_blocks(tmp_path: Path) -> None:
    markdown = tmp_path / "headings.md"
    markdown.write_text(
        "![](image.png)\n\n"
        "\n\n"
        "# Root\n\n"
        "Root text.\n\n"
        "#### Jump\n\n"
        "Jump text.\n\n"
        "---\n\n"
        "\n\n"
        "##### Nested\n\n"
        "Nested text.\n",
        encoding="utf-8",
    )

    passages = parse_markdown_witness(markdown, _witness())

    assert [passage.source_ordinal for passage in passages] == [1, 2, 3]
    assert [passage.heading_path for passage in passages] == [
        ["Root"],
        ["Root", "Jump"],
        ["Root", "Jump", "Nested"],
    ]
    assert [passage.heading_ordinal for passage in passages] == [1, 1, 1]
    assert all(passage.block_type == "paragraph" for passage in passages)


def test_real_pandoc_heading_stack_discards_stale_siblings_by_level(tmp_path: Path) -> None:
    markdown = tmp_path / "heading-stack.md"
    markdown.write_text(
        "# A\n\nA text.\n\n"
        "#### H4 A\n\nH4 A text.\n\n"
        "#### H4 B\n\nH4 B text.\n\n"
        "### H3\n\nH3 text.\n\n"
        "##### H5 A\n\nH5 A text.\n\n"
        "##### H5 B\n\nH5 B text.\n\n"
        "### H3 again\n\nH3 again text.\n",
        encoding="utf-8",
    )

    passages = parse_markdown_witness(markdown, _witness())

    assert [passage.heading_path for passage in passages] == [
        ["A"],
        ["A", "H4 A"],
        ["A", "H4 B"],
        ["A", "H3"],
        ["A", "H3", "H5 A"],
        ["A", "H3", "H5 B"],
        ["A", "H3 again"],
    ]


def test_dialogue_heuristic_distinguishes_mixed_speech(tmp_path: Path) -> None:
    markdown = tmp_path / "dialogue.md"
    markdown.write_text('He said "Go."\n\n"Stay," she replied.\n', encoding="utf-8")

    passages = parse_markdown_witness(markdown, _witness())

    assert [passage.direct_dialogue for passage in passages] == ["mixed", "direct"]


def test_pandoc_tagged_quoted_inlines_are_rendered_without_changing_literal_quotes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    markdown = tmp_path / "quotes.md"
    markdown.write_text('A literal "quote".\n', encoding="utf-8")
    _stub_pandoc(
        monkeypatch,
        {
            "blocks": [
                {
                    "t": "Para",
                    "c": [
                        {"t": "Quoted", "c": [{"t": "DoubleQuote"}, _text("double")]},
                        {"t": "Space"},
                        {"t": "Quoted", "c": [{"t": "SingleQuote"}, _text("single")]},
                        {"t": "Space"},
                        {"t": "Str", "c": 'literal "quote"'},
                    ],
                }
            ]
        },
    )

    passages = parse_markdown_witness(markdown, _witness())

    assert passages[0].original_text == '"double" \'single\' literal "quote"'


def test_real_pandoc_preserves_selected_short_fiction_identity(tmp_path: Path) -> None:
    source = Path(
        "stories/time-expedition/original/text/selected-short-fiction/the-star.md"
    )

    passages = parse_markdown_witness(
        source, _witness("selected-short-fiction/the-star")
    )

    assert passages
    assert {passage.witness_id for passage in passages} == {
        "selected-short-fiction/the-star"
    }
    assert {passage.source_id for passage in passages} == {"selected-short-fiction"}
    assert {passage.selection_id for passage in passages} == {"the-star"}
    assert passages[0].passage_id.startswith("selected-short-fiction/the-star:")


@pytest.mark.parametrize(
    ("pandoc", "message"),
    [
        ("definitely-not-a-pandoc-executable", "Pandoc executable not found"),
    ],
)
def test_parse_reports_missing_pandoc(pandoc: str, message: str, tmp_path: Path) -> None:
    markdown = tmp_path / "fixture.md"
    markdown.write_text("Text.", encoding="utf-8")

    with pytest.raises(CreativeWriterError, match=message):
        parse_markdown_witness(markdown, _witness(), pandoc)


def test_parse_reports_pandoc_failures_and_malformed_ast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    markdown = tmp_path / "fixture.md"
    markdown.write_text("Text.", encoding="utf-8")
    _stub_pandoc(monkeypatch, {"not": "used"}, stderr="bad input", code=2)

    with pytest.raises(CreativeWriterError, match="Pandoc failed"):
        parse_markdown_witness(markdown, _witness())
    _stub_pandoc(monkeypatch, {"blocks": "not a list"})
    with pytest.raises(CreativeWriterError, match="Malformed Pandoc AST"):
        parse_markdown_witness(markdown, _witness())


def test_parse_rejects_empty_substantive_result(tmp_path: Path) -> None:
    markdown = tmp_path / "fixture.md"
    markdown.write_text("![](cover.png)\n\n---\n", encoding="utf-8")

    with pytest.raises(CreativeWriterError, match="no substantive passages"):
        parse_markdown_witness(markdown, _witness())


def test_index_round_trip_is_deterministic_and_rejects_duplicate_ids(tmp_path: Path) -> None:
    markdown = tmp_path / "fixture.md"
    markdown.write_text("# Heading\n\nText.\n", encoding="utf-8")
    passage = parse_markdown_witness(markdown, _witness())[0]
    other = passage.model_copy(update={"source_ordinal": 2, "heading_ordinal": 2})
    other = other.model_copy(
        update={
            "normalized_text": "Other.",
            "original_text": "Other.",
            "content_hash": hashlib.sha256(b"Other.").hexdigest(),
            "passage_id": f"the-time-machine:heading:2:{hashlib.sha256(b'Other.').hexdigest()[:12]}",
        }
    )
    output = tmp_path / "passages.jsonl"
    write_passage_index(output, [other, passage])

    assert output.read_text(encoding="utf-8") == "".join(
        f"{json.dumps(item.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n"
        for item in [passage, other]
    )
    assert read_passage_index(output) == [passage, other]

    duplicate = tmp_path / "duplicate.jsonl"
    duplicate.write_text(
        output.read_text(encoding="utf-8") + output.read_text(encoding="utf-8").splitlines()[0] + "\n",
        encoding="utf-8",
    )
    with pytest.raises(CreativeWriterError, match="duplicate passage ID"):
        read_passage_index(duplicate)


def test_index_uses_explicit_global_witness_ordinals_for_write_and_read(tmp_path: Path) -> None:
    first_path = tmp_path / "first.md"
    second_path = tmp_path / "second.md"
    first_path.write_text("First.", encoding="utf-8")
    second_path.write_text("Second.", encoding="utf-8")
    first = parse_markdown_witness(first_path, _witness("z-witness", 2))[0]
    second = parse_markdown_witness(second_path, _witness("a-witness", 1))[0]
    output = tmp_path / "ordered.jsonl"

    write_passage_index(output, [first, second])

    records = read_passage_index(output)
    assert [record.witness_id for record in records] == ["a-witness", "z-witness"]
    assert [record.witness_ordinal for record in records] == [1, 2]


@pytest.mark.parametrize(
    "bad_records",
    [
        pytest.param([], id="empty"),
        pytest.param("duplicate", id="duplicate-id"),
        pytest.param("inconsistent-witness", id="inconsistent-witness-mapping"),
        pytest.param("duplicate-ordinal", id="duplicate-ordinal-mapping"),
        pytest.param("missing-ordinal", id="non-contiguous-ordinals"),
    ],
)
def test_write_rejects_invalid_collections_before_replacing_existing_artifact(
    tmp_path: Path, bad_records: object
) -> None:
    markdown = tmp_path / "fixture.md"
    markdown.write_text("Text.", encoding="utf-8")
    passage = parse_markdown_witness(markdown, _witness("first", 1))[0]
    other = parse_markdown_witness(markdown, _witness("second", 2))[0]
    output = tmp_path / "passages.jsonl"
    output.write_text("existing artifact\n", encoding="utf-8")

    if bad_records == "duplicate":
        records = [passage, passage]
    elif bad_records == "inconsistent-witness":
        records = [passage, passage.model_copy(update={"witness_ordinal": 2})]
    elif bad_records == "duplicate-ordinal":
        records = [passage, other.model_copy(update={"witness_ordinal": 1})]
    elif bad_records == "missing-ordinal":
        records = [passage, other.model_copy(update={"witness_ordinal": 3})]
    else:
        records = []

    with pytest.raises(CreativeWriterError):
        write_passage_index(output, records)
    assert output.read_text(encoding="utf-8") == "existing artifact\n"


def test_read_rejects_empty_file_and_non_reading_order(tmp_path: Path) -> None:
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(CreativeWriterError, match="empty"):
        read_passage_index(empty)

    markdown = tmp_path / "fixture.md"
    markdown.write_text("Text.", encoding="utf-8")
    first = parse_markdown_witness(markdown, _witness("first", 1))[0]
    second = parse_markdown_witness(markdown, _witness("second", 2))[0]
    unordered = tmp_path / "unordered.jsonl"
    unordered.write_text(
        "".join(
            json.dumps(record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
            for record in [second, first]
        ),
        encoding="utf-8",
    )

    with pytest.raises(CreativeWriterError, match="order"):
        read_passage_index(unordered)


@pytest.mark.parametrize("field", ["heading_label", "normalized_text", "word_count", "content_hash", "passage_id"])
def test_read_rejects_isolated_record_tampering(tmp_path: Path, field: str) -> None:
    markdown = tmp_path / "fixture.md"
    markdown.write_text("# Heading\n\nText.", encoding="utf-8")
    passage = parse_markdown_witness(markdown, _witness())[0]
    payload = passage.model_dump(mode="json")
    payload[field] = {
        "heading_label": "Tampered",
        "normalized_text": "Tampered.",
        "word_count": passage.word_count + 1,
        "content_hash": "b" * 64,
        "passage_id": "tampered",
    }[field]
    index = tmp_path / f"tampered-{field}.jsonl"
    index.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(CreativeWriterError):
        read_passage_index(index)


def test_write_rejects_isolated_record_tampering_before_replacing_artifact(tmp_path: Path) -> None:
    markdown = tmp_path / "fixture.md"
    markdown.write_text("# Heading\n\nText.", encoding="utf-8")
    passage = parse_markdown_witness(markdown, _witness())[0]
    output = tmp_path / "passages.jsonl"
    output.write_text("existing artifact\n", encoding="utf-8")
    tampered = passage.model_copy(update={"word_count": passage.word_count + 1})

    with pytest.raises(CreativeWriterError):
        write_passage_index(output, [tampered])
    assert output.read_text(encoding="utf-8") == "existing artifact\n"


@pytest.mark.parametrize("max_blocks", [True, False, 0, 6])
def test_partition_windows_rejects_non_strict_or_out_of_range_max_blocks(
    max_blocks: object,
) -> None:
    with pytest.raises(CreativeWriterError, match="max_blocks"):
        partition_windows([], max_blocks=max_blocks)  # type: ignore[arg-type]


def test_write_preserves_existing_artifact_when_atomic_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    markdown = tmp_path / "fixture.md"
    markdown.write_text("Text.", encoding="utf-8")
    passage = parse_markdown_witness(markdown, _witness())[0]
    output = tmp_path / "passages.jsonl"
    output.write_text("existing artifact\n", encoding="utf-8")

    def fail_replace(*args: object, **kwargs: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr("creative_writer.source_passages.os.replace", fail_replace)

    with pytest.raises(CreativeWriterError, match="replace"):
        write_passage_index(output, [passage])
    assert output.read_text(encoding="utf-8") == "existing artifact\n"
    assert list(tmp_path.glob(f".{output.name}.*.tmp")) == []


def test_write_wraps_directory_creation_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    markdown = tmp_path / "fixture.md"
    markdown.write_text("Text.", encoding="utf-8")
    passage = parse_markdown_witness(markdown, _witness())[0]
    output = tmp_path / "new-directory" / "passages.jsonl"

    def fail_mkdir(*args: object, **kwargs: object) -> None:
        raise OSError("mkdir failed")

    monkeypatch.setattr(Path, "mkdir", fail_mkdir)

    with pytest.raises(CreativeWriterError, match="directory"):
        write_passage_index(output, [passage])


def test_context_window_is_two_sided_and_heading_bounded(tmp_path: Path) -> None:
    markdown = tmp_path / "fixture.md"
    markdown.write_text(
        "# A\n\nA1.\n\nA2.\n\nA3.\n\nA4.\n\nA5.\n\nA6.\n\n## B\n\nB1.\n",
        encoding="utf-8",
    )
    passages = parse_markdown_witness(markdown, _witness())

    middle = context_window(passages, passages[3].passage_id)
    boundary = context_window(passages, passages[5].passage_id)

    assert [passage.normalized_text for passage in middle] == [
        "A2.",
        "A3.",
        "A4.",
        "A5.",
        "A6.",
    ]
    assert [passage.normalized_text for passage in boundary] == [
        "A4.",
        "A5.",
        "A6.",
    ]


def test_partition_windows_are_non_overlapping_and_heading_bounded(tmp_path: Path) -> None:
    markdown = tmp_path / "fixture.md"
    markdown.write_text(
        "# A\n\nA1.\n\nA2.\n\nA3.\n\nA4.\n\nA5.\n\nA6.\n\n## B\n\nB1.\n\nB2.\n",
        encoding="utf-8",
    )
    passages = parse_markdown_witness(markdown, _witness())

    windows = partition_windows(passages)

    assert [[passage.normalized_text for passage in window] for window in windows] == [
        ["A1.", "A2.", "A3.", "A4.", "A5."],
        ["A6."],
        ["B1.", "B2."],
    ]
    assert len({passage.passage_id for window in windows for passage in window}) == len(
        passages
    )
