# Findings: final decoder runs, track 1

This file records what ran and what was measured. Means over seeds, intervals, tests and their interpretation are in the results tables built from this folder and in the paper.

## What ran

- **Two waves on Modal, 32 jobs, all finished at the first attempt.** No job failed, none was preempted and none was rerun. Wave A (app `ap-eOvzhee5YGcEo56Mn1oenz`, 26 November 2026) ran the zero-shot model and LoRA at lambda 0, 0.25, 0.5, 1 and 2 with seeds 13, 42 and 1234. Wave B (app `ap-lBQKpGhqBd5dga2exsuOeR`, 26 November 2026) ran the three ablation rows at the chosen lambda: without reversed negatives (lambda 0 and 2), label words (zero-shot and lambda 2) and Qwen2.5-0.5B (lambda 0 and 2). The job lists are `wave_a_jobs.json` and `wave_b_jobs.json`.
- **One version of the method code.** Every `runs/*.json` records the same `source_sha256` (`2176a5a4…`) and `repo_dirty: false`. The repository commits differ between the waves (`21a261e` and `324debe`) because the second adds the lambda choice and the wave B job list; `src/dico_nli/` is the same in both.
- **Dates.** The folder keeps the planned date in its name. Wave A was planned for 25 November and ran on 26 November.
- **Settings.** One NVIDIA L4 per job, bfloat16 activations with float32 weights, micro-batches of 8 pairs, three epochs, the other settings as in `config.json`. Each trained job drew its own grouped 20 % validation split with its seed (599, 615 and 603 instances for seeds 13, 42 and 1234); zero-shot jobs were scored on seed 13's split.

## Order of the lambda choice

Lambda was chosen from the validation folders alone, by `notebooks/assignment-3/01_lambda_selection.ipynb`, and committed and pushed as `324debe` on 26 November 2026 at 10:02 (+05:00). That notebook recorded that no dev folder had been fetched when it ran. The dev folders of wave A were fetched after the push. The chosen value is lambda 2, the upper edge of the grid; the four validation means lie between 0.787 and 0.795 (`lambda_selection.json`, `tables/validation_grid.csv`).

## Checks that passed

- **Files.** Each wave's validation and dev fetch returned 64 of 64 expected files.
- **Validation score.** For all 30 trained jobs, the weighted F1 recomputed from the saved validation probabilities equals the value logged at the kept epoch (difference 0.0).
- **Predictions.** For all 32 jobs, the single-pass and symmetrized dev predictions recomputed from the saved probabilities equal the prediction files written in the container.
- **Repeat check** (`tables/repeat_check.csv`). The zero-shot model and seed 13 at lambda 0 and lambda 1 were rerun with the settings of the preliminary run of 14 November. In all three, the dev probabilities in both orders are identical to the preliminary run's (largest difference 0.0), every label agrees, and the kept epochs are the same (3 for lambda 0, 1 for lambda 1). Between the two runs the method code gained the two ablation options, so the default path gives the same result on the same GPU type, bit for bit as saved.

## What is in the folder

- `predictions/` and `scores/`: 64 prediction files (32 systems, single pass and symmetrized) in the official format, each with the official scorer's output.
- `probabilities/`: dev probabilities in both orders. `validation_probabilities/` and `validation_reference/`: the same for each job's validation split, with one reference per seed.
- `runs/`: each job's `run.json`. `logs/`: the two wave logs with timestamps (45 epoch lines each).
- `tables/dev_scores_per_seed.csv`: one row per system and decoding. `tables/training_history.csv`: one row per epoch. `tables/run_costs.csv`: measured seconds, GPU, peak memory and parameter counts per job. `tables/wave_costs.csv`: billed dollars per wave.

## Measured costs

- **Time.** A three-epoch run of the 1.5B model took 410 to 509 s of training; the 0.5B model took 319 to 352 s. Scoring a validation split in both orders took 4.6 to 41.1 s and scoring dev in both orders 5.0 to 14.1 s.
- **Memory.** Peak GPU memory was 16.0 to 16.3 GB for the trained 1.5B jobs, 8.7 GB for the 1.5B zero-shot jobs and 5.8 to 6.0 GB for the 0.5B jobs.
- **Money.** Modal's billing report of 26 November shows $2.01 for wave A and $1.86 for wave B, of which $1.83 and $1.68 are L4 time (`billing_report.json`). The two-job launcher test before wave A cost $0.06 and produced no reported result.

## Caveats on the record

- `config.json` was written by the notebook while its own outputs were uncommitted, so its top-level `repo_dirty` is true. The identity of the runs is under `waves` and in each `runs/*.json`, where it is false.
- The selection rule is applied in the selection notebook, not in a tested function of `src/dico_nli/`. It was kept out of the package so that the source digest stayed the same for both waves.
- Lambda 2 is the edge of the grid. No larger value was run.
- One GPU type. The exact repeat is shown on the L4 only.
