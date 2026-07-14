from __future__ import annotations

import hashlib
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory, load_yaml_model
from creative_writer.models import (
    RetainedSourceRecord,
    Slug,
    SourceAdmissionRecord,
    SourceStudyAdmission,
    SourcesRegistry,
)

EXCLUDED_PACKAGING_LINK_PATTERN = re.compile(
    r"\]\([^)]*(?:endnotes|imprint|colophon|uncopyright)\.xhtml(?:[#?][^)]*)?\)",
    re.IGNORECASE,
)
STORY_SLUG_ADAPTER = TypeAdapter(Slug)


@dataclass(slots=True)
class SourceAdmissionResult:
    story_slug: str
    report_path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _validate_story_slug(slug: str) -> str:
    try:
        return STORY_SLUG_ADAPTER.validate_python(slug)
    except ValidationError as exc:
        raise CreativeWriterError(
            "Story slug must use lowercase letters, numbers, and single hyphens."
        ) from exc


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
    if not path.is_file():
        return "not a regular file"
    try:
        if not zipfile.is_zipfile(path):
            return "not a ZIP-based EPUB"
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                return f"corrupt archive member: {bad_member}"
            members = set(archive.namelist())
            if "mimetype" not in members:
                return "missing mimetype member"
            if archive.read("mimetype") != b"application/epub+zip":
                return "mimetype member is not exactly application/epub+zip"
            container_path = "META-INF/container.xml"
            if container_path not in members:
                return f"missing {container_path}"
            try:
                container = ET.fromstring(archive.read(container_path))
            except ET.ParseError as exc:
                return f"could not parse container document: {exc}"
            rootfiles = [
                element.attrib.get("full-path", "")
                for element in container.iter()
                if element.tag.rsplit("}", 1)[-1] == "rootfile"
            ]
            if not rootfiles:
                return "container document has no rootfile"
            for package_path in rootfiles:
                if not package_path:
                    return "container rootfile has no full-path"
                if package_path not in members:
                    return f"referenced package document is missing: {package_path}"
    except Exception as exc:
        return f"could not inspect archive: {exc}"
    return None


def _append_parity_errors(
    source: SourceAdmissionRecord,
    retained: RetainedSourceRecord,
    errors: list[str],
) -> None:
    comparisons = (
        ("authority tier", source.authority.tier, retained.role.tier),
        (
            "story-world canon status",
            source.authority.story_world_canon,
            retained.role.story_world_canon,
        ),
        (
            "style authority",
            source.authority.style_authority,
            retained.role.style_authority,
        ),
        ("work identity", source.work, retained.work),
        (
            "analytical roles",
            source.analytical_roles,
            retained.role.analytical_roles,
        ),
        ("permitted uses", source.permitted_uses, retained.role.permitted_uses),
        (
            "prohibited uses",
            source.prohibited_uses,
            retained.role.prohibited_uses,
        ),
        ("edition publisher", source.edition.publisher, retained.edition.publisher),
        ("edition homepage", source.edition.homepage, retained.edition.homepage),
        (
            "edition download URL",
            source.edition.download_url,
            retained.edition.download_url,
        ),
    )
    for label, planned, recorded in comparisons:
        if planned != recorded:
            errors.append(
                f"`{source.id}` {label} differs between admission.yml and "
                "original/sources.yml."
            )


def _append_report_list(lines: list[str], label: str, values: list[str]) -> None:
    lines.append(f"- {label}:")
    lines.extend(f"  - {value}" for value in values)


def _render_report(
    admission: SourceStudyAdmission,
    registry: SourcesRegistry,
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
        "| ID | Status | Tier | Style authority | Author | Title |",
        "|---|---|---:|---|---|---|",
    ]
    for source in admission.sources:
        lines.append(
            f"| `{source.id}` | {source.status} | {source.authority.tier} | "
            f"{source.authority.style_authority} | {source.work.author} | "
            f"{source.work.title} |"
        )

    retained = {source.id: source for source in registry.sources}
    lines.extend(["", "## Detailed review", ""])
    for source in admission.sources:
        edition = source.edition
        lines.extend(
            [
                f"### `{source.id}`: {source.work.title}",
                "",
                f"- Author: {source.work.author}",
                f"- Title: {source.work.title}",
                f"- First published: {source.work.first_published}",
                f"- Status: {source.status}",
                f"- Authority tier: {source.authority.tier}",
                f"- Story-world canon: {str(source.authority.story_world_canon).lower()}",
                f"- Style authority: {source.authority.style_authority}",
                f"- Rationale: {source.rationale}",
            ]
        )
        if source.authority.tier == 4:
            lines.append(
                "- Tier 4 restriction: **Negative evidence only; never positive "
                "style or continuity authority.**"
            )
        _append_report_list(lines, "Analytical roles", source.analytical_roles)
        _append_report_list(lines, "Permitted uses", source.permitted_uses)
        _append_report_list(lines, "Prohibited uses", source.prohibited_uses)
        lines.extend(
            [
                f"- Planned path: `{edition.planned_path}`",
                f"- Edition publisher: {edition.publisher}",
                f"- Edition homepage: <{edition.homepage}>",
                f"- Edition download URL: <{edition.download_url}>",
                f"- Artifact format: {edition.artifact_format}",
                f"- Public-domain context: {edition.public_domain_context}",
                f"- Textual limitations: {edition.textual_limitations}",
                f"- Editorial normalisation: {edition.editorial_normalisation}",
                f"- Variant concerns: {edition.variant_concerns}",
            ]
        )
        if source.selections:
            lines.append("- Selected subworks:")
            for selection in source.selections:
                roles = "; ".join(selection.analytical_roles)
                lines.append(
                    f"  - **{selection.title}** ({selection.first_published}) — {roles}"
                )
        else:
            lines.append("- Selected subworks: None.")

        retained_source = retained.get(source.id)
        if retained_source is not None:
            lines.extend(
                [
                    "",
                    "#### Retained source",
                    "",
                    f"- EPUB path: `original/{retained_source.files.epub}`",
                    f"- EPUB SHA-256: `{retained_source.files.epub_sha256}`",
                    f"- Derived Markdown path: `original/{retained_source.files.markdown}`",
                    f"- Retrieved: {retained_source.retrieved}",
                    f"- Derivation tool: {retained_source.derivation.tool}",
                    f"- Derivation input: {retained_source.derivation.input}",
                    f"- Derivation writer: {retained_source.derivation.writer}",
                    f"- Derivation wrap: {retained_source.derivation.wrap}",
                    f"- Derivation filter: {retained_source.derivation.filter}",
                    f"- Provenance transcription: {retained_source.provenance.transcription}",
                    f"- Provenance page scans: {retained_source.provenance.page_scans}",
                    f"- Rights source text: {retained_source.rights.source_text}",
                    "- Rights edition contributions: "
                    f"{retained_source.rights.edition_contributions}",
                ]
            )
        lines.append("")

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
    slug = _validate_story_slug(slug)
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
        _append_parity_errors(source, retained_source, result.errors)

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
            if epub_path.is_file():
                try:
                    digest = _sha256(epub_path)
                except OSError as exc:
                    result.errors.append(
                        f"Unable to hash retained EPUB for `{source.id}`: {exc}"
                    )
                else:
                    if digest != retained_source.files.epub_sha256:
                        result.errors.append(f"SHA-256 mismatch for `{source.id}`: {epub_path}")
        if not markdown_path.exists():
            result.errors.append(f"Missing or empty derived Markdown for `{source.id}`: {markdown_path}")
        else:
            try:
                markdown = markdown_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                result.errors.append(
                    f"Unable to read derived Markdown for `{source.id}`: {exc}"
                )
            else:
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

    report_path.write_text(_render_report(admission, registry, result), encoding="utf-8")
    return result
