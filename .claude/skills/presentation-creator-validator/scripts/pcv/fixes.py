"""Safe automatic corrections, written as reviewable CSS overrides in <deck>/fixes/<slide>.css.

Only changes that cannot alter meaning are automatic: shrinking text that is clipped or spills out
of its box (never below the deck's minimum size) and letterboxing a stretched image. Each override
is recorded in fixes/ledger.json with the finding that caused it. The per-slide CSS is regenerated
from the ledger, so to undo a fix remove its ledger entry (or delete the whole fixes/ folder).
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

from .deckcfg import Deck
from .util import read_json, write_json


def _selector(deck: Deck, path: str) -> str:
    root = deck.render["selector"]
    return f"{root} > {path}" if path else root


def plan_fixes(deck: Deck, findings: list[dict]) -> tuple[list[dict], list[dict]]:
    """Returns (fixes to apply, findings that look fixable but are not safe to fix automatically)."""
    min_px = deck.rules["min_font_px"]
    apply, refuse = [], []
    for f in findings:
        fx = f.get("fix")
        if not fx or f.get("status") == "fixed":
            continue
        stem = Path(deck.cfg["slides"][f["slide"] - 1]).stem
        if fx["kind"] == "shrink-text":
            if fx["ratio"] >= 0.999:
                refuse.append({**f, "reason": "no shrink ratio could be measured (for example a zero-height box); fix the layout by hand"})
                continue
            # font_px is the CSS size the override sets; scale maps it to the size actually drawn
            # (CSS transforms, SVG viewBox), which is what the minimum applies to.
            new = math.floor(fx["font_px"] * fx["ratio"] * 0.97)
            drawn = new * fx.get("scale", 1.0)
            if drawn < min_px:
                refuse.append({**f, "reason": f"fitting needs {drawn:.0f}px as drawn, below the {min_px}px minimum; cut the text or enlarge the box"})
                continue
            apply.append({"stem": stem, "slide": f["slide"], "selector": _selector(deck, fx["path"]), "prop": "font-size",
                          "value": f"{new}px", "code": f["code"], "message": f["message"]})
        elif fx["kind"] == "object-fit":
            apply.append({"stem": stem, "slide": f["slide"], "selector": _selector(deck, fx["path"]), "prop": "object-fit",
                          "value": fx["value"], "code": f["code"], "message": f["message"]})
    return apply, refuse


def write_fixes(deck: Deck, fixes: list[dict]) -> list[int]:
    """Merge fixes into the ledger, regenerate per-slide CSS, return the affected 1-based slides."""
    d = deck.fixes_dir()
    ledger_p = d / "ledger.json"
    ledger = read_json(ledger_p) if ledger_p.is_file() else []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for fx in fixes:
        ledger = [e for e in ledger if not (e["stem"] == fx["stem"] and e["selector"] == fx["selector"] and e["prop"] == fx["prop"])]
        ledger.append({**fx, "at": now})
    write_json(ledger_p, ledger)
    for stem in {e["stem"] for e in ledger}:
        rules = [e for e in ledger if e["stem"] == stem]
        css = ["/* Automatic fixes from presentation-creator-validator. Review, then fold into the slide or delete. */"]
        for e in rules:
            css.append(f"/* {e['code']}: {e['message'][:120].replace('*/', '')} ({e['at']}) */")
            css.append(f"{e['selector']} {{ {e['prop']}: {e['value']} !important; }}")
        (d / f"{stem}.css").write_text("\n".join(css) + "\n", encoding="utf-8")
    return sorted({fx["slide"] for fx in fixes})
