# Storytelling

A deck is an argument delivered in a fixed time to a specific audience. Write the brief and the storyboard before any HTML; design follows from them, not the reverse.

## 1. Purpose and audience analysis

Answer in the brief, one line each:

| Question | Why it changes the deck |
|---|---|
| What must the audience **do or believe** afterwards? | Sets the central message and the ask on the last slide |
| Who are they, and what do they already know? | Sets how much setup the problem needs; examiners and peers skip basics, mixed audiences need one concrete example first |
| What will they be **looking for**? | Examiners look for weak claims and missing baselines; managers for cost and decision; peers for method. Put the answer where they look |
| How long, in what room, presented or read? | Sets slide count, word density and type size (`typography.md`) |
| What are they likely to object to? | Each strong objection gets a slide or a backup slide |

## 2. Central message

One sentence, at most about 25 words, that is a claim someone could disagree with. Test: could it be the opening slide's title? Could the conclusion slide restate it with evidence?

- Weak: "We study directional NLI." (topic)
- Strong form: "<Method> keeps predictions consistent under pair reversal, at <cost> in accuracy." (claim, with the trade-off stated; fill the brackets only with measured results)

If the results do not support the hoped-for message, the message changes. A method that loses to the baseline is reported as losing.

## 3. Narrative arcs

**Research talk (problem, gap, approach, evidence, limits):**

1. Opening: the central message.
2. Problem with one concrete example from the data.
3. Why existing approaches fall short (the gap), with citations.
4. The approach: the one idea, then the mechanism.
5. Methodology: data, baselines, metrics, controls (seeds, splits).
6. Results: the main finding first, then the supporting ones.
7. Analysis: where it fails, error examples, ablations.
8. Limitations and threats to validity.
9. Conclusion: message restated, contributions, next steps.

**Business deck (answer first, SCQA: situation, complication, question, answer):**

1. Opening: the recommendation and its headline consequence.
2. Situation: what is true now, shared ground.
3. Complication: what changed or what is at risk.
4. Answer: the recommendation, with options considered.
5. Evidence: two or three supporting proofs.
6. Cost, risk, timeline.
7. The ask: the decision needed, by when, from whom.

**Course progress presentation:** goal, what was done, what was measured (with numbers as measured), what did not work, what is next, what help is needed.

## 4. One job per slide

Every slide does exactly one of: state, show evidence, explain, compare, transition, ask. If a slide does two, split it. Symptoms of two jobs: a title with "and", two charts, or a chart plus a paragraph that is about something else.

## 5. Claim titles

The title is the slide's takeaway written as a sentence, 8 to 14 words, sentence case, no full stop. Reading only the titles in order must tell the whole story (the "title-only read" test; the contact sheet makes this easy).

| Topic title (avoid) | Claim title |
|---|---|
| Results | <Method> beats <baseline> on <metric> but loses on <other metric> |
| Dataset | <Majority label> dominates, so accuracy alone flatters a majority-class guess |
| Related work | Prior <approach> ignores <property>, which hides <error type> |

The brackets show form only. Fill them only with findings that are measured or cited; if the data says otherwise, the title says otherwise.

The validator reports titles wrapping past 2 lines and identical titles on two slides (`duplicate-title`). It cannot tell a topic title from a claim; the reviewer checks that.

## 6. Transitions

- The last element of a slide should set up the next slide's question. Write the transition line in speaker notes (`<slide>.notes.md`) even if it is not shown.
- Use a statement slide (editorial pattern) at the turns in the argument: problem to approach, approach to results, results to limits.
- Repeat a visual element across slides to carry continuity: the same chart re-drawn with a new highlight, the same architecture with a different node emphasised.
- For talks over about 15 minutes, a running section marker (small kicker) beats an agenda slide.

## 7. Slide count from duration

| Talk length | Content slides | Notes |
|---|---:|---|
| 5 min | 4 to 6 | One finding; no methodology detail |
| 10 min | 7 to 10 | One slide per 1 to 1.5 minutes |
| 15 min | 10 to 14 | |
| 20 min | 12 to 18 | Add one statement slide per section |
| 30 min | 18 to 25 | |

Opening and conclusion count as content slides. Backup slides (extra results, detailed tables) go after the conclusion and do not count. Dense technical slides take 2 to 3 minutes each; statement slides 20 to 30 seconds. Rehearse with a timer; cut slides, not speaking speed.

## 8. The brief

Write before the storyboard, in the deck folder (`brief.md`):

```markdown
# Brief: <deck title>
- Purpose: <what the audience should do or believe afterwards>
- Audience: <who, prior knowledge, what they look for>
- Setting: <duration, room, projected or read, presenter(s)>
- Central message: <one sentence claim>
- The ask: <decision, feedback or action wanted>
- Art direction: <direction from design-principles.md> + <adjective pair>
- Sources: <committed files the numbers come from; these go into deck.json "sources">
- Constraints: <template, design system, required sections, deadline>
- Objections to pre-empt: <list>
```

## 9. The storyboard

One block per slide, in order, before any HTML (`storyboard.md`). Fields:

```markdown
## 04
- title: <the claim, as the slide will show it>
- takeaway: <one sentence the audience keeps>
- support: <evidence, and the committed file it comes from, e.g. results/main.csv>
- visual: <what is drawn: bar chart of X by Y with Z emphasised; architecture with node N accented>
- composition: <layout pattern from layout-patterns.md, and how it differs from slides 03 and 05>
- narrative purpose: <state | evidence | explain | compare | transition | ask, and how it moves the argument>
- sources: <citation keys from deck.json references, and source files>
```

Storyboard checks before designing:

1. Titles alone tell the story.
2. Every number in `support` is in a file listed in deck.json `sources` (the validator checks every number on the rendered slides against those files and reports `unsupported-number`).
3. Every citation key exists in deck.json `references` (`data-ref="key"` elements and `[n]` markers are checked; `[n]` must be between 1 and the number of references).
4. No two consecutive slides use the same composition.
5. The slide count fits the duration table above.

## 10. Facts, interpretation and recommendation

Keep the three visibly distinct; audiences and examiners punish blurring them.

| Kind | Form on the slide | Requirement |
|---|---|---|
| Fact (measured or cited) | Number or statement with a `data-pcv-source` note or a `data-ref` citation | Traceable to a committed file or a reference; reported as measured, including unfavourable results |
| Interpretation | Hedged by evidence strength: "suggests", "is consistent with", "we attribute this to" | Must follow from facts on the same or an earlier slide; name the alternative explanation if one is plausible |
| Recommendation | Imperative or "we propose": an action | Must follow from the interpretation; state its condition or cost |

Practical rules:

- Put the fact in the chart and source note; put the interpretation in the title or a short "so what" line; put recommendations only on the conclusion or a dedicated slide.
- Never round a result up into a claim ("best", "significant") without the test that supports it. "Higher on this split, single seed" is a fact; "better" is an interpretation.
- Uncertainty travels with the number: mean ± sd over seeds, the number of seeds, the split.
- Do not use `data-pcv-nocheck` to hide a number the validator cannot trace. It exists for decorative numerals, slide numbers, dates and axis ticks; use it on nothing that states a result.
