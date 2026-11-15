# Schick and Schuetze 2021: Exploiting Cloze-Questions

Timo Schick and Hinrich Schuetze. *Exploiting Cloze-Questions for Few-Shot Text Classification and Natural Language Inference.* Proceedings of the 16th Conference of the European Chapter of the Association for Computational Linguistics: Main Volume, 255-269, 2021. DOI: 10.18653/v1/2021.eacl-main.20. Verified and read 2026-11-15 from the [ACL Anthology paper](https://aclanthology.org/2021.eacl-main.20/) and its linked PDF.

## What it says

Pattern-Exploiting Training (PET) turns classification inputs into cloze patterns containing a mask and maps each class to a vocabulary word through a verbalizer. At inference, the masked-language model scores the class words; a softmax over these scores yields a class distribution. PET also uses the trained pattern-verbalizer models to pseudo-label unlabeled examples before training a classifier.

## Why it matters for DiCo-NLI

This is a precedent for making classification decisions from language-model token scores instead of generating unconstrained text and parsing it. Our method takes the class-token scoring idea to a causal instruction model: it scores the next-token logits for four option letters. It does not use PET's masked-token patterns, multi-pattern ensemble, or pseudo-labeling procedure. The paper's NLI experiments also use the usual three-way relation setting rather than DiCo-NLI's four directional labels.

## Where it goes

Assignment 2: justify constrained four-letter scoring and distinguish our causal decoder inference from PET.
