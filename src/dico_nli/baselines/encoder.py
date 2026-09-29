"""Fine-tuned encoder baseline: a Hugging Face sequence-pair classifier trained with a compact,
seeded PyTorch loop (no ``Trainer``, so every step is visible and no extra dependency).

Epoch selection uses a held-out slice of the training data passed as ``holdout``; the dev set
is never seen during fitting. ``model_factory`` and ``tokenizer`` can be injected, which is how
the tests train a tiny randomly initialised model without downloading anything.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import f1_score
from torch.optim import AdamW

from ..data import LABELS, Instance

LABEL_TO_ID = {label: index for index, label in enumerate(LABELS)}


@dataclass(frozen=True)
class EncoderConfig:
    model_name: str = "microsoft/deberta-v3-base"
    max_length: int = 32
    batch_size: int = 16
    epochs: int = 5
    learning_rate: float = 2e-5
    warmup_fraction: float = 0.06
    weight_decay: float = 0.01
    seed: int = 13


def encode_pairs(tokenizer, instances: Sequence[Instance], max_length: int):
    """Tokenize ``(text1, text2)`` pairs as one sequence each, truncated and padded per batch."""
    return tokenizer(
        [i.text1 for i in instances],
        [i.text2 for i in instances],
        truncation=True,
        max_length=max_length,
        padding=True,
        return_tensors="pt",
    )


class EncoderBaseline:
    def __init__(
        self,
        config: EncoderConfig,
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

    @property
    def tokenizer(self):
        if self._tokenizer is None:
            from transformers import AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
        return self._tokenizer

    def _new_model(self) -> torch.nn.Module:
        if self._model_factory is not None:
            return self._model_factory()
        from transformers import AutoModelForSequenceClassification

        # transformers 5 loads a checkpoint in its stored dtype; deberta-v3-base stores float16,
        # and fine-tuning in pure half precision produces NaN losses. Train in float32.
        return AutoModelForSequenceClassification.from_pretrained(
            self.config.model_name,
            num_labels=len(LABELS),
            id2label=dict(enumerate(LABELS)),
            label2id=LABEL_TO_ID,
            dtype=torch.float32,
        )

    def fit(self, train: Sequence[Instance], holdout: Sequence[Instance] | None = None, log=None) -> "EncoderBaseline":
        """Train for ``config.epochs`` and keep the epoch with the best held-out weighted F1
        (or the lowest training loss when no holdout is given)."""
        from transformers import get_linear_schedule_with_warmup, set_seed

        cfg = self.config
        set_seed(cfg.seed)
        self.model = self._new_model().to(self.device)
        labels = torch.tensor([LABEL_TO_ID[i.label] for i in train])
        total_steps = math.ceil(len(train) / cfg.batch_size) * cfg.epochs
        optimizer = AdamW(self.model.parameters(), lr=cfg.learning_rate, weight_decay=cfg.weight_decay)
        scheduler = get_linear_schedule_with_warmup(optimizer, int(cfg.warmup_fraction * total_steps), total_steps)
        generator = torch.Generator().manual_seed(cfg.seed)

        self.history, self.best_epoch = [], None
        best_score, best_state = -math.inf, None
        for epoch in range(1, cfg.epochs + 1):
            self.model.train()
            order = torch.randperm(len(train), generator=generator)
            running_loss = 0.0
            for start in range(0, len(train), cfg.batch_size):
                index = order[start:start + cfg.batch_size]
                batch = encode_pairs(self.tokenizer, [train[i] for i in index.tolist()], cfg.max_length)
                batch = {k: v.to(self.device) for k, v in batch.items()}
                output = self.model(**batch, labels=labels[index].to(self.device))
                output.loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
                running_loss += output.loss.item() * len(index)
            row = {"epoch": epoch, "train_loss": running_loss / len(train)}
            if holdout:
                predictions = self.predict(holdout)
                gold = [i.label for i in holdout]
                predicted = [predictions[i.instance_id] for i in holdout]
                row["holdout_weighted_f1"] = float(f1_score(gold, predicted, average="weighted"))
                row["holdout_accuracy"] = float(np.mean([g == p for g, p in zip(gold, predicted)]))
                score = row["holdout_weighted_f1"]
            else:
                score = -row["train_loss"]
            if score > best_score:
                best_score = score
                best_state = {k: v.detach().cpu().clone() for k, v in self.model.state_dict().items()}
                self.best_epoch = epoch
            self.history.append(row)
            if log:
                log(" ".join(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}" for k, v in row.items()))
        if best_state is None:
            raise RuntimeError(
                "training produced no finite score in any epoch (loss was NaN or infinite); "
                "check the model dtype and the learning rate"
            )
        self.model.load_state_dict(best_state)
        return self

    @torch.no_grad()
    def predict_scores(self, instances: Sequence[Instance], batch_size: int = 64) -> pd.DataFrame:
        """Softmax probability per label, one row per instance in the given order."""
        self.model.eval()
        chunks = []
        for start in range(0, len(instances), batch_size):
            batch = encode_pairs(self.tokenizer, instances[start:start + batch_size], self.config.max_length)
            logits = self.model(**{k: v.to(self.device) for k, v in batch.items()}).logits
            chunks.append(torch.softmax(logits.float(), dim=-1).cpu().numpy())
        frame = pd.DataFrame(np.vstack(chunks), columns=list(LABELS))
        frame.insert(0, "instance_id", [i.instance_id for i in instances])
        return frame

    def predict(self, instances: Sequence[Instance]) -> dict[str, str]:
        scores = self.predict_scores(instances)
        best = scores[list(LABELS)].to_numpy().argmax(axis=1)
        return {instance_id: LABELS[k] for instance_id, k in zip(scores["instance_id"], best)}
