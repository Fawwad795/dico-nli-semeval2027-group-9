"""Run the decoder method on DiCo-NLI track 1 on Modal: zero-shot and LoRA, one GPU container each.

Launch from the repository root with your own Modal profile active. First a one-epoch timing
run, which also shows whether the settings fit the GPU's memory:

    PYTHONIOENCODING=utf-8 uv run modal run --detach scripts/modal/train_decoder.py --run-id <date>-decoder-timing --weights 1 --epochs 1 --no-zero-shot

Then the preliminary runs (zero-shot, LoRA with lambda 0, LoRA with lambda 1, seed 13):

    PYTHONIOENCODING=utf-8 uv run modal run --detach scripts/modal/train_decoder.py --run-id <date>-decoder-preliminary-track1

The GPU type is read from the environment when the run is launched (``DICO_NLI_GPU=T4``, default
``L4``). ``--micro-batch-size`` and ``--mixed-precision`` are memory levers that leave the
optimisation step unchanged (see ``DecoderConfig``); keep the same GPU type and the same two
settings for every run that is compared. A T4 has 16 GB and no fast bfloat16: use
``--no-mixed-precision --micro-batch-size 4`` there. Every epoch line in the log carries the
seconds and the peak GPU memory so far.

Each LoRA job trains on an 80/20 grouped split of train (the 20 % slice picks the epoch) and
writes a checkpoint to the volume after every epoch, so a preempted container continues from
its last finished epoch. Every job then scores dev once in both orders. Outputs land in the
Modal volume ``dico-nli-runs`` under ``<run-id>/<system>/``: ``probabilities_forward.csv`` and
``probabilities_reverse.csv``, ``predictions.csv`` (single pass) and
``predictions_symmetrized.csv`` (official format), ``run.json`` (config, per-epoch history, best
epoch, seconds, GPU, peak memory, versions) and, for LoRA, the adapter. Fetch them with

    uv run modal volume get dico-nli-runs <run-id> artifacts/decoder-preliminary-track1

(the local parent folder must already exist), then score and record them with
``notebooks/assignment-2/01_preliminary_verification.ipynb``.
"""

import os
from pathlib import Path

import modal

VOLUME_NAME = "dico-nli-runs"
REMOTE_DATA = "/data"
REMOTE_RUNS = "/runs"
GPU = os.environ.get("DICO_NLI_GPU", "L4")
PINS = [
    "torch==2.14.0",
    "transformers==5.17.0",
    "peft==0.21.3",
    "accelerate==1.15.0",
    "scikit-learn==1.9.1",
    "pandas==3.0.6",
]

image = modal.Image.debian_slim(python_version="3.11").pip_install(*PINS)
if modal.is_local():
    # Modal imports this file again inside the container (as /root/train_decoder.py), where the
    # repository does not exist; everything path-relative stays on the local side.
    REPO = Path(__file__).resolve().parents[2]
    image = image.add_local_dir(str(REPO / "src" / "dico_nli"), remote_path="/root/dico_nli").add_local_dir(
        str(REPO / "datasets" / "dico-nli" / "final_data"), remote_path=REMOTE_DATA
    )
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
app = modal.App("dico-nli-decoder", image=image)


def code_identity() -> dict:
    """Local only: the repository commit, whether the tree is dirty, and a digest of the
    ``dico_nli`` source actually shipped to the container, so a run stays traceable even
    when it was made before its commit."""
    import hashlib

    from dico_nli.experiments import repo_state

    commit, dirty = repo_state(REPO)
    digest = hashlib.sha256()
    for path in sorted((REPO / "src" / "dico_nli").rglob("*.py")):
        digest.update(path.relative_to(REPO).as_posix().encode())
        digest.update(path.read_bytes())
    return {"repo_commit": commit, "repo_dirty": dirty, "source_sha256": digest.hexdigest()}


def system_name(model_name: str, mode: str, consistency_weight: float, seed: int) -> str:
    """``qwen2.5-1.5b-zero-shot`` or ``qwen2.5-1.5b-lora-lambda1-seed13``."""
    short = model_name.split("/")[-1].lower().replace("-instruct", "")
    if mode == "zero-shot":
        return f"{short}-zero-shot"
    return f"{short}-lora-lambda{consistency_weight:g}-seed{seed}"


@app.function(gpu=GPU, timeout=2 * 60 * 60, volumes={REMOTE_RUNS: volume})
def run(
    mode: str,
    seed: int,
    run_id: str,
    consistency_weight: float = 1.0,
    track: int = 1,
    model_name: str = "Qwen/Qwen2.5-1.5B-Instruct",
    epochs: int = 3,
    batch_size: int = 16,
    micro_batch_size: int = 8,
    mixed_precision: bool = True,
    holdout_fraction: float = 0.2,
    code: dict | None = None,
) -> dict:
    import json
    import time
    from dataclasses import asdict

    import peft
    import torch
    import transformers

    from dico_nli.data import LABELS, grouped_split, load_reference
    from dico_nli.method.decoder import CHECKPOINT_NAME, DecoderClassifier, DecoderConfig
    from dico_nli.method.reversal import symmetrize
    from dico_nli.scoring import write_predictions

    if mode not in ("zero-shot", "lora"):
        raise ValueError(f"mode must be 'zero-shot' or 'lora', got {mode!r}")
    data_root = Path(REMOTE_DATA)
    train_all = load_reference(track, "train", root=data_root)
    dev = load_reference(track, "dev", root=data_root)
    fit_part, holdout = grouped_split(train_all, holdout_fraction, seed)
    config = DecoderConfig(
        model_name=model_name, epochs=epochs, batch_size=batch_size, micro_batch_size=micro_batch_size,
        mixed_precision=mixed_precision, consistency_weight=consistency_weight, seed=seed,
    )
    name = system_name(model_name, mode, consistency_weight, seed)
    out = Path(REMOTE_RUNS) / run_id / name
    out.mkdir(parents=True, exist_ok=True)
    gpu = torch.cuda.get_device_name(0)
    print(f"{name}: fit {len(fit_part)} holdout {len(holdout)} dev {len(dev)} on {gpu}")

    def log(message: str) -> None:
        print(f"{name}: {message} peak_gpu_memory_gb={torch.cuda.max_memory_allocated() / 2**30:.1f}")
        volume.commit()  # the checkpoint written just before an epoch line survives a preemption

    classifier = DecoderClassifier(config)
    longest = classifier.max_prompt_tokens([*train_all, *dev])
    print(f"{name}: longest prompt {longest} tokens, limit {config.max_length}")
    if mode == "lora":
        classifier.fit(fit_part, holdout=holdout, log=log, checkpoint_dir=out)
        classifier.save(out / "adapter")

    started = time.time()
    forward, reverse = classifier.predict_both_orders(dev)
    predict_seconds = time.time() - started
    forward.to_csv(out / "probabilities_forward.csv", index=False)
    reverse.to_csv(out / "probabilities_reverse.csv", index=False)
    columns = list(LABELS)
    single = forward[columns].to_numpy().argmax(axis=1)
    symmetric = symmetrize(forward[columns].to_numpy(), reverse[columns].to_numpy()).argmax(axis=1)
    ids = list(forward["instance_id"])
    write_predictions(out / "predictions.csv", {i: LABELS[k] for i, k in zip(ids, single)})
    write_predictions(out / "predictions_symmetrized.csv", {i: LABELS[k] for i, k in zip(ids, symmetric)})

    parameters = list(classifier.model.parameters())
    record = {
        "system": name,
        "mode": mode,
        "config": asdict(config),
        "holdout_fraction": holdout_fraction,
        "fit_size": len(fit_part),
        "holdout_size": len(holdout),
        "dev_size": len(dev),
        "longest_prompt_tokens": longest,
        "history": classifier.history,
        "best_epoch": classifier.best_epoch,
        "train_seconds": round(sum(row["seconds"] for row in classifier.history), 1),
        "predict_seconds": round(predict_seconds, 1),
        "trainable_parameters": sum(p.numel() for p in parameters if p.requires_grad) if mode == "lora" else 0,
        "total_parameters": sum(p.numel() for p in parameters),
        "gpu": gpu,
        "peak_gpu_memory_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2),
        "precision": "bfloat16 activations, float32 weights" if mixed_precision else "float32",
        "versions": {"torch": torch.__version__, "transformers": transformers.__version__, "peft": peft.__version__},
        "code": code or {},
    }
    (out / "run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    (out / CHECKPOINT_NAME).unlink(missing_ok=True)  # the run is complete; the adapter is the record
    volume.commit()
    summary = {"system": name, "train_seconds": record["train_seconds"], "peak_gpu_memory_gb": record["peak_gpu_memory_gb"]}
    if mode == "lora":
        best = classifier.history[classifier.best_epoch - 1]
        summary.update(best_epoch=classifier.best_epoch, holdout_weighted_f1=best.get("holdout_weighted_f1"))
    return summary


@app.local_entrypoint()
def main(
    run_id: str,
    seeds: str = "13",
    weights: str = "0,1",
    zero_shot: bool = True,
    epochs: int = 3,
    batch_size: int = 16,
    micro_batch_size: int = 8,
    mixed_precision: bool = True,
    model_name: str = "Qwen/Qwen2.5-1.5B-Instruct",
    track: int = 1,
):
    code = code_identity()
    print(f"code: {code}")
    print(f"gpu: {GPU}, mixed precision: {mixed_precision}, micro batch: {micro_batch_size}")
    first_seed = int(seeds.split(",")[0])
    jobs = []
    if zero_shot:
        jobs.append(("zero-shot", first_seed, run_id, 0.0))
    for seed in seeds.split(","):
        for weight in weights.split(","):
            jobs.append(("lora", int(seed), run_id, float(weight)))
    shared = (track, model_name, epochs, batch_size, micro_batch_size, mixed_precision, 0.2, code)
    for result in run.starmap([job + shared for job in jobs]):
        print(result)
    print(f"done: {len(jobs)} jobs under volume {VOLUME_NAME}/{run_id}")
