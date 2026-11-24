"""Content checks on the exact text the slides show: numbers traced to source files, references,
spelling (words found in the sources count as known), and doubled words."""
from __future__ import annotations

import csv
import io
import re
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

from .util import finding

# The trailing (?!\.\d) stops a decimal followed by a unit ("12.5ms") from being read as "12";
# such numbers are skipped, as unit-suffixed numbers always were (see references/typography.md).
NUM = re.compile(r"(?<![\w.\-/])[-+−]?\d{1,3}(?:,\d{3})+(?:\.\d+)?%?(?![\w\-/]|\.\d)|(?<![\w.\-/])[-+−]?\d+(?:\.\d+)?%?(?![\w\-/]|\.\d)")
WORD = re.compile(r"[A-Za-z][A-Za-z'’]+")
DOUBLED = re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE)
CITE = re.compile(r"\[(\d+(?:\s*[,–-]\s*\d+)*)\]")


def source_text(p: Path) -> str:
    if not p.is_file():
        return ""
    suf = p.suffix.lower()
    if suf == ".pdf":
        import pymupdf
        with pymupdf.open(p) as doc:
            return "\n".join(page.get_text() for page in doc)
    if suf == ".pptx":
        from pptx import Presentation
        out = []
        for s in Presentation(str(p)).slides:
            for sh in s.shapes:
                if sh.has_text_frame:
                    out.append(sh.text_frame.text)
        return "\n".join(out)
    text = p.read_text(encoding="utf-8", errors="replace")
    if suf in (".csv", ".tsv"):
        rows = csv.reader(io.StringIO(text), delimiter="\t" if suf == ".tsv" else ",")
        return "\n".join(" ".join(r) for r in rows)
    return text


def to_decimal(tok: str) -> tuple[Decimal, int, bool] | None:
    pct = tok.endswith("%")
    s = tok.rstrip("%").replace(",", "").replace("−", "-").lstrip("+")
    try:
        d = Decimal(s)
    except InvalidOperation:
        return None
    places = len(s.split(".")[1]) if "." in s else 0
    return d, places, pct


def source_numbers(texts: list[str]) -> list[Decimal]:
    vals = set()
    for t in texts:
        for m in NUM.finditer(t):
            v = to_decimal(m.group(0))
            if v:
                vals.add(v[0])
                # sources often write ratios; a slide may show them as percentages and vice versa
                vals.add(v[0] * 100)
                vals.add(v[0] / 100)
    return list(vals)


def supported(x: Decimal, places: int, pool: list[Decimal]) -> bool:
    """A slide value is supported when a source value rounds to it at the slide's precision. Exact
    ties accept both half-up (the usual convention) and half-even (Python's formatting)."""
    q = Decimal(1).scaleb(-places)
    for v in pool:
        for mode in (ROUND_HALF_UP, ROUND_HALF_EVEN):
            try:
                if abs(v.quantize(q, rounding=mode) - x) == 0 or abs(abs(v).quantize(q, rounding=mode) - abs(x)) == 0:
                    return True
            except InvalidOperation:
                break
    return False


def check_content(doms: dict[int, dict], deck_cfg: dict, sources: list[Path]) -> list[dict]:
    F: list[dict] = []
    rules = deck_cfg["rules"]
    src_texts = [source_text(p) for p in sources]
    for p, t in zip(sources, src_texts):
        if not t:
            F.append(finding("source-unreadable", "major", "content_accuracy", f"Source file missing or empty: {p}", None))
    pool = source_numbers(src_texts)
    refs = deck_cfg.get("references") or {}
    policy = rules["number_policy"]
    min_int = rules["min_integer_checked"]
    any_numbers = False

    for i, dom in sorted(doms.items()):
        texts = [t for t in dom.get("texts", []) if not t["flags"]["nocheck"]]
        has_numbers = False
        if policy != "off":
            for t in texts:
                if t["flags"]["source"]:
                    continue
                for m in NUM.finditer(t["text"]):
                    v = to_decimal(m.group(0))
                    if not v:
                        continue
                    x, places, pct = v
                    if places == 0 and not pct and abs(x) < min_int:
                        continue
                    has_numbers = True
                    if sources and not supported(x, places, pool):
                        F.append(finding("unsupported-number", policy, "content_accuracy",
                                         f"{m.group(0)} does not appear in any source file: “{t['text'][:70]}”.",
                                         i, {"number": m.group(0), "path": t["path"]}))
        any_numbers = any_numbers or has_numbers
        if has_numbers and rules["require_source_for_numbers"] and not any(t["flags"]["source"] for t in dom.get("texts", [])):
            F.append(finding("number-without-source", "major", "content_accuracy",
                             "Slide shows numbers but no source note.", i))
        for key in dom.get("refs", []):
            if key not in refs:
                F.append(finding("missing-reference", "major", "content_accuracy",
                                 f"Citation key “{key}” has no entry in deck.json references.", i, {"key": key}))
        for t in texts:
            for m in (CITE.finditer(t["text"]) if deck_cfg.get("check_citation_markers", True) else ()):
                for n in re.split(r"\s*[,–-]\s*", m.group(1)):
                    if n.isdigit() and (int(n) < 1 or int(n) > len(refs)):
                        F.append(finding("missing-reference", "major", "content_accuracy",
                                         f"Citation [{n}] has no matching reference ({len(refs)} listed).", i, {"marker": m.group(0)}))
            for m in DOUBLED.finditer(t["text"]):
                if not m.group(1).isdigit():
                    F.append(finding("doubled-word", "minor", "content_accuracy",
                                     f"Doubled word “{m.group(0)}”.", i, {"path": t["path"]}))

    if policy != "off" and not sources and any_numbers:
        F.append(finding("numbers-unchecked", "minor", "content_accuracy",
                         "Slides show numbers but deck.json lists no sources, so no number was checked.", None))
    if rules.get("spelling", True):
        F.extend(_spelling(doms, deck_cfg, src_texts))
    return F


def _spelling(doms: dict[int, dict], deck_cfg: dict, src_texts: list[str]) -> list[dict]:
    try:
        from spellchecker import SpellChecker
    except ImportError:
        return [finding("spelling-unchecked", "info", "content_accuracy", "pyspellchecker not installed; spelling not checked.")]
    sp = SpellChecker()
    known = {w.lower() for w in deck_cfg.get("glossary", [])}
    for t in src_texts:
        known.update(w.lower() for w in WORD.findall(t))
    F = []
    for i, dom in sorted(doms.items()):
        flagged = set()
        for t in dom.get("texts", []):
            fl = t["flags"]
            if fl["nocheck"] or fl["source"] or fl["spelling"]:
                continue
            for w in WORD.findall(t["text"]):
                core = w.strip("'’")
                if len(core) < 3 or core.isupper() or any(c.isupper() for c in core[1:]):
                    continue  # acronyms and CamelCase names
                lw = core.lower().replace("’", "'")
                if lw.endswith("'s"):
                    lw = lw[:-2]
                if lw in known or lw in flagged or not sp.unknown([lw]):
                    continue
                flagged.add(lw)
                guess = sp.correction(lw)
                F.append(finding("spelling", "minor", "content_accuracy",
                                 f"Possible misspelling “{core}”" + (f" (did you mean “{guess}”?)" if guess and guess != lw else "") + ".",
                                 i, {"word": core, "suggestion": guess}))
    return F
