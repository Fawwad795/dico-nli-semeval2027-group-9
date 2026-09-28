# Testing

> Test tiers, naming, and the tests-before-core-modules rule.

Adopted 2026-09-28. No test files exist yet; each lands with the module it tests, and
before it.

## The rule

A core module never lands before its test. Guarded: every `.py` under
`src/llm_project/`, at any depth, except `__init__.py` and `conftest.py`. Write the test
first, watch it fail, then write the module. `.claude/hooks/require-tests-first.py`
refuses a Write, Edit, or Bash redirect to a guarded module until a matching test file
exists under `tests/` and contains a `def test_`. Naming: `test_<module stem>*.py`
anywhere under `tests/`, tokens in order; `tokenizer.py` is satisfied by
`tests/unit/test_tokenizer.py` or `tests/integration/test_tokenizer_roundtrip.py`, and
`base.py` is not satisfied by `test_database.py`.

Code under `scripts/` and `notebooks/` is not mechanically checked. Anything a reported
number depends on moves into the package, where it is.

## Tiers

| Directory | Holds | Example file names |
|---|---|---|
| `tests/unit/` | One component in isolation on synthetic input: a loader, a metric, a prompt builder, a parser | `test_loader.py`, `test_metrics.py`, `test_prompt.py` |
| `tests/integration/` | Components wired together end to end on a small fixture: baseline run on ten samples, method run on ten samples | `test_baseline_end_to_end.py`, `test_method_end_to_end.py` |
| `tests/regression/` | Every bug an experiment found, pinned so it never returns | `test_known_bugs.py` |

## Conventions

- Tests are deterministic: fixed seeds, no network, no live model. A test that needs a
  model uses a recorded or stub implementation behind the model interface.
- Fixtures are small and committed under `tests/fixtures/`; a test never downloads data.
- A regression test names, in its docstring, the experiment or report that found the bug.
- Two test files with the same basename in different subdirectories collide under
  pytest's default import mode; give each such subdirectory an `__init__.py`
  (`pitfalls.md`).
- Runner: pytest with `testpaths = ["tests"]` and `pythonpath = ["src"]` from
  `pyproject.toml`; `uv run pytest`. See `commands.md`.
