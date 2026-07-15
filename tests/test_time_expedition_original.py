from __future__ import annotations

import hashlib
import re
import subprocess
import zipfile
from xml.etree import ElementTree
from pathlib import Path
from urllib.parse import urlsplit

import yaml


EXCLUDED_PACKAGING_FILES = {
    "endnotes.xhtml",
    "imprint.xhtml",
    "colophon.xhtml",
    "uncopyright.xhtml",
}
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _run_project_gutenberg_filter(html: str) -> str:
    repo_root = Path(__file__).resolve().parents[1]
    filter_path = (
        repo_root
        / "stories"
        / "time-expedition"
        / "original"
        / "filters"
        / "remove-project-gutenberg-boilerplate.lua"
    )
    result = subprocess.run(
        [
            "pandoc",
            "--from=html",
            "--to=gfm-raw_html",
            "--wrap=none",
            f"--lua-filter={filter_path}",
        ],
        cwd=repo_root,
        input=html,
        capture_output=True,
        check=True,
        text=True,
    )
    return result.stdout


def test_time_expedition_derived_sources_have_no_excluded_packaging_links() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = repo_root / "stories" / "time-expedition" / "original" / "text"
    source_paths = [
        source_dir / "the-time-machine.md",
        source_dir / "the-invisible-man.md",
        source_dir / "the-island-of-doctor-moreau.md",
        source_dir / "the-war-of-the-worlds.md",
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


def test_time_expedition_fixed_wells_epubs_match_pinned_hashes() -> None:
    root = Path(__file__).resolve().parents[1]
    original = root / "stories" / "time-expedition" / "original"
    expected = {
        "h-g-wells_the-island-of-doctor-moreau.epub": "c1805bbc79b423716520a24a016ee1feeaa970a9f74f1d4bac4d6c8bccc66c2d",
        "h-g-wells_the-war-of-the-worlds.epub": "56b57347a63fbd52a6a94b6500e5ff1c0a49a266e525223fef08789cb1ad4f8f",
    }
    for filename, digest in expected.items():
        assert hashlib.sha256((original / filename).read_bytes()).hexdigest() == digest


def test_desert_drama_retains_literary_text_from_final_linear_epub_member() -> None:
    root = Path(__file__).resolve().parents[1]
    original = root / "stories" / "time-expedition" / "original"
    epub_path = original / "arthur-conan-doyle_a-desert-drama.epub"
    final_member = "OEBPS/6605053776549637356_21768-h-6.htm.html"

    with zipfile.ZipFile(epub_path) as archive:
        opf = ElementTree.fromstring(archive.read("OEBPS/content.opf"))
        namespace = {"opf": "http://www.idpf.org/2007/opf"}
        manifest = {
            item.attrib["id"]: item.attrib["href"]
            for item in opf.findall("opf:manifest/opf:item", namespace)
        }
        linear_spine_members = [
            f"OEBPS/{manifest[itemref.attrib['idref']]}"
            for itemref in opf.findall("opf:spine/opf:itemref", namespace)
            if itemref.attrib.get("linear", "yes") != "no"
        ]
        assert final_member in linear_spine_members
        final_member_html = archive.read(final_member).decode("utf-8")

    expected_continuation = "A fortnight had passed away"
    assert expected_continuation in final_member_html

    markdown = (original / "text" / "a-desert-drama.md").read_text(encoding="utf-8")
    assert expected_continuation in markdown
    assert "THE END." in markdown


def test_desert_drama_derivation_declares_final_member_and_removes_gutenberg_license() -> None:
    root = Path(__file__).resolve().parents[1]
    original = root / "stories" / "time-expedition" / "original"
    registry = yaml.safe_load((original / "sources.yml").read_text(encoding="utf-8"))
    record = next(source for source in registry["sources"] if source["id"] == "a-desert-drama")

    assert record["derivation"]["input"] == (
        "OEBPS/6605053776549637356_21768-h-0.htm.html through "
        "OEBPS/6605053776549637356_21768-h-6.htm.html in numeric order"
    )

    markdown = (original / "text" / "a-desert-drama.md").read_text(encoding="utf-8")
    assert "Project Gutenberg License" not in markdown
    assert "FULL LICENSE" not in markdown
    assert "Section 1. Project Gutenberg License" not in markdown


def test_desert_drama_retains_passenger_list_and_tennyson_quotations() -> None:
    root = Path(__file__).resolve().parents[1]
    markdown = (
        root / "stories" / "time-expedition" / "original" / "text" / "a-desert-drama.md"
    ).read_text(encoding="utf-8")

    for passage in (
        "PASSENGERS.",
        "Colonel Cochrane",
        "Mr. Cecil Brown",
        "Oh, yet we trust that somehow good",
        "I falter where I firmly trod",
        "And faintly trust the larger hope.",
    ):
        assert passage in markdown
    for forbidden in (
        "PROJECT GUTENBERG",
        "FULL LICENSE",
        "TRANSCRIBER",
        "Front Cover",
        "Back Cover",
    ):
        assert forbidden not in markdown


def test_british_barbarians_retains_literary_quotations() -> None:
    root = Path(__file__).resolve().parents[1]
    markdown = (
        root
        / "stories"
        / "time-expedition"
        / "original"
        / "text"
        / "the-british-barbarians.md"
    ).read_text(encoding="utf-8")

    for passage in (
        "Singing songs unbidden",
        "Nature is made better by no mean",
        "Because right is right, to follow right",
    ):
        assert passage in markdown
    for forbidden in (
        "PROJECT GUTENBERG",
        "FULL LICENSE",
        "TRANSCRIBER",
        "Front Cover",
        "Back Cover",
    ):
        assert forbidden not in markdown


def test_project_gutenberg_filter_removes_leading_transcriber_note_preamble() -> None:
    output = _run_project_gutenberg_filter(
        """<div class="pg-boilerplate">Project Gutenberg credits.</div>
<p>Transcriber's Note:</p>
<p>Editorial preamble.</p>
<hr />
<p>Literary paragraph one.</p>
<p>Literary paragraph two.</p>
"""
    )

    assert output == "Literary paragraph one.\n\nLiterary paragraph two.\n"


def test_project_gutenberg_filter_preserves_later_transcriber_note_and_rules() -> None:
    output = _run_project_gutenberg_filter(
        """<p>First literary paragraph.</p>
<hr />
<p>Transcriber's Note:</p>
<p>Editorial text after the marker.</p>
<hr />
<p>Second literary paragraph.</p>
"""
    )

    assert output == (
        "First literary paragraph.\n\n"
        "------------------------------------------------------------------------\n\n"
        "Transcriber's Note:\n\n"
        "Editorial text after the marker.\n\n"
        "------------------------------------------------------------------------\n\n"
        "Second literary paragraph.\n"
    )


def test_project_gutenberg_filter_preserves_non_empty_mid_document_pgmonospaced_literature() -> None:
    output = _run_project_gutenberg_filter(
        """<p>Before the verse.</p>
<div class="pgmonospaced">A literary line<br/>B literary line</div>
<p>After the verse.</p>
"""
    )

    assert output == (
        "Before the verse.\n\n"
        "A literary line\\\n"
        "B literary line\n\n"
        "After the verse.\n"
    )
