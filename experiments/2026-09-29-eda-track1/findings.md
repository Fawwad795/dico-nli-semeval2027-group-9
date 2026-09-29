# EDA findings, DiCo-NLI track 1 (English)

Computed on the 3,042 training instances by `notebooks/assignment-1/02_eda_track1.ipynb`; the 660 dev instances appear only in the split comparison. Every number below is in `tables/`, every figure in `figures/`. Data commit and command: `config.json`.

## Statistical

- Labels: FORWARD_ENTAILMENT 881 (29 %), BACKWARD_ENTAILMENT 881 (29 %), EQUIVALENCE 802 (26 %), NEGATIVE_OTHER 478 (16 %). Dev matches within half a point. Forward and backward counts are equal by construction: each reversible source pair contributes one of each, or two equivalences.
- Structure: 1,760 source pairs, of which 1,282 are reversible (two instances each) and 478 are negatives (one instance, no flipped twin). Dev: 383 pairs, 277 reversible, 106 negatives.
- Split overlap: no source pair is shared, but 7 unordered text pairs occur in both splits, and 155 of the 712 distinct dev phrases (22 %) appear somewhere in train. The grouped split holds at pair level; a model can still have seen a fifth of dev's phrases during training.
- Phrases are short: 3.0 words on average, at most 15. In forward pairs the premise averages 3.5 words against 2.4 for the hypothesis; backward pairs mirror that; equivalences and negatives are balanced.
- Length cue (figure f2): the premise is longer in 78 % of forward pairs and the hypothesis in 78 % of backward pairs. Equivalences split 36 / 29 / 36 and negatives 24 / 49 / 27 (premise longer / same / hypothesis longer). The rule "the longer phrase is the entailing one" recovers direction in 78 % of directional pairs but cannot tell equivalences or negatives from them; equal length is the single strongest marker of a negative.

## Readability

- Syllables per word range from 1.53 to 1.60 across labels and characters per word from 4.5 to 4.9; equivalences use slightly longer words. Flesch reading ease medians sit between 78 and 82 for every label, and the formula assumes sentences. Readability does not separate the labels; the facet documents that the data is uniformly short caption and headline phrases.

## Lexical

- Word-set overlap is highest for directional pairs: mean Jaccard 0.41 for forward and backward against 0.24 for equivalence and 0.27 for negatives. Equivalences are paraphrases ("to repeal" / "revokes"); directional pairs are usually the same phrase with material added or removed.
- Containment is the directional cue (figure f4): all hypothesis words occur in the premise in 45 % of forward pairs and 2 % of backward pairs, and the mirror holds for backward. Equivalences 4 % / 4 %, negatives 1 % / 1 %. When full containment fires it almost always points the right way.
- The last token is shared in 58 % of directional pairs against 28 % of equivalences and 35 % of negatives: the head noun is kept and modifiers change ("Conservatives" / "Conservative opposition").
- Function words dominate the token counts of every label ("a", "the", "in", "on", "of"); content words are too sparse to rank.

## Semantic

- Cosine similarity of MiniLM embeddings has median 0.76 for equivalences, 0.77 for forward and backward, and 0.64 for negatives. Only 27 % of negatives lie above the equivalence median against 52 % of directional pairs, so similarity separates negatives from related pairs moderately and equivalences from entailments not at all.
- Cosine is symmetric, so an original and its flipped twin receive the same value and the forward and backward distributions are identical (figure f5 draws them as one curve). Any pair representation that is symmetric in the two phrases, such as a bi-encoder cosine or a bag of words, carries no information about direction. A model built on one can only be self-consistent by predicting a symmetric label everywhere, and the trivial-baseline run shows what the alternative looks like: FORWARD_ENTAILMENT everywhere scores SoftCons 0.

## Linguistic

- The head lemma is the same on both sides in 52 % of directional pairs against 30 % of equivalences and 34 % of negatives: directional pairs mostly add or drop modifiers around a kept head.
- The part-of-speech pattern is identical in 31 % of negatives against 7 % of directional pairs and 17 % of equivalences: negatives are often a minimal substitution inside the same structure ("off Mexico" / "on Mexico", "southern" / "northern").
- At least one phrase contains a preposition in 47 % of directional pairs, 54 % of equivalences and 61 % of negatives. The pilot paper found prepositional phrases to be its main error source; they are common everywhere here and most common in the class the pilot did not have.
- Adjectives are the added material: the premise carries 0.33 more adjectives than the hypothesis in forward pairs, 0.33 fewer in backward pairs, and the same number for equivalences and negatives. A numeral appears in 18 % of directional pairs, 14 % of negatives and 6 % of equivalences.
- The most frequent premise patterns are DET NOUN and ADP DET NOUN for backward pairs, DET ADJ NOUN and ADP DET ADJ NOUN for forward pairs, and verb forms (AUX VERB, VERB) for equivalences.

## What this means for the baselines

1. Direction lives in asymmetric surface features: which side is longer, which side's words contain the other's, which side carries the extra adjective. A cue-only baseline should recover much of the forward-versus-backward decision.
2. Equivalence against entailment is the hard boundary: similar overlap, identical similarity. The distinguishing signal is whether the added material narrows the meaning or paraphrases it, which none of the surface cues capture.
3. Negatives are marked by structural identity with a substituted word (same pattern, equal length) and by lower semantic similarity.
4. Symmetric representations are direction-blind by construction, so the consistency metrics reward symmetric predictions; the research question has to ask how a model earns direction rather than whether it stays consistent.

Caveats: one track, train only; spaCy's small English model tags three-word phrases without sentence context; MiniLM is one encoder; the containment and length cues were chosen before looking at dev.
