"""Story scaffolding logic."""

from __future__ import annotations

import re
from pathlib import Path

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory, write_text

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def slug_to_title(slug: str) -> str:
    """Convert a slug into a simple title."""

    words = [piece for piece in slug.replace("_", "-").split("-") if piece]
    if not words:
        raise CreativeWriterError("Story slug must contain at least one word.")
    return " ".join(word.capitalize() for word in words)


def create_story(root: Path, slug: str, kind: str, title: str | None = None) -> Path:
    """Create a new story directory with required and optional templates."""

    if kind not in {"original", "pastiche"}:
        raise CreativeWriterError("KIND must be either 'original' or 'pastiche'.")
    if not SLUG_PATTERN.fullmatch(slug):
        raise CreativeWriterError(
            "Story slug must use lowercase letters, numbers, and single hyphens."
        )

    story_title = title or slug_to_title(slug)
    story_dir = root / "stories" / slug
    if story_dir.exists():
        raise CreativeWriterError(f"Story already exists: {story_dir}")

    ensure_directory(story_dir)
    ensure_directory(story_dir / "manuscript")
    ensure_directory(story_dir / "scene-cards")

    write_text(
        story_dir / "story.yml",
        f"""
        title: "{story_title}"
        slug: "{slug}"
        kind: "{kind}"
        status: planning
        target_outputs:
          - epub
          - pdf
        chapters:
          - manuscript/01-opening.md
          - manuscript/02-turn.md
        """,
    )
    write_text(
        story_dir / "contract.yml",
        """
        human_role: "Provide premise, taste, structural feedback, and revision requests."
        ai_role: "Draft and revise manuscript material within the agreed story contract."
        authority_mode: direct_edit
        review_mode: git_diff
        lint:
          em_dash:
            enabled: true
            max_per_chapter: 2
          contrastive_parallelism:
            enabled: true
            max_instances_per_chapter: 1
        """,
    )
    write_text(
        story_dir / "style-guide.md",
        f"""
        # Style Guide

        This is a core artifact for `{story_title}`.

        ## Voice and tone

        - State the intended voice here.
        - Note tonal boundaries and prose constraints.

        ## Things to lean toward

        - Clarity
        - Narrative economy
        - Strong scene purpose

        ## Things to avoid

        - Empty atmospheric filler
        - Style drift away from the agreed contract
        - Repetitive AI habits not wanted in this project
        """,
    )
    write_text(
        story_dir / "outline.md",
        f"""
        # Outline

        ## Premise

        Summarize the premise of `{story_title}` here.

        ## Narrative arc

        - Opening situation
        - Escalation
        - Discovery or reversal
        - Consequence

        ## Chapter order

        1. `01-opening.md`
        2. `02-turn.md`
        """,
    )
    write_text(
        story_dir / "characters.yml",
        """
        # Optional registry: add named or recurring characters when helpful.
        characters: []
        """,
    )
    write_text(
        story_dir / "clues.yml",
        """
        # Optional registry: track clues, reveals, and mystery elements here.
        clues: []
        """,
    )
    write_text(
        story_dir / "locations.yml",
        """
        # Optional registry: track recurring or mission-critical places here.
        locations: []
        """,
    )
    write_text(
        story_dir / "timeline.yml",
        """
        # Optional registry: track events that matter for chronology.
        events: []
        """,
    )
    write_text(
        story_dir / "world.md",
        """
        # World Notes

        This is an optional artifact. Use it for setting facts, rules, and
        constraints that do not belong in the outline or style guide.
        """,
    )
    write_text(
        story_dir / "scene-cards" / "README.md",
        """
        # Scene Cards

        This optional directory can hold one Markdown file per scene card when a
        project benefits from scene-level planning.
        """,
    )
    write_text(
        story_dir / "manuscript" / "01-opening.md",
        """
        ---
        title: "Opening"
        summary: "Set up the story situation and introduce the first turn."
        characters: []
        locations: []
        clues_introduced: []
        clues_resolved: []
        plot_devices: []
        timeline_events: []
        ---

        ## Draft notes

        Replace this placeholder with prose or structured scene notes.
        """,
    )
    write_text(
        story_dir / "manuscript" / "02-turn.md",
        """
        ---
        title: "Turn"
        summary: "Develop the complication or discovery that redirects the story."
        characters: []
        locations: []
        clues_introduced: []
        clues_resolved: []
        plot_devices: []
        timeline_events: []
        ---

        ## Draft notes

        Replace this placeholder with prose or structured scene notes.
        """,
    )

    return story_dir
