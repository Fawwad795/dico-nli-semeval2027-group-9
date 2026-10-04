"""dico_nli.eda: six-group exploratory analysis, one DataFrame per feature function."""

import numpy as np
import pytest

from dico_nli.data import LABELS, read_instances
from dico_nli.eda import (
    data_quality_checks,
    label_distribution,
    length_features,
    lexical_features,
    linguistic_features,
    pair_structure,
    readability_features,
    semantic_similarity,
    task_specific_features,
    top_tokens_by_label,
    trial_source_summary,
)
from tests.support import FIXTURE_REFERENCE


@pytest.fixture(scope="module")
def instances():
    return read_instances(FIXTURE_REFERENCE)


def by_id(frame, instance_id):
    rows = frame[frame["instance_id"] == instance_id]
    assert len(rows) == 1
    return rows.iloc[0]


# statistical --------------------------------------------------------------------------------

def test_label_distribution_counts_in_canonical_order(instances):
    frame = label_distribution(instances)

    assert list(frame["label"]) == list(LABELS)
    assert list(frame["count"]) == [4, 2, 2, 4]
    assert frame["share"].sum() == pytest.approx(1.0)


def test_split_overlap_counts_shared_pairs_and_phrases_seen_in_train(instances):
    from dico_nli.data import Instance
    from dico_nli.eda import split_overlap

    dev = [
        Instance("d1", "d1", "a car", "a big house", "NEGATIVE_OTHER"),          # both phrases seen, pair new
        Instance("d2", "d2", "A RED SPORTS CAR", "a car", "FORWARD_ENTAILMENT"),  # same unordered pair as fx_0001
        Instance("d3", "d3", "a lorry", "a car", "FORWARD_ENTAILMENT"),           # one new phrase
    ]

    table = split_overlap(instances, dev).set_index("quantity")["value"]

    assert table["shared_pair_ids"] == 0
    assert table["shared_unordered_text_pairs"] == 1
    assert table["dev_phrases"] == 4
    assert table["dev_phrases_seen_in_train"] == 3
    assert table["train_phrases"] == 16


def test_label_facets_refuse_unlabeled_instances(instances):
    from dataclasses import replace

    unlabeled = [replace(i, label=None) for i in instances]

    with pytest.raises(ValueError, match="unlabeled"):
        label_distribution(unlabeled)
    with pytest.raises(ValueError, match="unlabeled"):
        top_tokens_by_label(unlabeled)


def test_pair_structure_counts_instances_pairs_and_negatives(instances):
    frame = pair_structure(instances).set_index("quantity")["value"]

    assert frame["instances"] == 12
    assert frame["source_pairs"] == 8
    assert frame["reversible_pairs"] == 4
    assert frame["negative_instances"] == 4


def test_length_features_record_which_side_is_longer(instances):
    frame = length_features(instances)

    original = by_id(frame, "fx_0001__en-en__original")  # "a car" -> "a red sports car", BACKWARD
    assert (original["words1"], original["words2"], original["word_diff"]) == (2, 4, -2)
    assert original["longer_side"] == "text2"
    assert original["label"] == "BACKWARD_ENTAILMENT"
    flipped = by_id(frame, "fx_0001__en-en__flipped")
    assert flipped["longer_side"] == "text1"
    assert by_id(frame, "fx_0005__en-en__original")["longer_side"] == "equal"
    assert original["chars1"] == len("a car")


def test_length_features_never_expose_the_instance_id_as_a_feature(instances):
    frame = length_features(instances)

    import pandas as pd

    feature_columns = [c for c in frame.columns if c not in ("instance_id", "pair_id", "label")]
    assert "instance_id" not in feature_columns
    assert all(pd.api.types.is_numeric_dtype(frame[c]) or pd.api.types.is_string_dtype(frame[c]) for c in feature_columns)
    assert not any(frame[c].astype(str).str.contains("__en-en__").any() for c in feature_columns)


# lexical ------------------------------------------------------------------------------------

def test_lexical_features_measure_overlap_and_containment_in_both_directions(instances):
    row = by_id(lexical_features(instances), "fx_0001__en-en__original")  # {a, car} vs {a, red, sports, car}

    assert row["jaccard"] == pytest.approx(0.5)
    assert row["containment_1_in_2"] == pytest.approx(1.0)
    assert row["containment_2_in_1"] == pytest.approx(0.5)
    assert bool(row["shared_first"]) is True
    assert bool(row["shared_last"]) is True


def test_lexical_features_lowercase_and_split_on_words(instances):
    row = by_id(lexical_features(instances), "fx_0008__en-en__original")  # "Crimea annexation" vs "Crimea 's independence"

    assert row["tokens1"] == 2
    assert row["tokens2"] == 3
    assert row["jaccard"] == pytest.approx(1 / 4)


def test_top_tokens_by_label_returns_the_most_frequent_tokens_per_label(instances):
    frame = top_tokens_by_label(instances, n=2)

    equivalence = frame[frame["label"] == "EQUIVALENCE"]
    assert set(equivalence["token"]) == {"a", "house"}
    assert list(equivalence["count"]) == [4, 4]
    assert set(frame["label"]) == set(LABELS)


# readability --------------------------------------------------------------------------------

def test_readability_features_give_syllables_and_word_length_per_side(instances):
    row = by_id(readability_features(instances), "fx_0001__en-en__original")  # "a car"

    assert row["syllables_per_word1"] == pytest.approx(1.0)
    assert row["mean_word_length1"] == pytest.approx(2.0)
    assert np.isfinite(row["flesch1"]) and np.isfinite(row["flesch2"])


# semantic -----------------------------------------------------------------------------------

def bag_of_words_encoder(texts):
    vocabulary = sorted({t for text in texts for t in text.lower().split()})
    index = {t: i for i, t in enumerate(vocabulary)}
    matrix = np.zeros((len(texts), len(vocabulary)))
    for r, text in enumerate(texts):
        for t in text.lower().split():
            matrix[r, index[t]] = 1.0
    return matrix


def test_semantic_similarity_uses_the_given_encoder_and_is_symmetric(instances):
    frame = semantic_similarity(instances, encoder=bag_of_words_encoder)

    assert by_id(frame, "fx_0003__en-en__original")["cosine"] == pytest.approx(2 / 3)  # a big house / a large house
    assert by_id(frame, "fx_0005__en-en__original")["cosine"] == pytest.approx(0.5)  # off Mexico / on Mexico
    assert by_id(frame, "fx_0001__en-en__original")["cosine"] == by_id(frame, "fx_0001__en-en__flipped")["cosine"]
    assert set(frame.columns) >= {"instance_id", "label", "cosine"}


# linguistic ---------------------------------------------------------------------------------

def test_linguistic_features_find_heads_modifiers_and_prepositions(instances):
    import spacy

    frame = linguistic_features(instances, nlp=spacy.load("en_core_web_sm"))

    car = by_id(frame, "fx_0001__en-en__original")  # "a car" vs "a red sports car"
    assert car["head1"] == "car" and car["head2"] == "car"
    assert bool(car["same_head"]) is True
    assert car["n_adj2"] >= 1
    iraq = by_id(frame, "fx_0006__en-en__original")  # "in southern Iraq" vs "in northern Iraq"
    assert bool(iraq["has_prep1"]) is True and bool(iraq["has_prep2"]) is True
    assert isinstance(car["pos1"], str) and car["pos1"].startswith("DET")


# data quality -------------------------------------------------------------------------------

def test_data_quality_checks_report_duplicate_groups_conflicts_and_phrase_flags():
    from dico_nli.data import Instance

    instances = [
        Instance("a", "p1", "'s war shrine visit", "one", "FORWARD_ENTAILMENT"),
        Instance("b", "p2", "'s war shrine visit", "one", "BACKWARD_ENTAILMENT"),
        Instance("c", "p3", "one", "'s war shrine visit", "BACKWARD_ENTAILMENT"),
        Instance("d", "p4", None, "   ", "NEGATIVE_OTHER", text1_lang="en", text2_lang="es"),
    ]

    table = data_quality_checks(instances).set_index("check")["value"]

    assert table["instances"] == 4
    assert table["missing_text_values"] == 1
    assert table["empty_text_values"] == 1
    assert table["exact_ordered_duplicate_groups"] == 1
    assert table["exact_ordered_duplicate_extra_instances"] == 1
    assert table["exact_ordered_duplicate_groups_with_label_disagreement"] == 1
    assert table["reversed_pair_groups"] == 1
    assert table["unordered_duplicate_groups"] == 1
    assert table["unordered_duplicate_extra_instances"] == 2
    assert table["one_word_phrases"] == 3
    assert table["phrases_8plus_words"] == 0
    assert table["phrases_starting_clitic_or_punctuation"] == 3
    assert table["en_en_instances"] == 3
    assert table["non_en_language_pairs"] == 1


def test_task_specific_features_detect_pair_level_quantifier_negation_number_and_entity():
    import spacy
    from dico_nli.data import Instance

    nlp = spacy.blank("en")
    ruler = nlp.add_pipe("entity_ruler")
    ruler.add_patterns([{"label": "GPE", "pattern": "Paris"}])
    instances = [
        Instance("a", "p1", "Every 3 cars", "not near Paris", "FORWARD_ENTAILMENT"),
        Instance("b", "p2", "blue cars", "ordinary things", "EQUIVALENCE"),
    ]

    frame = task_specific_features(instances, nlp=nlp)
    first = by_id(frame, "a")
    second = by_id(frame, "b")

    assert bool(first["has_quantifier"]) is True
    assert bool(first["has_negation"]) is True
    assert bool(first["has_numeral"]) is True
    assert bool(first["has_named_entity"]) is True
    assert bool(second["has_quantifier"]) is False
    assert bool(second["has_negation"]) is False
    assert bool(second["has_numeral"]) is False
    assert bool(second["has_named_entity"]) is False


def test_trial_source_summary_counts_split_modality_and_original_source():
    pairs = [
        {
            "split": "trial",
            "metadata": {
                "source_split": "train",
                "source_modality": "headlines",
                "original_source_file": "PhrasIS.train.headlines.positives.txt",
            }
        },
        {
            "split": "trial",
            "metadata": {
                "source_split": "train",
                "source_modality": "captions",
                "original_source_file": "PhrasIS.train.captions.positives.txt",
            }
        },
        {
            "split": "trial",
            "metadata": {
                "source_split": "dev",
                "source_modality": "headlines",
                "original_source_file": "PhrasIS.dev.headlines.positives.txt",
            }
        },
    ]

    table = trial_source_summary(pairs).set_index(["field", "value"])["count"]

    assert table.loc[("split", "trial")] == 3
    assert table.loc[("source_split", "train")] == 2
    assert table.loc[("source_split", "dev")] == 1
    assert table.loc[("source_modality", "captions")] == 1
    assert table.loc[("original_source_file", "PhrasIS.train.headlines.positives.txt")] == 1
