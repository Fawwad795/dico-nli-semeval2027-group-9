"""dico_nli.method.decoder: prompt, label scoring, LoRA training with the consistency loss.

The tests build a one-layer randomly initialised Qwen2 causal LM and a word-level tokenizer
over the words of the fixture's prompts, so nothing is downloaded and a fit takes seconds on a
CPU. The LoRA target modules carry the same names as in the real backbone.
"""

import inspect
from dataclasses import replace

import numpy as np
import pytest
import torch

from dico_nli.data import LABELS, read_instances
from dico_nli.method.decoder import (
    LETTERS,
    DecoderClassifier,
    DecoderConfig,
    build_prompt,
    plain_prompt,
)
from dico_nli.method.reversal import reverse_with_negative
from tests.support import FIXTURE_REFERENCE, tiny_decoder, word_level_tokenizer

CONFIG = DecoderConfig(model_name="tiny-for-tests", lora_rank=4, lora_alpha=8, lora_dropout=0.05,
                       max_length=128, batch_size=4, epochs=2, learning_rate=1e-2,
                       warmup_fraction=0.1, weight_decay=0.0, consistency_weight=1.0, seed=13)


@pytest.fixture(scope="module")
def instances():
    return read_instances(FIXTURE_REFERENCE)


@pytest.fixture(scope="module")
def tiny(instances):
    return tiny_decoder(instances)


@pytest.fixture(scope="module")
def fitted(instances, tiny):
    tokenizer, factory = tiny
    return DecoderClassifier(CONFIG, tokenizer=tokenizer, model_factory=factory).fit(instances, holdout=instances)


def probabilities(frame):
    return frame[list(LABELS)].to_numpy()


# --- prompt -------------------------------------------------------------------------------

def test_build_prompt_takes_only_the_two_phrases():
    assert list(inspect.signature(build_prompt).parameters) == ["text1", "text2"]


def test_build_prompt_names_both_phrases_in_order_and_every_option_letter():
    text = plain_prompt(build_prompt("a red car", "a car"))

    assert text.index("a red car") < text.index("Phrase 2")
    assert "Phrase 2: a car" in text
    for letter in LETTERS:
        assert f"{letter}. " in text


def test_build_prompt_depends_on_the_order_of_the_pair():
    assert build_prompt("a red car", "a car") != build_prompt("a car", "a red car")


def test_there_is_one_letter_per_label():
    assert len(LETTERS) == len(LABELS) == len(set(LETTERS))


# --- label scoring ------------------------------------------------------------------------

def test_a_letter_that_is_not_one_known_token_fails_loudly(tiny):
    _, factory = tiny
    tokenizer, _ = word_level_tokenizer(["A B C phrase"])  # no D in the vocabulary

    with pytest.raises(ValueError, match="one token"):
        DecoderClassifier(CONFIG, tokenizer=tokenizer, model_factory=factory).letter_ids


def test_the_classifier_pads_on_the_left(tiny):
    tokenizer, factory = tiny

    classifier = DecoderClassifier(CONFIG, tokenizer=tokenizer, model_factory=factory)

    assert classifier.tokenizer.padding_side == "left"


def test_predict_scores_gives_one_probability_per_label_without_training(instances, tiny):
    tokenizer, factory = tiny

    scores = DecoderClassifier(CONFIG, tokenizer=tokenizer, model_factory=factory).predict_scores(instances)

    assert list(scores.columns) == ["instance_id", *LABELS]
    assert list(scores["instance_id"]) == [i.instance_id for i in instances]
    assert np.allclose(probabilities(scores).sum(axis=1), 1.0)


def test_scores_equal_the_softmax_of_the_full_models_letter_logits(instances, tiny):
    tokenizer, factory = tiny
    classifier = DecoderClassifier(CONFIG, tokenizer=tokenizer, model_factory=factory)
    first = instances[0]

    scores = probabilities(classifier.predict_scores([first]))[0]

    batch = classifier.tokenizer([plain_prompt(build_prompt(first.text1, first.text2))], return_tensors="pt")
    with torch.no_grad():
        logits = classifier.model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]).logits
    expected = torch.softmax(logits[0, -1, classifier.letter_ids], dim=-1).numpy()
    assert np.allclose(scores, expected, atol=1e-6)


def test_a_score_does_not_depend_on_what_else_is_in_the_batch(instances, tiny):
    tokenizer, factory = tiny
    classifier = DecoderClassifier(CONFIG, tokenizer=tokenizer, model_factory=factory)

    alone = np.vstack([probabilities(classifier.predict_scores([i])) for i in instances])
    together = probabilities(classifier.predict_scores(instances))

    assert np.allclose(alone, together, atol=1e-5)


def test_the_reversed_order_of_a_pair_is_scored_like_its_twin(instances, tiny):
    tokenizer, factory = tiny
    classifier = DecoderClassifier(CONFIG, tokenizer=tokenizer, model_factory=factory)

    forward, reverse = classifier.predict_both_orders(instances)

    forward_by_id = dict(zip(forward["instance_id"], probabilities(forward)))
    reverse_by_id = dict(zip(reverse["instance_id"], probabilities(reverse)))
    twins = [i for i in instances if i.reverse_pair_id]
    assert twins
    for instance in twins:
        assert np.allclose(reverse_by_id[instance.instance_id], forward_by_id[instance.reverse_pair_id], atol=1e-5)


def test_a_prompt_over_the_limit_is_an_error_not_a_truncation(instances, tiny):
    tokenizer, factory = tiny
    short = replace(CONFIG, max_length=8)

    with pytest.raises(ValueError, match="max_length"):
        DecoderClassifier(short, tokenizer=tokenizer, model_factory=factory).predict_scores(instances)
    with pytest.raises(ValueError, match="max_length"):
        DecoderClassifier(short, tokenizer=tokenizer, model_factory=factory).fit(instances)


# --- prediction ---------------------------------------------------------------------------

def test_predict_gives_a_valid_label_for_every_instance(instances, fitted):
    predictions = fitted.predict(instances)

    assert set(predictions) == {i.instance_id for i in instances}
    assert set(predictions.values()) <= set(LABELS)


def test_symmetrized_predictions_of_a_pair_and_its_twin_obey_the_reversal_rule(instances, fitted):
    predictions = fitted.predict(instances, symmetric=True)

    for instance in instances:
        if instance.reverse_pair_id:
            twin = predictions[instance.reverse_pair_id]
            assert twin == reverse_with_negative(predictions[instance.instance_id])


# --- training -----------------------------------------------------------------------------

def test_fit_records_one_history_row_per_epoch_and_keeps_the_best_one(fitted):
    assert [row["epoch"] for row in fitted.history] == [1, 2]
    assert set(fitted.history[0]) >= {"epoch", "train_loss", "train_ce", "train_js", "holdout_weighted_f1", "seconds"}
    assert fitted.best_epoch == max(fitted.history, key=lambda row: row["holdout_weighted_f1"])["epoch"]


def test_fit_trains_the_adapters_and_leaves_the_backbone_frozen(fitted, tiny):
    _, factory = tiny
    trainable = [name for name, parameter in fitted.model.named_parameters() if parameter.requires_grad]
    untouched = factory().state_dict()
    after = fitted.model.get_base_model().state_dict()

    assert trainable and all("lora_" in name for name in trainable)
    for name, weight in untouched.items():
        # peft keeps the original tensors of an adapted layer under "<layer>.base_layer.<tensor>"
        layer, _, tensor = name.rpartition(".")
        wrapped = f"{layer}.base_layer.{tensor}"
        assert torch.equal(after[name] if name in after else after[wrapped], weight), name
    assert any(parameter.abs().sum() > 0 for name, parameter in fitted.model.named_parameters() if "lora_B" in name)


def test_the_loss_is_cross_entropy_plus_the_weighted_consistency_term(instances, tiny, fitted):
    tokenizer, factory = tiny
    plain = DecoderClassifier(replace(CONFIG, consistency_weight=0.0), tokenizer=tokenizer,
                              model_factory=factory).fit(instances, holdout=instances)

    for row in plain.history:
        assert row["train_loss"] == pytest.approx(row["train_ce"])
    for row in fitted.history:
        assert row["train_js"] > 0
        assert row["train_loss"] == pytest.approx(row["train_ce"] + CONFIG.consistency_weight * row["train_js"])


def test_micro_batches_give_the_same_training_as_one_pass_per_step(instances, tiny):
    tokenizer, factory = tiny
    whole_step = replace(CONFIG, lora_dropout=0.0, epochs=1)  # no dropout: it draws per forward pass

    whole = DecoderClassifier(whole_step, tokenizer=tokenizer, model_factory=factory).fit(instances)
    split = DecoderClassifier(replace(whole_step, micro_batch_size=2), tokenizer=tokenizer,
                              model_factory=factory).fit(instances)

    assert split.history[0]["train_loss"] == pytest.approx(whole.history[0]["train_loss"], rel=1e-4)
    assert np.allclose(probabilities(split.predict_scores(instances)),
                       probabilities(whole.predict_scores(instances)), atol=1e-4)


def test_same_seed_gives_the_same_model_and_predictions(instances, tiny, fitted):
    tokenizer, factory = tiny

    again = DecoderClassifier(CONFIG, tokenizer=tokenizer, model_factory=factory).fit(instances, holdout=instances)

    assert again.predict(instances) == fitted.predict(instances)
    assert [r["train_loss"] for r in again.history] == pytest.approx([r["train_loss"] for r in fitted.history])


def test_fit_fails_loudly_when_no_epoch_produces_a_finite_score(instances, tiny):
    tokenizer, factory = tiny

    def broken():
        # What a half-precision backbone does on a GPU: every loss is NaN from the first step.
        model = factory()
        with torch.no_grad():
            model.get_output_embeddings().weight.fill_(float("nan"))
        return model

    for holdout in (None, instances):
        with pytest.raises(RuntimeError, match="finite"):
            DecoderClassifier(CONFIG, tokenizer=tokenizer, model_factory=broken).fit(instances, holdout=holdout)


# --- persistence --------------------------------------------------------------------------

def test_a_saved_and_reloaded_model_gives_identical_scores(instances, tiny, fitted, tmp_path):
    tokenizer, factory = tiny

    fitted.save(tmp_path / "adapter")
    reloaded = DecoderClassifier.load(tmp_path / "adapter", tokenizer=tokenizer, model_factory=factory)

    assert reloaded.config == fitted.config
    assert reloaded.best_epoch == fitted.best_epoch
    assert np.array_equal(probabilities(reloaded.predict_scores(instances)),
                          probabilities(fitted.predict_scores(instances)))


def test_an_untrained_model_has_no_adapter_to_save(tiny, tmp_path):
    tokenizer, factory = tiny

    with pytest.raises(ValueError, match="fit"):
        DecoderClassifier(CONFIG, tokenizer=tokenizer, model_factory=factory).save(tmp_path / "adapter")


def test_an_interrupted_fit_resumes_from_its_last_finished_epoch(instances, tiny, fitted, tmp_path):
    tokenizer, factory = tiny

    class Interrupted(Exception):
        pass

    def stop_after_first_epoch(message):
        if message.startswith("epoch=1 "):
            raise Interrupted

    with pytest.raises(Interrupted):
        DecoderClassifier(CONFIG, tokenizer=tokenizer, model_factory=factory).fit(
            instances, holdout=instances, log=stop_after_first_epoch, checkpoint_dir=tmp_path)
    resumed = DecoderClassifier(CONFIG, tokenizer=tokenizer, model_factory=factory).fit(
        instances, holdout=instances, checkpoint_dir=tmp_path)

    assert [row["epoch"] for row in resumed.history] == [1, 2]
    assert [r["train_loss"] for r in resumed.history] == pytest.approx([r["train_loss"] for r in fitted.history])
    assert resumed.predict(instances) == fitted.predict(instances)


def test_a_checkpoint_from_another_configuration_is_refused(instances, tiny, tmp_path):
    tokenizer, factory = tiny
    DecoderClassifier(replace(CONFIG, epochs=1), tokenizer=tokenizer, model_factory=factory).fit(
        instances, checkpoint_dir=tmp_path)

    with pytest.raises(ValueError, match="checkpoint"):
        DecoderClassifier(replace(CONFIG, epochs=1, seed=42), tokenizer=tokenizer, model_factory=factory).fit(
            instances, checkpoint_dir=tmp_path)
