# Findings: preliminary verification of the decoder method, track 1

These are pipeline checks. Every trained system is one seed (13), so no number here is a performance claim, and no comparison with the encoder baseline is a claim of superiority. All scores are the official scorer's output on the 660 dev instances (277 reversible pairs). Tables are in `tables/`, settings in `config.json` and `runs/`.

## What works

- **The whole chain runs.** Data loads (2,443 instances to fit on, 599 to validate on, 660 dev, no pair on both sides of the split), prompts are built (longest 132 tokens, limit 160), the 1.5B model trains with LoRA on an NVIDIA L4, predictions come out in the official format, and the official scorer accepts all eight prediction files (`tables/dev_scores.csv`).
- **Training is cheap.** One epoch takes about 135 seconds; a three-epoch run takes 404 s (lambda 0) and 411 s (lambda 1). Peak GPU memory is 16.1 GB with bfloat16 activations, float32 weights and micro-batches of 8 pairs. The adapters are 4,358,144 trainable parameters out of 1,548,072,448, 0.28 % (`tables/run_costs.csv`).
- **Runs repeat.** The one-epoch timing run and the lambda 1 run, launched separately with the same seed, report the same first loss, 4.3513.
- **Scores for the same input are identical.** The reversed order of an instance and the forward order of its twin are the same text; their saved probabilities differ by 0.0.
- **The trained model makes meaningful predictions.** Predicted label counts follow the gold counts (`tables/predicted_label_counts.csv`), and the ten sampled examples show direction being read correctly, for example `in the field` / `in a lush green field` as BACKWARD (`tables/example_predictions.csv`).

## Scores (one seed, checks only)

| System | Decoding | Weighted F1 | SoftCons | HardCons |
|---|---|---|---|---|
| Qwen2.5-0.5B, zero-shot (CPU) | single | 0.112 | 0.957 | 0.310 |
| | symmetrized | 0.110 | 1.000 | 0.314 |
| Qwen2.5-1.5B, zero-shot | single | 0.267 | 0.144 | 0.087 |
| | symmetrized | 0.359 | 0.949 | 0.383 |
| Qwen2.5-1.5B, LoRA, lambda 0 | single | 0.823 | 0.801 | 0.776 |
| | symmetrized | 0.836 | 0.906 | 0.859 |
| Qwen2.5-1.5B, LoRA, lambda 1 | single | 0.792 | 0.845 | 0.823 |
| | symmetrized | 0.809 | 0.986 | 0.910 |
| DeBERTa-v3-base, mean of 3 seeds (Assignment 1) | single | 0.807 | 0.877 | 0.810 |

## What the checks showed

1. **Zero-shot, the two model sizes fail in opposite ways.** The 0.5B model answers EQUIVALENCE for 644 of 660 instances, so it scores like the always-EQUIVALENCE baseline: self-consistent and wrong. The 1.5B model answers FORWARD for 426 of 660 instances whatever the order, so it contradicts itself on 237 of 277 pairs (SoftCons 0.144). Neither reads direction without training.
2. **Plain LoRA reaches the encoder's weighted F1 range and stays less consistent.** Lambda 0, single pass: 0.823 against the encoder's 0.807 with a standard deviation of 0.015 over seeds, and SoftCons 0.801 against 0.877. That is the pattern hypothesis H5 predicted. It is one seed.
3. **The consistency loss raised single-pass SoftCons and lowered weighted F1 on this seed.** Lambda 1 against lambda 0: SoftCons 0.845 against 0.801, weighted F1 0.792 against 0.823. The F1 loss sits in NEGATIVE_OTHER (F1 0.484 against 0.632): the lambda 1 model answers NEGATIVE_OTHER 55 times where gold has 106. The two runs also kept different epochs (lambda 1 its first, lambda 0 its third), on validation scores that differ by about 0.02 or less between epochs, so this comparison is confounded and needs several seeds.
4. **Symmetrized decoding raised weighted F1 and HardCons in all three 1.5B systems.** Lambda 0: +0.013 weighted F1, +0.083 HardCons. Lambda 1: +0.017 and +0.087. Zero-shot: +0.092 and +0.296. Apart from one exact tie in the zero-shot system, it left no pair with exactly one direction right (`tables/pair_outcomes.csv`).

## What failed: a claim in the plan was wrong

The plan said symmetrized decoding makes SoftCons 1.0 by construction. It does not. The trained systems score 0.906 and 0.986.

The two predictions of a pair do always agree under our rule, where NEGATIVE_OTHER reverses to itself. The official scorer defines no reverse for NEGATIVE_OTHER and counts that answer on a reversible pair as incompatible. Every pair it counts as inconsistent under symmetrized decoding is explained (`tables/symmetrized_inconsistent_pairs.csv`): 26 pairs answered NEGATIVE_OTHER in both orders for lambda 0, 4 for lambda 1, 13 for zero-shot plus one exact tie between FORWARD and BACKWARD. No pair is unexplained.

The official SoftCons of symmetrized predictions is therefore one minus the share of reversible pairs answered NEGATIVE_OTHER. The unit tests had passed because the fixture model never gave that answer on a reversible pair. The case is now pinned in `tests/regression/test_known_bugs.py`, and the plan, the report and the code comments are corrected.

## To fix or settle before the full runs

- Report, next to SoftCons, how many reversible pairs each system answers NEGATIVE_OTHER. A system cannot know at test time which pairs are reversible (the identifier that says so is never an input), so this cannot be patched at decoding time without leaking.
- Run the three seeds before reading anything into lambda. The lambda 0 against lambda 1 difference above is within what epoch selection alone could produce.
- Check whether the consistency loss suppresses NEGATIVE_OTHER in general or only on this seed. It is the smallest class and the one where our reversal assumption applies.
- The launcher reported peak GPU memory per container, and the three jobs shared one container, so the lambda 1 figure includes the earlier jobs. The launcher now resets the counter at the start of each job.
- The settings for every later run are fixed by this run: NVIDIA L4, bfloat16 activations with float32 weights, micro-batches of 8 pairs.

Promoted on 24 November 2026: `probabilities/<system>__forward.csv` and `__reverse.csv` for the 1.5B zero-shot run and both seed-13 LoRA runs are byte-identical copies of the gitignored `artifacts/decoder-preliminary-track1/2026-11-14-decoder-preliminary-track1/<system>/probabilities_forward.csv` and `probabilities_reverse.csv`. Single-pass and symmetrized predictions and official scores recomputed from them match `predictions/` and `scores/` exactly, so no number changed. The 0.5B zero-shot run has no saved probabilities in `artifacts/`, so none are promoted for it.
