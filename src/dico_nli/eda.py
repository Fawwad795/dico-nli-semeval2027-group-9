"""Six-group exploratory analysis of DiCo-NLI instances: statistical, readability, lexical,
semantic, linguistic, and task-specific cues.

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


def data_quality_checks(instances: Sequence[Instance]) -> pd.DataFrame:
    """Count text, pair, phrase-shape, and language checks for one split.

    Duplicate pairs are exact and case-sensitive. Unordered pairs intentionally combine
    identical rows with reversed rows; label disagreement is checked only within identical
    ordered pairs, where opposite directional labels are a genuine conflict.
    """
    ordered: dict[tuple[str, str], list[Instance]] = {}
    unordered: dict[tuple[str, str], list[Instance]] = {}
    missing_texts = empty_texts = one_word = long_phrases = marked_starts = 0
    en_en = non_en = 0

    for instance in instances:
        texts = (instance.text1, instance.text2)
        for text in texts:
            if text is None:
                missing_texts += 1
                continue
            if not text.strip():
                empty_texts += 1
                continue
            words = tokens(text)
            one_word += len(words) == 1
            long_phrases += len(words) >= 8
            first = text.lstrip()
            marked_starts += bool(first and not first[0].isalnum())

        if all(isinstance(text, str) and text.strip() for text in texts):
            pair = (texts[0], texts[1])
            ordered.setdefault(pair, []).append(instance)
            unordered.setdefault(tuple(sorted(pair)), []).append(instance)

        lang1 = (instance.text1_lang or "").strip().lower()
        lang2 = (instance.text2_lang or "").strip().lower()
        en_en += (lang1, lang2) == ("en", "en")
        non_en += (lang1, lang2) != ("en", "en")

    duplicate_ordered = [group for group in ordered.values() if len(group) > 1]
    duplicate_unordered = [group for group in unordered.values() if len(group) > 1]
    conflicting_ordered = sum(
        len({instance.label for instance in group if instance.label is not None}) > 1
        for group in duplicate_ordered
    )
    reversed_pair_groups = {
        tuple(sorted(pair))
        for pair in ordered
        if pair[0] != pair[1] and (pair[1], pair[0]) in ordered
    }
    rows = [
        ("instances", len(instances)),
        ("missing_text_values", missing_texts),
        ("empty_text_values", empty_texts),
        ("complete_nonempty_pairs", sum(1 for i in instances if i.text1 and i.text1.strip() and i.text2 and i.text2.strip())),
        ("exact_ordered_duplicate_groups", len(duplicate_ordered)),
        ("exact_ordered_duplicate_extra_instances", sum(len(group) - 1 for group in duplicate_ordered)),
        ("exact_ordered_duplicate_groups_with_label_disagreement", conflicting_ordered),
        ("reversed_pair_groups", len(reversed_pair_groups)),
        ("unordered_duplicate_groups", len(duplicate_unordered)),
        ("unordered_duplicate_extra_instances", sum(len(group) - 1 for group in duplicate_unordered)),
        ("one_word_phrases", one_word),
        ("phrases_8plus_words", long_phrases),
        ("phrases_starting_clitic_or_punctuation", marked_starts),
        ("en_en_instances", en_en),
        ("non_en_language_pairs", non_en),
    ]
    return pd.DataFrame(rows, columns=["check", "value"])


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


_QUANTIFIERS = frozenset(
    {
        "all", "any", "both", "each", "either", "enough", "every", "few", "fewer",
        "fewest", "many", "more", "most", "much", "neither", "several", "some",
        "various", "whole",
    }
)
_NEGATIONS = frozenset(
    {
        "cannot", "hardly", "never", "no", "nobody", "none", "nor", "not", "nothing",
        "nowhere", "n't", "without",
    }
)


def task_specific_features(instances: Sequence[Instance], nlp) -> pd.DataFrame:
    """Pair-level quantifier, negation, numeral, and named-entity presence.

    A cue is present when either phrase contains at least one matching token/entity. Numerals
    and named entities use spaCy's token and entity annotations; the lexical cue lists are fixed
    here so the analysis is deterministic and reviewable.
    """
    texts = list(
        dict.fromkeys(
            text
            for instance in instances
            for text in (instance.text1, instance.text2)
            if isinstance(text, str) and text.strip()
        )
    )
    docs = dict(zip(texts, nlp.pipe(texts)))

    def has_token(doc, vocabulary: frozenset[str]) -> bool:
        return bool(doc and any(token.lower_ in vocabulary for token in doc))

    def has_numeral(doc) -> bool:
        return bool(doc and any(token.like_num or token.pos_ == "NUM" for token in doc))

    rows = []
    for instance in instances:
        doc1 = docs.get(instance.text1)
        doc2 = docs.get(instance.text2)
        rows.append(
            {
                **_keys(instance),
                "has_quantifier": has_token(doc1, _QUANTIFIERS) or has_token(doc2, _QUANTIFIERS),
                "has_negation": has_token(doc1, _NEGATIONS) or has_token(doc2, _NEGATIONS),
                "has_numeral": has_numeral(doc1) or has_numeral(doc2),
                "has_named_entity": bool((doc1 and doc1.ents) or (doc2 and doc2.ents)),
            }
        )
    return pd.DataFrame(rows)


def trial_source_summary(pairs: Sequence[dict]) -> pd.DataFrame:
    """Count trial examples by trial split and their original source metadata."""
    rows = []
    fields = ("split", "source_split", "source_modality", "original_source_file")
    for field in fields:
        counts = Counter()
        for pair in pairs:
            metadata = pair.get("metadata") or {}
            value = pair.get(field) if field == "split" else metadata.get(field)
            counts[str(value) if value not in (None, "") else "unavailable"] += 1
        rows.extend(
            {"field": field, "value": value, "count": count}
            for value, count in sorted(counts.items())
        )
    return pd.DataFrame(rows, columns=["field", "value", "count"])
