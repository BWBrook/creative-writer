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
      public_domain_context: Public-domain Wells text in a Standard Ebooks edition.
      textual_limitations: The edition is a modern transcription, not a first-edition facsimile.
      editorial_normalisation: Standard Ebooks house style may regularise presentation.
      variant_concerns: Serial and book witnesses may differ and require later comparison.
    selections: []
"""


def test_source_study_admission_parses_valid_yaml(tmp_path: Path) -> None:
    path = tmp_path / "admission.yml"
    path.write_text(VALID_ADMISSION, encoding="utf-8")

    admission = load_yaml_model(path, SourceStudyAdmission)

    assert admission.composition_window.start == 1897
    assert admission.sources[0].authority.style_authority == "primary"
    assert admission.sources[0].edition.public_domain_context.startswith(
        "Public-domain Wells text"
    )


@pytest.mark.parametrize(
    "field",
    [
        "public_domain_context",
        "textual_limitations",
        "editorial_normalisation",
        "variant_concerns",
    ],
)
def test_source_study_admission_requires_each_edition_risk_field(
    tmp_path: Path,
    field: str,
) -> None:
    path = tmp_path / "admission.yml"
    lines = [
        line
        for line in VALID_ADMISSION.splitlines()
        if not line.startswith(f"      {field}:")
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(CreativeWriterError, match=field):
        load_yaml_model(path, SourceStudyAdmission)


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
