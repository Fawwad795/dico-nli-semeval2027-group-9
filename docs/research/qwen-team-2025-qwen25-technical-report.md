# Qwen Team 2025: Qwen2.5 Technical Report

Qwen Team et al. *Qwen2.5 Technical Report.* arXiv:2412.15115, revised 2025. Verified and read 2026-11-15 from the [arXiv record and full HTML](https://arxiv.org/abs/2412.15115).

## What it says

The report describes the Qwen2.5 family of open-weight base and instruction-tuned models, including dense sizes from 0.5B through 72B. It documents the series' architecture and training, and lists the 1.5B dense model as a 28-layer model with 12 query heads and 2 key/value heads, a 32K context window, and an Apache 2.0 license.

## Why it matters for DiCo-NLI

The Assignment 2 plan selects Qwen2.5-1.5B-Instruct as the decoder backbone and Qwen2.5-0.5B-Instruct for local pipeline checks. This report is the primary technical source for describing the model family and the chosen backbone; benchmark claims in the report are not evidence that the model will solve our four-way NLI task.

## Where it goes

Assignment 2: model choice and system architecture. The architecture diagram marks this backbone as frozen and the LoRA adapters as trainable.
