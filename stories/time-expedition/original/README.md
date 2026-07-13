# Original Reference Corpus

This subtree retains the primary canonical and comparative sources for the
*Time Expedition* anthology. It is reference material, not anthology
manuscript or planning prose.

## Files

- `h-g-wells_the-time-machine.epub`: unchanged compatible EPUB downloaded
  from Standard Ebooks.
- `sources.yml`: authority roles, edition provenance, retrieval details,
  checksums, and derivation metadata.
- `text/the-time-machine.md`: working Markdown containing Wells's chapters
  I-XII and epilogue in source order.

At this intermediate commit, *The Time Machine* is the story-world canon and
primary style anchor. Task 4 installs the approved secondary dialogue and
social-style anchor.

The EPUB is the archival authority for this source. The Markdown exists for
search, structural comparison, quotation checks, and the later Wells style
study. Regenerate it from the pinned EPUB rather than editing it as though it
were anthology prose.

## Authority boundary

*The Time Machine* controls Time Traveller continuity, frame architecture,
reported voice, scientific exposition, and speculative method. Do not import
dialogue, characters, machine designs, visual motifs, or other inventions from
later film, television, game, audiobook, or illustrated adaptations.

## Reproduce the Time Machine Markdown

From the repository root in `zsh`:

```zsh
tmpdir=$(mktemp -d /tmp/time-expedition-extract.XXXXXX)
trap 'rm -rf "$tmpdir"' EXIT
unzip -q stories/time-expedition/original/h-g-wells_the-time-machine.epub \
  -d "$tmpdir/unpacked"
chapter_files=("$tmpdir"/unpacked/epub/text/chapter-{1..12}.xhtml)
pandoc "${chapter_files[@]}" \
  "$tmpdir/unpacked/epub/text/epilogue.xhtml" \
  --from=html \
  --to=gfm-raw_html \
  --wrap=none \
  --output=stories/time-expedition/original/text/the-time-machine.md
```

The extraction deliberately excludes the cover, imprint, endnotes, colophon,
and uncopyright pages. See `sources.yml` for the pinned artifact fingerprint
and upstream provenance. The rights note there records source context and is
not legal advice.
