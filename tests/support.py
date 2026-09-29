"""Paths and markers shared by the test suite."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
FIXTURE_REFERENCE = FIXTURES / "track1_reference_sample.csv"
DATA_CLONE = REPO_ROOT / "datasets" / "dico-nli"

requires_data_clone = pytest.mark.skipif(
    not (DATA_CLONE / "evaluation_functions" / "__main__.py").exists(),
    reason=(
        "the task repository is not cloned at datasets/dico-nli; "
        "see datasets/dico-nli.json for the download command"
    ),
)
