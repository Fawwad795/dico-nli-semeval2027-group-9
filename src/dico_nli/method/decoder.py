"""Reversal-equivariant LoRA: a frozen decoder LLM scored on four option letters, adapted with
LoRA under a loss that ties the prediction for ``(a, b)`` to the one for ``(b, a)``.

The pair goes into a fixed prompt that asks for one option letter. The classifier reads the
next-token logits of the four letter tokens and applies a softmax over those four only, so a
prediction is one deterministic forward pass with nothing generated and nothing parsed.

Training scores every pair in both orders in the same step::

    L = CE(p(. | a, b), y) + CE(p(. | b, a), Rev(y)) + lambda * JS(p(. | a, b), P p(. | b, a))

``Rev`` and ``P`` come from ``reversal.py`` (NEGATIVE_OTHER maps to itself, by assumption).
``consistency_weight`` is lambda; 0 gives plain LoRA. Epoch selection uses a held-out slice of
the training data passed as ``holdout``; the dev set is never seen during fitting.

``model_factory`` and ``tokenizer`` can be injected, which is how the tests train a tiny
randomly initialised model without downloading anything. Without ``fit`` the classifier scores
with the unadapted backbone (zero-shot).
"""

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.metrics import f1_score
from torch.optim import AdamW

from ..data import LABELS, Instance
from .reversal import REVERSE_INDEX, symmetrize

LABEL_TO_ID = {label: index for index, label in enumerate(LABELS)}
LETTERS: tuple[str, ...] = ("A", "B", "C", "D")  # in LABELS order
CHECKPOINT_NAME = "checkpoint.pt"
RECORD_NAME = "decoder.json"

SYSTEM_PROMPT = "You classify the semantic relation between two short phrases."
USER_TEMPLATE = (
    "Phrase 1: {text1}\n"
    "Phrase 2: {text2}\n\n"
    "Which relation holds?\n"
    "A. Equivalence: the two phrases mean the same.\n"
    "B. Forward entailment: Phrase 1 is more specific, so it entails Phrase 2.\n"
    "C. Backward entailment: Phrase 2 is more specific, so it entails Phrase 1.\n"
    "D. Other: neither phrase entails the other.\n\n"
    "Answer with one letter."
)


def build_prompt(text1: str, text2: str) -> list[dict[str, str]]:
    """The fixed instruction for one ordered pair, as chat messages. It takes the two phrases
    and nothing else: an instance id would leak the label."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(text1=text1, text2=text2)},
    ]


def plain_prompt(messages: Sequence[dict[str, str]]) -> str:
    """The messages as plain text, for a tokenizer that has no chat template."""
    return "\n\n".join(message["content"] for message in messages)


def render_prompt(tokenizer, text1: str, text2: str) -> str:
    """The text the model reads, ending where its answer starts."""
    messages = build_prompt(text1, text2)
    if getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return plain_prompt(messages)


@dataclass(frozen=True)
class DecoderConfig:
    model_name: str = "Qwen/Qwen2.5-1.5B-Instruct"
    lora_rank: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: tuple[str, ...] = ("q_proj", "k_proj", "v_proj", "o_proj")
    max_length: int = 160
    batch_size: int = 16
    epochs: int = 3
    learning_rate: float = 2e-4
    warmup_fraction: float = 0.06
    weight_decay: float = 0.01
    consistency_weight: float = 1.0
    # Memory levers that leave the optimisation step as it is: ``micro_batch_size`` runs a step's
    # pairs through the model a few at a time and adds up the gradients (the loss is a mean over
    # pairs, so the step is the same); ``mixed_precision`` computes activations in bfloat16 on a
    # GPU while the weights stay float32.
    micro_batch_size: int | None = None
    mixed_precision: bool = False
    seed: int = 13


class DecoderClassifier:
    def __init__(
        self,
        config: DecoderConfig,
        tokenizer=None,
        model_factory: Callable[[], torch.nn.Module] | None = None,
        device: str | None = None,
    ) -> None:
        self.config = config
        self._tokenizer = tokenizer
        self._model_factory = model_factory
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model: torch.nn.Module | None = None
        self.history: list[dict] = []
        self.best_epoch: int | None = None
        self._letter_ids: list[int] | None = None

    # --- tokenizer and model ----------------------------------------------------------------

    @property
    def tokenizer(self):
        if self._tokenizer is None:
            from transformers import AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
        # Pad on the left, so the last position of every row is the answer position.
        self._tokenizer.padding_side = "left"
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token
        return self._tokenizer

    @property
    def letter_ids(self) -> list[int]:
        """The token id of each option letter; every letter must be exactly one known token."""
        if self._letter_ids is None:
            ids = []
            for letter in LETTERS:
                encoded = self.tokenizer.encode(letter, add_special_tokens=False)
                if len(encoded) != 1 or encoded[0] == self.tokenizer.unk_token_id:
                    raise ValueError(f"option letter {letter!r} is not one token for this tokenizer: {encoded}")
                ids.append(encoded[0])
            self._letter_ids = ids
        return self._letter_ids

    def _new_backbone(self) -> torch.nn.Module:
        if self._model_factory is not None:
            return self._model_factory()
        from transformers import AutoModelForCausalLM

        # transformers 5 loads a checkpoint in its stored dtype; train and score in float32.
        return AutoModelForCausalLM.from_pretrained(self.config.model_name, dtype=torch.float32)

    def _ensure_model(self) -> torch.nn.Module:
        if self.model is None:
            self.model = self._new_backbone().to(self.device)
        return self.model

    def _autocast(self):
        enabled = self.config.mixed_precision and self.device.type == "cuda"
        return torch.autocast(device_type=self.device.type, dtype=torch.bfloat16, enabled=enabled)

    # --- scoring ----------------------------------------------------------------------------

    def max_prompt_tokens(self, instances: Sequence[Instance]) -> int:
        """The longest prompt over both orders of every instance, in tokens."""
        texts = [render_prompt(self.tokenizer, a, b)
                 for i in instances for a, b in ((i.text1, i.text2), (i.text2, i.text1))]
        return max(len(ids) for ids in self.tokenizer(texts)["input_ids"])

    def _check_length(self, tokens: int) -> None:
        if tokens > self.config.max_length:
            raise ValueError(
                f"a prompt has {tokens} tokens, over max_length={self.config.max_length}; "
                "prompts are never truncated, because that would cut off the answer position"
            )

    def _letter_log_probs(self, pairs: Sequence[tuple[str, str]]) -> torch.Tensor:
        """Log-probabilities over the four letters at the answer position, one row per pair."""
        batch = self.tokenizer([render_prompt(self.tokenizer, a, b) for a, b in pairs],
                               return_tensors="pt", padding=True)
        self._check_length(batch["input_ids"].shape[1])
        model = self._ensure_model()
        # Run the transformer body and apply the output layer to the last position and the four
        # letter rows only; the full vocabulary logits at every position are never built.
        causal_lm = model.get_base_model() if hasattr(model, "get_base_model") else model
        head = causal_lm.get_output_embeddings()
        with self._autocast():
            hidden = causal_lm.base_model(
                input_ids=batch["input_ids"].to(self.device),
                attention_mask=batch["attention_mask"].to(self.device),
            ).last_hidden_state[:, -1, :]
            bias = None if head.bias is None else head.bias[self.letter_ids]
            logits = F.linear(hidden, head.weight[self.letter_ids], bias)
        return F.log_softmax(logits.float(), dim=-1)

    def _frame(self, instances: Sequence[Instance], probabilities: np.ndarray) -> pd.DataFrame:
        frame = pd.DataFrame(probabilities, columns=list(LABELS))
        frame.insert(0, "instance_id", [i.instance_id for i in instances])
        return frame

    @torch.no_grad()
    def _probabilities(self, pairs: Sequence[tuple[str, str]], batch_size: int) -> np.ndarray:
        self._ensure_model().eval()
        chunks = [self._letter_log_probs(pairs[start:start + batch_size]).exp().cpu().numpy()
                  for start in range(0, len(pairs), batch_size)]
        return np.vstack(chunks)

    def predict_both_orders(self, instances: Sequence[Instance], batch_size: int = 32) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Two frames, one row per instance: the distribution for ``(text1, text2)`` and the one
        for ``(text2, text1)`` exactly as the model gives it for that reversed input."""
        forward = self._probabilities([(i.text1, i.text2) for i in instances], batch_size)
        reverse = self._probabilities([(i.text2, i.text1) for i in instances], batch_size)
        return self._frame(instances, forward), self._frame(instances, reverse)

    def predict_scores(self, instances: Sequence[Instance], symmetric: bool = False, batch_size: int = 32) -> pd.DataFrame:
        """Probability per label, one row per instance in the given order. ``symmetric`` averages
        the two orders of each pair (symmetrized decoding) at the cost of a second pass."""
        if not symmetric:
            return self._frame(instances, self._probabilities([(i.text1, i.text2) for i in instances], batch_size))
        forward, reverse = self.predict_both_orders(instances, batch_size)
        return self._frame(instances, symmetrize(forward[list(LABELS)].to_numpy(), reverse[list(LABELS)].to_numpy()))

    def predict(self, instances: Sequence[Instance], symmetric: bool = False) -> dict[str, str]:
        scores = self.predict_scores(instances, symmetric=symmetric)
        best = scores[list(LABELS)].to_numpy().argmax(axis=1)
        return {instance_id: LABELS[k] for instance_id, k in zip(scores["instance_id"], best)}

    # --- training ---------------------------------------------------------------------------

    def _trainable_state(self) -> dict[str, torch.Tensor]:
        return {name: parameter.detach().cpu().clone()
                for name, parameter in self.model.named_parameters() if parameter.requires_grad}

    def fit(
        self,
        train: Sequence[Instance],
        holdout: Sequence[Instance] | None = None,
        log=None,
        checkpoint_dir: Path | str | None = None,
    ) -> "DecoderClassifier":
        """Train the adapters for ``config.epochs`` and keep the epoch with the best held-out
        weighted F1 (single-pass decoding), or the lowest training loss when no holdout is given.

        With ``checkpoint_dir`` the state is written after every epoch, and a later call with the
        same configuration continues from the last finished epoch instead of starting over.
        """
        from peft import LoraConfig, get_peft_model
        from transformers import get_linear_schedule_with_warmup, set_seed

        cfg = self.config
        self._check_length(self.max_prompt_tokens([*train, *(holdout or [])]))
        backbone = self._new_backbone()
        set_seed(cfg.seed)  # after the backbone exists, so the seed governs the adapters
        self.model = get_peft_model(backbone, LoraConfig(
            r=cfg.lora_rank, lora_alpha=cfg.lora_alpha, lora_dropout=cfg.lora_dropout,
            target_modules=list(cfg.target_modules), task_type="CAUSAL_LM",
        )).to(self.device)
        parameters = [p for p in self.model.parameters() if p.requires_grad]
        labels = torch.tensor([LABEL_TO_ID[i.label] for i in train])
        reverse_index = torch.tensor(REVERSE_INDEX, device=self.device)
        total_steps = math.ceil(len(train) / cfg.batch_size) * cfg.epochs
        optimizer = AdamW(parameters, lr=cfg.learning_rate, weight_decay=cfg.weight_decay)
        scheduler = get_linear_schedule_with_warmup(optimizer, int(cfg.warmup_fraction * total_steps), total_steps)
        generator = torch.Generator().manual_seed(cfg.seed)

        self.history, self.best_epoch = [], None
        best_score, best_state, first_epoch = -math.inf, None, 1
        checkpoint = Path(checkpoint_dir) / CHECKPOINT_NAME if checkpoint_dir else None
        if checkpoint is not None and checkpoint.exists():
            saved = torch.load(checkpoint, map_location="cpu", weights_only=False)
            if saved["config"] != asdict(cfg):
                raise ValueError(f"the checkpoint at {checkpoint} was written under another configuration")
            self.model.load_state_dict(saved["trainable"], strict=False)
            optimizer.load_state_dict(saved["optimizer"])
            scheduler.load_state_dict(saved["scheduler"])
            generator.set_state(saved["generator"])
            torch.set_rng_state(saved["torch_rng"])
            if saved["cuda_rng"] is not None and torch.cuda.is_available():
                torch.cuda.set_rng_state_all(saved["cuda_rng"])
            self.history, self.best_epoch = saved["history"], saved["best_epoch"]
            best_score, best_state, first_epoch = saved["best_score"], saved["best_state"], saved["epoch"] + 1
            if log:
                log(f"resumed after epoch {saved['epoch']} from {checkpoint}")

        for epoch in range(first_epoch, cfg.epochs + 1):
            started = time.time()
            self.model.train()
            order = torch.randperm(len(train), generator=generator)
            totals = {"train_loss": 0.0, "train_ce": 0.0, "train_js": 0.0}
            for start in range(0, len(train), cfg.batch_size):
                index = order[start:start + cfg.batch_size]
                batch = [train[i] for i in index.tolist()]
                gold = labels[index].to(self.device)
                step = {"train_loss": 0.0, "train_ce": 0.0, "train_js": 0.0}
                micro = cfg.micro_batch_size or len(batch)
                for offset in range(0, len(batch), micro):
                    part, target = batch[offset:offset + micro], gold[offset:offset + micro]
                    forward = self._letter_log_probs([(i.text1, i.text2) for i in part])
                    # The reversed order, mapped back into the label space of (a, b): a cross-entropy
                    # against y here is the cross-entropy of p(. | b, a) against Rev(y).
                    reverse = self._letter_log_probs([(i.text2, i.text1) for i in part])[:, reverse_index]
                    ce = F.nll_loss(forward, target) + F.nll_loss(reverse, target)
                    mixture = torch.logsumexp(torch.stack([forward, reverse]), dim=0) - math.log(2)
                    js = 0.5 * (F.kl_div(mixture, forward, reduction="batchmean", log_target=True)
                                + F.kl_div(mixture, reverse, reduction="batchmean", log_target=True))
                    loss = ce + cfg.consistency_weight * js
                    share = len(part) / len(batch)  # every term is a mean over the pairs of the part
                    (loss * share).backward()
                    for key, value in (("train_loss", loss), ("train_ce", ce), ("train_js", js)):
                        step[key] += value.item() * share
                torch.nn.utils.clip_grad_norm_(parameters, 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
                if log and epoch == 1 and start == 0:
                    log(f"first_loss={step['train_loss']:.4f}")
                for key in totals:
                    totals[key] += step[key] * len(index)
            row = {"epoch": epoch, **{key: value / len(train) for key, value in totals.items()}}
            if holdout:
                predictions = self.predict(holdout)
                gold_labels = [i.label for i in holdout]
                predicted = [predictions[i.instance_id] for i in holdout]
                row["holdout_weighted_f1"] = float(f1_score(gold_labels, predicted, average="weighted"))
                row["holdout_accuracy"] = float(np.mean([g == p for g, p in zip(gold_labels, predicted)]))
                score = row["holdout_weighted_f1"] if math.isfinite(row["train_loss"]) else -math.inf
            else:
                score = -row["train_loss"]
            if score > best_score:
                best_score, best_state, self.best_epoch = score, self._trainable_state(), epoch
            row["seconds"] = round(time.time() - started, 1)
            self.history.append(row)
            if checkpoint is not None:
                checkpoint.parent.mkdir(parents=True, exist_ok=True)
                partial = checkpoint.with_suffix(".partial")
                torch.save({
                    "config": asdict(cfg), "epoch": epoch, "trainable": self._trainable_state(),
                    "optimizer": optimizer.state_dict(), "scheduler": scheduler.state_dict(),
                    "generator": generator.get_state(), "torch_rng": torch.get_rng_state(),
                    "cuda_rng": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
                    "history": self.history, "best_epoch": self.best_epoch,
                    "best_score": best_score, "best_state": best_state,
                }, partial)
                os.replace(partial, checkpoint)
            if log:
                log(" ".join(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}" for k, v in row.items()))
        if best_state is None:
            raise RuntimeError(
                "training produced no finite score in any epoch (loss was NaN or infinite); "
                "check the model dtype and the learning rate"
            )
        self.model.load_state_dict(best_state, strict=False)
        return self

    # --- persistence ------------------------------------------------------------------------

    def save(self, path: Path | str) -> None:
        """Write the adapter weights and the configuration; the frozen backbone is not copied."""
        if self.model is None or not hasattr(self.model, "get_base_model"):
            raise ValueError("there is no adapter to save; call fit first")
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        self.model.save_pretrained(str(path))
        record = {"config": asdict(self.config), "history": self.history, "best_epoch": self.best_epoch}
        (path / RECORD_NAME).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(
        cls,
        path: Path | str,
        tokenizer=None,
        model_factory: Callable[[], torch.nn.Module] | None = None,
        device: str | None = None,
    ) -> "DecoderClassifier":
        from peft import PeftModel

        path = Path(path)
        record = json.loads((path / RECORD_NAME).read_text(encoding="utf-8"))
        settings = dict(record["config"])
        settings["target_modules"] = tuple(settings["target_modules"])
        classifier = cls(DecoderConfig(**settings), tokenizer=tokenizer, model_factory=model_factory, device=device)
        classifier.model = PeftModel.from_pretrained(classifier._new_backbone(), str(path)).to(classifier.device)
        classifier.history, classifier.best_epoch = record["history"], record["best_epoch"]
        return classifier
