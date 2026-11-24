"""Shared setup for the presentation-creator-validator tests.

Run from the repository root:
    PYTHONDONTWRITEBYTECODE=1 uv run --group slides pytest .claude/skills/presentation-creator-validator/tests -p no:cacheprovider -q
Deselect the Chrome pipeline tests with -m "not browser".
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True  # never write __pycache__ into .claude/

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "browser: runs the real render pipeline in headed Chrome (slow; deselect with -m 'not browser')",
    )
