# Notebooks

One notebook per experiment, grouped by assignment (`assignment-1/`, `assignment-2/`, `assignment-3/`). They are the runner layer: a teammate reads them cell by cell to see what a run does, and running one headlessly reproduces its folder under `experiments/`.

```
PYTHONIOENCODING=utf-8 uv run jupyter execute notebooks/assignment-1/02_eda_track1.ipynb
```

Rules:

- Every computation a reported number depends on is a tested function in `src/dico_nli/`; a notebook calls those functions, displays the tables, draws the figures through `dico_nli.plotting`, and writes the run record. Logic that exists only in a notebook cell is not a result.
- Each notebook sets its parameters in the first code cell (`TRACK`, `RUN_DATE`, `OVERWRITE`, and `SEED` wherever anything is random) and records the exact headless command, including the `PYTHONIOENCODING=utf-8` prefix, in `config.json`.
- Strip outputs before committing (VS Code: "Clear All Outputs"; `jupyter execute` never saves them). Results and figures live in `experiments/`, not in the notebook file.
- Anything that has to be a plain script stays under `scripts/`: the Modal launchers (`modal run` needs a module) and the README panel generator.

| Notebook | Writes |
|---|---|
| `assignment-1/01_trivial_baselines.ipynb` | `experiments/2026-09-29-trivial-baselines-track1/` |
| `assignment-1/02_eda_track1.ipynb` | `experiments/2026-09-29-eda-track1/` and per-instance frames under `artifacts/eda-track1/` |
| `assignment-1/03_ml_baseline_track1.ipynb` | `experiments/2026-09-29-ml-baseline-track1/` and the cross-validation folds under `artifacts/ml-baseline-track1/` |
| `assignment-1/04_dl_baseline_track1.ipynb` | `experiments/2026-09-29-deberta-base-track1/`, from the Modal runs fetched under `artifacts/dl-baseline-track1/` (launcher: `scripts/modal/train_encoder.py`) |
