# Assignments

> The three graded deliverables, their due dates, and where each lands. Item lists are the course's generic requirements; they flex with the topic and are confirmed against the course brief once the topic is chosen.

| | Due | Branch area | Lands in |
|---|---|---|---|
| Assignment 1: problem formulation, literature and baseline | Sunday 4 October 2026, 11:59 PM (extended from 2 October) | `assignment-1/` | `docs/deliverables/assignment-1-problem-and-baseline/` |
| Assignment 2: proposed approach and experimental design | Friday 13 November 2026, 11:59 PM | `assignment-2/` | `docs/deliverables/assignment-2-approach-and-design/` |
| Assignment 3: experiments, analysis and research paper | Friday 4 December 2026, 11:59 PM | `assignment-3/` | `docs/deliverables/assignment-3-experiments-and-paper/` |

Notebooks that produce an assignment's runs live under `notebooks/assignment-<n>/`.

## Assignment 1: problem formulation, literature and baseline

The professor's brief (received 2026-10-02) is `docs/deliverables/assignment-1-problem-and-baseline/Assignment_1_Shared_Task_Project_Guidelines.pdf` and replaces the generic list. What it requires beyond the generic items:

- Progression: task understanding, data understanding, selective EDA, classical ML baseline, pretrained baseline, evaluation, error analysis.
- Task understanding black-box first (input, output, label space, metric, formulation), then white-box (cues, confounds, shortcuts, artifacts, imbalance, source effects).
- Minimum data checks: split sizes, label distribution, missing, empty, duplicated and unusually short or long samples, length statistics, metadata distributions.
- EDA: 4 to 8 feature groups, each answering a stated question, each interpreted as observation, interpretation, modeling implication. Never bare numbers.
- One single PDF of the selected EDA figures, without traditional captions: each plot carries a concise title, axis labels with units, and a legend where needed.
- Classical baseline on engineered features plus TF-IDF with logistic regression or linear SVM, with feature importance tied back to the EDA. Pretrained baseline only after it, stating frozen, feature extraction, fine-tuning or prompting.
- Metrics understood mathematically, why the task uses them, what they reward or penalise, the averaging scheme, and the effect of imbalance.
- Literature: the task description, the organizer paper and 3 to 5 related papers, read for formulation, data, features, models, evaluation and limitations.
- Report in LaTeX on Overleaf with BibTeX, maths and cross-references, in eleven sections: introduction and task definition, related work, dataset, EDA, feature engineering, baseline models, evaluation setup, results, error analysis, discussion, next steps.

## Assignment 2: proposed approach and experimental design

- Proposed method
- Justification
- Comparison systems
- Evaluation measures
- Experimental protocol
- Initial implementation

## Assignment 3: experiments, analysis and research paper

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
