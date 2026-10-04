# He et al. 2021: DeBERTaV3

Pengcheng He, Jianfeng Gao, Weizhu Chen. *DeBERTaV3: Improving DeBERTa using ELECTRA-Style Pre-Training with Gradient-Disentangled Embedding Sharing.* ICLR 2023; arXiv 2111.09543 (November 2021). Verified 2026-09-29 at https://arxiv.org/abs/2111.09543.

## What it says

DeBERTaV3 replaces masked-language-model pre-training with replaced-token detection and introduces gradient-disentangled embedding sharing so the generator and discriminator stop pulling the shared embeddings in opposite directions. The base model reaches the strongest GLUE results in its size class.

## Why it matters for DiCo-NLI

The pilot study's best baseline is DeBERTa-v3-base, and it is the model our deep-learning baseline fine-tunes, so the reference point and our number come from the same architecture.

## Where it goes

Assignment 1: baseline description.
