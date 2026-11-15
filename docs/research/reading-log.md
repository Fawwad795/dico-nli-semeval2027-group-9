# Reading log

One row per paper read for the project, newest first. Each has its own note in this folder; the note carries the verified citation and the paragraph it feeds.

| Date | Paper | Strand | Why it matters here | Feeds |
|---|---|---|---|---|
| 2026-11-15 | Wang, Sun and Xing 2019, AAAI | swap robustness | Closest prior: swap evaluation and training for three-way NLI; bounds what our four-way loss and symmetrized decoder add | A2 justification |
| 2026-11-15 | Hu et al. 2022, ICLR | parameter-efficient fine-tuning | Freezes the backbone and trains low-rank updates; supports the training-cost rationale without promising DiCo-NLI gains | A2 method justification and architecture |
| 2026-11-15 | Qwen Team et al. 2025, arXiv | backbone | Primary technical description of the selected Qwen2.5 open-weight family and 1.5B architecture | A2 method and architecture |
| 2026-11-15 | Schick and Schuetze 2021, EACL | label-token scoring | Pattern-verbalizer scoring gives a precedent for choosing a class from language-model token probabilities | A2 inference justification |
| 2026-11-15 | Liang et al. 2021, NeurIPS | consistency | R-Drop matches output distributions; clarifies the precedent and the difference in our reversed-input JS loss | A2 consistency-loss justification |
| 2026-09-29 | Apaolaza et al. 2026, LREC | pilot study | Defines SoftCons and HardCons; reference numbers for DeBERTa-v3-base; decoders least coherent | A1 baselines, A2 motivation |
| 2026-09-29 | Berglund et al. 2024, ICLR | reversal curse | Origin of the reversal framing; decoders fail "B is A" after learning "A is B" | A1 literature |
| 2026-09-29 | Lv et al. 2024, EMNLP | reversal curse | Cause is the causal objective; BICO fixes it at training time | A1 literature, A2 method |
| 2026-09-29 | Lopez-Gazpio et al. 2024, Logic Journal of the IGPL | data | PhrasIS, the phrase-pair source of DiCo-NLI | A1 data |
| 2026-09-29 | Agirre et al. 2016, SemEval | data | Interpretable STS chunk alignments, where the phrases come from | A1 data |
| 2026-09-29 | MacCartney and Manning 2009, IWCS | natural logic | The relation inventory and the edit view of entailment | A1 formal background |
| 2026-09-29 | Yanaka et al. 2019, *SEM | monotonicity | Direction of inference is learned and fragile; downward is harder | A1 literature, A2 augmentation |
| 2026-09-29 | He et al. 2021, ICLR 2023 | model | DeBERTaV3, the encoder baseline | A1 baseline |
| 2026-09-29 | Li et al. 2019, EMNLP | consistency | Logic rules over example groups as losses | A1 literature, A2 method |
| 2026-09-29 | Minervini and Riedel 2018, CoNLL | consistency | Adversarial regularisation for NLI constraints | A1 literature |
| 2026-09-29 | Elazar et al. 2021, TACL | consistency | Consistency as invariance under paraphrase; ParaRel | A1 definition paragraph |

Still to read, if time allows: Yanaka et al. 2019b (BlackboxNLP, monotonicity probing of NLI models); Geiger et al. 2020 (BlackboxNLP, lexical entailment and negation); Kitouni et al. 2024 (factorisation-agnostic training against the reversal curse), all cited by the pilot paper.
