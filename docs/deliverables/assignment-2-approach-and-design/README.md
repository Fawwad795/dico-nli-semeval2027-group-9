# Assignment 2: Proposed approach and experimental design

Due Sunday 15 November 2026, 11:59 PM (extended from 13 November).

Topic: SemEval-2027 Task 2, DiCo-NLI. The proposed method is reversal-equivariant LoRA: a frozen Qwen2.5-1.5B-Instruct decoder scored on four option letters, LoRA adapters trained with a loss that ties the prediction for a pair to the prediction for its reverse, and a decoding step that averages the two orders. It is compared against the Assignment 1 baselines, the fine-tuned DeBERTa-v3-base among them.

The brief is `Assignment_2_Proposed_Approach_and_Experimental_Design.pdf` in this folder. The plan, the fixed decisions and who writes what are in GitHub issue 13; the four task issues are 14 to 17.

| What | Where |
|---|---|
| Report source (LaTeX, ACL template) | `report/` |
| Method code | `src/dico_nli/method/` (`reversal.py`, `decoder.py`), tests under `tests/` |
| GPU launcher | `scripts/modal/train_decoder.py` |
| Preliminary verification | `notebooks/assignment-2/01_preliminary_verification.ipynb`, recorded in `experiments/2026-11-14-decoder-preliminary-track1/` |
| Significance tests and subgroups | `src/dico_nli/stats.py`, `notebooks/assignment-2/02_reliability_track1.ipynb`, recorded in `experiments/2026-11-15-reliability-track1/` |
| Submitted report | `SemEval_Task2_DiCo_NLI_Group_9_Assignment_2.pdf` |

Items from the brief's checklist:

- [x] Clearly specified proposed method (report section 1)
- [x] Justification grounded in Assignment 1 findings and literature (section 2)
- [x] Architecture diagram marking trainable and frozen parts (section 3)
- [x] Simple baseline, classical ML system, pretrained system (section 4)
- [x] Ablation experiments (section 5)
- [x] Official and secondary evaluation measures (section 6)
- [x] Complete experimental protocol, leakage prevention, data-split description (section 7)
- [x] Initial end-to-end implementation (section 8)
- [x] Preliminary verification experiment (section 9)
- [x] Reproducibility details, seeds and configurations (section 10)
- [x] Limitations and planned next experiments (sections 10 and 11)
- [x] LaTeX report with tables, figures and references

No item of the brief is inapplicable to this topic.

Every number reported here traces to a folder under `experiments/` with its seed, data version, config, and command.
