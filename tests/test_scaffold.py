from __future__ import annotations

from pathlib import Path

from creative_writer.scaffold import create_story


def test_init_story_creates_required_and_optional_artifacts(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "test-story", "original")

    expected = [
        "story.yml",
        "contract.yml",
        "style-guide.md",
        "outline.md",
        "characters.yml",
        "clues.yml",
        "locations.yml",
        "timeline.yml",
        "world.md",
        "manuscript/01-opening.md",
        "manuscript/02-turn.md",
        "scene-cards/README.md",
    ]

    for relative in expected:
        assert (story_dir / relative).exists(), relative
