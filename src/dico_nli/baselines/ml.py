"""Feature-based ML baselines: logistic regression on cues, TF-IDF or both; gradient boosting
on cues. Model selection and reporting inside the training data use grouped cross-validation
by source pair, scored fold by fold with the official scorer.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from ..data import LABELS, Instance
from ..features import CUE_COLUMNS, cue_matrix, pair_text
from ..scoring import score, write_predictions, write_reference

FEATURE_SETS = ("cues", "tfidf", "both")
MODELS = ("logreg", "gbdt")


@dataclass(frozen=True)
class MLConfig:
    features: str = "both"
    model: str = "logreg"
    seed: int = 13
    C: float = 1.0

    def __post_init__(self) -> None:
        if self.features not in FEATURE_SETS:
            raise ValueError(f"features must be one of {FEATURE_SETS}, got {self.features!r}")
        if self.model not in MODELS:
            raise ValueError(f"model must be one of {MODELS}, got {self.model!r}")
        if self.model == "gbdt" and self.features != "cues":
            raise ValueError("gbdt takes the dense cues only; use features='cues'")

    @property
    def name(self) -> str:
        return f"{self.features}+{self.model}"


class MLBaseline:
    def __init__(self, config: MLConfig) -> None:
        self.config = config
        self.scaler: StandardScaler | None = None
        self.vectorizer: TfidfVectorizer | None = None
        self.model = None

    def _matrix(self, instances: Sequence[Instance], fit: bool):
        parts = []
        if self.config.features in ("cues", "both"):
            cues = cue_matrix(instances)
            if fit:
                self.scaler = StandardScaler().fit(cues)
            parts.append(sp.csr_matrix(self.scaler.transform(cues)))
        if self.config.features in ("tfidf", "both"):
            texts = [pair_text(i) for i in instances]
            if fit:
                # The default token pattern drops one-letter words and would turn "[SEP]" into a
                # plain "sep"; this one keeps "a" and the separator as its own token "[sep]".
                self.vectorizer = TfidfVectorizer(
                    ngram_range=(1, 2), sublinear_tf=True, lowercase=True, token_pattern=r"(?u)\b\w+\b|\[sep\]"
                )
                self.vectorizer.fit(texts)
            parts.append(self.vectorizer.transform(texts))
        matrix = sp.hstack(parts).tocsr() if len(parts) > 1 else parts[0]
        return matrix.toarray() if self.config.model == "gbdt" else matrix

    def fit(self, train: Sequence[Instance]) -> "MLBaseline":
        X = self._matrix(train, fit=True)
        y = np.array([i.label for i in train])
        if self.config.model == "logreg":
            self.model = LogisticRegression(
                C=self.config.C, class_weight="balanced", max_iter=5000, random_state=self.config.seed
            )
        else:
            self.model = HistGradientBoostingClassifier(
                max_iter=300, learning_rate=0.05, class_weight="balanced", random_state=self.config.seed
            )
        self.model.fit(X, y)
        return self

    def predict(self, instances: Sequence[Instance]) -> dict[str, str]:
        labels = self.model.predict(self._matrix(instances, fit=False))
        return {instance.instance_id: str(label) for instance, label in zip(instances, labels)}

    def cue_coefficients(self) -> pd.DataFrame:
        """Standardised logistic-regression weights per label and cue (cue-bearing configs only)."""
        if self.config.model != "logreg" or self.config.features == "tfidf":
            raise ValueError("cue coefficients exist for logistic regression on cues")
        classes = [str(c) for c in self.model.classes_]
        coef = self.model.coef_
        if coef.shape[0] == 1:  # binary fit: one log-odds vector for classes_[1] against classes_[0]
            coef = np.vstack([-coef[0], coef[0]])
        rows = []
        for label, weights in zip(classes, coef):
            for cue, weight in zip(CUE_COLUMNS, weights[: len(CUE_COLUMNS)]):
                rows.append({"label": label, "cue": cue, "coefficient": float(weight)})
        return pd.DataFrame(rows)


def cross_validate(
    config: MLConfig, instances: Sequence[Instance], n_splits: int = 5, seed: int = 13, work_dir: Path | None = None
) -> pd.DataFrame:
    """Grouped k-fold by ``pair_id`` (both directions of a pair stay together), each held-out
    fold scored with the official scorer. Returns one row per fold."""
    work_dir = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="dico-cv-"))
    groups = [i.pair_id for i in instances]
    splitter = GroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    rows = []
    for fold, (train_idx, held_idx) in enumerate(splitter.split(instances, groups=groups)):
        train = [instances[i] for i in train_idx]
        held = [instances[i] for i in held_idx]
        predictions = MLBaseline(config).fit(train).predict(held)
        fold_dir = work_dir / f"fold{fold}"
        result = score(
            write_reference(fold_dir / "gold.csv", held),
            write_predictions(fold_dir / "predictions.csv", predictions),
            fold_dir / "scores",
        )
        rows.append(
            {
                "fold": fold,
                "train_pairs": len({i.pair_id for i in train}),
                "held_pairs": len({i.pair_id for i in held}),
                "weighted_f1": result.weighted_f1,
                "soft_cons": result.soft_cons,
                "hard_cons": result.hard_cons,
            }
        )
    return pd.DataFrame(rows, columns=["fold", "train_pairs", "held_pairs", "weighted_f1", "soft_cons", "hard_cons"])


__all__ = ["LABELS", "MLBaseline", "MLConfig", "cross_validate"]
