"""dico_nli.baselines.ml: feature-based classifiers with grouped cross-validation."""

import pytest

from dico_nli.baselines.ml import MLBaseline, MLConfig, cross_validate
from dico_nli.data import LABELS, read_instances
from tests.support import FIXTURE_REFERENCE, requires_data_clone


@pytest.fixture(scope="module")
def instances():
    return read_instances(FIXTURE_REFERENCE)


@pytest.mark.parametrize("features", ["cues", "tfidf", "both"])
def test_logistic_baseline_predicts_a_valid_label_for_every_instance(instances, features):
    baseline = MLBaseline(MLConfig(features=features, model="logreg", seed=13)).fit(instances)

    predictions = baseline.predict(instances)

    assert set(predictions) == {i.instance_id for i in instances}
    assert set(predictions.values()) <= set(LABELS)


def test_gradient_boosting_baseline_uses_cues_only(instances):
    baseline = MLBaseline(MLConfig(features="cues", model="gbdt", seed=13)).fit(instances)

    predictions = baseline.predict(instances)

    assert set(predictions) == {i.instance_id for i in instances}
    with pytest.raises(ValueError, match="cues"):
        MLBaseline(MLConfig(features="tfidf", model="gbdt", seed=13))


def test_tfidf_keeps_the_separator_as_its_own_token(instances):
    baseline = MLBaseline(MLConfig(features="tfidf", model="logreg", seed=13)).fit(instances)

    vocabulary = baseline.vectorizer.vocabulary_

    assert "[sep]" in vocabulary
    assert "sep" not in vocabulary
    assert "a [sep]" in vocabulary or "[sep] a" in vocabulary  # bigrams cross the separator


def test_fitting_twice_with_the_same_seed_gives_the_same_predictions(instances):
    config = MLConfig(features="both", model="logreg", seed=13)

    first = MLBaseline(config).fit(instances).predict(instances)
    again = MLBaseline(config).fit(instances).predict(instances)

    assert first == again


def test_cue_baseline_learns_the_length_direction_on_the_training_data(instances):
    baseline = MLBaseline(MLConfig(features="cues", model="logreg", seed=13)).fit(instances)

    predictions = baseline.predict(instances)

    # "a red sports car" -> "a car" is FORWARD and its reverse BACKWARD; the cue model must
    # separate the two directions on data it has seen.
    assert predictions["fx_0001__en-en__flipped"] == "FORWARD_ENTAILMENT"
    assert predictions["fx_0001__en-en__original"] == "BACKWARD_ENTAILMENT"


@requires_data_clone
def test_cross_validate_groups_by_pair_and_scores_each_fold_officially(instances, tmp_path):
    config = MLConfig(features="cues", model="logreg", seed=13)

    folds = cross_validate(config, instances, n_splits=2, seed=13, work_dir=tmp_path)

    assert list(folds.columns) == ["fold", "train_pairs", "held_pairs", "weighted_f1", "soft_cons", "hard_cons"]
    assert list(folds["fold"]) == [0, 1]
    assert (folds["train_pairs"] + folds["held_pairs"] == 8).all()
    scores = folds[["weighted_f1", "soft_cons", "hard_cons"]]
    assert ((scores >= 0) & (scores <= 1)).all().all()
