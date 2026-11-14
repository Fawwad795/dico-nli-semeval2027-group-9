"""Paths and markers shared by the test suite."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
FIXTURE_REFERENCE = FIXTURES / "track1_reference_sample.csv"
DATA_CLONE = REPO_ROOT / "datasets" / "dico-nli"

def word_level_tokenizer(texts):
    """A tokenizer whose vocabulary is the words and punctuation marks of ``texts``, and its size."""
    from tokenizers import Tokenizer, models, pre_tokenizers
    from transformers import PreTrainedTokenizerFast

    splitter = pre_tokenizers.Whitespace()
    words = sorted({word for text in texts for word, _ in splitter.pre_tokenize_str(text)})
    vocab = ["[PAD]", "[UNK]"] + words
    raw = Tokenizer(models.WordLevel({word: k for k, word in enumerate(vocab)}, unk_token="[UNK]"))
    raw.pre_tokenizer = splitter
    return PreTrainedTokenizerFast(tokenizer_object=raw, pad_token="[PAD]", unk_token="[UNK]"), len(vocab)


def tiny_decoder(instances):
    """``(tokenizer, model_factory)`` for a one-layer randomly initialised Qwen2 causal LM over
    the words of the instances' prompts. Nothing is downloaded, and the attention projections
    carry the same names as in the real backbone, so LoRA attaches the same way."""
    import torch
    from transformers import Qwen2Config, Qwen2ForCausalLM

    from dico_nli.method.decoder import build_prompt, plain_prompt

    prompts = [plain_prompt(build_prompt(a, b))
               for i in instances for a, b in ((i.text1, i.text2), (i.text2, i.text1))]
    tokenizer, vocab_size = word_level_tokenizer(prompts)

    def factory():
        torch.manual_seed(0)  # the same frozen backbone every time, like a downloaded checkpoint
        return Qwen2ForCausalLM(Qwen2Config(
            vocab_size=vocab_size, hidden_size=32, intermediate_size=64, num_hidden_layers=1,
            num_attention_heads=2, num_key_value_heads=2, max_position_embeddings=256, pad_token_id=0,
        ))

    return tokenizer, factory


requires_data_clone = pytest.mark.skipif(
    not (DATA_CLONE / "evaluation_functions" / "__main__.py").exists(),
    reason=(
        "the task repository is not cloned at datasets/dico-nli; "
        "see datasets/dico-nli.json for the download command"
    ),
)
