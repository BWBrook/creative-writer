# Original Reference Corpus

This subtree retains the closed reference corpus for the *Time Expedition*
forensic source study. It is reference material, not anthology manuscript,
planning prose, or completed analysis.

## Authority map

| Tier | Retained source | Authority |
|---:|---|---|
| 1 | H. G. Wells, *The Time Machine* | Sole story-world canon and primary style authority |
| 2 | H. G. Wells, *The Invisible Man* | Dialogue, social register, and comic friction |
| 2 | H. G. Wells, *The Island of Doctor Moreau* | Retrospective scientific adventure and moral pressure |
| 2 | H. G. Wells, *The War of the Worlds* | Catastrophe, landscape observation, and public behaviour |
| 2 | H. G. Wells, four selected short stories | Bounded short-form and role-specific evidence |
| 3 | H. G. Wells, *Certain Personal Matters* | Period nonfiction, explanation, humour, and idiom |
| 3 | H. G. Wells, *Text Book of Biology, Part 1* | Scientific vocabulary, classification, and exposition |
| 4 | Grant Allen, *The British Barbarians* | Scientific-romance and time-visitor control |
| 4 | Arthur Conan Doyle, *A Desert Drama* | Adventure and ensemble-dialogue control |
| 4 | Rudyard Kipling, *The Day's Work* | Technical-work and professional-register control |
| 4 | Richard Marsh, *The Beetle* | Sensational-fiction and horror-escalation control |
| 4 | H. Rider Haggard, *King Solomon's Mines* | Adventure architecture and motivation control |

Where the Wells sources differ, *The Time Machine* governs continuity and the
new expeditions. The five other authors are negative or comparative controls
only: they cannot prescribe Wellsian style, authorise phrase borrowing, supply
continuity, or justify a feature merely because it is historically plausible.
For *King Solomon's Mines*, permitted comparison is limited to adventure
motivation, expedition assembly, discovery sequence, danger escalation,
journey architecture, and the period framing of mysterious travel. Its
characters, places, incidents, lost-world content, imperial assumptions, and
racial ideology are prohibited.

Arthur Conan Doyle's *The Lost World* is an unacquired Tier 5 metadata record,
not part of this retained corpus. Its only possible future role is a
post-window negative diagnostic for anachronistic adventure architecture or a
later lost-world idiom. No EPUB, Markdown, conversion, or positive authority
exists for it.

## File inventory

The retained corpus contains exactly twelve EPUBs:

- `h-g-wells_the-time-machine.epub`
- `h-g-wells_the-invisible-man.epub`
- `h-g-wells_the-island-of-doctor-moreau.epub`
- `h-g-wells_the-war-of-the-worlds.epub`
- `h-g-wells_short-fiction.epub`
- `h-g-wells_certain-personal-matters.epub`
- `h-g-wells_text-book-of-biology-part-1.epub`
- `grant-allen_the-british-barbarians.epub`
- `arthur-conan-doyle_a-desert-drama.epub`
- `rudyard-kipling_the-days-work.epub`
- `richard-marsh_the-beetle.epub`
- `h-rider-haggard_king-solomons-mines.epub`

The derived interface contains exactly fifteen Markdown witnesses. Its eleven
full-work files are:

- `text/the-time-machine.md`
- `text/the-invisible-man.md`
- `text/the-island-of-doctor-moreau.md`
- `text/the-war-of-the-worlds.md`
- `text/certain-personal-matters.md`
- `text/text-book-of-biology-part-1.md`
- `text/the-british-barbarians.md`
- `text/a-desert-drama.md`
- `text/the-days-work.md`
- `text/the-beetle.md`
- `text/king-solomons-mines.md`

The other four witnesses are the selected stories listed below.
`sources.yml` records every retained EPUB and Markdown SHA-256, release
metadata, derivation input, provenance, rights, and authority role. The EPUBs
remain the archival authorities.

`filters/remove-excluded-packaging-links.lua` removes links into excluded
Standard Ebooks apparatus. `filters/remove-project-gutenberg-boilerplate.lua`
also removes Project Gutenberg boilerplate containers, images, front-cover
headings, leading singular transcriber notes, and terminal transcriber/back
cover matter. Non-empty literary `pgmonospaced` Divs are retained; that class
alone does not identify packaging. A singular transcriber-note marker triggers
leading-preamble removal only when it occurs before the first horizontal rule;
once that rule has been reached, a later marker cannot move the document start
or discard preceding literary text. Project Gutenberg derivations apply the
packaging-link filter first and the Gutenberg filter second. In *A Desert
Drama*, `OEBPS/6605053776549637356_21768-h-6.htm.html` is the final linear
literary member and must be included; the second filter removes the terminal
Project Gutenberg licence and packaging matter from that member.

The retained short-fiction EPUB contains works that are not admitted. It has
no aggregate Markdown file. Only these four fingerprinted selections enter
the derived interface, in this order:

1. `text/selected-short-fiction/the-plattner-story.md`
2. `text/selected-short-fiction/the-sea-raiders.md`
3. `text/selected-short-fiction/the-crystal-egg.md`
4. `text/selected-short-fiction/the-star.md`

The exact source fingerprints and archive metadata are recorded in
`.superpowers/sdd/corpus-scout-report.md`; the verified filter, derivation,
Markdown fingerprints, and boundary evidence are recorded in
`.superpowers/sdd/task-3a-report.md`.

## Regenerate the Markdown

Run from the repository root in `zsh`. These commands use explicit literary
inputs; do not substitute EPUB-wide conversion.

```zsh
tmpdir=$(mktemp -d /tmp/time-expedition-extract.XXXXXX)
trap 'rm -rf "$tmpdir"' EXIT
filter=stories/time-expedition/original/filters/remove-excluded-packaging-links.lua
gutenberg_filter=stories/time-expedition/original/filters/remove-project-gutenberg-boilerplate.lua

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

unzip -q stories/time-expedition/original/h-g-wells_short-fiction.epub \
  -d "$tmpdir/short-fiction"
for selection in the-plattner-story the-sea-raiders the-crystal-egg the-star; do
  pandoc "$tmpdir/short-fiction/epub/text/$selection.xhtml" \
    --from=html --to=gfm-raw_html --wrap=none \
    --lua-filter="$filter" \
    --output="stories/time-expedition/original/text/selected-short-fiction/$selection.md"
done

unzip -q stories/time-expedition/original/h-g-wells_certain-personal-matters.epub \
  -d "$tmpdir/certain-personal-matters"
certain_inputs=("$tmpdir"/certain-personal-matters/OEBPS/4588169185347793760_17508-h-{0..6}.htm.html)
pandoc "${certain_inputs[@]}" \
  --from=html --to=gfm-raw_html --wrap=none \
  --lua-filter="$filter" --lua-filter="$gutenberg_filter" \
  --output=stories/time-expedition/original/text/certain-personal-matters.md

unzip -q stories/time-expedition/original/h-g-wells_text-book-of-biology-part-1.epub \
  -d "$tmpdir/biology"
biology_inputs=("$tmpdir"/biology/OEBPS/6496333017750439206_21781-h-{0..6}.htm.html)
pandoc "${biology_inputs[@]}" \
  --from=html --to=gfm-raw_html --wrap=none \
  --lua-filter="$filter" --lua-filter="$gutenberg_filter" \
  --output=stories/time-expedition/original/text/text-book-of-biology-part-1.md

unzip -q stories/time-expedition/original/grant-allen_the-british-barbarians.epub \
  -d "$tmpdir/british-barbarians"
allen_inputs=("$tmpdir"/british-barbarians/OEBPS/137036109479442431_4340-h-{0..4}.htm.html)
pandoc "${allen_inputs[@]}" \
  --from=html --to=gfm-raw_html --wrap=none \
  --lua-filter="$filter" --lua-filter="$gutenberg_filter" \
  --output=stories/time-expedition/original/text/the-british-barbarians.md

unzip -q stories/time-expedition/original/arthur-conan-doyle_a-desert-drama.epub \
  -d "$tmpdir/desert-drama"
desert_inputs=("$tmpdir"/desert-drama/OEBPS/6605053776549637356_21768-h-{0..6}.htm.html)
pandoc "${desert_inputs[@]}" \
  --from=html --to=gfm-raw_html --wrap=none \
  --lua-filter="$filter" --lua-filter="$gutenberg_filter" \
  --output=stories/time-expedition/original/text/a-desert-drama.md

unzip -q stories/time-expedition/original/rudyard-kipling_the-days-work.epub \
  -d "$tmpdir/days-work"
kipling_inputs=("$tmpdir"/days-work/OEBPS/3331954580391865763_2569-h-{1..13}.htm.html)
pandoc "${kipling_inputs[@]}" \
  --from=html --to=gfm-raw_html --wrap=none \
  --lua-filter="$filter" --lua-filter="$gutenberg_filter" \
  --output=stories/time-expedition/original/text/the-days-work.md

unzip -q stories/time-expedition/original/richard-marsh_the-beetle.epub \
  -d "$tmpdir/beetle"
beetle_inputs=("$tmpdir"/beetle/OEBPS/5766576426201918088_5164-h-{0..10}.htm.html)
pandoc "${beetle_inputs[@]}" \
  --from=html --to=gfm-raw_html --wrap=none \
  --lua-filter="$filter" --lua-filter="$gutenberg_filter" \
  --output=stories/time-expedition/original/text/the-beetle.md

unzip -q stories/time-expedition/original/h-rider-haggard_king-solomons-mines.epub \
  -d "$tmpdir/king-solomons-mines"
haggard_inputs=("$tmpdir"/king-solomons-mines/epub/text/chapter-{1..20}.xhtml)
pandoc "${haggard_inputs[@]}" \
  --from=html --to=gfm-raw_html --wrap=none \
  --lua-filter="$filter" \
  --output=stories/time-expedition/original/text/king-solomons-mines.md
```

The explicit ranges exclude title, contents, cover, imprint, endnote,
colophon, uncopyright, licence, and other packaging members. Regenerated files
must remain non-empty UTF-8 and match the SHA-256 values in `sources.yml`.
Detailed source analysis remains prohibited until the generated admission
report has been reviewed by a human.
