from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

from creative_writer.exceptions import CreativeWriterError
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
