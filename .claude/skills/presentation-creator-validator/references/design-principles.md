# Design principles

How to make a slide look decided rather than generated. All numbers are CSS px on the 1920x1080 canvas. The validator measures geometry and contrast; it cannot judge taste, so everything here that it does not check is on you and the visual reviewer.

## 1. Set the art direction before the first slide

Write three lines into the brief before choosing a font or a colour:

1. **Purpose and room.** Persuade, inform, defend, teach? Projected in a lit seminar room, shared as a PDF, or read on a laptop? A PDF read alone tolerates 60 words per slide; a projected talk does not.
2. **Audience posture.** Examiners hunting for weak claims want visible evidence and sources. Executives want the decision first. Peers want the method.
3. **One adjective pair** that rules out the obvious: "quiet and exact", "loud and editorial", "dense but calm". Every later choice (type, palette, grid, image treatment) must be defensible against it.

Then pick **one** direction from the catalogue below and commit to its moves for the whole deck. Mixing two directions reads as no direction.

## 2. Direction catalogue

| Direction | Use when | Tell-tale moves |
|---|---|---|
| Modern editorial | Argument-led talks, research stories, anything with a narrative | Serif display titles (Fraunces, Newsreader, Instrument Serif) over a grotesk text face; generous left-aligned whitespace; kicker line above the title; pull-quote slides; thin rules instead of boxes |
| Swiss / International | Technical or analytical content that must look rigorous | Strict 12-column grid, flush-left ragged-right, one grotesk family in 2 weights, big numerals, asymmetric layouts, red or single strong accent, no ornaments |
| Minimalist | One idea per slide, keynote-style delivery where the speaker carries detail | 1 to 12 words per slide, 120 to 200px type, near-empty canvas, one accent used at most once per slide |
| Corporate premium | Business decks, funding asks, stakeholder updates | Restrained neutral palette with deep ink (navy, graphite, forest), 1 accent, crisp tables, consistent header band, executive-summary slide first |
| Academic | Course presentations, thesis defences, conference talks | Claim titles, numbered citations with a references slide, source notes on every data slide, method diagrams, honest error bars; plain but exact |
| Technical | Architecture, systems, pipelines, code | Mono accents (IBM Plex Mono, JetBrains Mono) for identifiers only, orthogonal-connector diagrams, dotted or lined backgrounds (`.pcv-bg-dots`, `.pcv-bg-lines`), dense but aligned |
| Dark cinematic | Short, high-stakes talks in a dark room; product reveals | Near-black ground (not #000), one luminous accent, large display type, full-bleed imagery with scrims, slow reveal of one number per slide. Avoid in lit rooms |
| Bold typographic | Opening and section slides, manifestos, talks with few visuals | Type as the image: 160 to 320px words, tight tracking, colour blocks, cropped letterforms using `data-pcv-allow="bleed"` deliberately |
| Data-driven infographic | Results-heavy decks where numbers carry the story | Every slide built around one chart or one number; direct labels; consistent scales across slides; annotation callouts; colour reserved for the point being made |

## 3. Visual hierarchy

- **Three levels, no more, per slide**: the claim (title or hero number), the evidence (chart, diagram, table), the support (labels, source note). If you need a fourth level, split the slide.
- **Size ratio between levels at least 1.5x.** A 64px title over 40px body reads as one level; 64px over 32px reads as two. The scale in `typography.md` builds this in.
- **One focal point.** The eye should land on one element within a second. Test: squint at the rendered PNG (or the 640px thumbnail on the contact sheet). If two things compete, demote one in size, weight or colour.
- **Colour is the most expensive emphasis.** Use the accent on at most one element or one data series per slide. Everything else is ink, ink-2 or ink-3.
- Weight and size before colour; position before both (top-left is read first in left-to-right languages).

## 4. Gestalt, applied

- **Proximity**: the gap between groups must be at least 2x the gap inside a group (e.g. 16px between a label and its value, 48px between two label/value pairs). Equal spacing everywhere destroys grouping.
- **Similarity**: same role, same treatment, across the whole deck. All source notes identical; all chart labels identical. The validator flags title size and x-position drift across slides (`title-size-inconsistent`, `title-position-inconsistent`).
- **Common region**: prefer whitespace and a single rule over drawing a box. A card is justified only when the content inside is a self-contained unit the speaker will point at.
- **Continuity and alignment**: every element's left edge sits on a column line. Count the distinct left edges on a slide; more than 3 or 4 looks accidental.
- **Figure/ground**: keep enough empty space that the figure is obvious. Aim for 30 to 45% of the canvas empty on content slides.

## 5. Grid

Default frame (the `pcv.css` tokens `--pcv-margin`, `--pcv-margin-y`, `--pcv-col`, `--pcv-gutter`): 112px side margins, 96px top and bottom margins, content area 1696x888, 12 columns of 112px with 32px gutters. Column n starts at x = 112 + (n - 1) x 144: 112, 256, 400, 544, 688, 832, 976, 1120, 1264, 1408, 1552, 1696. `.pcv-frame` is that content box; `.pcv-grid` is the same 12 columns as CSS grid (`grid-column: 1 / span 7`). The validator's safe margin is 64px (`rules.safe_margin_px`): text inside it is flagged `outside-safe-area` (minor), so a deck may tighten the margins to 64px but no further.

- Spans that work: 12 (full), 8+4, 7+5, 6+6, 4+4+4, 3+9, 5 (text) + 7 (figure).
- Asymmetric splits (7/5, 8/4, 3/9) look designed; 6/6 looks like a template. Use 6/6 only for true comparisons.
- Vertical rhythm on an 8px baseline: every gap is a multiple of 8 (16, 24, 32, 48, 64, 96).
- Keep the title block at the same y and x on every content slide. Vary what is below it, not the frame.

## 6. Balance

- **Asymmetric balance** (large element left, smaller dense element right, or the reverse) is the default for content slides. Symmetric, centred layouts are for openings, section breaks and single statements only.
- Visual weight grows with size, darkness, saturation and isolation. A small saturated accent element balances a large grey block.
- Do not centre body text. Centred multi-line text has no left edge to return to.

## 7. Density and cognitive load

- **One job per slide** (see `storytelling.md`). If the title needs "and", it is two slides.
- Words per content slide: 15 to 40 for a projected talk, up to about 70 for a read-alone PDF. The validator's default `max_words` is 90 (text inside `data-pcv-source` and `data-pcv-nocheck` is not counted) and reports `dense-slide` as minor; treat 90 as a ceiling, never a target.
- At most 3 bullets, and prefer none: a two-column claim/evidence layout or a numbered sequence carries structure better than bullets.
- Show the minimum data that proves the claim. Move the rest to an appendix slide or a table in the paper.
- Progressive disclosure across slides (build the same chart over 2 slides, second one with the highlight) beats one overloaded slide.

## 8. Ban list: generic AI-presentation tropes

| Trope | Do instead |
|---|---|
| Purple-to-blue gradient backgrounds, mesh blobs, aurora glows | A flat ground from the palette; texture only via `.pcv-bg-grain`, `.pcv-bg-dots` or `.pcv-bg-lines` at low intensity |
| Glassmorphism cards, frosted panels, soft drop shadows on everything | Whitespace and one hairline rule (1 to 2px, `--pcv-rule`) |
| Three equal cards each with an icon in a circle | A real comparison table, a numbered sequence, or one strong statement |
| Emoji or icon-font bullets | Numbers, short rules, or no markers at all |
| Bold lead-in bullets ("**Scalable:** it scales") | A claim sentence; or a two-column label/explanation list where labels are nouns |
| Topic titles: "Introduction", "Results", "Methodology", "Overview" | Claim titles that state what the slide proves |
| Agenda slide listing every section | A one-line roadmap on the first content slide, or none for talks under 15 minutes |
| A giant number with no comparison, unit or source | The number plus its baseline, unit and `data-pcv-source` note |
| Gradient or outlined text, word-art, 3D charts | Solid ink; flat 2D charts |
| Clichéd metaphors: brains, robots, lightbulbs, puzzle pieces, rockets, handshakes, circuit boards | The real thing: the actual data example, the actual architecture, the actual output |
| AI-generated or stock imagery | Diagrams, charts, real screenshots and real examples drawn in HTML/SVG. This skill never uses AI image generation |
| Rounded-corner-everything (16px radius on every box) | Square corners or a single small radius (2 to 4px) used consistently |
| Every element centred | Flush-left on the grid; centre only statements |
| "Thank you!" / "Questions?" end slide | A conclusion slide that restates the central message and the ask, with contact details |
| Identical layout on every slide | Vary composition between consecutive slides (`layout-patterns.md`) while keeping the frame fixed |
| Neon accents on black, glowing edges | One accent at checked contrast; dark ground #0E1116 to #16181D, not #000 |

## 9. Before rendering, ask

1. What is the one thing the audience should see first? Is it the largest or highest-contrast element?
2. Does every left edge sit on a column line?
3. Is the accent used once?
4. Would this slide look identical in a generic template deck? If yes, apply one move from the chosen direction.
5. After rendering: open the PNG with Read and the contact sheet; judge the deck's rhythm, not just each slide.
