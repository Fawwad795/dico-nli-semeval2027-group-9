import csv
from dataclasses import replace

import pytest

from dico_nli.analysis import analyze_predictions, read_prediction_file
from dico_nli.data import read_instances
from tests.support import FIXTURE_REFERENCE


def test_analyze_predictions_classifies_every_reversible_pair():
    instances = read_instances(FIXTURE_REFERENCE)
    predictions = {instance.instance_id: instance.label for instance in instances}
    predictions.update(
        {
            "fx_0002__en-en__original": "EQUIVALENCE",
            "fx_0002__en-en__flipped": "EQUIVALENCE",
            "fx_0003__en-en__flipped": "FORWARD_ENTAILMENT",
            "fx_0004__en-en__original": "FORWARD_ENTAILMENT",
            "fx_0004__en-en__flipped": "FORWARD_ENTAILMENT",
        }
    )

    pairs, _ = analyze_predictions(instances, predictions)

    outcomes = pairs.set_index("pair_id")["outcome"].to_dict()
    assert outcomes == {
        "fx_0001": "both_directions_correct",
        "fx_0002": "consistent_but_wrong",
        "fx_0003": "inconsistent_one_direction_correct",
        "fx_0004": "inconsistent_both_directions_wrong",
    }


def test_analyze_predictions_tags_directional_and_uninformative_length_cues():
    instances = read_instances(FIXTURE_REFERENCE)
    predictions = {instance.instance_id: instance.label for instance in instances}

    _, rows = analyze_predictions(instances, predictions)

    cue = rows.set_index("instance_id")["cue_status"]
    assert cue["fx_0001__en-en__original"] == "agrees"
    assert cue["fx_0002__en-en__original"] == "uninformative"
    assert cue["fx_0003__en-en__original"] == "uninformative"
    assert cue["fx_0005__en-en__original"] == "uninformative"
    assert len(rows) == 12

    altered = [
        replace(instance, text1="all dogs", text2="more than one dog")
        if instance.instance_id == "fx_0002__en-en__original"
        else replace(instance, text1="more than one dog", text2="all dogs")
        if instance.instance_id == "fx_0002__en-en__flipped"
        else instance
        for instance in instances
    ]
    _, altered_rows = analyze_predictions(altered, predictions)
    altered_cue = altered_rows.set_index("instance_id")["cue_status"]
    assert altered_cue["fx_0002__en-en__original"] == "misleads"


def test_analyze_predictions_rejects_missing_predictions():
    instances = read_instances(FIXTURE_REFERENCE)
    predictions = {instance.instance_id: instance.label for instance in instances[1:]}

    with pytest.raises(ValueError, match="missing predictions"):
        analyze_predictions(instances, predictions)


def test_read_prediction_file_rejects_duplicate_instance_ids(tmp_path):
    path = tmp_path / "predictions.csv"
    path.write_text(
        "instance_id,label\nfx_1,EQUIVALENCE\nfx_1,FORWARD_ENTAILMENT\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate instance_id"):
        read_prediction_file(path)