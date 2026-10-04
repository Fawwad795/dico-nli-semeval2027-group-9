# Apaolaza et al. 2026: Assessing Logical Coherence of LLMs via Fine-Grained NLI

Jon Felix Apaolaza Larraya, Begoña Altuna, Aitor Soroa, Inigo Lopez-Gazpio. *Assessing Logical Coherence of LLMs via Fine-Grained NLI.* LREC 2026, pages 5431 to 5444. Verified 2026-09-29 at https://lrec.elra.info/lrec2026-main-423 and read from the copy the organizers ship in the task repository (`latex/task_proposal_v2/item3.Baseline_System_Results__LREC_2026_DiCo_NLI_Pilot.pdf`).

## What it says

The pilot study behind SemEval-2027 Task 2. The authors fine-tune encoder, decoder and encoder-decoder transformers on PhrasIS phrase pairs and introduce two coherence measures: soft causal coherence (the prediction on a pair and on its reversal are compatible) and hard causal coherence (both are also correct). Encoders lead on every configuration, with DeBERTa-v3-base and -large strongest; decoder-only models trail on both accuracy and coherence, and all families drop from the seen to the unseen split. Hyperparameters came from up to 150 Optuna trials per model on an 80/20 split of the training data. The manual error analysis singles out prepositional phrases and near-synonymy or taxonomic relations as the main failure sources.

## Why it matters for DiCo-NLI

SoftCons and HardCons in the official scorer are these two measures. The paper's numbers (DeBERTa-v3-base at weighted F1 0.75, SoftCons 0.84, HardCons 0.79 on the positives track) are the reference point for our encoder baseline, with the caveat that the SemEval track adds NEGATIVE_OTHER and is scored on a different split. Its finding that decoder-only models are the least coherent is the gap our Assignment 2 method targets.

## Where it goes

Assignment 1: task and data understanding, the baseline section, and the comparability caveat. Assignment 2: the case for working on decoder LLMs.
