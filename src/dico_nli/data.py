"""Reading the DiCo-NLI CSVs, grouping instances by source pair, seeded grouped splits.

The id columns stay on ``Instance`` for bookkeeping and scoring only. Every ``__flipped``
instance is the reversal of an ``__original`` one and ``NEGATIVE_OTHER`` instances have no
flipped twin, so ``instance_id`` leaks the label: nothing that builds model input may read it.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

LABELS: tuple[str, ...] = ("EQUIVALENCE", "FORWARD_ENTAILMENT", "BACKWARD_ENTAILMENT", "NEGATIVE_OTHER")
REVERSIBLE_LABELS: tuple[str, ...] = LABELS[:3]
_REVERSE = {
    "EQUIVALENCE": "EQUIVALENCE",
    "FORWARD_ENTAILMENT": "BACKWARD_ENTAILMENT",
    "BACKWARD_ENTAILMENT": "FORWARD_ENTAILMENT",
}

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "datasets" / "dico-nli" / "final_data"


@dataclass(frozen=True)
class Instance:
    instance_id: str
    pair_id: str
    text1: str
    text2: str
    label: str | None
    reverse_pair_id: str | None = None
    text1_lang: str = "en"
    text2_lang: str = "en"


def reverse_label(label: str) -> str:
    """The official reversal operator; NEGATIVE_OTHER has no deterministic reverse."""
    try:
        return _REVERSE[label]
    except KeyError:
        raise ValueError(f"label {label!r} has no deterministic reverse") from None


def read_instances(path: Path | str) -> list[Instance]:
    """Read a participant, reference, or unlabeled CSV. Missing columns become None."""
    path = Path(path)
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    instances = []
    for row in rows:
        label = (row.get("label") or "").strip() or None
        if label is not None and label not in LABELS:
            raise ValueError(f"unknown label {label!r} in {path}")
        instances.append(
            Instance(
                instance_id=row["instance_id"],
                pair_id=row["pair_id"],
                text1=row["text1"],
                text2=row["text2"],
                label=label,
                reverse_pair_id=(row.get("reverse_pair_id") or "").strip() or None,
                text1_lang=row.get("text1_lang", "en"),
                text2_lang=row.get("text2_lang", "en"),
            )
        )
    return instances


def load_reference(track: int, split: str, root: Path = DATA_ROOT) -> list[Instance]:
    """The organizers' reference file for a track and split (``train`` or ``dev``)."""
    if split not in ("train", "dev"):
        raise ValueError(f"split must be 'train' or 'dev', got {split!r}")
    return read_instances(root / split / f"dico_nli_{split}_track{track}_reference.csv")


def group_pairs(instances: Iterable[Instance]) -> dict[str, list[Instance]]:
    """Instances by ``pair_id``: both directions of a reversible pair, or one negative."""
    groups: dict[str, list[Instance]] = {}
    for instance in instances:
        groups.setdefault(instance.pair_id, []).append(instance)
    return groups


def grouped_split(
    instances: Sequence[Instance], holdout_fraction: float, seed: int
) -> tuple[list[Instance], list[Instance]]:
    """Seeded split by source pair, so both directions of a pair land on the same side.

    The held-out size is ``round(holdout_fraction * number_of_pairs)``, at least one pair.
    """
    if not 0 < holdout_fraction < 1:
        raise ValueError("holdout_fraction must be strictly between 0 and 1")
    pair_ids = sorted(group_pairs(instances))
    random.Random(seed).shuffle(pair_ids)
    held_ids = set(pair_ids[: max(1, round(holdout_fraction * len(pair_ids)))])
    train = [i for i in instances if i.pair_id not in held_ids]
    held = [i for i in instances if i.pair_id in held_ids]
    return train, held
