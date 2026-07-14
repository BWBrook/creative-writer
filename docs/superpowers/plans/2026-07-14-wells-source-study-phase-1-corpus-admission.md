# Wells Source Study Phase 1: Corpus Admission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish and validate the exact source-admission boundary for the Wells forensic study, retain the two already-approved Wells witnesses, and stop at the required human corpus-review gate before detailed analysis.

**Architecture:** Add strict Pydantic schemas for the proposed and admitted source records, then expose a generic `source-admission` command that cross-checks story-local admission decisions against retained files, fingerprints, derived Markdown, and authority roles. Keep the study story-local under `stories/time-expedition/`; retain archival sources under `original/`, planning and method under `source-study/`, and generated reports under ignored `build/`.

**Tech Stack:** Python 3.12+, Pydantic 2, PyYAML, `uv`, Pytest, GNU Make, Pandoc 3.10, `curl`, `unzip`, and macOS `shasum`.

## Global Constraints

- *The Time Machine* remains the sole story-world canon and Tier 1 primary style authority.
- The positive style target remains Wells circa 1897-1899.
- *The Invisible Man*, *The Island of Doctor Moreau*, and *The War of the Worlds* contribute no `Time Expedition` continuity.
- Non-Wells authors are Tier 4 controls only and never prescribe anthology prose.
- The reader-facing recovered-manuscript conceit uses restrained editorial apparatus; repository metadata remains truthful about the pastiche.
- Source downloads, archive integrity, fingerprints, derived-text boundaries, and source locators are blocking validation concerns.
- Metrics are not implemented in this phase.
- No model API, Wells score, automatic rewriting, Permian research, narrative architecture, scene planning, or manuscript prose is permitted.
- Proposed sources must not be retained under `original/` until the admission report receives human approval.
- Existing source Markdown remains excluded from manuscript statistics.
- Manual edits use `apply_patch`; Pandoc may overwrite generated Markdown during reproducible derivation.

## Scope Boundary

The approved design contains a mandatory human review after corpus admission.
This plan therefore implements only Phase 1:

1. admission and provenance schemas;
2. admission validation and reporting;
3. the exact proposed corpus record;
4. acquisition of *Doctor Moreau* and *The War of the Worlds*, which the user
   has already approved as fixed additions;
5. a final admission report for human review.

The quantitative profile, close-reading findings, evidence ledger, held-out
validation, operational style guide, and recurring authenticity tooling will
receive a second implementation plan after this gate.

---

### Task 1: Add Source Admission and Provenance Schemas

**Files:**
- Modify: `src/creative_writer/models.py`
- Create: `tests/test_source_models.py`

**Interfaces:**
- Produces: `SourceStudyAdmission`, `SourceAdmissionRecord`, `SourceAuthority`, `SourceSelection`, `SourcesRegistry`, and their nested models.
- Consumes later: `load_yaml_model(path, SourceStudyAdmission)` and `load_yaml_model(path, SourcesRegistry)`.

- [ ] **Step 1: Write failing tests for valid admission data and authority invariants**

Create `tests/test_source_models.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import load_yaml_model
from creative_writer.models import SourceStudyAdmission, SourcesRegistry


VALID_ADMISSION = """composition_window:
  start: 1897
  end: 1899
editorial_mode: restrained_apparatus
sources:
  - id: the-time-machine
    status: admitted
    authority:
      tier: 1
      story_world_canon: true
      style_authority: primary
    work:
      title: The Time Machine
      author: H. G. Wells
      first_published: 1895
    analytical_roles:
      - canonical frame
    permitted_uses:
      - continuity
    prohibited_uses:
      - none
    rationale: Governing source.
    edition:
      publisher: Standard Ebooks
      homepage: https://standardebooks.org/ebooks/h-g-wells/the-time-machine
      download_url: https://standardebooks.org/ebooks/h-g-wells/the-time-machine/downloads/h-g-wells_the-time-machine.epub?source=download
      artifact_format: standard-ebooks-compatible-epub
      planned_path: original/h-g-wells_the-time-machine.epub
    selections: []
"""


def test_source_study_admission_parses_valid_yaml(tmp_path: Path) -> None:
    path = tmp_path / "admission.yml"
    path.write_text(VALID_ADMISSION, encoding="utf-8")

    admission = load_yaml_model(path, SourceStudyAdmission)

    assert admission.composition_window.start == 1897
    assert admission.sources[0].authority.style_authority == "primary"


def test_source_study_admission_rejects_duplicate_ids(tmp_path: Path) -> None:
    path = tmp_path / "admission.yml"
    path.write_text(VALID_ADMISSION + VALID_ADMISSION.split("sources:\n", 1)[1], encoding="utf-8")

    with pytest.raises(CreativeWriterError, match="source IDs must be unique"):
        load_yaml_model(path, SourceStudyAdmission)


def test_period_control_cannot_claim_positive_style_authority(tmp_path: Path) -> None:
    path = tmp_path / "admission.yml"
    path.write_text(
        VALID_ADMISSION.replace("tier: 1", "tier: 4")
        .replace("story_world_canon: true", "story_world_canon: false")
        .replace("style_authority: primary", "style_authority: bounded"),
        encoding="utf-8",
    )

    with pytest.raises(CreativeWriterError, match="Tier 4 sources must use control style authority"):
        load_yaml_model(path, SourceStudyAdmission)


@pytest.mark.parametrize(
    ("tier", "style_authority"),
    [(2, "primary"), (3, "secondary")],
)
def test_wells_witness_authority_must_match_tier(
    tmp_path: Path,
    tier: int,
    style_authority: str,
) -> None:
    path = tmp_path / "admission.yml"
    path.write_text(
        VALID_ADMISSION.replace("tier: 1", f"tier: {tier}")
        .replace("story_world_canon: true", "story_world_canon: false")
        .replace("style_authority: primary", f"style_authority: {style_authority}"),
        encoding="utf-8",
    )

    with pytest.raises(CreativeWriterError, match=f"Tier {tier} sources"):
        load_yaml_model(path, SourceStudyAdmission)


def test_sources_registry_rejects_inconsistent_primary_flags(tmp_path: Path) -> None:
    path = tmp_path / "sources.yml"
    path.write_text(
        """sources:
  - id: the-time-machine
    role:
      tier: 1
      story_world_canon: true
      style_authority: primary
      primary_style_anchor: false
      secondary_style_anchor: false
      focus: Canonical frame.
      analytical_roles: [canonical frame]
      permitted_uses: [continuity]
      prohibited_uses: [none]
    work:
      title: The Time Machine
      author: H. G. Wells
      first_published: 1895
    edition:
      publisher: Standard Ebooks
      homepage: https://example.test/book
      download_url: https://example.test/book.epub
      upstream_release: 2026-06-30T02:48:51Z
      upstream_revision: abc1234
    retrieved: 2026-07-13
    files:
      epub: book.epub
      epub_sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
      markdown: text/book.md
    derivation:
      tool: Pandoc 3.10
      input: chapters
      writer: gfm-raw_html
      wrap: none
      filter: filters/remove-excluded-packaging-links.lua
    provenance:
      transcription: Test transcription
      page_scans: Test scans
    rights:
      source_text: Public domain test fixture.
      edition_contributions: Test edition statement.
""",
        encoding="utf-8",
    )

    with pytest.raises(CreativeWriterError, match="primary_style_anchor must match style_authority"):
        load_yaml_model(path, SourcesRegistry)
```

- [ ] **Step 2: Run the model tests and verify RED**

Run:

```bash
uv run --group dev pytest tests/test_source_models.py -v
```

Expected: collection fails because the source-study model classes do not yet exist.

- [ ] **Step 3: Add the source-study models**

Append the following model family after `ContractConfig` in `src/creative_writer/models.py`:

```python
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
```

- [ ] **Step 4: Run the model tests and verify GREEN**

Run:

```bash
uv run --group dev pytest tests/test_source_models.py -v
```

Expected: all model tests pass.

- [ ] **Step 5: Run the existing model tests**

Run:

```bash
uv run --group dev pytest tests/test_models.py tests/test_source_models.py -v
```

Expected: all existing and new model tests pass.

- [ ] **Step 6: Commit the schema foundation**

```bash
git add src/creative_writer/models.py tests/test_source_models.py
git commit -m "Add forensic source admission schemas"
```

---

### Task 2: Add Admission Validation, Report, and CLI

**Files:**
- Create: `src/creative_writer/source_admission.py`
- Modify: `src/creative_writer/cli.py`
- Modify: `Makefile`
- Create: `tests/test_source_admission.py`

**Interfaces:**
- Consumes: `stories/<slug>/source-study/admission.yml` as `SourceStudyAdmission` and `stories/<slug>/original/sources.yml` as `SourcesRegistry`.
- Produces: `check_source_admission(root: Path, slug: str) -> SourceAdmissionResult` and `build/<slug>/reports/source-admission-report.md`.
- Public CLI: `creative-writer source-admission --story <slug>`.
- Public Make target: `make source-admission STORY=<slug>`.

- [ ] **Step 1: Write failing validation tests**

Create `tests/test_source_admission.py` with a helper that writes one admitted source and one proposed source. The tests must cover a clean report, a bad retained checksum, a missing admitted registry record, and premature acquisition of a proposed source:

```python
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from creative_writer.source_admission import check_source_admission


def _write_fixture(root: Path) -> Path:
    story = root / "stories" / "source-test"
    (story / "source-study").mkdir(parents=True)
    (story / "original" / "text").mkdir(parents=True)
    epub = story / "original" / "canonical.epub"
    with zipfile.ZipFile(epub, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
    digest = hashlib.sha256(epub.read_bytes()).hexdigest()
    (story / "original" / "text" / "canonical.md").write_text("Literary text.\n", encoding="utf-8")
    (story / "source-study" / "admission.yml").write_text(
        """composition_window:
  start: 1897
  end: 1899
editorial_mode: restrained_apparatus
sources:
  - id: canonical
    status: admitted
    authority: {tier: 1, story_world_canon: true, style_authority: primary}
    work: {title: Canonical, author: Author, first_published: 1895}
    analytical_roles: [frame]
    permitted_uses: [continuity]
    prohibited_uses: [none]
    rationale: Governing source.
    edition:
      publisher: Test
      homepage: https://example.test/canonical
      download_url: https://example.test/canonical.epub
      artifact_format: standard-ebooks-compatible-epub
      planned_path: original/canonical.epub
    selections: []
  - id: control
    status: proposed
    authority: {tier: 4, story_world_canon: false, style_authority: control}
    work: {title: Control, author: Other Author, first_published: 1898}
    analytical_roles: [period contrast]
    permitted_uses: [negative comparison]
    prohibited_uses: [style prescription]
    rationale: Detect generic period prose.
    edition:
      publisher: Test
      homepage: https://example.test/control
      download_url: https://example.test/control.epub
      artifact_format: project-gutenberg-epub
      planned_path: original/control.epub
    selections: []
""",
        encoding="utf-8",
    )
    (story / "original" / "sources.yml").write_text(
        f"""sources:
  - id: canonical
    role:
      tier: 1
      story_world_canon: true
      style_authority: primary
      primary_style_anchor: true
      secondary_style_anchor: false
      focus: Canonical frame.
      analytical_roles: [frame]
      permitted_uses: [continuity]
      prohibited_uses: [none]
    work: {{title: Canonical, author: Author, first_published: 1895}}
    edition:
      publisher: Test
      homepage: https://example.test/canonical
      download_url: https://example.test/canonical.epub
      upstream_release: test-release
      upstream_revision: test-revision
    retrieved: 2026-07-14
    files:
      epub: canonical.epub
      epub_sha256: {digest}
      markdown: text/canonical.md
    derivation:
      tool: Pandoc 3.10
      input: chapters
      writer: gfm-raw_html
      wrap: none
      filter: filters/remove-excluded-packaging-links.lua
    provenance: {{transcription: Test, page_scans: Test}}
    rights: {{source_text: Public domain test., edition_contributions: Test edition.}}
""",
        encoding="utf-8",
    )
    return story


def test_source_admission_writes_passing_report(tmp_path: Path) -> None:
    _write_fixture(tmp_path)

    result = check_source_admission(tmp_path, "source-test")

    assert result.ok
    report = result.report_path.read_text(encoding="utf-8")
    assert "Status: **PASS**" in report
    assert "| `canonical` | admitted | 1 | primary |" in report
    assert "| `control` | proposed | 4 | control |" in report


def test_source_admission_blocks_bad_checksum(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    (story / "original" / "canonical.epub").write_bytes(b"changed")

    result = check_source_admission(tmp_path, "source-test")

    assert not result.ok
    assert any("SHA-256 mismatch" in issue for issue in result.errors)


def test_source_admission_blocks_missing_retained_record(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    (story / "original" / "sources.yml").write_text("sources: []\n", encoding="utf-8")

    result = check_source_admission(tmp_path, "source-test")

    assert not result.ok
    assert any("has no retained source record" in issue for issue in result.errors)


def test_source_admission_blocks_proposed_artifact(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    (story / "original" / "control.epub").write_bytes(b"premature")

    result = check_source_admission(tmp_path, "source-test")

    assert not result.ok
    assert any("exists before corpus approval" in issue for issue in result.errors)


def test_source_admission_blocks_dangling_packaging_link(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    (story / "original" / "text" / "canonical.md").write_text(
        "Literary text.[1](endnotes.xhtml#note-1)\n",
        encoding="utf-8",
    )

    result = check_source_admission(tmp_path, "source-test")

    assert not result.ok
    assert any("excluded packaging link" in issue for issue in result.errors)
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
uv run --group dev pytest tests/test_source_admission.py -v
```

Expected: collection fails because `creative_writer.source_admission` does not exist.

- [ ] **Step 3: Implement admission validation and report rendering**

Create `src/creative_writer/source_admission.py` with these public types and functions:

```python
from __future__ import annotations

import hashlib
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory, load_yaml_model
from creative_writer.models import SourceStudyAdmission, SourcesRegistry

EXCLUDED_PACKAGING_LINK_PATTERN = re.compile(
    r"\]\([^)]*(?:endnotes|imprint|colophon|uncopyright)\.xhtml(?:[#?][^)]*)?\)",
    re.IGNORECASE,
)


@dataclass(slots=True)
class SourceAdmissionResult:
    story_slug: str
    report_path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _story_path(story_dir: Path, relative: str) -> Path:
    candidate = (story_dir / relative).resolve()
    base = story_dir.resolve()
    if candidate != base and base not in candidate.parents:
        raise CreativeWriterError(f"Source path escapes story directory: {relative}")
    return candidate


def _epub_integrity_error(path: Path) -> str | None:
    if not zipfile.is_zipfile(path):
        return "not a ZIP-based EPUB"
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
    if bad_member is not None:
        return f"corrupt archive member: {bad_member}"
    return None


def _render_report(
    admission: SourceStudyAdmission,
    result: SourceAdmissionResult,
) -> str:
    status = "PASS" if result.ok else "FAIL"
    counts = {
        name: sum(1 for source in admission.sources if source.status == name)
        for name in ("admitted", "approved", "proposed", "excluded")
    }
    lines = [
        "# Source Admission Report",
        "",
        f"- Story slug: `{result.story_slug}`",
        f"- Status: **{status}**",
        f"- Composition window: {admission.composition_window.start}-{admission.composition_window.end}",
        f"- Admitted: {counts['admitted']}",
        f"- Approved, awaiting retention: {counts['approved']}",
        f"- Proposed: {counts['proposed']}",
        f"- Excluded: {counts['excluded']}",
        "",
        "## Sources",
        "",
        "| ID | Status | Tier | Style authority | Work |",
        "|---|---|---:|---|---|",
    ]
    for source in admission.sources:
        lines.append(
            f"| `{source.id}` | {source.status} | {source.authority.tier} | "
            f"{source.authority.style_authority} | {source.work.title} |"
        )
    lines.extend(["", "## Blocking issues", ""])
    lines.extend(f"- {error}" for error in result.errors)
    if not result.errors:
        lines.append("- None.")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {warning}" for warning in result.warnings)
    if not result.warnings:
        lines.append("- None.")
    return "\n".join(lines) + "\n"


def check_source_admission(root: Path, slug: str) -> SourceAdmissionResult:
    story_dir = root / "stories" / slug
    admission_path = story_dir / "source-study" / "admission.yml"
    registry_path = story_dir / "original" / "sources.yml"
    report_path = root / "build" / slug / "reports" / "source-admission-report.md"
    ensure_directory(report_path.parent)
    result = SourceAdmissionResult(story_slug=slug, report_path=report_path)

    try:
        admission = load_yaml_model(admission_path, SourceStudyAdmission)
        registry = load_yaml_model(registry_path, SourcesRegistry)
    except CreativeWriterError as exc:
        result.errors.append(str(exc))
        report_path.write_text(
            "# Source Admission Report\n\n- Status: **FAIL**\n\n"
            f"## Blocking issues\n\n- {exc}\n",
            encoding="utf-8",
        )
        return result

    retained = {source.id: source for source in registry.sources}
    admitted_ids = {source.id for source in admission.sources if source.status == "admitted"}

    for source in admission.sources:
        try:
            planned_path = _story_path(story_dir, source.edition.planned_path)
        except CreativeWriterError as exc:
            result.errors.append(str(exc))
            continue
        if source.status == "proposed" and planned_path.exists():
            result.errors.append(
                f"`{source.id}` artifact exists before corpus approval: {planned_path}"
            )
        if source.status != "admitted":
            continue

        retained_source = retained.get(source.id)
        if retained_source is None:
            result.errors.append(f"Admitted source `{source.id}` has no retained source record.")
            continue

        try:
            epub_path = _story_path(story_dir / "original", retained_source.files.epub)
            markdown_path = _story_path(story_dir / "original", retained_source.files.markdown)
        except CreativeWriterError as exc:
            result.errors.append(str(exc))
            continue
        if epub_path != planned_path:
            result.errors.append(
                f"Retained EPUB path for `{source.id}` does not match the admission plan."
            )
        if not epub_path.exists():
            result.errors.append(f"Missing retained EPUB for `{source.id}`: {epub_path}")
        else:
            integrity_error = _epub_integrity_error(epub_path)
            if integrity_error:
                result.errors.append(
                    f"Invalid retained EPUB for `{source.id}`: {integrity_error}"
                )
            if _sha256(epub_path) != retained_source.files.epub_sha256:
                result.errors.append(f"SHA-256 mismatch for `{source.id}`: {epub_path}")
        if not markdown_path.exists():
            result.errors.append(f"Missing or empty derived Markdown for `{source.id}`: {markdown_path}")
        else:
            markdown = markdown_path.read_text(encoding="utf-8")
            if not markdown.strip():
                result.errors.append(f"Missing or empty derived Markdown for `{source.id}`: {markdown_path}")
            elif EXCLUDED_PACKAGING_LINK_PATTERN.search(markdown):
                result.errors.append(
                    f"Derived Markdown for `{source.id}` contains an excluded packaging link."
                )

    extra_retained = sorted(set(retained) - admitted_ids)
    for source_id in extra_retained:
        result.errors.append(
            f"Retained source `{source_id}` is not marked admitted in source-study/admission.yml."
        )

    report_path.write_text(_render_report(admission, result), encoding="utf-8")
    return result
```

- [ ] **Step 4: Wire the CLI and Make target**

In `src/creative_writer/cli.py`, add:

```python
from creative_writer.source_admission import check_source_admission
```

Then add a parser:

```python
source_admission = subparsers.add_parser(
    "source-admission",
    help="Validate a story-local forensic source admission record.",
)
source_admission.add_argument("--story", required=True, help="Story slug.")
```

Add the command branch before the final help fallback:

```python
if args.command == "source-admission":
    result = check_source_admission(root, args.story)
    print(f"Source admission report written to {result.report_path}")
    if result.ok:
        print("Source admission completed without blocking issues.")
        return 0
    print(f"Source admission failed with {len(result.errors)} blocking issue(s).", file=sys.stderr)
    return 1
```

In `Makefile`, add `source-admission` to `.PHONY` and add:

```make
source-admission:
	uv run creative-writer source-admission --story "$(STORY)"
```

- [ ] **Step 5: Run focused tests and verify GREEN**

Run:

```bash
uv run --group dev pytest tests/test_source_models.py tests/test_source_admission.py -v
```

Expected: all source admission tests pass.

- [ ] **Step 6: Commit the admission command**

```bash
git add Makefile src/creative_writer/cli.py src/creative_writer/source_admission.py tests/test_source_admission.py
git commit -m "Add source admission validation"
```

---

### Task 3: Record the Exact Proposed Corpus

**Files:**
- Create: `stories/time-expedition/source-study/README.md`
- Create: `stories/time-expedition/source-study/method.md`
- Create: `stories/time-expedition/source-study/admission.yml`
- Modify: `stories/time-expedition/original/sources.yml`
- Test: `tests/test_source_admission.py`

**Interfaces:**
- Consumes: the schema and command from Tasks 1-2.
- Produces: two admitted sources, two approved fixed additions, and seven proposed source artifacts covering four Wells short stories, two Wells nonfiction witnesses, and four period-control authors.

- [ ] **Step 1: Add a failing real-story admission smoke test**

Append to `tests/test_source_admission.py`:

```python
def test_time_expedition_admission_passes() -> None:
    root = Path(__file__).resolve().parents[1]

    result = check_source_admission(root, "time-expedition")

    assert result.ok
    report = result.report_path.read_text(encoding="utf-8")
    assert "- Admitted: 2" in report
    assert "- Approved, awaiting retention: 2" in report
    assert "- Proposed: 7" in report
    assert "| `the-time-machine` | admitted | 1 | primary |" in report
    assert "| `the-island-of-doctor-moreau` | approved | 2 | bounded |" in report
    assert "| `the-british-barbarians` | proposed | 4 | control |" in report
```

- [ ] **Step 2: Run the real-story test and verify RED**

Run:

```bash
uv run --group dev pytest tests/test_source_admission.py::test_time_expedition_admission_passes -v
```

Expected: FAIL because `source-study/admission.yml` does not exist and the retained registry has not been migrated to the strict schema.

- [ ] **Step 3: Create the exact admission record**

Create `stories/time-expedition/source-study/admission.yml` with eleven records:

```yaml
composition_window:
  start: 1897
  end: 1899
editorial_mode: restrained_apparatus
sources:
  - id: the-time-machine
    status: admitted
    authority: {tier: 1, story_world_canon: true, style_authority: primary}
    work: {title: "The Time Machine", author: "H. G. Wells", first_published: 1895}
    analytical_roles: ["continuity", "frame architecture", "reported first-person account", "speculative method"]
    permitted_uses: ["all Time Expedition continuity", "primary voice evidence", "frame and Traveller evidence"]
    prohibited_uses: ["later-adaptation material", "unsupported generalisation from one passage"]
    rationale: "The sole story-world canon and governing style authority."
    edition:
      publisher: "Standard Ebooks"
      homepage: "https://standardebooks.org/ebooks/h-g-wells/the-time-machine"
      download_url: "https://standardebooks.org/ebooks/h-g-wells/the-time-machine/downloads/h-g-wells_the-time-machine.epub?source=download"
      artifact_format: standard-ebooks-compatible-epub
      planned_path: "original/h-g-wells_the-time-machine.epub"
    selections: []

  - id: the-invisible-man
    status: admitted
    authority: {tier: 2, story_world_canon: false, style_authority: secondary}
    work: {title: "The Invisible Man", author: "H. G. Wells", first_published: 1897}
    analytical_roles: ["sustained dialogue", "social register", "comic friction", "crowd response"]
    permitted_uses: ["dialogue and social-style comparison"]
    prohibited_uses: ["Time Expedition continuity", "Traveller characterisation", "frame architecture"]
    rationale: "A close Wells witness for dialogue and social scenes only."
    edition:
      publisher: "Standard Ebooks"
      homepage: "https://standardebooks.org/ebooks/h-g-wells/the-invisible-man"
      download_url: "https://standardebooks.org/ebooks/h-g-wells/the-invisible-man/downloads/h-g-wells_the-invisible-man.epub?source=download"
      artifact_format: standard-ebooks-compatible-epub
      planned_path: "original/h-g-wells_the-invisible-man.epub"
    selections: []

  - id: the-island-of-doctor-moreau
    status: approved
    authority: {tier: 2, story_world_canon: false, style_authority: bounded}
    work: {title: "The Island of Doctor Moreau", author: "H. G. Wells", first_published: 1896}
    analytical_roles: ["retrospective first-person narration", "scientific argument", "moral pressure", "dialogue under stress"]
    permitted_uses: ["bounded narrative and scientific-style comparison"]
    prohibited_uses: ["Time Expedition continuity", "Moreau characters or inventions", "override of The Time Machine"]
    rationale: "The closest period witness for retrospective scientific adventure and observed horror."
    edition:
      publisher: "Standard Ebooks"
      homepage: "https://standardebooks.org/ebooks/h-g-wells/the-island-of-doctor-moreau"
      download_url: "https://standardebooks.org/ebooks/h-g-wells/the-island-of-doctor-moreau/downloads/h-g-wells_the-island-of-doctor-moreau.epub?source=download"
      artifact_format: standard-ebooks-compatible-epub
      planned_path: "original/h-g-wells_the-island-of-doctor-moreau.epub"
    selections: []

  - id: the-war-of-the-worlds
    status: approved
    authority: {tier: 2, story_world_canon: false, style_authority: bounded}
    work: {title: "The War of the Worlds", author: "H. G. Wells", first_published: 1898}
    analytical_roles: ["catastrophe", "landscape observation", "public behaviour", "evidence-to-speculation movement"]
    permitted_uses: ["bounded catastrophe and observational-style comparison"]
    prohibited_uses: ["Time Expedition continuity", "Martian inventions", "override of The Time Machine"]
    rationale: "A composition-window witness for catastrophe, technical observation, and reflective aftermath."
    edition:
      publisher: "Standard Ebooks"
      homepage: "https://standardebooks.org/ebooks/h-g-wells/the-war-of-the-worlds"
      download_url: "https://standardebooks.org/ebooks/h-g-wells/the-war-of-the-worlds/downloads/h-g-wells_the-war-of-the-worlds.epub?source=download"
      artifact_format: standard-ebooks-compatible-epub
      planned_path: "original/h-g-wells_the-war-of-the-worlds.epub"
    selections: []

  - id: selected-short-fiction
    status: proposed
    authority: {tier: 2, story_world_canon: false, style_authority: bounded}
    work: {title: "Selected Short Fiction", author: "H. G. Wells", first_published: null}
    analytical_roles: ["short-form architecture", "testimony", "biological danger", "scientific mystery", "cosmic catastrophe"]
    permitted_uses: ["bounded short-story and scene comparison"]
    prohibited_uses: ["Time Expedition continuity", "unselected stories", "override of The Time Machine"]
    rationale: "Four tightly dated stories supply short-form Wells evidence without admitting the entire 1894-1909 collection."
    edition:
      publisher: "Standard Ebooks"
      homepage: "https://standardebooks.org/ebooks/h-g-wells/short-fiction"
      download_url: "https://standardebooks.org/ebooks/h-g-wells/short-fiction/downloads/h-g-wells_short-fiction.epub?source=download"
      artifact_format: standard-ebooks-compatible-epub
      planned_path: "original/h-g-wells_short-fiction.epub"
    selections:
      - id: the-plattner-story
        title: "The Plattner Story"
        first_published: 1896
        analytical_roles: ["frame testimony", "epistemic uncertainty", "other-world description"]
      - id: the-sea-raiders
        title: "The Sea Raiders"
        first_published: 1896
        analytical_roles: ["biological observation", "compressed danger", "action"]
      - id: the-crystal-egg
        title: "The Crystal Egg"
        first_published: 1897
        analytical_roles: ["observational mystery", "scientific object", "speculative inference"]
      - id: the-star
        title: "The Star"
        first_published: 1897
        analytical_roles: ["catastrophe", "deep-scale description", "global montage"]

  - id: certain-personal-matters
    status: proposed
    authority: {tier: 3, story_world_canon: false, style_authority: bounded}
    work: {title: "Certain Personal Matters", author: "H. G. Wells", first_published: 1897}
    analytical_roles: ["essay voice", "humour", "conversation", "microscopic observation"]
    permitted_uses: ["nonfiction comparison for explanation, humour, and period idiom"]
    prohibited_uses: ["fictional continuity", "direct prescription of narrative voice"]
    rationale: "A composition-window nonfiction witness to Wells's conversational and explanatory habits."
    edition:
      publisher: "Project Gutenberg"
      homepage: "https://www.gutenberg.org/ebooks/17508"
      download_url: "https://www.gutenberg.org/ebooks/17508.epub.noimages"
      artifact_format: project-gutenberg-epub
      planned_path: "original/h-g-wells_certain-personal-matters.epub"
    selections: []

  - id: text-book-of-biology-part-1
    status: proposed
    authority: {tier: 3, story_world_canon: false, style_authority: bounded}
    work: {title: "Text Book of Biology, Part 1: Vertebrata", author: "H. G. Wells", first_published: 1893}
    analytical_roles: ["biological terminology", "instructional exposition", "comparison and classification"]
    permitted_uses: ["scientific vocabulary and explanatory-method comparison"]
    prohibited_uses: ["fictional continuity", "direct prescription of narrative voice", "post-1890s scientific knowledge"]
    rationale: "A formative scientific witness for the vocabulary and habits Wells brought to late-1890s fiction."
    edition:
      publisher: "Project Gutenberg"
      homepage: "https://www.gutenberg.org/ebooks/21781"
      download_url: "https://www.gutenberg.org/ebooks/21781.epub.noimages"
      artifact_format: project-gutenberg-epub
      planned_path: "original/h-g-wells_text-book-of-biology-part-1.epub"
    selections: []

  - id: the-british-barbarians
    status: proposed
    authority: {tier: 4, story_world_canon: false, style_authority: control}
    work: {title: "The British Barbarians", author: "Grant Allen", first_published: 1895}
    analytical_roles: ["scientific-romance control", "time-visitor premise", "social satire"]
    permitted_uses: ["negative period and genre comparison"]
    prohibited_uses: ["style prescription", "Time Expedition continuity", "phrase borrowing"]
    rationale: "Distinguishes Wells from a nearby scientific-romance treatment of time displacement and society."
    edition:
      publisher: "Project Gutenberg"
      homepage: "https://www.gutenberg.org/ebooks/4340"
      download_url: "https://www.gutenberg.org/ebooks/4340.epub.images"
      artifact_format: project-gutenberg-epub
      planned_path: "original/grant-allen_the-british-barbarians.epub"
    selections: []

  - id: a-desert-drama
    status: proposed
    authority: {tier: 4, story_world_canon: false, style_authority: control}
    work: {title: "A Desert Drama", author: "Arthur Conan Doyle", first_published: 1898}
    analytical_roles: ["adventure control", "group dialogue", "danger pacing", "social register"]
    permitted_uses: ["negative period and adventure comparison"]
    prohibited_uses: ["style prescription", "Time Expedition continuity", "phrase borrowing"]
    rationale: "A date-matched control for competent ensemble dialogue and adventure pressure."
    edition:
      publisher: "Project Gutenberg"
      homepage: "https://www.gutenberg.org/ebooks/21768"
      download_url: "https://www.gutenberg.org/ebooks/21768.epub.noimages"
      artifact_format: project-gutenberg-epub
      planned_path: "original/arthur-conan-doyle_a-desert-drama.epub"
    selections: []

  - id: the-days-work
    status: proposed
    authority: {tier: 4, story_world_canon: false, style_authority: control}
    work: {title: "The Day's Work", author: "Rudyard Kipling", first_published: 1898}
    analytical_roles: ["technical-work control", "professional dialogue", "imperial register", "machinery"]
    permitted_uses: ["negative period, technical, and professional-register comparison"]
    prohibited_uses: ["style prescription", "Time Expedition continuity", "phrase borrowing"]
    rationale: "A date-matched control for technical competence, work, and a strongly non-Wellsian period voice."
    edition:
      publisher: "Project Gutenberg"
      homepage: "https://www.gutenberg.org/ebooks/2569"
      download_url: "https://www.gutenberg.org/ebooks/2569.epub.images"
      artifact_format: project-gutenberg-epub
      planned_path: "original/rudyard-kipling_the-days-work.epub"
    selections: []

  - id: the-beetle
    status: proposed
    authority: {tier: 4, story_world_canon: false, style_authority: control}
    work: {title: "The Beetle: A Mystery", author: "Richard Marsh", first_published: 1897}
    analytical_roles: ["sensational-fiction control", "multiple narrators", "London danger", "horror escalation"]
    permitted_uses: ["negative period, sensational, and horror comparison"]
    prohibited_uses: ["style prescription", "Time Expedition continuity", "phrase borrowing"]
    rationale: "A date-matched control for the sensational register that the anthology must not accidentally adopt."
    edition:
      publisher: "Project Gutenberg"
      homepage: "https://www.gutenberg.org/ebooks/5164"
      download_url: "https://www.gutenberg.org/ebooks/5164.epub.noimages"
      artifact_format: project-gutenberg-epub
      planned_path: "original/richard-marsh_the-beetle.epub"
    selections: []
```

- [ ] **Step 4: Migrate the two retained source records to the strict authority schema**

In each existing record in `stories/time-expedition/original/sources.yml`:

- add `tier` and `style_authority` under `role`;
- add `analytical_roles`, `permitted_uses`, and `prohibited_uses` using the exact values from `admission.yml`;
- rename `rights.standard_ebooks_contributions` to `rights.edition_contributions`.

For *The Time Machine* use:

```yaml
      tier: 1
      style_authority: primary
```

For *The Invisible Man* use:

```yaml
      tier: 2
      style_authority: secondary
```

Retain their existing booleans, fingerprints, revision IDs, derivation data,
and prose exactly.

- [ ] **Step 5: Create the Phase 1 study README and method**

Create `stories/time-expedition/source-study/README.md` explaining:

- this directory stores evidence and method, never manuscript prose;
- `admission.yml` is the exact corpus gate;
- `original/sources.yml` contains only retained, admitted artifacts;
- approved sources may be acquired; proposed sources may not;
- the generated review surface is `build/time-expedition/reports/source-admission-report.md`;
- detailed analysis is blocked until the human approves that report.

Create `stories/time-expedition/source-study/method.md` with these sections and settled content:

```markdown
# Forensic Source Study Method

## Target

Reconstruct H. G. Wells's fictional practice circa 1897-1899 for a recovered-manuscript anthology, without reducing it to generic Victorian prose.

## Authority

The five-tier hierarchy in the approved design governs every claim. *The Time Machine* alone supplies continuity and primary voice authority. Period controls are negative evidence only.

## Admission rule

Only records marked `admitted` may be analysed. `approved` identifies the two fixed Wells additions awaiting reproducible retention. `proposed` records remain absent from `original/` until human review.

## Later analytical method

The next phase will preserve works separately, retain locators, calculate per-work measurements, close-read representative and contrary passages, record evidence and counterexamples, and validate the resulting profile against held-out Wells passages and period controls.

## Current prohibition

This phase performs no quantitative profile, close-reading findings, Permian research, narrative planning, or manuscript drafting.
```

- [ ] **Step 6: Run the real-story admission test and command**

Run:

```bash
uv run --group dev pytest tests/test_source_admission.py::test_time_expedition_admission_passes -v
make source-admission STORY=time-expedition
```

Expected:

- test passes;
- command exits `0`;
- report says `Admitted: 2`, `Approved, awaiting retention: 2`, and `Proposed: 7`;
- report has no blocking issues.

- [ ] **Step 7: Confirm proposed artifacts remain absent**

Run:

```bash
for path in \
  stories/time-expedition/original/h-g-wells_short-fiction.epub \
  stories/time-expedition/original/h-g-wells_certain-personal-matters.epub \
  stories/time-expedition/original/h-g-wells_text-book-of-biology-part-1.epub \
  stories/time-expedition/original/grant-allen_the-british-barbarians.epub \
  stories/time-expedition/original/arthur-conan-doyle_a-desert-drama.epub \
  stories/time-expedition/original/rudyard-kipling_the-days-work.epub \
  stories/time-expedition/original/richard-marsh_the-beetle.epub
do
  test ! -e "$path"
done
```

Expected: every check exits `0`.

- [ ] **Step 8: Commit the exact admission proposal**

```bash
git add stories/time-expedition/source-study stories/time-expedition/original/sources.yml tests/test_source_admission.py
git commit -m "Define Wells forensic study corpus"
```

---

### Task 4: Retain the Two Fixed Wells Witnesses

**Files:**
- Create: `stories/time-expedition/original/h-g-wells_the-island-of-doctor-moreau.epub`
- Create: `stories/time-expedition/original/h-g-wells_the-war-of-the-worlds.epub`
- Create: `stories/time-expedition/original/text/the-island-of-doctor-moreau.md`
- Create: `stories/time-expedition/original/text/the-war-of-the-worlds.md`
- Modify: `stories/time-expedition/original/sources.yml`
- Modify: `stories/time-expedition/original/README.md`
- Modify: `stories/time-expedition/source-study/admission.yml`
- Modify: `tests/test_time_expedition_original.py`
- Modify: `tests/test_source_admission.py`

**Interfaces:**
- Consumes: the current Standard Ebooks compatible EPUB endpoints and the existing packaging-link Lua filter.
- Produces: four admitted Wells sources, with exact local fingerprints and reproducible clean Markdown.

- [ ] **Step 1: Extend the source-boundary regression test before acquisition**

Replace the fixed two-file `source_paths` list in `tests/test_time_expedition_original.py` with:

```python
source_paths = [
    source_dir / "the-time-machine.md",
    source_dir / "the-invisible-man.md",
    source_dir / "the-island-of-doctor-moreau.md",
    source_dir / "the-war-of-the-worlds.md",
]
```

Append exact archive fingerprint assertions:

```python
def test_time_expedition_fixed_wells_epubs_match_pinned_hashes() -> None:
    root = Path(__file__).resolve().parents[1]
    original = root / "stories" / "time-expedition" / "original"
    expected = {
        "h-g-wells_the-island-of-doctor-moreau.epub": "c1805bbc79b423716520a24a016ee1feeaa970a9f74f1d4bac4d6c8bccc66c2d",
        "h-g-wells_the-war-of-the-worlds.epub": "56b57347a63fbd52a6a94b6500e5ff1c0a49a266e525223fef08789cb1ad4f8f",
    }
    for filename, digest in expected.items():
        assert hashlib.sha256((original / filename).read_bytes()).hexdigest() == digest
```

Add `import hashlib` at the top.

- [ ] **Step 2: Run the source tests and verify RED**

Run:

```bash
uv run --group dev pytest tests/test_time_expedition_original.py -v
```

Expected: FAIL because the two approved source artifacts and Markdown files do not yet exist.

- [ ] **Step 3: Download and verify both EPUBs in a temporary directory**

Run:

```zsh
tmpdir=$(mktemp -d /tmp/wells-fixed-sources.XXXXXX)
curl --fail --location --retry 3 --silent --show-error \
  --output "$tmpdir/moreau.epub" \
  "https://standardebooks.org/ebooks/h-g-wells/the-island-of-doctor-moreau/downloads/h-g-wells_the-island-of-doctor-moreau.epub?source=download"
curl --fail --location --retry 3 --silent --show-error \
  --output "$tmpdir/war.epub" \
  "https://standardebooks.org/ebooks/h-g-wells/the-war-of-the-worlds/downloads/h-g-wells_the-war-of-the-worlds.epub?source=download"
file "$tmpdir/moreau.epub" "$tmpdir/war.epub"
unzip -t "$tmpdir/moreau.epub"
unzip -t "$tmpdir/war.epub"
shasum -a 256 "$tmpdir/moreau.epub" "$tmpdir/war.epub"
```

Expected:

- both files are EPUB documents;
- both ZIP checks end with `No errors detected in compressed data`;
- Moreau SHA-256 is `c1805bbc79b423716520a24a016ee1feeaa970a9f74f1d4bac4d6c8bccc66c2d`;
- War SHA-256 is `56b57347a63fbd52a6a94b6500e5ff1c0a49a266e525223fef08789cb1ad4f8f`.

If either fingerprint differs, stop and inspect the upstream colophon and
revision instead of changing the expected value silently.

- [ ] **Step 4: Install and derive clean Markdown**

Continue in the same `zsh` shell:

```zsh
mv "$tmpdir/moreau.epub" stories/time-expedition/original/h-g-wells_the-island-of-doctor-moreau.epub
mv "$tmpdir/war.epub" stories/time-expedition/original/h-g-wells_the-war-of-the-worlds.epub
unzip -q stories/time-expedition/original/h-g-wells_the-island-of-doctor-moreau.epub -d "$tmpdir/moreau"
unzip -q stories/time-expedition/original/h-g-wells_the-war-of-the-worlds.epub -d "$tmpdir/war"
filter=stories/time-expedition/original/filters/remove-excluded-packaging-links.lua
moreau_chapters=("$tmpdir"/moreau/epub/text/chapter-{1..22}.xhtml)
pandoc "${moreau_chapters[@]}" \
  --from=html --to=gfm-raw_html --wrap=none --lua-filter="$filter" \
  --output=stories/time-expedition/original/text/the-island-of-doctor-moreau.md
war_book_one=("$tmpdir/war/epub/text/book-1.xhtml" "$tmpdir"/war/epub/text/chapter-1-{1..17}.xhtml)
war_book_two=("$tmpdir/war/epub/text/book-2.xhtml" "$tmpdir"/war/epub/text/chapter-2-{1..10}.xhtml)
pandoc "${war_book_one[@]}" "${war_book_two[@]}" \
  --from=html --to=gfm-raw_html --wrap=none --lua-filter="$filter" \
  --output=stories/time-expedition/original/text/the-war-of-the-worlds.md
rm -rf "$tmpdir"
```

- [ ] **Step 5: Add retained source records and mark both admitted**

Append complete `sources.yml` records using:

- Moreau release `2026-06-30T02:48:51Z`, revision `032c5a6`, transcription `Project Gutenberg ebook 159`, page scans `Internet Archive islandofdoctormo00welluoft`;
- War release `2026-06-30T02:48:51Z`, revision `99c7047`, transcription `Project Gutenberg ebook 36`, page scans `HathiTrust record 012293655`;
- retrieval date `2026-07-14`;
- the exact fingerprints from Step 3;
- the roles, permitted uses, and prohibited uses from `source-study/admission.yml`;
- `primary_style_anchor: false` and `secondary_style_anchor: true` for both;
- `edition_contributions: "Dedicated to the worldwide public domain under CC0 1.0 by Standard Ebooks contributors."`.

Change the two admission statuses from `approved` to `admitted`.

- [ ] **Step 6: Update the corpus README**

Update `original/README.md` so the authority map and file list include both
new witnesses, their bounded roles, and their exact reproduction commands.
Retain the rule that *The Time Machine* governs all conflicts. State that
proposed short fiction, nonfiction, and controls remain outside `original/`
until the human corpus review.

- [ ] **Step 7: Extend the real-story report assertions**

Change `test_time_expedition_admission_passes` to expect:

```python
assert "- Admitted: 4" in report
assert "- Approved, awaiting retention: 0" in report
assert "- Proposed: 7" in report
assert "| `the-island-of-doctor-moreau` | admitted | 2 | bounded |" in report
assert "| `the-war-of-the-worlds` | admitted | 2 | bounded |" in report
```

- [ ] **Step 8: Verify structure, boundaries, and reproducibility**

Run:

```bash
test "$(rg -c '^## (I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX|XXI|XXII)$' stories/time-expedition/original/text/the-island-of-doctor-moreau.md)" -eq 22
test "$(rg -c '^## Book (I|II)$' stories/time-expedition/original/text/the-war-of-the-worlds.md)" -eq 2
test "$(rg -c '^### (I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII)$' stories/time-expedition/original/text/the-war-of-the-worlds.md)" -eq 27
rg -q '^In the Dingey of the \*Lady Vain\*' stories/time-expedition/original/text/the-island-of-doctor-moreau.md
rg -q '^And so, in hope and solitude, my story ends\.' stories/time-expedition/original/text/the-island-of-doctor-moreau.md
rg -q '^The Eve of the War$' stories/time-expedition/original/text/the-war-of-the-worlds.md
rg -q "^And strangest of all is it to hold my wife’s hand again" stories/time-expedition/original/text/the-war-of-the-worlds.md
! rg -q '^## (Imprint|Endnotes|Colophon|Uncopyright)$|\]\([^)]*(endnotes|imprint|colophon|uncopyright)\.xhtml' stories/time-expedition/original/text/the-island-of-doctor-moreau.md stories/time-expedition/original/text/the-war-of-the-worlds.md
test "$(wc -c < stories/time-expedition/original/text/the-island-of-doctor-moreau.md)" -eq 242027
test "$(wc -c < stories/time-expedition/original/text/the-war-of-the-worlds.md)" -eq 340243
```

Then regenerate both files to a temporary directory with the exact Step 4
commands and use `cmp` to prove byte-for-byte identity.

- [ ] **Step 9: Run all Phase 1 verification**

Run:

```bash
make source-admission STORY=time-expedition
make check STORY=time-expedition
make stats STORY=time-expedition
rg -n 'Total manuscript words: 0|Chapters with manuscript words: 0' build/time-expedition/reports/ms-statistics.md
! rg -q '42,991|59,885|Original Reference Corpus' build/time-expedition/reports/ms-statistics.md
make test
git diff --check
```

Expected:

- admission report passes with four admitted and seven proposed sources;
- story check passes;
- manuscript words remain zero and source words do not leak into statistics;
- the full repository test suite passes;
- no whitespace errors are reported.

- [ ] **Step 10: Commit the fixed Wells additions**

```bash
git add \
  stories/time-expedition/original \
  stories/time-expedition/source-study/admission.yml \
  tests/test_time_expedition_original.py \
  tests/test_source_admission.py
git commit -m "Retain Wells forensic study anchors"
```

---

### Task 5: Final Phase 1 Review Gate

**Files:**
- Generated: `build/time-expedition/reports/source-admission-report.md`
- No tracked file changes are expected.

**Interfaces:**
- Consumes: all four implementation commits.
- Produces: the human review surface required before any proposed source is downloaded or analysed.

- [ ] **Step 1: Run controller-owned final verification**

Run fresh from the repository root:

```bash
make source-admission STORY=time-expedition
make check STORY=time-expedition
make stats STORY=time-expedition
make test
shasum -a 256 \
  stories/time-expedition/original/h-g-wells_the-time-machine.epub \
  stories/time-expedition/original/h-g-wells_the-invisible-man.epub \
  stories/time-expedition/original/h-g-wells_the-island-of-doctor-moreau.epub \
  stories/time-expedition/original/h-g-wells_the-war-of-the-worlds.epub
git diff --check
git status --short
```

Expected:

- source admission, story check, statistics, and all tests pass;
- all four fingerprints match `original/sources.yml`;
- worktree is clean.

- [ ] **Step 2: Review the generated admission report**

Confirm the report lists:

- admitted: *The Time Machine*, *The Invisible Man*, *The Island of Doctor Moreau*, *The War of the Worlds*;
- proposed Wells selections: *The Plattner Story*, *The Sea Raiders*, *The Crystal Egg*, *The Star*;
- proposed Wells nonfiction: *Certain Personal Matters*, *Text Book of Biology, Part 1*;
- proposed controls: Grant Allen, Conan Doyle, Kipling, and Richard Marsh;
- Tier 4 controls have no positive style or continuity authority;
- no blocking issues.

- [ ] **Step 3: Stop for human corpus approval**

Present `build/time-expedition/reports/source-admission-report.md` and
`stories/time-expedition/source-study/admission.yml` to the user. Do not
download the seven proposed source artifacts, build metrics, perform detailed
close reading, or edit the operational style guide until the user approves
the admitted corpus.
