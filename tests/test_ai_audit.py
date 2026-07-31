from __future__ import annotations

import json
from pathlib import Path

import pytest

from creative_writer.ai_audit import generate_ai_writing_audit
from creative_writer.ai_audit import scan_ai_writing_json
from creative_writer.exceptions import CreativeWriterError
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


def test_scan_ai_writing_json_preserves_structured_groups_without_risk(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manuscript = tmp_path / "chapter.md"
    manuscript.write_text("One.\nTwo.\nAnswer-shaped prose.\n", encoding="utf-8")
    scanner = tmp_path / "scanner.py"
    payload = {
        "risk": "moderate surface risk",
        "reasons": ["two groups"],
        "genre": "narrative",
        "metrics": {"words": 20},
        "groups": {
            "AI vocabulary": {
                "count": 1,
                "severity": 2,
                "advice": (
                    "Replace the stock abstraction with concrete observation."
                ),
                "hits": [
                    {
                        "group": "AI vocabulary",
                        "severity": 2,
                        "line": 3,
                        "match": "shaped",
                        "context": "answer-shaped",
                    }
                ],
                "scanner_extension": "preserved by the permissive model",
            }
        },
        "caution": "Surface scan only; not proof of AI authorship.",
    }
    scanner.write_text(
        "import json\n"
        "import sys\n"
        "from pathlib import Path\n"
        f"payload = {payload!r}\n"
        "Path(__file__).with_suffix('.args').write_text("
        "'\\n'.join(sys.argv[1:]), encoding='utf-8')\n"
        "print(json.dumps(payload))\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CREATIVE_WRITER_AI_AUDIT_SCRIPT", str(scanner))

    result = scan_ai_writing_json(manuscript)

    assert result.status == "complete"
    assert result.script_path == scanner
    assert list(result.groups) == ["AI vocabulary"]
    group = result.groups["AI vocabulary"]
    assert group.advice == (
        "Replace the stock abstraction with concrete observation."
    )
    assert group.hits[0].group == "AI vocabulary"
    assert group.hits[0].line == 3
    assert group.hits[0].match == "shaped"
    assert group.hits[0].context == "answer-shaped"
    assert group.model_extra == {
        "scanner_extension": "preserved by the permissive model"
    }
    assert result.caution == "Surface scan only; not proof of AI authorship."
    assert not hasattr(result, "risk")
    assert scanner.with_suffix(".args").read_text(encoding="utf-8").splitlines() == [
        "--genre",
        "narrative",
        "--json",
        str(manuscript),
    ]


def test_scan_ai_writing_json_marks_only_an_absent_optional_scanner_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manuscript = tmp_path / "chapter.md"
    manuscript.write_text("A chapter.\n", encoding="utf-8")
    missing = tmp_path / "missing-scanner.py"
    monkeypatch.setenv("CREATIVE_WRITER_AI_AUDIT_SCRIPT", str(missing))

    with pytest.raises(CreativeWriterError, match="script not found"):
        scan_ai_writing_json(manuscript)

    result = scan_ai_writing_json(manuscript, unavailable_is_error=False)

    assert result.status == "unavailable"
    assert result.script_path is None
    assert result.groups == {}
    assert result.notice is not None
    assert str(missing) in result.notice


def test_scan_ai_writing_json_rejects_nonzero_scanner(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manuscript = tmp_path / "chapter.md"
    manuscript.write_text("A chapter.\n", encoding="utf-8")
    scanner = tmp_path / "scanner.py"
    scanner.write_text(
        "import sys\n"
        "print('scanner failed', file=sys.stderr)\n"
        "raise SystemExit(7)\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CREATIVE_WRITER_AI_AUDIT_SCRIPT", str(scanner))

    with pytest.raises(CreativeWriterError, match="scanner failed"):
        scan_ai_writing_json(manuscript, unavailable_is_error=False)


def test_scan_ai_writing_json_rejects_malformed_json(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manuscript = tmp_path / "chapter.md"
    manuscript.write_text("A chapter.\n", encoding="utf-8")
    scanner = tmp_path / "scanner.py"
    scanner.write_text("print('not-json')\n", encoding="utf-8")
    monkeypatch.setenv("CREATIVE_WRITER_AI_AUDIT_SCRIPT", str(scanner))

    with pytest.raises(CreativeWriterError, match="malformed JSON"):
        scan_ai_writing_json(manuscript, unavailable_is_error=False)
