# Deployment

> Deploy target and deliverable artifacts.

There is no deploy target. The project ships three assignment submissions and the repository itself.

| Deliverable | Form | Lands in |
|---|---|---|
| Assignment 1, problem formulation, literature, baseline | Document plus initial results | `docs/deliverables/assignment-1-problem-and-baseline/` |
| Assignment 2, proposed approach and experimental design | Document plus initial implementation | `docs/deliverables/assignment-2-approach-and-design/` and `src/dico_nli/` |
| Assignment 3, experiments, analysis, paper | Paper-style report, presentation or demo | `docs/deliverables/assignment-3-experiments-and-paper/` and `docs/paper/` |

Dates and item lists: `assignments.md`.

Run outputs under `artifacts/` are gitignored. A result a deliverable cites is promoted into `experiments/<run-family>/` with its config and seed, or into `docs/` as a figure or table, before the deliverable is written.
