"""Command-line entrypoint."""

from __future__ import annotations

import argparse
import sys

from creative_writer.building import build_story
from creative_writer.checks import check_story
from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import repo_root
from creative_writer.novellas import (
    clear_ingested,
    export_novella,
    import_novella,
    resolve_novellas_dir,
)
from creative_writer.scaffold import create_story


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

    check = subparsers.add_parser("check", help="Run coherence and style checks.")
    check.add_argument("--story", required=True, help="Story slug.")

    epub = subparsers.add_parser("epub", help="Build an EPUB for a story.")
    epub.add_argument("--story", required=True, help="Story slug.")

    pdf = subparsers.add_parser("pdf", help="Build a PDF for a story.")
    pdf.add_argument("--story", required=True, help="Story slug.")

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

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface."""

    parser = build_parser()
    args = parser.parse_args(argv)
    root = repo_root()

    try:
        if args.command == "init-story":
            story_dir = create_story(root, args.story, args.kind, args.title)
            print(f"Created story scaffold at {story_dir}")
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
    except CreativeWriterError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
