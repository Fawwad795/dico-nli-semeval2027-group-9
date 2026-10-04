"""Run records: the folder under ``experiments/`` that every reported number traces back to.

A run folder holds ``config.json`` (seed, track, data commit, repository commit and whether
the tree was dirty, the exact command), the predictions, the official scorer's own output per
system, and ``results.md``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import date
from pathlib import Path
from typing import Mapping

from .data import REPO_ROOT
from .scoring import Scores

EXPERIMENTS_ROOT = REPO_ROOT / "experiments"
DATASET_RECORD = REPO_ROOT / "datasets" / "dico-nli.json"
HAND_WRITTEN = {"findings.md"}  # survives an overwrite; everything else in a run folder is regenerated


def data_commit(record: Path = DATASET_RECORD) -> str:
    """The task-repository commit recorded in ``datasets/dico-nli.json``."""
    return json.loads(record.read_text(encoding="utf-8"))["commit"]


def repo_state(cwd: Path = REPO_ROOT) -> tuple[str, bool | None]:
    """``(HEAD commit, tree is dirty)``, or ``("unknown", None)`` outside a git checkout.

    A dirty flag is recorded because a run made from uncommitted code cannot be traced
    to the commit alone.
    """
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout

    try:
        commit = git("rev-parse", "HEAD").strip()
        dirty = bool(git("status", "--porcelain").strip())
    except (OSError, subprocess.CalledProcessError):
        return "unknown", None
    return commit, dirty


def experiment_dir(
    slug: str, root: Path = EXPERIMENTS_ROOT, day: date | None = None, overwrite: bool = False
) -> Path:
    """``experiments/YYYY-MM-DD-<slug>/``, created if missing.

    A folder that already holds a ``config.json`` is a recorded run; reusing it needs
    ``overwrite=True``, which empties the folder first so nothing from the earlier run
    survives into the new record. ``findings.md`` is written by a person, not by the run,
    and is kept.
    """
    path = root / f"{(day or date.today()).isoformat()}-{slug}"
    if (path / "config.json").exists():
        if not overwrite:
            raise FileExistsError(f"{path} already holds a recorded run; pass overwrite to replace it")
        for entry in path.iterdir():
            if entry.name in HAND_WRITTEN:
                continue
            shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_config(
    directory: Path | str, *, seed: int, track: int, command: str, extra: Mapping | None = None
) -> Path:
    commit, dirty = repo_state()
    config = {
        "seed": seed,
        "track": track,
        "data_commit": data_commit(),
        "repo_commit": commit,
        "repo_dirty": dirty,
        "command": command,
        **(extra or {}),
    }
    path = Path(directory) / "config.json"
    path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_results_table(directory: Path | str, rows: Mapping[str, Scores], *, title: str) -> Path:
    lines = [f"# {title}", "", "| System | Weighted F1 | SoftCons | HardCons |", "|---|---|---|---|"]
    for name, scores in rows.items():
        lines.append(f"| {name} | {scores.weighted_f1:.3f} | {scores.soft_cons:.3f} | {scores.hard_cons:.3f} |")
    lines += [
        "",
        "Scores are the official scorer's output; a system's full report is under `scores/<system>/`, "
        "and a summary row (a mean over seeds) points to its table instead. "
        "Seed, data commit and command: `config.json`.",
        "",
    ]
    path = Path(directory) / "results.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
