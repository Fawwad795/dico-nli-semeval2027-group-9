# DeBERTa-v3-base, track 1 dev

| System | Weighted F1 | SoftCons | HardCons |
|---|---|---|---|
| deberta-v3-base, seed 13 | 0.824 | 0.881 | 0.823 |
| deberta-v3-base, seed 42 | 0.801 | 0.884 | 0.809 |
| deberta-v3-base, seed 1234 | 0.795 | 0.866 | 0.798 |
| deberta-v3-base, mean of 3 seeds | 0.807 | 0.877 | 0.810 |

Scores are the official scorer's output; a system's full report is under `scores/<system>/`, and a summary row (a mean over seeds) points to its table instead. Seed, data commit and command: `config.json`.
