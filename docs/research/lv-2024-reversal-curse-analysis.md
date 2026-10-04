# Lv et al. 2024: An Analysis and Mitigation of the Reversal Curse

Ang Lv, Kaiyi Zhang, Shufang Xie, Quan Tu, Yuhan Chen, Ji-Rong Wen, Rui Yan. *An Analysis and Mitigation of the Reversal Curse.* EMNLP 2024 main conference; arXiv 2311.07468 (November 2023). Verified 2026-09-29 at https://arxiv.org/abs/2311.07468.

## What it says

The reversal curse is traced to the training objective of causal language models, next-token prediction with a left-to-right attention mask, rather than to model size. The proposed remedy, bidirectional causal language model optimisation (BICO), changes the objective and the attention so that a model trained on "A is B" also learns "B is A".

## Why it matters for DiCo-NLI

It locates the cause of directional failure in the decoder objective, which matches the pilot's finding that decoder-only models are the least coherent family. For Assignment 2 it argues that a decoder LLM will not become direction-consistent by prompting alone; the fix has to touch training, which is why pair-swap augmentation and a consistency loss are on the candidate list.

## Where it goes

Assignment 1: selected literature, the reversal-curse strand; Assignment 2: method motivation.
