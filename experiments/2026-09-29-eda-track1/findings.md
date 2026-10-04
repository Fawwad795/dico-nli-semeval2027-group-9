# EDA findings, DiCo-NLI track 1 (English)

The notebook analyzes 3,042 ordered training instances across six feature groups. It uses dev only for label and pair structure, overlap, language, and data-quality checks; exploratory feature comparisons use train only. Phrase-quality counts refer to text-field occurrences across both sides, not unique strings. Tables and individual figures are in this run folder; `eda_figures.pdf` combines the seven figures. `config.json` records the command and the train-data commit.

## 1. Statistical and data quality

**Question:** Are the labels and source pairs structured as expected, and is the data clean enough to trust the feature comparisons? Does phrase length act as a directional cue?

**Observation:** Train has 802 equivalences (26%), 881 forward (29%), 881 backward (29%), and 478 negative/other instances (16%). Dev proportions are close: 26%, 29%, 29%, and 16%. Train contains 1,760 source pairs, including 1,282 reversible pairs; dev contains 383 pairs, including 277 reversible pairs. No pair IDs cross the split, but seven unordered text pairs do. Of 712 distinct dev phrases, 155 (22%) also appear in train. Phrases average about three words, with a train maximum of 15. In 78% of forward instances the premise is longer; backward instances mirror this, while equivalences split 36% / 29% / 36% across premise-longer / same-length / hypothesis-longer. Negative pairs are same-length in 49% of instances.

Both splits have zero missing or empty text values and all rows have two non-empty texts. Train contains 43 exact ordered-duplicate groups (51 extra rows), and dev contains four groups (four extra rows). One train group has disagreeing labels: `South Africans` → `South Africa` appears as both `FORWARD_ENTAILMENT` and `NEGATIVE_OTHER` under pair IDs `dico_phrasis_0000065` and `dico_phrasis_0002985`. There are 1,258 train and 275 dev distinct text pairs represented in both orders. The broader unordered-duplicate count is 1,258 groups / 1,309 extra rows in train and 275 / 279 in dev; it includes the intended reversed twins and should not be read as an error count. Train has 563 one-word phrase occurrences, 27 phrases with at least eight words, and 56 phrases starting with a clitic or punctuation. Dev has 135, 7, and 21 respectively. All 3,042 train and 660 dev instances are English-English. The reference CSVs do not include `source_split`, `source_modality`, or `original_source_file`. The 461 trial examples do include those nested source fields: 294 trace to source train and 167 to source test; 217 are headlines and 244 images.

**Interpretation:** The splits are similarly balanced and pair IDs are isolated, but repeated phrases still cross the split. The exact duplicate label conflict is a concrete audit candidate. Short, one-word phrases are common, while long phrases are rare. Reversed text pairs mostly reflect the task's designed reversible examples; counting them as generic errors would misstate data quality. Source provenance is available for trial examples but not the train/dev reference CSVs.

**Modeling implication:** Keep validation grouped by source pair and report phrase overlap when interpreting scores. Audit the conflicting duplicate before drawing conclusions from that example. Length and containment are promising directional baseline features, but length alone does not distinguish equivalence from negative pairs. Record that train/dev source provenance is unavailable if later analyses need to stratify by source.

## 2. Readability

**Question:** Do word and syllable lengths vary by relation, or are the phrases uniformly short?

**Observation:** Mean syllables per word range from 1.53 to 1.60 across labels, and mean characters per word range from 4.5 to 4.9. Median Flesch reading-ease values range from 77.9 to 82.4; the premise/hypothesis values swap for forward and backward labels, as expected for reversed pairs. These phrases average about three words, so the formula's sentence-level interpretation does not fit the data well. TTR, MTLD, and HD-D are omitted because phrase-level samples this short make lexical-diversity estimates unstable or uninformative.

**Interpretation:** Word-form complexity is broadly similar across labels. Small differences in Flesch scores mostly reflect syllable density and phrase length rather than sentence readability; the values are descriptive only.

**Modeling implication:** Readability measures are unlikely to separate relations on their own. If retained, use word and syllable measures as low-cost controls, and do not interpret Flesch as a calibrated difficulty score for these fragments.

## 3. Lexical

**Question:** Do word overlap, containment, and shared phrase endings distinguish entailment direction from equivalence and unrelated pairs?

**Observation:** Mean word-set Jaccard is 0.41 for forward and backward pairs, compared with 0.24 for equivalence and 0.27 for negative/other. Full containment is directional: every hypothesis word occurs in the premise for 45% of forward pairs and 2% of backward pairs; the reverse holds for backward pairs. Equivalences show 4% full containment in either direction, and negatives about 1% in either direction. The final token is shared in 58% of directional instances, 28% of equivalences, and 35% of negatives.

**Interpretation:** Directional pairs often preserve a phrase and add or remove words, while equivalences can use synonyms with less literal overlap. Full containment strongly favors one direction when it occurs, but it covers fewer than half of the directional instances. A shared ending often means the head phrase is retained as modifiers change.

**Modeling implication:** Include both orientations of containment and ordered token features in a cue baseline. Use lexical overlap as evidence for relatedness, not as a substitute for deciding whether added material narrows or changes meaning.

## 4. Semantic

**Question:** Does embedding similarity separate equivalent or directional pairs from unrelated pairs, and does it contain information about direction?

**Observation:** MiniLM cosine medians are 0.76 for equivalence, 0.77 for forward/backward, and 0.64 for negative/other. About 52% of directional instances and 50% of equivalences are at or above the equivalence median, versus 27% of negatives. Cosine is symmetric, so a reversed pair has the same value in either order.

**Interpretation:** The encoder separates negative pairs from semantically related pairs moderately, but similarity barely separates equivalence from entailment. Its symmetry means it cannot identify forward versus backward direction.

**Modeling implication:** Use cosine as a relatedness signal alongside an ordered representation, such as cross-phrase interactions or directional features. A symmetric-only representation cannot recover direction; consistency alone does not show that a model understands entailment direction.

## 5. Linguistic

**Question:** Do shared heads, part-of-speech patterns, adjectives, numerals, and prepositions vary by relation?

**Observation:** The two phrases share a head lemma in 52% of directional instances, compared with 30% of equivalences and 34% of negatives. Identical POS patterns are most common in negatives (31%), versus 17% of equivalences and 7% of directional instances. At least one phrase contains a preposition in 47% of directional, 54% of equivalence, and 61% of negative instances. Forward premises have 0.33 more adjectives on average than their hypotheses; backward pairs reverse that difference. A numeral appears in 18% of directional instances, 14% of negatives, and 6% of equivalences.

**Interpretation:** Directional pairs often keep the same head while adding or removing modifiers. Negatives often preserve the grammatical frame while substituting a word. Prepositions are common across all labels, especially negatives, so their presence alone is weak evidence. Numerals show some label variation but occur in a minority of pairs. spaCy parses these short fragments with little surrounding context.

**Modeling implication:** Compare the two phrase heads and modifier counts, and model lexical substitutions inside shared POS patterns. Treat spaCy features as noisy surface cues, then inspect errors involving prepositions and numeral substitutions.

## 6. Task-specific cues

**Question:** How often do quantifiers, negation, numerals, and named entities appear in each relation, and are they frequent enough to help a baseline?

**Observation:** A pair counts once when either side contains a cue. Quantifiers occur in 3.3% of forward/backward instances, 1.7% of negatives, and 0.7% of equivalences. Negation is rare: six equivalence rows and one row in each other label (under 1% per class). Numerals occur in 18.0% of directional instances, 14.0% of negatives, and 6.2% of equivalences. spaCy identifies named entities in 46.7% of directional instances, 38.1% of negatives, and 32.2% of equivalences. Reversible pairs contribute one ordered row to each directional label, so equal forward/backward counts are expected.

**Interpretation:** Numerals and named entities are frequent enough to test as features, but both appear across all relations. Quantifier and negation indicators are sparse; their apparent label differences rest on small counts. Named entities may reflect topic or source composition as much as entailment.

**Modeling implication:** Add these cues as explicit indicators or error-analysis slices, and compare them with a baseline without them. Keep rare-cue results descriptive and avoid treating the observed counts as reliable evidence of a general rule.

## Summary for the baselines

1. Ordered surface cues, especially length and containment, are the clearest signals for forward versus backward entailment.
2. Similarity and overlap identify related phrases more readily than they distinguish equivalence from entailment; that boundary needs meaning-sensitive evidence.
3. Negative pairs often keep a grammatical pattern while changing a word, and they have lower semantic similarity on average.
4. Symmetric representations cannot carry direction. Evaluate directional behavior with ordered inputs and pair-aware splits.

These findings are descriptive for one English track. spaCy's small English model sees headline-like fragments without sentence context, MiniLM is one encoder, and cue lists are fixed for this analysis. The data-quality and language checks run on both train and dev; feature comparisons above use train only.
