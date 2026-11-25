"""dico_nli.method.decoder: prompt, label scoring, LoRA training with the consistency loss.

The tests build a one-layer randomly initialised Qwen2 causal LM and a word-level tokenizer
over the words of the fixture's prompts, so nothing is downloaded and a fit takes seconds on a
CPU. The LoRA target modules carry the same names as in the real backbone.
"""

import inspect
import json
import math
from dataclasses import replace

import numpy as np
import pytest
import torch
import torch.nn.functional as F

from dico_nli.data import LABELS, read_instances
from dico_nli.method.decoder import (
    ANSWER_WORDS,
    LETTERS,
    RECORD_NAME,
    DecoderClassifier,
    DecoderConfig,
    build_prompt,
    pair_loss,
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
def tiny_words(instances):
    return tiny_decoder(instances, answer_format="words")


@pytest.fixture(scope="module")
def fitted(instances, tiny):
    tokenizer, factory = tiny
    return DecoderClassifier(CONFIG, tokenizer=tokenizer, model_factory=factory).fit(instances, holdout=instances)


def probabilities(frame):
    return frame[list(LABELS)].to_numpy()


# --- prompt -------------------------------------------------------------------------------

def test_build_prompt_takes_the_two_phrases_and_the_answer_format_only():
    parameters = inspect.signature(build_prompt).parameters

    assert list(parameters) == ["text1", "text2", "answer_format"]  # no instance id: it would leak the label
    assert parameters["answer_format"].kind is inspect.Parameter.KEYWORD_ONLY
    assert build_prompt("a red car", "a car") == build_prompt("a red car", "a car", answer_format="letters")


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


def test_the_words_prompt_keeps_the_phrase_lines_and_drops_every_option_letter():
    text = plain_prompt(build_prompt("a red car", "a car", answer_format="words"))

    assert build_prompt("a red car", "a car", answer_format="words")[0] == build_prompt("a red car", "a car")[0]
    assert "Phrase 1: a red car\nPhrase 2: a car" in text
    for letter in LETTERS:
        assert f"{letter}. " not in text
    for word in ANSWER_WORDS:
        assert f"\n{word}: " in text
    assert text.endswith("Answer with one word: Equivalence, Forward, Backward or Other.")


def test_there_is_one_answer_word_per_label():
    assert len(ANSWER_WORDS) == len(LABELS) == len(set(ANSWER_WORDS))


def test_an_unknown_answer_format_is_an_error():
    with pytest.raises(ValueError, match="answer_format"):
        build_prompt("a red car", "a car", answer_format="numbers")
    with pytest.raises(ValueError, match="answer_format"):
        DecoderConfig(answer_format="numbers")


# --- label scoring ------------------------------------------------------------------------

def test_a_letter_that_is_not_one_known_token_fails_loudly(tiny):
    _, factory = tiny
    tokenizer, _ = word_level_tokenizer(["A B C phrase"])  # no D in the vocabulary

    with pytest.raises(ValueError, match="one token"):
        DecoderClassifier(CONFIG, tokenizer=tokenizer, model_factory=factory).letter_ids


def test_letters_mode_scores_the_letter_tokens(tiny):
    tokenizer, factory = tiny

    classifier = DecoderClassifier(CONFIG, tokenizer=tokenizer, model_factory=factory)

    assert classifier.answer_ids == classifier.letter_ids


def test_words_mode_scores_the_first_token_of_each_answer_word(instances, tiny_words):
    tokenizer, factory = tiny_words
    classifier = DecoderClassifier(replace(CONFIG, answer_format="words"), tokenizer=tokenizer, model_factory=factory)
    first = instances[0]

    scores = probabilities(classifier.predict_scores([first]))[0]

    word_ids = [tokenizer.encode(word, add_special_tokens=False)[0] for word in ANSWER_WORDS]
    prompt = plain_prompt(build_prompt(first.text1, first.text2, answer_format="words"))
    batch = classifier.tokenizer([prompt], return_tensors="pt")
    with torch.no_grad():
        logits = classifier.model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]).logits
    assert classifier.answer_ids == word_ids
    assert np.allclose(scores, torch.softmax(logits[0, -1, word_ids], dim=-1).numpy(), atol=1e-6)


class SplittingTokenizer:
    """Stands in for a subword tokenizer: an answer word can be several tokens."""

    unk_token_id = 1
    pad_token = "[PAD]"
    padding_side = "left"

    def __init__(self, pieces):
        self.pieces = pieces

    def encode(self, text, add_special_tokens=False):
        return self.pieces[text]


def test_words_mode_takes_the_first_token_of_a_word_that_is_several_tokens(tiny):
    _, factory = tiny
    tokenizer = SplittingTokenizer({"Equivalence": [5, 9], "Forward": [6], "Backward": [7, 10], "Other": [8]})

    classifier = DecoderClassifier(replace(CONFIG, answer_format="words"), tokenizer=tokenizer, model_factory=factory)

    assert classifier.answer_ids == [5, 6, 7, 8]


def test_answer_words_that_share_a_first_token_fail_loudly(tiny):
    _, factory = tiny
    tokenizer = SplittingTokenizer({"Equivalence": [5, 9], "Forward": [6], "Backward": [5, 7], "Other": [8]})

    with pytest.raises(ValueError, match="distinct"):
        DecoderClassifier(replace(CONFIG, answer_format="words"), tokenizer=tokenizer, model_factory=factory).answer_ids


def test_an_answer_word_the_tokenizer_does_not_know_fails_loudly(tiny):
    _, factory = tiny
    tokenizer, _ = word_level_tokenizer(["Equivalence Forward Backward phrase"])  # no Other in the vocabulary

    with pytest.raises(ValueError, match="known token"):
        DecoderClassifier(replace(CONFIG, answer_format="words"), tokenizer=tokenizer, model_factory=factory).answer_ids


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


NEGATIVE = LABELS.index("NEGATIVE_OTHER")


def log_probabilities(seed, rows):
    generator = torch.Generator().manual_seed(seed)
    return torch.log_softmax(torch.randn(rows, len(LABELS), generator=generator), dim=-1)


def loss_as_first_run(forward, reverse, target, consistency_weight):
    """The loss statements of the code the Assignment 2 runs were made with, in their order."""
    ce = F.nll_loss(forward, target) + F.nll_loss(reverse, target)
    mixture = torch.logsumexp(torch.stack([forward, reverse]), dim=0) - math.log(2)
    js = 0.5 * (F.kl_div(mixture, forward, reduction="batchmean", log_target=True)
                + F.kl_div(mixture, reverse, reduction="batchmean", log_target=True))
    return ce + consistency_weight * js


def test_the_default_loss_and_its_gradients_are_bitwise_those_of_the_first_runs():
    """Reordering the default statements keeps the loss and changes the last digits of its
    gradients (seen on 2026-11-26), which would make a rerun of an earlier seed drift."""
    def loss_and_gradients(loss_function, seed):
        generator = torch.Generator().manual_seed(seed)
        logits_forward = torch.randn(16, len(LABELS), generator=generator, requires_grad=True)
        logits_reverse = torch.randn(16, len(LABELS), generator=generator, requires_grad=True)
        target = torch.randint(0, len(LABELS), (16,), generator=generator)
        loss = loss_function(torch.log_softmax(logits_forward, dim=-1), torch.log_softmax(logits_reverse, dim=-1),
                             target, 0.5)
        return loss, torch.autograd.grad(loss, (logits_forward, logits_reverse))

    for seed in range(5):
        expected_loss, expected_gradients = loss_and_gradients(loss_as_first_run, seed)
        loss, gradients = loss_and_gradients(lambda *arguments: pair_loss(*arguments)[0], seed)

        assert torch.equal(loss, expected_loss)
        for gradient, expected in zip(gradients, expected_gradients, strict=True):
            assert torch.equal(gradient, expected)


def test_without_negatives_in_the_batch_leaving_out_their_reversal_changes_nothing():
    forward, reverse = log_probabilities(1, 6), log_probabilities(2, 6)
    target = torch.tensor([0, 1, 2, 0, 1, 2])

    default = pair_loss(forward, reverse, target, 0.5)
    masked = pair_loss(forward, reverse, target, 0.5, reverse_negatives=False)

    assert default[2].item() > 0
    for with_reversal, without in zip(default, masked, strict=True):
        assert without.item() == pytest.approx(with_reversal.item(), rel=1e-6)


def test_with_only_negatives_the_loss_without_their_reversal_is_the_forward_cross_entropy():
    forward, reverse = log_probabilities(1, 5), log_probabilities(2, 5)
    target = torch.full((5,), NEGATIVE)

    loss, ce, js = pair_loss(forward, reverse, target, 0.5, reverse_negatives=False)

    forward_ce = F.nll_loss(forward, target).item()
    assert loss.item() == pytest.approx(forward_ce, rel=1e-6)
    assert ce.item() == pytest.approx(forward_ce, rel=1e-6)
    assert js.item() == 0.0
    assert pair_loss(forward, reverse, target, 0.5)[0].item() > loss.item()


def test_the_loss_without_reversed_negatives_still_divides_by_every_pair_of_the_micro_batch():
    forward, reverse = log_probabilities(1, 4), log_probabilities(2, 4)
    target = torch.tensor([0, NEGATIVE, 1, NEGATIVE])

    loss, ce, js = pair_loss(forward, reverse, target, 0.5, reverse_negatives=False)

    rows, kept = torch.arange(4), torch.tensor([0, 2])
    mixture = torch.log(0.5 * (forward.exp() + reverse.exp()))
    js_per_pair = 0.5 * ((forward.exp() * (forward - mixture)).sum(dim=1)
                         + (reverse.exp() * (reverse - mixture)).sum(dim=1))
    expected_ce = (-forward[rows, target].sum() - reverse[kept, target[kept]].sum()) / 4
    expected_js = js_per_pair[kept].sum() / 4
    assert ce.item() == pytest.approx(expected_ce.item(), rel=1e-5)
    assert js.item() == pytest.approx(expected_js.item(), rel=1e-5)
    assert loss.item() == pytest.approx((expected_ce + 0.5 * expected_js).item(), rel=1e-5)


def test_fit_without_reversed_negatives_trains_on_a_different_loss(instances, tiny, fitted):
    tokenizer, factory = tiny
    config = replace(CONFIG, reverse_negatives=False)

    masked = DecoderClassifier(config, tokenizer=tokenizer, model_factory=factory).fit(instances, holdout=instances)

    for row in masked.history:
        assert row["train_loss"] == pytest.approx(row["train_ce"] + config.consistency_weight * row["train_js"])
    assert masked.history[0]["train_ce"] < fitted.history[0]["train_ce"]  # the fixture has four negatives


def test_fit_in_words_mode_trains_and_predicts(instances, tiny_words):
    tokenizer, factory = tiny_words
    config = replace(CONFIG, answer_format="words", epochs=1)

    classifier = DecoderClassifier(config, tokenizer=tokenizer, model_factory=factory).fit(instances, holdout=instances)

    assert set(classifier.predict(instances).values()) <= set(LABELS)
    assert np.allclose(probabilities(classifier.predict_scores(instances)).sum(axis=1), 1.0)


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


# Recorded on 2026-11-26 from the code as merged for Assignment 2 (commit 04f4f75), before the
# options for the Assignment 3 ablations were added: CONFIG on the tiny model and the fixture.
PINNED_FIRST_LOSS = "first_loss=2.7535"
PINNED_HISTORY = [
    {"train_loss": 2.7839712301890054, "train_ce": 2.7774779001871743, "train_js": 0.006493336676309506,
     "holdout_weighted_f1": 0.047619047619047616},
    {"train_loss": 2.769115765889486, "train_ce": 2.7632569471995034, "train_js": 0.005858884037782748,
     "holdout_weighted_f1": 0.17500000000000002},
]
PINNED_FORWARD = [
    [0.2742151, 0.20170169, 0.27409947, 0.24998373],
    [0.27421758, 0.2017026, 0.27410212, 0.24997765],
    [0.27397165, 0.20138086, 0.27512515, 0.24952231],
    [0.27397048, 0.20137696, 0.27512854, 0.24952406],
    [0.2738067, 0.20182635, 0.2761854, 0.24818164],
    [0.2738063, 0.20182592, 0.27618164, 0.24818623],
    [0.27469724, 0.20121996, 0.27360088, 0.25048187],
    [0.27470177, 0.201218, 0.27359852, 0.25048167],
    [0.2730756, 0.20207202, 0.27671924, 0.24813315],
    [0.27487433, 0.20025524, 0.27257705, 0.2522935],
    [0.27429366, 0.20156102, 0.274114, 0.25003132],
    [0.2741409, 0.20120576, 0.27503687, 0.24961638],
]
PINNED_REVERSE = [
    [0.27421758, 0.2017026, 0.27410212, 0.24997765],
    [0.2742151, 0.20170169, 0.27409947, 0.24998373],
    [0.27397048, 0.20137696, 0.27512854, 0.24952406],
    [0.27397165, 0.20138086, 0.27512515, 0.24952231],
    [0.2738063, 0.20182592, 0.27618164, 0.24818623],
    [0.27380666, 0.20182632, 0.27618536, 0.24818161],
    [0.27470177, 0.201218, 0.27359852, 0.25048167],
    [0.27469724, 0.20121996, 0.27360088, 0.25048187],
    [0.27308118, 0.20206411, 0.27670476, 0.24814984],
    [0.27487442, 0.20025966, 0.2725814, 0.2522845],
    [0.27429393, 0.20156118, 0.2741132, 0.25003174],
    [0.27414408, 0.20120548, 0.27503112, 0.24961923],
]


def test_the_default_training_path_is_pinned(instances, tiny):
    """The default configuration must train and score exactly as it did before the ablation
    options existed. That is what makes a rerun of an earlier seed a valid repeat check."""
    tokenizer, factory = tiny
    lines = []

    classifier = DecoderClassifier(CONFIG, tokenizer=tokenizer, model_factory=factory).fit(
        instances, holdout=instances, log=lines.append)
    forward, reverse = classifier.predict_both_orders(instances)

    assert [line for line in lines if line.startswith("first_loss")] == [PINNED_FIRST_LOSS]
    assert classifier.best_epoch == 2
    for row, pinned in zip(classifier.history, PINNED_HISTORY, strict=True):
        for key, value in pinned.items():
            assert row[key] == pytest.approx(value, rel=1e-5), (row["epoch"], key)
    assert np.allclose(probabilities(forward), PINNED_FORWARD, atol=1e-5)
    assert np.allclose(probabilities(reverse), PINNED_REVERSE, atol=1e-5)


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


def test_an_interrupted_fit_with_the_ablation_options_resumes_like_an_uninterrupted_one(instances, tiny_words, tmp_path):
    tokenizer, factory = tiny_words
    config = replace(CONFIG, reverse_negatives=False, answer_format="words")

    class Interrupted(Exception):
        pass

    def stop_after_first_epoch(message):
        if message.startswith("epoch=1 "):
            raise Interrupted

    whole = DecoderClassifier(config, tokenizer=tokenizer, model_factory=factory).fit(instances, holdout=instances)
    with pytest.raises(Interrupted):
        DecoderClassifier(config, tokenizer=tokenizer, model_factory=factory).fit(
            instances, holdout=instances, log=stop_after_first_epoch, checkpoint_dir=tmp_path)
    resumed = DecoderClassifier(config, tokenizer=tokenizer, model_factory=factory).fit(
        instances, holdout=instances, checkpoint_dir=tmp_path)

    assert [r["train_loss"] for r in resumed.history] == pytest.approx([r["train_loss"] for r in whole.history])
    assert resumed.predict(instances) == whole.predict(instances)


def test_a_checkpoint_written_with_reversed_negatives_is_refused_without_them(instances, tiny, tmp_path):
    tokenizer, factory = tiny
    DecoderClassifier(replace(CONFIG, epochs=1), tokenizer=tokenizer, model_factory=factory).fit(
        instances, checkpoint_dir=tmp_path)

    with pytest.raises(ValueError, match="checkpoint"):
        DecoderClassifier(replace(CONFIG, epochs=1, reverse_negatives=False), tokenizer=tokenizer,
                          model_factory=factory).fit(instances, checkpoint_dir=tmp_path)


def test_an_adapter_saved_before_the_ablation_options_existed_still_loads(instances, tiny, fitted, tmp_path):
    tokenizer, factory = tiny
    fitted.save(tmp_path / "adapter")
    record_path = tmp_path / "adapter" / RECORD_NAME
    record = json.loads(record_path.read_text(encoding="utf-8"))
    for added in ("reverse_negatives", "answer_format"):
        del record["config"][added]  # the preliminary run's decoder.json has neither
    record_path.write_text(json.dumps(record), encoding="utf-8")

    reloaded = DecoderClassifier.load(tmp_path / "adapter", tokenizer=tokenizer, model_factory=factory)

    assert reloaded.config == fitted.config
    assert np.array_equal(probabilities(reloaded.predict_scores(instances)),
                          probabilities(fitted.predict_scores(instances)))
