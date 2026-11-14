"""The reversal rule on labels and on probability arrays, and symmetrized decoding.

Reversing an ordered pair keeps EQUIVALENCE and swaps FORWARD_ENTAILMENT with
BACKWARD_ENTAILMENT. The organizers define no reverse for NEGATIVE_OTHER; this project assumes
it maps to itself, and says so wherever a result depends on it.

Everything here works on plain numpy arrays in ``LABELS`` column order, so it applies to the
saved probabilities of any system, not only to the decoder.
"""

from __future__ import annotations

import numpy as np

from ..data import LABELS, reverse_label

NEGATIVE_LABEL = "NEGATIVE_OTHER"


def reverse_with_negative(label: str) -> str:
    """The official reversal operator, extended with NEGATIVE_OTHER mapped to itself."""
    if label == NEGATIVE_LABEL:
        return label
    return reverse_label(label)


# Column k of a reversed-order distribution holds the probability of LABELS[REVERSE_INDEX[k]]
# in the original order. The permutation is its own inverse.
REVERSE_INDEX: tuple[int, ...] = tuple(LABELS.index(reverse_with_negative(label)) for label in LABELS)


def permute(probabilities) -> np.ndarray:
    """Swap the FORWARD and BACKWARD columns of an array whose last axis is in ``LABELS`` order."""
    array = np.asarray(probabilities, dtype=float)
    if array.shape[-1] != len(LABELS):
        raise ValueError(f"expected {len(LABELS)} label columns, got shape {array.shape}")
    return array[..., list(REVERSE_INDEX)]


def symmetrize(p_forward_order, p_reverse_order) -> np.ndarray:
    """Average the distribution for ``(a, b)`` with the one for ``(b, a)`` mapped back.

    ``symmetrize(p_ab, p_ba)`` and ``symmetrize(p_ba, p_ab)`` are column permutations of each
    other, so their argmax labels obey the reversal rule. The one exception is an exact tie
    between FORWARD and BACKWARD at the top, where argmax picks FORWARD for both orders; it
    always happens when the two phrases are identical, because both orders are then one input.
    """
    return 0.5 * (np.asarray(p_forward_order, dtype=float) + permute(p_reverse_order))
