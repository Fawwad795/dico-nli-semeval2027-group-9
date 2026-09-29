# Deployment

> Deploy target and deliverable artifacts.

There is no deploy target. The project ships three assignment submissions and the repository itself.

| Deliverable | Form | Lands in |
|---|---|---|
| A1 problem formulation, literature, baseline | Document plus initial results | `docs/deliverables/a1-problem-and-baseline/` |
| A2 proposed approach and experimental design | Document plus initial implementation | `docs/deliverables/a2-approach-and-design/` and `src/dico_nli/` |
| A3 experiments, analysis, paper | Paper-style report, presentation or demo | `docs/deliverables/a3-experiments-and-paper/` and `docs/paper/` |

Dates and item lists: `assignments.md`.

Run outputs under `artifacts/` are gitignored. A result a deliverable cites is promoted into `experiments/<run-family>/` with its config and seed, or into `docs/` as a figure or table, before the deliverable is written.
