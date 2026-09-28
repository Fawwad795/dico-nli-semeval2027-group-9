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

Why: the harness rules (tests first, plan first, reproducible runs) only bite if the paths they guard exist before the first line of research code. Placeholders are marked `[TOPIC-TBD]` so a later session finds them with one grep.

## Open, to decide with the topic

- Research question or hypothesis, and the one-paragraph problem statement.
- Dataset(s): source, licence, size, splits, and whether a local copy is allowed.
- Baseline(s) to reproduce first, and the paper each comes from.
- Evaluation measures and the statistical treatment (seeds, confidence intervals, significance).
- Model access: hosted API, local via Ollama, or a GPU run; the budget and who holds the key.
- Seed and split policy, and where the versioned config lives.
- Package rename from `llm_project` to a topic name.
- Which A1 to A3 items the topic makes inapplicable, and the justification to record in each deliverable README.
