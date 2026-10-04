# Elazar et al. 2021: Measuring and Improving Consistency in Pretrained Language Models

Yanai Elazar, Nora Kassner, Shauli Ravfogel, Abhilasha Ravichander, Eduard Hovy, Hinrich Schütze, Yoav Goldberg. *Measuring and Improving Consistency in Pretrained Language Models.* TACL 9, 2021. Verified 2026-09-29 at https://aclanthology.org/2021.tacl-1.60/.

## What it says

Consistency is defined as invariance of a model's behaviour under meaning-preserving changes of its input. The ParaRel benchmark (328 paraphrases over 38 relations) shows pretrained language models are often inconsistent on factual queries, and a consistency loss improves them.

## Why it matters for DiCo-NLI

Reversal is not meaning-preserving, so DiCo-NLI's consistency is a related but different notion: the output must change in a prescribed way. The paper supplies the general definition and vocabulary against which the directional version is stated, and its "measure, then train for it" pattern is the one the task follows with SoftCons.

## Where it goes

Assignment 1: selected literature on consistency, the definition paragraph.
