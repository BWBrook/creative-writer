from __future__ import annotations

from pathlib import Path

from creative_writer.scaffold import create_story, list_style_cards


def test_init_story_creates_required_and_optional_artifacts(tmp_path: Path) -> None:
    (tmp_path / "templates" / "story" / "chapter-stubs").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "manuscript").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "scene-cards" / "01-opening").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "scene-cards" / "02-turn").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "assets" / "images").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "story.yml").write_text(
        'title: "{{story_title}}"\nslug: "{{story_slug}}"\nkind: "{{story_kind}}"\n'
        "status: planning\n"
        'language: "en-AU"\n'
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
    (tmp_path / "templates" / "story" / "style-card.md").write_text(
        "# Style Card\n\nDefault card for {{story_title}}.\n",
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
        "style-card.md",
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
    assert 'language: "en-AU"' in story_config
    assert "Stub for Test Story." in opening_stub
    assert "Prose for Test Story opening." in opening_manuscript


def test_init_story_can_copy_builtin_style_card(tmp_path: Path) -> None:
    (tmp_path / "templates" / "story").mkdir(parents=True)
    (tmp_path / "templates" / "style-cards").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "chapter-stubs").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "manuscript").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "scene-cards").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "assets" / "images").mkdir(parents=True)

    (tmp_path / "templates" / "story" / "story.yml").write_text(
        'title: "{{story_title}}"\nslug: "{{story_slug}}"\nkind: "{{story_kind}}"\n'
        "status: planning\n"
        'language: "en-AU"\n'
        "target_outputs:\n"
        "  - epub\n"
        "chapters:\n"
        "  - chapter-stubs/01-opening.md\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "contract.yml").write_text(
        'human_role: "Human role."\nai_role: "AI role."\nauthority_mode: direct_edit\nreview_mode: git_diff\n',
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "style-guide.md").write_text(
        "# Style Guide\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "style-card.md").write_text(
        "# Style Card\n\nPlaceholder.\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "outline.md").write_text(
        "# Outline\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "chapter-stubs" / "01-opening.md").write_text(
        "---\n"
        'title: "Opening"\n'
        'summary: "Set up."\n'
        'manuscript: "manuscript/01-opening.md"\n'
        "characters: []\nlocations: []\nclues_introduced: []\nclues_resolved: []\nplot_devices: []\ntimeline_events: []\nimages: []\n"
        "---\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "manuscript" / "01-opening.md").write_text(
        "Draft.\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "style-cards" / "quiet_catastrophe_realism.md").write_text(
        "# Style Card: Quiet Catastrophe Realism\n\nSelected content.\n",
        encoding="utf-8",
    )

    story_dir = create_story(
        tmp_path,
        "styled-story",
        "original",
        style_card="quiet-catastrophe-realism",
    )

    style_card_text = (story_dir / "style-card.md").read_text(encoding="utf-8")
    story_config = (story_dir / "story.yml").read_text(encoding="utf-8")

    assert "Quiet Catastrophe Realism" in style_card_text
    assert "Selected content." in style_card_text
    assert "style_card: quiet_catastrophe_realism" in story_config


def test_init_story_can_copy_custom_style_card(tmp_path: Path) -> None:
    (tmp_path / "templates" / "story").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "chapter-stubs").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "manuscript").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "scene-cards").mkdir(parents=True)
    (tmp_path / "templates" / "story" / "assets" / "images").mkdir(parents=True)

    (tmp_path / "templates" / "story" / "story.yml").write_text(
        'title: "{{story_title}}"\nslug: "{{story_slug}}"\nkind: "{{story_kind}}"\n'
        "status: planning\n"
        'language: "en-AU"\n'
        "target_outputs:\n"
        "  - epub\n"
        "chapters:\n"
        "  - chapter-stubs/01-opening.md\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "contract.yml").write_text(
        'human_role: "Human role."\nai_role: "AI role."\nauthority_mode: direct_edit\nreview_mode: git_diff\n',
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "style-guide.md").write_text(
        "# Style Guide\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "style-card.md").write_text(
        "# Style Card\n\nPlaceholder.\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "outline.md").write_text(
        "# Outline\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "chapter-stubs" / "01-opening.md").write_text(
        "---\n"
        'title: "Opening"\n'
        'summary: "Set up."\n'
        'manuscript: "manuscript/01-opening.md"\n'
        "characters: []\nlocations: []\nclues_introduced: []\nclues_resolved: []\nplot_devices: []\ntimeline_events: []\nimages: []\n"
        "---\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "story" / "manuscript" / "01-opening.md").write_text(
        "Draft.\n",
        encoding="utf-8",
    )
    custom_card = tmp_path / "my-custom-style.md"
    custom_card.write_text(
        "# Style Card: My Custom Style\n\nCustom content.\n",
        encoding="utf-8",
    )

    story_dir = create_story(
        tmp_path,
        "custom-story",
        "original",
        style_card=str(custom_card),
    )

    style_card_text = (story_dir / "style-card.md").read_text(encoding="utf-8")
    story_config = (story_dir / "story.yml").read_text(encoding="utf-8")

    assert "My Custom Style" in style_card_text
    assert "Custom content." in style_card_text
    assert "style_card: custom/my_custom_style" in story_config


def test_list_style_cards_returns_titles(tmp_path: Path) -> None:
    (tmp_path / "templates" / "style-cards").mkdir(parents=True)
    (tmp_path / "templates" / "style-cards" / "README.md").write_text(
        "# Style Cards\n",
        encoding="utf-8",
    )
    (tmp_path / "templates" / "style-cards" / "quiet_catastrophe_realism.md").write_text(
        "# Style Card: Quiet Catastrophe Realism\n",
        encoding="utf-8",
    )

    assert list_style_cards(tmp_path) == [
        ("quiet_catastrophe_realism", "Quiet Catastrophe Realism")
    ]
