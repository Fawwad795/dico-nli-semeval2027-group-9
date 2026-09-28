# Tech stack

> Non-default picks and why. Defaults that need no justification are not listed.

| Pick | Why |
|---|---|
| Python 3.11, pinned in `.python-version` | One interpreter across four machines (Windows, possibly macOS); uv installs it if missing |
| uv as the environment and dependency manager | One lockfile (`uv.lock`) every teammate syncs from; `uv run` avoids activating anything |
| `src/` layout with setuptools (`pyproject.toml`) | Tests import the installed package, not the working directory, so a missing `__init__.py` or path hack fails early |
| pytest as the only dev dependency | The tests-first hook needs a runner from day one; nothing else is justified before the topic |
| Shell scripts and YAML forced to LF (`.gitattributes`) | Git Bash on Windows breaks on CRLF scripts; patch files stay byte-exact |

Not chosen yet, decided with the topic (`research-decisions.md`): model access (API, local via Ollama, or GPU), data and evaluation libraries, experiment tracking.
