# Research decisions

> Dated design decisions with reasons, newest at the bottom, plus the list of things still open. A decision here is the reason a later session does not re-argue it.

## 2026-09-28: repository layout and placeholder package

Decided before the topic, so the harness and the assignment folders exist from day one:

- One Python package, `src/llm_project/`, guarded by the tests-first hook. The name is a placeholder; it is renamed in one commit once the topic is chosen (package directory, `pyproject.toml` name, the hook's `GUARDED` pattern, `test-hooks.py` fixtures, `testing.md`).
- Three test tiers, `unit`, `integration`, `regression`. No topic-specific tier until the topic needs one.
- Deliverables live under `docs/deliverables/<assignment slug>/`; research notes under `docs/research/`; the paper under `docs/paper/`.
- `experiments/` is committed and holds config, seed, command, and promoted results; `artifacts/` is gitignored and holds raw outputs; `datasets/` commits metadata only.
- Branch areas are `a1`, `a2`, `a3`, `harness`, `fix`, `docs`, `exp`, mirroring the assignments.
- pytest is the only dependency until the topic justifies more. Every addition is a team decision because `uv.lock` is shared.

Why: the harness rules (tests first, plan first, reproducible runs) only bite if the paths they guard exist before the first line of research code.

## 2026-09-29: topic is SemEval-2027 Task 2, DiCo-NLI

Chosen from the SemEval-2027 task list and the ICASSP 2027 grand challenges after reading every task page.

- **What it is.** Given an ordered phrase pair, predict EQUIVALENCE, FORWARD_ENTAILMENT, BACKWARD_ENTAILMENT, or NEGATIVE_OTHER. The pair also appears reversed, and the metrics SoftCons and HardCons score whether the two predictions are compatible. Tracks: English, Spanish, Basque, mixed. Course scope starts with English.
- **Why this one.** Train and dev data were downloadable on the day of the decision (3,042 train, 660 dev per track, CSV), the official scorer ships in the repository, and the organizers publish pilot baselines (DeBERTa-v3-base: weighted F1 0.75, SoftCons 0.84, HardCons 0.79; decoder-only OPT-125M far lower at 0.61). So A1's baseline is a reproduction with a known target. The consistency requirement is a real, measurable LLM-reliability question that fits two months. The agentic, tool-calling, steering, retrieval, and multimodal tasks are where most teams will go; a phrase-level NLI task with a Basque track is not.
- **Rejected.** RETECO (1.67M-document corpus, obvious RAG pick), CLaS (must run Llama-3.1-8B, evaluation on the organizers' side, no dates), AgentRisk (no data), VAKRA (executable tool environments), MMCultureQA and Multimodal Framing (audio or images), StereoQueerEval (data agreement, most obvious classification task), Par-PARSEME (ranked by manual native-speaker judgment in 13 languages the team cannot reproduce), ComPartMENT and Semantic Change (data and metrics unverifiable on CodaBench at decision time). Every ICASSP challenge is signal processing.
- **Evaluation split.** The official test set is released 10 January 2027, after A3. The dev set is the course test set; model selection uses a held-out slice of train, never dev. Stated in A1.
- **Research question, working form.** How can a decoder LLM be made direction-consistent on fine-grained NLI, and at what cost in weighted F1, compared with a fine-tuned encoder? Candidate mechanisms for A2: pair-swap augmentation, a consistency loss, symmetric prompting, LoRA on a small instruct model. The exact wording is settled in A1.
- **Compute.** Modal is primary: Starter plan, $30 free compute per workspace per month, no card; one workspace per teammate, so four accounts held by four people and no multi-accounting. Azure for Students was checked and rejected: the subscription is capped at 3 vCPUs with no GPU quota and no quota increases (Microsoft staff, 2025), and self-service sign-up from Pakistan appears blocked (Microsoft Q&A, Nov 2025 and Feb 2026); NUST has no public institutional arrangement. Free Colab T4 is the fallback for the encoder baseline. Modal for Academics (up to $10k) is worth one application, not a plan.
- **Professor's working notes** (black-box then white-box, five-facet EDA, ML and DL baselines, PDF plots, Overleaf report by email) are recorded in `assignments.md` and shape A1.

## 2026-09-29: package renamed to `dico_nli`

The placeholder `llm_project` became `src/dico_nli/` (distribution name `dico-nli`) before any module existed, so no test path or import ever had to change. Done as one unit: package directory, `pyproject.toml` and `uv.lock`, the tests-first hook's `GUARDED` pattern and its fixtures in `test-hooks.py`, and every reference to the path in the kernel, the reference library, and the READMEs. The GitHub repository is `dico-nli-semeval2027-group-9`; the import name is the short form because the group number is not part of the code.

## Open, to decide with A1

- Exact research question and hypothesis wording.
- The ML baseline's feature set and the DL baseline's exact config (model, seed policy, epochs), with three seeds if compute allows.
- Which decoder LLM(s) for the method: open-weight, small enough for an A10 or A100 LoRA run.
- Whether to add Spanish or Basque after English, and when.
- Dependencies to add (`modal`, `transformers`, `datasets`, `scikit-learn`, plotting): each a team decision under the dependency rule.
- Which A1 to A3 items the topic makes inapplicable, and the justification to record in each deliverable README.
