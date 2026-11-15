"""Paired significance tests and subgroup tags for reliability analysis."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from typing import TypeAlias

import numpy as np
import pandas as pd

from .analysis import analyze_predictions
from .data import LABELS, REVERSIBLE_LABELS, Instance, group_pairs, reverse_label
from .eda import tokens

Metric: TypeAlias = Callable[
    [Mapping[str, str], Mapping[str, str], Mapping[str, list[Instance]]], float
]


def _check_labels(gold: Mapping[str, str], predictions: Mapping[str, str]) -> None:
    if set(gold) != set(predictions):
        missing = set(gold) - set(predictions)
        extra = set(predictions) - set(gold)
        raise ValueError(
            f"prediction ids differ from gold: {len(missing)} missing, {len(extra)} extra"
        )
    invalid = (set(gold.values()) | set(predictions.values())) - set(LABELS)
    if invalid:
        raise ValueError(f"unknown labels: {sorted(invalid)}")


def _label_f1(gold: Mapping[str, str], predictions: Mapping[str, str], label: str) -> float:
    true_positive = sum(
        gold[instance_id] == label and predictions[instance_id] == label
        for instance_id in gold
    )
    false_positive = sum(
        gold[instance_id] != label and predictions[instance_id] == label
        for instance_id in gold
    )
    false_negative = sum(
        gold[instance_id] == label and predictions[instance_id] != label
        for instance_id in gold
    )
    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else 0.0
    )
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def weighted_f1(
    gold: Mapping[str, str],
    predictions: Mapping[str, str],
    _pairs: Mapping[str, list[Instance]] | None = None,
) -> float:
    """Return label F1 weighted by gold-label support."""
    _check_labels(gold, predictions)
    if not gold:
        raise ValueError("cannot score zero instances")
    return sum(
        sum(value == label for value in gold.values())
        / len(gold)
        * _label_f1(gold, predictions, label)
        for label in LABELS
    )


def macro_f1(
    gold: Mapping[str, str],
    predictions: Mapping[str, str],
    _pairs: Mapping[str, list[Instance]] | None = None,
) -> float:
    """Return the unweighted mean F1 over labels present in gold."""
    _check_labels(gold, predictions)
    present = [label for label in LABELS if label in gold.values()]
    if not present:
        raise ValueError("cannot score zero instances")
    return sum(_label_f1(gold, predictions, label) for label in present) / len(present)


def _reversible_pairs(
    pair_groups: Mapping[str, list[Instance]],
) -> list[tuple[Instance, Instance]]:
    return [tuple(members) for members in pair_groups.values() if len(members) == 2]


def soft_cons(
    gold: Mapping[str, str],
    predictions: Mapping[str, str],
    pair_groups: Mapping[str, list[Instance]],
) -> float:
    """Return prediction compatibility under the official reversal operator."""
    _check_labels(gold, predictions)
    pairs = _reversible_pairs(pair_groups)
    if not pairs:
        return 0.0
    compatible = 0
    for first, second in pairs:
        first_prediction = predictions[first.instance_id]
        compatible += (
            first_prediction in REVERSIBLE_LABELS
            and predictions[second.instance_id] == reverse_label(first_prediction)
        )
    return compatible / len(pairs)


def hard_cons(
    gold: Mapping[str, str],
    predictions: Mapping[str, str],
    pair_groups: Mapping[str, list[Instance]],
) -> float:
    """Return the share of reversible pairs correct in both directions."""
    _check_labels(gold, predictions)
    pairs = _reversible_pairs(pair_groups)
    if not pairs:
        return 0.0
    return sum(
        predictions[first.instance_id] == gold[first.instance_id]
        and predictions[second.instance_id] == gold[second.instance_id]
        for first, second in pairs
    ) / len(pairs)


METRICS: dict[str, Metric] = {
    "weighted_f1": weighted_f1,
    "macro_f1": macro_f1,
    "soft_cons": soft_cons,
    "hard_cons": hard_cons,
}


def _metric_function(metric: str | Metric) -> Metric:
    if callable(metric):
        return metric
    try:
        return METRICS[metric]
    except KeyError:
        raise ValueError(f"unknown metric {metric!r}; choose from {sorted(METRICS)}") from None


def bootstrap_difference(
    gold: Sequence[Instance],
    predictions_a: Mapping[str, str],
    predictions_b: Mapping[str, str],
    metric: str | Metric,
    n_resamples: int = 10_000,
    seed: int = 13,
) -> tuple[float, float, float]:
    """Return A minus B and its paired-bootstrap 95% percentile interval.

    Source-pair groups are sampled with replacement. Both ordered instances of a
    reversible pair therefore stay together, and every repeated draw receives new
    identifiers so its multiplicity contributes to the resampled metric.
    """
    instances = list(gold)
    if n_resamples <= 0:
        raise ValueError("n_resamples must be positive")
    by_id = {instance.instance_id: instance for instance in instances}
    if len(by_id) != len(instances):
        raise ValueError("gold contains duplicate instance ids")
    if any(instance.label is None for instance in instances):
        raise ValueError("gold contains unlabeled instances")
    gold_labels = {instance_id: instance.label for instance_id, instance in by_id.items()}
    _check_labels(gold_labels, predictions_a)
    _check_labels(gold_labels, predictions_b)
    pairs = group_pairs(instances)
    if not pairs:
        raise ValueError("gold contains no source pairs")

    metric_function = _metric_function(metric)
    observed = metric_function(gold_labels, predictions_a, pairs) - metric_function(
        gold_labels, predictions_b, pairs
    )
    pair_ids = sorted(pairs)
    rng = np.random.default_rng(seed)
    differences = np.empty(n_resamples, dtype=float)

    for resample_index in range(n_resamples):
        sampled_gold: dict[str, str] = {}
        sampled_a: dict[str, str] = {}
        sampled_b: dict[str, str] = {}
        sampled_pairs: dict[str, list[Instance]] = {}
        for draw_index in rng.integers(0, len(pair_ids), size=len(pair_ids)):
            source_pair_id = pair_ids[int(draw_index)]
            sampled_pair_id = f"sample-{resample_index}-{len(sampled_pairs)}"
            sampled_members = []
            for member_index, instance in enumerate(pairs[source_pair_id]):
                sampled_id = f"{sampled_pair_id}-{member_index}"
                sampled_gold[sampled_id] = gold_labels[instance.instance_id]
                sampled_a[sampled_id] = predictions_a[instance.instance_id]
                sampled_b[sampled_id] = predictions_b[instance.instance_id]
                sampled_members.append(
                    Instance(
                        instance_id=sampled_id,
                        pair_id=sampled_pair_id,
                        text1=instance.text1,
                        text2=instance.text2,
                        label=instance.label,
                    )
                )
            sampled_pairs[sampled_pair_id] = sampled_members
        differences[resample_index] = metric_function(
            sampled_gold, sampled_a, sampled_pairs
        ) - metric_function(sampled_gold, sampled_b, sampled_pairs)

    low, high = np.percentile(differences, [2.5, 97.5])
    return float(observed), float(low), float(high)


def mcnemar_exact(
    gold: Mapping[str, str],
    predictions_a: Mapping[str, str],
    predictions_b: Mapping[str, str],
) -> tuple[int, int, float]:
    """Return discordant counts and the exact two-sided McNemar p-value.

    Counts are ``(A wrong/B right, A right/B wrong)``.
    """
    _check_labels(gold, predictions_a)
    _check_labels(gold, predictions_b)
    a_wrong_b_right = sum(
        predictions_a[key] != value and predictions_b[key] == value
        for key, value in gold.items()
    )
    a_right_b_wrong = sum(
        predictions_a[key] == value and predictions_b[key] != value
        for key, value in gold.items()
    )
    discordant = a_wrong_b_right + a_right_b_wrong
    if discordant == 0:
        return 0, 0, 1.0
    smaller = min(a_wrong_b_right, a_right_b_wrong)
    p_value = min(
        1.0,
        2.0
        * sum(math.comb(discordant, count) for count in range(smaller + 1))
        / 2**discordant,
    )
    return a_wrong_b_right, a_right_b_wrong, p_value


def tag_subgroups(
    dev_instances: Sequence[Instance],
    train_instances: Sequence[Instance],
    length_bucket_boundaries: tuple[int, int] | None = None,
) -> pd.DataFrame:
    """Tag dev rows by train overlap, pair length, and the existing length cue.

    Overlap and length are defined on the unordered source pair, so both directions
    receive the same tag. Default length cutoffs are the nearest observed values to
    the 33rd and 67th percentiles of unique dev source pairs.
    """
    dev = list(dev_instances)
    train_phrases = {
        phrase.lower()
        for instance in train_instances
        for phrase in (instance.text1, instance.text2)
    }
    gold_predictions = {instance.instance_id: instance.label for instance in dev}
    _, analysis = analyze_predictions(dev, gold_predictions)
    cue_by_id = analysis.set_index("instance_id")["cue_status"].to_dict()

    pair_lengths = {
        pair_id: len(tokens(members[0].text1)) + len(tokens(members[0].text2))
        for pair_id, members in group_pairs(dev).items()
    }
    if not pair_lengths:
        raise ValueError("dev contains no instances")
    if length_bucket_boundaries is None:
        low, high = np.quantile(
            list(pair_lengths.values()), [1 / 3, 2 / 3], method="nearest"
        ).astype(int)
        if low == high:
            low, high = low - 1, high
    else:
        low, high = length_bucket_boundaries
    if low >= high:
        raise ValueError("length bucket boundaries must be strictly increasing")

    rows = []
    for instance in dev:
        seen = sum(
            phrase.lower() in train_phrases for phrase in (instance.text1, instance.text2)
        )
        total_words = pair_lengths[instance.pair_id]
        rows.append(
            {
                "instance_id": instance.instance_id,
                "pair_id": instance.pair_id,
                "phrase_overlap": ("neither", "one", "both")[seen],
                "total_words": total_words,
                "length_bucket": (
                    "short"
                    if total_words <= low
                    else "medium" if total_words <= high else "long"
                ),
                "cue_status": cue_by_id[instance.instance_id],
            }
        )
    result = pd.DataFrame(rows)
    result.attrs["length_bucket_boundaries"] = (int(low), int(high))
    return result


def score_subgroups(
    gold: Sequence[Instance],
    predictions: Mapping[str, Mapping[str, str]],
    tags: pd.DataFrame,
    subgroup_column: str,
) -> pd.DataFrame:
    """Return weighted F1, macro F1, and accuracy by subgroup and system."""
    instances = list(gold)
    gold_labels = {instance.instance_id: instance.label for instance in instances}
    if any(label is None for label in gold_labels.values()):
        raise ValueError("gold contains unlabeled instances")
    if subgroup_column not in tags:
        raise ValueError(f"unknown subgroup column {subgroup_column!r}")
    if set(tags["instance_id"]) != set(gold_labels):
        raise ValueError("tag ids differ from gold")
    if tags["instance_id"].duplicated().any():
        raise ValueError("tags contain duplicate instance ids")
    tag_by_id = tags.set_index("instance_id")[subgroup_column].to_dict()

    rows = []
    for subgroup in sorted(set(tag_by_id.values())):
        ids = [key for key in gold_labels if tag_by_id[key] == subgroup]
        subgroup_gold = {key: gold_labels[key] for key in ids}
        for system, system_predictions in predictions.items():
            _check_labels(gold_labels, system_predictions)
            subgroup_predictions = {key: system_predictions[key] for key in ids}
            rows.append(
                {
                    "subgroup": subgroup,
                    "n": len(ids),
                    "system": system,
                    "weighted_f1": weighted_f1(
                        subgroup_gold, subgroup_predictions
                    ),
                    "macro_f1": macro_f1(subgroup_gold, subgroup_predictions),
                    "accuracy": sum(
                        subgroup_predictions[key] == subgroup_gold[key] for key in ids
                    )
                    / len(ids),
                }
            )
    return pd.DataFrame(rows)
