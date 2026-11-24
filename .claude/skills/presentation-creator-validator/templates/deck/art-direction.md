# Art direction

## Direction

Editorial and measured: a printed research report rather than a pitch deck. Warm paper ground, near-black ink, one vermilion accent that only ever marks the thing the slide is about. The recurring motif is the ruler: a 2px rule across the 12 columns with a tick at every column edge.

## Type pairing

| Role | Face | Use |
|---|---|---|
| Display | Newsreader 400 (italic for a single emphasised word) | Titles, big numbers |
| Text | IBM Plex Sans 400, 500, 600 | Body, labels, chart text, tables |
| Mono | IBM Plex Mono 400, 500 | Kickers, folios, dates |

Scale at 1920x1080: display 112-120, h1 64, h2 36, lead 34, body 28, small 22, source notes 20. Nothing below 20px. Numbers use tabular figures.

## Palette

| Token | Value | Contrast on `--pcv-bg` | Use |
|---|---|---|---|
| `--pcv-bg` | #F4F1EA | | Ground |
| `--pcv-ink` | #15171C | 15.9:1 | Titles, values |
| `--pcv-ink-2` | #3B3F47 | 9.4:1 | Body, unemphasised bars |
| `--pcv-ink-3` | #62666E | 5.1:1 | Kickers, notes, axis labels |
| `--pcv-accent` | #B83D12 | 5.0:1 | The one emphasised element per slide |
| `--pcv-accent-2` | #1E5A78 | 6.7:1 | A second series only when a chart needs one |
| `--pcv-rule` | #D3CEC3 | 1.4:1 | Hairlines only, never text |
| `--pcv-mark` | #ABA699 | 2.2:1 | Context bars and lines, never text |

## Grid and spacing

- Margins 112px left and right, 96px top and bottom.
- 12 columns of 112px with 32px gutters (1696px content width).
- Spacing steps of 8px; titles sit at the top margin, source notes and folios on the bottom margin.

## Motifs

- The ruler (title slide, section openers).
- 2px ink rules to open and close tables and to mark a chart baseline; 1px hairlines between rows.
- Direct labels on every series and bar; no legends.

## What to avoid

- Drop shadows, gradients, rounded cards, icons used as decoration.
- More than one accent per slide; colour that carries no meaning.
- Bar charts that do not start at zero; axis labels where direct value labels would do.
- Text under 20px, centred paragraphs, titles that are topic labels instead of claims.
- AI-generated images.
