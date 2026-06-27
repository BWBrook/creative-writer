from __future__ import annotations

from pathlib import Path

from creative_writer.ai_audit import generate_ai_writing_audit
from creative_writer.scaffold import create_story


def test_generate_ai_writing_audit_uses_configured_scanner(
    tmp_path: Path,
    monkeypatch,
) -> None:
    story_dir = create_story(tmp_path, "audit-story", "original")
    (story_dir / "manuscript" / "01-opening.md").write_text(
        "The door was locked. She tried the latch twice.\n",
        encoding="utf-8",
    )
    scanner = tmp_path / "scanner.py"
    scanner.write_text(
        "import sys\n"
        "print('# fake scan')\n"
        "print('args=' + ' '.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CREATIVE_WRITER_AI_AUDIT_SCRIPT", str(scanner))

    result = generate_ai_writing_audit(tmp_path, "audit-story")

    assert result.chapter_count == 2
    assert result.report_path.exists()
    report = result.report_path.read_text(encoding="utf-8")
    assert "# AI Writing Audit: Audit Story" in report
    assert "## Opening" in report
    assert "# fake scan" in report
    assert "--genre narrative" in report
