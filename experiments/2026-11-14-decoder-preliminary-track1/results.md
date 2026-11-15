# Decoder method, preliminary verification, track 1 dev

| System | Weighted F1 | SoftCons | HardCons |
|---|---|---|---|
| qwen2.5-0.5b-zero-shot, single | 0.112 | 0.957 | 0.310 |
| qwen2.5-0.5b-zero-shot, symmetrized | 0.110 | 1.000 | 0.314 |
| qwen2.5-1.5b-zero-shot, single | 0.267 | 0.144 | 0.087 |
| qwen2.5-1.5b-zero-shot, symmetrized | 0.359 | 0.949 | 0.383 |
| qwen2.5-1.5b-lora-lambda0-seed13, single | 0.823 | 0.801 | 0.776 |
| qwen2.5-1.5b-lora-lambda0-seed13, symmetrized | 0.836 | 0.906 | 0.859 |
| qwen2.5-1.5b-lora-lambda1-seed13, single | 0.792 | 0.845 | 0.823 |
| qwen2.5-1.5b-lora-lambda1-seed13, symmetrized | 0.809 | 0.986 | 0.910 |

Scores are the official scorer's output; a system's full report is under `scores/<system>/`, and a summary row (a mean over seeds) points to its table instead. Seed, data commit and command: `config.json`.
