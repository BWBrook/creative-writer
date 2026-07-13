# Original Reference Corpus

This subtree retains the canonical and comparative Wells sources for the
*Time Expedition* anthology. It is reference material, not anthology
manuscript or planning prose.

## Authority map

- *The Time Machine* is the sole story-world canon and primary style anchor.
  It governs the Time Traveller, fictional continuity, frame architecture,
  reported first-person voice, scientific exposition, and speculative method.
- *The Invisible Man* is a secondary style anchor for sustained dialogue,
  social interaction, class register, comic friction, concealment, speech
  attribution, and crowd response. It contributes no fictional continuity to
  *Time Expedition*.

Where the books differ, *The Time Machine* governs the new expeditions.

## Files

- `h-g-wells_the-time-machine.epub`: unchanged compatible Standard Ebooks EPUB.
- `h-g-wells_the-invisible-man.epub`: unchanged compatible Standard Ebooks EPUB.
- `sources.yml`: authority roles, provenance, retrieval details, checksums,
  and derivation metadata for both works.
- `text/the-time-machine.md`: chapters I-XII and epilogue in source order.
- `text/the-invisible-man.md`: chapters I-XXVIII and epilogue in source order.

The EPUBs are the archival authorities for this checkout. The Markdown exists
for search, structural comparison, quotation checks, and the later Wells style
study. Regenerate derived text from the pinned EPUBs rather than editing it as
anthology prose.

## Canon boundary

Do not import dialogue, characters, events, technology, machine designs,
visual motifs, or other inventions from later film, television, game,
audiobook, or illustrated adaptations. Do not treat *The Invisible Man* as
evidence for the fictional continuity or narrator architecture of *Time
Expedition*.

## Reproduce the Markdown

From the repository root in `zsh`:

```zsh
tmpdir=$(mktemp -d /tmp/time-expedition-extract.XXXXXX)
trap 'rm -rf "$tmpdir"' EXIT

unzip -q stories/time-expedition/original/h-g-wells_the-time-machine.epub \
  -d "$tmpdir/time-machine"
time_machine_chapters=("$tmpdir"/time-machine/epub/text/chapter-{1..12}.xhtml)
pandoc "${time_machine_chapters[@]}" \
  "$tmpdir/time-machine/epub/text/epilogue.xhtml" \
  --from=html --to=gfm-raw_html --wrap=none \
  --output=stories/time-expedition/original/text/the-time-machine.md

unzip -q stories/time-expedition/original/h-g-wells_the-invisible-man.epub \
  -d "$tmpdir/invisible-man"
invisible_man_chapters=("$tmpdir"/invisible-man/epub/text/chapter-{1..28}.xhtml)
pandoc "${invisible_man_chapters[@]}" \
  "$tmpdir/invisible-man/epub/text/epilogue.xhtml" \
  --from=html --to=gfm-raw_html --wrap=none \
  --output=stories/time-expedition/original/text/the-invisible-man.md
```

Both extractions deliberately exclude covers, imprints, colophons,
uncopyright pages, and other ebook packaging. See `sources.yml` for pinned
fingerprints and upstream provenance. The rights records there are not legal
advice.
