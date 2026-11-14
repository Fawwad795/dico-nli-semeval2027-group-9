"""Fixture rows through the decoder method and the official scorer, end to end: prompts, LoRA
training with the consistency loss, both decodings, the official prediction format."""

from dico_nli.data import read_instances
from dico_nli.method.decoder import DecoderClassifier, DecoderConfig
from dico_nli.scoring import score, write_predictions
from tests.support import FIXTURE_REFERENCE, requires_data_clone, tiny_decoder

CONFIG = DecoderConfig(model_name="tiny-for-tests", lora_rank=4, lora_alpha=8, max_length=128, batch_size=4,
                       epochs=1, learning_rate=1e-2, weight_decay=0.0, consistency_weight=1.0, seed=13)


@requires_data_clone
def test_the_method_trains_predicts_and_is_scored_by_the_official_scorer(tmp_path):
    instances = read_instances(FIXTURE_REFERENCE)
    tokenizer, factory = tiny_decoder(instances)
    classifier = DecoderClassifier(CONFIG, tokenizer=tokenizer, model_factory=factory).fit(instances, holdout=instances)

    results = {}
    for name, symmetric in (("single", False), ("symmetrized", True)):
        predictions = write_predictions(tmp_path / f"{name}.csv", classifier.predict(instances, symmetric=symmetric))
        results[name] = score(FIXTURE_REFERENCE, predictions, tmp_path / name)

    for result in results.values():
        for value in (result.weighted_f1, result.soft_cons, result.hard_cons):
            assert 0.0 <= value <= 1.0
    # Symmetrized decoding makes every reversible pair obey the reversal rule by construction.
    assert results["symmetrized"].soft_cons == 1.0
