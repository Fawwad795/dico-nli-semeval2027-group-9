"""Run the decoder method on DiCo-NLI track 1 on Modal: zero-shot and LoRA, one GPU container each.

Launch from the repository root with your own Modal profile active. A wave of jobs is one
``modal run`` that reads a JSON list of jobs (one app per wave stays under Modal's app-creation
rate limit; the jobs run in parallel containers):

    PYTHONIOENCODING=utf-8 uv run modal run --detach scripts/modal/train_decoder.py::main --run-id <date>-decoder-final-wave-a --jobs experiments/<run folder>/wave_a_jobs.json

Each job in the file is an object. ``mode`` is ``"zero-shot"`` or ``"lora"``; a LoRA job also
needs ``seed`` and ``consistency_weight`` (lambda). Optional: ``model_name``,
``reverse_negatives`` (false leaves the reversed copies of the negatives out of the loss) and
``answer_format`` (``"letters"`` or ``"words"``); see ``DecoderConfig``. Without ``--jobs`` the
older flags build the list: ``--seeds 13 --weights 0,1`` and ``--no-zero-shot``, for example a
one-epoch timing run with ``--weights 1 --epochs 1 --no-zero-shot``.

The GPU type is read from the environment when the run is launched (``DICO_NLI_GPU=T4``, default
``L4``). ``--micro-batch-size`` and ``--mixed-precision`` are memory levers that leave the
optimisation step unchanged (see ``DecoderConfig``); keep the same GPU type and the same two
settings for every run that is compared. A T4 has 16 GB and no fast bfloat16: use
``--no-mixed-precision --micro-batch-size 4`` there. Every epoch line in the log carries the
seconds and the peak GPU memory so far.

Each LoRA job trains on an 80/20 grouped split of train drawn with its seed (the 20 % slice,
the validation split, picks the epoch) and writes a checkpoint to the volume after every epoch,
so a preempted container continues from its last finished epoch. A zero-shot job trains nothing
and uses the validation split of seed 13. Every job then scores its validation split and dev in
both orders. Outputs land in the Modal volume ``dico-nli-runs`` under ``<run-id>/<system>/``:

- ``validation/``: ``probabilities_forward.csv`` and ``probabilities_reverse.csv`` of the kept
  epoch, ``reference.csv`` (the validation instances with their labels) and a copy of ``run.json``;
- ``dev/``: ``probabilities_forward.csv``, ``probabilities_reverse.csv``, ``predictions.csv``
  (single pass) and ``predictions_symmetrized.csv`` (official format);
- ``adapter/``: the LoRA adapter (not for zero-shot);
- ``run.json``: config, per-epoch history, kept epoch, seconds, GPU, peak memory, versions.

The job computes and prints nothing from the dev labels. Model and lambda selection read
``validation/`` and ``run.json`` only, and ``dev/`` is fetched after the selection is committed.
Fetch one part of a wave, and check that every file arrived, with ``scripts/modal/fetch_wave.py``.
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
DEFAULT_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
ZERO_SHOT_SPLIT_SEED = 13
JOB_DEFAULTS = {
    "seed": ZERO_SHOT_SPLIT_SEED,
    "consistency_weight": 0.0,
    "model_name": DEFAULT_MODEL,
    "reverse_negatives": True,
    "answer_format": "letters",
}
# What a finished job leaves in each folder; ``fetch_wave.py`` checks a fetch against it.
PART_FILES = {
    "validation": ("probabilities_forward.csv", "probabilities_reverse.csv", "reference.csv", "run.json"),
    "dev": ("probabilities_forward.csv", "probabilities_reverse.csv", "predictions.csv", "predictions_symmetrized.csv"),
    "adapter": ("adapter_config.json", "adapter_model.safetensors", "decoder.json"),
}

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


def normalise_job(job: dict) -> dict:
    """The job with every setting filled in; an unknown key or a missing one is an error."""
    unknown = set(job) - {"mode", *JOB_DEFAULTS}
    if unknown:
        raise ValueError(f"unknown job settings {sorted(unknown)} in {job}")
    if job.get("mode") not in ("zero-shot", "lora"):
        raise ValueError(f"mode must be 'zero-shot' or 'lora' in {job}")
    if job["mode"] == "lora":
        missing = [key for key in ("seed", "consistency_weight") if key not in job]
        if missing:
            raise ValueError(f"a lora job needs {missing} in {job}")
    else:
        # A zero-shot system is one deterministic model: it has no seed, lambda or loss option.
        fixed = [key for key in ("seed", "consistency_weight", "reverse_negatives")
                 if key in job and job[key] != JOB_DEFAULTS[key]]
        if fixed:
            raise ValueError(f"a zero-shot job cannot set {fixed} in {job}")
    return {**JOB_DEFAULTS, **job}


def system_name(job: dict) -> str:
    """The folder name of a job: the model, then every setting that differs from the default.
    ``qwen2.5-1.5b-zero-shot``, ``qwen2.5-1.5b-lora-lambda0.5-seed42``,
    ``qwen2.5-1.5b-lora-lambda0-seed13-norevneg``, ``qwen2.5-1.5b-zero-shot-words``."""
    job = normalise_job(job)
    name = job["model_name"].split("/")[-1].lower().replace("-instruct", "")
    if job["mode"] == "zero-shot":
        name += "-zero-shot"
    else:
        name += f"-lora-lambda{float(job['consistency_weight']):g}-seed{job['seed']}"
    if not job["reverse_negatives"]:
        name += "-norevneg"
    if job["answer_format"] != "letters":
        name += f"-{job['answer_format']}"
    return name


def load_jobs(path: Path | str) -> list[dict]:
    """The jobs of a wave from its JSON file, checked: two jobs may not share a system name."""
    import json

    jobs = [normalise_job(job) for job in json.loads(Path(path).read_text(encoding="utf-8"))]
    names = [system_name(job) for job in jobs]
    repeated = sorted({name for name in names if names.count(name) > 1})
    if repeated:
        raise ValueError(f"{path} lists these systems more than once: {repeated}")
    return jobs


def run_job(
    job: dict,
    run_id: str,
    settings: dict,
    code: dict | None,
    runs_root: Path | str,
    data_root: Path | str,
    make_classifier=None,
    commit=lambda: None,
) -> dict:
    """One job, start to finish. It is a plain function so that it can be dry-run locally on a
    tiny model (``make_classifier``); on Modal ``commit`` flushes the volume."""
    import json
    import time
    from dataclasses import asdict

    import peft
    import torch
    import transformers
    from sklearn.metrics import f1_score

    from dico_nli.data import LABELS, grouped_split, load_reference
    from dico_nli.method.decoder import CHECKPOINT_NAME, DecoderClassifier, DecoderConfig
    from dico_nli.method.reversal import symmetrize
    from dico_nli.scoring import write_predictions, write_reference

    job = normalise_job(job)
    mode, seed = job["mode"], job["seed"]
    train_all = load_reference(settings["track"], "train", root=Path(data_root))
    dev = load_reference(settings["track"], "dev", root=Path(data_root))
    fit_part, holdout = grouped_split(train_all, settings["holdout_fraction"], seed)
    config = DecoderConfig(
        model_name=job["model_name"], epochs=settings["epochs"], batch_size=settings["batch_size"],
        micro_batch_size=settings["micro_batch_size"], mixed_precision=settings["mixed_precision"],
        consistency_weight=job["consistency_weight"], seed=seed,
        reverse_negatives=job["reverse_negatives"], answer_format=job["answer_format"],
    )
    name = system_name(job)
    out = Path(runs_root) / run_id / name
    out.mkdir(parents=True, exist_ok=True)
    on_gpu = torch.cuda.is_available()
    gpu = torch.cuda.get_device_name(0) if on_gpu else "cpu"
    if on_gpu:
        torch.cuda.reset_peak_memory_stats()  # a warm container is reused; the peak belongs to this job

    def peak_gb() -> float:
        return torch.cuda.max_memory_allocated() / 2**30 if on_gpu else 0.0

    print(f"{name}: fit {len(fit_part)} validation {len(holdout)} dev {len(dev)} on {gpu}")

    def log(message: str) -> None:
        print(f"{name}: {message} peak_gpu_memory_gb={peak_gb():.1f}")
        commit()  # the checkpoint written just before an epoch line survives a preemption

    classifier = make_classifier(config) if make_classifier else DecoderClassifier(config)
    longest = classifier.max_prompt_tokens([*train_all, *dev])
    print(f"{name}: longest prompt {longest} tokens, limit {config.max_length}")
    if mode == "lora":
        classifier.fit(fit_part, holdout=holdout, log=log, checkpoint_dir=out)
        classifier.save(out / "adapter")

    columns = list(LABELS)

    def score_both_orders(instances, folder: Path):
        started = time.time()
        forward, reverse = classifier.predict_both_orders(instances)
        seconds = time.time() - started
        folder.mkdir(parents=True, exist_ok=True)
        forward.to_csv(folder / "probabilities_forward.csv", index=False)
        reverse.to_csv(folder / "probabilities_reverse.csv", index=False)
        return forward, reverse, seconds

    # Validation, with the weights of the kept epoch (fit ends by loading them).
    forward, _, validation_seconds = score_both_orders(holdout, out / "validation")
    write_reference(out / "validation" / "reference.csv", holdout)
    predicted = [LABELS[k] for k in forward[columns].to_numpy().argmax(axis=1)]
    from_probabilities = float(f1_score([i.label for i in holdout], predicted, average="weighted"))
    validation_check = {"weighted_f1_from_saved_probabilities": from_probabilities}
    if mode == "lora":
        at_kept_epoch = classifier.history[classifier.best_epoch - 1]["holdout_weighted_f1"]
        validation_check.update(weighted_f1_at_kept_epoch=at_kept_epoch, difference=from_probabilities - at_kept_epoch)
    print(f"{name}: validation {validation_check}")

    # Dev: probabilities and predictions only. Nothing here reads a dev label.
    forward, reverse, predict_seconds = score_both_orders(dev, out / "dev")
    single = forward[columns].to_numpy().argmax(axis=1)
    symmetric = symmetrize(forward[columns].to_numpy(), reverse[columns].to_numpy()).argmax(axis=1)
    ids = list(forward["instance_id"])
    write_predictions(out / "dev" / "predictions.csv", {i: LABELS[k] for i, k in zip(ids, single)})
    write_predictions(out / "dev" / "predictions_symmetrized.csv", {i: LABELS[k] for i, k in zip(ids, symmetric)})

    parameters = list(classifier.model.parameters())
    record = {
        "system": name,
        "mode": mode,
        "config": asdict(config),
        "holdout_fraction": settings["holdout_fraction"],
        "split_seed": seed,
        "fit_size": len(fit_part),
        "holdout_size": len(holdout),
        "dev_size": len(dev),
        "longest_prompt_tokens": longest,
        "history": classifier.history,
        "best_epoch": classifier.best_epoch,
        "validation_check": validation_check,
        "train_seconds": round(sum(row["seconds"] for row in classifier.history), 1),
        "validation_seconds": round(validation_seconds, 1),
        "predict_seconds": round(predict_seconds, 1),
        "trainable_parameters": sum(p.numel() for p in parameters if p.requires_grad) if mode == "lora" else 0,
        "total_parameters": sum(p.numel() for p in parameters),
        "gpu": gpu,
        "peak_gpu_memory_gb": round(peak_gb(), 2),
        "precision": "bfloat16 activations, float32 weights" if settings["mixed_precision"] else "float32",
        "versions": {"torch": torch.__version__, "transformers": transformers.__version__, "peft": peft.__version__},
        "code": code or {},
    }
    text = json.dumps(record, indent=2) + "\n"
    (out / "run.json").write_text(text, encoding="utf-8")
    (out / "validation" / "run.json").write_text(text, encoding="utf-8")
    (out / CHECKPOINT_NAME).unlink(missing_ok=True)  # the run is complete; the adapter is the record
    commit()
    summary = {"system": name, "train_seconds": record["train_seconds"], "peak_gpu_memory_gb": record["peak_gpu_memory_gb"]}
    if mode == "lora":
        summary.update(best_epoch=classifier.best_epoch, validation_weighted_f1=validation_check["weighted_f1_at_kept_epoch"],
                       validation_check_difference=validation_check["difference"])
    return summary


@app.function(gpu=GPU, timeout=2 * 60 * 60, volumes={REMOTE_RUNS: volume})
def run(job: dict, run_id: str, settings: dict, code: dict | None = None) -> dict:
    return run_job(job, run_id, settings, code, runs_root=REMOTE_RUNS, data_root=REMOTE_DATA, commit=volume.commit)


@app.local_entrypoint()
def main(
    run_id: str,
    jobs: str = "",
    seeds: str = "13",
    weights: str = "0,1",
    zero_shot: bool = True,
    epochs: int = 3,
    batch_size: int = 16,
    micro_batch_size: int = 8,
    mixed_precision: bool = True,
    model_name: str = DEFAULT_MODEL,
    track: int = 1,
):
    if jobs:
        job_list = load_jobs(jobs)
    else:
        job_list = [{"mode": "zero-shot", "model_name": model_name}] if zero_shot else []
        job_list += [{"mode": "lora", "seed": int(seed), "consistency_weight": float(weight), "model_name": model_name}
                     for seed in seeds.split(",") for weight in weights.split(",")]
        job_list = [normalise_job(job) for job in job_list]
    names = [system_name(job) for job in job_list]
    code = code_identity()
    print(f"code: {code}")
    print(f"gpu: {GPU}, mixed precision: {mixed_precision}, micro batch: {micro_batch_size}")
    print(f"{len(names)} jobs: {names}")
    settings = {"track": track, "epochs": epochs, "batch_size": batch_size, "micro_batch_size": micro_batch_size,
                "mixed_precision": mixed_precision, "holdout_fraction": 0.2}
    # One failed job must not hide the others: exceptions come back as results.
    results = run.starmap([(job, run_id, settings, code) for job in job_list], return_exceptions=True)
    failed = []
    for index, result in enumerate(results):  # read to the end, so the result stream closes cleanly
        name = names[index]
        if isinstance(result, BaseException):
            failed.append(name)
            print(f"FAILED {name}: {result!r}")
        else:
            print(result)
    print(f"done: {len(names) - len(failed)} of {len(names)} jobs under volume {VOLUME_NAME}/{run_id}")
    if failed:
        raise SystemExit(f"{len(failed)} jobs failed, rerun them with a jobs file that lists only them: {failed}")
