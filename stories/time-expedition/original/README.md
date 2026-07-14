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
- *The Island of Doctor Moreau* is a bounded secondary witness for retrospective
  first-person narration, scientific argument, moral pressure, and dialogue
  under stress. It contributes no fictional continuity, Moreau characters, or
  inventions.
- *The War of the Worlds* is a bounded secondary witness for catastrophe,
  landscape observation, public behaviour, and movement from evidence to
  speculation. It contributes no fictional continuity or Martian inventions.

Where the books differ, *The Time Machine* governs the new expeditions.

## Files

- `h-g-wells_the-time-machine.epub`: unchanged compatible Standard Ebooks EPUB.
- `h-g-wells_the-invisible-man.epub`: unchanged compatible Standard Ebooks EPUB.
- `h-g-wells_the-island-of-doctor-moreau.epub`: unchanged compatible Standard Ebooks EPUB.
- `h-g-wells_the-war-of-the-worlds.epub`: unchanged compatible Standard Ebooks EPUB.
- `filters/remove-excluded-packaging-links.lua`: tracked Pandoc filter that
  removes links into excluded ebook apparatus files.
- `sources.yml`: authority roles, provenance, retrieval details, checksums,
  and derivation metadata for all four retained works.
- `text/the-time-machine.md`: chapters I-XII and epilogue in source order.
- `text/the-invisible-man.md`: chapters I-XXVIII and epilogue in source order.
- `text/the-island-of-doctor-moreau.md`: chapters I-XXII in source order.
- `text/the-war-of-the-worlds.md`: Books I-II and chapters I-XVII in source order.

The EPUBs are the archival authorities for this checkout. The Markdown exists
for search, structural comparison, quotation checks, and the later Wells style
study. Regenerate derived text from the pinned EPUBs rather than editing it as
anthology prose.

## Canon boundary

Do not import dialogue, characters, events, technology, machine designs,
visual motifs, or other inventions from later film, television, game,
audiobook, or illustrated adaptations. Do not treat *The Invisible Man*, *The
Island of Doctor Moreau*, or *The War of the Worlds* as evidence for the
fictional continuity or governing narrator architecture of *Time Expedition*.
Proposed short fiction, nonfiction, and control sources remain outside
`original/` until the human corpus review.

## Reproduce the Markdown

From the repository root in `zsh`:

```zsh
tmpdir=$(mktemp -d /tmp/time-expedition-extract.XXXXXX)
trap 'rm -rf "$tmpdir"' EXIT
filter=stories/time-expedition/original/filters/remove-excluded-packaging-links.lua

unzip -q stories/time-expedition/original/h-g-wells_the-time-machine.epub \
  -d "$tmpdir/time-machine"
time_machine_chapters=("$tmpdir"/time-machine/epub/text/chapter-{1..12}.xhtml)
pandoc "${time_machine_chapters[@]}" \
  "$tmpdir/time-machine/epub/text/epilogue.xhtml" \
  --from=html --to=gfm-raw_html --wrap=none \
  --lua-filter="$filter" \
  --output=stories/time-expedition/original/text/the-time-machine.md

unzip -q stories/time-expedition/original/h-g-wells_the-invisible-man.epub \
  -d "$tmpdir/invisible-man"
invisible_man_chapters=("$tmpdir"/invisible-man/epub/text/chapter-{1..28}.xhtml)
pandoc "${invisible_man_chapters[@]}" \
  "$tmpdir/invisible-man/epub/text/epilogue.xhtml" \
  --from=html --to=gfm-raw_html --wrap=none \
  --lua-filter="$filter" \
  --output=stories/time-expedition/original/text/the-invisible-man.md

unzip -q stories/time-expedition/original/h-g-wells_the-island-of-doctor-moreau.epub \
  -d "$tmpdir/moreau"
moreau_chapters=("$tmpdir"/moreau/epub/text/chapter-{1..22}.xhtml)
pandoc "${moreau_chapters[@]}" \
  --from=html --to=gfm-raw_html --wrap=none \
  --lua-filter="$filter" \
  --output=stories/time-expedition/original/text/the-island-of-doctor-moreau.md

unzip -q stories/time-expedition/original/h-g-wells_the-war-of-the-worlds.epub \
  -d "$tmpdir/war"
war_book_one=("$tmpdir/war/epub/text/book-1.xhtml" "$tmpdir"/war/epub/text/chapter-1-{1..17}.xhtml)
war_book_two=("$tmpdir/war/epub/text/book-2.xhtml" "$tmpdir"/war/epub/text/chapter-2-{1..10}.xhtml)
pandoc "${war_book_one[@]}" "${war_book_two[@]}" \
  --from=html --to=gfm-raw_html --wrap=none \
  --lua-filter="$filter" \
  --output=stories/time-expedition/original/text/the-war-of-the-worlds.md
```

Both extractions deliberately exclude covers, imprints, colophons,
uncopyright pages, and other ebook packaging. The tracked Pandoc filter also
removes any links into excluded apparatus files so the derived literary text
has no dangling packaging links. See `sources.yml` for pinned fingerprints and
upstream provenance. The rights records there are not legal advice. *The Time
Machine* governs all conflicts among the retained witnesses.
