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

Anything on a GPU. The path is Modal (decision: `research-decisions.md`, 2026-09-29). Claude prepares the Modal script and the exact command; a teammate launches it from their own workspace and fetches the results.

| Command | Does |
|---|---|
| `modal token new` | One-time login for a teammate's own workspace |
| `PYTHONIOENCODING=utf-8 uv run modal run --detach scripts/modal/<script>.py::<entrypoint> ...` | Launch a run. `--detach` on anything longer than a few minutes, the encoding variable on anything whose output is logged (`pitfalls.md`) |
| `modal app list`, `modal app logs <app-id>` | State and logs of a detached run |
| `modal volume get <vol> <run_id> <existing-local-parent>` | Fetch results; the local parent must already exist (`pitfalls.md`) |

`modal` is not a project dependency yet. Adding it (`uv add --dev modal`) is a team decision under the dependency rule; until then the commands above are the plan, not something that runs.

CPU-only work (the encoder baseline on a few thousand pairs, the official scorer, EDA) runs locally or on a free Colab T4 and needs none of this.
