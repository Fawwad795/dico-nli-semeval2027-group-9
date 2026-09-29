"""The numeric cue matrix for the ML baseline, and the text form fed to TF-IDF.

The cues are the EDA's length and lexical measurements (``eda.length_features`` and
``eda.lexical_features``) plus a few span and digit flags, so the ablation measures exactly
the shallow signals the EDA found. Ids and labels never enter the matrix.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
import pandas as pd

from .data import Instance
from .eda import length_features, lexical_features, tokens

CUE_COLUMNS: tuple[str, ...] = (
    "words1", "words2", "word_diff", "word_log_ratio",
    "chars1", "chars2", "char_diff",
    "shared_tokens", "jaccard", "containment_1_in_2", "containment_2_in_1",
    "shared_first", "shared_last",
    "text2_span_in_text1", "text1_span_in_text2",
    "digit1", "digit2",
)


def _contiguous(sub: list[str], full: list[str]) -> bool:
    n = len(sub)
    return 0 < n <= len(full) and any(full[i:i + n] == sub for i in range(len(full) - n + 1))


def cue_features(instances: Sequence[Instance]) -> pd.DataFrame:
    """One float row per instance, columns ``CUE_COLUMNS``, in instance order."""
    lengths = length_features(instances)
    lexical = lexical_features(instances)
    extra = []
    for instance in instances:
        t1, t2 = tokens(instance.text1), tokens(instance.text2)
        extra.append(
            {
                "word_log_ratio": math.log((len(t1) + 1) / (len(t2) + 1)),
                "text2_span_in_text1": _contiguous(t2, t1),
                "text1_span_in_text2": _contiguous(t1, t2),
                "digit1": any(ch.isdigit() for ch in instance.text1),
                "digit2": any(ch.isdigit() for ch in instance.text2),
            }
        )
    frame = pd.concat(
        [
            lengths[["words1", "words2", "word_diff", "chars1", "chars2", "char_diff"]],
            lexical[["shared_tokens", "jaccard", "containment_1_in_2", "containment_2_in_1", "shared_first", "shared_last"]],
            pd.DataFrame(extra),
        ],
        axis=1,
    )
    return frame[list(CUE_COLUMNS)].astype(float)


def cue_matrix(instances: Sequence[Instance]) -> np.ndarray:
    return cue_features(instances).to_numpy(dtype=float)


def pair_text(instance: Instance) -> str:
    """Both phrases in order with a separator token, the input to the TF-IDF features."""
    return f"{instance.text1} [SEP] {instance.text2}"
