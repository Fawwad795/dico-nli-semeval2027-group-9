# Assignment 1 notes: problem formulation, literature and baseline

Material for the Overleaf report, written once the professor confirms the template. Every number comes from a recorded run under `experiments/`; the folder is named next to each table.

## 1. Task and data understanding

**The task.** SemEval-2027 Task 2, DiCo-NLI, asks for one of four labels for an ordered pair of short phrases: EQUIVALENCE, FORWARD_ENTAILMENT (the first phrase entails the second), BACKWARD_ENTAILMENT (the second entails the first) or NEGATIVE_OTHER. Every reversible source pair appears twice, once in each order, and the official scorer reports three numbers: weighted F1 over all instances, SoftCons (the share of reversible pairs whose two predictions are compatible under the label-reversal operator, regardless of correctness) and HardCons (the share of reversible pairs where both predictions are correct). NEGATIVE_OTHER instances have no reversed twin and count only towards weighted F1. The task inherits its framing from the reversal curse (Berglund et al. 2024) and its data and metrics from the organizers' pilot study (Apaolaza et al. 2026), which defined soft and hard causal coherence on PhrasIS phrase pairs.

**The data.** Track 1 (English) train holds 3,042 instances from 1,760 source pairs: 1,282 reversible pairs contributing two instances each and 478 negatives contributing one. Dev holds 660 instances from 383 source pairs (277 reversible, 106 negatives). Labels are close to balanced in train (FORWARD 881, BACKWARD 881, EQUIVALENCE 802, NEGATIVE_OTHER 478) and dev mirrors the shares within half a point. Phrases are short: 3.0 words on average, at most 15. They come from PhrasIS (Lopez-Gazpio et al. 2024), itself built from the chunk alignments of interpretable STS (Agirre et al. 2016), so they are noun phrases, verb chains and prepositional phrases from image captions and news headlines. Source: organizers' repository at commit `588968e` (2026-09-08); checksums in `datasets/dico-nli.json`.

**Evaluation split.** The official test set is released on 10 January 2027, after the course ends. We use dev as the course test set and never select anything on it; model selection uses a slice of train split by source pair. Dev shares no source pair with train, but 7 unordered text pairs and 155 of its 712 distinct phrases (22 %) also occur in train, which we report rather than hide.

**Three cautions.** (1) The instance id leaks the label: every `__flipped` id belongs to a reversible pair, so no model input may include it. (2) The pilot's DeBERTa-v3-base numbers (weighted F1 0.75, SoftCons 0.84, HardCons 0.79) were measured on the PhrasIS positives track after a 150-trial hyperparameter search; SemEval track 1 adds NEGATIVE_OTHER and is a different split, so they are a reference point, not a reproduction target. (3) Direction correlates with surface form, which the EDA quantifies next.

**Exploratory analysis** (`experiments/2026-09-29-eda-track1/`, figures f1 to f6, `findings.md`). Five facets on train:

- *Statistical.* The premise is the longer phrase in 78 % of forward pairs and the hypothesis in 78 % of backward pairs; equivalences split 36 / 29 / 36 and negatives 24 / 49 / 27 (premise longer / same / hypothesis longer). Equal length is the strongest single marker of a negative.
- *Readability.* Syllables per word 1.53 to 1.60 and characters per word 4.5 to 4.9 across labels; Flesch medians 78 to 82 everywhere. The facet does not separate labels and documents that the data is uniformly short caption and headline language.
- *Lexical.* Directional pairs overlap most (mean Jaccard 0.41 against 0.24 for equivalences and 0.27 for negatives). Containment is directional: all hypothesis words occur in the premise in 45 % of forward pairs and 2 % of backward pairs, and the mirror holds. The last token is shared in 58 % of directional pairs: the head is kept and modifiers change.
- *Semantic.* MiniLM cosine similarity has median 0.76 for equivalences, 0.77 for both directions and 0.64 for negatives. Cosine is symmetric, so forward and backward pairs have identical distributions: a symmetric representation carries no information about direction.
- *Linguistic.* The head lemma is shared in 52 % of directional pairs against 30 % of equivalences; the POS pattern is identical in 31 % of negatives against 7 % of directional pairs (negatives are often a substituted word in the same structure); a preposition appears in 47 % to 61 % of pairs depending on label; adjectives are the added material (+0.33 on the premise side in forward pairs, the mirror in backward pairs).

## 2. Selected literature

Notes with verified citations are in `docs/research/`; the reading log lists them. Three strands:

- *Reversal and direction.* Berglund et al. 2024 show that decoder LLMs trained on "A is B" fail "B is A"; Lv et al. 2024 trace the cause to the causal training objective and mitigate it at training time (BICO). Yanaka et al. 2019 show that the direction of a monotonicity inference is learned and fragile, with downward inferences harder. Apaolaza et al. 2026 bring this to phrase-level NLI, define soft and hard coherence, and find encoders far ahead of decoders on both accuracy and coherence.
- *Consistency as a trainable property.* Minervini and Riedel 2018 and Li et al. 2019 turn logical constraints over groups of NLI examples (symmetry, transitivity) into regularisers; Elazar et al. 2021 define consistency as invariance under meaning-preserving change and measure it on ParaRel. Directional consistency is a constraint of the same form with a prescribed change rather than invariance.
- *Data and formalism.* PhrasIS (Lopez-Gazpio et al. 2024) and interpretable STS (Agirre et al. 2016) explain where the phrases come from; MacCartney and Manning 2009 supply the relation inventory and the edit view of entailment that the surface cues reflect. DeBERTaV3 (He et al. 2021) is the encoder we fine-tune.

## 3. Research question and hypotheses

**Research question.** On fine-grained phrase NLI, do systems achieve directional consistency by representing the relation between the two phrases, or by exploiting surface asymmetries such as length and lexical containment, and how much of a fine-tuned encoder's weighted F1, SoftCons and HardCons does a cue-only model recover? Assignment 1 measures the gap; Assignment 2 designs a method that gives a decoder LLM direction without giving up accuracy.

**H1.** A cue-only model reaches a large share of the encoder's SoftCons, because every cue is symmetric or flips sign exactly under reversal, so its decisions on a pair and its reverse are compatible by construction.

**H2.** The encoder's advantage concentrates in HardCons and in the equivalence-versus-entailment boundary, where the cues are uninformative.

**H3.** Accuracy and consistency trade off in models trained on single ordered instances: the more a model exploits asymmetric patterns, the more its SoftCons falls.

## 4. Baselines

- *Trivial floor* (`experiments/2026-09-29-trivial-baselines-track1/`): majority label (FORWARD_ENTAILMENT after the 881/881 tie-break) and uniform random with seed 13.
- *ML baseline* (`experiments/2026-09-29-ml-baseline-track1/`): logistic regression on 17 surface cues, on word 1-2-gram TF-IDF of the pair, and on both; gradient-boosted trees on the cues. Hyperparameters fixed in advance (scikit-learn defaults, C = 1.0, balanced class weights). Stability from 5-fold cross-validation on train grouped by source pair, every fold scored by the official scorer; one fit on full train and one scoring on dev.
- *DL baseline* (`experiments/2026-09-29-deberta-base-track1/`): DeBERTa-v3-base fine-tuned with a seeded loop (AdamW, learning rate 2e-5, batch 16, 5 epochs, 6 % warm-up, weight decay 0.01, max 32 tokens), epoch chosen on a 20 % grouped slice of train, three seeds (13, 42, 1234), one T4 per seed on Modal, about 140 s of training each. The run is deterministic given seed and GPU type: a second execution reproduced every dev prediction.

## 5. Initial results

Track 1 dev, official scorer.

| System | Weighted F1 | SoftCons | HardCons |
|---|---|---|---|
| majority | 0.129 | 0.000 | 0.000 |
| random (seed 13) | 0.246 | 0.184 | 0.054 |
| cues + logreg | 0.531 | 0.794 | 0.552 |
| tfidf + logreg | 0.407 | 0.426 | 0.256 |
| both + logreg | 0.596 | 0.747 | 0.570 |
| cues + gbdt | 0.574 | 0.718 | 0.527 |
| DeBERTa-v3-base, mean ± sd of 3 seeds | 0.807 ± 0.015 | 0.877 ± 0.010 | 0.810 ± 0.013 |

Cross-validated weighted F1 on train: cues + logreg 0.575 ± 0.037, tfidf + logreg 0.429 ± 0.011, both + logreg 0.617 ± 0.021, cues + gbdt 0.572 ± 0.024; dev sits within about one standard deviation for three systems and 1.2 below for the cue-only model, with the same ranking.

**What the results say so far.**

- H1 is supported by the ML baseline: the cue-only model is the most self-consistent system (SoftCons 0.79, 220 of 277 dev pairs) while confusing the two directions in only 14 of 380 directional instances; 67 of its consistent pairs are wrong in both directions, which is why HardCons stays at 0.55.
- H3 shows inside the ML family: adding TF-IDF raises F1 to 0.60 and lowers SoftCons to 0.75; trees on the cues raise F1 to 0.57 and lower SoftCons to 0.72.
- Equivalence is the hard class for every system (F1 0.39 to 0.46), as the EDA predicted: the cues say whether one phrase adds material, not whether the addition narrows the meaning.
- H2 is supported by the encoder: DeBERTa-v3-base clears the cue-based systems on all three scores (weighted F1 0.81 against 0.60, HardCons 0.81 against 0.57, SoftCons 0.88 against 0.79), and the gain concentrates where the cues were blind: EQUIVALENCE F1 from 0.45 to 0.78 while direction confusions stay rare (3 of 380 for seed 13). NEGATIVE_OTHER becomes the hardest class (F1 0.63).
- H3 does not hold for the encoder: it gained accuracy and consistency together, and only 16 to 21 of its consistent pairs are wrong in both directions against 67 for the cue-only model. The trade-off seen inside the ML family belongs to those feature sets, not to learning from ordered instances in general.
- The pilot's 0.75 / 0.84 / 0.79 remain a reference point only: different track, split and tuning budget.

## 6. Limitations and next steps

One track, one seed for the ML split and models, fixed rather than tuned hyperparameters, and a dev set that overlaps train at the phrase level for a fifth of its phrases. Assignment 2 moves to decoder LLMs, where the pilot found the largest consistency gap, with pair-swap augmentation, a consistency loss over the pair and its reverse, and symmetric prompting as candidate mechanisms.
