# Assignment 3: Experiments, analysis and research paper

Due Friday 4 December 2026, 11:59 PM.

The professor's brief is `Assignment_3_Experiments_Analysis_and_Research_Paper.pdf` in this folder (received 2026-11-23). It replaces the course's generic list. Its core principle: the project is judged on the quality of the evidence for what works, why, where it fails and how reliable the result is, not on its best score.

Topic: SemEval-2027 Task 2, DiCo-NLI, English Track 1. We execute the protocol fixed in the Assignment 2 report (`../assignment-2-approach-and-design/`): Section 7 and Appendix D for the protocol, Section 5 and Appendix C for the seven ablations, Section 11 and Appendix F for the run list. Every deviation from that protocol is named in the paper with its reason. Optional after the course: submit to the official evaluation window (10 to 31 January 2027) and write a SemEval system paper.

Every number reported here traces to a folder under `experiments/` with its seed, data commit, config and command. Model and lambda selection use the grouped validation split of train, never the development set.

## Brief requirements

Tick an item when it lands on `main`. An item the topic makes inapplicable is noted with the reason.

### 1. Completed experiments
- [ ] All primary comparison systems and the proposed system run
- [ ] Planned ablations run, important experiments repeated over seeds 13, 42 and 1234
- [ ] Official scorer used unchanged; official and secondary metrics reported
- [ ] Predictions, checkpoints, logs, configurations and experiment summaries preserved
- [ ] Final configurations, splits, preprocessing, model settings, seeds, hardware and computational cost reported
- [ ] Every deviation from the Assignment 2 protocol explained

### 2. Results and statistical analysis
- [ ] Measurement separated from interpretation; tables for exact comparisons, figures for trends and trade-offs
- [ ] Mean and variation over repeated runs
- [ ] Consistent rounding and identical evaluation procedures
- [ ] Statistically or practically meaningful differences identified (confidence intervals, standard deviations, significance tests)
- [ ] Whether conclusions hold across seeds, subsets and evaluation measures

### 3. Ablation and error analysis
- [ ] Each ablation's hypothesis restated and compared with the observed result
- [ ] Components that contribute consistently, weakly or negatively identified
- [ ] Interactions between components discussed
- [ ] Genuine effects distinguished from variance, leakage or changes in data coverage
- [ ] Error categories defined before examples are selected
- [ ] False positives and false negatives analyzed per label
- [ ] Failures related to linguistic, semantic, source and annotation factors
- [ ] Representative examples with target, prediction and explanation
- [ ] Error categories quantified
- [ ] Annotation ambiguity, label noise, shortcuts and dataset artifacts discussed

### 4. Comparison with baselines and relevant work
- [ ] Proposed method compared with simple, classical and pretrained baselines
- [ ] Whether shared-task comparisons use the same split, metric and conditions
- [ ] Literature results compared only when datasets, labels and protocols align
- [ ] Accuracy, interpretability, efficiency and resource trade-offs
- [ ] Each comparison marked direct, approximate or not comparable

### 5. Findings and discussion
- [ ] Strongest empirical finding and its evidence
- [ ] Which design choices mattered most, and under what conditions
- [ ] Unexpected and negative results discussed
- [ ] Observed results separated from hypotheses about their causes
- [ ] Limitations, threats to validity, compute constraints, generalization risks
- [ ] Concrete next steps that follow from the findings

### 6. Research-paper report (LaTeX, BibTeX, source in `docs/paper/`)
- [ ] 1 Title and abstract
- [ ] 2 Introduction and research questions
- [ ] 3 Related work
- [ ] 4 Task and dataset
- [ ] 5 Proposed method
- [ ] 6 Experimental setup
- [ ] 7 Results
- [ ] 8 Ablation and error analysis
- [ ] 9 Comparison with relevant work
- [ ] 10 Discussion and limitations
- [ ] 11 Conclusion and future work
- [ ] 12 References
- [ ] Maths where appropriate, labelled tables and figures, cross-references, explicit research questions or hypotheses

### 7. Presentation and demo
- [ ] Slides: problem and task formulation; data, observations and research questions; approach and architecture; experimental design and comparison systems; results, ablations and error analysis; findings, limitations and future work; a clear conclusion
- [ ] Demo of the complete input-to-output workflow, with successful and failure cases
- [ ] Demo explains model output and evaluation behaviour, and states whether it uses a live model, a saved checkpoint or scripted examples
- [ ] Fallback recording or screenshots
- [ ] No private data, credentials or unavailable external services in the demo

### 8. Reproducibility package
- [ ] Source code for preprocessing, training, inference and evaluation
- [ ] Configuration files and environment or dependency information
- [ ] Data-split definitions and instructions for obtaining the permitted data
- [ ] Saved predictions, logs and result tables
- [ ] Model checkpoint, or a documented redistribution limitation
- [ ] README describing execution order and expected outputs
- [ ] Presentation slides and demo materials

### Brief items the topic makes inapplicable

- **Large regression errors and poor generation outputs (3.2).** The task is four-way classification, and the decoder scores four label tokens without generating text. False positives and false negatives per label cover the same ground.
- **Interactions with modalities, and acoustic or speaker factors (3.1, 3.2).** One text modality, no audio.
- **Interactions with preprocessing (3.1).** Phrases enter the prompt as released, with no preprocessing variants to interact. Interactions between model components (training loss and decoding) are analyzed.

## Submission checklist (from the brief)

- [ ] Completed primary experiments
- [ ] All comparison systems reported
- [ ] Ablations completed and interpreted
- [ ] Quantitative error analysis with representative examples
- [ ] Comparison with baselines and relevant work
- [ ] Official and secondary metrics reported consistently
- [ ] Repeated-run or statistical reliability analysis where feasible
- [ ] Clear findings, limitations and threats to validity
- [ ] Paper-style LaTeX/Overleaf report
- [ ] Reproducibility package with code, configurations and results
- [ ] Presentation slides
- [ ] Working demo or recorded fallback
- [ ] Consistent references, tables, figures and cross-references
