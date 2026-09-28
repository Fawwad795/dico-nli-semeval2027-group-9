# Architecture

> Package layout, directory map, and data flow. The data flow is a placeholder until the topic is chosen.

## Package

`src/llm_project/` is the only Python package. It is empty apart from `__init__.py` and will be renamed once the topic is chosen (see `research-decisions.md`). Every module under it is guarded by the tests-first hook (`testing.md`).

Data flow: **[TOPIC-TBD]**. Fill in once the research question exists: what goes in (dataset, prompts, model), what the baseline does, what the proposed method changes, and what comes out (metrics, error analysis).

## Directory map

| Path | Holds | In git? |
|---|---|---|
| `src/llm_project/` | Library code: data loading, baselines, the proposed method, evaluation | yes |
| `tests/{unit,integration,regression}/` | pytest tiers, see `testing.md` | yes |
| `experiments/` | One folder per run family: config, seed, command, and the promoted results that a report cites | yes |
| `datasets/` | Metadata, licences, download instructions, split definitions. Never raw data | metadata only |
| `artifacts/` | Raw run outputs, model dumps, caches | no (gitignored) |
| `notebooks/` | Exploration only; anything a report depends on moves to `src/` or `experiments/` | yes, outputs stripped |
| `docs/deliverables/a{1,2,3}-*/` | What is handed in for each assignment | yes |
| `docs/research/` | Literature notes, reading log, related-work summaries | yes |
| `docs/paper/` | The A3 paper source and its figures | yes |
| `docs/governance/` | AI usage disclosure | yes |
| `scripts/` | Reusable tooling promoted from `.tmp/` (`readme/` is the previous project's panel generator, stale until redesigned) | yes |

## Where results live

A number that appears in a deliverable must trace to a folder under `experiments/` that records the seed, data version, config, and the exact command. Raw outputs stay in `artifacts/`; the promoted summary (a table, a JSON of metrics, a figure) is committed next to its config.
