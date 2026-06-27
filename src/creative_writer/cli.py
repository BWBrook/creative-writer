"""Command-line entrypoint."""

from __future__ import annotations

import argparse
import sys

from creative_writer.ai_audit import generate_ai_writing_audit
from creative_writer.building import build_story
from creative_writer.checks import check_story
from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import repo_root
from creative_writer.kindle import kindle_preflight, send_to_kindle, store_smtp_password
from creative_writer.novellas import (
    clear_ingested,
    export_novella,
    import_novella,
    resolve_novellas_dir,
)
from creative_writer.review_packs import generate_review_pack
from creative_writer.scaffold import create_story, list_style_cards
from creative_writer.stats import generate_story_statistics


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""

    parser = argparse.ArgumentParser(
        prog="creative-writer",
        description="Story scaffolding, coherence checks, and document builds.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_story = subparsers.add_parser(
        "init-story",
        help="Create a new story directory with mandatory and optional templates.",
    )
    init_story.add_argument("--story", required=True, help="Story slug.")
    init_story.add_argument(
        "--kind",
        default="original",
        choices=["original", "pastiche"],
        help="Story type.",
    )
    init_story.add_argument("--title", help="Optional title override.")
    init_story.add_argument(
        "--style-card",
        help="Optional built-in style card key or path to a custom Markdown style card.",
    )

    subparsers.add_parser(
        "style-cards",
        help="List the built-in style cards available for new story scaffolds.",
    )

    check = subparsers.add_parser("check", help="Run coherence and style checks.")
    check.add_argument("--story", required=True, help="Story slug.")

    epub = subparsers.add_parser("epub", help="Build an EPUB for a story.")
    epub.add_argument("--story", required=True, help="Story slug.")

    pdf = subparsers.add_parser("pdf", help="Build a PDF for a story.")
    pdf.add_argument("--story", required=True, help="Story slug.")

    stats = subparsers.add_parser(
        "stats",
        help="Generate a manuscript statistics report for a story.",
    )
    stats.add_argument("--story", required=True, help="Story slug.")

    ai_audit = subparsers.add_parser(
        "ai-audit",
        help="Run the audit-ai-writing scanner over a story manuscript.",
    )
    ai_audit.add_argument("--story", required=True, help="Story slug.")
    ai_audit.add_argument(
        "--genre",
        default="narrative",
        choices=["email", "general", "marketing", "narrative", "scientific", "wiki"],
        help="Scanner genre profile.",
    )

    review_pack = subparsers.add_parser(
        "review-pack",
        help="Build a targeted excerpt review pack from a story-local manifest.",
    )
    review_pack.add_argument("--story", required=True, help="Story slug.")
    review_pack.add_argument(
        "--pack", required=True, help="Review-pack manifest name (with or without .yml)."
    )

    novellas_path = subparsers.add_parser(
        "novellas-path", help="Print the resolved OneDrive Novellas directory."
    )

    import_novella_parser = subparsers.add_parser(
        "import-novella",
        help="Import a DOCX from OneDrive Documents/Novellas into ingested/ as Markdown.",
    )
    import_novella_parser.add_argument(
        "--source", required=True, help="DOCX filename inside the Novellas folder."
    )

    export_novella_parser = subparsers.add_parser(
        "export-novella",
        help="Export a repo Markdown file to DOCX in OneDrive Documents/Novellas.",
    )
    export_novella_parser.add_argument(
        "--input", required=True, help="Repo-relative or absolute Markdown path."
    )
    export_novella_parser.add_argument(
        "--output-name",
        help="Optional DOCX filename override for the Novellas folder.",
    )

    clear_ingested_parser = subparsers.add_parser(
        "clear-ingested",
        help="Clear an ingested Markdown source after a story has been safely back-fitted.",
    )
    clear_ingested_parser.add_argument(
        "--story",
        required=True,
        help="Story slug whose ingested staging files should be removed.",
    )

    kindle_preflight_parser = subparsers.add_parser(
        "kindle-preflight",
        help="Build the EPUB and verify Kindle delivery config and SMTP credentials.",
    )
    kindle_preflight_parser.add_argument(
        "--story", required=True, help="Story slug."
    )

    kindle_parser = subparsers.add_parser(
        "kindle",
        help="Build the EPUB and email it to the configured Send-to-Kindle address.",
    )
    kindle_parser.add_argument("--story", required=True, help="Story slug.")

    subparsers.add_parser(
        "kindle-store-password",
        help="Store the configured SMTP password in the macOS Keychain.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface."""

    parser = build_parser()
    args = parser.parse_args(argv)
    root = repo_root()

    try:
        if args.command == "init-story":
            story_dir = create_story(
                root,
                args.story,
                args.kind,
                args.title,
                args.style_card,
            )
            print(f"Created story scaffold at {story_dir}")
            return 0

        if args.command == "style-cards":
            cards = list_style_cards(root)
            if not cards:
                print("No built-in style cards found.")
                return 0
            for key, title in cards:
                print(f"{key}\t{title}")
            return 0

        if args.command == "check":
            result = check_story(root, args.story)
            print(f"Coherence report written to {result.report_path}")
            if result.ok:
                if result.warnings:
                    print(f"Check completed with {len(result.warnings)} warning(s).")
                else:
                    print("Check completed without blocking issues.")
                return 0
            print(f"Check failed with {len(result.errors)} blocking issue(s).", file=sys.stderr)
            return 1

        if args.command in {"epub", "pdf"}:
            output_path = build_story(root, args.story, args.command)
            print(f"Built {output_path}")
            return 0

        if args.command == "stats":
            result = generate_story_statistics(root, args.story)
            print(f"Statistics report written to {result.report_path}")
            print(
                f"Total manuscript words: {result.manuscript_total_words:,} "
                f"across {result.chapter_count} chapter(s)."
            )
            return 0

        if args.command == "ai-audit":
            result = generate_ai_writing_audit(root, args.story, args.genre)
            print(f"AI-writing audit report written to {result.report_path}")
            print(f"Scanned {result.chapter_count} chapter(s) with {result.script_path}.")
            return 0

        if args.command == "review-pack":
            result = generate_review_pack(root, args.story, args.pack)
            print(f"Review pack written to {result.output_path}")
            print(f"Manifest: {result.manifest_path}")
            print(f"Entries: {result.entry_count}")
            return 0

        if args.command == "novellas-path":
            print(resolve_novellas_dir())
            return 0

        if args.command == "import-novella":
            output_path = import_novella(root, args.source)
            print(f"Imported {output_path}")
            return 0

        if args.command == "export-novella":
            output_path = export_novella(root, args.input, args.output_name)
            print(f"Exported {output_path}")
            return 0

        if args.command == "clear-ingested":
            removed = clear_ingested(root, args.story)
            print(f"Cleared {len(removed)} staging path(s) for {args.story}:")
            for path in removed:
                print(path)
            return 0

        if args.command == "kindle-preflight":
            result = kindle_preflight(root, args.story)
            print(f"Kindle delivery is ready for {result.story_title}.")
            print(f"Attachment: {result.attachment_path}")
            print(f"Recipient: {result.recipient}")
            print(f"Report: {result.report_path}")
            return 0

        if args.command == "kindle":
            result = send_to_kindle(root, args.story)
            print(f"Sent {result.attachment_path.name} to {result.recipient}")
            print(f"Report: {result.report_path}")
            return 0

        if args.command == "kindle-store-password":
            key = store_smtp_password(root)
            print(f"Stored SMTP password in Keychain entry {key}")
            return 0
    except CreativeWriterError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
