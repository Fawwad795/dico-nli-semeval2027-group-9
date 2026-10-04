"""Pair-level and length-cue error analysis for DiCo-NLI predictions."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path

import pandas as pd

from .data import LABELS, Instance, group_pairs, reverse_label
from .eda import tokens

PAIR_OUTCOMES = (
    "both_directions_correct",
    "consistent_but_wrong",
    "inconsistent_one_direction_correct",
    "inconsistent_both_directions_wrong",
)


def read_prediction_file(path: Path | str) -> dict[str, str]:
    """Read an official ``instance_id,label`` prediction CSV, rejecting duplicate IDs."""
    with open(path, encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        required = {"instance_id", "label"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("prediction file must contain instance_id and label columns")

        predictions: dict[str, str] = {}
        for row in reader:
            instance_id = (row.get("instance_id") or "").strip()
            label = (row.get("label") or "").strip()
            if not instance_id:
                raise ValueError("prediction file contains an empty instance_id")
            if instance_id in predictions:
                raise ValueError(f"duplicate instance_id {instance_id!r} in prediction file")
            if label not in LABELS:
                raise ValueError(f"unknown prediction label {label!r} for {instance_id!r}")
            predictions[instance_id] = label
    return predictions


def _consistent(first: str, second: str) -> bool:
    try:
        return reverse_label(first) == second
    except ValueError:
        return False


def _cue_status(instance: Instance, word_count1: int, word_count2: int) -> tuple[str, str]:
    if word_count1 > word_count2:
        longer_side = "text1"
    elif word_count2 > word_count1:
        longer_side = "text2"
    else:
        longer_side = "equal"

    if instance.label not in ("FORWARD_ENTAILMENT", "BACKWARD_ENTAILMENT") or longer_side == "equal":
        return longer_side, "uninformative"

    entailing_side = "text1" if instance.label == "FORWARD_ENTAILMENT" else "text2"
    return longer_side, "agrees" if longer_side == entailing_side else "misleads"


def analyze_predictions(
    instances: Sequence[Instance], predictions: Mapping[str, str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return reversible-pair outcomes and per-instance correctness/cue annotations.

    Length is counted with the project's EDA tokenizer. For directional labels, a strictly
    longer entailing phrase means the cue agrees; a longer entailed phrase means it misleads.
    Equal-length pairs and non-directional labels cannot be judged by this cue and are marked
    ``uninformative`` rather than counted as agreement or error.
    """
    instances = list(instances)
    by_id = {instance.instance_id: instance for instance in instances}
    if len(by_id) != len(instances):
        raise ValueError("reference contains duplicate instance_id values")

    unlabeled = [instance.instance_id for instance in instances if instance.label is None]
    if unlabeled:
        raise ValueError(f"reference contains unlabeled instances: {unlabeled[:3]}")

    missing = set(by_id) - set(predictions)
    extra = set(predictions) - set(by_id)
    if missing:
        raise ValueError(f"missing predictions for {len(missing)} instance(s): {sorted(missing)[:3]}")
    if extra:
        raise ValueError(f"predictions contain {len(extra)} unknown instance(s): {sorted(extra)[:3]}")
    invalid = {key: value for key, value in predictions.items() if value not in LABELS}
    if invalid:
        raise ValueError(f"unknown prediction label(s): {invalid}")

    pair_rows = []
    seen_pairs: set[str] = set()
    for instance in instances:
        if not instance.reverse_pair_id or instance.pair_id in seen_pairs:
            continue
        reverse = by_id.get(instance.reverse_pair_id)
        if (
            reverse is None
            or reverse.reverse_pair_id != instance.instance_id
            or reverse.pair_id != instance.pair_id
        ):
            raise ValueError(f"pair {instance.pair_id!r} has a missing or non-reciprocal reverse")
        if reverse_label(instance.label) != reverse.label:
            raise ValueError(f"pair {instance.pair_id!r} has incompatible gold reversal labels")
        seen_pairs.add(instance.pair_id)

        first_prediction = predictions[instance.instance_id]
        reverse_prediction = predictions[reverse.instance_id]
        correct_directions = int(first_prediction == instance.label) + int(reverse_prediction == reverse.label)
        consistent = _consistent(first_prediction, reverse_prediction)
        if correct_directions == 2:
            outcome = "both_directions_correct"
        elif consistent:
            outcome = "consistent_but_wrong"
        elif correct_directions == 1:
            outcome = "inconsistent_one_direction_correct"
        else:
            outcome = "inconsistent_both_directions_wrong"

        pair_rows.append(
            {
                "pair_id": instance.pair_id,
                "instance_id_1": instance.instance_id,
                "instance_id_2": reverse.instance_id,
                "gold_label_1": instance.label,
                "gold_label_2": reverse.label,
                "prediction_1": first_prediction,
                "prediction_2": reverse_prediction,
                "predictions_consistent": consistent,
                "correct_directions": correct_directions,
                "outcome": outcome,
            }
        )

    instance_rows = []
    for instance in instances:
        word_count1 = len(tokens(instance.text1))
        word_count2 = len(tokens(instance.text2))
        longer_side, cue_status = _cue_status(instance, word_count1, word_count2)
        prediction = predictions[instance.instance_id]
        instance_rows.append(
            {
                "instance_id": instance.instance_id,
                "pair_id": instance.pair_id,
                "text1": instance.text1,
                "text2": instance.text2,
                "gold_label": instance.label,
                "predicted_label": prediction,
                "is_correct": prediction == instance.label,
                "word_count1": word_count1,
                "word_count2": word_count2,
                "longer_side": longer_side,
                "cue_status": cue_status,
            }
        )

    return pd.DataFrame(pair_rows), pd.DataFrame(instance_rows)