"""Design-system support: import a design system (tokens.json + component CSS/JS + README, e.g. a
Claude Design System artifact's project/ files) into a deck, and audit it before slides are built."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from .checks_image import contrast
from .util import finding, read_json, write_json

GROUND = re.compile(r"^(surface.*|paper|highlight|background.*|bg.*|.*-soft)$")
TEXTISH = re.compile(r"^(ink.*|text.*|.*-text|fg.*|foreground.*)$")
HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def _theme_values(tok: dict, themes: list[str]) -> dict:
    v = tok["value"]
    if isinstance(v, str):
        return {themes[0]: v}
    return {t: v.get(t, v.get(themes[0])) for t in themes if v.get(t, v.get(themes[0])) is not None}


LENGTH_FAMILIES = {"spacing", "radius", "size", "sizes", "space", "border", "borderWidth", "layout"}


def prop(name: str) -> str:
    """Token name -> custom property; characters outside [A-Za-z0-9_-] (e.g. the dot in color.ink) are escaped."""
    return "--" + re.sub(r"([^A-Za-z0-9_-])", r"\\\1", name)


def _css_value(v, length: bool = True) -> str:
    if isinstance(v, (int, float)):
        return f"{v}px" if length else str(v)
    s = str(v)
    m = re.fullmatch(r"\{([A-Za-z0-9_.-]+)\}", s)
    return f"var({prop(m.group(1))})" if m else s


def tokens_css(tokens: dict) -> str:
    color = tokens.get("color", {})
    themes = [t["id"] for t in color.get("themes", [])] or ["light"]
    per_theme: dict[str, list[str]] = {t: [] for t in themes}
    for tok in color.get("tokens", []):
        for th, v in _theme_values(tok, themes).items():
            per_theme[th].append(f"  {prop(tok['name'])}: {_css_value(v, length=False)};")
    base = list(per_theme[themes[0]])
    for key, fam in (tokens.get("type", {}).get("families") or {}).items():
        base.append(f"  --font-{key}: {fam};")
    for group in tokens.get("type", {}).get("groups", []):
        for st in group.get("styles", []):
            n = st["name"]
            base.append(f"  --type-{n}-size: {_css_value(st['fontSize'])};")
            if "lineHeight" in st:
                base.append(f"  --type-{n}-line: {st['lineHeight']};")
            if "fontWeight" in st:
                base.append(f"  --type-{n}-weight: {st['fontWeight']};")
    for fam_name, fam in tokens.items():
        if fam_name in ("color", "type", "name", "version", "meta") or not isinstance(fam, dict):
            continue
        for tok in fam.get("tokens", []):
            if isinstance(tok["value"], dict):  # per-theme value (shadows may differ by theme, like colours)
                for th, v in _theme_values(tok, themes).items():
                    (base if th == themes[0] else per_theme[th]).append(f"  {prop(tok['name'])}: {_css_value(v, length=False)};")
                continue
            base.append(f"  {prop(tok['name'])}: {_css_value(tok['value'], length=fam_name in LENGTH_FAMILIES)};")
    out = [f"/* {tokens.get('name', 'Design system')}: generated from tokens.json by presentation-creator-validator */",
           ":root {", *base, "}"]
    for th in themes[1:]:
        out += [f'[data-theme="{th}"] {{', *per_theme[th], "}"]
    return "\n".join(out) + "\n"


def import_ds(src: Path, deck_dir: Path) -> Path:
    """Copy a design system's files into <deck>/design-system/ and generate tokens.css."""
    src = src.resolve()
    tokens_p = next((p for p in (src / "tokens.json", src / "project" / "tokens.json") if p.is_file()), None)
    if not tokens_p:
        raise FileNotFoundError(f"no tokens.json under {src}")
    root = tokens_p.parent
    dst = deck_dir / "design-system"
    dst.mkdir(parents=True, exist_ok=True)
    for rel in ("tokens.json", "README.md", "components/bundle.css", "components/bundle.js", "components/index.d.ts"):
        if (root / rel).is_file():
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / rel, dst / rel)
    (dst / "tokens.css").write_text(tokens_css(read_json(tokens_p)), encoding="utf-8")
    return dst


def _rgb(v: str):
    m = HEX.match(v or "")
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def audit_ds(src: Path, min_font_px: float = 22) -> dict:
    src = src.resolve()
    tokens_p = next((p for p in (src / "tokens.json", src / "project" / "tokens.json", src / "design-system" / "tokens.json") if p.is_file()), None)
    if not tokens_p:
        raise FileNotFoundError(f"no tokens.json under {src}")
    tokens = read_json(tokens_p)
    color = tokens.get("color", {})
    themes = [t["id"] for t in color.get("themes", [])] or ["light"]
    toks = {t["name"]: t for t in color.get("tokens", [])}
    grounds = [n for n in toks if GROUND.match(n)]
    F, pairs = [], []
    for name, tok in toks.items():
        if not TEXTISH.match(name):
            continue
        usage = tok.get("usage", "")
        ul = usage.lower()
        marks_only = "never text" in ul or ("non-text" in ul and "text of" not in ul)
        if marks_only:
            continue
        need = 3.0 if re.search(r"(\d+)px or more|large text|3:1", ul) else 4.5
        # Grounds a usage note allows; a sentence like "Never on highlight." forbids, so it does not count.
        allowed_text = " ".join(s for s in re.split(r"(?<=[.;])\s+", usage)
                                if not re.search(r"\b(never|not|avoid|don't|do not)\b", s, re.I))
        named = [g for g in grounds if re.search(rf"(?<![\w-]){re.escape(g)}(?![\w-])", allowed_text)]
        targets = named or [g for g in grounds if g.startswith("surface")]
        for th in themes:
            fg = _rgb(_theme_values(tok, themes).get(th, ""))
            for g in targets:
                bg = _rgb(_theme_values(toks[g], themes).get(th, ""))
                if not fg or not bg:
                    continue
                r = contrast(fg, bg)
                ok = r >= need
                pairs.append({"text": name, "ground": g, "theme": th, "ratio": round(r, 2), "required": need, "ok": ok,
                              "ground_named_in_usage": bool(named)})
                if not ok:
                    F.append(finding("ds-token-contrast", "major", "typography",
                                     f"{name} on {g} ({th}) is {r:.2f}:1, below {need}:1"
                                     + ("; the token's usage note names this ground." if named else "."),
                                     None, {"text": name, "ground": g, "theme": th}))
    css_p = tokens_p.parent / "components" / "bundle.css"
    small = []
    if css_p.is_file():
        css = re.sub(r"/\*.*?\*/", "", css_p.read_text(encoding="utf-8"), flags=re.S)
        for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
            for m in re.finditer(r"font(?:-size)?\s*:\s*[^;]*?(\d+(?:\.\d+)?)px", body):
                px = float(m.group(1))
                if px < min_font_px:
                    small.append({"selector": sel.strip(), "px": px})
                    F.append(finding("ds-font-below-minimum", "minor", "typography",
                                     f"{sel.strip()} sets {px:g}px text, below the {min_font_px:g}px minimum.", None,
                                     {"selector": sel.strip(), "px": px}))
    return {"tokens": str(tokens_p), "pairs": pairs, "small_fonts": small, "findings": F}


def audit_md(name: str, audit: dict) -> str:
    L = [f"# Design system audit: {name}", "", f"Tokens: `{audit['tokens']}`", "",
         "## Text-token contrast", "", "| Text token | Ground | Theme | Ratio | Needs | Result |", "|---|---|---|---:|---:|---|"]
    for p in audit["pairs"]:
        L.append(f"| {p['text']} | {p['ground']} | {p['theme']} | {p['ratio']}:1 | {p['required']}:1 | {'pass' if p['ok'] else '**fail**'} |")
    L += ["", "Grounds are the ones each token's usage note names; where a note names none, every surface token is tested.", "",
          "## Component type below the minimum size", ""]
    L += [f"- `{s['selector']}`: {s['px']:g}px" for s in audit["small_fonts"]] or ["- none"]
    L += ["", "## Findings", ""]
    L += [f"- `{f['code']}` ({f['severity']}): {f['message']}" for f in audit["findings"]] or ["- none"]
    return "\n".join(L) + "\n"


def write_audit(src: Path, out: Path, min_font_px: float) -> Path:
    a = audit_ds(src, min_font_px)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "ds-audit.json", a)
    p = out / "ds-audit.md"
    p.write_text(audit_md(src.name, a), encoding="utf-8")
    return p
