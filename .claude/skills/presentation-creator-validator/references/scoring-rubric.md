# Scoring rubric

How a deck is scored and given a status. `scripts/pcv/score.py` implements it; this file states the same rules and how to apply them. Scores are a summary for the reader, never a target to tune toward. A low score reported honestly is the correct result.

## Categories and weights

Nine categories, each scored 0-10. The weights sum to 100.

| Category (`key`) | Weight | Scored by |
|---|---:|---|
| Visual design and aesthetics (`visual_design`) | 15 | reviewer, capped by findings |
| Typography and readability (`typography`) | 12 | reviewer, capped by findings |
| Layout and composition (`layout`) | 12 | reviewer, capped by findings |
| Information hierarchy (`hierarchy`) | 10 | reviewer, capped by findings |
| Content accuracy (`content_accuracy`) | 15 | reviewer, capped by findings |
| Storytelling and narrative flow (`storytelling`) | 10 | reviewer, capped by findings |
| Data visualization (`data_visualization`) | 8 | reviewer, capped by findings |
| Consistency across slides (`consistency`) | 8 | reviewer, capped by findings |
| Technical integrity (`technical`) | 10 | automated checks only |

## Anchors (every category)

| Score | Meaning |
|---|---|
| 9-10 | Professional work a careful expert would not fault; distinctive and purposeful. |
| 7-8 | Solid, with only minor issues. |
| 5-6 | Acceptable but noticeably weak: several minor problems or one major. |
| 3-4 | Significant problems that impair communication. |
| 0-2 | Broken, misleading or unreadable. |

`"n/a"` only when the category genuinely does not apply, for example `data_visualization` in a deck with no data. It is not a way to avoid scoring a weak category.

## Criteria per category

- **visual_design**: composition quality, a purposeful visual language, absence of generic AI-slide tropes (card grids, decorative icons, gradient blobs, title plus three boxes everywhere), image quality.
- **typography**: a hierarchy of sizes and weights, readability at presentation distance (nothing that reads small on a projector), consistent families, line length and leading.
- **layout**: alignment to a grid, consistent margins, balance, spacing rhythm, no crowding, no empty space without a purpose.
- **hierarchy**: one clear focal point per slide, a title that states the takeaway, an obvious eye path.
- **content_accuracy**: text matches the sources, numbers are right, labels are correct, no unsupported claims, correct spelling.
- **storytelling**: the sequence builds an argument, each slide has one job, transitions are logical, the ending lands.
- **data_visualization**: the right chart for the question, honest axes, direct labels, readable, emphasis on what matters.
- **consistency**: repeated elements in the same place and style across slides, one visual identity, compositions that vary but still belong together.
- **technical**: render integrity, assets, fonts, output files and the PowerPoint render-back, from automated checks only.

Every score needs a rationale that cites slide numbers. `review.py` rejects a numeric score with an empty rationale; citing slides is the reviewer's duty, and an uncited rationale is a weak review even when it validates. Never inflate a score.

## The cap from open findings

Open findings in a category put a ceiling on its score (`cap_for` in `score.py`). Findings with status other than `open` do not count. `info` findings never count.

```
cap = 10 - 1 x (open majors) - min(2, 0.25 x (open minors))
if open criticals >= 1:  cap = min(cap, 4 - (criticals - 1))
cap = max(0, cap)
```

So one critical caps the category at 4, two at 3, three at 2. Minor findings can take off at most 2 points in total.

Findings count in the category they carry: the automated categories listed in `validation-standards.md`, and for review findings the category the reviewer gave. A review finding raises the same cap as an automated one.

## Category score

- **technical**: score = cap. Nobody overrides it.
- **reviewer-scored categories**: score = min(reviewer score, cap), rounded to one decimal. When the cap lowers the score, the report appends `[capped from <reviewer score> to <cap> by open findings]` to the rationale.
- **"n/a"**: the category is left out of the overall score. Its open findings still count toward the deck status.
- **missing review**: when `review/review.json` is missing or fails validation (any problem `load_review` reports), every reviewer-scored category is "not assessed" and has no score. The technical score is still shown.

## Overall score

Computed only when every category has a score or `"n/a"`:

```
overall = round(10 x sum(weight x score) / sum(weight), 1)     over categories that are not "n/a"
```

The result is out of 100. **An overall score is not computed while the visual review is missing or incomplete**; the report says so instead of showing a number. Do not estimate one by hand.

## Status

Checked in this order; the first that applies wins.

1. **NOT READY**: any open critical finding, automated or from the review.
2. **INCOMPLETE**: the visual review is missing or invalid, or a pipeline stage did not complete (render errors, or the PPTX or PDF missing when validated).
3. **READY WITH WARNINGS**: any open major finding, or the PowerPoint render-back not verified.
4. **PRODUCTION-READY**: otherwise.

As implemented, render-back counts as "not verified" for status only when it was attempted and did not succeed (`renderback_verified` is `false`, which includes PowerPoint being unavailable). With `--no-renderback` the flag stays unset and does not by itself prevent PRODUCTION-READY. Report that limitation in words: a deck built with `--no-renderback` has not been checked in PowerPoint, whatever its status line says.

The same scorer runs for `deck.py inspect-pptx` (a PPTX this skill did not build). There the stages are "exported by PowerPoint" and "PPTX opened"; render-back does not apply, and review findings are not imported (only the review's scores), so open review findings do not cap categories or set the status in that mode.

## Worked examples

**Category with minors and a major.** The reviewer gives `layout` 8. Open layout findings: 1 major (`text-overlap`) and 3 minor (`outside-safe-area`).
cap = 10 - 1 - min(2, 0.75) = 8.25. Score = min(8, 8.25) = **8.0**. The cap does not bind.

**Cap binds.** The reviewer gives `typography` 9. Open typography findings: 2 major (`title-wraps`, `font-fallback`) and 10 minor (`off-scale-font-size`).
cap = 10 - 2 - min(2, 2.5) = 6.0. Score = min(9, 6.0) = **6.0**, reported as "[capped from 9 to 6.0 by open findings]".

**Critical.** The reviewer gives `content_accuracy` 8. Open findings: 1 critical (a review finding: a sign error in a reported result) and 1 major (`unsupported-number`).
cap = min(10 - 1, 4 - 0) = 4.0. Score = **4.0**, and the deck is NOT READY.

**Technical.** Open technical findings: 1 major (`asset-request-failed`), 2 minor (`console-error`), 1 info (`renderback-unavailable`).
cap = 10 - 1 - 0.5 = 8.5. Technical = **8.5**. The info finding costs nothing, but render-back is unverified, so the status can be at best READY WITH WARNINGS.

**Overall with an n/a.** Category scores: visual_design 8, typography 7, layout 8, hierarchy 7, content_accuracy 9, storytelling 7, data_visualization n/a, consistency 8, technical 8.5.

```
sum(weight x score) = 15x8 + 12x7 + 12x8 + 10x7 + 15x9 + 10x7 + 8x8 + 10x8.5
                    = 120 + 84 + 96 + 70 + 135 + 70 + 64 + 85 = 724
sum(weight)         = 100 - 8 = 92
overall             = round(10 x 724 / 92, 1) = 78.7
```

With `data_visualization` scored 6 instead of n/a: (724 + 48) / 100 x 10 = **77.2**.

**Review missing.** Same deck, no `review.json`: technical 8.5 is shown, the eight other categories show "-", the overall score is "not computed", and the status is INCOMPLETE (or NOT READY if a critical is open).
