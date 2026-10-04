# ML baseline findings, DiCo-NLI track 1 (English)

Recorded by `notebooks/assignment-1/03_ml_baseline_track1.ipynb`. Four systems, hyperparameters fixed before any run (scikit-learn defaults, `C = 1.0`, balanced class weights): logistic regression on 17 surface cues, on word 1-2-gram TF-IDF of `premise [SEP] hypothesis`, and on both; gradient-boosted trees on the cues. Stability from 5-fold cross-validation on train grouped by source pair (seed 13), every fold scored by the official scorer; then one fit on the full training set and one scoring on dev. Tables in `tables/`, figures in `figures/`, command and data commit in `config.json`.

## Scores

| System | CV weighted F1 (mean ± sd) | Dev weighted F1 | Dev SoftCons | Dev HardCons |
|---|---|---|---|---|
| cues + logreg | 0.575 ± 0.037 | 0.531 | 0.794 | 0.552 |
| tfidf + logreg | 0.429 ± 0.011 | 0.407 | 0.426 | 0.256 |
| both + logreg | 0.617 ± 0.021 | 0.596 | 0.747 | 0.570 |
| cues + gbdt | 0.572 ± 0.024 | 0.574 | 0.718 | 0.527 |

For reference, the trivial floor on the same dev set is weighted F1 0.129 (majority) and 0.246 (random); the organizers' pilot DeBERTa-v3-base, on a different data configuration, reported 0.75 / 0.84 / 0.79.

## What the ablation shows

1. **Surface cues carry direction.** The cue-only model gets forward and backward right at F1 0.66 each and confuses the two directions in only 8 of 380 directional dev instances, 4 each way (figure f2 shows the combined model, which confuses them 14 times; the cue-only confusion matrix is in `scores/cues+logreg/scores.json`). Corrected on 2026-10-04: an earlier version of this note gave the combined model's 14 for the cue-only model. The weights (figure f3) say how: containment of the hypothesis in the premise pushes towards FORWARD (+1.0) and away from BACKWARD (−1.4), the mirror cue does the reverse, and the character-length difference adds ±0.5. Equivalence has no strong positive cue; it is the residual class.
2. **Symmetric cues make a consistent model.** Every cue is either unchanged under reversal (overlap, shared tokens) or flips sign exactly (length difference, the two containments), so the cue model's decisions on a pair and its reverse are compatible by construction most of the time: SoftCons 0.79, the highest of the four systems, and 220 of 277 dev pairs consistent. But 67 of those 220 pairs are consistent and wrong in both directions, which is why HardCons stays at 0.55. Consistency and correctness are different properties, and this baseline separates them cleanly.
3. **A bag of n-grams is direction-blind and inconsistent.** TF-IDF alone reaches F1 0.41 and SoftCons 0.43: the same unigrams appear in both orders, and only the bigrams that cross the separator see the order at all. It matches the cue model on EQUIVALENCE (0.46 against 0.39), where lexical identity helps, and loses everywhere else.
4. **Adding TF-IDF to the cues buys F1 and costs consistency.** The combined model has the best cross-validated F1 (0.617 ± 0.021, dev 0.596) and the best HardCons (0.570), but its SoftCons drops from 0.79 to 0.75. Gradient boosting on the cues shows the same trade: dev F1 up to 0.574, SoftCons down to 0.72. The two more expressive models find asymmetric patterns that raise accuracy on single instances and break compatibility across the pair.
5. **The hard boundary is equivalence.** In the combined model's confusion matrix, 55 of 174 equivalences are predicted as one of the entailments and 46 as negatives, while 44 entailments are predicted as equivalences; F1 for EQUIVALENCE is 0.45 and for NEGATIVE_OTHER 0.41 against 0.71 to 0.72 for the two directions. This is the EDA's prediction: the cues say whether one phrase adds material to the other, not whether the addition narrows the meaning or paraphrases it.
6. **Cross-validation and dev rank the systems the same way.** Every dev score is at or below its cross-validated mean: within one standard deviation for the trees (0.1) and the combined model (1.0), 1.2 below for the cue-only model and 2.0 below for TF-IDF alone. The ranking is the same on both, and nothing was selected on dev. Corrected on 2026-10-04: an earlier version said three systems were within one standard deviation, which held before the TF-IDF separator fix and not after it.

## What this sets up for the encoder baseline

The fine-tuned encoder has to clear weighted F1 0.60 and HardCons 0.57 to add anything beyond surface cues, and the question that matters for the research question is whether it does so while keeping SoftCons at or above 0.79. If its consistency falls with its accuracy, as it did here for the two more expressive models, the trade-off is a property of learning from single ordered instances rather than of the model family, and a consistency-aware method has a target.

Caveats: one seed for the cross-validation split and the models (logistic regression is deterministic given the data; the trees and the split depend on seed 13); `C` and the gradient-boosting settings were fixed rather than tuned; the cue set is the EDA's, chosen before any model was fitted.
