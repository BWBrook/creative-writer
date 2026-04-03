from __future__ import annotations

from pathlib import Path

from creative_writer.scaffold import create_story


def test_init_story_creates_required_and_optional_artifacts(tmp_path: Path) -> None:
    (tmp_path / "templates" / "story" / "chapter-stubs").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "manuscript").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "scene-cards" / "01-opening").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "scene-cards" / "02-turn").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "assets" / "images").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "story.yml").write_text(
        'title: "{{story_title}}"\nslug: "{{story_slug}}"\nkind: "{{story_kind}}"\n'
        "status: planning\n"
        "target_outputs:\n"
        "  - epub\n"
        "chapters:\n"
        "  - chapter-stubs/01-opening.md\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "contract.yml").write_text(
        'human_role: "Human role for {{story_title}}."\n'
        'ai_role: "AI role for {{story_title}}."\n'
        "authority_mode: direct_edit\n"
        "review_mode: git_diff\n"
        "lint:\n"
        "  em_dash:\n"
        "    enabled: true\n"
        "    max_per_chapter: 2\n"
        "  contrastive_parallelism:\n"
        "    enabled: true\n"
        "    max_instances_per_chapter: 1\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "style-guide.md").write_text(
        "# Style Guide\n\nFor {{story_title}}.\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "outline.md").write_text(
        "# Outline\n\nPremise for {{story_title}}.\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "characters.yml").write_text(
        "characters: []\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "clues.yml").write_text(
        "clues: []\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "locations.yml").write_text(
        "locations: []\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "timeline.yml").write_text(
        "events: []\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "world.md").write_text(
        "# World Notes\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "assets" / "images" / "README.md").write_text(
        "# Story Images\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "scene-cards" / "README.md").write_text(
        "# Scene Cards\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "scene-cards" / "01-opening" / "README.md").write_text(
        "# Opening Scene Cards\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "scene-cards" / "02-turn" / "README.md").write_text(
        "# Turn Scene Cards\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "chapter-stubs" / "01-opening.md").write_text(
        "---\n"
        'title: "Opening"\n'
        'summary: "Set up the story."\n'
        'manuscript: "manuscript/01-opening.md"\n'
        'scene_cards_dir: "scene-cards/01-opening"\n'
        "characters: []\n"
        "locations: []\n"
        "clues_introduced: []\n"
        "clues_resolved: []\n"
        "plot_devices: []\n"
        "timeline_events: []\n"
        "images: []\n"
        "---\n\n"
        "Stub for {{story_title}}.\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "chapter-stubs" / "02-turn.md").write_text(
        "---\n"
        'title: "Turn"\n'
        'summary: "Develop the turn."\n'
        'manuscript: "manuscript/02-turn.md"\n'
        'scene_cards_dir: "scene-cards/02-turn"\n'
        "characters: []\n"
        "locations: []\n"
        "clues_introduced: []\n"
        "clues_resolved: []\n"
        "plot_devices: []\n"
        "timeline_events: []\n"
        "images: []\n"
        "---\n\n"
        "Turn stub for {{story_title}}.\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "manuscript" / "01-opening.md").write_text(
        "Prose for {{story_title}} opening.\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "manuscript" / "02-turn.md").write_text(
        "Prose for {{story_title}} turn.\n",
        encoding="utf-8",
    )

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
        "assets/images/README.md",
        "chapter-stubs/01-opening.md",
        "chapter-stubs/02-turn.md",
        "manuscript/01-opening.md",
        "manuscript/02-turn.md",
        "scene-cards/README.md",
        "scene-cards/01-opening/README.md",
        "scene-cards/02-turn/README.md",
    ]

    for relative in expected:
        assert (story_dir / relative).exists(), relative

    story_config = (story_dir / "story.yml").read_text(encoding="utf-8")
    opening_stub = (story_dir / "chapter-stubs" / "01-opening.md").read_text(
        encoding="utf-8"
    )
    opening_manuscript = (story_dir / "manuscript" / "01-opening.md").read_text(
        encoding="utf-8"
    )

    assert 'title: "Test Story"' in story_config
    assert 'slug: "test-story"' in story_config
    assert "Stub for Test Story." in opening_stub
    assert "Prose for Test Story opening." in opening_manuscript
