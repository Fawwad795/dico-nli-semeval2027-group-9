"""dico_nli.baselines.encoder: fine-tuning a sequence-pair classifier with a seeded loop.

The tests build a tiny randomly initialised BERT from a vocabulary of the fixture's words, so
nothing is downloaded and a two-epoch fit takes seconds on a CPU.
"""

import numpy as np
import pytest

from dico_nli.baselines.encoder import EncoderBaseline, EncoderConfig, encode_pairs
from dico_nli.data import LABELS, read_instances
from tests.support import FIXTURE_REFERENCE


@pytest.fixture(scope="module")
def instances():
    return read_instances(FIXTURE_REFERENCE)


@pytest.fixture(scope="module")
def tiny(tmp_path_factory, instances):
    from transformers import BertConfig, BertForSequenceClassification, BertTokenizerFast

    words = sorted({w for i in instances for w in f"{i.text1} {i.text2}".lower().split()})
    vocab = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"] + words
    vocab_file = tmp_path_factory.mktemp("vocab") / "vocab.txt"
    vocab_file.write_text("\n".join(vocab) + "\n", encoding="utf-8")
    tokenizer = BertTokenizerFast(vocab_file=str(vocab_file), do_lower_case=True)

    def factory():
        config = BertConfig(
            vocab_size=len(vocab), hidden_size=32, num_hidden_layers=1, num_attention_heads=2,
            intermediate_size=64, max_position_embeddings=64, num_labels=len(LABELS),
        )
        return BertForSequenceClassification(config)

    return tokenizer, factory


CONFIG = EncoderConfig(model_name="tiny-for-tests", max_length=16, batch_size=4, epochs=2,
                       learning_rate=1e-3, warmup_fraction=0.1, weight_decay=0.0, seed=13)


def test_encode_pairs_truncates_to_max_length_and_masks_padding(instances, tiny):
    tokenizer, _ = tiny

    batch = encode_pairs(tokenizer, instances[:3], max_length=6)

    assert batch["input_ids"].shape == (3, 6)
    assert batch["attention_mask"].shape == (3, 6)
    assert batch["attention_mask"].sum(axis=1).min() >= 3  # [CLS] text1 [SEP] at least


def test_fit_records_one_history_row_per_epoch_and_keeps_the_best_one(instances, tiny):
    tokenizer, factory = tiny

    baseline = EncoderBaseline(CONFIG, tokenizer=tokenizer, model_factory=factory).fit(instances, holdout=instances)

    assert [row["epoch"] for row in baseline.history] == [1, 2]
    assert set(baseline.history[0]) >= {"epoch", "train_loss", "holdout_weighted_f1"}
    best = max(baseline.history, key=lambda row: row["holdout_weighted_f1"])["epoch"]
    assert baseline.best_epoch == best


def test_predict_gives_a_valid_label_for_every_instance(instances, tiny):
    tokenizer, factory = tiny
    baseline = EncoderBaseline(CONFIG, tokenizer=tokenizer, model_factory=factory).fit(instances, holdout=instances)

    predictions = baseline.predict(instances)

    assert set(predictions) == {i.instance_id for i in instances}
    assert set(predictions.values()) <= set(LABELS)


def test_predict_scores_gives_one_probability_per_label(instances, tiny):
    tokenizer, factory = tiny
    baseline = EncoderBaseline(CONFIG, tokenizer=tokenizer, model_factory=factory).fit(instances, holdout=instances)

    scores = baseline.predict_scores(instances)

    assert list(scores.columns) == ["instance_id", *LABELS]
    assert np.allclose(scores[list(LABELS)].sum(axis=1), 1.0)
    assert list(scores["instance_id"]) == [i.instance_id for i in instances]


def test_fit_fails_loudly_when_no_epoch_produces_a_finite_score(instances, tiny):
    tokenizer, factory = tiny
    diverging = EncoderConfig(model_name="tiny-for-tests", max_length=16, batch_size=4, epochs=1,
                              learning_rate=1e6, warmup_fraction=0.0, weight_decay=0.0, seed=13)

    with pytest.raises(RuntimeError, match="finite"):
        EncoderBaseline(diverging, tokenizer=tokenizer, model_factory=factory).fit(instances)


def test_same_seed_gives_the_same_model_and_predictions(instances, tiny):
    tokenizer, factory = tiny

    first = EncoderBaseline(CONFIG, tokenizer=tokenizer, model_factory=factory).fit(instances, holdout=instances)
    again = EncoderBaseline(CONFIG, tokenizer=tokenizer, model_factory=factory).fit(instances, holdout=instances)

    assert first.predict(instances) == again.predict(instances)
    assert [r["train_loss"] for r in first.history] == pytest.approx([r["train_loss"] for r in again.history])
