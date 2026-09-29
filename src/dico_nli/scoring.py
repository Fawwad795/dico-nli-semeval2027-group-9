"""The official prediction format and the official scorer, run exactly as CodaBench runs it.

The scorer is GPL code that lives in the ignored clone under ``datasets/dico-nli``; it is
invoked as a subprocess (``python -m evaluation_functions``) rather than imported, so the
numbers reported here are the numbers the competition platform would produce.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from .data import REPO_ROOT

SCORER_ROOT = REPO_ROOT / "datasets" / "dico-nli"


class ScoringError(RuntimeError):
    """The official scorer rejected the submission or could not run."""


@dataclass(frozen=True)
class Scores:
    weighted_f1: float
    soft_cons: float
    hard_cons: float
    report_path: Path

    @classmethod
    def from_report(cls, path: Path) -> "Scores":
        report = json.loads(path.read_text(encoding="utf-8"))
        return cls(report["weighted_f1"], report["soft_cons"], report["hard_cons"], path)

    def as_dict(self) -> dict:
        data = asdict(self)
        data["report_path"] = str(self.report_path)
        return data


def write_predictions(path: Path | str, predictions: Mapping[str, str]) -> Path:
    """Write ``instance_id,label`` rows in the given order, LF-terminated."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["instance_id", "label"])
        writer.writerows(predictions.items())
    return path


def score(
    gold_csv: Path | str, predictions_csv: Path | str, output_dir: Path | str, scorer_root: Path = SCORER_ROOT
) -> Scores:
    """Run the official scorer; ``scores.json`` and ``scores.txt`` land in ``output_dir``."""
    if not (scorer_root / "evaluation_functions" / "__main__.py").exists():
        raise ScoringError(f"official scorer not found under {scorer_root}; see datasets/dico-nli.json")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, "-m", "evaluation_functions",
        "--gold", str(Path(gold_csv).resolve()),
        "--predictions", str(Path(predictions_csv).resolve()),
        "--output-dir", str(output_dir.resolve()),
    ]
    completed = subprocess.run(
        command,
        cwd=scorer_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip() or f"scorer exited with {completed.returncode}"
        raise ScoringError(message)
    return Scores.from_report(output_dir / "scores.json")
