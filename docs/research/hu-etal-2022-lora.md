# Hu et al. 2022: LoRA

Edward J. Hu, Yelong Shen, Phillip Wallis, Zeyuan Allen-Zhu, Yuanzhi Li, Shean Wang, Lu Wang, and Weizhu Chen. *LoRA: Low-Rank Adaptation of Large Language Models.* International Conference on Learning Representations, 2022. Verified and read 2026-11-15 from the [ICLR/OpenReview paper](https://openreview.net/pdf?id=nZeVKeeFYf9) and the arXiv record [2106.09685](https://arxiv.org/abs/2106.09685).

## What it says

LoRA freezes pretrained weights and represents their task-specific update with trainable low-rank matrices. The paper reports substantially fewer trainable parameters and lower optimizer memory than full fine-tuning, with competitive model quality in its experiments and no added inference latency after merging the updates.

## Why it matters for DiCo-NLI

Our 3,042 training instances form a small supervised dataset for adapting a 1.5B-parameter model. LoRA lets us test the proposed decoder while keeping the number of learned parameters and GPU memory lower than full fine-tuning. The paper supports that efficiency rationale; it does not establish that LoRA will outperform full fine-tuning on DiCo-NLI, so that remains an empirical question.

## Where it goes

Assignment 2: justification for frozen Qwen2.5-1.5B-Instruct with trainable rank-16 adapters on attention projections.
