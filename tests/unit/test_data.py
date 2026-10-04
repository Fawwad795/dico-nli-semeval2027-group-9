"""dico_nli.data: reading the task CSVs, grouping by source pair, seeded grouped splits."""

import csv

import pytest

from dico_nli.data import Instance, group_pairs, grouped_split, load_reference, read_instances, reverse_label
from tests.support import FIXTURE_REFERENCE, requires_data_clone


def test_reverse_label_mirrors_the_official_reversal_operator():
    assert reverse_label("FORWARD_ENTAILMENT") == "BACKWARD_ENTAILMENT"
    assert reverse_label("BACKWARD_ENTAILMENT") == "FORWARD_ENTAILMENT"
    assert reverse_label("EQUIVALENCE") == "EQUIVALENCE"
    with pytest.raises(ValueError, match="NEGATIVE_OTHER"):
        reverse_label("NEGATIVE_OTHER")


def _rewrite_without_columns(src, dst, drop):
    with open(src, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    fields = [c for c in rows[0] if c not in drop]
    with open(dst, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return dst


def test_read_instances_returns_one_instance_per_row_with_all_fields():
    instances = read_instances(FIXTURE_REFERENCE)

    assert len(instances) == 12
    assert instances[0] == Instance(
        instance_id="fx_0001__en-en__original",
        pair_id="fx_0001",
        text1="a car",
        text2="a red sports car",
        label="BACKWARD_ENTAILMENT",
        reverse_pair_id="fx_0001__en-en__flipped",
        text1_lang="en",
        text2_lang="en",
    )


def test_read_instances_maps_empty_reverse_pair_id_to_none():
    negatives = [i for i in read_instances(FIXTURE_REFERENCE) if i.label == "NEGATIVE_OTHER"]

    assert len(negatives) == 4
    assert all(i.reverse_pair_id is None for i in negatives)


def test_read_instances_accepts_participant_file_without_reverse_column(tmp_path):
    path = _rewrite_without_columns(FIXTURE_REFERENCE, tmp_path / "participant.csv", {"reverse_pair_id"})

    instances = read_instances(path)

    assert len(instances) == 12
    assert instances[0].label == "BACKWARD_ENTAILMENT"
    assert all(i.reverse_pair_id is None for i in instances)


def test_read_instances_accepts_unlabeled_file(tmp_path):
    path = _rewrite_without_columns(FIXTURE_REFERENCE, tmp_path / "unlabeled.csv", {"reverse_pair_id", "label"})

    instances = read_instances(path)

    assert all(i.label is None for i in instances)
    assert instances[1].text1 == "a red sports car"


def test_read_instances_rejects_an_unknown_label(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text(
        "instance_id,pair_id,text1_lang,text2_lang,text1,text2,label\n"
        "x__en-en__original,x,en,en,a,b,ENTAILS\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="ENTAILS"):
        read_instances(path)


def test_group_pairs_keeps_both_directions_under_one_pair_id():
    groups = group_pairs(read_instances(FIXTURE_REFERENCE))

    assert len(groups) == 8
    assert {i.instance_id for i in groups["fx_0001"]} == {"fx_0001__en-en__original", "fx_0001__en-en__flipped"}
    assert len(groups["fx_0005"]) == 1


def test_grouped_split_never_separates_a_pair_and_is_seeded():
    instances = read_instances(FIXTURE_REFERENCE)

    train, held = grouped_split(instances, holdout_fraction=0.5, seed=13)

    assert len(train) + len(held) == 12
    assert held and train
    assert {i.pair_id for i in train}.isdisjoint({i.pair_id for i in held})
    assert grouped_split(instances, holdout_fraction=0.5, seed=13) == (train, held)


def test_grouped_split_holdout_fraction_counts_source_pairs_not_rows():
    instances = read_instances(FIXTURE_REFERENCE)  # 8 source pairs

    _, held = grouped_split(instances, holdout_fraction=0.25, seed=1)

    assert len({i.pair_id for i in held}) == 2


def test_grouped_split_changes_with_the_seed():
    instances = read_instances(FIXTURE_REFERENCE)

    splits = {tuple(i.pair_id for i in grouped_split(instances, holdout_fraction=0.5, seed=s)[1]) for s in range(6)}

    assert len(splits) > 1


@requires_data_clone
def test_load_reference_reads_the_real_track1_files():
    assert len(load_reference(track=1, split="train")) == 3042
    assert len(load_reference(track=1, split="dev")) == 660
