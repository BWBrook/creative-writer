from __future__ import annotations

from pathlib import Path

from creative_writer.checks import check_story
from creative_writer.scaffold import create_story


def test_reference_integrity_fails_for_unknown_registry_entries(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "reference-test", "original")

    (story_dir / "characters.yml").write_text(
        "characters:\n  - id: hero\n    name: Hero\n",
        encoding="utf-8",
    )
    (story_dir / "manuscript" / "01-opening.md").write_text(
        """---
title: "Opening"
summary: "Introduce the protagonist."
characters:
  - stranger
locations: []
clues_introduced: []
clues_resolved: []
plot_devices: []
timeline_events: []
---

Body text.
""",
        encoding="utf-8",
    )

    result = check_story(tmp_path, "reference-test")

    assert not result.ok
    assert any("Unknown characters referenced" in error.message for error in result.errors)


def test_heuristics_warn_without_failing(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "warning-test", "original")

    (story_dir / "contract.yml").write_text(
        """human_role: "Guide the story."
ai_role: "Draft the prose."
authority_mode: direct_edit
review_mode: git_diff
lint:
  em_dash:
    enabled: true
    max_per_chapter: 0
  contrastive_parallelism:
    enabled: true
    max_instances_per_chapter: 0
""",
        encoding="utf-8",
    )
    (story_dir / "manuscript" / "01-opening.md").write_text(
        """---
title: "Opening"
summary: "Generate warnings but no blocking errors."
characters: []
locations: []
clues_introduced: []
clues_resolved: []
plot_devices: []
timeline_events: []
---

This line uses an em dash — once.
It was not quiet but tense.
""",
        encoding="utf-8",
    )

    result = check_story(tmp_path, "warning-test")

    assert result.ok
    assert len(result.warnings) == 2


def test_invalid_story_schema_is_blocking(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "schema-test", "original")
    (story_dir / "story.yml").write_text(
        """title: "Broken Story"
slug: "schema-test"
kind: "mystery"
status: planning
target_outputs:
  - epub
chapters:
  - manuscript/01-opening.md
""",
        encoding="utf-8",
    )

    result = check_story(tmp_path, "schema-test")

    assert not result.ok
    assert any("Schema validation failed" in error.message for error in result.errors)
