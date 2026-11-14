"""Bugs and wrong assumptions that an experiment found, pinned so they do not return."""

import numpy as np

from dico_nli.data import LABELS, read_instances
from dico_nli.method.reversal import reverse_with_negative, symmetrize
from dico_nli.scoring import score, write_predictions
from tests.support import FIXTURE_REFERENCE, requires_data_clone


@requires_data_clone
def test_the_official_scorer_counts_a_negative_prediction_on_a_reversible_pair_as_inconsistent(tmp_path):
    """Found by ``experiments/2026-11-14-decoder-preliminary-track1``: symmetrized decoding scored
    SoftCons 0.906 to 0.986 on the trained 1.5B systems, where the plan had claimed 1.0 by
    construction. The two predictions of a pair always agree under this project's rule
    (NEGATIVE_OTHER maps to itself), but the official scorer defines no reverse for
    NEGATIVE_OTHER and counts that prediction on a reversible pair as incompatible. So no
    decoding rule makes the official SoftCons 1.0 unless it also never answers NEGATIVE_OTHER
    on a reversible pair."""
    instances = read_instances(FIXTURE_REFERENCE)
    leaning_negative = np.tile([0.1, 0.2, 0.1, 0.6], (len(instances), 1))

    symmetric = symmetrize(leaning_negative, leaning_negative)
    labels = {i.instance_id: LABELS[k] for i, k in zip(instances, symmetric.argmax(axis=1))}

    assert set(labels.values()) == {"NEGATIVE_OTHER"}
    for instance in instances:
        if instance.reverse_pair_id:
            assert labels[instance.reverse_pair_id] == reverse_with_negative(labels[instance.instance_id])
    result = score(FIXTURE_REFERENCE, write_predictions(tmp_path / "negative.csv", labels), tmp_path / "negative")
    assert result.soft_cons == 0.0
