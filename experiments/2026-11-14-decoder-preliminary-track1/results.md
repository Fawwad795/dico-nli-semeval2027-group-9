# Decoder method, preliminary verification, track 1 dev

| System | Weighted F1 | SoftCons | HardCons |
|---|---|---|---|
| qwen2.5-0.5b-zero-shot, single | 0.112 | 0.957 | 0.310 |
| qwen2.5-0.5b-zero-shot, symmetrized | 0.110 | 1.000 | 0.314 |

Scores are the official scorer's output; a system's full report is under `scores/<system>/`, and a summary row (a mean over seeds) points to its table instead. Seed, data commit and command: `config.json`.
