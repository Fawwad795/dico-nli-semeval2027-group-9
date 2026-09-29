# Working in this repository

Setup, the branch workflow, and the rules we hold ourselves to. Written for the four of us.

## What you need

| Tool | Why | Install |
|---|---|---|
| Git | Version control | [git-scm.com](https://git-scm.com/downloads). On Windows, install Git Bash with it and use it as your shell |
| uv | Python, the virtual environment and the lockfile | Windows PowerShell: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"`. macOS or Linux: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| GitHub access | The repository is private | Accept the collaborator invite. `gh` ([cli.github.com](https://cli.github.com/)) is optional and makes pull requests a one-liner |

You do not need to install Python yourself. `uv sync` reads `.python-version` and fetches 3.11 if the machine lacks it.

## First-time setup

```
git clone https://github.com/Fawwad795/dico-nli-semeval2027-group-9.git
cd dico-nli-semeval2027-group-9
uv sync
uv run pytest
```

`uv sync` creates `.venv/` with the locked dependencies and installs `dico_nli` in editable mode. `uv run pytest` reports "no tests ran" and exits 5 until the first test file exists; that is the expected state, not an error. Prefix commands with `uv run` instead of activating the environment.

## Getting the data

The task data and the official scorer live in the organizers' repository (GPL-3.0). Clone it into `datasets/dico-nli/`, which git ignores:

```
git clone https://github.com/ilopezgazpio/SemEval-2027-Task-2-DiCo-NLI.git datasets/dico-nli
```

Train and dev CSVs are under `final_data/`, one folder per track. The first experiment records the commit hash of that clone in `datasets/dico-nli.json`, and every result cites it. Raw data never enters our git history; [datasets/README.md](datasets/README.md) holds the format, the splits and the scorer command.

Two rules about splits. The dev set is our test set, because the official test set only appears on 10 January 2027. Model selection and tuning use a held-out slice of train, never dev.

## Working on a branch

Nothing lands on `main` directly. Every change goes on its own branch and reaches `main` through a pull request that one teammate has approved.

1. Start from a fresh `main`:
   ```
   git checkout main
   git pull
   git checkout -b a1/eda-english
   ```
   Branch names are `<area>/<topic>`. Areas: `a1`, `a2`, `a3` for assignment work, `exp` for experiments, `docs`, `fix`, `harness`. One self-contained piece of work per branch, so the reviewer can tell what changed from the name.
2. Commit in plain English, one line, under about 60 characters, no prefixes or ticket codes. `Add the English EDA notebook` is good. `feat(eda): init nb` is not.
3. Push and open the pull request:
   ```
   git push -u origin a1/eda-english
   gh pr create --fill --base main
   ```
   Without `gh`, open the pull request on GitHub; it will offer the branch you just pushed.
4. A teammate reviews and approves. The author squash-merges and deletes the branch.

Unrelated changes never share a branch or a commit. If you notice a second problem while fixing the first, note it and open a second branch.

## Where things go

| Path | Holds |
|---|---|
| `src/dico_nli/` | Library code. Every module except `__init__.py` gets its test in `tests/<tier>/test_<stem>.py` before it exists |
| `tests/unit/`, `tests/integration/`, `tests/regression/` | One component on synthetic input; components wired together on a small fixture; bugs an experiment found, pinned |
| `experiments/YYYY-MM-DD-<slug>/` | Config, seed, exact command, data commit hash, and the promoted tables, metric JSON and figures a deliverable cites |
| `artifacts/` | Raw run outputs, checkpoints, caches. Ignored by git |
| `datasets/` | Metadata and download instructions only |
| `notebooks/` | Exploration. Strip outputs before committing. Anything a reported number depends on moves into the package or `experiments/` |
| `docs/deliverables/a1-*/`, `a2-*/`, `a3-*/` | What is handed in, with a README that ticks off the items |
| `docs/research/` | Literature notes, one file per paper or theme |
| `docs/paper/` | The A3 paper source and figures |
| `scripts/` | Reusable tooling, including the README panel generator |

Detailed conventions live in `.claude/reference/` (`testing.md`, `architecture.md`, `research-decisions.md`). They are written for the coding assistant but read fine as plain documentation, and when they disagree with a `docs/` file, fix the disagreement.

## Rules that do not bend

- **Every reported number comes from a run we can repeat.** Seed, data commit hash, config and the exact command sit in the experiment folder next to the result. No projected or illustrative numbers, anywhere.
- **Results are reported as measured**, including when our method loses to the baseline. Nothing is ever tuned against the instances used to score it.
- **Tests before modules.** A `.py` under `src/dico_nli/` is written after a failing test for it exists. Tiers and naming: [`.claude/reference/testing.md`](.claude/reference/testing.md).
- **Adding a dependency is a team decision.** `uv add <package>` changes the shared `uv.lock` that everyone syncs from. Say so in the pull request and commit `pyproject.toml` and `uv.lock` together.
- **Plots are saved as PDF**, so they drop into the paper without resampling. The professor asked for this.
- **AI assistance is disclosed** in [docs/governance/ai-usage-disclosure.md](docs/governance/ai-usage-disclosure.md), one dated row per material artifact. It is never mentioned in commit messages or pull requests.

## GPU runs

Anything larger than the encoder baseline runs on [Modal](https://modal.com). Each of us holds one Starter workspace with $30 of free compute a month and no card; that is four workspaces for four people, one each.

```
modal token new
```

That logs your machine into your own workspace. Launch commands, the fetch command for results, and the quirks that cost us time in the past are in [`.claude/reference/commands.md`](.claude/reference/commands.md) and [`.claude/reference/pitfalls.md`](.claude/reference/pitfalls.md). `modal` is not a project dependency yet; adding it follows the dependency rule above. A free Colab T4 covers the encoder baseline if Modal is unavailable.

## Windows notes

- Use Git Bash, not PowerShell, for the commands in this file. Shell scripts are forced to LF by `.gitattributes`, so `core.autocrlf=true` is safe.
- Any Python whose output is redirected to a file needs `PYTHONIOENCODING=utf-8` in front of it, or the first non-ASCII character it prints kills it with a `charmap` error while the shell still reports success.
- If you rename or move the project folder, delete `.venv/` and run `uv sync` again. The launchers inside it embed the old absolute path and `uv run pytest` fails with a "trampoline" error until you do.

## Using Claude Code here

Optional. The repository ships a harness under `.claude/` that the coding assistant reads on start: the project rules in `CLAUDE.md`, a reference library, and hooks that refuse edits on `main`, refuse a module before its test, and refuse any git write. Claude never commits or pushes; it hands you the commands and you run them. The hooks need `python` and `node` on your PATH. `node .claude/scripts/doctor.mjs` checks that the harness is healthy and `python .claude/scripts/test-hooks.py` runs the hook tests. Neither touches the project's own tests.
