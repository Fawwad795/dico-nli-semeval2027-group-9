"""Fine-tune an encoder on DiCo-NLI track 1 on Modal, one GPU container per seed.

Launch from the repository root with your own Modal profile active:

    PYTHONIOENCODING=utf-8 uv run modal run --detach scripts/modal/train_encoder.py --seeds 13,42,1234 --run-id 2026-09-29-deberta-base-track1

Each seed trains on an 80/20 grouped split of train (the 20 % slice picks the epoch), then
predicts dev once. Outputs land in the Modal volume ``dico-nli-runs`` under
``<run-id>/seed<seed>/``: ``predictions.csv`` (official format), ``probabilities.csv``,
``run.json`` (config, per-epoch history, best epoch, timing, GPU). Fetch them with

    uv run modal volume get dico-nli-runs <run-id> artifacts/dl-baseline-track1

(the local parent folder must already exist), then score and record them with
``notebooks/assignment-1/04_dl_baseline_track1.ipynb``.
"""

from pathlib import Path

import modal

VOLUME_NAME = "dico-nli-runs"
REMOTE_DATA = "/data"
REMOTE_RUNS = "/runs"
PINS = [
    "torch==2.14.0",
    "transformers==5.17.0",
    "sentencepiece==0.2.2",
    "protobuf==6.33.6",
    "scikit-learn==1.9.1",
    "pandas==3.0.6",
]

image = modal.Image.debian_slim(python_version="3.11").pip_install(*PINS)
if modal.is_local():
    # Modal imports this file again inside the container (as /root/train_encoder.py), where the
    # repository does not exist; everything path-relative stays on the local side.
    REPO = Path(__file__).resolve().parents[2]
    image = image.add_local_dir(str(REPO / "src" / "dico_nli"), remote_path="/root/dico_nli").add_local_dir(
        str(REPO / "datasets" / "dico-nli" / "final_data"), remote_path=REMOTE_DATA
    )
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
app = modal.App("dico-nli-encoder", image=image)


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


@app.function(gpu="T4", timeout=60 * 60, volumes={REMOTE_RUNS: volume})
def train(
    seed: int,
    run_id: str,
    track: int = 1,
    model_name: str = "microsoft/deberta-v3-base",
    epochs: int = 5,
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    max_length: int = 32,
    holdout_fraction: float = 0.2,
    code: dict | None = None,
) -> dict:
    import json
    import time
    from dataclasses import asdict

    import torch

    from dico_nli.baselines.encoder import EncoderBaseline, EncoderConfig
    from dico_nli.data import grouped_split, load_reference
    from dico_nli.scoring import write_predictions

    data_root = Path(REMOTE_DATA)
    train_all = load_reference(track, "train", root=data_root)
    dev = load_reference(track, "dev", root=data_root)
    fit_part, holdout = grouped_split(train_all, holdout_fraction, seed)
    config = EncoderConfig(
        model_name=model_name, max_length=max_length, batch_size=batch_size, epochs=epochs,
        learning_rate=learning_rate, seed=seed,
    )
    print(f"seed {seed}: fit {len(fit_part)} holdout {len(holdout)} dev {len(dev)} on {torch.cuda.get_device_name(0)}")

    started = time.time()
    baseline = EncoderBaseline(config).fit(fit_part, holdout=holdout, log=print)
    seconds = time.time() - started

    out = Path(REMOTE_RUNS) / run_id / f"seed{seed}"
    out.mkdir(parents=True, exist_ok=True)
    write_predictions(out / "predictions.csv", baseline.predict(dev))
    baseline.predict_scores(dev).to_csv(out / "probabilities.csv", index=False)
    record = {
        "config": asdict(config),
        "holdout_fraction": holdout_fraction,
        "fit_size": len(fit_part),
        "holdout_size": len(holdout),
        "dev_size": len(dev),
        "history": baseline.history,
        "best_epoch": baseline.best_epoch,
        "train_seconds": round(seconds, 1),
        "gpu": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "code": code or {},
    }
    (out / "run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    volume.commit()
    best = baseline.history[baseline.best_epoch - 1]
    return {"seed": seed, "best_epoch": baseline.best_epoch, "holdout_weighted_f1": best["holdout_weighted_f1"], "train_seconds": round(seconds, 1)}


@app.local_entrypoint()
def main(seeds: str = "13,42,1234", run_id: str = "deberta-base-track1", track: int = 1, epochs: int = 5):
    code = code_identity()
    print(f"code: {code}")
    jobs = [(int(seed), run_id, track, "microsoft/deberta-v3-base", epochs, 16, 2e-5, 32, 0.2, code)
            for seed in seeds.split(",")]
    for result in train.starmap(jobs):
        print(result)
    print(f"done: {len(jobs)} seeds under volume {VOLUME_NAME}/{run_id}")
