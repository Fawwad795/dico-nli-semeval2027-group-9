"""dico_nli.method.reversal: the reversal rule on labels and on probability arrays."""

import numpy as np
import pytest

from dico_nli.data import LABELS, REVERSIBLE_LABELS, reverse_label
from dico_nli.method.reversal import REVERSE_INDEX, permute, reverse_with_negative, symmetrize

EQ, FWD, BWD, NEG = (LABELS.index(label) for label in LABELS)


def labels_of(probabilities):
    return [LABELS[k] for k in np.asarray(probabilities).argmax(axis=-1)]


def random_distributions(rows, seed):
    return np.random.default_rng(seed).dirichlet(np.ones(len(LABELS)), size=rows)


def test_reverse_with_negative_agrees_with_the_official_operator_on_reversible_labels():
    for label in REVERSIBLE_LABELS:
        assert reverse_with_negative(label) == reverse_label(label)


def test_reverse_with_negative_maps_negative_other_to_itself():
    assert reverse_with_negative("NEGATIVE_OTHER") == "NEGATIVE_OTHER"


def test_reverse_with_negative_rejects_an_unknown_label():
    with pytest.raises(ValueError):
        reverse_with_negative("CONTRADICTION")


def test_reverse_index_is_the_label_permutation():
    assert [LABELS[k] for k in REVERSE_INDEX] == [reverse_with_negative(label) for label in LABELS]


def test_permute_swaps_only_the_forward_and_backward_columns():
    row = np.array([0.1, 0.2, 0.3, 0.4])

    swapped = permute(row)

    assert swapped[EQ] == 0.1 and swapped[NEG] == 0.4
    assert swapped[FWD] == 0.3 and swapped[BWD] == 0.2


def test_permute_works_on_a_batch_and_undoes_itself():
    batch = random_distributions(5, seed=13)

    assert permute(batch).shape == batch.shape
    assert np.array_equal(permute(permute(batch)), batch)


def test_permute_rejects_an_array_that_is_not_four_labels_wide():
    with pytest.raises(ValueError, match="4"):
        permute(np.ones((2, 3)))


def test_symmetrize_returns_distributions():
    forward_order, reverse_order = random_distributions(50, seed=13), random_distributions(50, seed=42)

    symmetric = symmetrize(forward_order, reverse_order)

    assert symmetric.shape == forward_order.shape
    assert np.allclose(symmetric.sum(axis=1), 1.0)
    assert (symmetric >= 0).all()


def test_symmetrized_labels_of_a_pair_and_its_reverse_always_obey_the_reversal_rule():
    p_ab, p_ba = random_distributions(500, seed=13), random_distributions(500, seed=42)

    for_ab = labels_of(symmetrize(p_ab, p_ba))
    for_ba = labels_of(symmetrize(p_ba, p_ab))

    assert for_ba == [reverse_with_negative(label) for label in for_ab]


def test_a_pair_the_single_pass_gets_inconsistent_becomes_consistent():
    p_ab = np.array([[0.10, 0.60, 0.20, 0.10]])  # FORWARD
    p_ba = np.array([[0.10, 0.50, 0.30, 0.10]])  # FORWARD again: breaks the rule
    assert labels_of(p_ab) == labels_of(p_ba) == ["FORWARD_ENTAILMENT"]

    for_ab = labels_of(symmetrize(p_ab, p_ba))
    for_ba = labels_of(symmetrize(p_ba, p_ab))

    assert for_ab == ["FORWARD_ENTAILMENT"]  # the more confident order wins
    assert for_ba == ["BACKWARD_ENTAILMENT"]


def test_symmetrize_leaves_an_already_consistent_pair_unchanged():
    p_ab = random_distributions(20, seed=13)

    assert np.allclose(symmetrize(p_ab, permute(p_ab)), p_ab)
