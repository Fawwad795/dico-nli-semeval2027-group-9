"""dico_nli.experiments: the run record every reported number traces back to."""

import json
import subprocess
from datetime import date

import pytest

from dico_nli.experiments import data_commit, experiment_dir, repo_state, write_config, write_results_table
from dico_nli.scoring import Scores


def test_experiment_dir_is_dated_and_slugged(tmp_path):
    path = experiment_dir("trivial-baselines-track1", root=tmp_path, day=date(2026, 9, 29))

    assert path == tmp_path / "2026-09-29-trivial-baselines-track1"
    assert path.is_dir()


def test_experiment_dir_refuses_to_reuse_a_recorded_run_unless_overwrite_is_explicit(tmp_path):
    path = experiment_dir("x", root=tmp_path, day=date(2026, 9, 29))
    (path / "config.json").write_text("{}", encoding="utf-8")

    with pytest.raises(FileExistsError, match="2026-09-29-x"):
        experiment_dir("x", root=tmp_path, day=date(2026, 9, 29))
    assert experiment_dir("x", root=tmp_path, day=date(2026, 9, 29), overwrite=True) == path


def test_experiment_dir_overwrite_starts_from_an_empty_folder(tmp_path):
    path = experiment_dir("x", root=tmp_path, day=date(2026, 9, 29))
    (path / "config.json").write_text("{}", encoding="utf-8")
    (path / "scores" / "old-system").mkdir(parents=True)
    (path / "scores" / "old-system" / "scores.json").write_text("{}", encoding="utf-8")

    again = experiment_dir("x", root=tmp_path, day=date(2026, 9, 29), overwrite=True)

    assert again == path and path.is_dir()
    assert list(path.iterdir()) == []


def test_experiment_dir_overwrite_keeps_the_hand_written_findings(tmp_path):
    path = experiment_dir("x", root=tmp_path, day=date(2026, 9, 29))
    (path / "config.json").write_text("{}", encoding="utf-8")
    (path / "findings.md").write_text("# what we learned\n", encoding="utf-8")
    (path / "results.md").write_text("| generated |\n", encoding="utf-8")

    experiment_dir("x", root=tmp_path, day=date(2026, 9, 29), overwrite=True)

    assert [p.name for p in path.iterdir()] == ["findings.md"]
    assert (path / "findings.md").read_text(encoding="utf-8") == "# what we learned\n"


def test_repo_state_reports_head_and_whether_the_tree_is_dirty(tmp_path):
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.org"]
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(git + ["commit", "-q", "--allow-empty", "-m", "start"], cwd=tmp_path, check=True)

    commit, dirty = repo_state(tmp_path)
    assert len(commit) == 40 and dirty is False

    (tmp_path / "scratch.txt").write_text("x", encoding="utf-8")
    assert repo_state(tmp_path) == (commit, True)


def test_repo_state_outside_a_checkout_is_unknown(tmp_path):
    assert repo_state(tmp_path) == ("unknown", None)


def test_data_commit_comes_from_the_dataset_record():
    assert data_commit() == "588968e610197ddc4c440314701cbc587afc4c1b"


def test_write_config_records_seed_data_commit_repo_commit_and_command(tmp_path):
    path = write_config(tmp_path, seed=13, track=1, command="uv run jupyter execute notebooks/assignment-1/x.ipynb", extra={"note": "x"})

    config = json.loads(path.read_text(encoding="utf-8"))
    assert path == tmp_path / "config.json"
    assert config["seed"] == 13
    assert config["track"] == 1
    assert config["data_commit"] == "588968e610197ddc4c440314701cbc587afc4c1b"
    assert len(config["repo_commit"]) == 40
    assert config["repo_dirty"] in (True, False)
    assert config["command"] == "uv run jupyter execute notebooks/assignment-1/x.ipynb"
    assert config["note"] == "x"
    assert path.read_text(encoding="utf-8").endswith("}\n")


def test_write_results_table_renders_one_row_per_system(tmp_path):
    rows = {
        "majority": Scores(0.15, 0.0, 0.0, tmp_path / "scores" / "majority" / "scores.json"),
        "random (seed 13)": Scores(0.2696, 0.2083, 0.0774, tmp_path / "scores" / "random" / "scores.json"),
    }

    path = write_results_table(tmp_path, rows, title="Trivial baselines, track 1 dev")

    text = path.read_text(encoding="utf-8")
    assert path == tmp_path / "results.md"
    assert "| System | Weighted F1 | SoftCons | HardCons |" in text
    assert "| majority | 0.150 | 0.000 | 0.000 |" in text
    assert "| random (seed 13) | 0.270 | 0.208 | 0.077 |" in text
    assert text.startswith("# Trivial baselines, track 1 dev")
