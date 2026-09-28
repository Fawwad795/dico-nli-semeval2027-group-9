# Commands

> Build, dev, and test commands, and the boundary of what runs in-session.

## Project

| Command | Does |
|---|---|
| `uv sync` | Create or update `.venv/` from `pyproject.toml` and `uv.lock` (Python 3.11 from `.python-version`) |
| `uv run pytest` | Run the whole suite (`testpaths = ["tests"]`, `pythonpath = ["src"]`). Exit 5 with "no tests ran" while the suite is empty |
| `uv run pytest tests/unit` | One tier only (`unit`, `integration`, `regression`) |
| `uv add <package>` | Adds a dependency to the shared lockfile. Ask first; see CLAUDE.md |

## Harness

| Command | Does |
|---|---|
| `node .claude/scripts/doctor.mjs` | Harness health: settings, SessionStart hook, skill frontmatter, reference files, template markers. Exit 1 on FAIL |
| `python .claude/scripts/test-hooks.py` | Regression tests for the four PreToolUse hooks. Prints `ALL PASS` |
| `bash .claude/scripts/context-weight.sh` | Approximate always-loaded context weight |
| `python scripts/readme/build_assets.py` | Previous project's README panel generator. Stale; do not run until it is redesigned for the new topic |

## Runs only the user can execute

Nothing yet. When the topic picks a model provider or a GPU path, record here which commands need an API key, paid inference, or a GPU, and how the user runs them. Until then, anything needing those is out of reach in-session and gets flagged, never claimed.
