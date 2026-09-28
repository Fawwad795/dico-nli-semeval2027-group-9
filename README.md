# llm-project

Semester research project for the Large Language Models course (semester 7).

Topic: [TOPIC-TBD]. The topic is not chosen yet; this README is updated when it is.

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
