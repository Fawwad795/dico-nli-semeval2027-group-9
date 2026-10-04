# Li et al. 2019: A Logic-Driven Framework for Consistency of Neural Models

Tao Li, Vivek Gupta, Maitrey Mehta, Vivek Srikumar. *A Logic-Driven Framework for Consistency of Neural Models.* EMNLP-IJCNLP 2019. Verified 2026-09-29 at https://aclanthology.org/D19-1405/.

## What it says

A neural model can be accurate on individual examples and still hold contradictory beliefs across related ones. The paper turns logical rules over groups of examples (for NLI: symmetry of contradiction, transitivity across three sentences) into differentiable losses that regularise the model away from inconsistency, on labelled and unlabelled data, and shows gains in both accuracy and consistency.

## Why it matters for DiCo-NLI

Directional consistency is a rule of this form: the label on (B, A) must be the reverse of the label on (A, B). The paper gives a ready template for a consistency loss over the original and reversed pair, which is one of the Assignment 2 candidate mechanisms.

## Where it goes

Assignment 1: selected literature on consistency; Assignment 2: method design.
