# ML baselines, track 1 dev

| System | Weighted F1 | SoftCons | HardCons |
|---|---|---|---|
| cues+logreg | 0.531 | 0.794 | 0.552 |
| tfidf+logreg | 0.407 | 0.426 | 0.256 |
| both+logreg | 0.596 | 0.747 | 0.570 |
| cues+gbdt | 0.574 | 0.718 | 0.527 |

Scores are the official scorer's output; each system's full report is under `scores/`. Seed, data commit and command: `config.json`.
