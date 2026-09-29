"""dico_nli.scoring: the official prediction format and the official scorer, run as CodaBench runs it."""

import pytest

from dico_nli.data import read_instances
from dico_nli.scoring import ScoringError, score, write_predictions, write_reference
from tests.support import FIXTURE_REFERENCE, requires_data_clone


def test_write_predictions_writes_the_official_two_column_format(tmp_path):
    path = write_predictions(tmp_path / "pred.csv", {"b": "EQUIVALENCE", "a": "NEGATIVE_OTHER"})

    assert path.read_text(encoding="utf-8") == "instance_id,label\nb,EQUIVALENCE\na,NEGATIVE_OTHER\n"


def test_write_reference_round_trips_a_subset_of_instances(tmp_path):
    subset = read_instances(FIXTURE_REFERENCE)[:3]

    path = write_reference(tmp_path / "gold.csv", subset)

    assert path.read_text(encoding="utf-8").splitlines()[0] == "instance_id,pair_id,text1_lang,text2_lang,text1,text2,reverse_pair_id,label"
    assert read_instances(path) == subset


@requires_data_clone
def test_write_reference_output_is_accepted_by_the_official_scorer(tmp_path):
    subset = [i for i in read_instances(FIXTURE_REFERENCE) if i.pair_id in ("fx_0001", "fx_0005")]
    gold = write_reference(tmp_path / "gold.csv", subset)
    predictions = write_predictions(tmp_path / "pred.csv", {i.instance_id: i.label for i in subset})

    result = score(gold, predictions, tmp_path / "scores")

    assert (result.weighted_f1, result.soft_cons, result.hard_cons) == (1.0, 1.0, 1.0)


@requires_data_clone
def test_score_gives_perfect_scores_when_predictions_equal_gold(tmp_path):
    gold = read_instances(FIXTURE_REFERENCE)
    predictions = write_predictions(tmp_path / "pred.csv", {i.instance_id: i.label for i in gold})

    result = score(FIXTURE_REFERENCE, predictions, tmp_path / "scores")

    assert (result.weighted_f1, result.soft_cons, result.hard_cons) == (1.0, 1.0, 1.0)
    assert (tmp_path / "scores" / "scores.json").exists()
    assert result.report_path == tmp_path / "scores" / "scores.json"


@requires_data_clone
def test_score_separates_self_consistency_from_correctness(tmp_path):
    # EQUIVALENCE everywhere is self-consistent under reversal (SoftCons 1.0) but only the
    # two EQUIVALENCE pairs of the four reversible pairs are correct (HardCons 0.5).
    gold = read_instances(FIXTURE_REFERENCE)
    predictions = write_predictions(tmp_path / "pred.csv", {i.instance_id: "EQUIVALENCE" for i in gold})

    result = score(FIXTURE_REFERENCE, predictions, tmp_path / "scores")

    assert result.soft_cons == 1.0
    assert result.hard_cons == 0.5
    assert 0.0 < result.weighted_f1 < 1.0


@requires_data_clone
def test_score_raises_with_the_scorer_message_when_a_prediction_is_missing(tmp_path):
    gold = read_instances(FIXTURE_REFERENCE)
    predictions = write_predictions(tmp_path / "pred.csv", {i.instance_id: i.label for i in gold[1:]})

    with pytest.raises(ScoringError, match="fx_0001__en-en__original"):
        score(FIXTURE_REFERENCE, predictions, tmp_path / "scores")
