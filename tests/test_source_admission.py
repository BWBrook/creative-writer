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
    members: dict[str, str] | None = None,
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
        for member, content in (members or {}).items():
            archive.writestr(member, content)


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
    canonical_markdown = story / "original" / "text" / "canonical.md"
    canonical_markdown.write_text("Literary text.\n", encoding="utf-8")
    canonical_markdown_digest = hashlib.sha256(
        canonical_markdown.read_bytes()
    ).hexdigest()
    witness_markdown = story / "original" / "text" / "witness.md"
    witness_markdown.write_text(
        "Witness text.\n",
        encoding="utf-8",
    )
    witness_markdown_digest = hashlib.sha256(witness_markdown.read_bytes()).hexdigest()
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
      markdown_sha256: {canonical_markdown_digest}
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
      markdown_sha256: {witness_markdown_digest}
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


def _write_yaml(path: Path, data: object) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _make_witness_omnibus(story: Path) -> None:
    epub = story / "original" / "witness.epub"
    _write_minimal_epub(
        epub,
        members={"epub/text/the-star.xhtml": "<html><body><p>Star source.</p></body></html>"},
    )
    markdown = story / "original" / "text" / "selected-short-fiction" / "the-star.md"
    markdown.parent.mkdir(parents=True)
    markdown.write_text("The selected star witness.\n", encoding="utf-8")

    admission_path = story / "source-study" / "admission.yml"
    admission = yaml.safe_load(admission_path.read_text(encoding="utf-8"))
    planned = next(item for item in admission["sources"] if item["id"] == "witness")
    planned["selections"] = [
        {
            "id": "the-star",
            "title": "The Star",
            "first_published": 1897,
            "analytical_roles": ["catastrophe"],
        }
    ]
    _write_yaml(admission_path, admission)

    registry_path = story / "original" / "sources.yml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    retained = next(item for item in registry["sources"] if item["id"] == "witness")
    retained["files"] = {
        "epub": "witness.epub",
        "epub_sha256": hashlib.sha256(epub.read_bytes()).hexdigest(),
    }
    retained["selections"] = [
        {
            "id": "the-star",
            "title": "The Star",
            "first_published": 1897,
            "input": "epub/text/the-star.xhtml",
            "markdown": "text/selected-short-fiction/the-star.md",
            "markdown_sha256": hashlib.sha256(markdown.read_bytes()).hexdigest(),
        }
    ]
    _write_yaml(registry_path, registry)


def _mutate_omnibus_fixture(story: Path, mutation: str) -> None:
    admission_path = story / "source-study" / "admission.yml"
    registry_path = story / "original" / "sources.yml"
    admission = yaml.safe_load(admission_path.read_text(encoding="utf-8"))
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    planned = next(item for item in admission["sources"] if item["id"] == "witness")
    retained = next(item for item in registry["sources"] if item["id"] == "witness")
    selection = retained["selections"][0]
    epub = story / "original" / "witness.epub"
    markdown = story / "original" / selection["markdown"]

    if mutation == "missing-retained-selection":
        full_markdown = story / "original" / "text" / "witness.md"
        retained["files"]["markdown"] = "text/witness.md"
        retained["files"]["markdown_sha256"] = hashlib.sha256(
            full_markdown.read_bytes()
        ).hexdigest()
        retained["selections"] = []
    elif mutation == "extra-retained-selection":
        second_markdown = markdown.parent / "second-story.md"
        second_markdown.write_text("Second selected witness.\n", encoding="utf-8")
        _write_minimal_epub(
            epub,
            members={
                "epub/text/the-star.xhtml": "<html><body><p>Star source.</p></body></html>",
                "epub/text/second-story.xhtml": "<html><body><p>Second source.</p></body></html>",
            },
        )
        retained["files"]["epub_sha256"] = hashlib.sha256(epub.read_bytes()).hexdigest()
        retained["selections"].append(
            {
                "id": "second-story",
                "title": "Second Story",
                "first_published": 1898,
                "input": "epub/text/second-story.xhtml",
                "markdown": "text/selected-short-fiction/second-story.md",
                "markdown_sha256": hashlib.sha256(second_markdown.read_bytes()).hexdigest(),
            }
        )
    elif mutation == "changed-title":
        selection["title"] = "Changed Title"
    elif mutation == "changed-year":
        selection["first_published"] = 1898
    elif mutation == "missing-input-member":
        _write_minimal_epub(epub)
        retained["files"]["epub_sha256"] = hashlib.sha256(epub.read_bytes()).hexdigest()
    elif mutation == "missing-markdown":
        markdown.unlink()
    elif mutation == "bad-markdown-hash":
        selection["markdown_sha256"] = "0" * 64
    elif mutation == "packaging-link":
        markdown.write_text("Text.[1](endnotes.xhtml#note-1)\n", encoding="utf-8")
        selection["markdown_sha256"] = hashlib.sha256(markdown.read_bytes()).hexdigest()
    else:
        raise AssertionError(f"Unknown mutation: {mutation}")

    _write_yaml(admission_path, admission)
    _write_yaml(registry_path, registry)


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
    assert "- Derived Markdown SHA-256: `" in report
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
    assert any("artifact exists before corpus admission" in issue for issue in result.errors)


def test_source_admission_accepts_and_reports_selected_witness(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    _make_witness_omnibus(story)
    result = check_source_admission(tmp_path, "source-test")
    assert result.ok
    report = result.report_path.read_text(encoding="utf-8")
    assert "- Derived Markdown path: `original/text/selected-short-fiction/the-star.md`" in report
    assert "- Derived Markdown SHA-256: `" in report
    assert "- Derivation input: `epub/text/the-star.xhtml`" in report


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("missing-retained-selection", "selection parity differs"),
        ("extra-retained-selection", "selection parity differs"),
        ("changed-title", "selection parity differs"),
        ("changed-year", "selection parity differs"),
        ("missing-input-member", "selection input member is missing"),
        ("missing-markdown", "Missing or empty derived Markdown"),
        ("bad-markdown-hash", "Markdown SHA-256 mismatch"),
        ("packaging-link", "excluded packaging link"),
    ],
)
def test_source_admission_blocks_invalid_selected_witness(
    tmp_path: Path, mutation: str, expected: str
) -> None:
    story = _write_fixture(tmp_path)
    _make_witness_omnibus(story)
    _mutate_omnibus_fixture(story, mutation)
    result = check_source_admission(tmp_path, "source-test")
    assert not result.ok
    assert any(expected in issue for issue in result.errors)


def test_source_admission_blocks_full_work_markdown_hash_mismatch(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    (story / "original" / "text" / "canonical.md").write_text("Changed.\n", encoding="utf-8")
    result = check_source_admission(tmp_path, "source-test")
    assert not result.ok
    assert any("Markdown SHA-256 mismatch" in issue for issue in result.errors)


def test_source_admission_accumulates_checks_with_unsafe_planned_epub(
    tmp_path: Path,
) -> None:
    story = _write_fixture(tmp_path)
    admission_path = story / "source-study" / "admission.yml"
    admission = yaml.safe_load(admission_path.read_text(encoding="utf-8"))
    planned = next(item for item in admission["sources"] if item["id"] == "witness")
    planned["edition"]["planned_path"] = "original/../../outside.epub"
    planned["selections"] = [
        {
            "id": "unretained",
            "title": "Unretained Selection",
            "first_published": 1898,
            "analytical_roles": ["observation"],
        }
    ]
    _write_yaml(admission_path, admission)

    markdown = story / "original" / "text" / "witness.md"
    markdown.write_text("Text.[1](endnotes.xhtml#note-1)\n", encoding="utf-8")
    _update_retained_source(
        story,
        "witness",
        [
            (
                ("files", "markdown_sha256"),
                hashlib.sha256(markdown.read_bytes()).hexdigest(),
            )
        ],
    )

    result = check_source_admission(tmp_path, "source-test")

    expected_errors = (
        "Source path escapes story directory: original/../../outside.epub",
        "`witness` selection parity differs",
        "Derived Markdown for `witness` contains an excluded packaging link.",
    )
    assert not result.ok
    report = result.report_path.read_text(encoding="utf-8")
    for expected in expected_errors:
        assert any(expected in issue for issue in result.errors)
        assert expected in report


def test_source_admission_accumulates_checks_with_unsafe_retained_epub(
    tmp_path: Path,
) -> None:
    story = _write_fixture(tmp_path)
    _make_witness_omnibus(story)
    registry_path = story / "original" / "sources.yml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    retained = next(item for item in registry["sources"] if item["id"] == "witness")
    retained["files"]["epub"] = "../unsafe.epub"
    retained["selections"][0]["title"] = "Changed Title"
    markdown = story / "original" / retained["selections"][0]["markdown"]
    markdown.write_text("Text.[1](endnotes.xhtml#note-1)\n", encoding="utf-8")
    retained["selections"][0]["markdown_sha256"] = hashlib.sha256(
        markdown.read_bytes()
    ).hexdigest()
    _write_yaml(registry_path, registry)

    result = check_source_admission(tmp_path, "source-test")

    expected_errors = (
        "Source path escapes story directory: ../unsafe.epub",
        "`witness` selection parity differs",
        "Derived Markdown for `witness/the-star` contains an excluded packaging link.",
    )
    assert not result.ok
    assert not any("selection input member is missing" in issue for issue in result.errors)
    report = result.report_path.read_text(encoding="utf-8")
    for expected in expected_errors:
        assert any(expected in issue for issue in result.errors)
        assert expected in report


def test_source_admission_blocks_excluded_artifact(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    admission_path = story / "source-study" / "admission.yml"
    admission = yaml.safe_load(admission_path.read_text(encoding="utf-8"))
    control = next(item for item in admission["sources"] if item["id"] == "control")
    control["status"] = "excluded"
    control["authority"] = {"tier": 5, "story_world_canon": False, "style_authority": "none"}
    admission_path.write_text(yaml.safe_dump(admission, sort_keys=False), encoding="utf-8")
    (story / "original" / "control.epub").write_bytes(b"must remain absent")
    result = check_source_admission(tmp_path, "source-test")
    assert not result.ok
    assert any("excluded source" in issue for issue in result.errors)


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
