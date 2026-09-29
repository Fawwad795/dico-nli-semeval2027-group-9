"""dico_nli.features: the numeric cue matrix and the text form used by the ML baseline."""

import numpy as np
import pandas as pd

from dico_nli.data import read_instances
from dico_nli.features import CUE_COLUMNS, cue_features, pair_text
from tests.support import FIXTURE_REFERENCE


def test_cue_features_is_a_numeric_matrix_with_one_row_per_instance():
    instances = read_instances(FIXTURE_REFERENCE)

    frame = cue_features(instances)

    assert list(frame.columns) == list(CUE_COLUMNS)
    assert len(frame) == 12
    assert all(pd.api.types.is_numeric_dtype(frame[c]) for c in frame.columns)
    assert not np.isnan(frame.to_numpy(dtype=float)).any()


def test_cue_features_never_include_ids_or_labels():
    instances = read_instances(FIXTURE_REFERENCE)

    frame = cue_features(instances)

    assert not {"instance_id", "pair_id", "label", "reverse_pair_id"} & set(frame.columns)
    assert not frame.astype(str).apply(lambda col: col.str.contains("__en-en__").any()).any()


def test_cue_features_flip_their_sign_when_the_pair_is_reversed():
    instances = read_instances(FIXTURE_REFERENCE)
    frame = cue_features(instances)
    original, flipped = frame.iloc[0], frame.iloc[1]  # fx_0001: "a car" / "a red sports car" and its reverse

    assert original["word_diff"] == -2 and flipped["word_diff"] == 2
    assert original["containment_1_in_2"] == 1.0 and original["containment_2_in_1"] == 0.5
    assert flipped["containment_1_in_2"] == 0.5 and flipped["containment_2_in_1"] == 1.0
    assert original["jaccard"] == flipped["jaccard"] == 0.5


def test_pair_text_joins_both_sides_with_a_separator():
    instance = read_instances(FIXTURE_REFERENCE)[0]

    assert pair_text(instance) == "a car [SEP] a red sports car"
