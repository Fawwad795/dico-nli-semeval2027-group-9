# Data visualization

A chart on a slide answers one question, and the claim title states the answer. Every value drawn must come from a committed source file listed in deck.json `sources`.

## 1. Choose the chart from the question

| Question | Chart | Notes |
|---|---|---|
| Which is bigger? (categories) | Horizontal bar (`PCV.barChart`, default orientation) | Sort by value unless the categories have a natural order; horizontal bars fit long labels |
| How did it change? (ordered x: epochs, time, size) | Line (`PCV.lineChart`) | Points or a line, never bars, for many ordered x values |
| How do a few groups compare across a few conditions? | Grouped bars as small multiples, one `barChart` per condition | Two to four panels with identical scales |
| What is the exact value? | Table (`PCV.table`) | When readers will quote numbers |
| Where do predictions go wrong? (classification) | Confusion matrix as a table with counts in cells | Label rows "gold" and columns "predicted"; emphasise the cells the slide is about |
| How are values distributed? | Histogram, strip or box plot, hand-built in inline SVG | State n |
| Do two quantities move together? | Scatter, hand-built in inline SVG | Label the points that matter directly |
| One decisive result | Hero number plus its comparison (statistics pattern in `layout-patterns.md`) | No chart needed |
| Part of a whole | A single 100% stacked bar, or plain bars of shares | Pies only for 2 slices; never donuts, never 3D |

If you cannot write the claim title for the chart, you have not decided the question yet.

## 2. Honest axes

- **Bars start at zero.** Bar length encodes value; a cut axis exaggerates differences. The validator reports `truncated-bar-axis` (major) for any bar chart whose `data-pcv-chart` says `yMin` is not 0. If the differences only show with a non-zero start, use dot or line marks and label the axis start clearly.
- Lines may start above zero when the range of interest is narrow, but the axis must be labelled and the visible range stated. Do not choose a range that turns noise into a slope.
- **Same scale for anything compared.** Panels of a small multiple, and the same metric on different slides, share `min` and `max`. The components default `max` to a nice ceiling per chart, so pass `min` and `max` explicitly on every panel.
- No dual y-axes. Use two aligned panels.
- No 3D, no perspective, no shading on marks.
- For bounded metrics (F1, accuracy in 0 to 1), a 0 to 1 axis is honest and often clarifying; if every bar is between 0.6 and 0.7, that sameness is the finding.

## 3. Labels, not legends

- Label values directly on or next to the marks; label series at the line end (`lineChart` does this; no legend box).
- Put the unit in the axis title or the chart title, not after every value.
- Tick and value labels at 22 to 24px minimum (validator floor 20px, `text-too-small`).
- Fewer ticks: 3 to 5 gridlines in `--pcv-rule`; delete the axis line when gridlines exist.
- Value precision follows the source: show the decimals the result supports, consistently across the deck.

## 4. Emphasis

- One series or one bar in `--pcv-accent` (`emphasis: true`); everything else in a neutral (`ink-3` or a light grey). The emphasised element is what the title talks about.
- Annotate instead of explaining in body text: a short label next to the point ("reversal errors drop here") in ink at 24px.
- Order and position emphasise too: put the method under discussion first or last, consistently across the deck.
- Never emphasise by hue alone when the distinction matters; add a label or weight (`color-and-accessibility.md`).

## 5. Uncertainty

- Results from several seeds or folds are shown as mean ± sd (or a confidence interval), with the number of runs stated: "mean ± sd over n seeds" in the axis title or source note. Say which measure it is; sd, standard error and a 95% CI are not interchangeable.
- A single run is labelled as a single run. Do not draw error bars that were not measured.
- In a table, write cells as "m ± s" with the same decimals for both. Both numbers are checked against the sources, so both must appear there (or be derivable as ×100 / ÷100 of a source value).
- The bar component draws no error bars. For interval plots, hand-build a dot-and-whisker chart in inline SVG and set `data-pcv-chart` yourself (section 7).
- If two intervals overlap substantially, the title must not claim a winner.

## 6. Tables versus charts

Use a table when exact values will be quoted, units are mixed, or there are few values (up to about 20 cells on a slide). Use a chart when the shape (ranking, trend, gap) is the point.

Table rules (`PCV.table`): numeric columns right-aligned with tabular figures (`numeric: true`); one emphasised row (`emphasisRow`) for the method under discussion; no vertical rules; header in ink-2 at the label size; at most about 6 rows and 5 columns on a projected slide, the rest to a backup slide.

## 7. What the validator checks on charts

Chart components set `data-pcv-chart` on the chart element with `{"type": "bar" | "line", "yMin": number, "valueLabels": [exact strings drawn]}`. The validator then:

- reports `truncated-bar-axis` (major) when `type` is `"bar"` and `yMin` is not 0;
- reports `chart-label-mismatch` (major) for each string in `valueLabels` that is not exactly the trimmed text of some `<text>` or `[data-pcv-label]` element inside the chart element. A label that was dropped, overlapped away or formatted differently fails;
- silently skips both checks if the attribute is not valid JSON. Keep it machine-written.

Other checks that hit charts:

- **Numbers:** every number in the slide's DOM text, SVG `<text>` included, is checked against the source files (`unsupported-number`). Integers below 10 (deck rule `min_integer_checked`) are skipped. Axis tick labels such as 0.2 and 0.4 are numbers too: if they are reported, the tick group needs `data-pcv-nocheck`. Never put `data-pcv-nocheck` on value labels.
- **Raster charts escape the number check.** Numbers inside a PNG, or inside an SVG loaded through `<img>`, are pixels, not text, so nothing verifies them. Draw charts as inline SVG or HTML (the PCV components) so every value is checked. A raster image is also flagged `image-low-resolution` when its natural width is under 0.8x its CSS width times the device scale of 2 (so a 960px-wide slot needs at least 1536px; under 960px is major).
- **Overlap:** HTML text positioned over an `svg`, `img` or `canvas` that is not its ancestor is `text-over-graphic` (major). Put annotations inside the chart's SVG, in the chart's margin, or inside the chart host; mark a purely decorative graphic `aria-hidden="true"` or `data-pcv-allow="decor"`.
- **Contrast:** SVG text is measured with its `fill` against the rendered pixels behind it. Labels inside light bars need dark ink.

## 8. Using the components

Link `/__pcv__/pcv.css` and `/__pcv__/pcv-components.js`. Give the host an explicit size from the grid; charts default to the host box. Draw from the data file itself where possible, so the drawing and the source cannot drift: files inside the deck folder are served at `http://deck.local/<path>`, so a slide can `fetch` them. Files outside the deck folder are not served; copy the values and list the original file in deck.json `sources` so the number check traces them.

```html
<!-- columns 1-8: x = 112, width = 8 x 144 - 32 = 1120 -->
<div id="f1-chart" style="position:absolute; left:112px; top:320px; width:1120px; height:600px"></div>
<script src="/__pcv__/pcv-components.js"></script>
<script>
  PCV.ready(fetch('data/results.json').then(r => r.json()).then(d => {
    PCV.barChart(document.getElementById('f1-chart'), {
      data: d.models.map(m => ({ label: m.name, value: m.weighted_f1, emphasis: m.name === d.highlight })),
      orientation: 'horizontal', min: 0, max: 1, digits: 3,
      ariaLabel: 'Weighted F1 by model, test split'
    });
  }));
</script>
```

- `barChart(host, {data, orientation, digits, min, max, width, height, unit, colors, ariaLabel})`: `min` defaults to 0, keep it there; `digits` is the number of decimal places printed, match it to the source. With negative values the component lowers `min` to a nice floor below zero, and the check reports any `yMin` other than 0, so a signed (diverging) bar chart is flagged; prefer a dot plot for signed values.
- Label size: charts take `fontSize` (default 24; line-chart ticks are drawn 2px smaller, never below 20).
- `lineChart(host, {series: [{name, points: [[x, y], ...], emphasis}], xLabels, min, max, digits, width, height, colors})`: one `emphasis: true` series; end labels are drawn instead of a legend.
- `table(host, {columns: [{label, align, numeric}], rows, emphasisRow, digits})`.
- Override `colors` only to map onto the deck's theme tokens; the defaults follow the custom properties.
- Wrap asynchronous drawing in `PCV.ready(promise)` so the renderer waits; without it a chart can be missing from the PNG.

After rendering, open the PNG with Read: check that labels did not collide, the emphasised bar is the one the title names, and the source note is present. Then read the report for `chart-label-mismatch`, `truncated-bar-axis` and `unsupported-number` on that slide.
