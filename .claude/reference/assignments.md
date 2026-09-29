# Assignments

> The three graded deliverables, their due dates, and where each lands. Item lists are the course's generic requirements; they flex with the topic and are confirmed against the course brief once the topic is chosen.

| | Due | Branch area | Lands in |
|---|---|---|---|
| A1 Problem formulation, literature and baseline | Friday 2 October 2026, 11:59 PM | `a1/` | `docs/deliverables/a1-problem-and-baseline/` |
| A2 Proposed approach and experimental design | Friday 13 November 2026, 11:59 PM | `a2/` | `docs/deliverables/a2-approach-and-design/` |
| A3 Experiments, analysis and research paper | Friday 4 December 2026, 11:59 PM | `a3/` | `docs/deliverables/a3-experiments-and-paper/` |

## A1: problem formulation, literature and baseline

- Task and data understanding
- Selected literature
- Research question or hypothesis
- Appropriate baselines
- Initial results

## A2: proposed approach and experimental design

- Proposed method
- Justification
- Comparison systems
- Evaluation measures
- Experimental protocol
- Initial implementation

## A3: experiments, analysis and research paper

- Completed experiments
- Ablations and error analysis
- Comparison with baselines and relevant work
- Findings
- Paper-style report
- Presentation or demo

## Professor's working notes (recorded 2026-09-29)

Given in class as the expected way of working on the assignment, whichever SemEval or ICASSP task is chosen:

1. **Black-box understanding first, then white-box.** Start by treating models as black boxes (what goes in, what comes out, where they fail), then open them up.
2. **EDA to understand the data and its patterns**, covering statistical, readability, lexical, semantic, and linguistic properties. For DiCo-NLI: label balance per track, phrase lengths, readability scores, vocabulary overlap between premise and hypothesis, embedding similarity by label, and part-of-speech or syntactic patterns per label.
3. **Baselines of two kinds: ML and DL.** A classical machine-learning baseline (features plus a linear model or tree) and a deep-learning baseline (the fine-tuned encoder), both reported.
4. **Plots and graphs saved as PDF**, not raster images, so they drop into the paper cleanly.
5. **Report written in Overleaf and sent by email** to the professor.

## Standing rules

- Every number in a deliverable traces to a run under `experiments/` with its seed, data version, config, and command.
- Each deliverable folder's README lists the items above; tick them off as they land and note any item the topic makes inapplicable, with the reason.
- Material AI assistance on a deliverable gets a row in `docs/governance/ai-usage-disclosure.md`.
