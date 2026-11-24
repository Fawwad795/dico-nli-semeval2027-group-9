# Validation standards

What `deck.py validate` (and the validate step inside `build`) checks, every finding code the code can emit, how to resolve each one, and what automation cannot judge. The code in `scripts/pcv/` is what runs. If this file and the code disagree, fix the disagreement; do not trust the prose over the code.

## How findings work

Each finding is a JSON object written to `<out>/validation/findings.json`:

```json
{"code": "text-clipped", "severity": "critical", "category": "layout", "slide": 3,
 "message": "...", "evidence": {"path": "div:nth-child(2) > p:nth-child(1)", "...": "..."},
 "fix": {"kind": "shrink-text", "...": "..."}, "status": "open"}
```

- `slide` is the 1-based slide number, or `null` for a deck-level finding.
- `evidence.path` is the element path relative to the slide root (`tag:nth-child(n) > ...`). Open the slide HTML and follow it to find the element.
- Severity drives scoring and status (see `scoring-rubric.md`). **critical**: the deck is NOT READY while it is open, and its category is capped at 4. **major**: -1 from the category cap and READY WITH WARNINGS at best. **minor**: -0.25 from the cap, at most -2 per category. **info**: a note in the report, with no effect on score or status.
- Validation order: render-manifest errors, then per slide the geometry checks (`checks_dom.check_slide`), the image checks (`checks_image.check_image`) and the contrast checks (`check_contrast`), then deck-level consistency (`check_deck`), then content (`check_content`), then the output files (`check_pptx`, `check_pdf`, `renderback`), and finally the findings from a valid `review/review.json`. The fix loop (`deck.py fix`, and `build` without `--no-fix`) validates without the output stage.

Some failures stop the run with an exception instead of producing a finding: the viewport drifting from the configured size or scale, a screenshot whose pixel size is wrong, a page load timing out, a canvas that is not 16:9 at `assemble`, slides missing from the render manifest (`slides not rendered: [...]`), and a `rules.number_policy` value other than `off`, `critical`, `major`, `minor` or `info` (an `AssertionError` in `util.finding`). Read the traceback; nothing is scored.

## Markup hooks and opt-outs

`data-pcv-allow` takes a space-separated list. It applies to the element that carries it **and every descendant** (the inspector uses `closest()`). Each opt-out is an explicit, deliberate claim that the flagged condition is intended. Use it on the smallest element that needs it, never on the slide root to silence a slide.

| Hook | Switches off | Does not switch off |
|---|---|---|
| `data-pcv-allow="overlap"` | `text-overlap` (on either text, or on either text's block), `text-over-graphic` (on the text or on the graphic) | `text-clipped`, `text-overflows-box` |
| `data-pcv-allow="small"` | `text-too-small` | `off-scale-font-size` |
| `data-pcv-allow="bleed"` | `text-out-of-bounds` and `outside-safe-area` (on text), `graphic-out-of-bounds` (on a graphic) | `text-clipped` |
| `data-pcv-allow="contrast"` | `low-contrast` | nothing else |
| `data-pcv-allow="spelling"` | `spelling` | `doubled-word`, number checks |
| `data-pcv-allow="decor"` | `text-over-graphic`, on the graphic side; `aria-hidden="true"` on the graphic element itself has the same effect | `graphic-out-of-bounds` |
| `data-pcv-nocheck` (`rules.nocheck_selector`) | `unsupported-number`, numbered `[n]` citation markers, `doubled-word`, `spelling`, the `dense-slide` word count | `data-ref` keys, every geometry, font and contrast check |
| `data-pcv-source` (`rules.source_selector`) | numbers, spelling and the word count inside the note; satisfies `require_source_for_numbers` | numbered `[n]` markers and `doubled-word` are still checked inside it |
| `data-pcv-title` or `h1` (`rules.title_selector`) | marks titles for `no-title`, `title-wraps` and the deck-level title checks | |
| `data-pcv-chart` | declares a chart spec for `truncated-bar-axis` and `chart-label-mismatch` | |
| `data-pcv-label` | marks an HTML element inside a chart as a drawn label (SVG `<text>` counts automatically) | |
| `data-pcv-graphic` | treats any element as a graphic for `text-over-graphic` and `graphic-out-of-bounds` | |
| `data-ref="key"` | declares a citation that must exist in deck.json `references` | |

Elements hidden with `display:none`, `visibility:hidden` or `opacity:0` are not inspected at all.

## Stage 1: render

**`render-error`** · critical · technical. Trigger: the render manifest lists an error for the slide, either `slide source missing: <path>` (the file in deck.json `slides` does not exist) or `slide root '<selector>' never appeared` within `render.timeout_ms`. Resolve: fix the path in deck.json, or make sure an element matching `render.selector` (default `[data-pcv-slide]`) exists after load. Opt-out: none.

**`slide-root-missing`** · critical · technical. Trigger: the inspector found no element matching `render.selector` after the screenshot (the root was attached earlier but is gone, for example removed by a script). Resolve: do not replace or remove the root from script after load. Opt-out: none.

**`slide-root-size`** · critical · technical. Trigger: the root's bounding box is off by more than 1 CSS px from `(0, 0, render.width, render.height)`, default 1920x1080 at the origin. Resolve: give the root exactly `width:1920px; height:1080px` with no margin, transform or scrolling offset; `pcv.css` does this for `[data-pcv-slide]`. A design system whose root class has padding must use `box-sizing:border-box`. Opt-out: none.

## Stage 2: geometry, type and assets (per slide, measured in the live page)

Text geometry is measured on a glyph box: each line rectangle from the browser, reduced to its middle 70% of height (the inked band), so tight leading and descenders do not trigger findings.

**`text-out-of-bounds`** · critical · layout. Trigger: a text line's glyph box extends past the slide edges by more than 1 px. One finding per block. Resolve: move or shorten the text. Opt-out: `data-pcv-allow="bleed"` for deliberate bleed typography (for example a giant numeral cropped by the slide edge).

**`text-clipped`** · critical · layout · auto-fix `shrink-text`. Trigger: a text line's glyph box crosses the box of an ancestor (below the slide root) whose `overflow-x` or `overflow-y` is not `visible`, on the clipping axis, by more than 1 px. This includes `text-overflow: ellipsis` and line-clamp truncation. Resolve: the fix loop writes `font-size: floor(font_px x ratio x 0.97)px !important` into `<deck>/fixes/<stem>.css` when that stays at or above `rules.min_font_px`; otherwise it refuses and lists the slide under "Not fixed automatically". Then shorten the text or enlarge the box. Known false positives: deliberate truncation, which the standard treats as a defect anyway. Opt-out: none.

**`outside-safe-area`** · minor · layout. Trigger: a text line is on the slide but its glyph box enters the `rules.safe_margin_px` margin (default 64 px) by more than 2 px. One finding per block. Resolve: keep text inside the margin. Known false positives: deliberate corner folios and edge labels. Opt-out: `data-pcv-allow="bleed"` (this also switches off `text-out-of-bounds` for that element).

**`text-too-small`** · major · typography. Trigger: computed `font-size` is below `rules.min_font_px` (default 20 CSS px, which is 40 device px at scale 2). Resolve: enlarge the text, or cut it. Known false positives and negatives: SVG text inside a `viewBox` that scales the drawing, and HTML text under a CSS `transform: scale()`, report their unscaled computed size, so the check can be wrong in either direction; fix the drawing to use real pixel sizes instead of opting out. Opt-out: `data-pcv-allow="small"` for text that is legitimately small, such as a legal line that is not meant to be read aloud. Use it sparingly; anything the audience must read must not be small.

**`off-scale-font-size`** · minor · typography. Trigger: only when `rules.type_scale` is a list. A computed font size is more than 0.5 px from every value in the list. One finding per size per slide. Resolve: use a size from the scale; set `type_scale` from the design system's type scale. Known false positives: sizes set by `fitText()` (which steps the size down to fit) are off-scale by design; either include the reachable sizes or leave `type_scale` unset for such decks. Opt-out: none.

**`text-overlap`** · major · layout. Trigger: glyph boxes from two different blocks (neither block containing the other) intersect by more than 2 px in each direction and over more than 10% of the smaller box. Inline elements belong to their nearest block-level ancestor, so spans in one paragraph are never compared. Resolve: separate the elements. Known false positives: intentional layering such as a large ghost numeral behind a heading. Opt-out: `data-pcv-allow="overlap"` on either text, or on an ancestor of either.

**`text-over-graphic`** · major · layout. Trigger: a text line overlaps a top-level graphic (`img`, `svg`, `canvas`, `video` or `[data-pcv-graphic]`) by more than 2 px in each direction and more than 10% of the line's glyph box, and the graphic is not an ancestor of the text. Resolve: move the text off the graphic, or put it on a panel. Known false positives: HTML labels laid over a connector or chart SVG layer (for example the `flow()` component), and background ornaments. Opt-out: `aria-hidden="true"` on the graphic element, or `data-pcv-allow="decor"` on the graphic or an ancestor, for purely decorative graphics; `data-pcv-allow="overlap"` on the text or the graphic for deliberate labels on a drawing.

**`text-overflows-box`** · major · layout · auto-fix `shrink-text`. Trigger: the inked extent of a block's text spills outside the block's own box by more than `max(2 px, 0.25 x font-size)` on either axis, for blocks that are not the root, not SVG, have `overflow: visible` on both axes and non-zero width. The spill usually lands on a neighbour. Resolve: the fix loop shrinks the block's font size as for `text-clipped` (refused below `min_font_px`); otherwise remove a fixed `height`/`width` so the box grows, or cut the text. The fix sets the block's font size, so it has no effect when children set their own `px` sizes; the finding then stays open. Known false positives: intentional negative margins and hanging punctuation. A zero-height box gets no fix ratio, so the fix is neither applied nor refused. Opt-out: none.

**`graphic-out-of-bounds`** · major · layout. Trigger: a top-level graphic's box extends more than 2 px past the slide. Resolve: resize or reposition it. Opt-out: `data-pcv-allow="bleed"` on the graphic for deliberate full-bleed images.

**`missing-asset`** · critical · technical. Trigger: an `<img>` is not complete or has natural width 0 (failed, blocked or no `src`). Resolve: fix the path (paths resolve against `http://deck.local/<path in the deck folder>`) or the allow-list. Check `asset-request-failed` on the same slide for the cause. Opt-out: none.

**`image-distorted`** · major · visual_design · auto-fix `object-fit`. Trigger: a raster `<img>` with `object-fit: fill` is shown at an aspect ratio more than 2% away from its natural aspect ratio. SVG sources are skipped. Resolve: the fix loop sets `object-fit: contain` (letterboxing). If cropping is wanted, set `object-fit: cover` yourself; if the image must fill the box, crop the source file to the right aspect ratio. Opt-out: none.

**`image-low-resolution`** · major when the natural width is below 50% of the shown width in device pixels, minor below 80%. visual_design. Trigger: raster `<img>` whose natural width is less than 0.8 x box width x device scale (at scale 2, an image shown 1000 CSS px wide needs at least 1600 source px; below 1000 px it is major). Resolve: use a larger source, or show it smaller. Known false positives: `object-fit: contain` in a box wider than the image's aspect ratio, where the drawn width is less than the box width. CSS `background-image` is never checked. Opt-out: none.

**`no-title`** · minor · hierarchy. Trigger: `rules.require_title` is true and no visible element matches `rules.title_selector` (default `[data-pcv-title], h1`). Resolve: mark the slide's main statement with `data-pcv-title`; for a cover or a section divider mark its largest text. Opt-out: none per slide; `rules.require_title: false` switches it off for the whole deck.

**`title-wraps`** · major · typography. Trigger: a title's text spans more than `rules.max_title_lines` (default 2) distinct line tops. Resolve: shorten the claim, widen the title box, or step the title size down within the type scale. Opt-out: none; raise `max_title_lines` only when the design system says so.

**`dense-slide`** · minor · hierarchy. Trigger: more than `rules.max_words` (default 90) words on the slide, counting every visible text node, including titles and chart labels, except text inside the source note or `data-pcv-nocheck`. Resolve: cut, split the slide, or move detail to speaker notes (`<slide>.notes.md`). Opt-out: none; do not hide prose in `nocheck` to pass.

**`truncated-bar-axis`** · major · data_visualization. Trigger: a `[data-pcv-chart]` spec with `"type": "bar"` and a `yMin` other than 0 (a missing `yMin` counts as 0). Resolve: start bar axes at zero; use a dot plot or a line chart when the differences are small. Opt-out: none.

**`chart-label-mismatch`** · major · data_visualization. Trigger: a string in the chart spec's `valueLabels` does not equal, after trimming, the text of any `<text>` or `[data-pcv-label]` element inside the chart. Resolve: draw every value label exactly as declared; HTML labels need `data-pcv-label`. Opt-out: none.

**`font-load-failed`** · major · typography. Trigger: a `FontFace` in `document.fonts` has status `error`. Resolve: fix the `@font-face` URL or the Google Fonts link; check `asset-request-failed` for the blocked or missing file. Opt-out: none.

**`font-fallback`** · major · typography. Trigger: for up to two sampled elements per family, weight and style, Chrome's platform-font report (CDP `CSS.getPlatformFontsForNode`) shows that the first family in the `font-family` stack was not used. For a family declared by `@font-face`, the face must be loaded and a custom font must have drawn the text; for an installed family, a used platform font name must start with the requested name. Generic families (`serif`, `sans-serif`, `system-ui` and so on) are skipped. Resolve: load the font, or name a font that exists on the render machine. Known false positives: a sample whose text consists only of glyphs the font lacks (arrows, math symbols, emoji). Opt-out: none; move such glyphs into a span with a font that has them.

**`console-error`** · minor · technical. Trigger: a browser console message of type `error` **or `warning`**, or an uncaught page error, during the slide's load. Resolve: fix the script error; a failed resource load also appears here next to `asset-request-failed`. Known false positives: deprecation warnings from third-party libraries. Opt-out: none.

**`asset-request-failed`** · major · technical. Trigger: a request logged as `blocked` (host not in deck.json `network.allow`), `missing` (a `deck.local` path that is not a file in the deck folder or the canvas folder, or that escapes them), `fetch-failed` (an allow-listed host unreachable on first use, with nothing cached) or `http-NNN` (an allow-listed host answered with a non-2xx status). Resolve: copy the asset into the deck folder, or fix the URL; pin CDN URLs to an exact version. Widen `network.allow` only as a recorded deck.json decision, never to make a finding disappear. Opt-out: none.

## Stage 3: rendered pixels (per slide)

**`image-missing`** · critical · technical. Trigger: the slide's PNG or JPEG is not on disk. Resolve: re-render.

**`image-size`** · critical · technical. Trigger: the image is not exactly `round(width x scale) x round(height x scale)` (3840x2160 by default). Resolve: re-render; do not resize images by hand.

**`image-transparency`** · minor · technical. Trigger: an RGBA image with any pixel below full opacity. Resolve: give `html`, `body` or the slide root an opaque background.

**`blank-slide`** · critical · technical. Trigger: the image, reduced to 192x108 grayscale, has a standard deviation below 1.0 (a single flat colour). Known false positives: a deliberately empty colour slide, which this standard does not allow. Resolve: check that the content rendered (fonts, scripts, `PCV_READY`). Opt-out: none.

**`low-contrast`** · critical below 2.0:1, otherwise major. typography. Trigger: WCAG contrast measured on the rendered pixels. For each line of text, the background is the most frequent colour in the line's box (5-bit quantised); the foreground is the computed text colour (`fill` for SVG) blended with the element's cumulative opacity over that background. Text needs 4.5:1, or 3.0:1 when it is at least 24 px, or at least 18.66 px and weight 700 or more. One finding per block, at its worst line. Resolve: darken or lighten the text, or put it on a panel. Known false positives: very heavy display text whose ink covers most of its box (the "background" becomes the text colour), and text over photographs or busy textures where the most frequent colour is not what sits behind the letters. Known false negatives: colours that are not computed as `rgb()`/`rgba()` (for example `oklch()` or `color()` values, gradient or pattern `fill`, `background-clip: text`) are skipped silently. The visual review must check those. Opt-out: `data-pcv-allow="contrast"`, only after you have checked the rendered image yourself and the text is legible.

## Stage 4: deck-level consistency (needs at least 3 slides with a title)

The first title on each slide is used.

**`title-size-inconsistent`** · minor · consistency. Trigger: a title's rounded size differs from the deck's most common title size, is used by only that one slide, and is within 25% of the mode (much larger cover or section titles are not flagged). Resolve: use the content-slide title size.

**`title-position-inconsistent`** · minor · consistency. Trigger: a title at the modal size starts more than 4 px left or right of the most common title x position. Resolve: align titles to the same grid line. Only the x position is checked.

**`duplicate-title`** · minor · storytelling. Trigger: two titles with the same text, compared case-insensitively. Resolve: give each slide its own claim; a continued slide should say what it adds.

**`too-many-families`** · minor · consistency · deck-level. Trigger: more than three distinct first families in `font-family` across all text in the deck (generic families count). Resolve: reduce to a display face, a text face and at most one mono face.

## Stage 5: content (exact text the slides show)

**`source-unreadable`** · major · content_accuracy · deck-level. Trigger: a file in deck.json `sources` is missing or yields no text. PDF, PPTX, CSV and TSV are parsed; anything else is read as UTF-8 text. A scanned PDF with no text layer yields nothing. Resolve: fix the path, or provide a text version of the source.

**`unsupported-number`** · severity = `rules.number_policy` (default `major`; `off` disables the check) · content_accuracy. Trigger: a number on the slide does not match any number in any source file. What counts as a number: digits with an optional sign, thousands separators, decimals and a `%`, not glued to letters, `.`, `-` or `/` (so `F1`, `SemEval-2027`, `v1.2`, `3/4` and `12ms` are not checked). Integers below `rules.min_integer_checked` (default 10) without decimals or `%` are skipped. Text in the source note and `data-pcv-nocheck` is skipped. What counts as a match: a source number `v`, or `v x 100`, or `v / 100`, rounded to the number of decimals the slide shows (an exact tie is accepted rounded either half-up or half-even), equals the slide value, ignoring sign. So a source `0.8237` supports `0.82`, `82.4%` and `82%`, and a source `0.8125` supports both `0.813` and `0.812`. Resolve: copy the number from the source, at the precision the source supports; add the source file to deck.json `sources` if it was missing. Known false positives: axis tick values, slide numbers and years that no source contains (mark generated ticks and folios `data-pcv-nocheck`). Known false negatives: the check proves only that the number appears **somewhere** in the sources. It does not prove it is the right number for this claim, the right sign or the right unit. When `sources` is empty, numbers are not checked at all and no finding says so. Opt-out: `data-pcv-nocheck` for text that is not a claim (ticks, folios, dates in a footer). Never use it on a reported result.

**`number-without-source`** · major · content_accuracy. Trigger: `rules.require_source_for_numbers` is true, `number_policy` is not `off`, the slide shows at least one checked number, and no text on it matches `rules.source_selector`. Resolve: add a `data-pcv-source` note naming the source file.

**`missing-reference`** · major · content_accuracy. Trigger: either a `data-ref="key"` whose key is not in deck.json `references`, or a numbered marker `[n]`, `[n, m]` or `[n-m]` in checked text whose number is below 1 or above the number of references. Resolve: add the reference, or correct the key or marker. Known false positives: bracketed numbers that are not citations, such as intervals `[0, 1]`; mark them `data-pcv-nocheck`. Opt-out: none for `data-ref`.

**`doubled-word`** · minor · content_accuracy. Trigger: the same word twice in a row within one text node, compared case-insensitively, ignoring pure digits. Resolve: delete the repeat. Known false positives: grammatical repeats ("had had", "that that"). Opt-out: `data-pcv-nocheck` only.

**`spelling`** · minor · content_accuracy. Trigger: pyspellchecker (English) does not know a word. Words shorter than 3 letters, all-caps words and words with an internal capital (acronyms, CamelCase) are skipped; every word in the source files and in deck.json `glossary` counts as known; a trailing `'s` is stripped. One finding per word per slide. Resolve: correct the word, or add a correct term to `glossary`. Known false positives: proper names and technical terms absent from the sources; letters with accents split words. Opt-out: `data-pcv-allow="spelling"` (for example on a quoted foreign phrase); `rules.spelling: false` switches spelling off for the deck.

**`spelling-unchecked`** · info · content_accuracy · deck-level. Trigger: pyspellchecker is not importable. Resolve: run through `uv run --group slides`.

## Stage 6: output files

**`pptx-missing`** · critical · technical. The PPTX was not produced. Run `assemble`.

**`pptx-corrupt`** · critical · technical. The zip test fails or python-pptx cannot open the file. Rebuild it; close PowerPoint if it holds a lock.

**`pptx-size`** · critical · technical · deck-level. Slide size is not 12192000 x 6858000 EMU (13.333 x 7.5 in, 16:9).

**`pptx-count`** · critical · technical · deck-level. Number of PPTX slides differs from the number of rendered images.

**`pptx-picture-count`** · critical · technical. A PPTX slide does not hold exactly one picture.

**`pptx-extra-shapes`** · major · technical. A slide holds shapes besides the picture. Only `assemble` should write the PPTX; do not hand-edit it.

**`pptx-image-placement`** · critical · technical. The picture is not at (0, 0) with exactly the slide's width and height in EMU.

**`pptx-image-cropped`** · critical · technical. The picture has a crop on any side.

**`slide-image-mismatch`** · critical · technical. The SHA-256 of the embedded picture matches no rendered image: the PPTX is stale. Re-run `assemble` after every render.

**`slide-order-mismatch`** · critical · technical. PPTX slide *i* embeds rendered slide *j* (matched by SHA-256). Known false positive: two slides that render to byte-identical images (a repeated divider) make the earlier one look out of order.

**`pptx-no-alt-text`** · minor · technical. The picture has no `descr`. `assemble` always writes the slide text or "Slide n", so this means the file was produced elsewhere.

**`pdf-missing`**, **`pdf-corrupt`** · critical · technical. The PDF was not produced or does not open. Run `pdf`.

**`pdf-count`** · critical · technical · deck-level. PDF page count differs from the slide count.

**`pdf-page-size`** · major · technical. A page is not 960 x 540 pt (within 0.5 pt).

**`pdf-mismatch`** · critical · technical. The page, rasterised at 2x and compared in grayscale at 960x540 with the rendered image, has a mean absolute difference of 3.0 levels or more, or more than 0.5% of pixels differing by more than 16 levels after a 3x3 erosion (which removes resampling halos on glyph edges). Re-run `pdf` after every render.

**`renderback-unavailable`** · info · technical. Not Windows, no `powershell`, or `scripts/renderback.ps1` failed (usually PowerPoint is not installed). The report then says the render-back was not verified.

**`renderback-missing`** · critical · technical. PowerPoint exported no PNG for this slide.

**`renderback-mismatch`** · critical · technical. PowerPoint's own export of the slide differs from the design render by the same test as `pdf-mismatch`. Open `<out>/renderback/slide-NN.png` next to `<out>/images/` before deciding the cause: missing or moved content is a real defect; a uniform tone shift points to colour handling. The test is grayscale, so a hue change at equal brightness passes unnoticed.

## Stage 7: visual-review findings

When `<out>/review/review.json` is valid, `validate` copies each of its findings into `findings.json` with the reviewer's `code` (default `visual-review`), severity, category and slide, so they cap categories and set status exactly like automated findings. Review findings enter only when `validate` runs after the review was written; `report` alone does not import them. See `visual-review.md`.

## Foreign PPTX (`deck.py inspect-pptx <file.pptx> --out <dir>`; not part of `validate`)

For a PPTX this skill did not build (`pcv/foreign.py`). PowerPoint exports each slide to `<out>/images/slide-NN.png` (3840 px wide) through `scripts/renderback.ps1`. python-pptx reads the text and shape frames, the image and content checks run, the review kit is built, and the report is written in the same run. There is no live page, so clipping, glyph overlap, font fallback and measured contrast are not checked, and none of the geometry opt-outs exist. Options: `--sources` (files numbers must trace to), `--glossary` (known words), `--min-font` (px on a 1920-px-wide canvas, default 20).

Codes in this mode, besides `image-*`, `blank-slide` and the content codes above:

**`pptx-size`** · minor (not critical, as for built decks) · technical. The slide aspect ratio is not 16:9.

**`text-too-small`** · major · typography. A run's explicit size in pt, converted to px on a 1920-px-wide canvas (`pt x 1920 / slide width in inches / 72`), is below `--min-font`. Runs that inherit their size from the layout or master are not checked.

**`text-out-of-bounds`** · major (not critical) · layout. A text-bearing shape's frame starts more than 0.01 in left of or above the slide, or ends more than 0.2% past its right or bottom edge. It measures the frame, not the glyphs.

**`empty-placeholder`** · minor · technical. A placeholder with a text frame and no text (it shows "Click to add" while editing).

**`shape-overlap`** · minor · layout. The frames of two text-bearing shapes overlap by more than 10% of the smaller frame. Frames are often larger than their text, so confirm on the image before acting.

**`export-failed`** · critical · technical · deck-level. `renderback.ps1` returned an error: no images, so no image checks and no review kit.

**`export-unavailable`** · critical · technical · deck-level. Not Windows, or no `powershell`: the file cannot be exported, so no visual review is possible on this machine.

**`layout-unchecked`** · info · layout · deck-level. Always emitted, to record that the live-page checks could not run. The visual review must cover clipping, overlap, fonts and contrast.

Known false positive in this mode: the content check runs with no references, so every numbered `[n]` citation marker is reported as `missing-reference`. Check those markers against the deck's own reference slide by eye.

## Design-system audit (`deck.py ds-audit`; not part of `validate`)

Written to `<out>/ds-audit.json` and `<out>/ds-audit.md`. These findings do not enter the deck's score.

**`ds-token-contrast`** · major · typography. A text-like colour token (name matching `ink*`, `text*`, `*-text`, `fg*`, `foreground*`) has contrast below the requirement against a ground token, per theme. The requirement is 3:1 when the token's `usage` note mentions `<n>px or more`, `large text` or `3:1`, otherwise 4.5:1. Grounds are the ground tokens (`surface*`, `paper`, `highlight`, `background*`, `bg*`, `*-soft`) named in the usage note; if the note names none, every `surface*` token. Tokens whose usage says `never text`, or `non-text` without `text of`, are skipped. Only hex colours are compared. Resolve: report the failing pair to the design system's owner (see `design-systems.md`), and avoid that pair on slides.

**`ds-font-below-minimum`** · minor · typography. A `font` or `font-size` declaration in `components/bundle.css` sets a `px` size below `--min-font` (default 22, while the deck rule `min_font_px` defaults to 20: pass `--min-font` with the deck's value). Only `px` values are read.

## Automatic fixes

Only fixes that cannot change meaning are automatic: `shrink-text` (from `text-clipped` and `text-overflows-box`) and `object-fit: contain` (from `image-distorted`). They are written as reviewable CSS in `<deck>/fixes/<slide-stem>.css` with a ledger in `<deck>/fixes/ledger.json`, injected after the page's own CSS, and re-rendered for up to three rounds. Delete a slide's fix file to undo it. Fold accepted fixes into the slide source. The fix CSS is injected after the page's scripts have run, so layouts computed in JavaScript (charts, `fitText`) do not respond to it. The fix loop writes into the deck folder: for a deck stored under `.claude/`, always pass `--no-fix`.

## What automation cannot judge (the visual review must)

The checks measure geometry, pixels and strings. They cannot see whether a slide communicates. The visual review is responsible for:

- **Meaning of numbers.** Whether each number is the right one for its claim, with the right sign, unit, split and precision. The number check proves only that the value appears somewhere in a source.
- **Claims.** Whether the title's claim follows from the evidence shown, and whether a statement is unsupported though number-free.
- **Hierarchy and focus.** One focal point per slide, the eye path, and whether the title states the takeaway.
- **Composition.** Grid alignment beyond the title's x position, balance, spacing rhythm, crowding, purposeless empty space, and graphics overlapping other graphics (only text is checked against graphics).
- **Visual language.** Generic AI-slide tropes (card grids, decorative icons, gradient blobs, title plus three boxes everywhere), image quality, and whether decoration earns its place.
- **Charts.** Whether the chart type fits the question, honest scales other than the bar zero baseline (line-chart ranges, dual axes, aspect), legends instead of direct labels, colour-only encoding, and emphasis on what matters.
- **Text the checks cannot read.** Text inside raster images or `<canvas>`, CSS `content` in `::before`/`::after`, text in CSS background images: none of it is checked for size, contrast, spelling or numbers.
- **Contrast the checks skip or misjudge.** `oklch()`/`color()` colours, gradient fills, text over photographs, and colour-blind safety.
- **Sizes under scaling.** SVG text inside a scaled `viewBox`, transformed text.
- **Storytelling and consistency.** Sequence, one job per slide, transitions, the ending, and repeated elements in the same place and style.

## The evidence rule

Never claim a slide looks right, or that the visual review happened, without opening the rendered images in this session with the Read tool. A passing `validate` is not visual evidence. `review.json` lists in `inspected` only the slides that were actually opened, and sets `contact_sheet_inspected` to true only if the contact sheet was opened. A review of an earlier render is not evidence about the current one: after any re-render, delete `review/review.json` and review again. Report every finding as measured, including the ones that make the deck NOT READY.
