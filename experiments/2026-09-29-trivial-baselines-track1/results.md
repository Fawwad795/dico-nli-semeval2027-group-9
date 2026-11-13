# Trivial baselines, track 1 dev

| System | Weighted F1 | SoftCons | HardCons |
|---|---|---|---|
| majority | 0.129 | 0.000 | 0.000 |
| random (seed 13) | 0.246 | 0.184 | 0.054 |
| always EQUIVALENCE | 0.110 | 1.000 | 0.314 |
| always NEGATIVE_OTHER | 0.044 | 0.000 | 0.000 |

Scores are the official scorer's output; a system's full report is under `scores/<system>/`, and a summary row (a mean over seeds) points to its table instead. Seed, data commit and command: `config.json`.
