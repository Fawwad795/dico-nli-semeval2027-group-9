# Liang et al. 2021: R-Drop

Xiaobo Liang, Lijun Wu, Juntao Li, Yue Wang, Qi Meng, Tao Qin, Wei Chen, Min Zhang, and Tie-Yan Liu. *R-Drop: Regularized Dropout for Neural Networks.* Advances in Neural Information Processing Systems 34, 2021. Verified and read 2026-11-15 from the [NeurIPS proceedings record](https://proceedings.neurips.cc/paper/2021/hash/5a66b9200f29ac3fa0ae244cc2a51b39-Abstract.html) and linked paper PDF; arXiv:2106.14448.

## What it says

R-Drop sends each training example through the same network twice with independent dropout masks and penalizes the divergence between the two output distributions with a bidirectional KL term. The method targets inconsistency caused by stochastic dropout submodels and reports experiments across language and vision tasks.

## Why it matters for DiCo-NLI

R-Drop is a precedent for regularizing a model by matching output distributions, but our consistency relation is different. We compare predictions for two different ordered inputs, `(a,b)` and `(b,a)`, after permuting the reversed distribution according to the NLI reversal rule; the plan uses Jensen-Shannon divergence rather than R-Drop's bidirectional KL. The analogy supports a distribution-level penalty, not a claim that R-Drop itself solves directional consistency.

## Where it goes

Assignment 2: explain the consistency-loss design and how it differs from dropout consistency.
