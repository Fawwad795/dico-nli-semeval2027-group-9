"""dico_nli.baselines.trivial: majority and seeded random baselines."""

import pytest

from dico_nli.baselines.trivial import majority_label, predict_constant, predict_majority, predict_random
from dico_nli.data import LABELS, read_instances
from tests.support import FIXTURE_REFERENCE


def test_predict_constant_gives_every_target_the_same_label():
    instances = read_instances(FIXTURE_REFERENCE)

    predictions = predict_constant(instances, "EQUIVALENCE")

    assert list(predictions) == [i.instance_id for i in instances]
    assert set(predictions.values()) == {"EQUIVALENCE"}


def test_predict_constant_rejects_a_label_outside_the_task():
    with pytest.raises(ValueError, match="ENTAILS"):
        predict_constant(read_instances(FIXTURE_REFERENCE), "ENTAILS")


def test_majority_label_picks_the_most_frequent_label():
    instances = [i for i in read_instances(FIXTURE_REFERENCE) if i.pair_id != "fx_0003"]  # 2 E, 2 F, 2 B, 4 N

    assert majority_label(instances) == "NEGATIVE_OTHER"


def test_majority_label_breaks_ties_in_canonical_label_order():
    # The fixture has 4 EQUIVALENCE and 4 NEGATIVE_OTHER; the real track-1 train set ties
    # FORWARD and BACKWARD at 881 each, so the tie-break must be deterministic and stated.
    instances = read_instances(FIXTURE_REFERENCE)

    assert majority_label(instances) == "EQUIVALENCE"
    assert LABELS.index("EQUIVALENCE") < LABELS.index("NEGATIVE_OTHER")


def test_predict_majority_labels_every_target_with_the_training_majority():
    instances = read_instances(FIXTURE_REFERENCE)

    predictions = predict_majority(train=instances, targets=instances[:5])

    assert set(predictions) == {i.instance_id for i in instances[:5]}
    assert set(predictions.values()) == {"EQUIVALENCE"}


def test_predict_random_is_seeded_and_uses_only_valid_labels():
    instances = read_instances(FIXTURE_REFERENCE)

    first = predict_random(instances, seed=13)
    again = predict_random(instances, seed=13)
    other = predict_random(instances, seed=14)

    assert first == again
    assert first != other
    assert set(first) == {i.instance_id for i in instances}
    assert set(first.values()) <= set(LABELS)
