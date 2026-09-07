"""Coherence and style checks for story projects."""

from __future__ import annotations

import re
from pathlib import Path

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory, load_chapter_document, load_yaml_model
from creative_writer.models import (
    CharactersRegistry,
    CheckMessage,
    CheckResult,
    CluesRegistry,
    ContractConfig,
    LocationsRegistry,
    PlotDeviceRecord,
    PlotDevicesRegistry,
    ReviewPackEntry,
    StoryConfig,
    TimelineRegistry,
)
from creative_writer.prose_heuristics import run_surface_heuristics
from creative_writer.review_packs import review_pack_manifest_paths, validate_review_pack_manifest
from creative_writer.style_models import StyleReferencePacket
from creative_writer.style_profiles import (
    StyleContext,
    load_style_context,
    resolve_style_profile_path,
    validate_chapter_style_metadata,
)

MANDATORY_ARTIFACTS = [
    "story.yml",
    "contract.yml",
    "style-guide.md",
    "narrative-design.md",
    "outline.md",
    "chapter-stubs",
    "manuscript",
]
IGNORED_SCENE_CARD_FILES = {"README.md", "_template.md"}
IGNORED_STYLE_REFERENCE_PACKET_FILES = {"_template.yml"}

MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
HTML_IMAGE_PATTERN = re.compile(r'<img[^>]+src="([^"]+)"', re.IGNORECASE)


def _add_error(result: CheckResult, location: Path | str, message: str) -> None:
    result.errors.append(CheckMessage("error", str(location), message))


def _add_warning(result: CheckResult, location: Path | str, message: str) -> None:
    result.warnings.append(CheckMessage("warning", str(location), message))


def _load_registry(
    story_dir: Path,
    filename: str,
    model_type: type,
    result: CheckResult,
):
    path = story_dir / filename
    if not path.exists():
        return None

    try:
        return load_yaml_model(path, model_type)
    except CreativeWriterError as exc:
        _add_error(result, path, str(exc))
        return None


def _scene_card_files(story_dir: Path, scene_cards_dir: str | None) -> list[str]:
    if not scene_cards_dir:
        return []

    directory = story_dir / scene_cards_dir
    if not directory.exists() or not directory.is_dir():
        return []

    return sorted(
        path.relative_to(story_dir).as_posix()
        for path in directory.glob("*.md")
        if path.name not in IGNORED_SCENE_CARD_FILES
    )


def _render_report(
    result: CheckResult,
    story_dir: Path,
    registry_counts: dict[str, int],
    scene_cards_by_chapter: dict[str, list[str]],
    plot_devices: list[PlotDeviceRecord],
) -> str:
    status = "PASS"
    if result.errors:
        status = "FAIL"
    elif result.warnings:
        status = "WARN"

    lines = [
        f"# Coherence Report: {result.story_title or result.story_slug}",
        "",
        f"- Story slug: `{result.story_slug}`",
        f"- Status: **{status}**",
        f"- Blocking issues: {len(result.errors)}",
        f"- Warnings: {len(result.warnings)}",
        f"- Story path: `{story_dir}`",
        "",
        "## Mandatory artifacts",
        "",
    ]
    for artifact in MANDATORY_ARTIFACTS:
        target = story_dir / artifact
        lines.append(
            f"- `{artifact}`: {'present' if target.exists() else 'missing'}"
        )

    lines.extend(
        [
            "",
            "## Registries",
            "",
            f"- Characters tracked: {registry_counts['characters']}",
            f"- Clues tracked: {registry_counts['clues']}",
            f"- Locations tracked: {registry_counts['locations']}",
            f"- Timeline events tracked: {registry_counts['timeline']}",
            f"- Plot devices tracked: {registry_counts['plot_devices']}",
            "",
            "## Chapters",
            "",
        ]
    )
    if result.chapters:
        for chapter in result.chapters:
            fm = chapter.front_matter
            scene_cards = scene_cards_by_chapter.get(chapter.stub_path.name, [])
            lines.append(
                f"- `{chapter.stub_path.name}` -> `{chapter.manuscript_path.name}`: "
                f"{fm.title} | characters={len(fm.characters)} | "
                f"locations={len(fm.locations)} | clues introduced={len(fm.clues_introduced)} | "
                f"clues resolved={len(fm.clues_resolved)} | "
                f"plot devices={len(fm.plot_devices)} | scene cards={len(scene_cards)}"
            )
    else:
        lines.append("- No chapters were successfully parsed.")

    lines.extend(["", "## Scene cards", ""])
    if result.chapters:
        for chapter in result.chapters:
            scene_cards = scene_cards_by_chapter.get(chapter.stub_path.name, [])
            if scene_cards:
                joined = ", ".join(f"`{path}`" for path in scene_cards)
                lines.append(
                    f"- `{chapter.stub_path.name}`: {len(scene_cards)} scene card(s) -> {joined}"
                )
            elif chapter.front_matter.scene_cards_dir:
                lines.append(f"- `{chapter.stub_path.name}`: none.")
            else:
                lines.append(f"- `{chapter.stub_path.name}`: no scene card directory linked.")
    else:
        lines.append("- No chapters were successfully parsed.")

    lines.extend(["", "## Plot devices", ""])
    if plot_devices:
        for item in plot_devices:
            details = []
            if item.narrative_role:
                details.append(item.narrative_role)
            if item.description:
                details.append(item.description)
            summary = " | ".join(details)
            if summary:
                lines.append(
                    f"- `{item.id}` ({item.status}): {item.name} | {summary}"
                )
            else:
                lines.append(f"- `{item.id}` ({item.status}): {item.name}")
    else:
        lines.append("- None tracked.")

    lines.extend(["", "## Blocking issues", ""])
    if result.errors:
        for item in result.errors:
            lines.append(f"- `{item.location}`: {item.message}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Warnings", ""])
    if result.warnings:
        for item in result.warnings:
            lines.append(f"- `{item.location}`: {item.message}")
    else:
        lines.append("- None.")

    return "\n".join(lines) + "\n"


def _extract_image_paths(markdown: str) -> set[str]:
    paths = set(MARKDOWN_IMAGE_PATTERN.findall(markdown))
    paths.update(HTML_IMAGE_PATTERN.findall(markdown))
    return {path for path in paths if path and not path.startswith("http")}


def _validate_configured_style(
    root: Path,
    story_dir: Path,
    result: CheckResult,
    profile_override: str | None,
    review_pack_style_entries: list[tuple[Path, ReviewPackEntry]],
) -> None:
    configured_profile = (
        result.contract.style_lint.profile
        if result.contract is not None and result.contract.style_lint is not None
        else None
    )
    if configured_profile is None and profile_override is None:
        for manifest_path, entry in review_pack_style_entries:
            _add_error(
                result,
                manifest_path,
                f"Review-pack entry `{entry.id}` has style calibration "
                "metadata but no active style profile.",
            )
        return

    requested_profile = (
        profile_override if profile_override is not None else configured_profile
    )
    try:
        profile_path = resolve_style_profile_path(
            story_dir,
            configured_profile,
            profile_override,
        )
    except CreativeWriterError as exc:
        location = story_dir / requested_profile if requested_profile else story_dir
        _add_error(result, location, str(exc))
        return

    packet_dir = story_dir / "style-reference-packets"
    manifest_paths = (
        [
            path
            for path in sorted(packet_dir.glob("*.yml"))
            if path.name not in IGNORED_STYLE_REFERENCE_PACKET_FILES
            and path.is_file()
        ]
        if packet_dir.is_dir()
        else []
    )
    manifests: dict[str, Path] = {}
    invalid_manifest = False
    for manifest_path in manifest_paths:
        try:
            manifest = load_yaml_model(manifest_path, StyleReferencePacket)
        except CreativeWriterError as exc:
            _add_error(result, manifest_path, str(exc))
            invalid_manifest = True
            continue
        if manifest.id != manifest_path.stem:
            _add_error(
                result,
                manifest_path,
                f"Packet file declares ID {manifest.id}, expected {manifest_path.stem}",
            )
            invalid_manifest = True
            continue
        manifests[manifest.id] = manifest_path

    if invalid_manifest:
        return

    try:
        context = load_style_context(root, story_dir, profile_path)
    except CreativeWriterError as exc:
        _add_error(result, profile_path, str(exc))
        return

    for packet_id, manifest_path in manifests.items():
        if packet_id not in context.packets:
            _add_error(
                result,
                manifest_path,
                f"Style-reference packet {packet_id} is not declared by "
                "the configured profile.",
            )

    for metadata_error in validate_chapter_style_metadata(context, result.chapters):
        location, separator, message = metadata_error.partition(": ")
        _add_error(
            result,
            location if separator else profile_path,
            message if separator else metadata_error,
        )

    manuscript_paths = {
        chapter.front_matter.manuscript for chapter in result.chapters
    }
    for manifest_path, entry in review_pack_style_entries:
        for metadata_error in validate_review_pack_style_context(
            entry,
            context,
            manuscript_paths,
        ):
            _add_error(result, manifest_path, metadata_error)



def check_story(
    root: Path,
    slug: str,
    *,
    profile_override: str | None = None,
) -> CheckResult:
    """Run validation and style checks for one story."""

    story_dir = root / "stories" / slug
    result = CheckResult(story_slug=slug)
    report_dir = root / "build" / slug / "reports"
    ensure_directory(report_dir)
    result.report_path = report_dir / "coherence-report.md"

    if not story_dir.exists():
        _add_error(result, story_dir, "Story directory does not exist.")
        result.report_path.write_text(
            _render_report(
                result,
                story_dir,
                {
                    "characters": 0,
                    "clues": 0,
                    "locations": 0,
                    "timeline": 0,
                    "plot_devices": 0,
                },
                {},
                [],
            ),
            encoding="utf-8",
        )
        return result

    for artifact in MANDATORY_ARTIFACTS:
        target = story_dir / artifact
        if not target.exists():
            _add_error(result, target, "Missing mandatory artifact.")

    story_path = story_dir / "story.yml"
    contract_path = story_dir / "contract.yml"

    if story_path.exists():
        try:
            result.story = load_yaml_model(story_path, StoryConfig)
            result.story_title = result.story.title
        except CreativeWriterError as exc:
            _add_error(result, story_path, str(exc))

    if contract_path.exists():
        try:
            result.contract = load_yaml_model(contract_path, ContractConfig)
        except CreativeWriterError as exc:
            _add_error(result, contract_path, str(exc))

    characters_registry = _load_registry(
        story_dir, "characters.yml", CharactersRegistry, result
    )
    clues_registry = _load_registry(story_dir, "clues.yml", CluesRegistry, result)
    locations_registry = _load_registry(
        story_dir, "locations.yml", LocationsRegistry, result
    )
    timeline_registry = _load_registry(
        story_dir, "timeline.yml", TimelineRegistry, result
    )
    plot_devices_registry = _load_registry(
        story_dir, "plot_devices.yml", PlotDevicesRegistry, result
    )

    registry_ids = {
        "characters": (
            {item.id for item in characters_registry.characters}
            if characters_registry
            else set()
        ),
        "clues": ({item.id for item in clues_registry.clues} if clues_registry else set()),
        "locations": (
            {item.id for item in locations_registry.locations}
            if locations_registry
            else set()
        ),
        "timeline": (
            {item.id for item in timeline_registry.events}
            if timeline_registry
            else set()
        ),
        "plot_devices": (
            {item.id for item in plot_devices_registry.plot_devices}
            if plot_devices_registry
            else set()
        ),
    }
    scene_cards_by_chapter: dict[str, list[str]] = {}
    plot_devices = plot_devices_registry.plot_devices if plot_devices_registry else []

    if result.story:
        for chapter_name in result.story.chapters:
            chapter_path = story_dir / chapter_name
            if not chapter_path.exists():
                _add_error(result, chapter_path, "Listed chapter file does not exist.")
                continue

            try:
                chapter = load_chapter_document(story_dir, chapter_path)
            except CreativeWriterError as exc:
                _add_error(result, chapter_path, str(exc))
                continue

            result.chapters.append(chapter)

            if registry_ids["characters"]:
                unknown = sorted(
                    set(chapter.front_matter.characters) - registry_ids["characters"]
                )
                if unknown:
                    _add_error(
                        result,
                        chapter.stub_path,
                        f"Unknown characters referenced: {', '.join(unknown)}",
                    )

            if registry_ids["locations"]:
                unknown = sorted(
                    set(chapter.front_matter.locations) - registry_ids["locations"]
                )
                if unknown:
                    _add_error(
                        result,
                        chapter.stub_path,
                        f"Unknown locations referenced: {', '.join(unknown)}",
                    )

            if registry_ids["clues"]:
                clue_refs = set(chapter.front_matter.clues_introduced).union(
                    chapter.front_matter.clues_resolved
                )
                unknown = sorted(clue_refs - registry_ids["clues"])
                if unknown:
                    _add_error(
                        result,
                        chapter.stub_path,
                        f"Unknown clues referenced: {', '.join(unknown)}",
                    )

            if registry_ids["timeline"]:
                unknown = sorted(
                    set(chapter.front_matter.timeline_events) - registry_ids["timeline"]
                )
                if unknown:
                    _add_error(
                        result,
                        chapter.stub_path,
                        f"Unknown timeline events referenced: {', '.join(unknown)}",
                    )

            if chapter.front_matter.scene_cards_dir:
                scene_cards_dir = story_dir / chapter.front_matter.scene_cards_dir
                if not scene_cards_dir.exists():
                    _add_error(
                        result,
                        chapter.stub_path,
                        f"Missing scene cards directory: {chapter.front_matter.scene_cards_dir}",
                    )
                scene_cards_by_chapter[chapter.stub_path.name] = _scene_card_files(
                    story_dir, chapter.front_matter.scene_cards_dir
                )
            else:
                scene_cards_by_chapter[chapter.stub_path.name] = []

            plot_device_refs = set(chapter.front_matter.plot_devices)
            unknown_plot_devices = sorted(
                plot_device_refs - registry_ids["plot_devices"]
            )
            if unknown_plot_devices:
                _add_error(
                    result,
                    chapter.stub_path,
                    "Unknown plot devices referenced: "
                    + ", ".join(unknown_plot_devices),
                )

            listed_images = set(chapter.front_matter.images)
            for image_path in sorted(listed_images):
                image_file = story_dir / image_path
                if not image_file.exists():
                    _add_error(
                        result,
                        chapter.stub_path,
                        f"Listed image does not exist: {image_path}",
                    )

            referenced_images = _extract_image_paths(chapter.manuscript_body)
            for image_path in sorted(referenced_images):
                image_file = story_dir / image_path
                if not image_file.exists():
                    _add_error(
                        result,
                        chapter.manuscript_path,
                        f"Referenced image does not exist: {image_path}",
                    )

            unlisted_images = sorted(referenced_images - listed_images)
            if unlisted_images:
                _add_warning(
                    result,
                    chapter.stub_path,
                    "Images referenced in the manuscript are not listed in the stub: "
                    + ", ".join(unlisted_images),
                )

            if result.contract:
                for warning in run_surface_heuristics(
                    chapter.manuscript_body,
                    result.contract.lint,
                ):
                    _add_warning(
                        result,
                        chapter.manuscript_path,
                        warning.observed,
                    )

    chapter_index = {
        chapter.front_matter.manuscript: (
            chapter.front_matter.title,
            chapter.front_matter.summary,
        )
        for chapter in result.chapters
    }
    review_pack_discovery_failed = False
    try:
        review_pack_paths = review_pack_manifest_paths(story_dir)
    except CreativeWriterError as exc:
        location, separator, message = str(exc).partition(": ")
        _add_error(
            result,
            location if separator else story_dir / "review-packs",
            message if separator else str(exc),
        )
        review_pack_paths = []
        review_pack_discovery_failed = True
    if (
        result.contract
        and result.contract.review_mode == "excerpt_pack"
        and not review_pack_paths
        and not review_pack_discovery_failed
    ):
        _add_warning(
            result,
            story_dir / "review-packs",
            "review_mode is excerpt_pack but no review-pack manifests were found.",
        )
    review_pack_style_entries: list[tuple[Path, ReviewPackEntry]] = []
    for manifest_path in review_pack_paths:
        try:
            _manifest, resolved_entries = validate_review_pack_manifest(
                story_dir,
                manifest_path,
                chapter_index,
            )
        except CreativeWriterError as exc:
            _add_error(result, manifest_path, str(exc))
            continue
        review_pack_style_entries.extend(
            (manifest_path, resolved.entry)
            for resolved in resolved_entries
            if resolved.entry.style is not None
        )

    _validate_configured_style(
        root,
        story_dir,
        result,
        profile_override,
        review_pack_style_entries,
    )

    report_body = _render_report(
        result,
        story_dir,
        {
            "characters": len(registry_ids["characters"]),
            "clues": len(registry_ids["clues"]),
            "locations": len(registry_ids["locations"]),
            "timeline": len(registry_ids["timeline"]),
            "plot_devices": len(registry_ids["plot_devices"]),
        },
        scene_cards_by_chapter,
        plot_devices,
    )
    result.report_path.write_text(report_body, encoding="utf-8")
    return result


def validate_review_pack_style_context(
    entry: ReviewPackEntry,
    context: StyleContext,
    manuscript_paths: set[str],
) -> list[str]:
    """Cross-check optional calibration metadata against the active profile."""

    style = entry.style
    if style is None:
        return []

    prefix = f"Review-pack entry `{entry.id}`"
    errors: list[str] = []
    if style.profile_id != context.profile.profile_id:
        errors.append(
            f"{prefix} profile ID `{style.profile_id}` does not match active "
            f"profile `{context.profile.profile_id}`"
        )
    if style.profile_version != context.profile.version:
        errors.append(
            f"{prefix} profile version `{style.profile_version}` does not "
            f"match active profile version `{context.profile.version}`"
        )

    known_roles = {role.id for role in context.profile.roles}
    if style.narrative_role not in known_roles:
        errors.append(
            f"{prefix} uses unknown style role `{style.narrative_role}`"
        )

    known_claims = {
        claim_id
        for rule in context.profile.rules
        for claim_id in rule.claim_ids
    }
    for claim_id in style.claim_ids:
        if claim_id not in known_claims:
            errors.append(
                f"{prefix} uses unknown Phase 2B claim `{claim_id}`"
            )

    if entry.manuscript not in manuscript_paths:
        errors.append(
            f"{prefix} uses unknown configured manuscript "
            f"`{entry.manuscript}`"
        )
    return errors
