#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 1 || $# -gt 3 ]]; then
  echo "Usage: scripts/new_story.sh <story-slug> [original|pastiche] [title]" >&2
  exit 1
fi

story_slug="$1"
story_kind="${2:-original}"
story_title="${3:-}"

cmd=(uv run creative-writer init-story --story "$story_slug" --kind "$story_kind")

if [[ -n "$story_title" ]]; then
  cmd+=(--title "$story_title")
fi

"${cmd[@]}"
