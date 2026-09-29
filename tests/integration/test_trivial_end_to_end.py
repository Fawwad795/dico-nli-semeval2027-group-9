"""Fixture rows through the trivial baselines and the official scorer, end to end."""

from dico_nli.baselines.trivial import predict_majority, predict_random
from dico_nli.data import read_instances
from dico_nli.scoring import score, write_predictions
from tests.support import FIXTURE_REFERENCE, requires_data_clone


@requires_data_clone
def test_majority_baseline_is_self_consistent_but_half_right_on_the_fixture(tmp_path):
    instances = read_instances(FIXTURE_REFERENCE)
    predictions = write_predictions(tmp_path / "majority.csv", predict_majority(instances, instances))

    result = score(FIXTURE_REFERENCE, predictions, tmp_path / "majority")

    # Majority on the fixture is EQUIVALENCE (tie with NEGATIVE_OTHER broken by label order):
    # consistent under reversal everywhere, correct on the two EQUIVALENCE pairs only.
    assert result.soft_cons == 1.0
    assert result.hard_cons == 0.5


@requires_data_clone
def test_random_baseline_scores_are_reproducible_for_a_seed(tmp_path):
    instances = read_instances(FIXTURE_REFERENCE)
    results = []
    for run in ("first", "second"):
        predictions = write_predictions(tmp_path / f"{run}.csv", predict_random(instances, seed=13))
        results.append(score(FIXTURE_REFERENCE, predictions, tmp_path / run))

    assert (results[0].weighted_f1, results[0].soft_cons, results[0].hard_cons) == (
        results[1].weighted_f1, results[1].soft_cons, results[1].hard_cons,
    )
    assert (tmp_path / "first" / "scores.json").read_bytes() == (tmp_path / "second" / "scores.json").read_bytes()
