# Lopez-Gazpio et al. 2024: PhrasIS, Phrase Inference and Similarity benchmark

Iñigo Lopez-Gazpio, J. Gaviria, P. García, H. Sanjurjo-González, B. Sanz, A. Zarranz, Montse Maritxalar, Eneko Agirre. *PhrasIS: Phrase Inference and Similarity benchmark.* Logic Journal of the IGPL 32(6), pages 1088 to 1101, 2024, doi 10.1093/jigpal/jzae037; an earlier version appeared as a SOCO 2021 chapter (Springer, Advances in Intelligent Systems and Computing). Verified 2026-09-29 at https://academic.oup.com/jigpal/article-abstract/32/6/1088/7639121 and https://link.springer.com/chapter/10.1007/978-3-030-87869-6_25.

## What it says

A dataset of phrase pairs annotated with both an inference label and a similarity score, built from naturally occurring image captions and news headlines and annotated by experts. It sits between word-level and sentence-level resources, so compositional models can be evaluated at phrase granularity. The paper analyses how inference labels and similarity scores relate and reports baseline systems.

## Why it matters for DiCo-NLI

DiCo-NLI is the reversible subset of PhrasIS with the remaining labels collapsed into NEGATIVE_OTHER, plus the reversed copy of every reversible pair. The phrase lengths, the caption and headline mix, and the label inventory we see in the EDA all come from here.

## Where it goes

Assignment 1: task and data understanding, provenance of the data.
