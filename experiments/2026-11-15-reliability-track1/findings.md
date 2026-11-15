# Reliability analysis findings, DiCo-NLI track 1

The analysis compares fixed Assignment 1 predictions on the 660-instance English
development split. The paired bootstrap uses 10,000 source-pair resamples with seed 13;
McNemar's test is exact and two-sided on per-instance correctness. The run trained no
model. Tables and the reproducibility record are in this folder.

## Observations

1. DeBERTa seed 13 is clearly separated from both+logreg. Its weighted-F1 difference is
   0.228 with a 95% percentile interval of [0.175, 0.282]. The intervals for macro F1,
   SoftCons, and HardCons also exclude zero. It gets 189 instances right that both+logreg
   misses, against 37 in the other direction (exact McNemar $p < 10^{-25}$).
2. Seed variation is large enough to affect some conclusions. Seed 13 exceeds seed 1234
   by 0.029 weighted F1, with interval [0.002, 0.057], and by 0.031 macro F1, with interval
   [0.002, 0.061]. The exact correctness comparison gives $p=0.041$. The corresponding
   SoftCons interval [-0.026, 0.055] and HardCons interval [-0.014, 0.064] include zero.
   One seed can therefore look better on classification without establishing a consistency
   improvement.
3. Aggregate performance hides a weak length subgroup. DeBERTa seed 13 scores 0.765
   weighted F1 on long pairs (more than seven total words), compared with 0.833 on medium
   pairs and 0.843 on short pairs. The same ordering appears for the other two DeBERTa
   seeds. Long pairs contain 139 instances, so this is more stable than the ten-instance
   misleading-cue slice, but it remains descriptive rather than a separate significance test.
4. Phrase overlap is associated with a large performance difference. DeBERTa seed 13
   scores 0.970 weighted F1 when both dev phrases occur in train, 0.903 when one occurs,
   and 0.757 when neither occurs. The split contains 67, 206, and 387 instances in those
   groups. This pattern is evidence of distribution overlap, not evidence that memorization
   caused any individual prediction.
5. The length cue fails exactly where expected. Both logistic-regression systems score zero
   weighted F1 on the ten misleading instances, while every DeBERTa seed scores 0.800.
   Because this subgroup has only ten instances, its magnitude should not be generalized.

## Reporting rule for the proposed method

There is no fixed score difference that is automatically real. We may call the proposed
method different from a comparison system only when the source-pair bootstrap interval for
that metric excludes zero. For item accuracy, we also report the exact McNemar test. The
seed-13 versus seed-1234 result shows why a single favorable seed is insufficient: a 0.029
weighted-F1 gap can pass the paired tests on this fixed dev set while still being a difference
between training seeds. The proposed method will therefore be reported as the mean and
standard deviation over seeds 13, 42, and 1234; its paired comparison will use predictions
matched by seed, and consistency gains will be claimed only for metrics whose intervals
exclude zero.

## Interpretation for Assignment 2

The DeBERTa-to-both+logreg gap is much larger than the observed encoder seed gap on every
metric, so the Assignment 1 encoder remains a defensible strong baseline. Evaluation of the
proposed decoder method must show the complete weighted-F1, SoftCons, and HardCons profile.
SoftCons alone cannot establish improvement because symmetrized decoding raises it by design,
and constant EQUIVALENCE prediction scores 1.0 on it.

Correction, 15 November 2026: this paragraph first said that symmetrized decoding makes
SoftCons 1.0 by construction. The preliminary decoder run measured 0.906 and 0.986. The
official scorer counts a NEGATIVE_OTHER answer on a reversible pair as incompatible, so the
SoftCons of symmetrized predictions is one minus the share of reversible pairs answered
NEGATIVE_OTHER (`experiments/2026-11-14-decoder-preliminary-track1/findings.md`).

