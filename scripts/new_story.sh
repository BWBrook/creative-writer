#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 1 || $# -gt 4 ]]; then
  echo "Usage: scripts/new_story.sh <story-slug> [original|pastiche] [title] [style-card-or-path]" >&2
  exit 1
fi

story_slug="$1"
story_kind="${2:-original}"
story_title="${3:-}"
style_card="${4:-}"

cmd=(uv run creative-writer init-story --story "$story_slug" --kind "$story_kind")

if [[ -n "$story_title" ]]; then
  cmd+=(--title "$story_title")
fi

if [[ -n "$style_card" ]]; then
  cmd+=(--style-card "$style_card")
fi

"${cmd[@]}"
