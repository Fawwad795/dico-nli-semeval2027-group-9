# Colour and accessibility

Every ratio quoted here is the WCAG 2 contrast ratio, computed with the same formula the validator uses (sRGB relative luminance, (L1 + 0.05) / (L2 + 0.05)).

## Palette roles

A deck palette is a set of custom properties, overridden in the deck's `theme.css` (loaded after `pcv.css`). Measured ratios are for the `pcv.css` defaults on their ground #F4F1EA:

| Token | Role | Rule | Default, ratio on ground |
|---|---|---|---|
| `--pcv-bg` | Slide ground | One ground for content slides; a second (inverted or tinted) only for section breaks | #F4F1EA |
| `--pcv-surface` | Panels, table header fills | Barely different from the ground; re-check ink-3 on it | #EAE6DC (ink-3 on it: 4.62) |
| `--pcv-ink` | Titles, body, data in focus | At least 12:1 for projection | #15171C, 15.90 |
| `--pcv-ink-2` | Secondary text, labels, non-focus data | At least 7:1 | #3B3F47, 9.36 |
| `--pcv-ink-3` | Source notes, ticks, metadata | At least 4.5:1 (it is small text) | #62666E, 5.11 |
| `--pcv-rule` | Hairlines, gridlines, dividers | Quiet, about 1.3:1 to 2:1; never carries meaning, never text | #D3CEC3, 1.39 |
| `--pcv-mark` | Neutral (non-emphasised) chart marks | Marks only, never text; labels go in ink | #ABA699, 2.15 |
| `--pcv-accent` | The one thing to look at | Used once per slide; at least 4.5:1 if it colours small text, 3:1 if only large text or fills | #B83D12, 5.01 |
| `--pcv-accent-soft` | Tint behind an emphasised row or callout | Ink must stay at 7:1+ on it | #F3DFD3 (ink on it: 13.92) |
| `--pcv-accent-2` | Second category when a contrast pair is needed | Must differ from accent in lightness, not just hue | #1E5A78, 6.68 |
| `--pcv-on-accent` | Text on accent fills | At least 4.5:1 on the accent | #FFFFFF, 5.65 on accent |

Changing any token means re-measuring the pairs that use it.

## Building a palette

1. **Start with neutrals, not the accent.** Choose the ground (warm off-white such as #F7F5F0, cool white #FFFFFF, or dark #0E1116 to #16181D), then derive ink, ink-2, ink-3 as a lightness ladder of the same hue family.
2. **Pick one accent** from the art direction and the content (a domain colour, an institution colour, or a deliberate contrast to the neutrals). Check it against the ground at the size it will be used.
3. **Add accent-2 only if the story has two things to compare.** Make it differ in lightness from the accent by at least 20 L* points so it survives greyscale and colour-blind viewing.
4. **Categorical data beyond two series**: use a colour-blind-safe set (Okabe-Ito, below) and still label directly.
5. Write the ratios you checked into the theme file as comments. If the deck imports a design system, run `deck.py ds-audit` first; it reports text-token contrast pairs and fonts below the minimum.

Grey ladders that pass, measured:

| On #FFFFFF | Ratio | | On #111111 | Ratio |
|---|---:|---|---|---:|
| #111111 | 18.88 | | #F2F2F2 | 16.87 |
| #555555 | 7.46 | | #A3A3A3 | 7.49 |
| #6B6B6B | 5.33 | | #7A7A7A | 4.40 (fails small text) |
| #767676 | 4.54 (lowest passing grey for small text) | | #5C5C5C | 2.82 (fails everything) |
| #959595 | 3.00 (large text only) | | | |

## WCAG thresholds the validator applies

| Text | Threshold | Validator rule |
|---|---|---|
| Normal text | 4.5:1 | size below 24px, or below 18.66px when bold |
| Large text | 3:1 | size 24px or larger, or 18.66px or larger at weight 700 or more |
| Below 2:1 | | reported as critical; otherwise a failure is major |

Aim higher than the minimum for projection: projectors and lit rooms lower effective contrast a lot. Target 7:1 for body and labels.

Non-text contrast (WCAG 1.4.11: chart marks, icons, focus lines at 3:1 against adjacent colours) is **not** measured by the validator. Check it yourself for bars, lines and diagram strokes that carry meaning.

## How the validator measures contrast on rendered pixels

`check_contrast` works on the PNG, not on CSS, so it sees gradients, panels, images and overlays as the audience does:

1. For every visible text node, it takes each rendered line box (the text's client rect, multiplied by the device scale of 2).
2. The **background** is the most frequent colour in that box, with each channel quantised to 5 bits and averaged within the winning bin.
3. The **foreground** is the element's computed CSS `color` (or `fill` for SVG text), composited over that background with its alpha times the product of all ancestor `opacity` values.
4. The ratio is compared with 4.5 or 3.0 as above; the worst line of each block is reported once as `low-contrast` with the measured foreground, background and ratio.

Consequences:

- Text over a photo or gradient is measured against the dominant colour behind that line. Busy images can pass while individual letters fail; put a solid or 80%+ opaque scrim behind text on images.
- Text painted by `background-clip: text`, `-webkit-text-fill-color`, strokes or shadows is measured from CSS `color`, not from what was painted. Do not use gradient or outlined text.
- If the glyphs cover more of the line box than the ground does (ultra-heavy, tightly tracked display type), the dominant colour can be the ink itself and the check reports a false failure near 1:1. Confirm by eye on the PNG; only then wrap that element in `data-pcv-allow="contrast"`.
- Opacity lowers measured contrast. `opacity: 0.6` on grey text over white turns a pass into a fail; set a solid token colour instead.
- `data-pcv-allow="contrast"` is for decoration that is not meant to be read (watermark numerals, ghosted background words). Never use it to silence real text.
- The renderer runs with `color_scheme: light`, so `prefers-color-scheme: dark` rules never apply. Set dark slides explicitly.

## Colour-blind safe practice

About 1 in 12 men has a red-green deficiency. Rules:

- **Never encode meaning by hue alone.** Pair colour with a second channel: direct text labels, position, shape, line style (solid vs dashed), weight, or lightness difference.
- Avoid red vs green as the only distinction (good/bad, up/down). Use blue vs orange, or dark vs light, plus a label.
- Highlight by contrast with grey: the series in focus in the accent, all others in ink-3 or a light grey. This survives every vision type and greyscale printing.
- Check with a greyscale test: if two categories become the same grey, they need a different lightness or a label.
- Legends force colour matching; direct labels remove the need (see `data-visualization.md`).

Okabe-Ito categorical colours, with measured contrast:

| Colour | Hex | On #FFFFFF | On #111111 | Use on light ground |
|---|---|---:|---:|---|
| Blue | #0072B2 | 5.19 | | Text and fills |
| Vermillion | #D55E00 | 3.87 | | Large text (24px+) and fills only |
| Bluish green | #009E73 | 3.42 | | Large text and fills only |
| Reddish purple | #CC79A7 | 3.06 | | Fills only, labels in ink |
| Orange | #E69F00 | 2.25 | 8.38 | Fills only on light; fine for text on dark |
| Sky blue | #56B4E9 | 2.31 | 8.18 | Fills only on light; fine for text on dark |
| Yellow | #F0E442 | | 14.28 | Dark grounds only |

When a fill colour cannot carry text, put the label outside the mark in ink.

## Light versus dark slides for projection

| | Light ground | Dark ground |
|---|---|---|
| Room | Lit rooms, daytime seminars, most classrooms | Darkened auditoriums, keynote stages |
| Projector | Robust on weak or old projectors | Black levels on cheap projectors turn grey and kill contrast |
| PDF and print | Reads and prints well | Heavy toner, harder to annotate |
| Type | Any weight from 400 | Avoid weights under 400; text looks bolder and blooms |
| Accent | Deep, saturated accents | Lighter, slightly desaturated accents |

Default to light for academic and course presentations. If dark, use #0E1116 to #16181D (not #000000), ink near #E8E6E1 (15.16:1 on #0E1116), and check secondary greys: #9AA0A6 gives 7.16:1 on #0E1116, #6B7280 only 3.91:1.

Mixing light and dark slides in one deck: only for section breaks or a single hero slide, used consistently.

## Other accessibility points

- Minimum 20px text (validator floor); 28px+ for body when projected.
- Never rely on motion: the renderer disables animations and transitions, and the output is static images.
- The PPTX and PDF contain pictures only. In the PPTX, each picture's alt text and the notes page carry the slide's visible text (taken from the DOM) plus `<slide>.notes.md` if present; the PDF carries no text at all. Write real text in the HTML (not text baked into images or SVG paths) so it reaches the alt text, and keep speaker notes complete for anyone who needs the content as text.
