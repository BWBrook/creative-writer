from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

from creative_writer.building import build_story
from creative_writer.checks import check_story
from creative_writer.files import repo_root


def test_seeded_story_builds_epub_and_pdf() -> None:
    root = repo_root(Path(__file__).resolve())
    epub_path = build_story(root, "mars-2044-cave", "epub")
    pdf_path = build_story(root, "mars-2044-cave", "pdf")

    assert epub_path.exists()
    assert pdf_path.exists()


def test_make_end_to_end_for_seeded_story() -> None:
    root = repo_root(Path(__file__).resolve())

    subprocess.run(
        ["make", "check", "STORY=mars-2044-cave"],
        cwd=root,
        check=True,
    )
    subprocess.run(
        ["make", "epub", "STORY=mars-2044-cave"],
        cwd=root,
        check=True,
    )
    subprocess.run(
        ["make", "pdf", "STORY=mars-2044-cave"],
        cwd=root,
        check=True,
    )

    report_path = root / "build" / "mars-2044-cave" / "reports" / "coherence-report.md"
    assert report_path.exists()
    assert check_story(root, "mars-2044-cave").ok


def test_built_epub_has_valid_language_metadata() -> None:
    root = repo_root(Path(__file__).resolve())
    epub_path = build_story(root, "mars-2044-cave", "epub")

    with zipfile.ZipFile(epub_path) as archive:
        content_opf = archive.read("EPUB/content.opf").decode("utf-8")

    assert "<dc:language>en-AU</dc:language>" in content_opf
    assert 'xml:lang="en-AU"' in content_opf
