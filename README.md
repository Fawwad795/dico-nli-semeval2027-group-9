<picture>
  <source media="(prefers-color-scheme: dark) and (max-width: 640px)" srcset="assets/readme/hero-narrow-dark.svg">
  <source media="(max-width: 640px)" srcset="assets/readme/hero-narrow-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/hero-dark.svg">
  <img alt="DiCo-NLI, SemEval-2027 Task 2: a phrase pair swaps order and its label flips from forward to backward entailment, consistent when reversed" src="assets/readme/hero-light.svg" width="1200">
</picture>

Given two short phrases in order, say how they relate: the same meaning, the first entails the second, the second entails the first, or neither. The scorer also shows every pair reversed. A system that answers "forward" one way has to answer "backward" the other, and two of the three official metrics, SoftCons and HardCons, measure exactly that. The third is weighted F1.

[Task page](https://inigolopezgazpio.net/SemEval-2027-Task-2-DiCo-NLI/) · [Data and official scorer](https://github.com/ilopezgazpio/SemEval-2027-Task-2-DiCo-NLI) · Tracks: English, Spanish, Basque and mixed. This project starts with English.

## The four relations

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/relations-dark.svg">
  <img alt="EQUIVALENCE: each phrase entails the other. FORWARD_ENTAILMENT: the first entails the second. BACKWARD_ENTAILMENT: the second entails the first. NEGATIVE_OTHER: neither direction holds." src="assets/readme/relations-light.svg" width="1200">
</picture>

## Results

None yet. The first target is the organizers' pilot baseline on the English dev set, DeBERTa-v3-base at weighted F1 0.75, SoftCons 0.84 and HardCons 0.79, reproduced with our own seed and config. Every number that lands here links to a folder under [experiments/](experiments/) holding its seed, data version, config and command. The dev set is our test set, because the official test set is released in January 2027.

## Assignments

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/timeline-dark.svg">
  <img alt="A1 problem, literature and baseline, due 2 October 2026, in progress. A2 approach and experimental design, due 13 November 2026. A3 experiments, analysis and paper, due 4 December 2026." src="assets/readme/timeline-light.svg" width="1200">
</picture>

Each assignment has a folder under [docs/deliverables/](docs/deliverables/) whose README lists its items and ticks them off as they land.

## Quick start

```
git clone https://github.com/Fawwad795/dico-nli-semeval2027-group-9.git
cd dico-nli-semeval2027-group-9
uv sync
uv run pytest
```

Requires [uv](https://docs.astral.sh/uv/). It installs Python 3.11 if the machine lacks it. Data download, the branch workflow, GPU access and the house rules are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Layout

| Path | Holds |
|---|---|
| [src/dico_nli/](src/dico_nli/) | Library code: data loading, baselines, the method, evaluation glue. Every module lands after its test |
| [tests/](tests/) | `unit`, `integration` and `regression` tiers |
| [experiments/](experiments/) | One folder per run family: config, seed, command, data version, promoted results |
| [datasets/](datasets/) | Metadata and download instructions. Raw data stays out of git |
| [docs/deliverables/](docs/deliverables/) | What is handed in for A1, A2 and A3 |
| [docs/research/](docs/research/) | Literature notes and the reading log |
| [docs/paper/](docs/paper/) | The A3 paper and its figures |

## Team

Muhammad Shaheer Saleh · Ahmad Imran · Syed Fawwad Ahmed · Aqib Raza

Large Language Models course, semester 7, NUST. AI assistance on this repository is disclosed in [docs/governance/ai-usage-disclosure.md](docs/governance/ai-usage-disclosure.md).

---

<p align="center">
  <a href=".python-version">
    <img src="https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white" alt="Python 3.11">
  </a>
  <a href="https://docs.astral.sh/uv/">
    <img src="https://img.shields.io/badge/env-uv-261230?logo=uv&logoColor=white" alt="uv">
  </a>
  <a href="tests/">
    <img src="https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white" alt="pytest">
  </a>
  <a href="https://inigolopezgazpio.net/SemEval-2027-Task-2-DiCo-NLI/">
    <img src="https://img.shields.io/badge/SemEval--2027-Task%202-8250df" alt="SemEval-2027 Task 2">
  </a>
</p>
