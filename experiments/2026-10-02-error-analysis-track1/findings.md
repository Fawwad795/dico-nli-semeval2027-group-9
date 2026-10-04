# Assignment 1 error analysis: track 1 dev

## Data and method

This analysis uses the 660-row English dev reference at data commit `588968e610197ddc4c440314701cbc587afc4c1b` and committed predictions for cues+logreg, both+logreg, and DeBERTa seeds 13, 42, and 1234. No model was retrained or selected on dev. Full-set metrics use saved official-scorer reports; subset metrics are classification-only because cue filtering may break reversible pairs.

## Pair outcomes

- **cues+logreg:** both_directions_correct 153/277, consistent_but_wrong 67/277, inconsistent_one_direction_correct 1/277, inconsistent_both_directions_wrong 56/277
- **both+logreg:** both_directions_correct 158/277, consistent_but_wrong 49/277, inconsistent_one_direction_correct 21/277, inconsistent_both_directions_wrong 49/277
- **DeBERTa seed 13:** both_directions_correct 228/277, consistent_but_wrong 16/277, inconsistent_one_direction_correct 15/277, inconsistent_both_directions_wrong 18/277
- **DeBERTa seed 42:** both_directions_correct 224/277, consistent_but_wrong 21/277, inconsistent_one_direction_correct 12/277, inconsistent_both_directions_wrong 20/277
- **DeBERTa seed 1234:** both_directions_correct 221/277, consistent_but_wrong 19/277, inconsistent_one_direction_correct 17/277, inconsistent_both_directions_wrong 20/277

`both_directions_correct` means both gold labels were predicted. `consistent_but_wrong` means predictions obey reversal but are not both gold-correct. The other categories are inconsistent with one or neither direction correct.

## H2: scores by length-cue status

| Cue status | n | Cues + logreg weighted F1 | DeBERTa mean weighted F1 | Encoder minus cue |
|---|---:|---:|---:|---:|
| agrees | 282 | 0.907 | 0.931 | +0.024 |
| misleads | 10 | 0.000 | 0.800 | +0.800 |
| uninformative | 368 | 0.313 | 0.754 | +0.442 |

The largest DeBERTa-minus-cue weighted-F1 gap is in **misleads** (+0.800). Equal-length and non-directional examples are uninformative to the length cue and remain separate. The misleading-cue subset contains only 10 rows, so its gap is descriptive rather than a stable estimate.

## Shared DeBERTa errors

All three DeBERTa seeds misclassify **80** of 660 dev instances. Cues+logreg also misclassifies **50** (62.5%). Full list: `tables/deberta_all_seeds_wrong.csv`.

## Twenty inspected seed-13 errors

| Primary category | Count | Rationale |
|---|---:|---|
| prepositional_relation | 4 | Preposition choice or attachment changes the relation. |
| numeral_or_quantifier | 4 | Cardinality and quantifier scope need explicit reasoning. |
| near_synonym_or_taxonomy | 4 | Close lexical relations are not always equivalence or entailment. |
| one_word_negative_contrast | 4 | A single lexical substitution preserves overlap but changes the gold relation. |
| chunking_or_fragment | 4 | Short phrase fragments and different chunk boundaries obscure the relation. |

The category families are guided by the pilot paper's manual analysis (Apaolaza et al., 2026; see [`docs/research/apaolaza-2026-logical-coherence.md`](../../docs/research/apaolaza-2026-logical-coherence.md)); numeral/quantifier scope and one-word negative contrasts are included because they recur in this sample. These errors were manually selected, not sampled randomly; counts describe these 20 only. Phrases and gold/predicted labels: `tables/seed13_error_examples.csv`.

## Full-set scores

See `tables/overall_scores.csv` for weighted F1, macro F1, accuracy, SoftCons, and HardCons for every existing system. See `tables/cue_slice_scores.csv` for n and classification metrics on each cue group.

## Caveats

SoftCons and HardCons are not computed on cue-filtered subsets because a subset may remove one direction of a reversible pair. Manual categories involve judgment and are not corpus-wide category rates. Predictions are fixed; uncertainty beyond the three DeBERTa seeds is not estimated.
