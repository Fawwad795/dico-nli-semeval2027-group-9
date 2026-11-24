# Typography

Sizes are CSS px on the 1920x1080 canvas (rendered at device scale 2, so 32px text is 64 device px in the 3840x2160 PNG). On a projector the canvas shrinks to the screen; type that looks generous on a monitor is often barely legible at the back of a room.

## What the validator enforces

| Rule (deck.json `rules`) | Default | Finding |
|---|---|---|
| `min_font_px` | 20 | `text-too-small` (major) for any text below it, unless inside `data-pcv-allow="small"` |
| `max_title_lines` | 2 | `title-wraps` (major); lines are counted on the rendered title |
| `title_selector` | `[data-pcv-title], h1` | `no-title` (minor) when nothing matches and `require_title` is true |
| `type_scale` | none | When set to a list of px sizes, `off-scale-font-size` (minor) for any size more than 0.5px off the list |
| deck level | | `title-size-inconsistent` and `title-position-inconsistent` (minor) when one slide's title differs from the deck's usual size (within 25%) or x position (more than 4px); `too-many-families` (minor) when more than 3 first-listed families appear across the deck |
| fonts | | `font-load-failed` (major) when a declared web font errors; `font-fallback` (major) when Chrome actually drew the text with a different font than the first family requested |

Text that is clipped by an `overflow` container (`text-clipped`, critical) or spills out of its own fixed box (`text-overflows-box`, major) is shrunk automatically by `fix`, but never below `min_font_px`; below that the fix is refused and you must cut words or enlarge the box.

The validator does not check leading, tracking, measure, weights or pairing. The reviewer does, against this file.

## Type scale for 1920x1080

Use the `pcv.css` type classes for roles and override sizes in `theme.css` only for a reason. Recommended ranges per role:

| Role | Class | Size | Weight | Leading | Notes |
|---|---|---|---|---|---|
| Source note, folio | `[data-pcv-source]`, `.pcv-foot` | 20 | 400 | 1.35 | Absolute floor. Only for text nobody needs to read aloud |
| Kicker, small print, chart ticks | `.pcv-kicker`, `.pcv-small` | 22 to 24 | 400 to 500 | 1.2 to 1.4 | Ticks below 22 vanish on projectors |
| Labels, captions, table cells, chart values | | 24 to 28 | 400 to 500 | 1.3 | Chart components default to 24 |
| Body text | `.pcv-body` | 28 to 32 | 400 | 1.4 to 1.45 | 32 for projected talks in large rooms; 28 is the minimum when projected |
| Lead / subtitle | `.pcv-lead` | 34 to 40 | 400 | 1.3 to 1.4 | |
| Section heading inside a slide | `.pcv-h2` | 36 to 48 | 600 | 1.15 to 1.2 | |
| Slide title (claim) | `.pcv-h1` | 56 to 64 | 400 (display serif) or 600 to 700 (sans) | 1.1 | Same size on every content slide |
| Display (opening, section break) | `.pcv-display` | 96 to 128 | 400 serif or 700 to 800 sans | 1.0 to 1.05 | |
| Hero number | `.pcv-num` | 128 to 240 | 400 to 800 | 0.92 to 1.0 | One per slide; tabular figures |

Adjacent roles should differ by a ratio of about 1.25 or more; 34px lead next to 36px heading reads as one level, so do not use both on one slide. To make drift visible, set `rules.type_scale` to the exact sizes your deck uses: every size of every class you use (read `pcv.css`), every chart `fontSize`, and your `theme.css` overrides. Any rendered size more than 0.5px off the list is reported, which includes sizes `fitText` or an automatic fix produced.

Projection minimums for a typical seminar room: body never below 28, labels never below 24. The 20px validator floor is a safety net, not a design size.

## Title length

- At 64px in a typical sans, average glyph width is about 0.5em (32px), so the 1696px frame holds roughly 50 to 55 characters per line. Two lines therefore cap a claim title at about 100 characters, and 70 to 90 is comfortable. Condensed or wide faces shift this; the validator measures the real line count.
- Claim titles are sentences: sentence case, no trailing period, 8 to 14 words.
- If a title wraps to two lines, balance it: `text-wrap: balance` on the title element.
- Never set titles in all caps. Kickers (the small line above a title) may be uppercase at 20 to 24px with +0.08em tracking.

## Measure, leading and tracking

- Measure: 45 to 75 characters per line for body text. At 32px that is about 720 to 1200px, i.e. 5 to 8 columns of the 12-column grid (688 to 1120px). Full-width (1696px) body text is too long to read.
- Leading tightens as size grows: 1.4 for body, 1.15 for headings, 1.0 to 1.05 for display. Large display text at 1.4 looks broken apart.
- Tracking: 0 for body; -0.01 to -0.02em for titles; -0.03em for display above 100px; +0.06 to +0.1em only for small uppercase kickers. Never track lowercase body text.
- Ragged-right, never justified (justification makes rivers at slide measures). Use `hyphens: manual`.
- Avoid single-word last lines in titles and leads: `text-wrap: balance` for titles, `text-wrap: pretty` for paragraphs.

## Weights

- Two weights per family is usually enough (400 + 600, or 400 + 700). Load only the weights you use.
- Bold within body text is emphasis for one phrase per slide, not every lead-in.
- Light weights (300 and below) wash out on projectors and on dark grounds. Do not use them under 48px.
- On dark slides, text looks heavier; drop one step (600 to 500) for large type if it feels clotted.

## Pairing

Rules: at most 2 families plus an optional mono for code and identifiers (the validator flags more than 3). Pair on contrast of structure (serif with sans, humanist with geometric), match x-heights, and give each family one role.

Open-licence pairs on Google Fonts:

| Pair | Character | Good for |
|---|---|---|
| Newsreader (display) + Inter (text) | Editorial, literate | Research narratives, modern editorial |
| Fraunces (display, opsz axis) + Source Sans 3 | Warm, characterful | Story-led talks, bold openings |
| Instrument Serif (display, 400 only) + Inter Tight | Fashion-editorial, high contrast | Title and section slides; keep the serif above 64px |
| Source Serif 4 + Source Sans 3 + Source Code Pro | One superfamily, quiet | Academic decks with code |
| IBM Plex Sans + IBM Plex Serif + IBM Plex Mono | Engineered, neutral | Technical and corporate premium |
| Space Grotesk (display) + IBM Plex Sans + JetBrains Mono | Technical, slightly quirky | Systems and architecture talks |
| Schibsted Grotesk or Bricolage Grotesque (display) + Inter | Bold, contemporary | Bold typographic and infographic directions |
| DM Serif Display + DM Sans | Classic contrast | Corporate premium openings |
| Atkinson Hyperlegible (text) | Maximum letter distinction | Dense labels, accessibility-first decks |

Inter alone is the default look of generated decks. If you use it, pair it with a distinctive display face so the deck has a voice.

## Numerals

- Tabular figures (`font-variant-numeric: tabular-nums`) in tables, aligned columns, axis labels and anything that updates. Proportional figures in running text and hero numbers.
- Lining figures everywhere on slides; old-style figures only in an editorial serif body.
- Use the true minus sign (U+2212 "−") and "±". The number check reads "−0.3" as a negative number.
- Write the percent sign directly after the number ("72.3%"); thousands separators as "12,345".
- Numbers glued to letters are not checked as written: "10k", "F1", "12.5ms" and "13.2x" are skipped entirely. Prefer "13.2×" (the multiplication sign is not a letter, so 13.2 is checked) and verify any remaining glued forms by hand. Hyphenated ranges ("2019-2021") are skipped too; write "2019 to 2021".
- Keep the decimal places the source supports. The check rounds each source value (and its ×100 and ÷100 forms) to the decimal places shown on the slide, accepting half-up or half-even at exact ties: 0.7234 in a source supports "0.72", "72.3%" and "72%", but not "0.724".
- Set units in the label or column header, not after every value.

## Loading fonts so the renderer captures them

The renderer waits for `document.fonts.ready`, every image, `window.PCV_READY` if it is a Promise, then two animation frames, and only then screenshots. A font that is not loaded by then is a fallback in the PNG.

1. **Google Fonts**: link the css2 API in `<head>`; fonts.googleapis.com and fonts.gstatic.com are allow-listed and cached on disk by URL on first fetch, so later renders work offline.

   ```html
   <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,600&family=Inter:wght@400;600&display=block">
   ```
2. **Local files**: put `.woff2` files in the deck folder and declare them with `@font-face` using a relative URL; they are served from `http://deck.local/`.
3. Do not rely on system fonts (Segoe UI, Georgia, Helvetica, SF Pro). `pcv.css` defaults to system stacks only so a bare slide renders; a real deck overrides them in `theme.css` with loaded faces. Teammates render on Windows and macOS, and a system face differs or is missing between them; the `font-fallback` check catches a missing face, but only on the machine that rendered.
4. Name the web font first in every `font-family` stack (via `--pcv-font-display`, `--pcv-font-text`, `--pcv-font-mono` in `theme.css`). The fallback check compares the first family against what Chrome actually drew.
5. Font loading is lazy: a face is fetched only when text uses it. A face for a glyph range you never use will not load, which is fine.
6. If text is drawn by script after load (charts, `fitText`), resolve `PCV.ready(promise)` after drawing so the renderer waits for it.
7. After render, check the report (or `<build dir>/dom/*.json`) for `font-fallback`; a single fallback means every slide using that style is off.
