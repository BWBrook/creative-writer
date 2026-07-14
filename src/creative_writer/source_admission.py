from __future__ import annotations

import hashlib
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory, load_yaml_model
from creative_writer.models import SourceStudyAdmission, SourcesRegistry

EXCLUDED_PACKAGING_LINK_PATTERN = re.compile(
    r"\]\([^)]*(?:endnotes|imprint|colophon|uncopyright)\.xhtml(?:[#?][^)]*)?\)",
    re.IGNORECASE,
)


@dataclass(slots=True)
class SourceAdmissionResult:
    story_slug: str
    report_path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _story_path(story_dir: Path, relative: str) -> Path:
    candidate = (story_dir / relative).resolve()
    base = story_dir.resolve()
    if candidate != base and base not in candidate.parents:
        raise CreativeWriterError(f"Source path escapes story directory: {relative}")
    return candidate


def _epub_integrity_error(path: Path) -> str | None:
    if not zipfile.is_zipfile(path):
        return "not a ZIP-based EPUB"
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
    if bad_member is not None:
        return f"corrupt archive member: {bad_member}"
    return None


def _render_report(
    admission: SourceStudyAdmission,
    result: SourceAdmissionResult,
) -> str:
    status = "PASS" if result.ok else "FAIL"
    counts = {
        name: sum(1 for source in admission.sources if source.status == name)
        for name in ("admitted", "approved", "proposed", "excluded")
    }
    lines = [
        "# Source Admission Report",
        "",
        f"- Story slug: `{result.story_slug}`",
        f"- Status: **{status}**",
        f"- Composition window: {admission.composition_window.start}-{admission.composition_window.end}",
        f"- Admitted: {counts['admitted']}",
        f"- Approved, awaiting retention: {counts['approved']}",
        f"- Proposed: {counts['proposed']}",
        f"- Excluded: {counts['excluded']}",
        "",
        "## Sources",
        "",
        "| ID | Status | Tier | Style authority | Work |",
        "|---|---|---:|---|---|",
    ]
    for source in admission.sources:
        lines.append(
            f"| `{source.id}` | {source.status} | {source.authority.tier} | "
            f"{source.authority.style_authority} | {source.work.title} |"
        )
    lines.extend(["", "## Blocking issues", ""])
    lines.extend(f"- {error}" for error in result.errors)
    if not result.errors:
        lines.append("- None.")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {warning}" for warning in result.warnings)
    if not result.warnings:
        lines.append("- None.")
    return "\n".join(lines) + "\n"


def check_source_admission(root: Path, slug: str) -> SourceAdmissionResult:
    story_dir = root / "stories" / slug
    admission_path = story_dir / "source-study" / "admission.yml"
    registry_path = story_dir / "original" / "sources.yml"
    report_path = root / "build" / slug / "reports" / "source-admission-report.md"
    ensure_directory(report_path.parent)
    result = SourceAdmissionResult(story_slug=slug, report_path=report_path)

    try:
        admission = load_yaml_model(admission_path, SourceStudyAdmission)
        registry = load_yaml_model(registry_path, SourcesRegistry)
    except CreativeWriterError as exc:
        result.errors.append(str(exc))
        report_path.write_text(
            "# Source Admission Report\n\n- Status: **FAIL**\n\n"
            f"## Blocking issues\n\n- {exc}\n",
            encoding="utf-8",
        )
        return result

    retained = {source.id: source for source in registry.sources}
    admitted_ids = {source.id for source in admission.sources if source.status == "admitted"}

    for source in admission.sources:
        try:
            planned_path = _story_path(story_dir, source.edition.planned_path)
        except CreativeWriterError as exc:
            result.errors.append(str(exc))
            continue
        if source.status == "proposed" and planned_path.exists():
            result.errors.append(
                f"`{source.id}` artifact exists before corpus approval: {planned_path}"
            )
        if source.status != "admitted":
            continue

        retained_source = retained.get(source.id)
        if retained_source is None:
            result.errors.append(f"Admitted source `{source.id}` has no retained source record.")
            continue

        try:
            epub_path = _story_path(story_dir / "original", retained_source.files.epub)
            markdown_path = _story_path(story_dir / "original", retained_source.files.markdown)
        except CreativeWriterError as exc:
            result.errors.append(str(exc))
            continue
        if epub_path != planned_path:
            result.errors.append(
                f"Retained EPUB path for `{source.id}` does not match the admission plan."
            )
        if not epub_path.exists():
            result.errors.append(f"Missing retained EPUB for `{source.id}`: {epub_path}")
        else:
            integrity_error = _epub_integrity_error(epub_path)
            if integrity_error:
                result.errors.append(
                    f"Invalid retained EPUB for `{source.id}`: {integrity_error}"
                )
            if _sha256(epub_path) != retained_source.files.epub_sha256:
                result.errors.append(f"SHA-256 mismatch for `{source.id}`: {epub_path}")
        if not markdown_path.exists():
            result.errors.append(f"Missing or empty derived Markdown for `{source.id}`: {markdown_path}")
        else:
            markdown = markdown_path.read_text(encoding="utf-8")
            if not markdown.strip():
                result.errors.append(f"Missing or empty derived Markdown for `{source.id}`: {markdown_path}")
            elif EXCLUDED_PACKAGING_LINK_PATTERN.search(markdown):
                result.errors.append(
                    f"Derived Markdown for `{source.id}` contains an excluded packaging link."
                )

    extra_retained = sorted(set(retained) - admitted_ids)
    for source_id in extra_retained:
        result.errors.append(
            f"Retained source `{source_id}` is not marked admitted in source-study/admission.yml."
        )

    report_path.write_text(_render_report(admission, result), encoding="utf-8")
    return result
