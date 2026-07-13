from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit


EXCLUDED_PACKAGING_FILES = {
    "endnotes.xhtml",
    "imprint.xhtml",
    "colophon.xhtml",
    "uncopyright.xhtml",
}
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def test_time_expedition_derived_sources_have_no_excluded_packaging_links() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = repo_root / "stories" / "time-expedition" / "original" / "text"
    source_paths = [
        source_dir / "the-time-machine.md",
        source_dir / "the-invisible-man.md",
    ]

    violations = []
    for source_path in source_paths:
        for target in MARKDOWN_LINK_PATTERN.findall(source_path.read_text(encoding="utf-8")):
            target_filename = Path(urlsplit(target).path).name
            if target_filename in EXCLUDED_PACKAGING_FILES:
                violations.append(f"{source_path}:{target}")

    assert not violations, "Derived source contains excluded packaging links:\n" + "\n".join(
        violations
    )
