from __future__ import annotations

from pathlib import Path

from creative_writer.scaffold import create_story
from creative_writer.stats import generate_story_statistics


def test_generate_story_statistics_writes_report_and_counts_words(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "stats-story", "original")

    (story_dir / "manuscript" / "01-opening.md").write_text(
        "One two three four.\n",
        encoding="utf-8",
    )
    (story_dir / "manuscript" / "02-turn.md").write_text(
        "Five six seven eight nine.\n",
        encoding="utf-8",
    )
    (story_dir / "outline.md").write_text(
        "# Outline\n\nTen eleven twelve.\n",
        encoding="utf-8",
    )

    result = generate_story_statistics(tmp_path, "stats-story")

    assert result.manuscript_total_words == 9
    assert result.chapter_count == 2
    assert result.average_chapter_words == 4
    assert result.supporting_markdown_words > 0
    assert result.report_path.exists()

    report_text = result.report_path.read_text(encoding="utf-8")
    assert "# Manuscript Statistics: Stats Story" in report_text
    assert "| 1 | Opening | 4 |" in report_text
    assert "| 2 | Turn | 5 |" in report_text
    assert "Total manuscript words: 9" in report_text


def test_generate_story_statistics_falls_back_when_story_yml_is_invalid(
    tmp_path: Path,
) -> None:
    story_dir = create_story(tmp_path, "fallback-story", "original")
    (story_dir / "story.yml").write_text("title: [broken\n", encoding="utf-8")
    (story_dir / "manuscript" / "01-opening.md").write_text(
        "Fallback words only.\n",
        encoding="utf-8",
    )

    result = generate_story_statistics(tmp_path, "fallback-story")

    assert result.story_title == "Fallback Story"
    assert result.chapter_count >= 1
    assert any("Invalid YAML" in note for note in result.notes)
