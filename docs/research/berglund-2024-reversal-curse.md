# Berglund et al. 2024: The Reversal Curse

Lukas Berglund, Meg Tong, Max Kaufmann, Mikita Balesni, Asa Cooper Stickland, Tomasz Korbak, Owain Evans. *The Reversal Curse: LLMs trained on "A is B" fail to learn "B is A".* ICLR 2024; arXiv 2309.12288 (September 2023). Verified 2026-09-29 at https://arxiv.org/abs/2309.12288.

## What it says

Autoregressive language models fine-tuned on statements of the form "A is B" do not generalise to the reversed question "B is A". The effect holds across model sizes and families, and the reversed direction is answered at chance level rather than degraded gradually. The authors treat it as a failure of logical deduction by the training objective, not a matter of scale.

## Why it matters for DiCo-NLI

The task takes its name and its evaluation idea from this paper: every phrase pair is scored in both orders and a system must produce compatible labels. The DiCo-NLI organizers are explicit that their setting differs, because both phrases are given as input, so the model is not asked to recall a reversed fact but to apply the reversed relation. Our research question asks whether the same asymmetry shows up in that easier setting.

## Where it goes

Assignment 1, selected literature, first paragraph: the origin of the reversal framing. Assignment 2, motivation for the consistency-aware method.
