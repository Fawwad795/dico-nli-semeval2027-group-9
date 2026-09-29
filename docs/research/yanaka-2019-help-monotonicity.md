# Yanaka et al. 2019: HELP, monotonicity reasoning

Hitomi Yanaka, Koji Mineshima, Daisuke Bekki, Kentaro Inui, Satoshi Sekine, Lasha Abzianidze, Johan Bos. *HELP: A Dataset for Identifying Shortcomings of Neural Models in Monotonicity Reasoning.* *SEM 2019. Verified 2026-09-29 at https://aclanthology.org/S19-1027/.

## What it says

A dataset built to test whether NLI models handle monotonicity: whether replacing a phrase by a more general or more specific one preserves entailment depends on the polarity of its context. Augmenting training data with HELP improves models overall, but some inference types stay hard, and the authors' related work shows models do far better on upward than on downward inferences.

## Why it matters for DiCo-NLI

Forward and backward entailment between phrases are exactly upward and downward monotone moves, and the pilot paper found the same asymmetry between the two. The paper is evidence that the direction of an inference is a learned, fragile property rather than something a model gets for free from lexical overlap.

## Where it goes

Assignment 1: selected literature on directional inference; Assignment 2: a source of augmentation ideas.
