"""Majority and seeded random baselines: the floor every real system has to clear."""

from __future__ import annotations

import random
from collections import Counter
from typing import Iterable

from ..data import LABELS, Instance


def majority_label(train: Iterable[Instance]) -> str:
    """The most frequent training label; ties go to the earlier label in ``LABELS``.

    The tie-break matters: track-1 train has 881 FORWARD_ENTAILMENT and 881
    BACKWARD_ENTAILMENT, so the majority baseline predicts FORWARD_ENTAILMENT there.
    """
    counts = Counter(i.label for i in train if i.label is not None)
    if not counts:
        raise ValueError("no labelled instances to take a majority from")
    return max(LABELS, key=lambda label: (counts.get(label, 0), -LABELS.index(label)))


def predict_majority(train: Iterable[Instance], targets: Iterable[Instance]) -> dict[str, str]:
    label = majority_label(train)
    return {t.instance_id: label for t in targets}


def predict_random(targets: Iterable[Instance], seed: int) -> dict[str, str]:
    """A uniform label per target from ``random.Random(seed)``, in target order."""
    rng = random.Random(seed)
    return {t.instance_id: rng.choice(LABELS) for t in targets}
