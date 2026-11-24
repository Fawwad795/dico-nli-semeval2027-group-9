---
name: presentation-creator-validator
description: Create, redesign or validate slide decks. HTML/CSS/SVG slides render to exact 4K images, assemble into image-based PPTX and PDF, then get checked (layout, contrast, numbers vs sources, PowerPoint render-back) and scored.
---

# Presentation creator and validator

The design canvas (one HTML file per slide, 1920x1080 CSS px) is the source of truth. The renderer
captures each slide at exact 3840x2160 (or 5760x3240). The PPTX and PDF are containers holding one
full-bleed image per slide. Validation inspects what was rendered, not what the HTML intended.

## Modes

| Mode | Input | Do |
|---|---|---|
| CREATE | prompt, papers, reports, data, outline | phases 1-8, then report |
| VALIDATE | a deck folder, or an existing .pptx | phase 6 and 9 only; `inspect-pptx` for a foreign .pptx |
| REDESIGN | existing .pptx/.pdf/.md | extract its content (`checks_content.source_text` reads .pptx and .pdf), keep every fact, then CREATE |
| CREATE_AND_VALIDATE | as CREATE | all phases, iterate until no critical issue remains |

## Hard rules

- Slides are built from HTML, CSS, SVG and JS. Never generate a slide, or an image containing slide
  text or layout, with an image model. Licensed photos and sourced illustrations are allowed; record
  them in `assets/ATTRIBUTION.md`.
- Every number on a slide must be in a file listed under `sources` in deck.json; the validator checks.
  Never invent statistics, citations or findings. Keep facts, interpretation and recommendation apart.
- Never say a slide was visually inspected unless you opened its rendered image. Never call a deck
  production-ready while a critical issue is open. Report scores as computed, not rounded up.
- Tell the user plainly that slide content in the PPTX is a flattened image and is not editable in
  PowerPoint; they edit the HTML and rebuild. The speaker notes carry each slide's text.
- If the person or team has a design system, it governs over this skill's defaults
  ([design-systems.md](references/design-systems.md)). Report its defects to its owner; do not hide them.
- A deck stored under a protected folder (for example `.claude/`) is built with `--out <elsewhere> --no-fix`.

## Setup (once per machine)

```bash
uv sync --group slides                       # python-pptx, playwright, pymupdf, pillow, numpy, pyspellchecker
uv run --group slides playwright install chromium   # only if Google Chrome is not installed
```

`D` below means `uv run --group slides python .claude/skills/presentation-creator-validator/scripts/deck.py`.
Rendering runs headed Chrome with the window parked off-screen (GPU rendering); `--headless` only where
no display exists. PowerPoint render-back needs Windows with PowerPoint; elsewhere it is reported as
not verified, never as passed.

## Workflow

1. **Input analysis.** Read every source. Write `brief.md`: purpose, audience, duration, objective,
   constraints, central message, sources. Ask only for what the material cannot answer.
   [storytelling.md](references/storytelling.md)
2. **Content structuring.** Write `storyboard.md` (number, claim title, takeaway, support and source,
   visual, composition, narrative purpose). Slide count follows duration and content, not habit.
3. **Art direction.** Write `art-direction.md`: direction, type pairing, palette with contrast ratios,
   grid, spacing, motifs, bans. [design-principles.md](references/design-principles.md),
   [typography.md](references/typography.md), [color-and-accessibility.md](references/color-and-accessibility.md)
4. **Slide design.** `D new <deck> --title "..."` (add `--design-system <folder>` to import one).
   Compose each slide for its content with the canvas library (`/__pcv__/pcv.css`,
   `/__pcv__/pcv-components.js`) or custom HTML/SVG. Vary compositions.
   [layout-patterns.md](references/layout-patterns.md), [data-visualization.md](references/data-visualization.md)
5. **Rendering.** `D render <deck>` (`--slides 3,5-7` to re-render some; `--scale 3` for 5760x3240;
   `--format jpeg` for photographic decks).
6. **Initial QA.** `D validate <deck> --no-renderback`, then open the PNGs in `build/images/`.
7. **Refinement.** `D fix <deck>` applies only safe fixes (shrink clipped text, never below the minimum;
   letterbox stretched images) as reviewable CSS in `<deck>/fixes/`. Fold accepted fixes into the
   slide source, delete `fixes/`, re-render. Everything else you fix by hand.
8. **Assembly.** `D assemble <deck>` and `D pdf <deck>`.
9. **Final validation.** `D review-kit <deck>`, then the visual review
   ([visual-review.md](references/visual-review.md)): a fresh-context reviewer opens every preview and
   the contact sheet and writes `build/review/review.json`. Then `D validate <deck>` (includes the
   PowerPoint render-back comparison) and `D report <deck>`.
   [validation-standards.md](references/validation-standards.md), [scoring-rubric.md](references/scoring-rubric.md)
10. **Delivery.** Give the user: `build/<name>.pptx`, `build/<name>.pdf`, `build/images/`, the deck
    folder (source), `build/validation/report.md`, `build/review/contact-sheet.png`. State the status
    line and the open issues; say which checks did not run.

`D build <deck>` runs 5 to 9 except the visual review; run `D report <deck>` again after writing review.json.

## Validating a foreign PPTX

`D inspect-pptx <file.pptx> --out <dir> [--sources a.pdf b.csv]` exports every slide through
PowerPoint, extracts its text, runs the image, content and file checks, and builds the review kit.
Layout checks that need the live page (clipping, overlap, font fallback) cannot run on a foreign
file; the report says so and the visual review covers them.

## Files

- `scripts/deck.py`, `scripts/pcv/`: pipeline. `scripts/renderback.ps1`: PowerPoint export.
- `canvas/`: base CSS, components, in-page inspector. `templates/deck/`: new-deck skeleton.
- Decks built on a design system follow [design-systems.md](references/design-systems.md).
- `tests/`: `uv run --group slides pytest .claude/skills/presentation-creator-validator/tests -p no:cacheprovider`.
