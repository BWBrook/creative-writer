"""Schema models for story projects."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Slug = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
NonEmptyStr = Annotated[str, Field(min_length=1)]


def _validate_string_list(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("values must be non-empty strings")
        cleaned.append(value.strip())
    return cleaned


class StoryConfig(BaseModel):
    """Metadata for a story project."""

    model_config = ConfigDict(extra="forbid")

    title: NonEmptyStr
    slug: Slug
    kind: Literal["original", "pastiche"]
    status: Literal["planning", "draft", "revising", "complete"]
    language: str = Field(default="en-AU", pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
    target_outputs: list[Literal["epub", "pdf"]] = Field(min_length=1)
    chapters: list[str] = Field(min_length=1)

    @field_validator("chapters")
    @classmethod
    def validate_chapters(cls, value: list[str]) -> list[str]:
        cleaned = _validate_string_list(value)
        seen: set[str] = set()
        for chapter in cleaned:
            if chapter in seen:
                raise ValueError("chapters must be unique")
            if not chapter.startswith("chapter-stubs/") or not chapter.endswith(".md"):
                raise ValueError(
                    "chapter paths must live under chapter-stubs/ and end in .md"
                )
            seen.add(chapter)
        return cleaned


class EmDashLint(BaseModel):
    """Heuristic settings for em-dash warnings."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    max_per_chapter: int = Field(default=2, ge=0)


class ContrastiveLint(BaseModel):
    """Heuristic settings for contrastive parallelism warnings."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    max_instances_per_chapter: int = Field(default=1, ge=0)


class LintSettings(BaseModel):
    """Lint settings attached to the collaboration contract."""

    model_config = ConfigDict(extra="forbid")

    em_dash: EmDashLint = Field(default_factory=EmDashLint)
    contrastive_parallelism: ContrastiveLint = Field(
        default_factory=ContrastiveLint
    )


class ContractConfig(BaseModel):
    """Human/AI contract for a story project."""

    model_config = ConfigDict(extra="forbid")

    human_role: NonEmptyStr
    ai_role: NonEmptyStr
    authority_mode: Literal["direct_edit", "suggest_only", "review_first"]
    review_mode: Literal["git_diff", "summary", "none"]
    lint: LintSettings = Field(default_factory=LintSettings)


class CharacterRecord(BaseModel):
    """Character registry item."""

    model_config = ConfigDict(extra="forbid")

    id: Slug
    name: NonEmptyStr
    role: str = ""
    motivation: str = ""


class CharactersRegistry(BaseModel):
    """Optional character registry."""

    model_config = ConfigDict(extra="forbid")

    characters: list[CharacterRecord] = Field(default_factory=list)


class ClueRecord(BaseModel):
    """Clue registry item."""

    model_config = ConfigDict(extra="forbid")

    id: Slug
    name: NonEmptyStr
    description: str = ""
    status: Literal["hidden", "introduced", "resolved"] = "hidden"


class CluesRegistry(BaseModel):
    """Optional clue registry."""

    model_config = ConfigDict(extra="forbid")

    clues: list[ClueRecord] = Field(default_factory=list)


class LocationRecord(BaseModel):
    """Location registry item."""

    model_config = ConfigDict(extra="forbid")

    id: Slug
    name: NonEmptyStr
    description: str = ""


class LocationsRegistry(BaseModel):
    """Optional location registry."""

    model_config = ConfigDict(extra="forbid")

    locations: list[LocationRecord] = Field(default_factory=list)


class TimelineEvent(BaseModel):
    """Timeline registry item."""

    model_config = ConfigDict(extra="forbid")

    id: Slug
    label: NonEmptyStr
    when: NonEmptyStr
    description: str = ""


class TimelineRegistry(BaseModel):
    """Optional timeline registry."""

    model_config = ConfigDict(extra="forbid")

    events: list[TimelineEvent] = Field(default_factory=list)


class ChapterFrontMatter(BaseModel):
    """Required YAML front matter for chapter stubs."""

    model_config = ConfigDict(extra="allow")

    title: NonEmptyStr
    summary: NonEmptyStr
    manuscript: NonEmptyStr
    scene_cards_dir: str | None = None
    characters: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    clues_introduced: list[str] = Field(default_factory=list)
    clues_resolved: list[str] = Field(default_factory=list)
    plot_devices: list[str] = Field(default_factory=list)
    timeline_events: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)

    @field_validator(
        "manuscript",
    )
    @classmethod
    def validate_manuscript_path(cls, value: str) -> str:
        if not value.startswith("manuscript/") or not value.endswith(".md"):
            raise ValueError("manuscript must live under manuscript/ and end in .md")
        return value

    @field_validator(
        "scene_cards_dir",
    )
    @classmethod
    def validate_scene_cards_dir(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.startswith("scene-cards/"):
            raise ValueError("scene_cards_dir must live under scene-cards/")
        return value

    @field_validator(
        "characters",
        "locations",
        "clues_introduced",
        "clues_resolved",
        "plot_devices",
        "timeline_events",
        "images",
    )
    @classmethod
    def validate_lists(cls, value: list[str]) -> list[str]:
        return _validate_string_list(value)


@dataclass(slots=True)
class ChapterDocument:
    """A parsed chapter with validated front matter."""

    stub_path: Path
    manuscript_path: Path
    front_matter: ChapterFrontMatter
    stub_body: str
    manuscript_body: str


@dataclass(slots=True)
class CheckMessage:
    """A blocking or advisory message from `check`."""

    kind: Literal["error", "warning"]
    location: str
    message: str


@dataclass(slots=True)
class CheckResult:
    """Complete result for a story check run."""

    story_slug: str
    story_title: str = ""
    story: StoryConfig | None = None
    contract: ContractConfig | None = None
    chapters: list[ChapterDocument] = field(default_factory=list)
    errors: list[CheckMessage] = field(default_factory=list)
    warnings: list[CheckMessage] = field(default_factory=list)
    report_path: Path | None = None

    @property
    def ok(self) -> bool:
        return not self.errors
