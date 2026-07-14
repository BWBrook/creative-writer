"""Schema models for story projects."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    style_card: str | None = None
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
    review_mode: Literal["git_diff", "summary", "none", "excerpt_pack"]
    lint: LintSettings = Field(default_factory=LintSettings)


class CompositionWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: int = Field(ge=1800, le=2100)
    end: int = Field(ge=1800, le=2100)

    @model_validator(mode="after")
    def validate_order(self) -> "CompositionWindow":
        if self.end < self.start:
            raise ValueError("composition window end must not precede start")
        return self


class SourceAuthority(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tier: Literal[1, 2, 3, 4, 5]
    story_world_canon: bool
    style_authority: Literal["primary", "secondary", "bounded", "control", "none"]

    @model_validator(mode="after")
    def validate_tier(self) -> "SourceAuthority":
        if self.tier == 1:
            if not self.story_world_canon or self.style_authority != "primary":
                raise ValueError("Tier 1 must be canonical and use primary style authority")
        elif self.story_world_canon:
            raise ValueError("only Tier 1 may provide story-world canon")
        if self.tier == 2 and self.style_authority not in {"secondary", "bounded"}:
            raise ValueError("Tier 2 sources must use secondary or bounded style authority")
        if self.tier == 3 and self.style_authority != "bounded":
            raise ValueError("Tier 3 sources must use bounded style authority")
        if self.tier == 4 and self.style_authority != "control":
            raise ValueError("Tier 4 sources must use control style authority")
        if self.tier == 5 and self.style_authority != "none":
            raise ValueError("Tier 5 sources must use no style authority")
        return self


class SourceWork(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: NonEmptyStr
    author: NonEmptyStr
    first_published: int | None = Field(default=None, ge=1800, le=2100)


class PlannedSourceEdition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    publisher: NonEmptyStr
    homepage: NonEmptyStr
    download_url: NonEmptyStr
    artifact_format: Literal[
        "standard-ebooks-compatible-epub",
        "project-gutenberg-epub",
    ]
    planned_path: NonEmptyStr

    @field_validator("planned_path")
    @classmethod
    def validate_planned_path(cls, value: str) -> str:
        if not value.startswith("original/") or not value.endswith(".epub"):
            raise ValueError("planned_path must be an EPUB below original/")
        return value


class SourceSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Slug
    title: NonEmptyStr
    first_published: int = Field(ge=1800, le=2100)
    analytical_roles: list[NonEmptyStr] = Field(min_length=1)


class SourceAdmissionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Slug
    status: Literal["admitted", "approved", "proposed", "excluded"]
    authority: SourceAuthority
    work: SourceWork
    analytical_roles: list[NonEmptyStr] = Field(min_length=1)
    permitted_uses: list[NonEmptyStr] = Field(min_length=1)
    prohibited_uses: list[NonEmptyStr] = Field(min_length=1)
    rationale: NonEmptyStr
    edition: PlannedSourceEdition
    selections: list[SourceSelection] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_status(self) -> "SourceAdmissionRecord":
        if self.status == "excluded" and self.authority.tier != 5:
            raise ValueError("excluded sources must use Tier 5")
        if self.status != "excluded" and self.authority.tier == 5:
            raise ValueError("Tier 5 sources must be excluded")
        return self


class SourceStudyAdmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    composition_window: CompositionWindow
    editorial_mode: Literal["restrained_apparatus"]
    sources: list[SourceAdmissionRecord] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_sources(self) -> "SourceStudyAdmission":
        ids = [item.id for item in self.sources]
        if len(ids) != len(set(ids)):
            raise ValueError("source IDs must be unique")
        tier_one = [item for item in self.sources if item.authority.tier == 1]
        if len(tier_one) != 1:
            raise ValueError("admission must contain exactly one Tier 1 source")
        return self


class RetainedSourceRole(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tier: Literal[1, 2, 3, 4]
    story_world_canon: bool
    style_authority: Literal["primary", "secondary", "bounded", "control"]
    primary_style_anchor: bool
    secondary_style_anchor: bool
    focus: NonEmptyStr
    analytical_roles: list[NonEmptyStr] = Field(min_length=1)
    permitted_uses: list[NonEmptyStr] = Field(min_length=1)
    prohibited_uses: list[NonEmptyStr] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_flags(self) -> "RetainedSourceRole":
        authority = SourceAuthority(
            tier=self.tier,
            story_world_canon=self.story_world_canon,
            style_authority=self.style_authority,
        )
        del authority
        if self.primary_style_anchor != (self.style_authority == "primary"):
            raise ValueError("primary_style_anchor must match style_authority")
        if self.secondary_style_anchor != (
            self.style_authority in {"secondary", "bounded"}
        ):
            raise ValueError("secondary_style_anchor must match style_authority")
        return self


class RetainedSourceEdition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    publisher: NonEmptyStr
    homepage: NonEmptyStr
    download_url: NonEmptyStr
    upstream_release: NonEmptyStr
    upstream_revision: NonEmptyStr


class RetainedSourceFiles(BaseModel):
    model_config = ConfigDict(extra="forbid")

    epub: NonEmptyStr
    epub_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    markdown: NonEmptyStr


class SourceDerivation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: NonEmptyStr
    input: NonEmptyStr
    writer: NonEmptyStr
    wrap: NonEmptyStr
    filter: NonEmptyStr


class SourceProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transcription: NonEmptyStr
    page_scans: NonEmptyStr


class SourceRights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_text: NonEmptyStr
    edition_contributions: NonEmptyStr


class RetainedSourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Slug
    role: RetainedSourceRole
    work: SourceWork
    edition: RetainedSourceEdition
    retrieved: NonEmptyStr
    files: RetainedSourceFiles
    derivation: SourceDerivation
    provenance: SourceProvenance
    rights: SourceRights


class SourcesRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sources: list[RetainedSourceRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "SourcesRegistry":
        ids = [item.id for item in self.sources]
        if len(ids) != len(set(ids)):
            raise ValueError("retained source IDs must be unique")
        return self


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


class PlotDeviceRecord(BaseModel):
    """Plot-device registry item."""

    model_config = ConfigDict(extra="forbid")

    id: Slug
    name: NonEmptyStr
    narrative_role: str = ""
    description: str = ""
    status: Literal["dormant", "active", "resolved"] = "dormant"


class PlotDevicesRegistry(BaseModel):
    """Optional plot-device registry."""

    model_config = ConfigDict(extra="forbid")

    plot_devices: list[PlotDeviceRecord] = Field(default_factory=list)


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


class ReviewPackEntry(BaseModel):
    """One targeted excerpt request inside a review pack."""

    model_config = ConfigDict(extra="forbid")

    id: Slug
    label: NonEmptyStr
    manuscript: NonEmptyStr
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    kind: Literal["confidence", "uncertainty"]
    question: NonEmptyStr
    context: str = ""

    @field_validator("manuscript")
    @classmethod
    def validate_manuscript_path(cls, value: str) -> str:
        if not value.startswith("manuscript/") or not value.endswith(".md"):
            raise ValueError("manuscript must live under manuscript/ and end in .md")
        return value

    @model_validator(mode="after")
    def validate_line_range(self) -> "ReviewPackEntry":
        if self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")
        return self


class ReviewPackManifest(BaseModel):
    """A story-local manifest for targeted review excerpts."""

    model_config = ConfigDict(extra="forbid")

    title: NonEmptyStr
    purpose: NonEmptyStr
    entries: list[ReviewPackEntry] = Field(min_length=1)


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
