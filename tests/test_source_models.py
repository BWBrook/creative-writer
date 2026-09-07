from __future__ import annotations

from pathlib import Path

import pytest

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import load_yaml_model
from creative_writer.models import SourcesRegistry


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


def _retained_record_yaml(derived: str) -> str:
    return f"""sources:
  - id: the-time-machine
    role:
      tier: 1
      story_world_canon: true
      style_authority: primary
      primary_style_anchor: true
      secondary_style_anchor: false
      focus: Canonical frame.
      analytical_roles: [canonical frame]
      permitted_uses: [continuity]
      prohibited_uses: [none]
    work: {{title: The Time Machine, author: H. G. Wells, first_published: 1895}}
    edition:
      publisher: Standard Ebooks
      homepage: https://example.test/book
      download_url: https://example.test/book.epub
      upstream_release: test-release
      upstream_revision: test-revision
    retrieved: "2026-07-14"
    files:
      epub: book.epub
      epub_sha256: {'a' * 64}
{derived}
    derivation:
      tool: Pandoc 3.10
      input: Explicit XHTML inputs.
      writer: gfm-raw_html
      wrap: none
      filter: filters/remove-excluded-packaging-links.lua
    provenance: {{transcription: Test transcription, page_scans: Test scans}}
    rights: {{source_text: Public domain test fixture., edition_contributions: Test edition statement.}}
"""


def test_retained_full_work_requires_markdown_fingerprint(tmp_path: Path) -> None:
    path = tmp_path / "sources.yml"
    path.write_text(
        _retained_record_yaml(
            """      markdown: text/book.md
      markdown_sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    selections: []"""
        ),
        encoding="utf-8",
    )
    registry = load_yaml_model(path, SourcesRegistry)
    assert registry.sources[0].files.markdown == "text/book.md"
    assert registry.sources[0].selections == []


def test_retained_omnibus_parses_fingerprinted_selections(tmp_path: Path) -> None:
    path = tmp_path / "sources.yml"
    path.write_text(
        _retained_record_yaml(
            """    selections:
      - id: the-star
        title: The Star
        first_published: 1897
        input: epub/text/the-star.xhtml
        markdown: text/selected-short-fiction/the-star.md
        markdown_sha256: cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"""
        ),
        encoding="utf-8",
    )
    registry = load_yaml_model(path, SourcesRegistry)
    assert registry.sources[0].files.markdown is None
    assert registry.sources[0].selections[0].input == "epub/text/the-star.xhtml"


@pytest.mark.parametrize(
    ("derived", "message"),
    [
        ("    selections: []", "exactly one derived-text shape"),
        (
            """      markdown: text/book.md
    selections: []""",
            "markdown and markdown_sha256 must be supplied together",
        ),
        (
            """      markdown_sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    selections: []""",
            "markdown and markdown_sha256 must be supplied together",
        ),
        (
            """      markdown: text/book.md
      markdown_sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    selections:
      - id: the-star
        title: The Star
        first_published: 1897
        input: epub/text/the-star.xhtml
        markdown: text/selected-short-fiction/the-star.md
        markdown_sha256: cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc""",
            "exactly one derived-text shape",
        ),
    ],
)
def test_retained_source_rejects_invalid_derived_shape(
    tmp_path: Path,
    derived: str,
    message: str,
) -> None:
    path = tmp_path / "sources.yml"
    path.write_text(_retained_record_yaml(derived), encoding="utf-8")
    with pytest.raises(CreativeWriterError, match=message):
        load_yaml_model(path, SourcesRegistry)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "input",
            "../the-star.xhtml",
            "selection input must be a relative XHTML member",
        ),
        (
            "input",
            "/epub/text/the-star.xhtml",
            "selection input must be a relative XHTML member",
        ),
        (
            "input",
            "C:/epub/text/the-star.xhtml",
            "selection input must be a relative XHTML member",
        ),
        (
            "input",
            "epub/text/./the-star.xhtml",
            "selection input must be a relative XHTML member",
        ),
        (
            "input",
            "epub//text/the-star.xhtml",
            "selection input must be a relative XHTML member",
        ),
        (
            "input",
            "epub\\text\\..\\..\\the-star.xhtml",
            "selection input must be a relative XHTML member",
        ),
        (
            "input",
            "epub/text/the-star.md",
            "selection input must be a relative XHTML member",
        ),
        ("markdown", "../the-star.md", "selection markdown must be below text/"),
        (
            "markdown",
            "/text/the-star.md",
            "selection markdown must be below text/",
        ),
        (
            "markdown",
            "other/the-star.md",
            "selection markdown must be below text/",
        ),
        (
            "markdown",
            "text/./story.md",
            "selection markdown must be below text/",
        ),
        (
            "markdown",
            "text//the-star.md",
            "selection markdown must be below text/",
        ),
        (
            "markdown",
            "text/..\\..\\the-star.md",
            "selection markdown must be below text/",
        ),
    ],
)
def test_retained_selection_rejects_invalid_paths(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    derived = """    selections:
      - id: the-star
        title: The Star
        first_published: 1897
        input: epub/text/the-star.xhtml
        markdown: text/selected-short-fiction/the-star.md
        markdown_sha256: cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"""
    old_value = (
        "epub/text/the-star.xhtml"
        if field == "input"
        else "text/selected-short-fiction/the-star.md"
    )
    derived = derived.replace(f"{field}: {old_value}", f"{field}: {value}")
    path = tmp_path / "sources.yml"
    path.write_text(_retained_record_yaml(derived), encoding="utf-8")
    with pytest.raises(CreativeWriterError, match=message):
        load_yaml_model(path, SourcesRegistry)


@pytest.mark.parametrize(
    ("second_id", "second_input", "second_markdown", "message"),
    [
        (
            "the-star",
            "epub/text/second-story.xhtml",
            "text/selected-short-fiction/second.md",
            "retained selection IDs must be unique",
        ),
        (
            "second-story",
            "epub/text/the-star.xhtml",
            "text/selected-short-fiction/second.md",
            "retained selection input paths must be unique",
        ),
        (
            "second-story",
            "epub/text/second-story.xhtml",
            "text/selected-short-fiction/the-star.md",
            "retained selection Markdown paths must be unique",
        ),
    ],
)
def test_retained_source_rejects_duplicate_selection_identity(
    tmp_path: Path,
    second_id: str,
    second_input: str,
    second_markdown: str,
    message: str,
) -> None:
    derived = f"""    selections:
      - id: the-star
        title: The Star
        first_published: 1897
        input: epub/text/the-star.xhtml
        markdown: text/selected-short-fiction/the-star.md
        markdown_sha256: {'c' * 64}
      - id: {second_id}
        title: Second Story
        first_published: 1898
        input: {second_input}
        markdown: {second_markdown}
        markdown_sha256: {'d' * 64}"""
    path = tmp_path / "sources.yml"
    path.write_text(_retained_record_yaml(derived), encoding="utf-8")
    with pytest.raises(CreativeWriterError, match=message):
        load_yaml_model(path, SourcesRegistry)


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
      markdown_sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
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
