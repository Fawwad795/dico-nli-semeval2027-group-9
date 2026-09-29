# llm-project

Semester research project for the Large Language Models course (semester 7).

Topic: **SemEval-2027 Task 2, DiCo-NLI** (Directional-Consistent Fine-Grained Natural Language Inference). Given two short phrases in order, a system says whether they mean the same thing, the first implies the second, the second implies the first, or neither. The catch is consistency: when the pair is shown reversed, the answer must flip accordingly, and the scorer measures that directly.

- Task page: https://inigolopezgazpio.net/SemEval-2027-Task-2-DiCo-NLI/
- Data and official scorer: https://github.com/ilopezgazpio/SemEval-2027-Task-2-DiCo-NLI
- Tracks: English, Spanish, Basque, and a mixed multilingual track. The course project starts with English.

## Team

- Muhammad Shaheer Saleh
- Ahmad Imran
- Syed Fawwad Ahmed
- Aqib Raza

## Assignments

| | Due |
|---|---|
| A1: Problem formulation, literature and baseline | Friday 2 October 2026, 11:59 PM |
| A2: Proposed approach and experimental design | Friday 13 November 2026, 11:59 PM |
| A3: Experiments, analysis and research paper | Friday 4 December 2026, 11:59 PM |

Deliverables live under `docs/deliverables/`. Each folder's README lists that assignment's items.

## Setup

Requires [uv](https://docs.astral.sh/uv/). Python 3.11 is pinned in `.python-version`; uv installs it if missing.

```
uv sync
uv run pytest
```

The panel generator in `scripts/readme/` is left over from a previous project and will be redesigned once the topic exists.
