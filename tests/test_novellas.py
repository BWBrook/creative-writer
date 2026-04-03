from __future__ import annotations

import subprocess
from pathlib import Path

from creative_writer.exceptions import CreativeWriterError
from creative_writer.novellas import (
    NOVELLAS_ENV_VAR,
    clear_ingested,
    export_novella,
    import_novella,
    resolve_novellas_dir,
)
from creative_writer.scaffold import create_story


def test_resolve_novellas_dir_prefers_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(NOVELLAS_ENV_VAR, str(tmp_path))
    assert resolve_novellas_dir() == tmp_path.resolve()


def test_import_docx_creates_markdown(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    novellas_dir = tmp_path / "novellas"
    root.mkdir()
    novellas_dir.mkdir()
    monkeypatch.setenv(NOVELLAS_ENV_VAR, str(novellas_dir))

    source_markdown = tmp_path / "source.md"
    source_markdown.write_text("# The New Grand Tour\n\nA short imported test.\n", encoding="utf-8")
    source_docx = novellas_dir / "The New Grand Tour.docx"
    subprocess.run(["pandoc", str(source_markdown), "-o", str(source_docx)], check=True)

    imported_path = import_novella(root, "The New Grand Tour.docx")

    assert imported_path.exists()
    imported_text = imported_path.read_text(encoding="utf-8")
    assert "The New Grand Tour" in imported_text
    assert "A short imported test." in imported_text


def test_export_markdown_creates_docx(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    ingested_dir = root / "ingested"
    novellas_dir = tmp_path / "novellas"
    ingested_dir.mkdir(parents=True)
    novellas_dir.mkdir()
    monkeypatch.setenv(NOVELLAS_ENV_VAR, str(novellas_dir))

    markdown_path = ingested_dir / "sample-piece.md"
    markdown_path.write_text("# Sample Piece\n\nExport me.\n", encoding="utf-8")

    exported_path = export_novella(root, "ingested/sample-piece.md")

    assert exported_path.exists()
    assert exported_path.name == "Sample Piece.docx"


def test_clear_ingested_removes_staging_when_story_is_safe(tmp_path: Path) -> None:
    create_story(tmp_path, "cleanup-story", "original")
    ingested_dir = tmp_path / "ingested"
    media_dir = ingested_dir / "media" / "cleanup-story"
    media_dir.mkdir(parents=True)
    (ingested_dir / "README.md").write_text("# Ingested\n", encoding="utf-8")
    (ingested_dir / "cleanup-story.md").write_text("Imported text.\n", encoding="utf-8")
    (media_dir / "image.jpeg").write_text("binary-ish", encoding="utf-8")

    story_asset = (
        tmp_path
        / "stories"
        / "cleanup-story"
        / "assets"
        / "images"
        / "image.jpeg"
    )
    story_asset.write_text("copied", encoding="utf-8")

    removed = clear_ingested(tmp_path, "cleanup-story")

    assert (tmp_path / "ingested" / "README.md").exists()
    assert not (ingested_dir / "cleanup-story.md").exists()
    assert not media_dir.exists()
    assert any(path.name == "cleanup-story.md" for path in removed)


def test_clear_ingested_refuses_when_story_still_references_ingested(tmp_path: Path) -> None:
    story_dir = create_story(tmp_path, "sticky-story", "original")
    ingested_dir = tmp_path / "ingested"
    ingested_dir.mkdir(parents=True)
    (ingested_dir / "README.md").write_text("# Ingested\n", encoding="utf-8")
    (ingested_dir / "sticky-story.md").write_text("Imported text.\n", encoding="utf-8")
    (story_dir / "outline.md").write_text(
        "This outline still references ingested/sticky-story.md\n",
        encoding="utf-8",
    )

    try:
        clear_ingested(tmp_path, "sticky-story")
    except CreativeWriterError as exc:
        assert "still reference" in str(exc)
    else:
        raise AssertionError("clear_ingested should have refused cleanup")
