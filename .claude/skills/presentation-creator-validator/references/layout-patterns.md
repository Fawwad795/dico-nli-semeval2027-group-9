# Layout patterns

A catalogue mapping content types to compositions on the 12-column grid from `design-principles.md` and `pcv.css` (112px side and 96px top/bottom margins, 12 x 112px columns, 32px gutters; column n starts at x = 112 + (n - 1) x 144; a span of k columns is 144k - 32 px wide). Wireframes show columns 1 to 12 across, the title band at the top. `T` is the claim title, `S` the source note.

Patterns are starting points, not templates. Two rules for any deck:

1. **Fixed frame, varied composition.** Title position, title size, margins and source-note position stay identical on every content slide (the validator flags title size and x drift). What sits below the title changes.
2. **No two consecutive slides share a composition.** If slides 5 and 6 are both 7/5 text-plus-chart, flip one to 5/7, make one full-width, or turn one into a statement slide. Check rhythm on the contact sheet the review kit produces.

Common vertical bands (adjust per deck, keep consistent): `.pcv-head` at y = 96 holds the kicker and, 20px below it, the title (two lines at 64px end near y = 270); content y = 320 to about 940; `.pcv-foot` holds the source note (left) and folio (right) with its bottom edge at y = 1008, inside the 64px safe margin. Slide numbers of 10 and above are numbers to the content check, so give the folio `data-pcv-nocheck`.

---

### Opening

```
 1  2  3  4  5  6  7  8  9 10 11 12
+-----------------------------------+
| KICKER (course, venue, date)      |
|                                   |
| CENTRAL MESSAGE AS A CLAIM,       |
| DISPLAY TYPE 88-128px (cols 1-9)  |
|                                   |
| names, affiliation (1-6)    [mark]|
+-----------------------------------+
```
Use: first slide. The title is the deck's central message, not the topic. Optional single strong graphic (a real example from the data, a diagram fragment) in cols 9 to 12.
Fails when: it says only the topic ("DiCo-NLI"), centres everything, or uses a stock or generated hero image.

### Problem framing

```
+-----------------------------------+
| T: what is broken, as a claim     |
|                                   |
| [ concrete example: real input  ] |  cols 1-7
| [ and the wrong/inconsistent    ] |
| [ output, drawn large           ] |
|                      why it matters| cols 9-12, 2-3 short lines
+-----------------------------------+
```
Use: establishing the problem with one concrete instance before any abstraction.
Fails when: the example is invented rather than taken from the data, or replaced by bullets describing the problem in general terms.

### Editorial storytelling (statement)

```
+-----------------------------------+
|                                   |
|   ONE SENTENCE, 64-88px,          |  cols 2-10
|   THE TURN IN THE ARGUMENT        |
|                                   |
|   attribution or one line (2-7)   |
+-----------------------------------+
```
Use: transitions, the key insight, a quotation from a source. Maximum about one in five slides.
Fails when: overused, or the sentence is a platitude rather than a claim the talk then proves.

### Comparison

```
+-----------------------------------+
| T: A beats B on X, loses on Y     |
| A (cols 1-6)     | B (cols 7-12)  |
| row: criterion 1 | criterion 1    |
| row: criterion 2 | criterion 2    |
| verdict line across 1-12          |
+-----------------------------------+
```
Use: two options, methods or conditions on the same criteria. The one true use of 6/6. For more than two options or more than four criteria, use a table (`PCV.table`).
Fails when: the two sides have different criteria, or the winner is marked only by colour (add a label or weight).

### Architecture diagram

```
+-----------------------------------+
| T: what the architecture enables  |
|                                   |
| [in] --> [enc] --> [head] --> [out]|  cols 1-12, PCV.flow
|            |                       |
|          [aux]   callout (10-12)   |
+-----------------------------------+
```
Use: system structure, model architecture, data pipeline. Draw with `PCV.flow` (HTML nodes, orthogonal SVG connectors). Left-to-right flow, one emphasised node (`tone: "accent"`) for the part the slide is about.
Fails when: more than about 8 nodes, crossing connectors, every node accented, or explanatory text placed on top of connectors (`text-over-graphic`).

### Process

```
+-----------------------------------+
| T: the procedure in one sentence  |
|  01        02        03        04 |
|  step      step      step      step|  4 x 3 cols
|  1-2 lines each                    |
+-----------------------------------+
```
Use: ordered steps, 3 to 5 of them. Numbers are the markers; no icons in circles.
Fails when: steps are not actually sequential (use a list or table), or step text exceeds about 15 words each.

### Timeline

```
+-----------------------------------+
| T: what changed over time         |
|                                   |
| --o--------o-------o--------O---- |  PCV.timeline
|  when     when    when     WHEN   |
|  label    label   label    LABEL  |
+-----------------------------------+
```
Use: history of an approach, project schedule, milestones. Emphasise the item the talk is about (`emphasis: true`). Every year shown is a number the content check traces to a source; put dates in a source file or mark the axis `data-pcv-nocheck`.
Fails when: uneven time is drawn with even spacing without saying so, or there are more than about 7 items.

### Statistics (hero number)

```
+-----------------------------------+
| T: what the number means          |
|                                   |
|  N.NNN        vs  N.NNN           |  number cols 1-6 (128-240px),
|  our method       baseline        |  comparison cols 7-11
|                                   |
| S: source, seed, split            |
+-----------------------------------+
```
Use: one decisive result. Always pair the number with its comparison, unit and a `data-pcv-source` note.
Fails when: the number has no baseline, the comparison is cherry-picked, or the number does not appear in a deck.json source (`unsupported-number`).

### Findings (chart plus interpretation)

```
+-----------------------------------+
| T: the finding as a claim         |
| [ chart, PCV.barChart  ] | so what |  chart cols 1-8,
| [ direct labels        ] | 2-3     |  text cols 9-12
| [ emphasis on 1 bar    ] | lines   |
| S: source                         |
+-----------------------------------+
```
Use: the workhorse results slide. Alternate with the mirrored version (text 1-4, chart 5-12) or a full-width chart to vary rhythm.
Fails when: the title describes the chart ("F1 by model") instead of the finding, or the interpretation repeats the numbers.

### Methodology

```
+-----------------------------------+
| T: how we tested it, in one line  |
| DATA        | MODEL      | METRIC |  3 x 4 cols
| what, size  | what, how  | what   |
| -----------------------------------|
| controls: seeds, splits (1-12)    |
+-----------------------------------+
```
Use: experimental setup. Labels are nouns, content is specific (dataset version, split sizes, seeds) and sourced.
Fails when: it turns into a dense paragraph, or omits what makes the comparison fair.

### Technical concept

```
+-----------------------------------+
| T: the idea, plainly              |
| [ worked example, step by    ] | definition |
| [ step, real values, cols 1-7] | cols 9-12  |
|                                | formula in |
|                                | mono/serif |
+-----------------------------------+
```
Use: a definition, metric or algorithm. Lead with the example; the formal statement supports it.
Fails when: only the formula is shown, or the example uses values that are not traceable.

### Conclusion

```
+-----------------------------------+
| T: the central message, restated  |
| 1  finding (cols 1-8)             |
| 2  finding                        |
| 3  limitation, stated honestly    |
|                    ask / next step| cols 9-12
| contact, repo (small)             |
+-----------------------------------+
```
Use: last content slide. Restates the central message from the opening, the evidence, the limits, and the ask.
Fails when: it is "Thank you" or "Questions?", introduces new results, or drops the limitations.

---

## Varying a sequence

Example rhythm for ten slides: opening, problem framing, statement, methodology, findings (chart left), statistics, findings (chart right), comparison table, technical concept, conclusion. Read the sequence on the contact sheet: alternating density (dense, light, dense) and alternating orientation (left-heavy, right-heavy, full) is what keeps a deck from looking templated.
