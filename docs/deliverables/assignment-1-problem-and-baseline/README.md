# Assignment 1: Problem formulation, literature and baseline

Due Sunday 4 October 2026, 11:59 PM (extended from Friday 2 October).

Topic: SemEval-2027 Task 2, DiCo-NLI, English track. The organizers' pilot DeBERTa-v3-base numbers (weighted F1 0.75, SoftCons 0.84, HardCons 0.79) are a reference point, not a reproduction target: they were measured on the PhrasIS positives track after a 150-trial hyperparameter search, and SemEval track 1 adds NEGATIVE_OTHER on a different split. The dev set is the course test set because the official test set is released only in January 2027; model selection uses a grouped slice of train.

The professor's brief is `Assignment_1_Shared_Task_Project_Guidelines.pdf` in this folder. The material for the report is in `a1-notes.md`; the report itself is written in LaTeX on Overleaf once the professor confirms the template, with the brief's eleven sections: introduction and task definition, related work, dataset, exploratory data analysis, feature engineering, baseline models, evaluation setup, results, error analysis, discussion, next steps.

Submission checklist, from the brief:

- [ ] Clear black-box and white-box task understanding: content in `a1-notes.md` section 1; to be framed black-box first, then white-box, in the report
- [ ] Dataset statistics and quality checks: statistics in `experiments/2026-09-29-eda-track1/`; quality checks (duplicates, outliers, fragments, metadata) open, issue for Ahmad Imran
- [ ] Justified selection of task-relevant EDA features: five groups computed; the question each answers, and why lexical richness is left out, open, same issue
- [ ] Interpretation of each feature as observation, interpretation and modeling implication: open, same issue
- [ ] Single PDF containing the relevant EDA plots: open, same issue (six separate PDFs today; several lack axis labels)
- [x] At least one classical ML baseline on engineered features: `experiments/2026-09-29-ml-baseline-track1/`, with cue weights tied back to the EDA
- [x] At least one pretrained-model baseline: DeBERTa-v3-base, fine-tuned, three seeds, `experiments/2026-09-29-deberta-base-track1/`
- [ ] Correct understanding of the official metrics: definitions in words in `a1-notes.md`; formulas, averaging, imbalance and degenerate strategies open, issue for Aqib Raza
- [x] Initial literature review grounded in the task and baseline papers: `docs/research/`, eleven verified notes and the reading log
- [ ] LaTeX/Overleaf report with a reproducible experimental description: pending the template and the two open issues
- [ ] Error analysis (the brief's progression and report section 9): open, issue for Aqib Raza

Every number reported here traces to a folder under `experiments/` with its seed, data version, config, and command.
