"""Command-line entrypoint."""

from __future__ import annotations

import argparse
import sys

from creative_writer.building import build_story
from creative_writer.checks import check_story
from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import repo_root
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
    except CreativeWriterError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
