# presentation-creator-validator

A Claude Code skill that designs slides as HTML, CSS and SVG, renders them to exact-size
high-resolution images, packs them into a PowerPoint file and a PDF, and then checks the result
independently: what was rendered, not what the code intended.

## Why images in PowerPoint

Each slide is designed on a web canvas, where any layout, diagram or typographic detail is possible,
and captured at 3840x2160 pixels. The .pptx holds one picture per slide, filling it edge to edge.
The deck looks the same on every machine that opens it, with no font substitution and no shifted
text boxes.

The cost: **text and shapes are not editable inside PowerPoint.** To change a slide, edit its HTML
file and rebuild (one command, about two seconds per slide). Each slide's text goes into its alt
text and speaker notes, so the deck stays searchable and screen readers can still read the slides.

## Install

The skill lives in this repository at `.claude/skills/presentation-creator-validator/`, so Claude
Code finds it automatically. Its Python packages are in the repository's optional `slides` group:

```bash
uv sync --group slides
uv run --group slides playwright install chromium   # only if Google Chrome is not installed
```

| Package | Used for |
|---|---|
| playwright | drives Chrome to render slides and measure their layout |
| python-pptx | writes and inspects the .pptx |
| pymupdf | writes the PDF, reads PDF sources |
| pillow, numpy | image checks, contrast, comparisons, contact sheet |
| pyspellchecker | spelling check (words found in the sources count as known) |

PowerPoint on Windows is optional. When it is installed, the validator opens the finished .pptx in
PowerPoint, exports every slide, and compares the result with the original render. Without it, the
report says this check was not run.

## Use

Ask Claude for a presentation, a redesign, or a validation; the skill guides it through the phases.
To run the commands yourself (`D` is `uv run --group slides python .claude/skills/presentation-creator-validator/scripts/deck.py`):

```bash
D new decks/my-talk --title "My talk"          # start a deck folder
D new decks/my-talk --design-system path/to/ds # start one on an existing design system
D build decks/my-talk                          # render, fix, PPTX, PDF, review kit, checks, report
D render decks/my-talk --slides 3              # re-render one slide while designing
D report decks/my-talk                         # re-score after the visual review is written
D inspect-pptx old.pptx --out review/ --sources paper.pdf   # check a deck made elsewhere
D ds-audit path/to/ds --out audit/             # contrast and minimum-size audit of a design system
```

Outputs land in `<deck>/build/` (gitignored):
- `images/`: one exact-size PNG per slide.
- `<name>.pptx` and `<name>.pdf`.
- `review/`: previews, `contact-sheet.png`, and `review.json`.
- `validation/`: `findings.json`, `report.md`, `report.json`.
- `renderback/`: PowerPoint's own export.

## A deck folder

```
deck.json          title, slide order, sources, glossary, references, render settings, validation rules
brief.md           purpose, audience, duration, objective, central message
storyboard.md      one row per slide: claim, takeaway, evidence and source, visual, composition
art-direction.md   type, palette with contrast ratios, grid, motifs, things to avoid
theme.css          the deck's colours and fonts (overrides of the --pcv-* properties)
slides/NN-name.html            one slide per file; NN-name.notes.md holds its speaker notes
assets/            images and their ATTRIBUTION.md
fixes/             automatic fixes waiting for review (fold them into the slides, then delete)
```

Every number on a slide must appear in a file listed under `sources`. If one doesn't, the validator
reports it, as a critical issue when `number_policy` is `critical`.

## What the validator checks

| Stage | Checks |
|---|---|
| Live page | text clipped or off the slide, text overlapping text or images, text spilling out of its box, text below the minimum size, titles that wrap, off-scale font sizes, font fallback (the font Chrome actually drew), missing and stretched images, low-resolution images, honest chart axes, blocked or failed asset requests |
| Pixels | exact image size, blank slides, transparency, WCAG contrast measured against the rendered background behind each line |
| Content | numbers traced to sources, citation keys and markers, spelling, doubled words |
| Deck | title size and position consistency, duplicate titles, number of type families |
| Files | .pptx opens, 16:9, one full-slide picture per slide, no cropping, slide order by image hash, alt text; PDF pages match the render; PowerPoint render-back matches the render |
| Visual review | a fresh-context reviewer opens every slide and the contact sheet and scores eight categories against the rubric |

Safe fixes are automatic: shrinking clipped text (never below the minimum size) and letterboxing
stretched images. They are written as CSS in `fixes/` for review. Everything else becomes a
recommendation in the report.

The score is out of 100 across nine weighted categories. Open automated findings cap the reviewer's
scores. No overall score is computed while the visual review is missing, and a deck with an open
critical issue is never production-ready. See `references/scoring-rubric.md`.

## Limits

- Slides in the .pptx are images: there is no in-PowerPoint editing, and there are no animations or
  builds.
- The PowerPoint render-back needs Windows with PowerPoint. On macOS it is reported as not verified.
- A .pptx made elsewhere (`inspect-pptx`) can only get shape-level and image-level checks.
  Clipping, glyph overlap and font fallback need the live HTML page.
- Spelling uses a general English dictionary. Domain terms go in `glossary`, or are learned from the
  source files.
- The visual-quality scores are a reviewer's judgement against a written rubric, not a measurement.
  The report labels them that way.

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --group slides pytest .claude/skills/presentation-creator-validator/tests -p no:cacheprovider
```

The integration tests render a fixture deck full of deliberate defects and assert that each defect
is detected on the right slide.
