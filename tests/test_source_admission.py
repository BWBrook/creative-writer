from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest
import yaml

from creative_writer.exceptions import CreativeWriterError
from creative_writer.source_admission import check_source_admission


def _write_minimal_epub(
    path: Path,
    *,
    mimetype: str = "application/epub+zip",
    container: str | None = None,
    package_path: str | None = "EPUB/package.opf",
) -> None:
    if container is None and package_path is not None:
        container = f"""<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
    <rootfile full-path="{package_path}" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", mimetype)
        if container is not None:
            archive.writestr("META-INF/container.xml", container)
        if package_path is not None:
            archive.writestr(
                package_path,
                """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="id">fixture</dc:identifier>
    <dc:title>Fixture</dc:title>
    <dc:language>en</dc:language>
  </metadata>
  <manifest/>
  <spine/>
</package>
""",
            )


def _write_fixture(root: Path) -> Path:
    story = root / "stories" / "source-test"
    (story / "source-study").mkdir(parents=True)
    (story / "original" / "text").mkdir(parents=True)
    epub = story / "original" / "canonical.epub"
    _write_minimal_epub(epub)
    digest = hashlib.sha256(epub.read_bytes()).hexdigest()
    witness_epub = story / "original" / "witness.epub"
    _write_minimal_epub(witness_epub)
    witness_digest = hashlib.sha256(witness_epub.read_bytes()).hexdigest()
    (story / "original" / "text" / "canonical.md").write_text("Literary text.\n", encoding="utf-8")
    (story / "original" / "text" / "witness.md").write_text(
        "Witness text.\n",
        encoding="utf-8",
    )
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
      public_domain_context: Test public-domain context for the canonical edition.
      textual_limitations: Test transcription rather than a diplomatic facsimile.
      editorial_normalisation: Test edition presentation may be normalised.
      variant_concerns: Test witnesses may contain textual variants.
    selections: []
  - id: witness
    status: admitted
    authority: {tier: 2, story_world_canon: false, style_authority: bounded}
    work: {title: Witness, author: Author, first_published: 1898}
    analytical_roles: [observation]
    permitted_uses: [bounded comparison]
    prohibited_uses: [continuity]
    rationale: Bounded witness.
    edition:
      publisher: Test
      homepage: https://example.test/witness
      download_url: https://example.test/witness.epub
      artifact_format: standard-ebooks-compatible-epub
      planned_path: original/witness.epub
      public_domain_context: Test public-domain context for the witness edition.
      textual_limitations: Test transcription rather than a diplomatic facsimile.
      editorial_normalisation: Test edition presentation may be normalised.
      variant_concerns: Test witnesses may contain textual variants.
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
      public_domain_context: Test public-domain context for the control edition.
      textual_limitations: Test transcription rather than a diplomatic facsimile.
      editorial_normalisation: Test edition presentation may be normalised.
      variant_concerns: Test witnesses may contain textual variants.
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
    retrieved: "2026-07-14"
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
  - id: witness
    role:
      tier: 2
      story_world_canon: false
      style_authority: bounded
      primary_style_anchor: false
      secondary_style_anchor: true
      focus: Bounded witness.
      analytical_roles: [observation]
      permitted_uses: [bounded comparison]
      prohibited_uses: [continuity]
    work: {{title: Witness, author: Author, first_published: 1898}}
    edition:
      publisher: Test
      homepage: https://example.test/witness
      download_url: https://example.test/witness.epub
      upstream_release: test-release
      upstream_revision: test-revision
    retrieved: "2026-07-14"
    files:
      epub: witness.epub
      epub_sha256: {witness_digest}
      markdown: text/witness.md
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


def _update_retained_source(
    story: Path,
    source_id: str,
    updates: list[tuple[tuple[str, ...], object]],
) -> None:
    registry_path = story / "original" / "sources.yml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    source = next(item for item in registry["sources"] if item["id"] == source_id)
    for keys, value in updates:
        target = source
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value
    registry_path.write_text(
        yaml.safe_dump(registry, sort_keys=False),
        encoding="utf-8",
    )


def test_source_admission_writes_passing_report(tmp_path: Path) -> None:
    _write_fixture(tmp_path)

    result = check_source_admission(tmp_path, "source-test")

    assert result.ok
    report = result.report_path.read_text(encoding="utf-8")
    assert "Status: **PASS**" in report
    assert "| `canonical` | admitted | 1 | primary |" in report
    assert "| `control` | proposed | 4 | control |" in report
    assert "### `canonical`: Canonical" in report
    assert "- Author: Author" in report
    assert "- Rationale: Governing source." in report
    assert "- Planned path: `original/canonical.epub`" in report
    assert "- Public-domain context: Test public-domain context for the canonical edition." in report
    assert "- Analytical roles:\n  - frame" in report
    assert "- Permitted uses:\n  - continuity" in report
    assert "- Prohibited uses:\n  - none" in report
    assert "#### Retained source" in report
    assert "- Derivation tool: Pandoc 3.10" in report
    assert "- Provenance transcription: Test" in report
    assert "- Rights source text: Public domain test." in report


@pytest.mark.parametrize(
    ("updates", "expected"),
    [
        ([(('role', 'tier'), 3)], "authority tier"),
        (
            [
                (('role', 'tier'), 1),
                (('role', 'story_world_canon'), True),
                (('role', 'style_authority'), 'primary'),
                (('role', 'primary_style_anchor'), True),
                (('role', 'secondary_style_anchor'), False),
            ],
            "story-world canon status",
        ),
        ([(('role', 'style_authority'), 'secondary')], "style authority"),
        ([(('work', 'title'), 'Different Witness')], "work identity"),
        ([(('role', 'analytical_roles'), ['different role'])], "analytical roles"),
        ([(('role', 'permitted_uses'), ['different use'])], "permitted uses"),
        ([(('role', 'prohibited_uses'), ['different prohibition'])], "prohibited uses"),
        ([(('edition', 'publisher'), 'Different Publisher')], "edition publisher"),
        ([(('edition', 'homepage'), 'https://example.test/different')], "edition homepage"),
        ([(('edition', 'download_url'), 'https://example.test/different.epub')], "edition download URL"),
    ],
    ids=[
        "tier",
        "canon",
        "style-authority",
        "work",
        "analytical-roles",
        "permitted-uses",
        "prohibited-uses",
        "publisher",
        "homepage",
        "download-url",
    ],
)
def test_source_admission_blocks_cross_file_parity_divergence(
    tmp_path: Path,
    updates: list[tuple[tuple[str, ...], object]],
    expected: str,
) -> None:
    story = _write_fixture(tmp_path)
    _update_retained_source(story, "witness", updates)

    result = check_source_admission(tmp_path, "source-test")

    assert not result.ok
    assert any(expected in issue for issue in result.errors)


def test_source_admission_blocks_generic_zip(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    epub = story / "original" / "canonical.epub"
    with zipfile.ZipFile(epub, "w") as archive:
        archive.writestr("readme.txt", "ordinary ZIP")

    result = check_source_admission(tmp_path, "source-test")

    assert not result.ok
    assert any("mimetype" in issue for issue in result.errors)


def test_source_admission_blocks_epub_with_wrong_mimetype(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    _write_minimal_epub(
        story / "original" / "canonical.epub",
        mimetype="application/zip",
    )

    result = check_source_admission(tmp_path, "source-test")

    assert not result.ok
    assert any("exactly application/epub+zip" in issue for issue in result.errors)


def test_source_admission_blocks_epub_without_container_metadata(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    _write_minimal_epub(
        story / "original" / "canonical.epub",
        container=None,
        package_path=None,
    )

    result = check_source_admission(tmp_path, "source-test")

    assert not result.ok
    assert any("META-INF/container.xml" in issue for issue in result.errors)


def test_source_admission_blocks_epub_with_unparseable_container(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    _write_minimal_epub(
        story / "original" / "canonical.epub",
        container="<container>",
        package_path=None,
    )

    result = check_source_admission(tmp_path, "source-test")

    assert not result.ok
    assert any("parse container document" in issue for issue in result.errors)


def test_source_admission_blocks_epub_without_rootfile(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    _write_minimal_epub(
        story / "original" / "canonical.epub",
        container="""<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles/>
</container>
""",
        package_path=None,
    )

    result = check_source_admission(tmp_path, "source-test")

    assert not result.ok
    assert any("no rootfile" in issue for issue in result.errors)


def test_source_admission_blocks_epub_without_package_document(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    _write_minimal_epub(
        story / "original" / "canonical.epub",
        package_path="EPUB/missing.opf",
    )
    # Rebuild without the referenced package document.
    epub = story / "original" / "canonical.epub"
    with zipfile.ZipFile(epub, "r") as archive:
        mimetype = archive.read("mimetype")
        container = archive.read("META-INF/container.xml")
    with zipfile.ZipFile(epub, "w") as archive:
        archive.writestr("mimetype", mimetype)
        archive.writestr("META-INF/container.xml", container)

    result = check_source_admission(tmp_path, "source-test")

    assert not result.ok
    assert any("referenced package document" in issue for issue in result.errors)


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


def test_source_admission_rejects_absolute_slug_without_writing_outside_root(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-absolute-admission-escape"

    with pytest.raises(CreativeWriterError, match="Story slug must use lowercase"):
        check_source_admission(tmp_path, str(outside))

    assert not outside.exists()
    assert not (tmp_path / "build").exists()


def test_source_admission_rejects_traversal_slug_without_writing_outside_root(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-traversal-admission-escape"
    slug = f"../../{outside.name}"

    with pytest.raises(CreativeWriterError, match="Story slug must use lowercase"):
        check_source_admission(tmp_path, slug)

    assert not outside.exists()
    assert not (tmp_path / "build").exists()


def test_source_admission_reports_non_utf8_derived_markdown(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    (story / "original" / "text" / "canonical.md").write_bytes(
        b"Literary text.\xff\n"
    )

    result = check_source_admission(tmp_path, "source-test")

    assert not result.ok
    assert any("Unable to read derived Markdown" in issue for issue in result.errors)
    report = result.report_path.read_text(encoding="utf-8")
    assert "Status: **FAIL**" in report


def test_source_admission_reports_non_regular_epub_path(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    epub = story / "original" / "canonical.epub"
    epub.unlink()
    epub.mkdir()

    result = check_source_admission(tmp_path, "source-test")

    assert not result.ok
    assert any("Invalid retained EPUB" in issue for issue in result.errors)
    report = result.report_path.read_text(encoding="utf-8")
    assert "Status: **FAIL**" in report


def test_time_expedition_admission_passes() -> None:
    root = Path(__file__).resolve().parents[1]

    result = check_source_admission(root, "time-expedition")

    assert result.ok
    report = result.report_path.read_text(encoding="utf-8")
    assert "- Admitted: 4" in report
    assert "- Approved, awaiting retention: 0" in report
    assert "- Proposed: 7" in report
    assert "| `the-time-machine` | admitted | 1 | primary |" in report
    assert "| `the-island-of-doctor-moreau` | admitted | 2 | bounded |" in report
    assert "| `the-war-of-the-worlds` | admitted | 2 | bounded |" in report
    assert "| `the-british-barbarians` | proposed | 4 | control |" in report
    for title in (
        "The Plattner Story",
        "The Sea Raiders",
        "The Crystal Egg",
        "The Star",
    ):
        assert f"- **{title}**" in report
    for author in (
        "Grant Allen",
        "Arthur Conan Doyle",
        "Rudyard Kipling",
        "Richard Marsh",
    ):
        assert f"- Author: {author}" in report
    assert report.count(
        "- Tier 4 restriction: **Negative evidence only; never positive style or continuity authority.**"
    ) == 4
