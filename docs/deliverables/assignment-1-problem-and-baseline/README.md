# Assignment 1: Problem formulation, literature and baseline

Due Friday 2 October 2026, 11:59 PM.

Topic: SemEval-2027 Task 2, DiCo-NLI, English track. The organizers' pilot DeBERTa-v3-base numbers (weighted F1 0.75, SoftCons 0.84, HardCons 0.79) are a reference point, not a reproduction target: they were measured on the PhrasIS positives track after a 150-trial hyperparameter search, and SemEval track 1 adds NEGATIVE_OTHER on a different split. The dev set is the course test set because the official test set is released only in January 2027; model selection uses a grouped slice of train.

The material for the report is in `a1-notes.md` in this folder; the report itself is written in Overleaf once the professor confirms the template.

Items (from the course's generic requirements; they flex with the topic, and any item the topic makes inapplicable is noted here with the reason):

- [x] Task and data understanding: `notebooks/assignment-1/02_eda_track1.ipynb`, `experiments/2026-09-29-eda-track1/findings.md`, `datasets/dico-nli.json`
- [x] Selected literature: `docs/research/`, eleven verified notes and the reading log
- [x] Research question or hypothesis: section 3 of `a1-notes.md`, recorded in `.claude/reference/research-decisions.md`
- [x] Appropriate baselines: trivial (`experiments/2026-09-29-trivial-baselines-track1/`), ML ablation (`experiments/2026-09-29-ml-baseline-track1/`), DeBERTa-v3-base over three seeds (`experiments/2026-09-29-deberta-base-track1/`)
- [x] Initial results: section 5 of `a1-notes.md`, every number from the run folders above
- [ ] Report in Overleaf: pending the professor's template

Every number reported here traces to a folder under `experiments/` with its seed, data version, config, and command.
