# Encoder baseline findings, DiCo-NLI track 1 (English)

DeBERTa-v3-base fine-tuned with our seeded loop (`dico_nli.baselines.encoder`), three seeds, one T4 each on Modal (`scripts/modal/train_encoder.py`), scored on dev by `notebooks/assignment-1/04_dl_baseline_track1.ipynb`. Hyperparameters were fixed before the first launch (AdamW, learning rate 2e-5, batch 16, 5 epochs, 6 % warm-up, weight decay 0.01, max 32 tokens); the epoch was chosen on a 20 % slice of train split by source pair with the run's seed, and dev was scored once per seed. Tables in `tables/`, figures in `figures/`, the per-seed training records with the code identity (repository commit, dirty flag, SHA-256 of the shipped `dico_nli` source) in `runs/`.

The run was executed twice on T4s, before and after the code identity was added to the launcher, and produced byte-identical dev predictions for all three seeds. Given the seed and the GPU type, the pipeline is deterministic.

## Scores on track 1 dev

| Seed | Best epoch | Held-out weighted F1 | Weighted F1 | SoftCons | HardCons |
|---|---|---|---|---|---|
| 13 | 5 | 0.819 | 0.824 | 0.881 | 0.823 |
| 42 | 4 | 0.800 | 0.801 | 0.884 | 0.809 |
| 1234 | 5 | 0.775 | 0.795 | 0.866 | 0.798 |
| mean ± sd | | | 0.807 ± 0.015 | 0.877 ± 0.010 | 0.810 ± 0.013 |

Per-label F1, mean over seeds: EQUIVALENCE 0.78, FORWARD_ENTAILMENT 0.86, BACKWARD_ENTAILMENT 0.87, NEGATIVE_OTHER 0.63. Of the 277 reversible dev pairs, 240 to 245 were predicted compatibly and 221 to 228 fully correctly; 16 to 21 pairs per seed were consistent and wrong in both directions, against 67 for the cue-only model.

## What the run shows

1. **The encoder clears every bar the ML baselines set, on all three scores.** Weighted F1 0.81 against 0.60 for the best ML system, HardCons 0.81 against 0.57, and SoftCons 0.88 against 0.79 for the cue-only model. H2 holds: the gain concentrates where the cues were blind, EQUIVALENCE F1 from 0.45 to 0.78 and HardCons up by 0.24. H3 does not hold for the encoder: it gained accuracy and consistency together, so the trade-off seen inside the ML family belongs to those feature sets, not to learning from ordered instances in general. Reported as measured.
2. **Direction is not where the encoder adds value.** Seed 13 confuses forward with backward in 3 of 380 directional instances, about what the cue model managed. The improvement is in telling entailment from equivalence (26 entailments predicted as equivalences, 13 the other way, against 44 and 55 for the combined ML model) and in the negatives.
3. **NEGATIVE_OTHER is now the hardest class.** F1 0.63; seed 13 calls 34 of 106 negatives related (13 equivalence, 11 forward, 10 backward) and 41 related pairs negative. The EDA's description of negatives as a substituted word inside an identical structure ("off Mexico" / "on Mexico") fits: lexical and structural overlap point towards relatedness, and the model follows it.
4. **The encoder's consistency is mostly correctness.** The cue model was consistent by construction and wrong on 67 pairs; the encoder is consistent on 244 pairs and wrong on 16 of them. Its SoftCons comes from getting both directions right, not from symmetric features.
5. **The held-out slice is a usable proxy for dev.** Held-out weighted F1 at the chosen epoch (0.78 to 0.82) sits within two points of dev F1 (0.80 to 0.82) for every seed, and the ranking of seeds is the same on both. Two seeds were still improving at epoch 5; a longer schedule was not tried, by protocol.
6. **Against the pilot, a reference point and not a comparison.** 0.807 / 0.877 / 0.810 here against the pilot's 0.75 / 0.84 / 0.79: their positives track has no negatives (our hardest class), their split differs, their hyperparameters came from 150 Optuna trials and ours from a fixed recipe, and 22 % of our dev phrases occur in train. Nothing here claims to beat the pilot.
7. **Compute.** About 140 s of training per seed on a T4 (around five minutes each including the image and model load), roughly $0.15 for the three seeds. A float32 CPU run on the project laptop measured 5.1 s per step, about 65 minutes of training per seed, so a local run is a viable overnight fallback rather than the default.

## What this means for the research question and Assignment 2

The gap between the cue-only model and the encoder is the room a meaning-aware model has over surface asymmetry: about 0.28 weighted F1 and 0.26 HardCons, most of it on the equivalence boundary and the negatives. The encoder keeps direction as cleanly as the cues do and adds the semantics. Assignment 2 turns to decoder LLMs, where the pilot found consistency far below the encoders, and asks whether pair-swap augmentation, a consistency loss over the pair and its reverse, or symmetric prompting closes that gap without giving up the accuracy the encoder shows is available.

Caveats: no hyperparameter search; the 32-token limit is not reached by typical pairs (three words a side) but was not audited for the longest ones; one GPU type, on which the run is deterministic; one track.
