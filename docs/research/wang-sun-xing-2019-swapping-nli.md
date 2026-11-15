# Wang, Sun, and Xing 2019: What If We Simply Swap the Two Text Fragments?

Haohan Wang, Da Sun, and Eric P. Xing. *What If We Simply Swap the Two Text Fragments? A Straightforward yet Effective Way to Test the Robustness of Methods to Confounding Signals in Nature Language Inference Tasks.* Proceedings of the AAAI Conference on Artificial Intelligence 33(1), 7136-7143, 2019. DOI: 10.1609/aaai.v33i01.33017136. Verified and read 2026-11-15 from the [AAAI proceedings paper](https://ojs.aaai.org/index.php/AAAI/article/view/4696) and its linked PDF.

## What it says

The paper studies confounding lexical signals in three-way NLI. It derives which labels should survive swapping premise and hypothesis, evaluates systems on swapped test data, and trains systems on mixtures with different proportions of swapped pairs. Its framing is a stress test for whether a model uses meaning or collection artifacts; its training experiment measures robustness as the swap rate changes.

## Why it matters for DiCo-NLI

This is the closest prior work because it makes pair order central to NLI evaluation and training. Our task has four directional labels, including distinct forward and backward entailment. Our method trains on the aligned distributions for both orders with an explicit label permutation and a Jensen-Shannon consistency term, then averages the aligned distributions at prediction time. Wang et al. do not define this four-way objective or an inference-time symmetrization rule. Their results motivate testing reversal behavior, while our Assignment 1 pair structure shows that simply duplicating reversible pairs would add little new training information.

## Where it goes

Assignment 2: method justification and closest-prior-work comparison; the relation between swap training and our consistency objective.
