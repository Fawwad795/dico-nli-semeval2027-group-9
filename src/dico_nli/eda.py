"""Five-facet exploratory analysis of DiCo-NLI instances: statistical, readability, lexical,
semantic, linguistic.

Every per-instance function returns a pandas DataFrame with ``instance_id``, ``pair_id`` and
``label`` as bookkeeping columns (for joins, tables and figures) and the facet's measurements
as the remaining columns. The ids are never a feature: see ``data.py``.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Callable, Iterable, Sequence

import numpy as np
import pandas as pd

from .data import LABELS, Instance, group_pairs

_TOKEN = re.compile(r"[\w']+")


def tokens(text: str) -> list[str]:
    """Lower-cased word tokens; clitics such as ``'s`` stay attached as their own token."""
    return _TOKEN.findall(text.lower())


def _keys(instance: Instance) -> dict:
    return {"instance_id": instance.instance_id, "pair_id": instance.pair_id, "label": instance.label}


def _require_labels(instances: Sequence[Instance]) -> None:
    unlabeled = sum(1 for i in instances if i.label is None)
    if unlabeled:
        raise ValueError(f"{unlabeled} unlabeled instances; label facets need gold labels")


def _unique_texts(instances: Iterable[Instance]) -> list[str]:
    seen: dict[str, None] = {}
    for instance in instances:
        seen.setdefault(instance.text1)
        seen.setdefault(instance.text2)
    return list(seen)


# statistical --------------------------------------------------------------------------------

def label_distribution(instances: Sequence[Instance]) -> pd.DataFrame:
    _require_labels(instances)
    counts = Counter(i.label for i in instances)
    total = sum(counts.values())
    return pd.DataFrame(
        {
            "label": list(LABELS),
            "count": [counts.get(label, 0) for label in LABELS],
            "share": [counts.get(label, 0) / total if total else 0.0 for label in LABELS],
        }
    )


def pair_structure(instances: Sequence[Instance]) -> pd.DataFrame:
    groups = group_pairs(instances)
    rows = [
        ("instances", len(instances)),
        ("source_pairs", len(groups)),
        ("reversible_pairs", sum(1 for members in groups.values() if len(members) == 2)),
        ("negative_instances", sum(1 for i in instances if i.label == "NEGATIVE_OTHER")),
    ]
    return pd.DataFrame(rows, columns=["quantity", "value"])


def split_overlap(train: Sequence[Instance], dev: Sequence[Instance]) -> pd.DataFrame:
    """How much of ``dev`` is already visible in ``train``: shared pair ids, identical unordered
    text pairs (case-insensitive), and dev phrases that occur anywhere in train."""

    def pairs(instances):
        return {frozenset((i.text1.lower(), i.text2.lower())) for i in instances}

    def phrases(instances):
        return {i.text1.lower() for i in instances} | {i.text2.lower() for i in instances}

    train_phrases, dev_phrases = phrases(train), phrases(dev)
    rows = [
        ("shared_pair_ids", len({i.pair_id for i in train} & {i.pair_id for i in dev})),
        ("shared_unordered_text_pairs", len(pairs(train) & pairs(dev))),
        ("dev_phrases", len(dev_phrases)),
        ("dev_phrases_seen_in_train", len(dev_phrases & train_phrases)),
        ("train_phrases", len(train_phrases)),
    ]
    return pd.DataFrame(rows, columns=["quantity", "value"])


def length_features(instances: Sequence[Instance]) -> pd.DataFrame:
    rows = []
    for instance in instances:
        words1, words2 = len(tokens(instance.text1)), len(tokens(instance.text2))
        diff = words1 - words2
        rows.append(
            {
                **_keys(instance),
                "words1": words1,
                "words2": words2,
                "word_diff": diff,
                "chars1": len(instance.text1),
                "chars2": len(instance.text2),
                "char_diff": len(instance.text1) - len(instance.text2),
                "longer_side": "text1" if diff > 0 else "text2" if diff < 0 else "equal",
            }
        )
    return pd.DataFrame(rows)


# lexical ------------------------------------------------------------------------------------

def lexical_features(instances: Sequence[Instance]) -> pd.DataFrame:
    rows = []
    for instance in instances:
        t1, t2 = tokens(instance.text1), tokens(instance.text2)
        s1, s2 = set(t1), set(t2)
        shared, union = s1 & s2, s1 | s2
        rows.append(
            {
                **_keys(instance),
                "tokens1": len(t1),
                "tokens2": len(t2),
                "shared_tokens": len(shared),
                "jaccard": len(shared) / len(union) if union else 0.0,
                "containment_1_in_2": len(shared) / len(s1) if s1 else 0.0,
                "containment_2_in_1": len(shared) / len(s2) if s2 else 0.0,
                "shared_first": bool(t1 and t2 and t1[0] == t2[0]),
                "shared_last": bool(t1 and t2 and t1[-1] == t2[-1]),
            }
        )
    return pd.DataFrame(rows)


def top_tokens_by_label(instances: Sequence[Instance], n: int = 10) -> pd.DataFrame:
    """The ``n`` most frequent tokens over both phrases, per label; ties broken alphabetically."""
    _require_labels(instances)
    counters: dict[str, Counter] = {label: Counter() for label in LABELS}
    for instance in instances:
        counters[instance.label].update(tokens(instance.text1) + tokens(instance.text2))
    rows = []
    for label in LABELS:
        ranked = sorted(counters[label].items(), key=lambda item: (-item[1], item[0]))[:n]
        rows.extend({"label": label, "token": token, "count": count} for token, count in ranked)
    return pd.DataFrame(rows, columns=["label", "token", "count"])


# readability --------------------------------------------------------------------------------

def readability_features(instances: Sequence[Instance]) -> pd.DataFrame:
    """Syllables per word, mean word length and Flesch reading ease per phrase.

    Flesch-style formulas assume sentences; on two- and three-word phrases they mostly track
    syllable density, so the table reports them once, with that caveat, and leans on the two
    simpler columns.
    """
    import textstat

    def measures(text: str) -> tuple[float, float, float]:
        words = tokens(text)
        syllables = sum(textstat.syllable_count(w) for w in words)
        return (
            syllables / len(words) if words else 0.0,
            float(np.mean([len(w) for w in words])) if words else 0.0,
            float(textstat.flesch_reading_ease(text)),
        )

    cache = {text: measures(text) for text in _unique_texts(instances)}
    rows = []
    for instance in instances:
        s1, l1, f1 = cache[instance.text1]
        s2, l2, f2 = cache[instance.text2]
        rows.append(
            {
                **_keys(instance),
                "syllables_per_word1": s1,
                "syllables_per_word2": s2,
                "mean_word_length1": l1,
                "mean_word_length2": l2,
                "flesch1": f1,
                "flesch2": f2,
            }
        )
    return pd.DataFrame(rows)


# semantic -----------------------------------------------------------------------------------

def semantic_similarity(
    instances: Sequence[Instance], encoder: Callable[[list[str]], np.ndarray]
) -> pd.DataFrame:
    """Cosine similarity between the two phrases under ``encoder`` (texts -> row vectors)."""
    texts = _unique_texts(instances)
    vectors = np.asarray(encoder(texts), dtype=float)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    unit = vectors / np.where(norms == 0, 1.0, norms)
    row = {text: i for i, text in enumerate(texts)}
    rows = [
        {**_keys(instance), "cosine": float(unit[row[instance.text1]] @ unit[row[instance.text2]])}
        for instance in instances
    ]
    return pd.DataFrame(rows)


# linguistic ---------------------------------------------------------------------------------

def linguistic_features(instances: Sequence[Instance], nlp) -> pd.DataFrame:
    """Head lemma, part-of-speech pattern, adjective and numeral counts, prepositions, per side.

    ``nlp`` is a spaCy pipeline with a tagger and parser (``en_core_web_sm`` in this project).
    """
    texts = _unique_texts(instances)
    analysed = {}
    for text, doc in zip(texts, nlp.pipe(texts)):
        roots = [t for t in doc if t.head == t]
        analysed[text] = {
            "head": roots[0].lemma_.lower() if roots else "",
            "pos": " ".join(t.pos_ for t in doc),
            "n_adj": sum(t.pos_ == "ADJ" for t in doc),
            "n_num": sum(t.pos_ == "NUM" or t.like_num for t in doc),
            "has_prep": any(t.pos_ == "ADP" for t in doc),
            "n_tokens": len(doc),
        }
    rows = []
    for instance in instances:
        a, b = analysed[instance.text1], analysed[instance.text2]
        rows.append(
            {
                **_keys(instance),
                "head1": a["head"],
                "head2": b["head"],
                "same_head": a["head"] == b["head"],
                "pos1": a["pos"],
                "pos2": b["pos"],
                "same_pos_pattern": a["pos"] == b["pos"],
                "n_adj1": a["n_adj"],
                "n_adj2": b["n_adj"],
                "n_num1": a["n_num"],
                "n_num2": b["n_num"],
                "has_prep1": a["has_prep"],
                "has_prep2": b["has_prep"],
            }
        )
    return pd.DataFrame(rows)
